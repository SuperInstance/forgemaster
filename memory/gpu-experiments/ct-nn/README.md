# constraint-theory-nn

Exact 1-nearest-neighbor lookup on the Pythagorean triple manifold.

## What It Does

- **TripleIndex** — pre-computed sorted index of all triples up to max_c
- **O(log n) snap** — binary search finds nearest triple to any query angle
- **100% correctness** — verified against brute force (wraps around 0/2π)
- **All 8 octants** — full-circle generation for uniform coverage

## Install

```toml
[dependencies]
constraint-theory-nn = "0.1"
```

## Quick Start

```rust
use constraint_theory_nn::TripleIndex;

let idx = TripleIndex::from_max_c(50000);
let triple = idx.snap_triple(0.6435); // nearest to arctan(3/4)
println!("({}, {}, {})", triple.a, triple.b, triple.c);

let result = idx.verify(100000);
assert_eq!(result.agreement_rate, 1.0);
```

## Performance

~10M+ qps at max_c=50000 (binary search on ~24K triples).

## License

MIT
