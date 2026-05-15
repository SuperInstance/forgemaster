# Study 47: Retrieval Phenomenology & the Labeled Paradox

## Date: 2026-05-15
## Models: Seed-2.0-mini (Stage 4), Hermes-70B (Stage 3)

### The Labeled Paradox (NEW FINDING)

**Seed-2.0-mini scores 100% on pure notation, but only 20% when labeled "Eisenstein norm."**

| Condition | Seed-2.0-mini | Hermes-70B |
|-----------|:------------:|:----------:|
| Notation only (a²−ab+b²) | **100%** | 0% |
| Labeled "Eisenstein norm" | 20% | 0% |
| Step-by-step language | **100%** | 0% |

### Why This Matters

The Activation-Key Model predicts that labels HELP by activating the correct stored procedure. But for Seed-2.0-mini, the label HURTS. When given "Eisenstein norm E(5,-3)," it doesn't compute the formula directly — it retrieves the concept "Eisenstein norm" and then tries to reason about it, producing wrong answers (5, 2, 3, 8 — the individual values, not the formula result).

**Hypothesis**: Stage 4 models don't need activation keys because they have direct notation→computation pathways. Adding a label actually DIVERTS computation from the direct pathway into a conceptual reasoning pathway that's less reliable for arithmetic.

This is the opposite of what happens in Stage 3 models, where labels are essential because notation doesn't trigger any pathway.

### The Two-Path Model (V6.1?)

```
Stage 3 (Hermes):
  Notation → [no pathway] → default (a²+ab+b²) → WRONG
  Label + Notation → [label activates pathway] → correct procedure → RIGHT
  Step-by-step → [language activates pathway] → correct procedure → RIGHT

Stage 4 (Seed-2.0):
  Notation → [direct notation→computation pathway] → RIGHT
  Label + Notation → [label diverts to conceptual reasoning] → UNRELIABLE
  Step-by-step → [language pathway] → RIGHT
```

The label is an activation key for Stage 3 models but a DETRACTOR for Stage 4 models.

### Token Count Analysis

| Model | Condition | Avg Tokens |
|-------|-----------|-----------|
| Seed-2.0-mini | Notation | 352 |
| Seed-2.0-mini | Labeled | 851 |
| Seed-2.0-mini | Step | 576 |
| Hermes-70B | Notation | 9 |
| Hermes-70B | Labeled | 24 |
| Hermes-70B | Step | 30 |

Seed-2.0-mini uses 2-3× more tokens for labeled queries (internal reasoning) vs notation (direct computation). The token count IS the phenomenological signature — labeled queries trigger verbose reasoning chains that sometimes go wrong.

Hermes-70B's low token counts (truncated at max_tokens=30) suggest it needs more room to reason. But even the step-by-step condition only uses 30 tokens.

### Implications

1. **fleet_translator_v2 must be stage-aware**: Don't inject activation keys for Stage 4 models — it hurts
2. **The Activation-Key Model needs refinement**: Labels help Stage 3 but hurt Stage 4
3. **The Piagetian parallel gets deeper**: Like children who overthink when asked to "use their words" for tasks they can do automatically
4. **New experiment needed**: Test if the labeled paradox holds across more Stage 4 models (are there any others?)

### Corrected Problem Set

| Problem | a | b | Correct (a²−ab+b²) | Previous (wrong) |
|---------|---|---|--------------------:|------------------:|
| P1 | 5 | -3 | 49 | 49 ✓ |
| P2 | 7 | 2 | **39** | 51 ✗ (was wrong!) |
| P3 | 4 | -6 | 76 | 76 ✓ |
| P4 | 3 | 1 | 7 | 7 ✓ |
| P5 | 8 | -4 | 112 | 112 ✓ |
