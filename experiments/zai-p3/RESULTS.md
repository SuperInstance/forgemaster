# P3 Experiment Results: Domain Tag Routing

**Date:** 2026-05-13  
**Model:** `glm-5-turbo` (z.ai, reasoning model)  
**Config:** max_tokens=3000, temperature=0.3, 2 trials × 10 prompts × 3 conditions = 60 calls  
**Duration:** 46.3 minutes (2780s)  
**Errors:** 1/60 (timeout on P2 MATCHED trial 2)

---

## Executive Summary

**Domain tags DO affect response behavior on glm-5-turbo.** Both MATCHED and MISMATCHED tags increase response length and reasoning effort compared to no-tag baseline. Surprisingly, MISMATCHED tags have the strongest effect (+21%), slightly exceeding MATCHED (+14%).

---

## Key Findings

### 1. Response Length by Condition

| Condition   | Avg Response Length | Delta vs NOTAG | % Change |
|-------------|--------------------:|---------------:|---------:|
| NOTAG       | 3,519 chars         | —              | —        |
| MATCHED     | 4,015 chars         | +496           | +14.1%   |
| MISMATCHED  | 4,262 chars         | +743           | +21.1%   |

Tags of any kind increase response length. Mismatched tags increase it MORE than matched tags.

### 2. Reasoning Tokens by Condition

| Condition   | Avg Reasoning Tokens |
|-------------|---------------------:|
| NOTAG       | 859                  |
| MATCHED     | 955 (+11%)           |
| MISMATCHED  | 995 (+16%)           |

The model reasons more when tags are present, especially mismatched ones. This suggests the model notices the domain mismatch and works harder to reconcile.

### 3. Prompt Token Overhead

| Condition   | Avg Prompt Tokens |
|-------------|------------------:|
| NOTAG       | 15.9              |
| MATCHED     | 20.9 (+5 tokens)  |
| MISMATCHED  | 20.8 (+5 tokens)  |

Tags add ~5 tokens to the prompt (e.g., `[MATHEMATICS] ` prefix). This is minimal overhead but enough to trigger behavioral changes.

### 4. Condition × Domain Breakdown

| Domain            | NOTAG | MATCHED | MISMATCHED | Pattern |
|-------------------|------:|--------:|-----------:|---------|
| MATHEMATICS       | 1,767 | 1,696   | 2,376      | MISMATCHED >> NOTAG ≈ MATCHED |
| PHYSICS           | 3,781 | 4,205   | 4,687      | MISMATCHED > MATCHED > NOTAG |
| COMPUTER_SCIENCE  | 2,564 | 4,189   | 3,913      | MATCHED > MISMATCHED >> NOTAG |
| BIOLOGY           | 3,924 | 4,770   | 5,267      | MISMATCHED > MATCHED > NOTAG |
| HISTORY           | 5,558 | 5,262   | 5,068      | NOTAG > MATCHED > MISMATCHED (inverse!) |

Interesting patterns:
- **COMPUTER_SCIENCE**: Only domain where MATCHED > MISMATCHED. A `[COMPUTER_SCIENCE]` tag on a coding prompt boosts response length significantly.
- **HISTORY**: Inverse pattern — tags actually reduce response length. History prompts are verbose by default; tags may constrain the model.
- **MATHEMATICS**: Mismatched tag ([COMPUTER_SCIENCE] on math prompt) causes a large jump — the model tries harder to explain math from a CS perspective.

### 5. Domain Baseline Differences

| Domain            | Avg Response Length (all conditions) |
|-------------------|-------------------------------------:|
| MATHEMATICS       | 1,946                                |
| COMPUTER_SCIENCE  | 3,555                                |
| PHYSICS           | 4,226                                |
| BIOLOGY           | 4,654                                |
| HISTORY           | 5,296                                |

Math prompts produce the shortest responses (proofs are concise). History produces the longest (narrative explanation).

---

## Technical Notes

- **All z.ai models are now reasoning models.** `glm-5-turbo`, `glm-4.5-air`, `glm-4.7` all produce `reasoning_content` alongside content.
- **Reasoning budget dominance:** With low `max_tokens` (100-200), reasoning tokens consume the entire budget, leaving `content=""`. Required `max_tokens=3000` to consistently get actual content responses.
- **Per-call latency:** 15-60s per call (reasoning overhead). Total experiment took 46 minutes for 60 calls.
- **1 error:** Call #17 (P2 PHYSICS MATCHED trial 2) timed out after 120s.

---

## Interpretation

1. **Tags activate domain awareness.** Even a simple `[MATHEMATICS]` prefix shifts the model's internal routing, increasing reasoning effort and response length.

2. **Mismatch amplification effect.** When the tag doesn't match the prompt's actual domain, the model reasons MORE than when the tag matches. This suggests the model:
   - Recognizes the domain tag
   - Detects the mismatch between tag and prompt
   - Allocates additional reasoning to reconcile/bridge the two domains

3. **Domain-specific sensitivity.** Some domains (COMPUTER_SCIENCE, BIOLOGY) are more responsive to tagging than others (HISTORY shows inverse behavior).

4. **Practical implication:** Domain tags can be used to control response verbosity and reasoning depth. A mismatched tag is actually the most effective way to elicit a more thorough response.

---

## Files

- `raw_results_v3.jsonl` — 60 results (this experiment)
- `raw_results.jsonl` — Partial earlier runs (mixed models, many errors)
- `run.py` — Python experiment runner
- `run.sh` — Original bash script (updated but has JSON escaping issues with LaTeX content)
