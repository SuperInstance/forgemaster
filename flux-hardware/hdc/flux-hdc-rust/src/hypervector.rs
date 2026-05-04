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