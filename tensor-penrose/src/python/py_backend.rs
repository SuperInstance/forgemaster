//! PyBackend — Python wrappers for lattice backends.

use pyo3::prelude::*;
use pyo3::types::PyDict;
use crate::backend::eisenstein::EisensteinBackend;
use crate::backend::penrose::PenroseBackend;
use crate::backend::LatticeBackend;

/// Eisenstein A₂ lattice backend (26M snap/s via fleet-math-c C bridge).
#[pyclass(name = "EisensteinBackend")]
pub struct PyEisensteinBackend {
    inner: EisensteinBackend,
}

fn snap_to_dict<'py>(py: Python<'py>, error: f64, dodecet: u16, chamber: u8, is_safe: bool) -> PyResult<Bound<'py, PyDict>> {
    let dict = PyDict::new_bound(py);
    dict.set_item("error", error)?;
    dict.set_item("dodecet", dodecet)?;
    dict.set_item("chamber", chamber)?;
    dict.set_item("is_safe", is_safe)?;
    Ok(dict)
}

#[pymethods]
impl PyEisensteinBackend {
    #[new]
    fn new() -> Self {
        Self { inner: EisensteinBackend::new() }
    }

    /// Snap a point (x, y) to the nearest lattice point.
    /// Returns a dict with error, dodecet, chamber, is_safe.
    fn snap<'py>(&self, py: Python<'py>, x: f64, y: f64) -> PyResult<Bound<'py, PyDict>> {
        let result = self.inner.snap(x, y);
        snap_to_dict(py, result.error, result.dodecet, result.chamber, result.is_safe)
    }

    fn __repr__(&self) -> PyResult<String> {
        Ok("EisensteinBackend()".to_string())
    }
}

/// Penrose 5D→2D projection backend.
#[pyclass(name = "PenroseBackend")]
pub struct PyPenroseBackend {
    inner: PenroseBackend,
}

#[pymethods]
impl PyPenroseBackend {
    #[new]
    fn new() -> Self {
        Self { inner: PenroseBackend::new() }
    }

    /// Snap a point (x, y) to the nearest lattice point.
    fn snap<'py>(&self, py: Python<'py>, x: f64, y: f64) -> PyResult<Bound<'py, PyDict>> {
        let result = self.inner.snap(x, y);
        snap_to_dict(py, result.error, result.dodecet, result.chamber, result.is_safe)
    }

    fn __repr__(&self) -> PyResult<String> {
        Ok("PenroseBackend()".to_string())
    }
}
