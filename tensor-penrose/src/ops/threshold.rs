//! Threshold operation — zero out values below a threshold.

use crate::tile::PTile;
use super::TileOp;

/// Zero out tensor values below a given threshold.
pub struct Threshold {
    pub value: f32,
}

impl Threshold {
    pub fn new(value: f32) -> Self {
        Self { value }
    }
}

impl TileOp for Threshold {
    fn apply(&self, tile: &mut PTile) {
        tile.apply_threshold(self.value);
    }

    fn name(&self) -> &'static str {
        "threshold"
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::TileType;

    #[test]
    fn test_threshold_op() {
        let mut tile = PTile::new([3, 3, 3, 3, 3], TileType::Thick, 0.0, [0.0, 0.0]);
        tile.fill();
        let before = tile.inner.tensor.clone();
        let op = Threshold::new(0.5);
        op.apply(&mut tile);
        for (i, &v) in tile.inner.tensor.iter().enumerate() {
            if before[i] < 0.5 {
                assert_eq!(v, 0.0);
            }
        }
    }
}
