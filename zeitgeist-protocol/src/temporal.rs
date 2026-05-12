//! Temporal tracking — beat grid and rhythm coherence

use serde::{Deserialize, Serialize};

/// Phase enum
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[repr(u8)]
pub enum Phase {
    Idle = 0,
    Approaching = 1,
    Snap = 2,
    Hold = 3,
}

impl From<u8> for Phase {
    fn from(v: u8) -> Self {
        match v {
            0 => Phase::Idle,
            1 => Phase::Approaching,
            2 => Phase::Snap,
            _ => Phase::Hold,
        }
    }
}

/// Temporal state captures rhythm alignment with a beat grid.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct TemporalState {
    /// Position in beat grid (0-1)
    pub beat_pos: f64,
    /// Current phase
    pub phase: Phase,
    /// How well rhythm matches grid (0-1)
    pub rhythm_coherence: f64,
}

impl TemporalState {
    pub fn new(beat_pos: f64, phase: Phase, rhythm_coherence: f64) -> Self {
        Self { beat_pos, phase, rhythm_coherence }
    }

    pub fn default() -> Self {
        Self {
            beat_pos: 0.0,
            phase: Phase::Idle,
            rhythm_coherence: 1.0,
        }
    }

    /// Check alignment: beat_pos must be 0-1
    pub fn check_alignment(&self) -> Vec<String> {
        let mut violations = Vec::new();
        if !(0.0..=1.0).contains(&self.beat_pos) {
            violations.push("temporal.beat_pos must be 0-1".into());
        }
        if !(0.0..=1.0).contains(&self.rhythm_coherence) {
            violations.push("temporal.rhythm_coherence must be 0-1".into());
        }
        violations
    }

    /// Merge: max beat position (latest in grid), take later phase, max coherence.
    /// All semilattice operations.
    pub fn merge(&self, other: &Self) -> Self {
        Self {
            beat_pos: self.beat_pos.max(other.beat_pos),
            phase: std::cmp::max(self.phase, other.phase),
            rhythm_coherence: self.rhythm_coherence.max(other.rhythm_coherence),
        }
    }
}
