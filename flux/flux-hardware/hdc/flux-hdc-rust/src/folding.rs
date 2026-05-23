//! Bit-folding from 1024-bit Hypervector to 128-bit FoldedVector.
//! Preserves Hamming similarity ratios.

use crate::{FoldedVector, Hypervector};
use thiserror::Error;

/// Error type for folding operations.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Error)]
#[non_exhaustive]
pub enum FoldError {
    /// Hypervector is invalid for folding.
    #[error("invalid hypervector for folding")]
    InvalidInput,
}

/// Fold a 1024-bit hypervector into a 128-bit folded vector.
/// Splits the hypervector into 8 x 128-bit chunks and XORs all chunks.
/// Preserves Hamming similarity ratios for practical HDC use cases.
#[inline]
pub fn fold(hv: &Hypervector) -> FoldedVector {
    let words = hv.as_u64_array();
    // Chunk structure: [0,1], [2,3], [4,5], [6,7], [8,9], [10,11], [12,13], [14,15]
    FoldedVector([
        words[0] ^ words[2] ^ words[4] ^ words[6] ^ words[8] ^ words[10] ^ words[12] ^ words[14],
        words[1] ^ words[3] ^ words[5] ^ words[7] ^ words[9] ^ words[11] ^ words[13] ^ words[15],
    ])
}