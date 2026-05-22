"""Fraction-based clock — exact arithmetic, zero floating-point drift."""

from __future__ import annotations

import time
from fractions import Fraction
from dataclasses import dataclass, field


@dataclass
class FractionClock:
    """Clock using Fraction arithmetic. Never loses precision.

    Tracks true_time (monotonic Fraction counter) and offset (accumulated drift).
    The observed time is ``true_time + offset``.
    """

    true_time: Fraction = Fraction(0)
    offset: Fraction = Fraction(0)
    drift_rate: Fraction = Fraction(0)          # drift per tick
    last_correction: Fraction = Fraction(0)
    epoch_wall: float = field(default_factory=time.monotonic)

    # -- derived ----------------------------------------------------------

    @property
    def local_time(self) -> Fraction:
        return self.true_time + self.offset

    @property
    def drift(self) -> Fraction:
        return self.offset

    # -- mutators ---------------------------------------------------------

    def tick(self) -> None:
        """Advance one logical tick. Offset grows by drift_rate."""
        self.true_time += Fraction(1)
        self.offset += self.drift_rate

    def correct(self, delta: Fraction) -> None:
        """Apply a clock correction (additive)."""
        self.offset += delta
        self.last_correction = delta

    def snap_to(self, reference: Fraction) -> None:
        """Hard-set offset so that local_time == reference."""
        self.offset = reference - self.true_time

    def elapsed_wall(self) -> float:
        """Wall-clock seconds since this clock was created / last reset."""
        return time.monotonic() - self.epoch_wall
