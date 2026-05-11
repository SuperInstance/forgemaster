"""
Temporal snap — T-minus-0 detection and beat grid alignment — OPTIMIZED.

Changes from baseline:
  - BeatGrid uses __slots__ with precomputed _inv_period
  - TemporalSnap uses circular buffer (no list slicing)
  - Batch operations
  - Type hints on signatures only
"""

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass(frozen=True, slots=True)
class TemporalResult:
    original_time: float
    snapped_time: float
    offset: float
    is_on_beat: bool
    is_t_minus_0: bool
    beat_index: int
    beat_phase: float


class BeatGrid:
    """A periodic grid of time points."""
    __slots__ = ('period', 'phase', 't_start', '_inv_period')

    def __init__(self, period: float = 1.0, phase: float = 0.0, t_start: float = 0.0):
        if period <= 0:
            raise ValueError("period must be positive")
        self.period = period
        self.phase = phase
        self.t_start = t_start
        self._inv_period = 1.0 / period

    def nearest_beat(self, t: float) -> Tuple[float, int]:
        adjusted = t - self.t_start - self.phase
        index = round(adjusted * self._inv_period)
        beat_time = self.t_start + self.phase + index * self.period
        return beat_time, index

    def snap(self, t: float, tolerance: float = 0.1) -> TemporalResult:
        beat_time, beat_index = self.nearest_beat(t)
        offset = t - beat_time
        is_on_beat = abs(offset) <= tolerance
        phase = ((t - self.t_start - self.phase) % self.period) * self._inv_period
        if phase < 0:
            phase += 1.0

        return TemporalResult(
            original_time=t, snapped_time=beat_time,
            offset=offset, is_on_beat=is_on_beat,
            is_t_minus_0=False, beat_index=beat_index,
            beat_phase=phase,
        )

    def snap_batch(
        self,
        timestamps: List[float],
        tolerance: float = 0.1,
    ) -> List[TemporalResult]:
        """Snap multiple timestamps to the beat grid."""
        return [self.snap(t, tolerance) for t in timestamps]

    def beats_in_range(self, t_start: float, t_end: float) -> List[float]:
        if t_end <= t_start:
            return []
        first_idx = math.ceil((t_start - self.t_start - self.phase) * self._inv_period)
        last_idx = math.floor((t_end - self.t_start - self.phase) * self._inv_period)
        return [
            self.t_start + self.phase + i * self.period
            for i in range(first_idx, last_idx + 1)
        ]


class TemporalSnap:
    """Temporal snap with T-minus-0 detection."""
    __slots__ = ('grid', 'tolerance', 't0_threshold', 't0_window',
                 '_history', '_hist_idx', '_hist_len', '_hist_cap')

    def __init__(
        self,
        grid: BeatGrid,
        tolerance: float = 0.1,
        t0_threshold: float = 0.05,
        t0_window: int = 3,
    ):
        self.grid = grid
        self.tolerance = tolerance
        self.t0_threshold = t0_threshold
        self.t0_window = max(2, t0_window)
        self._hist_cap = self.t0_window * 2
        self._history = [None] * self._hist_cap
        self._hist_idx = 0
        self._hist_len = 0

    def observe(self, t: float, value: float) -> TemporalResult:
        self._history[self._hist_idx] = (t, value)
        self._hist_idx = (self._hist_idx + 1) % self._hist_cap
        if self._hist_len < self._hist_cap:
            self._hist_len += 1

        is_t0 = self._detect_t0()

        result = self.grid.snap(t, self.tolerance)
        return TemporalResult(
            original_time=result.original_time,
            snapped_time=result.snapped_time,
            offset=result.offset,
            is_on_beat=result.is_on_beat,
            is_t_minus_0=is_t0,
            beat_index=result.beat_index,
            beat_phase=result.beat_phase,
        )

    def _detect_t0(self) -> bool:
        if self._hist_len < 3:
            return False

        cap = self._hist_cap
        idx = self._hist_idx

        curr_t, curr_val = self._history[(idx - 1) % cap]
        mid_t, mid_val = self._history[(idx - 2) % cap]
        prev_t, prev_val = self._history[(idx - 3) % cap]

        if abs(curr_val) > self.t0_threshold:
            return False

        dt1 = mid_t - prev_t
        dt2 = curr_t - mid_t
        if dt1 == 0 or dt2 == 0:
            return False

        d1 = (mid_val - prev_val) / dt1
        d2 = (curr_val - mid_val) / dt2

        return d1 * d2 < 0

    def reset(self) -> None:
        self._hist_idx = 0
        self._hist_len = 0

    @property
    def history(self) -> List[Tuple[float, float]]:
        result = []
        for i in range(self._hist_len):
            idx = (self._hist_idx - self._hist_len + i) % self._hist_cap
            val = self._history[idx]
            if val is not None:
                result.append(val)
        return result
