# Phase 19 Progress — Python Bindings via PyO3

> **Date:** 2026-05-13
> **Status:** ✅ COMPLETE

## What Was Built

### Rust Side (PyO3 bindings gated behind `python` feature flag)

**Files created:**
- `src/python/mod.rs` — `#[pymodule]` entry point (`_tensor_penrose`)
- `src/python/py_tile.rs` — `PyTile` #[pyclass] wrapping `PTile`
- `src/python/py_tiling.rs` — `PyTiling` #[pyclass] wrapping `PTiling` + `from_coordinates()` function
- `src/python/py_backend.rs` — `PyEisensteinBackend` and `PyPenroseBackend` wrappers
- `src/python/py_ops.rs` — `PyThresholdOp`, `PyL1NormOp`, `apply_threshold()` convenience function

**Files modified:**
- `Cargo.toml` — Added `pyo3` 0.22, `numpy` 0.22 as optional deps; added `python` feature; added `cdylib` crate type
- `src/lib.rs` — Added `#[cfg(feature = "python")] pub mod python;`

### Python Side

**Files created:**
- `pyproject.toml` — maturin build config
- `tensor_penrose/__init__.py` — Re-exports all classes and functions

## API Surface

### Classes
| Python Class | Rust Type | Methods |
|---|---|---|
| `Tile` | `PTile` | `source_coords`, `values`, `values_array()`, `tile_type`, `position`, `shape`, `fill()`, `l1_norm()`, `l2_norm()`, `apply_threshold()` |
| `Tiling` | `PTiling` | `__len__`, `__getitem__`, `edge_count()`, `fill()`, `apply_threshold()`, `constrain()`, `constraint_check()`, `l1_norms()`, `l2_norms()`, `save()`, `load_tiling()`, `backend_name`, `info()` |
| `EisensteinBackend` | `EisensteinBackend` | `snap(x, y)` → dict |
| `PenroseBackend` | `PenroseBackend` | `snap(x, y)` → dict |
| `ThresholdOp` | `Threshold` | constructor(threshold) |
| `L1NormOp` | `L1Norm` | constructor() |

### Functions
- `from_coordinates(sources, backend="eisenstein")` → `Tiling`
- `apply_threshold(tiling, threshold)` → in-place

## Verification

- ✅ `cargo build --features python` — compiles clean
- ✅ `cargo test` — 17/17 tests pass (no feature regression)
- ✅ `maturin develop --features python` — wheel builds
- ✅ `import tensor_penrose as pt` — works
- ✅ `pt.from_coordinates(...)` — creates tiling, tiles filled
- ✅ `tile.values_array()` — returns numpy 2D array with correct shape
- ✅ `tiling.constraint_check()` — returns violation values
- ✅ `tiling.save()` / `Tiling.load_tiling()` — round-trips correctly
- ✅ Backend snap returns dict with error/dodecet/chamber/is_safe
- ✅ `tiling.info()` — returns dict with tile/edge counts

## PyO3/numpy Version Notes

- PyO3 0.22.6 — uses `Bound<'py, T>` API (not deprecated `&T`)
- `PyDict::new_bound(py)` instead of `PyDict::new(py)`
- `PyArray2::from_vec2_bound(py, &nested)` for 2D numpy arrays
- numpy 0.22.1 — compatible with PyO3 0.22.x

## Not Yet Implemented (deferred to Phase 19 polish / Phase 21)

- [ ] `kernels.py` — Python-side kernel factories
- [ ] `torch_bridge.py` — `from_torch()` / `to_torch()` helpers
- [ ] `@pt.kernel` decorator for custom Python kernels
- [ ] Zero-copy numpy (currently copies — needs pinned buffer)
- [ ] CI wheel matrix (linux/mac/windows)
- [ ] PyPI publish
