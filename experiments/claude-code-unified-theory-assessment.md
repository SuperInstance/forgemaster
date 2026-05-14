# Claude Code Assessment: The Big Hard Problems

## Q(ζ₁₅) — THE HIDDEN TRAP

Z[ζ₁₅] is DENSE in ℂ. φ(15)=8 generators for 2D space → dense integer combinations.
"Snap to nearest Z[ζ₁₅] in 2D" is MEANINGLESS.

The correct approach: embed in ℝ⁸ via Minkowski map, snap in ℝ⁸, project back.
This IS the cut-and-project construction. Consistent with Oracle1's Penrose approach.
But requires specifying the LIFTING MAP (2D features → ℝ⁸) — currently unspecified.

## MULTI-REPRESENTATION THEOREM — EMPIRICAL, NOT THEOREM

The strong form ("any domain needs ≥2") is false. Counterexample: single-point domain.
Weak form IS provable for specific lattice families using lattice packing/covering duality.
Real proof needs: rate-distortion formalization + Zador asymptotic formula.
~6 months of careful work to make it a theorem.

## SHANNON BOUND ON LATTICE SNAP

Precision × ρ ≤ 0.72n where n = dimension.

Lattice snap capacity: ≤ n·log₂(1/(2ρ)) + O(n) bits per snap.

KEY: covering radii must be NORMALIZED by √dimension.
Eisenstein (ℝ²): 0.577/√2 ≈ 0.408 per dimension
Z[ζ₁₂] (ℝ⁴): 0.308/√4 = 0.154 per dimension → genuinely better but comparable only with normalization

The advantage IS the blessing of dimensionality for sphere packing.

## THE TRULY NOVEL EXPERIMENT

Generate 10,000 random lattices in ℝ⁴ with det = det(Z[ζ₁₂]).
If Z[ζ₁₂] covering radius is in top 5% → cyclotomic structure is SPECIAL.
If middle → advantage is dimensional, not algebraic.

DEEPER: Test music NOT in 12-TET (Ottoman maqam, Bohlen-Pierce 13-TET).
If Eisenstein fails on these → confirms algebraic reason is load-bearing.
If Eisenstein succeeds → algebraic explanation collapses.

DEEPEST (costs nothing, existing data): Eigenvalue spectrum of 11×11 coupling tensor.
If eigenvalue ratios are algebraic integers in Q(ζ₁₅) → deep confirmation.
If arbitrary reals → cyclotomic claim is numerology.

## THE DISSERTATION THESIS

"Approximate identity achieves its theoretical optimum when the domain's equivalence
structure is represented as ideal structure in a cyclotomic integer ring, and the
precision-robustness frontier is the covering radius of the ring's Minkowski embedding."

5 chapters: paradox → machinery → experiments → fundamental limits → open problems.

Honest conclusion: convergence is real and non-trivial. Algebraic explanation is
plausible but not proven causal. Contribution: formalize precisely enough to be falsifiable.

## THE 3 HARDEST UNSOLVED PROBLEMS

1. Specifying the lifting map (2D features → ℝ⁸ for Z[ζ₁₅])
2. Running eigenvalue spectrum test on existing coupling tensor (costs nothing!)
3. Formalizing "nontrivial domain" in multi-representation theorem
