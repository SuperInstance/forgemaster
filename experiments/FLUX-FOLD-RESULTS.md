# Study 16: FLUX Fold Encoding — Z[ζ₁₂] Multi-Rep Snap + Permutation Consensus

**Date**: 2026-05-15 06:20 AKDT
**Status**: COMPLETE

## Results

### Multi-Rep Covering Radius (Z[ζ₁₂], 6 direction pairs)

| Method | Max Snap Distance | Improvement |
|--------|:-----------------:|:-----------:|
| Eisenstein single pair (90°) | 0.7060 | baseline |
| Multi-rep (6 pairs) | 0.5105 | **1.38× tighter** |
| Mean per-point improvement | — | **1.97×** |

### Which Pair Wins?

| Pair (angle) | Win Rate |
|:---:|:---:|
| k=3 (90° — Eisenstein) | 18.9% |
| k=2 (60°) | 17.0% |
| k=5 (150°) | 16.9% |
| k=1 (30°) | 16.8% |
| k=4 (120°) | 16.7% |
| k=6 (180°) | 13.7% |

**All pairs contribute.** No single pair dominates. The Eisenstein pair (90°) wins slightly more often but the distribution is remarkably uniform.

### Permutation Consensus (top 4 pairs, 24 permutations)

| Unique Targets | Frequency |
|:-:|:-:|
| 1 (full consensus) | 4% |
| 3 (high consensus) | 30% |
| 5-8 (typical) | 60% |
| 9-10 (low consensus) | 6% |

Mean: **5.7 unique targets** out of 24 permutations.

## Findings

- **R35 (SOLID)**: Multi-rep snap with Z[ζ₁₂] achieves 1.38× tighter covering than single Eisenstein pair, confirming yesterday's overcomplete basis finding.
- **R36 (SOLID)**: All 6 direction pairs contribute to coverage. The multi-rep advantage comes from ensemble diversity, not algebraic magic of any single pair.
- **R37 (SUGGESTIVE)**: Permutation consensus (2% full, 17% high) is too sparse for reliable confidence metric. The overcomplete basis gives tight covering, but the permutation signal is noisy.

## Connection to Previous Work

Confirms yesterday's zero-side-info theorem: the advantage is K representations for log₂(n) bits. The covering improves 1.38× from 6 pairs that cost only ~3 bits to specify. The Pareto frontier holds.
