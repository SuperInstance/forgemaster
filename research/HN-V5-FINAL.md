# Show HN: Exact arithmetic for simulations – snap floats to exact rationals, zero drift (Rust, no_std, 620 lines)

Take a unit vector. Rotate it 360°. It should come back to (1, 0).

In IEEE 754, it comes back to (0.9999999999999998, 0.0000000000000002).

After ten thousand rotations, things that should point up are pointing sideways. Your multiplayer desyncs. Your Monte Carlo doesn't reproduce. Your robot drifts 40° off course — not from sensor error, but from adding 0.1 radians 288,000 times and rounding wrong each time.

Here's the fix: snap every value to the nearest *exact rational* from a pre-computed lattice. Rotate 360° and you get exactly (1, 0). Rotate 3,600,000° and you still get exactly (1, 0). No epsilon. No drift. No "close enough."

The lookup table is 4KB.

---

`cargo add eisenstein`

```rust
use eisenstein::{E12, HexDisk};

let z = E12::new(-5, 3);              // Eisenstein integer
assert_eq!(z.norm(), 49);              // exact: a²-ab+b² = 49

let dir = E12::snap_from_angle(0.0);   // snap any angle to hex grid
let disk = HexDisk::radius(36);        // 3,997 exact vertices, ~16KB
```

```python
# Python (Pythagorean lattice)
from constraint_theory import PythagoreanManifold

manifold = PythagoreanManifold(200)
x, y, noise = manifold.snap(0.577, 0.816)   # → nearest exact triple
```

620 lines of Rust. `#![no_std]`. Zero dependencies. Zero unsafe.

---

## How it works

Here's the thing nobody tells you about floating point: the error isn't random. It's *structured*. Your CPU represents numbers on a grid, and every operation rounds to the nearest grid point.

Snapping asks: what if the grid was *your* grid?

**Pythagorean triples** — the set of (a/c, b/c) where a²+b²=c² exactly — form a natural lattice in 2D. Every point is exact. Indexed with a KD-tree, nearest lookup is ~100ns. `pip install constraint-theory`.

**Eisenstein integers** — numbers of the form a + bω where ω = e^(2πi/3) — tile the angle space with hexagonal symmetry. 6× denser than Pythagorean triples. The norm a²-ab+b² is always an integer. No floats anywhere in the crate. `cargo add eisenstein`.

You're not losing precision by discretizing. You're *choosing* a precision that's closed under the operations you actually perform. The floats were always on a lattice. You just picked a bad one.

---

## What we've verified

**61M differential test inputs**, GPU vs CPU, zero mismatches. The CUDA kernels are [real source](https://github.com/SuperInstance/constraint-theory-ecosystem), not pseudocode.

**Negative results we published:**
- FP16 is **unsafe** for values > 2048 — 76% precision mismatches
- Tensor cores barely help (1.05–1.19×) — memory-bound, not compute-bound
- Bank conflict padding is **counterproductive** on Ada GPUs

We'd rather you trust us for publishing our failures than for overstating our successes.

We also maintain an [honest errata](https://github.com/SuperInstance/constraint-theory-math/blob/main/ERRATA.md) of 5 claims we got wrong and corrected, including demoting "theorem" to "open problem" and "unification" to "recognition of standard construction."

---

## The embedded path

There's a bare-metal C runtime (`flux_embedded.h`) — 4KB code, 1KB stack, Cortex-M0+. The ISA is Turing-incomplete (42 opcodes, no unbounded loops), so every program provably terminates.

**We are not safety-certified.** We have a mathematical path toward DO-178C/ISO 26262. Don't use this in your airplane yet.

---

## What needs work

- No WASM build yet
- No Cortex-M4 benchmarks on real hardware
- Python package does snapping only, not constraint checking
- The broader ecosystem (22 repos) varies in quality — eisenstein and constraint-theory-core are the strongest

---

[eisenstein v0.3.0](https://crates.io/crates/eisenstein) · [constraint-theory-core v2.2.0](https://crates.io/crates/constraint-theory-core) · [CUDA benchmarks](https://github.com/SuperInstance/constraint-theory-ecosystem) · [Math + Errata](https://github.com/SuperInstance/constraint-theory-math) · [Live demo](https://superinstance.github.io/cocapn-ai-web/demo-divergence-tolerance.html)
