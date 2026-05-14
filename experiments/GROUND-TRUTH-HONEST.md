# Ground Truth: Honest Assessment of Permutational Folding

## What We Claimed vs What's Real

### CLAIM: Z[ζ₅] is 8× denser → tighter constraint checking
**REALITY**: Z[ζ₅] pair snap max_d = 0.614, WORSE than Eisenstein 0.574.
The "0.074" result was from biased sampling near origin with search_range=3.
The overcomplete basis has MORE vectors but the 2D projection pairs don't 
cover as well as the Eisenstein hexagonal lattice for n=5.

### CLAIM: Z[ζ₁₂] gives 1.55× tighter covering radius
**REALITY**: CONFIRMED. Z[ζ₁₂] max_d = 0.308 vs Eisenstein 0.574.
With 10 basis pair projections, the 12th cyclotomic field genuinely covers better.
This is the real finding — but only for n≥10.

### CLAIM: Consensus is uncertainty quantification
**REALITY**: NOT CALIBRATED. 91% of test points land in the same consensus bin.
The fold order diversity doesn't produce useful uncertainty signals.
The 2.9/24 mean consensus is a bug, not a feature — it means the folds
almost always disagree, so consensus has no discriminative power.

### CLAIM: 6× more work recovers via SIMD
**REALITY**: Babai's nearest plane TIES pair snap 94% of the time for Z[ζ₅].
The overcomplete approach adds almost nothing over the standard algorithm.
For Z[ζ₁₂], the improvement IS real but the computational cost is 10× more
basis pairs, and SIMD recovery is theoretical (not benchmarked in C yet).

### CLAIM: Constraint walk stability improves
**REALITY**: NO IMPROVEMENT. Max drift identical for both bounds.
The random walk dominates the drift, not the lattice bound.
Tighter lattice doesn't help when the noise is larger than the lattice spacing.

## What ACTUALLY Works

1. **Z[ζ₁₂] covering radius is genuinely tighter** (0.308 vs 0.577)
2. **Parallel function serving** is real — different n for different tasks
3. **The four clocks framing** (growth/memory/hormone/electric) is correct
4. **FLUX ISA is a clean abstraction** — 7 opcodes, 16 bytes, substrate-independent
5. **The Galois orbit = posterior connection** (from reverse-actualization) is promising but unproven

## What DOESN'T Work

1. **Z[ζ₅] is NOT better than Eisenstein** for snap accuracy
2. **Consensus is not calibrated** as uncertainty signal
3. **Constraint walks don't improve** with tighter bounds
4. **The fold order diversity is noise, not information** (for n=5)
5. **Permutational folding doesn't beat Babai** for n=5

## The Honest Conclusion

The overcomplete lattice idea has ONE verified win: Z[ζ₁₂] covering radius.
Everything else is either worse than Eisenstein or not calibrated.
The parallel function serving concept (different n per function) is the 
most promising direction, not permutational folding itself.

The extension simulator worked correctly: we followed the thread,
found the truth, and the truth said "not as good as we hoped."
That's how science works. The baton spline remembers the off-curve points.
