"""metronome.py — Phase-coupled metronome with deadband convergence.

Each Metronome has a period T, initial phase phi0, precision epsilon (deadband),
and correction threshold delta. Agents tick and then correct toward their
neighbors' phases. The deadband (delta) prevents micro-corrections, leading
to convergence within delta.

Based on the Kuramoto-style coupling with a deadband refinement:
  - tick(): advance phase by 2π/T
  - correct(neighbor_phases): pull phase toward neighbors if mean deviation > delta
  - observe(x, y): feed external observation to narrow epsilon (via lattice snap)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from fractions import Fraction
from typing import List, Optional, Tuple

from .lattice import snap, covering_radius

__all__ = ["Metronome", "MetronomeState"]

_TWO_PI = 2.0 * math.pi


@dataclass
class MetronomeState:
    """Snapshot of metronome state for inheritance."""
    epsilon: float
    delta: float
    phase: float
    anomaly_count: int


class Metronome:
    """Phase-coupled metronome agent.

    Args:
        T: Period (seconds).
        phi0: Initial phase (radians).
        epsilon: Precision (deadband for observations).
        delta: Convergence threshold (deadband for neighbor correction).
        neighbors: List of neighbor agent indices.
        edges: Global edge list (optional, for topology reference).
        n_agents: Total number of agents in the network.
    """

    def __init__(
        self,
        T: float = 1.0,
        phi0: float = 0.0,
        epsilon: Optional[float] = None,
        delta: Optional[float] = None,
        neighbors: Optional[List[int]] = None,
        edges: Optional[List[Tuple[int, int]]] = None,
        n_agents: int = 1,
    ):
        self.T = T
        self.phase = phi0
        self.epsilon = float(epsilon if epsilon is not None else covering_radius())
        self.delta = float(delta if delta is not None else covering_radius())
        self.neighbors = neighbors or []
        self.edges = edges or []
        self.n_agents = n_agents

        self.tick_count = 0
        self.anomaly_count = 0
        self.converged = False

    def tick(self):
        """Advance one tick: phase += 2π/T."""
        self.phase = (self.phase + _TWO_PI / self.T) % _TWO_PI
        self.tick_count += 1

    def correct(self, neighbor_phases: List[float]):
        """Pull phase toward the mean of neighbor phases.

        Uses all-to-all coupling with deadband: if the circular distance
        is within delta, applies a gentle (10%) correction to tighten
        further; if beyond delta, applies a stronger (50%) correction.
        """
        if not neighbor_phases:
            self.converged = True
            return

        # Circular mean of neighbor phases
        sin_sum = sum(math.sin(p) for p in neighbor_phases)
        cos_sum = sum(math.cos(p) for p in neighbor_phases)
        mean_phase = math.atan2(sin_sum, cos_sum) % _TWO_PI

        # Circular distance
        diff = mean_phase - self.phase
        diff = (diff + math.pi) % _TWO_PI - math.pi  # wrap to [-π, π]

        if abs(diff) <= self.delta:
            # Within deadband — apply small tightening correction
            # to drive convergence below delta over time.
            self.phase = (self.phase + diff * 0.1) % _TWO_PI
            self.converged = True
        else:
            # Apply 50% correction toward mean
            self.phase = (self.phase + diff * 0.5) % _TWO_PI
            self.converged = False

    def observe(self, x: float, y: float):
        """Process a lattice observation to narrow epsilon.

        Snaps (x, y) to Eisenstein lattice; if the snap error is within
        the current epsilon, narrows epsilon by 0.5%.
        """
        _, _, error = snap(x, y)
        if error < self.epsilon:
            self.epsilon *= 0.995
        else:
            self.anomaly_count += 1

    def state(self) -> MetronomeState:
        """Return a snapshot of current state."""
        return MetronomeState(
            epsilon=self.epsilon,
            delta=self.delta,
            phase=self.phase,
            anomaly_count=self.anomaly_count,
        )
