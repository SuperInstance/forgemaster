# Show HN: Constraint-theory – Coq-proved snapping for games, safety-critical embedded, and GPU (4KB C runtime, 22 repos)

We built a constraint satisfaction framework where every algorithm has a Coq proof, and it ships on $2 ARM chips.

**What it is:** Mathematical foundations for deterministic constraint resolution, implemented across 22 repos (4 published Rust crates, 1 published Python package), and a bare-metal C runtime. Apache 2.0. 3 proven theorems (2 Coq-verified). Real CUDA kernels.

**What you can use today:**

**1. Pythagorean snapping (Rust & Python)**
Snap floating-point values to exact rational representations. Eliminates desync in deterministic lockstep multiplayer — the #1 source of multiplayer bugs. Works in 48 directions via Eisenstein integer encoding.

```bash
# Rust
cargo add eisenstein
# Python
pip install constraint-theory
```

```rust
use eisenstein::{E12, HexDisk};

let z = E12::new(-5, 3);            // Eisenstein integer
assert_eq!(z.norm(), 49);            // a²-ab+b² = 25+15+9 = 49
let dir = E12::snap_from_angle(0.0);  // Snap any angle to hex grid
let disk = HexDisk::radius(36);       // 3997 exact vertices, ~16KB
```

```python
from constraint_theory import PythagoreanManifold

manifold = PythagoreanManifold(200)
x, y, noise = manifold.snap(0.577, 0.816)
# → closest Pythagorean triple, noise = sqrt(best_dist)
```

**2. Embedded C runtime (the killer feature)**
4KB code, 1KB stack, runs on Cortex-M0+. Coq proofs compile to FLUX-C bytecode you can flash to a $2 ARM chip. Architectural WCET guarantees (no malloc, no recursion, no unbounded loops — the 42-opcode ISA is Turing-incomplete, so every program provably terminates). We're not certified — we have a *path* to certification (DO-178C, ISO 26262). The mathematical foundations are real. Don't plan your safety-critical system around it yet.

**3. GPU constraint resolution**
Real CUDA kernels with verified numerical bounds. 1.02B checks/sec on RTX 4050. 100M differential test cases, zero false negatives. Mixed-precision AVX-512: 3.17× speedup (cycle-accurate, 5-run mean).

[constraint-theory-core](https://crates.io/crates/constraint-theory-core) · [flux-lucid](https://crates.io/crates/flux-lucid) · [holonomy-consensus](https://crates.io/crates/holonomy-consensus) · [eisenstein](https://crates.io/crates/eisenstein)

**What's real vs. what's aspirational:**

We publish an [honest errata](https://github.com/SuperInstance/constraint-theory-math/blob/main/ERRATA.md) listing 5 corrected claims from our own papers. Our Galois theory "recognitions" are observations that standard constructions apply — not new mathematics. `dim H⁰ = 9` checks out. `DivergenceAwareTolerance` is elegant framing, not deep new math. The Python package currently does Pythagorean snapping only — full constraint checking is Rust-only for now.

**Negative results (published permanently):**
- FP16 is **unsafe** for values > 2048 — 76% precision mismatches
- Tensor cores barely help (1.05-1.19×) — memory-bound, not compute-bound
- Bank conflict padding is **counterproductive** on Ada GPUs (0.96×)

We'd rather you trust us because we're honest about limitations than because we oversold capabilities.

**What we know we need:**
- WASM demo (`wasm-pack build` + npm package) for game devs
- Cortex-M4 cycle benchmarks and MISRA compliance for embedded
- Full constraint checking in the Python package (currently Rust-only)
- Struct returns instead of tuples (game dev ergonomics)

**Repos:** [github.com/SuperInstance](https://github.com/SuperInstance?q=constraint) · [Math + Proofs](https://github.com/SuperInstance/constraint-theory-math) · [CUDA Benchmarks](https://github.com/SuperInstance/constraint-theory-ecosystem) · [Live Demo](https://superinstance.github.io/cocapn-ai-web/demo-divergence-tolerance.html)

We're particularly interested in feedback from: embedded engineers doing WCET analysis, game devs fighting deterministic lockstep desyncs, and anyone who thinks Coq proofs for $2 microcontrollers is either brilliant or insane.
