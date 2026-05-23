"""Hebbian Enhancement Layer for the PLATO room system.

Five tightly-coupled modules that add emergent routing on top of the existing
fleet_router / fleet_dispatch / fleet_stage_classifier stack.

Architecture:
    TileFlowTracker  ─►  HebbianRouter  ─►  PLATO rooms
         │                     │
         ▼                     ▼
    EmergentStageClassifier    CUDAHebbianKernel (hot-path weight updates)
         │
         ▼
    RoomClusterDetector  ─►  visualize / cluster routing

Integration:
    from hebbian_layer import TileFlowTracker, HebbianRouter, EmergentStageClassifier
    from hebbian_layer import CUDAHebbianKernel, RoomClusterDetector
"""

from __future__ import annotations

import collections
import ctypes
import json
import math
import os
import struct
import tempfile
import time
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

import numpy as np
import requests

# ---------------------------------------------------------------------------
# Optional heavy deps — imported lazily so the rest of the module loads fine
# ---------------------------------------------------------------------------

try:
    import networkx as nx
    _HAS_NX = True
except ImportError:
    _HAS_NX = False

try:
    import cupy as cp
    _HAS_CUPY = True
except ImportError:
    _HAS_CUPY = False


# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

PLATO_BASE = "http://147.224.38.131:8847"
TILE_TYPES = frozenset({"model", "data", "compression", "benchmark", "deploy"})

# Hebbian hyperparameters (tunable at runtime via HebbianRouter)
DEFAULT_LR: float = 0.01          # learning rate η
DEFAULT_DECAY: float = 0.001      # weight decay λ  (prevents runaway growth)
DEFAULT_NOVELTY_THRESHOLD: float = 0.15   # freq below this → novel tile
DEFAULT_HABITUATION_THRESHOLD: float = 0.70  # freq above this → habituated tile
RING_BUFFER_SIZE: int = 50_000    # flow records kept in memory


# ===========================================================================
# 1. TileFlowTracker
# ===========================================================================

@dataclass
class FlowRecord:
    """A single tile-flow event between two rooms."""
    source_room: str
    dest_room: str
    tile_type: str
    tile_hash: str
    timestamp: float = field(default_factory=time.monotonic)
    lamport_clock: int = 0


class TileFlowTracker:
    """Tracks tile flow between PLATO rooms and derives connection strengths.

    Stores the most recent ``ring_size`` flow events in a ring buffer.  All
    heavier statistics (connection strength, novelty/habituation) are computed
    lazily from that buffer with an exponential-recency weighting so old events
    fade out naturally.

    Thread-safe via a single RW lock on the ring buffer.

    Parameters
    ----------
    ring_size:
        Maximum number of flow records to retain.
    decay_half_life:
        Seconds after which an event contributes half its weight to statistics.
        Longer values produce more stable but slower-adapting weights.
    persist_path:
        If given, the tracker periodically snapshots its state to this JSON
        file so weights survive process restarts.
    """

    def __init__(
        self,
        ring_size: int = RING_BUFFER_SIZE,
        decay_half_life: float = 3600.0,
        persist_path: Optional[str] = None,
    ) -> None:
        self._ring: deque[FlowRecord] = deque(maxlen=ring_size)
        self._half_life = decay_half_life
        self._persist_path = persist_path
        self._lock = threading.RLock()

        # Fast-path caches — invalidated on each record_flow()
        self._strength_cache: Dict[Tuple[str, str], float] = {}
        self._type_freq_cache: Dict[str, float] = {}
        self._cache_valid = False

        # Lamport clock for this tracker instance
        self._lamport: int = 0

        if persist_path and os.path.exists(persist_path):
            self._load_snapshot(persist_path)

    # ------------------------------------------------------------------
    # Core write path
    # ------------------------------------------------------------------

    def record_flow(
        self,
        source_room: str,
        dest_room: str,
        tile_type: str,
        tile_hash: str = "",
        lamport_clock: int = 0,
    ) -> FlowRecord:
        """Record a tile emission from *source_room* to *dest_room*.

        Parameters
        ----------
        source_room:
            The room that emitted the tile.
        dest_room:
            The room that received/will process the tile.
        tile_type:
            One of ``{"model","data","compression","benchmark","deploy"}``.
        tile_hash:
            SHA-256 of the tile content (from ``Tile._hash``).  Used to
            identify whether the exact same tile is being re-routed.
        lamport_clock:
            Lamport timestamp from the originating room.

        Returns
        -------
        FlowRecord
            The recorded event (useful for chaining / logging).
        """
        with self._lock:
            self._lamport = max(self._lamport, lamport_clock) + 1
            rec = FlowRecord(
                source_room=source_room,
                dest_room=dest_room,
                tile_type=tile_type,
                tile_hash=tile_hash,
                timestamp=time.monotonic(),
                lamport_clock=self._lamport,
            )
            self._ring.append(rec)
            self._cache_valid = False
            return rec

    # ------------------------------------------------------------------
    # Statistics — all use exponential recency weighting
    # ------------------------------------------------------------------

    def _decay_weight(self, age_seconds: float) -> float:
        """Exponential decay: w = 2^(-age / half_life)."""
        return math.pow(2.0, -age_seconds / self._half_life)

    def _rebuild_caches(self) -> None:
        """Recompute strength and frequency caches from the ring buffer."""
        now = time.monotonic()
        pair_weights: Dict[Tuple[str, str], float] = defaultdict(float)
        type_weights: Dict[str, float] = defaultdict(float)
        total_weight = 0.0

        for rec in self._ring:
            w = self._decay_weight(now - rec.timestamp)
            pair = (rec.source_room, rec.dest_room)
            pair_weights[pair] += w
            type_weights[rec.tile_type] += w
            total_weight += w

        # Normalise type frequencies to [0, 1]
        if total_weight > 0:
            self._type_freq_cache = {
                t: v / total_weight for t, v in type_weights.items()
            }
        else:
            self._type_freq_cache = {}

        # Connection strength: normalised pair weight, clipped to [0, 1]
        # Use pair weight / max-pair-weight so the strongest link is 1.0
        max_pw = max(pair_weights.values(), default=1.0)
        self._strength_cache = {
            pair: min(1.0, v / max_pw) for pair, v in pair_weights.items()
        }
        self._cache_valid = True

    def get_connection_strength(self, room_a: str, room_b: str) -> float:
        """Return the normalised connection strength between two rooms.

        Returns a float in ``[0.0, 1.0]``.  Directionality is ignored —
        bidirectional flow strengthens the same edge.

        Parameters
        ----------
        room_a, room_b:
            Room names.  Order does not matter.
        """
        with self._lock:
            if not self._cache_valid:
                self._rebuild_caches()
            # Try both directions
            key = (room_a, room_b)
            rev = (room_b, room_a)
            return max(
                self._strength_cache.get(key, 0.0),
                self._strength_cache.get(rev, 0.0),
            )

    def get_novelty_score(self, tile_type: str) -> float:
        """Return how novel *tile_type* is, in ``[0.0, 1.0]``.

        1.0 = never seen before.  0.0 = extremely common.
        Computed as ``1 - relative_frequency``.
        """
        with self._lock:
            if not self._cache_valid:
                self._rebuild_caches()
            freq = self._type_freq_cache.get(tile_type, 0.0)
            return 1.0 - freq

    def get_habituation_score(self, tile_type: str) -> float:
        """Return how habituated the system is to *tile_type*, in ``[0.0, 1.0]``.

        1.0 = extremely common (fast-path candidate).  Inverse of novelty.
        """
        return 1.0 - self.get_novelty_score(tile_type)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def snapshot(self, path: Optional[str] = None) -> None:
        """Persist ring buffer to JSON for warm-restart."""
        target = path or self._persist_path
        if not target:
            return
        with self._lock:
            records = [asdict(r) for r in self._ring]
        with open(target, "w") as fh:
            json.dump({"records": records, "lamport": self._lamport}, fh)

    def _load_snapshot(self, path: str) -> None:
        with open(path) as fh:
            data = json.load(fh)
        self._lamport = data.get("lamport", 0)
        for r in data.get("records", []):
            self._ring.append(FlowRecord(**r))
        self._cache_valid = False

    # ------------------------------------------------------------------
    # Iteration helpers
    # ------------------------------------------------------------------

    def iter_recent(self, n: int = 1000) -> Iterator[FlowRecord]:
        """Yield the *n* most recent flow records (newest first)."""
        with self._lock:
            records = list(self._ring)
        yield from reversed(records[-n:])

    def room_neighbors(self, room: str, min_strength: float = 0.1) -> List[Tuple[str, float]]:
        """Return ``(neighbor_room, strength)`` pairs for *room*, sorted desc."""
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

    def __len__(self) -> int:
        return len(self._ring)


# ===========================================================================
# 2. HebbianRouter
# ===========================================================================

class HebbianRouter:
    """Route tiles to rooms based on emergent connection strengths.

    Combines learned Hebbian weights with the existing explicit routing rules
    (fleet_router.py).  The key insight:

    - **Novel tiles** → route through MORE rooms (deep exploration)
    - **Habituated tiles** → route through FEWER rooms (fast path)
    - **Unknown patterns** → fall through to ``explicit_router``

    Parameters
    ----------
    tracker:
        A :class:`TileFlowTracker` providing live connection strengths.
    all_rooms:
        Complete list of room names in the PLATO system.
    explicit_router:
        Callable ``(tile_type, tags) → List[str]`` — the existing
        fleet_router logic.  Called as fallback for cold-start or unknown types.
    novelty_threshold:
        Tiles with novelty score above this are treated as novel.
    habituation_threshold:
        Tiles with habituation score above this get fast-path routing.
    max_novel_rooms:
        Cap on rooms for novel tiles (prevents fanout explosion).
    min_habituated_rooms:
        Minimum rooms even for highly-habituated tiles.
    """

    def __init__(
        self,
        tracker: TileFlowTracker,
        all_rooms: List[str],
        explicit_router: Optional[Any] = None,
        novelty_threshold: float = DEFAULT_NOVELTY_THRESHOLD,
        habituation_threshold: float = DEFAULT_HABITUATION_THRESHOLD,
        max_novel_rooms: int = 12,
        min_habituated_rooms: int = 2,
        strength_cutoff: float = 0.15,
    ) -> None:
        self.tracker = tracker
        self.all_rooms = list(all_rooms)
        self.explicit_router = explicit_router
        self.novelty_threshold = novelty_threshold
        self.habituation_threshold = habituation_threshold
        self.max_novel_rooms = max_novel_rooms
        self.min_habituated_rooms = min_habituated_rooms
        self.strength_cutoff = strength_cutoff

    def route(
        self,
        tile_type: str,
        tile_hash: str,
        source_room: str,
        tags: Optional[List[str]] = None,
        force_explicit: bool = False,
    ) -> List[str]:
        """Decide which rooms should process this tile.

        Parameters
        ----------
        tile_type:
            Type of the tile being routed.
        tile_hash:
            Content hash of the tile (used to detect exact repeat).
        source_room:
            Room that emitted this tile.
        tags:
            Optional domain tags from the tile — passed to explicit_router.
        force_explicit:
            If True, skip Hebbian logic and use explicit_router only.

        Returns
        -------
        List[str]
            Ordered list of rooms to send the tile to.
            First entry is the primary destination; subsequent entries are
            secondary (enrichment) destinations.
        """
        if force_explicit or len(self.tracker) < 100:
            # Cold-start: not enough data to trust Hebbian weights
            return self._explicit_fallback(tile_type, tags)

        novelty = self.tracker.get_novelty_score(tile_type)
        habituation = self.tracker.get_habituation_score(tile_type)

        # Get neighbours of source_room ranked by connection strength
        neighbours = self.tracker.room_neighbors(source_room, min_strength=self.strength_cutoff)

        if novelty >= self.novelty_threshold:
            return self._route_novel(tile_type, source_room, neighbours, tags)
        elif habituation >= self.habituation_threshold:
            return self._route_habituated(source_room, neighbours)
        else:
            return self._route_normal(source_room, neighbours, tile_type, tags)

    def _route_novel(
        self,
        tile_type: str,
        source_room: str,
        neighbours: List[Tuple[str, float]],
        tags: Optional[List[str]],
    ) -> List[str]:
        """Novel tile: cast wide, up to max_novel_rooms.

        Strategy: include all rooms with any positive connection strength,
        PLUS any rooms returned by explicit_router that aren't already covered.
        """
        rooms: List[str] = []

        # Start with Hebbian candidates
        for room, strength in neighbours:
            if room != source_room:
                rooms.append(room)
                if len(rooms) >= self.max_novel_rooms:
                    break

        # Augment with explicit routing — covers domains not yet in the graph
        explicit = self._explicit_fallback(tile_type, tags)
        for r in explicit:
            if r not in rooms and r != source_room:
                rooms.append(r)
                if len(rooms) >= self.max_novel_rooms:
                    break

        return rooms if rooms else explicit

    def _route_habituated(
        self,
        source_room: str,
        neighbours: List[Tuple[str, float]],
    ) -> List[str]:
        """Habituated tile: fast path — top N strongest connections only."""
        rooms = [
            r for r, _s in neighbours[:self.min_habituated_rooms]
            if r != source_room
        ]
        if not rooms and self.all_rooms:
            # Fallback: pick the first non-source room
            rooms = [r for r in self.all_rooms if r != source_room][:1]
        return rooms

    def _route_normal(
        self,
        source_room: str,
        neighbours: List[Tuple[str, float]],
        tile_type: str,
        tags: Optional[List[str]],
    ) -> List[str]:
        """Normal tile: blend Hebbian top-k with one explicit suggestion."""
        rooms = [r for r, _s in neighbours[:5] if r != source_room]
        explicit = self._explicit_fallback(tile_type, tags)
        # Inject explicit primary if not already present
        if explicit and explicit[0] not in rooms:
            rooms.insert(0, explicit[0])
        return rooms[:6]

    def _explicit_fallback(
        self, tile_type: str, tags: Optional[List[str]]
    ) -> List[str]:
        """Call the existing fleet_router or return a safe default."""
        if self.explicit_router is not None:
            try:
                result = self.explicit_router(tile_type, tags or [])
                if isinstance(result, list):
                    return result
            except Exception:
                pass
        # Safe default: route to any room whose name contains the tile_type
        return [r for r in self.all_rooms if tile_type in r.lower()][:3] or self.all_rooms[:1]

    def record_outcome(
        self,
        source_room: str,
        dest_room: str,
        tile_type: str,
        tile_hash: str,
        success: bool,
    ) -> None:
        """Inform the tracker about a routing outcome.

        Call this after a routed tile has been processed.  Successful
        outcomes reinforce the edge; failures let it decay naturally.

        Parameters
        ----------
        success:
            Whether the destination room produced a useful response tile.
        """
        if success:
            self.tracker.record_flow(
                source_room=source_room,
                dest_room=dest_room,
                tile_type=tile_type,
                tile_hash=tile_hash,
            )


# ===========================================================================
# 3. EmergentStageClassifier
# ===========================================================================

@dataclass
class RoomBehaviorRecord:
    """Running statistics for one (room, tile_type) pair."""
    room: str
    tile_type: str
    total_attempts: int = 0
    successful_responses: int = 0
    avg_confidence: float = 0.0
    last_updated: float = field(default_factory=time.monotonic)

    @property
    def success_rate(self) -> float:
        if self.total_attempts == 0:
            return 0.0
        return self.successful_responses / self.total_attempts

    def update(self, success: bool, confidence: float) -> None:
        self.total_attempts += 1
        if success:
            self.successful_responses += 1
        # Exponential moving average of confidence
        alpha = 0.1
        self.avg_confidence = (1 - alpha) * self.avg_confidence + alpha * confidence
        self.last_updated = time.monotonic()


class EmergentStageClassifier:
    """Classify room capability stages from observed tile-processing behavior.

    Unlike the 6-probe ``StageClassifier`` (which sends explicit test
    traffic), this classifier is purely observational.  It watches real tile
    processing and infers stage from the pattern of successes and failures.

    Stage mapping (mirrors fleet_stage_classifier.py semantics):

    =====  ========================================================
    Stage  Meaning
    =====  ========================================================
    1      Room fails on almost all tile types (< 10% success)
    2      Room echoes/parrots tiles but rarely transforms them
    3      Room processes tiles with moderate reliability (10–79%)
    4      Room reliably produces high-confidence responses (≥ 80%)
    =====  ========================================================

    Parameters
    ----------
    min_observations:
        Minimum tile-processing events before a stage assignment is made.
        Below this threshold, the room is reported as stage 0 (unknown).
    """

    def __init__(self, min_observations: int = 20) -> None:
        self.min_observations = min_observations
        # (room, tile_type) → RoomBehaviorRecord
        self._records: Dict[Tuple[str, str], RoomBehaviorRecord] = {}
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Update path — called after every tile-processing event
    # ------------------------------------------------------------------

    def observe(
        self,
        room: str,
        tile_type: str,
        success: bool,
        confidence: float,
        response_is_echo: bool = False,
    ) -> None:
        """Record one tile-processing observation for *room*.

        Parameters
        ----------
        room:
            Name of the PLATO room being observed.
        tile_type:
            Type of tile that was processed.
        success:
            True if the room produced a useful, non-empty response tile.
        confidence:
            Confidence score of the response tile (0.0–1.0).
        response_is_echo:
            True if the response appeared to mirror the input without
            transformation (triggers stage-2 signal).
        """
        with self._lock:
            key = (room, tile_type)
            if key not in self._records:
                self._records[key] = RoomBehaviorRecord(room=room, tile_type=tile_type)
            rec = self._records[key]
            # Echo responses are never counted as success regardless of flag
            effective_success = success and not response_is_echo
            rec.update(effective_success, confidence)

    # ------------------------------------------------------------------
    # Query path
    # ------------------------------------------------------------------

    def classify_room(self, room: str) -> int:
        """Return the emergent stage (0–4) for *room* across all tile types.

        Returns 0 if the room has fewer than ``min_observations``.

        Algorithm
        ---------
        1. Gather all ``RoomBehaviorRecord`` entries for this room.
        2. Compute weighted-average success_rate (weight = total_attempts).
        3. Compute echo_rate = fraction of tile types where success_rate ≈ 0
           but total_attempts > 0.
        4. Map to stage using thresholds matching the explicit classifier.
        """
        with self._lock:
            room_records = [
                rec for (r, _), rec in self._records.items() if r == room
            ]

        if not room_records:
            return 0

        total_obs = sum(r.total_attempts for r in room_records)
        if total_obs < self.min_observations:
            return 0

        weighted_success = sum(
            r.success_rate * r.total_attempts for r in room_records
        ) / total_obs

        weighted_conf = sum(
            r.avg_confidence * r.total_attempts for r in room_records
        ) / total_obs

        # Echo detection: rooms that "process" tiles but produce near-zero
        # confidence are likely echoing
        low_conf_frac = sum(
            r.total_attempts for r in room_records if r.avg_confidence < 0.1
        ) / total_obs

        if weighted_success >= 0.80 and weighted_conf >= 0.70:
            return 4
        elif weighted_success < 0.05:
            return 1
        elif low_conf_frac > 0.60 and weighted_success < 0.15:
            return 2  # Echo pattern
        else:
            return 3

    def classify_room_for_type(self, room: str, tile_type: str) -> int:
        """Stage for a specific (room, tile_type) pair.

        More fine-grained than ``classify_room`` — useful when a room is a
        specialist (stage 4 for 'math' but stage 2 for 'deploy').
        """
        with self._lock:
            rec = self._records.get((room, tile_type))

        if rec is None or rec.total_attempts < self.min_observations:
            return 0

        if rec.success_rate >= 0.80 and rec.avg_confidence >= 0.70:
            return 4
        elif rec.success_rate < 0.05:
            return 1
        elif rec.avg_confidence < 0.1 and rec.success_rate < 0.15:
            return 2
        else:
            return 3

    def get_high_confidence_rooms(
        self, tile_type: str, min_stage: int = 3
    ) -> List[Tuple[str, float]]:
        """Return ``(room, confidence)`` pairs capable of handling *tile_type*.

        Sorted by average confidence descending.  Used by ``HebbianRouter``
        to prefer proven rooms when routing habituated tile types.
        """
        with self._lock:
            candidates = [
                (rec.room, rec.avg_confidence)
                for (r, t), rec in self._records.items()
                if t == tile_type and self.classify_room_for_type(r, t) >= min_stage
            ]
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates

    def export_stages(self) -> Dict[str, int]:
        """Return ``{room: stage}`` mapping for all observed rooms."""
        rooms = {r for (r, _) in self._records}
        return {room: self.classify_room(room) for room in rooms}


# ===========================================================================
# 4. CUDAHebbianKernel
# ===========================================================================

# Inline PTX source for the Hebbian weight update kernel.
# Formula: w_new[i,j] = w[i,j] + lr * pre[i] * post[j] - decay * w[i,j]
#        = w[i,j] * (1 - decay) + lr * pre[i] * post[j]
#
# Grid: 1D, one thread per (i,j) pair where i < N, j < N
# Shared: none — each thread handles one weight independently (coalesced reads)
_PTX_HEBBIAN = r"""
.version 7.0
.target sm_80
.address_size 64

.visible .entry hebbian_update(
    .param .u64 param_w,      // float* weights [N*N]
    .param .u64 param_pre,    // float* pre_activations [N]
    .param .u64 param_post,   // float* post_activations [N]
    .param .u32 param_n,      // int    N (number of rooms)
    .param .f32 param_lr,     // float  learning_rate
    .param .f32 param_decay   // float  weight_decay
)
{
    .reg .u64   %pw, %ppre, %ppost;
    .reg .u32   %n, %tid, %stride, %i, %j, %idx;
    .reg .f32   %lr, %decay, %wi, %pj, %qi, %delta, %wij;
    .reg .pred  %p0;

    ld.param.u64    %pw,    [param_w];
    ld.param.u64    %ppre,  [param_pre];
    ld.param.u64    %ppost, [param_post];
    ld.param.u32    %n,     [param_n];
    ld.param.f32    %lr,    [param_lr];
    ld.param.f32    %decay, [param_decay];

    // Global thread index
    mov.u32         %tid,    %ctaid.x;
    mul.lo.u32      %tid,    %tid, %ntid.x;
    add.u32         %tid,    %tid, %tid.x;

    // Bounds check: tid must be < N*N
    mul.lo.u32      %idx, %n, %n;
    setp.ge.u32     %p0, %tid, %idx;
    @%p0 bra        done;

    // Compute i = tid / N,  j = tid % N
    div.u32         %i, %tid, %n;
    rem.u32         %j, %tid, %n;

    // Load pre[i] and post[j]
    mul.wide.u32    %pw,    %i, 4;         // byte offset for pre[i]
    add.u64         %pw,    %ppre, %pw;
    ld.global.f32   %wi,    [%pw];

    mul.wide.u32    %pw,    %j, 4;         // byte offset for post[j]
    add.u64         %pw,    %ppost, %pw;
    ld.global.f32   %pj,    [%pw];

    // Load w[tid]
    mul.wide.u32    %pw,    %tid, 4;
    add.u64         %pw,    param_w, %pw;  // reuse %pw as weight ptr
    ld.global.f32   %wij,   [%pw];

    // delta = lr * pre[i] * post[j] - decay * w[i,j]
    mul.f32         %delta, %wi,   %pj;
    mul.f32         %delta, %delta, %lr;
    mul.f32         %qi,    %wij,  %decay;
    sub.f32         %delta, %delta, %qi;

    // w[i,j] += delta
    add.f32         %wij,   %wij,  %delta;
    st.global.f32   [%pw],  %wij;

done:
    ret;
}
"""


class CUDAHebbianKernel:
    """CUDA/PTX implementation of the Hebbian weight update.

    Provides two backends, selected automatically:

    - **cupy** (preferred): loads the PTX source via ``cp.RawModule``.
    - **numpy fallback**: pure-Python vectorised fallback for systems
      without a GPU.  ~100× slower but API-identical.

    Parameters
    ----------
    n_rooms:
        Number of rooms.  The weight matrix is ``[n_rooms × n_rooms]``.
    learning_rate:
        Hebbian η.
    decay:
        Weight decay λ — prevents runaway growth.
    dtype:
        NumPy/CuPy dtype for the weight matrix (default ``float32``).
    """

    def __init__(
        self,
        n_rooms: int,
        learning_rate: float = DEFAULT_LR,
        decay: float = DEFAULT_DECAY,
        dtype: Any = np.float32,
    ) -> None:
        self.n = n_rooms
        self.lr = learning_rate
        self.decay = decay
        self.dtype = dtype
        self._backend = "cupy" if _HAS_CUPY else "numpy"

        if _HAS_CUPY:
            self._weights = cp.zeros((n_rooms, n_rooms), dtype=dtype)
            self._module = cp.RawModule(code=_PTX_HEBBIAN, backend="ptx")
            self._kernel_fn = self._module.get_function("hebbian_update")
        else:
            self._weights = np.zeros((n_rooms, n_rooms), dtype=dtype)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def update(
        self,
        pre_activations: np.ndarray,
        post_activations: np.ndarray,
    ) -> None:
        """Apply one Hebbian update step.

        Parameters
        ----------
        pre_activations:
            Float32 array of shape ``(n_rooms,)`` — activation level of each
            room *before* the tile was processed.  Typically the number of
            tiles emitted in the last window, normalised to ``[0, 1]``.
        post_activations:
            Float32 array of shape ``(n_rooms,)`` — activation level *after*
            processing.  High value = room was engaged by this tile.

        Notes
        -----
        On an A100 with n_rooms=1141, each update touches a 1141×1141
        float32 matrix (~5 MB).  At 125K updates/sec the bandwidth is ~600 GB/s
        — well within A100 HBM2e limits if batched correctly.
        """
        pre = np.asarray(pre_activations, dtype=self.dtype)
        post = np.asarray(post_activations, dtype=self.dtype)

        if self._backend == "cupy":
            self._update_cuda(pre, post)
        else:
            self._update_numpy(pre, post)

    def _update_cuda(self, pre: np.ndarray, post: np.ndarray) -> None:
        """Run the PTX kernel via cupy."""
        pre_gpu = cp.asarray(pre)
        post_gpu = cp.asarray(post)
        n = np.int32(self.n)
        total_elements = self.n * self.n
        threads_per_block = 256
        blocks = math.ceil(total_elements / threads_per_block)
        self._kernel_fn(
            (blocks,),
            (threads_per_block,),
            (
                self._weights,
                pre_gpu,
                post_gpu,
                n,
                np.float32(self.lr),
                np.float32(self.decay),
            ),
        )

    def _update_numpy(self, pre: np.ndarray, post: np.ndarray) -> None:
        """Vectorised NumPy fallback.  Identical semantics to the PTX kernel."""
        # outer product: delta[i,j] = lr * pre[i] * post[j]
        delta = self.lr * np.outer(pre, post)
        self._weights += delta - self.decay * self._weights

    def get_weights(self) -> np.ndarray:
        """Return the current weight matrix as a host-side NumPy array."""
        if self._backend == "cupy":
            return cp.asnumpy(self._weights)
        return self._weights.copy()

    def set_weights(self, w: np.ndarray) -> None:
        """Overwrite the weight matrix (e.g., from a persisted snapshot)."""
        if self._backend == "cupy":
            self._weights = cp.asarray(w.astype(self.dtype))
        else:
            self._weights = w.astype(self.dtype)

    def get_top_connections(self, n: int = 20) -> List[Tuple[int, int, float]]:
        """Return the top-*n* ``(i, j, weight)`` triples by absolute weight."""
        w = self.get_weights()
        flat = np.abs(w).ravel()
        indices = np.argpartition(flat, -n)[-n:]
        indices = indices[np.argsort(flat[indices])[::-1]]
        result = []
        for idx in indices:
            i, j = divmod(int(idx), self.n)
            result.append((i, j, float(w[i, j])))
        return result

    def save(self, path: str) -> None:
        """Persist weight matrix to an .npy file."""
        np.save(path, self.get_weights())

    def load(self, path: str) -> None:
        """Load weight matrix from an .npy file."""
        self.set_weights(np.load(path))

    @property
    def backend(self) -> str:
        """``'cupy'`` or ``'numpy'``."""
        return self._backend


# ===========================================================================
# 5. RoomClusterDetector
# ===========================================================================

@dataclass
class RoomCluster:
    """A self-organised group of rooms specialising in related tile types."""
    cluster_id: int
    rooms: List[str]
    dominant_tile_types: List[str]   # tile types this cluster is good at
    avg_internal_strength: float     # mean strength of intra-cluster edges
    avg_external_strength: float     # mean strength of inter-cluster edges
    stage_distribution: Dict[int, int] = field(default_factory=dict)


class RoomClusterDetector:
    """Detect self-organised room clusters from Hebbian connection strengths.

    Uses the Louvain community detection algorithm (via ``python-louvain`` if
    available, otherwise a greedy connected-components fallback).

    Clusters are groups of rooms that have developed strong mutual connections
    — they represent emergent specialist modules.

    Parameters
    ----------
    tracker:
        :class:`TileFlowTracker` providing live edge weights.
    stage_classifier:
        :class:`EmergentStageClassifier` for annotating cluster stage.
    min_strength:
        Edges below this weight are excluded from the cluster graph.
    min_cluster_size:
        Clusters smaller than this are merged into an 'unclustered' group.
    """

    def __init__(
        self,
        tracker: TileFlowTracker,
        stage_classifier: Optional[EmergentStageClassifier] = None,
        min_strength: float = 0.2,
        min_cluster_size: int = 2,
    ) -> None:
        if not _HAS_NX:
            raise ImportError(
                "networkx is required for RoomClusterDetector: pip install networkx"
            )
        self.tracker = tracker
        self.stage_classifier = stage_classifier
        self.min_strength = min_strength
        self.min_cluster_size = min_cluster_size
        self._last_clusters: List[RoomCluster] = []

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------

    def _build_graph(self) -> "nx.Graph":
        """Build a weighted undirected graph from current flow records."""
        G = nx.Graph()
        with self.tracker._lock:
            if not self.tracker._cache_valid:
                self.tracker._rebuild_caches()
            for (a, b), s in self.tracker._strength_cache.items():
                if s >= self.min_strength:
                    G.add_edge(a, b, weight=s)
        return G

    # ------------------------------------------------------------------
    # Cluster detection
    # ------------------------------------------------------------------

    def detect_clusters(self) -> List[RoomCluster]:
        """Run community detection and return the current cluster list.

        Uses Louvain if ``python-louvain`` (``community`` package) is
        installed, otherwise falls back to connected components.  In both
        cases the result is stable across calls with the same graph state.

        Returns
        -------
        List[RoomCluster]
            Sorted by cluster size descending.
        """
        G = self._build_graph()
        if G.number_of_nodes() == 0:
            self._last_clusters = []
            return []

        # Attempt Louvain (best modularity)
        partition: Dict[str, int]
        try:
            import community as community_louvain  # type: ignore[import]
            partition = community_louvain.best_partition(G, weight="weight")
        except ImportError:
            # Fallback: greedy modularity via networkx
            try:
                communities = nx.algorithms.community.greedy_modularity_communities(G, weight="weight")
                partition = {}
                for cid, comm in enumerate(communities):
                    for node in comm:
                        partition[node] = cid
            except Exception:
                # Final fallback: connected components
                partition = {}
                for cid, comp in enumerate(nx.connected_components(G)):
                    for node in comp:
                        partition[node] = cid

        # Group by cluster_id
        cluster_rooms: Dict[int, List[str]] = defaultdict(list)
        for room, cid in partition.items():
            cluster_rooms[cid].append(room)

        # Build RoomCluster objects
        clusters: List[RoomCluster] = []
        for cid, rooms in cluster_rooms.items():
            if len(rooms) < self.min_cluster_size:
                continue

            # Intra-cluster edge strengths
            intra: List[float] = []
            for i, ra in enumerate(rooms):
                for rb in rooms[i + 1:]:
                    s = self.tracker.get_connection_strength(ra, rb)
                    if s > 0:
                        intra.append(s)
            avg_internal = float(np.mean(intra)) if intra else 0.0

            # Inter-cluster edge strengths (sample up to 50 edges)
            other_rooms = [r for r, c in partition.items() if c != cid]
            inter_sample = [
                self.tracker.get_connection_strength(ra, rb)
                for ra in rooms[:5]
                for rb in other_rooms[:10]
            ]
            avg_external = float(np.mean(inter_sample)) if inter_sample else 0.0

            # Dominant tile types: find which types flow most within cluster
            dominant = self._dominant_tile_types(rooms)

            # Stage distribution
            stage_dist: Dict[int, int] = defaultdict(int)
            if self.stage_classifier:
                for room in rooms:
                    s = self.stage_classifier.classify_room(room)
                    stage_dist[s] += 1

            clusters.append(RoomCluster(
                cluster_id=cid,
                rooms=sorted(rooms),
                dominant_tile_types=dominant,
                avg_internal_strength=avg_internal,
                avg_external_strength=avg_external,
                stage_distribution=dict(stage_dist),
            ))

        # Sort by cluster size descending
        clusters.sort(key=lambda c: len(c.rooms), reverse=True)
        # Reassign sequential IDs after sort
        for i, c in enumerate(clusters):
            c.cluster_id = i

        self._last_clusters = clusters
        return clusters

    def _dominant_tile_types(self, rooms: List[str]) -> List[str]:
        """Find tile types that flow most between rooms in *rooms*."""
        type_counts: Dict[str, float] = defaultdict(float)
        room_set = set(rooms)
        for rec in self.tracker.iter_recent(5000):
            if rec.source_room in room_set and rec.dest_room in room_set:
                type_counts[rec.tile_type] += 1.0
        if not type_counts:
            return []
        total = sum(type_counts.values())
        sorted_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)
        # Return types accounting for > 10% of intra-cluster flow
        return [t for t, c in sorted_types if c / total > 0.10][:5]

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def get_cluster_for_task(self, task_type: str) -> Optional[RoomCluster]:
        """Return the cluster best suited for *task_type*.

        Uses the dominant tile types of each cluster.  If no cluster has
        *task_type* as dominant, returns the cluster with the highest average
        internal strength (the most cohesive specialist group).

        Parameters
        ----------
        task_type:
            A tile type string, e.g. ``"math"``, ``"deploy"``, ``"data"``.
        """
        if not self._last_clusters:
            self.detect_clusters()

        # Exact match on dominant tile types first
        for cluster in self._last_clusters:
            if task_type in cluster.dominant_tile_types:
                return cluster

        # Fuzzy: cluster whose rooms' names suggest the task type
        for cluster in self._last_clusters:
            if any(task_type in room.lower() for room in cluster.rooms):
                return cluster

        # Default: most cohesive cluster
        return max(
            self._last_clusters,
            key=lambda c: c.avg_internal_strength,
            default=None,
        )

    def get_specialist_rooms(
        self, tile_type: str, min_stage: int = 3
    ) -> List[str]:
        """Return rooms from the matching cluster that have high stage.

        Combines cluster membership (structural) with stage classification
        (behavioural) to produce the strongest routing recommendation.
        """
        cluster = self.get_cluster_for_task(tile_type)
        if cluster is None:
            return []

        if self.stage_classifier is None:
            return cluster.rooms[:5]

        return [
            room for room in cluster.rooms
            if self.stage_classifier.classify_room(room) >= min_stage
        ][:5]

    def visualize_cluster_graph(
        self,
        output_path: str = "cluster_graph.json",
        include_weights: bool = True,
    ) -> Dict[str, Any]:
        """Export the cluster graph as a D3-compatible JSON structure.

        Returns a dict with ``nodes`` and ``links`` arrays suitable for
        rendering with D3.js force-directed graphs or Graphviz.

        Parameters
        ----------
        output_path:
            If given, the JSON is written to this path.
        include_weights:
            Include edge weights in the output.
        """
        G = self._build_graph()
        if not self._last_clusters:
            self.detect_clusters()

        # Build room → cluster_id mapping
        room_to_cluster: Dict[str, int] = {}
        for cluster in self._last_clusters:
            for room in cluster.rooms:
                room_to_cluster[room] = cluster.cluster_id

        nodes = [
            {
                "id": room,
                "cluster": room_to_cluster.get(room, -1),
                "stage": (
                    self.stage_classifier.classify_room(room)
                    if self.stage_classifier else 0
                ),
            }
            for room in G.nodes()
        ]

        links = [
            {
                "source": u,
                "target": v,
                "weight": float(d["weight"]) if include_weights else 1.0,
            }
            for u, v, d in G.edges(data=True)
        ]

        graph_data = {"nodes": nodes, "links": links}
        if output_path:
            with open(output_path, "w") as fh:
                json.dump(graph_data, fh, indent=2)

        return graph_data

    @property
    def clusters(self) -> List[RoomCluster]:
        """The most recently computed cluster list (may be stale)."""
        return self._last_clusters


# ===========================================================================
# Integration helper — HebbianLayer orchestrates all five modules
# ===========================================================================

class HebbianLayer:
    """Top-level orchestrator for the Hebbian enhancement layer.

    Wires together the five modules and provides the one-call integration
    point for the PLATO tile-processing loop.

    Example
    -------
    ::

        layer = HebbianLayer.from_plato(base_url=PLATO_BASE)
        rooms = layer.route_tile(tile_type="data", tile_hash=tile._hash,
                                  source_room="room-42")
        for room in rooms:
            layer.dispatch_tile(tile, room)

    Parameters
    ----------
    all_rooms:
        Full room list from the PLATO server.
    n_cuda_rooms:
        Number of rooms tracked by the CUDA kernel weight matrix.
        Default: ``len(all_rooms)``.
    persist_dir:
        Directory for persisting tracker state and CUDA weights between runs.
    """

    def __init__(
        self,
        all_rooms: List[str],
        n_cuda_rooms: Optional[int] = None,
        persist_dir: Optional[str] = None,
        explicit_router: Optional[Any] = None,
    ) -> None:
        n = n_cuda_rooms or len(all_rooms)
        tracker_persist = (
            os.path.join(persist_dir, "flow_tracker.json") if persist_dir else None
        )
        cuda_persist = (
            os.path.join(persist_dir, "hebbian_weights.npy") if persist_dir else None
        )

        self.tracker = TileFlowTracker(persist_path=tracker_persist)
        self.router = HebbianRouter(
            tracker=self.tracker,
            all_rooms=all_rooms,
            explicit_router=explicit_router,
        )
        self.stage_classifier = EmergentStageClassifier()
        self.cuda_kernel = CUDAHebbianKernel(n_rooms=n)
        self.cluster_detector = RoomClusterDetector(
            tracker=self.tracker,
            stage_classifier=self.stage_classifier,
        )

        if cuda_persist and os.path.exists(cuda_persist):
            self.cuda_kernel.load(cuda_persist)

        self._room_index: Dict[str, int] = {r: i for i, r in enumerate(all_rooms)}
        self._persist_dir = persist_dir

    @classmethod
    def from_plato(
        cls,
        base_url: str = PLATO_BASE,
        persist_dir: Optional[str] = None,
        explicit_router: Optional[Any] = None,
    ) -> "HebbianLayer":
        """Construct a HebbianLayer by fetching the current room list from PLATO."""
        resp = requests.get(f"{base_url}/rooms", timeout=15)
        resp.raise_for_status()
        data = resp.json()
        rooms: List[str] = data if isinstance(data, list) else data.get("rooms", [])
        return cls(all_rooms=rooms, persist_dir=persist_dir, explicit_router=explicit_router)

    def route_tile(
        self,
        tile_type: str,
        tile_hash: str,
        source_room: str,
        tags: Optional[List[str]] = None,
    ) -> List[str]:
        """Main entry point — returns the list of rooms to route this tile to."""
        return self.router.route(tile_type, tile_hash, source_room, tags)

    def record_outcome(
        self,
        source_room: str,
        dest_room: str,
        tile_type: str,
        tile_hash: str,
        success: bool,
        confidence: float,
        response_is_echo: bool = False,
    ) -> None:
        """Call after each tile-processing event to train all modules."""
        self.router.record_outcome(source_room, dest_room, tile_type, tile_hash, success)
        self.stage_classifier.observe(
            dest_room, tile_type, success, confidence, response_is_echo
        )
        # Update CUDA kernel if rooms are indexed
        src_idx = self._room_index.get(source_room)
        dst_idx = self._room_index.get(dest_room)
        if src_idx is not None and dst_idx is not None:
            n = len(self._room_index)
            pre = np.zeros(n, dtype=np.float32)
            post = np.zeros(n, dtype=np.float32)
            pre[src_idx] = 1.0
            post[dst_idx] = float(confidence) if success else 0.0
            self.cuda_kernel.update(pre, post)

    def save(self) -> None:
        """Persist all state to ``persist_dir``."""
        if not self._persist_dir:
            return
        os.makedirs(self._persist_dir, exist_ok=True)
        self.tracker.snapshot()
        self.cuda_kernel.save(os.path.join(self._persist_dir, "hebbian_weights.npy"))
