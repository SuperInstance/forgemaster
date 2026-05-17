# Cycle 12 Results: Effective Rank Sweep — Mapping the Structural/Dynamical Transition

## Executive Summary

Mapped the transition between structural and dynamical conservation mechanisms using hybrid coupling C(x) = α·xx^T/N + (1-α)·R. **The transition is GRADUAL, not sharp.** In the structural regime (pure Hebbian), γ=1.0000 and H=0.0000 is a perfect algebraic identity. In the dynamical regime (full-rank R), CV stays low (~0.004–0.015) via eigenvector stability. The two mechanisms overlap in the α=0.85–0.95 region where both contribute.

## Experiment 1: Static Matrices (Control)

All effective ranks (1.0–5.0) give CV=0.0000 with static coupling. Confirms: static eigenvalues → trivially conserved.

## Experiment 2: State-Dependent Hybrid (α Sweep)

C(x) = α·xx^T/N + (1-α)·R, where R is a fixed random matrix (symmetric, positive-definite).

| α | CV(γ+H) | Rotation | eff_rank | γ | H | Mechanism |
|---|---------|----------|----------|---|---|-----------|
| 0.00 | 0.0000 | 0.0° | 3.69 | 3.40 | 1.31 | Static (R fixed) |
| 0.10 | 0.0026 | 0.7° | 3.56 | 3.22 | 1.27 | Static-dominated |
| 0.30 | 0.0069 | 2.0° | 3.63 | 3.33 | 1.29 | Mixed |
| 0.50 | 0.0083 | 1.3° | 3.56 | 3.23 | 1.27 | Mixed |
| 0.70 | 0.0055 | 1.8° | 3.74 | 3.44 | 1.31 | Mixed |
| 0.80 | 0.0103 | 2.0° | 3.70 | 3.42 | 1.31 | Hebbian growing |
| 0.90 | 0.0217 | 3.3° | 3.74 | 3.42 | 1.32 | Hebbian-dominated |
| 0.95 | 0.0325 | 10.0° | 3.75 | 3.41 | 1.32 | Transition zone |
| **1.00** | **0.0000** | **66.4°** | **1.00** | **1.00** | **0.00** | **Structural** |

### Key Observation: The "Valley" at α=1.0

CV peaks at α≈0.95 (0.033) then DROPS to 0.000 at α=1.0. The effective rank collapses from ~3.7 to 1.0 at α=1.0. This is the structural mechanism taking over: rank-1 C(x) has γ=1, H=0 as an exact identity.

The α=0.95 point is the WORST conservation: Hebbian part is dominant (creating large state-dependent eigenvalue variation) but not yet rank-1 (so structural identity doesn't apply). The matrix fluctuates between rank-1-ish and rank-3-ish, causing maximum γ+H variation.

## Experiment 3: γ+H Decomposition (Pure Hebbian SD)

ALL 10 samples: γ = 1.0000 (std=0.000000), H = 0.0000 (std=0.000000), γ+H = 1.0000.

**This is a perfect algebraic identity.** For rank-1 matrix C = xx^T/N:
- Single eigenvalue: λ₁ = ||x||²/N, all others zero
- Participation: γ = (λ₁)²/(λ₁)² = 1 (exactly)
- Entropy: H = -1·ln(1) = 0 (exactly)

The structural regime doesn't just APPROXIMATE conservation — it's an exact mathematical identity.

## Experiment 4: Fine-Grained α Sweep

| α range | CV(γ+H) | Rotation | Behavior |
|---------|---------|----------|----------|
| 0.00–0.20 | 0.001–0.004 | 0–2.5° | R dominates, near-static coupling |
| 0.20–0.80 | 0.004–0.012 | 0.8–2.5° | Stable plateau, mixed regime |
| 0.80–0.90 | 0.011–0.016 | 1.8–3.8° | Hebbian growing, CV increasing |
| 0.95 | 0.049 | 12.0° | **Peak CV** — transition zone |
| 1.00 | 0.000 | 68.0° | Structural regime (rank-1 collapse) |

**The transition is GRADUAL on both sides of the peak but SHARP at α=1.0** (structural collapse). The effective rank stays ~3.5–3.7 for all α<1.0, then drops to 1.0 discontinuously.

## Experiment 5: Eigenvalue-Engineered Effective Rank

Engineered C(x) with fixed eigenvalue spectra (target rank 1.0–5.0) but Hebbian eigenvectors.

**ALL conditions: CV=0.0000.** Even with 17–66° eigenvector rotation.

### Critical Finding: Fixed Spectrum → Perfect Conservation

When the eigenvalue SHAPE is held constant (even as eigenvectors rotate freely), γ+H is trivially conserved. This means:

1. **Conservation failure comes from eigenvalue SHAPE variation**, not eigenvector rotation
2. **Eigenvector rotation is a PROXY** for eigenvalue shape variation (correlated but not causal)
3. **The true driver is how much the spectral distribution changes with state**

This revises Cycle 10's framework: eigenvector rotation predicts conservation because it CORRELATES with spectral variation, but the causal mechanism is spectral shape stability.

## Synthesis: Three Conservation Regimes

```
Regime 1: STRUCTURAL (eff_rank = 1.0)
  - Mechanism: Algebraic identity (γ=1, H=0)
  - CV = 0.0000 exactly
  - Eigenvector rotation: IRRELEVANT (up to 66° → still perfect)
  - Example: Pure Hebbian SD

Regime 2: DYNAMICAL (eff_rank > 1, stable spectrum)
  - Mechanism: Eigenvalue shape stability under state-dependent coupling
  - CV ≈ 0.004–0.015
  - Rotation: 1–3° (low, because R is static)
  - Example: Attention SD with high τ

Regime 3: TRANSITIONAL (eff_rank fluctuates)
  - Mechanism: Neither structural nor dynamical dominates
  - CV ≈ 0.02–0.05
  - Rotation: 3–12° (moderate)
  - Example: Hybrid α=0.85–0.95
  - The Hebbian part creates spectral instability without rank-1 collapse
```

## Answers to Mission Questions

### 1. Effective Rank Sweep
The transition is **NOT a function of effective rank alone.** All α<1.0 have eff_rank ~3.5–3.7 regardless of α. The effective rank only collapses at α=1.0. What matters is the **fraction of coupling that is state-dependent** AND the **spectral shape of the state-dependent component.**

### 2. Rank Threshold
**No sharp threshold at a specific rank value.** The transition from dynamical to structural is discontinuous at α=1.0 (rank drops from ~3.7 to 1.0). But in terms of CV behavior, the transition is gradual (CV peaks at α=0.95 then drops). The "threshold" is binary: either C(x) is rank-1 (structural) or it's not (dynamical/transitional).

### 3. Decompose γ+H
**CONFIRMED:** In the structural regime, γ=1.0000 and H=0.0000 are EXACT algebraic identities of rank-1 matrices. Not approximate — exact to machine precision. No other algebraic identities found; this IS the structural mechanism.

### 4. Hybrid Coupling
CV follows a **non-monotonic curve**: low at α=0 (static R), increases to peak at α≈0.95 (maximum spectral instability), then collapses to 0 at α=1.0 (structural identity). The peak at α=0.95 occurs because the Hebbian component creates large eigenvalue swings without the rank-1 safety net.

## Revised Theory

```
Conservation = f(spectral shape stability)

Structural: C(x) is rank-1 → spectral shape is trivially stable → γ=1, H=0
Dynamical: C(x) has stable spectral shape → γ+H ≈ constant
Transitional: C(x) spectral shape fluctuates → γ+H varies

Eigenvector rotation is a CORRELATE, not a CAUSE, of conservation quality.
The causal variable is eigenvalue SHAPE stability under state evolution.
```

## Open Questions for Cycle 13
1. **What makes spectral shape stable?** Is it related to Tr(C^k) moments being conserved?
2. **Can we measure "spectral shape stability" directly** rather than using eigenvector rotation as proxy?
3. **Does the structural regime generalize to rank-2?** Rank-2 C(x) = u·u^T + v·v^T — does it have a similar algebraic identity?
4. **Can we engineer coupling that smoothly interpolates structural→dynamical** without the CV peak at the transition?
5. **Real attention layers:** What is the effective rank of attention coupling in trained transformers?
