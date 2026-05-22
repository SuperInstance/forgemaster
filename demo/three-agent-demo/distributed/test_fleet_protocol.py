"""Tests for the binary fleet wire protocol."""

import struct
from fractions import Fraction

import pytest

from .fleet_protocol import (
    MAGIC,
    MessageType,
    ProtocolError,
    decode_message,
    decode_raw,
    encode_ack,
    encode_beacon,
    encode_cadence_call,
    encode_correction,
    encode_drift_report,
    encode_inherit,
    encode_leave,
    encode_message,
    encode_raw,
    encode_sunset,
    encode_tick,
    now_ms,
)


def test_now_ms_is_positive():
    assert now_ms() > 0


# ------------------------------------------------------------------
# Raw encode / decode
# ------------------------------------------------------------------

def test_encode_decode_roundtrip():
    payload = b"hello"
    raw = encode_raw(MessageType.TICK, sender_id=7, timestamp_ms=12345, payload=payload)
    assert len(raw) == 10 + len(payload) + 2
    decoded = decode_raw(raw)
    assert decoded["type"] == MessageType.TICK
    assert decoded["sender_id"] == 7
    assert decoded["timestamp_ms"] == 12345
    assert decoded["payload"] == payload


def test_bad_magic_raises():
    raw = encode_raw(MessageType.TICK, sender_id=1, timestamp_ms=0, payload=b"")
    # Corrupt magic
    bad = struct.pack(">I", 0xDEADBEEF) + raw[4:]
    with pytest.raises(ProtocolError, match="Bad magic"):
        decode_raw(bad)


def test_bad_crc_raises():
    raw = encode_raw(MessageType.TICK, sender_id=1, timestamp_ms=0, payload=b"")
    # Corrupt last byte
    bad = raw[:-1] + bytes([raw[-1] ^ 0xFF])
    with pytest.raises(ProtocolError, match="CRC mismatch"):
        decode_raw(bad)


def test_short_message_raises():
    with pytest.raises(ProtocolError, match="too short"):
        decode_raw(b"short")


def test_unknown_type_raises():
    raw = encode_raw(99, sender_id=1, timestamp_ms=0, payload=b"")
    with pytest.raises(ProtocolError, match="Unknown message type"):
        decode_raw(raw)


# ------------------------------------------------------------------
# BEACON
# ------------------------------------------------------------------

def test_beacon_roundtrip():
    theta = {
        "T": Fraction(1, 2),
        "phi0": 1234567890,
        "epsilon": Fraction(1, 1000),
        "delta": Fraction(1, 100),
    }
    raw = encode_beacon(
        sender_id=3,
        timestamp_ms=1000,
        uptime_ms=5000,
        theta=theta,
        known_peers={1, 2, 5},
    )
    msg = decode_message(raw)
    assert msg["type"] == MessageType.BEACON
    assert msg["sender_id"] == 3
    assert msg["timestamp_ms"] == 1000
    p = msg["payload"]
    assert p["uptime_ms"] == 5000
    assert p["theta"]["T"] == Fraction(1, 2)
    assert p["theta"]["phi0"] == 1234567890
    assert p["known_peers"] == {1, 2, 5}


# ------------------------------------------------------------------
# TICK
# ------------------------------------------------------------------

def test_tick_roundtrip():
    raw = encode_tick(
        sender_id=4,
        timestamp_ms=2000,
        beat=42,
        time_ms=9999,
        drift=0.123,
        state=1,
    )
    msg = decode_message(raw)
    assert msg["type"] == MessageType.TICK
    p = msg["payload"]
    assert p["beat"] == 42
    assert p["time_ms"] == 9999
    assert abs(p["drift"] - 0.123) < 1e-6
    assert p["state"] == 1


# ------------------------------------------------------------------
# DRIFT_REPORT
# ------------------------------------------------------------------

def test_drift_report_roundtrip():
    raw = encode_drift_report(
        sender_id=5,
        timestamp_ms=3000,
        from_node=1,
        to_node=2,
        drift_value=0.456,
    )
    msg = decode_message(raw)
    assert msg["type"] == MessageType.DRIFT_REPORT
    p = msg["payload"]
    assert p["from_node"] == 1
    assert p["to_node"] == 2
    assert abs(p["drift_value"] - 0.456) < 1e-6


# ------------------------------------------------------------------
# CADENCE_CALL
# ------------------------------------------------------------------

def test_cadence_call_roundtrip():
    raw = encode_cadence_call(
        sender_id=6,
        timestamp_ms=4000,
        caller_id=6,
        caller_uptime_ms=8000,
        claimed_tick=100,
    )
    msg = decode_message(raw)
    assert msg["type"] == MessageType.CADENCE_CALL
    p = msg["payload"]
    assert p["caller_id"] == 6
    assert p["caller_uptime_ms"] == 8000
    assert p["claimed_tick"] == 100


# ------------------------------------------------------------------
# CORRECTION
# ------------------------------------------------------------------

def test_correction_roundtrip():
    raw = encode_correction(
        sender_id=7,
        timestamp_ms=5000,
        from_node=1,
        to_node=2,
        correction_value=-0.05,
    )
    msg = decode_message(raw)
    assert msg["type"] == MessageType.CORRECTION
    p = msg["payload"]
    assert p["from_node"] == 1
    assert p["to_node"] == 2
    assert abs(p["correction_value"] - (-0.05)) < 1e-6


# ------------------------------------------------------------------
# SUNSET
# ------------------------------------------------------------------

def test_sunset_roundtrip():
    raw = encode_sunset(
        sender_id=8,
        timestamp_ms=6000,
        node_id=8,
        tile_count=42,
    )
    msg = decode_message(raw)
    assert msg["type"] == MessageType.SUNSET
    p = msg["payload"]
    assert p["node_id"] == 8
    assert p["tile_count"] == 42


# ------------------------------------------------------------------
# INHERIT
# ------------------------------------------------------------------

def test_inherit_roundtrip():
    tiles = {"foo": "bar", "count": 7}
    raw = encode_inherit(
        sender_id=9,
        timestamp_ms=7000,
        from_node=8,
        to_node=9,
        tiles_data=tiles,
    )
    msg = decode_message(raw)
    assert msg["type"] == MessageType.INHERIT
    p = msg["payload"]
    assert p["from_node"] == 8
    assert p["to_node"] == 9
    assert p["tiles_data"] == tiles


# ------------------------------------------------------------------
# ACK
# ------------------------------------------------------------------

def test_ack_roundtrip():
    raw = encode_ack(
        sender_id=10,
        timestamp_ms=8000,
        acked_type=MessageType.TICK,
        acked_timestamp_ms=1234,
    )
    msg = decode_message(raw)
    assert msg["type"] == MessageType.ACK
    p = msg["payload"]
    assert p["acked_type"] == MessageType.TICK
    assert p["acked_timestamp_ms"] == 1234


# ------------------------------------------------------------------
# LEAVE
# ------------------------------------------------------------------

def test_leave_roundtrip():
    raw = encode_leave(
        sender_id=11,
        timestamp_ms=9000,
        node_id=11,
    )
    msg = decode_message(raw)
    assert msg["type"] == MessageType.LEAVE
    p = msg["payload"]
    assert p["node_id"] == 11


# ------------------------------------------------------------------
# Convenience dispatcher
# ------------------------------------------------------------------

def test_encode_message_dispatcher():
    raw = encode_message(
        MessageType.SUNSET,
        sender_id=1,
        timestamp_ms=111,
        node_id=1,
        tile_count=5,
    )
    msg = decode_message(raw)
    assert msg["payload"]["tile_count"] == 5


def test_encode_message_auto_timestamp():
    before = now_ms()
    raw = encode_message(MessageType.ACK, sender_id=1, acked_type=2, acked_timestamp_ms=99)
    after = now_ms()
    msg = decode_message(raw)
    assert before <= msg["timestamp_ms"] <= after
