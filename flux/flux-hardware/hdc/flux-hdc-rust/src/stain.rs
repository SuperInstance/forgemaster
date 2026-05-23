//! Bit-staining for hypervector provenance tracking.
//! Reserves low bits of the hypervector for metadata, with minimal impact on similarity.

use crate::{FoldedVector, Hypervector};
use thiserror::Error;

/// Error type for staining operations.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Error)]
#[non_exhaustive]
pub enum StainError {
    /// Stain value exceeds the maximum allowed for the vector type.
    #[error("stain value {0} exceeds maximum {1}")]
    InvalidStainValue(u32, u32),
}

/// Trait for hypervectors that support bit-staining for provenance tracking.
pub trait Stainable {
    /// Number of bits reserved for staining.
    const STAIN_BITS: usize;
    /// Maximum allowed stain value.
    const MAX_STAIN: u32;
    /// Bit mask for stain bits.
    const STAIN_MASK: u64;

    /// Set the stain value (provenance metadata) for the vector.
    /// Overwrites any existing stain.
    fn set_stain(&mut self, stain: u32) -> Result<(), StainError>;

    /// Get the current stain value from the vector.
    fn get_stain(&self) -> u32;

    /// Clear the stain value (set to 0).
    #[inline]
    fn clear_stain(&mut self) {
        let _ = self.set_stain(0);
    }
}

impl Stainable for Hypervector {
    /// 8 bits reserved for staining (0.78% of total bits, minimal similarity impact).
    const STAIN_BITS: usize = 8;
    const MAX_STAIN: u32 = (1 << Self::STAIN_BITS) - 1;
    const STAIN_MASK: u64 = Self::MAX_STAIN as u64;

    #[inline]
    fn set_stain(&mut self, stain: u32) -> Result<(), StainError> {
        if stain > Self::MAX_STAIN {
            return Err(StainError::InvalidStainValue(stain, Self::MAX_STAIN));
        }
        // Use first 8 bits of first u64 for stain
        self.0[0] = (self.0[0] & !Self::STAIN_MASK) | (stain as u64);
        Ok(())
    }

    #[inline]
    fn get_stain(&self) -> u32 {
        (self.0[0] & Self::STAIN_MASK) as u32
    }
}

impl Stainable for FoldedVector {
    /// 4 bits reserved for staining (3.125% of total bits, acceptable impact for folded vectors).
    const STAIN_BITS: usize = 4;
    const MAX_STAIN: u32 = (1 << Self::STAIN_BITS) - 1;
    const STAIN_MASK: u64 = Self::MAX_STAIN as u64;

    #[inline]
    fn set_stain(&mut self, stain: u32) -> Result<(), StainError> {
        if stain > Self::MAX_STAIN {
            return Err(StainError::InvalidStainValue(stain, Self::MAX_STAIN));
        }
        self.0[0] = (self.0[0] & !Self::STAIN_MASK) | (stain as u64);
        Ok(())
    }

    #[inline]
    fn get_stain(&self) -> u32 {
        (self.0[0] & Self::STAIN_MASK) as u32
    }
}