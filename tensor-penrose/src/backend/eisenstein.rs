//! Eisenstein A₂ lattice backend.
//!
//! Wraps `fleet-math-c` C bridge for 26M snap/s performance.

use crate::backend::{LatticeBackend, SnapResult};

/// A₂ Eisenstein lattice backend using the fleet-math-c C bridge.
pub struct EisensteinBackend {
    // Stateless — all state is in the C library
}

impl EisensteinBackend {
    pub fn new() -> Self {
        Self
    }
}

impl Default for EisensteinBackend {
    fn default() -> Self {
        Self::new()
    }
}

impl LatticeBackend for EisensteinBackend {
    fn name(&self) -> &'static str {
        "eisenstein"
    }

    fn snap(&self, x: f64, y: f64) -> SnapResult {
        let result = fleet_math_c::snap(x as f32, y as f32);
        SnapResult {
            error: result.error as f64,
            dodecet: result.dodecet,
            chamber: result.chamber,
            is_safe: result.is_safe,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_eisenstein_snap() {
        let backend = EisensteinBackend::new();
        let result = backend.snap(0.0, 0.0);
        assert!(result.error < 0.001, "Origin should snap to itself");
    }

    #[test]
    fn test_eisenstein_name() {
        let backend = EisensteinBackend::new();
        assert_eq!(backend.name(), "eisenstein");
    }

    #[test]
    fn test_eisenstein_chamber_valid() {
        let backend = EisensteinBackend::new();
        for x in -5..=5 {
            for y in -5..=5 {
                let result = backend.snap(x as f64, y as f64);
                assert!(result.chamber <= 5, "Chamber must be 0-5, got {}", result.chamber);
            }
        }
    }
}
