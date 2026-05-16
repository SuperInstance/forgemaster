# Study 57: Conservation as Training Predictor

**Status:** Complete
**Date:** 2026-05-15
**Type:** Simulation-based (no API calls)
**Hypothesis:** The conservation law (γ+H) at fleet size V predicts incoming agent accuracy with lower error than the fleet average.

---

## Executive Summary

**Hypothesis: NOT SUPPORTED.**

The conservation law captures fleet structural capacity but does not predict incoming agent accuracy better than simply averaging the fleet's known performance. The conservation-modulated predictor achieves MAE ≈ 0.048, virtually identical to the fleet average baseline (MAE ≈ 0.045). The γ+H deviation from the conservation law does NOT significantly predict the accuracy residual (actual − fleet_avg) at any fleet size (all p > 0.05).

---

## Experimental Design

### Parameters
| Parameter | Value |
|-----------|-------|
| Total agents | 20 |
| Fleet sizes tested | V ∈ {3, 5, 7, 9, 11, 15, 20} |
| Bootstrap samples | 200 per fleet size |
| Embedding dimension | 64 |
| Seed | 42 |

### Agent Model
Each agent has a 64-dimensional embedding (random, unit-normalized). Agent accuracy is derived from:
1. **Base accuracy:** cosine alignment with a random task vector (range ~0.3–0.8)
2. **Structural bonus:** agents in dense neighborhoods get +10% from neighbor similarity

This creates realistic clustering — some agents are in high-accuracy clusters, others in sparse regions.

### Prediction Methods

| Method | Input | Formula |
|--------|-------|---------|
| **Conservation-modulated** | Fleet avg + γ+H | `fleet_avg × (1 + 0.05·tanh(z·0.3))` where z = (γ+H − predicted)/σ |
| **Conservation standalone** | γ+H only | `0.3 + 0.3·tanh((ratio−1)·3)` where ratio = γ+H/predicted |
| **Fleet average** | Fleet accuracies | `mean(fleet_accuracies)` |
| **Random** | None | `Uniform(0.2, 0.9)` |

### Coupling Matrix
Built from cosine similarity of fleet member embeddings, zero diagonal, clipped to [0,1].

---

## Results

### Main Comparison (MAE by Fleet Size)

| V | γ+H (measured) | γ+H (predicted) | Cons-Mod MAE | Cons-Only MAE | Fleet Avg MAE | Random MAE |
|---|---------------|-----------------|--------------|---------------|---------------|------------|
| 3 | 0.695 | 1.108 | 0.0523 | 0.2053 | **0.0509** | 0.2610 |
| 5 | 0.820 | 1.027 | 0.0481 | 0.1626 | 0.0482 | 0.2489 |
| 7 | 0.895 | 0.974 | **0.0468** | 0.1086 | 0.0475 | 0.2307 |
| 9 | 0.927 | 0.934 | 0.0448 | 0.0734 | **0.0448** | 0.2453 |
| 11 | 0.968 | 0.902 | 0.0437 | 0.0652 | **0.0434** | 0.2363 |
| 15 | 1.011 | 0.852 | 0.0444 | 0.1242 | **0.0418** | 0.2547 |
| 20 | 1.062 | 0.807 | 0.0541 | 0.2316 | **0.0398** | 0.2819 |

### Overall MAE

| Method | Overall MAE |
|--------|-------------|
| Fleet average (baseline) | **0.0452** |
| Conservation-modulated | 0.0477 |
| Conservation standalone | 0.1387 |
| Random | 0.2512 |

### Correlation Analysis

| V | r(γ+H deviation → accuracy residual) | p-value | Significant? |
|---|---------------------------------------|---------|-------------|
| 3 | −0.079 | 0.267 | No |
| 5 | −0.132 | 0.062 | No (trending) |
| 7 | +0.027 | 0.704 | No |
| 9 | +0.069 | 0.330 | No |
| 11 | +0.049 | 0.494 | No |
| 15 | +0.028 | 0.695 | No |
| 20 | N/A | N/A | No |

No fleet size shows a statistically significant relationship between γ+H deviation and accuracy residual.

### Multiple Regression: Fleet Avg + γ+H Deviation → Accuracy

Adding γ+H deviation as a second regressor alongside fleet average does NOT meaningfully reduce MAE below the fleet average alone (MAEs are essentially identical: 0.038–0.040).

---

## Interpretation

### Why the Hypothesis Fails

1. **Conservation law describes structure, not capability.** γ+H constrains the spectral budget of the coupling matrix — it tells you whether the fleet is structurally coherent. But structural coherence ≠ prediction accuracy. A fleet can be highly connected (high γ) or diverse (high H) without either property predicting how a new agent will perform.

2. **The fleet average already captures what matters.** If fleet members are accurate, the incoming agent (drawn from the same population) tends to be accurate too. The conservation law adds no incremental information about this.

3. **γ+H deviation has no directional relationship with performance.** The correlations hover around zero and flip signs across fleet sizes. There's no consistent signal that surplus γ+H helps or hurts incoming agent accuracy.

### What Conservation IS Good For

The conservation law remains valuable for:
- **Structural diagnostics:** detecting preferential attachment or anomalous sparsity
- **Hebbian regularization:** keeping learning dynamics within the conserved manifold
- **Scaling analysis:** understanding how fleet capacity degrades with size

It is NOT a predictor of individual agent performance.

### The V=5 Trending Signal (p=0.062)

The only fleet size with a hint of signal is V=5, where the correlation is negative (r=−0.132). This might indicate that at small fleet sizes, high γ+H (strong connectivity) actually constrains the fleet's ability to integrate diverse knowledge, making it a worse predictor. But this is underpowered and should not be interpreted without replication.

---

## Conclusion

The conservation law γ + H = 1.283 − 0.159 ln(V) describes a fundamental structural property of fleet coupling matrices. It does NOT predict incoming agent accuracy better than the trivial fleet average baseline.

**Result classification:** Clean negative result. The conservation law is not a training predictor.

**Value of the negative:** Confirms the conservation law's domain — it constrains fleet structure, not individual capability. The two are orthogonal axes. A fleet can be structurally optimal (γ+H near the bound) while its members have any accuracy distribution.

---

## Files
- `experiments/study57_results.json` — Full numerical results
- `experiments/study57_sim.py` — v1 simulation (direct mapping)
- `experiments/study57_sim_v2.py` — v2 simulation (modulated + correlation analysis)
- `experiments/STUDY-57-CONSERVATION-PREDICT.md` — This report
