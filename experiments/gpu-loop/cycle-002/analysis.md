# Cycle 2 Analysis (Nemotron-30B) — 2026-05-16

## Reading the Signals

Two cycles, two different model architectures, and the story is converging:

### What's Rock-Solid (Both Models Agree)
1. **γ+H conservation holds across all precisions** — CV < 0.005 for random coupling, regardless of bits
2. **Architecture dominates precision** — random/Wigner coupling conserves, structured doesn't
3. **INT8 achieves frozen conservation** (CV=0.0000) — the quantization grid pins dynamics
4. **C is genuinely flat** across precision (0.64 ± 0.01 in Cycle 1's controlled setup)
5. **Asymmetric coupling preserves or IMPROVES conservation** — the biggest surprise

### What's Unexplained
1. **WHY does random coupling conserve while Hebbian/Attention don't?** Cycle 1 says "GOE eigenvalue statistics" but doesn't explain the mechanism. What is it about Wigner-Dyson level spacing that enforces γ+H = C?

2. **WHY does asymmetry improve conservation?** Cycle 1 found asymmetric has LOWER CV than symmetric. The noise-injection hypothesis is plausible but untested. If asymmetry adds stochastic regularization, we should see it in the eigenvalue spacing distribution.

3. **The ternary floor** — Is the ternary→binary transition sharp (phase transition) or gradual? This matters for whether there's a critical precision threshold or just progressive degradation.

4. **Can we DESIGN coupling matrices that conserve?** If GOE statistics are the key, we should be able to engineer structured matrices that have GOE-like eigenvalue statistics while maintaining useful structure.

### My Angle (Different Architecture, Different Instincts)

As a different model, I'm drawn to the **mechanism question** rather than the boundary-finding question. The previous models found WHERE conservation holds and where it breaks. I want to understand WHY.

**Key hypothesis to test:** Conservation emerges from the UNBIASED NATURE of random coupling. Wigner matrices have no preferred direction in matrix space — their eigenvalue statistics are universal (GOE). Hebbian and Attention matrices have CORRELATIONS between entries (structured by data or attention patterns). If I can show that decorrelating the entries of a Hebbian matrix restores conservation, that proves the mechanism.

**Secondary hypothesis:** Asymmetric coupling improves conservation because it breaks spurious correlations between the upper and lower triangles. Symmetric matrices have redundant information (J_ij = J_ji). Asymmetric coupling breaks this redundancy, and the resulting "noise" in the off-diagonal entries actually pushes the eigenvalue statistics closer to GOE.

## Priority Experiments

1. **Eigenvalue spacing distribution** — Test whether random/Hebbian/Attention have GOE vs Poisson spacing (Wigner surmise). This is the SMOKING GUN for the mechanism.

2. **Decorrelation of structured coupling** — Add increasing noise to Hebbian/Attention matrices and watch conservation emerge. Find the critical noise level.

3. **Designed coupling for conservation** — Construct structured matrices with GOE-matching eigenvalue statistics. Test conservation.

4. **Asymmetry as correlation breaker** — Measure entry correlations in symmetric vs asymmetric coupling. Test if asymmetry pushes eigenvalue statistics toward GOE.

5. **Ternary→Binary transition mapping** — Fine-grained sweep from 3-level to 2-level quantization.

## Confidence in Prior Findings

| Finding | Confidence | My Assessment |
|---------|-----------|---------------|
| Conservation is substrate-invariant | HIGH | Confirmed by two independent models with different experimental setups |
| Architecture dominates precision | HIGH | Clear signal (CV 0.03 vs 0.13). Need to understand mechanism. |
| INT8 frozen conservation | HIGH | Replicable, clear mechanism (quantization grid) |
| Asymmetric preserves/improves conservation | HIGH | Counterintuitive but well-measured |
| C is flat across precision | MED | Only confirmed in Cycle 1's controlled setup |
| Ternary is the floor | MED | Only one data point showing the transition |
| BBP no broadening | LOW | Methodology was flawed (block matrices) |
