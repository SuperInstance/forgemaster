#![allow(unused_imports)]
//! # tensor-penrose — The Constraint Tensor Framework
//!
//! Like PyTorch, but the tensors come with positions and the array is a tiling.
//!
//! ## Core Types
//! - [`PTile`] — a tensor-valued Penrose tile (wraps `TensorTile` from penrose-memory)
//! - [`PTiling`] — a collection of tiles with adjacency info and constraint checking
//! - [`LatticeBackend`] — pluggable lattice geometry (Eisenstein, Penrose, custom)
//!
//! ## Quick Start
//! ```rust,ignore
//! use tensor_penrose::{PTiling, backend::PenroseBackend};
//!
//! let backend = PenroseBackend::new();
//! let tiling = PTiling::from_lattice(&points, &backend);
//! tiling.apply(&ops::Threshold::new(0.5));
//! let violations = tiling.constraint_check();
//! ```

pub mod tile;
pub mod tiling;
pub mod backend;
pub mod ops;

pub use tile::PTile;
pub use tiling::{PTiling, PTilingInfo};

/// Tile type classification — thick (72°) or thin (36°) rhomb.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TileType {
    Thick,
    Thin,
}

impl From<penrose_memory::cut_and_project::TileType> for TileType {
    fn from(tt: penrose_memory::cut_and_project::TileType) -> Self {
        match tt {
            penrose_memory::cut_and_project::TileType::Thick => TileType::Thick,
            _ => TileType::Thin,
        }
    }
}
