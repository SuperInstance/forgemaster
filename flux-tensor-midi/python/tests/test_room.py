"""Tests for RoomMusician."""

import pytest
from flux_tensor_midi.core.room import RoomMusician
from flux_tensor_midi.core.flux import FluxVector
from flux_tensor_midi.core.snap import RhythmicRole
from flux_tensor_midi.core.clock import TZeroClock


class TestRoomMusician:
    def test_create(self):
        rm = RoomMusician("test-room")
        assert rm.name == "test-room"
        assert rm.role == RhythmicRole.ROOT
        assert rm.clock is not None

    def test_create_with_role(self):
        rm = RoomMusician("triplet-room", role=RhythmicRole.TRIPLET)
        assert rm.role == RhythmicRole.TRIPLET

    def test_create_with_clock(self):
        clock = TZeroClock(bpm=80.0)
        rm = RoomMusician("clock-room", clock=clock)
        assert rm.clock.bpm == 80.0

    def test_state_default(self):
        rm = RoomMusician("empty")
        assert sum(rm.state.values) == 0.0

    def test_update_state(self):
        rm = RoomMusician("updater")
        v = FluxVector([1.0] * 9)
        rm.update_state(v)
        assert rm.state.values == (1.0,) * 9

    def test_emit_returns_timestamp_vector(self):
        rm = RoomMusician("emitter")
        rm.update_state(FluxVector([0.5] * 9))
        ts, vec = rm.emit()
        assert ts > 0
        assert vec.values == (0.5,) * 9

    def test_emit_with_explicit_vector(self):
        rm = RoomMusician("explicit")
        v = FluxVector([2.0] * 9)
        ts, vec = rm.emit(v)
        assert vec.values == (2.0,) * 9

    def test_emit_stores_history(self):
        rm = RoomMusician("historian")
        rm.emit()
        assert len(rm.event_history) == 1

    def test_listen_to_another(self):
        a = RoomMusician("A")
        b = RoomMusician("B")
        a.listen_to(b)
        assert b.room_id in a.listeners

    def test_stop_listening(self):
        a = RoomMusician("A")
        b = RoomMusician("B")
        a.listen_to(b)
        a.stop_listening(b)
        assert b.room_id not in a.listeners

    def test_listen_gets_last_event(self):
        a = RoomMusician("A")
        b = RoomMusician("B")
        a.listen_to(b)
        b.emit()
        events = a.listen()
        assert len(events) > 0
        name, ts, vec = events[0]
        assert name == "B"

    def test_coherence(self):
        a = RoomMusician("samer")
        b = RoomMusician("same")
        v = FluxVector([1.0] * 9)
        a.update_state(v)
        b.update_state(v)
        assert abs(a.coherence_with(b) - 1.0) < 1e-10

    def test_coherence_orthogonal(self):
        a = RoomMusician("a")
        b = RoomMusician("b")
        a.update_state(FluxVector.unit(0))
        b.update_state(FluxVector.unit(1))
        assert abs(a.coherence_with(b)) < 1e-10

    def test_join_ensemble(self):
        conductor = RoomMusician("conductor")
        player = RoomMusician("player")
        player.join_ensemble(conductor)
        assert conductor.room_id in player.listeners

    def test_leave_ensemble(self):
        player = RoomMusician("loner")
        conductor = RoomMusician("cond")
        player.join_ensemble(conductor)
        player.leave_ensemble()
        assert len(player.listeners) == 0

    def test_room_id_is_unique(self):
        a = RoomMusician("dup")
        b = RoomMusician("dup")
        assert a.room_id != b.room_id

    def test_sidechannel_nod(self):
        a = RoomMusician("a")
        b = RoomMusician("b")
        a.listen_to(b)
        a.send_nod(b)
        msgs = b.receive_sidechannels()
        assert len(msgs["nods"]) > 0

    def test_sidechannel_smile(self):
        a = RoomMusician("a")
        b = RoomMusician("b")
        a.listen_to(b)
        a.send_smile(b)
        msgs = b.receive_sidechannels()
        assert len(msgs["smiles"]) > 0

    def test_sidechannel_frown(self):
        a = RoomMusician("a")
        b = RoomMusician("b")
        a.listen_to(b)
        a.send_frown(b)
        msgs = b.receive_sidechannels()
        assert len(msgs["frowns"]) > 0
