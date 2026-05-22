//! INT8 Tensor-MIDI encoding for compact wire representation of clock state.
//!
//! Encodes Fraction timestamps and offsets as quantized INT8 tensors
//! compatible with MIDI-style byte streams. Each value is mapped to [-127, 127]
//! with a configurable scale factor.

use crate::fraction_clock::Fraction;

extern crate alloc;
use alloc::vec::Vec;

/// Magic bytes for fleet-clock Tensor-MIDI frames.
pub const FLEET_MAGIC: [u8; 2] = [0xF1, 0xEE];

/// Message types (compatible with fleet protocol).
#[repr(u8)]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum MessageType {
    Beacon = 1,
    Tick = 2,
    DriftReport = 3,
    CadenceCall = 4,
    Correction = 5,
    Sunset = 6,
    Inherit = 7,
    Ack = 8,
    Leave = 9,
}

impl TryFrom<u8> for MessageType {
    type Error = ();
    fn try_from(v: u8) -> Result<Self, ()> {
        match v {
            1 => Ok(MessageType::Beacon),
            2 => Ok(MessageType::Tick),
            3 => Ok(MessageType::DriftReport),
            4 => Ok(MessageType::CadenceCall),
            5 => Ok(MessageType::Correction),
            6 => Ok(MessageType::Sunset),
            7 => Ok(MessageType::Inherit),
            8 => Ok(MessageType::Ack),
            9 => Ok(MessageType::Leave),
            _ => Err(()),
        }
    }
}

/// Tensor-MIDI encoder/decoder.
#[derive(Clone, Debug)]
pub struct TensorMidi {
    /// Scale factor: maps Fraction range to INT8 [-127, 127].
    pub scale: Fraction,
}

impl TensorMidi {
    /// Create encoder with default scale (1/1).
    pub fn new() -> Self {
        TensorMidi {
            scale: Fraction::ONE,
        }
    }

    /// Create encoder with custom scale.
    pub fn with_scale(scale: Fraction) -> Self {
        TensorMidi { scale }
    }

    /// Quantize a Fraction to INT8.
    ///
    /// Returns i8 clamped to [-127, 127].
    pub fn quantize(&self, value: Fraction) -> i8 {
        let scaled = value.mul(self.scale).to_f64();
        let clamped = if scaled > 127.0 {
            127.0
        } else if scaled < -127.0 {
            -127.0
        } else {
            scaled
        };
        clamped.round() as i8
    }

    /// Dequantize an INT8 back to Fraction.
    pub fn dequantize(&self, value: i8) -> Fraction {
        Fraction::new(value as i64, 1).mul(Fraction::new(
            self.scale.den as i64,
            self.scale.num.unsigned_abs(),
        ))
    }

    /// Encode a tick message into a byte buffer.
    ///
    /// Format:
    ///   [0xF1, 0xEE] magic (2 bytes)
    ///   msg_type (1 byte)
    ///   sender_id (1 byte)
    ///   timestamp_quantized (1 byte, INT8)
    ///   payload_len (1 byte)
    ///   payload (variable)
    ///   crc16 (2 bytes)
    pub fn encode_tick(&self, sender_id: u8, timestamp: Fraction, payload: &[u8]) -> Vec<u8> {
        let mut buf = Vec::with_capacity(8 + payload.len());
        buf.extend_from_slice(&FLEET_MAGIC);
        buf.push(MessageType::Tick as u8);
        buf.push(sender_id);
        buf.push(self.quantize(timestamp) as u8);
        buf.push(payload.len() as u8);
        buf.extend_from_slice(payload);

        let crc = crc16(&buf);
        buf.push(((crc >> 8) & 0xFF) as u8);
        buf.push((crc & 0xFF) as u8);
        buf
    }

    /// Decode a tick message. Returns (sender_id, quantized_timestamp, payload).
    ///
    /// Validates magic and CRC.
    pub fn decode_tick(&self, data: &[u8]) -> Result<(u8, Fraction, Vec<u8>), DecodeError> {
        if data.len() < 8 {
            return Err(DecodeError::TooShort);
        }
        if data[0] != FLEET_MAGIC[0] || data[1] != FLEET_MAGIC[1] {
            return Err(DecodeError::BadMagic);
        }

        let msg_type = data[2];
        if msg_type != MessageType::Tick as u8 {
            return Err(DecodeError::WrongType);
        }

        let sender_id = data[3];
        let quant_ts = data[4] as i8;
        let payload_len = data[5] as usize;

        if data.len() < 6 + payload_len + 2 {
            return Err(DecodeError::TooShort);
        }

        // Verify CRC
        let body_end = 6 + payload_len;
        let calc_crc = crc16(&data[..body_end]);
        let recv_crc = ((data[body_end] as u16) << 8) | data[body_end + 1] as u16;
        if calc_crc != recv_crc {
            return Err(DecodeError::CrcMismatch);
        }

        let payload = data[6..body_end].to_vec();
        let timestamp = self.dequantize(quant_ts);

        Ok((sender_id, timestamp, payload))
    }

    /// Encode a drift report as INT8 tensor.
    ///
    /// Packs N drift values into a compact byte stream.
    pub fn encode_drift_tensor(&self, drifts: &[Fraction]) -> Vec<i8> {
        drifts.iter().map(|d| self.quantize(*d)).collect()
    }

    /// Decode an INT8 tensor back to Fractions.
    pub fn decode_drift_tensor(&self, tensor: &[i8]) -> Vec<Fraction> {
        tensor.iter().map(|v| self.dequantize(*v)).collect()
    }
}

impl Default for TensorMidi {
    fn default() -> Self {
        Self::new()
    }
}

/// Decode error types.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum DecodeError {
    TooShort,
    BadMagic,
    WrongType,
    CrcMismatch,
}

/// CRC-16/HQX (same as Python's binascii.crc_hqx).
fn crc16(data: &[u8]) -> u16 {
    let mut crc: u16 = 0;
    for &byte in data {
        crc ^= (byte as u16) << 8;
        for _ in 0..8 {
            if crc & 0x8000 != 0 {
                crc = (crc << 1) ^ 0x1021;
            } else {
                crc <<= 1;
            }
        }
    }
    crc
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_quantize_roundtrip() {
        let tm = TensorMidi::new();
        let val = Fraction::new(42, 1);
        let q = tm.quantize(val);
        assert_eq!(q, 42);
    }

    #[test]
    fn test_quantize_clamp() {
        let tm = TensorMidi::new();
        let val = Fraction::new(200, 1);
        assert_eq!(tm.quantize(val), 127);
        assert_eq!(tm.quantize(Fraction::new(-200, 1)), -127);
    }

    #[test]
    fn test_encode_decode_tick() {
        let tm = TensorMidi::new();
        let ts = Fraction::new(50, 1);
        let payload = b"hello";
        let encoded = tm.encode_tick(0x42, ts, payload);
        let (sender, decoded_ts, decoded_payload) = tm.decode_tick(&encoded).unwrap();
        assert_eq!(sender, 0x42);
        assert_eq!(decoded_payload, payload);
    }

    #[test]
    fn test_bad_magic() {
        let tm = TensorMidi::new();
        let bad = vec![0x00, 0x00, 2, 0, 0, 0, 0, 0];
        assert_eq!(tm.decode_tick(&bad), Err(DecodeError::BadMagic));
    }

    #[test]
    fn test_drift_tensor() {
        let tm = TensorMidi::new();
        let drifts = vec![Fraction::new(1, 1), Fraction::new(-2, 1), Fraction::new(3, 1)];
        let tensor = tm.encode_drift_tensor(&drifts);
        assert_eq!(tensor, vec![1, -2, 3]);
    }
}
