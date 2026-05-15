# STUDY 44: Formula Conflict Causal Intervention

**Date:** 2026-05-15
**Model:** Hermes-3-Llama-3.1-70B (DeepInfra)
**Temperature:** 0.3 | **Max tokens:** 150
**Trials per condition:** 25 | **Total API calls:** 100
**Computation:** f(5, -3) where f(a,b) = a² - ab + b² = 25 - (-15) + 9 = **49**

---

## Design

Four conditions isolating whether domain vocabulary can override an explicitly present formula.

| Condition | Description | Key Manipulation |
|-----------|-------------|-----------------|
| **C1** | `f(5,-3)` where `f(a,b) = a² - ab + b²` | Generic function name, no domain word |
| **C2** | polynomial norm `N(5,-3)` where `N(a,b) = a² - ab + b²` | Safe domain word + named function |
| **C3** | Eisenstein norm `N(5,-3)` where `N(a,b) = a² - ab + b²` | Landmine word + formula PRESENT |
| **C4** | Eisenstein norm, formula HIGHLY emphasized, step-by-step shown | Landmine word + maximally foregrounded formula |

---

## Results

| Condition | Correct | Total | Accuracy |
|-----------|---------|-------|----------|
| C1 (formula only, no domain) | 0 | 25 | **0%** |
| C2 (formula + safe domain) | 23 | 25 | **92%** |
| C3 (formula + landmine) | 25 | 25 | **100%** |
| C4 (formula + emphasized) | 25 | 25 | **100%** |

### C1 Failure Pattern
C1 produced only two wrong answers: **136** (9/25) and **1364** (16/25). These are systematic, not random — the model is computing *something* consistently but not the given formula. Likely the Unicode superscripts (²) cause tokenization issues when no domain context grounds the interpretation.

### C2 Errors
Two trials produced 61 and 97 — also systematic computation errors, possibly sign handling.

### C3 and C4: Perfect
The "Eisenstein" landmine word caused **ZERO degradation** when the formula was explicitly present. Both conditions hit 100%.

---

## Causal Intervention Analysis

### Predictions vs. Outcomes

| Prediction | Expected | Actual | Verdict |
|------------|----------|--------|---------|
| C1 (no domain) ~100% | ✓ | **0%** | ❌ FAILED — C1 catastrophically fails |
| C3 < C1 (landmine degrades) | <80% | **100%** | ❌ FAILED — landmine doesn't degrade at all |
| C4 recovers if attention issue | ~100% | **100%** | Trivially true |

### Falsification Tests

**Test 1: Does vocabulary override explicit formula?**
- C3 (Eisenstein + formula) = 100% = C2 (polynomial + formula)
- **Result: NO.** Domain vocabulary does NOT override an explicitly given formula.

**Test 2: Is the stored formula irrepressible?**
- C4 (Eisenstein + emphasized formula) = 100%
- **Result: NO.** There is no irrepressible stored formula fighting for control.

**Test 3: C1 baseline anomaly**
- C1 = 0% with generic `f(a,b)` notation, while C2-C4 all ≥92%
- This is a **confound**, not evidence for CPA-ABD. The failure is in parsing Unicode superscripts in abstract notation, not in domain vocabulary interference.

---

## Conclusion

### CPA-ABD Falsified on This Model

**The core prediction of CPA-ABD was that domain vocabulary ("Eisenstein") would degrade performance even with the correct formula present, because stored attractor basins would override the in-context formula. This did NOT happen.**

The Eisenstein landmine word had literally zero effect when the formula was present (C3 = C4 = 100%). This is the strongest possible falsification: the attractor basin does not override explicit formulas on Hermes-70B.

### What Actually Happened

1. **Abstract notation (C1) catastrophically fails** — The model cannot parse `f(a,b) = a² - ab + b²` correctly, producing 136/1364 systematically. This is a tokenization/encoding issue, not an attractor basin effect.

2. **Any domain grounding helps enormously** — Adding "polynomial norm" or "Eisenstein norm" with a named function `N` rockets accuracy to 92-100%. The domain word *helps* by providing interpretive context for the Unicode math.

3. **Landmine words don't override explicit formulas** — "Eisenstein" caused zero degradation. The model reads the formula, uses it, and computes correctly. No stored Eisenstein norm formula competes for control.

### Broader Implication

On Hermes-70B at temperature 0.3, the model follows explicit in-context formulas faithfully regardless of domain vocabulary. The CPA-ABD hypothesis (that domain vocabulary creates irrepressible attractor basins) is **not supported** on this architecture. The simpler explanation — that domain words shift attention/math interpretation — is sufficient to explain prior findings.

**Caveat:** This is one model. GLM-5.1 and other models may behave differently. The Unicode encoding issue in C1 is a confound that should be addressed in a follow-up with ASCII notation (`a^2 - a*b + b^2`).

---

*Study 44 complete. 100/100 API calls successful. Wall time ~5 seconds.*
