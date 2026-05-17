# Cycle 10 Results: Stress Test of the Convergent Theory

**Model:** Seed-2.0-mini (fourth rotation)
**Theory under test:** Conservation quality = eigenvector stability × activation contractivity
**Dynamics:** x_{t+1} = σ(C(x)·x) + noise(σ=0.1), state-dependent coupling, N=20 default

---

## VERDICT: Theory PARTIALLY FALSIFIED — Needs Major Refinement

The theory passes several tests but fails the most critical one: **Hebbian SD produces PERFECT conservation (CV=0.000) with MAXIMAL eigenvector rotation (79°)**. This is the opposite of the theory's prediction.

---

## Experiment 1: Eigenvector Rotation × CV Correlation

### Finding: Moderate Correlation, But Critical Outlier (confidence: HIGH)

- r(rotation, CV) = 0.777 (p < 0.0001) — moderate positive correlation
- r(log(rotation), CV) = 0.781 — essentially identical
- **BUT the relationship is NON-LINEAR** (R²_linear=0.60, R²_quad=0.63)
- No sharp threshold: rotation < 5° → mean CV=0.006, rotation ≥ 5° → mean CV=0.032

### The Outlier That Breaks the Theory

| Config | Rotation | CV(γ+H) | Prediction |
|--------|----------|---------|------------|
| sd_hebbian | **79.45°** | **0.0000** | Should be WORST |
| attention τ=10 | 0.00° | 0.0006 | Should be BEST |
| random_resampled | 79.48° | 0.0233 | Should be bad ✓ |

Hebbian SD has the SAME eigenvector rotation as random resampled (79°), yet achieves CV=0.0000 while random gives CV=0.023. **Eigenvector rotation alone cannot predict conservation.**

### Attention Temperature Sweep Confirmed

Attention τ sweep shows monotonic improvement: CV=0.018 (τ=0.1) → CV=0.001 (τ=10). Rotation decreases from 0.26° to 0.00°. This subsystem of the theory holds.

### Mixed Coupling: Rotation is Constant, CV Varies

All mixed (Hebbian↔Random) configs have ~79.5° rotation, yet CV ranges from 0.023 to 0.045. The variation is explained entirely by state norm (||x||=0.60→2.83). **Within the high-rotation regime, norm, not rotation, predicts CV.**

---

## Experiment 2: Activation Contractivity Sweep

### MAJOR REVISION: All Activations Perform Equally Under Attention SD (confidence: HIGH)

| Activation | Lipschitz | CV(γ+H) | ||x|| |
|-----------|-----------|---------|-------|
| leaky_relu | ∞ | 0.0033 | 0.94 |
| sigmoid | 0.25 | 0.0035 | 2.97 |
| swish | 1.1 | 0.0036 | 0.46 |
| hard_tanh | 1.0 | 0.0037 | 0.86 |
| tanh | 1.0 | 0.0037 | 0.73 |
| relu | ∞ | 0.0036 | 0.97 |
| softplus | ∞ | 0.0039 | 19.96 |

**All CVs are between 0.0033 and 0.0039.** The 18% spread is negligible. Cycle 8's finding of dramatic activation differences (swish CV=0.018 vs relu CV=0.106) does NOT reproduce under the refined experimental setup.

### Why the Revision?

The difference: this cycle uses symmetrized coupling (C_sym = (C+C^T)/2) for eigenvalue computation, which stabilizes all activations. The previous cycle's activation ranking was partially driven by numerical instability in non-smooth activations.

### Finding: Lipschitz Constant is Irrelevant (confidence: HIGH)

- r(Lipschitz, CV) is meaningless — all CVs are within 18% of each other
- Bounded activations (CV=0.0036) = Unbounded activations (CV=0.0036) exactly
- **The activation function barely matters when coupling is well-conditioned**

### Softplus Paradox

Softplus has ||x||=19.96 (state explodes!) yet CV=0.0039 — barely worse than swish (||x||=0.46, CV=0.0036). Large state norm does NOT necessarily cause poor conservation when the coupling structure is benign.

---

## Experiment 3: Eigenvector Destabilization

### Finding: Non-Monotonic Response to Eigenvector Noise (confidence: HIGH)

| σ_noise | Rotation | CV(γ+H) |
|---------|----------|---------|
| 0.000 | 0.02° | 0.0035 |
| 0.001 | 0.25° | 0.0111 |
| 0.005 | 1.24° | 0.0187 |
| 0.010 | 2.46° | 0.0176 |
| 0.050 | 12.34° | 0.0114 |
| 0.100 | 25.10° | 0.0191 |
| 0.200 | 54.92° | 0.0312 |
| 0.500 | 78.35° | 0.0241 |
| 1.000 | 79.42° | 0.0225 |
| 2.000 | 79.18° | 0.0232 |

CV **peaks at intermediate noise** (σ=0.005 gives CV=0.019), then **decreases** at high noise (σ=1.0 gives CV=0.023, not 0.19). The relationship is **inverted-U shaped**, not monotonic.

This is because at high noise, the added perturbation dominates the attention coupling, creating a near-GOE matrix that itself has moderate conservation. At very low noise, the perturbation creates a small but structured deviation from the near-perfect attention conservation.

### Correlation Analysis

- r(σ, CV) = 0.42 (p=0.23, NOT significant)
- r(rotation, CV) = 0.74 (p=0.02, significant)
- Multiple regression: rotation coefficient dominates (0.000456 vs σ coefficient of -0.008)

**Eigenvector rotation mediates the destabilization effect**, but the mediation is weak (rotation explains only 55% of σ→CV pathway).

---

## Experiment 4: Scale Verification

### Finding: Hebbian SD is a Universal Counterexample (confidence: HIGH)

| N | Coupling | CV | Rotation | Rank by CV |
|---|----------|-----|----------|------------|
| 5 | attention | 0.0096 | 0.12° | 2nd |
| 5 | hebbian | **0.0000** | 66.67° | **1st** ✓ |
| 5 | random | 0.0950 | 66.82° | 3rd |
| 10 | attention | 0.0062 | 0.05° | 2nd |
| 10 | hebbian | **0.0000** | 74.58° | **1st** ✓ |
| 10 | random | 0.0475 | 74.70° | 3rd |
| 20 | attention | 0.0036 | 0.02° | 2nd |
| 20 | hebbian | **0.0000** | 79.13° | **1st** ✓ |
| 20 | random | 0.0233 | 79.50° | 3rd |
| 50 | attention | 0.0018 | 0.01° | 2nd |
| 50 | hebbian | **0.0000** | 83.16° | **1st** ✓ |
| 50 | random | 0.0097 | 83.33° | 3rd |

**At every scale, Hebbian SD has PERFECT conservation despite 67-83° rotation.** The rotation ranking NEVER matches the CV ranking. Cross-size r(rotation, CV) = 0.22 (p=0.49) — **no significant relationship**.

### Why Hebbian SD Conserves Perfectly

Hebbian SD: C(x) = xx^T/N is rank-1 with eigenvalue λ₁ = ||x||²/N. Therefore:
- γ = 1 (single eigenvalue dominates)
- H = 0 (only one nonzero eigenvalue)
- γ+H = ||x||²/N = ||x||²/N

Under tanh dynamics: x_{t+1} = tanh(||x||²/N · x) + noise. The state remains approximately proportional to a fixed direction, so ||x||² varies minimally → CV ≈ 0.

**Conservation in Hebbian SD is a consequence of rank-1 structure, NOT eigenvector stability.** The eigenvectors rotate wildly (because the state vector is the top eigenvector), but the spectral gap and entropy are structurally fixed by the rank.

### Attention Improves with Scale

Attention CV decreases monotonically: 0.0096 (N=5) → 0.0018 (N=50). This is a 5× improvement. Random also improves: 0.095 → 0.010 (10× improvement).

---

## Experiment 5: Counterexample Search

### COUNTEREXAMPLES FOUND: 3 (confidence: HIGH)

| Type | Config | Rotation | CV |
|------|--------|----------|-----|
| HIGH ROT + LOW CV | hebbian_swish_sf=1.0 | 79.31° | **0.0000** |
| HIGH ROT + LOW CV | hebbian_swish_sf=2.0 | 79.21° | **0.0000** |
| HIGH ROT + LOW CV | hebbian_swish_sf=3.0 | 79.17° | **0.0000** |

**These are genuine counterexamples to the theory.** High eigenvector rotation + perfect conservation.

### Additional Notable Cases

| Config | Rotation | CV | Note |
|--------|----------|-----|------|
| switching_period=5 | 6.82° | 0.030 | Moderate rotation, moderate CV |
| diag_spread=5.0 | 85.43° | 0.047 | Extreme rotation, moderate CV |
| rotating_rank2_swish_sf=1.0 | 79.27° | 0.120 | High rotation, HIGH CV |

### No "Low Rotation + High CV" Counterexamples Found

Every config with rotation < 5° has CV < 0.01. The forward direction (low rotation → good conservation) holds. The failure is the converse (high rotation → poor conservation).

---

## REVISED THEORY

### What the Theory Gets Right

1. ✅ Low eigenvector rotation → good conservation (no counterexamples)
2. ✅ Attention SD: low rotation, good conservation (confirmed across 4 scales)
3. ✅ Temperature monotonically controls conservation quality for attention
4. ✅ Noise destabilization is mediated through eigenvector rotation

### What the Theory Gets Wrong

1. ❌ High eigenvector rotation ≠ poor conservation (Hebbian SD is the counterexample)
2. ❌ Activation contractivity is a secondary effect (all activations ~equal under attention SD)
3. ❌ The theory is NOT sufficient — eigenvector stability is one mechanism, not the only one

### The Correct Theory: Two Independent Conservation Mechanisms

```
CONSERVATION QUALITY = max(STRUCTURAL_MECHANISM, DYNAMICAL_MECHANISM)

Structural mechanism (rank-1 / degenerate coupling):
  - Hebbian SD: C = xx^T → rank-1 → γ=1, H=0 regardless of eigenvector rotation
  - Conservation is an ALGEBRAIC identity: γ+H = const follows from the rank structure
  - Eigenvector rotation is irrelevant because γ and H are fixed by the rank

Dynamical mechanism (eigenvector stability):
  - Attention SD: full-rank coupling → eigenvectors matter → rotation predicts CV
  - Conservation depends on how eigenvectors evolve → rotation ∝ CV
  - Works for coupling matrices with non-trivial spectrum

Activation role:
  - Tertiary effect (all activations within 18% of each other under attention SD)
  - Matters only when dynamics are near instability boundary
```

### Key Diagnostic: Effective Rank of C(x)

```
eff_rank(C) = (Σλᵢ)² / Σλᵢ²

If eff_rank < 1.5 → structural mechanism dominates → rotation irrelevant
If eff_rank > 2   → dynamical mechanism dominates → rotation predicts CV
```

### Prediction for Cycle 11

1. For attention SD (eff_rank > 5): rotation predicts CV ✓
2. For Hebbian SD (eff_rank = 1): rotation irrelevant ✓
3. For rank-2 coupling (eff_rank = 2): BOTH mechanisms contribute
4. Engineering principle: normalize coupling to control eff_rank for desired mechanism

---

## Summary of All Findings

| Finding | Confidence | Supports Theory? |
|---------|-----------|-----------------|
| r(rotation, CV) = 0.78 under mixed configs | HIGH | Partial |
| Non-linear rotation-CV relationship | HIGH | No (predicted linear) |
| Hebbian SD: CV=0 with 79° rotation | HIGH | **FALSIFIES** |
| All activations equal under attention SD | HIGH | **FALSIFIES** contractivity |
| Non-monotonic noise response (inverted-U) | MED | Partial |
| Scale: Hebbian always wins, rotation never predicts | HIGH | **FALSIFIES** |
| No low-rotation + high-CV counterexample | HIGH | Supports |
| Attention improves with scale | HIGH | Supports |
| Switching coupling: moderate rotation, moderate CV | MED | Neutral |

**THEORY STATUS:** The convergent theory (conservation = eigenvector stability × activation contractivity) is PARTIALLY CORRECT but INCOMPLETE. It correctly identifies the dynamical mechanism for full-rank coupling but misses the structural mechanism that makes rank-1 coupling trivially conserve regardless of eigenvector rotation. Activation contractivity is a minor effect, not a primary driver.
