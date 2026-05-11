"""FLUX 9-channel intent vector with salience and tolerance per channel.

Each channel represents a dimension of attention:
  0: Temporal    — time/interval awareness
  1: Harmonic    — relationship to others
  2: Structural  — code/architecture focus
  3: Semantic    — meaning/content
  4: Social      — coordination/communication
  5: Resource    — compute/memory/bandwidth
  6: Error       — anomaly/delta detection
  7: Creative    — novelty/exploration
  8: Meta        — self-monitoring
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class FluxChannel:
    """Single channel of the FLUX intent vector.

    Attributes:
        index: Channel index (0-8).
        salience: How much attention this channel gets [0.0, 1.0].
        tolerance: Acceptable deviation before flagging [0.0, 1.0].
        label: Human-readable channel name.
    """
    index: int
    salience: float = 0.5
    tolerance: float = 0.5
    label: str = ""

    def __post_init__(self) -> None:
        self.salience = max(0.0, min(1.0, self.salience))
        self.tolerance = max(0.0, min(1.0, self.tolerance))
        if not self.label:
            self.label = _CHANNEL_LABELS[self.index] if self.index < len(_CHANNEL_LABELS) else f"ch{self.index}"

    def weighted_value(self) -> float:
        """Return salience adjusted by tolerance (high tolerance = less reactive)."""
        return self.salience * (1.0 - self.tolerance * 0.5)

    def adapt(self, target: float, learning_rate: float = 0.1) -> None:
        """Move salience toward target by learning_rate.

        Args:
            target: Target salience value.
            learning_rate: How fast to adapt [0.0, 1.0].
        """
        self.salience += learning_rate * (target - self.salience)
        self.salience = max(0.0, min(1.0, self.salience))


@dataclass
class Alignment:
    """Result of comparing two FLUX vectors.

    Attributes:
        cosine_similarity: Cosine similarity of salience vectors [-1, 1].
        in_tolerance: Whether all channels are within each other's tolerance.
        channel_deltas: Per-channel absolute differences.
        overall: Composite alignment score [0, 1].
    """
    cosine_similarity: float
    in_tolerance: bool
    channel_deltas: List[float]
    overall: float


CHANNEL_NAMES = [
    "temporal", "harmonic", "structural", "semantic", "social",
    "resource", "error", "creative", "meta",
]

_CHANNEL_LABELS = CHANNEL_NAMES


class FluxVector:
    """9-channel intent vector with salience and tolerance per channel.

    The FLUX vector represents what a room is paying attention to
    and how sensitive it is to deviations in each dimension.
    """

    NUM_CHANNELS = 9

    def __init__(
        self,
        saliences: Optional[List[float]] = None,
        tolerances: Optional[List[float]] = None,
    ) -> None:
        """Initialize FLUX vector.

        Args:
            saliences: Per-channel salience values (9 elements). Defaults to 0.5.
            tolerances: Per-channel tolerance values (9 elements). Defaults to 0.5.
        """
        if saliences and len(saliences) != self.NUM_CHANNELS:
            raise ValueError(f"Expected {self.NUM_CHANNELS} salience values, got {len(saliences)}")
        if tolerances and len(tolerances) != self.NUM_CHANNELS:
            raise ValueError(f"Expected {self.NUM_CHANNELS} tolerance values, got {len(tolerances)}")

        s = saliences or [0.5] * self.NUM_CHANNELS
        t = tolerances or [0.5] * self.NUM_CHANNELS
        self.channels: List[FluxChannel] = [
            FluxChannel(index=i, salience=s[i], tolerance=t[i], label=CHANNEL_NAMES[i])
            for i in range(self.NUM_CHANNELS)
        ]

    def salience_vector(self) -> List[float]:
        """Return the salience values as a plain list."""
        return [ch.salience for ch in self.channels]

    def tolerance_vector(self) -> List[float]:
        """Return the tolerance values as a plain list."""
        return [ch.tolerance for ch in self.channels]

    def check_alignment(self, other: FluxVector) -> Alignment:
        """Compute alignment between this and another FLUX vector.

        Uses cosine similarity on salience vectors and checks
        per-channel tolerance bounds.

        Args:
            other: The other FLUX vector to compare against.

        Returns:
            Alignment with cosine similarity, tolerance check, and deltas.
        """
        sv = self.salience_vector()
        ov = other.salience_vector()

        # Cosine similarity
        dot = sum(a * b for a, b in zip(sv, ov))
        mag_a = math.sqrt(sum(a * a for a in sv))
        mag_b = math.sqrt(sum(b * b for b in ov))
        if mag_a == 0 or mag_b == 0:
            cosine = 0.0
        else:
            cosine = dot / (mag_a * mag_b)

        # Per-channel deltas and tolerance check
        deltas = [abs(a - b) for a, b in zip(sv, ov)]
        in_tol = all(
            deltas[i] <= max(self.channels[i].tolerance, other.channels[i].tolerance)
            for i in range(self.NUM_CHANNELS)
        )

        # Composite score: average of (1 - normalized_delta) weighted by salience
        total_weight = sum(max(ch.salience, 0.01) for ch in self.channels)
        weighted_alignment = sum(
            max(ch.salience, 0.01) * (1.0 - deltas[i])
            for i, ch in enumerate(self.channels)
        ) / total_weight

        return Alignment(
            cosine_similarity=cosine,
            in_tolerance=in_tol,
            channel_deltas=deltas,
            overall=weighted_alignment,
        )

    def adapt(self, observation: Any, learning_rate: float = 0.1) -> None:
        """Adapt salience based on an observation.

        The observation can be:
          - A dict mapping channel names/indices to target salience values.
          - A list of 9 target salience values.
          - A float to apply uniformly.
          - An Alignment result to move toward.

        Args:
            observation: What to learn from.
            learning_rate: How fast to adapt [0.0, 1.0].
        """
        if isinstance(observation, dict):
            for key, value in observation.items():
                if isinstance(key, int) and 0 <= key < self.NUM_CHANNELS:
                    self.channels[key].adapt(float(value), learning_rate)
                elif isinstance(key, str):
                    for ch in self.channels:
                        if ch.label == key or ch.label.startswith(key):
                            ch.adapt(float(value), learning_rate)
        elif isinstance(observation, (list, tuple)):
            for i, val in enumerate(observation):
                if i < self.NUM_CHANNELS:
                    self.channels[i].adapt(float(val), learning_rate)
        elif isinstance(observation, float):
            for ch in self.channels:
                ch.adapt(observation, learning_rate)
        elif isinstance(observation, Alignment):
            for i, delta in enumerate(observation.channel_deltas):
                target = self.channels[i].salience + delta * 0.5
                self.channels[i].adapt(min(1.0, target), learning_rate)

    def copy(self) -> FluxVector:
        """Return a deep copy of this FLUX vector."""
        return FluxVector(
            saliences=self.salience_vector(),
            tolerances=self.tolerance_vector(),
        )

    def __repr__(self) -> str:
        parts = []
        for ch in self.channels:
            parts.append(f"{ch.label[:3]}:{ch.salience:.2f}/{ch.tolerance:.2f}")
        return f"FluxVector([{', '.join(parts)}])"
