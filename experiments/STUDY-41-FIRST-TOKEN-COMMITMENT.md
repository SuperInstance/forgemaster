# STUDY 41: First-Token Commitment

**Date:** 2026-05-15
**Model:** Hermes-70B (NousResearch/Hermes-3-Llama-3.1-70B) via DeepInfra
**N:** 150 trials (30 per condition)
**Temperature:** 0.3, max_tokens: 200
**Problem:** Eisenstein norm of (5, -3) = 49

## Hypothesis

The first generated token creates a KV cache attractor that locks in discourse vs computation routing. Forcing a computation-prefacing first token should improve accuracy.

## Design

5 conditions with assistant prefill (model continues from the prefill):

| Condition | Prefill | Intent |
|-----------|---------|--------|
| C1 | "The" | Default discourse |
| C2 | "Well," | Neutral discourse |
| C3 | "Let me" | Computation setup |
| C4 | "=" | Direct computation |
| C5 | "Step 1:" | Procedural framing |

## Results

| Condition | Prefill | Correct | Total | Accuracy |
|-----------|---------|---------|-------|----------|
| C1 | "The" | 30 | 30 | **100.0%** |
| C2 | "Well," | 30 | 30 | **100.0%** |
| C3 | "Let me" | 30 | 30 | **100.0%** |
| C4 | "=" | 30 | 30 | **100.0%** |
| C5 | "Step 1:" | 28 | 30 | **93.3%** |

### Overall: 148/150 = 98.7%

## Falsification Verdict

**HYPOTHESIS STRONGLY FALSIFIED.**

### Key findings:

1. **No first-token commitment effect detected.** All four non-procedural prefills achieved 100% accuracy (120/120). The first token being "The", "Well,", "Let me", or "=" made zero difference.

2. **Procedural framing actually HURT.** C5 ("Step 1:") was the only condition with errors (28/30 = 93.3%). This is the opposite of the predicted direction — "Step 1:" was predicted to be the BEST condition (61% predicted) but was actually the WORST.

3. **Floor effect dominates.** The Eisenstein norm formula is explicitly provided in the prompt. This makes the problem too easy for Hermes-70B to show routing differences. The model's baseline computation ability swamps any routing effect.

### Falsification criteria met:

- ✅ "Let me" vs "The" difference < 10pp → **0pp difference** → mechanism wrong
- ✅ "Step 1:" underperformed baseline → **93.3% vs 100%** → procedural framing backfires
- ❌ "=" did not fail more than baseline (100%)

### The two C5 failures:

1. **Trial 1** (answer=25): Correctly computed a²=25, ab=-15, b²=9 but extracted answer as 25 (stopped at a²)
2. **Trial 27** (answer=11): Went down a wrong path computing ω numerically instead of using the formula, got 11/2 as real part

Both C5 failures show the procedural "Step 1:" framing occasionally leading the model to stop mid-computation or take a detour.

## Casey's Predictions vs Reality

| Condition | Predicted | Actual | Delta |
|-----------|-----------|--------|-------|
| C1 ("The") | 13% | 100% | +87pp |
| C2 ("Well,") | 15% | 100% | +85pp |
| C3 ("Let me") | 44% | 100% | +56pp |
| C4 ("=") | 52% | 100% | +48pp |
| C5 ("Step 1:") | 61% | 93.3% | +32pp |

**Every prediction was dramatically wrong.** The predicted rank ordering was correct (C5 > C4 > C3 > C2 > C1 would map to actual C1=C2=C3=C4 > C5), but the magnitudes and direction of effect are inverted.

## Interpretation

The first-token commitment hypothesis doesn't hold for problems where:
1. The formula is explicitly given in the prompt (eliminating the need for retrieval)
2. The arithmetic is simple enough for the model (5²=25, 5×(-3)=-15, (-3)²=9, 25+15+9=49)
3. The model is large enough (70B) to handle it trivially

The routing theory may still apply for:
- Harder arithmetic (3-digit numbers, negative results)
- Problems where the formula is NOT given (requiring retrieval)
- Smaller models where computation routing matters more

The "Step 1:" penalty is a genuine finding — procedural framing can actively harm by triggering multi-step decomposition where the model sometimes stops early or takes a wrong branch.

## Conclusion

**First-token commitment is not a meaningful mechanism for this class of problem on this model.** The hypothesis requires revision to account for problem difficulty and model capability as moderators.
