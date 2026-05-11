# snapkit-rs

Zero-dependency Eisenstein snap, spectral analysis, temporal grids, and connectome detection — `no_std` compatible.

Port of the Python [snapkit](https://github.com/SuperInstance/snapkit) library to Rust. Designed for embedded/Jetson deployment where `no_std` is required.

## Features

- **Zero dependencies** — no external crates, pure Rust
- **`no_std` compatible** — works on embedded targets
- **Covering radius ≤ 1/√3** guaranteed for Voronoï snap
- **Batch operations** for all modules
- **crates.io-ready** — just needs a publish token

## Modules

| Module | Description |
|--------|-------------|
| `eisenstein` | Eisenstein integer type, naive 4-candidate snap |
| `voronoi` | 9-candidate Voronoï snap with covering radius guarantee |
| `temporal` | Beat grid alignment, T-minus-0 inflection detection |
| `spectral` | Shannon entropy, Hurst R/S exponent, autocorrelation |
| `connectome` | Cross-correlation coupling detection between signals |
| `types` | Shared types (`TemporalResult`, `SpectralSummary`, etc.) |

## Installation

```toml
[dependencies]
snapkit = "0.1"
```

## Quick Start

### Eisenstein Snap

```rust
use snapkit::eisenstein::EisensteinInt;
use snapkit::voronoi::eisenstein_round_voronoi;

// Snap a point to the nearest Eisenstein lattice point
let nearest = eisenstein_round_voronoi(1.3, 0.7);
println!("Snapped to: {}", nearest); // "2+1ω"

// Eisenstein integer arithmetic (exact, no drift)
let a = EisensteinInt::new(3, -2);
let b = EisensteinInt::new(1, 4);
let product = a * b; // Norm is multiplicative!
assert_eq!(product.norm_squared(), a.norm_squared() * b.norm_squared());
```

### Beat Grid (Temporal Snap)

```rust
use snapkit::temporal::BeatGrid;

let grid = BeatGrid::new(1.0, 0.0, 0.0); // period=1s, phase=0, start=0

// Snap timestamps to nearest beat
let result = grid.snap(2.37, 0.1);
if result.is_on_beat {
    println!("On beat {} at t={}", result.beat_index, result.snapped_time);
} else {
    println!("Off beat by {}", result.offset);
}

// List all beats in a range
let beats = grid.beats_in_range(1.5, 4.5);
assert_eq!(beats, vec![2.0, 3.0, 4.0]);
```

### T-Minus-0 Detection

```rust
use snapkit::temporal::{BeatGrid, TemporalSnap};

let grid = BeatGrid::new(1.0, 0.0, 0.0);
let mut detector = TemporalSnap::new(grid, 0.1, 0.1, 3);

// Feed observations
let result = detector.observe(0.0, 0.5);
let result = detector.observe(1.0, 0.02);
let result = detector.observe(2.0, 0.03);

if result.is_t_minus_0 {
    println!("T-minus-0 detected! Inflection point at t={}", result.original_time);
}
```

### Spectral Analysis

```rust
use snapkit::spectral;

let signal: Vec<f64> = (0..200).map(|i| (i as f64 * 0.1).sin()).collect();

// Entropy (bits)
let h = spectral::entropy(&signal, 10);

// Hurst exponent (R/S analysis)
let hurst = spectral::hurst_exponent(&signal);

// Full summary
let summary = spectral::spectral_summary(&signal, 10, None);
println!("Entropy: {:.2} bits, Hurst: {:.3}, Stationary: {}", 
    summary.entropy_bits, summary.hurst, summary.is_stationary);
```

### Connectome (Coupling Detection)

```rust
use snapkit::connectome::TemporalConnectome;
use snapkit::CouplingType;

let mut tc = TemporalConnectome::new(0.3, 5, 10);

// Add room activity traces
let room_a: Vec<f64> = (0..20).map(|i| i as f64).collect();
let room_b: Vec<f64> = (0..20).map(|i| i as f64 * 2.0).collect();
tc.add_room(&room_a);
tc.add_room(&room_b);

let result = tc.analyze();
for pair in &result.pairs {
    println!("Room {} ↔ Room {}: {:?} (r={:.3})", 
        pair.room_a, pair.room_b, pair.coupling, pair.correlation);
}
```

## Covering Radius Guarantee

The Voronoï snap (`eisenstein_round_voronoi`) tests 9 candidates in the A₂ lattice cell, guaranteeing the maximum snap distance never exceeds **1/√3 ≈ 0.5774**. This is verified by the `verify_covering_radius()` function:

```rust
use snapkit::voronoi::verify_covering_radius;

let max_dist = verify_covering_radius(100);
assert!(max_dist <= 1.0 / 3.0_f64.sqrt() + 1e-10);
```

## no_std Usage

All modules work without `std`. The crate uses `alloc` for `Vec` in batch operations. For `no_std` targets:

```toml
[dependencies]
snapkit = { version = "0.1", default-features = false, features = [] }
```

## License

MIT OR Apache-2.0
