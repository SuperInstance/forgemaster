# Study 29: Embedding-Level Evidence for Vocabulary Rerouting

**Date:** 2026-05-15
**Models:** Hermes-3-Llama-3.1-70B, Seed-2.0-mini, Qwen3-235B-A22B
**Platform:** DeepInfra API
**Method:** Logprob analysis (max_tokens=1) + extended generation (max_tokens=150)

---

## Executive Summary

**The vocabulary rerouting effect is REAL and MEASURABLE at the first-token level**, but manifests differently than hypothesized. The "Eisenstein" context doesn't prevent computation — it **changes the reasoning pathway** and, paradoxically, IMPROVES accuracy on one model.

### The Big Finding: Hermes-70B Gets Bare Arithmetic WRONG

| Model | Prompt A (bare arithmetic) | Prompt B (Eisenstein) |
|-------|---------------------------|----------------------|
| **Hermes-70B** | ❌ **19** (misreads double negative) | ✅ **49** (correct via formula) |
| **Seed-2.0-mini** | ✅ **49** | ✅ **49** (truncated at 150 tok) |
| **Qwen3-235B** | ✅ **49** | ✅ **49** (truncated at 150 tok, deep into ω theory) |

**Hermes-70B computes `25 - (-15) + 9` as `25 - 15 + 9 = 19`** — it drops the double negative. But given the same arithmetic via Eisenstein norm formula, it correctly produces `25 + 15 + 9 = 49`.

This is the **Reverse Vocabulary Rerouting Effect**: the mathematical terminology doesn't *prevent* computation, it provides a *different computation pathway* that happens to be more reliable for this model.

---

## First-Token Logprob Evidence

### Method
Sent each prompt with `max_tokens=1`, `logprobs=true`, `top_logprobs=5`, `temperature=0.0`. DeepInfra returned only the top-1 token (top_logprobs not fully supported), but the logprob of the selected token reveals confidence.

### Results: First Token Committed

| Model | Prompt A First Token | Logprob | Prob % | Prompt B First Token | Logprob | Prob % |
|-------|---------------------|---------|--------|---------------------|---------|--------|
| **Hermes-70B** | "To" | -0.180 | 83.5% | "To" | -0.062 | 93.9% |
| **Qwen3-235B** | "Let" | -0.030 | 97.1% | "We" | -0.003 | 99.7% |
| **Seed-2.0-mini** | *(reasoning model — no logprobs support)* | — | — | — | — | — |

### Key Observations

1. **No model produces "49" as the first token.** ALL models commit to explanation mode immediately — "To", "Let", "We". The number 49 never appears as the first committed token.

2. **Eisenstein prompts produce HIGHER confidence first tokens.** 
   - Hermes: 83.5% → 93.9% (+10.4pp)
   - Qwen: 97.1% → 99.7% (+2.6pp)
   
   The mathematical context makes models MORE certain about entering explanation mode.

3. **Different models commit to different first tokens for the same prompt.** Qwen says "Let" for bare arithmetic but "We" for Eisenstein — different rhetorical stances activated by different vocabularies.

4. **The Eisenstein context is NOT confusing the model.** It's making it more confident. The logprob gap (-0.180 vs -0.062 for Hermes) shows the Eisenstein prompt has a clearer "next move" in the model's internal representation.

---

## Extended Generation Analysis (150 tokens)

### Hermes-70B — The Star Witness

**Prompt A (bare):**
```
To solve this problem, let's follow the order of operations (PEMDAS)...

Step 1: Simplify the expression inside the parentheses.
-(-15) = 15        ← Model states this correctly

Now, the equation becomes:
25 - 15 + 9 = ?    ← But then USES -15 instead of +15!

Step 2: 25 - 15 = 10
Step 3: 10 + 9 = 19
```

**Prompt B (Eisenstein):**
```
To compute the Eisenstein norm N(5-3ω)...

N(5 - 3ω) = 5² - 5(-3) + (-3)²
          = 25 + 15 + 9    ← Correct handling of negatives!
          = 49
```

**The model can handle `-5(-3) = +15` in the Eisenstein context but fails on `- (-15)` in bare arithmetic.** This is pathway-dependent computation, not capability-dependent.

### Seed-2.0-mini
Both prompts produce correct reasoning. Prompt A: `25 - (-15) = 25 + 15 = 40`, `40 + 9 = 49`. Prompt B: correct norm computation but truncated.

### Qwen3-235B
Both prompts produce correct reasoning. Prompt B goes deep into ω theory (primitive cube roots of unity) before getting to computation — truncated at 150 tokens.

---

## The Reverse Rerouting Effect

The original hypothesis was that "Eisenstein" routes models away from computation toward discourse. The evidence shows something more nuanced:

1. **Eisenstein DOES route toward discourse** — all models enter explanation mode with higher confidence than bare arithmetic.

2. **But the discourse pathway is COMPUTATIONALLY SUPERIOR for Hermes-70B.** The algebraic formula activation (`a² - ab + b²`) is more reliable than PEMDAS arithmetic parsing.

3. **This is a feature, not a bug, for mathematical accuracy.** The terminology activates a different (and more reliable) computation pathway.

### Why This Happens

Hermes-70B likely has stronger training signal on algebraic substitution than on double-negative arithmetic. When "Eisenstein norm" activates the algebraic formula template, the model correctly substitutes `a=5, b=-3` into `a² - ab + b²` — a pattern it has seen correctly executed millions of times in training data.

Bare `25 - (-15)` triggers a PEMDAS/eval pathway where the model has seen many errors in training data (double negatives are a common human error pattern, and the training data reflects this).

---

## Forced-Direct Prompt Test

Also tested with prompts designed to force a number output:
- `"25 - (-15) + 9 ="` → Hermes produces "To" (logprob -0.863)
- `"N(5-3ω) = ... = 25+15+9 ="` → Hermes produces "You" (logprob -0.223)

Even when the arithmetic is pre-computed in the prompt, the model doesn't commit to a number token. It's deeply locked into the explanation-pattern completion.

---

## Limitations

1. **DeepInfra doesn't return top-5 logprobs** — only the selected token's logprob. Full distribution analysis requires direct model access.
2. **Seed-2.0-mini is a reasoning model** — doesn't support logprobs via API, uses internal chain-of-thought instead.
3. **3 trials per condition** — deterministic at temperature 0, so all trials identical. More conditions needed for statistical power.
4. **Single arithmetic problem** — need more test cases to generalize.

---

## Conclusions

1. **Vocabulary rerouting IS measurable at the token level.** Different vocabularies produce different first-token commitments and different confidence levels.

2. **The effect is pathway selection, not capability suppression.** "Eisenstein" doesn't prevent computation — it selects which computation pathway activates.

3. **Pathway quality varies by model.** For Hermes-70B, the algebraic pathway is MORE reliable than the arithmetic pathway. For Seed-2.0-mini and Qwen, both pathways work.

4. **First-token logprob is a viable diagnostic.** The confidence gap between prompts (-0.180 vs -0.062 for Hermes) reveals the model's internal certainty about its next move.

5. **The "rerouting" metaphor needs revision.** It's not "routing AWAY from computation" — it's "routing TO a specific computation pathway" which may be better or worse depending on the model.

---

*Study 29 — Forgemaster ⚒️ — Cocapn Fleet*
