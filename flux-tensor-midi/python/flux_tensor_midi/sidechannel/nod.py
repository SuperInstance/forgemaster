"""
Nod side-channel: agreement / acknowledgment between musicians.

A nod is a gentle, affirmative gesture — "I hear you, I agree."
Used for beat alignment, phrase boundaries, and chord changes.
"""

from __future__ import annotations
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flux_tensor_midi.core.room import RoomMusician


class Nod:
    """A nod gesture sent between musicians.

    Parameters
    ----------
    intensity : float, default=0.5
        Strength of the nod (0–1).
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
        """Send a nod to a target musician."""
        self._sent_to.add(target.room_id)
        self._timestamps.append(time.monotonic())

    def has_sent_to(self, room_id: str) -> bool:
        """Check if a nod was sent to a specific room."""
        return room_id in self._sent_to

    def rate(self, window_seconds: float = 10.0) -> float:
        """Nods per second in the given time window."""
        now = time.monotonic()
        recent = [t for t in self._timestamps if now - t <= window_seconds]
        return len(recent) / max(window_seconds, 0.001)

    def reset(self) -> None:
        """Clear nod history."""
        self._sent_to.clear()
        self._timestamps.clear()

    def __repr__(self) -> str:
        return f"Nod(intensity={self._intensity}, count={self.count})"
