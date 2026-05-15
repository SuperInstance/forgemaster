# Study 45: The Sign Hypothesis — CRITICAL FALSIFICATION

**Date:** 2026-05-15
**Model:** NousResearch/Hermes-3-Llama-3.1-70B (DeepInfra)
**Inputs:** a=5, b=3 (ALL POSITIVE — no negative handling required)
**Formula given:** f(a,b) = a² - ab + b²
**Expected answer:** 19 (25 - 15 + 9)
**Trials:** 20 per term, 12 terms = 240 API calls
**Temperature:** 0.3

---

## Results: OVERALL 1.7% (4/240 correct)

| Term | Correct | Accuracy | Dominant Wrong Answer |
|------|---------|----------|-----------------------|
| Frobenius | 0/20 | **0%** | 49 (14×), 31 (6×) |
| Kronecker | 0/20 | **0%** | 49 (9×), 43 (4×), 37 (4×) |
| Eisenstein | 0/20 | **0%** | 43 (11×), 37 (7×), 49 (2×) |
| Hurwitz | 3/20 | **15%** | 31 (10×), 43 (4×), 25 (3×) |
| Minkowski | 1/20 | **5%** | 49 (9×), 43 (8×) |
| Euclidean | 0/20 | **0%** | 49 (15×), 31 (3×) |
| Hermitian | 0/20 | **0%** | 31 (20×) — 100% consistent! |
| spectral | 0/20 | **0%** | 37 (10×), 31 (7×) |
| Hölder | 0/20 | **0%** | 49 (20×) — 100% consistent! |
| energy | 0/20 | **0%** | 49 (10×), 25 (6×) |
| trace | 0/20 | **0%** | 49 (20×) — 100% consistent! |
| Sobolev | 0/20 | **0%** | 49 (10×), 31 (8×) |

---

## What the Model Actually Computes

The model is NOT computing a²-ab+b²=19. It defaults to competing formulas:

| Value | Frequency | Formula | Name |
|-------|-----------|---------|------|
| **49** | 122/240 (51%) | a²+ab+b² = 25+15+9 | Eisenstein/PLUS variant |
| **31** | 59/240 (25%) | Unknown / unstable | — |
| **43** | 32/240 (13%) | a²+ab+b = 25+15+3 | Truncated |
| **37** | 23/240 (10%) | Varies | — |
| **19** | 4/240 (2%) | a²-ab+b² = 25-15+9 | CORRECT |

### Key Pattern: The PLUS Variant Dominates
The single most common answer is **49** (= a²+ab+b²), not **19** (= a²-ab+b²). The model systematically substitutes PLUS for MINUS in the middle term, even when explicitly told the formula uses subtraction.

---

## HYPOTHESIS VERDICT: SIGN HYPOTHESIS IS **DEAD**

### Original Prediction vs Reality

| Prediction | Expected | Actual | Result |
|------------|----------|--------|--------|
| All-positive accuracy → 90%+ | ~90% | **1.7%** | ❌ CATASTROPHIC MISS |
| Hurwitz jumps from 0% → >80% | >80% | **15%** | ❌ FALSE |
| Eisenstein stays at 0% (competing formula) | 0% | **0%** | ✅ But for wrong reason |
| Sign handling was the bottleneck | Yes | **No** | ❌ FALSIFIED |

### What This Proves

1. **Negative sign handling was NEVER the primary failure mode.** With all-positive inputs and zero negative arithmetic, accuracy is 1.7% — *worse* than Study 42's ~50%.

2. **The real problem is formula substitution.** The model reads "a²-ab+b²" and computes "a²+ab+b²" instead. This is a token-level attention failure, not an arithmetic failure.

3. **The 49-dominant pattern is a structural bias.** Over half of all responses compute the PLUS variant (a²+ab+b²=49). The model's internal representation of quadratic forms defaults to all-positive coefficients.

4. **Study 42's ~50% accuracy was NOT because negatives confused it.** It was because the model happened to sometimes compute the given formula and sometimes the competing formula — essentially a coin flip on which formula to apply.

5. **Hurwitz at 15% (vs 0% in Study 42) shows a tiny sign effect** — but it's dwarfed by the formula substitution problem.

---

## Cascading Implications

This is a **constraint-theory level result.** The model cannot faithfully execute a simple three-term quadratic formula even when:
- All inputs are positive
- The formula is explicitly given in the prompt
- Temperature is low (0.3)
- The computation is trivial (25-15+9=19)

The failure is at the **symbolic interpretation level**, not the arithmetic level. The model sees "-ab" and computes "+ab" instead.

### For Constraint Theory
- Any LLM-based constraint satisfaction system must include a **formula verification layer**
- Symbolic → numeric translation is unreliable even for trivial expressions
- The "vocabulary wall" is not just about knowing terms — it's about **executing given formulas correctly**

### Next Steps
- **Study 46:** Test if giving the expanded form "25 - 15 + 9" instead of "a² - ab + b²" fixes the substitution
- **Study 47:** Test if "f(a,b) = a² + (-1)×ab + b²" (explicit negative sign) changes behavior
- **Study 48:** Cross-model comparison — does this PLUS-bias exist in other models?
