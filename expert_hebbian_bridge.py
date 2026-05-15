#!/usr/bin/env python3
"""Expert-Hebbian Bridge — connects Oracle1's expert daemon system to the Hebbian service.

Maps 9 expert daemons to 9 Hebbian rooms, tracks cross-consultation coupling,
enforces conservation constraints, and exposes a dashboard on :8850.

Architecture:
    Expert Daemons (9) ─► ExpertRoomAdapter ─► Hebbian Network
           │                    │                     │
           ▼                    ▼                     ▼
    ExpertRoomAdapter    ExpertCouplingMatrix    ConservationHebbianKernel
           │                    │
           ▼                    ▼
    ExpertStageClassifier  ConservationConstrainedCrossConsult
           │
           ▼
    ExpertHebbianDashboard (:8850)
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

# MythosTile integration
try:
    from mythos_tile import MythosTile
    HAS_MYTHOS = True
except ImportError:
    HAS_MYTHOS = False

# Inline the conservation math from fleet_hebbian_service (no cross-import)
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
# Expert definitions — 9 Oracle1 expert daemons
# ---------------------------------------------------------------------------

EXPERT_TYPES = [
    "conservation",    # Physics / constraint theory
    "architect",       # System architecture, PLATO rooms
    "tripartite",      # Agent behavior, tripartite model
    "mathematician",   # Pure math, proofs, symbolic computation
    "synthesist",      # Cross-domain integration
    "critic",          # Review, verification, adversarial testing
    "builder",         # Implementation, code generation
    "navigator",       # Fleet routing, coordination
    "oracle",          # Deep reasoning, prediction
]

EXPERT_DOMAIN_MAP = {
    "conservation": "math",
    "architect": "plato",
    "tripartite": "agent",
    "mathematician": "math",
    "synthesist": "cross-domain",
    "critic": "review",
    "builder": "code",
    "navigator": "fleet",
    "oracle": "reasoning",
}

# Expert cross-consultation topology — who tends to consult whom
EXPERT_AFFINITY = {
    "conservation": ["mathematician", "oracle", "critic"],
    "architect": ["builder", "navigator", "synthesist"],
    "tripartite": ["critic", "synthesist", "oracle"],
    "mathematician": ["conservation", "oracle", "critic"],
    "synthesist": ["architect", "tripartite", "navigator"],
    "critic": ["conservation", "mathematician", "tripartite"],
    "builder": ["architect", "mathematician", "navigator"],
    "navigator": ["architect", "synthesist", "oracle"],
    "oracle": ["conservation", "mathematician", "tripartite"],
}


# ---------------------------------------------------------------------------
# 1. ExpertRoomAdapter — Convert expert daemon tiles to PLATO room format
# ---------------------------------------------------------------------------

class ExpertRoomAdapter:
    """Converts expert daemon output to PLATO room tiles.

    Maps each of the 9 expert types to a Hebbian room domain, converts
    expert output to tile content, and assigns activation keys based on
    expert confidence.
    """

    def __init__(self, n_experts: int = 9):
        self.n_experts = n_experts
        self.expert_names = EXPERT_TYPES[:n_experts]
        self._room_map: Dict[str, str] = {}
        self._tile_counts: Dict[str, int] = defaultdict(int)
        self._lock = threading.RLock()

        for name in self.expert_names:
            self._room_map[name] = f"expert-{name}"
            self._tile_counts[name] = 0

    def expert_to_room(self, expert_type: str) -> str:
        """Map expert type to PLATO room name."""
        if expert_type not in self._room_map:
            raise ValueError(f"Unknown expert type: {expert_type}")
        return self._room_map[expert_type]

    def room_to_expert(self, room_name: str) -> str:
        """Reverse map room name to expert type."""
        prefix = "expert-"
        if room_name.startswith(prefix):
            expert = room_name[len(prefix):]
            if expert in self.expert_names:
                return expert
        raise ValueError(f"No expert for room: {room_name}")

    def expert_to_domain(self, expert_type: str) -> str:
        """Map expert type to domain category."""
        return EXPERT_DOMAIN_MAP.get(expert_type, "unknown")

    def all_rooms(self) -> List[str]:
        """Return list of all expert room names."""
        return [self._room_map[name] for name in self.expert_names]

    def room_index(self) -> Dict[str, int]:
        """Return {room_name: index} mapping."""
        return {room: i for i, room in enumerate(self.all_rooms())}

    def expert_index(self) -> Dict[str, int]:
        """Return {expert_type: index} mapping."""
        return {name: i for i, name in enumerate(self.expert_names)}

    def convert_tile(self, expert_type: str, output: str,
                     confidence: float = 0.9,
                     tile_type: str = "model") -> Dict[str, Any]:
        """Convert expert output to a PLATO tile.

        Parameters
        ----------
        expert_type:
            Which expert produced this output.
        output:
            The expert's text/structured output.
        confidence:
            Expert confidence in its output (0-1).
        tile_type:
            PLATO tile type category.

        Returns
        -------
        dict with room, domain, tile content, activation keys.
        """
        if expert_type not in self._room_map:
            raise ValueError(f"Unknown expert type: {expert_type}")

        room = self.expert_to_room(expert_type)
        domain = self.expert_to_domain(expert_type)
        tile_hash = hashlib.sha256(
            f"{expert_type}:{output[:64]}:{time.time()}".encode()
        ).hexdigest()[:16]

        # Activation keys — indicate which layers are active
        activation_keys = self._compute_activation_keys(expert_type, confidence)

        with self._lock:
            self._tile_counts[expert_type] += 1

        return {
            "room": room,
            "domain": domain,
            "expert_type": expert_type,
            "tile_type": tile_type,
            "tile_hash": tile_hash,
            "confidence": confidence,
            "content": output,
            "activation_keys": activation_keys,
            "tile_count": self._tile_counts[expert_type],
        }

    def convert_to_mythos_tile(self, expert_type: str, output: str,
                                confidence: float = 0.9,
                                tile_type: str = "model") -> 'MythosTile':
        """Convert expert output directly to a MythosTile.

        Uses MythosTile.from_expert_output() for proper protocol conformance.
        Falls back to convert_tile() dict if MythosTile is not available.
        """
        if not HAS_MYTHOS:
            # Return a dict wrapper that mimics MythosTile interface
            return self.convert_tile(expert_type, output, confidence, tile_type)

        expert_output = {
            "domain": self.expert_to_domain(expert_type),
            "output": output,
            "confidence": confidence,
            "tags": [expert_type, tile_type],
            "meta": {
                "tile_type": tile_type,
                "activation_keys": self._compute_activation_keys(expert_type, confidence),
            },
        }
        return MythosTile.from_expert_output(expert_type, expert_output)

    def _compute_activation_keys(self, expert_type: str,
                                  confidence: float) -> List[str]:
        """Determine which activation layers are active for this expert."""
        keys = ["base"]
        if confidence >= 0.5:
            keys.append("filtered")
        if confidence >= 0.7:
            keys.append("dual-filtered")
        if confidence >= 0.85:
            keys.append("self-review")
        if confidence >= 0.95:
            keys.append("conservation-aware")
        return keys

    def get_tile_counts(self) -> Dict[str, int]:
        """Return tile counts per expert."""
        with self._lock:
            return dict(self._tile_counts)

    def summary(self) -> Dict[str, Any]:
        return {
            "n_experts": self.n_experts,
            "expert_names": self.expert_names,
            "rooms": self.all_rooms(),
            "domains": {name: self.expert_to_domain(name) for name in self.expert_names},
            "tile_counts": self.get_tile_counts(),
        }


# ---------------------------------------------------------------------------
# 2. ExpertCouplingMatrix — Track expert cross-consultation topology
# ---------------------------------------------------------------------------

class ExpertCouplingMatrix:
    """Tracks which experts cross-consult with which others.

    Maintains a Hebbian weight matrix over expert pairs. Cross-consultation
    events strengthen connections; lack of consultation lets them decay.
    Conservation law: γ+H stays within bounds.
    """

    def __init__(self, n_experts: int = 9, learning_rate: float = 0.01,
                 decay: float = 0.001):
        self.n = n_experts
        self.expert_names = EXPERT_TYPES[:n_experts]
        self._expert_idx = {name: i for i, name in enumerate(self.expert_names)}
        self.lr = learning_rate
        self.decay = decay
        self._weights = np.zeros((n_experts, n_experts), dtype=np.float32)
        self._consultation_log: deque = deque(maxlen=1000)
        self._lock = threading.Lock()

    def record_consultation(self, source_expert: str, target_expert: str,
                            strength: float = 1.0,
                            context: Optional[str] = None) -> Dict[str, Any]:
        """Record that source_expert consulted target_expert.

        Updates the Hebbian coupling weight and returns the new state.
        """
        src_idx = self._expert_idx.get(source_expert)
        tgt_idx = self._expert_idx.get(target_expert)
        if src_idx is None or tgt_idx is None:
            raise ValueError(f"Unknown expert(s): {source_expert}, {target_expert}")

        with self._lock:
            # Hebbian update: strengthen the connection
            old_weight = float(self._weights[src_idx, tgt_idx])
            self._weights[src_idx, tgt_idx] = (
                old_weight + self.lr * strength - self.decay * old_weight
            )
            np.clip(self._weights[src_idx, tgt_idx], 0, None,
                    out=self._weights[src_idx, tgt_idx:tgt_idx+1])

            event = {
                "timestamp": time.time(),
                "source": source_expert,
                "target": target_expert,
                "strength": strength,
                "old_weight": round(old_weight, 6),
                "new_weight": round(float(self._weights[src_idx, tgt_idx]), 6),
                "context": context,
            }
            self._consultation_log.append(event)

        return event

    def record_self_review(self, expert: str, quality: float = 0.5) -> Dict[str, Any]:
        """Record a self-review event (diagonal weight update)."""
        return self.record_consultation(expert, expert, strength=quality * 0.5,
                                        context="self-review")

    def get_coupling_strength(self, source: str, target: str) -> float:
        """Get current coupling strength between two experts."""
        src_idx = self._expert_idx.get(source)
        tgt_idx = self._expert_idx.get(target)
        if src_idx is None or tgt_idx is None:
            return 0.0
        with self._lock:
            return float(self._weights[src_idx, tgt_idx])

    def get_matrix(self) -> np.ndarray:
        """Return a copy of the coupling matrix."""
        with self._lock:
            return self._weights.copy()

    def get_top_couplings(self, n: int = 10) -> List[Dict[str, Any]]:
        """Return top-n strongest expert couplings."""
        with self._lock:
            w = self._weights.copy()
        flat = np.abs(w).ravel()
        top_n = min(n, len(flat))
        top_idx = np.argpartition(flat, -top_n)[-top_n:]
        top_idx = top_idx[np.argsort(flat[top_idx])[::-1]]

        results = []
        for idx in top_idx:
            i, j = divmod(int(idx), self.n)
            val = float(w[i, j])
            if val > 0:
                results.append({
                    "source": self.expert_names[i],
                    "target": self.expert_names[j],
                    "weight": round(val, 6),
                    "domain_pair": (
                        EXPERT_DOMAIN_MAP.get(self.expert_names[i], "?"),
                        EXPERT_DOMAIN_MAP.get(self.expert_names[j], "?"),
                    ),
                })
        return results

    def check_conservation(self) -> Dict[str, Any]:
        """Check conservation law compliance: γ+H within bounds."""
        with self._lock:
            w = self._weights.copy()

        if np.sum(w) < 1e-10:
            return {
                "gamma": 0.0, "H": 0.0, "gamma_plus_H": 0.0,
                "predicted": predicted_gamma_plus_H(self.n),
                "conserved": True, "deviation": 0.0,
            }

        try:
            gamma = algebraic_normalized(w)
            H = coupling_entropy(w)
            actual = gamma + H
            predicted = predicted_gamma_plus_H(self.n)
            sigma = _interpolate_sigma(self.n)
            deviation = actual - predicted
            conserved = abs(deviation) <= 2.0 * sigma
        except (np.linalg.LinAlgError, ValueError):
            gamma, H, actual = 0.0, 0.0, 0.0
            predicted = predicted_gamma_plus_H(self.n)
            deviation = 0.0
            conserved = True

        return {
            "gamma": round(gamma, 4),
            "H": round(H, 4),
            "gamma_plus_H": round(actual, 4),
            "predicted": round(predicted, 4),
            "deviation": round(deviation, 4),
            "conserved": conserved,
        }

    def project_to_conservation(self) -> float:
        """Project weights back into conservation bounds if they've drifted.

        Returns the scale factor applied (1.0 = no change needed).
        """
        report = self.check_conservation()
        if report["conserved"]:
            return 1.0

        with self._lock:
            # If γ+H is too high: scale down weak connections
            if report["deviation"] > 0:
                threshold = np.percentile(
                    self._weights[self._weights > 0], 50
                ) if np.any(self._weights > 0) else 0
                mask = self._weights < threshold
                self._weights[mask] *= 0.5
                return float(np.mean(mask)) if np.any(mask) else 1.0
            else:
                # γ+H is too low: boost top connections
                flat = self._weights.ravel()
                top_k = max(1, int(0.1 * len(flat)))
                top_idx = np.argpartition(flat, -top_k)[-top_k:]
                flat[top_idx] *= 1.05
                return 1.05

    def recent_consultations(self, n: int = 50) -> List[Dict[str, Any]]:
        """Return the n most recent cross-consultation events."""
        with self._lock:
            return list(self._consultation_log)[-n:]

    def summary(self) -> Dict[str, Any]:
        return {
            "n_experts": self.n,
            "learning_rate": self.lr,
            "decay": self.decay,
            "total_consultations": len(self._consultation_log),
            "conservation": self.check_conservation(),
            "top_couplings": self.get_top_couplings(5),
            "weight_stats": {
                "min": round(float(self._weights.min()), 6),
                "max": round(float(self._weights.max()), 6),
                "mean": round(float(self._weights.mean()), 6),
                "nonzero": int(np.count_nonzero(self._weights)),
            },
        }


# ---------------------------------------------------------------------------
# 3. ConservationConstrainedCrossConsult
# ---------------------------------------------------------------------------

class ConservationConstrainedCrossConsult:
    """Manages expert cross-consultation with conservation constraints.

    When expert A wants to consult expert B:
    - If coupling strength > threshold: allow direct consultation
    - If coupling strength < threshold: route through Hebbian router
    - After consultation: update Hebbian weights
    - Conservation check: if γ+H drifts, project back
    """

    def __init__(self, coupling_matrix: ExpertCouplingMatrix,
                 adapter: ExpertRoomAdapter,
                 direct_threshold: float = 0.1,
                 router_threshold: float = 0.01):
        self.coupling = coupling_matrix
        self.adapter = adapter
        self.direct_threshold = direct_threshold
        self.router_threshold = router_threshold
        self._pending: deque = deque(maxlen=200)
        self._completed: deque = deque(maxlen=500)
        self._lock = threading.Lock()

    def request_consultation(self, source_expert: str, target_expert: str,
                             query: str = "",
                             confidence: float = 0.9) -> Dict[str, Any]:
        """Request a cross-consultation between experts.

        Routes based on coupling strength and conservation compliance.
        If MythosTile is available, produces a MythosTile in the result.
        """
        strength = self.coupling.get_coupling_strength(source_expert, target_expert)

        # Determine routing mode
        if strength >= self.direct_threshold:
            mode = "direct"
        elif strength >= self.router_threshold:
            mode = "routed"
        else:
            # Check affinity topology — maybe they SHOULD be connected
            affinity = EXPERT_AFFINITY.get(source_expert, [])
            if target_expert in affinity:
                mode = "routed"  # Allow through router even if coupling is weak
            else:
                mode = "blocked"

        # Conservation pre-check
        conservation = self.coupling.check_conservation()

        request = {
            "timestamp": time.time(),
            "source": source_expert,
            "target": target_expert,
            "query": query,
            "confidence": confidence,
            "mode": mode,
            "coupling_strength": round(strength, 6),
            "conservation_ok": conservation["conserved"],
        }

        with self._lock:
            self._pending.append(request)

        if mode == "blocked":
            request["status"] = "blocked"
            request["reason"] = "insufficient coupling and no affinity"
            return request

        # Record the consultation
        consultation_strength = confidence if mode == "direct" else confidence * 0.5
        event = self.coupling.record_consultation(
            source_expert, target_expert,
            strength=consultation_strength,
            context=query[:100] if query else None,
        )
        request["consultation_event"] = event

        # Post-consultation conservation check
        post_conservation = self.coupling.check_conservation()
        if not post_conservation["conserved"]:
            scale = self.coupling.project_to_conservation()
            request["conservation_correction"] = {
                "applied": True,
                "scale_factor": round(scale, 4),
                "pre_deviation": conservation["deviation"],
                "post_deviation": post_conservation["deviation"],
            }

        request["status"] = "completed"
        request["post_conservation"] = post_conservation

        # Attach MythosTile if available
        if HAS_MYTHOS:
            mythos = MythosTile.from_expert_output(source_expert, {
                "domain": self.adapter.expert_to_domain(source_expert),
                "output": query or f"consultation to {target_expert}",
                "confidence": confidence,
                "tags": ["cross-consultation", source_expert, target_expert],
                "meta": {"mode": mode, "target_expert": target_expert},
            })
            request["mythos_tile"] = json.loads(mythos.to_json())
            request["mythos_tile_id"] = mythos.tile_id

        with self._lock:
            self._completed.append(request)

        return request

    def batch_consult(self, source_expert: str, target_experts: List[str],
                      query: str = "", confidence: float = 0.9) -> List[Dict[str, Any]]:
        """Request consultations from one expert to multiple targets."""
        results = []
        for target in target_experts:
            results.append(self.request_consultation(
                source_expert, target, query, confidence
            ))
        return results

    def get_pending(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._pending)

    def get_completed(self, n: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._completed)[-n:]

    def summary(self) -> Dict[str, Any]:
        return {
            "direct_threshold": self.direct_threshold,
            "router_threshold": self.router_threshold,
            "pending_count": len(self._pending),
            "completed_count": len(self._completed),
            "conservation": self.coupling.check_conservation(),
        }


# ---------------------------------------------------------------------------
# 4. ExpertStageClassifier — Classify each expert's development stage
# ---------------------------------------------------------------------------

class ExpertStageClassifier:
    """Classify each expert daemon's development stage.

    Stage 0: Empty room, no tiles produced
    Stage 1: Few tiles, echoing input (low confidence)
    Stage 2: Growing tiles, some filtering active
    Stage 3: Many tiles, dual filtering active, vocabulary-gated
    Stage 4: Self-review active, cross-consulting, conservation-aware
    """

    def __init__(self, adapter: ExpertRoomAdapter):
        self.adapter = adapter
        self._observations: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

        # Initialize observation records for each expert
        for name in adapter.expert_names:
            self._observations[name] = {
                "tiles_produced": 0,
                "tiles_received": 0,
                "total_confidence": 0.0,
                "echo_count": 0,
                "filter_count": 0,
                "dual_filter_count": 0,
                "self_reviews": 0,
                "cross_consultations": 0,
                "conservation_corrections": 0,
            }

    def observe_production(self, expert_type: str, confidence: float,
                           is_echo: bool = False,
                           activation_keys: Optional[List[str]] = None) -> None:
        """Record that an expert produced a tile."""
        with self._lock:
            if expert_type not in self._observations:
                return
            obs = self._observations[expert_type]
            obs["tiles_produced"] += 1
            obs["total_confidence"] += confidence
            if is_echo:
                obs["echo_count"] += 1
            if activation_keys:
                if "filtered" in activation_keys:
                    obs["filter_count"] += 1
                if "dual-filtered" in activation_keys:
                    obs["dual_filter_count"] += 1
                if "self-review" in activation_keys:
                    obs["self_reviews"] += 1
                if "conservation-aware" in activation_keys:
                    obs["conservation_corrections"] += 1

    def observe_reception(self, expert_type: str) -> None:
        """Record that an expert received a tile for processing."""
        with self._lock:
            if expert_type in self._observations:
                self._observations[expert_type]["tiles_received"] += 1

    def observe_cross_consultation(self, expert_type: str) -> None:
        """Record that an expert participated in cross-consultation."""
        with self._lock:
            if expert_type in self._observations:
                self._observations[expert_type]["cross_consultations"] += 1

    def classify(self, expert_type: str) -> int:
        """Classify the current stage of an expert (0-4)."""
        with self._lock:
            obs = self._observations.get(expert_type)
            if obs is None:
                return 0

        tiles = obs["tiles_produced"]
        if tiles == 0:
            return 0  # Empty room

        avg_confidence = obs["total_confidence"] / tiles if tiles > 0 else 0
        echo_rate = obs["echo_count"] / tiles if tiles > 0 else 0
        filter_rate = obs["filter_count"] / tiles if tiles > 0 else 0
        dual_filter_rate = obs["dual_filter_count"] / tiles if tiles > 0 else 0
        self_review_rate = obs["self_reviews"] / tiles if tiles > 0 else 0
        cross_consult_rate = obs["cross_consultations"] / tiles if tiles > 0 else 0

        # Stage 4: Self-review active, cross-consulting, conservation-aware
        if (self_review_rate > 0.3 and cross_consult_rate > 0.1
                and obs["conservation_corrections"] > 0):
            return 4

        # Stage 3: Many tiles, dual filtering active, vocabulary-gated
        if tiles >= 10 and dual_filter_rate > 0.3 and avg_confidence > 0.6:
            return 3

        # Stage 2: Growing tiles, some filtering
        if tiles >= 3 and filter_rate > 0.2 and avg_confidence > 0.3:
            return 2

        # Stage 1: Few tiles, echoing input
        if tiles >= 1:
            return 1

        return 0

    def classify_all(self) -> Dict[str, int]:
        """Classify all experts."""
        return {name: self.classify(name) for name in self.adapter.expert_names}

    def get_details(self, expert_type: str) -> Dict[str, Any]:
        """Get detailed stage info for an expert."""
        with self._lock:
            obs = self._observations.get(expert_type, {})
        return {
            "expert": expert_type,
            "stage": self.classify(expert_type),
            "observations": dict(obs),
            "domain": self.adapter.expert_to_domain(expert_type),
            "room": self.adapter.expert_to_room(expert_type),
        }

    def summary(self) -> Dict[str, Any]:
        stages = self.classify_all()
        return {
            "stages": stages,
            "stage_distribution": {
                str(s): sum(1 for v in stages.values() if v == s)
                for s in range(5)
            },
            "avg_stage": round(sum(stages.values()) / len(stages), 2) if stages else 0,
            "details": {name: self.get_details(name) for name in self.adapter.expert_names},
        }


# ---------------------------------------------------------------------------
# 5. ExpertHebbianDashboard — HTTP API on :8850
# ---------------------------------------------------------------------------

class ExpertHebbianDashboard:
    """HTTP dashboard for the Expert-Hebbian bridge on :8850.

    Endpoints:
        GET  /experts       — list all experts with stages and tile counts
        GET  /coupling      — expert coupling matrix
        GET  /flow          — recent cross-consultation events
        GET  /conservation  — conservation compliance per expert pair
        POST /consult       — trigger expert cross-consultation
    """

    def __init__(self, adapter: ExpertRoomAdapter,
                 coupling: ExpertCouplingMatrix,
                 cross_consult: ConservationConstrainedCrossConsult,
                 stage_classifier: ExpertStageClassifier,
                 port: int = 8850):
        self.adapter = adapter
        self.coupling = coupling
        self.cross_consult = cross_consult
        self.stage_classifier = stage_classifier
        self.port = port
        self._running = False
        self._http_server: Optional[HTTPServer] = None

    def start(self, block: bool = True):
        """Start the HTTP API server."""
        self._running = True
        dashboard = self

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
                if self.path == "/experts":
                    stages = dashboard.stage_classifier.classify_all()
                    tile_counts = dashboard.adapter.get_tile_counts()
                    experts = []
                    for name in dashboard.adapter.expert_names:
                        experts.append({
                            "name": name,
                            "domain": dashboard.adapter.expert_to_domain(name),
                            "room": dashboard.adapter.expert_to_room(name),
                            "stage": stages.get(name, 0),
                            "tiles_produced": tile_counts.get(name, 0),
                        })
                    self._json({"experts": experts, "total": len(experts)})

                elif self.path == "/coupling":
                    matrix = dashboard.coupling.get_matrix()
                    names = dashboard.adapter.expert_names
                    # Human-readable matrix
                    readable = []
                    for i, src in enumerate(names):
                        for j, tgt in enumerate(names):
                            val = float(matrix[i, j])
                            if val > 0:
                                readable.append({
                                    "source": src,
                                    "target": tgt,
                                    "weight": round(val, 6),
                                })
                    self._json({
                        "matrix_shape": list(matrix.shape),
                        "connections": readable,
                        "top_couplings": dashboard.coupling.get_top_couplings(10),
                        "conservation": dashboard.coupling.check_conservation(),
                    })

                elif self.path.startswith("/flow"):
                    n = 100
                    if "?" in self.path:
                        params = dict(
                            p.split("=") for p in self.path.split("?")[1].split("&")
                            if "=" in p
                        )
                        n = min(int(params.get("n", "100")), 500)
                    events = dashboard.coupling.recent_consultations(n)
                    completed = dashboard.cross_consult.get_completed(n)
                    self._json({
                        "consultation_events": events,
                        "completed_consultations": completed,
                        "pending": dashboard.cross_consult.get_pending(),
                    })

                elif self.path == "/conservation":
                    conservation = dashboard.coupling.check_conservation()
                    # Per-expert-pair analysis
                    matrix = dashboard.coupling.get_matrix()
                    names = dashboard.adapter.expert_names
                    pair_analysis = []
                    for i, src in enumerate(names):
                        for j, tgt in enumerate(names):
                            if i < j:
                                w = float(max(matrix[i, j], matrix[j, i]))
                                if w > 0:
                                    pair_analysis.append({
                                        "pair": f"{src} ↔ {tgt}",
                                        "weight": round(w, 6),
                                        "domains": (
                                            EXPERT_DOMAIN_MAP.get(src, "?"),
                                            EXPERT_DOMAIN_MAP.get(tgt, "?"),
                                        ),
                                    })
                    self._json({
                        "global_conservation": conservation,
                        "pair_analysis": pair_analysis,
                        "projection_needed": not conservation["conserved"],
                    })

                elif self.path == "/status":
                    self._json({
                        "service": "expert-hebbian-bridge",
                        "status": "running" if dashboard._running else "stopped",
                        "port": dashboard.port,
                        "adapter": dashboard.adapter.summary(),
                        "coupling": dashboard.coupling.summary(),
                        "stages": dashboard.stage_classifier.summary(),
                        "cross_consult": dashboard.cross_consult.summary(),
                    })

                else:
                    self._json({"error": f"unknown endpoint: {self.path}"}, 404)

            def do_POST(self):
                if self.path == "/consult":
                    body = self._read_body()
                    required = ["source", "target"]
                    for k in required:
                        if k not in body:
                            self._json({"error": f"missing field: {k}"}, 400)
                            return
                    result = dashboard.cross_consult.request_consultation(
                        source_expert=body["source"],
                        target_expert=body["target"],
                        query=body.get("query", ""),
                        confidence=body.get("confidence", 0.9),
                    )
                    self._json(result, 201)

                elif self.path == "/consult/mythos":
                    # Consultation that returns MythosTile via adapter
                    body = self._read_body()
                    required = ["source", "target"]
                    for k in required:
                        if k not in body:
                            self._json({"error": f"missing field: {k}"}, 400)
                            return
                    result = dashboard.cross_consult.request_consultation(
                        source_expert=body["source"],
                        target_expert=body["target"],
                        query=body.get("query", ""),
                        confidence=body.get("confidence", 0.9),
                    )
                    # Also produce a MythosTile via the adapter
                    if HAS_MYTHOS:
                        source = body["source"]
                        query_text = body.get("query", "")
                        conf = body.get("confidence", 0.9)
                        tile = dashboard.adapter.convert_to_mythos_tile(
                            source, query_text, conf
                        )
                        if isinstance(tile, MythosTile):
                            result["mythos_tile_via_adapter"] = json.loads(tile.to_json())
                    self._json(result, 201)

                elif self.path == "/batch-consult":
                    body = self._read_body()
                    if "source" not in body or "targets" not in body:
                        self._json({"error": "missing source or targets"}, 400)
                        return
                    results = dashboard.cross_consult.batch_consult(
                        source_expert=body["source"],
                        target_experts=body["targets"],
                        query=body.get("query", ""),
                        confidence=body.get("confidence", 0.9),
                    )
                    self._json({"results": results}, 201)

                else:
                    self._json({"error": f"unknown endpoint: {self.path}"}, 404)

            def log_message(self, format, *args):
                pass  # suppress request logging

        class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
            daemon_threads = True
            allow_reuse_address = True

        self._http_server = ThreadedHTTPServer(("0.0.0.0", self.port), Handler)
        print(f"⚒️  Expert-Hebbian Bridge Dashboard on :{self.port}")
        print(f"   Experts: {len(self.adapter.expert_names)}")
        print(f"   Endpoints: /experts /coupling /flow /conservation /status")
        print(f"   POST: /consult /batch-consult")

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
        print("⚒️  Expert-Hebbian Bridge Dashboard stopped.")


# ---------------------------------------------------------------------------
# Bridge Orchestrator — wires everything together
# ---------------------------------------------------------------------------

class ExpertHebbianBridge:
    """Orchestrates the full Expert-Hebbian bridge system.

    Creates all components and wires them together.
    """

    def __init__(self, n_experts: int = 9, dashboard_port: int = 8850):
        self.adapter = ExpertRoomAdapter(n_experts=n_experts)
        self.coupling = ExpertCouplingMatrix(n_experts=n_experts)
        self.cross_consult = ConservationConstrainedCrossConsult(
            coupling_matrix=self.coupling,
            adapter=self.adapter,
        )
        self.stage_classifier = ExpertStageClassifier(adapter=self.adapter)
        self.dashboard = ExpertHebbianDashboard(
            adapter=self.adapter,
            coupling=self.coupling,
            cross_consult=self.cross_consult,
            stage_classifier=self.stage_classifier,
            port=dashboard_port,
        )

    def start(self, block: bool = True):
        """Start the dashboard."""
        self.dashboard.start(block=block)

    def stop(self):
        """Stop the dashboard."""
        self.dashboard.stop()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Expert-Hebbian Bridge Dashboard")
    parser.add_argument("--port", type=int, default=8850)
    parser.add_argument("--experts", type=int, default=9)
    args = parser.parse_args()

    bridge = ExpertHebbianBridge(n_experts=args.experts, dashboard_port=args.port)
    bridge.start(block=True)


if __name__ == "__main__":
    main()
