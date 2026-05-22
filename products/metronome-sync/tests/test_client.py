"""Tests for metronome-sync library."""

import time
from fractions import Fraction

import pytest

from metronome_sync import MetronomeClient, FleetConfig, PtpMode
from metronome_sync.fraction_clock import FractionClock
from metronome_sync.ptp import (
    PeerSample,
    OffsetEstimator,
    compute_offset,
    compute_offset_from_sample,
    weighted_offsets,
)
from metronome_sync.topology import build_laman, is_laman, peer_map, laman_coupling_matrix
from metronome_sync.tensor_midi import (
    quantize_int8, dequantize_int8, encode_drift, decode_drift,
    encode_fraction, decode_fraction,
    encode_clock_snapshot, decode_clock_snapshot,
    encode_tile, decode_tile,
)
from metronome_sync.protocol import (
    MAGIC, MessageType, ProtocolError,
    encode_raw, decode_raw,
    encode_beacon, decode_beacon,
    encode_tick, decode_tick,
    encode_sunset, decode_sunset,
    encode_correction, decode_correction,
    encode_leave, now_ms,
)
from metronome_sync.sunset import SunsetPayload, sunset, inherit, tiles_from_history


# -- FractionClock tests (5) -----------------------------------------------

class TestFractionClock:
    def test_initial_state(self):
        c = FractionClock()
        assert c.true_time == Fraction(0)
        assert c.offset == Fraction(0)
        assert c.local_time == Fraction(0)

    def test_tick_increments(self):
        c = FractionClock()
        c.tick()
        assert c.true_time == Fraction(1)
        assert c.local_time == Fraction(1)

    def test_drift_accumulates(self):
        c = FractionClock(drift_rate=Fraction(1, 100))
        for _ in range(100):
            c.tick()
        assert c.true_time == Fraction(100)
        assert c.offset == Fraction(1)  # 100 * 1/100
        assert c.drift == Fraction(1)

    def test_correction(self):
        c = FractionClock()
        c.tick()
        c.correct(Fraction(-1, 10))
        assert c.offset == Fraction(-1, 10)
        assert c.local_time == Fraction(9, 10)

    def test_snap_to(self):
        c = FractionClock()
        c.tick()
        c.tick()
        c.snap_to(Fraction(100))
        assert c.local_time == Fraction(100)
        assert c.true_time == Fraction(2)
        assert c.offset == Fraction(98)


# -- PTP offset tests (6) --------------------------------------------------

class TestPtpOffset:
    def test_naive_zero_rtt(self):
        off = compute_offset(Fraction(100), Fraction(105), Fraction(0), PtpMode.NAIVE)
        assert off == Fraction(5)

    def test_ptp_with_rtt(self):
        off = compute_offset(Fraction(100), Fraction(110), Fraction(10), PtpMode.PTP)
        # offset = remote - (local + rtt/2) = 110 - (100 + 5) = 5
        assert off == Fraction(5)

    def test_cristian_with_rtt(self):
        off = compute_offset(Fraction(100), Fraction(110), Fraction(10), PtpMode.CRISTIAN)
        # (remote - rtt/2) - local = (110-5) - 100 = 5
        assert off == Fraction(5)

    def test_negative_offset(self):
        off = compute_offset(Fraction(110), Fraction(100), Fraction(0), PtpMode.PTP)
        assert off == Fraction(-10)

    def test_peer_sample(self):
        s = PeerSample(
            local_sent=Fraction(100), remote_recv=Fraction(150),
            remote_sent=Fraction(151), local_recv=Fraction(110),
            weight=Fraction(1),
        )
        assert s.rtt == Fraction(10)
        off = compute_offset_from_sample(s)
        # ((150-100) + (151-110)) / 2 = (50 + 41) / 2 = 91/2
        assert off == Fraction(91, 2)

    def test_weighted_offsets_zero_samples(self):
        assert weighted_offsets([]) == Fraction(0)


# -- OffsetEstimator tests (3) ---------------------------------------------

class TestOffsetEstimator:
    def test_first_update(self):
        e = OffsetEstimator()
        result = e.update(Fraction(5))
        assert result == Fraction(5)
        assert e.sample_count == 1

    def test_ema_converges(self):
        e = OffsetEstimator(alpha=Fraction(1, 2))
        e.update(Fraction(10))
        e.update(Fraction(0))
        e.update(Fraction(0))
        # 10 -> 5 -> 5/2 -> 5/4
        # After 3 updates: first sets ema=10, then 0.5*0+0.5*10=5, then 0.5*0+0.5*5=5/2
        # Wait — update(10) sets ema=10, update(0): 0.5*0+0.5*10=5, update(0): 0.5*0+0.5*5=5/2
        assert e.value == Fraction(5, 2)

    def test_reset(self):
        e = OffsetEstimator()
        e.update(Fraction(5))
        e.reset()
        assert e.value == Fraction(0)
        assert e.sample_count == 0


# -- Topology tests (4) ----------------------------------------------------

class TestTopology:
    def test_k3_base(self):
        verts, edges = build_laman(3)
        assert len(edges) == 3
        assert is_laman(3, edges)

    def test_laman_edge_count(self):
        for n in [4, 5, 6, 7, 8]:
            verts, edges = build_laman(n)
            assert len(edges) == 2 * n - 3
            assert is_laman(n, edges)

    def test_peer_map(self):
        _, edges = build_laman(4)
        pm = peer_map(edges)
        # Every vertex should have at least 2 peers
        for v, peers in pm.items():
            assert len(peers) >= 2

    def test_coupling_matrix(self):
        verts, edges = build_laman(4)
        mat = laman_coupling_matrix(4, edges)
        # Row sums should be zero
        for row in mat:
            assert sum(row) == Fraction(0)


# -- Tensor-MIDI tests (4) -------------------------------------------------

class TestTensorMidi:
    def test_roundtrip_fraction(self):
        f = Fraction(22, 7)
        encoded = encode_fraction(f)
        decoded, _ = decode_fraction(encoded)
        assert decoded == f

    def test_int8_quantize(self):
        assert quantize_int8(Fraction(0)) == 0
        assert quantize_int8(Fraction(1, 1000)) == 1
        assert quantize_int8(Fraction(-1, 1000)) == -1
        # Clamping
        assert quantize_int8(Fraction(1)) == 127
        assert quantize_int8(Fraction(-1)) == -128

    def test_clock_snapshot_roundtrip(self):
        snap = encode_clock_snapshot(Fraction(100), Fraction(1, 100), Fraction(1, 1000))
        decoded = decode_clock_snapshot(snap)
        assert decoded["true_time"] == Fraction(100)
        assert decoded["drift_rate"] == Fraction(1, 1000)

    def test_tile_roundtrip(self):
        tile = encode_tile(42, 3, Fraction(1000), Fraction(1, 50))
        decoded = decode_tile(tile)
        assert decoded["tick"] == 42
        assert decoded["agent_id"] == 3
        assert decoded["local_time"] == Fraction(1000)


# -- Protocol tests (4) ----------------------------------------------------

class TestProtocol:
    def test_raw_roundtrip(self):
        msg = encode_raw(MessageType.TICK, 5, 1000, b"hello")
        decoded = decode_raw(msg)
        assert decoded["type"] == MessageType.TICK
        assert decoded["sender_id"] == 5
        assert decoded["timestamp_ms"] == 1000
        assert decoded["payload"] == b"hello"

    def test_bad_magic(self):
        msg = encode_raw(MessageType.TICK, 1, 1000, b"x")
        corrupted = (MAGIC + 1).to_bytes(4, "big") + msg[4:]
        with pytest.raises(ProtocolError, match="Bad magic"):
            decode_raw(corrupted)

    def test_crc_mismatch(self):
        msg = encode_raw(MessageType.BEACON, 1, 1000, b"test")
        corrupted = msg[:-1] + bytes([(msg[-1] + 1) & 0xFF])
        with pytest.raises(ProtocolError, match="CRC mismatch"):
            decode_raw(corrupted)

    def test_beacon_roundtrip(self):
        msg = encode_beacon(1, now_ms(), 5000, {2, 3, 5})
        decoded = decode_raw(msg)
        beacon = decode_beacon(decoded["payload"])
        assert beacon["uptime_ms"] == 5000
        assert beacon["known_peers"] == {2, 3, 5}


# -- Sunset tests (3) ------------------------------------------------------

class TestSunset:
    def test_sunset_payload_roundtrip(self):
        p = SunsetPayload(
            true_time=Fraction(1000),
            offset=Fraction(1, 50),
            drift_rate=Fraction(1, 1000),
            tick_count=1000,
        )
        d = p.to_dict()
        p2 = SunsetPayload.from_dict(d)
        assert p2.true_time == Fraction(1000)
        assert p2.tick_count == 1000

    def test_inherit(self):
        payload = SunsetPayload(
            true_time=Fraction(500),
            offset=Fraction(1, 10),
            drift_rate=Fraction(1, 100),
        )
        cal = inherit(payload)
        assert cal["true_time"] == Fraction(500)
        assert cal["offset"] == Fraction(1, 10)

    def test_tiles_from_history(self):
        tiles = tiles_from_history("agent-1", [(1, Fraction(1), Fraction(0)), (2, Fraction(2), Fraction(0))])
        assert len(tiles) == 4  # 2 ticks * 2 keys


# -- MetronomeClient integration tests (4) ----------------------------------

class TestMetronomeClient:
    def test_start_stop(self):
        c = MetronomeClient(FleetConfig(name="test", tick_interval=0.01))
        c.start()
        time.sleep(0.05)
        t = c.now()
        assert t > Fraction(0)
        c.stop()
        assert c.fleet_status()["running"] is False

    def test_correction(self):
        c = MetronomeClient(FleetConfig(name="test"))
        c._clock.tick()
        c._clock.tick()
        assert c.now() == Fraction(2)
        c.correct(Fraction(-1))
        assert c.now() == Fraction(1)

    def test_fleet_topology(self):
        topo = MetronomeClient.build_fleet_topology(5)
        assert topo["is_rigid"]
        assert len(topo["edges"]) == 7  # 2*5-3

    def test_sunset_produces_tiles(self):
        c = MetronomeClient(FleetConfig(name="test"))
        for _ in range(10):
            c._clock.tick()
            c._tick_count += 1
            c._history.append((c._tick_count, c._clock.local_time, c._clock.drift))
        tiles = c.sunset()
        assert len(tiles) > 0
        # Last tile should be the sunset metadata
        assert tiles[-1].key == "sunset"
