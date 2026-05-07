# Show HN: Exact snapping for games and embedded – eisenstein crate (Rust, no_std, zero deps)

`cargo add eisenstein`

```rust
use eisenstein::{E12, HexDisk};

let z = E12::new(-5, 3);             // Eisenstein integer
assert_eq!(z.norm(), 49);             // a²-ab+b² = 49, exact

let dir = E12::snap_from_angle(0.0);  // Snap any angle to nearest hex direction
let disk = HexDisk::radius(36);       // 3,997 exact vertices, ~16KB
```

620 lines. `#![no_std]`. Zero dependencies. Zero unsafe. The norm `a²-ab+b²` is always an integer — no floats anywhere in the crate.

## Why this exists

Floating-point drift kills deterministic systems. Lockstep multiplayer desyncs. Monte Carlo non-reproducibility. Safety-critical bounds checking that passes on one machine and fails on another.

The fix: snap to exact rational points on discrete lattices.

**Hexagonal lattice** (this crate): Eisenstein integers `a + bω` where `ω = e^(2πi/3)`. Norm is always exact integer. 6× denser than Pythagorean triples. `snap_from_angle(θ)` finds the nearest Eisenstein integer to any direction.

**Pythagorean lattice** (sister crate): `pip install constraint-theory` — snap 2D unit vectors to exact Pythagorean triples `(a/c, b/c)` where `a²+b²=c²`. KD-tree indexed, ~100ns per snap.

## What's actually proven

We have an [honest errata](https://github.com/SuperInstance/constraint-theory-math/blob/main/ERRATA.md) listing 5 claims we got wrong and corrected:

- Intent-Holonomy duality → **demoted from theorem to open problem** (we couldn't close the proof gap)
- Temporal snap → **demoted to conjecture** (no proof exists)
- Galois "unifications" → **reclassified as recognitions of standard constructions** (not new math)
- Two other claims corrected with 30% confidence scores

Marcus (game dev, reviewed our code): *"The most honest errata I've seen in a software project."*

## The CUDA numbers are real

We ran 61M differential test inputs through GPU kernels with CPU reference checks. Zero mismatches. The kernels are [real source](https://github.com/SuperInstance/constraint-theory-ecosystem), not pseudocode:

- RTX 4050: 1.02B checks/sec (INT8 × 8 constraints)
- AVX-512 mixed precision: 3.17× speedup (cycle-accurate, 5-run mean)
- FP16 is **unsafe** for values > 2048 — 76% precision mismatches (published this negative result)
- Tensor cores barely help — workload is memory-bound, not compute-bound
- Bank conflict padding is **counterproductive** on Ada GPUs

## The embedded path

There's a bare-metal C runtime (`flux_embedded.h`) — 4KB code, 1KB stack, runs on Cortex-M0+. The 42-opcode ISA is Turing-incomplete (every program provably terminates). No malloc, no recursion, no unbounded loops.

**We are not safety-certified.** We have a mathematical path toward DO-178C / ISO 26262. Don't use this in your airplane yet.

## What needs work

- No WASM build yet (game devs: `wasm-pack` support coming)
- No Cortex-M4 cycle benchmarks on real hardware
- Python package only does snapping, not constraint checking
- The broader ecosystem (22 repos) has varying quality — eisenstein and constraint-theory-core are the strongest

## Repos

- [eisenstein](https://crates.io/crates/eisenstein) (this crate, v0.3.0)
- [constraint-theory-core](https://crates.io/crates/constraint-theory-core) (Pythagorean snapping, v2.2.0, 184 tests)
- [flux-lucid](https://crates.io/crates/flux-lucid) (CDCL + mixed precision, v0.1.6)
- [holonomy-consensus](https://crates.io/crates/holonomy-consensus) (GL(9) consensus, v0.1.2)
- [Math + Proofs + Errata](https://github.com/SuperInstance/constraint-theory-math)
- [CUDA benchmarks](https://github.com/SuperInstance/constraint-theory-ecosystem)
