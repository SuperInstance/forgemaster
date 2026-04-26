# pythagorean-snap

**O(log n) nearest-neighbor search on the Pythagorean manifold** — full-circle, zero-drift, 316× faster than brute force.

## What It Does

Generates all primitive Pythagorean triples up to `max_c`, mirrors them across all 8 octants for full-circle coverage, sorts by angle, and provides binary-search-based snap queries. Returns exact integer triples — zero floating-point drift guaranteed.

## Performance

At `max_c = 50,000` (41,216 full-circle triples):

| Strategy | Throughput | Speedup |
|----------|-----------|---------|
| Brute force | ~33K qps | 1.0× |
| Interpolation | ~3.8M qps | 114× |
| Bucket (1024) | ~4.6M qps | 139× |
| **Binary search** | **~10.5M qps** | **316×** |

- **100% agreement** with brute-force ground truth
- **Zero drift** — all results are exact integer triples satisfying x² + y² = c²
- **CV = 0.067** — nearly uniform angular distribution across the full circle

## Quick Start

```rust
use pythagorean_snap::PythagoreanManifold;

let m = PythagoreanManifold::new(50_000);
let t = m.snap_angle(0.785); // snap to nearest triple at ~45°
assert!(t.verify());          // always exact — zero drift
println!("({}, {}, {}) — angle: {:.4} rad", t.x, t.y, t.c, t.angle());
```

## API

| Method | Description |
|--------|-------------|
| `new(max_c)` | Build manifold with all triples up to hypotenuse `max_c` |
| `snap_angle(theta)` | Find nearest triple to angle (radians), returns `&Triple` |
| `snap_index(theta)` | Find nearest triple index |
| `constraint_distance(theta)` | Angular distance to nearest triple |
| `snap_brute(theta)` | Brute-force reference (for verification) |
| `len()` | Number of triples in manifold |
| `max_c()` | Maximum hypotenuse value |
| `angle_range()` | (min_angle, max_angle) in radians |
| `iter()` | Iterate over all triples |
| `get(i)` | Get triple by index |

## Triple Structure

```rust
pub struct Triple {
    pub x: i64,  // Signed x-component (leg a)
    pub y: i64,  // Signed y-component (leg b)
    pub c: u64,  // Hypotenuse (always positive)
}
```

Methods: `angle()`, `norm()`, `verify()` (checks x² + y² = c²).

## Key Finding

Single-octant Pythagorean triples are **highly non-uniform** (CV = 2.581) — they cluster near 0° and 45°. Expanding to all 8 octants produces a **nearly uniform** distribution (CV = 0.067), making binary search extremely effective.

## No Std Support

Disable the `std` feature for `no_std` environments:

```toml
[dependencies]
pythagorean-snap = { version = "0.1", default-features = false }
```

## License

MIT
