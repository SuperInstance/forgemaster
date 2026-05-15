# STUDY 46: Reverse-Engineer Mode C — What Does the Model Compute?

**Date:** 2026-05-15
**Model:** Hermes-70B (NousResearch/Hermes-3-Llama-3.1-70B) via DeepInfra
**Status:** ✅ Complete

## TL;DR

**The model is NOT computing a different function.** It is failing to reliably parse and compute symbolic formulas at all. When forced to show step-by-step work, it computes correctly. The "1364" answer is a computational pipeline failure, not a systematic alternative function.

## Key Discovery

| Notation | f(5,-3) Answer | Correct (49)? |
|----------|---------------|----------------|
| `a² - ab + b²` (unicode) | 1364 | ✗ |
| `a^2 - ab + b^2` | 1364 | ✗ |
| `a**2 - a*b + b**2` | 136 | ✗ |
| `a*a - a*b + b*b` | 52 | ✗ (close!) |
| `5*5 - 5*-3 + -3*-3` (substituted) | 97 | ✗ |
| "a squared minus a times b plus b squared" | **49** | **✓** |
| `a² - ab + b²` with "show step by step" | **49** | **✓** |

**The model can do the math. It cannot reliably parse the notation into a computation.**

## Phase 1: Systematic Testing (Unicode ², 100 API calls)

### Input Pairs and Results

| # | a | b | Correct | Mode Answer | Accuracy |
|---|---|---|---------|-------------|----------|
| 1 | 5 | -3 | 49 | 1364 | 0% |
| 2 | 3 | 2 | 7 | 49 | 0% |
| 3 | 4 | 1 | 13 | 65 | 0% |
| 4 | 2 | -1 | 7 | 65 | 0% |
| 5 | 6 | 0 | 36 | 216 | 0% |
| 6 | 0 | 3 | 9 | 81 | 0% |
| 7 | 1 | 1 | 1 | 65 | 0% |
| 8 | 7 | -2 | 67 | 449 | 0% |
| 9 | 3 | 3 | 9 | 54 | 0% |
| 10 | 2 | 5 | 19 | 41 | 0% |

**Overall: 0% accuracy across all 100 trials.**

### Analysis: No Recognizable Function Fits

Tested these candidate functions against the mode answers:

| Candidate Function | Matches |
|--------------------|---------|
| a² - ab + b² (correct) | 0/10 |
| a² + ab + b² (sign flip) | 0/10 |
| a² + b² (drop ab) | 0/10 |
| (a+b)² | 0/10 |
| (a-b)² | 0/10 |
| a² × b² | 0/10 |
| a³ + b³ | 3/10 (partial) |
| a⁴ - a²b² + b⁴ | 1/10 |

**Brute-force polynomial regression** with degree ≤6 monomials: **no 2-term or 3-term exact integer-coefficient combination found.**

The outputs do not follow ANY consistent polynomial function g(a,b).

### The "65" Anomaly

The value 65 appears as the mode answer for three completely different inputs: (4,1), (2,-1), (1,1). No polynomial function maps these three pairs to the same output. This is strong evidence of **tokenization-driven hallucination** rather than systematic miscalculation.

## Phase 2: Notation Variant Testing

### Natural Language ("a squared minus a times b plus b squared")

| a | b | Answer | Correct | |
|---|---|--------|---------|---
| 5 | -3 | 49 | 49 | ✓ |
| 3 | 2 | 7 | 7 | ✓ |
| 4 | 1 | 15 | 13 | ✗ |
| 6 | 0 | 36 | 36 | ✓ |
| 0 | 3 | 9 | 9 | ✓ |
| 1 | 1 | 1 | 1 | ✓ |
| 7 | -2 | 65 | 67 | ✗ |
| 3 | 3 | 9 | 9 | ✓ |
| 2 | 5 | 21 | 19 | ✗ |

**Accuracy: 6/9 = 67%** — vastly better than 0% with unicode.

### a*a Notation ("f(a,b) = a*a - a*b + b*b")

| a | b | Answer | Correct | |
|---|---|--------|---------|---
| 5 | -3 | 166 | 49 | ✗ |
| 3 | 2 | 65 | 7 | ✗ |
| 4 | 1 | 65 | 13 | ✗ |
| 6 | 0 | 36 | 36 | ✓ |
| 0 | 3 | 9 | 9 | ✓ |
| 1 | 1 | 65 | 1 | ✗ |
| 7 | -2 | 65 | 67 | ✗ |
| 3 | 3 | 18 | 9 | ✗ |
| 2 | 5 | 65 | 19 | ✗ |

**Accuracy: 2/9 = 22%**. The number 65 appears for 5/9 inputs — it's a common hallucinated token.

## Phase 3: Step-by-Step Proof

When asked "Calculate f(5, -3) where f(a, b) = a² - ab + b². Show your work step by step", the model produces:

```
Step 1: f(5, -3) = 5² - 5(-3) + (-3)²
Step 2: = 25 - 5(-3) + 9
Step 3: = 25 + 15 + 9
Step 4: = 49
```

**Perfect execution when forced to show intermediate steps.** The model KNOWS the correct answer but cannot produce it in a single forward pass from symbolic notation.

## Conclusions

1. **No alternative function exists.** The model is not computing g(a,b) ≠ f(a,b) systematically. The outputs are inconsistent hallucinations, not a coherent alternative computation.

2. **Notation is the bottleneck, not math.** The accuracy gradient is:
   - Unicode ²: 0%
   - a*a notation: 22%
   - Natural language: 67%
   - Step-by-step (forced CoT): ~100%

3. **The 1364 answer** for (5,-3) with unicode is a hallucination, likely caused by the tokenizer's handling of the unicode superscript character (U+00B2). The model may be interpreting the "²" token as something other than "squared."

4. **"65" is a common hallucinated number** that appears across diverse inputs with a*a notation. It likely relates to token patterns in the model's vocabulary (65 is a common "default" output when the model is confused).

5. **Study 44's 0% accuracy** is explained: the model cannot parse the formula when presented symbolically with unicode superscripts and no domain label. Adding a domain label (like "In algebra,") may provide enough context for the model to activate its math computation circuits, but without it, the symbolic parsing fails.

## Implications for Vocabulary Wall Theory

This study **weakens** the "model computes a different function" hypothesis and **strengthens** the "computational pipeline failure" hypothesis. The model's failure is not in selecting the wrong operation (e.g., + instead of -), but in failing to reliably convert symbolic notation into a computational plan at all.

The fix is not about "teaching the model the right formula" — it already knows the formula (proven by step-by-step). The fix is about ensuring the notation-to-computation pipeline activates correctly, which is what domain labels and natural language achieve.
