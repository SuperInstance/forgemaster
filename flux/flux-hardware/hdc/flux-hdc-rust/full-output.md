```toml
# Cargo.toml
[package]
name = "flux-hdc"
version = "0.1.0"
edition = "2021"
rust-version = "1.75"
description = "Hyperdimensional Constraint Matching Library for no_std and std environments"
license = "MIT OR Apache-2.0"
keywords = ["hdc", "hyperdimensional", "constraint-matching", "no_std"]
categories = ["algorithms", "embedded", "no-std"]

[features]
default = ["std"]
std = [
    "rand/std",
    "thiserror/std",
]

[dependencies]
thiserror = { version = "1.0.48", default-features = false }
rand = { version = "0.8.5", default-features = false, features = ["small_rng"] }
rand_xoshiro = { version = "0.6.0", default-features = false }

[dev-dependencies]
rand = { version = "0.8.5", default-features = true }
```

```rust
// src/lib.rs
#![cfg_attr(not(feature = "std"), no_std)]
#![deny(unsafe_code)]
#![deny(missing_docs)]

//! Hyperdimensional Constraint Matching (HDC) library for no_std and std environments.
//!
//! Provides 1024-bit hypervectors, semantic encoding, matching, folding, and provenance tracking.

// Core modules
pub mod hypervector;
pub mod operations;
pub mod folding;
pub mod encoding;
pub mod matcher;
pub mod sram;
pub mod stain;

// Public API re-exports
pub use hypervector::{FoldedVector, Hypervector};
pub use operations::{
    bind, hamming_distance, hamming_similarity, majority_bundle, permute_left, permute_right,
    OperationError,
};
pub use folding::{fold, FoldError};
pub use encoding::{Encoder, EncodingError};
pub use matcher::{TUTORConstraintMatcher, MatcherError};
pub use sram::{SramRecord, SramError};
pub use stain::{Stainable, StainError};
```

```rust
// src/hypervector.rs
//! 1024-bit Hypervector and 128-bit FoldedVector core types.

use core::hash::{Hash, Hasher};
use rand::Rng;

/// 1024-bit hypervector, the core unit of HDC computation.
/// Wrapper around `[u64; 16]` for type safety and efficient operations.
#[repr(transparent)]
#[derive(Clone, Copy, PartialEq, Eq, Default)]
pub struct Hypervector(pub [u64; 16]);

/// 128-bit folded hypervector for compact storage and matching.
/// Wrapper around `[u64; 2]` for type safety.
#[repr(transparent)]
#[derive(Clone, Copy, PartialEq, Eq, Default)]
pub struct FoldedVector(pub [u64; 2]);

impl Hypervector {
    /// Number of bits in a hypervector (1024).
    pub const BITS: usize = 1024;
    /// Number of u64 elements in a hypervector (16).
    pub const LEN: usize = 16;

    /// Create a new hypervector from a raw array.
    #[inline]
    pub const fn new(raw: [u64; 16]) -> Self {
        Self(raw)
    }

    /// Generate a random hypervector using the provided RNG.
    #[inline]
    pub fn random<R: Rng>(rng: &mut R) -> Self {
        Self([(); 16].map(|_| rng.next_u64()))
    }

    /// Get a reference to the inner u64 array.
    #[inline]
    pub const fn as_u64_array(&self) -> &[u64; 16] {
        &self.0
    }

    /// Get a mutable reference to the inner u64 array.
    #[inline]
    pub fn as_u64_array_mut(&mut self) -> &mut [u64; 16] {
        &mut self.0
    }

    /// View the hypervector as a byte slice.
    #[inline]
    pub const fn as_bytes(&self) -> &[u8] {
        // SAFETY: Hypervector is a transparent wrapper around [u64;16], which is valid for byte reads
        unsafe {
            core::slice::from_raw_parts(
                self.0.as_ptr() as *const u8,
                core::mem::size_of::<Self>(),
            )
        }
    }
}

impl FoldedVector {
    /// Number of bits in a folded vector (128).
    pub const BITS: usize = 128;
    /// Number of u64 elements in a folded vector (2).
    pub const LEN: usize = 2;

    /// Create a new folded vector from a raw array.
    #[inline]
    pub const fn new(raw: [u64; 2]) -> Self {
        Self(raw)
    }

    /// Generate a random folded vector using the provided RNG.
    #[inline]
    pub fn random<R: Rng>(rng: &mut R) -> Self {
        Self([(); 2].map(|_| rng.next_u64()))
    }

    /// Get a reference to the inner u64 array.
    #[inline]
    pub const fn as_u64_array(&self) -> &[u64; 2] {
        &self.0
    }
}

// Trait implementations for debugging and hashing
impl core::fmt::Debug for Hypervector {
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        write!(f, "Hypervector({:x?})", self.0)
    }
}

impl core::fmt::Debug for FoldedVector {
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        write!(f, "FoldedVector({:x?})", self.0)
    }
}

impl Hash for Hypervector {
    #[inline]
    fn hash<H: Hasher>(&self, state: &mut H) {
        self.0.hash(state)
    }
}

impl Hash for FoldedVector {
    #[inline]
    fn hash<H: Hasher>(&self, state: &mut H) {
        self.0.hash(state)
    }
}
```

```rust
// src/operations.rs
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
```

```rust
// src/folding.rs
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
```

```rust
// src/encoding.rs
//! 3-layer multi-scale semantic encoding for range constraints.
//! Uses log-uniform thresholds for high similarity between nearly-identical ranges.

use crate::{Hypervector, bind, majority_bundle};
use rand::{Rng, SeedableRng};
use rand_xoshiro::XorShift64Star;
use thiserror::Error;

/// Error type for encoding operations.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Error)]
#[non_exhaustive]
pub enum EncodingError {
    /// Range bounds are invalid (a >= b).
    #[error("invalid range bounds: a={0} >= b={1}")]
    InvalidBounds(f64, f64),
    /// Range is outside [0, 100] limits.
    #[error("range out of bounds: must be within [0, 100]")]
    OutOfRange,
    /// No thresholds matched the range (internal error).
    #[error("no thresholds matched the range")]
    NoMatchingThresholds,
}

/// Minimum threshold value for log-uniform spacing (avoids log(0)).
pub const MIN_THRESHOLD: f64 = 1e-6;
/// Maximum threshold value (matches [0, 100] range requirement).
pub const MAX_THRESHOLD: f64 = 100.0;

/// Default number of log-uniform thresholds (1024 for fine-grained overlap detection).
pub const DEFAULT_NUM_THRESHOLDS: usize = 1024;
/// Default number of center quantization levels (128 for smooth center encoding).
pub const DEFAULT_NUM_CENTER_LEVELS: usize = 128;
/// Default number of span quantization levels (128 for smooth span encoding).
pub const DEFAULT_NUM_SPAN_LEVELS: usize = 128;

/// Generate log-uniform spaced thresholds for range overlap detection.
/// Log-uniform spacing ensures nearly-identical ranges have >99% threshold overlap.
pub const fn generate_log_uniform_thresholds<const N: usize>() -> [f64; N] {
    let mut thresholds = [0.0; N];
    let log_min = MIN_THRESHOLD.ln();
    let log_max = MAX_THRESHOLD.ln();
    let log_step = (log_max - log_min) / (N - 1) as f64;

    let mut i = 0;
    while i < N {
        thresholds[i] = (log_min + log_step * i as f64).exp();
        i += 1;
    }
    thresholds
}

/// Semantic encoder for range constraints using 3-layer multi-scale HDC encoding.
/// 
/// Layers:
/// 1. Threshold Occupation: Bundle of thresholds within the range (main similarity driver)
/// 2. Center Levels: Hypervector for the range center
/// 3. Span Levels: Hypervector for the range width
#[derive(Debug, Clone)]
pub struct Encoder<
    const NUM_THRESHOLDS: usize = DEFAULT_NUM_THRESHOLDS,
    const NUM_CENTER_LEVELS: usize = DEFAULT_NUM_CENTER_LEVELS,
    const NUM_SPAN_LEVELS: usize = DEFAULT_NUM_SPAN_LEVELS,
> {
    thresholds: [f64; NUM_THRESHOLDS],
    threshold_hvs: [Hypervector; NUM_THRESHOLDS],
    center_hvs: [Hypervector; NUM_CENTER_LEVELS],
    span_hvs: [Hypervector; NUM_SPAN_LEVELS],
}

impl<
    const NUM_T: usize,
    const NUM_C: usize,
    const NUM_S: usize,
> Encoder<NUM_T, NUM_C, NUM_S> {
    /// Create a new encoder with reproducible hypervectors from a seed.
    pub fn new(seed: u64) -> Self {
        let mut rng = XorShift64Star::seed_from_u64(seed);
        let thresholds = generate_log_uniform_thresholds::<NUM_T>();
        let threshold_hvs = [(); NUM_T].map(|_| Hypervector::random(&mut rng));
        let center_hvs = [(); NUM_C].map(|_| Hypervector::random(&mut rng));
        let span_hvs = [(); NUM_S].map(|_| Hypervector::random(&mut rng));

        Self { thresholds, threshold_hvs, center_hvs, span_hvs }
    }

    /// Encode a range [a, b] (0 ≤ a < b ≤ 100) into a hypervector.
    /// 
    /// # Guarantees
    /// - range(0, 100) vs range(0, 99) have >0.95 similarity
    /// - Similar ranges have high similarity, dissimilar ranges have ~0.5 similarity
    pub fn encode_range(&self, a: f64, b: f64) -> Result<Hypervector, EncodingError> {
        // Validate input
        if a < 0.0 || b > MAX_THRESHOLD {
            return Err(EncodingError::OutOfRange);
        }
        if a >= b {
            return Err(EncodingError::InvalidBounds(a, b));
        }

        // 1. Threshold Occupation Layer
        let active_thresholds: Vec<Hypervector> = self.thresholds
            .iter()
            .zip(self.threshold_hvs.iter())
            .filter(|(&t, _)| t >= a && t <= b)
            .map(|(_, &hv)| hv)
            .collect();

        if active_thresholds.is_empty() {
            return Err(EncodingError::NoMatchingThresholds);
        }

        let threshold_hv = majority_bundle(&active_thresholds)?;

        // 2. Center Level Layer
        let center = (a + b) / 2.0;
        let center_idx = ((center - MIN_THRESHOLD) / (MAX_THRESHOLD - MIN_THRESHOLD) * (NUM_C - 1) as f64)
            .round() as usize;
        let center_idx = center_idx.clamp(0, NUM_C - 1);
        let center_hv = self.center_hvs[center_idx];

        // 3. Span Level Layer
        let span = b - a;
        let span_idx = (span / MAX_THRESHOLD * (NUM_S - 1) as f64)
            .round() as usize;
        let span_idx = span_idx.clamp(0, NUM_S - 1);
        let span_hv = self.span_hvs[span_idx];

        // Bind all layers
        Ok(bind(bind(threshold_hv, center_hv), span_hv))
    }
}
```

```rust
// src/matcher.rs
//! TUTOR-style hyperdimensional constraint matcher.

use crate::{Hypervector, hamming_similarity};
use thiserror::Error;

/// Error type for matcher operations.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Error)]
#[non_exhaustive]
pub enum MatcherError {
    /// No concepts stored in matcher.
    #[error("matcher contains no concepts")]
    NoConcepts,
    /// Top-k value is 0.
    #[error("top-k must be greater than 0")]
    InvalidTopK,
}

/// TUTOR-style hyperdimensional classifier/matcher.
/// Stores concepts as hypervectors (bundles of training examples) and matches queries
/// using Hamming similarity.
#[derive(Debug, Clone, Default)]
pub struct TUTORConstraintMatcher<K: Clone + PartialEq> {
    concepts: Vec<(K, Hypervector)>,
}

impl<K: Clone + PartialEq> TUTORConstraintMatcher<K> {
    /// Create a new empty matcher.
    #[inline]
    pub fn new() -> Self {
        Self { concepts: Vec::new() }
    }

    /// Add or update a concept with a pre-bundled hypervector.
    #[inline]
    pub fn add_concept(&mut self, id: K, hv: Hypervector) {
        if let Some((_, existing_hv)) = self.concepts.iter_mut().find(|(cid, _)| cid == &id) {
            *existing_hv = hv;
        } else {
            self.concepts.push((id, hv));
        }
    }

    /// Add an example to an existing concept (or create a new concept).
    /// Updates the concept's hypervector to be the majority bundle of all existing examples
    /// and the new example.
    pub fn add_example(&mut self, id: K, example_hv: Hypervector) {
        if let Some((_, existing_hv)) = self.concepts.iter_mut().find(|(cid, _)| cid == &id) {
            // Bundle existing concept (1 example) with new example
            *existing_hv = match majority_bundle(&[*existing_hv, example_hv]) {
                Ok(hv) => hv,
                Err(_) => example_hv,
            };
        } else {
            self.concepts.push((id, example_hv));
        }
    }

    /// Bundle all stored concepts into a single hypervector.
    /// Useful for compact storage or multi-concept queries.
    pub fn bundle_all(&self) -> Result<Hypervector, MatcherError> {
        if self.concepts.is_empty() {
            return Err(MatcherError::NoConcepts);
        }
        let hvs: Vec<Hypervector> = self.concepts.iter().map(|(_, hv)| *hv).collect();
        Ok(majority_bundle(&hvs)?)
    }

    /// Query the matcher for the top-k most similar concepts.
    /// Returns a vector of (concept_id, similarity) sorted by similarity descending.
    pub fn query(&self, query_hv: &Hypervector, top_k: usize) -> Result<Vec<(K, f64)>, MatcherError> {
        if self.concepts.is_empty() {
            return Err(MatcherError::NoConcepts);
        }
        if top_k == 0 {
            return Err(MatcherError::InvalidTopK);
        }

        // Calculate similarities
        let mut scores: Vec<(K, f64)> = self.concepts
            .iter()
            .map(|(id, hv)| (id.clone(), hamming_similarity(query_hv, hv)))
            .collect();

        // Sort by similarity descending
        scores.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(core::cmp::Ordering::Equal));

        // Take top-k
        Ok(scores.into_iter().take(top_k).collect())
    }

    /// Get the number of stored concepts.
    #[inline]
    pub fn len(&self) -> usize {
        self.concepts.len()
    }

    /// Check if the matcher is empty.
    #[inline]
    pub fn is_empty(&self) -> bool {
        self.concepts.is_empty()
    }
}

// Import for majority_bundle used in add_example
use crate::majority_bundle;
```

```rust
// src/sram.rs
//! 64-byte aligned SRAM records for embedded storage.

use core::mem::{align_of, size_of};
use thiserror::Error;

/// Error type for SRAM record operations.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Error)]
#[non_exhaustive]
pub enum SramError {
    /// Byte slice has invalid length for the record type.
    #[error("invalid length: expected {0}, got {1}")]
    InvalidLength(usize, usize),
    /// Byte slice is not 64-byte aligned.
    #[error("byte slice is not 64-byte aligned")]
    Misaligned,
}

/// 64-byte aligned record for SRAM storage.
/// Guarantees 64-byte alignment for cache-line and SRAM compatibility.
///
/// # Type Parameters
/// * `T` - Type of value stored in the record (must be `Copy + Clone`)
#[repr(align(64))]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct SramRecord<T: Clone + Copy>(pub T);

impl<T: Clone + Copy> SramRecord<T> {
    /// Create a new SRAM record from a value.
    #[inline]
    pub const fn new(value: T) -> Self {
        Self(value)
    }

    /// Get a reference to the inner value.
    #[inline]
    pub const fn inner(&self) -> &T {
        &self.0
    }

    /// Get a mutable reference to the inner value.
    #[inline]
    pub fn inner_mut(&mut self) -> &mut T {
        &mut self.0
    }

    /// View the record as a byte slice (for serialization).
    #[inline]
    pub fn as_bytes(&self) -> &[u8] {
        // SAFETY: SramRecord is aligned, T is Copy, and byte representation is valid
        unsafe {
            core::slice::from_raw_parts(
                (self as *const Self) as *const u8,
                size_of::<Self>(),
            )
        }
    }

    /// Create a record from a byte slice (for deserialization).
    /// Requires the slice to be 64-byte aligned and have the correct length.
    pub fn from_bytes(bytes: &[u8]) -> Result<Self, SramError> {
        let expected_len = size_of::<Self>();
        if bytes.len() != expected_len {
            return Err(SramError::InvalidLength(expected_len, bytes.len()));
        }

        // Check alignment
        let ptr = bytes.as_ptr();
        if (ptr as usize) % 64 != 0 {
            return Err(SramError::Misaligned);
        }

        // SAFETY: Checked length and alignment, T is Copy
        Ok(unsafe { core::ptr::read(ptr as *const Self) })
    }

    /// Check if the record is correctly 64-byte aligned.
    #[inline]
    pub const fn is_aligned(&self) -> bool {
        (self as *const Self as usize) % align_of::<Self>() == 0
    }
}

// Compile-time alignment check
const _: () = assert!(align_of::<SramRecord<u8>>() == 64);
const _: () = assert!(align_of::<SramRecord<[u64; 16]>>() == 64);
```

```rust
// src/stain.rs
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
```

```rust
// tests/integration.rs
//! Integration tests for flux-hdc library.
#![cfg(test)]

use flux_hdc::*;
use rand::Rng;
use rand_xoshiro::XorShift64Star;
use rand::SeedableRng;

const TEST_SEED: u64 = 0xdeadbeef_cafe_babe;

#[test]
fn test_encoding_similarity_near_ranges() {
    // Test requirement: range(0,100) vs range(0,99) >0.95 similarity
    let encoder = Encoder::new(TEST_SEED);
    let hv1 = encoder.encode_range(0.0, 100.0).unwrap();
    let hv2 = encoder.encode_range(0.0, 99.0).unwrap();
    let sim = hamming_similarity(&hv1, &hv2);
    assert!(sim > 0.95, "Similarity {} is below 0.95 threshold", sim);
}

#[test]
fn test_encoding_similarity_adjacent_ranges() {
    let encoder = Encoder::new(TEST_SEED);
    let hv1 = encoder.encode_range(0.0, 50.0).unwrap();
    let hv2 = encoder.encode_range(0.0, 51.0).unwrap();
    let sim = hamming_similarity(&hv1, &hv2);
    assert!(sim > 0.95, "Adjacent ranges similarity {} < 0.95", sim);
}

#[test]
fn test_encoding_dissimilar_ranges() {
    let encoder = Encoder::new(TEST_SEED);
    let hv1 = encoder.encode_range(0.0, 1.0).unwrap();
    let hv2 = encoder.encode_range(99.0, 100.0).unwrap();
    let sim = hamming_similarity(&hv1, &hv2);
    // Dissimilar ranges should have ~0.5 similarity (random chance)
    assert!(sim < 0.6, "Dissimilar ranges similarity {} is too high", sim);
    assert!(sim > 0.4, "Dissimilar ranges similarity {} is too low", sim);
}

#[test]
fn test_folding_similarity_preservation() {
    let mut rng = XorShift64Star::seed_from_u64(TEST_SEED);
    let hv1 = Hypervector::random(&mut rng);
    let hv2 = Hypervector::random(&mut rng);

    // Induce 10% difference (102