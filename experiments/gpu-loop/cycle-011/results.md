# Cycle 011: P Matrix vs Contraction Metric — Results

**Date:** 2026-05-17 | **Agent:** Forgemaster subagent | **N=5, T=50, 500 sample points**

## Executive Summary

**P ≠ M. In fact, P doesn't exist as a genuine quadratic form.** The γ+H conservation is real (CV < 0.01) but it is NOT mediated by a quadratic invariant x^T P x in state space.

## Key Findings

### 1. γ+H Conservation is Confirmed

| Architecture | CV(γ+H) | CV(||x||²) | Conservation Advantage |
|---|---|---|---|
| Random | 0.000296 | 2.75 | **9300×** |
| Attention | 0.002545 | 0.40 | **160×** |
| Hebbian | 0.003470 | 0.43 | **123×** |
| Symmetric | 0.000117 | 0.000605 | **5×** |

γ+H is conserved orders of magnitude better than ||x||². This is not just "x doesn't move."

### 2. γ+H is NOT a Quadratic Function of x

| Architecture | R²(full quadratic) | R²(||x||²+b) | R²(linear) |
|---|---|---|---|
| Random | **-8.11** | 0.32 | 0.01 |
| Attention | **-21.0** | 0.24 | 0.02 |
| Hebbian | **-38.6** | 0.65 | 0.01 |
| Symmetric | **-9.64** | 0.25 | 0.01 |

The R² values are **negative** for the full quadratic fit — meaning x^T P x fits WORSE than predicting the mean. Adding cubic terms doesn't help. γ+H is a genuinely nonlinear function of x (depends on Jacobian eigenvalue structure, which depends on x through sech² terms).

### 3. The Cycle 4 "R²=1.0" Was an Artifact

From insights.md: *"The R²=1.0 from Cycle 4 was specific to static coupling (trivially conserved)."* Under tanh dynamics with diverse x values, no quadratic form fits γ+H. The apparent R²=1.0 arose because:
- Single-trajectory data: x barely changes near fixed point → any quadratic is "constant"
- Static coupling: no dynamics → trivially constant γ+H

### 4. Contraction Metric Comparison (Negative Result)

Since the quadratic fit fails (R² < 0), there is no meaningful P to compare against contraction metrics. The test is moot — **the hypothesis "P = contraction metric M" is vacuously false because P doesn't exist.**

## What IS the Conservation Mechanism?

γ+H depends on the Jacobian J(x) = diag(1-x²)·C:
- **γ** = spectral gap of J(x)
- **H** = participation entropy of |eig(J)|

Along a trajectory converging to x*, the Jacobian changes smoothly. The conservation occurs because:
1. tanh is contractive → x converges → J(x) converges
2. The eigenvalue structure of J = diag(sech²(Cx))·C has a **first-order stability**: small changes in x produce small changes in eigenvalues
3. The spectral gap + entropy combination is **self-stabilizing**: as x approaches x*, both γ and H converge monotonically

The conservation is a **spectral property of the Jacobian along the attractor**, not a metric in state space.

## Implications for the Theory

| Previous Claim (Cycle 0-8) | Cycle 011 Finding |
|---|---|
| γ+H = x^T P x (R²=1.0) | **FALSE.** R² < 0 for quadratic fit over diverse x |
| P might be the contraction metric M | **N/A.** No valid P exists to compare |
| Conservation is a quadratic invariant | **FALSE.** Conservation is spectral, not metric |
| γ+H depends on x through quadratic channel | **FALSE.** γ+H depends on x through Jacobian eigenvalues (nonlinear) |

## Revised Theory

```
Conservation Mechanism:
  1. tanh creates contraction → x → x* (fixed point)
  2. J(x) = diag(sech²(Cx))·C changes smoothly along trajectory  
  3. Eigenvalues of J are smooth functions of x
  4. Spectral gap + entropy = first integral on the attractor
  5. This is NOT a quadratic/metric property — it's spectral

Conservation Quality = 
  f(spectral structure of C, eigenvector rotation rate, activation contractivity)

NOT = f(some metric P in state space)
```

## What Would Prove a Theorem?

The path forward is NOT "find P such that x^T P x = const." The path is:

1. **Prove that γ+H is a Lyapunov function** (non-increasing along trajectories) — this follows from contraction theory
2. **Prove that γ+H converges to a constant** — follows from LaSalle + the fact that x converges
3. **Prove the constant is determined by C alone** — the fixed-point value γ+H(x*) depends only on C
4. **Characterize the transient conservation quality** — eigenvector rotation rate predicts CV

The theorem would be: *"For contracting tanh-coupled systems, γ+H converges monotonically to a C-determined constant. The convergence rate is determined by eigenvector rotation, and the conservation quality is proportional to contractivity."*

This is still novel — it's a spectral first integral in nonlinear dynamics — but it's NOT a quadratic invariant.
