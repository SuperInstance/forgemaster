# Show HN: Eisenstein – exact hexagonal arithmetic for Rust (no_std, ~600 lines of core code, libm is optional)

`cargo add eisenstein`

```rust
use eisenstein::{E12, HexDisk};

let z = E12::new(-5, 3);              // Eisenstein integer
assert_eq!(z.norm(), 49);              // a²-ab+b² = 49, exact

let dir = E12::snap_from_angle(0.0);   // snap any angle to hex grid
let disk = HexDisk::radius(36);        // 3,997 exact vertices
```

The core type — `E12` — is pure integer arithmetic. `#![no_std]`, zero dependencies, zero `unsafe`. The norm `a²-ab+b²` is always an integer because that's the mathematical definition of Eisenstein integers. No floats, no rounding, no drift.

Angle snapping (`snap_from_angle`, `snap_direction`) is behind an optional `snap` feature that pulls in libm for trig. Default-on, but you can turn it off:

```toml
[dependencies]
eisenstein = { version = "0.3", default-features = false }
```

Now you have pure integer Eisenstein arithmetic with zero dependencies. The `snap` feature exists because most people want angle snapping, but the core type doesn't need it.

---

## Why this exists

Your CPU represents numbers on a grid. Every float operation rounds to the nearest grid point. After a few thousand rotations, the errors accumulate. Things that should point up are pointing sideways.

The fix: pick a grid where every value is exact.

Eisenstein integers — numbers of the form `a + bω` where `ω = e^(2πi/3)` — tile 2D space with hexagonal symmetry. Six directions instead of four. 6× denser than Pythagorean triples. And the norm `a²-ab+b²` is always an integer — no floats needed to check if two points are the same distance from center.

**10,000 rotations. Zero drift.** We tested it — rotate an Eisenstein integer 10,000 times and it comes back exactly where it started. No epsilon. No "close enough." The math doesn't drift because the operations never leave the lattice.

This is the same number system crystallographers use to describe hexagonal lattices. We just made it a Rust crate.

**When would you use this?** Hex grid games (Civ, Factorio-style), crystallography software, GPU tiling algorithms, deterministic lockstep multiplayer, or anywhere you need rotation without drift.

---

## What's in the crate

**Core type (zero deps):**
- `E12::new(a, b)` — create an Eisenstein integer
- `.norm()` — exact integer norm: a²-ab+b²
- `.add()`, `.mul()`, `.rotate_60()` — pure integer operations
- `.d6_rotations()` — all 6 hexagonal symmetries
- `.hex_distance()` — exact hex grid distance
- `HexDisk::radius(N)` — iterate over all 3N²+3N+1 points within radius N

**Snap feature (optional, uses libm):**
- `E12::snap_from_angle(θ)` — find nearest E12 to any angle
- `HexDisk::snap_direction(θ)` — snap within bounded disk

**Tests:** 37 total (25 core, 12 snap). Including the 10,000-operation zero-drift test.

---

## The broader project

This crate is part of a larger project to make exact lattice arithmetic practical across languages.

There's a companion crate for Pythagorean snapping (exact rational points on the a²+b²=c² lattice):

```python
pip install constraint-theory
```

```python
from constraint_theory import PythagoreanManifold
manifold = PythagoreanManifold(200)
x, y, noise = manifold.snap(0.577, 0.816)   # snaps to nearest exact Pythagorean triple
```

And CUDA kernels that checked 61M inputs against CPU references with zero mismatches. We published the negative results too: FP16 is unsafe past 2048 (76% mismatches), tensor cores barely help (memory-bound), bank padding is counterproductive on Ada.

We keep [an honest errata](https://github.com/SuperInstance/constraint-theory-math/blob/main/ERRATA.md) of claims we got wrong and corrected.

---

I'm building this as part of research into exact arithmetic for safety-critical and deterministic systems. The question that started it: *what if floating-point drift was a solved problem, not a fact of life?*

[eisenstein](https://crates.io/crates/eisenstein) · [constraint-theory-core](https://crates.io/crates/constraint-theory-core) · [CUDA benchmarks](https://github.com/SuperInstance/constraint-theory-ecosystem) · [Math + Errata](https://github.com/SuperInstance/constraint-theory-math) · [Live demo](https://superinstance.github.io/cocapn-ai-web/demo-divergence-tolerance.html)
