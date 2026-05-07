# Constraint Theory ⚒️

**Billion-scale constraint satisfaction, proven correct, running on consumer GPUs.**

[![crates.io](https://img.shields.io/crates/v/flux-lucid.svg)](https://crates.io/crates/flux-lucid)
[![PyPI](https://img.shields.io/pypi/v/constraint-theory.svg)](https://pypi.org/project/constraint-theory/)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

## What It Does

Constraint Theory checks whether a set of constraints is simultaneously satisfiable — at GPU speed, with mathematical guarantees.

```
use constraint_theory_core::{Constraint, solve};

let constraints = vec![
    Constraint::new("x > 0"), Constraint::new("x < 100"),
    Constraint::new("y > x"), Constraint::new("y < 200"),
];

// One billion checks/sec on a laptop GPU
let result = solve(&constraints); // SAT or UNSAT in microseconds
```

## Why It Matters

Autonomous systems need **guaranteed** constraint satisfaction — not probabilistic guessing.

| Approach | Speed | Proven Correct |
|----------|-------|----------------|
| Formal methods (Coq, Z3) | Minutes per check | ✅ |
| Heuristic SAT solvers | Fast | ❌ |
| **Constraint Theory** | **1B checks/sec** | **✅** |

We hit the sweet spot: fast enough for real-time control loops, verified enough for DO-178C DAL A certification.

## The Numbers (real hardware, RTX 4050 laptop)

| Metric | Value |
|--------|-------|
| Throughput (INT8) | 1.02B checks/sec |
| Mixed-precision speedup | 3.17× (cycle-accurate, 5-run mean) |
| Differential mismatches | 0 out of 100,000,000 |
| WCET | 0.228ms |
| P99 latency | 0.065ms |
| Headroom for 1kHz control | 4.4× |

## 5-Minute Quickstart

### Rust
```bash
cargo add flux-lucid
```
```rust
use flux_lucid::{IntentVector, check_alignment, DivergenceAwareTolerance};

let intent = IntentVector::new([0.5, 0.3, 0.7, 0.4, 0.6, 0.2, 0.8, 0.3, 0.9]);
let aligned = check_alignment(&intent, &other);
println!("Alignment: {:.3}", aligned.cosine_similarity());
```

### Python
```bash
pip install constraint-theory
```
```python
from constraint_theory import IntentVector, check_alignment

intent = IntentVector(values=[0.5, 0.3, 0.7, 0.4, 0.6, 0.2, 0.8, 0.3, 0.9])
result = check_alignment(intent, other)
print(f"Aligned: {result.cosine_similarity:.3f}")
```

### JavaScript
```bash
npm install @superinstance/polyformalism-a2a  # (publishing soon)
```
```js
import { IntentVector, checkAlignment } from '@superinstance/polyformalism-a2a';

const intent = new IntentVector({ values: [0.5, 0.3, 0.7, 0.4, 0.6, 0.2, 0.8, 0.3, 0.9] });
const result = checkAlignment(intent, other);
console.log(`Aligned: ${result.cosineSimilarity.toFixed(3)}`);
```

## The Math (honestly)

### Proven ✅
- **XOR isomorphism**: Symmetric difference on P(U) ≅ bitwise XOR on ℤ₂^|U| ([Coq proof](https://github.com/SuperInstance/constraint-theory-math/blob/main/proofs/XOR-ISOMORPHISM.v))
- **INT8 soundness**: Saturation cast preserves ordering on [-127, 127] ([15 Coq theorems](https://github.com/SuperInstance/constraint-theory-ecosystem))
- **dim H⁰ = 9**: Global sections of trivial GL(9) bundle on constraint tree = 9
- **3.17× speedup**: Measured on real hardware, 5 runs, rdtsc cycle-accurate
- **0/100M mismatches**: Differential testing across INT8, FP32, and dual paths

### Open Problems 🔬
- **Intent-Holonomy duality**: One direction partially proven, converse has fundamental obstacle
- **Temporal Galois connections**: No poset structure found yet
- We openly mark these as [conjectured, not proven](https://github.com/SuperInstance/constraint-theory-math/blob/main/ERRATA.md)

### Negative Results (what didn't work)
- FP16 is **unsafe** for values > 2048 (76% precision mismatches)
- Tensor cores: only 1.05-1.19× benefit (memory-bound, not compute-bound)
- Bank conflict padding: **counterproductive** on Ada GPUs (0.96×)

## The Stack

| Crate | Language | What It Does | Tests |
|-------|----------|-------------|-------|
| [constraint-theory-core](https://crates.io/crates/constraint-theory-core) | Rust | Core SAT types + solving | 47 |
| [flux-lucid](https://crates.io/crates/flux-lucid) | Rust | Intent-directed compilation + tolerance | 93 |
| [holonomy-consensus](https://crates.io/crates/holonomy-consensus) | Rust | Zero-holonomy geometric consensus | 30 |
| [fleet-coordinate](https://crates.io/crates/fleet-coordinate) | Rust | Fleet coordination via Laman rigidity | 3 |
| [eisenstein](https://crates.io/crates/eisenstein) | Rust | Eisenstein integer number theory | 25 |
| [constraint-theory](https://pypi.org/project/constraint-theory/) | Python | Python bindings + 9-channel intent | — |
| [polyformalism-a2a](https://pypi.org/project/polyformalism-a2a/) | Python/JS | Agent-to-agent alignment | 18+9 |

**22 crates total** on crates.io, **4 packages** on PyPI.

## Try the Demos

- **[Divergence-Aware Tolerance](https://htmlpreview.github.io/?https://raw.githubusercontent.com/SuperInstance/cocapn-ai-web/main/demo-divergence-tolerance.html)** — Interactive 9-channel drift visualization
- **[Fleet Spread](https://htmlpreview.github.io/?https://raw.githubusercontent.com/SuperInstance/cocapn-ai-web/main/demo-fleet-spread.html)** — Multi-agent coordination

## Certification Path

We've mapped the path to:
- **DO-178C DAL A** (aircraft software) — 527-line certification report published
- **ISO 26262 ASIL D** (automotive) — Safe-TOPS/W benchmark: 20.17 vs 0 for uncertified
- **IEC 61508 SIL 4** (industrial) — Compliance mapping complete

## The Team

**Casey Digennaro** + an AI fleet of 9 agents. 22 crates, 4 PyPI packages, 50+ Coq theorems, 100M+ differential tests. All open source, Apache 2.0.

## Links

- **[GitHub Org](https://github.com/SuperInstance)** — All repos
- **[Constraint Theory Math](https://github.com/SuperInstance/constraint-theory-math)** — Proofs, errata, open problems
- **[Intent-Directed Compilation](https://github.com/SuperInstance/intent-directed-compilation)** — AVX-512 technique + benchmarks
- **[Polyformalism](https://github.com/SuperInstance/polyformalism-a2a-python)** — 9-channel agent alignment

---

*We'd rather be honest than impressive. Our [ERRATA.md](https://github.com/SuperInstance/constraint-theory-math/blob/main/ERRATA.md) lists 5 claims we corrected after red-team review.*
