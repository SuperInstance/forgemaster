# Constraint Theory Math

**Math for people who check bounds for a living.**

We built a mixed-precision constraint checker — sometimes int8, sometimes int32, sometimes both — and discovered it sits on top of genuine mathematical structure. This repo is the proof.

Why care? Because constraint satisfaction is everywhere — sensor validation, fleet coordination, real-time control — and the math tells you *when you can trust a fast approximation* and *when you can't*.

---

## What's Here

| Status | Result | File |
|--------|--------|------|
| ✅ Proven | INT8 is sound on [-127, 127] | [`paper/PAPER.md`](paper/PAPER.md) §3.1 |
| ✅ Proven | XOR flip is an order isomorphism | [`proofs/XOR-ISOMORPHISM.v`](proofs/XOR-ISOMORPHISM.v) |
| ✅ Proven | dim H⁰ = 9 on a tree | [`proofs/PROOF-DIM-H0-EQUALS-9.md`](proofs/PROOF-DIM-H0-EQUALS-9.md) |
| ✅ Proven | Bloom filters are a Heyting algebra | [`paper/PAPER.md`](paper/PAPER.md) §4 |
| 🔶 Conjecture | Consistency–Holonomy Correspondence | [`proposed/CONSISTENCY-HOLONOMY-CORRESPONDENCE.md`](proposed/CONSISTENCY-HOLONOMY-CORRESPONDENCE.md) |
| 🔶 Conjecture | Galois Unification Principle | [`proposed/GALOIS-UNIFICATION-PROOFS.md`](proposed/GALOIS-UNIFICATION-PROOFS.md) |
| 🔶 Partial | Intent–Holonomy Duality (one direction) | [`proposed/INTENT-HOLONOMY-DUALITY-ATTEMPT.md`](proposed/INTENT-HOLONOMY-DUALITY-ATTEMPT.md) |
| ❌ Debunked | Beam-Intent Equivalence | [`proposed/DEBUNKED-BEAM-INTENT.md`](proposed/DEBUNKED-BEAM-INTENT.md) |

---

## The Three Proven Theorems

### 1. INT8 Soundness — Your fast check isn't lying

**The claim:** If all your values fit in [-127, 127], then `int8_comparison == int32_comparison`. Always.

**Why it matters:** This is the mathematical justification for running 4× more constraint checks per cycle by dropping to int8 on AVX-512. The proof is one line: the int8 cast is the identity on this range.

```python
# The cast: f(x) = ((x + 128) % 256) - 128
# For x in [-127, 127]: x + 128 is in [1, 255], no wraparound, so f(x) = x
# Therefore: int8(v >= lo and v <= hi) == (v >= lo and v <= hi) for all v,lo,hi in [-127,127]

def int8_sound(v, lo, hi):
    """Works because cast is identity on [-127, 127]."""
    return (int8(v) >= int8(lo)) and (int8(v) <= int8(hi))
    # Identical result to: (v >= lo) and (v <= hi)
```

This is a Galois connection between the interval sublattice [-127, 127] ⊂ ℤ and the int8 lattice. The inclusion is the lower adjoint; restriction is the upper adjoint. Standard math, applied to a real optimization.

### 2. XOR Order Isomorphism — Signed ↔ unsigned for free

**The claim:** `g(x) = x ^ 0x80000000` is a bijective order isomorphism from signed to unsigned 32-bit integers.

**Why it matters:** You can verify a signed comparison by flipping the sign bit and doing an unsigned comparison. If both disagree, you have a hardware fault. This gives you overflow-safe dual-path verification with one XOR instruction.

```c
// Flip the sign bit → converts signed ordering to unsigned ordering
uint32_t g(uint32_t x) { return x ^ 0x80000000; }

// Dual verification: signed path AND unsigned path must agree
bool check(int32_t v, int32_t lo, int32_t hi) {
    bool signed_ok   = (v >= lo) && (v <= hi);
    bool unsigned_ok  = (g(v) >= g(lo)) && (g(v) <= g(hi));
    assert(signed_ok == unsigned_ok);  // hardware fault if not
    return signed_ok;
}
```

The proof: in two's complement, the sign bit has weight -2³¹ signed and +2³¹ unsigned. XOR flips only this bit, equivalent to adding 2³¹ mod 2³². Addition by a constant is strictly increasing, so order is preserved. Bijectivity follows from g∘g = id.

### 3. dim H⁰ = 9 — Global consistency needs exactly 9 parameters

**The claim:** On a tree-shaped network with 9 channels per node, the space of globally consistent states has dimension exactly 9.

**Why it matters:** If you have 100 agents in a tree topology, each tracking 9 intent channels, you don't need 900 parameters for global consistency. You need 9 — one vector at the root, propagated through the edges. Adding cycles (redundant paths) doesn't add dimensions; it adds constraints.

```python
# Tree = unique path between any two nodes
# Pick a root, propagate values along edges
# Each edge carries an invertible map T_e: R^9 -> R^9

def propagate(root_value, tree, edge_maps):
    """Global state from a single 9-vector. dim H^0 = 9."""
    state = {root: root_value}
    for parent, child in tree_edges_bfs(tree):
        state[child] = edge_maps[(parent, child)] @ state[parent]
    return state  # globally consistent by construction
```

Proof is by root propagation isomorphism (Φ: V_root → H⁰ is bijective). For graphs with cycles, dim H⁰ ≤ 9 + 9·β₁ where β₁ is the number of independent cycles.

---

## Bloom Filters Live in Intuitionistic Logic

A Bloom filter has two answers: "definitely not present" (certain) and "possibly present" (uncertain). This is not classical logic. The "possibly present" answer satisfies neither P nor ¬P — the law of excluded middle fails.

This makes the Bloom filter state space a **Heyting algebra** (not a Boolean algebra). The definitive answer is the negative one — "definitely not present." This connects to the core insight:

> **Negative knowledge is the primary computational resource.** Knowing where violations *are not* eliminates the majority of checks.

A 67% DNP rate means 67% of exact checks are skipped with zero false confirms.

---

## What's Not Proven (Yet)

### Consistency–Holonomy Correspondence
Global constraint consistency ↔ flat connection on a GL(9) bundle ↔ vanishing Čech class. The (a)⟹(b) direction works; the full equivalence remains open.

### Galois Unification Principle
Six structures — XOR, INT8, Bloom, quantization, alignment, holonomy — all share the same Galois connection pattern: a lower adjoint (approximation) and upper adjoint (reconstruction) with conservative approximation and information loss. This is an observation that standard constructions apply, not new mathematics.

### Intent–Holonomy Duality
One direction partially proven. The converse requires fixed-point strengthening that hasn't been shown. Internal confidence: ~30%.

---

## What We Got Wrong

Full details in [`ERRATA.md`](ERRATA.md). The important ones:

| Claim | Reality | Fix |
|-------|---------|-----|
| 24-bit norm bound for Eisenstein coords | Overflows for a=4096, b=-4096 (49M > 16M) | i32 is correct; docs updated |
| 11 D6 orbits | Should be 13 | Fixed by enumeration |
| 1.5× Laman redundancy | True for infinite lattice only | Bounded regions: ~1.38-1.44× |
| Temporal snap is a Galois connection | No poset structure, multi-valued maps | Demoted to conjecture |
| Intent-Holonomy "duality" | Only one direction proven | Marked as partial |

**Honesty note:** The Galois "recognitions" in §6 of the paper are observations that standard constructions apply to our specific structures — not new theorems. The three proven results are genuine. The conjectures may or may not pan out.

---

## Also in This Repo

- **[`eisenstein-triples/`](eisenstein-triples/)** — Eisenstein integer triples (73% denser than Pythagorean), verified with Python
- **[`hex-zhc/`](hex-zhc/)** — Hex lattice constraint checking with Laman rigidity analysis
- **[`galois-unification-visualizer.py`](galois-unification-visualizer.py)** — Visual demo of the six Galois connections

## Structure

```
paper/           — Full paper with all proofs and definitions
proofs/          — Coq proof (XOR) + Markdown proof (dim H⁰ = 9)
proposed/        — Conjectures, proof sketches, DeepSeek analyses
eisenstein-triples/  — Eisenstein triple enumeration and verification
hex-zhc/         — Hex lattice rigidity analysis and benchmarks
```

## License

MIT

— *Forgemaster ⚒️, Cocapn Fleet*
