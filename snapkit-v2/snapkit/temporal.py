"""
Temporal snap — T-minus-0 detection and beat grid alignment.

Detects when a temporal signal reaches a critical point (T-0) and
snaps observations to the nearest beat grid. This is the temporal
analog of the Eisenstein spatial snap: instead of snapping to a
hexagonal lattice in the complex plane, we snap to a 1D grid on
the time axis.

Key concepts:
  - BeatGrid: a periodic grid of time points with configurable phase.
  - T-minus-0: the moment a signal transitions from "approaching" to
    "arrived" — analogous to the snap boundary in spatial algorithms.
  - TemporalSnap: combines beat grid alignment with T-0 detection.
"""

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass(frozen=True, slots=True)
class TemporalResult:
    """Result of a temporal snap operation."""
    original_time: float
    snapped_time: float
    offset: float           # signed distance to nearest grid point
    is_on_beat: bool        # |offset| ≤ tolerance
    is_t_minus_0: bool      # T-0 event detected
    beat_index: int         # index of nearest beat (0-based)
    beat_phase: float       # phase within current beat cycle [0, 1)


@dataclass
class BeatGrid:
    """A periodic grid of time points.

    Attributes:
        period: interval between beats (seconds).
        phase: offset of beat 0 from t=0 (seconds, 0 ≤ phase < period).
        t_start: start time of the grid (seconds).
    """
    period: float = 1.0
    phase: float = 0.0
    t_start: float = 0.0

    def nearest_beat(self, t: float) -> Tuple[float, int]:
        """Find the nearest grid point to time t.

        Returns (beat_time, beat_index).
        """
        if self.period <= 0:
            raise ValueError("period must be positive")
        adjusted = t - self.t_start - self.phase
        index_float = adjusted / self.period
        index = round(index_float)
        beat_time = self.t_start + self.phase + index * self.period
        return beat_time, int(index)

    def snap(self, t: float, tolerance: float = 0.1) -> TemporalResult:
        """Snap time t to the nearest beat within tolerance.

        Args:
            t: Time to snap.
            tolerance: Maximum offset for on-beat classification.

        Returns:
            TemporalResult with snap details.
        """
        beat_time, beat_index = self.nearest_beat(t)
        offset = t - beat_time
        is_on_beat = abs(offset) <= tolerance
        phase = ((t - self.t_start - self.phase) % self.period) / self.period
        if phase < 0:
            phase += 1.0

        return TemporalResult(
            original_time=t,
            snapped_time=beat_time,
            offset=offset,
            is_on_beat=is_on_beat,
            is_t_minus_0=False,
            beat_index=beat_index,
            beat_phase=phase,
        )

    def beats_in_range(self, t_start: float, t_end: float) -> List[float]:
        """List all beat times in [t_start, t_end]."""
        if t_end <= t_start:
            return []
        first_idx = math.ceil((t_start - self.t_start - self.phase) / self.period)
        last_idx = math.floor((t_end - self.t_start - self.phase) / self.period)
        return [
            self.t_start + self.phase + i * self.period
            for i in range(first_idx, last_idx + 1)
        ]


class TemporalSnap:
    """Temporal snap with T-minus-0 detection.

    T-0 detection works by monitoring a stream of observations and
    detecting when the signal crosses a threshold (approaches zero
    derivative, or crosses a critical value). This is the temporal
    equivalent of the Eisenstein snap boundary.

    The detector uses a simple sliding-window approach:
    - Track the last N observations.
    - T-0 fires when the derivative crosses zero (local extremum)
      AND the value is within a critical zone.
    """

    def __init__(
        self,
        grid: BeatGrid,
        tolerance: float = 0.1,
        t0_threshold: float = 0.05,
        t0_window: int = 3,
    ):
        """
        Args:
            grid: Beat grid for snap alignment.
            tolerance: Maximum offset for on-beat classification.
            t0_threshold: Value threshold for T-0 zone.
            t0_window: Window size for derivative estimation.
        """
        self.grid = grid
        self.tolerance = tolerance
        self.t0_threshold = t0_threshold
        self.t0_window = max(2, t0_window)
        self._history: List[Tuple[float, float]] = []  # (time, value)

    def observe(self, t: float, value: float) -> TemporalResult:
        """Observe a (time, value) pair and snap.

        T-0 is detected when:
          1. The value is within t0_threshold of zero (critical zone).
          2. The derivative (estimated from window) crosses zero.
        """
        self._history.append((t, value))
        if len(self._history) > self.t0_window * 2:
            self._history = self._history[-self.t0_window * 2:]

        # T-0 detection
        is_t0 = self._detect_t0()

        result = self.grid.snap(t, self.tolerance)
        # Override the T-0 flag from the grid snap
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
        """Detect T-minus-0 from observation history.

        T-0 fires when:
          - Value is in the critical zone (|value| ≤ threshold).
          - Derivative sign change detected in the window.
        """
        if len(self._history) < 2:
            return False

        # Check if current value is in critical zone
        _, current_val = self._history[-1]
        if abs(current_val) > self.t0_threshold:
            return False

        # Estimate derivative from recent observations
        if len(self._history) >= self.t0_window:
            recent = self._history[-self.t0_window:]
            dt = recent[-1][0] - recent[0][0]
            if dt == 0:
                return False
            dv = recent[-1][1] - recent[0][1]
            deriv_current = dv / dt
        else:
            _, prev_val = self._history[-2]
            _, curr_val = self._history[-1]
            prev_t, curr_t = self._history[-2][0], self._history[-1][0]
            dt = curr_t - prev_t
            if dt == 0:
                return False
            deriv_current = (curr_val - prev_val) / dt

        # Check for derivative sign change (zero crossing)
        if len(self._history) >= 3:
            prev_t, prev_val = self._history[-3]
            mid_t, mid_val = self._history[-2]
            curr_t, curr_val = self._history[-1]
            d1 = (mid_val - prev_val) / (mid_t - prev_t) if (mid_t - prev_t) != 0 else 0
            d2 = (curr_val - mid_val) / (curr_t - mid_t) if (curr_t - mid_t) != 0 else 0
            # Sign change in derivative
            return d1 * d2 < 0

        return False

    def reset(self) -> None:
        """Clear observation history."""
        self._history.clear()

    @property
    def history(self) -> List[Tuple[float, float]]:
        """Read-only access to observation history."""
        return list(self._history)
