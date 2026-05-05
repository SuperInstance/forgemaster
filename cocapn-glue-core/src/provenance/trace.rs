//! Verification trace — a record of constraint verification.

use serde::{Serialize, Deserialize};
use sha2::{Sha256, Digest};
use alloc::vec::Vec;
use crate::wire::TierId;
use crate::provenance::merkle::Hash;

/// A verification trace recording the result of a constraint check.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct VerificationTrace {
    /// Which tier performed the verification.
    pub verifier: TierId,
    /// Monotonic verification ID.
    pub trace_id: u64,
    /// The constraint being verified (opaque bytes).
    pub constraint_hash: Vec<u8>,
    /// Result: 0 = pass, non-zero = failure code.
    pub result: u32,
    /// Timestamp (epoch millis or similar).
    pub timestamp: u64,
}

impl VerificationTrace {
    pub fn new(verifier: TierId, trace_id: u64, constraint_hash: Vec<u8>, result: u32, ts: u64) -> Self {
        VerificationTrace {
            verifier, trace_id, constraint_hash, result, timestamp: ts,
        }
    }

    /// SHA-256 hash of this trace for Merkle tree inclusion.
    pub fn hash(&self) -> Hash {
        let mut hasher = Sha256::new();
        hasher.update(self.verifier.as_bytes());
        hasher.update(self.trace_id.to_le_bytes());
        hasher.update(&self.constraint_hash);
        hasher.update(self.result.to_le_bytes());
        hasher.update(self.timestamp.to_le_bytes());
        hasher.finalize().into()
    }

    pub fn is_pass(&self) -> bool {
        self.result == 0
    }
}
