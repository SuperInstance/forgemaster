"""T-0 clock with EWMA adaptation.

The T-0 clock is an agent's temporal expectation engine.
It tracks when the next "tick" should happen, adapts its interval
using exponentially weighted moving averages, and reports drift.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TZeroClock:
    """Agent's temporal expectation clock with EWMA adaptation.

    The clock tracks an expected interval and learns from actual
    observations using exponential moving average.

    Attributes:
        interval: Expected interval in seconds.
        adaptive: Whether to use EWMA to adjust the interval.
    """

    interval: float = 300.0
    adaptive: bool = True

    def __post_init__(self) -> None:
        self._t_last: float = time.time()
        self._t_zero: float = self._t_last + self.interval
        self._ewma_alpha: float = 0.1
        self._tick_count: int = 0

    @property
    def t_zero(self) -> float:
        """When the next tick is expected."""
        return self._t_zero

    @property
    def t_last(self) -> float:
        """When the last tick occurred."""
        return self._t_last

    @property
    def tick_count(self) -> int:
        """Total ticks since creation."""
        return self._tick_count

    @property
    def bpm(self) -> float:
        """Convert current interval to BPM (beats per minute).

        A 300s interval = 0.2 BPM (very slow).
        A 1s interval = 60 BPM.
        A 0.5s interval = 120 BPM.
        """
        if self.interval <= 0:
            return 0.0
        return 60.0 / self.interval

    @bpm.setter
    def bpm(self, value: float) -> None:
        """Set interval from BPM value."""
        if value > 0:
            self.interval = 60.0 / value
            self._recalculate_t_zero()

    def _recalculate_t_zero(self) -> None:
        """Recalculate t_zero from t_last and current interval."""
        self._t_zero = self._t_last + self.interval

    def tick(self) -> Optional[float]:
        """Check if T-0 has passed.

        Returns:
            Delta (actual - expected) if T-0 passed, None if on time.
            Positive delta = late, negative delta = early.
        """
        now = time.time()
        if now >= self._t_zero:
            actual_interval = now - self._t_last
            delta = actual_interval - self.interval
            self._t_last = now
            self._tick_count += 1

            if self.adaptive:
                self.observe(actual_interval)

            self._recalculate_t_zero()
            return delta
        return None

    def observe(self, actual_interval: float) -> None:
        """Learn from actual interval using EWMA.

        Args:
            actual_interval: The observed interval in seconds.
        """
        self.interval = (
            self._ewma_alpha * actual_interval
            + (1.0 - self._ewma_alpha) * self.interval
        )
        self.interval = max(0.01, self.interval)  # Floor at 10ms

    def missed_ticks(self, elapsed: Optional[float] = None) -> int:
        """How many expected ticks were missed in the elapsed time.

        Args:
            elapsed: Time elapsed. Defaults to time since last tick.

        Returns:
            Number of missed ticks (0 if none missed).
        """
        if elapsed is None:
            elapsed = time.time() - self._t_last
        if self.interval <= 0:
            return 0
        expected = elapsed / self.interval
        actual = elapsed / (elapsed + 0.001)
        return max(0, int(expected) - 1)

    def reset(self, interval: Optional[float] = None) -> None:
        """Reset the clock.

        Args:
            interval: New interval. Defaults to current.
        """
        if interval is not None:
            self.interval = interval
        self._t_last = time.time()
        self._recalculate_t_zero()

    def remaining(self) -> float:
        """Seconds until next T-0."""
        return max(0.0, self._t_zero - time.time())

    def __repr__(self) -> str:
        return (
            f"TZeroClock(interval={self.interval:.2f}s, "
            f"bpm={self.bpm:.1f}, ticks={self._tick_count})"
        )
