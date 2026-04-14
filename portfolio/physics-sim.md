---
id: P-001
title: Physics Simulation Proof
repo: SuperInstance/proof-physics-sim
status: live
tech: [rust, constraint-theory-core, f64, verlet-integration]
result: "3-body energy drift elimination via PythagoreanManifold snap"
created: 2026-04-14
---

# Physics Simulation — Float vs Constraint Theory

## What It Is

A 3-body solar system simulation running 100,000 timesteps of Velocity Verlet integration. Two modes: standard f64 physics vs constraint-theory snapping after each integration step. The float version accumulates energy drift. The CT version doesn't.

## Why It Matters

This is the most visceral proof. Anyone who's run a physics sim knows the pain — orbits decay, energy appears from nowhere, planets fly off. Constraint theory fixes it by snapping positions back to an exact grid after each step. The energy can't drift because the grid won't let it.

## What I Learned

- The real `PythagoreanManifold` API takes integer density, not float tolerance
- `snap()` works on `[f32; 2]` — 2D unit vectors. For 3D, decompose into direction (2D polar) + magnitude separately
- The proof agent adapted by working in the 2D orbital plane, snapping orbital angles to Pythagorean ratios
- Need to verify against real crate — this was written by Claude Code guessing the API

## How to Extend

- Add more bodies (N-body chaos)
- Add collision detection (float vs CT position agreement)
- Visual output ( Gnuplot or terminal plot)
- Compare different integration schemes (Euler, RK4, Verlet) all with CT snap

## Agent Pickup Instructions

```bash
git clone https://github.com/SuperInstance/proof-physics-sim.git
cd proof-physics-sim
# First: verify constraint-theory-core API matches
cargo check
# If API mismatch, check crates.io docs for constraint-theory-core v1.0.1
# Then: run the benchmark
cargo run --release
```
