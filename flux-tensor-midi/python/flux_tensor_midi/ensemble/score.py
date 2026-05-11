"""
Score: A written record of a performance.

Records events from all musicians over time and provides
playback/analysis capabilities.
"""

from __future__ import annotations
from typing import Sequence
from flux_tensor_midi.core.flux import FluxVector
from flux_tensor_midi.midi.events import MidiEvent
from flux_tensor_midi.harmony.chord import HarmonyState
from flux_tensor_midi.harmony.spectrum import spectral_flux


class Score:
    """A recorded performance score.

    Stores timestamped events from multiple musicians and
    provides analysis and export utilities.
    """

    def __init__(self, title: str = "Untitled"):
        self._title = title
        self._events: dict[str, list[tuple[float, FluxVector]]] = {}
        self._side_channels: dict[str, dict[str, list[float]]] = {}

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        self._title = value

    @property
    def musician_names(self) -> list[str]:
        return list(self._events.keys())

    # ---- recording ----

    def record_event(self, musician: str, timestamp: float, vector: FluxVector) -> None:
        """Record an event from a musician."""
        if musician not in self._events:
            self._events[musician] = []
        self._events[musician].append((timestamp, vector))

    def record_side_channel(self, musician: str, channel: str, timestamp: float) -> None:
        """Record a side-channel event."""
        if musician not in self._side_channels:
            self._side_channels[musician] = {}
        if channel not in self._side_channels[musician]:
            self._side_channels[musician][channel] = []
        self._side_channels[musician][channel].append(timestamp)

    # ---- access ----

    def events_for(self, musician: str) -> list[tuple[float, FluxVector]]:
        """Get all events for a musician."""
        return list(self._events.get(musician, []))

    def vectors_for(self, musician: str) -> list[FluxVector]:
        """Get all FluxVectors for a musician."""
        return [v for _, v in self._events.get(musician, [])]

    def all_events(self) -> list[tuple[str, float, FluxVector]]:
        """Get all events across all musicians, sorted by timestamp."""
        flat: list[tuple[str, float, FluxVector]] = []
        for musician, events in self._events.items():
            for ts, vec in events:
                flat.append((musician, ts, vec))
        flat.sort(key=lambda x: x[1])
        return flat

    # ---- analysis ----

    def total_events(self) -> int:
        """Total number of events across all musicians."""
        return sum(len(events) for events in self._events.values())

    def duration_ms(self) -> float:
        """Total duration (last timestamp - first timestamp) in ms."""
        all_events = self.all_events()
        if not all_events:
            return 0.0
        return all_events[-1][1] - all_events[0][1]

    def spectral_flux(self, musician: str) -> float:
        """Spectral flux for a specific musician."""
        vecs = self.vectors_for(musician)
        return spectral_flux(vecs)

    def harmony_at(self, timestamp: float, window_ms: float = 100.0) -> HarmonyState | None:
        """Get the harmonic state near a given timestamp.

        Collects the nearest event from each musician within window_ms.
        """
        if not self._events:
            return None

        nearest: list[FluxVector] = []
        for musician, events in self._events.items():
            best_vec = None
            best_dist = window_ms
            for ts, vec in events:
                dist = abs(ts - timestamp)
                if dist < best_dist:
                    best_dist = dist
                    best_vec = vec
            if best_vec is not None:
                nearest.append(best_vec)

        if not nearest:
            return None

        return HarmonyState(nearest)

    # ---- export ----

    def to_midi_events(self, velocity_scale: int = 100) -> list[MidiEvent]:
        """Convert the score to a flat list of MIDI events.

        Each FluxVector channel becomes a note.
        """
        midi_events: list[MidiEvent] = []
        for musician, events in self._events.items():
            # Simple: use a consistent channel offset per musician
            ch_idx = min(self.musician_names.index(musician), 15)
            for ts, vec in events:
                midi_events.extend(
                    MidiEvent.from_flux(
                        vec.values,
                        start_ms=ts,
                        duration_ms=250.0,  # quarter note default
                        channel=ch_idx,
                        velocity_scale=velocity_scale,
                    )
                )
        midi_events.sort(key=lambda e: e.start_ms)
        return midi_events

    def summary(self) -> dict:
        """Get a summary dict for the score."""
        return {
            "title": self._title,
            "musicians": len(self._events),
            "total_events": self.total_events(),
            "duration_ms": self.duration_ms(),
            "events_per_musician": {
                name: len(events) for name, events in self._events.items()
            },
        }

    def __repr__(self) -> str:
        return (
            f"Score(title={self._title!r}, "
            f"musicians={len(self._events)}, "
            f"events={self.total_events()})"
        )
