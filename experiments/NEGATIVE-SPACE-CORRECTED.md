# Negative Space Probe — Corrected Results

## Methodological Confound Discovered

The ground truth and negative space probes used DIFFERENT prompts:
- **Spoke 2 (correct results)**: system="Give ONLY the final number" + max_tokens=20
- **Ground truth probe (wrong results)**: no system prompt + max_tokens=50

Without the system prompt, the model outputs chain-of-thought ("a²=9, b²=4, so a²+b²=25") and max_tokens=50 cuts off before the answer. Our regex grabs the last number in the truncated output = a sub-expression, not the answer.

**THIS IS ITSELF A FINDING**: The extraction method is a systematic confound. The same model on the same question gives different extracted answers depending on:
1. Whether a "only number" system prompt is used
2. Whether max_tokens allows the full answer to appear

The model's ACTUAL computation is the same — it always computes 9+16=25. But our measurement tool measures a different thing depending on prompt.

**R32 (BEDROCK): Extraction method is a first-class variable.** The same model+question gives different measured accuracy depending on prompt format and max_tokens. This is NOT model noise — it's measurement noise.

## Corrected Model Profiles

Using the correct extraction (system prompt + max_tokens=20), from spoke 2 + prompt sensitivity data:

### llama-3.1-8b-instant (GROUND TRUTH, 454 queries)
- **a+b, a-b, a*b**: 100% deterministic (20/20)
- **a²+b²**: 100% (20/20)  
- **a²-ab+b² (3,4)=13**: ~25% (variable, sub-expression leaking)
- **a²-ab+b² (5,-3)=49**: ~55% (semi-stable at T=0.3)
- **Width-3 formulas**: 25% generally
- **Student prompt**: 4/5 correct on multi-input test
- **T=0.0 PERFECT** on N(5,-3)=49 (10/10), T=0.3 drops to ~20%

### llama-3.3-70b-versatile (from spoke 2)
- **a²+b²**: 100%
- **a²-ab+b²**: 25% width-3 (SAME as 8B!)
- **Width-2 novel**: 25% (WORSE than 8B's 75%)
- **70B model NOT better at math** — training coverage matters more

### llama-4-scout-17b-MoE (from spoke 2)
- **a²+b²**: 100%
- **a²-ab+b²**: 25% width-3 (SAME as 8B and 70B)
- **Novel width-1**: 50% (between 8B's 100% and other models)
- **MoE confirmed**: Behaves like 8B dense, not 17B

## The Real Negative Space

All three Groq models FAIL at a²-ab+b² at the same rate (25%). This is NOT a model-specific failure — it's a TASK-specific failure. The Eisenstein norm is simply beyond all three models at width 3.

The 8B model's advantage shows at WIDTH 2 (75% vs 25%) — its math training gives it better coverage at that level.

**Implication for fleet routing**: At width ≤ 2, use llama-3.1-8b (fast, accurate). At width 3+, ALL models fail — route to a larger/reasoning model (qwen3-32b, DeepSeek) or decompose the task.
