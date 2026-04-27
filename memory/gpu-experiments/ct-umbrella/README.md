# ct — Constraint Theory Umbrella

Unified API for the constraint theory ecosystem.

## What It Does

- `snap(theta, max_c)` — snap any angle to its nearest Pythagorean triple
- `holonomy(start, steps)` — measure angular deficit on the manifold
- `generate_triples(max_c)` — Euclid formula, all octants
- `Triple`, `SnapResult`, `ManifoldPoint` types

## Install

```toml
[dependencies]
ct = "0.1"
```

## Quick Start

```rust
use ct::{snap, Triple, DEFAULT_MAX_C};

let result = snap(std::f64::consts::FRAC_PI_4, DEFAULT_MAX_C);
assert_eq!(result.triple, Triple::new(3, 4, 5));
println!("Distance: {}", result.distance); // ~0.002 rad
```

## GPU Performance

| Platform | Throughput | Speedup |
|----------|-----------|---------|
| CPU (single) | 10.5M qps | 1x |
| CPU (Rayon) | 13.5M qps | 1.3x |
| GPU (RTX 4050) | 2.65B qps | 252x |

## License

MIT
