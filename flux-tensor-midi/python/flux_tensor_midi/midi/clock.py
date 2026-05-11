"""
MIDI clock and timing utilities for FLUX-Tensor-MIDI.

Implements MIDI clock (0xF8), start/stop/continue messages,
and PPQN-based timing.
"""

from __future__ import annotations
from typing import Callable


class MidiClock:
    """Software MIDI clock generator.

    Generates MIDI clock pulses (0xF8) at 24 PPQN (pulses per quarter note).

    Parameters
    ----------
    bpm : float, default=120.0
        Beats per minute.
    tick_callback : Callable[[int], None] | None
        Called on each 0xF8 tick with tick count.
    """

    PPQN = 24  # Pulses per quarter note (MIDI standard)

    def __init__(self, bpm: float = 120.0, tick_callback: Callable[[int], None] | None = None):
        if bpm <= 0:
            raise ValueError(f"bpm must be positive, got {bpm}")
        self._bpm = bpm
        self._callback = tick_callback
        self._tick_count = 0
        self._running = False

    @property
    def bpm(self) -> float:
        return self._bpm

    @bpm.setter
    def bpm(self, value: float) -> None:
        if value <= 0:
            raise ValueError(f"bpm must be positive, got {value}")
        self._bpm = value

    @property
    def tick_count(self) -> int:
        return self._tick_count

    @property
    def pulse_interval_ms(self) -> float:
        """Time between clock pulses in ms."""
        return 60000.0 / (self._bpm * self.PPQN)

    @property
    def quarter_note_ms(self) -> float:
        """Duration of one quarter note in ms."""
        return 60000.0 / self._bpm

    # ---- control ----

    def start(self) -> None:
        """Start the clock."""
        self._running = True
        self._tick_count = 0

    def stop(self) -> None:
        """Stop the clock."""
        self._running = False

    def continue_(self) -> None:
        """Continue the clock (preserves tick count)."""
        self._running = True

    def tick(self) -> int:
        """Advance one clock tick.  Returns tick count."""
        if not self._running:
            return self._tick_count
        self._tick_count += 1
        if self._callback:
            self._callback(self._tick_count)
        return self._tick_count

    def reset(self) -> None:
        """Reset tick count to 0."""
        self._tick_count = 0

    # ---- position helpers ----

    def beat(self) -> int:
        """Current beat number (1 beat = 24 ticks)."""
        return self._tick_count // self.PPQN

    def measure(self, beats_per_measure: int = 4) -> int:
        """Current measure number."""
        return self.beat() // beats_per_measure

    def tick_in_beat(self) -> int:
        """Tick position within the current beat (0–23)."""
        return self._tick_count % self.PPQN

    def tick_in_measure(self, beats_per_measure: int = 4) -> int:
        """Tick position within the current measure."""
        return self._tick_count % (self.PPQN * beats_per_measure)

    @classmethod
    def tempo_from_delay(cls, pulse_delay_ms: float) -> float:
        """Calculate BPM from a clock pulse delay in ms."""
        if pulse_delay_ms <= 0:
            raise ValueError(f"pulse_delay_ms must be positive, got {pulse_delay_ms}")
        return 60000.0 / (pulse_delay_ms * cls.PPQN)

    def __repr__(self) -> str:
        return (
            f"MidiClock(bpm={self._bpm}, ppqn={self.PPQN}, "
            f"running={self._running}, ticks={self._tick_count})"
        )
