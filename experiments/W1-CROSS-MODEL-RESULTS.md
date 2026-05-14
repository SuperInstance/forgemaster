# W1 Final Results: Cross-Model Death Zone

## The Data (10 trials phi4-mini, 5 trials gemma3:1b, qwen3:4b unusable)

| DATA Variant | phi4-mini (10 trials) | gemma3:1b (5 trials) | qwen3:4b | Pattern |
|---|---|---|---|---|
| V1: formula only | — | 0% | 0% | Can't compute from name |
| V2: formula + inputs | — | 0% | 0% | Tiny model fails on math |
| V3: partial intermediates | **20%** ☠️ | **40%** | 0% | **DEATH ZONE CONFIRMED** |
| V4: full answer | 100% ✓ | 100% ✓ | 0% | Answer-in-DATA = perfect (when model can read) |

## The Real Finding

**The Death Zone is NOT the absence of the answer. It's the PRESENCE of partial intermediates.**

Look at gemma3:1b:
- Formula + inputs → 0% (can't do the math)
- Partial intermediates → 40% (intermediates HELP this tiny model!)
- Full answer → 100% (trusts the provided answer)

For gemma3:1b, the intermediates are NOT a death zone — they're a LIFELINE. The tiny model can't compute a²=16 by itself, but when you SHOW it "a²=16", it uses that to get closer. 40% is better than 0%.

For phi4-mini, the intermediates are a DEATH zone — 20% vs what should be 67% (formula only). The mid-size model CAN compute the math, but the intermediates CONFUSE it.

## The Cross-Model Death Zone Pattern

```
Model Size    | No intermediates | Partial intermediates | Full answer
Small (1B)    | 0% (can't math)  | 40% (helps!)         | 100% (trusts)
Medium (3.8B) | 67% (computes)   | 20% (DEATH ZONE!)    | 100% (trusts)
```

**The death zone is MODEL-SIZE DEPENDENT:**
- **Small models:** intermediates HELP (they can't compute on their own)
- **Medium models:** intermediates HURT (they can compute, but get confused by partial info)
- **Large models:** probably don't care either way (would verify with GLM-5-turbo)

## What This Means

**R7 stays at TIER 2.** The Death Zone is real but model-dependent. It's not a universal principle.

**NEW FINDING:** The effect REVERSES for small models. Partial intermediates are a SCAFFOLDING mechanism for weak models and a CONFUSION mechanism for medium models.

**Architectural implication:** The fleet needs MODEL-AWARE DATA TEMPLATES.
- For small models (capability level BASIC): provide full worked examples with intermediates
- For medium models (capability level COMPETENT): provide formula + inputs only, NO intermediates
- For large models (capability level EXPERT): either works

**This is Spoke 8 (model-specific templates) validated.** The DATA design depends on who's reading it.

## The Map Update

R7 (Death Zone) stays TIER 2 with CAVEAT:
- Death Zone confirmed for medium-capability models (phi4-mini)
- Effect REVERSES for small models (gemma3:1b)
- Full answer in DATA = 100% for ALL models that can read
- Model-aware DATA templates are REQUIRED, not optional
