//! Lattice backends — pluggable lattice geometry for tile projection.

pub mod eisenstein;
pub mod penrose;

use crate::TileType;
use crate::tile::PTile;

/// Result of snapping a point to the lattice.
#[derive(Debug, Clone)]
pub struct SnapResult {
    /// Distance from original point to snapped lattice point.
    pub error: f64,
    /// Constraint state bits.
    pub dodecet: u16,
    /// Weyl chamber index (0-5).
    pub chamber: u8,
    /// Whether this snap is considered safe.
    pub is_safe: bool,
}

/// Trait for lattice backends.
///
/// Each backend defines how 2D coordinates map to tile positions and shapes.
/// Implement this trait to add custom lattice geometries.
pub trait LatticeBackend: Send + Sync {
    /// Name of this backend (e.g., "eisenstein", "penrose").
    fn name(&self) -> &'static str;

    /// Snap a point (x, y) to the nearest lattice point.
    fn snap(&self, x: f64, y: f64) -> SnapResult;

    /// Get the tensor shape for a given tile type.
    fn tile_shape(&self, tile_type: TileType) -> (usize, usize) {
        match tile_type {
            TileType::Thick => (5, 5),
            TileType::Thin => (3, 8),
        }
    }
}
