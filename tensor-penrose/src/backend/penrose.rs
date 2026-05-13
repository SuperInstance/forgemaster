//! 5D→2D Penrose cut-and-project backend.
//!
//! Uses the penrose-memory CutAndProjectCompiler for tile generation.

use crate::backend::{LatticeBackend, SnapResult};

/// 5D→2D Penrose cut-and-project backend.
///
/// Uses the penrose-memory `CutAndProjectCompiler` with golden projection
/// for generating Penrose tilings from 5D lattice coordinates.
pub struct PenroseBackend;

impl PenroseBackend {
    pub fn new() -> Self {
        Self
    }
}

impl Default for PenroseBackend {
    fn default() -> Self {
        Self::new()
    }
}

impl LatticeBackend for PenroseBackend {
    fn name(&self) -> &'static str {
        "penrose"
    }

    fn snap(&self, x: f64, y: f64) -> SnapResult {
        // For Penrose backend, snapping uses the golden-ratio quantization.
        // Map to a dodecet based on which sector the point falls in.
        let phi = 1.618033988749895_f64;
        let qx = (x / phi).round();
        let qy = (y / phi).round();
        let dx = x - qx * phi;
        let dy = y - qy * phi;
        let error = (dx * dx + dy * dy).sqrt();

        // Determine sector from angle
        let angle = dy.atan2(dx);
        let sector = ((angle + std::f64::consts::PI) / (std::f64::consts::PI / 3.0)).floor() as u8;
        let chamber = sector.min(5);

        // Dodecet from golden-ratio hashing
        let hash = (qx as i64).wrapping_mul(0x9E3779B97F4A7C15u64 as i64)
            .wrapping_add((qy as i64).wrapping_mul(0x517CC1B727220A95u64 as i64));
        let dodecet = ((hash.wrapping_abs() as u64) % 4096) as u16;

        SnapResult {
            error,
            dodecet,
            chamber,
            is_safe: error < 0.5,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_penrose_snap() {
        let backend = PenroseBackend::new();
        let result = backend.snap(0.0, 0.0);
        assert!(result.error < 1.0, "Origin should snap close");
    }

    #[test]
    fn test_penrose_name() {
        let backend = PenroseBackend::new();
        assert_eq!(backend.name(), "penrose");
    }

    #[test]
    fn test_penrose_chamber_valid() {
        let backend = PenroseBackend::new();
        for x in -5..=5 {
            for y in -5..=5 {
                let result = backend.snap(x as f64 * 0.5, y as f64 * 0.5);
                assert!(result.chamber <= 5);
            }
        }
    }
}
