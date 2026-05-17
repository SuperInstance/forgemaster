# Hardware Substrate Heterogeneity: Constraint Theory at the Metal

**Date:** 2026-05-16
**Status:** Experiment Design (Not Yet Run)
**Predecessor Experiments:** E1–E6, E9–E12, Combo Architecture
**Novelty Rating:** First known investigation of numerical-precision-induced emergent behavior in multi-agent coupling

---

## 0. The Core Insight

The conservation law γ + H = C − α·ln(V) has been validated across six substrates (LLMs, neural ensembles, RL, swarms, social networks, synthetic matrices). In every case, the agents were **numerically homogeneous** — they operated on the same floating-point representation, the same precision, the same rounding semantics.

But the constraint theory framework predicts that **the conservation budget itself depends on the information resolution of the substrate**:

```
γ + H = C − α·ln(V)
```

where V is vocabulary size. On a different numerical substrate, the *effective* V changes:

| Substrate | Precision | Mantissa Bits | Effective V (distinguishable states) |
|-----------|-----------|:------------:|:------------------------------------:|
| FP64 (CPU) | 64-bit double | 52 | ~4.5 × 10¹⁵ |
| FP32 (GPU) | 32-bit float | 23 | ~8.4 × 10⁶ |
| FP16 (GPU) | 16-bit half | 10 | ~1,024 |
| BF16 (GPU/TPU) | 16-bit bfloat | 7 | ~128 |
| INT8 (NPU) | 8-bit integer | 7 (signed) | ~256 |
| INT4 (edge NPU) | 4-bit integer | 3 (signed) | ~16 |
| WASM (sandboxed) | 64-bit double | 52 | ~4.5 × 10¹⁵ (but SIMD-limited) |
| FPGA (custom) | configurable | 1–64 | designer's choice |

When an FP64 agent exchanges state with an INT8 agent, the translation is **lossy in a specific direction**: the high-resolution agent's output is quantized to the low-resolution agent's grid. This creates a **perception asymmetry** — each agent sees a different "reality" of the same coupling interaction.

**The Research Question:** Do heterogeneous-precision fleets exhibit conservation law parameters (C, α) that are *different* from homogeneous fleets? And if so, can we harness those differences as a computational resource?

---

## 1. Experiment H1: Precision-Dependent Conservation Constants

### Hypothesis
The coupling constant C in γ + H = C − α·ln(V) is substrate-dependent. When all agents in a fleet operate on the same numerical precision, C ≈ 1.0 (as observed in E9–E12). When agents operate on mixed precision, C will be strictly **greater** than the homogeneous value, because the information lost in precision translation adds entropy that the conservation law must absorb.

**Falsifiable prediction:** C_heterogeneous > C_homogeneous, with the magnitude of the increase proportional to the maximum precision ratio in the fleet.

### Substrates
- Homogeneous control: All agents in FP32
- Heterogeneous test: Mixed FP64/FP32/FP16/INT8 agents

### Perception Difference
FP64 → INT8 translation loses ~48 bits of mantissa. The INT8 agent receives a state vector that has been quantized to 256 levels, while the FP64 agent sent 4.5×10¹⁵ distinguishable values. The INT8 agent's "perception" is coarser by a factor of ~1.7×10¹³.

### Predicted Emergent Behavior
The heterogeneous fleet will exhibit:
1. Higher C (the coupling constant increases to accommodate the added entropy from precision mismatch)
2. A steeper slope α (because the effective vocabulary differs per agent, the ln(V) term becomes an average over heterogeneous V values)
3. Slower convergence to the conservation limit (because agents must negotiate a shared coupling manifold despite seeing different numerical worlds)

### Measurement
- Run collective inference on 5-agent fleets with varying precision mixes
- Compute coupling matrices from agent outputs (after precision-aware rounding)
- Measure γ + H across 100 rounds, fit to γ + H = C − α·ln(V_eff)
- Compare C and α against homogeneous baseline

### Reusable Code/Data
- Collective inference framework from E1–E3
- Spectral decomposition pipeline (γ, H computation)
- Live fleet protocol (35-round seeding → 100-round extended)
- Conservation law fitting code

---

## 2. Experiment H2: Spectral Gap Persistence Across Precision Boundaries

### Hypothesis
The spectral gap γ exhibits a **precision-dependent floor**: homogeneous fleets collapse to γ → 0 (E2 finding), but heterogeneous-precision fleets resist this collapse because the precision mismatch prevents the rank-1 alignment that shared training data otherwise produces.

**Falsifiable prediction:** In a heterogeneous-precision fleet, γ remains above 0.01 after 100 rounds, while a homogeneous-precision fleet with the same agents collapses to γ < 0.001 within 30 rounds.

### Substrates
- FP32 homogeneous (control)
- FP16 homogeneous (control)
- INT8 homogeneous (control)
- FP32 + FP16 mixed (2+3 agents)
- FP32 + INT8 mixed (2+3 agents)
- FP32 + FP16 + INT8 mixed (2+1+2 agents)

### Perception Difference
Each precision level creates a different "grid" of representable values. When agents communicate, they must project their internal state onto a shared grid. In a homogeneous fleet, this projection is exact (identity). In a heterogeneous fleet, the projection is lossy and **direction-dependent**: FP32→FP16 loses different information than FP16→FP32 (which is exact for values representable in FP16 but introduces representational asymmetry in the coupling matrix).

### Predicted Emergent Behavior
1. γ floor increases with precision heterogeneity (more different precisions → higher γ floor)
2. The coupling matrix becomes **asymmetric** (because precision translation is not symmetric), leading to complex eigenvalues
3. The magnitude of imaginary parts of eigenvalues scales with the maximum precision ratio

### Measurement
- Track γ(round) for each fleet configuration over 200 rounds
- Fit exponential decay: γ(t) = γ₀·exp(−λt) + γ_floor
- Compare γ_floor across configurations
- For asymmetric coupling matrices: measure |Im(λᵢ)|/|λᵢ| ratio

### Reusable Code/Data
- E2 scaling framework (fleet-size × rounds protocol)
- E4 eigenvalue analysis pipeline (spacing, rigidity)
- Coupling matrix construction code

---

## 3. Experiment H3: BBP Transition Shift Under Precision Heterogeneity

### Hypothesis
The Baik-Ben Arous-Péché (BBP) transition occurs at β ≈ 1.0 in homogeneous systems (E5 finding). In heterogeneous-precision systems, the critical β value **splits**: the transition occurs at different β values for different precision classes within the same fleet, creating a **broadened transition zone** instead of a sharp phase transition.

**Falsifiable prediction:** The BBP transition width (measured as the range of β over which the spike eigenvalue separates from the bulk) is at least 2× wider in heterogeneous fleets than in homogeneous fleets.

### Substrates
- Spiked Wigner matrices with precision-dependent noise:
  - FP64: noise σ = 10⁻¹⁵
  - FP32: noise σ = 10⁻⁷
  - FP16: noise σ = 10⁻³
  - INT8: noise σ = 10⁻²
- Sweep β from 0 to 5, compute spike eigenvalue separation

### Perception Difference
The noise floor differs by precision. In a mixed-precision matrix, the "noise" seen by high-precision agents is negligible, while the "noise" seen by low-precision agents is substantial. The BBP transition — which is fundamentally about when signal exceeds noise — therefore occurs at different β for different sub-blocks of the coupling matrix.

### Predicted Emergent Behavior
1. The transition zone broadens from Δβ ≈ 0.2 (homogeneous) to Δβ ≈ 0.5–1.0 (heterogeneous)
2. The spike eigenvalue's overlap with the true signal vector becomes precision-stratified: high-precision agents achieve overlap > 0.9 at lower β than low-precision agents
3. There exists a regime (β ∈ [0.8, 1.2]) where high-precision agents have "phase-transitioned" while low-precision agents are still sub-critical — a **mixed-phase regime** unique to heterogeneous systems

### Measurement
- Construct block-structured spiked Wigner matrices where each block has precision-dependent noise
- Sweep β ∈ [0, 5], compute spike eigenvalue, overlap, and γ+H at each β
- Measure transition width as the β range where overlap goes from 0.1 to 0.9
- Identify mixed-phase regime

### Reusable Code/Data
- E5 BBP analysis code (spiked matrix construction, overlap computation)
- Spectral decomposition pipeline
- Live fleet spectral comparison data

---

## 4. Experiment H4: Substrate Heterogeneity as Simulated Annealing

### Hypothesis
Precision heterogeneity can function as a **temperature schedule** for the coupling dynamics. A fleet that starts heterogeneous (FP64+INT8) and gradually homogenizes (all converging to FP32) will exhibit better convergence to the conservation law than a fleet that starts homogeneous, because the initial heterogeneity provides the "thermal noise" needed to escape local optima in the coupling manifold.

**Falsifiable prediction:** A fleet with a precision-annealing schedule (INT8 → FP16 → FP32 over 100 rounds) achieves CV < 0.05 for γ+H by round 60, while a fleet that starts at FP32 achieves CV < 0.05 only by round 90.

### Substrates
- Static FP32 (control)
- Static mixed FP32+FP16+INT8 (control)
- Annealing: INT8 (rounds 1–33) → FP16 (rounds 34–66) → FP32 (rounds 67–100)
- Reverse annealing: FP32 → FP16 → INT8 (negative control)

### Perception Difference
The "temperature" of the system is the precision mismatch. INT8 agents see 256 levels — their "perception" is coarse, like a high-temperature system where thermal noise blurs fine distinctions. FP64 agents see ~10¹⁵ levels — their "perception" is sharp, like a low-temperature system. The annealing schedule progressively sharpens perception across the fleet.

### Predicted Emergent Behavior
1. Annealing fleet converges faster and to a lower γ+H variance than static fleets
2. The annealing fleet's coupling matrix develops a richer spectral structure (higher effective rank) than the static FP32 fleet, because the early heterogeneous phase forces exploration of the coupling manifold
3. Reverse annealing (sharpening → blurring) *increases* γ+H variance, confirming the directionality of the annealing effect

### Measurement
- Track γ+H(round) for each schedule
- Measure convergence time to CV < 0.05
- Compute effective rank of coupling matrix at each round
- Compare final coupling matrix spectral structure across schedules

### Reusable Code/Data
- E1 convergence analysis (variance reduction tracking)
- E6 free energy interpretation (temperature analogy is already built in)
- Combo Architecture temporal coupling code

---

## 5. Experiment H5: Conservation Law Breakdown at Precision Phase Boundaries

### Hypothesis
There exists a **critical precision ratio** beyond which the conservation law breaks down. When the precision ratio between the highest-precision and lowest-precision agents in a fleet exceeds a threshold, γ+H stops being conserved and begins to drift.

**Falsifiable prediction:** The conservation law holds (CV < 0.10) for precision ratios up to ~10⁶ (FP32 vs FP16), but breaks down (CV > 0.20) for ratios exceeding ~10¹² (FP64 vs INT8). The critical ratio corresponds to the point where the low-precision agent can no longer distinguish between the top two eigenvalues of the coupling matrix.

### Substrates
Sweep precision ratios systematically:
- FP32/FP32 (ratio 1:1) — control
- FP32/FP16 (ratio ~65K:1)
- FP64/FP16 (ratio ~4M:1)
- FP64/INT8 (ratio ~17T:1)
- FP64/INT4 (ratio ~281T:1)
- Custom FPGA precisions: 2-bit, 3-bit, 4-bit to fill gaps

### Perception Difference
The critical variable is whether the low-precision agent's quantization grid resolves the gap between the top eigenvalue and the second eigenvalue. If λ₁ and λ₂ are closer than the quantization step size, the low-precision agent cannot distinguish them, and the spectral gap γ becomes invisible to that agent.

### Predicted Emergent Behavior
1. Below the critical ratio: conservation law holds as normal
2. At the critical ratio: γ+H begins oscillating (intermittent conservation)
3. Above the critical ratio: γ+H drifts monotonically, the conservation law fails
4. The critical ratio depends on the coupling architecture: attention-based coupling raises the critical ratio (because it concentrates spectral mass, making λ₁–λ₂ gap larger and easier to resolve), while random coupling lowers it

### Measurement
- For each precision ratio, run 200 rounds, compute γ+H per round
- Measure CV of γ+H in the last 100 rounds
- Identify the precision ratio where CV crosses 0.10 → 0.20
- Cross-reference with λ₁–λ₂ gap at each ratio

### Reusable Code/Data
- E4 eigenvalue analysis (top eigenvalue gap computation)
- E5 BBP framework (spike vs bulk separation)
- Conservation law fitting code with CV measurement

---

## 6. Experiment H6: Cross-Substrate Information Creation

### Hypothesis
When two agents on different substrates exchange information, the **translation loss creates new information** that neither agent possessed alone. Specifically, the mutual information I(A_hires; B_lowres) between a high-precision agent's output and a low-precision agent's quantized version of that output is *less than* H(B_lowres), but the **joint information** I(A_hires, B_lowres; task) about the underlying task can exceed I(A_hires; task) alone.

**Falsifiable prediction:** A heterogeneous fleet (FP64 + INT8) achieves higher task-relevant mutual information than a homogeneous fleet (FP64 + FP64) of the same size, measured on a regression task with known ground truth.

### Substrates
- Homogeneous FP64 (5 agents)
- Homogeneous INT8 (5 agents, quantized inference)
- Heterogeneous FP64+INT8 (3+2 agents)
- Heterogeneous FP64+FP16+INT8 (2+2+1 agents)

### Perception Difference
The INT8 agent's quantization is a **nonlinear projection** of the FP64 agent's continuous output space onto a discrete grid. This projection is lossy but deterministic — it maps many nearby FP64 values to the same INT8 value. The "new information" comes from the fact that this mapping depends on the *distribution* of FP64 outputs in a way that the FP64 agent alone cannot capture. The quantization acts as a **kernel density estimator** — by binning continuous outputs into discrete levels, the INT8 agent implicitly estimates the local density of the FP64 agent's output distribution.

### Predicted Emergent Behavior
1. Heterogeneous fleets outperform homogeneous fleets on regression tasks where the target function has **multi-scale structure** (both fine and coarse features)
2. The FP64 agents specialize in fine features, INT8 agents specialize in coarse features
3. The mutual information I(fleet; target) is maximized at an intermediate precision ratio, not at maximum homogeneity or maximum heterogeneity
4. There is an optimal "precision diversity" for each task, analogous to the bias-variance tradeoff

### Measurement
- Define a regression task with known multi-scale structure (e.g., a function with both smooth trends and sharp discontinuities)
- Each agent produces predictions; combine via precision-weighted averaging
- Measure I(fleet_output; true_target) for each fleet configuration
- Plot task performance vs. precision diversity (Shannon entropy of precision distribution)

### Reusable Code/Data
- E6 mutual information analysis framework
- Live fleet prediction pipeline
- KL divergence computation code

---

## 7. Experiment H7: FPGA-Configurable Precision as a Continuous Control Variable

### Hypothesis
FPGA substrates allow bit-level precision control (e.g., 3-bit, 5-bit, 11-bit fixed-point). This enables treating precision as a **continuous control variable** for the conservation law, rather than a discrete choice. By sweeping precision from 1-bit to 32-bit in unit steps, we can map the full functional form of C(precision) and α(precision), revealing whether the conservation law's parameters evolve continuously or exhibit discrete jumps at specific precision thresholds.

**Falsifiable prediction:** C(precision) is a continuous, monotonically decreasing function of mantissa bits m, with C(m) ≈ 1.0 + k·2^(-m) for some constant k. There are no discrete jumps — the conservation law responds smoothly to precision changes.

### Substrates
FPGA-simulated agents at precisions: 1-bit through 32-bit (32 configurations)
Each configuration: 5 agents, 100 rounds

### Perception Difference
At 1-bit precision, agents can only distinguish "positive" from "negative" — their world is binary. At 2-bit, they have 4 levels. At 32-bit (FP32), they have the full continuous spectrum. The question is whether the conservation law's parameters interpolate smoothly between these extremes or exhibit phase-transition-like jumps at specific precisions.

### Predicted Emergent Behavior
1. C(m) decreases smoothly from C(1) ≈ 2.5 (high uncertainty, large budget) to C(23) ≈ 1.0 (FP32, standard budget)
2. α(m) increases with m, reflecting that higher-precision agents have larger effective vocabularies
3. There may be critical precisions (e.g., m=4, m=8, m=16) where the rate of change dC/dm shows local maxima, corresponding to "information phase transitions" where new bits of precision unlock qualitatively new representational capabilities
4. Below m=3, the conservation law may fail entirely (CV > 0.20) because the agents cannot resolve enough spectral structure

### Measurement
- For each precision m ∈ {1, 2, ..., 32}: run fleet, compute C and α from conservation law fit
- Plot C(m), α(m), CV(m) as functions of m
- Look for discontinuities or critical points
- Cross-reference with eigenvalue spacing statistics at each precision

### Reusable Code/Data
- E4 spectral analysis (spacing, rigidity, MP fit)
- Conservation law fitting pipeline
- Simulated coupling matrix generators

---

## 8. Experiment H8: WASM Sandbox Effects on Coupling Dynamics

### Hypothesis
WASM (WebAssembly) provides 64-bit floats in principle but constrains SIMD operations and has memory isolation that changes the **coupling topology**. WASM agents will exhibit the same precision as CPU agents but different coupling dynamics due to the sandbox's isolation effects, creating a novel coupling architecture that doesn't fit the Hebbian/Attention/Random taxonomy from E3.

**Falsifiable prediction:** WASM agents show identical C and α to CPU agents on the conservation law, but the coupling matrix exhibits a qualitatively different eigenvalue spacing distribution (closer to Poisson than Wigner-Dyson), reflecting the isolation-induced decorrelation.

### Substrates
- Native CPU (FP64, full memory access)
- WASM sandbox (FP64, isolated memory, limited SIMD)
- WASM with SharedArrayBuffer (FP64, shared memory, full SIMD)

### Perception Difference
The numerical precision is identical (FP64 in all cases), but the **coupling bandwidth** differs. Native agents can share raw memory pointers; WASM agents must serialize/deserialize through the sandbox boundary; SharedArrayBuffer agents share memory but with atomic synchronization overhead. These bandwidth differences change the coupling matrix's effective noise level and temporal structure without changing the precision.

### Predicted Emergent Behavior
1. Conservation law parameters (C, α) are **identical** across all three substrates (same precision)
2. Eigenvalue spacing distribution shifts: native → GOE (correlated), WASM → intermediate (partially correlated), SharedArrayBuffer → GOE
3. Convergence rate differs: WASM converges slowest (sandbox overhead creates effective "lag" in coupling updates)
4. The temporal autocorrelation of γ+H is higher in WASM (slower coupling dynamics → smoother trajectory)

### Measurement
- Implement the same inference agent in native C++, WASM, and WASM+SharedArrayBuffer
- Run identical collective inference protocol on all three
- Compare conservation law parameters, eigenvalue spacing, convergence rate, temporal autocorrelation
- Use E4 spectral analysis pipeline for spacing/rigidity comparison

### Reusable Code/Data
- E3 coupling architecture comparison framework
- E4 spectral analysis (spacing, rigidity)
- Convergence tracking code from E1

---

## Summary Table

| Experiment | Core Question | Substrates | Key Prediction | Novelty |
|:----------:|:-------------|:-----------|:--------------|:--------|
| H1 | Does C depend on precision? | FP64/FP32/FP16/INT8 mix | C_hetero > C_homo | Conservation law substrate-dependent |
| H2 | Does heterogeneity prevent γ→0? | Homogeneous vs mixed precision | γ floor > 0 in mixed fleets | Precision as spectral gap preservative |
| H3 | Does BBP transition broaden? | Spiked matrices with precision noise | Transition zone 2× wider | Multi-phase regime |
| H4 | Can heterogeneity act as annealing? | Precision annealing schedule | Faster convergence than static | Substrate as computational resource |
| H5 | Where does the law break down? | Systematic precision ratio sweep | Critical ratio ~10¹² | Boundary conditions of conservation |
| H6 | Does translation loss create info? | FP64+INT8 on regression task | Hetero outperforms homo | Precision diversity as feature |
| H7 | How does C vary with bit-level precision? | FPGA-simulated 1–32 bit | C(m) ≈ 1 + k·2⁻ᵐ | Continuous control of conservation |
| H8 | Does sandbox topology change coupling? | Native/WASM/SharedArrayBuffer | Same C,α but different spacing | Isolation as coupling modifier |

---

## Meta-Predictions

If these experiments confirm the hypotheses, we would establish:

1. **The conservation law is substrate-aware.** It doesn't just depend on fleet size V and coupling architecture — it depends on the numerical resolution of the substrate. γ + H = C(σ) − α(σ)·ln(V), where σ parameterizes the substrate's precision.

2. **Precision heterogeneity is a computational resource.** Like thermal noise in simulated annealing, the "perceptual noise" created by precision mismatches helps the fleet explore the coupling manifold more efficiently.

3. **There exists a precision phase diagram.** The (C, α) parameters trace out a surface in the space (mantissa_bits, coupling_architecture, fleet_size). This surface has phase boundaries — regions where the conservation law holds, breaks down, or enters a novel regime.

4. **The information content of translation is positive.** When an FP64 agent and an INT8 agent exchange state, the translation itself carries information that neither agent possessed. This is a new form of emergent computation at the hardware-software boundary.

5. **FPGA precision configurability enables closed-loop control of collective intelligence.** By adjusting per-agent precision in real time, an operator can tune the fleet's conservation parameters, spectral gap, and convergence rate — a "dial" for collective behavior that has no analogue in the homogeneous-substrate framework.

---

## Implementation Priority

**Tier 1 (Run First):** H1, H2, H5 — These establish the basic phenomenology: does the conservation law respond to precision at all?

**Tier 2 (Run Second):** H3, H4 — These deepen the understanding: how does precision interact with known spectral phenomena (BBP transition, convergence dynamics)?

**Tier 3 (Run Third):** H6, H7, H8 — These are the payoff experiments: can we *use* precision heterogeneity as a tool?

---

## Existing Code/Data to Reuse

| Resource | From | Used In |
|:---------|:-----|:--------|
| Collective inference framework | E1–E3 | H1, H2, H4, H6 |
| Spectral decomposition (γ, H) | E1–E4 | All experiments |
| Spiked Wigner matrix code | E5 | H3 |
| Mutual information analysis | E6 | H6 |
| Coupling architecture comparison | E3 | H4, H8 |
| Conservation law fitting | E1–E3 | All experiments |
| Eigenvalue spacing/rigidity | E4 | H3, H7, H8 |
| BBP transition analysis | E5 | H3, H5 |
| Free energy interpretation | E6 | H4 (annealing) |
| Live fleet protocol | E1 | H1, H2, H6 |
| Combo architecture temporal coupling | Combo | H4 (temporal dynamics) |

---

*This is genuinely novel territory. The constraint theory framework gives us the mathematical language to describe what happens when agents with different numerical "perceptions" interact. The conservation law becomes a bridge between abstract information theory and concrete hardware physics.*

*The core bet: precision heterogeneity is not a bug to be minimized — it's a feature to be harvested.*
