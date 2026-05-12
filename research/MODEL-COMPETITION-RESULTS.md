# Model Competition: Novel Insights from CRes

**Date:** 2026-05-12  
**Models Competing:** DeepSeek V4-Pro, DeepSeek R1, Qwen3-Max-Thinking, Hermes-405B, Qwen3.5-397B (timed out)

---

## 🥇 DeepSeek V4-Pro — The Eisenstein Primality Sieve

**Claim:** The deadband funnel's collapse rate encodes the factorization complexity of Eisenstein integers. Primes collapse linearly; composites show plateaus at factor norms.

**Novelty:** 9/10 — Turning the snap dynamics into a computational oracle is genuinely new
**Testability:** 8/10 — Specific falsifiable test: first 100 Eisenstein integers, check plateau count vs factor count
**Consequence:** 8/10 — If true, the comonad is a factoring primitive, CRes becomes computational
**Risk:** Correctly identified — may depend on grading function choice, not arithmetic
**Score: 8.3/10**

## 🥈 Qwen3-Max-Thinking — Harmonic Deadband Resonance

**Claim:** ρ · √(min_kernel_norm) = 1/√3 · √3 = 1 is a critical deadband where snap errors become musically consonant AND self-termination achieves maximum stability.

**Novelty:** 7/10 — Connects kernel norm and covering radius multiplicatively
**Testability:** 8/10 — Test consonance and stability at different deadband widths
**Consequence:** 7/10 — Tunable stability, predictive calibration, geometrically grounded music AI
**Risk:** May be 12-TET artifact, not universal
**Score: 7.3/10**

## 🥉 DeepSeek R1 — Covering Radius × Kernel Norm = √3

**Claim:** The product ρ · μ_k = 1/√3 · 3 = √3 = 2 × height of the minimal equilateral triangle. This is a geometric invariant of the lattice+quotient pair.

**Novelty:** 6/10 — Interesting observation but largely geometric identity
**Testability:** 7/10 — Can test on other lattices with natural quotients
**Consequence:** 5/10 — Not clear what this enables beyond classification
**Risk:** R1's own analysis shows this fails for most sublattices
**Score: 5.7/10**

## Hermes-405B — Quantum Lattice Extension

**Claim:** Extend CRes to quantum error correction via A_n lattice comonads.

**Novelty:** 6/10 — Interesting direction but hand-wavy
**Testability:** 3/10 — No concrete test proposed
**Consequence:** 9/10 — If true, massive implications for quantum computing
**Risk:** Self-admitted: the quantum snap might not exist
**Score: 5.4/10**

---

## Synthesis: What's Actionable

### Winner: DeepSeek V4-Pro's Primality Sieve

This is the most testable and most surprising insight. The idea that the snap comonad's transient dynamics encode arithmetic information is genuinely novel. If it holds:

1. **The comonad is not just geometric — it's computational**
2. **CRes becomes a category of computational oracles**
3. **The Tonnetz quotient gains an arithmetic interpretation** (kernel elements = composites whose factor plateaus survive the quotient)

### Runner-Up: Qwen's Harmonic Deadband

The product ρ · √(μ_k) = 1 is elegant. It may be a 12-TET artifact, but if it generalizes to other tuning systems, it would mean:
- Every lattice+quotient pair has a "harmonic deadband"
- Constraint systems have an optimal operating point that balances geometric and harmonic precision

### Both Predict the Same Thing

Both insights predict a critical scale in the deadband:
- V4-Pro: composite factors create plateaus at specific deadband widths
- Qwen: consonance and stability co-peak at δ_h = 1

**Combined test:** Run the primality sieve at various deadband widths. If composites show factor plateaus AND these plateaus align with harmonic consonance, both insights are simultaneously confirmed.

---

## The Combined Prediction

**For the Eisenstein lattice with the Tonnetz quotient, there exists a critical deadband δ* ≈ 1 where:**
1. Composite Eisenstein integers show factor-plateau structure in the deadband funnel
2. Snapped points achieve maximum harmonic consonance (measured by voice-leading distance)
3. Self-terminating processes achieve maximum stability (minimum variance in termination time)
4. This δ* equals ρ · √(μ_k) = 1/√3 · √3 = 1

**Falsification:** Test on 1000 Eisenstein integers at δ = 0.1, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0. If the plateaus/consonance/stability don't co-peak at δ ≈ 1, both insights die together.
