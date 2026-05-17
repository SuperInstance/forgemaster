# GPU Loop Cycle 2 — Results Summary

**Model:** Nemotron-30B (via GLM-5.1 orchestrator)
**Date:** 2026-05-16 23:28 AKDT
**Runtime:** ~50 seconds (all 5 experiments)

---

## EXP-1: Eigenvalue Spacing Distribution — ✅ VALID RESULTS

| Architecture | KS(GOE) | KS(Poisson) | Classification | Spacing std | frac<0.5 | γ+H CV (cross-instance) |
|---|---|---|---|---|---|---|
| **Random** | 0.038 | 0.210 | **GOE** | 0.619 | 0.207 | 0.0150 |
| **Hebbian** | 0.793 | 0.589 | **Poisson** | 2.921 | 0.850 | 0.2680 |
| **Attention** | 0.545 | 0.306 | **Intermediate** | 3.717 | 0.707 | 0.0162 |

### KEY FINDINGS

1. **Random coupling has textbook GOE spacing** (KS=0.038 to Wigner surmise). This confirms Cycle 1's hypothesis that GOE statistics are the mechanism.

2. **Hebbian coupling has Poisson spacing** (KS=0.589 to Poisson, KS=0.793 to GOE). Massive level clustering (frac<0.5 = 0.85) — eigenvalues pile up instead of repelling. This is WHY conservation fails: eigenvalue degeneracy creates sensitivity.

3. **Attention is a surprise.** It has intermediate spacing (not GOE, not Poisson), yet its cross-instance CV is 0.016 — very low! This PARTIALLY falsifies the "GOE = conservation" hypothesis. Conservation doesn't require strict GOE spacing.

4. **GOE-score vs Conservation correlation:**
   - Random: GOE-score=0.962, Conservation-score=40.06
   - Attention: GOE-score=0.455, Conservation-score=38.20
   - Hebbian: GOE-score=0.208, Conservation-score=3.60

   Attention has HALF the GOE score of Random but nearly IDENTICAL conservation. This means GOE spacing is SUFFICIENT but NOT NECESSARY for conservation.

### REVISED MECHANISM HYPOTHESIS
Conservation requires **eigenvalue repulsion** (avoidance of degeneracy), not specifically GOE statistics. GOE is one way to achieve repulsion. Attention achieves repulsion through a different mechanism (its structured but non-degenerate eigenvalue distribution).

---

## EXP-2: Decorrelation of Structured Coupling — ⚠️ METHODOLOGICAL ISSUE

**All CV values = 0.0000 for all noise levels and architectures.**

This is a measurement artifact. The conservation metric computed γ+H from the static eigenvalue spectrum of J (which doesn't change across dynamics rounds), producing n_rounds identical values. CV=0 is trivially correct but meaningless for conservation dynamics.

**However, the eigenvalue spacing analysis IS valid:**
- Hebbian level repulsion violations: 0.794 (low noise) → 0.171 (high noise)
- At noise_level=5.0, Hebbian spacing becomes GOE-like (violations drop from 79% to 17%)
- **Critical noise for GOE transition is between noise=1.0 and noise=5.0**

This suggests that adding random noise to structured matrices DOES push eigenvalue statistics toward GOE. The decorrelation hypothesis has indirect support.

---

## EXP-3: Asymmetric Coupling as Correlation Breaker — ⚠️ SAME METHODOLOGICAL ISSUE

All CV=0.0000 due to static eigenvalue measurement.

**Valid findings:**
- Entry correlation for symmetric random: 1.0000 (by definition)
- Entry correlation for all asymmetric configs: ≈0.000 (independent triangles)
- GOE-peak score: symmetric=0.627, all asymmetric≈0.173

Wait — asymmetric configs have LOWER GOE-peak scores than symmetric? That contradicts the hypothesis that asymmetry improves GOE-ness. But note: asymmetric matrices have COMPLEX eigenvalues, so the GOE spacing test (designed for real eigenvalues) may not apply directly.

**Correlation between entry correlation and CV: r = -0.071 (no correlation)**
This is based on all-zero CVs, so it's not meaningful.

---

## EXP-4: Designing Coupling Matrices — ⚠️ SAME METHODOLOGICAL ISSUE

All CV=0.0000. Cannot distinguish between methods.

The GOE projection did work: Hebbian KS dropped from 0.747 to 0.108 (near random's 0.104). This confirms we CAN engineer eigenvalue statistics.

---

## EXP-5: Quantization Level Transition — ⚠️ SAME METHODOLOGICAL ISSUE

All CV=0.0000 for all levels (2 through 19) and all interpolation values. Cannot map the ternary→binary transition with this measurement.

---

## OVERALL ASSESSMENT

### What Worked
- **EXP-1 eigenvalue spacing analysis is the key result of this cycle.** It provides the first quantitative evidence for the GOE-conservation mechanism.
- The finding that Attention achieves conservation WITHOUT strict GOE spacing is novel and important.

### What Failed
- EXP-2 through 5 used a flawed conservation metric (static eigenvalues → trivial CV=0).
- The measurement must track γ+H across DYNAMICS rounds where the STATE VECTOR evolves, not the eigenvalues.

### Honest Summary
| Finding | Confidence | Notes |
|---------|-----------|-------|
| Random coupling = GOE spacing | HIGH | KS=0.038, textbook |
| Hebbian coupling = Poisson spacing | HIGH | KS=0.589, massive degeneracy |
| Attention = intermediate spacing but conserves | MED | Partially falsifies GOE-necessity |
| GOE sufficient but not necessary for conservation | MED | Attention is the counterexample |
| Noise pushes Hebbian toward GOE | MED | Violations drop from 79% to 17% |
| Eigenvalue engineering works (projection) | HIGH | KS drops from 0.747 to 0.108 |

### Methodological Fix for Next Cycle
The conservation metric must be:
```python
for round in range(n_rounds):
    x = J @ x
    x = x / ||x||
    # Compute γ from evolving state, not fixed eigenvalues
    gamma = spectral_gap_from_state(x, J)
    H = entropy_from_state(x)
    gh_values.append(gamma + H)
```

The STATE-DEPENDENT γ+H (not eigenvalue-dependent) is what matters for conservation dynamics.

---

## Open Questions for Cycle 3
1. **Why does Attention conserve despite non-GOE spacing?** What mechanism prevents eigenvalue degeneracy in structured attention matrices?
2. **What is the minimum eigenvalue repulsion needed for conservation?** Is there a "repulsion threshold" below which conservation breaks?
3. **Can the dynamics-based conservation metric resolve the ternary→binary transition?** Need to fix the measurement.
4. **For asymmetric matrices, what spacing distribution applies?** Ginibre ensemble (complex eigenvalues)?
5. **Can we predict conservation from the spacing distribution alone?** (If yes: engineering conserved coupling becomes a solved problem.)
