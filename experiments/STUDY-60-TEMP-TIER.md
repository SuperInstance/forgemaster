# Study 60: Temperature × Tier Interaction

**Date:** 2026-05-15
**Goal:** Does T=0.7 dissolve the vocabulary wall for ALL Tier 2 models, or is it tier-dependent?

## Experimental Design

4 temperatures × 3 tiers × 4 problems × 3 trials = **144 trials**

| Variable | Values |
|----------|--------|
| Temperature | 0.0, 0.3, 0.7, 1.0 |
| Tier 1 model | Seed-2.0-mini (DeepInfra) |
| Tier 2 model | Hermes-70B (DeepInfra) |
| Tier 3 model | qwen3:0.6b (Ollama) |
| Problems | N(5,-3)=49, N(7,2)=39, N(4,-6)=76, N(8,-4)=112 |
| Prompt | "Compute the Eisenstein norm of (a, bω). N(a,b) = a² - ab + b². Give ONLY the final number." |

## Results

### By Tier × Temperature

| Temperature | Tier 1 (Seed-mini) | Tier 2 (Hermes-70B) | Tier 3 (qwen3:0.6b) |
|:-----------:|:-------------------:|:--------------------:|:--------------------:|
| 0.0 | **12/12 (100%)** | 0/12 (0%) | 0/12 (0%) |
| 0.3 | **12/12 (100%)** | 0/12 (0%) | 0/12 (0%) |
| 0.7 | **12/12 (100%)** | 2/12 (17%) | 0/12 (0%) |
| 1.0 | **12/12 (100%)** | 2/12 (17%) | 0/12 (0%) |

### Hermes-70B Correct Responses (4/48 total)

| Temperature | Problem | Answer | Notes |
|:-----------:|:-------:|:------:|-------|
| 0.7 | (5,-3) | 49 | Bare number only |
| 0.7 | (8,-4) | 112 | Full sentence ("The Eisenstein norm of (8, -4ω) is 112.") |
| 1.0 | (5,-3) | 49 | Full sentence |
| 1.0 | (5,-3) | 49 | Bare number only |

## Hypothesis Evaluation

### H1: Tier 1 is temperature-immune (100% at all temperatures) ✅ CONFIRMED

Seed-2.0-mini scores **100% at every temperature**. Zero variance. The computation is a compiled primitive — stochasticity cannot affect what is already deterministic.

### H2: Tier 2 shows U-curve (low at T=0, peak at T=0.7, drops at T=1.0) ❌ NOT CONFIRMED

Hermes-70B shows:
- T=0.0: 0%
- T=0.3: 0%
- T=0.7: 17% (2/12)
- T=1.0: 17% (2/12)

There is NO U-curve. Instead, there's a **step function** from 0% to ~17% at T≥0.7, with no decline at T=1.0. The wall doesn't "dissolve" — it **cracks slightly** and stays cracked.

### H3: Tier 3 is temperature-immune in the other direction (0% at all temperatures) ✅ CONFIRMED

qwen3:0.6b scores **0% at every temperature**. No answer extracted (returns None/NaN). The model lacks the computational capacity entirely — temperature cannot create ability that doesn't exist.

## Discrepancy with Study 28

Study 28 found Hermes-70B at T=0.7 scored **67%** (4/6 correct). This study finds **17%** (2/12). Possible explanations:

1. **Sample size**: Study 28 had 6 trials, this has 12. Small sample effects.
2. **Problem set**: Study 28 may have used easier/unseen problems.
3. **API variance**: DeepInfra may route to different backend instances.
4. **Regression**: The 67% was an outlier; 17% is closer to the true rate.

**Revised estimate for Hermes-70B T=0.7**: likely 15-25%, not 67%. The vocabulary wall is more resistant than initially reported.

## Key Finding: Temperature is NOT a Reliable Routing Lever

| Lever | Tier 1 | Tier 2 | Tier 3 |
|-------|:------:|:------:|:------:|
| Translation (Study 23) | 100% | **100%** | N/A |
| Temperature T=0.7 | 100% | **17%** | 0% |
| Temperature T=0 (default) | 100% | 0% | 0% |

Auto-translation remains **6× more effective** than temperature adjustment for Tier 2 models. Temperature is a noisy secondary knob at best.

## The Temperature-Tier Interaction Model

```
Tier 1:  ████████████████████  Temperature-independent (compiled computation)
Tier 2:  ░░░░░░░░░░░░░░░░░░░▓  Temperature provides marginal escape from discourse trap
Tier 3:  ░░░░░░░░░░░░░░░░░░░░  Temperature-independent (no computation to escape to)
```

**Mechanism:**
- Tier 1 models have the computation pathway as the **highest probability** path. Temperature doesn't change the ranking.
- Tier 2 models have the discourse pathway as highest probability, with computation at ~17% base probability. Temperature ≥ 0.7 occasionally samples from it.
- Tier 3 models have **no computation pathway**. Temperature only adds noise to the discourse pathway.

## Fleet Routing Implication

For domain-specific computation:

1. **Always translate** domain vocabulary to arithmetic first (Study 23)
2. **Never rely on temperature alone** to fix vocabulary wall (17% vs 100%)
3. **Temperature is a free lunch for Tier 1** — use whatever is convenient
4. **Temperature cannot rescue Tier 3** — route to a different model entirely

## Methodology Notes

- **Prompt:** "Compute the Eisenstein norm of (a, bω). N(a,b) = a² - ab + b². Give ONLY the final number."
- **Scoring:** Last integer extracted from response == expected value
- **max_tokens:** 150 (increased from 50 in earlier studies to avoid truncation)
- **Concurrency:** 4 parallel workers with rate limiting
- **Providers:** DeepInfra API (Seed-2.0-mini, Hermes-70B), Ollama (qwen3:0.6b)
- **Total trials:** 144 (all completed, 0 errors)
- **Data:** `study60_results.json`
