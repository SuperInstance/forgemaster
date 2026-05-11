# SnapKit C ⚒️ — Tolerance-Compressed Attention Allocation

**Everything within tolerance is compressed away. Only the deltas survive.**

SnapKit C is a high-performance, portable C11 library implementing **Snaps as Attention** theory — a mathematical framework for allocating finite cognitive resources using tolerance-compressed snap functions over ADE-classified lattices.

## Features

- **Eisenstein Lattice Snap (A₂)** — Optimal branchless O(1) nearest-point algorithm using Conway-Sloane (1982) Voronoi boundary conditions
- **ADE Topology Support** — A₁ binary, A₂ hexagonal, A₃ octahedral, D₄ triality, E₆/E₇/E₈ exceptional
- **Delta Detection** — Multi-stream delta monitoring with per-stream tolerance
- **Attention Budget** — Finite cognition allocation (actionability-weighted, reactive, uniform)
- **Script Library** — Pattern matching with cosine similarity
- **Constraint Sheaf** — Cohomological consistency checking
- **SIMD Paths** — NEON (ARM) and SSE (x86) acceleration where available
- **Header-only mode** — `#define SNAPKIT_HEADER_ONLY 1` before including `snapkit.h`
- **No dynamic allocation in hot path** — All core operations use stack allocation

## Performance

| Operation | Ops | Branching | SIMD |
|-----------|-----|-----------|------|
| Eisenstein snap (scalar) | ~15-20 FLOPs | Branchless (cmov) | — |
| Eisenstein snap (NEON) | 2× throughput | Branchless | float64x2_t |
| Batch snap | O(N) | Fully parallel | Yes |

The optimal Eisenstein snap uses the exact 6-condition Voronoi test from Conway & Sloane (1982), not the naive 3×3=9 candidate search — **5× faster with zero distance computations in the correction path**.

## Build

### Requirements
- C11 compiler (GCC, Clang, MSVC, or compatible)
- CMake (optional, for `find_package` integration)
- make

### Quick Start

```bash
make              # Build static library
make test         # Build and run tests
make benchmark    # Build and run benchmarks
make examples     # Build example programs
make shared       # Build shared library
```

### Install

```bash
make install              # Install to /usr/local
make install PREFIX=~/.local  # Install to user prefix
```

### Cross-compilation

```bash
make CROSS_COMPILE=arm-none-eabi- CC=arm-none-eabi-gcc AR=arm-none-eabi-ar
```

### Debug Build

```bash
make DEBUG=1     # -O0 -g -fsanitize=address
```

## API Overview

```c
#include "snapkit/snapkit.h"

// Create a snap configuration
snapkit_config_t config = snapkit_default_config();
config.tolerance = 0.1;
config.topology = SNAPKIT_TOPOLOGY_HEXAGONAL;

// Snap a value
snapkit_result_t result = snapkit_snap(&config, 0.05);
if (result.within_tolerance) {
    printf("Value snapped. Delta=%f\n", result.delta);
}

// Optimal Eisenstein lattice snap (A₂)
int a, b;
double snapped_re, snapped_im, dist;
snapkit_nearest_eisenstein_optimal(1.2, 0.7, &a, &b, &snapped_re, &snapped_im, &dist);
printf("Eisenstein: (%d, %d), distance=%f\n", a, b, dist);

// Batch snap
double reals[] = {0.1, 0.5, 1.2, 2.0};
double imags[] = {0.2, 0.8, 0.7, 0.0};
int a_out[4], b_out[4];
double dist_out[4];
snapkit_nearest_eisenstein_optimal_neon(NULL /* fallback to scalar */);
// Use batch scalar fallback
for (int i = 0; i < 4; i++) {
    snapkit_nearest_eisenstein_optimal(reals[i], imags[i], &a_out[i], &b_out[i], 
                                       &snapped_re, &snapped_im, &dist_out[i]);
}

// Delta detection
snapkit_delta_t deltas[16];
int n_deltas = 0;
snapkit_observe(&config, 0.3, deltas, &n_deltas);

// Attention budget
snapkit_budget_t budget = snapkit_budget_create(100.0, SNAPKIT_STRATEGY_ACTIONABILITY);
snapkit_allocate(&budget, deltas, n_deltas);
printf("Remaining budget: %f\n", budget.remaining);
```

## API Reference

See the header file `include/snapkit/snapkit.h` for complete API documentation.

| Function | Description |
|----------|-------------|
| `snapkit_snap()` | Core snap — test a value against tolerance |
| `snapkit_snap_batch()` | Snap multiple values efficiently |
| `snapkit_calibrate()` | Auto-tune tolerance from historical data |
| `snapkit_nearest_eisenstein_optimal()` | A₂ nearest point (branchless, O(1)) |
| `snapkit_nearest_eisenstein_norm()` | Lightweight variant (no sqrt) |
| `snapkit_nearest_eisenstein_optimal_neon()` | NEON-accelerated batch A₂ snap |
| `snapkit_delta_create()` | Create delta detector instance |
| `snapkit_delta_observe()` | Process new observation, check for deltas |
| `snapkit_budget_create()` | Create attention budget |
| `snapkit_budget_allocate()` | Allocate attention to deltas |
| `snapkit_script_library_create()` | Create script library |
| `snapkit_script_match()` | Match input against known scripts |
| `snapkit_script_learn()` | Learn a new script from example |
| `snapkit_constraint_sheaf_create()` | Create constraint sheaf |
| `snapkit_sheaf_verify()` | Verify consistency of constraints |
| `snapkit_ade_data()` | Get ADE classification data |

## Benchmarks

```bash
make benchmark
```

Expected results (single-threaded, GCC -O3 -march=native):
- Eisenstein scalar snap: ~50M snaps/sec per core
- Eisenstein NEON batch: ~80M snaps/sec per core
- Delta threshold: ~100M/sec
- Eisenstein norm-only (no sqrt): ~80M snaps/sec

## Project Structure

```
snapkit-c/
├── Makefile                  — Build system
├── README.md                 — This file
├── LICENSE                   — MIT License
├── include/snapkit/          — Public headers
│   ├── snapkit.h             — Master header (full API)
│   └── snapkit_internal.h    — Internal constants & helpers
├── src/                      — Implementation
│   ├── core_ade.c            — ADE topology data
│   ├── core_eisenstein.c     — Eisenstein lattice (baseline)
│   ├── core_eisenstein_optimal.c — Optimal branchless A₂ snap
│   ├── core_snap.c           — SnapFunction core
│   └── core_delta.c          — Delta detection
├── tests/                    — Test suite + benchmarks
│   ├── test_snapkit.c        — 25+ unit tests
│   └── bench_snapkit.c       — Performance benchmarks
├── examples/                 — Example programs
│   ├── example_eisenstein.c  — Eisenstein snap demo
│   └── example_delta.c       — Delta detection demo
└── docs/
    └── doxygen/              — Generated documentation
```

## Integration

### pkg-config

```bash
pkg-config --cflags --libs snapkit
```

### CMake

```cmake
find_package(snapkit REQUIRED)
target_link_libraries(my_app snapkit::snapkit)
```

## License

MIT — use freely, give credit.

---

*Built for the Cocapn fleet. The optimal Eisenstein snap implementation reduces a 3×3=9 candidate search to 15 FLOPs with zero branch divergence.*

*"The snap is the gatekeeper of attention. The delta is the compass. The lattice is the infrastructure."*
