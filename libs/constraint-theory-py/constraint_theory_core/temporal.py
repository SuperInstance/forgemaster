"""temporal.py — TemporalAgent with funnel-phase anomaly detection.

The TemporalAgent observes (x, y) pairs over time, snaps each observation
to the Eisenstein lattice, and tracks whether the snap error stays within
a narrowing deadband (epsilon). Anomalies are flagged when the error
exceeds the current deadband.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

from .lattice import snap, covering_radius

__all__ = ["FunnelPhase", "ObservationResult", "TemporalAgent"]


class FunnelPhase(Enum):
    """Funnel phases for anomaly detection."""
    NORMAL = auto()
    CONVERGING = auto()
    ANOMALY = auto()


@dataclass
class ObservationResult:
    """Result of a single TemporalAgent.observe() call."""
    x: float
    y: float
    error: float
    deadband: float
    phase: FunnelPhase


class TemporalAgent:
    """Temporal agent with Eisenstein lattice snapping and funnel-phase detection.

    The deadband (epsilon) narrows over time via exponential decay, creating
    a "funnel" that tightens precision requirements as the system converges.
    """

    def __init__(
        self,
        decay_rate: float = 0.01,
        epsilon_0: Optional[float] = None,
        delta: Optional[float] = None,
        anomaly_sigma: Optional[float] = None,
        learning_rate: Optional[float] = None,
    ):
        self.decay_rate = decay_rate
        self.epsilon = float(epsilon_0 if epsilon_0 is not None else covering_radius())
        self.delta = float(delta if delta is not None else covering_radius())
        self.anomaly_sigma = float(anomaly_sigma if anomaly_sigma is not None else 2.0)
        self.learning_rate = float(learning_rate if learning_rate is not None else 0.01)

        self._observations: list[tuple[float, float]] = []
        self._errors: list[float] = []
        self.anomaly_count = 0
        self._tick = 0

    def observe(self, x: float, y: float, t: Optional[float] = None) -> ObservationResult:
        """Process an observation and return the funnel-phase result.

        Anomaly detection uses delta (the hard covering-radius bound) as the
        threshold. Epsilon is the precision target that narrows over time,
        but it does not trigger anomalies — it only drives convergence.
        """
        self._tick += 1
        self._observations.append((x, y))

        _, _, error = snap(x, y)
        self._errors.append(error)

        # Exponential decay of epsilon (precision tightens)
        self.epsilon *= (1.0 - self.decay_rate)

        # Anomaly: only when error exceeds delta (the hard bound).
        # The Eisenstein covering radius ρ guarantees error ≤ ρ,
        # so if delta = ρ, anomalies are impossible.
        if error > self.delta:
            phase = FunnelPhase.ANOMALY
            self.anomaly_count += 1
        elif error > self.epsilon:
            phase = FunnelPhase.CONVERGING
        else:
            phase = FunnelPhase.NORMAL

        return ObservationResult(
            x=x, y=y, error=error, deadband=self.epsilon, phase=phase
        )

    def summary(self) -> dict:
        """Return a summary of the agent's state."""
        return {
            "tick": self._tick,
            "epsilon": self.epsilon,
            "delta": self.delta,
            "anomaly_count": self.anomaly_count,
            "mean_error": sum(self._errors) / len(self._errors) if self._errors else 0.0,
            "max_error": max(self._errors) if self._errors else 0.0,
            "n_observations": len(self._observations),
        }

    def state(self) -> "TemporalAgent":
        """Return self (compatible with metronome state() interface)."""
        return self
