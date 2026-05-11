"""
FLUX-Tensor-MIDI timing protocol — rooms as musicians.

In the Cocapn fleet, rooms are musicians in a temporal orchestra.
This module maps the fleet's room activity onto a MIDI-like timing
protocol where:

  - Each room is a "musician" with its own voice (channel).
  - A TempoMap defines the global timeline and tempo changes.
  - MIDIEvents represent discrete temporal events (note on/off, control).
  - The FluxTensorMIDI conductor coordinates timing across rooms.

The protocol is designed for precise temporal coordination without
external dependencies — all timing is math-based, not clock-based.
"""

import math
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, List, Optional, Tuple


class MIDIEventType(IntEnum):
    NOTE_ON = 0x90
    NOTE_OFF = 0x80
    CONTROL_CHANGE = 0xB0
    PROGRAM_CHANGE = 0xC0
    TEMPO_CHANGE = 0xFE  # meta-event


@dataclass(frozen=True, slots=True)
class MIDIEvent:
    """A discrete timing event in the FLUX protocol.

    Attributes:
        tick: Absolute tick position on the timeline.
        channel: Room (musician) channel (0-15).
        event_type: Type of MIDI event.
        value: Primary value (note number, CC number, etc.).
        velocity: Secondary value (velocity, CC value, etc.).
    """
    tick: int
    channel: int
    event_type: MIDIEventType
    value: int = 0
    velocity: int = 0

    def __lt__(self, other: "MIDIEvent") -> bool:
        return (self.tick, self.channel) < (other.tick, other.channel)


@dataclass
class Room:
    """A room acting as a musician in the temporal orchestra.

    Attributes:
        name: Human-readable room name.
        channel: MIDI channel (0-15).
        voice: Instrument/voice identifier.
        active: Whether the room is currently playing.
        last_event_tick: Tick of the last event from this room.
    """
    name: str
    channel: int
    voice: int = 0
    active: bool = True
    last_event_tick: int = 0

    def note_on(self, tick: int, note: int, velocity: int = 100) -> MIDIEvent:
        """Create a NOTE_ON event for this room."""
        self.last_event_tick = tick
        return MIDIEvent(
            tick=tick,
            channel=self.channel,
            event_type=MIDIEventType.NOTE_ON,
            value=note,
            velocity=velocity,
        )

    def note_off(self, tick: int, note: int) -> MIDIEvent:
        """Create a NOTE_OFF event for this room."""
        self.last_event_tick = tick
        return MIDIEvent(
            tick=tick,
            channel=self.channel,
            event_type=MIDIEventType.NOTE_OFF,
            value=note,
            velocity=0,
        )


@dataclass
class TempoMap:
    """Global timeline with tempo changes.

    The timeline is measured in ticks. Default resolution: 480 ticks per beat
    (standard MIDI resolution).

    Attributes:
        ticks_per_beat: Resolution in ticks per quarter note.
        initial_bpm: Starting tempo in beats per minute.
    """
    ticks_per_beat: int = 480
    initial_bpm: float = 120.0

    # Internal tempo change log: list of (tick, bpm) pairs
    _tempo_changes: List[Tuple[int, float]] = field(default_factory=list)

    def __post_init__(self):
        if not self._tempo_changes:
            self._tempo_changes = [(0, self.initial_bpm)]

    def set_tempo(self, tick: int, bpm: float) -> None:
        """Insert a tempo change at the given tick."""
        self._tempo_changes.append((tick, bpm))
        self._tempo_changes.sort()

    def bpm_at(self, tick: int) -> float:
        """Get the BPM in effect at the given tick."""
        bpm = self.initial_bpm
        for change_tick, change_bpm in self._tempo_changes:
            if change_tick <= tick:
                bpm = change_bpm
            else:
                break
        return bpm

    def tick_to_seconds(self, tick: int) -> float:
        """Convert an absolute tick position to seconds.

        Accounts for all tempo changes up to the given tick.
        """
        seconds = 0.0
        prev_tick = 0
        prev_bpm = self.initial_bpm

        for change_tick, change_bpm in self._tempo_changes:
            if change_tick >= tick:
                break
            # Time elapsed in the previous tempo segment
            delta_ticks = change_tick - prev_tick
            beats = delta_ticks / self.ticks_per_beat
            seconds += (beats / prev_bpm) * 60.0
            prev_tick = change_tick
            prev_bpm = change_bpm

        # Remaining ticks at current tempo
        delta_ticks = tick - prev_tick
        beats = delta_ticks / self.ticks_per_beat
        seconds += (beats / prev_bpm) * 60.0

        return seconds

    def seconds_to_tick(self, seconds: float) -> int:
        """Convert seconds to the nearest tick position."""
        accumulated = 0.0
        prev_tick = 0
        prev_bpm = self.initial_bpm

        for change_tick, change_bpm in self._tempo_changes:
            delta_ticks = change_tick - prev_tick
            beats = delta_ticks / self.ticks_per_beat
            segment_time = (beats / prev_bpm) * 60.0

            if accumulated + segment_time >= seconds:
                break

            accumulated += segment_time
            prev_tick = change_tick
            prev_bpm = change_bpm
        else:
            # Past all tempo changes
            pass

        remaining = seconds - accumulated
        ticks_remaining = remaining * prev_bpm * self.ticks_per_beat / 60.0
        return int(round(prev_tick + ticks_remaining))

    def beat_duration_seconds(self, bpm: Optional[float] = None) -> float:
        """Duration of one beat in seconds at the given BPM."""
        b = bpm if bpm is not None else self.initial_bpm
        return 60.0 / b


class FluxTensorMIDI:
    """Conductor for the FLUX-Tensor-MIDI timing protocol.

    Coordinates multiple rooms (musicians) on a shared timeline,
    managing event scheduling, quantization, and temporal alignment.

    Usage:
        conductor = FluxTensorMIDI()
        conductor.add_room("bridge", channel=0)
        conductor.add_room("engineering", channel=1)

        # Schedule events
        conductor.note_on("bridge", tick=0, note=60)
        conductor.note_off("bridge", tick=480, note=60)

        # Render to sorted event list
        timeline = conductor.render()
    """

    def __init__(self, tempo_map: Optional[TempoMap] = None):
        self.tempo = tempo_map or TempoMap()
        self._rooms: Dict[str, Room] = {}
        self._events: List[MIDIEvent] = []

    def add_room(self, name: str, channel: int, voice: int = 0) -> Room:
        """Register a room as a musician."""
        if not (0 <= channel <= 15):
            raise ValueError(f"channel must be 0-15, got {channel}")
        if name in self._rooms:
            raise ValueError(f"room '{name}' already registered")
        room = Room(name=name, channel=channel, voice=voice)
        self._rooms[name] = room
        return room

    def room(self, name: str) -> Room:
        """Get a room by name."""
        if name not in self._rooms:
            raise KeyError(f"room '{name}' not found")
        return self._rooms[name]

    def note_on(
        self, room_name: str, tick: int, note: int, velocity: int = 100
    ) -> MIDIEvent:
        """Schedule a note-on event for a room."""
        room = self.room(room_name)
        event = room.note_on(tick, note, velocity)
        self._events.append(event)
        return event

    def note_off(self, room_name: str, tick: int, note: int) -> MIDIEvent:
        """Schedule a note-off event for a room."""
        room = self.room(room_name)
        event = room.note_off(tick, note)
        self._events.append(event)
        return event

    def render(self) -> List[MIDIEvent]:
        """Render all scheduled events in tick order.

        Returns:
            Sorted list of MIDIEvents.
        """
        return sorted(self._events)

    def quantize(self, grid: int = 120) -> List[MIDIEvent]:
        """Snap all events to the nearest grid point.

        Args:
            grid: Grid size in ticks (e.g., 120 = sixteenth notes at 480 tpqn).

        Returns:
            New sorted event list with quantized tick positions.
        """
        quantized = []
        for e in self._events:
            new_tick = round(e.tick / grid) * grid
            quantized.append(MIDIEvent(
                tick=max(0, new_tick),
                channel=e.channel,
                event_type=e.event_type,
                value=e.value,
                velocity=e.velocity,
            ))
        return sorted(quantized)

    def clear(self) -> None:
        """Clear all scheduled events."""
        self._events.clear()

    @property
    def rooms(self) -> List[str]:
        """List registered room names."""
        return list(self._rooms.keys())

    @property
    def event_count(self) -> int:
        """Total number of scheduled events."""
        return len(self._events)

    def timeline_seconds(self) -> float:
        """Total duration of the timeline in seconds."""
        if not self._events:
            return 0.0
        last_tick = max(e.tick for e in self._events)
        return self.tempo.tick_to_seconds(last_tick)
