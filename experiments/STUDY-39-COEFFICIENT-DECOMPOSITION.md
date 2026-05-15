# STUDY 39: Coefficient Decomposition — Substitution Burden Hypothesis

**Date:** 2025-05-15  
**Model:** NousResearch/Hermes-3-Llama-3.1-70B (DeepInfra)  
**Computation:** Eisenstein norm of (5, -3) = 25 - (-15) + 9 = 49  
**Trials:** 30 per condition, 180 total  
**Temperature:** 0.3, max_tokens: 200-400  

---

## Hypothesis

Cognitive load L = α·F + β·S + γ·A where F=formula recall, S=symbolic substitution, A=arithmetic.

**Prediction:** β > α > γ (substitution burden dominates)

**Key test:** C3 (S removed) > C2 (F removed) > C4 (A removed) must hold.

---

## Results

| Condition | Description | Burden Removed | Correct | Rate | Predicted | Delta |
|-----------|-------------|----------------|---------|------|-----------|-------|
| C1 | Baseline (full task) | — | 30/30 | **100.0%** | 15% | +85% |
| C2 | Formula given, domain hidden | F removed | 30/30 | **100.0%** | 38% | +62% |
| C3 | Substitution pre-done | S removed | 22/30 | **73.3%** | 62% | +11% |
| C4 | Answer given, explain why | A removed | 30/30 | **100.0%** | 27% | +73% |
| C5 | Bare arithmetic only | F+S removed | 20/30 | **66.7%** | 81% | -14% |
| C6 | Full precompute, verify | All removed | 30/30 | **100.0%** | 94% | +6% |

---

## Hypothesis Test

| Prediction | Required | Actual | Verdict |
|------------|----------|--------|---------|
| C3 > C2 | β > α | 73.3% < 100.0% | **REJECTED** ❌ |
| C2 > C4 | α > γ | 100.0% = 100.0% | **NULL** (no difference) |
| β > α > γ | Full chain | α = γ > β | **REJECTED** ❌ |

**The substitution burden hypothesis is REJECTED for Hermes-70B.**

---

## Analysis

### 1. Predictions Were Dramatically Wrong

Every prediction missed by ≥10 percentage points. The model was far more capable than predicted on structured prompts (C1: 100% vs 15%) and less capable on bare arithmetic (C5: 67% vs 81%).

### 2. The Actual Ordering: α = γ ≥ β

The empirical ordering is C1 = C2 = C4 = C6 = 100% > C3 (73%) ≈ C5 (67%). Formula recall (α) and arithmetic (γ) contribute equally and are **fully handled** by this model. Symbolic substitution pre-processing (β) appears to **hurt** performance.

### 3. Why C3 Fails: The Re-Computation Trap

C3 gave the model the arithmetic pre-done: "a²=25, ab=-15, b²=9. So a² - ab + b² = 25 - (-15) + 9." Despite this, the model typically re-does the full computation from scratch, re-deriving a², ab, b² from a=5, b=-3. This causes:

- **Token exhaustion:** The re-computation uses so many tokens that the response is truncated before stating 49
- **Re-introduction of errors:** By re-doing the work, the model re-introduces the very errors the pre-computation was meant to avoid

The 8 failures (of 30) in C3 are all cases where the model's verbose re-computation ran out of the 200-token budget.

### 4. Why C5 Fails: Double Negative Confusion

C5 ("Compute: 25 - (-15) + 9 = ?") shows 66.7% accuracy. Error analysis reveals consistent patterns:

- **Sign error:** Multiple responses compute `-(-15) = 15` correctly in prose, but then evaluate `25 - 15 = 10` instead of `25 + 15 = 40`
- **Result:** The model reaches 19 (= 10 + 9) instead of 49 (= 40 + 9)
- This is a genuine arithmetic failure, not a token issue

### 5. Why C4 Is Trivially Easy

C4 gave the answer (49) and asked the model to explain why. The scoring checked if 49 and correct arithmetic appeared in the response. Since 49 was in the prompt, this was trivially easy. A more stringent check (evaluating the quality of the explanation) would likely show lower rates, but that requires LLM-as-judge scoring.

### 6. The Real Finding: Context-Rich > Context-Poor

The striking pattern is that **domain context improves performance**:

- C1 (Eisenstein norm, formula given): 100%
- C2 (generic formula, no domain label): 100%  
- C5 (bare arithmetic, no context): 67%

The model benefits from the framing of the problem. Mathematical context ("Eisenstein norm", "a + bω") activates relevant computational pathways, while bare arithmetic triggers generic PEMDAS application that's more error-prone.

---

## Failure Mode Analysis

### C3 Failures (8/30 = 26.7%)
All failures: model re-computes from scratch, response truncated before reaching 49.
All successes: model either uses pre-computed values or completes re-computation within token budget.

### C5 Failures (10/30 = 33.3%)
Primary error: `25 - (-15)` computed as `25 - 15 = 10` (sign error on double negative).
Correct path: `25 - (-15) = 25 + 15 = 40` → `40 + 9 = 49`.
Error path: `25 - 15 = 10` → `10 + 9 = 19`.

---

## Revised Model for Hermes-70B

For this model on this computation:

```
L = α·F + β·S + γ·A + δ·D

Where:
  D = "context deprivation" penalty
  α ≈ 0 (formula recall is free)
  γ ≈ 0 (arithmetic is free when contextualized)
  β ≈ -0.27 (pre-done substitution HURTS via re-computation trap)
  δ ≈ 0.33 (stripping all context causes arithmetic errors)
```

The original three-factor model is insufficient. A fourth factor — contextual framing — dominates.

---

## Recommendations for Study 40+

1. **Increase max_tokens to 500+** to eliminate truncation as a confound
2. **Add C3b condition:** Same as C3 but with "Do NOT re-derive a², ab, b². Use the values I gave you."
3. **Use LLM-as-judge for C4** to properly score explanation quality
4. **Test on multiple computations** to generalize beyond this single instance
5. **Compare models:** This effect likely varies dramatically across model families
6. **Control for prompt engineering:** The "re-computation trap" suggests the model doesn't trust pre-computed values

---

## Raw Data

Full results in `study39-results.json` (180 records).
