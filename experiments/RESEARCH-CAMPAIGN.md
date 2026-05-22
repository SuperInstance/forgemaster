# Research Campaign: Constraining the Unknown

**SuperInstance Fleet · Constraint-Theoretic Metronome Architecture**
**Date:** 2026-05-22
**Status:** Active research campaign — hypothesis-driven experimentation

---

## What We Know (PROVEN)

| # | Claim | Evidence | Status |
|---|-------|----------|--------|
| 1 | Laman rigidity: 2N-3 is exact threshold | Exp 1,9,10: N=3..100, edge removal always breaks rigidity | ✅ PROVEN |
| 2 | Zero drift: Fraction arithmetic gives exact zero accumulation | Exp 6: 10,000 ops, zero error | ✅ PROVEN |
| 3 | Partition recovery: O(log N) after healing | Exp 9: 13 ticks for N=10 | ✅ PROVEN |
| 4 | Fleet scaling: convergence is 7.23·log₂N | Exp 10: N=3..100, R²=0.98 | ✅ PROVEN |
| 5 | Deadband sparsity: 99.44% sub-threshold in converged fleet | Exp 3: Corrected theorem (not I(X;Y)=0) | ✅ PROVEN |
| 6 | BFT: N≥3f+1 with reputation+trimmed mean | Exp 11,16: f≤3 converges | ✅ PROVEN |
| 7 | Byzantine filter: reputation+trimmed is near-optimal | Exp 16: fastest convergence among 6 filters | ✅ PROVEN |

## What We DON'T Know (GAPS → EXPERIMENTS)

### Gap 1: Spectral Coupling Deviation
**Unknown:** Why does theory predict α*=2/(λ₂+λₙ) but experiments show 1.076× deviation?
- Exp 12: **Spectral Coupling Deviation Source** — sweep deadband δ, isolate the source
- Hypothesis: deviation comes from deadband nonlinearity, not topology
- If confirmed → deadband-aware spectral theorem needed
- If refuted → look at small-world augmentation or Fraction discretization

### Gap 2: Optimal Deadband Threshold
**Unknown:** Is δ=1/16 optimal? Is there a closed-form for optimal δ(N, σ)?
- Exp 13: **Optimal δ Sweep** — sweep δ from 1/256 to 1/4, find the Pareto frontier
- Hypothesis: optimal δ balances sparsity vs convergence, derivable from σ and N
- If confirmed → δ becomes a function, not a parameter
- If refuted → δ is truly application-dependent, no universal optimum

### Gap 3: Heterogeneous Clock Tolerance
**Unknown:** How much clock rate heterogeneity can the metronome tolerate?
- Exp 14: **Heterogeneous Clock Rates** — one agent at 2×, 5×, 10×, 20× speed
- Hypothesis: system tolerates up to 10× before significant degradation
- If confirmed → metronome works across heterogeneous hardware
- If refuted → need rate-adaptive coupling

### Gap 4: Memoir Compression Bound
**Unknown:** What is the true compression bound for agent memoirs?
- Exp 15: **Memoir Compression** — DONE ✅
- **RESULT: O(log T) REFUTED. True bound appears to be O(√T).**
- SVD achieves O(log T) in state space dimension but O(√T) needed for prediction
- Need: revised sunset compression theorem

### Gap 5: BFT Filter Optimality
**Unknown:** Is reputation+trimmed mean optimal? Can we do better?
- Exp 16: **BFT Filter Comparison** — DONE ✅
- **RESULT: Near-optimal for speed. Hybrid (reputation → trimmed fallback) could be optimal.**
- Topology-aware filtering adds no value in Laman graphs (all neighbors are direct)
- Need: hybrid filter implementation

### Gap 6: Topology Augmentation Effects
**Unknown:** What happens when edges are ADDED to Laman? Is there a sweet spot?
- Exp 17: **Edge Augmentation** — add 0%, 10%, 20%, 50%, 100% extra edges to Laman base
- Hypothesis: diminishing returns after 20% augmentation
- If confirmed → small-world augmentation is well-calibrated
- If refuted → Laman alone may be sufficient, extra edges are waste

### Gap 7: Drift Dynamics Under Load
**Unknown:** How does drift behave under high constraint-checking load?
- Exp 18: **Load-Drift Coupling** — vary constraint checking frequency (1, 10, 100, 1000 per tick)
- Hypothesis: drift is independent of constraint load (metronome and constraint checker are decoupled)
- If confirmed → architecture scales independently
- If refuted → need resource-aware scheduling

### Gap 8: Multi-Generation Sunset Dynamics
**Unknown:** How does calibration quality degrade across multiple generations?
- Exp 19: **Multi-Generation Inheritance** — 5 generations of sunset/inheritance, measure drift per generation
- Hypothesis: drift grows linearly with generation count (each handoff loses some calibration)
- If confirmed → need periodic re-calibration protocol
- If refuted → if drift stays bounded, inheritance is self-correcting

### Gap 9: δ-Network Latency Interaction
**Unknown:** How does δ interact with network latency? Is there a δ that compensates for latency?
- Exp 20: **Latency-δ Tradeoff** — vary latency (0, 10ms, 50ms, 100ms) and δ simultaneously
- Hypothesis: optimal δ scales linearly with latency (δ_opt = k × latency)
- If confirmed → self-tuning δ based on network conditions
- If refuted → δ and latency are independent concerns

### Gap 10: Emergence Detection Threshold
**Unknown:** Can the fleet detect emergent behaviors (oscillation, resonance, cascade) before they cause drift violations?
- Exp 21: **Emergence Early Warning** — inject oscillatory drift into one agent, measure detection time
- Hypothesis: drift velocity (second derivative) detects emergence 10+ ticks before violation
- If confirmed → predictive emergence detection is possible
- If refuted → can only detect violations after they occur

### Gap 11: Tensor-MIDI Compression in Practice
**Unknown:** Does INT8 Tensor-MIDI preserve enough information for real fleet coordination?
- Exp 22: **Tensor-MIDI Fidelity** — compare fleet performance with float64 vs INT8 Tensor-MIDI
- Hypothesis: INT8 produces <1% additional drift vs float64 for δ≥1/64
- If confirmed → INT8 is safe for production
- If refuted → need INT16 or adaptive quantization

### Gap 12: Minimum Fleet Size for BFT
**Unknown:** What is the minimum N that achieves BFT with our filters?
- Exp 23: **Minimum BFT Fleet** — sweep N from 4 to 20 with f=1,2,3
- Hypothesis: N=3f+1 is tight (N=4 works for f=1, N=7 for f=2, N=10 for f=3)
- If confirmed → BFT bound is tight for our architecture
- If refuted → our filters may need N>3f+1, weaker than theoretical bound

---

## Experiment Status

| Exp | Topic | Status | Key Result |
|-----|-------|--------|------------|
| 1-8 | Original 8 | ✅ DONE | 7 proven, 1 buggy |
| 9 | Partition tolerance | ✅ DONE | 13-tick recovery |
| 10 | Fleet scaling | ✅ DONE | O(log N) confirmed |
| 11 | Byzantine tolerance | ✅ DONE | f≤3 converges with 3-layer filter |
| 12 | Spectral deviation | 🔄 RUNNING | Isolating deviation source |
| 13 | Optimal δ | 🔄 RUNNING | Sweeping δ=[1/256..1/4] |
| 14 | Heterogeneous clocks | 🔄 RUNNING | Clock rate 2×..20× |
| 15 | Memoir compression | ✅ DONE | O(log T) REFUTED → O(√T) |
| 16 | BFT filter comparison | ✅ DONE | Reputation+trimmed near-optimal |
| 17-23 | Remaining 7 | ⏳ QUEUED | Design approved, awaiting execution |

## Research Principles

1. **Every hypothesis is falsifiable** — each experiment can refute its hypothesis
2. **Negative results are valuable** — Exp 15 refuting O(log T) is as important as a confirmation
3. **Constrain the unknown** — each experiment shrinks the space of what we don't know
4. **Build on what's proven** — new experiments reference proven results
5. **Ideate from gaps** — every gap generates multiple possible experiments; pick the most constraining one
