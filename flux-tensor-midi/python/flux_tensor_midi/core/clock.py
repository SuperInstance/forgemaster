"""
TZeroClock: An EWMA-adaptive clock for PLATO room T-0 time.

Each RoomMusician has a TZeroClock that produces drift-corrected
timestamps.  Uses Exponentially Weighted Moving Average to adapt
to observed clock skew from the conductor (or any reference beat).
"""

from __future__ import annotations
import math
import time
from typing import Callable


class TZeroClock:
    """An adaptive clock using EWMA for drift correction.

    Parameters
    ----------
    alpha : float, default=0.125
        EWMA smoothing factor.  Higher = faster adapt, lower = smoother.
    reference_clock : Callable[[], float], optional
        Source of wall time in seconds.  Defaults to time.monotonic.
    initial_ticks : int, default=0
        Starting tick count.
    bpm : float, default=120.0
        Beats per minute for tick duration.
    """

    def __init__(
        self,
        alpha: float = 0.125,
        reference_clock: Callable[[], float] | None = None,
        initial_ticks: int = 0,
        bpm: float = 120.0,
    ):
        if not 0 < alpha < 1:
            raise ValueError(f"alpha must be in (0, 1), got {alpha}")
        if bpm <= 0:
            raise ValueError(f"bpm must be positive, got {bpm}")

        self._alpha = alpha
        self._clock = reference_clock or time.monotonic
        self._ticks = initial_ticks
        self._bpm = bpm

        # EWMA state
        self._drift: float = 0.0  # ms drift estimate
        self._last_wall: float = self._clock()  # last wall clock reading

        # Timing
        self._tick_duration_s: float = 60.0 / bpm  # seconds per tick
        self._start_wall: float = self._last_wall
        self._start_tick: float = 0.0  # virtual tick time at start

    @property
    def alpha(self) -> float:
        return self._alpha

    @property
    def bpm(self) -> float:
        return self._bpm

    @property
    def tick_duration_ms(self) -> float:
        return self._tick_duration_s * 1000.0

    @property
    def ticks(self) -> int:
        return self._ticks

    # ---- core operations ----

    def tick(self) -> float:
        """Advance one tick and return the corrected timestamp (ms)."""
        now = self._clock()
        expected_s = (self._ticks + 1) * self._tick_duration_s
        actual_s = now - self._start_wall

        # Observed drift in ms
        observed_drift_ms = (actual_s - expected_s) * 1000.0

        # EWMA update
        self._drift = self._alpha * observed_drift_ms + (1 - self._alpha) * self._drift

        # Corrected timestamp (ms): expected time - estimated drift
        corrected_ms = expected_s * 1000.0 - self._drift

        self._ticks += 1
        self._last_wall = now
        return corrected_ms

    def time_ms(self) -> float:
        """Current corrected time in ms (without advancing ticks)."""
        now = self._clock()
        elapsed_s = now - self._start_wall
        return elapsed_s * 1000.0 - self._drift

    def drift_ms(self) -> float:
        """Current estimated drift in ms (negative = ahead of wall)."""
        return self._drift

    def reset(self, bpm: float | None = None) -> None:
        """Reset the clock.  Optionally set a new BPM."""
        if bpm is not None:
            if bpm <= 0:
                raise ValueError(f"bpm must be positive, got {bpm}")
            self._bpm = bpm
            self._tick_duration_s = 60.0 / bpm
        self._drift = 0.0
        self._ticks = 0
        self._last_wall = self._clock()
        self._start_wall = self._last_wall
        self._start_tick = 0.0

    def set_bpm(self, bpm: float) -> None:
        """Change BPM mid-stream (preserves drift estimate)."""
        if bpm <= 0:
            raise ValueError(f"bpm must be positive, got {bpm}")
        self._bpm = bpm
        self._tick_duration_s = 60.0 / bpm

    def synchronize_to(self, other: TZeroClock) -> None:
        """Synchronize drift estimate to another clock."""
        self._drift = other._drift

    # ---- alignment ----

    def align(self, reference_timestamp: float) -> float:
        """Align clock to a reference timestamp, return correction applied."""
        current = self.time_ms()
        correction = reference_timestamp - current
        # Apply correction by adjusting start wall equivalently
        # (negative correction = we were ahead, move start_wall forward)
        self._start_wall -= correction / 1000.0
        return correction

    @classmethod
    def from_beat(cls, beat_number: int, bpm: float = 120.0, alpha: float = 0.125) -> TZeroClock:
        """Create a clock pre-advanced to a specific beat."""
        c = cls(alpha=alpha, bpm=bpm)
        for _ in range(beat_number):
            c.tick()
        return c
