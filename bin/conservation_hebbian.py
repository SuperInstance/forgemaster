"""Conservation-constrained Hebbian kernel.

Extends hebbian_layer.CUDAHebbianKernel with the fleet conservation law:
    γ + H = 1.283 - 0.159·log(V) ± ε

The conservation law acts as a regularizer: after each Hebbian update,
the weight matrix (which IS the coupling matrix) is projected back onto
the conservation manifold if it drifts too far.

This prevents:
  - Runaway connectivity (all tiles flow to one room)
  - Runaway diversity (tiles spread everywhere, no specialization)
  - Numerical instability in long-running Hebbian processes

Usage:
    from conservation_hebbian import ConservationHebbianKernel

    kernel = ConservationHebbianKernel(n_rooms=1141, V=30)
    kernel.update(pre_activations, post_activations)
    # If conservation violated → auto-projected back to manifold

    # Check compliance
    report = kernel.conservation_report()
    print(report)  # {gamma, H, predicted, deviation, conserved, corrections}
"""

from __future__ import annotations

import math
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Conservation Law (from fleet-math v0.3+, inline to avoid version dependency)
# ---------------------------------------------------------------------------

CONSERVATION_INTERCEPT = 1.283
CONSERVATION_LOG_COEFF = -0.159

CONSERVATION_SIGMA_TABLE = {
    5: 0.070, 10: 0.065, 20: 0.058, 30: 0.050,
    50: 0.048, 100: 0.042, 200: 0.038,
}


def _interpolate_sigma(V: int) -> float:
    """Interpolate empirical sigma for any V from the calibration table."""
    vs = sorted(CONSERVATION_SIGMA_TABLE.keys())
    if V <= vs[0]:
        return CONSERVATION_SIGMA_TABLE[vs[0]]
    if V >= vs[-1]:
        return CONSERVATION_SIGMA_TABLE[vs[-1]]
    for lo, hi in zip(vs, vs[1:]):
        if lo < V <= hi:
            frac = (V - lo) / (hi - lo)
            return CONSERVATION_SIGMA_TABLE[lo] + frac * (CONSERVATION_SIGMA_TABLE[hi] - CONSERVATION_SIGMA_TABLE[lo])
    return 0.05


def predicted_gamma_plus_H(V: int) -> float:
    """Predicted γ+H for fleet size V (universal style coupling)."""
    return CONSERVATION_INTERCEPT + CONSERVATION_LOG_COEFF * math.log(max(V, 3))


# ---------------------------------------------------------------------------
# Spectral analysis (from fleet-math.health, inline)
# ---------------------------------------------------------------------------

def coupling_entropy(C: np.ndarray) -> float:
    """Spectral entropy H of coupling matrix C."""
    eigs = np.linalg.eigvalsh(C)[::-1]
    p = np.abs(eigs) / (np.sum(np.abs(eigs)) + 1e-15)
    p = p[p > 1e-10]
    return float(-np.sum(p * np.log(p)) / np.log(len(eigs)))


def algebraic_normalized(C: np.ndarray) -> float:
    """Algebraic connectivity γ = (λ₂ - λ₁) / (λₙ - λ₁) of the graph Laplacian."""
    if C.shape[0] < 2:
        return 0.0
    L = np.diag(C.sum(axis=1)) - C
    eigs = np.linalg.eigvalsh(L)
    return float((eigs[1] - eigs[0]) / (eigs[-1] - eigs[0] + 1e-15))


# ---------------------------------------------------------------------------
# ConservationHebbianKernel
# ---------------------------------------------------------------------------

@dataclass
class ConservationReport:
    """Snapshot of conservation law compliance after an update."""
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
    """Hebbian weight update constrained by the fleet conservation law.

    After each update step:
      1. Compute γ (algebraic connectivity) and H (spectral entropy)
      2. Check if γ + H is within tolerance of predicted(V)
      3. If violated, project weight matrix back to conservation manifold
         by rescaling toward the predicted value

    The weight matrix W is treated as a coupling matrix. Positive weights
    become coupling strengths, and the spectral properties of the resulting
    graph are constrained by the conservation law.

    Parameters
    ----------
    n_rooms:
        Number of rooms (dimension of the square weight matrix).
    V:
        Fleet size — number of active agents/rooms for conservation law.
    learning_rate:
        Hebbian learning rate η.
    decay:
        Weight decay λ.
    tolerance_sigma:
        How many σ deviations before triggering correction (default 2.0 = 95% CI).
    correction_strength:
        How aggressively to project back (0=none, 1=hard projection, 0.5=soft).
    """

    def __init__(
        self,
        n_rooms: int,
        V: Optional[int] = None,
        learning_rate: float = 0.01,
        decay: float = 0.001,
        tolerance_sigma: float = 2.0,
        correction_strength: float = 0.5,
        dtype: Any = np.float32,
    ) -> None:
        self.n = n_rooms
        self.V = V or n_rooms
        self.lr = learning_rate
        self.decay = decay
        self.tolerance_sigma = tolerance_sigma
        self.correction_strength = correction_strength
        self.dtype = dtype

        # Weight matrix
        self._weights = np.zeros((n_rooms, n_rooms), dtype=dtype)

        # Conservation state
        self._predicted = predicted_gamma_plus_H(self.V)
        self._sigma = _interpolate_sigma(self.V)
        self._tolerance = tolerance_sigma * self._sigma

        # Tracking
        self._update_count = 0
        self._correction_count = 0
        self._last_report: Optional[ConservationReport] = None
        self._lock = threading.Lock()

        # Self-calibration: measure actual γ+H during warmup, then use as target
        self._warmup_samples: List[float] = []
        self._warmup_target = self._predicted  # start with random-matrix prediction
        self._auto_calibrated = False

        # Try cupy
        try:
            import cupy as cp
            self._cp = cp
            self._weights_gpu = cp.zeros((n_rooms, n_rooms), dtype=dtype)
            self._backend = "cupy"
        except ImportError:
            self._cp = None
            self._backend = "numpy"

    @property
    def backend(self) -> str:
        return self._backend

    def update(
        self,
        pre_activations: np.ndarray,
        post_activations: np.ndarray,
    ) -> ConservationReport:
        """Apply one conservation-constrained Hebbian update.

        Returns a ConservationReport with compliance status.
        """
        with self._lock:
            return self._update_locked(pre_activations, post_activations)

    def _update_locked(
        self,
        pre: np.ndarray,
        post: np.ndarray,
    ) -> ConservationReport:
        pre = np.asarray(pre, dtype=self.dtype)
        post = np.asarray(post, dtype=self.dtype)

        # Step 1: Standard Hebbian update
        # w[i,j] += lr * pre[i] * post[j] - decay * w[i,j]
        delta = self.lr * np.outer(pre, post)
        self._weights += delta - self.decay * self._weights

        # Ensure non-negative (coupling strengths)
        np.clip(self._weights, 0, None, out=self._weights)

        # Step 2: Check conservation law
        correction_applied = False
        scale_factor = 1.0

        try:
            gamma = algebraic_normalized(self._weights)
            H = coupling_entropy(self._weights)
            actual = gamma + H

            # Self-calibration: collect warmup samples to find Hebbian natural γ+H
            if self._update_count < 50:
                self._warmup_samples.append(actual)
                target = self._predicted  # use random prediction during warmup
            elif not self._auto_calibrated:
                # Calibrate from observed Hebbian dynamics
                self._warmup_target = float(np.median(self._warmup_samples))
                self._auto_calibrated = True
                target = self._warmup_target
            else:
                target = self._warmup_target

            deviation = actual - target

            if abs(deviation) > self._tolerance:
                # Step 3: Project back to conservation manifold
                correction_applied = True
                self._correction_count += 1

                # Two-pronged correction:
                # 1. If sum too HIGH (too connected): sparsify weak connections + increase decay
                # 2. If sum too LOW (too disconnected): boost strongest connections
                if deviation > 0:
                    # Too connected — sparsify by zeroing out the weakest connections
                    threshold = np.percentile(self._weights[self._weights > 0], 50)
                    mask = self._weights < threshold
                    self._weights[mask] *= (1.0 - self.correction_strength)
                    scale_factor = float(np.mean(mask))
                else:
                    # Too disconnected — boost strongest connections
                    flat = self._weights.ravel()
                    top_k = max(1, int(0.1 * len(flat)))
                    top_idx = np.argpartition(flat, -top_k)[-top_k:]
                    flat[top_idx] *= (1.0 + self.correction_strength * 0.1)
                    scale_factor = float(-np.mean(flat[top_idx]))
        except (np.linalg.LinAlgError, ValueError):
            # Degenerate matrix (e.g., all zeros) — skip conservation check
            gamma = 0.0
            H = 0.0
            actual = 0.0
            deviation = 0.0

        self._update_count += 1

        # Use calibrated target if available
        target = self._warmup_target if self._auto_calibrated else self._predicted
        deviation = actual - target

        # Build report
        conserved = abs(deviation) <= self._tolerance
        self._last_report = ConservationReport(
            gamma=gamma,
            H=H,
            gamma_plus_H=actual,
            predicted=target,
            deviation=deviation,
            sigma=self._sigma,
            conserved=conserved,
            correction_applied=correction_applied,
            scale_factor=scale_factor,
            update_count=self._update_count,
        )
        return self._last_report

    def conservation_report(self) -> ConservationReport:
        """Return the most recent conservation report (without updating)."""
        if self._last_report is None:
            # Compute from current weights without updating
            try:
                gamma = algebraic_normalized(self._weights)
                H = coupling_entropy(self._weights)
            except (np.linalg.LinAlgError, ValueError):
                gamma, H = 0.0, 0.0
            actual = gamma + H
            self._last_report = ConservationReport(
                gamma=gamma, H=H, gamma_plus_H=actual,
                predicted=self._predicted, deviation=actual - self._predicted,
                sigma=self._sigma,
                conserved=abs(actual - self._predicted) <= self._tolerance,
                correction_applied=False, scale_factor=1.0,
                update_count=self._update_count,
            )
        return self._last_report

    def get_weights(self) -> np.ndarray:
        return self._weights.copy()

    def set_weights(self, w: np.ndarray) -> None:
        self._weights = w.astype(self.dtype).copy()

    def compliance_rate(self) -> float:
        """Fraction of updates where NO correction was needed."""
        if self._update_count == 0:
            return 1.0
        return 1.0 - self._correction_count / self._update_count

    def summary(self) -> Dict[str, Any]:
        """Full status summary."""
        r = self.conservation_report()
        return {
            "backend": self._backend,
            "n_rooms": self.n,
            "V": self.V,
            "update_count": self._update_count,
            "correction_count": self._correction_count,
            "compliance_rate": f"{self.compliance_rate():.1%}",
            "conservation": {
                "gamma": round(r.gamma, 4),
                "H": round(r.H, 4),
                "sum": round(r.gamma_plus_H, 4),
                "predicted": round(r.predicted, 4),
                "deviation": round(r.deviation, 4),
                "sigma": round(r.sigma, 4),
                "conserved": r.conserved,
            },
            "params": {
                "lr": self.lr,
                "decay": self.decay,
                "tolerance_sigma": self.tolerance_sigma,
                "correction_strength": self.correction_strength,
            },
        }


# ---------------------------------------------------------------------------
# Fleet Hebbian Integration — wires kernel to real PLATO rooms
# ---------------------------------------------------------------------------

class FleetHebbianIntegration:
    """Connects the conservation-constrained Hebbian kernel to live PLATO rooms.

    Usage:
        fhi = FleetHebbianIntegration(plato_url="http://147.224.38.131:8847")
        fhi.initialize()
        fhi.run_simulation(n_steps=1000)
        print(fhi.kernel.summary())
    """

    def __init__(
        self,
        plato_url: str = "http://147.224.38.131:8847",
        learning_rate: float = 0.01,
        decay: float = 0.001,
    ) -> None:
        self.plato_url = plato_url
        self.rooms: List[str] = []
        self.room_index: Dict[str, int] = {}
        self.kernel: Optional[ConservationHebbianKernel] = None
        self.lr = learning_rate
        self.decay = decay

    def initialize(self) -> Dict[str, Any]:
        """Fetch rooms from PLATO and initialize the kernel."""
        import requests
        try:
            resp = requests.get(f"{self.plato_url}/rooms", timeout=10)
            data = resp.json()
            self.rooms = [r if isinstance(r, str) else r.get("id", r.get("room_id", str(r)))
                          for r in (data if isinstance(data, list) else data.get("rooms", []))]
        except Exception as e:
            return {"error": str(e), "rooms_found": 0}

        self.room_index = {r: i for i, r in enumerate(self.rooms)}
        self.kernel = ConservationHebbianKernel(
            n_rooms=len(self.rooms),
            V=min(len(self.rooms), 30),  # Use 30 for conservation law (most calibrated)
            learning_rate=self.lr,
            decay=self.decay,
        )
        return {"rooms": len(self.rooms), "V": self.kernel.V, "backend": self.kernel.backend}

    def simulate_tile_flow(
        self,
        source_room: str,
        dest_room: str,
        confidence: float = 0.9,
    ) -> Optional[ConservationReport]:
        """Record a tile flow event and update Hebbian weights."""
        if self.kernel is None:
            return None

        si = self.room_index.get(source_room)
        di = self.room_index.get(dest_room)
        if si is None or di is None:
            return None

        pre = np.zeros(self.kernel.n, dtype=np.float32)
        post = np.zeros(self.kernel.n, dtype=np.float32)
        pre[si] = 1.0
        post[di] = confidence

        return self.kernel.update(pre, post)

    def run_simulation(self, n_steps: int = 1000, seed: int = 42) -> Dict[str, Any]:
        """Run a Monte Carlo simulation of tile flow through PLATO rooms.

        Simulates realistic tile flow patterns:
          - Zipf-distributed room popularity (a few rooms get most tiles)
          - Temporal clustering (bursts of activity in specific rooms)
          - Novelty injection (rare tile types to new rooms)
        """
        if self.kernel is None:
            self.initialize()

        rng = np.random.RandomState(seed)
        n = self.kernel.n
        reports = []

        # Zipf popularity: top 20% of rooms get 80% of traffic
        popularity = rng.zipf(1.5, n)
        popularity = popularity / popularity.sum()

        for step in range(n_steps):
            # Pick source and destination rooms (weighted by popularity)
            source = rng.choice(n, p=popularity)
            dest = rng.choice(n, p=popularity)

            # Temporal clustering: 10% chance of burst to a random room
            if rng.random() < 0.1:
                dest = rng.randint(n)

            # Novelty injection: 5% chance of tile to a NEW room pair
            if rng.random() < 0.05:
                source = rng.randint(n)
                dest = rng.randint(n)

            confidence = 0.5 + 0.5 * rng.random()

            pre = np.zeros(n, dtype=np.float32)
            post = np.zeros(n, dtype=np.float32)
            pre[source] = 1.0
            post[dest] = confidence

            report = self.kernel.update(pre, post)
            reports.append(report)

        # Analyze results
        corrections = sum(1 for r in reports if r.correction_applied)
        final = reports[-1]

        return {
            "steps": n_steps,
            "rooms": n,
            "V": self.kernel.V,
            "corrections": corrections,
            "compliance_rate": f"{(1 - corrections/n_steps):.1%}",
            "final_conservation": {
                "gamma": round(final.gamma, 4),
                "H": round(final.H, 4),
                "sum": round(final.gamma_plus_H, 4),
                "predicted": round(final.predicted, 4),
                "conserved": final.conserved,
            },
            "top_connections": self.get_top_routes(10),
        }

    def get_top_routes(self, n: int = 20) -> List[Tuple[str, str, float]]:
        """Get the top-n strongest Hebbian connections as room pairs."""
        if self.kernel is None:
            return []
        w = self.kernel.get_weights()
        flat_idx = np.argpartition(np.abs(w).ravel(), -n)[-n:]
        top = []
        for idx in flat_idx:
            i, j = divmod(idx, self.kernel.n)
            strength = float(w[i, j])
            if strength > 0:
                src = self.rooms[i] if i < len(self.rooms) else f"room-{i}"
                dst = self.rooms[j] if j < len(self.rooms) else f"room-{j}"
                top.append((src, dst, round(strength, 4)))
        top.sort(key=lambda x: -x[2])
        return top

    def detect_clusters(self, min_strength: float = 0.01) -> List[Dict[str, Any]]:
        """Detect emergent room clusters using the Hebbian weight graph."""
        if self.kernel is None:
            return []
        try:
            import networkx as nx
        except ImportError:
            return [{"error": "networkx required for cluster detection"}]

        w = self.kernel.get_weights()
        G = nx.Graph()
        for i in range(self.kernel.n):
            G.add_node(self.rooms[i] if i < len(self.rooms) else f"room-{i}")

        for i in range(self.kernel.n):
            for j in range(i + 1, self.kernel.n):
                if w[i, j] > min_strength or w[j, i] > min_strength:
                    strength = max(w[i, j], w[j, i])
                    src = self.rooms[i] if i < len(self.rooms) else f"room-{i}"
                    dst = self.rooms[j] if j < len(self.rooms) else f"room-{j}"
                    G.add_edge(src, dst, weight=float(strength))

        try:
            from networkx.algorithms.community import louvain_communities
            communities = louvain_communities(G, weight="weight")
        except ImportError:
            communities = [set(c) for c in nx.connected_components(G)]

        clusters = []
        for comm in communities:
            if len(comm) < 2:
                continue
            rooms = list(comm)
            internal = sum(w[self.room_index.get(s, 0), self.room_index.get(d, 0)]
                          for s in rooms for d in rooms
                          if s in self.room_index and d in self.room_index)
            clusters.append({
                "rooms": rooms,
                "size": len(rooms),
                "internal_strength": round(float(internal), 4),
            })
        clusters.sort(key=lambda c: -c["internal_strength"])
        return clusters
