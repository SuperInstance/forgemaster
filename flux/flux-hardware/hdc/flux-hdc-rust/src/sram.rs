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
    pub fn is_aligned(&self) -> bool {
        (self as *const Self as usize) % align_of::<Self>() == 0
    }
}

// Compile-time alignment check
const _: () = assert!(align_of::<SramRecord<u8>>() == 64);
const _: () = assert!(align_of::<SramRecord<[u64; 16]>>() == 64);