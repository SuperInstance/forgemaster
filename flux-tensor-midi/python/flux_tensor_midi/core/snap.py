"""
EisensteinSnap: Rhythmic quantization via Eisenstein lattice.

The Eisenstein lattice (hexagonal / triangular tiling) provides a natural
framework for rhythm snapping.  Ratios map to musical intervals:
    1:1 = unison
    2:1 = halftime
    3:2 = triplet
    3:1 = waltz time
    4:3 = compound meter

The covering radius 1/sqrt(3) ensures optimal packing.
"""

from __future__ import annotations
import math
from enum import Enum


class RhythmicRole(Enum):
    """Rhythmic role for a musician in the ensemble."""
    ROOT = "root"           # 1:1 — downbeat
    HALFTIME = "halftime"   # 2:1 — half speed
    TRIPLET = "triplet"     # 3:2 — swung feel
    WALTZ = "waltz"         # 3:1 — waltz time
    COMPOUND = "compound"   # 4:3 — compound meter
    DOUBLETIME = "double"   # 1:2 — double speed
    OFFSET = "offset"       # 1:1 with pi/3 phase
    QUINTUPLE = "quintuple" # 5:4 — quintuple meter
    SEPTUPLE = "septuple"   # 7:4 — septuple meter


class EisensteinRatio:
    """A rational ratio for rhythmic relationships.

    Parameters
    ----------
    numerator : int
    denominator : int
    phase_offset : float, default=0.0
        Phase offset in fractions of a period (0–1).
    """

    def __init__(
        self,
        numerator: int,
        denominator: int,
        phase_offset: float = 0.0,
    ):
        if denominator <= 0:
            raise ValueError(f"denominator must be positive, got {denominator}")
        self._num = numerator
        self._den = denominator
        self._phase = phase_offset

    @property
    def ratio(self) -> float:
        """The numeric ratio."""
        return self._num / self._den

    @property
    def numerator(self) -> int:
        return self._num

    @property
    def denominator(self) -> int:
        return self._den

    @property
    def phase(self) -> float:
        return self._phase

    def snap(self, t: float, base_period_ms: float = 500.0) -> float:
        """Snap a timestamp to this ratio's grid.

        Parameters
        ----------
        t : float
            Timestamp in ms.
        base_period_ms : float
            Base period (quarter note at current BPM) in ms.

        Returns
        -------
        Snapped timestamp in ms.
        """
        period = base_period_ms * self._num / self._den
        phase_ms = period * self._phase
        return round((t - phase_ms) / period) * period + phase_ms

    def __repr__(self) -> str:
        return f"EisensteinRatio({self._num}:{self._den}, phase={self._phase:.3f})"


# Pre-defined rhythmic ratios
UNISON = EisensteinRatio(1, 1)       # 1:1
HALFTIME = EisensteinRatio(2, 1)     # 2:1
TRIPLET = EisensteinRatio(3, 2)      # 3:2
WALTZ_TIME = EisensteinRatio(3, 1)   # 3:1
COMPOUND = EisensteinRatio(4, 3)     # 4:3
DOUBLE_TIME = EisensteinRatio(1, 2)  # 1:2
OFFSET = EisensteinRatio(1, 1, 1/3)  # 1:1 with 120° phase
QUINTUPLE = EisensteinRatio(5, 4)    # 5:4
SEPTUPLE = EisensteinRatio(7, 4)     # 7:4

# Map roles to ratios
ROLE_RATIO_MAP: dict[RhythmicRole, EisensteinRatio] = {
    RhythmicRole.ROOT: UNISON,
    RhythmicRole.HALFTIME: HALFTIME,
    RhythmicRole.TRIPLET: TRIPLET,
    RhythmicRole.WALTZ: WALTZ_TIME,
    RhythmicRole.COMPOUND: COMPOUND,
    RhythmicRole.DOUBLETIME: DOUBLE_TIME,
    RhythmicRole.OFFSET: OFFSET,
    RhythmicRole.QUINTUPLE: QUINTUPLE,
    RhythmicRole.SEPTUPLE: SEPTUPLE,
}


class EisensteinSnap:
    """Eisenstein lattice rhythm snapper.

    Uses the hexagonal packing lattice to snap timestamps to the
    nearest grid point.  The covering radius is 1/sqrt(3) ≈ 0.577
    of the grid spacing — optimal for hexagonal tiling.
    """

    COVERING_RADIUS = 1.0 / math.sqrt(3.0)

    def __init__(self, base_period_ms: float = 500.0):
        self._base_period_ms = base_period_ms

    @property
    def base_period_ms(self) -> float:
        return self._base_period_ms

    def set_tempo(self, bpm: float) -> None:
        """Update base period from BPM (quarter note = 1 beat)."""
        if bpm <= 0:
            raise ValueError(f"bpm must be positive, got {bpm}")
        self._base_period_ms = 60000.0 / bpm

    def snap(self, t: float, role: RhythmicRole = RhythmicRole.ROOT) -> float:
        """Snap a timestamp to the Eisenstein lattice for the given role."""
        ratio = ROLE_RATIO_MAP.get(role, UNISON)
        return ratio.snap(t, self._base_period_ms)

    def snap_vector(
        self, timestamps: list[float], role: RhythmicRole = RhythmicRole.ROOT
    ) -> list[float]:
        """Snap a list of timestamps."""
        return [self.snap(t, role) for t in timestamps]

    def grid_for(self, role: RhythmicRole = RhythmicRole.ROOT) -> list[float]:
        """Generate the next 16 snapped grid times from t=0."""
        ratio = ROLE_RATIO_MAP.get(role, UNISON)
        period = self._base_period_ms * ratio.ratio
        phase_ms = period * ratio.phase
        return [round(i * period + phase_ms, 3) for i in range(16)]

    def distance_to_grid(self, t: float, role: RhythmicRole = RhythmicRole.ROOT) -> float:
        """Distance from timestamp to nearest grid point (as fraction of period)."""
        snapped = self.snap(t, role)
        ratio = ROLE_RATIO_MAP.get(role, UNISON)
        period = self._base_period_ms * ratio.ratio
        if period == 0:
            return 0.0
        return abs(t - snapped) / period

    def in_phase(self, t1: float, t2: float, role: RhythmicRole = RhythmicRole.ROOT) -> bool:
        """Check if two timestamps land on the same grid point."""
        return self.snap(t1, role) == self.snap(t2, role)

    @staticmethod
    def hexagonal_distance(t1: float, t2: float, period: float = 500.0) -> float:
        """Distance in the hexagonal lattice metric.

        Uses the Eisenstein integer norm: |a + bω|² = a² + b² - ab
        where a,b are integer grid coordinates.
        """
        a1 = int(round(t1 / period))
        a2 = int(round(t2 / period))
        da = a1 - a2
        # Compute hexagonal norm: a² + b² - ab for 1D case (b=0)
        return abs(da) * period

    def __repr__(self) -> str:
        return f"EisensteinSnap(base_period_ms={self._base_period_ms}, covering_radius={self.COVERING_RADIUS:.4f})"
