//! Core HDC operations: bind, bundle, permute, Hamming metrics.

use crate::{FoldedVector, Hypervector};
use thiserror::Error;

/// Error type for HDC operations.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Error)]
#[non_exhaustive]
pub enum OperationError {
    /// Input slice is empty (for bundle operations).
    #[error("empty input slice provided")]
    EmptyInput,
    /// Shift value is invalid (exceeds vector bit length).
    #[error("shift value {0} exceeds vector length {1}")]
    InvalidShift(usize, usize),
}

/// Bind two hypervectors using XOR (associative, commutative, invertible).
#[inline]
pub fn bind(a: Hypervector, b: Hypervector) -> Hypervector {
    Hypervector(a.0.zip(b.0).map(|(x, y)| x ^ y))
}

/// Bind multiple hypervectors (left-associative XOR).
#[inline]
pub fn bind_many(hvs: &[Hypervector]) -> Result<Hypervector, OperationError> {
    if hvs.is_empty() {
        return Err(OperationError::EmptyInput);
    }
    Ok(hvs.iter().copied().fold(Hypervector::default(), |acc, hv| bind(acc, hv)))
}

/// Majority bundle of hypervectors (bit-wise majority vote).
/// Ties (even count) resolve to 0.
pub fn majority_bundle(hvs: &[Hypervector]) -> Result<Hypervector, OperationError> {
    let n = hvs.len();
    if n == 0 {
        return Err(OperationError::EmptyInput);
    }
    let threshold = (n / 2) as u16;
    let mut counts = [[0u16; 64]; 16]; // [u64_idx][bit_idx]

    for hv in hvs {
        for (i, &word) in hv.as_u64_array().iter().enumerate() {
            for bit in 0..64 {
                if (word >> bit) & 1 != 0 {
                    counts[i][bit] += 1;
                }
            }
        }
    }

    let mut result = [0u64; 16];
    for (i, word_counts) in counts.iter().enumerate() {
        for (bit, &count) in word_counts.iter().enumerate() {
            if count > threshold {
                result[i] |= 1 << bit;
            }
        }
    }

    Ok(Hypervector(result))
}

/// Cyclically permute a hypervector left by `k` bits.
#[inline]
pub fn permute_left(hv: Hypervector, k: usize) -> Result<Hypervector, OperationError> {
    let k = k % Hypervector::BITS;
    if k == 0 {
        return Ok(hv);
    }
    let word_shift = k / 64;
    let bit_shift = k % 64;
    let bit_shift_inv = 64 - bit_shift;

    let mut result = [0u64; 16];
    for i in 0..16 {
        let prev_word_idx = (i + 16 - word_shift - 1) % 16;
        let curr_word_idx = (i + 16 - word_shift) % 16;
        result[i] = (hv.0[prev_word_idx] << bit_shift) | (hv.0[curr_word_idx] >> bit_shift_inv);
    }

    Ok(Hypervector(result))
}

/// Cyclically permute a hypervector right by `k` bits.
#[inline]
pub fn permute_right(hv: Hypervector, k: usize) -> Result<Hypervector, OperationError> {
    permute_left(hv, Hypervector::BITS - (k % Hypervector::BITS))
}

/// Hamming distance between two hypervectors (number of differing bits).
#[inline]
pub fn hamming_distance(a: &Hypervector, b: &Hypervector) -> u32 {
    a.0.iter()
        .zip(b.0.iter())
        .map(|(&x, &y)| (x ^ y).count_ones())
        .sum()
}

/// Hamming similarity between two hypervectors (1 - distance/1024).
#[inline]
pub fn hamming_similarity(a: &Hypervector, b: &Hypervector) -> f64 {
    1.0 - (hamming_distance(a, b) as f64 / Hypervector::BITS as f64)
}

/// Hamming distance between two folded vectors.
#[inline]
pub fn folded_hamming_distance(a: &FoldedVector, b: &FoldedVector) -> u32 {
    a.0.iter()
        .zip(b.0.iter())
        .map(|(&x, &y)| (x ^ y).count_ones())
        .sum()
}

/// Hamming similarity between two folded vectors (1 - distance/128).
#[inline]
pub fn folded_hamming_similarity(a: &FoldedVector, b: &FoldedVector) -> f64 {
    1.0 - (folded_hamming_distance(a, b) as f64 / FoldedVector::BITS as f64)
}