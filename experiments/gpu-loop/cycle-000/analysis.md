# Cycle 0 Analysis (GLM-5.1) — 2026-05-16

## Context
This is the FIRST cycle. No previous results exist. Analysis based on master design (GPU-CONSTRAINT-HETEROGENEITY.md) and prior experiments E4, E6, Combo.

## Prior Context Summary
- **E4 (Eigenvalue Deep Dive):** γ+H ranges 0.6–3.9 depending on V and architecture. Conservation law γ+H = C - α·ln(V) validated across architectures. Eigenvalue spacing follows Wigner-Dyson for all architectures.
- **E6 (Info-Theoretic):** Free energy interpretation confirmed (F = E - T·S). KL divergence grows with V separation. Random architecture has zero mutual information.
- **Combo Architecture:** γ+H CV = 0.105 (marginally above 10% threshold). Temporal coupling shows γ growing then stabilizing.

## Priority Experiments Selected
From the master design's 8 experiments (H1-H8), Tier 1 priority + H3 + H4:
1. **H1** — Precision-dependent C (core phenomenology)
2. **H2** — Spectral gap persistence (γ→0 resistance)
3. **H5** — Conservation law breakdown boundary
4. **H3** — BBP transition broadening
5. **H4** — Precision as simulated annealing

## Results Summary

### EXP-1: Conservation Constants (H1)
**Hypothesis:** C_heterogeneous > C_homogeneous
**Result:** **FALSIFIED.** C_hetero (15.54) < C_homo (17.79). γ+H is remarkably stable across ALL precision configurations (CV < 0.005). The conservation constant does NOT increase with heterogeneity — if anything, it decreases slightly.

Key data:
- Homo FP64: γ+H = 1.669 ± 0.003 (CV=0.002)
- Homo INT8: γ+H = 1.653 ± 0.000 (CV=0.000, pinned to grid)
- Hetero extreme (FP64+INT4): γ+H = 1.746 ± 0.001

**Surprise:** INT8 has zero variance — the quantization grid pins γ+H to a fixed value. This is a genuine "frozen" state.

**Confidence:** HIGH. Clear numerical result.

### EXP-2: Spectral Gap Persistence (H2)
**Hypothesis:** Heterogeneity prevents γ→0 collapse
**Result:** **FALSIFIED.** Homogeneous γ floor (0.082) > Heterogeneous γ floor (0.076). No collapse to zero in ANY configuration. INT8 homogeneous actually has the HIGHEST floor (0.109).

**Surprise:** Lower precision alone prevents collapse. The quantization grid acts as a structural "floor" that prevents the rank-1 alignment.

**Confidence:** HIGH. Consistent across 300 rounds.

### EXP-3: Conservation Breakdown (H5)
**Hypothesis:** Conservation breaks at precision ratio ~10^12
**Result:** **STRONGLY FALSIFIED.** Conservation holds (CV < 0.001) at ALL ratios tested, up to FP64 vs 2-bit (ratio ~10^15). The 1-bit case failed numerically (NaN from quantization), suggesting breakdown only below 2-bit precision.

**Surprise:** The conservation law is far more robust to precision heterogeneity than predicted. Even extreme quantization preserves γ+H.

**Confidence:** HIGH for ratios above 2-bit. Unknown below (experiment crashed).

### EXP-4: BBP Transition Broadening (H3)
**Hypothesis:** Heterogeneous precision broadens the BBP transition 2×
**Result:** **FALSIFIED.** Transition width is ~0.40 for ALL configurations (homo and hetero). The noise floor from quantization doesn't significantly affect the BBP transition in spiked Wigner matrices of this size.

**Confidence:** MED. Matrix size N=20 is small; results may differ at larger N.

### EXP-5: Annealing (H4)
**Hypothesis:** Precision annealing speeds convergence
**Result:** **WEAK SUPPORT.** Annealing (INT8→FP16→FP32) converges in round 26 vs static FP32's round 30 (1.2× speedup). But final errors are nearly identical (0.0043 vs 0.0040). Reverse annealing increases error (0.0267), confirming directionality.

**Confidence:** LOW. Effect is small and could be noise.

## Key Insight: The Conservation Law is Substrate-Invariant

The overwhelming finding from all 5 experiments: **γ+H is conserved regardless of precision heterogeneity.** The conservation law doesn't depend on the numerical substrate — it's a property of the coupling structure itself, not the representation.

This is actually MORE interesting than the predicted result. It means:
1. The conservation law is deeper than we thought — it survives quantization noise
2. Precision affects the DYNAMICS (convergence speed, γ floor) but not the CONSERVATION itself
3. The "frozen" INT8 state (zero CV) suggests quantization can stabilize conservation

## New Questions for Cycle 1
1. Does conservation hold under ASYMMETRIC coupling (where precision translation is direction-dependent)?
2. Is there a system size N where BBP broadening actually appears?
3. Can the INT8 "frozen conservation" state be exploited for reliable fleet coordination?
4. What happens with 1-bit agents (below the breakdown boundary)?
5. Does the coupling ARCHITECTURE (Hebbian vs Attention vs Random) interact with precision effects?
