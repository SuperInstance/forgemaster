# SnapKit ⚒️ — Tolerance-Compressed Attention Allocation

**EVERYTHING within tolerance is compressed away. ONLY the deltas survive.**

SnapKit is a Rust implementation of the **Snaps as Attention** theory — a mathematical framework for allocating finite cognitive/attention resources using tolerance-compressed snap functions.

## Core Idea

A **snap function** maps continuous values to their nearest expected point (lattice point in a chosen topology). Values **within tolerance** snap silently. Only values **exceeding tolerance** (deltas) demand attention — and attention is the finite resource.

```
    Value 0.05 ──→ SnapFunction ──→ ✓ Snapped (within 0.1 tolerance)
    Value 0.30 ──→ SnapFunction ──→ ⚠ DELTA (exceeds tolerance)
```

This mirrors how expertise works: familiar patterns snap automatically, freeing cognition for what's actually novel or significant.

## Features

- **SnapFunction** — Generic tolerance gatekeeper (`f32`, `f64`)
- **DeltaDetector** — Multi-stream delta monitoring with per-stream topologies
- **AttentionBudget** — Three allocation strategies (Actionability, Reactive, Uniform)
- **ScriptLibrary** — Pattern matching with cosine similarity → automated response
- **Pipeline** — Composable snap→detect→allocate processing
- **LearningCycle** — Full expertise lifecycle: DeltaFlood → ScriptBurst → SmoothRunning → Disruption → Rebuilding
- **Eisenstein Lattice** — ℤ[ω] hexagonal lattice (A₂ root system) — the crown jewel
- **FakeDeltaDetector** — Adversarial delta injection detection
- **CamouflageGenerator** — Signal masking for adversarial settings
- **StreamProcessor** — Real-time stream processing with ring buffer windowing

## Quick Start

```rust
use snapkit::{SnapFunction, SnapTopology};

// Create a snap function with builder pattern
let mut snap = SnapFunction::<f64>::builder()
    .tolerance(0.1)
    .topology(SnapTopology::Hexagonal)
    .build();

// Within tolerance — no attention required
let result = snap.observe(0.05);
assert!(result.within_tolerance);

// Exceeds tolerance — demands attention
let result = snap.observe(0.3);
assert!(result.is_delta());

// Check calibration
println!("Snap rate: {:.1}%", snap.snap_rate() * 100.0);
println!("Calibration: {:.4}", snap.calibration());
```

### The Eisenstein Crown Jewel

```rust
use snapkit::{EisensteinInt, eisenstein_snap, eisenstein_distance};

// Snap (1.2, 0.7) to nearest hexagonal lattice point
let nearest = eisenstein_snap((1.2, 0.7));
assert_eq!(nearest, EisensteinInt::new(2, 1));

// Multiplicative norm: a² - ab + b²
let e = EisensteinInt::new(3, 2);
assert_eq!(e.norm(), 7);  // 9 - 6 + 4 = 7
```

## Topologies

| Topology | Root System | ADE | Best For | Tolerance |
|----------|-------------|-----|----------|-----------|
| Binary | A₁ | Yes | Yes/no decisions | 0.15 |
| Categorical | A₁×A₁×... | Yes | Slot-filling | 0.1 |
| Hexagonal | A₂ | Yes | 2D continuous data | 0.1 |
| Octahedral | A₃ | Yes | Directional data | 0.2 |
| Cubic | A₁³ | No | 3D positional | 0.2 |
| Uniform | — | — | Unknown structure | 0.08 |

## Learning Cycle

The expertise lifecycle modeled as phase transitions:

1. **🌊 DeltaFlood** — No scripts, everything is novel (cognitive load ≈ 1.0)
2. **💥 ScriptBurst** — Patterns emerging, rapid script creation
3. **🏃 SmoothRunning** — Most things snap to scripts (cognitive load ≈ 0.0)
4. **🚨 Disruption** — Accumulated deltas, scripts failing
5. **🔨 Rebuilding** — Constructing new scripts from deltas

## Examples

```bash
# Poker attention engine — multi-stream delta detection
cargo run --example poker

# Rubik's cube script matching
cargo run --example rubik

# Real-time stream monitoring
cargo run --example monitoring

# Learning cycle phase transitions
cargo run --example learning
```

## Benchmarks

```bash
cargo bench
```

## Installation

```toml
[dependencies]
snapkit = "0.1.0"
```

## License

MIT OR Apache-2.0
