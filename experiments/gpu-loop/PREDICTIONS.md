# Testable Predictions — GPU Constraint Experiment Loop

**Date:** 2026-05-17
**Author:** Forgemaster ⚒️
**Status:** 10 falsifiable predictions derived from established theory
**Prerequisite:** These predictions follow from the causal chain: softmax → row-stochastic + positive → eigenvalues bounded [0,1] with spectral gap (Perron-Frobenius) → Tr(C²) bounded and smooth → γ+H conserved → substrate-invariant because precision enters at O(α²) ≈ 0.0025.

---

## Theory Summary

The established chain:

```
Softmax(QKᵀ/τ)
  → row-stochastic + strictly positive entries
    → Perron-Frobenius: λ₁=1 > |λ₂| > ... (spectral gap δ > 0)
      → Tr(C²) = Σλᵢ² bounded and smooth
        → Contraction dynamics: Tr(C²) conserved (CV≈0.002)
          → Two-moment constraint pins γ+H (CV≈0.004)
            → Substrate-invariant: precision noise enters at O(α²) ≈ 0.0025
```

Each prediction below tests a specific link in this chain. If the chain is correct, all predictions should hold. If any fails, the theory needs revision.

---

## Prediction 1: Temperature Monotonically Controls Tr(C²)

**Link tested:** Softmax temperature → eigenvalue spread → Tr(C²)

**Experiment:** Run fleet simulation with attention coupling, varying τ across {0.01, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0}. Measure Tr(C²) at steady state for each τ.

**Theory predicts:**
- Tr(C²) decreases monotonically with τ (approaching 1 as τ→∞)
- The relationship is smooth: Tr(C²) ≈ 1 + f(τ) where f is monotone decreasing
- γ+H CV should decrease as τ increases (higher τ → more uniform attention → more stable Tr(C²))
- At τ=10, Tr(C²) should be within 5% of 1.0 (near-uniform attention)
- At τ=0.01, Tr(C²) should approach N (near-one-hot attention)

**What falsifies it:** Tr(C²) is non-monotonic in τ, or γ+H CV does not decrease with increasing τ.

**Priority:** 1 — This is the most direct test of the softmax→Tr(C²) link. Simple to run, decisive result.

---

## Prediction 2: Row-Stochastic Normalization Fixes Hebbian Conservation

**Link tested:** Row-stochastic constraint → eigenvalue ceiling → Tr(C²) stability

**Experiment:** Modify Hebbian coupling to be row-stochastic: after computing C_ij = x_i · x_j, normalize each row: C_ij ← C_ij / Σ_k C_ik. Run fleet simulation and measure γ+H CV.

**Theory predicts:**
- Row-stochastic Hebbian should have Tr(C²) dramatically more stable than raw Hebbian
- γ+H CV should drop from ~0.12 to <0.02 (approaching attention performance)
- The improvement should be large: at least 5× reduction in CV
- However, it will NOT match attention perfectly because Hebbian can have zero entries (violating strict positivity → no guaranteed spectral gap)

**What falsifies it:** Row-stochastic Hebbian still has γ+H CV > 0.05, or the improvement is negligible (<2×).

**Priority:** 1 — Directly tests whether row-stochastic normalization is the key mechanism. If confirmed, it proves the eigenvalue ceiling is the primary driver.

---

## Prediction 3: Removing Positivity Breaks Conservation

**Link tested:** Strict positivity → Perron-Frobenius spectral gap → Tr(C²) stability

**Experiment:** Implement "hard attention" — replace softmax with a top-k mask (keep top k entries per row, set rest to 0), then normalize rows to sum to 1. Test k ∈ {1, 2, 3, ⌊N/2⌋, N}. This produces row-stochastic matrices with zero entries, violating strict positivity.

**Theory predicts:**
- As k decreases (more zeros), γ+H CV should increase
- k=1 (one-hot attention): Tr(C²) should be maximally unstable (permutation matrix, degenerate spectral gap)
- k=N (full softmax): baseline conservation (CV≈0.004)
- The relationship k vs CV should show a clear monotonic trend
- There should be a critical k* where conservation degrades sharply (spectral gap closure)

**What falsifies it:** Hard attention with k=2 or k=3 maintains the same CV as full softmax (CV≈0.004). This would mean positivity is not required — only row-stochastic normalization matters.

**Priority:** 1 — Tests the Perron-Frobenius link directly. Distinguishes whether row-stochasticity alone is sufficient, or whether strict positivity is also needed.

---

## Prediction 4: Spectral Gap Correlates with Conservation Quality

**Link tested:** Spectral gap δ = 1 - |λ₂| → Tr(C²) stability → γ+H stability

**Experiment:** For each architecture (attention, random, Hebbian, row-stochastic Hebbian, hard attention), compute the spectral gap δ of the coupling matrix. Also compute γ+H CV from fleet simulation. Correlate δ with CV.

**Theory predicts:**
- Strong negative correlation: larger δ → lower CV (better conservation)
- Attention should have the largest spectral gap among structured architectures
- Row-stochastic Hebbian should have a larger gap than raw Hebbian
- Random coupling should have moderate gap (eigenvalues spread in unit circle but not concentrated)
- The relationship should hold across ALL architectures, not just within one class

**What falsifies it:** No significant correlation between δ and γ+H CV, or the correlation is positive (larger gap → worse conservation).

**Priority:** 1 — This is the key quantitative prediction linking spectral structure to conservation. If it holds, the theory is on solid ground.

---

## Prediction 5: Two-Moment Regression Has R² > 0.95

**Link tested:** Tr(C) + Tr(C²) → γ+H (two-moment constraint)

**Experiment:** Across all fleet simulations (all architectures, all precisions, all N values), collect (Tr(C), Tr(C²), γ+H) tuples. Fit γ+H = a + b·Tr(C) + c·Tr(C²). Report R².

**Theory predicts:**
- R² > 0.95 for the combined regression
- The coefficient c (for Tr(C²)) should be much more important than b (for Tr(C)), since Tr(C) is trivially fixed by normalization
- Adding a third moment Tr(C³) should NOT significantly improve R² (incremental improvement < 0.01)
- The residuals should show no systematic pattern (random scatter)

**What falsifies it:** R² < 0.80, or adding Tr(C³) improves R² by > 0.05 (meaning higher moments matter).

**Priority:** 1 — The mathematical backbone of the entire theory. If two moments don't predict γ+H, the whole framework needs revision.

---

## Prediction 6: Precision Noise Scales as O(α²)

**Link tested:** Contraction dynamics → substrate-invariance → O(α²) noise floor

**Experiment:** Run fleet simulation across precisions {FP64, FP32, FP16, INT8, INT4, ternary, binary}. For each, measure the deviation of Tr(C²) from the FP64 baseline at steady state. The deviation should be:

δTr(C²) ≈ α² · ε(precision) · N

where ε is the quantization step size (ε_FP64 ≈ 2.2e-16, ε_FP32 ≈ 1.2e-7, ε_FP16 ≈ 9.8e-4, ε_INT8 ≈ 1/128, etc.)

**Theory predicts:**
- The deviation δTr(C²) should scale linearly with ε(precision)
- The proportionality constant should be approximately α² · N ≈ 0.0025 × 20 = 0.05
- At INT8 (ε ≈ 0.008): δTr(C²) ≈ 0.05 × 0.008 ≈ 0.0004
- At binary (ε ≈ 1): δTr(C²) ≈ 0.05 × 1 ≈ 0.05 (still small relative to Tr(C²) ≈ 20)
- Plotting δTr(C²) vs ε should give a straight line through the origin

**What falsifies it:** The deviation scales as O(α) or O(1) rather than O(α²), or the relationship with ε is non-linear.

**Priority:** 2 — Important for the substrate-invariance claim, but requires careful quantization implementation.

---

## Prediction 7: Concentration Ratio ρ Predicts Conservation Ranking

**Link tested:** ρ = [Tr(C)]² / [N · Tr(C²)] → concentrated distribution → tight γ+H bounds

**Experiment:** Compute ρ for each architecture in steady state. Rank architectures by ρ. Compare ranking to γ+H CV ranking.

**Theory predicts:**
- ρ_attention > ρ_random > ρ_hebbian
- ρ_attention > 0.95 (highly concentrated eigenvalue distribution)
- ρ_hebbian < 0.5 (degenerate, rank-1 dominated)
- The two rankings (ρ and CV quality) should be identical or near-identical
- There should be a threshold ρ* ≈ 0.8 above which conservation is good (CV < 0.01) and below which it degrades

**What falsifies it:** ρ ranking does not match CV ranking, or ρ_hebbian > ρ_random (inverted).

**Priority:** 2 — Tests the concentrated-distribution argument. If confirmed, it provides a single scalar diagnostic for conservation quality.

---

## Prediction 8: Contraction Rate Controls Relaxation Time

**Link tested:** C_{t+1} = (1-α)C_t + αW_t → exponential convergence → Tr(C²) fixed point

**Experiment:** Vary the mixing rate α across {0.01, 0.02, 0.05, 0.1, 0.2, 0.5}. For each α, measure:
1. Number of rounds until Tr(C²) reaches steady state (relaxation time)
2. Tr(C²) CV at steady state

**Theory predicts:**
- Relaxation time ≈ 1/(2α) (from (1-α)² convergence factor)
- At α=0.01: ~50 rounds to converge. At α=0.5: ~1 round.
- Steady-state Tr(C²) CV should be approximately proportional to α (larger α → more noise per step)
- Specifically: CV(Tr(C²)) ≈ α · ε/√(T) where T is the number of rounds after convergence
- There is a tradeoff: small α → slower convergence but tighter steady-state conservation

**What falsifies it:** Relaxation time does not scale as 1/(2α), or steady-state CV does not increase with α.

**Priority:** 2 — Tests the contraction mapping mechanism. Practical implication: we can tune α for desired convergence/accuracy tradeoff.

---

## Prediction 9: Nonlinear Activation Preserves Conservation If Structure Maintained

**Link tested:** Does the theory extend beyond linear dynamics?

**Experiment:** Replace linear state evolution x_{t+1} = Cx_t with nonlinear: x_{t+1} = tanh(Cx_t). Keep the coupling update C_{t+1} = (1-α)C_t + α·softmax(x·xᵀ). Measure γ+H CV.

**Theory predicts:**
- tanh should NOT break conservation if the coupling is still softmax-based
- The coupling matrix C remains row-stochastic and positive (softmax guarantees this)
- tanh affects the state vector but not the coupling matrix structure
- γ+H CV should remain < 0.01 (slightly worse than linear due to nonlinear state coupling)
- If the state dynamics diverge wildly (large norms), tanh saturation may degrade conservation — but only marginally

**What falsifies it:** γ+H CV > 0.05 with nonlinear dynamics, meaning conservation is an artifact of linear dynamics only.

**Priority:** 3 — Important for generalizing the theory beyond simple linear models, but not critical for the core theory.

---

## Prediction 10: Hybrid Architecture Achieves Both Structure and Conservation

**Link tested:** Engineering insight — can we build a coupling that has semantic structure AND conservation?

**Experiment:** Construct a "hybrid" coupling: C = β · softmax(structured_scores) + (1-β) · softmax(random_scores). Vary β ∈ {0, 0.2, 0.4, 0.6, 0.8, 1.0}. For each β, measure:
1. Semantic quality: how well does C capture meaningful relationships?
2. Conservation quality: γ+H CV
3. Spectral properties: ρ, δ, Tr(C²) stability

**Theory predicts:**
- Conservation should be excellent for ALL β values (softmax guarantees row-stochastic + positive regardless of input)
- γ+H CV < 0.01 for all β
- ρ should be > 0.9 for all β (softmax always produces concentrated distributions)
- The semantic structure should degrade smoothly with decreasing β
- This means we CAN have both conservation and structure — softmax is the universal solvent

**What falsifies it:** Intermediate β (e.g., 0.5) has significantly worse conservation than pure softmax (β=0 or β=1). This would mean mixing score types creates eigenvalue instability.

**Priority:** 3 — This is an engineering prediction, not a theoretical necessity. But if confirmed, it opens the door to practical fleet architectures that combine semantic grounding with conservation guarantees.

---

## Prediction Priority Summary

| # | Prediction | Priority | Effort | Decisive? |
|---|-----------|----------|--------|-----------|
| 1 | Temperature monotonically controls Tr(C²) | **1** | Low (parameter sweep) | Yes — direct test of softmax→Tr(C²) |
| 2 | Row-stochastic normalization fixes Hebbian | **1** | Low (one-line modification) | Yes — tests eigenvalue ceiling mechanism |
| 3 | Removing positivity breaks conservation | **1** | Low (top-k masking) | Yes — tests Perron-Frobenius requirement |
| 4 | Spectral gap correlates with conservation | **1** | Low (eigenvalue computation) | Yes — key quantitative link |
| 5 | Two-moment regression R² > 0.95 | **1** | Medium (data collection + regression) | Yes — mathematical backbone |
| 6 | Precision noise scales as O(α²) | 2 | Medium (precision sweep) | No — confirms substrate-invariance |
| 7 | Concentration ratio ρ predicts ranking | 2 | Low (scalar computation) | No — diagnostic, not causal |
| 8 | Contraction rate controls relaxation | 2 | Low (α sweep) | No — confirms mechanism |
| 9 | Nonlinear activation preserves conservation | 3 | Medium (new dynamics model) | Partial — generalization test |
| 10 | Hybrid architecture has both properties | 3 | Medium (new architecture) | No — engineering prediction |

### Recommended Run Order

**Batch 1 (30 min, decisive):** Predictions 1, 2, 3, 4 — these test the core causal chain. If all four hold, the theory is strongly confirmed. If any fails, we know which link to revise.

**Batch 2 (1 hour, confirmatory):** Predictions 5, 6, 7, 8 — these quantify the relationships and confirm the mathematical framework.

**Batch 3 (2 hours, exploratory):** Predictions 9, 10 — these test generalization and practical implications.

---

## Falsification Criteria Summary

The theory is **strongly falsified** if:
- Prediction 5 fails (two moments don't predict γ+H)
- Predictions 1 AND 2 both fail (neither temperature nor normalization matters)

The theory is **partially falsified** (needs revision) if:
- Prediction 3 fails but 2 holds (row-stochasticity is sufficient without positivity)
- Prediction 4 fails (spectral gap is not the right predictor)
- Prediction 6 fails (substrate-invariance has a different mechanism)

The theory is **confirmed** if:
- All Priority 1 predictions hold
- R² > 0.95 for the two-moment regression
- Spectral gap correlates r < -0.8 with conservation quality

---

*These predictions are specific, falsifiable, and derived directly from the established causal chain. Each has clear experimental protocol and unambiguous pass/fail criteria. Run Batch 1 first — the results will determine whether the theory is worth pursuing further.*
