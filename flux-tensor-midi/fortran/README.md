# FLUX-Tensor-MIDI — Fortran Backend

Heavy numerical lifting for the FLUX-Tensor-MIDI system: batch spectral analysis,
Hurst exponents, autocorrelation, cross-correlation matrices, and Eisenstein snap operations.

## Architecture

PLATO rooms as musicians with T-0 clocks, Eisenstein snap, and side-channels.
Fortran handles the array-level number crunching for N rooms × M time intervals.

## Modules

| Module | Description |
|--------|-------------|
| `flux_midi_flux` | Tensor-flux: scalar flux from 3D tensors, L2 normalization, power spectrum via DFT |
| `flux_midi_clock` | T-0 clock: harmonic alignment state machine (PRE/TICK/T0/POST/HOLD) |
| `flux_midi_snap` | Eisenstein snap: lattice rounding, integer quantization, lattice radius |
| `flux_midi_room` | PLATO room model: identity vectors, resonance, batch similarity matrix |
| `flux_midi_harmony` | Cross-correlation: N×N harmony matrix, coherence score |
| `flux_midi_spectrum` | **THE KILLER** — batch entropy, Hurst R/S analysis, autocorrelation, spectral centroid/rolloff |
| `flux_midi_batch` | Batch T-0 classification (WHERE clauses), batch Eisenstein snap dispatch |

## Key Features

- **Array operations throughout** — batch N rooms × M intervals
- **`temporal_entropy`** — batch Shannon entropy across N rooms
- **`hurst_exponent`** — R/S analysis with log-log regression
- **`batch_harmony_matrix`** — N×N cross-correlation in array ops
- **`batch_t0_check`** — WHERE clauses for state classification
- **`batch_eisenstein_snap`** — vectorized lattice rounding

## Build

### Using Make (recommended)

```bash
make         # build library + test executables
make test    # build and run all tests
make clean   # clean build artifacts
```

### Using CMake

```bash
mkdir build && cd build
cmake ..
make
make check  # run all tests
```

## Requirements

- Fortran 2008 compiler (gfortran ≥ 7 recommended)
- No external dependencies — intrinsic functions only

## Tests

Four test suites covering all modules:

- `test_flux` — tensor flux, normalization, power spectrum
- `test_clock` — T-0 clock state machine, batch advance/count/sync
- `test_snap` — Eisenstein snap, lattice radius, batch operations
- `test_spectrum` — **comprehensive**: entropy, autocorrelation, Hurst, centroid, rolloff
