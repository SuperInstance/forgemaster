//! PyTile — Python wrapper for PTile.

use pyo3::prelude::*;
use numpy::PyArray2;
use crate::tile::PTile;
use crate::TileType;

/// A tensor-valued Penrose tile.
///
/// Each tile has source coordinates (5D Eisenstein integers), a tensor of float32
/// values, a tile type (thick or thin), and a 2D position in the tiling.
#[pyclass(name = "Tile")]
pub struct PyTile {
    pub(crate) inner: PTile,
}

#[pymethods]
impl PyTile {
    /// Source coordinates as a list of 5 integers [a, b, c, d, e].
    #[getter]
    fn source_coords(&self) -> PyResult<Vec<i32>> {
        Ok(self.inner.inner.source_coords.to_vec())
    }

    /// Tensor values as a flat list of floats.
    /// Use .values_array for a numpy array with proper shape.
    #[getter]
    fn values(&self) -> PyResult<Vec<f32>> {
        Ok(self.inner.inner.tensor.clone())
    }

    /// Tensor values as a numpy 2D array with proper shape.
    fn values_array<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyArray2<f32>>> {
        let (rows, cols) = self.inner.inner.tensor_shape;
        let data = self.inner.inner.tensor.clone();
        // Build nested Vec<Vec<f32>> for from_vec2_bound
        let mut nested = Vec::with_capacity(rows);
        for r in 0..rows {
            let row: Vec<f32> = data[r * cols..(r + 1) * cols].to_vec();
            nested.push(row);
        }
        let arr = PyArray2::from_vec2_bound(py, &nested)?;
        Ok(arr)
    }

    /// Tile type: "thick" or "thin".
    #[getter]
    fn tile_type(&self) -> PyResult<&'static str> {
        Ok(match self.inner.tile_type() {
            TileType::Thick => "thick",
            TileType::Thin => "thin",
        })
    }

    /// 2D position (x, y) in the Penrose floor.
    #[getter]
    fn position(&self) -> PyResult<(f64, f64)> {
        let pos = self.inner.inner.position;
        Ok((pos[0], pos[1]))
    }

    /// Tensor shape as (rows, cols).
    #[getter]
    fn shape(&self) -> PyResult<(usize, usize)> {
        Ok(self.inner.inner.tensor_shape)
    }

    /// Fill the tensor from source coordinates.
    fn fill(&mut self) -> PyResult<()> {
        self.inner.fill();
        Ok(())
    }

    /// L1 norm of the tensor (constraint energy).
    fn l1_norm(&self) -> PyResult<f32> {
        Ok(self.inner.l1_norm())
    }

    /// L2 norm of the tensor (signal strength).
    fn l2_norm(&self) -> PyResult<f32> {
        Ok(self.inner.l2_norm())
    }

    /// Apply threshold: zero out values below `threshold`.
    fn apply_threshold(&mut self, threshold: f32) -> PyResult<()> {
        self.inner.apply_threshold(threshold);
        Ok(())
    }

    fn __repr__(&self) -> PyResult<String> {
        let (rows, cols) = self.inner.inner.tensor_shape;
        Ok(format!(
            "Tile(type={}, shape=({}, {}), coords={:?})",
            match self.inner.tile_type() {
                TileType::Thick => "thick",
                TileType::Thin => "thin",
            },
            rows,
            cols,
            self.inner.inner.source_coords,
        ))
    }
}
