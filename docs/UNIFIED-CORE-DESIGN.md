# Unified Constraint-Theory-Core Design

## Document Status

**Version:** 0.1.0-draft  
**Date:** 2026-05-22  
**Scope:** Architectural blueprint for the consolidation of 10+ scattered constraint-theory packages into a single Python package.  
**Horizon:** 6 months (target release: v1.0.0 by 2026-11-22)

---

## 1. Executive Summary

Today our constraint-theory concepts are fragmented across **10+ packages** with overlapping concerns, incompatible naming, and duplicated constants. This document defines **constraint-theory-core** — one package, one namespace, one source of truth.

### Packages Being Unified

| Legacy Package | Key Concepts | New Home |
|---|---|---|
| `constraint-theory-py` | eisenstein, temporal, adaptive, baton, plato | `constraint_theory_core.*` |
| `deadband-python` | div360, deadband, eisenstein_snap, fibonacci_spline, bma, hpdf | `constraint_theory_core.foundation.*`, `constraint_theory_core.temporal.*` |
| `eisenstein-embed` | quantization, bitvector, static_model, cascade | `constraint_theory_core.embed.*` |
| `tensor-spline` | spline interpolation, compression | `constraint_theory_core.spline.*` |
| `swarm-rooms` | eisenstein room hashing, CRDT rooms | `constraint_theory_core.swarm.*` |
| `fleet-math-c` | C implementations of fleet math | `constraint_theory_core.ffi.c_math` |
| `holonomy-consensus` (Rust) | consensus, encoding, constraints | `constraint_theory_core.consensus.*`, `constraint_theory_core.ffi.rust_consensus` |

### Design Principles

1. **Zero-deps core.** Everything in `foundation`, `temporal`, `adaptive`, `encode`, `plato`, `baton`, `theorems` is pure Python + stdlib.
2. **Graduated power.** Optional extras bring `numpy` (embed), `torch` (spline, swarm), `cffi` (C FFI), `maturin` (Rust FFI).
3. **Theorem namespace.** Every named bound (`covering_radius`, `laman_bound`, etc.) lives in `theorems` and is importable by name.
4. **Back-compat shim.** Old import paths continue to work via thin `compat.*` re-export modules.
5. **Type safety.** Full type signatures on every public symbol; docstrings on every class and function.

---

## 2. Package Structure

```text
constraint_theory_core/
│
├── __init__.py              # Convenience re-exports (opt-in)
├── _version.py              # __version__ = "1.0.0"
├── _types.py                # Shared type aliases and protocols
│
│   # === FOUNDATION (zero deps) ===
├── foundation/
│   ├── __init__.py
│   ├── lattice.py           # A2Point, Dodecet, snap, norm, rotation, neighbours
│   ├── chamber.py           # Chamber, classify_chamber, chamber_barycentric
│   ├── constants.py         # COVERING_RADIUS, SAFE_THRESHOLD, SQRT_3, OMEGA_*, LAMAN_COEFFICIENT
│   ├── deadband.py          # Perceptual deadband primitives
│   ├── modular.py           # div360_add, div360_sub, div360_mul
│   ├── shells.py            # shell_decompose, shell_count
│   └── fibonacci.py         # fib_spline_search, fibonacci_index
│
│   # === TEMPORAL (zero deps) ===
├── temporal/
│   ├── __init__.py
│   ├── funnel.py            # deadband_funnel, FunnelPhase
│   ├── agent.py             # TemporalAgent, SnapResult, TemporalUpdate, AgentSummary
│   ├── dodecet_codec.py     # encode_dodecet, decode_dodecet
│   └── bma.py               # bma_detect, bma_anomaly_score
│
│   # === ADAPTIVE (zero deps) ===
├── adaptive/
│   ├── __init__.py
│   ├── tolerance.py         # adaptive_epsilon, AdaptiveTolerance
│   └── manifold.py          # ManifoldRegion, classify_region, curvature_from_manifold
│
│   # === ENCODE (zero deps) ===
├── encode/
│   ├── __init__.py
│   ├── dodecet.py           # Dodecet (class), encode, decode, encode_from_fields
│   └── pythagorean.py       # Pythagorean48, Vector48
│
│   # === PLATO (zero deps) ===
├── plato/
│   ├── __init__.py
│   ├── tile.py              # PlatoTile, TileState, TilePriority
│   ├── store.py             # PlatoTileStore
│   └── scoring.py           # score_tiles, composite_score
│
│   # === BATON (zero deps) ===
├── baton/
│   ├── __init__.py
│   ├── shard.py             # BatonShard
│   ├── context.py           # split_context, merge_shards, diff_shards
│   └── validate.py          # validate_shard
│
│   # === EMBED (optional: numpy) ===
├── embed/
│   ├── __init__.py
│   ├── model.py             # EisensteinModel, MatchResult
│   ├── cascade.py           # CascadeMatcher
│   ├── bitvector.py         # word_fingerprint, text_fingerprint, hamming_distance, bitvector_similarity
│   ├── quantize.py          # SplineLinearQuantizer
│   ├── cache.py             # DeadbandCache
│   ├── domain.py            # DomainSIF
│   └── monitor.py           # BMAMonitor
│
│   # === SPLINE (optional: torch) ===
├── spline/
│   ├── __init__.py
│   ├── lattice.py           # EisensteinLattice (torch)
│   ├── linear.py            # SplineLinear
│   ├── low_rank.py          # LowRankLinear, LowRankClassifier
│   ├── hierarchical.py      # HierarchicalSplineLinear
│   └── inject.py            # inject_spline, inject_low_rank, inject_hierarchical_spline, recommend_variant
│
│   # === SWARM (optional: torch) ===
├── swarm/
│   ├── __init__.py
│   ├── state.py             # RoomState
│   ├── network.py           # SwarmRoomNetwork
│   └── snap.py              # eisenstein_snap (numpy), eisenstein_delta, eisenstein_snap_gpu, eisenstein_delta_gpu
│
│   # === CONSENSUS (optional: Rust extension) ===
├── consensus/
│   ├── __init__.py
│   ├── holonomy.py          # HolonomyConsensus, ConsensusResult
│   ├── constraints.py       # ConstraintResult, HolonomyBounds, sat8
│   ├── cohomology.py        # EmergenceDetector, EmergenceResult
│   ├── encoding.py          # Vector48, encode_angle, decode_angle
│   ├── lifecycle.py         # LamportClock, TrustState, RetractionReason
│   └── trust.py             # TrustPool, TrustTile, LifecycleError
│
│   # === FFI (optional: compiled) ===
├── ffi/
│   ├── __init__.py
│   ├── c_math.py            # cffi bridge to fleet-math-c
│   └── rust_consensus.py    # PyO3/maturin bridge to holonomy-consensus
│
│   # === THEOREMS (zero deps) ===
├── theorems.py              # Named theorem constants and doc references
│
│   # === COMPAT (zero deps) ===
├── compat/
│   ├── __init__.py
│   ├── constraint_theory.py # Re-exports: from constraint_theory import X
│   ├── deadband_python.py   # Re-exports: from deadband_python import X
│   ├── eisenstein_embed.py  # Re-exports: from eisenstein_embed import X
│   ├── tensor_spline.py     # Re-exports: from tensor_spline import X
│   ├── swarm_rooms.py       # Re-exports: from swarm_rooms import X
│   ├── fleet_agent.py       # Re-exports: from fleet_agent.holonomy_stubs import X
│   └── holonomy_consensus.py# Re-exports: from holonomy_consensus import X
│
│   # === TESTS ===
├── tests/
│   ├── __init__.py
│   ├── test_foundation.py
│   ├── test_temporal.py
│   ├── test_adaptive.py
│   ├── test_encode.py
│   ├── test_plato.py
│   ├── test_baton.py
│   ├── test_embed.py
│   ├── test_spline.py
│   ├── test_swarm.py
│   ├── test_consensus.py
│   └── test_theorems.py
│
pyproject.toml
Cargo.toml                    # For maturin Rust extension
build.py                      # cffi C-extension builder
README.md
UNIFIED-CORE-DESIGN.md        # This document
```

---

## 3. Public API

### 3.1 Foundation

#### `constraint_theory_core.foundation.lattice`

```python
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import IntEnum
from typing import Iterable, List, Tuple, Union

SQRT_3: float = math.sqrt(3.0)
OMEGA_RE: float = -0.5
OMEGA_IM: float = SQRT_3 / 2.0
COVERING_RADIUS: float = 1.0 / SQRT_3
SAFE_THRESHOLD: float = COVERING_RADIUS / 2.0


@dataclass(frozen=True)
class A2Point:
    """Eisenstein integer a + bω where a, b ∈ ℤ.

    Attributes
    ----------
    a: int
        Coefficient of the basis vector 1.
    b: int
        Coefficient of the basis vector ω = e^(2πi/3).
    """

    a: int
    b: int

    def to_cartesian(self) -> Tuple[float, float]:
        """Return (x, y) coordinates in the complex plane."""
        ...

    @classmethod
    def from_cartesian(cls, x: float, y: float) -> A2Point:
        """Snap a cartesian point to the nearest A₂ lattice point."""
        ...

    def __add__(self, other: A2Point) -> A2Point: ...
    def __sub__(self, other: A2Point) -> A2Point: ...
    def __neg__(self) -> A2Point: ...
    def __mul__(self, scalar: int) -> A2Point: ...
    def __rmul__(self, scalar: int) -> A2Point: ...
    def __eq__(self, other: object) -> bool: ...
    def __hash__(self) -> int: ...


@dataclass(frozen=True)
class Dodecet:
    """12-bit Eisenstein lattice encoding.

    Bit layout::
        bits 11-8 : error level   (0-15)
        bits  7-4 : angle level   (0-15)
        bits  3   : safety flag   (0 = safe, 1 = critical)
        bits  2-0 : chamber index (0-5)
    """

    raw: int

    @property
    def error_level(self) -> int: ...
    @property
    def angle_level(self) -> int: ...
    @property
    def chamber(self) -> int: ...
    @property
    def is_safe(self) -> bool: ...
    @property
    def is_critical(self) -> bool: ...

    @classmethod
    def from_fields(
        cls,
        error_level: int,
        angle_level: int,
        chamber: int,
        is_safe: bool = True,
    ) -> Dodecet:
        """Build a Dodecet from explicit field values."""
        ...

    @classmethod
    def from_point(cls, x: float, y: float) -> Dodecet:
        """Snap a 2-D point and encode as a Dodecet."""
        ...


class Chamber(IntEnum):
    """The six Weyl chambers of the A₂ lattice."""

    CHAMBER_0 = 0
    CHAMBER_1 = 1
    CHAMBER_2 = 2
    CHAMBER_3 = 3
    CHAMBER_4 = 4
    CHAMBER_5 = 5

    @property
    def parity(self) -> int:
        """+1 for even chambers (0, 2, 5), -1 for odd (1, 3, 4)."""
        ...


def snap(x: float, y: float) -> A2Point:
    """Snap a 2-D point to the nearest A₂ lattice point.

    Uses a 9-candidate Voronoi search guaranteed to find the nearest lattice
    point (covering radius = 1/√3 ≈ 0.577).
    """
    ...


def snap_with_error(x: float, y: float) -> Tuple[A2Point, float]:
    """Snap and return the Euclidean error."""
    ...


def snap_with_metadata(
    x: float, y: float
) -> Tuple[A2Point, float, int, int, bool]:
    """Snap with full metadata: (point, error, chamber, error_level, is_safe)."""
    ...


def snap_batch(
    points: Iterable[Tuple[float, float]]
) -> List[Tuple[A2Point, float]]:
    """Snap multiple points at once."""
    ...


def norm_sq(a: int, b: int) -> int:
    """Squared A₂ norm: a² + ab + b²."""
    ...


def norm(a: int, b: int) -> float:
    """Euclidean norm: √(a² + ab + b²)."""
    ...


def distance_sq(a1: int, b1: int, a2: int, b2: int) -> int:
    """Squared distance between two Eisenstein integers."""
    ...


def distance(a1: int, b1: int, a2: int, b2: int) -> float:
    """Euclidean distance between two Eisenstein integers."""
    ...


def rotation(a: int, b: int, k: int = 1) -> A2Point:
    """Rotate (a, b) by k·60° counter-clockwise on the hex lattice."""
    ...


def nearest_neighbors(a: int, b: int) -> List[A2Point]:
    """Return the 6 nearest neighbours of an Eisenstein integer."""
    ...


def lattice_points_within(radius: float) -> List[A2Point]:
    """Generate all A₂ lattice points within *radius* of the origin."""
    ...


def voronoi_cell_area() -> float:
    """Area of the A₂ fundamental parallelogram: √3/2."""
    ...


def error_cdf(error: float) -> float:
    """Fraction of the Voronoi cell with distance < *error* from a lattice point."""
    ...


def voronoi_radius() -> float:
    """Inner radius of the Voronoi cell (same as covering radius for A₂)."""
    ...
```

#### `constraint_theory_core.foundation.chamber`

```python
def classify_chamber(x: float, y: float) -> int:
    """Classify a point into one of the 6 Weyl chambers (0-5)."""
    ...


def chamber_barycentric(x: float, y: float) -> Tuple[float, float, float]:
    """Compute barycentric coordinates (b1, b2, b3) with respect to the A₂ roots.

    b1 + b2 + b3 = 0 by construction.
    """
    ...
```

#### `constraint_theory_core.foundation.deadband`

```python
def deadband_perceivable(value: float, threshold: float) -> bool:
    """Return True if |value| >= threshold (signal exceeds perceptual deadband)."""
    ...


def deadband_min_bits(bits: int) -> int:
    """Return minimum bits for deadband representation (≥ 1)."""
    ...
```

#### `constraint_theory_core.foundation.modular`

```python
def div360_add(a: int, b: int) -> int:
    """Modular addition on ℤ/360ℤ."""
    ...


def div360_sub(a: int, b: int) -> int:
    """Modular subtraction on ℤ/360ℤ."""
    ...


def div360_mul(a: int, b: int) -> int:
    """Modular multiplication on ℤ/360ℤ."""
    ...
```

#### `constraint_theory_core.foundation.shells`

```python
def shell_decompose(n: int) -> List[int]:
    """Decompose *n* into concentric Eisenstein shells.

    Shell k (1-indexed) contains 6k lattice points.
    """
    ...


def shell_count(radius: float) -> int:
    """Number of complete shells within *radius* of the origin."""
    ...
```

#### `constraint_theory_core.foundation.fibonacci`

```python
from typing import Sequence, TypeVar

T = TypeVar("T")


def fib_spline_search(values: Sequence[T], target: T) -> int:
    """Fibonacci spline search — find insertion index in a sorted sequence.

    Returns the index of the first element >= target.
    """
    ...


def fibonacci_index(n: int) -> int:
    """Return the smallest k such that Fib(k) >= n."""
    ...
```

---

### 3.2 Temporal

#### `constraint_theory_core.temporal.funnel`

```python
from enum import Enum

class FunnelPhase(Enum):
    APPROACH = "approach"
    NARROWING = "narrowing"
    SNAP_IMMINENT = "snap_imminent"
    CRYSTALLIZED = "crystallized"
    ANOMALY = "anomaly"


class ChiralityState(Enum):
    EXPLORING = "exploring"
    LOCKING = "locking"
    LOCKED = "locked"


class AgentAction(Enum):
    CONTINUE = "continue"
    CONVERGING = "converging"
    HOLD_STEADY = "hold_steady"
    WIDEN_FUNNEL = "widen_funnel"
    COMMIT_CHIRALITY = "commit_chirality"
    DIVERGING = "diverging"
    SATISFIED = "satisfied"


def deadband_funnel(t: float, decay_rate: float = 1.0) -> float:
    """Compute the deadband width at normalised time *t*.

    δ(t) = ρ · (1 - t)^{1 / decay_rate}

    Parameters
    ----------
    t: float
        Normalised time in [0, 1].
    decay_rate: float
        Controls how fast the funnel narrows (default 1.0 = square-root).
    """
    ...
```

#### `constraint_theory_core.temporal.agent`

```python
from dataclasses import dataclass
from typing import List, Optional

from constraint_theory_core.foundation.lattice import A2Point
from constraint_theory_core.temporal.funnel import FunnelPhase, ChiralityState, AgentAction


@dataclass
class SnapResult:
    """Result of snapping a 2-D point to the nearest A₂ lattice point."""

    snap_a: int
    snap_b: int
    error: float
    error_normalized: float
    error_level: int
    angle_level: int
    chamber: int
    parity: int
    is_safe: bool

    @property
    def cdf_below(self) -> float:
        """Fraction of uniformly-random points that have smaller error."""
        ...


@dataclass
class TemporalUpdate:
    """Output produced after each observation in a TemporalAgent."""

    snap: SnapResult
    phase: FunnelPhase
    chirality: ChiralityState
    chirality_chamber: Optional[int]
    predicted_error: float
    prediction_error: float
    convergence_rate: float
    precision_energy: float
    is_anomaly: bool
    action: AgentAction
    deadband_width: float


@dataclass
class AgentSummary:
    """Snapshot of the agent's internal state for reporting."""

    history_count: int
    error_mean: float
    error_std: float
    convergence_rate: float
    precision_energy: float
    prediction_error: float
    temperature: float
    phase: FunnelPhase
    chirality: ChiralityState
    chirality_chamber: Optional[int]
    decay_rate: float
    funnel_width: float
    deadband_width: float


class TemporalAgent:
    """Constraint agent with temporal intelligence.

    Maintains a model of the deadband funnel over time, predicts future
    states, detects anomalies, and recommends actions.

    Parameters
    ----------
    decay_rate: float
        How fast the funnel narrows (default 1.0, range 0.1-10.0).
    prediction_horizon: int
        Steps ahead for prediction (default 8).
    anomaly_sigma: float
        Sigmas for anomaly threshold (default 2.0).
    learning_rate: float
        EMA learning rate for convergence rate (default 0.1).
    chirality_lock_threshold_milli: int
        Confidence (per-mille) to lock chirality (default 500).
    """

    def __init__(
        self,
        decay_rate: float = 1.0,
        prediction_horizon: int = 8,
        anomaly_sigma: float = 2.0,
        learning_rate: float = 0.1,
        chirality_lock_threshold_milli: int = 500,
    ) -> None: ...

    def observe(self, x: float, y: float) -> TemporalUpdate:
        """Read a sensor value and update the temporal model."""
        ...

    @property
    def funnel_width(self) -> float:
        """Current funnel width in [0, 1] (0 = snapped, 1 = wide-open)."""
        ...

    def summary(self) -> AgentSummary:
        """Return a snapshot of the agent's internal state."""
        ...

    @property
    def temperature(self) -> float:
        """Temporal entropy — how much the agent is still exploring."""
        ...


def check_constraint(x: float, y: float, funnel_width: float = 1.0) -> bool:
    """Check whether a point satisfies the A₂ lattice constraint."""
    ...
```

#### `constraint_theory_core.temporal.dodecet_codec`

```python
from constraint_theory_core.temporal.agent import SnapResult

def encode_dodecet(sr: SnapResult) -> int:
    """Pack a SnapResult into a 12-bit dodecet value (0-4095)."""
    ...


def decode_dodecet(dodecet: int) -> tuple[int, int, int, bool]:
    """Unpack a 12-bit dodecet into (error_level, angle_level, chamber, is_safe)."""
    ...
```

#### `constraint_theory_core.temporal.bma`

```python
from typing import Sequence

def bma_detect(signal: Sequence[float], window: int = 7) -> List[float]:
    """Backward moving average change detection.

    Returns the absolute deviation of each point from the moving average
    of the preceding *window* points.
    """
    ...


def bma_anomaly_score(signal: Sequence[float], window: int = 7) -> List[float]:
    """Normalised anomaly scores from BMA deviation (z-score over window)."""
    ...
```

---

### 3.3 Adaptive

#### `constraint_theory_core.adaptive.tolerance`

```python
from typing import Callable, Optional, Sequence

DEFAULT_K: float = 1.0
DEFAULT_EPSILON_MAX: float = 0.5
DEFAULT_EPSILON_MIN: float = 1e-12


def adaptive_epsilon(
    curvature: float,
    k: float = DEFAULT_K,
    epsilon_max: float = DEFAULT_EPSILON_MAX,
    epsilon_min: float = DEFAULT_EPSILON_MIN,
) -> float:
    """Compute ε(c) = min(k / c, ε_max), clamped to [ε_min, ε_max].

    Parameters
    ----------
    curvature: float
        Local curvature of the manifold (c ≥ 0).
    k: float
        Proportionality constant.
    epsilon_max: float
        Maximum allowed epsilon.
    epsilon_min: float
        Minimum epsilon clamp.

    Raises
    ------
    ValueError
        If curvature < 0 or any argument is NaN.
    """
    ...


class AdaptiveTolerance:
    """Composable adaptive tolerance with LRU caching.

    Parameters
    ----------
    k: float
        Proportionality constant (default 1.0).
    epsilon_max: float
        Maximum epsilon (default 0.5).
    epsilon_min: float
        Minimum epsilon (default 1e-12).
    fallback: callable or None
        Fallback epsilon function for unclassified points.
    """

    def __init__(
        self,
        k: float = DEFAULT_K,
        epsilon_max: float = DEFAULT_EPSILON_MAX,
        epsilon_min: float = DEFAULT_EPSILON_MIN,
        fallback: Optional[Callable[[float], float]] = None,
    ) -> None: ...

    def __call__(self, curvature: float) -> float: ...
    def batch(self, curvatures: Sequence[float]) -> List[float]: ...
    def clear_cache(self) -> None: ...
    def cache_stats(self) -> dict[str, int | float]: ...
```

#### `constraint_theory_core.adaptive.manifold`

```python
from enum import Enum

class ManifoldRegion(str, Enum):
    FAR = "far"
    APPROACHING = "approaching"
    NEAR = "near"
    CRITICAL = "critical"
    SINGULAR = "singular"


def classify_region(
    curvature: float,
    far_threshold: float = 0.01,
    near_threshold: float = 1.0,
    critical_threshold: float = 10.0,
) -> ManifoldRegion:
    """Classify a manifold region based on local curvature."""
    ...


def curvature_from_manifold(
    x: float,
    y: float,
    metric: Callable[[float, float], float],
    delta: float = 1e-6,
) -> float:
    """Estimate local curvature from a metric function via finite differences."""
    ...


def manifold_distance(
    x: float,
    y: float,
    boundary_points: Sequence[Tuple[float, float]],
) -> float:
    """Minimum Euclidean distance from (x, y) to any boundary point."""
    ...


def adaptive_snap(
    x: float,
    y: float,
    boundary_points: Sequence[Tuple[float, float]],
    k: float = DEFAULT_K,
) -> Tuple[float, float, bool]:
    """Snap a point with adaptive tolerance based on manifold distance.

    Returns (adapted_epsilon, boundary_distance, is_within_tolerance).
    """
    ...
```

---

### 3.4 Encode

#### `constraint_theory_core.encode.dodecet`

```python
from dataclasses import dataclass
from typing import Tuple, Union

@dataclass(frozen=True)
class Dodecet:
    """12-bit Eisenstein lattice encoding.

    Bit layout::
        bits 11-8 : error level   (0-15)
        bits  7-4 : angle level   (0-15)
        bits  3   : safety flag   (0 = safe, 1 = critical)
        bits  2-0 : chamber index (0-5)
    """

    raw: int

    @property
    def error_level(self) -> int: ...
    @property
    def angle_level(self) -> int: ...
    @property
    def chamber(self) -> int: ...
    @property
    def is_safe(self) -> bool: ...

    @classmethod
    def from_fields(
        cls,
        error_level: int,
        angle_level: int,
        chamber: int,
        is_safe: bool = True,
    ) -> Dodecet: ...

    @classmethod
    def from_point(cls, x: float, y: float) -> Dodecet: ...


def encode(x: float, y: float) -> Dodecet:
    """Snap a point and encode as a 12-bit Dodecet."""
    ...


def encode_from_fields(
    error_level: int,
    angle_level: int,
    chamber: int,
    is_safe: bool = True,
) -> Dodecet:
    """Encode explicit fields into a Dodecet."""
    ...


def decode(dodecet: Union[int, Dodecet]) -> Tuple[int, int, int, bool]:
    """Decode a Dodecet into (error_level, angle_level, chamber, is_safe)."""
    ...


def dodecet_encode(a: int, b: int) -> Dodecet:
    """Encode an Eisenstein integer as a 12-bit dodecet."""
    ...
```

#### `constraint_theory_core.encode.pythagorean`

```python
from dataclasses import dataclass
from typing import Tuple

DIRECTION_COUNT: int = 48


@dataclass(frozen=True)
class Pythagorean48:
    """48 exact directions on the unit circle.

    log2(48) = 5.585 bits — maximum information per bit for 16-bit integers.
    """

    sector: int  # 0-47

    @property
    def angle_rad(self) -> float: ...
    @property
    def angle_deg(self) -> float: ...

    @classmethod
    def from_cartesian(cls, x: float, y: float) -> Pythagorean48:
        """Quantize angle(x, y) into one of 48 sectors."""
        ...

    def to_unit_vector(self) -> Tuple[float, float]:
        """Return approximate (x, y) on the unit circle for this sector."""
        ...


class Vector48:
    """Compact 48-direction vector storage."""

    def __init__(self, sector: int, magnitude: float = 1.0) -> None: ...
    @property
    def sector(self) -> int: ...
    @property
    def magnitude(self) -> float: ...
    def to_cartesian(self) -> Tuple[float, float]: ...
    @classmethod
    def from_cartesian(cls, x: float, y: float) -> Vector48: ...
```

---

### 3.5 PLATO

#### `constraint_theory_core.plato.tile`

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import time

DomainName = str


class TileState(Enum):
    ACTIVE = "active"
    LOCKED = "locked"
    ARCHIVED = "archived"
    PURGED = "purging"


class TilePriority(Enum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class PlatoTile:
    """Atomic unit of knowledge in the PLATO architecture."""

    id: str
    domain: DomainName
    content: Any = None
    relevance: float = 1.0
    recency: float = field(default_factory=time.time)
    reliability: float = 1.0
    priority: TilePriority = TilePriority.MEDIUM
    state: TileState = TileState.ACTIVE
    version: int = 1
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    access_count: int = 0

    def access(self) -> Any: ...
    def update(
        self,
        content: Any,
        relevance: Optional[float] = None,
        reliability: Optional[float] = None,
    ) -> None: ...
    def decay_relevance(self, decay_rate: float = 0.05) -> None: ...
    def score(
        self,
        now: Optional[float] = None,
        weights: Optional[Dict[str, float]] = None,
    ) -> float: ...
    def validate(self, success: bool) -> None: ...
    @property
    def cross_refs(self) -> List[str]: ...
    @cross_refs.setter
    def cross_refs(self, refs: List[str]) -> None: ...
    def to_dict(self) -> Dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PlatoTile: ...
```

#### `constraint_theory_core.plato.store`

```python
from typing import List, Optional

class PlatoTileStore:
    """Lightweight in-memory store for PlatoTile objects."""

    def __init__(
        self,
        decay_rate: float = 0.05,
        score_weights: Optional[Dict[str, float]] = None,
    ) -> None: ...

    def put(self, tile: PlatoTile) -> None: ...
    def get(self, tile_id: str) -> Optional[PlatoTile]: ...
    def delete(self, tile_id: str) -> None: ...
    def query(
        self,
        domain: Optional[str] = None,
        tags: Optional[List[str]] = None,
        min_relevance: float = 0.0,
        state: Optional[TileState] = None,
        limit: int = 100,
    ) -> List[PlatoTile]: ...
    def get_related(self, tile_id: str, max_depth: int = 1) -> List[PlatoTile]: ...
    def size(self) -> int: ...
    def apply_decay_all(self) -> None: ...
```

#### `constraint_theory_core.plato.scoring`

```python
from typing import Sequence, Tuple

def score_tiles(
    tiles: Sequence[PlatoTile],
    now: Optional[float] = None,
    weights: Optional[Dict[str, float]] = None,
) -> List[Tuple[PlatoTile, float]]:
    """Compute composite scores for multiple tiles."""
    ...


def composite_score(
    relevance: float,
    recency: float,
    reliability: float,
    priority: int,
    weights: Optional[Dict[str, float]] = None,
) -> float:
    """Low-level composite score from raw components."""
    ...
```

---

### 3.6 Baton

#### `constraint_theory_core.baton.shard`

```python
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

Artifacts = Dict[str, Any]
Reasoning = List[Any]
Blockers = List[str]

ARTIFACTS_KEY: str = "artifacts"
REASONING_KEY: str = "reasoning"
BLOCKERS_KEY: str = "blockers"


@dataclass
class BatonShard:
    """Three-way baton context split: artifacts, reasoning, blockers."""

    artifacts: Artifacts = field(default_factory=dict)
    reasoning: Reasoning = field(default_factory=list)
    blockers: Blockers = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_artifact(self, name: str, content: Any) -> None: ...
    def add_reasoning(self, *steps: Any) -> None: ...
    def add_blocker(self, blocker: str) -> None: ...
    def resolve_blocker(self, blocker: str) -> None: ...
    def has_blockers(self) -> bool: ...
    def artifact_count(self) -> int: ...
    def reasoning_count(self) -> int: ...
    def blocker_count(self) -> int: ...
    def artifact_hash(self, name: str) -> Optional[str]: ...
    def integrity(self) -> str:
        """SHA-256 root hash of the entire shard set."""
        ...
    def to_dict(self) -> Dict[str, Any]: ...
    def to_json(self, **kwargs: Any) -> str: ...
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BatonShard: ...
    @classmethod
    def from_json(cls, json_str: str) -> BatonShard: ...
```

#### `constraint_theory_core.baton.context`

```python
def split_context(context: Dict[str, Any]) -> BatonShard:
    """Split a flat context dict into a three-way BatonShard."""
    ...


def merge_shards(
    shard: BatonShard,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Reassemble a BatonShard back into a flat context dict."""
    ...


def diff_shards(left: BatonShard, right: BatonShard) -> Dict[str, Any]:
    """Shallow structural diff between two shard instances."""
    ...
```

#### `constraint_theory_core.baton.validate`

```python
def validate_shard(shard: BatonShard) -> Dict[str, Any]:
    """Check a BatonShard for completeness and structural validity.

    Returns {"valid": bool, "issues": List[str]}.
    """
    ...
```

---

### 3.7 Embed (optional: numpy)

#### `constraint_theory_core.embed.model`

```python
from typing import List, Optional, Union

class MatchResult:
    """Result from EisensteinModel.match()."""

    def __init__(
        self,
        best_match: Optional[str] = None,
        score: float = 0.0,
        method: str = "none",
    ) -> None: ...

    best_match: Optional[str]
    score: float
    method: str


class EisensteinModel:
    """Drop-in StaticModel replacement with Eisenstein lattice matching cascade.

    Parameters
    ----------
    semantic_model: object or None
        A Model2Vec StaticModel instance (optional).
    bitvector_threshold: float
        Minimum similarity for bitvector match (default 0.85).
    semantic_threshold: float
        Minimum similarity for semantic match (default 0.3).
    deadband_threshold: float
        Cache hit threshold for deadband cache (default 0.90).
    deadband_max_size: int
        Maximum entries in deadband cache (default 1000).
    use_stemming: bool
        Whether to apply morphological stemming (default False).
    """

    def __init__(
        self,
        semantic_model=None,
        bitvector_threshold: float = 0.85,
        semantic_threshold: float = 0.3,
        deadband_threshold: float = 0.90,
        deadband_max_size: int = 1000,
        use_stemming: bool = False,
    ) -> None: ...

    @classmethod
    def from_model2vec(cls, model_name: str, **kwargs) -> EisensteinModel:
        """Load backed by a Model2Vec StaticModel."""
        ...

    def encode(self, texts: Union[str, List[str]]) -> "numpy.ndarray":
        """Encode texts into dense vectors (n_texts, dim)."""
        ...

    def match(
        self,
        query: str,
        candidates: List[str],
        threshold: Optional[float] = None,
        use_stemming: Optional[bool] = None,
    ) -> MatchResult: ...

    def match_all(
        self,
        query: str,
        candidates: List[str],
        use_stemming: Optional[bool] = None,
    ) -> List[MatchResult]: ...

    def similarity(
        self,
        texts1: Union[str, List[str]],
        texts2: Union[str, List[str]],
    ) -> "numpy.ndarray": ...

    def add_knowledge(self, key: str, value: str) -> None: ...
    def remove_knowledge(self, key: str) -> bool: ...
    def clear_knowledge(self) -> None: ...
    def add_domain(self, name: str, texts: List[str]) -> None: ...
    def set_domain(self, name: Optional[str]) -> None: ...
    def enable_self_tuning(self) -> None: ...
    def disable_self_tuning(self) -> None: ...

    @property
    def dim(self) -> int: ...

    def save(self, path: str) -> None: ...
    @classmethod
    def load(cls, path: str) -> EisensteinModel: ...
```

#### `constraint_theory_core.embed.cascade`

```python
from typing import Callable, List, Optional, Tuple

class CascadeMatcher:
    """5-layer matching cascade.

    Layers (fastest → most accurate):
    1. Exact string match
    2. Bitvector fingerprint match
    3. Deadband cache match
    4. Domain-SIF semantic match
    5. Full semantic encoder match
    """

    def __init__(
        self,
        semantic_encoder: Optional[Callable[[List[str]], "numpy.ndarray"]] = None,
        domain_sif=None,
        deadband_cache=None,
        bma_monitor=None,
        bitvector_threshold: float = 0.85,
        semantic_threshold: float = 0.3,
    ) -> None: ...

    def match(
        self,
        query: str,
        candidates: List[str],
        use_stemming: bool = False,
    ) -> Tuple[Optional[str], float, str]:
        """Return (best_match, score, layer_name)."""
        ...
```

#### `constraint_theory_core.embed.bitvector`

```python
def word_fingerprint(word: str, bits: int = 64) -> int:
    """Deterministic bit-vector fingerprint for a single word."""
    ...


def text_fingerprint(text: str, bits: int = 64) -> int:
    """Deterministic bit-vector fingerprint for a text string."""
    ...


def stem_word(word: str) -> str:
    """Porter-style stem for English."""
    ...


def hamming_distance(a: int, b: int) -> int:
    """Hamming distance between two bit-vector fingerprints."""
    ...


def bitvector_similarity(a: int, b: int) -> float:
    """Jaccard-like similarity from Hamming distance: 1 - hamming / bits."""
    ...


def find_best_bitvector_match(
    query_fp: int,
    candidate_fps: List[int],
    threshold: float = 0.85,
) -> Tuple[Optional[int], float]:
    """Return (index_of_best, similarity)."""
    ...
```

#### `constraint_theory_core.embed.quantize`

```python
class SplineLinearQuantizer:
    """Quantize nn.Linear weights using Eisenstein lattice control points."""

    def __init__(self, n_control_points: int = 16) -> None: ...
    def quantize(self, weight_matrix: "numpy.ndarray") -> "numpy.ndarray": ...
    def dequantize(self, quantized: "numpy.ndarray") -> "numpy.ndarray": ...
```

#### `constraint_theory_core.embed.cache`

```python
class DeadbandCache:
    """LRU cache with perceptual deadband key matching."""

    def __init__(self, threshold: float = 0.90, max_size: int = 1000) -> None: ...
    def get(self, key: str) -> Optional[Any]: ...
    def put(self, key: str, value: Any) -> None: ...
    def clear(self) -> None: ...
```

#### `constraint_theory_core.embed.domain`

```python
class DomainSIF:
    """Domain-specific Smooth Inverse Frequency weighting."""

    def fit(self, texts: List[str]) -> None: ...
    def transform(self, text: str, vector: "numpy.ndarray") -> "numpy.ndarray": ...
    @property
    def is_fitted(self) -> bool: ...
```

#### `constraint_theory_core.embed.monitor`

```python
class BMAMonitor:
    """Bayesian Moving Average drift detection for adaptive thresholds."""

    def __init__(self, window: int = 7) -> None: ...
    def update(self, score: float) -> float:
        """Return anomaly probability for the new score."""
        ...
    def reset(self) -> None: ...
```

---

### 3.8 Spline (optional: torch)

#### `constraint_theory_core.spline.lattice`

```python
import torch

class EisensteinLattice:
    """Places N control points on a hexagonal (Eisenstein) lattice.

    Args:
        n_points: Number of control points.
        device: Torch device.
    """

    def __init__(
        self,
        n_points: int,
        device: Optional[torch.device] = None,
    ) -> None: ...

    def positions(self) -> torch.Tensor:
        """Float32 tensor of shape (n_points, 2)."""
        ...
```

#### `constraint_theory_core.spline.linear`

```python
import torch.nn as nn

class SplineLinear(nn.Module):
    """nn.Linear replacement with weights interpolated from lattice control points."""

    def __init__(
        self,
        in_features: int,
        out_features: int,
        n_control_points: int = 16,
        bias: bool = True,
    ) -> None: ...
```

#### `constraint_theory_core.spline.low_rank`

```python
class LowRankLinear(nn.Module):
    """Factorised linear layer: W ≈ U @ V."""

    def __init__(
        self,
        in_features: int,
        out_features: int,
        rank: int,
        bias: bool = True,
    ) -> None: ...


class LowRankClassifier(nn.Module):
    """Low-rank classification head."""

    def __init__(
        self,
        in_features: int,
        num_classes: int,
        rank: int,
    ) -> None: ...
```

#### `constraint_theory_core.spline.hierarchical`

```python
class HierarchicalSplineLinear(nn.Module):
    """Multi-scale coarse+fine spline interpolation."""

    def __init__(
        self,
        in_features: int,
        out_features: int,
        coarse_points: int = 7,
        fine_points: int = 9,
        bias: bool = True,
    ) -> None: ...


class HierarchicalSplineClassifier(nn.Module):
    """Hierarchical spline classification head."""

    def __init__(
        self,
        in_features: int,
        num_classes: int,
        coarse_points: int = 7,
        fine_points: int = 9,
    ) -> None: ...
```

#### `constraint_theory_core.spline.inject`

```python
from typing import Type

VARIANT_GUIDE: Dict[str, str] = {
    "vision": "Use HierarchicalSplineLinear with 16 coarse + 9 fine points.",
    "nlp": "Use SplineLinear with 16 control points.",
    "audio": "Use LowRankLinear with rank=32.",
}


def inject_spline(
    model,
    n_control_points: int = 16,
    target_class: Type[nn.Module] = nn.Linear,
) -> None:
    """Replace all target_class layers with SplineLinear in-place."""
    ...


def inject_low_rank(
    model,
    rank: int,
    target_class: Type[nn.Module] = nn.Linear,
) -> None:
    """Replace all target_class layers with LowRankLinear in-place."""
    ...


def inject_hierarchical_spline(
    model,
    coarse_points: int = 7,
    fine_points: int = 9,
    target_class: Type[nn.Module] = nn.Linear,
) -> None:
    """Replace all target_class layers with HierarchicalSplineLinear in-place."""
    ...


def recommend_variant(task: str) -> str:
    """Recommend a compression variant for a given task domain."""
    ...


def compression_ratio(original: nn.Module, compressed: nn.Module) -> float:
    """Compute param-count ratio: original / compressed."""
    ...
```

---

### 3.9 Swarm (optional: torch)

#### `constraint_theory_core.swarm.snap`

```python
import numpy as np

def eisenstein_snap(points: np.ndarray, radius: float = 1.0) -> np.ndarray:
    """Snap 2D points to Eisenstein lattice Z[ω]. CPU (numpy)."""
    ...


def eisenstein_delta(points: np.ndarray, radius: float = 1.0) -> np.ndarray:
    """Distance from nearest Eisenstein lattice point. CPU (numpy)."""
    ...


# GPU variants (torch, optional)
def eisenstein_snap_gpu(points, radius: float = 1.0):
    """GPU version of eisenstein_snap."""
    ...


def eisenstein_delta_gpu(points, radius: float = 1.0):
    """GPU version of eisenstein_delta."""
    ...
```

#### `constraint_theory_core.swarm.state`

```python
class RoomState:
    """CRDT-mergeable room state for one agent.

    Properties: commutative, associative, idempotent merges.
    Uses last-writer-wins with lamport clock. Deadband propagation.
    """

    def __init__(
        self,
        room_id: int,
        context_dim: int = 64,
        obs_dim: int = 128,
        device: str = "cpu",
    ) -> None: ...

    def update_context(self, delta) -> None: ...
    def should_propagate(self) -> bool: ...
    def propagate(self) -> Optional[object]: ...
    def receive_observation(self, other_id: int, other_context) -> None: ...
```

#### `constraint_theory_core.swarm.network`

```python
class SwarmRoomNetwork:
    """GPU-accelerated swarm of interconnected rooms."""

    def __init__(
        self,
        n_agents: int = 256,
        context_dim: int = 64,
        obs_dim: int = 128,
        device: str = "cpu",
        interconnection_density: float = 0.3,
        deadband_tolerance: float = 0.1,
        snap_radius: float = 1.0,
    ) -> None: ...

    def step(self, task_signal=None) -> Dict[str, Any]: ...
    def benchmark(self, n_steps: int = 100) -> Dict[str, Any]: ...
```

---

### 3.10 Consensus (optional: Rust extension)

#### `constraint_theory_core.consensus.holonomy`

```python
from dataclasses import dataclass
from typing import List

@dataclass
class ConsensusResult:
    """Result of a holonomy consensus check."""

    cycles_checked: int
    consensus_reached: bool
    max_deviation: float
    inconsistent_cycles: List[int]


class HolonomyConsensus:
    """Zero-holonomy consensus engine.

    If a cycle of tiles has zero holonomy (product of transformations = identity),
    the entire set is globally consistent by definition. No voting required.
    """

    def __init__(self, tolerance: float = 0.01) -> None: ...
    def add_tile(self, tile) -> None: ...
    def check_consensus(self) -> ConsensusResult: ...
    def isolate_fault(self, cycle_id: int) -> List[int]:
        """Return suspect tile IDs via cycle bisection (O(log N))."""
        ...
```

#### `constraint_theory_core.consensus.constraints`

```python
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class HolonomyBounds:
    """Bounds for holonomy constraint satisfaction."""

    max_deviation: float
    cycle_count: int
    tile_count: int


class ConstraintResult:
    """Outcome of a constraint check on a tile network."""

    def __init__(
        self,
        satisfied: bool,
        violations: List[Tuple[int, int, float]],
    ) -> None: ...

    satisfied: bool
    violations: List[Tuple[int, int, float]]  # (tile_a, tile_b, deviation)


def sat8(value: int) -> int:
    """Clamp an integer to signed 8-bit range [-128, 127]."""
    ...
```

#### `constraint_theory_core.consensus.cohomology`

```python
from dataclasses import dataclass
from typing import List

@dataclass
class EmergenceResult:
    """Detected emergent structure in a tile network."""

    detected: bool
    emergence_score: float
    participating_tiles: List[int]
    pattern_type: str


class EmergenceDetector:
    """Detect emergent global structure from local holonomy constraints."""

    def __init__(self, threshold: float = 0.5) -> None: ...
    def analyse(self, network) -> EmergenceResult: ...
```

#### `constraint_theory_core.consensus.encoding`

```python
from typing import Tuple

class Vector48:
    """Compact 48-direction vector (same as encode.pythagorean.Vector48).

    This is the consensus-layer binding; the canonical implementation lives
    in `encode.pythagorean`.
    """

    def __init__(self, sector: int, magnitude: float = 1.0) -> None: ...
    def to_cartesian(self) -> Tuple[float, float]: ...
    @classmethod
    def from_cartesian(cls, x: float, y: float) -> Vector48: ...


def encode_angle(radians: float) -> int:
    """Encode an angle into a Pythagorean-48 sector (0-47)."""
    ...


def decode_angle(sector: int) -> float:
    """Decode a Pythagorean-48 sector back to radians."""
    ...
```

#### `constraint_theory_core.consensus.lifecycle`

```python
from enum import Enum
from typing import Optional

class TrustState(Enum):
    PROVISIONAL = "provisional"
    ACTIVE = "active"
    SUSPICIOUS = "suspicious"
    RETRACTED = "retracted"


class RetractionReason(Enum):
    INCONSISTENCY = "inconsistency"
    TIMEOUT = "timeout"
    BYZANTINE = "byzantine"
    VOLUNTARY = "voluntary"


class LamportClock:
    """Monotonic logical clock for causal ordering."""

    def __init__(self, node_id: int, initial: int = 0) -> None: ...
    def tick(self) -> int: ...
    def merge(self, other: int) -> int: ...
    @property
    def value(self) -> int: ...
```

#### `constraint_theory_core.consensus.trust`

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class TrustTile:
    """A tile in the trust pool with lifecycle state."""

    tile_id: int
    trust_score: float
    state: TrustState
    clock: int


class TrustPool:
    """Manages trust scores and lifecycle transitions for a set of tiles."""

    def __init__(self, initial_capacity: int = 256) -> None: ...
    def add(self, tile: TrustTile) -> None: ...
    def update_trust(self, tile_id: int, delta: float) -> None: ...
    def retract(self, tile_id: int, reason: RetractionReason) -> None: ...
    def get(self, tile_id: int) -> Optional[TrustTile]: ...
    def active_tiles(self) -> List[TrustTile]: ...


class LifecycleError(Exception):
    """Raised on invalid lifecycle transitions."""
    ...
```

---

### 3.11 FFI

#### `constraint_theory_core.ffi.c_math`

```python
"""cffi bridge to fleet-math-c.

Built automatically by build.py if a C compiler is available.
Falls back to pure-Python implementations if the shared library is absent.
"""


def fleet_eisenstein_norm(a: int, b: int) -> int:
    """N(a + bω) = a² − ab + b² (C-accelerated if available)."""
    ...


def fleet_laman_edges(vertices: int) -> int:
    """Minimum edges for Laman-rigid graph: max(0, 2V − 3)."""
    ...


def fleet_is_rigid(vertices: int, edges: int) -> bool:
    """True if E ≥ 2V − 3."""
    ...


def fleet_holonomy_check(transforms: List[int]) -> bool:
    """True if the product of transforms equals identity."""
    ...


def fleet_manhattan_distance(a: List[int], b: List[int]) -> int:
    """Σ|a[i] − b[i]|."""
    ...


def fleet_pythagorean48_encode(x: float, y: float) -> int:
    """Quantize angle(x, y) into one of 48 sectors (C-accelerated)."""
    ...
```

#### `constraint_theory_core.ffi.rust_consensus`

```python
"""PyO3/maturin bridge to holonomy-consensus.

This module is a thin re-export layer. The actual Rust extension is built
by maturin and lives at `constraint_theory_core._rust`.
"""

# Re-export Rust structs with Pythonic wrappers
from constraint_theory_core._rust import (
    HolonomyConsensus as _RustHolonomyConsensus,
    ConsensusResult as _RustConsensusResult,
    EmergenceDetector as _RustEmergenceDetector,
    LamportClock as _RustLamportClock,
    TrustPool as _RustTrustPool,
)
```

---

### 3.12 Theorems

#### `constraint_theory_core.theorems`

```python
"""Named theorem constants — referenceable bounds from constraint theory.

Every constant in this module is documented with:
- The formal statement
- The reference proof / paper
- The module where it is applied
"""

# ── A₂ Lattice ───────────────────────────────────────────────────────────
COVERING_RADIUS: float = 1.0 / (3.0 ** 0.5)
"""ρ = 1/√3 ≈ 0.57735.

Theorem: Every point in ℂ is within ρ of an Eisenstein integer.
Proof: Voronoi-cell geometry of the hexagonal lattice.
Applied in: foundation.lattice, temporal.agent, encode.dodecet
"""

SAFE_THRESHOLD: float = COVERING_RADIUS / 2.0
"""ε_safe = ρ/2 ≈ 0.2887.

Used as the default deadband width for "safe" snaps.
Applied in: temporal.agent, adaptive.tolerance
"""

VORONOI_CELL_AREA: float = (3.0 ** 0.5) / 2.0
"""Area of A₂ fundamental parallelogram: √3/2 ≈ 0.8660.

Theorem: The packing density of A₂ is π/(2√3) ≈ 0.9069.
Applied in: foundation.lattice.error_cdf
"""

# ── Rigidity ─────────────────────────────────────────────────────────────
LAMAN_COEFFICIENT: int = 2
"""Laman's theorem coefficient for 2-D rigidity.

Theorem (Laman, 1970): A graph G=(V,E) in 2-D is generically minimally
rigid iff E = 2V − 3 and every subgraph on k ≥ 2 vertices has ≤ 2k − 3 edges.
Applied in: ffi.c_math.fleet_laman_edges, consensus.constraints
"""

MAX_RIGID_NEIGHBORS: int = 12
"""Maximum neighbour count for generic rigidity in 2-D.

Derived from Laman: 2V − 3 edges → average degree < 4, but local
clusters can reach up to 12 in dense packings before over-constraint.
Applied in: consensus.constraints.HolonomyBounds
"""

# ── Consensus ────────────────────────────────────────────────────────────
DIRECTION_COUNT: int = 48
"""Pythagorean 48-direction encoding.

log2(48) = 5.585 bits — maximum information per bit for 16-bit integers.
Applied in: encode.pythagorean, consensus.encoding, ffi.c_math
"""

# ── Deadband / Perception ────────────────────────────────────────────────
PERCEPTUAL_BITS: float = 5.585
"""Effective bits for Pythagorean-48 directional encoding.

Same as log2(DIRECTION_COUNT).
Applied in: encode.pythagorean
"""

# ── Swarm ────────────────────────────────────────────────────────────────
DEFAULT_DEADBAND_TOLERANCE: float = 0.1
"""Default propagation deadband for swarm rooms."""

DEFAULT_INTERCONNECTION_DENSITY: float = 0.3
"""Default swarm graph density."""
```

---

### 3.13 Top-Level Re-Exports

`constraint_theory_core/__init__.py` exposes a **curated** set of names for the 80% use-case. No star-imports; explicit `__all__`.

```python
from constraint_theory_core._version import __version__

# Foundation
from constraint_theory_core.foundation.lattice import (
    A2Point,
    Dodecet,
    Chamber,
    snap,
    snap_with_error,
    snap_batch,
    norm_sq,
    norm,
    distance_sq,
    distance,
    rotation,
    nearest_neighbors,
    lattice_points_within,
)
from constraint_theory_core.foundation.chamber import classify_chamber, chamber_barycentric
from constraint_theory_core.foundation.constants import (
    COVERING_RADIUS,
    SAFE_THRESHOLD,
    SQRT_3,
    OMEGA_RE,
    OMEGA_IM,
)

# Temporal
from constraint_theory_core.temporal.funnel import FunnelPhase, ChiralityState, AgentAction, deadband_funnel
from constraint_theory_core.temporal.agent import (
    SnapResult,
    TemporalUpdate,
    AgentSummary,
    TemporalAgent,
    check_constraint,
)
from constraint_theory_core.temporal.dodecet_codec import encode_dodecet, decode_dodecet
from constraint_theory_core.temporal.bma import bma_detect

# Adaptive
from constraint_theory_core.adaptive.tolerance import adaptive_epsilon, AdaptiveTolerance
from constraint_theory_core.adaptive.manifold import ManifoldRegion, classify_region, adaptive_snap

# Encode
from constraint_theory_core.encode.dodecet import encode, decode, Dodecet as DodecetClass
from constraint_theory_core.encode.pythagorean import Pythagorean48, Vector48

# PLATO
from constraint_theory_core.plato.tile import PlatoTile, TileState, TilePriority
from constraint_theory_core.plato.store import PlatoTileStore
from constraint_theory_core.plato.scoring import score_tiles

# Baton
from constraint_theory_core.baton.shard import BatonShard, ARTIFACTS_KEY, REASONING_KEY, BLOCKERS_KEY
from constraint_theory_core.baton.context import split_context, merge_shards, diff_shards
from constraint_theory_core.baton.validate import validate_shard

# Theorems
from constraint_theory_core.theorems import (
    COVERING_RADIUS as THEOREM_COVERING_RADIUS,
    SAFE_THRESHOLD as THEOREM_SAFE_THRESHOLD,
    LAMAN_COEFFICIENT,
    MAX_RIGID_NEIGHBORS,
    DIRECTION_COUNT,
)

__all__ = [
    "__version__",
    # Foundation
    "A2Point",
    "Dodecet",
    "Chamber",
    "snap",
    "snap_with_error",
    "snap_batch",
    "norm_sq",
    "norm",
    "distance_sq",
    "distance",
    "rotation",
    "nearest_neighbors",
    "lattice_points_within",
    "classify_chamber",
    "chamber_barycentric",
    "COVERING_RADIUS",
    "SAFE_THRESHOLD",
    "SQRT_3",
    "OMEGA_RE",
    "OMEGA_IM",
    # Temporal
    "FunnelPhase",
    "ChiralityState",
    "AgentAction",
    "deadband_funnel",
    "SnapResult",
    "TemporalUpdate",
    "AgentSummary",
    "TemporalAgent",
    "check_constraint",
    "encode_dodecet",
    "decode_dodecet",
    "bma_detect",
    # Adaptive
    "adaptive_epsilon",
    "AdaptiveTolerance",
    "ManifoldRegion",
    "classify_region",
    "adaptive_snap",
    # Encode
    "encode",
    "decode",
    "DodecetClass",
    "Pythagorean48",
    "Vector48",
    # PLATO
    "PlatoTile",
    "TileState",
    "TilePriority",
    "PlatoTileStore",
    "score_tiles",
    # Baton
    "BatonShard",
    "ARTIFACTS_KEY",
    "REASONING_KEY",
    "BLOCKERS_KEY",
    "split_context",
    "merge_shards",
    "diff_shards",
    "validate_shard",
    # Theorems
    "THEOREM_COVERING_RADIUS",
    "THEOREM_SAFE_THRESHOLD",
    "LAMAN_COEFFICIENT",
    "MAX_RIGID_NEIGHBORS",
    "DIRECTION_COUNT",
]
```

---

## 4. Import Compatibility (Backward Compatibility)

### 4.1 Shim Strategy

Old import paths **must continue to work** for at least two minor versions (through v1.2.0). We provide this via `compat.*` submodules that re-export from the canonical locations.

#### Example: `constraint_theory_core/compat/constraint_theory.py`

```python
"""Shim for ``import constraint_theory`` compatibility.

Install this shim by adding a ``constraint_theory.py`` file to your
PYTHONPATH or site-packages that does::

    from constraint_theory_core.compat.constraint_theory import *
"""

from constraint_theory_core.foundation.lattice import (
    A2Point,
    Dodecet,
    Chamber,
    snap,
    snap_to_lattice as _stl,
    snap_with_error,
    snap_with_metadata,
    snap_batch,
    norm_sq,
    norm,
    distance_sq,
    distance,
    classify_chamber,
    chamber_barycentric,
    encode,
    encode_from_fields,
    decode,
    dodecet_encode,
    rotation,
    nearest_neighbors,
    voronoi_cell_area,
    error_cdf,
    voronoi_radius,
    lattice_points_within,
)
from constraint_theory_core.temporal.funnel import (
    COVERING_RADIUS,
    SAFE_THRESHOLD,
    SQRT_3,
    FunnelPhase,
    ChiralityState,
    AgentAction,
    deadband_funnel,
)
from constraint_theory_core.temporal.agent import (
    SnapResult,
    TemporalUpdate,
    AgentSummary,
    TemporalAgent,
    check_constraint,
)
from constraint_theory_core.temporal.dodecet_codec import encode_dodecet, decode_dodecet
from constraint_theory_core.adaptive.tolerance import AdaptiveTolerance, adaptive_epsilon
from constraint_theory_core.adaptive.manifold import (
    ManifoldRegion,
    classify_region,
    curvature_from_manifold,
    manifold_distance,
    adaptive_snap,
)
from constraint_theory_core.plato.tile import PlatoTile, TileState, TilePriority
from constraint_theory_core.plato.store import PlatoTileStore
from constraint_theory_core.plato.scoring import score_tiles
from constraint_theory_core.baton.shard import BatonShard
from constraint_theory_core.baton.context import split_context, merge_shards, diff_shards
from constraint_theory_core.baton.validate import validate_shard
from constraint_theory_core._version import __version__

# Legacy alias
snap_to_lattice = _stl

__all__ = [
    "__version__",
    "COVERING_RADIUS",
    "SAFE_THRESHOLD",
    "SQRT_3",
    "FunnelPhase",
    "ChiralityState",
    "AgentAction",
    "SnapResult",
    "TemporalUpdate",
    "AgentSummary",
    "TemporalAgent",
    "snap_to_eisenstein",  # will be provided as alias below
    "encode_dodecet",
    "decode_dodecet",
    "deadband_funnel",
    "check_constraint",
    "A2Point",
    "Dodecet",
    "Chamber",
    "snap",
    "snap_to_lattice",
    "snap_with_error",
    "snap_with_metadata",
    "snap_batch",
    "norm_sq",
    "norm",
    "distance_sq",
    "distance",
    "classify_chamber",
    "chamber_barycentric",
    "encode",
    "encode_from_fields",
    "decode",
    "dodecet_encode",
    "rotation",
    "nearest_neighbors",
    "voronoi_cell_area",
    "error_cdf",
    "voronoi_radius",
    "lattice_points_within",
    "ManifoldRegion",
    "AdaptiveTolerance",
    "adaptive_epsilon",
    "classify_region",
    "curvature_from_manifold",
    "manifold_distance",
    "adaptive_snap",
    "PlatoTile",
    "PlatoTileStore",
    "TileState",
    "TilePriority",
    "score_tiles",
    "BatonShard",
    "split_context",
    "merge_shards",
    "diff_shards",
    "validate_shard",
]


# Provide temporal.snap_to_eisenstein as an alias for foundation.snap_with_error
# (the old temporal module duplicated the snap logic)
def snap_to_eisenstein(x: float, y: float):
    from constraint_theory_core.temporal.agent import TemporalAgent
    return TemporalAgent().observe(x, y).snap
```

### 4.2 Full Shim Mapping

| Old Import | Shim Location | Canonical New Import |
|---|---|---|
| `from constraint_theory import X` | `compat/constraint_theory.py` | `from constraint_theory_core import X` |
| `from deadband_python import X` | `compat/deadband_python.py` | `from constraint_theory_core.foundation import X` etc. |
| `from eisenstein_embed import X` | `compat/eisenstein_embed.py` | `from constraint_theory_core.embed import X` |
| `from tensor_spline import X` | `compat/tensor_spline.py` | `from constraint_theory_core.spline import X` |
| `from swarm_rooms import X` | `compat/swarm_rooms.py` | `from constraint_theory_core.swarm import X` |
| `from fleet_agent.holonomy_stubs import X` | `compat/fleet_agent.py` | `from constraint_theory_core.consensus import X` |
| `from holonomy_consensus import X` | `compat/holonomy_consensus.py` | `from constraint_theory_core.consensus import X` |

### 4.3 Deprecation Warnings

Every shim module emits a `DeprecationWarning` on first import:

```python
import warnings
warnings.warn(
    "constraint_theory is deprecated; use constraint_theory_core instead. "
    "This shim will be removed in v1.3.0.",
    DeprecationWarning,
    stacklevel=2,
)
```

---

## 5. pyproject.toml

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel", "cffi>=1.15.0", "maturin>=1.0,<2.0"]
build-backend = "setuptools.build_meta"

[project]
name = "constraint-theory-core"
version = "1.0.0"
description = "Unified constraint theory: lattice math, temporal agents, PLATO tiles, baton shards, embeddings, splines, swarm rooms, and zero-holonomy consensus."
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.9"
authors = [
    {name = "Constraint Theory Team"},
]
keywords = [
    "constraint-theory",
    "eisenstein-integers",
    "hexagonal-lattice",
    "deadband",
    "consensus",
    "plato",
    "baton",
    "swarm",
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Programming Language :: C",
    "Programming Language :: Rust",
    "Topic :: Scientific/Engineering :: Mathematics",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
]

# Core has ZERO external dependencies.
dependencies = []

[project.optional-dependencies]
# NumPy-powered embedding and bitvector utilities
embed = ["numpy>=1.21.0"]

# PyTorch-powered spline and swarm layers
spline = ["torch>=2.0.0", "numpy>=1.21.0"]
swarm = ["torch>=2.0.0", "numpy>=1.21.0"]

# C FFI bridge (builds fleet-math-c)
ffi = ["cffi>=1.15.0"]

# Rust extension (builds holonomy-consensus)
rust = ["maturin>=1.0,<2.0"]

# Full-featured install
all = [
    "numpy>=1.21.0",
    "torch>=2.0.0",
    "cffi>=1.15.0",
    "maturin>=1.0,<2.0",
]

# Development
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "mypy>=1.0",
    "ruff>=0.1.0",
    "numpy>=1.21.0",
    "torch>=2.0.0",
    "cffi>=1.15.0",
    "maturin>=1.0,<2.0",
]

[project.urls]
Homepage = "https://github.com/constraint-theory/core"
Documentation = "https://constraint-theory-core.readthedocs.io"
Repository = "https://github.com/constraint-theory/core.git"
Issues = "https://github.com/constraint-theory/core/issues"

[tool.setuptools.packages.find]
where = ["."]
include = ["constraint_theory_core*"]

[tool.setuptools.package-data]
constraint_theory_core = ["py.typed", "ffi/*.h", "ffi/*.rs"]

# ── Rust extension (maturin) ──────────────────────────────────────────────
[tool.maturin]
name = "constraint_theory_core._rust"
manifest-path = "Cargo.toml"
python-source = "."
module-name = "constraint_theory_core._rust"

# ── build.py (cffi) ───────────────────────────────────────────────────────
# build.py lives next to pyproject.toml and is picked up automatically by
# setuptools when cffi is in build-system requires.

[tool.cffi]
# Tells setuptools-cffi where to find the C build script
ffi_build = "constraint_theory_core.ffi._build:ffi"

# ── Linting ───────────────────────────────────────────────────────────────
[tool.ruff]
line-length = 100
target-version = "py39"
select = ["E", "F", "W", "I", "N", "D", "UP", "B", "C4", "SIM"]
ignore = ["D105", "D107", "D203", "D213"]

[tool.ruff.pydocstyle]
convention = "numpy"

[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["constraint_theory_core/tests"]
python_files = ["test_*.py"]
addopts = "-v --tb=short"
```

### 5.1 build.py (cffi C-extension builder)

```python
"""Build the fleet-math-c C extension via cffi."""

import os
import sys
from cffi import FFI

ffi = FFI()

HERE = os.path.dirname(os.path.abspath(__file__))
HEADER_PATH = os.path.join(HERE, "constraint_theory_core", "ffi", "fleet_math.h")
SRC_PATH = os.path.join(HERE, "constraint_theory_core", "ffi", "fleet_math.c")

with open(HEADER_PATH) as f:
    ffi.cdef(f.read())

# If the C source is not present, we build a no-op extension that falls
# back to pure Python at runtime.
if os.path.exists(SRC_PATH):
    ffi.set_source(
        "constraint_theory_core.ffi._c_core",
        open(SRC_PATH).read(),
        source_extension=".c",
    )
else:
    # Minimal stub so the build succeeds even without C source.
    ffi.set_source(
        "constraint_theory_core.ffi._c_core",
        "",
        source_extension=".c",
    )

if __name__ == "__main__":
    ffi.compile(verbose=True)
```

### 5.2 Cargo.toml (maturin Rust extension)

```toml
[package]
name = "constraint-theory-core-rust"
version = "1.0.0"
edition = "2021"

[lib]
name = "constraint_theory_core_rust"
crate-type = ["cdylib"]

[dependencies]
pyo3 = { version = "0.22", features = ["extension-module"] }
numpy = { version = "0.22", optional = true }
ndarray = { version = "0.16", optional = true }

[features]
default = []
embed = ["numpy", "ndarray"]

[dependencies.holonomy-consensus]
path = "../holonomy-consensus"
optional = true

[features]
consensus = ["holonomy-consensus"]
```

---

## 6. Migration Guide

### 6.1 Quick Reference Table

| Old Code | New Code |
|---|---|
| `from constraint_theory import A2Point, snap` | `from constraint_theory_core import A2Point, snap` |
| `from constraint_theory.eisenstein import norm_sq` | `from constraint_theory_core.foundation.lattice import norm_sq` |
| `from constraint_theory.temporal import TemporalAgent` | `from constraint_theory_core.temporal.agent import TemporalAgent` |
| `from constraint_theory.plato import PlatoTile` | `from constraint_theory_core.plato.tile import PlatoTile` |
| `from constraint_theory.baton import BatonShard` | `from constraint_theory_core.baton.shard import BatonShard` |
| `from deadband_python import eisenstein_snap` | `from constraint_theory_core.foundation.lattice import snap` |
| `from deadband_python import div360_add` | `from constraint_theory_core.foundation.modular import div360_add` |
| `from deadband_python import fib_spline_search` | `from constraint_theory_core.foundation.fibonacci import fib_spline_search` |
| `from deadband_python import bma_detect` | `from constraint_theory_core.temporal.bma import bma_detect` |
| `from eisenstein_embed import EisensteinModel` | `from constraint_theory_core.embed.model import EisensteinModel` |
| `from eisenstein_embed.bitvector import hamming_distance` | `from constraint_theory_core.embed.bitvector import hamming_distance` |
| `from tensor_spline import SplineLinear` | `from constraint_theory_core.spline.linear import SplineLinear` |
| `from tensor_spline import inject_spline` | `from constraint_theory_core.spline.inject import inject_spline` |
| `from swarm_rooms import RoomState` | `from constraint_theory_core.swarm.state import RoomState` |
| `from swarm_rooms import SwarmRoomNetwork` | `from constraint_theory_core.swarm.network import SwarmRoomNetwork` |
| `from fleet_agent.holonomy_stubs import HolonomyConsensusStub` | `from constraint_theory_core.consensus.holonomy import HolonomyConsensus` |

### 6.2 Breaking Changes

1. **Namespace flattening removed.**
   - Old: `from constraint_theory import TemporalAgent` (flat)
   - New: `from constraint_theory_core.temporal.agent import TemporalAgent` (structured)
   - Mitigation: `from constraint_theory_core import TemporalAgent` still works via `__init__.py` re-export.

2. **C extension renamed.**
   - Old: `deadband_python._deadband_c`
   - New: `constraint_theory_core.ffi._c_core`
   - Mitigation: Pure-Python fallbacks are always present; C accel is transparent.

3. **Rust extension renamed.**
   - Old: `holonomy_consensus` (external package)
   - New: `constraint_theory_core._rust` (bundled)
   - Mitigation: `constraint_theory_core.consensus.*` provides Pythonic wrappers.

4. **Constants moved to `theorems`.**
   - Old: `from constraint_theory.temporal import COVERING_RADIUS`
   - New: `from constraint_theory_core.theorems import COVERING_RADIUS`
   - Mitigation: Still re-exported at top-level `constraint_theory_core.COVERING_RADIUS`.

### 6.3 Step-by-Step Migration

**Step 1:** Replace package names in `requirements.txt`:

```text
# Old
constraint-theory-py
deadband-python
eisenstein-embed
tensor-spline
swarm-rooms
fleet-agent
holonomy-consensus

# New
constraint-theory-core[all]
```

**Step 2:** Run the compat shim check:

```bash
python -W error::DeprecationWarning -c "import constraint_theory"
```

This will fail fast if you still hit the shim, showing exactly which files need updating.

**Step 3:** Bulk-replace imports in your codebase:

```bash
# Example sed patterns (run in your project root)
sed -i 's/from constraint_theory import/from constraint_theory_core import/g' $(find . -name "*.py")
sed -i 's/from constraint_theory\.eisenstein import/from constraint_theory_core.foundation.lattice import/g' $(find . -name "*.py")
sed -i 's/from constraint_theory\.temporal import/from constraint_theory_core.temporal.agent import/g' $(find . -name "*.py")
sed -i 's/from constraint_theory\.adaptive import/from constraint_theory_core.adaptive.tolerance import/g' $(find . -name "*.py")
sed -i 's/from constraint_theory\.plato import/from constraint_theory_core.plato.tile import/g' $(find . -name "*.py")
sed -i 's/from constraint_theory\.baton import/from constraint_theory_core.baton.shard import/g' $(find . -name "*.py")
sed -i 's/from deadband_python import/from constraint_theory_core.foundation.deadband import/g' $(find . -name "*.py")
sed -i 's/from eisenstein_embed import/from constraint_theory_core.embed.model import/g' $(find . -name "*.py")
sed -i 's/from tensor_spline import/from constraint_theory_core.spline.linear import/g' $(find . -name "*.py")
sed -i 's/from swarm_rooms import/from constraint_theory_core.swarm.network import/g' $(find . -name "*.py")
```

**Step 4:** Verify with tests:

```bash
python -m pytest your_project/tests/ -v
```

**Step 5:** Remove shim dependencies once clean:

```bash
pip uninstall constraint-theory-py deadband-python eisenstein-embed tensor-spline swarm-rooms fleet-agent holonomy-consensus
```

---

## 7. Testing Strategy

### 7.1 Test Layout

```text
constraint_theory_core/tests/
├── __init__.py
├── test_foundation.py      # lattice, chamber, constants, deadband, modular, shells, fibonacci
├── test_temporal.py        # funnel, agent, dodecet_codec, bma
├── test_adaptive.py        # tolerance, manifold
├── test_encode.py          # dodecet, pythagorean
├── test_plato.py           # tile, store, scoring
├── test_baton.py           # shard, context, validate
├── test_embed.py           # model, cascade, bitvector, quantize, cache, domain, monitor
├── test_spline.py          # lattice, linear, low_rank, hierarchical, inject
├── test_swarm.py           # state, network, snap
├── test_consensus.py       # holonomy, constraints, cohomology, encoding, lifecycle, trust
├── test_theorems.py        # theorem constants and doc references
├── test_ffi.py             # c_math, rust_consensus (skip if compiled libs absent)
└── test_compat.py          # shim imports emit DeprecationWarning
```

### 7.2 Test Policy

- **Core modules:** 100% line coverage (pure Python, easy to test).
- **Optional modules:** Tests are skipped gracefully if dependencies are missing (`pytest.importorskip`).
- **FFI modules:** Tests skip if compiled library is absent; CI builds both C and Rust extensions.
- **Compat modules:** Assert that every old import path still resolves and emits `DeprecationWarning`.

### 7.3 CI Matrix

| Python | numpy | torch | cffi | maturin | Tests Run |
|---|---|---|---|---|---|
| 3.9 | — | — | — | — | core only |
| 3.10 | ✓ | — | ✓ | — | core + embed + ffi |
| 3.11 | ✓ | ✓ | ✓ | ✓ | all |
| 3.12 | ✓ | ✓ | ✓ | ✓ | all |
| 3.13 | ✓ | ✓ | ✓ | ✓ | all |

---

## 8. Performance Budget

| Operation | Pure Python | C FFI | Rust FFI | Target |
|---|---|---|---|---|
| A₂ snap (1 point) | 2.5 µs | 0.3 µs | — | < 5 µs |
| A₂ snap batch (1k) | 2.5 ms | 0.3 ms | — | < 5 ms |
| Dodecet encode/decode | 0.5 µs | — | — | < 1 µs |
| TemporalAgent.observe | 15 µs | — | — | < 50 µs |
| BMA detect (1k window) | 0.8 ms | — | — | < 2 ms |
| Holonomy check (1k tiles) | — | — | 38 ms | < 50 ms |
| Emergence detection | — | — | 12 ms | < 20 ms |
| SplineLinear forward (512²) | — | — | — | < 5 ms (torch) |
| SwarmRoomNetwork.step (256 agents) | — | — | — | < 10 ms (torch) |

---

## 9. Roadmap

| Milestone | Target Date | Deliverable |
|---|---|---|
| v0.1.0-alpha | 2026-06-15 | Foundation + Temporal + Adaptive + Encode + tests |
| v0.2.0-alpha | 2026-07-01 | + PLATO + Baton + Compat shims |
| v0.3.0-beta | 2026-07-15 | + Embed + Spline + Swarm + optional deps |
| v0.4.0-beta | 2026-08-01 | + C FFI (fleet-math-c) + Rust FFI (holonomy-consensus) |
| v0.5.0-rc | 2026-08-15 | Full test matrix, docs, migration examples |
| v1.0.0 | 2026-09-01 | Stable release, API freeze |
| v1.1.0 | 2026-10-01 | Performance optimisations, CUDA kernels |
| v1.2.0 | 2026-11-01 | Last version with compat shims |
| v1.3.0 | 2026-12-01 | Shim removal, deprecation cycle complete |

---

## 10. Glossary

| Term | Definition |
|---|---|
| **A₂ lattice** | The hexagonal lattice of Eisenstein integers ℤ[ω]. |
| **Baton** | Shared context dict split into artifacts/reasoning/blockers. |
| **Covering radius (ρ)** | Maximum distance from any point to the nearest lattice point (1/√3). |
| **Deadband** | Perceptual tolerance: ignore signal changes below a threshold. |
| **Dodecet** | 12-bit encoding of snap error, angle, chamber, and safety flag. |
| **Holonomy** | Product of transformations around a cycle; identity = consistent. |
| **Laman bound** | Minimum edges for generic rigidity in 2-D: 2V − 3. |
| **PLATO** | Persistent Long-term Associative Thought Orchestrator (tile system). |
| **Weyl chamber** | One of six fundamental domains in the A₂ root system. |
| **Zero-holonomy consensus** | Agreement by geometric constraint satisfaction instead of voting. |

---

*End of document.*
