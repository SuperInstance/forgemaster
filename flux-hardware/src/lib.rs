//! # flux-hardware
//!
//! FLUX production GPU kernel for constraint checking on CUDA.
//!
//! ## Design (from 30 experiments)
//! - INT8 flat bounds array — coalesced memory reads
//! - Masked output — which constraints failed per sensor (1.27x faster than pass/fail)
//! - Block-reduce atomic for violation counting — minimal global atomics
//! - Incremental bounds update — scatter kernel for changed constraints only
//!
//! ## Compile Targets
//! - `sm_86` — RTX 4050
//! - `sm_80` — A100
//! - `sm_70` — V100

#[cfg(feature = "cuda")]
pub mod cuda;

pub const CONSTRAINTS_PER_SET: usize = 8;

/// Violation mask helpers — interpret the per-sensor output byte.
pub mod mask {
    use super::CONSTRAINTS_PER_SET;

    /// Check if a specific constraint (0-7) was violated.
    #[inline]
    pub fn is_violated(mask: u8, constraint: usize) -> bool {
        debug_assert!(constraint < CONSTRAINTS_PER_SET);
        (mask & (1 << constraint)) != 0
    }

    /// Count total violated constraints in a mask.
    #[inline]
    pub fn count_violations(mask: u8) -> u32 {
        mask.count_ones()
    }

    /// Check if any constraint was violated.
    #[inline]
    pub fn any_violated(mask: u8) -> bool {
        mask != 0
    }

    /// Get the indices of all violated constraints.
    pub fn violated_indices(mask: u8) -> Vec<usize> {
        let mut result = Vec::new();
        for i in 0..CONSTRAINTS_PER_SET {
            if is_violated(mask, i) {
                result.push(i);
            }
        }
        result
    }
}

/// Build a flat bounds array from per-set bounds.
///
/// Each constraint set is 8 INT8 values. Pass a slice of `[u8; 8]` arrays.
pub fn build_flat_bounds(sets: &[[u8; CONSTRAINTS_PER_SET]]) -> Vec<u8> {
    let mut flat = Vec::with_capacity(sets.len() * CONSTRAINTS_PER_SET);
    for set in sets {
        flat.extend_from_slice(set);
    }
    flat
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_mask_helpers() {
        assert!(mask::is_violated(0x01, 0));
        assert!(!mask::is_violated(0x01, 1));
        assert!(mask::any_violated(0x03));
        assert!(!mask::any_violated(0x00));
        assert_eq!(mask::count_violations(0b10101010), 4);
        assert_eq!(mask::violated_indices(0b01010101), vec![0, 2, 4, 6]);
    }

    #[test]
    fn test_build_flat_bounds() {
        let sets = [
            [10u8, 20, 30, 40, 50, 60, 70, 80],
            [15u8, 25, 35, 45, 55, 65, 75, 85],
        ];
        let flat = build_flat_bounds(&sets);
        assert_eq!(flat.len(), 16);
        assert_eq!(flat[0], 10);
        assert_eq!(flat[8], 15); // second set starts at index 8
    }
}
