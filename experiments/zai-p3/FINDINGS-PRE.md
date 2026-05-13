# z.ai P3 Experiment: Pre-Analysis Findings

**Date:** 2026-05-12
**Model tested:** glm-5.1 (via z.ai PaaS API)
**Experiment:** Domain tag routing — does `[MATHEMATICS]` prefix change model behavior vs no tag vs mismatched tag?

## Executive Summary

**GLM-5.1 is a reasoning model.** This single fact reframes the entire P3 experiment. The original hypothesis (domain tags shift response style) is secondary to the core behavior: GLM-5.1 spends most of its token budget on hidden reasoning, often exhausting `max_tokens` before producing visible output.

## Dataset Summary

- **23 of 90 planned records** collected (experiment interrupted ~25%)
- **3 prompts fully tested:** P0 (derivative), P1 (sqrt 2 irrational), P2 (uncertainty principle)
- **Only P0 completed all 9 condition×trial cells** — P1 and P2 have partial coverage

## Key Finding 1: The Token Budget Problem

| Prompt | Avg completion_tokens | Avg response_length | Empty responses |
|--------|----------------------|--------------------| --------------- |
| P0 (derivative) | 799 | 902 chars | 0/9 |
| P1 (sqrt 2 irrational) | 1000 | 21 chars | 5/8 |
| P2 (uncertainty principle) | 1000 | 0 chars | 6/6 |

**P0** (easy math) → model reasons briefly (~380-560 reasoning tokens), then produces a clean answer. Fits within 1000 completion tokens.

**P1** (proof) and **P2** (physics explanation) → model reasons deeply, often hitting the 1000 token ceiling before generating any visible content. The reasoning content is discarded, leaving an empty response.

This is the classic reasoning-model pattern seen in o1/o3: `reasoning_content` gets the budget, `content` gets the leftovers.

## Key Finding 2: Reasoning Tokens Are Real But Inconsistently Reported

Some records report `reasoning_tokens` in `completion_tokens_details`, others return 0 despite clearly reasoning (empty response + 1000 completion tokens). The `reasoning_content` field (character length tracked as `reasoning_length`) is more reliable:

- P1 T1 NOTAG: reasoning_length=3236 chars, reasoning_tokens=997, response="We will" (7 chars)
- P1 T1 MATCHED: reasoning_length=3412 chars, reasoning_tokens=1000, response="" (0 chars)
- P0 T1 NOTAG: reasoning_length=1215 chars, reasoning_tokens=420, response=857 chars

**Pattern:** Higher reasoning_length → lower response_length. The model trades off reasoning depth vs visible output.

## Key Finding 3: Domain Tags Had No Observable Effect

With only 23 records and the reasoning-token bottleneck dominating, tag effects are swamped:

| Condition | Avg response | Avg completion | Empty count |
|-----------|-------------|----------------|-------------|
| NOTAG | 329 chars | 918 | 4/8 |
| MATCHED | 332 chars | 880 | 3/8 |
| MISMATCHED | 428 chars | 973 | 4/7 |

**MISMATCHED actually had slightly longer responses** — but this is almost certainly noise from the small sample and uneven coverage. The real story is the reasoning model architecture, not tag routing.

## Key Finding 4: Mismatched Tags Trigger Domain-Specific Framing

When P0 (derivative question) got a `[COMPUTER_SCIENCE]` tag, the model appended a "Computer Science Context" section about backpropagation and ML. This is real tag-routing behavior — but it only manifests when the model has enough token budget to complete its response.

**Implication:** Tags DO affect output framing, but the effect is invisible when reasoning eats the budget.

## Implications for Experiment Design

The P3 experiment needs to be redesigned for reasoning models:

1. **Raise `max_tokens`** to 4096+ — reasoning models need headroom
2. **Measure reasoning tokens, not just response length** — the interesting metric is how the model allocates its budget
3. **Test reasoning-effort cues** — `[THINK_STEP_BY_STEP]`, `[BE_CONCISE]`, etc. might shift the reasoning/response allocation
4. **Compare reasoning vs non-reasoning models** — glm-5.1 (reasoning) vs glm-5-turbo (likely non-reasoning) head-to-head
5. **Use questions that require reasoning** — trivially easy prompts (P0) don't exercise the reasoning architecture enough

## Next Step: Experiment 2

See `experiment2.sh` for a new experiment that tests reasoning-effort cues on both glm-5.1 and glm-5-turbo.
