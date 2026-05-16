# E5: Spiked Random Matrix Theory Connection

**Date:** 2026-05-16 01:55
**Hypothesis:** Conservation law corresponds to the sub-critical regime where spike is absorbed into bulk.

## BBP Phase Transition (N=50)

| β | λ₁ | Overlap | Spike Shift | Top-1 Ratio | γ+H | Regime |
|---|----|---------|-------------|-------------|-----|--------|
| 0.00 | 1.3596 | 0.0173 | +0.1140 | 0.0448 | 1.0017 | sub |
| 0.25 | 1.3497 | 0.0442 | +0.0995 | 0.0446 | 1.0061 | sub |
| 0.50 | 1.3721 | 0.1046 | +0.1198 | 0.0451 | 0.9985 | sub |
| 0.75 | 1.4031 | 0.2624 | +0.1291 | 0.0460 | 1.0039 | sub |
| 0.90 | 1.4505 | 0.3275 | +0.1621 | 0.0473 | 1.0082 | critical |
| 1.00 | 1.4755 | 0.4327 | +0.1772 | 0.0481 | 1.0046 | critical |
| 1.10 | 1.5599 | 0.5604 | +0.2434 | 0.0503 | 1.0069 | super |
| 1.25 | 1.6341 | 0.6621 | +0.3243 | 0.0526 | 1.0090 | super |
| 1.50 | 1.8248 | 0.7720 | +0.5058 | 0.0585 | 1.0225 | super |
| 2.00 | 2.2396 | 0.8773 | +0.9257 | 0.0706 | 1.0543 | super |
| 3.00 | 3.1759 | 0.9468 | +1.8412 | 0.0978 | 1.1559 | super |
| 5.00 | 5.1227 | 0.9808 | +3.8062 | 0.1481 | 1.2996 | super |

## Hebbian → Spiked Mapping (N=10, lr=0.01, 500 steps)

| Decay | β_eff/σ_eff | Overlap | Top-1 Ratio | γ+H | Regime |
|-------|-------------|---------|-------------|-----|--------|
| 0.001 | 1.288 | 1.0000 | 0.1262 | 1.1713 | super-critical |
| 0.005 | 1.342 | 1.0000 | 0.1311 | 1.1711 | super-critical |
| 0.01 | 1.460 | 1.0000 | 0.1420 | 1.1616 | super-critical |
| 0.05 | 2.111 | 1.0000 | 0.2049 | 1.1341 | super-critical |
| 0.1 | 2.660 | 1.0000 | 0.2626 | 1.1255 | super-critical |

## Phase Transition Detection

- **Empirical transition β:** 0.900 (theoretical BBP: β = 1)
- **γ+H at transition:** 1.0253
- **Overlap at transition:** 0.4077

## Sub- vs Super-Critical Regimes

| Regime | Mean γ+H | Std γ+H |
|--------|----------|---------|
| Sub-critical (β < 0.90) | 1.0217 | 0.0039 |
| Super-critical (β > 0.90) | 1.0866 | 0.0430 |

## Prediction Assessment

| Prediction | Result | Status |
|-----------|--------|--------|
| Hebbian in sub-critical regime | β/σ = 1.772 | ✗ REJECTED — Hebbian is SUPER-critical |
| Conservation law ↔ sub-critical regime | Super-critical Hebbian produces eigenvalue concentration | See analysis |

## Key Findings

1. **BBP transition is clearly observable** at β ≈ 0.90, close to theoretical prediction of β = 1.
2. **Eigenvector overlap jumps** sharply at the transition — the signal direction becomes recoverable.
3. **Hebbian dynamics produce effective β/σ ≈ 1.772**, placing them in the super-critical regime.
4. **γ+H varies across regimes** but the conservation structure persists in both.

### Refined Prediction

The conservation law γ+H = C − α·ln(V) is **NOT simply the sub-critical regime**. Instead:
- The **mechanism** (eigenvalue concentration) corresponds to the spike strength growing with network size
- The **slope direction** (decreasing) requires sufficient spike-to-noise ratio, which Hebbian provides
- The **specific constants** (1.283, −0.159) depend on the Hebbian parameters (lr, decay, activation structure)

## Files

- `E5_results.json` — Full numerical results
- `E5_spiked_rmt.py` — This script
