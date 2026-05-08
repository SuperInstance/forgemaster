# Show HN: Eisenstein – exact hexagonal arithmetic for Rust (zero drift after 10k rotations)

`cargo add eisenstein`

```rust
use eisenstein::{E12, HexDisk};

let z = E12::new(-5, 3);              // Eisenstein integer
assert_eq!(z.norm(), 49);              // a²-ab+b² = 49, exact

let dir = E12::snap_from_angle(0.0);   // snap angle to hex grid
let disk = HexDisk::radius(36);        // 3,997 exact vertices
```

Floating-point hex coordinates drift after repeated rotations. Eisenstein integers don't.

Pure integer arithmetic. `#![no_std]`, zero deps, zero `unsafe`. The norm `a²-ab+b²` is always an integer — that's the mathematical definition. No floats, no rounding, no drift.

**10,000 rotations. Zero drift.** Rotate ten thousand times, comes back exactly where it started. The operations never leave the lattice.

Eisenstein integers tile 2D space with hexagonal symmetry — same number system crystallographers use. 6× denser than Pythagorean triples covering the same 2D space.

**Use cases:** hex grid games (Civ, Factorio), deterministic lockstep multiplayer, crystallography, GPU tiling, anywhere you need rotation without drift.

**Core ops** (zero deps): exact norm, addition, multiplication, 60° rotation, D6 group, hex distance, disk iteration. `HexDisk::radius(1000)` is cache-friendly and allocation-free.

**Angle snapping** (optional, libm): `snap_from_angle(θ)`, `snap_direction(θ)`.

```toml
eisenstein = { version = "0.3", default-features = false }  # pure ints
eisenstein = "0.3"  # with angle snapping
```

Includes 10,000-op drift test and property tests for all six symmetries.

We publish [negative results](https://github.com/SuperInstance/constraint-theory-ecosystem) (FP16 unsafe past 2048, tensor cores barely help, bank padding counterproductive) and an [honest errata](https://github.com/SuperInstance/constraint-theory-math/blob/main/ERRATA.md) of claims we got wrong. Companion Python package for Pythagorean snapping.

Feedback: does the `#![no_std]` API surface feel right? Should we expose more lattice reduction internals?

Dev tools: [eisenstein-bench](https://github.com/SuperInstance/eisenstein-bench) · [eisenstein-fuzz](https://github.com/SuperInstance/eisenstein-fuzz) · [eisenstein-c](https://github.com/SuperInstance/eisenstein-c) · [eisenstein-wasm](https://github.com/SuperInstance/eisenstein-wasm) · [hexgrid-gen](https://github.com/SuperInstance/hexgrid-gen)

[eisenstein](https://crates.io/crates/eisenstein) · [constraint-theory-core](https://crates.io/crates/constraint-theory-core) · [CUDA benchmarks](https://github.com/SuperInstance/constraint-theory-ecosystem) · [Math + Errata](https://github.com/SuperInstance/constraint-theory-math) · [Interactive demo](https://superinstance.github.io/cocapn-ai-web/demo-eisenstein.html)
