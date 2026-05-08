# Show HN: Eisenstein – exact hexagonal arithmetic for Rust (zero drift after 10k rotations)

`cargo add eisenstein`

```rust
use eisenstein::{E12, HexDisk};

let z = E12::new(-5, 3);              // Eisenstein integer
assert_eq!(z.norm(), 49);              // a²-ab+b² = 49, exact

let dir = E12::snap_from_angle(0.0);   // snap any angle to hex grid
let disk = HexDisk::radius(36);        // 3,997 exact vertices
```

Pure integer arithmetic. `#![no_std]`, zero dependencies, zero `unsafe`.

The norm `a²-ab+b²` is always an integer — that's the mathematical definition of Eisenstein integers. No floats, no rounding, no drift.

**10,000 rotations. Zero drift.** Rotate an E12 ten thousand times and it comes back exactly where it started. The operations never leave the lattice. We have a test for this.

Eisenstein integers tile 2D space with hexagonal symmetry — same number system crystallographers use for hexagonal lattices. 6× denser than Pythagorean triples.

**Use cases:** hex grid games (Civ, Factorio), deterministic lockstep multiplayer, crystallography, GPU tiling, anywhere you need rotation without drift.

**Core operations** (zero deps):
- `E12::new(a, b)`, `.norm()`, `.add()`, `.mul()`, `.rotate_60()`
- `.d6_rotations()` — all 6 hexagonal symmetries
- `.hex_distance()` — exact hex grid distance
- `HexDisk::radius(N)` — iterate over all 3N²+3N+1 points

**Angle snapping** (optional, uses libm):
- `E12::snap_from_angle(θ)` — find nearest E12 to any angle
- `HexDisk::snap_direction(θ)` — snap within bounded disk

```toml
eisenstein = { version = "0.3", default-features = false }  # pure integers
eisenstein = "0.3"  # includes angle snapping
```

37 tests (25 core, 12 snap) including the 10,000-operation drift test.

There's also a companion Pythagorean snapping crate: `pip install constraint-theory` or `cargo add constraint-theory-core`. And CUDA kernels that checked 61M inputs with zero GPU/CPU mismatches.

We publish [negative results](https://github.com/SuperInstance/constraint-theory-ecosystem) (FP16 unsafe past 2048, tensor cores barely help, bank padding counterproductive) and an [honest errata](https://github.com/SuperInstance/constraint-theory-math/blob/main/ERRATA.md) of claims we got wrong.

[eisenstein](https://crates.io/crates/eisenstein) · [constraint-theory-core](https://crates.io/crates/constraint-theory-core) · [CUDA benchmarks](https://github.com/SuperInstance/constraint-theory-ecosystem) · [Math + Errata](https://github.com/SuperInstance/constraint-theory-math) · [Live demo](https://superinstance.github.io/cocapn-ai-web/demo-divergence-tolerance.html)
