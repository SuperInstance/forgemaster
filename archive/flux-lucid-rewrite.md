# flux-lucid

**Unified constraint theory ecosystem.** CDCL → LLVM IR → AVX-512 compilation, GL(9) zero-holonomy fleet consensus, and 9-channel intent communication — one crate.

```
cargo add flux-lucid
```

**v0.1.6** · 2,000+ LOC · 93 tests · crates.io · Apache-2.0

---

## API at a Glance

### Intent Vectors — 9-Channel Profile

```rust
use flux_lucid::{Channel, IntentVector, intent};

// Encode: stakes matter (0.9), process matters (0.8)
let mut sender = IntentVector::zero();
sender.set(Channel::Stakes, 0.9);
sender.set(Channel::Process, 0.8);

// Check alignment against another profile
let mut receiver = IntentVector::zero();
receiver.set(Channel::Stakes, 0.85);
let report = intent::check_alignment(&sender, &receiver);
println!("{report}"); // ✓ SAFE

// Check draft (context depth required)
let draft = navigation::check_draft(&sender, 0.8, 0.0);
println!("{draft}"); // SAFE
```

### Constraint Precision — Stakes → Bit Width

Higher stakes → stiffer tolerance → wider precision. This maps stakes (C9) directly to bits per constraint:

| Stakes | Material | Precision | Bits | Constraints/AVX-512 reg |
|--------|----------|-----------|------|------------------------|
| > 0.75 | Steel | DUAL | 64 | 16 |
| 0.5–0.75 | Fiberglass | INT32 | 32 | 16 |
| 0.25–0.50 | Oak | INT16 | 16 | 32 |
| < 0.25 | Rubber/Cedar | INT8 | 8 | 64 |

```rust
use flux_lucid::beam_tolerance::{compute_tolerance, classify_precision};

// Steel (stakes > 0.75): E=200 GPa → tolerance ~0.05
let tol = compute_tolerance(0.9, 1.0);
assert!(tol < 0.1);

// Rubber (stakes < 0.1): E=0.01 GPa → tolerance ~1.0
let tol = compute_tolerance(0.05, 1.0);
assert!(tol > 0.5);

// Classify precision directly
assert_eq!(classify_precision(0.9, 1.0), Precision::DUAL);
assert_eq!(classify_precision(0.05, 1.0), Precision::INT8);
```

### Mixed-Precision Batch (SoA)

Groups constraints by precision class into struct-of-arrays for cache-friendly AVX-512 execution:

```rust
use flux_lucid::soa_emitter::SoABatch;

let constraints = vec![
    (5.0, 0.0, 10.0, 0.1),     // INT8
    (500.0, 0.0, 1000.0, 0.6), // INT32
    (5000.0, 0.0, 10000.0, 0.9), // DUAL
];
let batch = SoABatch::from_constraints(&constraints);
let results = batch.check_all();
let (actual_bits, baseline_bits) = batch.memory_stats();
```

Typical sensor mixes save **50–70% memory** vs uniform INT32.

### Divergence-Aware Tolerance Adjustment

Connects runtime drift detection to compile-time constraint tolerance. When Oracle1/zeroclaw detects drift on a channel, tolerance tightens automatically — the compile↔runtime feedback loop.

```rust
use flux_lucid::divergence_tolerance::{DivergenceAwareTolerance, DriftTrend};

let mut dat = DivergenceAwareTolerance::new(&intent_vector, 0.9, 0.5);

// Drift observed on Stakes channel — tighten aggressively
dat.adjust(Channel::Stakes, 0.7, DriftTrend::Increasing);
dat.adjust(Channel::Stakes, 0.8, DriftTrend::Increasing);

// Effective tolerance shrinks
let effective = dat.effective_tolerance(Channel::Stakes);
assert!(effective < 0.5);

// Precision class auto-bumps to DUAL when drift > 10%
assert_eq!(dat.precision_classes()[Channel::Stakes as usize], PrecisionClass::DUAL);

// Decay adjustments as drift resolves
dat.decay();
```

Backed by real tests — no-drift, increasing-drift, decay-restore, max-tightening-capped, channel-independence, observation-counting all verified.

### XOR Dual-Path Verification

DUAL-classified constraints use two independent execution paths:

1. **Path A**: Direct comparison (`v >= lo && v <= hi`)
2. **Path B**: XOR-based signed→unsigned conversion (`v ^ 0x80000000`)

Both paths must agree. Catches silicon-level errors (rowhammer, cosmic ray bit flips) without doubling execution time — the XOR trick is branchless and pipeline-friendly.

### Intent-Directed Constraint Emission

Bridges 9-channel intent profiles to constraint compilation:

```rust
use flux_lucid::intent_emitter::emit_constraints;

let batch = emit_constraints(&profile, &specs);
```

---

## Components

| Crate | Role |
|-------|------|
| `constraint-theory-llvm` | CDCL → LLVM IR → AVX-512 |
| `holonomy-consensus` | GL(9) zero-holonomy consensus |
| `flux-lucid` | 9-channel intent + precision classification |

## Cargo Features

| Feature | Description |
|---------|-------------|
| `x86-64-emitter` | Direct AVX-512 emission (bypasses LLVM) |
| `jit` | JIT compilation via Cranelift |
| `fleet` | Full fleet coordination features |

## Modules

- **`beam_tolerance`** — Physical math (beam stiffness → precision class)
- **`divergence_tolerance`** — Runtime drift → compile-time tolerance tightening
- **`intent_compilation`** — Precision classification from C9 stakes
- **`intent_emitter`** — Intent-directed constraint batching
- **`soa_emitter`** — Struct-of-arrays mixed-precision batch execution
- **`navigation`** — Draft/safety checks
- **`head_direction`** — Directional intent alignment

## Status

**v0.1.6** — Active development. The constraint→precision mapping and mixed-precision SoA batch execution are real and tested. Fleet consensus and JIT features are scaffolding ready for the runtime integration layer.

## License

Apache-2.0
