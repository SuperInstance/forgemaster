# STUDY 40: Domain Specificity Gradient

**Date:** 2026-05-15
**Model:** NousResearch/Hermes-3-Llama-3.1-70B (DeepInfra)
**Temperature:** 0.3 | **Max tokens:** 200
**Trials per condition:** 30 (240 total calls)
**Correct answer:** 49 (Eisenstein norm of (5, -3): 25 - (-15) + 9 = 49)

## Hypothesis

Domain specificity of the leading adjective monotonically tracks success rate. Higher specificity → lower activation of the discourse head that overrides the explicit formula. Predicted monotone: T1(15%) < T2(19%) < T3(28%) < T4(41%) < T5(58%) < T6(68%) < T7(77%) < T8(85%).

## Results

| Cond | Specificity | Correct/30 | Rate | Dominant Wrong Answer |
|------|-------------|-----------|------|----------------------|
| T1   | 0.95        | 0/30      | 0.0% | 61 (a²+b² fallback)  |
| T2   | 0.88        | 27/30     | 90.0%| 61 (3 failures)      |
| T3   | 0.72        | 0/30      | 0.0% | 61                   |
| T4   | 0.55        | 5/30      | 16.7%| 61                   |
| T5   | 0.38        | 22/30     | 73.3%| 61 (8 failures)      |
| T6   | 0.20        | 0/30      | 0.0% | Garbage (3496, 520…)  |
| T7   | 0.10        | 0/30      | 0.0% | 136 (a²·b² fallback)  |
| T8   | 0.02        | 0/30      | 0.0% | 1364 (misread)        |

## Falsification Verdict

### Inversions: 2 (out of 7 adjacent pairs)
- T2→T3: 90.0% → 0.0% (massive inversion at specificity 0.88→0.72)
- T5→T6: 73.3% → 0.0% (inversion at specificity 0.38→0.20)

### Pearson r = +0.3311 (positive, not negative!)
The correlation runs **opposite** to prediction. Specificity does NOT monotonically predict success.

### Verdict: **HYPOTHESIS FALSIFIED**

## Key Findings

### 1. The "Eisenstein" word is POISON, not activation
T1 ("Eisenstein polynomial norm") scored 0%. The word "Eisenstein" triggers a discourse head that **overrides** the explicitly given formula. The model "knows" Eisenstein norms exist but computes `a² + b² = 61` instead of the given `a² - ab + b²`. This is the vocabulary wall in pure form.

### 2. "Kronecker" breaks the spell (90%)
T2 ("Kronecker polynomial norm") achieved 90% — the highest of any condition. "Kronecker" is domain-adjacent enough to feel mathematical but doesn't trigger the specific Eisenstein norm formula that conflicts with the given computation. The model follows the explicit formula.

### 3. "integer-coefficient" also works (73.3%)
T5 scored 73.3%. This generic descriptor doesn't activate any domain-specific override.

### 4. "irreducible" fails completely (0%)
T3 ("irreducible polynomial norm") = 0%. The word "irreducible" apparently activates norm-finding heuristics that override the formula.

### 5. Mystery polynomial (T6) produces garbage
When the domain label is meaningless ("mystery polynomial M norm"), the model doesn't default to the formula — it produces completely incoherent answers (3496, 520, 1488…). The model needs SOME framing to even attempt the computation.

### 6. Pure expression (T8) fails
Without any polynomial framing, the model misparses the expression entirely (1364 dominant).

## Interpretation

The pattern is **not** a monotone gradient. It's a **binary gate** pattern:
- Words that activate conflicting domain knowledge → 0% (Eisenstein, irreducible)
- Words that are math-adjacent but non-conflicting → 73-90% (Kronecker, integer-coefficient)
- Words that are too vague or meaningless → 0% or garbage

This suggests the mechanism is not "attention competition along a specificity gradient" but rather **discrete head activation**: certain specific tokens trigger hard-coded formula overrides that conflict with the given explicit formula. The gradient is not monotone — it's a minefield where specific domain terms are landmines.

## Comparison to Predictions

| Cond | Predicted | Actual | Delta |
|------|-----------|--------|-------|
| T1   | 15%       | 0.0%   | -15%  |
| T2   | 19%       | 90.0%  | +71%  |
| T3   | 28%       | 0.0%   | -28%  |
| T4   | 41%       | 16.7%  | -24%  |
| T5   | 58%       | 73.3%  | +15%  |
| T6   | 68%       | 0.0%   | -68%  |
| T7   | 77%       | 0.0%   | -77%  |
| T8   | 85%       | 0.0%   | -85%  |

Predictions were massively wrong. The monotone gradient model is completely refuted by this data.

## Raw Data
See `study40-results.json` for complete trial-level data.
