"""Tensor-MIDI encoding — INT8 wire format for fleet clock data.

Encodes clock state as compact byte sequences for UDP transmission.
Uses INT8 quantization for drift values and Fraction serialization for timestamps.
"""

from __future__ import annotations

import struct
from fractions import Fraction
from typing import Tuple


# INT8 range
INT8_MIN = -128
INT8_MAX = 127

# Quantization scale: maps Fraction drift to INT8
# drift_in_ticks * SCALE → INT8 (clamped)
DEFAULT_SCALE = 1000  # 0.001 tick resolution


def quantize_int8(value: Fraction, scale: int = DEFAULT_SCALE) -> int:
    """Quantize a Fraction to INT8 with given scale.

    Returns clamped integer in [-128, 127].
    """
    raw = int(value * scale)
    return max(INT8_MIN, min(INT8_MAX, raw))


def dequantize_int8(encoded: int, scale: int = DEFAULT_SCALE) -> Fraction:
    """Dequantize an INT8 back to a Fraction."""
    return Fraction(encoded, scale)


def encode_drift(drift: Fraction, scale: int = DEFAULT_SCALE) -> bytes:
    """Encode a drift Fraction as a single INT8 byte."""
    return struct.pack(">b", quantize_int8(drift, scale))


def decode_drift(data: bytes, offset: int = 0, scale: int = DEFAULT_SCALE) -> Fraction:
    """Decode an INT8 byte to a drift Fraction."""
    val = struct.unpack_from(">b", data, offset)[0]
    return dequantize_int8(val, scale)


def encode_fraction(f: Fraction) -> bytes:
    """Encode a Fraction as: [4B numerator] [4B denominator]."""
    return struct.pack(">ii", f.numerator, f.denominator)


def decode_fraction(data: bytes, offset: int = 0) -> Tuple[Fraction, int]:
    """Decode a Fraction from bytes. Returns (Fraction, bytes_consumed)."""
    num, den = struct.unpack_from(">ii", data, offset)
    return Fraction(num, den), 8


def encode_clock_snapshot(
    true_time: Fraction,
    offset: Fraction,
    drift_rate: Fraction,
) -> bytes:
    """Encode a full clock snapshot as compact bytes.

    Format:
        [4B true_time_num] [4B true_time_den]
        [1B offset INT8]
        [4B drift_rate_num] [4B drift_rate_den]
    Total: 17 bytes.
    """
    buf = bytearray()
    buf.extend(encode_fraction(true_time))
    buf.extend(encode_drift(offset))
    buf.extend(encode_fraction(drift_rate))
    return bytes(buf)


def decode_clock_snapshot(data: bytes, offset: int = 0) -> dict:
    """Decode a clock snapshot. Returns dict with Fraction fields."""
    pos = offset

    true_time, consumed = decode_fraction(data, pos)
    pos += consumed

    drift_val = decode_drift(data, pos)
    pos += 1

    drift_rate, consumed = decode_fraction(data, pos)
    pos += consumed

    return {
        "true_time": true_time,
        "offset": drift_val,
        "drift_rate": drift_rate,
    }


def encode_tile(tick: int, agent_id: int, local_time: Fraction, drift: Fraction) -> bytes:
    """Encode a PLATO tile for transmission.

    Format:
        [4B tick] [1B agent_id] [8B local_time Fraction] [1B drift INT8]
    Total: 14 bytes.
    """
    buf = bytearray()
    buf.extend(struct.pack(">IB", tick, agent_id))
    buf.extend(encode_fraction(local_time))
    buf.extend(encode_drift(drift))
    return bytes(buf)


def decode_tile(data: bytes, offset: int = 0) -> dict:
    """Decode a PLATO tile."""
    pos = offset
    tick, agent_id = struct.unpack_from(">IB", data, pos)
    pos += 5

    local_time, consumed = decode_fraction(data, pos)
    pos += consumed

    drift = decode_drift(data, pos)

    return {
        "tick": tick,
        "agent_id": agent_id,
        "local_time": local_time,
        "drift": drift,
    }
