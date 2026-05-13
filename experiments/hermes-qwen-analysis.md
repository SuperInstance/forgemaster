# Hermes-70B & Qwen3-235B: Structure > Scale Follow-Up Analysis

## Results Grid (All on 5-point scale, same 5 hard questions)

| Model | Naive | Structured | Δ |
|---|---|---|---|
| **Hermes-3-Llama-3.1-70B** | 3.00 | 2.40 | **-0.60** |
| **Qwen/Qwen3-235B-A22B** | 2.60 | 2.20 | **-0.40** |

### Prior data (from Structure > Scale hard test):
| Model | Naive | Structured | Δ |
|---|---|---|---|
| qwen3:0.6b (tiny) | 1.40 | 1.20 | -0.20 |
| glm-5-turbo (mid) | 1.80 | 3.20 | **+1.40** |
| Seed-2.0-mini (large) | 3.20 | 2.60 | **-0.60** |
| **Hermes-70B** | 3.00 | 2.40 | **-0.60** |
| **Qwen3-235B** | 2.60 | 2.20 | **-0.40** |

## Analysis: Where Do These Models Fall?

### Hermes-70B: Same as Seed-2.0-mini on structure penalty
Hermes-70B gets **exactly the same -0.60 structure penalty** as Seed-2.0-mini from the original experiment. The pattern is striking:

- **Q1** (Eisenstein drift): naive=3 → structured=2 — lost context integration
- **Q3** (baton+Lighthouse): naive=2 → structured=2 — flat, but picked up more false claims (+2 vs +1)
- **Q5** (creative synthesis): naive=3 → structured=1 — **biggest hit**, structured framing hurt the creative "not a coincidence" argument badly
- **Q4** (True/False): 5 in both — well-defined factual questions perform equally well regardless of format

The false claims also rose: herm70B structured had **6 total false claims vs 3 naive**. The PLATO formatting appears to have introduced confusion rather than clarity.

### Qwen3-235B: Smaller penalty, but same direction
Qwen3-235B shows a **-0.40 drop** with structure, smaller than both Hermes-70B and Seed-2.0-mini (-0.60 each).

- **Q1** (Eisenstein drift): naive=2 → structured=1 — structure hurt comprehension
- **Q4** (True/False): structured=4 (BEST) — factual question actually improved with structure
- **Q5** (creative): naive=3 → structured=1 — same creative hit as Hermes-70B and Seed-2.0-mini

Notably, Qwen3-235B had **zero false claims in naive** and only **1 false claim in structured** — much cleaner than Hermes-70B. But it also scored lower overall, suggesting it plays it safer rather than being smarter.

### The "Sweet Spot" Hypothesis

The original finding was:

```
       tiny (0.6b)    mid (turbo)     large (70B+)     creative task
Δ:       -0.20          +1.40           -0.60            -0.60+ hurt
```

**The sweet spot was ~glm-5-turbo size** — large enough to understand and use structure, not so large that it sees structure as noise.

**Hermes-70B and Qwen3-235B confirm this pattern**: both are in the "large model" category where structure hurts creative synthesis tasks. Neither falls into the sweet spot.

### Why Structure Hurts Large Models on Creative Tasks

Looking at Q5 specifically across all large models:

| Model | Naive Q5 | Structured Q5 | Δ |
|---|---|---|---|
| Seed-2.0-mini | — | — | large drop |
| Hermes-70B | 3 | 1 | -2 |
| Qwen3-235B | 3 | 1 | -2 |

Q5 is the most creative question — it asks the model to *construct an argument that √3 appearing twice is not a coincidence*. With naive context (prose), large models can freely recombine information. With PLATO-structured context, they seem to **pattern-match against the room structure** instead of synthesizing across domains. They treat the structured rooms as separate buckets and fail to cross-pollinate.

## Conclusion

1. **Sweet spot holds**: Mid-range models (~glm-5-turbo) benefit from structure (+1.40). Large models (70B+) and tiny models (<1B) are both hurt.
2. **Hermes-70B (-0.60)** tracks Seed-2.0-mini (-0.60) almost exactly — same magnitude structure penalty.
3. **Qwen3-235B (-0.40)** is slightly less affected, possibly due to MoE architecture treating structured input more like a routing problem.
4. **Creative tasks are the weakest link**: Q5 was the hardest hit across ALL large models in structured condition.
5. **Factual questions are structure-agnostic**: Q4 (True/False) scored equally or better with structure in all models.
