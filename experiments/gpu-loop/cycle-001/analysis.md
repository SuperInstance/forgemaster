# Cycle 1 Analysis (Seed-2.0-mini) — 2026-05-16

## Fresh Eyes on Cycle 0 (GLM-5.1 Results)

GLM-5.1's headline finding: "Conservation law is substrate-invariant." Strong claim. Let me poke at it.

### What GLM-5.1 Got Right
- Conservation γ+H IS remarkably stable across precision configs (CV < 0.005). This is robust.
- INT8 frozen conservation (CV=0.0000) is a genuine finding — quantization grid pins the dynamics.
- The falsification of H1, H2, H3, H5 is well-supported by the data.

### What GLM-5.1 May Have Missed

**1. C varies 5× across configs — "invariant" is too strong**
- C ranges from 7.20 (INT8) to 37.71 (FP64). That's a 5.2× range.
- The conservation LAW holds (low CV), but the CONSTANT C is precision-dependent.
- GLM-5.1 noted this in the data table but didn't flag the contradiction with "substrate-invariant."
- The law γ+H = C is conserved, but C itself is a function of precision. This is subtler and more interesting than "invariant."

**2. All coupling was SYMMETRIC — the biggest untested assumption**
- In GLM-5.1's experiments, agent A communicates with agent B using a shared precision.
- In real GPU fleets, agent A (FP64) sends to B (INT8), and the translation is LOSSY in one direction.
- Agent B sends back to A, and the translation is lossless (INT8→FP64 is exact).
- This creates an ASYMMETRIC coupling matrix J_ij ≠ J_ji. Complex eigenvalues.
- The conservation law was derived for symmetric matrices. Asymmetric coupling is genuinely uncharted territory.

**3. BBP width 0.404 for ALL configs is suspiciously uniform**
- Every single config got width = 0.404 (or 0.354, 0.505 for two outliers).
- At N=20, the BBP transition is poorly resolved — you're seeing the finite-size artifact, not the true transition.
- This needs testing at N≥50 to say anything meaningful about broadening.

**4. The 1-bit crash was treated as a failure, not investigated**
- NaN from 1-bit quantization could mean: (a) the dynamics diverge, or (b) the implementation has a log(0) issue.
- Ternary (3-level: -1, 0, +1) was never tested. This is the natural sub-2-bit regime.
- The breakdown boundary is the most interesting feature and was left at "crashed."

**5. No coupling architecture × precision interaction**
- All cycle-0 experiments used one coupling architecture (unspecified, likely Hebbian or default).
- E4 showed architecture strongly affects γ+H (Random: 0.63–1.67, Hebbian: 1.63–2.38, None: 1.61–3.89).
- Architecture × precision could reveal interactions that pure precision experiments miss.

## Priority for Cycle 1

1. **ASYMMETRIC COUPLING** (highest priority — genuinely new territory)
2. **Sub-2-bit regime** (ternary, 2-bit variants — find the true breakdown)
3. **System size scaling** (N=10,20,50,100 — is BBP broadening real?)
4. **Architecture × precision** (Hebbian vs Attention vs Random with mixed precision)
5. **C(precision) functional form** — is C really "invariant" or does it follow a pattern?

## Confidence Assessment

| Finding from Cycle 0 | My Confidence | Why |
|---|---|---|
| γ+H is conserved across precision | HIGH | CV data is clear |
| "Substrate-invariant" conservation constant C | LOW | C varies 5× — the law holds, C is NOT invariant |
| INT8 frozen conservation | HIGH | Zero CV is unmistakable |
| BBP no broadening | VERY LOW | N=20 is too small to resolve |
| Conservation holds to 10^15:1 ratio | HIGH | Clear data, but only for symmetric coupling |

## Key Question for This Cycle

**Does asymmetric coupling (A→B lossy, B→A lossless) break the conservation law?**

If yes: the conservation law requires symmetric coupling, and GPU fleets with mixed precision are in genuinely new territory.
If no: the conservation law is even deeper than GLM-5.1 claimed.
