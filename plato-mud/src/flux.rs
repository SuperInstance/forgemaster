//! PLATO MUD Engine — FLUX Transference
//!
//! Zeitgeist encoding/decoding, room-to-room transference, merge, deadband,
//! parity monitoring.

extern crate alloc;

use alloc::string::String;
use alloc::vec::Vec;

use crate::types::*;

/// FLUX transference manager
pub struct FluxManager {
    pending: Vec<FluxTransference>,
    parity_state: alloc::collections::BTreeMap<RoomId, ParityState>,
}

/// Parity state for a room (CONSTRAINT 7)
#[derive(Debug, Clone)]
pub struct ParityState {
    pub even_count: u64,
    pub odd_count: u64,
    pub last_check: f64,
    pub parity_ok: bool,
}

impl FluxManager {
    pub fn new() -> Self {
        Self {
            pending: Vec::new(),
            parity_state: alloc::collections::BTreeMap::new(),
        }
    }

    /// Create a FLUX transference from source to target
    pub fn create_flux(
        &mut self,
        source: RoomId,
        target: RoomId,
        timestamp: f64,
        payload: TransferencePayload,
        zeitgeist: Zeitgeist,
    ) -> FluxTransference {
        FluxTransference {
            source,
            target,
            timestamp,
            payload,
            zeitgeist,
        }
    }

    /// Send a FLUX transference (queue it)
    pub fn send_flux(&mut self, flux: FluxTransference) {
        // CONSTRAINT 8: FLUX must carry full zeitgeist
        self.pending.push(flux);
    }

    /// Receive pending FLUX transferences for a target room
    pub fn recv_flux_for(&mut self, target: &RoomId) -> Vec<FluxTransference> {
        let (for_target, remaining): (Vec<_>, Vec<_>) =
            self.pending.drain(..).partition(|f| &f.target == target);
        self.pending = remaining;
        for_target
    }

    /// Receive any pending FLUX transference
    pub fn recv_flux(&mut self) -> Option<FluxTransference> {
        if self.pending.is_empty() {
            None
        } else {
            Some(self.pending.remove(0))
        }
    }

    /// Update parity state for a room (CONSTRAINT 7)
    pub fn update_parity(&mut self, room: &RoomId, zeitgeist: &Zeitgeist, timestamp: f64) {
        let parity = zeitgeist.temporal.beat % 2;
        let state = self.parity_state.entry(room.clone()).or_insert(ParityState {
            even_count: 0,
            odd_count: 0,
            last_check: 0.0,
            parity_ok: true,
        });

        if parity == 0 {
            state.even_count += 1;
        } else {
            state.odd_count += 1;
        }
        state.last_check = timestamp;

        // Parity is OK if both even and odd counts are present
        state.parity_ok = state.even_count > 0 && state.odd_count > 0;
    }

    /// Check if a room has valid parity (CONSTRAINT 7)
    pub fn check_parity(&self, room: &RoomId) -> bool {
        self.parity_state.get(room)
            .map(|s| s.parity_ok)
            .unwrap_or(false)
    }

    /// Encode zeitgeist to bytes (simplified CBOR-like format)
    pub fn encode_zeitgeist(zeitgeist: &Zeitgeist) -> Vec<u8> {
        // Simple encoding: we'll use a compact binary format
        // In production, use serde_cbor or postcard
        let mut bytes = Vec::new();

        // Precision funnel
        bytes.extend_from_slice(&zeitgeist.precision.center.to_le_bytes());
        bytes.extend_from_slice(&zeitgeist.precision.width.to_le_bytes());
        bytes.extend_from_slice(&zeitgeist.precision.samples.to_le_bytes());
        bytes.push(zeitgeist.precision.converged as u8);

        // Bloom filter
        bytes.push(zeitgeist.confidence.num_hashes as u8);
        for word in &zeitgeist.confidence.bits {
            bytes.extend_from_slice(&word.to_le_bytes());
        }

        // Trajectory
        bytes.extend_from_slice(&zeitgeist.trajectory.value.to_le_bytes());
        bytes.extend_from_slice(&zeitgeist.trajectory.confidence.to_le_bytes());

        // Consensus
        bytes.extend_from_slice(&zeitgeist.consensus.coherence.to_le_bytes());

        // Temporal
        bytes.extend_from_slice(&zeitgeist.temporal.beat.to_le_bytes());
        bytes.extend_from_slice(&zeitgeist.temporal.tempo.to_le_bytes());

        bytes
    }

    /// Decode zeitgeist from bytes
    pub fn decode_zeitgeist(bytes: &[u8]) -> Result<Zeitgeist, String> {
        if bytes.len() < 8 + 8 + 8 + 1 {
            return Err("Insufficient bytes for zeitgeist".into());
        }

        let mut offset = 0;

        let center = f64::from_le_bytes(bytes[offset..offset+8].try_into().map_err(|_| "parse error")?);
        offset += 8;
        let width = f64::from_le_bytes(bytes[offset..offset+8].try_into().map_err(|_| "parse error")?);
        offset += 8;
        let samples = u64::from_le_bytes(bytes[offset..offset+8].try_into().map_err(|_| "parse error")?);
        offset += 8;
        let converged = bytes[offset] != 0;
        offset += 1;

        let num_hashes = bytes[offset] as u32;
        offset += 1;

        let remaining_words = (bytes.len() - offset - 8 - 8 - 8 - 8 - 8) / 8;
        let mut bits = Vec::new();
        for i in 0..remaining_words {
            if offset + 8 <= bytes.len() {
                bits.push(u64::from_le_bytes(bytes[offset..offset+8].try_into().map_err(|_| "parse error")?));
                offset += 8;
            }
        }

        let trajectory_value = f64::from_le_bytes(bytes[offset..offset+8].try_into().map_err(|_| "parse error")?);
        offset += 8;
        let trajectory_confidence = f64::from_le_bytes(bytes[offset..offset+8].try_into().map_err(|_| "parse error")?);
        offset += 8;

        let coherence = f64::from_le_bytes(bytes[offset..offset+8].try_into().map_err(|_| "parse error")?);
        offset += 8;

        let beat = u64::from_le_bytes(bytes[offset..offset+8].try_into().map_err(|_| "parse error")?);
        offset += 8;
        let tempo = f64::from_le_bytes(bytes[offset..offset+8].try_into().map_err(|_| "parse error")?);

        Ok(Zeitgeist {
            precision: FunnelState { center, width, samples, converged },
            confidence: BloomFilter { bits, num_hashes, estimated_count: 0 },
            trajectory: HurstEstimate { value: trajectory_value, confidence: trajectory_confidence, sample_count: 0 },
            consensus: HolonomyState { cycle_count: 0, coherence, last_check: 0.0 },
            temporal: BeatPosition { beat, tempo, phase: 0.0 },
        })
    }

    /// Track deadband funnel for precision convergence
    pub fn track_funnel(&self, zeitgeist: &Zeitgeist, observations: &[f64]) -> FunnelState {
        if observations.is_empty() {
            return zeitgeist.precision.clone();
        }

        let n = observations.len() as f64;
        let mean = observations.iter().sum::<f64>() / n;
        let variance = observations.iter()
            .map(|x| (x - mean).powi(2))
            .sum::<f64>() / n;
        let std_dev = variance.sqrt();
        let width = 2.0 * std_dev; // 1-sigma deadband

        FunnelState {
            center: mean,
            width,
            samples: observations.len() as u64,
            converged: width < 0.01, // converged when deadband < 1%
        }
    }

    /// Pending count
    pub fn pending_count(&self) -> usize {
        self.pending.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_flux_create_and_send() {
        let mut mgr = FluxManager::new();
        let flux = mgr.create_flux(
            RoomId("r1".to_string()),
            RoomId("r2".to_string()),
            100.0,
            TransferencePayload::Heartbeat,
            Zeitgeist::new(),
        );
        mgr.send_flux(flux);
        assert_eq!(mgr.pending_count(), 1);
    }

    #[test]
    fn test_flux_recv_for_target() {
        let mut mgr = FluxManager::new();

        let flux1 = mgr.create_flux(
            RoomId("r1".to_string()), RoomId("r2".to_string()),
            100.0, TransferencePayload::Heartbeat, Zeitgeist::new(),
        );
        let flux2 = mgr.create_flux(
            RoomId("r1".to_string()), RoomId("r3".to_string()),
            101.0, TransferencePayload::Heartbeat, Zeitgeist::new(),
        );
        mgr.send_flux(flux1);
        mgr.send_flux(flux2);

        let for_r2 = mgr.recv_flux_for(&RoomId("r2".to_string()));
        assert_eq!(for_r2.len(), 1);
        assert_eq!(mgr.pending_count(), 1);
    }

    #[test]
    fn test_zeitgeist_encode_decode() {
        let zeitgeist = Zeitgeist::new();
        let encoded = FluxManager::encode_zeitgeist(&zeitgeist);
        let decoded = FluxManager::decode_zeitgeist(&encoded);
        assert!(decoded.is_ok());
    }

    #[test]
    fn test_parity_monitoring() {
        let mut mgr = FluxManager::new();
        let room = RoomId("r1".to_string());

        // Initially no parity
        assert!(!mgr.check_parity(&room));

        // Update with even beat
        let mut z1 = Zeitgeist::new();
        z1.temporal.beat = 0; // even
        mgr.update_parity(&room, &z1, 100.0);
        assert!(!mgr.check_parity(&room)); // Only even, no odd yet

        // Update with odd beat
        let mut z2 = Zeitgeist::new();
        z2.temporal.beat = 1; // odd
        mgr.update_parity(&room, &z2, 200.0);
        assert!(mgr.check_parity(&room)); // Both even and odd present
    }

    #[test]
    fn test_funnel_tracking() {
        let mgr = FluxManager::new();
        let zeitgeist = Zeitgeist::new();

        // Tight observations → narrow funnel → converged
        let obs: Vec<f64> = vec![1.001, 1.002, 0.999, 1.000, 1.001];
        let funnel = mgr.track_funnel(&zeitgeist, &obs);
        assert!(funnel.converged);
        assert!(funnel.width < 0.01);

        // Wide observations → wide funnel → not converged
        let wide: Vec<f64> = vec![0.0, 1.0, 2.0, 3.0, 4.0];
        let funnel2 = mgr.track_funnel(&zeitgeist, &wide);
        assert!(!funnel2.converged);
    }

    #[test]
    fn test_bloom_filter() {
        let mut bf = BloomFilter::new(3, 256);
        bf.insert(b"hello");
        bf.insert(b"world");

        assert!(bf.contains(b"hello"));
        assert!(bf.contains(b"world"));
        assert!(!bf.contains(b"missing"));
    }

    #[test]
    fn test_bloom_filter_merge() {
        let mut bf1 = BloomFilter::new(3, 256);
        bf1.insert(b"hello");

        let mut bf2 = BloomFilter::new(3, 256);
        bf2.insert(b"world");

        bf1.merge(&bf2);
        assert!(bf1.contains(b"hello"));
        assert!(bf1.contains(b"world"));
    }
}
