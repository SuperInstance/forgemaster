# snapkit-zig ⚒️

Constraint geometry snap toolkit — Zig port.

Eisenstein integer lattice snapping, temporal beat grids, T-minus-0 detection, and spectral analysis. Zero dependencies. Compile-time constraint checking. Cross-compilation out of the box.

## Why Zig?

| Feature | Python | C | Zig |
|---|---|---|---|
| comptime constraint checking | ❌ | ❌ macros | ✅ full comptime evaluation |
| Cross-compilation | ❌ | toolchain hell | ✅ `zig build -Dtarget=...` |
| SIMD batch operations | numpy | manual intrinsics | ✅ `@Vector` built-in |
| Hidden control flow | exceptions everywhere | setjmp/macros | ✅ explicit error unions |
| C interop | ctypes/cffi | native | ✅ `export fn` + `@cImport` |
| No hidden allocations | GC | malloc everywhere | ✅ allocator-free by default |

## Installation

```bash
git clone https://github.com/SuperInstance/snapkit-zig.git
cd snapkit-zig
zig build test        # run all tests
zig build install     # build static + shared libs
```

## Cross-Compilation

```bash
zig build arm64          # aarch64-linux
zig build wasm           # wasm32-freestanding
zig build x86-windows    # x86_64-windows
# Or any target:
zig build install -Dtarget=aarch64-macos
```

## Quickstart

```zig
const snapkit = @import("snapkit-zig");

// Snap a point to the nearest Eisenstein lattice point
const nearest = snapkit.eisenstein.snapVoronoi(1.37, 0.82);
// nearest.a = 2, nearest.b = 1

// Snap with tolerance
const result = snapkit.eisenstein.snap(1.37, 0.82, 0.5);
// result.distance ≈ 0.21, result.is_snap = true

// Compile-time snap — evaluated entirely during compilation
const ct = snapkit.eisenstein.comptimeSnap(0.7, 0.3);
// ct is a comptime constant! No runtime cost.

// Compile-time lattice verification
const verified = snapkit.eisenstein.comptimeAssertLatticePoint(1.0, 0.0);
// This compiles. But try passing (0.5, 0.5) — compile error!

// Temporal snap
const grid = try snapkit.temporal.beatGridInit(1.0, 0.0, 0.0);
const ts = snapkit.temporal.beatGridSnap(&grid, 2.05, 0.1);
// ts.is_on_beat = true, ts.snapped_time = 2.0

// Spectral analysis (caller provides scratch buffers)
var acf_buf: [25]f64 = undefined;
var counts: [10]usize = undefined;
var data: [100]f64 = undefined;
// ... fill data ...
const summary = snapkit.spectral.spectralSummary(&data, 10, 12, &acf_buf, &counts);
// summary.hurst, summary.entropy_bits, summary.is_stationary
```

## API

### `eisenstein.zig` — Eisenstein Integer Operations

| Function | Description |
|---|---|
| `snapNaive(x, y)` | 4-candidate naive snap |
| `snapVoronoi(x, y)` | 9-candidate exact snap (≤ 1/√3) |
| `snap(x, y, tolerance)` | Snap with tolerance check |
| `eisensteinDistance(x1, y1, x2, y2)` | Eisenstein lattice distance |
| `snapBatch(x, y, out)` | Scalar batch snap |
| `snapBatchSimd(x, y, out)` | SIMD `@Vector(4, f64)` batch snap |
| `snapBatchFull(x, y, tol, out)` | Batch snap with `SnapResult` |
| `comptimeSnap(x, y)` | **Compile-time** nearest Eisenstein integer |
| `comptimeAssertLatticePoint(x, y)` | **Compile-time** lattice point verification |

### `temporal.zig` — Beat Grids & T-minus-0

| Function | Description |
|---|---|
| `beatGridInit(period, phase, t_start)` | Create a beat grid |
| `beatGridSnap(grid, t, tolerance)` | Snap timestamp to grid |
| `beatGridSnapBatch(grid, ts, tol, out)` | Batch temporal snap |
| `beatGridRange(grid, t0, t1, out)` | Enumerate beats in range |
| `TemporalSnap.init(grid, tol, t0_thresh, win)` | T-minus-0 detector |
| `temporal_snap.observe(t, value)` | Observe + detect zero-crossing |

### `spectral.zig` — Spectral Analysis

| Function | Description |
|---|---|
| `entropy(data, bins, counts)` | Shannon entropy via histogram |
| `autocorrelation(data, max_lag, out)` | Normalized autocorrelation |
| `hurstExponent(data)` | Hurst exponent via R/S analysis |
| `spectralSummary(data, bins, lag, acf, cnt)` | Full spectral summary |

### `voronoi.zig` — Covering Radius

| Function | Description |
|---|---|
| `verifyCoveringRadius(x, y)` | Check distance ≤ 1/√3 |
| `verifyCoveringRadiusGrid(...)` | Exhaustive grid verification |
| `snapBatchVerified(x, y, out, tol)` | Batch snap with debug assertions |

## C Interop

The shared library exports C-compatible functions:

```c
#include <snapkit-zig.h>  // Zig module as header

// Or just declare the functions you need:
extern sk_eisenstein sk_eisenstein_snap_voronoi(double x, double y);
extern sk_snap_result sk_eisenstein_snap(double x, double y, double tolerance);
extern int sk_beat_grid_init(sk_beat_grid *grid, double period, double phase, double t_start);
extern double sk_entropy(const double *data, size_t n, size_t bins);
```

Build: `zig build install` → `zig-out/lib/libsnapkit.so`

## Zig Advantages Demonstrated

### 1. comptime Constraint Checking

The killer feature. Pass a comptime-known value and get compile-time verification:

```zig
// This compiles — (1, 0) is a valid Eisenstein integer
const e1 = snapkit.eisenstein.comptimeAssertLatticePoint(1.0, 0.0);

// This causes a COMPILE ERROR — (0.5, 0.5) is not a lattice point
const e2 = snapkit.eisenstein.comptimeAssertLatticePoint(0.5, 0.5);

// Compile-time snap — zero runtime cost
const nearest = snapkit.eisenstein.comptimeSnap(1.37, 0.82);
```

### 2. Cross-Compilation

Single binary, any target. No toolchain setup needed:

```bash
zig build install -Dtarget=aarch64-linux        # ARM64 Linux
zig build install -Dtarget=wasm32-freestanding   # WebAssembly
zig build install -Dtarget=x86_64-windows        # Windows
zig build install -Dtarget=aarch64-macos         # Apple Silicon
```

### 3. @Vector SIMD

Batch operations use Zig's built-in SIMD vectors — no intrinsics:

```zig
const Vec = @Vector(4, f64);  // 256-bit SIMD
// All 9-candidate distance checks vectorized automatically
snapkit.eisenstein.snapBatchSimd(x_coords, y_coords, &results);
```

### 4. No Hidden Control Flow

All errors are explicit. No exceptions, no hidden returns:

```zig
const grid = snapkit.temporal.beatGridInit(1.0, 0.0, 0.0) catch |err| {
    // err is error.InvalidPeriod — the ONLY possible error
    return;
};
```

### 5. C Exports via `export fn`

Functions are directly callable from C with no wrapper layer:

```zig
export fn sk_eisenstein_snap_voronoi(x: f64, y: f64) EisensteinInteger {
    return snapVoronoi(x, y);
}
```

## Architecture

```
snapkit-zig/
├── build.zig          # Build system with cross-compilation targets
├── src/
│   ├── root.zig       # Main entry, re-exports all modules
│   ├── types.zig      # Shared types (EisensteinInteger, SnapResult, etc.)
│   ├── eisenstein.zig # Eisenstein snap (naive, Voronoï, SIMD, comptime)
│   ├── voronoi.zig    # Covering radius guarantee & verification
│   ├── temporal.zig   # BeatGrid, TemporalSnap, T-minus-0 detection
│   └── spectral.zig   # Entropy, Hurst R/S, autocorrelation
└── README.md
```

## Covering Radius Guarantee

The A₂ lattice (Eisenstein integers) has Voronoï cells that are regular hexagons with circumradius 1/√3 ≈ 0.5774. Every point in the plane is within distance 1/√3 of some lattice point. The 9-candidate Voronoï snap finds this nearest point exactly.

## License

MIT
