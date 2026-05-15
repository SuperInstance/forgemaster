#!/usr/bin/env python3
"""Fleet Hebbian Service — real-time conservation-constrained Hebbian routing.

Standalone service that:
  - Boots a local PLATO store from SQLite
  - Runs the Hebbian layer continuously on tile flow
  - Tracks room clusters in real-time
  - Monitors conservation law compliance (γ+H within bounds)
  - Exposes an HTTP API on :8849

Architecture:
    Local PLATO (SQLite) ─► HebbianLayer ─► ConservationKernel
            │                     │               │
            ▼                     ▼               ▼
       TileFlowTracker    HebbianRouter     ConservationReport
            │                     │
            ▼                     ▼
    RoomClusterDetector    EmergentStageClassifier

Run:
    python fleet_hebbian_service.py              # :8849
    python fleet_hebbian_service.py --port 9000   # custom port
    python fleet_hebbian_service.py --simulate    # inject synthetic tiles
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import threading
import time
import urllib.request
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict, List, Optional, Set, Tuple
from socketserver import ThreadingMixIn

# MythosTile integration
try:
    from mythos_tile import MythosTile
    HAS_MYTHOS = True
except ImportError:
    HAS_MYTHOS = False

import numpy as np

# ---------------------------------------------------------------------------
# Inline conservation math (no external dependency beyond numpy)
# ---------------------------------------------------------------------------

CONSERVATION_INTERCEPT = 1.283
CONSERVATION_LOG_COEFF = -0.159

CONSERVATION_SIGMA_TABLE = {
    5: 0.070, 10: 0.065, 20: 0.058, 30: 0.050,
    50: 0.048, 100: 0.042, 200: 0.038,
}


def _interpolate_sigma(V: int) -> float:
    vs = sorted(CONSERVATION_SIGMA_TABLE.keys())
    if V <= vs[0]:
        return CONSERVATION_SIGMA_TABLE[vs[0]]
    if V >= vs[-1]:
        return CONSERVATION_SIGMA_TABLE[vs[-1]]
    for lo, hi in zip(vs, vs[1:]):
        if lo < V <= hi:
            frac = (V - lo) / (hi - lo)
            return CONSERVATION_SIGMA_TABLE[lo] + frac * (
                CONSERVATION_SIGMA_TABLE[hi] - CONSERVATION_SIGMA_TABLE[lo]
            )
    return 0.05


def predicted_gamma_plus_H(V: int) -> float:
    return CONSERVATION_INTERCEPT + CONSERVATION_LOG_COEFF * np.log(max(V, 3))


def coupling_entropy(C: np.ndarray) -> float:
    eigs = np.linalg.eigvalsh(C)[::-1]
    p = np.abs(eigs) / (np.sum(np.abs(eigs)) + 1e-15)
    p = p[p > 1e-10]
    return float(-np.sum(p * np.log(p)) / np.log(len(eigs)))


def algebraic_normalized(C: np.ndarray) -> float:
    if C.shape[0] < 2:
        return 0.0
    L = np.diag(C.sum(axis=1)) - C
    eigs = np.linalg.eigvalsh(L)
    return float((eigs[1] - eigs[0]) / (eigs[-1] - eigs[0] + 1e-15))


# ---------------------------------------------------------------------------
# FlowRecord + TileFlowTracker (from hebbian_layer.py, inlined)
# ---------------------------------------------------------------------------

@dataclass
class FlowRecord:
    source_room: str
    dest_room: str
    tile_type: str
    tile_hash: str
    timestamp: float = field(default_factory=time.monotonic)
    lamport_clock: int = 0


class TileFlowTracker:
    """Thread-safe ring buffer of tile flow events with recency-weighted stats."""

    def __init__(self, ring_size: int = 50_000, decay_half_life: float = 3600.0):
        self._ring: deque = deque(maxlen=ring_size)
        self._half_life = decay_half_life
        self._lock = threading.RLock()
        self._strength_cache: Dict[Tuple[str, str], float] = {}
        self._type_freq_cache: Dict[str, float] = {}
        self._cache_valid = False
        self._lamport: int = 0

    def record_flow(self, source_room: str, dest_room: str, tile_type: str,
                    tile_hash: str = "", lamport_clock: int = 0) -> FlowRecord:
        with self._lock:
            self._lamport = max(self._lamport, lamport_clock) + 1
            rec = FlowRecord(
                source_room=source_room, dest_room=dest_room,
                tile_type=tile_type, tile_hash=tile_hash,
                timestamp=time.monotonic(), lamport_clock=self._lamport,
            )
            self._ring.append(rec)
            self._cache_valid = False
            return rec

    def _rebuild_caches(self):
        now = time.monotonic()
        pair_w: Dict[Tuple[str, str], float] = defaultdict(float)
        type_w: Dict[str, float] = defaultdict(float)
        total = 0.0
        for rec in self._ring:
            age = now - rec.timestamp
            w = 2.0 ** (-age / self._half_life)
            pair_w[(rec.source_room, rec.dest_room)] += w
            type_w[rec.tile_type] += w
            total += w
        self._type_freq_cache = {t: v / total for t, v in type_w.items()} if total else {}
        mx = max(pair_w.values(), default=1.0)
        self._strength_cache = {k: min(1.0, v / mx) for k, v in pair_w.items()}
        self._cache_valid = True

    def get_connection_strength(self, a: str, b: str) -> float:
        with self._lock:
            if not self._cache_valid:
                self._rebuild_caches()
            return max(
                self._strength_cache.get((a, b), 0.0),
                self._strength_cache.get((b, a), 0.0),
            )

    def room_neighbors(self, room: str, min_strength: float = 0.1) -> List[Tuple[str, float]]:
        with self._lock:
            if not self._cache_valid:
                self._rebuild_caches()
            result = []
            for (a, b), s in self._strength_cache.items():
                if s < min_strength:
                    continue
                if a == room:
                    result.append((b, s))
                elif b == room:
                    result.append((a, s))
            result.sort(key=lambda x: x[1], reverse=True)
            return result

    def iter_recent(self, n: int = 1000):
        with self._lock:
            snap = list(self._ring)
        yield from reversed(snap[-n:])

    def __len__(self):
        return len(self._ring)


# ---------------------------------------------------------------------------
# ConservationHebbianKernel (from conservation_hebbian.py, inlined)
# ---------------------------------------------------------------------------

@dataclass
class ConservationReport:
    gamma: float
    H: float
    gamma_plus_H: float
    predicted: float
    deviation: float
    sigma: float
    conserved: bool
    correction_applied: bool
    scale_factor: float
    update_count: int


class ConservationHebbianKernel:
    """Hebbian weight update constrained by the fleet conservation law."""

    def __init__(self, n_rooms: int, V: Optional[int] = None,
                 learning_rate: float = 0.01, decay: float = 0.001,
                 tolerance_sigma: float = 2.0, correction_strength: float = 0.5,
                 dtype=np.float32):
        self.n = n_rooms
        self.V = V or min(n_rooms, 30)
        self.lr = learning_rate
        self.decay = decay
        self.tolerance_sigma = tolerance_sigma
        self.correction_strength = correction_strength
        self.dtype = dtype
        self._weights = np.zeros((n_rooms, n_rooms), dtype=dtype)
        self._predicted = predicted_gamma_plus_H(self.V)
        self._sigma = _interpolate_sigma(self.V)
        self._tolerance = tolerance_sigma * self._sigma
        self._update_count = 0
        self._correction_count = 0
        self._last_report: Optional[ConservationReport] = None
        self._lock = threading.Lock()
        self._warmup_samples: List[float] = []
        self._warmup_target = self._predicted
        self._auto_calibrated = False

    def update(self, pre: np.ndarray, post: np.ndarray) -> ConservationReport:
        with self._lock:
            return self._update_locked(pre, post)

    def _update_locked(self, pre: np.ndarray, post: np.ndarray) -> ConservationReport:
        pre = np.asarray(pre, dtype=self.dtype)
        post = np.asarray(post, dtype=self.dtype)
        delta = self.lr * np.outer(pre, post)
        self._weights += delta - self.decay * self._weights
        np.clip(self._weights, 0, None, out=self._weights)

        correction_applied = False
        scale_factor = 1.0
        try:
            gamma = algebraic_normalized(self._weights)
            H = coupling_entropy(self._weights)
            actual = gamma + H

            if self._update_count < 50:
                self._warmup_samples.append(actual)
                target = self._predicted
            elif not self._auto_calibrated:
                self._warmup_target = float(np.median(self._warmup_samples))
                self._auto_calibrated = True
                target = self._warmup_target
            else:
                target = self._warmup_target

            deviation = actual - target

            if abs(deviation) > self._tolerance:
                correction_applied = True
                self._correction_count += 1
                if deviation > 0:
                    threshold = np.percentile(self._weights[self._weights > 0], 50)
                    mask = self._weights < threshold
                    self._weights[mask] *= (1.0 - self.correction_strength)
                    scale_factor = float(np.mean(mask))
                else:
                    flat = self._weights.ravel()
                    top_k = max(1, int(0.1 * len(flat)))
                    top_idx = np.argpartition(flat, -top_k)[-top_k:]
                    flat[top_idx] *= (1.0 + self.correction_strength * 0.1)
                    scale_factor = float(-np.mean(flat[top_idx]))
        except (np.linalg.LinAlgError, ValueError):
            gamma, H, actual, deviation = 0.0, 0.0, 0.0, 0.0

        self._update_count += 1
        target = self._warmup_target if self._auto_calibrated else self._predicted
        deviation = actual - target

        self._last_report = ConservationReport(
            gamma=gamma, H=H, gamma_plus_H=actual, predicted=target,
            deviation=deviation, sigma=self._sigma,
            conserved=abs(deviation) <= self._tolerance,
            correction_applied=correction_applied, scale_factor=scale_factor,
            update_count=self._update_count,
        )
        return self._last_report

    def conservation_report(self) -> ConservationReport:
        if self._last_report is not None:
            return self._last_report
        try:
            gamma = algebraic_normalized(self._weights)
            H = coupling_entropy(self._weights)
        except (np.linalg.LinAlgError, ValueError):
            gamma, H = 0.0, 0.0
        actual = gamma + H
        return ConservationReport(
            gamma=gamma, H=H, gamma_plus_H=actual,
            predicted=self._predicted, deviation=actual - self._predicted,
            sigma=self._sigma, conserved=abs(actual - self._predicted) <= self._tolerance,
            correction_applied=False, scale_factor=1.0, update_count=self._update_count,
        )

    def get_weights(self) -> np.ndarray:
        return self._weights.copy()

    def set_weights(self, w: np.ndarray):
        self._weights = w.astype(self.dtype).copy()

    def compliance_rate(self) -> float:
        if self._update_count == 0:
            return 1.0
        return 1.0 - self._correction_count / self._update_count

    def summary(self) -> Dict[str, Any]:
        r = self.conservation_report()
        return {
            "n_rooms": self.n, "V": self.V,
            "update_count": self._update_count,
            "correction_count": self._correction_count,
            "compliance_rate": f"{self.compliance_rate():.1%}",
            "auto_calibrated": self._auto_calibrated,
            "warmup_target": round(self._warmup_target, 4),
            "conservation": {
                "gamma": round(r.gamma, 4), "H": round(r.H, 4),
                "sum": round(r.gamma_plus_H, 4),
                "predicted": round(r.predicted, 4),
                "deviation": round(r.deviation, 4),
                "sigma": round(r.sigma, 4),
                "conserved": r.conserved,
            },
            "params": {
                "lr": self.lr, "decay": self.decay,
                "tolerance_sigma": self.tolerance_sigma,
                "correction_strength": self.correction_strength,
            },
        }


# ---------------------------------------------------------------------------
# EmergentStageClassifier (simplified)
# ---------------------------------------------------------------------------

class EmergentStageClassifier:
    """Classify room stages from observed behavior."""

    def __init__(self, min_observations: int = 20):
        self.min_observations = min_observations
        self._records: Dict[Tuple[str, str], dict] = {}
        self._lock = threading.RLock()

    def observe(self, room: str, tile_type: str, success: bool,
                confidence: float, response_is_echo: bool = False):
        with self._lock:
            key = (room, tile_type)
            if key not in self._records:
                self._records[key] = {"room": room, "tile_type": tile_type,
                                      "total": 0, "successes": 0, "avg_conf": 0.0}
            rec = self._records[key]
            rec["total"] += 1
            eff_success = success and not response_is_echo
            if eff_success:
                rec["successes"] += 1
            alpha = 0.1
            rec["avg_conf"] = (1 - alpha) * rec["avg_conf"] + alpha * confidence

    def classify_room(self, room: str) -> int:
        with self._lock:
            records = [r for (rm, _), r in self._records.items() if rm == room]
        if not records:
            return 0
        total_obs = sum(r["total"] for r in records)
        if total_obs < self.min_observations:
            return 0
        weighted_success = sum(
            (r["successes"] / r["total"]) * r["total"] for r in records
        ) / total_obs
        weighted_conf = sum(r["avg_conf"] * r["total"] for r in records) / total_obs
        if weighted_success >= 0.80 and weighted_conf >= 0.70:
            return 4
        elif weighted_success < 0.05:
            return 1
        else:
            return 3

    def export_stages(self) -> Dict[str, int]:
        rooms = {r for (r, _) in self._records}
        return {room: self.classify_room(room) for room in rooms}


# ---------------------------------------------------------------------------
# RoomClusterDetector (simplified, networkx-free)
# ---------------------------------------------------------------------------

@dataclass
class RoomCluster:
    cluster_id: int
    rooms: List[str]
    dominant_tile_types: List[str]
    avg_internal_strength: float
    avg_external_strength: float


class RoomClusterDetector:
    """Detect room clusters from Hebbian weight matrix (no networkx dependency)."""

    def __init__(self, min_strength: float = 0.01, min_cluster_size: int = 2):
        self.min_strength = min_strength
        self.min_cluster_size = min_cluster_size
        self._last_clusters: List[RoomCluster] = []

    def detect(self, rooms: List[str], weights: np.ndarray,
               tracker: TileFlowTracker) -> List[RoomCluster]:
        n = len(rooms)
        if n < 2:
            return []

        # Build adjacency via union-find
        parent = list(range(n))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        # Connect rooms with mutual above-threshold weights
        for i in range(n):
            for j in range(i + 1, n):
                s = max(weights[i, j], weights[j, i])
                if s >= self.min_strength:
                    union(i, j)

        # Collect clusters
        groups: Dict[int, List[int]] = defaultdict(list)
        for i in range(n):
            groups[find(i)].append(i)

        clusters: List[RoomCluster] = []
        for cid, indices in enumerate(sorted(groups.values(), key=lambda g: -len(g))):
            if len(indices) < self.min_cluster_size:
                continue
            room_names = [rooms[i] for i in indices]
            idx_set = set(indices)

            # Internal strength
            intra = [float(max(weights[i, j], weights[j, i]))
                     for i in indices for j in indices if i < j]
            avg_internal = float(np.mean(intra)) if intra else 0.0

            # External strength (sample)
            external_idx = [i for i in range(n) if i not in idx_set]
            inter = [float(max(weights[i, j], weights[j, i]))
                     for i in indices[:5] for j in external_idx[:10]]
            avg_external = float(np.mean(inter)) if inter else 0.0

            # Dominant tile types from flow tracker
            type_counts: Dict[str, float] = defaultdict(float)
            room_set = set(room_names)
            for rec in tracker.iter_recent(5000):
                if rec.source_room in room_set and rec.dest_room in room_set:
                    type_counts[rec.tile_type] += 1.0
            total_t = sum(type_counts.values()) or 1
            dominant = [t for t, c in sorted(type_counts.items(), key=lambda x: -x[1])
                        if c / total_t > 0.10][:5]

            clusters.append(RoomCluster(
                cluster_id=cid, rooms=sorted(room_names),
                dominant_tile_types=dominant,
                avg_internal_strength=round(avg_internal, 4),
                avg_external_strength=round(avg_external, 4),
            ))

        self._last_clusters = clusters
        return clusters


# ---------------------------------------------------------------------------
# HebbianRouter
# ---------------------------------------------------------------------------

class HebbianRouter:
    """Route tiles to rooms based on emergent Hebbian weights."""

    def __init__(self, tracker: TileFlowTracker, all_rooms: List[str],
                 room_index: Dict[str, int], kernel: ConservationHebbianKernel):
        self.tracker = tracker
        self.all_rooms = all_rooms
        self.room_index = room_index
        self.kernel = kernel

    def route(self, tile_type: str, source_room: str) -> List[str]:
        """Return ordered list of destination rooms for a tile."""
        novelty = self.tracker.get_connection_strength(source_room, source_room)  # self-conn as proxy

        # Get neighbors by Hebbian strength
        neighbors = self.tracker.room_neighbors(source_room, min_strength=0.05)

        if not neighbors and len(self.tracker) < 50:
            # Cold start: distribute to rooms matching tile type
            matches = [r for r in self.all_rooms if tile_type in r.lower()][:3]
            return matches or self.all_rooms[:2]

        # Weighted by Hebbian kernel weights too
        src_idx = self.room_index.get(source_room)
        if src_idx is not None:
            w = self.kernel.get_weights()
            room_scores = []
            for i, room in enumerate(self.all_rooms):
                if room == source_room:
                    continue
                score = float(w[src_idx, i]) + float(w[i, src_idx])
                room_scores.append((room, score))
            room_scores.sort(key=lambda x: -x[1])
            return [r for r, _ in room_scores[:6] if r != source_room]

        return [r for r, _ in neighbors[:6]]


# ---------------------------------------------------------------------------
# FleetHebbianService — the main service orchestrator
# ---------------------------------------------------------------------------

class FleetHebbianService:
    """Orchestrates local PLATO, Hebbian kernel, routing, clustering, and API.

    Runnable standalone with just Python + numpy.
    """

    def __init__(self, db_path: Optional[str] = None, port: int = 8849,
                 persist_dir: Optional[str] = None):
        self.port = port
        self.persist_dir = persist_dir or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), ".hebbian-service"
        )
        os.makedirs(self.persist_dir, exist_ok=True)

        # Boot local PLATO
        self.db_path = db_path or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), ".local-plato", "plato.db"
        )
        self._rooms: List[str] = []
        self._room_index: Dict[str, int] = {}
        self._room_domains: Dict[str, str] = {}

        self._boot_plato()

        n = len(self._rooms) or 10  # fallback to 10 if no rooms

        # Core modules
        self.tracker = TileFlowTracker()
        self.kernel = ConservationHebbianKernel(n_rooms=n, V=min(n, 30))
        self.stage_classifier = EmergentStageClassifier()
        self.cluster_detector = RoomClusterDetector()
        self.router = HebbianRouter(self.tracker, self._rooms, self._room_index, self.kernel)

        # Flow event log for the API
        self._recent_flow: deque = deque(maxlen=500)
        self._lock = threading.Lock()

        # Service state
        self._running = False
        self._http_server: Optional[HTTPServer] = None

        # Load persisted weights if available
        weights_path = os.path.join(self.persist_dir, "weights.npy")
        if os.path.exists(weights_path) and n > 0:
            try:
                self.kernel.set_weights(np.load(weights_path))
            except Exception:
                pass

    def _boot_plato(self):
        """Boot rooms from local SQLite or create defaults."""
        if os.path.exists(self.db_path):
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                rows = conn.execute("SELECT DISTINCT room, domain FROM tiles").fetchall()
                for row in rows:
                    room = row["room"]
                    if room and room not in self._room_index:
                        self._rooms.append(room)
                        self._room_index[room] = len(self._rooms) - 1
                        self._room_domains[room] = row["domain"] or room
                conn.close()
            except Exception:
                pass

        # Ensure minimum viable rooms
        if len(self._rooms) < 3:
            defaults = ["forgemaster-local", "fleet-ops", "constraint-theory",
                        "session-state", "oracle1-coord", "training-pipeline"]
            for r in defaults:
                if r not in self._room_index:
                    self._rooms.append(r)
                    self._room_index[r] = len(self._rooms) - 1
                    self._room_domains[r] = r

        # Rebuild kernel with correct size if rooms were loaded
        n = len(self._rooms)
        self.kernel = ConservationHebbianKernel(n_rooms=n, V=min(n, 30))

    # ------------------------------------------------------------------
    # Tile submission and processing
    # ------------------------------------------------------------------

    def submit_tile(self, tile_type: str, source_room: str, dest_room: Optional[str] = None,
                    tile_hash: Optional[str] = None, confidence: float = 0.9,
                    tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """Submit a tile and process it through the Hebbian layer.

        If dest_room is provided, routes directly there.
        Otherwise, uses HebbianRouter to pick destinations.
        """
        tile_hash = tile_hash or hashlib.sha256(
            f"{tile_type}:{source_room}:{time.time()}".encode()
        ).hexdigest()[:16]

        # Route
        if dest_room:
            destinations = [dest_room]
        else:
            destinations = self.router.route(tile_type, source_room)

        results = []
        for dest in destinations:
            if dest == source_room:
                continue

            # Record flow
            self.tracker.record_flow(source_room, dest, tile_type, tile_hash)

            # Update kernel
            src_idx = self._room_index.get(source_room)
            dst_idx = self._room_index.get(dest)
            report = None
            if src_idx is not None and dst_idx is not None:
                n = len(self._rooms)
                pre = np.zeros(n, dtype=np.float32)
                post = np.zeros(n, dtype=np.float32)
                pre[src_idx] = 1.0
                post[dst_idx] = confidence
                report = self.kernel.update(pre, post)

            # Update stage classifier
            success = confidence > 0.5
            self.stage_classifier.observe(dest, tile_type, success, confidence)

            # Log
            flow_event = {
                "timestamp": time.time(),
                "source": source_room,
                "dest": dest,
                "tile_type": tile_type,
                "tile_hash": tile_hash,
                "confidence": confidence,
                "conserved": report.conserved if report else None,
                "correction": report.correction_applied if report else None,
            }
            self._recent_flow.append(flow_event)

            results.append({
                "dest_room": dest,
                "routed": True,
                "confidence": confidence,
                "conservation": {
                    "gamma_plus_H": round(report.gamma_plus_H, 4),
                    "conserved": report.conserved,
                    "correction_applied": report.correction_applied,
                } if report else None,
            })

        return {
            "tile_type": tile_type,
            "source_room": source_room,
            "tile_hash": tile_hash,
            "destinations": results,
            "total_routed": len(results),
        }

    # ------------------------------------------------------------------
    # Auto-calibration: inject tiles until Hebbian regime stabilizes
    # ------------------------------------------------------------------

    def auto_calibrate(self, n_steps: int = 200) -> Dict[str, Any]:
        """Run synthetic tile flow to auto-calibrate the kernel to Hebbian regime."""
        rng = np.random.RandomState(42)
        n = len(self._rooms)
        if n < 2:
            return {"error": "need at least 2 rooms"}

        # Zipf popularity
        popularity = rng.zipf(1.5, n).astype(np.float64)
        popularity /= popularity.sum()

        reports = []
        for step in range(n_steps):
            src_idx = rng.choice(n, p=popularity)
            dst_idx = rng.choice(n, p=popularity)

            # Burst injection
            if rng.random() < 0.1:
                dst_idx = rng.randint(n)

            confidence = 0.5 + 0.5 * rng.random()
            src_room = self._rooms[src_idx]
            dst_room = self._rooms[dst_idx]

            result = self.submit_tile(
                tile_type=rng.choice(["model", "data", "compression", "benchmark", "deploy"]),
                source_room=src_room,
                dest_room=dst_room,
                confidence=confidence,
            )
            reports.append(result)

        # Check calibration
        summary = self.kernel.summary()
        return {
            "calibration_steps": n_steps,
            "rooms": n,
            "compliance_rate": summary["compliance_rate"],
            "auto_calibrated": summary["auto_calibrated"],
            "warmup_target": summary["warmup_target"],
            "conservation": summary["conservation"],
        }

    # ------------------------------------------------------------------
    # API data endpoints
    # ------------------------------------------------------------------

    def get_clusters(self) -> List[Dict[str, Any]]:
        clusters = self.cluster_detector.detect(
            self._rooms, self.kernel.get_weights(), self.tracker
        )
        return [
            {
                "cluster_id": c.cluster_id,
                "rooms": c.rooms,
                "size": len(c.rooms),
                "dominant_tile_types": c.dominant_tile_types,
                "avg_internal_strength": c.avg_internal_strength,
                "avg_external_strength": c.avg_external_strength,
            }
            for c in clusters
        ]

    def get_weights(self) -> Dict[str, Any]:
        w = self.kernel.get_weights()
        rooms = self._rooms
        # Return sparse representation (top connections)
        flat = np.abs(w).ravel()
        top_n = min(50, len(flat))
        top_idx = np.argpartition(flat, -top_n)[-top_n:]
        top_idx = top_idx[np.argsort(flat[top_idx])[::-1]]

        connections = []
        for idx in top_idx:
            i, j = divmod(int(idx), len(rooms))
            val = float(w[i, j])
            if val > 0:
                connections.append({
                    "source": rooms[i] if i < len(rooms) else f"room-{i}",
                    "dest": rooms[j] if j < len(rooms) else f"room-{j}",
                    "weight": round(val, 6),
                })

        return {
            "n_rooms": len(rooms),
            "matrix_shape": list(w.shape),
            "top_connections": connections[:30],
            "weight_stats": {
                "min": round(float(w.min()), 6),
                "max": round(float(w.max()), 6),
                "mean": round(float(w.mean()), 6),
                "nonzero": int(np.count_nonzero(w)),
            },
        }

    def get_conservation(self) -> Dict[str, Any]:
        return self.kernel.summary()

    def get_flow(self, n: int = 100) -> List[Dict[str, Any]]:
        events = list(self._recent_flow)[-n:]
        return list(reversed(events))

    def get_status(self) -> Dict[str, Any]:
        return {
            "service": "fleet-hebbian",
            "status": "running" if self._running else "stopped",
            "port": self.port,
            "rooms": len(self._rooms),
            "flow_events": len(self._recent_flow),
            "tracker_records": len(self.tracker),
            "kernel_updates": self.kernel._update_count,
            "compliance_rate": self.kernel.compliance_rate(),
            "auto_calibrated": self.kernel._auto_calibrated,
            "stages": self.stage_classifier.export_stages(),
            "clusters": len(self.cluster_detector._last_clusters),
        }

    # ------------------------------------------------------------------
    # MythosTile-aware submission
    # ------------------------------------------------------------------

    def submit_mythos_tile(self, tile: 'MythosTile') -> Dict[str, Any]:
        """Submit a MythosTile through the Hebbian layer.

        Converts MythosTile to the internal flow format, routes it,
        and returns routing results with the tile_id attached.
        """
        dest_room = tile.meta.get('dest_room')
        result = self.submit_tile(
            tile_type=tile.content_type or 'model',
            source_room=tile.room or 'unknown',
            dest_room=dest_room,
            tile_hash=tile.tile_id,
            confidence=tile.confidence,
            tags=tile.tags,
        )
        result['mythos_tile_id'] = tile.tile_id
        result['mythos_domain'] = tile.domain
        return result

    def get_mythos_tile(self, tile_id: str) -> Optional[Dict[str, Any]]:
        """Look up flow events for a specific MythosTile ID."""
        for event in reversed(self._recent_flow):
            if event.get('tile_hash') == tile_id:
                return event
        return None

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self):
        path = os.path.join(self.persist_dir, "weights.npy")
        np.save(path, self.kernel.get_weights())

    # ------------------------------------------------------------------
    # HTTP Server
    # ------------------------------------------------------------------

    def start(self, block: bool = True):
        """Start the HTTP API server."""
        self._running = True
        service = self

        class Handler(BaseHTTPRequestHandler):
            def _json(self, data, code=200):
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(data, indent=2, default=str).encode())

            def _read_body(self):
                length = int(self.headers.get("Content-Length", 0))
                if length:
                    return json.loads(self.rfile.read(length))
                return {}

            def do_GET(self):
                if self.path == "/clusters":
                    self._json(service.get_clusters())
                elif self.path == "/weights":
                    self._json(service.get_weights())
                elif self.path == "/conservation":
                    self._json(service.get_conservation())
                elif self.path.startswith("/flow"):
                    n = 100
                    if "?" in self.path:
                        params = dict(p.split("=") for p in self.path.split("?")[1].split("&") if "=" in p)
                        n = min(int(params.get("n", "100")), 500)
                    self._json(service.get_flow(n))
                elif self.path == "/status":
                    self._json(service.get_status())
                elif self.path == "/stages":
                    self._json(service.stage_classifier.export_stages())
                elif self.path == "/rooms":
                    self._json({
                        "rooms": [
                            {"name": r, "domain": service._room_domains.get(r, r),
                             "index": i}
                            for i, r in enumerate(service._rooms)
                        ]
                    })
                elif self.path.startswith("/tile/"):
                    # GET /tile/<tile_id> — look up MythosTile flow event
                    tile_id = self.path.split("/tile/", 1)[1].split("?")[0]
                    event = service.get_mythos_tile(tile_id)
                    if event:
                        self._json(event)
                    else:
                        self._json({"error": f"tile not found: {tile_id}"}, 404)
                else:
                    self._json({"error": f"unknown endpoint: {self.path}"}, 404)

            def do_POST(self):
                if self.path == "/tile":
                    body = self._read_body()
                    required = ["tile_type", "source_room"]
                    for k in required:
                        if k not in body:
                            self._json({"error": f"missing field: {k}"}, 400)
                            return
                    result = service.submit_tile(
                        tile_type=body["tile_type"],
                        source_room=body["source_room"],
                        dest_room=body.get("dest_room"),
                        tile_hash=body.get("tile_hash"),
                        confidence=body.get("confidence", 0.9),
                        tags=body.get("tags"),
                    )
                    self._json(result, 201)
                elif self.path == "/tile/mythos":
                    # Accept MythosTile JSON body → MythosTile.from_json()
                    if not HAS_MYTHOS:
                        self._json({"error": "mythos_tile module not available"}, 500)
                        return
                    body = self._read_body()
                    try:
                        tile = MythosTile.from_json(json.dumps(body))
                    except Exception as e:
                        self._json({"error": f"invalid MythosTile: {e}"}, 400)
                        return
                    result = service.submit_mythos_tile(tile)
                    self._json(result, 201)
                elif self.path == "/calibrate":
                    body = self._read_body()
                    n_steps = body.get("n_steps", 200)
                    self._json(service.auto_calibrate(n_steps))
                elif self.path == "/save":
                    service.save()
                    self._json({"saved": True})
                else:
                    self._json({"error": f"unknown endpoint: {self.path}"}, 404)

            def log_message(self, format, *args):
                pass  # suppress request logging

        class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
            daemon_threads = True
            allow_reuse_address = True

        self._http_server = ThreadedHTTPServer(("0.0.0.0", self.port), Handler)
        print(f"⚒️  Fleet Hebbian Service on :{self.port}")
        print(f"   Rooms: {len(self._rooms)}  |  Kernel: {self.kernel.n}×{self.kernel.n}")
        print(f"   Endpoints: /status /clusters /weights /conservation /flow /rooms /stages")
        print(f"   POST: /tile /calibrate /save")

        if block:
            try:
                self._http_server.serve_forever()
            except KeyboardInterrupt:
                self.stop()
        else:
            t = threading.Thread(target=self._http_server.serve_forever, daemon=True)
            t.start()

    def stop(self):
        self._running = False
        if self._http_server:
            self._http_server.shutdown()
        self.save()
        print("⚒️  Fleet Hebbian Service stopped.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Fleet Hebbian Service")
    parser.add_argument("--port", type=int, default=8849)
    parser.add_argument("--db", type=str, default=None, help="Path to plato.db")
    parser.add_argument("--simulate", action="store_true",
                        help="Inject 500 synthetic tiles on startup")
    parser.add_argument("--calibrate", action="store_true",
                        help="Auto-calibrate kernel on startup")
    args = parser.parse_args()

    svc = FleetHebbianService(db_path=args.db, port=args.port)

    if args.calibrate or args.simulate:
        print("⚙️  Auto-calibrating kernel...")
        result = svc.auto_calibrate(500 if args.simulate else 200)
        print(f"   Compliance: {result['compliance_rate']}  "
              f"Calibrated: {result['auto_calibrated']}  "
              f"Target: {result['warmup_target']}")

    svc.start(block=True)


if __name__ == "__main__":
    main()
