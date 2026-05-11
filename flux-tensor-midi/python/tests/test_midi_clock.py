"""Tests for MidiClock."""

import pytest
from flux_tensor_midi.midi.clock import MidiClock


class TestMidiClock:
    def test_default(self):
        c = MidiClock()
        assert c.bpm == 120.0
        assert c.tick_count == 0
        assert not c._running

    def test_custom_bpm(self):
        c = MidiClock(bpm=60.0)
        assert c.bpm == 60.0

    def test_invalid_bpm(self):
        with pytest.raises(ValueError, match="bpm must be positive"):
            MidiClock(bpm=0)

    def test_pulse_interval(self):
        c = MidiClock(bpm=120.0)
        # 60000 / (120 * 24) = 20.833 ms
        assert abs(c.pulse_interval_ms - 20.8333) < 0.01

    def test_quarter_note_ms(self):
        c = MidiClock(bpm=120.0)
        assert c.quarter_note_ms == 500.0

    def test_start_stop(self):
        c = MidiClock()
        c.start()
        assert c._running
        c.stop()
        assert not c._running

    def test_tick_increments(self):
        c = MidiClock()
        c.start()
        assert c.tick() == 1
        assert c.tick_count == 1

    def test_tick_does_nothing_when_stopped(self):
        c = MidiClock()
        c.tick()
        assert c.tick_count == 0

    def test_continue_preserves_count(self):
        c = MidiClock()
        c.start()
        c.tick()
        c.stop()
        c.continue_()
        assert c.tick_count == 1

    def test_reset(self):
        c = MidiClock()
        c.start()
        c.tick()
        c.reset()
        assert c.tick_count == 0

    def test_beat(self):
        c = MidiClock()
        c.start()
        for _ in range(24):
            c.tick()
        assert c.beat() == 1
        for _ in range(24):
            c.tick()
        assert c.beat() == 2

    def test_measure(self):
        c = MidiClock()
        c.start()
        for _ in range(96):  # 4 beats
            c.tick()
        assert c.measure() == 1

    def test_tick_in_beat(self):
        c = MidiClock()
        c.start()
        assert c.tick_in_beat() == 0
        c.tick()
        assert c.tick_in_beat() == 1

    def test_tempo_from_delay(self):
        bpm = MidiClock.tempo_from_delay(20.8333)
        assert abs(bpm - 120.0) < 0.1

    def test_tempo_from_delay_invalid(self):
        with pytest.raises(ValueError, match="pulse_delay_ms must be positive"):
            MidiClock.tempo_from_delay(-1)

    def test_set_bpm(self):
        c = MidiClock(bpm=120.0)
        c.bpm = 80.0
        assert c.bpm == 80.0

    def test_set_bpm_invalid(self):
        c = MidiClock()
        with pytest.raises(ValueError, match="bpm must be positive"):
            c.bpm = 0

    def test_callback(self):
        calls: list[int] = []

        def cb(tick: int):
            calls.append(tick)

        c = MidiClock(tick_callback=cb)
        c.start()
        c.tick()
        c.tick()
        assert calls == [1, 2]
