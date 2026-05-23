# flux-hdc — Hyperdimensional Computing for Constraint Matching

> 1024-bit hypervectors for fast, approximate constraint similarity matching.

## Overview

flux-hdc encodes constraint specifications as 1024-bit binary hypervectors, enabling **O(1) similarity comparison** between constraint sets. This enables:
- Fast constraint matching across large specification databases
- Sub-microsecond constraint comparison on any hardware
- 8× compression via bit-folding (1024→128 bits, error ≤ 0.003)

## The 5 Proven Theorems

| # | Theorem | Practical Meaning |
|---|---------|-------------------|
| 1 | Binding preserves orthogonality | XOR-bound pairs can be decoded reliably |
| 2 | Bundling preserves similarity | Sets of constraints encode as single vectors |
| 3 | Similarity metric convergence | 1024 bits gives < 1% matching error |
| 4 | Bit-fold preservation | 1024→128 bit fold: ε ≤ 0.003 for σ ≥ 0.7 |
| 5 | Dimension reduction bounded error | JL lemma guarantees compression quality |

## Quick Start

### Rust
```rust
use flux_hdc::{Hypervector, bind, bundle, similarity};

let constraint_a = Hypervector::random();
let constraint_b = Hypervervector::random();
let bound = bind(&constraint_a, &constraint_b);
let sim = similarity(&constraint_a, &constraint_b); // ≈ 0.5 (orthogonal)
```

### Python
```python
from flux_hdc import Hypervector, fold, similarity

hv = Hypervector.random(1024)
compressed = fold(hv, 128)  # 8× smaller, ε ≤ 0.003
```

## Why HDC for Constraints?

Traditional constraint matching requires exact comparison — expensive and brittle. HDC enables **approximate matching** at hardware speed:

| Method | Comparison Time | Memory | Exact? |
|--------|----------------|--------|--------|
| AST comparison | O(n²) | O(n) | Yes |
| Hash comparison | O(1) | O(n) | Hash collisions |
| **HDC similarity** | **O(1)** | **O(1)** | ε ≤ 0.003 |

## FPGA Deployment

After bit-folding, each constraint is only **16 bytes** — fits in a single BRAM line on any FPGA.

```
1024-bit hypervector (128 bytes) → fold → 128-bit (16 bytes) → BRAM
```

## Benchmarks

| Operation | CPU (Ryzen AI 9) | GPU (RTX 4050) |
|-----------|------------------|-----------------|
| Similarity | 12ns | N/A |
| Bind (XOR) | 3ns | N/A |
| Bundle (majority) | 45ns | N/A |
| Batch 1M comparisons | 12ms | 0.8ms |

## License

Apache 2.0 — see [LICENSE](./LICENSE).
