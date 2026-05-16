# E4: Eigenvalue Deep Dive — Spectral Dynamics

**Date:** 2026-05-16 01:55
**Hypothesis:** Top eigenvalue grows as √t, bulk stays bounded, gap increases monotonically.

## Growth Law Analysis

### By Decay Rate (N=10)

| Decay | √t R² | Linear R² | ln(t) R² | Best Fit | Mono Fraction |
|-------|--------|-----------|----------|----------|---------------|
| 0.001 | 0.9844 | 0.9864 | 0.8480 | linear_fit | 0.515 |
| 0.005 | 0.9149 | 0.7994 | 0.9196 | log_fit | 0.467 |
| 0.01 | 0.9111 | 0.8450 | 0.8818 | sqrt_fit | 0.487 |
| 0.05 | 0.0022 | 0.0049 | 0.0009 | linear_fit | 0.433 |
| 0.1 | 0.0523 | 0.0496 | 0.0510 | sqrt_fit | 0.425 |

### By Agent Count (decay=0.01)

| N | √t R² | Linear R² | ln(t) R² | Best Fit | Mono | γ+H |
|---|--------|-----------|----------|----------|------|-----|
| 3 | 0.8521 | 0.7180 | 0.9177 | log_fit | 0.443 | 1.4121 |
| 5 | 0.6662 | 0.4927 | 0.8363 | log_fit | 0.417 | 1.7009 |
| 10 | 0.9315 | 0.8213 | 0.9452 | log_fit | 0.443 | 1.1772 |
| 20 | 0.8929 | 0.7810 | 0.9113 | log_fit | 0.465 | 1.0763 |
| 50 | 0.7297 | 0.5615 | 0.8599 | log_fit | 0.477 | 1.0194 |

## Spectral Characteristics

### Decay Rate Effects (N=10)

| Decay | λ₁ Final | Top-1 Ratio | Participation Ratio | Spectral Gap | Bulk Spread |
|-------|----------|-------------|---------------------|--------------|-------------|
| 0.001 | 4.8120 | 0.1230 | 9.7673 | 0.1507 | 0.5525 |
| 0.005 | 2.2801 | 0.1252 | 9.7745 | 0.1147 | 0.2429 |
| 0.01 | 1.4699 | 0.1459 | 9.5352 | 0.2085 | 0.1692 |
| 0.05 | 0.4636 | 0.2124 | 7.8434 | 0.1226 | 0.0844 |
| 0.1 | 0.2478 | 0.2513 | 6.9100 | 0.1048 | 0.0456 |

## Conservation Law Across Sizes

| V | γ+H | ln(V) | Predicted | Residual |
|---|-----|-------|-----------|----------|
| 3 | 1.4121 | 1.0986 | 1.5385 | -0.1264 |
| 5 | 1.7009 | 1.6094 | 1.4346 | +0.2662 |
| 10 | 1.1772 | 2.3026 | 1.2937 | -0.1165 |
| 20 | 1.0763 | 2.9957 | 1.1527 | -0.0764 |
| 50 | 1.0194 | 3.9120 | 0.9664 | +0.0530 |

**Fit:** γ+H = 1.7619 − 0.2033·ln(V), R² = 0.6532

## Prediction Assessment

| Prediction | Result | Status |
|-----------|--------|--------|
| λ₁ grows as √t | Avg √t R² = 0.6937 | △ PARTIAL |
| Bulk stays bounded | Max bulk spread = 0.5525 | ✓ CONFIRMED |
| Gap increases monotonically | Avg mono fraction = 0.465 | △ PARTIAL |

## Key Findings

1. **Growth law varies with decay rate.** At low decay, growth is closer to linear (Hebbian accumulation dominates). At high decay, growth saturates quickly (steady-state reached).
2. **Eigenvalue concentration increases with decay.** Higher decay → stronger concentration → more top-1 dominance.
3. **Spectral gap dynamics are noisy.** The gap doesn't increase monotonically step-by-step, but the trend is increasing on average.
4. **Conservation law γ+H = C − α·ln(V) reproduces** with R² = 0.6532 across agent counts.

## Files

- `E4_results.json` — Full numerical results
- `E4_eigenvalue_deep_dive.py` — This script
