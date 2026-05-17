# Research Brief: Spectral Spike Deformation Experiment

*Cycle 3 — 2026-05-17 | Experiment: `cycle-003/exp-deformation.py`*

---

## The Hypothesis (from Dandi et al. 2024)

> Learning/structure creates spectral spikes that break GOE universality, which in turn breaks γ+H conservation. There exists a critical deformation α_c where conservation transitions.

**Interpolated coupling:** C_α = (1-α)·W + α·H (Wigner → Hebbian)

---

## Result: HYPOTHESIS FALSIFIED (direction reversed)

Cross-instance CV of γ+H **monotonically decreases** from pure Wigner (α=0) to pure Hebbian (α=1):

| N | CV at α=0 (random) | CV at α=1 (Hebbian) | Trend |
|---|---|---|---|
| 5 | 0.550 | 0.089 | ↓ |
| 10 | 0.440 | 0.065 | ↓ |
| 20 | 0.315 | 0.040 | ↓ |
| 50 | 0.248 | 0.027 | ↓ |

**Structure IMPROVES cross-instance conservation, not destroys it.**

There is no critical α_c — the transition is smooth and monotonic.

---

## Why the Hypothesis Failed

### What Dandi et al. got right
- Structure DOES create spectral modifications (KS to GOE increases from ~0.11 → 0.29 as α → 1)
- frac<0.5 DOES increase (more eigenvalue clustering with structure)
- Spectral statistics DO depart from GOE

### What the hypothesis got wrong
The hypothesis assumed GOE universality = conservation stability. In fact:

1. **Random matrices have HIGH cross-instance variation.** Each Wigner matrix has a different eigenvalue spectrum → different γ+H steady-state → high CI_CV. GOE universality describes the *shape* of the distribution, not the *consistency* across draws.

2. **Hebbian matrices have LOW cross-instance variation.** The outer-product structure constrains all Hebbian matrices to similar spectral shapes (one dominant eigenvalue near the "mean pattern" direction, bulk follows Marchenko-Pastur). The top eigenvector ≈ (1,1,...,1)/√N consistently → same H → low CI_CV.

3. **Structure is a stabilizer, not a disruptor.** The spectral spikes from Hebbian construction act as *constraints* that pin the dynamics to a predictable subspace.

### The mechanism
After initial transient, dynamics converge to the dominant eigenvector of J. The steady-state γ+H is determined by this eigenvector:
- **Wigner:** top eigenvector is random → H varies widely across draws → high CI_CV
- **Hebbian:** top eigenvector ≈ uniform → H ≈ log(N) consistently → low CI_CV

The cross-instance CV is measuring **eigenvector variability**, not conservation dynamics.

---

## Spectral Metrics vs Conservation

| Metric | Correlation with CI_CV | p-value |
|--------|----------------------|---------|
| frac<0.5 | r = -0.559 | 3.3e-09 |
| KS(GOE) | r = 0.169 | 0.099 |
| spike_count | r = 0.211 | 0.039 |

**frac<0.5 is the best predictor** (|r|=0.559), confirming Cycle 2's finding. But the direction is NEGATIVE: more eigenvalue clustering → LESS cross-instance variation. This is because clustered eigenvalues (Hebbian) produce constrained, predictable dynamics.

---

## Size Scaling

| N | Max CI_CV | α at max CV | CI_CV at α=1 |
|---|-----------|-------------|--------------|
| 5 | 0.563 | 0.04 | 0.089 |
| 10 | 0.440 | 0.00 | 0.065 |
| 20 | 0.338 | 0.08 | 0.040 |
| 50 | 0.267 | 0.02 | 0.027 |

- Larger matrices have lower overall CI_CV (0.56 → 0.27 at α=0)
- The rate of CV decrease with α is similar across sizes
- No sharp phase transition at any size

**Max CI_CV ~ N^{-0.3}** (approximate power law from 0.56 to 0.27 as N goes 5→50)

---

## Revised Understanding

### What we now know about conservation:

1. **Temporal conservation** (CV within a single dynamics run) is LOW for all architectures (~0.01-0.05). The dynamics converge quickly and then sit at a fixed γ+H value. This isn't really "conservation" — it's convergence.

2. **Cross-instance conservation** (CV across different random draws) measures something fundamentally different: how consistent the steady-state is across matrix realizations. This is high for random (inconsistent) and low for structured (consistent).

3. **The GOE-conservation link from Cycle 1 was misleading.** Cycle 1 found that random (GOE) coupling conserves and Hebbian doesn't. But that used a different dynamics model. Our experiment shows the opposite for cross-instance stability.

4. **Spectral spikes from structure are stabilizing, not destabilizing.** This contradicts the Dandi et al. mechanism as applied to our system. In neural network features, spikes indicate learned structure that *helps* generalization. Similarly, in our coupling system, spectral structure *helps* consistency.

### The real conservation question

The original finding (γ+H = C is conserved across time in coupled dynamics) and the new finding (cross-instance CV varies with structure) are measuring different things. The deformation experiment reveals that:

- **Temporal conservation** (γ+H constant over time) may be trivially true for any coupling that converges to a fixed point
- **Cross-instance stability** (γ+H consistent across random draws) is the more interesting and meaningful metric
- Structure HELPS cross-instance stability by constraining the spectral shape

---

## Implications for Next Cycle

1. **The dynamics model needs rethinking.** Current dynamics (x → Jx, normalize) converge too fast to be informative. Need either:
   - Longer transient dynamics (nonlinear coupling, noise)
   - Multi-step coupling with memory
   - Coupled ODE dynamics instead of discrete map

2. **Cross-instance CV is the right metric** but needs to be computed from genuinely non-trivial dynamics, not from steady-state values.

3. **The deformation interpolation is smooth** — no phase transition. If there IS a critical α_c, it requires a different kind of dynamics to reveal.

4. **Test the "convergence to fixed point" hypothesis** explicitly: measure the convergence rate and check whether all architectures converge to eigenvector alignment.

5. **Revisit Cycle 1's temporal CV finding** with the correct dynamics model to reconcile the apparently contradictory results.

---

## What This Proves About Dandi et al.

Dandi et al. (2024) showed that learning creates spectral spikes in neural network features. Our experiment confirms this mechanism at the eigenvalue level:
- KS to GOE increases from 0.11 to 0.29 as structure increases ✓
- Eigenvalue clustering (frac<0.5) increases from 0.20 to 0.43 ✓

But the *consequence* of these spikes is the opposite of what we hypothesized:
- Hypothesis: spikes → broken universality → broken conservation
- Reality: spikes → constrained eigenvectors → MORE consistent steady-state

The Dandi et al. mechanism is correct (learning creates spikes), but the mapping from spikes to conservation is wrong. Spikes don't break conservation — they stabilize it.

---

*Experiment: `cycle-003/exp-deformation.py` | Data: `cycle-003/results/deformation-results.json`*
*Runtime: 28.9s | 80 samples × 4 sizes × 24 α values = 7,680 dynamics runs*
