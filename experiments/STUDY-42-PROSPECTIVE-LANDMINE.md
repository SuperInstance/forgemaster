# STUDY 42: Prospective Landmine Prediction

**Date:** 2026-05-15  
**Model:** Hermes-3-Llama-3.1-70B (DeepInfra)  
**Trials:** 20 per term, 240 total  
**Temperature:** 0.3  
**Task:** Compute f(5, -3) where f(a,b) = a² - ab + b² → correct answer = 49

## Hypothesis

If domain vocabulary triggers STORED FORMULAS that override explicit instructions, we can PREDICT which tokens will be landmines AND what wrong answer they'll produce BEFORE running any trials.

## Design

Same explicit formula f(a,b) = a² - ab + b², wrapped in 12 different domain terms. For each, a specific prediction was made about what competing formula might fire and produce a wrong answer.

## Results Summary

| Term | Predicted Safe? | Accuracy | Most Common Wrong | Predicted Wrong | Match? |
|------|:---:|:---:|:---:|:---:|:---:|
| Frobenius norm | LANDMINE | **100%** | — | 34 or 6 | ✗ MISSED |
| Minkowski norm | LANDMINE | **80%** | 37 (×4) | 34 or 6 | ✗ MISSED |
| Euclidean norm | LANDMINE | **85%** | 31 (×3) | 34 or 6 | ✗ MISSED |
| Hermitian norm | LANDMINE | **40%** | 43 (×6) | uncertain | N/A |
| Hurwitz norm | SAFE | **0%** | 43 (×20) | — | ✗ WRONG |
| spectral norm | LANDMINE | **20%** | 43 (×10) | uncertain | N/A |
| Hölder norm | LANDMINE | **100%** | — | 5 | ✗ MISSED |
| energy norm | SAFE | **50%** | 67 (×10) | — | ✗ WRONG |
| trace norm | SAFE | **40%** | 67 (×11) | — | ✗ WRONG |
| Sobolev norm | SAFE | **35%** | 37 (×13) | — | ✗ WRONG |
| nuclear norm | SAFE | **85%** | 67 (×3) | — | ✓ correct |
| Mahalanobis distance | LANDMINE | **100%** | — | uncertain | N/A |

## Wrong Answer Taxonomy

The wrong answers cluster into three distinct values, each corresponding to a different competing formula:

| Wrong Value | Computation | Formula Override |
|:-----------:|:-----------:|:-----------------|
| **43** | 25 + 15 + 3 = 5² + 5·3 + 3 = a² + a\|b\| + \|b\| | Swaps -ab → +a\|b\| (ignores sign of b) |
| **37** | 25 + 3 + 9 = a² + \|ab\|... unclear | Multiple pathways, arithmetic error variant |
| **67** | 25 + 15 + 9 + ... | Appears in energy/trace/nuclear — may compute a² + ab + b² + extra |

### Key Pattern: **43** dominates in "norm" terms
- Hurwitz: 20/20 wrong → all 43
- spectral: 10/16 wrong → 43
- Hermitian: 6/12 wrong → 43

**43 = 25 + 15 + 3** — This is the model computing f(a,b) = a² + a|b| + |b| or simply ignoring the negative sign on -3 and computing a² - ab + b² where b=3 instead of b=-3.

## Falsification Criteria

### 1. Landmine terms with predicted competing formulas
**NOT CONFIRMED.** Predicted: sqrt(25+9)=34 or √34≈6. Actual: Frobenius got 100% correct, Minkowski produced 37, Euclidean produced 31. None produced the predicted 34 or 6.

### 2. Safe terms >70% accuracy
**NOT CONFIRMED.** Only nuclear norm (85%) exceeded 70%. Hurwitz (0%), energy (50%), trace (40%), Sobolev (35%) all failed spectacularly.

### 3. Overall prediction accuracy
**3/12 (25%) — NEEDS REVISION.** Only 3 of 12 predictions were correct (Frobenius predicted landmine but got 100%, Mahalanobis predicted landmine but got 100%, nuclear predicted safe and got 85%).

## Critical Discoveries

### 1. Predictions were INVERTED for key terms
The predicted "landmine" terms (Frobenius, Euclidean) were among the BEST performers (100% and 85%). The predicted "safe" terms (Hurwitz, Sobolev) were the WORST (0% and 35%).

### 2. The competing formula was NOT what we predicted
We predicted Euclidean-norm formula (sqrt(a²+b²)=34 or 6). The actual competing formulas produced 43, 37, and 67 — completely different arithmetic errors.

### 3. The 43-pattern is SIGN CONSUSION, not formula substitution
The dominant error (43) = 5² + 5·3 + 3 = treating b=+3 instead of b=-3. This isn't a "stored Euclidean norm formula" — it's a simpler failure mode: **the model loses track of the negative sign on -3.**

### 4. Hurwitz norm: 100% failure rate
Every single trial produced 43. This is the strongest landmine in the entire study — on a term we predicted would be SAFE.

### 5. Domain terms don't trigger specific competing formulas
The hypothesis was that "Frobenius norm" would trigger sqrt(a²+b²). Instead, errors are dominated by sign-handling failures (43) and arithmetic errors (37, 67), with no clear mapping from domain term to specific wrong formula.

## Implications for CPA-ABD Theory

1. **Stored formulas DO interfere** — but the interference is NOT predictable from the domain term alone
2. **The primary failure mode is sign handling** — not formula substitution
3. **"Safe" domain terms can be MORE dangerous** than "dangerous" ones (Hurwitz 0% vs Frobenius 100%)
4. **Prospective prediction of specific landmines FAILED** — we cannot predict WHAT wrong answer a term will produce from its domain association alone
5. **The interference may be more about computational pathway** than stored formula lookup

## Unexpected Winners

- **Frobenius norm** (100%), **Hölder norm** (100%), **Mahalanobis distance** (100%) — all perfect
- **Nuclear norm** (85%) — only "safe" prediction that held

These suggest that some domain terms may actually PRIME correct computation rather than interfere with it.
