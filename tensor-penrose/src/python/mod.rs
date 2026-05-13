//! Python bindings via PyO3.

mod py_tile;
mod py_tiling;
mod py_backend;
mod py_ops;

use pyo3::prelude::*;

/// tensor-penrose Python module.
#[pymodule]
fn _tensor_penrose(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<py_tile::PyTile>()?;
    m.add_class::<py_tiling::PyTiling>()?;
    m.add_class::<py_backend::PyEisensteinBackend>()?;
    m.add_class::<py_backend::PyPenroseBackend>()?;
    m.add_class::<py_ops::PyThresholdOp>()?;
    m.add_class::<py_ops::PyL1NormOp>()?;
    m.add_function(wrap_pyfunction!(py_ops::apply_threshold, m)?)?;
    m.add_function(wrap_pyfunction!(py_tiling::from_coordinates, m)?)?;
    Ok(())
}
