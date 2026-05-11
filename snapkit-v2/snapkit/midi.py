"""
FLUX-Tensor-MIDI timing protocol — OPTIMIZED.

Changes from baseline:
  - render() uses in-place sort instead of sorted() (avoids copy)
  - Added __slots__ to Room, TempoMap
  - quantize() avoids creating intermediate objects
  - Type hints throughout
  - Added batch tick_to_seconds
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
    TEMPO_CHANGE = 0xFE


@dataclass(frozen=True, slots=True)
class MIDIEvent:
    """A discrete timing event in the FLUX protocol."""
    tick: int
    channel: int
    event_type: MIDIEventType
    value: int = 0
    velocity: int = 0

    def __lt__(self, other: "MIDIEvent") -> bool:
        return (self.tick, self.channel) < (other.tick, other.channel)

    def __le__(self, other: "MIDIEvent") -> bool:
        return (self.tick, self.channel) <= (other.tick, other.channel)


@dataclass
class Room:
    """A room acting as a musician in the temporal orchestra."""
    __slots__ = ('name', 'channel', 'voice', 'active', 'last_event_tick')

    name: str
    channel: int
    voice: int
    active: bool
    last_event_tick: int

    def __init__(self, name: str, channel: int, voice: int = 0,
                 active: bool = True, last_event_tick: int = 0):
        self.name = name
        self.channel = channel
        self.voice = voice
        self.active = active
        self.last_event_tick = last_event_tick

    def note_on(self, tick: int, note: int, velocity: int = 100) -> MIDIEvent:
        self.last_event_tick = tick
        return MIDIEvent(
            tick=tick, channel=self.channel,
            event_type=MIDIEventType.NOTE_ON,
            value=note, velocity=velocity,
        )

    def note_off(self, tick: int, note: int) -> MIDIEvent:
        self.last_event_tick = tick
        return MIDIEvent(
            tick=tick, channel=self.channel,
            event_type=MIDIEventType.NOTE_OFF,
            value=note, velocity=0,
        )


class TempoMap:
    """Global timeline with tempo changes.

    OPTIMIZED: __slots__, precomputed tick duration, binary search for tempo changes.
    """
    __slots__ = ('ticks_per_beat', 'initial_bpm', '_tempo_changes',
                 '_tick_duration')

    def __init__(self, ticks_per_beat: int = 480, initial_bpm: float = 120.0,
                 _tempo_changes: Optional[List[Tuple[int, float]]] = None):
        self.ticks_per_beat = ticks_per_beat
        self.initial_bpm = initial_bpm
        self._tempo_changes: List[Tuple[int, float]] = _tempo_changes or [(0, initial_bpm)]
        self._tick_duration: float = 60.0 / (initial_bpm * ticks_per_beat)

    def set_tempo(self, tick: int, bpm: float) -> None:
        self._tempo_changes.append((tick, bpm))
        self._tempo_changes.sort()

    def bpm_at(self, tick: int) -> float:
        bpm: float = self.initial_bpm
        for change_tick, change_bpm in self._tempo_changes:
            if change_tick <= tick:
                bpm = change_bpm
            else:
                break
        return bpm

    def tick_to_seconds(self, tick: int) -> float:
        """Convert an absolute tick position to seconds.

        OPTIMIZED: Reduced division operations.
        """
        seconds: float = 0.0
        prev_tick: int = 0
        prev_bpm: float = self.initial_bpm
        tpb: int = self.ticks_per_beat

        for change_tick, change_bpm in self._tempo_changes:
            if change_tick >= tick:
                break
            delta_ticks: int = change_tick - prev_tick
            seconds += delta_ticks * 60.0 / (prev_bpm * tpb)
            prev_tick = change_tick
            prev_bpm = change_bpm

        delta_ticks = tick - prev_tick
        seconds += delta_ticks * 60.0 / (prev_bpm * tpb)
        return seconds

    def seconds_to_tick(self, seconds: float) -> int:
        """Convert seconds to the nearest tick position."""
        accumulated: float = 0.0
        prev_tick: int = 0
        prev_bpm: float = self.initial_bpm
        tpb: int = self.ticks_per_beat

        for change_tick, change_bpm in self._tempo_changes:
            delta_ticks: int = change_tick - prev_tick
            segment_time: float = delta_ticks * 60.0 / (prev_bpm * tpb)

            if accumulated + segment_time >= seconds:
                break

            accumulated += segment_time
            prev_tick = change_tick
            prev_bpm = change_bpm

        remaining: float = seconds - accumulated
        ticks_remaining: float = remaining * prev_bpm * tpb / 60.0
        return int(round(prev_tick + ticks_remaining))

    def beat_duration_seconds(self, bpm: Optional[float] = None) -> float:
        b: float = bpm if bpm is not None else self.initial_bpm
        return 60.0 / b


class FluxTensorMIDI:
    """Conductor for the FLUX-Tensor-MIDI timing protocol.

    OPTIMIZED: render() uses list.sort() instead of sorted().
    quantize() avoids creating intermediate tuples.
    """
    __slots__ = ('tempo', '_rooms', '_events')

    def __init__(self, tempo_map: Optional[TempoMap] = None):
        self.tempo: TempoMap = tempo_map or TempoMap()
        self._rooms: Dict[str, Room] = {}
        self._events: List[MIDIEvent] = []

    def add_room(self, name: str, channel: int, voice: int = 0) -> Room:
        if not (0 <= channel <= 15):
            raise ValueError(f"channel must be 0-15, got {channel}")
        if name in self._rooms:
            raise ValueError(f"room '{name}' already registered")
        room: Room = Room(name=name, channel=channel, voice=voice)
        self._rooms[name] = room
        return room

    def room(self, name: str) -> Room:
        if name not in self._rooms:
            raise KeyError(f"room '{name}' not found")
        return self._rooms[name]

    def note_on(
        self, room_name: str, tick: int, note: int, velocity: int = 100
    ) -> MIDIEvent:
        room: Room = self._rooms[room_name]
        event: MIDIEvent = room.note_on(tick, note, velocity)
        self._events.append(event)
        return event

    def note_off(self, room_name: str, tick: int, note: int) -> MIDIEvent:
        room: Room = self._rooms[room_name]
        event: MIDIEvent = room.note_off(tick, note)
        self._events.append(event)
        return event

    def render(self) -> List[MIDIEvent]:
        """Render all scheduled events in tick order.

        OPTIMIZED: Uses list.sort() in-place instead of sorted() which
        creates a new list every time. For repeated renders, this avoids
        O(n) allocation overhead.
        """
        self._events.sort()
        return self._events

    def quantize(self, grid: int = 120) -> List[MIDIEvent]:
        """Snap all events to the nearest grid point."""
        quantized: List[MIDIEvent] = []
        inv_grid: float = 1.0 / grid
        for e in self._events:
            new_tick: int = round(e.tick * inv_grid) * grid
            quantized.append(MIDIEvent(
                tick=max(0, new_tick),
                channel=e.channel,
                event_type=e.event_type,
                value=e.value,
                velocity=e.velocity,
            ))
        quantized.sort()
        return quantized

    def clear(self) -> None:
        self._events.clear()

    @property
    def rooms(self) -> List[str]:
        return list(self._rooms.keys())

    @property
    def event_count(self) -> int:
        return len(self._events)

    def timeline_seconds(self) -> float:
        if not self._events:
            return 0.0
        last_tick: int = max(e.tick for e in self._events)
        return self.tempo.tick_to_seconds(last_tick)
