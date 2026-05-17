# Research Brief: Engineered Eigenvalue Distribution Experiment

**Date:** 2026-05-17
**Author:** Forgemaster ⚒️ (Research Subagent)
**Status:** RESULTS IN — two-moment hypothesis weakened, new dynamics-dependent picture emerges
**Experiment:** `cycle-004/exp-engineered.py`

---

## Executive Summary

**Can we engineer conservation by controlling Tr(C²)? Partially — but the mechanism is more nuanced than expected.** Under nonlinear tanh dynamics, conservation depends on the eigenvalue distribution shape but the two-moment constraint (Tr(C) + Tr(C²) → γ+H) explains only ~14% of γ+H variance. The real story is that **degeneracy helps, spread hurts (modestly), and the dynamics model determines everything.**

**The key actionable finding:** Identity matrices (maximum degeneracy) produce the best temporal conservation under tanh dynamics. This is a genuine design principle.

---

## Experiment Design

Six experiments with nonlinear dynamics `x_{t+1} = tanh(C @ x_t)`:

| Exp | Question | Method |
|-----|----------|--------|
| 1 | Which eigenvalue distributions conserve best? | 8 engineered distributions, temporal + cross-instance CV |
| 2 | Does fixing Tr(C²) force conservation? | Constrain Tr(C²) to target, measure CI_CV |
| 3 | Does Tr(C²) time-variation break conservation? | Time-varying coupling with controlled Tr(C²) trajectory |
| 4 | How much of γ+H do Tr(C) + Tr(C²) explain? | Two-moment regression across 160 diverse matrices |
| 5 | Does eigenvalue spread alone predict conservation? | Vary spread with fixed Tr(C)=N |
| 6 | What about maximum degeneracy (identity)? | C = s·I for various scalars |

---

## Results

### RESULT 1: Degeneracy Wins Under Tanh Dynamics (confidence: HIGH)

**Ranking by temporal CV (N=20, tanh dynamics):**

| Distribution | Temporal CV | CI_CV | γ-H Corr |
|-------------|------------|-------|----------|
| **Degenerate (all equal)** | **0.0070** | **0.0070** | 0.000 |
| Two-cluster | 0.0101 | 0.0142 | 0.948 |
| Uniform | 0.0109 | 0.0066 | 0.879 |
| Rank-1 limit | 0.0163 | 0.0171 | 0.462 |
| Exponential | 0.0170 | 0.0141 | 0.742 |
| Attention | 0.0295 | 0.0222 | 0.574 |
| Wigner/GOE | 0.0419 | 0.0518 | 0.343 |
| **Power-law** | **1.0365** | **0.5687** | 0.902 |

**Degenerate matrices conserve best. Power-law (heavy-tailed) distributions are catastrophically bad.** This is the OPPOSITE of what power iteration showed (where random/GOE "won" by converging to a trivial fixed point).

**Interpretation:** With tanh nonlinearity, all eigenvalues equal means all dimensions are equally amplified → x_t spreads across all coordinates → entropy stays high and stable. Power-law gives one dominant direction → x_t collapses → entropy crashes → γ+H varies wildly.

### RESULT 2: Fixing Tr(C²) Does NOT Force Conservation (confidence: HIGH)

| Target Tr(C²) (×attention) | N=10 CI_CV | N=20 CI_CV |
|---------------------------|-----------|-----------|
| 0.5× | 0.0159 | 0.0077 |
| 1.0× | 0.0095 | 0.0071 |
| 2.0× | 0.0087 | 0.0044 |
| 5.0× | 0.0205 | 0.0109 |

**All values are low.** Fixing Tr(C²) gives decent cross-instance consistency, but there's no clear monotonic relationship. The variation (0.004–0.020) is small and noisy. Tr(C²) is neither necessary nor sufficient as a single control knob.

### RESULT 3: Conservation is Robust to Tr(C²) Variation (confidence: HIGH)

Time-varying coupling with different Tr(C²) trajectories:

| Mode | CV(Tr(C²)) | CV(γ+H) | Corr(γ+H, Tr(C²)) |
|------|-----------|---------|-------------------|
| Constant | 0.0000 | 0.0118 | 0.000 |
| Linear drift (+50%) | 0.1156 | 0.0131 | 0.297 |
| Random walk | 0.0614 | 0.0122 | -0.143 |
| Sinusoidal (±30%) | 0.2121 | 0.0122 | -0.144 |

**Conservation is nearly identical regardless of Tr(C²) trajectory.** Even when Tr(C²) oscillates by ±30% (sinusoidal), CV(γ+H) barely changes (0.0122 vs 0.0118 for constant). There's no consistent correlation between Tr(C²) and γ+H.

**This is a surprise.** It means Tr(C²) variation does NOT directly cause γ+H variation under nonlinear dynamics. The coupling between spectral and state-space quantities is weaker than the two-moment hypothesis predicted.

### RESULT 4: Two-Moment Regression is WEAK (confidence: HIGH)

| N | R²(Tr(C)) | R²(Tr(C²)) | R²(both) |
|---|-----------|------------|----------|
| 10 | 0.100 | 0.047 | **0.144** |
| 20 | 0.086 | 0.034 | **0.150** |

**Tr(C) + Tr(C²) together explain only ~14% of γ+H variance.** This directly contradicts the Cycle 3 finding that "Tr(C²) conservation perfectly predicts γ+H conservation." The previous result was an artifact of the simpler dynamics model (power iteration → convergence to fixed point → trivial conservation).

**What explains the other 86%?** Likely:
- Higher spectral moments (Tr(C³), Tr(C⁴), etc.)
- Eigenvector structure (which the trace moments ignore)
- Nonlinear interaction between state dynamics and spectral structure

### RESULT 5: Eigenvalue Spread Has Modest Effect (confidence: HIGH)

Varying eigenvalue spread with fixed Tr(C) = N:

| Spread | Tr(C²) | Temporal CV | CI_CV |
|--------|--------|------------|-------|
| 0.1 | 20.06 | 0.0125 | 0.0068 |
| 0.5 | 21.48 | 0.0132 | 0.0061 |
| 1.0 | 26.56 | 0.0140 | 0.0081 |
| 2.0 | 45.16 | 0.0157 | 0.0112 |
| 5.0 | 166.11 | 0.0192 | 0.0170 |
| 10.0 | 651.02 | 0.0217 | 0.0512 |

Conservation degrades gracefully with spread. Going from near-degenerate (spread=0.1) to wildly spread (10.0) only increases temporal CV from 0.0125 to 0.0217 — less than 2×. This is a gentle slope, not a cliff. But the CI_CV does increase more significantly at extreme spread (0.0512 at spread=10).

### RESULT 6: Identity Conservation Depends on Scale (confidence: HIGH)

| Matrix | Temporal CV |
|--------|------------|
| 0.1 × I | **3.39** (catastrophic) |
| 0.5 × I | **1.69** (bad) |
| 1.0 × I | 0.007 (excellent) |
| 2.0 × I | 0.005 (excellent) |
| 5.0 × I | 0.005 (excellent) |

**Small eigenvalues → terrible conservation.** With C = 0.1·I, tanh(0.1·x) ≈ 0.1·x (nearly linear), and x_t decays to zero rapidly. γ+H for a near-zero vector is ill-defined and noisy.

**Threshold is around eigenvalue ≈ 1.** Below that, tanh is in the linear regime and dynamics collapse. Above that, tanh saturates and provides bounded, stable dynamics.

---

## Revised Theory

### What Happened to the Two-Moment Hypothesis?

The two-moment hypothesis (Tr(C) + Tr(C²) determine γ+H) was based on:
1. Cross-instance correlation: architectures with stable Tr(C²) had stable γ+H
2. Power iteration dynamics: converge to fixed point → γ+H is steady-state value → determined by eigenvectors

Under **nonlinear tanh dynamics**, the picture changes:
- x_t doesn't converge to the top eigenvector — tanh creates a non-trivial attractor
- The attractor depends on ALL eigenvalues AND eigenvectors, not just the first two moments
- Conservation is about attractor stability, not moment conservation

### The Dynamics-Dependent Conservation Framework

| Dynamics Model | What Conserves | Mechanism |
|---------------|---------------|-----------|
| Power iteration | Cross-instance CV | Convergence to top eigenvector → CI_CV = f(eigenvector variability) |
| Power iteration | Temporal CV | Trivially conserved after convergence |
| **Tanh nonlinear** | **Temporal CV** | **Attractor stability → better with degeneracy** |
| **Tanh nonlinear** | **CI_CV** | **Determined by eigenvector distribution shape** |

The conservation law is **dynamics-model dependent**. There is no universal γ+H = C that holds across all dynamics.

### Engineering Principles (Actionable)

Despite the weakened theory, we can extract real design principles:

1. **Degenerate spectra conserve best.** If you can make all coupling eigenvalues equal, conservation is maximized. This means: normalize coupling to have uniform spectral structure.

2. **Avoid heavy-tailed eigenvalue distributions.** Power-law spectra are catastrophic (CV > 1). Keep eigenvalue ratios bounded (< 10:1).

3. **Ensure eigenvalues are above the tanh linear regime.** Minimum eigenvalue should be ≥ 1.0 for stable conservation under tanh dynamics.

4. **Conservation is robust to moderate Tr(C²) variation.** You don't need to hold Tr(C²) exactly constant. ±30% oscillation barely affects conservation.

5. **The two-moment model is insufficient.** To predict γ+H from spectral properties, you need at least 3-4 moments or eigenvector information.

---

## What This Means for the Fleet

### Good News
- Conservation under nonlinear dynamics is REAL (CV ~ 0.01 for reasonable spectra)
- It's robust to time-varying coupling (Tr(C²) oscillation doesn't break it)
- Simple design rule: keep eigenvalue spread bounded

### Bad News
- The elegant two-moment theory was too good to be true (R² = 0.14)
- Conservation is dynamics-dependent, not a universal law
- You can't simply control Tr(C²) to dial conservation up/down

### The Open Question
**What spectral quantity ACTUALLY determines γ+H under tanh dynamics?** The R²=0.14 result means we're missing the main driver. Candidates:
1. Higher spectral moments (Tr(C³), Tr(C⁴))
2. Eigenvalue entropy / participation ratio
3. Eigenvector coherence / delocalization
4. The Lyapunov spectrum of the nonlinear dynamics
5. The structure of the tanh-induced attractor

---

## Priority Next Steps

1. **30 min:** Compute higher-moment regression (Tr(C), Tr(C²), Tr(C³), Tr(C⁴) → γ+H). If R² jumps above 0.5, the multi-moment hypothesis is viable.

2. **1 hour:** Compute the participation ratio / inverse participation ratio of eigenvectors and correlate with γ+H. If eigenvector structure matters more than eigenvalues, this is a different mechanism.

3. **Theory:** The tanh dynamics create a specific attractor structure. Can we characterize this analytically? Even for C = I, the dynamics x → tanh(x) has a non-trivial attractor (all coordinates → ±1). The entropy of this attractor depends on the sign pattern, which depends on the initial condition.

4. **Fleet design:** Even without full theory, the engineering principles above are actionable. Normalize coupling matrices, avoid heavy-tailed spectra, keep eigenvalues ≥ 1.

---

## Bottom Line

**The two-moment hypothesis is dead for nonlinear dynamics.** R²=0.14 means Tr(C) + Tr(C²) explain only 14% of γ+H variance under tanh dynamics. But conservation IS real (CV ~ 0.01 for good spectra), and we've found genuine engineering principles: degeneracy helps, heavy tails kill, scale matters.

**The experiment that would crack this:** characterize the FULL attractor structure of tanh(C @ x) for various C, and relate attractor properties to γ+H. This is a dynamical systems problem, not a linear algebra problem.

*Experiment: `cycle-004/exp-engineered.py` | Data: `cycle-004/results/engineered-results.json`*
*Runtime: 3.8s | 6 experiments, 8 architectures × 2 sizes × 15 trials*
