"""Tests for MidiEvent."""

import pytest
from flux_tensor_midi.midi.events import MidiEvent, NoteName


class TestMidiEvent:
    def test_create(self):
        e = MidiEvent(note=60, velocity=100, start_ms=0.0, duration_ms=500.0)
        assert e.note == 60
        assert e.velocity == 100
        assert e.start_ms == 0.0
        assert e.duration_ms == 500.0

    def test_end_ms(self):
        e = MidiEvent(60, 100, 0.0, 500.0)
        assert e.end_ms == 500.0

    def test_channel_default(self):
        e = MidiEvent(60, 100, 0.0, 500.0)
        assert e.channel == 0

    def test_channel_custom(self):
        e = MidiEvent(60, 100, 0.0, 500.0, channel=5)
        assert e.channel == 5

    def test_note_off_bytes(self):
        e = MidiEvent(60, 100, 0.0, 500.0)
        status, note, vel = e.note_off_bytes()
        assert status == 0x80
        assert note == 60
        assert vel == 0

    def test_note_on_bytes(self):
        e = MidiEvent(60, 100, 0.0, 500.0)
        status, note, vel = e.note_on_bytes()
        assert status == 0x90
        assert note == 60
        assert vel == 100

    def test_note_on_bytes_channel_5(self):
        e = MidiEvent(60, 100, 0.0, 500.0, channel=5)
        status, _, _ = e.note_on_bytes()
        assert status == 0x95

    def test_invalid_note_low(self):
        with pytest.raises(ValueError, match="note must be 0–127"):
            MidiEvent(-1, 100, 0.0, 500.0)

    def test_invalid_note_high(self):
        with pytest.raises(ValueError, match="note must be 0–127"):
            MidiEvent(128, 100, 0.0, 500.0)

    def test_invalid_velocity_low(self):
        with pytest.raises(ValueError, match="velocity must be 0–127"):
            MidiEvent(60, -1, 0.0, 500.0)

    def test_invalid_velocity_high(self):
        with pytest.raises(ValueError, match="velocity must be 0–127"):
            MidiEvent(60, 128, 0.0, 500.0)

    def test_invalid_channel_low(self):
        with pytest.raises(ValueError, match="channel must be 0–15"):
            MidiEvent(60, 100, 0.0, 500.0, channel=-1)

    def test_invalid_channel_high(self):
        with pytest.raises(ValueError, match="channel must be 0–15"):
            MidiEvent(60, 100, 0.0, 500.0, channel=16)

    def test_invalid_duration(self):
        with pytest.raises(ValueError, match="duration_ms must be >= 0"):
            MidiEvent(60, 100, 0.0, -1.0)

    def test_as_dict(self):
        e = MidiEvent(60, 100, 0.0, 500.0, channel=2)
        d = e.as_dict()
        assert d["note"] == 60
        assert d["velocity"] == 100
        assert d["channel"] == 2

    def test_equality(self):
        a = MidiEvent(60, 100, 0.0, 500.0)
        b = MidiEvent(60, 100, 0.0, 500.0)
        assert a == b

    def test_inequality(self):
        a = MidiEvent(60, 100, 0.0, 500.0)
        b = MidiEvent(61, 100, 0.0, 500.0)
        assert a != b

    def test_hashable(self):
        a = MidiEvent(60, 100, 0.0, 500.0)
        d = {a: "test"}
        assert d[a] == "test"

    def test_from_flux(self):
        values = (0.5, 0.0, 0.8, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        events = MidiEvent.from_flux(values, start_ms=0.0, duration_ms=500.0)
        assert len(events) == 2  # two non-zero channels
        assert events[0].note == 60
        assert events[1].note == 62

    def test_from_flux_zero_vector(self):
        events = MidiEvent.from_flux((0.0,) * 9, start_ms=0.0, duration_ms=500.0)
        assert len(events) == 0


class TestNoteName:
    def test_c4(self):
        assert NoteName.C4 == 60

    def test_d5(self):
        assert NoteName.D5 == 74

    def test_all_9_notes(self):
        assert len(NoteName) == 9
