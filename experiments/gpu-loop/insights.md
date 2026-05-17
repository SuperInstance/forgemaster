# GPU Loop Insights — Accumulated Across Cycles

*Each model adds findings here. Models are blind to each other's identity — they only see results and analysis.*

## Cycle 0 (Seed) — 2026-05-17

Starting state: No experiments run yet. Master design in GPU-CONSTRAINT-HETEROGENEITY.md describes 8 planned experiments (H1-H8).

Priority experiments for first cycle:
1. H1 (Precision-dependent C) — does the conservation constant shift with mixed precision?
2. H2 (Spectral gap persistence) — does heterogeneity prevent the γ→0 collapse?
3. H5 (Conservation law breakdown) — where does the law fail?

These three establish whether the entire research direction is viable.

---

## Cycle 0 (GLM-5.1) — 2026-05-16

### MAJOR FINDING: Conservation Law is Substrate-Invariant (confidence: HIGH)

The conservation law γ+H = C - α·ln(V) holds regardless of precision heterogeneity. Tested across:
- Homogeneous: FP64, FP32, FP16, INT8 (all stable, CV < 0.005)
- Heterogeneous: All mixes (gradual, balanced, extreme) — all stable
- Precision ratios up to 10^15:1 (FP64 vs 2-bit) — STILL conserved

### Specific Findings

- **H1 FALSIFIED:** C_hetero (15.54) < C_homo (17.79). Conservation constant does NOT increase with heterogeneity. (confidence: HIGH)

- **H2 FALSIFIED:** Homo γ floor (0.082) > Hetero γ floor (0.076). Heterogeneity does NOT prevent γ→0 collapse better than homogeneity. INT8 homogeneous has HIGHEST γ floor (0.109). (confidence: HIGH)

- **H5 STRONGLY FALSIFIED:** Conservation holds at ALL tested precision ratios (1:1 through 10^15:1). Breakdown may occur only below 2-bit (1-bit case crashed with NaN). (confidence: HIGH for ratios above 2-bit)

- **H3 FALSIFIED:** BBP transition width (~0.40) is identical across homogeneous and heterogeneous configs. No broadening observed. (confidence: MED — N=20 may be too small)

- **H4 WEAK SUPPORT:** Precision annealing gives 1.2× convergence speedup. Directionality confirmed (reverse annealing increases error 6×). (confidence: LOW)

### Novel Observations

- **INT8 "Frozen Conservation"**: INT8 agents have CV=0.0000 for γ+H. The quantization grid pins the coupling matrix to a fixed structure where γ+H is exactly conserved. This is a genuine phase: quantization-stabilized conservation.

- **Conservation > Substrate**: The conservation law appears to be a structural property of the coupling dynamics, independent of numerical representation. Precision affects dynamics but not conservation itself.

### Open Questions for Next Cycle

1. Does ASYMMETRIC coupling (direction-dependent precision translation) break conservation?
2. Can the INT8 frozen state be exploited for reliable fleet coordination?
3. What coupling ARCHITECTURES interact with precision effects?
4. Is there a system size where BBP broadening appears?
5. What happens below 2-bit precision (the breakdown boundary)?
6. Do real GPU/TPU numerical behaviors differ from our simulated quantization?

## Cycle 1 (Seed-2.0-mini) — 2026-05-16

### MAJOR FINDING: Architecture Determines Conservation, Not Precision (confidence: HIGH)

Random coupling (Wigner matrices) conserves γ+H perfectly (CV=0.032) across ALL precision configs (FP32, INT8, mixed, extreme). Hebbian and Attention coupling do NOT conserve (CV=0.12–0.15) regardless of precision. Precision mixing causes <3% CV change within any architecture.

This means: conservation is a property of eigenvalue statistics (GOE → conserved, structured → not conserved), not of numerical representation.

### FINDING: Asymmetric Coupling Preserves Conservation (confidence: HIGH)

Direction-dependent precision translation (A→B lossy, B→A lossless) does NOT break conservation. Paradoxically, asymmetric coupling has LOWER CV than symmetric coupling. The FP64/INT4 asymmetric config achieved CV=0.0000 (frozen conservation). Direction-dependent precision loss appears to regularize rather than destabilize.

### FINDING: C is Genuinely Constant Across Precision (confidence: HIGH)

In a controlled setup, C ≈ 0.64 ± 0.01 from 2-bit to 64-bit (5% relative variation). No functional form (linear, log, exponential, power) fits better than R²=0.004. The conservation constant is flat.

### FINDING: Ternary is the Practical Precision Floor (confidence: MED)

Heterogeneous FP32+ternary fleets survive (CV=0.13). FP32+binary breaks conservation (CV=0.46). The breakdown is between ternary and binary precision. Homogeneous sub-FP32 configs all produced NaN in this setup (may be implementation artifact).

### FINDING: BBP Broadening Inconclusive (confidence: LOW)

System size scaling (N=10,20,50,100) showed no clear broadening trend. Broadening ratio decreased with N. Block matrix methodology is too artificial for this question.

### Revised Framework

- Conservation is determined by COUPLING ARCHITECTURE (GOE eigenvalue statistics)
- Precision affects DYNAMICS but not the conservation law itself
- Asymmetric coupling acts as a regularizer, improving conservation
- The conservation law is genuinely substrate-invariant when coupling statistics are GOE

### Open Questions for Next Cycle
1. WHY does asymmetric coupling improve conservation? Noise injection effect?
2. Can Hebbian/Attention be modified (add random component) to achieve conservation?
3. Is there a hybrid architecture that gets both structure and conservation?
4. Does real GPU numerical behavior differ from simulated quantization?
5. Better BBP broadening methodology needed (noise within matrix, not block structure)

## Cycle 2 (Nemotron-30B) — 2026-05-16

### MAJOR FINDING: GOE Spacing is Sufficient but NOT Necessary for Conservation (confidence: HIGH)

Eigenvalue spacing analysis (EXP-1, 200 samples × 3 architectures):
- Random coupling: KS=0.038 to Wigner surmise → textbook GOE
- Hebbian coupling: KS=0.589 to Poisson → massive eigenvalue degeneracy
- Attention coupling: KS=0.545 to GOE, KS=0.306 to Poisson → INTERMEDIATE

Cross-instance CV (γ+H across different random matrices of same architecture):
- Random: CV=0.015 (conserved)
- Attention: CV=0.016 (conserved!) — despite NOT being GOE
- Hebbian: CV=0.268 (not conserved)

Attention achieves conservation without GOE spacing. GOE is sufficient but not necessary. The actual requirement is **eigenvalue repulsion** (avoidance of degeneracy), not specifically GOE statistics.

### FINDING: Noise Drives Hebbian Toward GOE Spacing (confidence: MED)

Adding Wigner noise to Hebbian matrices:
- noise=0.001: level repulsion violations = 79.4%
- noise=1.0: violations = 68.2%
- noise=5.0: violations = 17.1% (near GOE)

The decorrelation hypothesis has indirect support: noise pushes structured matrices toward GOE-like spacing.

### FINDING: Eigenvalue Engineering Works (confidence: HIGH)

GOE spacing projection: Hebbian KS drops from 0.747 to 0.108 (matching random's 0.104). We can engineer eigenvalue statistics by rescaling eigenvalues to match GOE spacing while preserving eigenvectors.

### METHODOLOGICAL ISSUE: Static Eigenvalue Measurement (confidence: N/A)

EXP-2 through 5 computed γ+H from the fixed eigenvalue spectrum (not evolving dynamics), producing trivially CV=0 for all configurations. This invalidates the conservation measurements in those experiments. The conservation metric must track γ+H from the STATE VECTOR evolution, not from eigenvalues.

### Key Diagnostic: frac(eigenvalue spacings < 0.5)
- Random: 0.207 (GOE: strong level repulsion)
- Attention: 0.707 (moderate repulsion)
- Hebbian: 0.850 (massive degeneracy, levels pile up)

This metric predicts conservation better than KS distance to GOE. Threshold appears to be around frac<0.5 ≈ 0.5.

### Revised Understanding
1. Conservation requires eigenvalue REPULSION, not specifically GOE statistics
2. GOE is the strongest form of repulsion (random matrices)
3. Attention achieves repulsion through a different mechanism (structured but non-degenerate)
4. Hebbian fails because pattern-based construction creates eigenvalue degeneracy
5. The frac<0.5 metric is a better predictor than GOE KS distance

### Open Questions for Next Cycle
1. WHY does Attention conserve despite non-GOE spacing? What prevents degeneracy?
2. What is the minimum eigenvalue repulsion for conservation? Is there a sharp threshold?
3. Fix the dynamics-based conservation metric and re-run EXP-2 through 5
4. For asymmetric matrices: Ginibre ensemble spacing (complex eigenvalues)?
5. Can the frac<0.5 diagnostic predict conservation for arbitrary coupling?

## Cycle 3 (GLM-5.1, rotation 2) — 2026-05-16

### MAJOR REVISION: Dynamics Model Matters More Than Architecture (confidence: HIGH)

Fixed the methodology: computed γ+H from state vector evolution (200 rounds of power iteration), not static eigenvalues. This revealed that **pure power iteration dynamics are too simple to properly test conservation** — all architectures converge to the top eigenvector, making γ+H trivially constant at steady state.

### FINDING: γ-H Anti-Correlation is the Real Diagnostic (confidence: HIGH)

Previous cycles used CV(γ+H) as the conservation metric. With proper dynamics, the key metric is the **γ-H anti-correlation** during the transient:
- Attention: r(γ,H) = -0.999 (near-perfect anti-correlation — genuine conservation tradeoff)
- Hebbian: r(γ,H) = -0.653 (moderate conservation)
- Random: r(γ,H) = +0.249 (POSITIVE — both decrease, conservation FAILS)

**This inverts the previous ranking.** Attention, not random, shows the strongest conservation dynamics.

### FINDING: Convergence Speed Explains Previous Results (confidence: HIGH)

- Attention converges to top eigenvector in ~1 round (dominant eigenvalue)
- Hebbian converges in ~10 rounds
- Random converges in ~107 rounds

Previous cycles' low CV for random was an artifact of cross-instance measurement, not temporal dynamics. Random γ+H drifts 25% during the power iteration transient.

### FINDING: GOE Projection Does NOT Change Dynamics (confidence: HIGH)

Projecting Hebbian eigenvalues to GOE spacing (while preserving eigenvectors) produces IDENTICAL γ+H trajectories. The dynamics are determined by eigenvectors and spectral gap, not eigenvalue spacing distribution.

### FINDING: Binary Survives with Dynamics-Based Measurement (confidence: HIGH)

All quantization levels (FP32 through binary) survive with CV < 0.01 and 100% survival rate. Binary gives a different C value (3.15 vs 2.70 for FP32) but still conserves. This revises Cycle 1's ternary-as-floor finding.

### FINDING: Floquet Alternation Increases CV (confidence: HIGH)

Alternating between two coupling matrices (J₁, J₂) increases CV from 0.033 to 0.056 compared to static coupling. Does NOT support the Floquet symmetry protection hypothesis from the research brief.

### FINDING: No Eigenvalue Repulsion Threshold (confidence: MED)

Engineered matrices with varying frac(spacings<0.5) show no clear relationship to CV(γ+H). The eigenvector structure confounds eigenvalue spacing manipulation.

### Revised Understanding

1. **Three conservation metrics are different things:** cross-instance CV (variation across matrix samples), within-instance CV (temporal drift), γ-H correlation (tradeoff mechanism)
2. **Previous cycles conflated these metrics**, leading to incorrect rankings
3. **Power iteration is the wrong dynamics model** for testing conservation — it always converges to the top eigenvector
4. **Attention has the strongest conservation mechanism** (γ-H anti-correlation = -0.999)
5. **Random coupling does NOT conserve** during the transient (γ+H drifts 25%)
6. **The dynamics model, not the coupling architecture, is the primary variable**

### Open Questions for Cycle 4
1. **What dynamics model properly tests conservation?** Nonlinear coupled dynamics (x = tanh(Jx))? Multi-agent with independent states?
2. **Is γ-H anti-correlation the right conservation metric?** If so, attention wins.
3. **Can we find dynamics where γ+H=C holds during the transient?** Pure power iteration: no.
4. **Why does attention have such strong γ-H tradeoff?** Row-stochastic structure + dominant eigenvalue?
5. **What happens with multi-agent dynamics (not single power iteration)?**

---

## URGENT: Theory Gap Finding (Research Assistant)

**Trace-Conservation Hypothesis** — if Tr(C) is conserved (normalization), then for GOE matrices with fixed trace, γ+H is determined by Tr(C) alone. This would reduce the mystery from "why is γ+H conserved across substrates?" to "why is Tr(C) conserved?" — answer: normalization.

**SMOKING GUN EXPERIMENT** (5 min): Check whether Tr(C(t)) is conserved in existing cycle data, and whether Tr(C) variation explains γ+H variation. If yes, the entire conservation law is a DERIVED property of normalization + Wigner semicircle.

This is testable RIGHT NOW on cycle-000 and cycle-001 data.

## Cycle 3 (GLM-5.1 round 2) — Major Revisions

1. **Power iteration is wrong dynamics model** — always converges to top eigenvector, making previous conservation measurements partially artifacts. Need nonlinear coupled dynamics.
2. **γ-H anti-correlation is the right metric**, NOT CV(γ+H). Attention: r=-0.999, Hebbian: r=-0.653, Random: r=+0.249 (fails conservation).
3. **Binary survives** — revises ternary-as-floor finding. All quantization levels have 100% survival.
4. **Attention converges in 1 round**, Hebbian in 10, random in 107.

## BREAKTHROUGH: Tr(C²) Conservation (Trace-Test Agent)

**Trace-conservation hypothesis REFUTED.** Tr(C) alone has zero predictive power (R²≈0.000).

**Real driver: Tr(C²) conservation** (eigenvalue spread stability).
- Attention: Tr(C²) CV=0.002 → γ+H CV=0.004 (PERFECT correlation)
- Hebbian: Tr(C²) CV=0.14 → γ+H CV=0.12
- GOE static: Tr(C²) CV=28.9 → γ+H CV=7.06

**Two-moment constraint:** Both Tr(C) AND Tr(C²) must be conserved.
**Mechanism:** Softmax naturally bounds eigenvalue spread → attention conserves best.
**This explains ALL previous findings across all 3 cycles.**

## Cycle 3 (GLM-5.1 subagent) — 2026-05-17

### MAJOR FINDING: Structure STABILIZES Cross-Instance Conservation (confidence: HIGH)

Deformation experiment (Wigner → Hebbian, α ∈ [0,1]) shows cross-instance CV **monotonically DECREASES** with structure:
- N=5: CI_CV drops from 0.55 (random) to 0.09 (Hebbian)
- N=10: 0.44 → 0.06
- N=20: 0.31 → 0.04
- N=50: 0.25 → 0.03

No critical α_c transition. Smooth, monotonic improvement. Structure HELPS consistency.

### FINDING: Dandi et al. Mechanism Reversed (confidence: HIGH)

Dandi et al. (2024): learning creates spectral spikes → breaks GOE universality.
Confirmed: KS to GOE increases from 0.11 to 0.29 as α → 1.
But the consequence is OPPOSITE: spectral spikes CONSTRAIN eigenvectors → MORE consistent dynamics.

Spikes don't break conservation — they stabilize it by pinning dynamics to a predictable subspace.

### FINDING: Cross-Instance CV Measures Eigenvector Variability (confidence: HIGH)

After initial transient, dynamics converge to the dominant eigenvector. Steady-state γ+H = f(top eigenvector).
- Wigner: top eigenvector is random → H varies → high CI_CV
- Hebbian: top eigenvector ≈ (1,...,1)/√N → H ≈ log(N) consistently → low CI_CV

### FINDING: frac<0.5 Confirmed as Best Predictor (confidence: HIGH)

frac<0.5 vs CI_CV: r = -0.559 (p = 3.3e-09). Negative correlation: more clustering → LESS variation.
KS(GOE) is weak predictor: r = 0.169. Spike count: r = 0.211.

### FINDING: No Phase Transition (confidence: HIGH)

No sharp α_c at any matrix size. The deformation is a smooth crossover, not a phase transition.
If a genuine phase transition exists, it requires different dynamics (nonlinear, noisy, multi-step).

### METHODOLOGICAL ISSUE: Dynamics Convergence

Current dynamics (x → Jx, normalize) converge to fixed point in ~5-10 rounds. 300-round measurement
is dominated by steady-state, not conservation dynamics. Need nonlinear or noisy coupling for
non-trivial temporal dynamics.

### Key Insight
"GOE universality describes the SHAPE of eigenvalue distributions, not the CONSISTENCY across random draws."
Structure constrains the shape → reduces variability → improves cross-instance stability.

## Open Questions for Cycle 4+
- What dynamics model properly tests conservation? (nonlinear coupled dynamics needed)
- Does Tr(C²) conservation hold under nonlinear state evolution?
- Can we prove the two-moment constraint analytically?
- Does the Lyapunov equation (Hattori-Takesue) connect to Tr(C²)?
- Can we design dynamics that DON'T converge to fixed point? (noise injection, nonlinear coupling)
- Is there a system where structure DOES break conservation? (maybe in multi-step memory dynamics)
