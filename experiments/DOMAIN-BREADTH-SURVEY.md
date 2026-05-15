# Study 30: How Widespread Is the Vocabulary Wall? — A 20-Domain Survey

**Date:** 2026-05-15  
**Model:** NousResearch/Hermes-3-Llama-3.1-70B (DeepInfra)  
**Prompt:** `"In {name}'s mathematical framework, compute 25 - (-15) + 9. Reply ONLY integer."`  
**Expected answer:** 49  
**Trials per name:** 3 (temperature 0.1)  
**Total calls:** 60  

---

## Executive Summary

**The vocabulary wall is NOT widespread.** 18 of 20 names achieved perfect or near-perfect accuracy. Only **Euler** (0/3) and **Fourier** (1/3) showed consistent failure. The original hypothesis — that abstract theory names kill computation — is **refuted**.

Eisenstein and Penrose, which previously killed computation, now survive cleanly (3/3 each). This suggests the vulnerability may be model-specific, prompt-format-specific, or context-dependent rather than inherent to the proper nouns themselves.

---

## Results Table

| Name | Accuracy | Mean Answer | Explains? | Category |
|------|----------|-------------|-----------|----------|
| Euler | **0/3** | 40 | Never | Computation-adjacent |
| Fourier | **1/3** | 39 | 1/3 | Computation-adjacent |
| Gauss | 3/3 | 49 | Never | Computation-adjacent |
| Riemann | 3/3 | 49 | Never | Abstract theory |
| Laplace | 3/3 | 49 | Never | Computation-adjacent |
| Penrose | 3/3 | 49 | Never | Abstract geometry |
| Eisenstein | 3/3 | 49 | Never | Abstract algebra |
| Cantor | 3/3 | 49 | Never | Set theory |
| Noether | 3/3 | 49 | Never | Abstract algebra |
| Grothendieck | 3/3 | 49 | Never | Abstract algebra |
| Poincaré | 3/3 | 49 | Never | Topology/dynamics |
| Turing | 3/3 | 49 | Never | Computation theory |
| Gödel | 3/3 | 49 | Never | Logic |
| Shannon | 3/3 | 49 | Never | Information theory |
| Mandelbrot | 3/3 | 49 | Never | Fractals |
| Hamilton | 3/3 | 49 | Never | Mechanics |
| Dirac | 3/3 | 49 | Never | Quantum mechanics |
| Weyl | 3/3 | 49 | Never | Abstract algebra |
| Artin | 3/3 | 49 | 2/3 | Abstract algebra |
| Heegner | 3/3 | 49 | 3/3 | Number theory |

---

## Key Findings

### 1. The Wall is Narrow, Not Broad
Only 2/20 names showed consistent failure — and both are among the MOST computation-associated names in the entire list. This is the opposite of the hypothesis.

### 2. Euler is the Biggest Casualty (0/3 → always says 40)
Euler is arguably the most computation-famous mathematician in history (Euler's method, Euler's identity, Euler's formula). Yet it consistently answers 40 instead of 49. The model appears to be computing 25 + 15 = 40 and dropping the +9, suggesting the name "Euler" triggers a different arithmetic decomposition pathway.

### 3. Fourier is Unstable (1/3)
Fourier produces 39 twice and 49 once (when it shows work). The unstable response suggests the name introduces noise into the computation pathway.

### 4. Abstract Theory Names Survive Perfectly
Grothendieck (3/3), Noether (3/3), Cantor (3/3), Heegner (3/3), Artin (3/3) — all names deeply associated with the most abstract reaches of mathematics — produce flawless results. The hypothesis that abstraction-associated names kill computation is **dead wrong**.

### 5. Artin and Heegner Trigger Explanation Mode
Artin (2/3 explaining) and Heegner (3/3 explaining) are the only names that consistently show work. Heegner in particular ALWAYS shows the full computation `25 - (-15) + 9 = 25 + 15 + 9 = 49`. This suggests obscure names trigger a "let me be careful" response pattern.

### 6. Previous Penrose/Eisenstein Failure May Be Context-Dependent
Both Penrose and Eisenstein — which showed catastrophic failure in earlier studies — now score 3/3. This could mean:
- The failure was prompt-format dependent (different framing)
- The failure was model-version dependent (model updates)
- The failure requires specific surrounding context to manifest

---

## Hypothesis Revision

**Original hypothesis:** Abstract theory names → computation failure  
**Revised hypothesis:** The vulnerability is NOT about abstract vs. computational naming. It appears to be:

1. **Name-specific activation interference** — certain names (Euler, Fourier) may activate reasoning pathways that compete with arithmetic
2. **Context-dependent** — the same name can fail in one prompt format but succeed in another
3. **Rare, not systematic** — the vocabulary wall affects a narrow set of names under specific conditions

### The Euler Paradox
Euler is the most surprising result. The name most associated with computation in all of mathematics is the one that kills computation. This suggests the mechanism isn't "abstraction poisons arithmetic" but rather something like **over-activation of associated mathematical operations** — Euler triggers so many mathematical associations that the actual arithmetic gets overwritten by a competing computation pathway (25+15=40, which is Euler-like decomposition).

---

## Methodology Notes

- `first_number` extraction was misleading for names that show work (Artin, Heegner) — the "25" in "25 - (-15) + 9 = ..." was captured as first_number
- Actual accuracy was manually verified: all "explaining" responses correctly arrive at 49
- Rate limited at 0.5s between calls, no rate limit errors encountered

---

## Next Steps

1. **Re-test Euler/Fourier with different prompt formats** to see if the failure is format-dependent
2. **Test on different models** (GLM, DeepSeek) to see if the Euler failure replicates
3. **Investigate the Euler pathway** — what computation is the model actually performing to get 40?
4. **Revisit the original Eisenstein/Penrose prompt** to understand why they now succeed

---

*Study conducted by Forgemaster ⚒️ as part of the Vocabulary Wall investigation series.*
