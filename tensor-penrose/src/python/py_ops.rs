//! PyOps — Python wrappers for tile operations.

use pyo3::prelude::*;
use crate::ops::{Threshold, L1Norm, TileOp};
use crate::tile::PTile;
use super::py_tiling::PyTiling;

/// Threshold operation: zero out values below a threshold.
#[pyclass(name = "ThresholdOp")]
pub struct PyThresholdOp {
    threshold: f32,
}

#[pymethods]
impl PyThresholdOp {
    #[new]
    fn new(threshold: f32) -> Self {
        Self { threshold }
    }

    fn __repr__(&self) -> PyResult<String> {
        Ok(format!("ThresholdOp({})", self.threshold))
    }
}

/// L1 norm operation (read-only, returns norms).
#[pyclass(name = "L1NormOp")]
pub struct PyL1NormOp;

#[pymethods]
impl PyL1NormOp {
    #[new]
    fn new() -> Self {
        Self
    }

    fn __repr__(&self) -> PyResult<String> {
        Ok("L1NormOp()".to_string())
    }
}

/// Convenience function: apply threshold to all tiles in a tiling.
#[pyfunction]
pub fn apply_threshold(tiling: &mut PyTiling, threshold: f32) -> PyResult<()> {
    let op = Threshold::new(threshold);
    tiling.inner.apply(&op);
    Ok(())
}
