//! Tile operations — functions that transform tiles.

mod threshold;
mod norm;

pub use threshold::Threshold;
pub use norm::L1Norm;

use crate::tile::PTile;

/// Trait for unary tile operations.
pub trait TileOp {
    /// Apply this operation to a single tile.
    fn apply(&self, tile: &mut PTile);

    /// Human-readable name for this operation.
    fn name(&self) -> &'static str;
}

/// Trait for binary border operations (between adjacent tiles).
pub trait BorderOp {
    /// Compute a value from the border between two adjacent tiles.
    fn compute(&self, tile_a: &PTile, tile_b: &PTile) -> f32;

    /// Human-readable name for this operation.
    fn name(&self) -> &'static str;
}
