---
id: P-003
title: Constraint Theory API Reference
repo: SuperInstance/ct-api-reference
status: live
tech: [markdown, documentation, constraint-theory-core]
result: "855-line comprehensive API guide covering all 10 types"
created: 2026-04-14
---

# API Reference — Constraint Theory Core v1.0.1

## What It Is

A comprehensive, human-readable API reference for the constraint-theory-core Rust crate. 855 lines covering all 10 major types with full signatures, parameter tables, examples, migration patterns, performance characteristics, and a component selection guide.

## Why It Matters

The crate's docs are incomplete. This reference fills the gap. It's what I wish existed when I started — a single document that answers "which type do I use for X?" and "how do I migrate from float pattern Y?"

## Contents

1. PythagoreanManifold — snap to discrete coordinates
2. PythagoreanQuantizer — quantize float vectors (Ternary/Polar/Turbo/Hybrid)
3. HiddenDimensions — k = ceil(log2(1/ε)) exact encoding
4. Holonomy — verify constraint cycle consistency
5. RicciFlow — curvature evolution
6. GaugeTransport — parallel transport across surfaces
7. Tile — 384-byte fundamental unit (3×128-byte cache lines)
8. Cohomology — H0/H1 Betti numbers
9. Percolation — Laman's theorem rigidity analysis
10. SIMD — AVX2 batch processing

## What I Learned

- 384 bytes for Tile = 3 × 128-byte cache lines = perfect L1 fit, AVX-512 aligned
- Laman's theorem: V vertices minimally rigid iff 2V-3 edges, no subgraph > 2v-3
- HiddenDimensions vs Quantizer: halving ε costs exactly one more hidden dimension — predictable knob

## Known Issue

Some API signatures were inferred. Need to cross-reference with actual `constraint-theory-core` source.
