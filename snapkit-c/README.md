# snapkit-c

Plug-and-play C library for **Eisenstein lattice snapping**, **temporal beat grids**, and **spectral analysis** — designed for embedded systems, bare-metal, and WebAssembly targets.

## Features

- **C99 compatible** — works on ARM Cortex-M, ESP32, Jetson, x86, WASM
- **Zero dependencies** — no malloc; caller provides all buffers
- **Single header option** — `#define SNAPKIT_IMPLEMENTATION` (stb-style)
- **Covering radius ≤ 1/√3** guaranteed for Eisenstein snap
- **Batch operations** for all modules
- **Three modules**: Eisenstein lattice, temporal beat grids, spectral analysis

## Quick Start

### Single-header mode

```c
#define SNAPKIT_IMPLEMENTATION
#include "snapkit.h"

// Done — all functions are now defined.
```

### Linked library mode

```bash
make          # builds libsnapkit.a and libsnapkit.so
make test     # builds and runs tests
make install  # installs to /usr/local (override with PREFIX=)
```

Or with CMake:

```bash
mkdir build && cd build
cmake .. && make
ctest
```

## API Reference

### Eisenstein Snap

```c
// Snap to nearest Eisenstein integer (Voronoi — exact nearest neighbor)
sk_eisenstein e = sk_eisenstein_snap_voronoi(x, y);

// Snap with tolerance check
sk_snap_result r = sk_eisenstein_snap(x, y, tolerance);
if (r.is_snap) { /* point is within tolerance of a lattice point */ }

// Batch snap
sk_eisenstein out[n];
sk_eisenstein_snap_batch(x_array, y_array, n, out);
```

### Temporal

```c
// Create a beat grid (period=1.0, phase=0.0, start=0.0)
sk_beat_grid grid;
sk_beat_grid_init(&grid, 1.0, 0.0, 0.0);

// Snap a timestamp
sk_temporal_result r = sk_beat_grid_snap(&grid, t, tolerance);

// T-minus-0 detection
sk_temporal_snap ts;
sk_temporal_snap_init(&ts, &grid, 0.1, 0.05, 3);
sk_temporal_result r = sk_temporal_observe(&ts, t, value);
if (r.is_t_minus_0) { /* zero crossing detected! */ }
```

### Spectral

```c
// Entropy
double h = sk_entropy(data, n, 10);  // 10 bins

// Autocorrelation (caller provides buffer)
double acf[max_lag + 1];
int len = sk_autocorrelation(data, n, max_lag, acf);

// Hurst exponent (R/S analysis)
double hurst = sk_hurst_exponent(data, n);

// Full spectral summary (caller provides scratch buffers)
sk_spectral_summary s = sk_spectral_analyze(data, n, bins, max_lag, acf_buf, counts_buf);
```

## Data Structures

| Type | Description |
|------|-------------|
| `sk_eisenstein` | `{int a, b}` — Eisenstein integer a + bω |
| `sk_snap_result` | Snap result with distance and is_snap flag |
| `sk_beat_grid` | Periodic beat grid |
| `sk_temporal_result` | Temporal snap result with beat info |
| `sk_temporal_snap` | T-minus-0 detector with circular buffer |
| `sk_spectral_summary` | Entropy, Hurst, autocorrelation, stationarity |

## Build Targets

| Target | Status |
|--------|--------|
| x86-64 (Linux/macOS/Windows) | ✅ Tested |
| ARM Cortex-M | ✅ C99, no OS dependencies |
| ESP32 (Xtensa) | ✅ C99 compatible |
| WebAssembly (Emscripten) | ✅ No OS calls |
| Jetson (ARM64) | ✅ Standard C |

## License

MIT
