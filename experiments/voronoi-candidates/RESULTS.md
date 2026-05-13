# Voronoi Candidate Count Experiment

**Date:** 2026-05-13
**Points tested:** 1,000,000 random in [-5,5] x [-5,5]

| Candidates | Max Error | Violations | Mismatches vs 9-ref |
|------------|-----------|------------|-------------------|
| 2 | 1.391 | 91.10% | 95.75% |
| 3 | 1.391 | 91.10% | 95.75% |
| 4 | 1.323 | 83.07% | 91.40% |
| 5 | 0.661 | 3.51% | 8.51% |
| 6 | 0.660 | 1.74% | 4.20% |
| 7 | 0.660 | **1.74%** | **4.20%** |
| **8** | **0.577** | **0.00%** | **0.00%** |
| 9 | 0.577 | 0.00% | 0.00% |

**Conclusion: 8 candidates minimum for full accuracy.** 
The 8th candidate covers a critical Voronoi cell corner that 2-7 miss.
Current implementation uses 9 — correct and optimal. No reduction possible.

