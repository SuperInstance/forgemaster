//! Deadband funnel precision tracking

use serde::{Deserialize, Serialize};

/// Precision state tracks the deadband funnel — how tightly
/// a value is converging toward its target.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct PrecisionState {
    /// Current deadband width (must be > 0 and < covering_radius)
    pub deadband: f64,
    /// Position in funnel: 0 = wide open, 1 = snap
    pub funnel_pos: f64,
    /// Whether we're within the closing threshold
    pub snap_imminent: bool,
}

impl PrecisionState {
    pub const COVERING_RADIUS: f64 = 1e6;

    pub fn new(deadband: f64, funnel_pos: f64, snap_imminent: bool) -> Self {
        Self {
            deadband,
            funnel_pos,
            snap_imminent,
        }
    }

    pub fn default() -> Self {
        Self {
            deadband: Self::COVERING_RADIUS / 2.0,
            funnel_pos: 0.0,
            snap_imminent: false,
        }
    }

    /// Check alignment: deadband must be > 0 and < covering_radius
    pub fn check_alignment(&self) -> Vec<String> {
        let mut violations = Vec::new();
        if self.deadband <= 0.0 {
            violations.push("precision.deadband must be > 0".into());
        }
        if self.deadband >= Self::COVERING_RADIUS {
            violations.push("precision.deadband must be < covering_radius".into());
        }
        if !(0.0..=1.0).contains(&self.funnel_pos) {
            violations.push("precision.funnel_pos must be 0-1".into());
        }
        violations
    }

    /// Merge: take the tighter deadband, higher funnel position, snap if either snaps
    pub fn merge(&self, other: &Self) -> Self {
        Self {
            deadband: self.deadband.min(other.deadband),
            funnel_pos: self.funnel_pos.max(other.funnel_pos),
            snap_imminent: self.snap_imminent || other.snap_imminent,
        }
    }
}
