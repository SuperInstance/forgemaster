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
