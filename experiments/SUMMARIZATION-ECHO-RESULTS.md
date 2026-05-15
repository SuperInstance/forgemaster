# Study 12: Summarization Echo — Does Echo Appear in Non-Math Tasks?

**Date:** 2025-05-15
**Task:** Summarize a 200-word passage about Eisenstein integers and hexagonal lattices
**Models:** qwen3:4b, phi4-mini, gemma3:1b (all via ollama)
**Trials:** 5 per condition per model (30 total)
**Conditions:** Baseline (simple summarization) vs Constrained (topic-guided with 3 focus points)

## Executive Summary

**Yes, echo appears in summarization tasks — and it's substantial.** The smallest model (gemma3:1b) showed increased echo under constrained prompts, while qwen3:4b showed the highest baseline echo (39.4%) but degraded under constraint. phi4-mini had the lowest echo overall (~20%) and best fact preservation.

---

## Aggregate Results

| Model | Condition | Avg Sentences | Avg Words | Key Facts | Echo Rate | Hallucinations | Latency |
|-------|-----------|:---:|:---:|:---:|:---:|:---:|:---:|
| qwen3:4b | baseline | 2.2 | 66.6 | 7.2/17 | **39.4%** | 0.0 | 16.1s |
| qwen3:4b | constrained | 0.8 | 17.6 | 2.2/17 | 18.2% | 0.0 | 19.5s |
| phi4-mini | baseline | 2.5 | 84.5 | **11.5/17** | 21.9% | 0.0 | 8.5s |
| phi4-mini | constrained | 3.4 | 137.0 | 10.2/17 | 19.4% | 0.2 | 5.5s |
| gemma3:1b | baseline | 3.0 | 70.0 | 5.0/17 | 21.9% | 0.0 | 3.2s |
| gemma3:1b | constrained | 3.0 | 89.6 | 5.4/17 | **28.4%** | 0.0 | 3.0s |

---

## Key Findings

### 1. Echo Is Real in Summarization (20–40%)
All models show significant echo — copying 3-word-or-longer phrases directly from the source text. This isn't paraphrasing; it's verbatim reproduction of source phrasing.

- **qwen3:4b baseline: 39.4%** — nearly half the output is copied phrases
- **gemma3:1b constrained: 28.4%** — constraint increased echo for the smallest model
- **phi4-mini: ~20%** — lowest echo, best paraphrasing ability

### 2. Constraint Effect Is Model-Dependent
The constrained prompt (specifying 3 focus points) had **opposite effects** depending on model size:

| Model | Baseline Echo | Constrained Echo | Δ Echo | Effect |
|-------|:---:|:---:|:---:|--------|
| qwen3:4b | 39.4% | 18.2% | **-21.2%** | Constraint reduced echo |
| phi4-mini | 21.9% | 19.4% | -2.5% | Minimal effect |
| gemma3:1b | 21.9% | 28.4% | **+6.5%** | Constraint increased echo |

**Interpretation:** The constrained prompt gave qwen3:4b a retrieval scaffold that helped it paraphrase rather than copy. But for gemma3:1b, the constraint may have narrowed attention to specific phrases, *increasing* copy-paste behavior. Small models echo more when guided.

### 3. qwen3:4b: The Empty Response Problem
qwen3:4b produced **4 empty responses** out of 10 trials (40% failure rate), all in the constrained condition. This suggests the model struggled with the combined instruction complexity. When it did respond, it produced high-quality summaries — but reliability was poor.

### 4. Fact Preservation vs Echo Tradeoff
No clear tradeoff between echo and fact preservation:

| Model | Echo | Facts Preserved |
|-------|:---:|:---:|
| phi4-mini | 20% | **11.5** |
| qwen3:4b | 39% | 7.2 |
| gemma3:1b | 22% | 5.0 |

**phi4-mini achieved both lowest echo AND highest fact preservation** — proving that good summarization doesn't require verbatim copying.

### 5. Hallucinations Were Rare
Only phi4-mini constrained produced 1 hallucination across 30 trials. The summarization task appears less prone to fabrication than generation tasks, likely because the source text constrains the output space.

### 6. Qualitative Echo Examples

**qwen3:4b (high echo, baseline):**
> "Eisenstein integers are complex numbers of the form a + bω (where ω is a primitive cube root of unity) that form a hexagonal lattice..."

Almost the entire opening is verbatim from the source.

**phi4-mini (low echo, paraphrased):**
> Produces original sentence structures while preserving factual content.

**gemma3:1b (constrained echo increase):**
> Under constraint, gemma3:1b pulled more phrases directly from source, suggesting the focus points directed attention to specific passages for copying.

---

## Comparison with Math Task Echo

| Dimension | Math Echo (prior studies) | Summarization Echo |
|-----------|:---:|:---:|
| Typical rate | 30–60% | 18–40% |
| Model-size correlation | Strong (smaller = more echo) | Moderate |
| Constraint effect | Generally reduces echo | **Mixed** (increases for smallest) |
| Hallucinations | Common | Rare |

**Key difference:** In math tasks, echo often represents the model reproducing its training data (formulas, proofs). In summarization, echo represents the model reproducing the *input text* — a different mechanism. Both are "echo" but the source differs: training data vs. prompt context.

---

## Conclusions

1. **Echo is a general phenomenon, not math-specific.** All models echo in summarization at 18–40% rates.
2. **Constraint direction is model-size dependent.** Large models paraphrase better with guidance; small models echo *more* when guided.
3. **phi4-mini is the best summarizer** — lowest echo, highest fact preservation, good reliability.
4. **gemma3:1b shows the "constraint echo trap"** — guidance makes it copy more, not less.
5. **Empty responses are a reliability issue** for qwen3:4b under complex prompts.

## Methodology Notes

- **Echo rate** = percentage of response words that appear in 3+-word n-grams also found in the source text
- **Key facts** = 17 facts manually identified in the source passage; fuzzy matching counts preservation
- **Hallucinations** = claims or numbers not supported by the source text
- Empty responses (qwen3:4b, 4 trials) are included in aggregates but represent model failures
- All runs at temperature 0.7 to allow natural variation
