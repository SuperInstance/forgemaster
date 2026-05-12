//! Confidence tracking via bloom filter + parity

use serde::{Deserialize, Serialize};

/// Confidence state captures certainty about a proposition
/// using a bloom filter hash, XOR parity (Euler characteristic), and scalar certainty.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ConfidenceState {
    /// Bloom filter hash (32 bytes)
    pub bloom: [u8; 32],
    /// XOR parity (Euler χ)
    pub parity: u8,
    /// Certainty scalar 0.0-1.0
    pub certainty: f64,
}

impl ConfidenceState {
    pub fn new(bloom: [u8; 32], parity: u8, certainty: f64) -> Self {
        Self {
            bloom,
            parity,
            certainty,
        }
    }

    pub fn default() -> Self {
        Self {
            bloom: [0u8; 32],
            parity: 0,
            certainty: 0.0,
        }
    }

    /// Check alignment: certainty must be 0-1
    pub fn check_alignment(&self) -> Vec<String> {
        let mut violations = Vec::new();
        if !(0.0..=1.0).contains(&self.certainty) {
            violations.push("confidence.certainty must be 0-1".into());
        }
        violations
    }

    /// Merge: OR the bloom bits, OR the parities, take max certainty
    /// All semilattice operations (OR is idempotent, commutative, associative)
    pub fn merge(&self, other: &Self) -> Self {
        let mut bloom = [0u8; 32];
        for i in 0..32 {
            bloom[i] = self.bloom[i] | other.bloom[i];
        }
        Self {
            bloom,
            parity: self.parity | other.parity,
            certainty: self.certainty.max(other.certainty),
        }
    }
}
