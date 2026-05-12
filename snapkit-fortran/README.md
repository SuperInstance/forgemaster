# snapkit-fortran ⚒️

Fortran 2008 port of the [snapkit](https://github.com/SuperInstance/snapkit-v2) constraint geometry snap toolkit — Eisenstein integer snap, Voronoï cells, spectral analysis, and temporal beat grid quantization.

## Why Fortran?

| Feature | Python | Fortran |
|---------|--------|---------|
| **Batch snap** | `for` loop, vectorized via NumPy | Whole-array ops, column-major layout |
| **Parallelism** | multiprocessing | Pure/elemental procedures → auto-parallel |
| **BLAS/LAPACK** | `scipy.linalg` wrapper | Native interop, zero-copy |
| **Memory layout** | Row-major (C-contiguous) | Column-major — different cache optimization |
| **Distribution** | Single-node | Coarrays for fleet-wide parallel execution |
| **Latency** | ~10μs per snap | ~100ns per snap (estimated) |

## Build

```bash
make          # builds lib/libsnapkit.a + test binaries
make test     # runs all tests
make clean    # remove build artifacts
```

Requires `gfortran` (tested with GNU Fortran 11.4).

## Modules

### `snapkit_eisenstein` — Eisenstein Integer Snap
- `eisenstein_round(x, y)` — Voronoï 9-candidate snap (fast path)
- `eisenstein_round_naive(x, y)` — 4-candidate round (comparison)
- `eisenstein_snap(x, y, tolerance)` — snap with tolerance check
- `eisenstein_snap_batch(x, y, tol, results)` — vectorized batch snap
- `eisenstein_distance(x1, y1, x2, y2)` — lattice distance
- `eisenstein_fundamental_domain(x, y, unit, reduced)` — FD reduction
- Arithmetic: `eisenstein_add`, `eisenstein_sub`, `eisenstein_mul`
- `eisenstein_conjugate`, `eisenstein_norm_sq`, `eisenstein_units`

### `snapkit_voronoi` — Voronoï Cell Geometry
- `covering_radius()` — A₂ lattice covering radius (1/√3)
- `voronoi_cell_vertices(vx, vy)` — regular hexagon vertices
- `voronoi_cell_area()` — cell area (√3/2)

### `snapkit_spectral` — Spectral Analysis
- `entropy(data, bins)` — Shannon entropy via histogram (bits)
- `autocorrelation(data, max_lag)` — normalized ACF
- `hurst_exponent(data)` — R/S analysis
- `spectral_summary(data)` — full summary (entropy, Hurst, ACF, stationarity)
- `spectral_batch(data_2d, results)` — column-wise batch (column-major layout)

### `snapkit_temporal` — Beat Grid & Temporal Snap
- `temporal_snap(time, grid, tolerance)` — snap timestamp to grid
- `temporal_snap_batch(times, grid, tol, results)` — batch temporal snap
- `quantize_to_grid(times, grid, ticks, snapped)` — hard quantize
- `detect_swing(intervals)` — swing ratio from inter-onset intervals

## Architecture

```
snapkit-fortran/
├── src/
│   ├── eisenstein.f90    # Eisenstein snap + arithmetic
│   ├── voronoi.f90       # A₂ Voronoï geometry
│   ├── spectral.f90      # Entropy, Hurst, autocorrelation
│   └── temporal.f90      # Beat grid, temporal snap
├── tests/
│   ├── test_eisenstein.f90
│   └── test_spectral.f90
├── lib/                  # built: libsnapkit.a + .mod files
├── bin/                  # built: test executables
├── Makefile
└── README.md
```

## Usage Example

```fortran
program demo
    use snapkit_eisenstein
    use snapkit_spectral
    use snapkit_temporal
    implicit none

    type(eisenstein_int) :: e
    type(beat_grid) :: bg
    type(temporal_result) :: tr

    ! Snap a point to the Eisenstein lattice
    e = eisenstein_round(0.7d0, 0.4d0)
    print *, 'Snapped to:', e%a, e%b

    ! Temporal snap to 120 BPM, 16th notes
    bg = new_beat_grid(120.0d0, 4.0d0)
    tr = temporal_snap(1.137d0, bg, 0.01d0)
    print *, 'On grid:', tr%is_on_grid, 'Offset:', tr%offset

end program demo
```

## Key Fortran Advantages

1. **Array syntax** — batch operations use whole-array expressions, no explicit loops
2. **Pure/elemental** — compiler can auto-parallelize and vectorize
3. **BLAS/LAPACK interop** — spectral analysis ready for native LAPACK routines
4. **Column-major** — cache-friendly for column-wise batch operations
5. **Coarrays** — parallel execution across fleet nodes (future: `snapkit[*]`)

## License

Part of the SuperInstance constraint theory ecosystem.
