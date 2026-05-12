//! Consensus tracking — holonomy state + CRDT version vector

use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

/// Consensus state captures cycle coherence via holonomy integral
/// and peer agreement with a CRDT version vector.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ConsensusState {
    /// Cycle integral (0 = coherent)
    pub holonomy: f64,
    /// Fraction of agreeing peers (0-1)
    pub peer_agreement: f64,
    /// State vector clock (agent_id -> version)
    pub crdt_version: BTreeMap<u64, u64>,
}

impl ConsensusState {
    pub fn new(holonomy: f64, peer_agreement: f64, crdt_version: BTreeMap<u64, u64>) -> Self {
        Self { holonomy, peer_agreement, crdt_version }
    }

    pub fn default() -> Self {
        Self {
            holonomy: 0.0,
            peer_agreement: 1.0,
            crdt_version: BTreeMap::new(),
        }
    }

    /// Check alignment: holonomy should approach 0
    pub fn check_alignment(&self) -> Vec<String> {
        let mut violations = Vec::new();
        if !(0.0..=1.0).contains(&self.peer_agreement) {
            violations.push("consensus.peer_agreement must be 0-1".into());
        }
        violations
    }

    /// Merge: min holonomy (most coherent), max peer agreement,
    /// supmerge version vectors (pointwise max). All semilattice operations.
    pub fn merge(&self, other: &Self) -> Self {
        let holonomy = self.holonomy.min(other.holonomy);
        let peer_agreement = self.peer_agreement.max(other.peer_agreement);

        // CRDT merge: pointwise max (PVV semilattice)
        let mut crdt_version = self.crdt_version.clone();
        for (k, v) in &other.crdt_version {
            crdt_version
                .entry(*k)
                .and_modify(|existing| *existing = (*existing).max(*v))
                .or_insert(*v);
        }

        Self { holonomy, peer_agreement, crdt_version }
    }
}
