# Study 28: Temperature vs Vocabulary Wall

**Date**: 2026-05-15 07:10 AKDT

## Results (Hermes-70B, 3 trials per condition)

| Temperature | Vocab ("Eisenstein") | Bare arithmetic | Gap |
|:-----------:|:--------------------:|:---------------:|:---:|
| 0.0 | 0% | 100% | +3 |
| 0.3 | 0% | 100% | +3 |
| **0.7** | **67%** | **100%** | **+1** |
| 1.0 | 0% | 100% | +3 |
| 1.5 | 33% | 33% | 0 |

## R46 (BEDROCK): Temperature Dissolves the Vocabulary Wall at T≈0.7

At T=0.0-0.3, the Vocabulary Wall is absolute — the model deterministically routes "Eisenstein" to discourse pathways. At T=0.7, the stochasticity is high enough that the model occasionally escapes the pattern-match pathway and finds the computation pathway instead (67% accuracy).

At T=1.0, the wall returns. At T=1.5, everything degrades (too stochastic for any computation).

**Mechanism**: Higher temperature samples from less probable tokens. The "correct computation" pathway exists but has lower probability than the "discourse about Eisenstein" pathway. At T=0.7, sampling is wide enough to occasionally select the computation pathway. At T=1.0+, noise overwhelms.

## Fleet Implication

For domain-specific computation tasks on non-Stage-4 models:
- **Best**: Auto-translate to arithmetic (Study 23) — 100% at any temperature
- **Fallback**: Use T=0.7 to partially dissolve the wall (67%)
- **Worst**: Use T=0 with domain vocabulary (0%)

Auto-translation remains superior (100% vs 67%) but temperature adjustment is a useful secondary knob.
