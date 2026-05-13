//! PTile — tensor-valued Penrose tile wrapper.
//!
//! Wraps `TensorTile` from penrose-memory, adding dtype/device metadata
//! and Python interop helpers.

use crate::TileType;
use penrose_memory::cut_and_project::TileCoord;
use penrose_memory::tensor_tile::TensorTile;

/// A tensor-valued Penrose tile.
///
/// Thin wrapper around `TensorTile` with dtype/device metadata for future
/// Python interop (PyO3) and GPU backend support.
#[derive(Debug, Clone)]
pub struct PTile {
    /// The underlying tensor tile.
    pub inner: TensorTile,
    /// Data type — f32 only for now.
    pub dtype: String,
    /// Device — "cpu" by default.
    pub device: String,
}

impl PTile {
    /// Create a new PTile from 5D source coordinates.
    ///
    /// - Thick tiles get shape `(5, 5)`.
    /// - Thin tiles get shape `(3, 8)`.
    pub fn new(
        source_coords: [i32; 5],
        tile_type: TileType,
        orientation: f64,
        position: [f64; 2],
    ) -> Self {
        let pm_type = match tile_type {
            TileType::Thick => penrose_memory::cut_and_project::TileType::Thick,
            TileType::Thin => penrose_memory::cut_and_project::TileType::Thin,
        };
        Self {
            inner: TensorTile::new(source_coords, pm_type, orientation, position),
            dtype: "float32".to_string(),
            device: "cpu".to_string(),
        }
    }

    /// Create from a penrose-memory `TileCoord`.
    pub fn from_tile_coord(tc: &TileCoord) -> Self {
        let tt = crate::TileType::from(tc.tile_type);
        let mut coords = [0i32; 5];
        for (k, &v) in tc.source_coords.iter().enumerate().take(5) {
            coords[k] = v;
        }
        Self::new(coords, tt, 0.0, [tc.x, tc.y])
    }

    /// Fill the tensor from 5D source coordinates using orthogonal basis modes.
    pub fn fill(&mut self) {
        self.inner.fill_from_source();
    }

    /// Apply threshold: zero out values below `threshold`.
    pub fn apply_threshold(&mut self, threshold: f32) {
        self.inner.apply_threshold(threshold);
    }

    /// L1 norm of the tensor (constraint energy).
    pub fn l1_norm(&self) -> f32 {
        self.inner.l1_norm()
    }

    /// L2 norm of the tensor (signal strength).
    pub fn l2_norm(&self) -> f32 {
        self.inner.l2_norm()
    }

    /// Export tensor as flat Vec<f32> (row-major). For Python/numpy interop.
    pub fn to_numpy(&self) -> Vec<f32> {
        self.inner.tensor.clone()
    }

    /// Tensor shape (rows, cols).
    pub fn shape(&self) -> (usize, usize) {
        self.inner.tensor_shape
    }

    /// Position in the Penrose floor.
    pub fn position(&self) -> [f64; 2] {
        self.inner.position
    }

    /// Tile type.
    pub fn tile_type(&self) -> TileType {
        match self.inner.tile_type {
            penrose_memory::cut_and_project::TileType::Thick => TileType::Thick,
            _ => TileType::Thin,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ptile_creation() {
        let tile = PTile::new([1, 2, 3, 4, 5], TileType::Thick, 0.0, [1.0, 2.0]);
        assert_eq!(tile.shape(), (5, 5));
        assert_eq!(tile.dtype, "float32");
        assert_eq!(tile.device, "cpu");
        assert!(tile.inner.tensor.iter().all(|&v| v == 0.0));
    }

    #[test]
    fn test_ptile_fill() {
        let mut tile = PTile::new([5, 5, 5, 5, 5], TileType::Thick, 0.0, [0.0, 0.0]);
        tile.fill();
        // Should have non-zero values after fill
        assert!(tile.inner.tensor.iter().any(|&v| v != 0.0));
        // Norms should be positive
        assert!(tile.l1_norm() > 0.0);
        assert!(tile.l2_norm() > 0.0);
    }

    #[test]
    fn test_ptile_threshold() {
        let mut tile = PTile::new([3, 3, 3, 3, 3], TileType::Thick, 0.0, [0.0, 0.0]);
        tile.fill();
        let before = tile.inner.tensor.clone();
        tile.apply_threshold(0.5);
        for (i, &v) in tile.inner.tensor.iter().enumerate() {
            if before[i] < 0.5 {
                assert_eq!(v, 0.0);
            } else {
                assert_eq!(v, before[i]);
            }
        }
    }

    #[test]
    fn test_ptile_to_numpy() {
        let mut tile = PTile::new([1, 1, 1, 1, 1], TileType::Thick, 0.0, [0.0, 0.0]);
        tile.fill();
        let arr = tile.to_numpy();
        assert_eq!(arr.len(), 25); // 5x5
    }

    #[test]
    fn test_ptile_thin_shape() {
        let tile = PTile::new([1, 2, 3, 4, 5], TileType::Thin, 0.0, [0.0, 0.0]);
        assert_eq!(tile.shape(), (3, 8));
    }
}
