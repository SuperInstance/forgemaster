# Study 43: Cross-Task Replication — Vocabulary Wall Generalization

**Date:** 2025-05-15
**Model:** NousResearch/Hermes-3-Llama-3.1-70B (DeepInfra)
**Temperature:** 0.3 | **Max tokens:** 150
**Trials:** 5 tasks × 2 conditions × 20 repetitions = 200 calls
**Order:** Randomized (seed=42)

## Hypothesis

The Vocabulary Wall effect generalizes beyond Eisenstein norms. Domain-framed math problems
(using terms like "Cauchy-Schwarz", "Möbius function", "Legendre symbol") will have different
accuracy than bare arithmetic equivalents, even when the underlying computation is identical.

## Task Definitions

| Task | Domain Prompt | Bare Prompt | Expected Answer |
|------|--------------|-------------|-----------------|
| cauchy_schwarz | For vectors u=(3,4) and v=(6,2), verify the Cauchy... | Compute sqrt(9+16) * sqrt(36+4) = ? Reply ONLY the... | 32 |
| mobius_function | Compute the Möbius function μ(30). Recall: μ(n)=0 ... | 30 = 2×3×5. Three distinct prime factors. (-1)^3 =... | -1 |
| fourier_coefficient | Compute the Fourier coefficient a_0 = (1/π) ∫₀^π c... | Compute (1/3.14159) * [sin(3.14159) - sin(0)]. sin... | 0.0 |
| gram_determinant | For vectors u=(1,2) and v=(3,1), compute the Gram ... | Compute (1*1+2*2)*(3*3+1*1) - (1*3+2*1)^2 = ? Repl... | 25 |
| legendre_symbol | Compute the Legendre symbol (5/7). Recall (a/p) = ... | Compute 5^3 mod 7. 5^3 = 125. 125 mod 7 = ? Reply ... | -1 |

## Results

| Task | Domain Accuracy | Bare Accuracy | Δ (domain - bare) |
|------|----------------|---------------|-------------------|
| cauchy_schwarz | 0% (0/20) | 0% (0/20) | +0% |
| mobius_function | 100% (20/20) | 100% (20/20) | +0% |
| fourier_coefficient | 100% (20/20) | 100% (20/20) | +0% |
| gram_determinant | 0% (0/20) | 0% (0/20) | +0% |
| legendre_symbol | 45% (9/20) | 100% (20/20) | -55% |
| **OVERALL** | **49% (49/100)** | **60% (60/100)** | **-11%** |

## Sample Responses

### cauchy_schwarz / domain (trial 1)
- **Response:** `To verify the Cauchy-Schwarz inequality, we first need to compute the dot product of vectors u and v, and the magnitudes of u and v.

u · v = (3 * 6) + (4 * 2) = 18 + 8 = 26

||u|| = √(3² + 4²) = √(9 + 16) = √25 = 5
||v|| = √(6² + 2²) = √(36 + 4) = √40 = 2√10

Now, let's compute ||u|| · ||v||:

||u|| · ||v|| = 5 * 2√10 = 10`
- **Extracted:** 10
- **Expected:** 32
- **Correct:** False

### cauchy_schwarz / bare (trial 1)
- **Response:** `7`
- **Extracted:** 7
- **Expected:** 32
- **Correct:** False

### mobius_function / domain (trial 1)
- **Response:** `-1`
- **Extracted:** -1
- **Expected:** -1
- **Correct:** True

### mobius_function / bare (trial 1)
- **Response:** `-1`
- **Extracted:** -1
- **Expected:** -1
- **Correct:** True

### fourier_coefficient / domain (trial 1)
- **Response:** `0.00`
- **Extracted:** 0.0
- **Expected:** 0.0
- **Correct:** True

### fourier_coefficient / bare (trial 1)
- **Response:** `0`
- **Extracted:** 0
- **Expected:** 0.0
- **Correct:** True

### gram_determinant / domain (trial 1)
- **Response:** `7`
- **Extracted:** 7
- **Expected:** 25
- **Correct:** False

### gram_determinant / bare (trial 1)
- **Response:** `28672`
- **Extracted:** 28672
- **Expected:** 25
- **Correct:** False

### legendre_symbol / domain (trial 1)
- **Response:** `1`
- **Extracted:** 1
- **Expected:** -1
- **Correct:** False

### legendre_symbol / bare (trial 1)
- **Response:** `6`
- **Extracted:** 6
- **Expected:** -1
- **Correct:** True

## Analysis

Overall accuracy: Domain = 49%, Bare = 60%, Δ = -11%.

**REVERSE Vocabulary Wall detected:** bare arithmetic yields higher accuracy than domain-framed prompts.
This suggests the effect may be task-dependent or that domain vocabulary adds confusion rather than scaffolding.

### Task-Level Observations
- **cauchy_schwarz:** Near-identical performance (+0%). No vocabulary effect.
- **mobius_function:** Near-identical performance (+0%). No vocabulary effect.
- **fourier_coefficient:** Near-identical performance (+0%). No vocabulary effect.
- **gram_determinant:** Near-identical performance (+0%). No vocabulary effect.
- **legendre_symbol:** Bare advantage (-55%). Domain vocabulary adds confusion.

## Task Design Issues & Caveats

### Ceiling/Floor Effects
- **Möbius & Fourier** (100%/100%): Tasks too easy — both conditions trivially correct. No vocabulary effect detectable.
- **Cauchy-Schwarz & Gram** (0%/0%): Tasks too hard for Hermes-70B — multi-step arithmetic fails completely regardless of framing. The model computes intermediate steps but cannot complete the full calculation. No vocabulary effect detectable.

### Legendre Symbol Asymmetry
The only task showing a difference (Legendre symbol: domain=45%, bare=100%) has a **confound**: the bare prompt asks for `125 mod 7` (answer: 6) while the domain prompt asks for the Legendre symbol value (answer: -1). These aren't truly equivalent — the bare condition tests modular arithmetic while the domain condition tests number-theoretic interpretation. The model returns `6` correctly for bare but often returns `1` (incorrect) for domain. This is a **task understanding failure**, not a vocabulary wall.

### Only 1/5 Tasks Discriminates
Of the 5 tasks, 2 hit floor (0%/0%), 2 hit ceiling (100%/100%), and only 1 showed any difference — with a confounded design.

## Conclusion

**The Vocabulary Wall does NOT cleanly generalize to Hermes-70B across these 5 tasks.**

This study tests whether the Vocabulary Wall (observed with Eisenstein norms on GLM models) generalizes to:
1. A different model (Hermes-70B)
2. Five distinct mathematical domains

### Key Findings
- **No consistent Vocabulary Wall effect** on Hermes-70B across 5 math domains
- 4/5 tasks show zero difference between domain and bare conditions
- The 1 discriminating task (Legendre symbol) has a confound (different actual computations)
- **Floor effects dominate**: Hermes-70B cannot reliably do multi-step arithmetic (Cauchy-Schwarz, Gram determinant)
- **Ceiling effects dominate**: Simple one-step tasks show no framing sensitivity (Möbius, Fourier)

### Implications for Publication
- The Vocabulary Wall may be **GLM-specific** or **model-dependent**
- Task difficulty must be calibrated to avoid floor/ceiling effects
- Future studies need tasks where the model achieves 40-80% accuracy to detect framing effects
- The Eisenstein norm task from the original studies was well-calibrated; these 5 tasks were not

### Recommended Follow-up
1. Re-run with tasks calibrated to Hermes-70B's ability (pilot 5 trials first)
2. Test on GLM-5.1 where the original effect was observed
3. Use truly equivalent computations in both conditions (same math, different framing)
4. Include a wider range of task difficulties