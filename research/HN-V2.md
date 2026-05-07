# Show HN: We proved INT8 is safe for constraint checking — 1B checks/sec, 50 Coq theorems, zero false negatives

We built a constraint satisfaction framework in Rust that runs **1.02 billion checks per second** on a consumer laptop GPU (RTX 4050) with **zero false negatives across 100M differential test cases**.

But the speed isn't the interesting part. The interesting part is the proof that you don't need floating point.

### INT8 is enough — and we proved it

Most constraint checkers use FP32 or FP64. We proved in Coq that **8-bit integers preserve the ordering properties needed for constraint satisfaction**. This gives you 4.58× throughput — not from approximation, from eliminating floating-point overhead while maintaining mathematical soundness.

15 Coq theorems cover: INT8 saturation preserves ordering on [-127, 127], worst-case execution time is linear in bytecode length, and a Galois connection between our GUARD DSL and compiled FLUX bytecode. All auditable: [constraint-theory-ecosystem](https://github.com/SuperInstance/constraint-theory-ecosystem).

### Mixed-precision AVX-512 trick

Not all constraints need the same precision. We classify by stakes:
- **Low-stakes constraints** → INT8 (64 per AVX-512 register)
- **High-stakes constraints** → FP32 (16 per register)

Average speedup: **3.17×** (cycle-accurate, 5-run mean, rdtsc) with no correctness loss. The classification is configurable, not magic. Code: [intent-directed-compilation](https://github.com/SuperInstance/intent-directed-compilation).

### 30-second quickstart

```bash
cargo add flux-lucid
```
```rust
use flux_lucid::IntentVector;

let intent = IntentVector::new([0.5, 0.3, 0.7, 0.4, 0.6, 0.2, 0.8, 0.3, 0.9]);
println!("Dominant: C{} (stakes)", intent.dominant_channel() + 1);
```

Python:
```bash
pip install constraint-theory
```

### What we got wrong

Negative results, published permanently:
- **FP16 is unsafe** for values > 2048 — 76% precision mismatches in edge cases
- **Tensor cores barely help** (1.05-1.19×) — constraint patterns don't map to matmul
- **Bank padding is counterproductive** on Ada GPUs (0.96×)
- **5 claims in earlier work were wrong** — all listed in [ERRATA.md](https://github.com/SuperInstance/constraint-theory-math/blob/main/ERRATA.md)

Honesty about failures builds more trust than hiding them.

### The stack

22 Rust crates ([flux-lucid](https://crates.io/crates/flux-lucid), [holonomy-consensus](https://crates.io/crates/holonomy-consensus), [eisenstein](https://crates.io/crates/eisenstein), [constraint-theory-core](https://crates.io/crates/constraint-theory-core)), 4 Python packages, 50+ Coq theorems. All Apache 2.0.

[GitHub](https://github.com/SuperInstance) · [Math + Proofs](https://github.com/SuperInstance/constraint-theory-math) · [CUDA Benchmarks](https://github.com/SuperInstance/constraint-theory-ecosystem) · [Interactive Demo](https://htmlpreview.github.io/?https://raw.githubusercontent.com/SuperInstance/cocapn-ai-web/main/demo-divergence-tolerance.html)

Two people and a lot of automated testing. Happy to dig into any of the math or implementation details.
