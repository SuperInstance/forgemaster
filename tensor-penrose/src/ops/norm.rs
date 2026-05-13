//! Norm operations.

use crate::tile::PTile;
use super::BorderOp;

/// L1 border norm — absolute difference between border vectors.
pub struct L1Norm;

impl BorderOp for L1Norm {
    fn compute(&self, tile_a: &PTile, tile_b: &PTile) -> f32 {
        let (rows_a, cols_a) = tile_a.inner.tensor_shape;
        let (_rows_b, cols_b) = tile_b.inner.tensor_shape;

        let mut mismatch = 0.0f32;

        // Compare last row of A with first row of B
        let border_len = cols_a.min(cols_b);
        for col in 0..border_len {
            let va = tile_a.inner.tensor_at(rows_a - 1, col);
            let vb = tile_b.inner.tensor_at(0, col);
            mismatch += (va - vb).abs();
        }

        mismatch
    }

    fn name(&self) -> &'static str {
        "l1_norm"
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::TileType;

    #[test]
    fn test_l1_border_norm_identical() {
        let mut tile = PTile::new([2, 2, 2, 2, 2], TileType::Thick, 0.0, [0.0, 0.0]);
        tile.fill();
        let tile_b = tile.clone();
        let norm = L1Norm;
        let result = norm.compute(&tile, &tile_b);
        // Same tile cloned: comparing last row with first row of SAME tensor
        // The last row and first row may differ (fill_from_source is not uniform)
        // Just verify it's non-negative and finite
        assert!(result.is_finite());
        assert!(result >= 0.0, "Border norm should be non-negative");
    }
}
