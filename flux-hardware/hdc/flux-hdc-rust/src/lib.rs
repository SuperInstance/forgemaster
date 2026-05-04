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