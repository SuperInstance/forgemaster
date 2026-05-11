"""Tests for Score recording."""

import pytest
from flux_tensor_midi.ensemble.score import Score
from flux_tensor_midi.core.flux import FluxVector


class TestScore:
    def test_create_default(self):
        s = Score()
        assert s.title == "Untitled"
        assert s.total_events() == 0
        assert s.musician_names == []

    def test_create_custom_title(self):
        s = Score("My Performance")
        assert s.title == "My Performance"

    def test_record_event(self):
        s = Score()
        v = FluxVector([1.0] * 9)
        s.record_event("piano", 0.0, v)
        s.record_event("piano", 500.0, v)
        assert s.total_events() == 2
        assert "piano" in s.musician_names

    def test_events_for(self):
        s = Score()
        v = FluxVector([1.0] * 9)
        s.record_event("piano", 0.0, v)
        s.record_event("piano", 500.0, v)
        events = s.events_for("piano")
        assert len(events) == 2
        assert events[0][0] == 0.0

    def test_events_for_nonexistent(self):
        s = Score()
        assert s.events_for("ghost") == []

    def test_vectors_for(self):
        s = Score()
        v = FluxVector([1.0, 2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        s.record_event("piano", 0.0, v)
        vecs = s.vectors_for("piano")
        assert len(vecs) == 1
        assert vecs[0][1] == 2.0

    def test_all_events_sorted(self):
        s = Score()
        v = FluxVector([1.0] * 9)
        s.record_event("b", 500.0, v)
        s.record_event("a", 0.0, v)
        all_ev = s.all_events()
        assert len(all_ev) == 2
        assert all_ev[0][0] == "a"

    def test_duration_ms(self):
        s = Score()
        v = FluxVector([1.0] * 9)
        s.record_event("piano", 100.0, v)
        s.record_event("piano", 600.0, v)
        assert s.duration_ms() == 500.0

    def test_duration_ms_empty(self):
        s = Score()
        assert s.duration_ms() == 0.0

    def test_side_channel(self):
        s = Score()
        s.record_side_channel("piano", "nod", 100.0)
        assert "piano" in s._side_channels

    def test_spectral_flux(self):
        s = Score()
        v1 = FluxVector.zero()
        v2 = FluxVector.unit(0)
        s.record_event("piano", 0.0, v1)
        s.record_event("piano", 500.0, v2)
        flux = s.spectral_flux("piano")
        assert flux > 0

    def test_harmony_at(self):
        s = Score()
        v = FluxVector([1.0, 2.0, 3.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        s.record_event("piano", 100.0, v)
        s.record_event("drums", 110.0, v)
        hs = s.harmony_at(105.0, window_ms=20.0)
        assert hs is not None
        assert hs.size == 2

    def test_harmony_at_empty(self):
        s = Score()
        assert s.harmony_at(0.0) is None

    def test_to_midi_events(self):
        s = Score()
        v = FluxVector([0.5, 0.0, 0.8, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        s.record_event("piano", 0.0, v)
        s.record_event("drums", 500.0, v)
        midi = s.to_midi_events(velocity_scale=100)
        assert len(midi) > 0

    def test_summary(self):
        s = Score("Test")
        v = FluxVector([1.0] * 9)
        s.record_event("piano", 0.0, v)
        s.record_event("piano", 500.0, v)
        s.record_event("drums", 250.0, v)
        summary = s.summary()
        assert summary["title"] == "Test"
        assert summary["total_events"] == 3
        assert summary["musicians"] == 2
