"""Tests for Nod, Smile, Frown side-channels."""

import pytest
from flux_tensor_midi.sidechannel.nod import Nod
from flux_tensor_midi.sidechannel.smile import Smile
from flux_tensor_midi.sidechannel.frown import Frown
from flux_tensor_midi.core.room import RoomMusician


class TestNod:
    def test_create_default(self):
        n = Nod()
        assert n.intensity == 0.5
        assert n.count == 0

    def test_custom_intensity(self):
        n = Nod(intensity=0.8)
        assert n.intensity == 0.8

    def test_invalid_intensity_low(self):
        with pytest.raises(ValueError, match="intensity must be 0–1"):
            Nod(intensity=-0.1)

    def test_invalid_intensity_high(self):
        with pytest.raises(ValueError, match="intensity must be 0–1"):
            Nod(intensity=1.1)

    def test_send(self):
        a = RoomMusician("A")
        b = RoomMusician("B")
        n = Nod()
        n.send(b)
        assert n.count == 1
        assert n.has_sent_to(b.room_id)

    def test_rate(self):
        n = Nod()
        a = RoomMusician("A")
        for _ in range(5):
            n.send(a)
        rate = n.rate(window_seconds=60.0)
        assert rate > 0

    def test_reset(self):
        n = Nod()
        a = RoomMusician("A")
        n.send(a)
        n.reset()
        assert n.count == 0


class TestSmile:
    def test_create(self):
        s = Smile()
        assert s.intensity == 0.5

    def test_send(self):
        b = RoomMusician("B")
        s = Smile()
        s.send(b)
        assert s.has_sent_to(b.room_id)

    def test_rate(self):
        s = Smile()
        a = RoomMusician("A")
        for _ in range(3):
            s.send(a)
        assert s.count == 3

    def test_reset(self):
        s = Smile()
        a = RoomMusician("A")
        s.send(a)
        s.reset()
        assert s.count == 0


class TestFrown:
    def test_create(self):
        f = Frown()
        assert f.intensity == 0.5

    def test_send(self):
        b = RoomMusician("B")
        f = Frown()
        f.send(b)
        assert f.has_sent_to(b.room_id)

    def test_count(self):
        f = Frown()
        a = RoomMusician("A")
        for _ in range(7):
            f.send(a)
        assert f.count == 7

    def test_reset(self):
        f = Frown()
        a = RoomMusician("A")
        f.send(a)
        f.reset()
        assert f.count == 0
