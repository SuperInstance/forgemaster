"""
MIDI event representation for FLUX-Tensor-MIDI.

Maps FluxVector channels to MIDI note events.
"""

from __future__ import annotations
from enum import IntEnum


class NoteName(IntEnum):
    """MIDI note numbers for a 9-channel mapping (C4..D5)."""
    C4 = 60
    D4 = 62
    E4 = 64
    F4 = 65
    G4 = 67
    A4 = 69
    B4 = 71
    C5 = 72
    D5 = 74


class MidiEvent:
    """A single MIDI note event.

    Parameters
    ----------
    note : int
        MIDI note number (0–127).
    velocity : int
        Note velocity (0–127).
    start_ms : float
        Start time in milliseconds.
    duration_ms : float
        Duration in milliseconds.
    channel : int, default=0
        MIDI channel (0–15).
    """

    def __init__(
        self,
        note: int,
        velocity: int,
        start_ms: float,
        duration_ms: float,
        channel: int = 0,
    ):
        if not 0 <= note <= 127:
            raise ValueError(f"note must be 0–127, got {note}")
        if not 0 <= velocity <= 127:
            raise ValueError(f"velocity must be 0–127, got {velocity}")
        if not 0 <= channel <= 15:
            raise ValueError(f"channel must be 0–15, got {channel}")
        if duration_ms < 0:
            raise ValueError(f"duration_ms must be >= 0, got {duration_ms}")

        self._note = note
        self._velocity = velocity
        self._start_ms = start_ms
        self._duration_ms = duration_ms
        self._channel = channel

    # ---- properties ----

    @property
    def note(self) -> int:
        return self._note

    @property
    def velocity(self) -> int:
        return self._velocity

    @property
    def start_ms(self) -> float:
        return self._start_ms

    @property
    def duration_ms(self) -> float:
        return self._duration_ms

    @property
    def end_ms(self) -> float:
        return self._start_ms + self._duration_ms

    @property
    def channel(self) -> int:
        return self._channel

    # ---- MIDI wire helpers ----

    def note_on_bytes(self) -> tuple[int, int, int]:
        """Return (status, note, velocity) for a Note On message.

        status = 0x90 | channel
        """
        return (0x90 | self._channel, self._note, self._velocity)

    def note_off_bytes(self) -> tuple[int, int, int]:
        """Return (status, note, velocity=0) for a Note Off message."""
        return (0x80 | self._channel, self._note, 0)

    # ---- conversions ----

    def as_dict(self) -> dict:
        return {
            "note": self._note,
            "velocity": self._velocity,
            "start_ms": self._start_ms,
            "duration_ms": self._duration_ms,
            "channel": self._channel,
        }

    @classmethod
    def from_flux(
        cls,
        vector_values: tuple[float, ...],
        start_ms: float,
        duration_ms: float,
        channel: int = 0,
        base_note: int = NoteName.C4,
        velocity_scale: int = 100,
    ) -> list[MidiEvent]:
        """Convert a FluxVector to a list of MIDI events.

        Non-zero channels become notes.  Salience modulates velocity.
        Tolerance modulates note-off jitter.
        """
        events: list[MidiEvent] = []
        for i, val in enumerate(vector_values):
            if val == 0.0:
                continue
            note = min(127, max(0, base_note + i))
            velocity = min(127, max(1, int(val * velocity_scale)))
            events.append(cls(note, velocity, start_ms, duration_ms, channel))
        return events

    # ---- display ----

    def __repr__(self) -> str:
        return (
            f"MidiEvent(note={self._note}, vel={self._velocity}, "
            f"start={self._start_ms:.1f}ms, dur={self._duration_ms:.1f}ms, "
            f"ch={self._channel})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MidiEvent):
            return NotImplemented
        return (
            self._note == other._note
            and self._velocity == other._velocity
            and self._start_ms == other._start_ms
            and self._duration_ms == other._duration_ms
            and self._channel == other._channel
        )

    def __hash__(self) -> int:
        return hash((self._note, self._velocity, self._start_ms, self._duration_ms, self._channel))
