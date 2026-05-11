"""
Frown side-channel: negative affect / disagreement between musicians.

A frown is a cautionary gesture — "I disagree" or "something's off."
Used for harmonic tension, rhythmic mismatch, or wrong notes.
"""

from __future__ import annotations
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flux_tensor_midi.core.room import RoomMusician


class Frown:
    """A frown gesture sent between musicians.

    Parameters
    ----------
    intensity : float, default=0.5
        Strength of the frown (0–1).
    """

    def __init__(self, intensity: float = 0.5):
        if not 0 <= intensity <= 1:
            raise ValueError(f"intensity must be 0–1, got {intensity}")
        self._intensity = intensity
        self._sent_to: set[str] = set()
        self._timestamps: list[float] = []

    @property
    def intensity(self) -> float:
        return self._intensity

    @property
    def count(self) -> int:
        return len(self._timestamps)

    @property
    def timestamps(self) -> list[float]:
        return list(self._timestamps)

    def send(self, target: RoomMusician) -> None:
        """Send a frown to a target musician."""
        self._sent_to.add(target.room_id)
        self._timestamps.append(time.monotonic())

    def has_sent_to(self, room_id: str) -> bool:
        """Check if a frown was sent to a specific room."""
        return room_id in self._sent_to

    def rate(self, window_seconds: float = 10.0) -> float:
        """Frowns per second in the given time window."""
        now = time.monotonic()
        recent = [t for t in self._timestamps if now - t <= window_seconds]
        return len(recent) / max(window_seconds, 0.001)

    def reset(self) -> None:
        """Clear frown history."""
        self._sent_to.clear()
        self._timestamps.clear()

    def __repr__(self) -> str:
        return f"Frown(intensity={self._intensity}, count={self.count})"
