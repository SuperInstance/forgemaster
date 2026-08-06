"""Binary wire protocol for fleet communication.

Format:
    4 bytes : magic   (0xF1EE7)
    1 byte  : message type
    1 byte  : sender ID
    4 bytes : timestamp (ms since epoch)
    N bytes : payload (varies by type)
    2 bytes : CRC16
"""

from __future__ import annotations

import binascii
import json
import struct
import time
from enum import IntEnum
from fractions import Fraction
from typing import Any, Dict, Set

MAGIC = 0xF1EE7
# 8-byte timestamp because ms-since-epoch does not fit in 4 bytes (>4.2B).
_HEADER_FMT = ">IBBQ"
_HEADER_LEN = struct.calcsize(_HEADER_FMT)
_CRC_LEN = 2
_MIN_MSG_LEN = _HEADER_LEN + _CRC_LEN


class MessageType(IntEnum):
    BEACON = 1
    TICK = 2
    DRIFT_REPORT = 3
    CADENCE_CALL = 4
    CORRECTION = 5
    SUNSET = 6
    INHERIT = 7
    ACK = 8
    LEAVE = 9


class ProtocolError(ValueError):
    """Raised when a message fails magic/CRC/type validation."""


# ---------------------------------------------------------------------------
# Low-level primitives
# ---------------------------------------------------------------------------

def _crc16(data: bytes) -> int:
    """Compute CRC-16/HQX over data."""
    return binascii.crc_hqx(data, 0) & 0xFFFF


def encode_raw(msg_type: int, sender_id: int, timestamp_ms: int, payload: bytes) -> bytes:
    """Pack a message with header and CRC16 footer."""
    if not (0 <= sender_id <= 0xFF):
        raise ValueError(f"sender_id out of range: {sender_id}")
    header = struct.pack(_HEADER_FMT, MAGIC, msg_type, sender_id, timestamp_ms)
    body = header + payload
    crc = _crc16(body)
    return body + struct.pack(">H", crc)


def decode_raw(data: bytes) -> Dict[str, Any]:
    """Unpack and verify a raw message.

    Returns dict with keys: type (MessageType), sender_id, timestamp_ms, payload (bytes).
    Raises ProtocolError on any validation failure.
    """
    if len(data) < _MIN_MSG_LEN:
        raise ProtocolError(f"Message too short: {len(data)} bytes (need >= {_MIN_MSG_LEN})")

    magic, msg_type, sender_id, timestamp_ms = struct.unpack(_HEADER_FMT, data[:_HEADER_LEN])
    if magic != MAGIC:
        raise ProtocolError(f"Bad magic: 0x{magic:08X} (expected 0x{MAGIC:08X})")

    payload = data[_HEADER_LEN:-_CRC_LEN]
    recv_crc = struct.unpack(">H", data[-_CRC_LEN:])[0]
    calc_crc = _crc16(data[:-_CRC_LEN])
    if recv_crc != calc_crc:
        raise ProtocolError(f"CRC mismatch: {recv_crc:04X} != {calc_crc:04X}")

    if msg_type == 0:
        typ = 0  # Simple dict payload (not a MessageType enum value)
    else:
        try:
            typ = MessageType(msg_type)
        except ValueError as exc:
            raise ProtocolError(f"Unknown message type: {msg_type}") from exc

    return {
        "type": typ,
        "sender_id": sender_id,
        "timestamp_ms": timestamp_ms,
        "payload": payload,
    }


# ---------------------------------------------------------------------------
# Theta helpers (Fraction <-> JSON)
# ---------------------------------------------------------------------------

def _theta_to_json(theta: Dict[str, Any]) -> bytes:
    """Serialize theta = {T: Fraction, phi0: int/float, epsilon: Fraction, delta: Fraction}."""
    def frac_item(f: Fraction) -> list:
        return [f.numerator, f.denominator]
    obj = {
        "T": frac_item(theta["T"]),
        "phi0": theta["phi0"],
        "epsilon": frac_item(theta["epsilon"]),
        "delta": frac_item(theta["delta"]),
    }
    return json.dumps(obj, separators=(",", ":")).encode("utf-8")


def _theta_from_json(data: bytes) -> Dict[str, Any]:
    """Deserialize theta JSON back to dict with Fractions."""
    obj = json.loads(data.decode("utf-8"))
    return {
        "T": Fraction(*obj["T"]),
        "phi0": obj["phi0"],
        "epsilon": Fraction(*obj["epsilon"]),
        "delta": Fraction(*obj["delta"]),
    }


# ---------------------------------------------------------------------------
# Per-type encoders
# ---------------------------------------------------------------------------

def encode_beacon(
    sender_id: int,
    timestamp_ms: int,
    uptime_ms: int,
    theta: Dict[str, Any],
    known_peers: Set[int],
) -> bytes:
    """BEACON: peer discovery (node_id, uptime, θ, known_peers)."""
    theta_json = _theta_to_json(theta)
    peers_bytes = bytes(sorted(known_peers))
    payload = (
        struct.pack(">I", uptime_ms)
        + struct.pack(">H", len(theta_json))
        + theta_json
        + struct.pack(">B", len(peers_bytes))
        + peers_bytes
    )
    return encode_raw(MessageType.BEACON, sender_id, timestamp_ms, payload)


def decode_beacon(data: bytes) -> Dict[str, Any]:
    """Decode BEACON payload."""
    if len(data) < 6:
        raise ProtocolError("BEACON payload too short")
    uptime_ms = struct.unpack(">I", data[:4])[0]
    theta_len = struct.unpack(">H", data[4:6])[0]
    offset = 6
    theta = _theta_from_json(data[offset : offset + theta_len])
    offset += theta_len
    peers_len = struct.unpack(">B", data[offset : offset + 1])[0]
    offset += 1
    known_peers = set(data[offset : offset + peers_len])
    return {
        "uptime_ms": uptime_ms,
        "theta": theta,
        "known_peers": known_peers,
    }


def encode_tick(
    sender_id: int,
    timestamp_ms: int,
    beat: int,
    time_ms: int,
    drift: float,
    state: int,
) -> bytes:
    """TICK: clock tick (beat, time, drift, state)."""
    payload = struct.pack(">IIfB", beat, time_ms, drift, state)
    return encode_raw(MessageType.TICK, sender_id, timestamp_ms, payload)


def decode_tick(data: bytes) -> Dict[str, Any]:
    if len(data) < 13:
        raise ProtocolError("TICK payload too short")
    beat, time_ms, drift, state = struct.unpack(">IIfB", data[:13])
    return {"beat": beat, "time_ms": time_ms, "drift": drift, "state": state}


def encode_drift_report(
    sender_id: int,
    timestamp_ms: int,
    from_node: int,
    to_node: int,
    drift_value: float,
) -> bytes:
    """DRIFT_REPORT: drift exceeded threshold (from, to, drift_value)."""
    payload = struct.pack(">BBf", from_node, to_node, drift_value)
    return encode_raw(MessageType.DRIFT_REPORT, sender_id, timestamp_ms, payload)


def decode_drift_report(data: bytes) -> Dict[str, Any]:
    if len(data) < 6:
        raise ProtocolError("DRIFT_REPORT payload too short")
    from_node, to_node, drift_value = struct.unpack(">BBf", data[:6])
    return {"from_node": from_node, "to_node": to_node, "drift_value": drift_value}


def encode_cadence_call(
    sender_id: int,
    timestamp_ms: int,
    caller_id: int,
    caller_uptime_ms: int,
    claimed_tick: int,
) -> bytes:
    """CADENCE_CALL: election (caller_id, caller_uptime, claimed_tick)."""
    payload = struct.pack(">BII", caller_id, caller_uptime_ms, claimed_tick)
    return encode_raw(MessageType.CADENCE_CALL, sender_id, timestamp_ms, payload)


def decode_cadence_call(data: bytes) -> Dict[str, Any]:
    if len(data) < 9:
        raise ProtocolError("CADENCE_CALL payload too short")
    caller_id, caller_uptime_ms, claimed_tick = struct.unpack(">BII", data[:9])
    return {
        "caller_id": caller_id,
        "caller_uptime_ms": caller_uptime_ms,
        "claimed_tick": claimed_tick,
    }


def encode_correction(
    sender_id: int,
    timestamp_ms: int,
    from_node: int,
    to_node: int,
    correction_value: float,
) -> bytes:
    """CORRECTION: deadband correction (from, to, correction_value)."""
    payload = struct.pack(">BBf", from_node, to_node, correction_value)
    return encode_raw(MessageType.CORRECTION, sender_id, timestamp_ms, payload)


def decode_correction(data: bytes) -> Dict[str, Any]:
    if len(data) < 6:
        raise ProtocolError("CORRECTION payload too short")
    from_node, to_node, correction_value = struct.unpack(">BBf", data[:6])
    return {
        "from_node": from_node,
        "to_node": to_node,
        "correction_value": correction_value,
    }


def encode_sunset(
    sender_id: int,
    timestamp_ms: int,
    node_id: int,
    tile_count: int,
) -> bytes:
    """SUNSET: graceful retirement (node_id, tile_count)."""
    payload = struct.pack(">BI", node_id, tile_count)
    return encode_raw(MessageType.SUNSET, sender_id, timestamp_ms, payload)


def decode_sunset(data: bytes) -> Dict[str, Any]:
    if len(data) < 5:
        raise ProtocolError("SUNSET payload too short")
    node_id, tile_count = struct.unpack(">BI", data[:5])
    return {"node_id": node_id, "tile_count": tile_count}


def encode_inherit(
    sender_id: int,
    timestamp_ms: int,
    from_node: int,
    to_node: int,
    tiles_data: Dict[str, Any],
) -> bytes:
    """INHERIT: tile transfer (from, to, tiles_data)."""
    tiles_json = json.dumps(tiles_data, separators=(",", ":")).encode("utf-8")
    payload = struct.pack(">BB", from_node, to_node) + struct.pack(">H", len(tiles_json)) + tiles_json
    return encode_raw(MessageType.INHERIT, sender_id, timestamp_ms, payload)


def decode_inherit(data: bytes) -> Dict[str, Any]:
    if len(data) < 4:
        raise ProtocolError("INHERIT payload too short")
    from_node, to_node = struct.unpack(">BB", data[:2])
    tiles_len = struct.unpack(">H", data[2:4])[0]
    tiles_data = json.loads(data[4 : 4 + tiles_len].decode("utf-8"))
    return {"from_node": from_node, "to_node": to_node, "tiles_data": tiles_data}


def encode_ack(
    sender_id: int,
    timestamp_ms: int,
    acked_type: int,
    acked_timestamp_ms: int,
) -> bytes:
    """ACK: acknowledgment."""
    payload = struct.pack(">BI", acked_type, acked_timestamp_ms)
    return encode_raw(MessageType.ACK, sender_id, timestamp_ms, payload)


def decode_ack(data: bytes) -> Dict[str, Any]:
    if len(data) < 5:
        raise ProtocolError("ACK payload too short")
    acked_type, acked_timestamp_ms = struct.unpack(">BI", data[:5])
    return {"acked_type": acked_type, "acked_timestamp_ms": acked_timestamp_ms}


def encode_leave(
    sender_id: int,
    timestamp_ms: int,
    node_id: int,
) -> bytes:
    """LEAVE: graceful departure announcement."""
    payload = struct.pack(">B", node_id)
    return encode_raw(MessageType.LEAVE, sender_id, timestamp_ms, payload)


def decode_leave(data: bytes) -> Dict[str, Any]:
    if len(data) < 1:
        raise ProtocolError("LEAVE payload too short")
    node_id = struct.unpack(">B", data[:1])[0]
    return {"node_id": node_id}


# ---------------------------------------------------------------------------
# Convenience dispatcher
# ---------------------------------------------------------------------------

ENCODERS = {
    MessageType.BEACON: encode_beacon,
    MessageType.TICK: encode_tick,
    MessageType.DRIFT_REPORT: encode_drift_report,
    MessageType.CADENCE_CALL: encode_cadence_call,
    MessageType.CORRECTION: encode_correction,
    MessageType.SUNSET: encode_sunset,
    MessageType.INHERIT: encode_inherit,
    MessageType.ACK: encode_ack,
    MessageType.LEAVE: encode_leave,
}

DECODERS = {
    MessageType.BEACON: decode_beacon,
    MessageType.TICK: decode_tick,
    MessageType.DRIFT_REPORT: decode_drift_report,
    MessageType.CADENCE_CALL: decode_cadence_call,
    MessageType.CORRECTION: decode_correction,
    MessageType.SUNSET: decode_sunset,
    MessageType.INHERIT: decode_inherit,
    MessageType.ACK: decode_ack,
    MessageType.LEAVE: decode_leave,
}


def encode_message(msg_type: MessageType, sender_id: int, **kwargs) -> bytes:
    """Encode a message by type.  Additional kwargs are forwarded to the per-type encoder.

    The ``timestamp_ms`` kwarg is automatically injected (rounded ``time.time()*1000``)
    unless you pass it explicitly.
    """
    if msg_type not in ENCODERS:
        raise ProtocolError(f"No encoder for {msg_type}")
    if "timestamp_ms" not in kwargs:
        kwargs["timestamp_ms"] = int(time.time() * 1000)
    return ENCODERS[msg_type](sender_id=sender_id, **kwargs)


def decode_message(data: bytes) -> Dict[str, Any]:
    """Decode a full message (header + payload + CRC) and return a dict with:

    - type: MessageType
    - sender_id: int
    - timestamp_ms: int
    - payload: dict (type-specific)
    """
    raw = decode_raw(data)
    decoder = DECODERS.get(raw["type"])
    if decoder is None:
        raise ProtocolError(f"No decoder for {raw['type']}")
    parsed = decoder(raw["payload"])
    return {
        "type": raw["type"],
        "sender_id": raw["sender_id"],
        "timestamp_ms": raw["timestamp_ms"],
        "payload": parsed,
    }


def now_ms() -> int:
    """Current timestamp in milliseconds since epoch."""
    return int(time.time() * 1000)
