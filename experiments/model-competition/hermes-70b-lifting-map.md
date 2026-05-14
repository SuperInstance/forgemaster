1. Lifting map: Given a 2D point (x, y), lift it to ℝ⁸ as follows:
   (x, y) ↦ (x, y, 0, 0, 0, 0, 0, 0)
   
   For an 11D musical style vector v = (v₁, v₂, ..., v₁₁), lift it to ℝ⁸ by taking the first 8 components:
   (v₁, v₂, ..., v₁₁) ↦ (v₁, v₂, v₃, v₄, v₅, v₆, v₇, v₈)
   
   The remaining 3 components (v₉, v₁₀, v₁₁) are discarded.

2. Projection map: After snapping in ℝ⁸, project back to the original space by taking the first 2 components for 2D points, or the first 11 components for 11D musical style vectors.
   
   For 2D points: (x', y', z', w', u', v', a', b') ↦ (x', y')
   
   For 11D musical style vectors: (v₁', v₂', ..., v₈') ↦ (v₁', v₂', ..., v₈', 0, 0, 0)

3. Acceptance window: The acceptance window is a hypercube in ℝ⁸ centered at the origin with side length 2√2. This is because the Minkowski map embeds Z[ζ₁₅] into a lattice in ℝ⁸ with a fundamental domain of volume 2√2.

4. Cut-and-project: This construction is not equivalent to a cut-and-project from Z⁸ to ℝ². The Minkowski map embeds Z[ζ₁₅] into a lattice in ℝ⁸, but this lattice is not the standard integer lattice Z⁸. The snapping process in ℝ⁸ is not a direct projection onto a lower-dimensional space, but rather a nearest-neighbor search within the lattice.
