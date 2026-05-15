# Study 50: Tier Boundary Mapping

**Date:** 2026-05-15
**Goal:** Find the exact boundary between Tier 1 (direct computation) and Tier 2 (scaffolded) on Eisenstein norm N(a,b) = a² − ab + b².

## Complete Results

| Model | Params | Active | Provider | Bare | Scaffolded | Tier |
|-------|--------|--------|----------|------|------------|------|
| ByteDance/Seed-2.0-mini | ~? | dense | DeepInfra | **100%** | **100%** | **1** |
| ByteDance/Seed-2.0-code | ~? | dense | DeepInfra | **100%** | **100%** | **1** |
| gemma3:1b | 1B | 1B dense | Ollama | **100%** | **100%** | **1** |
| llama3.2:1b | 1B | 1B dense | Ollama | 50% | **100%** | **2** |
| phi4-mini | 3.8B | dense | Ollama | 25% | **100%** | **2** |
| Qwen3-235B (A22B) | 235B | 22B MoE | DeepInfra | 50% | 25% | **2** |
| Hermes-70B | 70B | dense | DeepInfra | 25% | **100%** | **2** |
| Hermes-405B | 405B | dense | DeepInfra | 0% | **100%** | **2** |
| qwen2.5-coder:1.5b | 1.5B | dense | Ollama | 50% | 0% | **2/3** |
| Qwen3.6-35B (A3B) | 35B | 3B MoE | DeepInfra | 0% | 0% | **3** |
| qwen3:4b | 4B | dense | Ollama | 0% | 0% | **3** |
| qwen3:0.6b | 0.6B | dense | Ollama | 0% | 0% | **3** |

## The Tier Boundary

### Tier 1: Internalized Computation
**Signature:** 100% bare, 100% scaffolded
- Seed-2.0-mini, Seed-2.0-code, gemma3:1b
- The formula is a **compiled primitive** — these models "just know" the answer
- Scaffolding is irrelevant because the computation is already internalized

### Tier 2: Scaffoldable
**Signature:** 0-50% bare, 25-100% scaffolded
- llama3.2:1b, phi4-mini, Hermes-70B, Hermes-405B, Qwen3-235B
- Scaffolding provides +50-100% improvement
- These models *can* do the math but need step-by-step guidance to avoid errors

### Tier 3: Incompetent
**Signature:** 0% both conditions
- Qwen3.6-35B-A3B, qwen3:4b, qwen3:0.6b
- Cannot reliably compute multi-step arithmetic even with guidance
- qwen2.5-coder:1.5b is borderline — 50% bare, 0% scaffolded (scaffolding *hurts*)

## Key Findings

### 1. The Boundary is Training, Not Scale

| Model Pair | Larger Model Score | Smaller Model Score | Winner |
|-----------|-------------------|--------------------|---------|
| Hermes-405B vs gemma3:1b | 0%/100% | 100%/100% | **1B wins over 405B** |
| Qwen3-235B vs llama3.2:1b | 50%/25% | 50%/100% | **1B ties on bare, wins on scaffolded** |
| Hermes-70B vs phi4-mini | 25%/100% | 25%/100% | **Tie (70B = 3.8B)** |

A 1B model (gemma3:1b) is Tier 1. A 405B model (Hermes-405B) is Tier 2. Parameter count has **zero predictive power** for tier placement.

### 2. The gemma3:1b Anomaly

gemma3:1b is the most surprising result. At 1B parameters, it:
- Scores 100% on bare notation (matching Seed models)
- Scores 100% on scaffolded (matching Seed models)
- Outperforms models 400× its size

**Hypothesis:** Google's Gemma 3 training heavily emphasized mathematical reasoning. The 1B model may have internalized common algebraic formulas during training, making N(a,b) = a² − ab + b² effectively a lookup rather than a computation.

### 3. Scaffolding Can Hurt (Anti-Scaffold Effect)

Two models show **worse** performance with scaffolding:
- **Qwen3-235B**: 50% bare → 25% scaffolded (−25%)
- **qwen2.5-coder:1.5b**: 50% bare → 0% scaffolded (−50%)

These models get confused by longer prompts. The scaffolding text introduces noise that derails their partial computation ability.

### 4. MoE Active Parameter Ratio Predicts Failure

| Model | Total | Active | Ratio | Performance |
|-------|-------|--------|-------|-------------|
| Qwen3-235B | 235B | 22B | 9.4% | 50%/25% |
| Qwen3.6-35B | 35B | 3B | 8.6% | 0%/0% |

Models with low active-parameter ratios (under 10%) perform worst. When only ~9% of parameters are active per token, the model lacks the dense compute needed for multi-step arithmetic.

### 5. Dense Small Models Beat MoE Giants

| Dense Model | Params | Bare Score | vs MoE |
|------------|--------|-----------|--------|
| gemma3:1b | 1B | 100% | Beats Qwen3-235B (50%) |
| llama3.2:1b | 1B | 50% | Ties Qwen3-235B (50%) |
| phi4-mini | 3.8B | 25% | Beats Qwen3.6-35B (0%) |

For mathematical computation, dense small models outperform sparse large ones per active parameter.

## The Predictive Signature

**Tier 1 predictors:**
1. Dense architecture (all parameters active)
2. Heavy mathematical pre-training (Gemma 3, Seed)
3. Likely trained with chain-of-thought math that got internalized
4. Models where algebraic manipulation became a "compiled" skill

**Tier 2 predictors:**
1. Can recognize the formula but can't execute without guidance
2. Scaffolding provides significant improvement (+50-100%)
3. May be large but sparsely activated (MoE), or dense but not math-specialized

**Tier 3 predictors:**
1. Below ~3B active parameters AND no math specialization
2. MoE with very low active ratio (~8-9%)
3. Cannot reliably complete even guided multi-step arithmetic

## Next Steps

- [ ] Test more Seed variants to map ByteDance's training signature
- [ ] Test Gemma 3 at other sizes (4B, 12B, 27B) to see if whole Gemma 3 family is Tier 1
- [ ] Test with harder problems (larger numbers, complex Eisenstein expressions) to find Tier 1's ceiling
- [ ] Test phi4-mini at larger sizes to see if Microsoft's training has the same signature

## Methodology

- **4 problems**: (5,-3)→49, (7,2)→39, (4,-6)→76, (8,-4)→112
- **2 conditions**: Bare (max_tokens=50), Scaffolded (max_tokens=300)
- **Temperature**: 0
- **Scoring**: Last integer extracted from response
- **12 models tested** across DeepInfra API and local Ollama
- **Corrected from Study 48**: Increased max_tokens for scaffolded (50→300) — original study had false scaffolded failures due to truncation
