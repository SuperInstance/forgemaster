# Study 38: Stage 4 Model Hunt — DeepInfra Full Scan

Date: 2026-05-15
Probes: 6 | Trials per probe: 3 | Temperature: 0.1

## Results Summary

| Model | Accuracy | Eisenstein | Stage |
|-------|----------|------------|-------|
| Hermes-3-Llama-3.1-405B | 83% (15/18) | 0% | Stage 3 (Resistant) |
| Hermes-3-Llama-3.1-70B | 67% (12/18) | 0% | Stage 2 (Partial) |
| Qwen3-235B-A22B-Instruct-2507 | 83% (15/18) | 0% | Stage 3 (Resistant) |
| Qwen3.6-35B-A3B | 0% (0/18) | 0% | Stage 1 (Vulnerable) |
| Seed-2.0-mini | 100% (18/18) | 100% | Stage 4 (Immune) |
| Seed-2.0-code | 100% (18/18) | 100% | Stage 4 (Immune) |
| Meta-Llama-3.1-70B-Instruct | 83% (15/18) | 0% | Stage 3 (Resistant) |
| Meta-Llama-3.1-8B-Instruct | 67% (12/18) | 0% | Stage 2 (Partial) |
| Mixtral-8x7B-Instruct-v0.1 | 78% (14/18) | 0% | Stage 3 (Resistant) |
| gemma-2-27b-it | 83% (15/18) | 0% | Stage 3 (Resistant) |
| Phi-3-medium-4k-instruct | 67% (12/18) | 0% | Stage 2 (Partial) |

## Stage Classification

- **Stage 4 (Immune)**: ≥90% accuracy — handles all arithmetic including Eisenstein
- **Stage 3 (Resistant)**: 70-89% — mostly correct, fails on some probes
- **Stage 2 (Partial)**: 50-69% — inconsistent
- **Stage 1 (Vulnerable)**: <50% — vocabulary wall or tokenization issues

## Stage 4 (Immune) Models

- **ByteDance/Seed-2.0-mini** — 100% overall, 100% Eisenstein
- **ByteDance/Seed-2.0-code** — 100% overall, 100% Eisenstein

## Stage 3 (Resistant) Models

- **NousResearch/Hermes-3-Llama-3.1-405B** — 83% overall, 0% Eisenstein
- **Qwen/Qwen3-235B-A22B-Instruct-2507** — 83% overall, 0% Eisenstein
- **meta-llama/Meta-Llama-3.1-70B-Instruct** — 83% overall, 0% Eisenstein
- **mistralai/Mixtral-8x7B-Instruct-v0.1** — 78% overall, 0% Eisenstein
- **google/gemma-2-27b-it** — 83% overall, 0% Eisenstein

## Detailed Probe Results

### NousResearch/Hermes-3-Llama-3.1-405B

| Probe | Expected | Trial 1 | Trial 2 | Trial 3 |
|-------|----------|---------|---------|---------|
| add_37_58 | 95 | 95 ✓ | 95 ✓ | 95 ✓ |
| mul_12_11 | 132 | 132 ✓ | 132 ✓ | 132 ✓ |
| eisenstein | 49 | 9 ✗ | 9 ✗ | 9 ✗ |
| sub_neg | 49 | 49 ✓ | 49 ✓ | 49 ✓ |
| mod_17_5 | 2 | 2 ✓ | 2 ✓ | 2 ✓ |
| sequence | 91 | 91 ✓ | 91 ✓ | 91 ✓ |

### NousResearch/Hermes-3-Llama-3.1-70B

| Probe | Expected | Trial 1 | Trial 2 | Trial 3 |
|-------|----------|---------|---------|---------|
| add_37_58 | 95 | 95 ✓ | 95 ✓ | 95 ✓ |
| mul_12_11 | 132 | 132 ✓ | 132 ✓ | 132 ✓ |
| eisenstein | 49 | 61 ✗ | 61 ✗ | 61 ✗ |
| sub_neg | 49 | 49 ✓ | 49 ✓ | 49 ✓ |
| mod_17_5 | 2 | 2 ✓ | 2 ✓ | 2 ✓ |
| sequence | 91 | 85 ✗ | 85 ✗ | 85 ✗ |

### Qwen/Qwen3-235B-A22B-Instruct-2507

| Probe | Expected | Trial 1 | Trial 2 | Trial 3 |
|-------|----------|---------|---------|---------|
| add_37_58 | 95 | 95 ✓ | 95 ✓ | 95 ✓ |
| mul_12_11 | 132 | 132 ✓ | 132 ✓ | 132 ✓ |
| eisenstein | 49 | 3 ✗ | 3 ✗ | 3 ✗ |
| sub_neg | 49 | 49 ✓ | 49 ✓ | 49 ✓ |
| mod_17_5 | 2 | 2 ✓ | 2 ✓ | 2 ✓ |
| sequence | 91 | 91 ✓ | 91 ✓ | 91 ✓ |

### Qwen/Qwen3.6-35B-A3B

| Probe | Expected | Trial 1 | Trial 2 | Trial 3 |
|-------|----------|---------|---------|---------|
| add_37_58 | 95 | None ✗ | None ✗ | None ✗ |
| mul_12_11 | 132 | None ✗ | None ✗ | None ✗ |
| eisenstein | 49 | None ✗ | None ✗ | None ✗ |
| sub_neg | 49 | None ✗ | None ✗ | None ✗ |
| mod_17_5 | 2 | None ✗ | None ✗ | None ✗ |
| sequence | 91 | None ✗ | None ✗ | None ✗ |

### ByteDance/Seed-2.0-mini

| Probe | Expected | Trial 1 | Trial 2 | Trial 3 |
|-------|----------|---------|---------|---------|
| add_37_58 | 95 | 95 ✓ | 95 ✓ | 95 ✓ |
| mul_12_11 | 132 | 132 ✓ | 132 ✓ | 132 ✓ |
| eisenstein | 49 | 49 ✓ | 49 ✓ | 49 ✓ |
| sub_neg | 49 | 49 ✓ | 49 ✓ | 49 ✓ |
| mod_17_5 | 2 | 2 ✓ | 2 ✓ | 2 ✓ |
| sequence | 91 | 91 ✓ | 91 ✓ | 91 ✓ |

### ByteDance/Seed-2.0-code

| Probe | Expected | Trial 1 | Trial 2 | Trial 3 |
|-------|----------|---------|---------|---------|
| add_37_58 | 95 | 95 ✓ | 95 ✓ | 95 ✓ |
| mul_12_11 | 132 | 132 ✓ | 132 ✓ | 132 ✓ |
| eisenstein | 49 | 49 ✓ | 49 ✓ | 49 ✓ |
| sub_neg | 49 | 49 ✓ | 49 ✓ | 49 ✓ |
| mod_17_5 | 2 | 2 ✓ | 2 ✓ | 2 ✓ |
| sequence | 91 | 91 ✓ | 91 ✓ | 91 ✓ |

### meta-llama/Meta-Llama-3.1-70B-Instruct

| Probe | Expected | Trial 1 | Trial 2 | Trial 3 |
|-------|----------|---------|---------|---------|
| add_37_58 | 95 | 95 ✓ | 95 ✓ | 95 ✓ |
| mul_12_11 | 132 | 132 ✓ | 132 ✓ | 132 ✓ |
| eisenstein | 49 | 2 ✗ | 2 ✗ | 2 ✗ |
| sub_neg | 49 | 49 ✓ | 49 ✓ | 49 ✓ |
| mod_17_5 | 2 | 2 ✓ | 2 ✓ | 2 ✓ |
| sequence | 91 | 91 ✓ | 91 ✓ | 91 ✓ |

### meta-llama/Meta-Llama-3.1-8B-Instruct

| Probe | Expected | Trial 1 | Trial 2 | Trial 3 |
|-------|----------|---------|---------|---------|
| add_37_58 | 95 | 95 ✓ | 95 ✓ | 95 ✓ |
| mul_12_11 | 132 | 132 ✓ | 132 ✓ | 132 ✓ |
| eisenstein | 49 | -3 ✗ | -3 ✗ | -3 ✗ |
| sub_neg | 49 | 40 ✗ | 40 ✗ | 40 ✗ |
| mod_17_5 | 2 | 2 ✓ | 2 ✓ | 2 ✓ |
| sequence | 91 | 91 ✓ | 91 ✓ | 91 ✓ |

### mistralai/Mixtral-8x7B-Instruct-v0.1

| Probe | Expected | Trial 1 | Trial 2 | Trial 3 |
|-------|----------|---------|---------|---------|
| add_37_58 | 95 | 95 ✓ | 95 ✓ | 95 ✓ |
| mul_12_11 | 132 | 132 ✓ | 132 ✓ | 132 ✓ |
| eisenstein | 49 | -3 ✗ | -3 ✗ | -3 ✗ |
| sub_neg | 49 | 49 ✓ | 49 ✓ | 49 ✓ |
| mod_17_5 | 2 | 2 ✓ | 2 ✓ | 2 ✓ |
| sequence | 91 | 89 ✗ | 91 ✓ | 91 ✓ |

### google/gemma-2-27b-it

| Probe | Expected | Trial 1 | Trial 2 | Trial 3 |
|-------|----------|---------|---------|---------|
| add_37_58 | 95 | 95 ✓ | 95 ✓ | 95 ✓ |
| mul_12_11 | 132 | 132 ✓ | 132 ✓ | 132 ✓ |
| eisenstein | 49 | 14 ✗ | 14 ✗ | 14 ✗ |
| sub_neg | 49 | 49 ✓ | 49 ✓ | 49 ✓ |
| mod_17_5 | 2 | 2 ✓ | 2 ✓ | 2 ✓ |
| sequence | 91 | 91 ✓ | 91 ✓ | 91 ✓ |

### microsoft/Phi-3-medium-4k-instruct

| Probe | Expected | Trial 1 | Trial 2 | Trial 3 |
|-------|----------|---------|---------|---------|
| add_37_58 | 95 | 95 ✓ | 95 ✓ | 95 ✓ |
| mul_12_11 | 132 | 132 ✓ | 132 ✓ | 132 ✓ |
| eisenstein | 49 | -3 ✗ | -3 ✗ | -3 ✗ |
| sub_neg | 49 | 40 ✗ | 40 ✗ | 40 ✗ |
| mod_17_5 | 2 | 2 ✓ | 2 ✓ | 2 ✓ |
| sequence | 91 | 91 ✓ | 91 ✓ | 91 ✓ |

## Eisenstein Norm Analysis

The Eisenstein norm probe (probe 3) is the hardest — requiring abstract math computation.

| Model | Eisenstein Accuracy | Notes |
|-------|---------------------|-------|
| Hermes-3-Llama-3.1-405B | 0% | 9, 9, 9 |
| Hermes-3-Llama-3.1-70B | 0% | 61, 61, 61 |
| Qwen3-235B-A22B-Instruct-2507 | 0% | 3, 3, 3 |
| Qwen3.6-35B-A3B | 0% | None, None, None |
| Seed-2.0-mini | 100% | 49, 49, 49 |
| Seed-2.0-code | 100% | 49, 49, 49 |
| Meta-Llama-3.1-70B-Instruct | 0% | 2, 2, 2 |
| Meta-Llama-3.1-8B-Instruct | 0% | -3, -3, -3 |
| Mixtral-8x7B-Instruct-v0.1 | 0% | -3, -3, -3 |
| gemma-2-27b-it | 0% | 14, 14, 14 |
| Phi-3-medium-4k-instruct | 0% | -3, -3, -3 |

## Conclusion

**2 Stage 4 model(s) found.** These are immune to the vocabulary wall and can handle abstract mathematical computation.