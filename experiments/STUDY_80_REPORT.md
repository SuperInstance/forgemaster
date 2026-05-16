# Study 80: Live Conservation Verification on Mixed Fleet
Date: 2026-05-16 03:34

## Hypothesis
Conservation of γ + H holds even across heterogeneous models (different architectures, sizes, training data).

## Fleet Composition

- GLM-5-Turbo
- Seed-2.0-Mini
- Qwen3-0.6B
- Gemma3-1B
- Llama3.2-1B

## Results by Round

### Round 1
- γ (Fiedler value): 0.2153
- H (Coupling entropy): 3.6217
- γ + H: 3.8370

### Round 2
- γ (Fiedler value): 0.1876
- H (Coupling entropy): 3.6346
- γ + H: 3.8222

### Round 3
- γ (Fiedler value): 0.0935
- H (Coupling entropy): 3.4190
- γ + H: 3.5125

## Coupling Matrices

### Round 1

| | GLM | Seed | Qwen3 | Gemma3 | Llama3.2 |
|---|---|---|---|---|---|
| GLM | 1.000 | 0.560 | 0.115 | 0.078 | 0.089 |
| Seed | 0.560 | 1.000 | 0.069 | 0.102 | 0.052 |
| Qwen3 | 0.115 | 0.069 | 1.000 | 0.007 | 0.089 |
| Gemma3 | 0.078 | 0.102 | 0.007 | 1.000 | 0.022 |
| Llama3.2 | 0.089 | 0.052 | 0.089 | 0.022 | 1.000 |

### Round 2

| | GLM | Seed | Qwen3 | Gemma3 | Llama3.2 |
|---|---|---|---|---|---|
| GLM | 1.000 | 0.575 | 0.183 | 0.086 | 0.060 |
| Seed | 0.575 | 1.000 | 0.160 | 0.095 | 0.034 |
| Qwen3 | 0.183 | 0.160 | 1.000 | 0.006 | 0.043 |
| Gemma3 | 0.086 | 0.095 | 0.006 | 1.000 | 0.020 |
| Llama3.2 | 0.060 | 0.034 | 0.043 | 0.020 | 1.000 |

### Round 3

| | GLM | Seed | Qwen3 | Gemma3 | Llama3.2 |
|---|---|---|---|---|---|
| GLM | 1.000 | 0.509 | 0.013 | 0.100 | 0.073 |
| Seed | 0.509 | 1.000 | 0.012 | 0.095 | 0.050 |
| Qwen3 | 0.013 | 0.012 | 1.000 | 0.007 | 0.051 |
| Gemma3 | 0.100 | 0.095 | 0.007 | 1.000 | 0.022 |
| Llama3.2 | 0.073 | 0.050 | 0.051 | 0.022 | 1.000 |

## Conservation Analysis

| Round | γ + H |
|-------|-------|
| Round 1 | 3.8370 |
| Round 2 | 3.8222 |
| Round 3 | 3.5125 |

**Mean γ + H: 3.7239**
**Std Dev: 0.1496**
**Coefficient of Variation: 0.0402 (4.0%)**
**Conserved? YES ✓** (threshold: CV < 15%)

## Conclusions

1. γ + H is conserved across rounds with mixed models
2. The Fiedler value γ measures fleet coherence — higher = more agreement
3. Entropy H measures coupling diversity — reflects heterogeneity
4. The trade-off γ + H = const would indicate a fundamental conservation law
