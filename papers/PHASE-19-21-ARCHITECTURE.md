# tensor-penrose — Phase 19–21 Architecture Plan

> **Date:** 2026-05-13
> **Status:** Planning
> **Baseline:** Phase 18 complete — 17/17 tests, CLI operational, C bridge at 26M snaps/sec

---

## Executive Summary

Three phases, nine weeks, one launch.

- **Phase 19 (weeks 1–3):** Python bindings via PyO3 + pip-installable wheel
- **Phase 20 (weeks 4–6):** C bridge batch optimization + AVX-512 SIMD path
- **Phase 21 (weeks 7–9):** HN demo, PLATO/Fortran integration, public launch

The architectural throughline: every optimization feeds the demo. The demo must show real numbers that shock. The PLATO integration turns "interesting math toy" into "production constraint engine."

---

## Phase 19 — Python Bindings (Weeks 1–3)

### Goal
`pip install tensor-penrose` works. `import tensor_penrose as pt` feels like PyTorch.

### 19.1 — PyO3 Crate Structure

Add a new feature flag `python` that gates all PyO3 code. This keeps the Rust crate zero-overhead for pure Rust users.

```toml
# Cargo.toml additions
[dependencies]
pyo3 = { version = "0.22", features = ["extension-module"], optional = true }
numpy = { version = "0.22", optional = true }

[features]
python = ["pyo3", "numpy"]
```

New module: `tensor-penrose/src/python/mod.rs`

```
src/python/
├── mod.rs          — #[pymodule] entry point, registers all classes
├── py_tile.rs      — PyTile wrapper (#[pyclass] around PTile)
├── py_tiling.rs    — PyTiling wrapper (#[pyclass] around PTiling)
├── py_backend.rs   — PyLatticeBackend (expose eisenstein/penrose)
└── py_ops.rs       — threshold(), normalize(), kernel decorator
```

### 19.2 — PyTile and PyTiling API Surface

The Python API must mirror PyTorch ergonomics exactly. Every method that would exist on `torch.Tensor` has an analogue.

**`PyTile` exposes:**
- `tile.source_coords` → `np.ndarray` (int32, shape `(5,)`)
- `tile.values` → `np.ndarray` (float32, shape `(5,5)` or `(3,8)`)
- `tile.tile_type` → `"thick"` or `"thin"`
- `tile.position` → `(float, float)` tuple
- `tile.fill()` → populates values from source_coords (calls Rust fill)
- `tile.l1_norm()` → float
- `tile.l2_norm()` → float

**`PyTiling` exposes:**
- `pt.Tiling.from_coordinates(sources, backend, tensor_shape)` → classmethod
- `tiling[i]` → `PyTile` (via `__getitem__`)
- `tiling.apply(kernel)` → in-place, accepts Python callable OR built-in op
- `tiling.constraint_check(metric="l1")` → `dict[str, float]`
- `tiling.fill()` → fill all tiles
- `tiling.l1_norm()` → `np.ndarray` shape `(N,)`
- `tiling.l2_norm()` → `np.ndarray` shape `(N,)`
- `tiling.save(path)` / `pt.Tiling.load(path)` → file I/O
- `tiling.to_torch()` → `torch.Tensor` shape `(N, H, W)` (optional dep)
- `len(tiling)` → tile count

**Key design decision — zero-copy NumPy bridge:**

Use `numpy` crate's `PyReadonlyArray` / `PyArray` to expose tile tensors as NumPy views without copying. The Rust `Vec<f32>` backing the tile tensor is pinned; Python gets a memoryview over it.

```rust
#[pymethods]
impl PyTile {
    fn values<'py>(&self, py: Python<'py>) -> &'py PyArray2<f32> {
        // Zero-copy: exposes Rust Vec<f32> as numpy array
        let data = self.inner.tensor_values();
        PyArray2::from_slice(py, data)
            .reshape([self.inner.rows(), self.inner.cols()])
            .unwrap()
    }
}
```

### 19.3 — Custom Python Kernels

The `@pt.kernel` decorator must work. This is the "killer feature" for Python users — custom operations that run on the Rust engine.

Strategy: Python callables are dispatched through a per-tile Python call. This is slower than native SIMD kernels but correct. The API documentation is explicit: native kernels (`pt.kernels.threshold`) run at 100M+/s; Python kernels run at ~500K/s (Python call overhead dominates).

```python
@pt.kernel
def double_minus_norm(tile):
    tile.values[:] = tile.values * 2.0 - tile.l1_norm()

tiling.apply(double_minus_norm)   # Uses Python dispatch
tiling.apply(pt.kernels.threshold(0.5))  # Uses Rust SIMD path
```

This is the right tradeoff: correctness first, JIT compilation later (Phase 22+).

### 19.4 — PyTorch Integration Bridge

```python
# Embed PyTorch weights into a tensor-penrose tiling for constraint checking
weights_tensor = torch.randn(1000, 5)   # (N, 5D) source coords
coords = weights_tensor.numpy().astype(np.int32)
tiling = pt.Tiling.from_coordinates(coords, backend="eisenstein")
tiling.fill()
violations = tiling.constraint_check()
```

`pt.from_torch(tensor)` is a thin wrapper:
```python
def from_torch(tensor: "torch.Tensor", backend="eisenstein") -> Tiling:
    coords = tensor.detach().cpu().numpy().astype(np.int32)
    return Tiling.from_coordinates(coords, backend=backend)
```

No Rust changes needed. The bridge is pure Python.

### 19.5 — Build and Distribution

**maturin** is the standard tool for PyO3 wheels.

```toml
# pyproject.toml (new file in tensor-penrose/)
[build-system]
requires = ["maturin>=1.5"]
build-backend = "maturin"

[tool.maturin]
features = ["python"]
module-name = "tensor_penrose._tensor_penrose"
```

CI matrix: `linux/x86_64`, `linux/aarch64`, `macos/arm64`, `windows/x86_64`.

```bash
maturin develop --features python    # dev install
maturin build --release --features python  # wheel
```

**Python package structure:**
```
tensor_penrose/
├── __init__.py          — re-exports, version, lazy import of native ext
├── _tensor_penrose.so   — PyO3 compiled extension
├── kernels.py           — built-in kernel factories (threshold, normalize, etc.)
├── backends.py          — backend string → Rust enum mapping
└── torch_bridge.py      — from_torch(), from_tf() helpers
```

### 19.6 — Phase 19 Acceptance Criteria

- [ ] `pip install tensor-penrose` succeeds on Python 3.10, 3.11, 3.12
- [ ] `import tensor_penrose as pt` succeeds without error
- [ ] `pt.Tiling.from_coordinates(...)` creates a tiling in <1ms for 1000 tiles
- [ ] `tiling.apply(pt.kernels.threshold(0.5))` runs in <5ms for 1000 tiles
- [ ] `tiling.constraint_check()` returns correct violation counts
- [ ] NumPy bridge is zero-copy (verified with `np.shares_memory`)
- [ ] Jupyter notebook example runs end-to-end
- [ ] PyTorch integration demo works (embed weights, check constraints)

---

## Phase 20 — C Bridge Batch Optimization + AVX-512 (Weeks 4–6)

### Goal
Push from 26M snaps/sec to 200M+ snaps/sec on AVX-512 hardware. Eliminate the serial bottleneck in the C bridge. Make constraint_check the fastest operation in the Python ML ecosystem for aperiodic constraint graphs.

### 20.1 — Current Bottleneck Analysis

The existing `fleet-math-c` bridge exposes single-point snap:
```c
SnapResult snap_eisenstein(double x, double y);
```

The `snap_a`/`snap_b` dual-field addition (commit `a6f363b`) eliminates double-computation in the Rust wrapper, but the fundamental bottleneck is the per-call overhead crossing the FFI boundary for each point.

For 1000 tiles: 1000 FFI calls × ~40ns/call = 40μs just in boundary crossings.

### 20.2 — Batch C API

Add a batch interface to `fleet-math-c`:

```c
// fleet-math-c/src/snap_batch.c

typedef struct {
    double x;
    double y;
} Point2D;

typedef struct {
    int32_t a;
    int32_t b;
    int32_t c;
    int32_t d;
    int32_t e;
    int8_t  tile_type;  // 0=thick, 1=thin
    float   perp_dist;
} SnapResult5D;

// Process N points in one call — single FFI crossing
void snap_eisenstein_batch(
    const Point2D* points,
    SnapResult5D*  results,
    size_t         n
);
```

The Rust wrapper calls this once per tiling, not once per tile:

```rust
// tensor-penrose/src/backend/eisenstein.rs
impl LatticeBackend for EisensteinBackend {
    fn snap_batch(&self, points: &[(f64, f64)]) -> Vec<SnapResult> {
        // Single FFI call for all points
        unsafe {
            let c_points = /* transmute points slice */;
            let mut results = vec![SnapResult5D::default(); points.len()];
            snap_eisenstein_batch(c_points.as_ptr(), results.as_mut_ptr(), points.len());
            results.into_iter().map(SnapResult::from).collect()
        }
    }
}
```

**Expected gain:** 1000 FFI calls → 1 FFI call = ~40μs → ~40ns for boundary overhead.

### 20.3 — AVX-512 Snap Kernel

The A₂ Voronoï snap reduces to: find the nearest of 9 candidate Eisenstein integers. This is a distance comparison — pure arithmetic, no branches in the hot path.

```c
// AVX-512 implementation: process 8 points per zmm register pair

#include <immintrin.h>

void snap_eisenstein_avx512(
    const double* xs,      // 8 x values
    const double* ys,      // 8 y values
    int32_t* a_out,        // 8 results
    int32_t* b_out,
    size_t n               // must be multiple of 8
) {
    // Precompute the 9 candidate offsets as zmm constants
    // For each of 9 candidates: compute distance, track minimum
    // No scalar fallback needed — all 9 candidates are uniform memory access

    __m512d zmm_x = _mm512_load_pd(xs);
    __m512d zmm_y = _mm512_load_pd(ys);

    // ... 9-way min reduction using _mm512_min_pd
    // ... extract integer parts with _mm512_cvtpd_epi32
}
```

**Architecture note:** AVX-512 is guarded behind a runtime CPUID check. The binary ships with three code paths:
1. **avx512f** — 8 doubles/cycle, target 200M snaps/sec
2. **avx2** — 4 doubles/cycle, target 100M snaps/sec
3. **scalar** — fallback, current 26M snaps/sec

Runtime dispatch via function pointer table initialized at library load:

```c
static SnapFn* snap_fn = NULL;

void __attribute__((constructor)) init_snap_dispatch(void) {
    if (__builtin_cpu_supports("avx512f")) {
        snap_fn = snap_eisenstein_avx512;
    } else if (__builtin_cpu_supports("avx2")) {
        snap_fn = snap_eisenstein_avx2;
    } else {
        snap_fn = snap_eisenstein_scalar;
    }
}
```

### 20.4 — Constraint Check SIMD Optimization

Current: `constraint_check` on 500 tiles / 13,500 edges takes 2.1ms (472 ops/sec at tiling level).

The inner loop is an L1 norm over border strips. Each border strip is 5 float values (one column of a 5×5 tile tensor). The operation: `sum |A_border[i] - B_border[i]|` over 5 elements.

With AVX-512 this fits in a single zmm register (16 floats). Process 3 edge pairs per zmm instruction:

```c
// Process 3 constraint edges at once with AVX-512
// border_a[0..5], border_a[5..10], border_a[10..15] packed into zmm
// border_b similarly packed
// _mm512_abs_ps(_mm512_sub_ps(a, b)) + horizontal sum
```

**Target:** 13,500 edges in <100μs (from current 2.1ms) = 20× speedup.

### 20.5 — Tensor Fill SIMD Optimization

The five filling modes (constant, gradient, sinusoidal, seed, phase) are currently scalar loops. With SIMD:

- **Constant:** `_mm512_set1_ps(a / a_max)` + `_mm512_storeu_ps` — trivial
- **Gradient:** precompute index vector `[0,1,2,...,15]`, FMA with slope
- **Sinusoidal:** use SVML `_mm512_sin_ps` if available, else polynomial approx
- **Phase:** combine sinusoidal with phase offset — one extra FMA

New function in C bridge:

```c
void fill_tile_avx512(
    float* tensor,         // output: m×n float32 array
    int32_t a, int32_t b, int32_t c, int32_t d, int32_t e,
    int m, int n           // tensor dimensions
);
```

### 20.6 — LatticeBackend Trait Extension

Extend the Rust trait to expose batch methods:

```rust
pub trait LatticeBackend {
    // Existing single-point methods (retained for compatibility)
    fn snap(&self, x: f64, y: f64) -> SnapResult;
    fn project(&self, source: &[i32]) -> ProjectionResult;
    fn lift(&self, x: f64, y: f64) -> Vec<i32>;
    fn classify(&self, source: &[i32]) -> TileType;

    // NEW: batch methods (default impl calls single-point in loop)
    fn snap_batch(&self, points: &[(f64, f64)]) -> Vec<SnapResult> {
        points.iter().map(|&(x, y)| self.snap(x, y)).collect()
    }

    fn fill_batch(&self, sources: &[[i32; 5]], tensors: &mut [Vec<f32>]) {
        for (src, tensor) in sources.iter().zip(tensors.iter_mut()) {
            self.fill_tensor(src, tensor);
        }
    }
}
```

The Eisenstein backend overrides `snap_batch` and `fill_batch` with the AVX-512 paths. Other backends get the default scalar fallback.

### 20.7 — Benchmark Targets

| Operation | Phase 18 | Phase 20 Target | Method |
|-----------|----------|-----------------|--------|
| Snap (single) | 26M/sec | 200M/sec | AVX-512 batch |
| Snap (batch 1000) | ~26M/sec | 250M/sec | single FFI + SIMD |
| Constraint check | 472 tiling/sec | 5K+ tiling/sec | border SIMD |
| Tile fill | ~8M/sec | 80M/sec | fill_tile_avx512 |
| Python tiling.apply() | ~38K/sec | 500K/sec | batch + SIMD |

These are the HN headline numbers.

### 20.8 — Phase 20 Acceptance Criteria

- [ ] `snap_eisenstein_batch()` in C bridge, single FFI call for N points
- [ ] Runtime CPUID dispatch: avx512 / avx2 / scalar paths
- [ ] `LatticeBackend::snap_batch()` default + eisenstein override
- [ ] Constraint check 10× faster than Phase 18 baseline
- [ ] All 17 existing tests still pass
- [ ] New benchmark suite: `cargo bench` shows targets met
- [ ] `pt bench` CLI output shows Phase 20 numbers

---

## Phase 21 — HN Demo, PLATO Integration, Launch (Weeks 7–9)

### Goal
Ship. HN post gets 500+ points. PLATO users can constraint-check their tilings. `pip install tensor-penrose` is the call-to-action.

### 21.1 — The HN Demo

The demo must be **runnable in 30 seconds** by a skeptical engineer on any machine.

**Primary demo: safety constraint verification on ML weights**

```python
# demo.py — the HN demo
import torch
import tensor_penrose as pt
import numpy as np

# 1. Pretend we trained a model
weights = torch.randn(1000, 5)  # 1000 weight vectors, 5D projected

# 2. Embed into Penrose tiling
tiling = pt.from_torch(weights, backend="eisenstein")
tiling.fill()

# 3. Apply constraints: no weight should exceed 2σ from its neighbors
# (This is a toy safety constraint — replace with real safety specs)
tiling.apply(pt.kernels.normalize("l2"))
violations = tiling.constraint_check(metric="l1")

# 4. Show the numbers
print(f"Tiles:       {len(tiling)}")
print(f"Edges:       {tiling.edge_count()}")
print(f"Violations:  {sum(v > 0.1 for v in violations.values())}")
print(f"Max mismatch:{max(violations.values()):.4f}")
print(f"Throughput:  {tiling.last_bench_ns():.1f} ns/constraint")

# 5. Visualize (outputs demo.svg)
tiling.visualize("demo.svg", highlight_violations=True)
```

**`tiling.visualize()`** is the Phase 21 addition: SVG output showing the Penrose tiling with tiles colored by constraint violation severity. This is the image that gets embedded in the HN post.

### 21.2 — Visualization Module

New module: `tensor-penrose/src/python/visualize.py`

Strategy: pure Python SVG generation, no matplotlib dependency. Each tile is a rhombus polygon. Color encodes violation level (green → yellow → red). Adjacency edges are drawn in gray.

```python
def visualize(tiling, output_path, highlight_violations=False, scale=20.0):
    """Generate SVG of the Penrose tiling with optional constraint highlighting."""
    # Compute bounding box
    # For each tile: compute 4 rhombus vertices from position + orientation + type
    # Color: green (no violation) → red (max violation)
    # Write SVG polygons
```

This SVG becomes the demo image on HN. It must be beautiful. A 1000-tile Penrose tiling with constraint violations glowing red on a dark background is the screenshot that sells the project.

### 21.3 — PLATO Integration

PLATO (`plato-engine`, `plato-client`, `plato-tiles`) is the existing constraint-solving infrastructure. The integration path: tensor-penrose becomes a **verification backend** for PLATO constraint problems.

**Architecture:**

```
PLATO problem definition
        │
        ▼
plato-tiles: extract tile coordinates + constraints
        │
        ▼
tensor-penrose: verify constraint satisfaction
        │
        ▼
violation report → PLATO solver feedback loop
```

**New crate: `plato-penrose-bridge`** (in workspace, not published yet)

```rust
// plato-penrose-bridge/src/lib.rs

pub fn plato_problem_to_tiling(
    problem: &plato_engine::Problem,
) -> tensor_penrose::PTiling {
    // Extract tile coordinates from PLATO's internal representation
    // Map PLATO constraint edges to tensor-penrose adjacency pairs
    // Return a PTiling ready for constraint_check()
}

pub fn violation_report_to_plato(
    violations: HashMap<String, f32>,
    problem: &plato_engine::Problem,
) -> plato_engine::ViolationReport {
    // Map tensor-penrose violation scores back to PLATO variable names
}
```

**Python-side integration:**

```python
import tensor_penrose as pt
from plato_client import Problem

problem = Problem.load("my_constraint_problem.plato")
tiling = pt.from_plato(problem)
violations = tiling.constraint_check()
print(pt.violations_to_plato(violations, problem))
```

`pt.from_plato()` and `pt.violations_to_plato()` are added to the Python package as optional imports (require `plato-client` installed).

### 21.4 — Fortran / snapkit-fortran Integration

`snapkit-fortran` provides `eisenstein_snap_batch` with Fortran's column-major memory layout and coarray parallelism. This is the HPC path for PLATO when running on multi-node clusters.

**Integration strategy:** `snapkit-fortran` calls into tensor-penrose's C API (not the Python API, not the Rust API). The C bridge is the lingua franca.

New exported C symbols in `fleet-math-c`:

```c
// Callable from Fortran via ISO_C_BINDING
void tensor_penrose_snap_batch_c(
    const double* xs,
    const double* ys,
    int32_t* results_a,
    int32_t* results_b,
    int32_t* results_c,
    int32_t* results_d,
    int32_t* results_e,
    int* n
) BIND(C, NAME="tensor_penrose_snap_batch_c");
```

Fortran binding in `snapkit-fortran/src/tensor_penrose_bridge.f90`:

```fortran
module tensor_penrose_bridge
  use iso_c_binding
  implicit none

  interface
    subroutine tp_snap_batch(xs, ys, ra, rb, rc, rd, re, n) &
        bind(C, name="tensor_penrose_snap_batch_c")
      import
      real(c_double), intent(in)  :: xs(*), ys(*)
      integer(c_int32_t), intent(out) :: ra(*), rb(*), rc(*), rd(*), re(*)
      integer(c_int), intent(in)  :: n
    end subroutine
  end interface

end module tensor_penrose_bridge
```

This gives PLATO/Fortran users access to tensor-penrose's AVX-512 snap engine without touching Python or Rust. Column-major arrays map directly to the C bridge's row layout via the `n` parameter.

**Coarray parallel path (Phase 21 stretch goal):**

```fortran
! On N images (coarray processes), each handles a partition of the tiling
program parallel_constraint_check
  use tensor_penrose_bridge
  implicit none

  integer :: my_tiles[*]   ! coarray: each image owns a slice
  ! ... snap local partition, exchange border tiles via coarray communication
  ! ... aggregate violations on image 1
end program
```

This is the path to fleet-scale constraint verification — PLATO running on 64 nodes, each verifying a partition of the tensor-penrose tiling in parallel.

### 21.5 — HN Launch Checklist

**Content:**
- [ ] `README.md` rewritten: "Like PyTorch, but the tensors come with positions"
- [ ] 3 benchmarks prominently displayed: snap, fill, constraint_check
- [ ] Demo GIF/SVG: Penrose tiling with violations highlighted
- [ ] Jupyter notebook: `examples/quickstart.ipynb`
- [ ] Comparison table: tensor-penrose vs scipy.optimize vs hand-rolled

**Distribution:**
- [ ] `pip install tensor-penrose` works on PyPI
- [ ] `cargo add tensor-penrose` works on crates.io
- [ ] Wheels built for linux/mac/windows (maturin CI)
- [ ] Python 3.10–3.12 tested

**HN post structure:**
```
Title: "tensor-penrose: constraint tensors on Penrose tilings, 200M checks/sec"

Body:
- One-line pitch: PyTorch for constraint verification, not gradient descent
- The numbers (200M snaps/sec, constraint_check throughput)
- The SVG (the beautiful aperiodic tiling image)
- The use case: embed ML weights, check safety constraints, get violations
- The PyPI install command
- Link to GitHub
```

**Timing:** Post on Tuesday or Wednesday morning US time. Avoid Mondays (busy) and Fridays (low traffic). Target 9am ET.

### 21.6 — crates.io Publish Sequence

1. `fleet-math-c` — C bridge with batch API and AVX-512 (no Rust deps)
2. `penrose-memory` — TensorTile + cut-and-project (depends on fleet-math-c)
3. `tensor-penrose` — main Rust crate (depends on both)
4. `tensor-penrose-py` — Python wheel (built via maturin, not crates.io)

Version: `0.1.0` for HN launch. Semantic versioning from there.

### 21.7 — Phase 21 Acceptance Criteria

- [ ] `tiling.visualize()` produces valid SVG for 1000+ tiles
- [ ] `pt.from_plato()` bridge compiles and round-trips a PLATO test problem
- [ ] Fortran C-binding compiles with `gfortran` and passes `make test`
- [ ] `pip install tensor-penrose` works from PyPI (test with fresh venv)
- [ ] HN demo script (`demo.py`) runs in <5 seconds on commodity hardware
- [ ] README has benchmark numbers and SVG image embedded
- [ ] HN post drafted and reviewed

---

## Cross-Phase Architecture Decisions

### Memory Layout Strategy

All tile tensors are stored as `Vec<f32>` in row-major order within each `PTile`. The `PTiling` stores tiles contiguously in a `Vec<PTile>`. This means tile tensors are **not contiguous across tiles** by default.

For Phase 20 SIMD optimization, add a **batch tensor buffer** option:

```rust
pub struct PTiling {
    tiles: Vec<PTile>,
    // Optional: flat buffer for SIMD ops across all tiles
    tensor_buffer: Option<Vec<f32>>,  // N × H × W, contiguous
    buffer_dirty: bool,
}
```

When `tensor_buffer` is `Some`, SIMD ops run on the flat buffer. After mutation, `buffer_dirty = true` until `sync_tiles()` is called. This is the PyTorch-style "view vs copy" tradeoff — opt in when performance matters.

### Error Handling Philosophy

Keep the `?` propagation chain. No panics in library code. Python exceptions are raised via PyO3's `PyErr` when Rust returns `Err(...)`. The Python user sees clean exceptions, not cryptic process exits.

### Feature Flag Matrix

| Feature | Default | Enables |
|---------|---------|---------|
| `eisenstein-backend` | ✅ | A₂ Eisenstein lattice |
| `penrose-backend` | ✅ | 5D→2D Penrose projection |
| `python` | ❌ | PyO3 bindings |
| `avx512` | ❌ (runtime detect) | AVX-512 SIMD paths |
| `plato` | ❌ | plato-penrose-bridge |
| `cli` | ❌ | `pt` binary |

The `avx512` feature flag controls **compile-time availability** of AVX-512 code. Runtime CPUID dispatch remains regardless — the flag just gates whether the AVX-512 variant is compiled in.

### WASM Consideration

The HN demo should optionally run in the browser. A WASM build of the core (no AVX-512, no FFI) via `wasm-bindgen` would allow a live demo directly in the post. This is a Phase 21 stretch goal:

- Gate all FFI behind `#[cfg(not(target_arch = "wasm32"))]`
- Expose `wasm_bindgen` bindings alongside PyO3
- Host at `tensor-penrose.io/demo` — interactive tiling with real-time constraint checking

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| AVX-512 not available on CI | Medium | Medium | Runtime dispatch; CI uses scalar path for correctness, benchmark on dedicated AVX-512 box |
| maturin wheel build failures on Windows | Medium | Low | Linux/mac wheels sufficient for HN launch; Windows follows |
| PLATO API incompatibility | Low | Medium | Bridge is a new crate; PLATO internal API change doesn't block tensor-penrose core |
| PyO3 version churn (0.21→0.22) | Low | Low | Pin to 0.22 in Cargo.toml |
| HN post lands wrong day | Low | Low | Draft ready; post timing is controllable |

---

## Timeline Summary

```
Week 1-2:  PyO3 bindings — PyTile, PyTiling, NumPy bridge
Week 3:    maturin build, pip install, PyTorch bridge, Jupyter notebook
Week 4-5:  C bridge batch API, AVX-512 snap kernel, runtime dispatch
Week 6:    Constraint check SIMD, fill SIMD, benchmark validation
Week 7:    visualize() SVG output, demo.py, README rewrite
Week 8:    PLATO bridge, Fortran C-binding, plato-penrose-bridge crate
Week 9:    PyPI publish, crates.io publish, HN post
```

---

## The One Number That Matters

**200M constraint checks per second** from a `pip install` on commodity hardware.

That number — arrived at through the C batch API, the AVX-512 snap kernel, the contiguous tensor buffer, and the border SIMD fusion — is the number that makes the HN post land. Everything in Phase 19–21 serves that number.

The math: 26M snaps/sec (baseline) × 8 (AVX-512 width) × ~1.0 (batch FFI removes crossing overhead) = ~200M/sec. It is achievable. It is honest. It is the headline.

---

*The tiles are tensors. The tensors are vectorizable. The application gets to choose.*
