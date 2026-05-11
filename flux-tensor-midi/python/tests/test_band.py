"""Tests for Band ensemble."""

import pytest
from flux_tensor_midi.ensemble.band import Band
from flux_tensor_midi.core.room import RoomMusician
from flux_tensor_midi.core.snap import RhythmicRole
from flux_tensor_midi.core.flux import FluxVector


class TestBand:
    def test_create_empty(self):
        band = Band("test-band")
        assert band.name == "test-band"
        assert band.member_count == 0
        assert band.conductor is None

    def test_create_with_conductor(self):
        cond = RoomMusician("maestro")
        band = Band("test", conductor=cond)
        assert band.member_count == 1
        assert band.conductor is not None

    def test_add_musician(self):
        band = Band("band")
        m = RoomMusician("alice")
        band.add_musician(m)
        assert band.member_count == 1
        assert "alice" in [x.name for x in band.members.values()]

    def test_add_musician_syncs_clock_if_conductor(self):
        cond = RoomMusician("maestro", clock=None)
        band = Band("band", conductor=cond, bpm=140.0)
        m = RoomMusician("bob")
        band.add_musician(m)
        assert m.clock.bpm == 140.0

    def test_remove_musician(self):
        band = Band("band")
        m = RoomMusician("charlie")
        band.add_musician(m)
        band.remove_musician(m)
        assert band.member_count == 0

    def test_get_musician_by_name(self):
        band = Band("band")
        m = RoomMusician("dave")
        band.add_musician(m)
        assert band.get_musician("dave") is m
        assert band.get_musician("nonexistent") is None

    def test_everyone_listens_to_conductor(self):
        cond = RoomMusician("cond")
        band = Band("band", conductor=cond)
        m = RoomMusician("player")
        band.add_musician(m)
        band.everyone_listens_to_conductor()
        assert cond.room_id in m.listeners

    def test_everyone_listens_to_everyone(self):
        cond = RoomMusician("cond")
        band = Band("band", conductor=cond)
        a = RoomMusician("a")
        b = RoomMusician("b")
        band.add_musician(a)
        band.add_musician(b)
        band.everyone_listens_to_everyone()
        # Each musician listens to all others
        assert len(a.listeners) == 2
        assert len(b.listeners) == 2

    def test_tick_all(self):
        cond = RoomMusician("cond")
        band = Band("band", conductor=cond)
        a = RoomMusician("a")
        b = RoomMusician("b")
        band.add_musician(a)
        band.add_musician(b)
        results = band.tick_all()
        assert len(results) == 3  # cond + a + b

    def test_set_bpm(self):
        cond = RoomMusician("cond")
        band = Band("band", conductor=cond, bpm=120.0)
        m = RoomMusician("player")
        band.add_musician(m)
        band.set_bpm(160.0)
        assert all(mem.clock.bpm == 160.0 for mem in band.members.values())

    def test_harmony(self):
        band = Band("band")
        a = RoomMusician("a")
        b = RoomMusician("b")
        a.update_state(FluxVector.unit(0))
        b.update_state(FluxVector.unit(4))
        band.add_musician(a)
        band.add_musician(b)
        hs = band.harmony()
        assert hs.size == 2

    def test_mean_coherence(self):
        band = Band("band")
        a = RoomMusician("a")
        b = RoomMusician("b")
        v = FluxVector([1.0] * 9)
        a.update_state(v)
        b.update_state(v)
        band.add_musician(a)
        band.add_musician(b)
        assert abs(band.mean_coherence() - 1.0) < 1e-10

    def test_get_roles(self):
        band = Band("band")
        a = RoomMusician("a", role=RhythmicRole.TRIPLET)
        b = RoomMusician("b", role=RhythmicRole.HALFTIME)
        band.add_musician(a)
        band.add_musician(b)
        roles = band.get_roles()
        assert roles["a"] == RhythmicRole.TRIPLET
        assert roles["b"] == RhythmicRole.HALFTIME
