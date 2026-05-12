//! Trajectory tracking via Hurst exponent estimation

use serde::{Deserialize, Serialize};

/// Trend enum
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[repr(u8)]
pub enum Trend {
    Stable = 0,
    Rising = 1,
    Falling = 2,
    Chaotic = 3,
}

impl From<u8> for Trend {
    fn from(v: u8) -> Self {
        match v {
            0 => Trend::Stable,
            1 => Trend::Rising,
            2 => Trend::Falling,
            _ => Trend::Chaotic,
        }
    }
}

/// Trajectory state captures trend direction and momentum
/// via Hurst exponent estimation.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct TrajectoryState {
    /// Hurst exponent estimate (0-1)
    pub hurst: f64,
    /// Current trend
    pub trend: Trend,
    /// Rate of change (velocity)
    pub velocity: f64,
}

impl TrajectoryState {
    pub fn new(hurst: f64, trend: Trend, velocity: f64) -> Self {
        Self { hurst, trend, velocity }
    }

    pub fn default() -> Self {
        Self {
            hurst: 0.5,
            trend: Trend::Stable,
            velocity: 0.0,
        }
    }

    /// Check alignment: Hurst must be 0-1
    pub fn check_alignment(&self) -> Vec<String> {
        let mut violations = Vec::new();
        if !(0.0..=1.0).contains(&self.hurst) {
            violations.push("trajectory.hurst must be 0-1".into());
        }
        violations
    }

    /// Merge: min hurst (conservative), pick dominant trend (Chaotic on disagreement),
    /// max velocity (most urgent signal). All semilattice operations.
    pub fn merge(&self, other: &Self) -> Self {
        Self {
            hurst: self.hurst.min(other.hurst),
            trend: if self.trend == other.trend { self.trend } else { Trend::Chaotic },
            velocity: self.velocity.max(other.velocity),
        }
    }
}
