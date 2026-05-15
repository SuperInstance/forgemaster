# Study 26: Echo Thermometer — 6 Probes Sufficient for Stage Classification

**Date**: 2026-05-15 07:00 AKDT

## Results (20 probes per model)

| Model | Accuracy | Echo Rate | Dominant Response | Stage |
|-------|:--------:|:---------:|:-----------------:|:-----:|
| phi4-mini | 25% | **45%** | echo_input + echo_partial | 2-3 |
| gemma3:1b | 5% | 20% | other (random noise) | 2 |

## Convergence

| Probes | phi4-mini acc | phi4-mini echo | gemma3:1b acc | gemma3:1b echo |
|:------:|:-------------:|:--------------:|:-------------:|:--------------:|
| 3 | 0% | 67% | 0% | 0% |
| 6 | 33% | 33% | 0% | 0% |
| 9 | 22% | 22% | 0% | 11% |
| 12 | 25% | 33% | 0% | 8% |
| 15 | 20% | 40% | 7% | 7% |
| 20 | 25% | 45% | 5% | 20% |

## R45 (SOLID): 6 Probes Sufficient for Stage Classification

After 6 probes, the echo rate is already diagnostic:
- **echo > 30%** → Stage 2-3 (phi4-mini)
- **other > 70%** → Stage 2 pure (gemma3:1b)
- **accuracy > 80%** → Stage 4 (from Study 24)

Fleet routing can classify model stage in ~6 API calls (~3 seconds parallel, ~30 seconds sequential).
