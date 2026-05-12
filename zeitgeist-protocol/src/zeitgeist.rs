//! Zeitgeist — the composite CRDT semilattice

use serde::{Deserialize, Serialize};

use crate::precision::PrecisionState;
use crate::confidence::ConfidenceState;
use crate::trajectory::TrajectoryState;
use crate::consensus::ConsensusState;
use crate::temporal::TemporalState;

/// Alignment report returned by constraint checking
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct AlignmentReport {
    pub aligned: bool,
    pub violations: Vec<String>,
}

/// The Zeitgeist — composite CRDT capturing five dimensions of agent alignment.
///
/// Merge is a CRDT semilattice operation:
/// - Commutative: merge(a,b) == merge(b,a)
/// - Associative: merge(merge(a,b),c) == merge(a,merge(b,c))
/// - Idempotent: merge(a,a) == a
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Zeitgeist {
    pub precision: PrecisionState,
    pub confidence: ConfidenceState,
    pub trajectory: TrajectoryState,
    pub consensus: ConsensusState,
    pub temporal: TemporalState,
}

impl Zeitgeist {
    pub fn new(
        precision: PrecisionState,
        confidence: ConfidenceState,
        trajectory: TrajectoryState,
        consensus: ConsensusState,
        temporal: TemporalState,
    ) -> Self {
        Self { precision, confidence, trajectory, consensus, temporal }
    }

    pub fn default() -> Self {
        Self {
            precision: PrecisionState::default(),
            confidence: ConfidenceState::default(),
            trajectory: TrajectoryState::default(),
            consensus: ConsensusState::default(),
            temporal: TemporalState::default(),
        }
    }

    /// Merge two zeitgeists (CRDT semilattice).
    /// Each sub-field merges independently with its own semilattice rule.
    pub fn merge(&self, other: &Self) -> Self {
        Self {
            precision: self.precision.merge(&other.precision),
            confidence: self.confidence.merge(&other.confidence),
            trajectory: self.trajectory.merge(&other.trajectory),
            consensus: self.consensus.merge(&other.consensus),
            temporal: self.temporal.merge(&other.temporal),
        }
    }

    /// Encode to CBOR bytes
    pub fn encode(&self) -> Vec<u8> {
        let mut buf = Vec::new();
        ciborium::into_writer(self, &mut buf)
            .expect("CBOR encoding should not fail for Zeitgeist");
        buf
    }

    /// Decode from CBOR bytes
    pub fn decode(data: &[u8]) -> Result<Self, String> {
        ciborium::from_reader(data)
            .map_err(|e| format!("CBOR decode error: {}", e))
    }

    /// Check alignment constraints across all five dimensions
    pub fn check_alignment(&self) -> AlignmentReport {
        let mut violations = Vec::new();
        violations.extend(self.precision.check_alignment());
        violations.extend(self.confidence.check_alignment());
        violations.extend(self.trajectory.check_alignment());
        violations.extend(self.consensus.check_alignment());
        violations.extend(self.temporal.check_alignment());
        let aligned = violations.is_empty();
        AlignmentReport { aligned, violations }
    }
}
