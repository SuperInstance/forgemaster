"""
PLATO Room Integrity Monitor
=============================
Applies the spectral first integral theory (I = γ + H) to PLATO rooms.

Each PLATO room has tiles that create coupling structure between rooms.
The spectral first integral I(room) = γ + H measures the room's knowledge integrity:
  γ = spectral gap of the room's coupling = how focused the knowledge is
  H = participation entropy = how diverse the knowledge is
  I = γ + H = total knowledge "shape" — conserved when the room is healthy

Based on:
  - MATH-JAZZ-THEOREM.md — Spectral shape conservation under trajectory divergence
  - MATH-KOOPMAN-EIGENFUNCTION.md — I(x) is an approximate Koopman eigenfunction (λ ≈ 1)

Forgemaster ⚒️ | 2026-05-17
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
import warnings


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class RoomHealth(Enum):
    """Health status of a PLATO room based on integrity regime."""
    SWELL = "swell"           # Dynamical regime — healthy knowledge flow
    CHOP = "chop"             # Transitional regime — knowledge degradation
    DEAD = "dead"             # Structural collapse — rank-1 trap
    UNKNOWN = "unknown"       # Not enough data yet


@dataclass
class Tile:
    """Represents a single knowledge tile in a PLATO room."""
    tile_id: str
    content_vector: np.ndarray        # embedding of tile content
    source_room: Optional[str] = None  # room that produced this tile
    target_room: Optional[str] = None  # room receiving this tile
    strength: float = 1.0             # coupling strength

    @property
    def dim(self) -> int:
        return len(self.content_vector)


@dataclass
class RoomState:
    """Represents a PLATO room's coupling state at a given time step."""
    room_id: str
    tiles: List[Tile]
    coupling_matrix: Optional[np.ndarray] = None   # C(x) — built from tiles
    state_vector: Optional[np.ndarray] = None       # x — room's current state

    @property
    def dim(self) -> int:
        if self.state_vector is not None:
            return len(self.state_vector)
        if self.coupling_matrix is not None:
            return self.coupling_matrix.shape[0]
        if self.tiles:
            return self.tiles[0].dim
        return 0

    def build_state_vector(self) -> np.ndarray:
        """Build state vector from tile content vectors (mean)."""
        if not self.tiles:
            return np.zeros(1)
        vecs = np.array([t.content_vector for t in self.tiles])
        self.state_vector = vecs.mean(axis=0)
        return self.state_vector


@dataclass
class IntegritySnapshot:
    """Single time-step measurement of room integrity."""
    room_id: str
    step: int
    gamma: float              # participation ratio (spectral focus)
    entropy: float            # participation entropy (spectral diversity)
    integrity: float          # I = γ + H
    commutator_norm: float    # ||[D, C]|| — controls conservation quality
    spectral_gap: float       # gap between top two eigenvalues
    eigenvalues: np.ndarray   # full eigenvalue spectrum
    health: RoomHealth = RoomHealth.UNKNOWN


@dataclass
class IntegrityTracker:
    """Tracks I(x) over time for a single room, computes CV, detects degradation."""
    room_id: str
    history: List[IntegritySnapshot] = field(default_factory=list)

    @property
    def integrity_values(self) -> np.ndarray:
        if not self.history:
            return np.array([])
        return np.array([s.integrity for s in self.history])

    @property
    def cv(self) -> float:
        """Coefficient of variation of integrity — lower = more conserved."""
        vals = self.integrity_values
        if len(vals) < 2 or np.mean(vals) == 0:
            return float('inf')
        return float(np.std(vals) / np.abs(np.mean(vals)))

    @property
    def mean_integrity(self) -> float:
        vals = self.integrity_values
        return float(np.mean(vals)) if len(vals) > 0 else 0.0

    @property
    def integrity_drift(self) -> float:
        """Slope of integrity over time (linear fit). Negative = degrading."""
        vals = self.integrity_values
        if len(vals) < 3:
            return 0.0
        t = np.arange(len(vals))
        slope = np.polyfit(t, vals, 1)[0]
        return float(slope)

    def record(self, snapshot: IntegritySnapshot) -> None:
        self.history.append(snapshot)

    def latest(self) -> Optional[IntegritySnapshot]:
        return self.history[-1] if self.history else None


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def compute_spectral_properties(C: np.ndarray) -> Tuple[np.ndarray, float, float, float]:
    """
    Compute spectral properties of coupling matrix C.

    Returns (eigenvalues, participation_ratio, participation_entropy, spectral_gap).
    """
    eigvals = np.linalg.eigvalsh(C) if np.allclose(C, C.T) else np.linalg.eigvals(C)
    # Use absolute values for spectral shape
    abs_eig = np.abs(eigvals).astype(float)

    # Avoid division by zero
    total = np.sum(abs_eig ** 2)
    if total < 1e-15:
        return eigvals, 0.0, 0.0, 0.0

    # Participation ratio: γ = (Σ|λ_i|²)² / Σ|λ_i|⁴
    gamma = float(total ** 2 / np.sum(abs_eig ** 4))

    # Participation entropy: H = -Σ p_i ln(p_i)
    p = abs_eig ** 2 / total
    p = p[p > 1e-15]  # filter zeros
    entropy = float(-np.sum(p * np.log(p)))

    # Spectral gap between top two eigenvalues
    sorted_eig = np.sort(abs_eig)[::-1]
    gap = float(sorted_eig[0] - sorted_eig[1]) if len(sorted_eig) > 1 else float(sorted_eig[0])

    return eigvals, gamma, entropy, gap


def compute_commutator(C: np.ndarray, x: np.ndarray, activation: str = 'tanh') -> float:
    """
    Compute ||[D, C]||_F where D = diag(σ'(Cx)).

    This controls the conservation quality (Jazz Theorem).
    """
    Cx = C @ x
    if activation == 'tanh':
        d = 1.0 - np.tanh(Cx) ** 2  # tanh'
    elif activation == 'sigmoid':
        s = 1.0 / (1.0 + np.exp(-Cx))
        d = s * (1.0 - s)  # sigmoid'
    elif activation == 'swish':
        s = 1.0 / (1.0 + np.exp(-Cx))
        d = s + Cx * s * (1.0 - s)  # swish' = σ(x) + xσ'(x)
    else:
        d = np.ones_like(Cx)

    D = np.diag(d)
    commutator = D @ C - C @ D
    return float(np.linalg.norm(commutator, 'fro'))


def compute_integrity(room_state: RoomState, activation: str = 'tanh') -> IntegritySnapshot:
    """
    Compute I(x) = γ + H for a PLATO room.

    This is the spectral first integral from the Jazz Theorem.
    """
    C = room_state.coupling_matrix
    x = room_state.state_vector

    if C is None:
        raise ValueError(f"Room {room_state.room_id} has no coupling matrix")
    if x is None:
        raise ValueError(f"Room {room_state.room_id} has no state vector")

    eigvals, gamma, entropy, spectral_gap = compute_spectral_properties(C)
    comm_norm = compute_commutator(C, x, activation)
    integrity = gamma + entropy

    # Classify health regime
    if gamma < 1.01:
        health = RoomHealth.DEAD       # rank-1 trap
    elif comm_norm < 0.01:
        health = RoomHealth.SWELL      # dynamical regime (healthy)
    else:
        health = RoomHealth.CHOP       # transitional (degrading)

    return IntegritySnapshot(
        room_id=room_state.room_id,
        step=0,  # caller should override
        gamma=gamma,
        entropy=entropy,
        integrity=integrity,
        commutator_norm=comm_norm,
        spectral_gap=spectral_gap,
        eigenvalues=eigvals,
        health=health,
    )


# ---------------------------------------------------------------------------
# Coupling matrix builders
# ---------------------------------------------------------------------------

def room_coupling_matrix(tiles: List[Tile], method: str = 'attention',
                         tau: float = 1.0) -> np.ndarray:
    """
    Build coupling matrix C from tile interaction patterns.

    Methods:
      'attention' — scaled dot-product: C_ij = softmax(x_i · x_j / τ)
      'hebbian'   — Hebbian: C_ij = x_i · x_j
      'cosine'    — cosine similarity matrix
    """
    if not tiles:
        return np.array([[1.0]])

    n = len(tiles)
    vecs = np.array([t.content_vector for t in tiles])
    dim = vecs.shape[1]

    # If we have fewer tiles than dimension, pad to tile count
    N = max(n, dim)
    # Build N×N coupling from tile vectors
    # Use first N vectors (or cycle if needed)
    if n < N:
        # Extend with zeros
        padded = np.zeros((N, vecs.shape[1]))
        padded[:n] = vecs
        vecs = padded

    # Use first N entries as "nodes"
    X = vecs[:N]

    if method == 'attention':
        # Scaled dot-product with tanh (NOT full softmax — preserves spectral diversity)
        C = X @ X.T / tau
        C = np.tanh(C)
        C = (C + C.T) / 2  # symmetrize
        C += 0.1 * np.eye(N)  # diagonal stability
    elif method == 'hebbian':
        C = X @ X.T
        # Normalize to prevent explosion
        norm = np.linalg.norm(C, 'fro')
        if norm > 1e-10:
            C = C / norm * N
        C += 0.05 * np.eye(N)
    elif method == 'cosine':
        norms = np.linalg.norm(X, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-10)
        X_norm = X / norms
        C = X_norm @ X_norm.T
        C += 0.1 * np.eye(N)
    else:
        raise ValueError(f"Unknown method: {method}")

    return C


def fleet_coupling_matrix(rooms: List[RoomState],
                          method: str = 'attention',
                          tau: float = 1.0) -> np.ndarray:
    """
    Build fleet-wide coupling from room-to-room tile exchange.

    The fleet coupling is a block matrix where off-diagonal blocks
    represent inter-room tile exchange and diagonal blocks are intra-room coupling.
    """
    if not rooms:
        return np.array([[1.0]])

    # Build each room's coupling
    room_couplings = []
    for room in rooms:
        if room.coupling_matrix is not None:
            room_couplings.append(room.coupling_matrix)
        else:
            C = room_coupling_matrix(room.tiles, method, tau)
            room.coupling_matrix = C
            room_couplings.append(C)

    # Block-diagonal as base
    sizes = [C.shape[0] for C in room_couplings]
    N = sum(sizes)
    fleet_C = np.zeros((N, N))

    # Fill diagonal blocks
    offset = 0
    for C in room_couplings:
        n = C.shape[0]
        fleet_C[offset:offset+n, offset:offset+n] = C
        offset += n

    # Off-diagonal: inter-room tile exchange
    # For each pair of rooms, compute cross-coupling from shared tiles
    for i, room_a in enumerate(rooms):
        for j, room_b in enumerate(rooms):
            if i == j:
                continue
            # Cross-coupling from room A's state to room B's coupling
            if room_a.state_vector is not None and room_b.coupling_matrix is not None:
                x_a = room_a.state_vector
                C_b = room_b.coupling_matrix
                dim_a = len(x_a)
                dim_b = C_b.shape[0]
                # Use attention-style cross coupling
                min_dim = min(dim_a, dim_b)
                # Cross attention: x_a (query) attends to columns of C_b (keys)
                cross = np.outer(x_a[:min_dim], np.ones(min_dim))
                cross[:, :min_dim] = np.outer(x_a[:min_dim], np.ones(min_dim))
                # Scale down inter-room coupling (tiles are exchanged, not shared)
                scale = 0.1
                oi = sum(sizes[:i])
                oj = sum(sizes[:j])
                # Place cross-coupling in off-diagonal block
                for ii in range(min(sizes[i], min_dim)):
                    for jj in range(min(sizes[j], min_dim)):
                        if ii < len(x_a) and jj < C_b.shape[1]:
                            fleet_C[oi + ii, oj + jj] += scale * x_a[min(ii, len(x_a)-1)] * C_b[min(jj, C_b.shape[0]-1), min(jj, C_b.shape[1]-1)]

    # Symmetrize for stability
    fleet_C = (fleet_C + fleet_C.T) / 2

    # Add small identity for regularity
    fleet_C += 1e-6 * np.eye(N)

    return fleet_C


# ---------------------------------------------------------------------------
# Regime detection
# ---------------------------------------------------------------------------

def detect_chop(tracker: IntegrityTracker, window: int = 10,
                cv_threshold: float = 0.04) -> bool:
    """
    Detect transitional regime (knowledge degradation).

    "Chop" = the room's integrity is fluctuating beyond the healthy dynamical regime.
    This corresponds to the transitional regime in the Jazz Theorem where
    ||[D, C]|| is large and conservation breaks down.

    Signs of chop:
      1. CV(I) > threshold over recent window
      2. Negative drift (integrity decreasing)
      3. Commutator norm is elevated
    """
    if len(tracker.history) < window:
        return False

    recent = tracker.history[-window:]
    vals = np.array([s.integrity for s in recent])

    if np.mean(vals) == 0:
        return True  # zero integrity = dead

    cv = np.std(vals) / np.abs(np.mean(vals))
    drift = np.polyfit(np.arange(len(vals)), vals, 1)[0]

    # Elevated commutator in recent history
    comm_norms = [s.commutator_norm for s in recent]
    avg_comm = np.mean(comm_norms)

    return cv > cv_threshold or drift < -0.01 or avg_comm > 0.5


def detect_swell(tracker: IntegrityTracker, window: int = 10,
                 cv_threshold: float = 0.04) -> bool:
    """
    Confirm dynamical regime (healthy knowledge flow).

    "Swell" = the room's integrity is stable and conserved.
    This corresponds to the dynamical regime where I ≈ const (Koopman λ ≈ 1).

    Signs of swell:
      1. CV(I) < threshold over recent window
      2. Stable or positive drift
      3. Low commutator norm
    """
    if len(tracker.history) < window:
        return False

    recent = tracker.history[-window:]
    vals = np.array([s.integrity for s in recent])

    if np.mean(vals) == 0:
        return False

    cv = np.std(vals) / np.abs(np.mean(vals))
    drift = np.polyfit(np.arange(len(vals)), vals, 1)[0]
    comm_norms = [s.commutator_norm for s in recent]
    avg_comm = np.mean(comm_norms)

    return cv < cv_threshold and drift >= -0.005 and avg_comm < 0.3


def detect_dead(tracker: IntegrityTracker, window: int = 5) -> bool:
    """
    Detect structural collapse (rank-1 trap).

    "Dead" = γ ≈ 1, H ≈ 0 — the coupling is dominated by a single eigenvalue.
    All knowledge has collapsed to one dimension.
    """
    if len(tracker.history) < window:
        return False

    recent = tracker.history[-window:]
    avg_gamma = np.mean([s.gamma for s in recent])
    avg_entropy = np.mean([s.entropy for s in recent])

    return avg_gamma < 1.1 and avg_entropy < 0.1


# ---------------------------------------------------------------------------
# Health reports
# ---------------------------------------------------------------------------

def health_report(tracker: IntegrityTracker, verbose: bool = True) -> str:
    """
    Generate human-readable integrity report for a PLATO room.
    """
    if not tracker.history:
        return f"[{tracker.room_id}] No integrity data yet."

    latest = tracker.history[-1]
    lines = []
    lines.append(f"{'='*60}")
    lines.append(f"  PLATO ROOM INTEGRITY REPORT: {tracker.room_id}")
    lines.append(f"{'='*60}")
    lines.append(f"  Step:              {latest.step}")
    lines.append(f"  Health:            {latest.health.value.upper()}")
    lines.append(f"  Integrity I:       {latest.integrity:.6f}")
    lines.append(f"    γ (focus):       {latest.gamma:.6f}")
    lines.append(f"    H (diversity):   {latest.entropy:.6f}")
    lines.append(f"  Spectral gap:      {latest.spectral_gap:.6f}")
    lines.append(f"  Commutator ||[D,C]||: {latest.commutator_norm:.6f}")
    lines.append(f"{'─'*60}")

    # Time-series stats
    vals = tracker.integrity_values
    lines.append(f"  HISTORY ({len(vals)} steps)")
    lines.append(f"    Mean I:          {np.mean(vals):.6f}")
    lines.append(f"    Std I:           {np.std(vals):.6f}")
    lines.append(f"    CV(I):           {tracker.cv:.6f}")
    lines.append(f"    Drift:           {tracker.integrity_drift:+.6f}")

    # Regime detection
    is_chop = detect_chop(tracker)
    is_swell = detect_swell(tracker)
    is_dead = detect_dead(tracker)

    lines.append(f"{'─'*60}")
    lines.append(f"  REGIME ANALYSIS")
    if is_dead:
        lines.append(f"    ⚠️  DEAD — rank-1 collapse detected (γ < 1.1, H < 0.1)")
    elif is_chop:
        lines.append(f"    🌊 CHOP — transitional regime, knowledge degrading")
    elif is_swell:
        lines.append(f"    ✨ SWELL — dynamical regime, knowledge healthy")
    else:
        lines.append(f"    ❓ UNKNOWN — insufficient data or mixed signals")

    # Conservation quality (Jazz Theorem)
    lines.append(f"{'─'*60}")
    lines.append(f"  CONSERVATION (Jazz Theorem)")
    if tracker.cv < 0.01:
        lines.append(f"    EXCELLENT — I is conserved (CV < 0.01)")
        lines.append(f"    Koopman eigenvalue λ ≈ 1 (structural regime)")
    elif tracker.cv < 0.04:
        lines.append(f"    GOOD — I is approximately conserved (CV < 0.04)")
        lines.append(f"    Koopman eigenvalue λ ≈ 1 (dynamical regime)")
    else:
        lines.append(f"    POOR — I varies significantly (CV ≥ 0.04)")
        lines.append(f"    Koopman eigenvalue |1-λ| may be large")

    # Eigenvalue summary
    lines.append(f"{'─'*60}")
    lines.append(f"  EIGENVALUE SPECTRUM (top 5)")
    sorted_eig = np.sort(np.abs(latest.eigenvalues))[::-1]
    for i, e in enumerate(sorted_eig[:5]):
        bar = '█' * int(min(e / max(sorted_eig[0], 1e-10) * 30, 30))
        lines.append(f"    λ_{i+1}: {e:+.6f}  {bar}")

    lines.append(f"{'='*60}")
    return '\n'.join(lines)


def fleet_health_report(trackers: Dict[str, IntegrityTracker]) -> str:
    """Generate summary report for all rooms in the fleet."""
    lines = []
    lines.append(f"{'='*70}")
    lines.append(f"  PLATO FLEET INTEGRITY SUMMARY — {len(trackers)} ROOMS")
    lines.append(f"{'='*70}")

    for room_id, tracker in trackers.items():
        if not tracker.history:
            lines.append(f"  {room_id:20s}  [NO DATA]")
            continue

        latest = tracker.history[-1]
        status_emoji = {"swell": "✨", "chop": "🌊", "dead": "💀", "unknown": "❓"}
        emoji = status_emoji.get(latest.health.value, "?")
        lines.append(
            f"  {emoji} {room_id:18s}  "
            f"I={latest.integrity:.4f}  "
            f"CV={tracker.cv:.4f}  "
            f"γ={latest.gamma:.3f}  "
            f"H={latest.entropy:.3f}  "
            f"||[D,C]||={latest.commutator_norm:.4f}"
        )

    # Fleet-wide coupling
    all_cvs = [t.cv for t in trackers.values() if len(t.history) > 1]
    if all_cvs:
        lines.append(f"{'─'*70}")
        lines.append(f"  Fleet mean CV:  {np.mean(all_cvs):.6f}")
        lines.append(f"  Fleet max CV:   {np.max(all_cvs):.6f}")
        lines.append(f"  Fleet min CV:   {np.min(all_cvs):.6f}")

    lines.append(f"{'='*70}")
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Simulation helpers
# ---------------------------------------------------------------------------

def step_room(room: RoomState, activation: str = 'tanh',
              coupling_method: str = 'attention', tau: float = 1.0,
              noise_scale: float = 0.01) -> RoomState:
    """
    Advance room state by one time step: x_{t+1} = σ(C(x_t) · x_t) + noise.

    Returns a new RoomState with updated state_vector.
    """
    C = room.coupling_matrix
    x = room.state_vector

    if C is None or x is None:
        raise ValueError(f"Room {room.room_id} needs coupling_matrix and state_vector")

    N = len(x)
    # Ensure C is NxN
    if C.shape[0] != N or C.shape[1] != N:
        # Resize coupling matrix
        C_new = np.eye(N)
        min_d = min(C.shape[0], N, C.shape[1], N)
        C_new[:min_d, :min_d] = C[:min_d, :min_d]
        C = C_new

    Cx = C @ x

    if activation == 'tanh':
        x_new = np.tanh(Cx)
    elif activation == 'sigmoid':
        x_new = 1.0 / (1.0 + np.exp(-Cx))
    elif activation == 'swish':
        x_new = Cx / (1.0 + np.exp(-Cx))
    else:
        x_new = np.tanh(Cx)

    # Add small noise (knowledge fluctuation)
    x_new += noise_scale * np.random.randn(N)

    # Update tile content vectors (independent drift — maintain diversity)
    new_tiles = []
    for i, tile in enumerate(room.tiles):
        new_vec = tile.content_vector.copy()
        # Each tile drifts independently with small noise (knowledge evolves)
        new_vec += 0.05 * np.random.randn(len(new_vec))
        new_tiles.append(Tile(
            tile_id=tile.tile_id,
            content_vector=new_vec,
            source_room=tile.source_room,
            target_room=tile.target_room,
            strength=tile.strength,
        ))

    return RoomState(
        room_id=room.room_id,
        tiles=new_tiles,
        coupling_matrix=room_coupling_matrix(new_tiles, coupling_method, tau),
        state_vector=x_new,
    )


def exchange_tiles(rooms: List[RoomState], exchange_rate: float = 0.1) -> List[RoomState]:
    """
    Simulate tile exchange between rooms.

    Each room sends its highest-strength tile to a random other room.
    The received tile slightly perturbs the receiving room's coupling.
    """
    if len(rooms) < 2:
        return rooms

    new_rooms = []
    outgoing = {}  # room_id -> tile to send

    # Select outgoing tiles
    for room in rooms:
        if room.tiles:
            best = max(room.tiles, key=lambda t: t.strength)
            outgoing[room.room_id] = Tile(
                tile_id=f"{room.room_id}:{best.tile_id}",
                content_vector=best.content_vector.copy(),
                source_room=room.room_id,
                strength=best.strength * exchange_rate,
            )

    # Apply incoming tiles
    for room in rooms:
        new_tiles = list(room.tiles)
        for other_id, tile in outgoing.items():
            if other_id != room.room_id:
                # Merge incoming tile's influence into existing tiles
                incoming_vec = tile.content_vector
                for existing in new_tiles:
                    # Blend: existing tile absorbs some of incoming
                    blend = 1.0 - exchange_rate
                    min_len = min(len(existing.content_vector), len(incoming_vec))
                    existing.content_vector[:min_len] = (
                        blend * existing.content_vector[:min_len] +
                        exchange_rate * incoming_vec[:min_len]
                    )
                    existing.strength = existing.strength * blend + tile.strength * exchange_rate

        new_rooms.append(RoomState(
            room_id=room.room_id,
            tiles=new_tiles,
            coupling_matrix=room.coupling_matrix,  # will be rebuilt on next step
            state_vector=room.state_vector,
        ))

    return new_rooms
