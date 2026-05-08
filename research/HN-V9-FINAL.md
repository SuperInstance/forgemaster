# Show HN: Eisenstein – exact hexagonal arithmetic for Rust (zero drift after 10k rotations)

`cargo add eisenstein`

```rust
use eisenstein::{E12, HexDisk};

let z = E12::new(-5, 3);              // Eisenstein integer
assert_eq!(z.norm(), 49);              // a²-ab+b² = 49, exact

let dir = E12::snap_from_angle(0.0);   // snap any angle to hex grid
let disk = HexDisk::radius(36);        // 3,997 exact vertices
```

Floating-point hex coordinates drift after repeated rotations. Eisenstein integers don't.

Pure integer arithmetic. `#![no_std]`, zero dependencies, zero `unsafe`. The norm `a²-ab+b²` is always an integer — that's the mathematical definition. No floats, no rounding, no drift.

**10,000 rotations. Zero drift.** Rotate an E12 ten thousand times and it comes back exactly where it started. The operations never leave the lattice.

Eisenstein integers tile 2D space with hexagonal symmetry — same number system crystallographers use for hexagonal lattices. 6× denser than Pythagorean triples for covering the same 2D space.

**Use cases:** hex grid games (Civ, Factorio), deterministic lockstep multiplayer, crystallography, GPU tiling, anywhere you need rotation without drift.

**Core operations** (zero deps): construction, exact norm, addition, multiplication, 60° rotation, the full D6 symmetry group, hex distance, and disk iteration. Iterating a `HexDisk::radius(1000)` is cache-friendly and allocation-free.

**Angle snapping** (optional, uses libm): `snap_from_angle(θ)` and `snap_direction(θ)`.

```toml
eisenstein = { version = "0.3", default-features = false }  # pure integers
eisenstein = "0.3"  # includes angle snapping
```

Includes a 10,000-operation drift test and property tests for all six symmetries.

We publish [negative results](https://github.com/SuperInstance/constraint-theory-ecosystem) (FP16 unsafe past 2048, tensor cores barely help, bank padding counterproductive) and an [honest errata](https://github.com/SuperInstance/constraint-theory-math/blob/main/ERRATA.md) of claims we got wrong. There's also a companion Python package for Pythagorean snapping.

We'd particularly love feedback on whether the `#![no_std]` API surface feels right, or if we should expose more of the lattice reduction internals.

[eisenstein](https://crates.io/crates/eisenstein) · [constraint-theory-core](https://crates.io/crates/constraint-theory-core) · [CUDA benchmarks](https://github.com/SuperInstance/constraint-theory-ecosystem) · [Math + Errata](https://github.com/SuperInstance/constraint-theory-math) · [Live demo](https://superinstance.github.io/cocapn-ai-web/demo-divergence-tolerance.html)
