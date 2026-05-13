//! PyTiling — Python wrapper for PTiling.

use pyo3::prelude::*;
use pyo3::types::PyDict;
use crate::tiling::PTiling;
use crate::backend::eisenstein::EisensteinBackend;
use crate::backend::penrose::PenroseBackend;
use crate::backend::LatticeBackend;
use super::py_tile::PyTile;

/// A collection of tensor tiles with adjacency info and constraint ops.
#[pyclass(name = "Tiling")]
pub struct PyTiling {
    pub(crate) inner: PTiling,
}

#[pymethods]
impl PyTiling {
    /// Number of tiles.
    fn __len__(&self) -> PyResult<usize> {
        Ok(self.inner.tiles.len())
    }

    /// Get tile by index.
    fn __getitem__(&self, idx: isize) -> PyResult<PyTile> {
        let len = self.inner.tiles.len() as isize;
        let actual = if idx < 0 { len + idx } else { idx };
        if actual < 0 || actual as usize >= self.inner.tiles.len() {
            return Err(pyo3::exceptions::PyIndexError::new_err("index out of range"));
        }
        Ok(PyTile {
            inner: self.inner.tiles[actual as usize].clone(),
        })
    }

    /// Number of adjacency edges.
    fn edge_count(&self) -> PyResult<usize> {
        Ok(self.inner.adjacency.len())
    }

    /// Fill all tiles from their source coordinates.
    fn fill(&mut self) -> PyResult<()> {
        for tile in &mut self.inner.tiles {
            tile.fill();
        }
        Ok(())
    }

    /// Apply a threshold operation to all tiles.
    fn apply_threshold(&mut self, threshold: f32) -> PyResult<()> {
        for tile in &mut self.inner.tiles {
            tile.apply_threshold(threshold);
        }
        Ok(())
    }

    /// Register constraint edges between tiles.
    fn constrain(&mut self, edges: Vec<(usize, usize)>) -> PyResult<()> {
        self.inner.constrain(&edges);
        Ok(())
    }

    /// Check constraints: return border mismatch per registered edge.
    /// Returns a list of floats — lower = better match, zero = perfect.
    fn constraint_check(&self) -> PyResult<Vec<f32>> {
        Ok(self.inner.constraint_check())
    }

    /// L1 norms of all tiles as a list.
    fn l1_norms(&self) -> PyResult<Vec<f32>> {
        Ok(self.inner.tiles.iter().map(|t| t.l1_norm()).collect())
    }

    /// L2 norms of all tiles as a list.
    fn l2_norms(&self) -> PyResult<Vec<f32>> {
        Ok(self.inner.tiles.iter().map(|t| t.l2_norm()).collect())
    }

    /// Save tiling to a binary file.
    fn save(&self, path: &str) -> PyResult<()> {
        self.inner.save(path)?;
        Ok(())
    }

    /// Load tiling from a binary file.
    #[staticmethod]
    fn load_tiling(path: &str) -> PyResult<Self> {
        let tiling = PTiling::load(path)?;
        Ok(PyTiling { inner: tiling })
    }

    /// Get backend name.
    #[getter]
    fn backend_name(&self) -> PyResult<&str> {
        Ok(&self.inner.backend_name)
    }

    /// Summary info as a dict.
    fn info<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let i = self.inner.info();
        let dict = PyDict::new_bound(py);
        dict.set_item("tile_count", i.tile_count)?;
        dict.set_item("thick_count", i.thick_count)?;
        dict.set_item("thin_count", i.thin_count)?;
        dict.set_item("adjacency_count", i.adjacency_count)?;
        dict.set_item("backend_name", &i.backend_name)?;
        Ok(dict)
    }

    fn __repr__(&self) -> PyResult<String> {
        Ok(format!(
            "Tiling(tiles={}, edges={}, backend={})",
            self.inner.tiles.len(),
            self.inner.adjacency.len(),
            self.inner.backend_name,
        ))
    }
}

/// Create a Tiling from 5D source coordinates.
///
/// Args:
///     sources: list of [a, b, c, d, e] integer coordinate lists
///     backend: "eisenstein" or "penrose" (default: "eisenstein")
///
/// Returns:
///     A Tiling with tiles created and filled from the coordinates.
#[pyfunction]
#[pyo3(signature = (sources, backend="eisenstein"))]
pub fn from_coordinates(sources: Vec<[i32; 5]>, backend: &str) -> PyResult<PyTiling> {
    let tiling = match backend {
        "eisenstein" => {
            let b = EisensteinBackend::new();
            PTiling::from_lattice(&sources, &b)
        }
        "penrose" => {
            let b = PenroseBackend::new();
            PTiling::from_lattice(&sources, &b)
        }
        other => {
            return Err(pyo3::exceptions::PyValueError::new_err(format!(
                "Unknown backend: '{}'. Use 'eisenstein' or 'penrose'.",
                other
            )));
        }
    };
    Ok(PyTiling { inner: tiling })
}
