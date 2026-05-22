"""Binary wire protocol for fleet UDP communication.

Message format (big-endian):
    [4B magic 0xF1EE7] [1B type] [1B sender] [8B timestamp_ms]
    [N bytes payload]
    [2B CRC16]

All timestamps are ms-since-epoch (int64).
"""

from __future__ import annotations

import binascii
import json
import struct
import time
from enum import IntEnum
from fractions import Fraction
from typing import Any, Dict, Optional, Set

MAGIC = 0xF1EE7

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
    """Raised on magic/CRC/type validation failure."""


# -- CRC -------------------------------------------------------------------

def _crc16(data: bytes) -> int:
    return binascii.crc_hqx(data, 0) & 0xFFFF


# -- Raw encode/decode -----------------------------------------------------

def encode_raw(msg_type: int, sender_id: int, timestamp_ms: int, payload: bytes = b"") -> bytes:
    if not (0 <= sender_id <= 0xFF):
        raise ValueError(f"sender_id out of range: {sender_id}")
    header = struct.pack(_HEADER_FMT, MAGIC, msg_type, sender_id, timestamp_ms)
    body = header + payload
    crc = _crc16(body)
    return body + struct.pack(">H", crc)


def decode_raw(data: bytes) -> Dict[str, Any]:
    if len(data) < _MIN_MSG_LEN:
        raise ProtocolError(f"Message too short: {len(data)} bytes")
    magic, msg_type, sender_id, timestamp_ms = struct.unpack(_HEADER_FMT, data[:_HEADER_LEN])
    if magic != MAGIC:
        raise ProtocolError(f"Bad magic: 0x{magic:08X}")
    payload = data[_HEADER_LEN:-_CRC_LEN]
    recv_crc = struct.unpack(">H", data[-_CRC_LEN:])[0]
    calc_crc = _crc16(data[:-_CRC_LEN])
    if recv_crc != calc_crc:
        raise ProtocolError(f"CRC mismatch: {recv_crc:04X} != {calc_crc:04X}")
    try:
        typ = MessageType(msg_type)
    except ValueError as exc:
        raise ProtocolError(f"Unknown message type: {msg_type}") from exc
    return {"type": typ, "sender_id": sender_id, "timestamp_ms": timestamp_ms, "payload": payload}


# -- Convenience encoders --------------------------------------------------

def encode_beacon(sender_id: int, timestamp_ms: int, uptime_ms: int, known_peers: Set[int]) -> bytes:
    peers_bytes = bytes(sorted(known_peers))
    payload = struct.pack(">I", uptime_ms) + struct.pack(">B", len(peers_bytes)) + peers_bytes
    return encode_raw(MessageType.BEACON, sender_id, timestamp_ms, payload)


def decode_beacon(payload: bytes) -> Dict[str, Any]:
    uptime_ms = struct.unpack(">I", payload[:4])[0]
    peers_len = payload[4]
    known_peers = set(payload[5 : 5 + peers_len])
    return {"uptime_ms": uptime_ms, "known_peers": known_peers}


def encode_tick(sender_id: int, timestamp_ms: int, beat: int, time_ms: int, drift: float, state: int) -> bytes:
    payload = struct.pack(">IIfB", beat, time_ms, drift, state)
    return encode_raw(MessageType.TICK, sender_id, timestamp_ms, payload)


def decode_tick(payload: bytes) -> Dict[str, Any]:
    beat, time_ms, drift, state = struct.unpack(">IIfB", payload[:13])
    return {"beat": beat, "time_ms": time_ms, "drift": drift, "state": state}


def encode_sunset(sender_id: int, timestamp_ms: int, data: dict) -> bytes:
    """Encode sunset (retirement) payload as JSON."""
    json_bytes = json.dumps({k: str(v) for k, v in data.items()}).encode()
    return encode_raw(MessageType.SUNSET, sender_id, timestamp_ms, json_bytes)


def decode_sunset(payload: bytes) -> Dict[str, Any]:
    raw = json.loads(payload.decode())
    # Convert string-encoded Fractions back
    result = {}
    for k, v in raw.items():
        try:
            result[k] = Fraction(v)
        except (ValueError, ZeroDivisionError):
            result[k] = v
    return result


def encode_correction(sender_id: int, timestamp_ms: int, target_id: int, correction_num: int, correction_den: int) -> bytes:
    payload = struct.pack(">Bii", target_id, correction_num, correction_den)
    return encode_raw(MessageType.CORRECTION, sender_id, timestamp_ms, payload)


def decode_correction(payload: bytes) -> Dict[str, Any]:
    target_id, num, den = struct.unpack(">Bii", payload[:9])
    return {"target_id": target_id, "correction": Fraction(num, den)}


def encode_leave(sender_id: int, timestamp_ms: int) -> bytes:
    return encode_raw(MessageType.LEAVE, sender_id, timestamp_ms)


def encode_ack(sender_id: int, timestamp_ms: int, ack_type: int) -> bytes:
    payload = struct.pack(">B", ack_type)
    return encode_raw(MessageType.ACK, sender_id, timestamp_ms, payload)


def now_ms() -> int:
    return int(time.time() * 1000)
