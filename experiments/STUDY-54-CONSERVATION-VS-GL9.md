# Study 54: Conservation Law vs GL(9) Alignment Correlation

**Date:** 2026-05-15
**Status:** Complete
**Priority:** P0

## Question

Do the conservation law (γ+H) and GL(9) alignment measure the same thing, or are they independent health signals?

## Hypothesis

They measure DIFFERENT things:
- **Conservation (γ+H):** Structural balance — no room dominates the Hebbian weight matrix
- **GL(9) alignment:** Behavioral alignment — agents agree on intent vectors across 9 CI facets

Expected: LOW correlation between the two.

## Phase A: Correlation Measurement

**Samples:** 100 random fleet states (5-20 rooms, varying distributions)

### Pearson Correlation

| Metric Pair | r |
|---|---|
| Conservation compliance ↔ GL(9) alignment | **-0.1789** |
| Gamma (algebraic) ↔ GL(9) alignment | 0.1722 |
| Coupling entropy ↔ GL(9) alignment | 0.0157 |

### Spearman ρ (rank correlation)

ρ = -0.1465

### Distribution

- Conservation compliance: mean=0.3620, std=0.3519
- GL(9) alignment: mean=0.1446, std=0.0604

### Verdict: INDEPENDENT — keep both as separate signals

## Phase B: Stress Testing

### B1: Agents aligned + one room dominating
- Conservation broken: True
- GL(9) alignment: 0.9827
- **Result:** Conservation BREAKS, GL(9) HOLDS ✓

### B2: Perfect conservation + agents disagree
- Conservation deviation: 0.1159
- GL(9) alignment: 0.0016
- **Result:** Conservation HOLDS, GL(9) BREAKS ✓

### B3: Both broken (dominant + disagreeing)
- Conservation broken: True
- GL(9) alignment: 0.0025

### B4: Both healthy (balanced + aligned)
- Conservation deviation: 0.2016
- GL(9) alignment: 0.9970

### Independent failure modes confirmed: True

## Phase C: Combined Predictive Power

Linear model: health = a × conservation + b × alignment + c

| Model | R² |
|---|---|
| Conservation only | 0.8235 |
| GL(9) alignment only | 0.0291 |
| **Combined** | **0.8463** |

### Coefficients
- Conservation weight: 0.4134
- Alignment weight: 0.2911
- Intercept: 0.1580

### Improvement over best single model: +0.0228 R²

## Final Recommendation

### **KEEP SEPARATE**

Low correlation (r=-0.179) + independent failure modes confirmed. Conservation and GL(9) measure fundamentally different aspects of fleet health. Combined model has better predictive power (higher R²).

### Summary

| Evidence | Result |
|---|---|
| Correlation (r) | -0.1789 |
| Independent failure modes | True |
| Combined R² improvement | +0.0228 |

### What Each Signal Measures

| Signal | Measures | Failure Mode |
|---|---|---|
| **Conservation (γ+H)** | Structural balance of Hebbian weights | One room dominates flow |
| **GL(9) alignment** | Behavioral agreement on intent | Agents pursue conflicting goals |

Both signals are orthogonal health dimensions. The fleet needs BOTH for complete health monitoring.
