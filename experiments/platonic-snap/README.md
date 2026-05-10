# Platonic Snap Experiments

Testing the **Platonic Snap Hypothesis**: ADE classification determines snap quality, and the golden ratio is algebraically incompatible with Eisenstein lattice snapping.

## Quick Results

### Experiment 1: 3D Snap Topology Comparison (1M vectors)

| Solid | Vertices | Mean Angular Error | Isotropy (CV) |
|-------|----------|-------------------|---------------|
| Dodecahedron | 20 | 18.03° | 0.0048 |
| Icosahedron | 12 | 22.32° | 0.0026 |
| Octahedron | 8 | 28.13° | 0.0016 |
| Cube | 6 | 31.89° | 0.0011 |
| Tetrahedron | 4 | 39.58° | 0.0010 |

**Key finding:** More vertices → lower error (obvious), but **isotropy follows the opposite trend** — fewer directions = more evenly loaded (tetrahedron CV=0.001 vs dodecahedron CV=0.005). The tetrahedron is the most isotropic snap despite being least accurate.

**Eisenstein composition:** Dodecahedron has highest mismatch rate (0.38) with Eisenstein 2D snap, consistent with φ incompatibility.

### Experiment 2: Tensor Consistency (100K matrix pairs)

| Solid | Coxeter h | Relative Error |
|-------|-----------|---------------|
| Dodecahedron | 10 | 0.546 |
| Icosahedron | 10 | 0.658 |
| Cube | 6 | 0.753 |
| Octahedron | 6 | 0.801 |
| Tetrahedron | 4 | 1.100 |

**Key finding:** Coxeter number correlates -0.90 with tensor error. Higher Coxeter → better tensor preservation. Zero preservation rate everywhere (element-wise snap destroys tensor contraction regardless).

**ADE connection:** The Coxeter number h is a real predictor of snap quality for tensor operations.

### Experiment 3: Constraint H¹ by ADE Type

| Lattice | ADE Type | Mean Holonomy |
|---------|----------|--------------|
| A₂ Eisenstein | A₂ (SL, CR) | 1.14 |
| B₃ Cubic | B₃ (CR) | 1.85 |
| A₃ Tetrahedral | A₃ (SL, CR) | 2.32 |
| H₃ Icosahedral | H₃ (NC) | 2.54 |

**Key finding:** Holonomy increases A₂ < B₃ < A₃ < H₃. The simply-laced A₂ (Eisenstein) has the lowest holonomy. The non-crystallographic H₃ has the highest. **Note:** The H¹ fraction via linear algebra was uniformly 1.0 (all cycles non-trivial), so holonomy magnitude is the differentiator, not binary H¹.

### Experiment 4: Eisenstein × Golden Ratio Incompatibility

| Test | A₂×B₃ (cubic) | A₂×H₃ (icosahedral) | Ratio |
|------|---------------|---------------------|-------|
| 3D ring closure | 0.000 | 1.717 | ∞ |
| 5D addition consistency | 0.950 | 3.592 | 3.8× |
| Scalar mult consistency | 1.107 | 0.631 | 0.6× |

**Algebraic proof:** φ ∉ ℤ[ω]. Closest Eisenstein integer to φ is 2 (distance 0.382). The fields ℚ(ω) and ℚ(φ) intersect only at ℚ.

**Key findings:**
1. **Cubic ℤ³ has perfect ring closure** (zero error) — it's a genuine lattice
2. **Icosahedral snap has 16.7% ring closure** — it's NOT a lattice homomorphism
3. **5D addition is 3.8× worse** when composing Eisenstein with icosahedral vs cubic
4. **Scalar multiplication is actually better** for icosahedral (more snap directions absorb scaling)

## ADE Theory Connections

### Confirmed
- ✓ Coxeter number predicts tensor snap quality (r = -0.90)
- ✓ φ ∉ ℤ[ω] — definitive algebraic obstruction
- ✓ Icosahedral/dodecahedral snaps are NOT lattice homomorphisms
- ✓ Eisenstein × cubic composes better than Eisenstein × icosahedral

### Nuanced
- The "H¹ hypothesis" (SL < NSL < NC) didn't hold as a binary test — all lattices showed non-trivial holonomy
- The difference manifests in **holonomy magnitude**, not cohomology rank
- More vertices always gives better angular resolution but worse isotropy

### Open Questions
- Does the Coxeter number → tensor preservation correlation hold for higher-rank tensors?
- Can the holonomy magnitude difference (A₂=1.14 vs H₃=2.54) be proven analytically?
- What happens in 4D (D₄, F₄ root systems)?

## Files

- `solids.py` — Platonic solid vertices and snap functions
- `experiment1_snap_topology.py` — 3D snap topology comparison
- `experiment2_tensor.py` — Tensor contraction consistency
- `experiment3_h1.py` — Constraint H¹ by ADE type
- `experiment4_incompatibility.py` — Eisenstein × golden ratio incompatibility
- `results_exp{1,2,3,4}.json` — Raw results
