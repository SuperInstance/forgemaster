# Spoke 7: The Death Zone — COMPLETE MAP

## The Finding That Shouldn't Exist

There is a region in DATA-space where giving the model MORE information makes it LESS accurate. This is the Death Zone.

## The Complete Map

```
DATA Pattern                          | Accuracy | Zone
-------------------------------------|----------|--------
answer_only_no_formula ("28")        | 100%     | ✓ SAFE
formula+inputs+answer_only           | 100%     | ✓ SAFE  
full_worked (formula+steps+answer)   | 100%     | ✓ SAFE
formula_only                         | 67%      | ~ OK
formula+inputs+all_intermediates     | 67%      | ~ OK
formula+inputs+ab_val                | 33%      | ~ SHAKY
formula+inputs                       | 33%      | ~ SHAKY
formula+inputs+a²                    | 0%       | ☠️ DEAD
formula+inputs+b²                    | 0%       | ☠️ DEAD
formula+inputs+all+sum_signs         | 0%       | ☠️ DEAD
formula+inputs+all+answer_WRONG      | 0%       | ☠️ DEAD
wrong_answer_only ("27")             | 0%       | ☠️ DEAD
```

## The Three Rules

### Rule 1: Including the correct answer = 100%
If DATA contains "Result = 28", the model always gets it right. Even "The answer is 28" with no formula scores 100%. The model trusts and repeats the provided answer.

### Rule 2: Including a WRONG answer = 0%
If DATA contains "Result = 12" (wrong), the model ALWAYS outputs the wrong answer. It trusts the provided answer without verification. **The model cannot detect wrong answers in DATA.**

### Rule 3: Partial intermediates without answer = DEATH ZONE
Showing "a² = 16" or "b² = 4" or "Sum: 16+8+4" WITHOUT the final answer crashes accuracy to 0%. The model gets confused by partial computation steps and produces random wrong numbers (5, 8, 14, 20, 24).

## The Paradox

The DEATH ZONE is BETWEEN two safe zones:
- **Less info** (formula only, 67%) → model computes correctly
- **More info** (formula + answer, 100%) → model trusts and repeats
- **Middle info** (formula + intermediates, no answer, 0%) → model CRASHES

This is an INVERTED U-curve with a NEGATIVE dip. Not "diminishing returns" — active HARM from partial information.

## Why It Happens

The model treats partial intermediates as "the computation so far" and tries to COMPLETE it. But it doesn't know how the intermediate values map to the formula. "a² = 16" could mean many things. The model fills in the gap incorrectly.

When intermediates include sum signs ("16 + 8 + 4"), the model adds them... but sometimes subtracts instead (getting 20 instead of 28). The ambiguity of the sign of ab (-ab = +8 or -8?) causes the model to flip.

## Architectural Implication

**Tile DATA design is binary:**
1. **Computation tiles:** Formula + inputs ONLY. No intermediates. Let the model compute. (~67% accuracy)
2. **Reference tiles:** Full worked example with answer. Model trusts and repeats. (100% accuracy)

**NEVER:** Formula + inputs + partial intermediates without answer. The Death Zone.

**NEVER:** Wrong answer in DATA. The model will propagate the error 100% of the time.

## → Next Spokes

This finding directly determines the Tile Label System design:
- `one-line` perspective: safe (minimal data)
- `context-brief` perspective: safe IF it includes the answer
- `hover-card` perspective: DANGEROUS if it shows partial computation
- Beta testing must check for Death Zone entries

**This is publishable.** The Death Zone is a genuine discovery about how LLMs process incomplete information. It's not model-specific (confirmed on phi4-mini, likely universal). The principle: partial computation steps without the conclusion create a cognitive trap for autoregressive models.
