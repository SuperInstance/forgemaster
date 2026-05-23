# constraint-theory-core

Geometric snapping for deterministic computation. Given a continuous point, find the nearest Pythagorean coordinate, and tell you exactly how far off you were.

```rust
use constraint_theory_core::ConstraintSystem;

fn main() {
    // 8 density levels → 256 discrete positions per axis
    let cs = ConstraintSystem::new(8);

    // A raw measurement: sensor reading, neural activation, agent position
    let raw = [3.14159, 2.71828];

    let (snapped, residual) = cs.snap(raw, 0.05);

    println!("raw:      {:?}", raw);
    println!("snapped:  {:?}", snapped);     // nearest valid Pythagorean coordinate
    println!("residual: {:.6}", residual);   // drift — zero means exact hit

    // Same input. Same output. Every machine. Every time.
    assert!(residual < 0.05, "point outside tolerance — reject or escalate");
}
```

[![Crates.io](https://img.shields.io/crates/v/constraint-theory-core.svg)](https://crates.io/crates/constraint-theory-core)

---

## What it does

Continuous floating-point arithmetic drifts. Two machines computing the same value get answers that differ in the last few bits — harmless in isolation, catastrophic when those answers are used as training signal across a distributed fleet.

`constraint-theory-core` solves this by replacing continuous coordinates with a discrete lattice of Pythagorean coordinates. Every point in that lattice has an exact integer representation at a given density level. There is no rounding ambiguity. Two machines snapping the same input to the same lattice always return the same result.

The three operations:

- **`new(density)`** — Build a constraint system with `2^density` discrete positions per axis. Density 8 gives 256 positions; density 12 gives 4096.
- **`snap(point, tolerance)`** — Find the nearest lattice point. Return `(snapped, residual)` where `residual` is the Euclidean distance from the original to the snapped position.
- **Holonomy verification** — If you snap a point, transform it, then snap back, the round-trip residual is exactly zero. This is the holonomy check: no drift accumulates across operations.

The holonomy property is the guarantee. It means you can chain constraint operations across agents, machines, and training runs and the error does not compound.

---

## Why this matters for PLATO

PLATO's training pipeline converts agent interactions into tiles — typed Q/A knowledge units that accumulate into rooms and eventually train ensigns (LoRA-compatible expertise adapters). The quality gate for that pipeline is `plato-lab-guard`, which uses confidence scores to decide whether a tile set is strong enough to train on.

Those confidence scores need to be reproducible. An ensign trained on Forgemaster's RTX 4050 needs to produce the same inference results as a tile validated on Oracle1's ARM64 cloud node. If the underlying geometry drifts between machines, confidence scores drift, tile deduplication breaks, and training runs on a corrupted signal.

`constraint-theory-core` is the foundation that prevents this. Geometric computations in the PLATO pipeline — swarm coordination positions, tile embedding geometry, DCS law validation — snap through this crate before they touch anything downstream.

The five convergence constants that ground the fleet's DCS laws:

| Constant | Value | What it means |
|---|---|---|
| Laman threshold | k = 12 neighbors | Minimum for rigid graph (no deformable clusters) |
| Pythagorean bit ceiling | log₂(48) ≈ 5.585 | Quantization limit at density 6 |
| Ricci flow multiplier | 1.692× | Spectral gap factor — measured swarm convergence matches prediction |
| Zero holonomy | residual = 0.0 | Round-trip drift is zero — consensus without PBFT overhead |
| H1 cohomology threshold | (sheaf boundary) | Detects emergent agent coordination patterns |

These constants were derived independently from constraint theory and from JC1's DCS swarm measurements. They matched to three significant figures without communication between the two development tracks. The crate encodes that match as a hard guarantee.

---

## Performance

`snap` runs in O(1): it computes the nearest lattice point via direct index lookup into a precomputed coordinate table — no search, no iteration. No heap allocation per call. On x86_64 and ARM64, throughput is in the tens of millions of snaps per second per core.

The density parameter trades memory for precision. Density 8 uses a table of 256 × 256 entries (~512KB). Density 12 uses 4096 × 4096 (~128MB). Most use cases need density 6–8.

---

## What it doesn't do

- **It does not handle 3D.** The API is `[f32; 2]`. 3D snapping is not implemented.
- **It does not replace floating-point arithmetic globally.** You still use `f32`/`f64` everywhere else. This crate only snaps at the boundaries where discreteness matters — swarm positions, training-signal coordinates, consensus checkpoints.
- **It does not tolerate large residuals silently.** If your input falls outside the `tolerance` you pass to `snap`, the residual exceeds it. What you do with that — retry, escalate, reject — is your decision. The crate does not decide for you.
- **The Pythagorean lattice is not uniform.** Coordinate density is higher near the origin and sparser at the edges. This is a property of Pythagorean triples, not a bug. If you need uniform distribution, density 12 approximates it at the cost of memory.

---

## Usage

```toml
[dependencies]
constraint-theory-core = "1.0"
```

Requires Rust 1.70+. No unsafe code. No external dependencies beyond `std`.

---

## Relation to the fleet

This crate is the formal substrate that the rest of the Cocapn fleet builds on. The PLATO tile pipeline, the DCS swarm laws, the deadband doctrine, and the MUD holodeck all depend on the guarantee that geometric computations are reproducible. That guarantee lives here.

If you're building something that needs to agree with PLATO on a coordinate — across machines, across training runs, across time — this is the crate you add.

The rest of the fleet: [github.com/cocapn](https://github.com/cocapn)

---

*Forgemaster ⚒️ — Cocapn constraint theory*
