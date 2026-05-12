//! FLUX packet encode/decode

use crate::zeitgeist::Zeitgeist;

/// FLUX magic bytes: 0xFLUX
pub const FLUX_MAGIC: [u8; 4] = [0x46, 0x4C, 0x55, 0x58]; // "FLUX"

/// Packet flags
pub const FLAG_COMPRESSED: u8 = 0x01;
pub const FLAG_ENCRYPTED: u8 = 0x02;

/// FLUX packet — the wire format for Zeitgeist transference
#[derive(Debug, Clone, PartialEq)]
pub struct FluxPacket {
    pub magic: [u8; 4],
    pub version: u16,
    pub flags: u8,
    pub source: u32,
    pub target: u32,
    pub timestamp: f64,
    pub payload: Vec<u8>,
    pub zeitgeist: Zeitgeist,
    pub parity: u8,
}

impl FluxPacket {
    /// Create a new FLUX packet with default magic
    pub fn new(source: u32, target: u32, payload: Vec<u8>, zeitgeist: Zeitgeist) -> Self {
        Self {
            magic: FLUX_MAGIC,
            version: 1,
            flags: 0,
            source,
            target,
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs_f64(),
            payload,
            zeitgeist,
            parity: 0, // computed during encode
        }
    }

    /// Compute parity: XOR of all bytes in the packet (excluding parity field itself)
    fn compute_parity(header: &[u8], payload: &[u8], zeitgeist_bytes: &[u8]) -> u8 {
        let mut p: u8 = 0;
        for &b in header { p ^= b; }
        for &b in payload { p ^= b; }
        for &b in zeitgeist_bytes { p ^= b; }
        p
    }

    /// Encode to binary wire format
    pub fn encode(&self) -> Vec<u8> {
        let zeitgeist_bytes = self.zeitgeist.encode();

        // Build header (25 bytes before lengths)
        let mut header = Vec::with_capacity(25);
        header.extend_from_slice(&self.magic);           // 4 bytes
        header.extend_from_slice(&self.version.to_be_bytes()); // 2 bytes
        header.push(self.flags);                          // 1 byte
        header.extend_from_slice(&self.source.to_be_bytes()); // 4 bytes
        header.extend_from_slice(&self.target.to_be_bytes()); // 4 bytes
        header.extend_from_slice(&self.timestamp.to_be_bytes()); // 8 bytes
        header.extend_from_slice(&(self.payload.len() as u32).to_be_bytes()); // 4 bytes
        header.extend_from_slice(&(zeitgeist_bytes.len() as u32).to_be_bytes()); // 4 bytes

        let parity = Self::compute_parity(&header, &self.payload, &zeitgeist_bytes);

        let mut buf = Vec::with_capacity(
            header.len() + self.payload.len() + zeitgeist_bytes.len() + 1
        );
        buf.extend_from_slice(&header);
        buf.extend_from_slice(&self.payload);
        buf.extend_from_slice(&zeitgeist_bytes);
        buf.push(parity);

        buf
    }

    /// Decode from binary wire format
    pub fn decode(data: &[u8]) -> Result<Self, String> {
        if data.len() < 26 {
            return Err("Packet too short".into());
        }

        // Parse header
        let magic = &data[0..4];
        if magic != FLUX_MAGIC {
            return Err(format!("Invalid magic: {:02X?}", magic));
        }

        let version = u16::from_be_bytes([data[4], data[5]]);
        let flags = data[6];
        let source = u32::from_be_bytes([data[7], data[8], data[9], data[10]]);
        let target = u32::from_be_bytes([data[11], data[12], data[13], data[14]]);
        let timestamp = f64::from_be_bytes([
            data[15], data[16], data[17], data[18],
            data[19], data[20], data[21], data[22],
        ]);
        let payload_len = u32::from_be_bytes([data[23], data[24], data[25], data[26]]) as usize;
        let zeitgeist_len = u32::from_be_bytes([data[27], data[28], data[29], data[30]]) as usize;

        let expected_len = 31 + payload_len + zeitgeist_len + 1; // +1 for parity
        if data.len() < expected_len {
            return Err(format!(
                "Packet truncated: expected {} bytes, got {}",
                expected_len,
                data.len()
            ));
        }

        let payload = data[31..31 + payload_len].to_vec();
        let zeitgeist_data = &data[31 + payload_len..31 + payload_len + zeitgeist_len];
        let zeitgeist = Zeitgeist::decode(zeitgeist_data)?;
        let parity = data[31 + payload_len + zeitgeist_len];

        // Verify parity
        let header = &data[0..31];
        let computed_parity = Self::compute_parity(header, &payload, zeitgeist_data);
        if computed_parity != parity {
            return Err(format!(
                "Parity mismatch: computed 0x{:02X}, got 0x{:02X}",
                computed_parity, parity
            ));
        }

        Ok(Self {
            magic: [magic[0], magic[1], magic[2], magic[3]],
            version,
            flags,
            source,
            target,
            timestamp,
            payload,
            zeitgeist,
            parity,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::precision::PrecisionState;
    use crate::confidence::ConfidenceState;
    use crate::trajectory::{TrajectoryState, Trend};
    use crate::consensus::ConsensusState;
    use crate::temporal::{TemporalState, Phase};
    use std::collections::BTreeMap;

    fn test_zeitgeist() -> Zeitgeist {
        Zeitgeist::new(
            PrecisionState::new(100.0, 0.5, false),
            ConfidenceState::new([1u8; 32], 0xFF, 0.8),
            TrajectoryState::new(0.7, Trend::Rising, 0.3),
            ConsensusState::new(0.1, 0.9, BTreeMap::from([(1u64, 5u64), (2u64, 3u64)])),
            TemporalState::new(0.5, Phase::Approaching, 0.95),
        )
    }

    #[test]
    fn test_packet_roundtrip() {
        let zg = test_zeitgeist();
        let packet = FluxPacket::new(42, 99, b"hello flux".to_vec(), zg);
        let encoded = packet.encode();
        let decoded = FluxPacket::decode(&encoded).unwrap();

        assert_eq!(decoded.magic, FLUX_MAGIC);
        assert_eq!(decoded.version, 1);
        assert_eq!(decoded.flags, 0);
        assert_eq!(decoded.source, 42);
        assert_eq!(decoded.target, 99);
        assert_eq!(decoded.payload, b"hello flux".to_vec());
        assert_eq!(decoded.zeitgeist, packet.zeitgeist);
    }

    #[test]
    fn test_invalid_magic() {
        let mut data = vec![0x00, 0x00, 0x00, 0x00];
        data.extend_from_slice(&[0; 22]);
        assert!(FluxPacket::decode(&data).is_err());
    }

    #[test]
    fn test_parity_check() {
        let zg = test_zeitgeist();
        let packet = FluxPacket::new(1, 2, vec![], zg);
        let mut encoded = packet.encode();
        // Corrupt a byte
        encoded[10] ^= 0xFF;
        assert!(FluxPacket::decode(&encoded).is_err());
    }
}
