# ct-simd

Rayon-parallel batch snap on the Pythagorean manifold. Same API, multi-core throughput.

## Install

```toml
[dependencies]
ct-simd = "0.1"
```

## Quick Start

```rust
use ct_simd::BatchSnap;

let snap = BatchSnap::new(50_000); // ~41K triples
let queries: Vec<f64> = (0..1_000_000).map(|i| i as f64 / 1_000_000.0 * std::f64::consts::TAU).collect();
let results = snap.snap_batch(&queries); // parallel, uses all cores
```

## Key Finding

At 50K max_c, single-threaded binary search is ~44M qps — so fast that
Rayon parallelism adds only 1.3x. The real speedup lives on GPU (CUDA: 550x).

This crate's value: drop-in parallel batch API + built-in benchmarking.

## Benchmarks (WSL2, 24 threads, rustc 1.95)

| max_c | Triples | Sequential | Parallel | Speedup |
|-------|---------|------------|----------|---------|
| 1,000 | 896 | 95M qps | 11M qps | 0.1x (overhead) |
| 10,000 | 8,296 | 65M qps | 15M qps | 0.2x (overhead) |
| 50,000 | 41,216 | 44M qps | 57M qps | 1.3x |

## License

MIT
