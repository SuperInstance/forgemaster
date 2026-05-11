"""Multi-dimensional state tensor for room coordination.

The Tensor tracks temporal, harmonic, and side-channel dimensions
of a room's state at a given moment.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class TensorSlice:
    """A single time-slice of the multi-dimensional tensor.

    Attributes:
        timestamp: When this slice was captured (epoch seconds).
        flux_saliences: FLUX 9-channel salience snapshot.
        harmony_scores: Per-room harmony scores.
        side_channels: Side-channel signal states.
        metadata: Arbitrary metadata.
    """
    timestamp: float
    flux_saliences: List[float]
    harmony_scores: Dict[str, float] = field(default_factory=dict)
    side_channels: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class Tensor:
    """Multi-dimensional state tensor for a room musician.

    Tracks temporal evolution of FLUX, harmony, and side-channels.
    Supports entropy and trend analysis.
    """

    def __init__(self, max_history: int = 1000) -> None:
        """Initialize tensor.

        Args:
            max_history: Maximum number of slices to retain.
        """
        self.max_history = max_history
        self._slices: List[TensorSlice] = []

    def record(
        self,
        saliences: List[float],
        harmony_scores: Optional[Dict[str, float]] = None,
        side_channels: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[float] = None,
    ) -> TensorSlice:
        """Record a new tensor slice.

        Args:
            saliences: Current FLUX salience values.
            harmony_scores: Current harmony scores with other rooms.
            side_channels: Current side-channel states.
            metadata: Arbitrary metadata for this slice.
            timestamp: Override timestamp (defaults to now).

        Returns:
            The recorded TensorSlice.
        """
        slice_obj = TensorSlice(
            timestamp=timestamp or time.time(),
            flux_saliences=list(saliences),
            harmony_scores=dict(harmony_scores or {}),
            side_channels=dict(side_channels or {}),
            metadata=dict(metadata or {}),
        )
        self._slices.append(slice_obj)
        if len(self._slices) > self.max_history:
            self._slices = self._slices[-self.max_history:]
        return slice_obj

    @property
    def slices(self) -> List[TensorSlice]:
        """Return all recorded slices."""
        return list(self._slices)

    @property
    def latest(self) -> Optional[TensorSlice]:
        """Return the most recent slice, or None if empty."""
        return self._slices[-1] if self._slices else None

    def flux_entropy(self) -> float:
        """Compute Shannon entropy of the latest FLUX salience distribution.

        Returns:
            Entropy in bits. Higher = more spread attention.
        """
        if not self._slices:
            return 0.0
        s = self._slices[-1].flux_saliences
        total = sum(s)
        if total == 0:
            return 0.0
        probs = [v / total for v in s if v > 0]
        return -sum(p * math.log2(p) for p in probs)

    def flux_trend(self, channel: int, window: int = 10) -> float:
        """Compute trend (linear regression slope) for a FLUX channel.

        Args:
            channel: Channel index (0-8).
            window: Number of recent slices to consider.

        Returns:
            Slope of the trend (positive = increasing).
        """
        recent = self._slices[-window:]
        if len(recent) < 2:
            return 0.0
        n = len(recent)
        xs = list(range(n))
        ys = [s.flux_saliences[channel] for s in recent]
        mean_x = sum(xs) / n
        mean_y = sum(ys) / n
        cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
        var_x = sum((x - mean_x) ** 2 for x in xs)
        return cov / var_x if var_x > 0 else 0.0

    def harmony_trend(self, room_id: str, window: int = 10) -> float:
        """Compute trend for harmony score with a specific room.

        Args:
            room_id: Target room identifier.
            window: Number of recent slices.

        Returns:
            Slope of harmony trend.
        """
        recent = self._slices[-window:]
        if len(recent) < 2:
            return 0.0
        n = len(recent)
        xs = list(range(n))
        ys = [s.harmony_scores.get(room_id, 0.0) for s in recent]
        mean_x = sum(xs) / n
        mean_y = sum(ys) / n
        cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
        var_x = sum((x - mean_x) ** 2 for x in xs)
        return cov / var_x if var_x > 0 else 0.0

    def interval_sequence(self) -> List[float]:
        """Return the sequence of intervals between consecutive slices."""
        if len(self._slices) < 2:
            return []
        return [
            self._slices[i + 1].timestamp - self._slices[i].timestamp
            for i in range(len(self._slices) - 1)
        ]

    def __len__(self) -> int:
        return len(self._slices)

    def __repr__(self) -> str:
        return f"Tensor(slices={len(self._slices)}, entropy={self.flux_entropy():.3f})"
