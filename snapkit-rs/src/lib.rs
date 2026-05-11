//! # snapkit
//!
//! Zero-dependency Eisenstein snap, spectral analysis, temporal grids,
//! and connectome detection — `no_std` compatible.
//!
//! ## Modules
//!
//! - [`eisenstein`] — Eisenstein integer type, naive snap
//! - [`voronoi`] — 9-candidate Voronoï snap with covering radius guarantee
//! - [`temporal`] — Beat grid, T-minus-0 detection
//! - [`spectral`] — Entropy, Hurst exponent, autocorrelation
//! - [`connectome`] — Cross-correlation coupling detection
//! - [`types`] — Shared types

#![no_std]
#![allow(clippy::excessive_precision)]

extern crate alloc;

pub mod eisenstein;
pub mod voronoi;
pub mod temporal;
pub mod spectral;
pub mod connectome;
pub mod types;

// Re-export key types at crate root for convenience
pub use eisenstein::EisensteinInt;
pub use voronoi::eisenstein_round_voronoi;
pub use types::{TemporalResult, SpectralSummary, CouplingType, RoomPair, ConnectomeResult};
