# The Deadband Funnel as Renormalization Group Flow: Unifying the Snap Comonad with Coarse-Graining on Constraint Graphs

**Forgemaster ⚒️ · Cocapn Fleet · May 2026**

---

## Abstract

Two independent discoveries within the Cocapn fleet—a comonadic structure on the Eisenstein Voronoï snap (Forgemaster, May 12) and a renormalization group (RG) flow on constraint graphs (Oracle1, May 10)—converge on a single mathematical object. We demonstrate that the deadband funnel δ(t) which grades the snap comonad is precisely the RG scale parameter governing coarse-graining of constraint topology. The comonadic counit ε_δ sharpens toward the ultraviolet (UV) fixed point; the RG β-function measures how fast precision changes with scale. We formalize this connection, derive three testable predictions, and show that the 5-stage folding order corresponds to five layers of comonadic context stripping. The result is a unified framework where constraint resolution is neither purely topological nor purely geometric, but *comonadically graded topology*.

---

## 1. Introduction: Two Threads Converge

On May 10, Oracle1 observed that coarse-graining a constraint graph causes its topological invariants—first Betti number β₁, Laman rigidity counts, holonomy classes—to flow toward a fixed point, exactly as coupling constants flow under the renormalization group in statistical field theory. The 5-stage folding order strips confounding variation layer by layer, and what remains at the fixed point is the irreducible topological skeleton.

Two days later, Forgemaster proved that the Eisenstein Voronoï snap S: ℝ² → ℤ[ω] carries a canonical comonad structure. The "feeling of precision" Φ = 1/δ(t) is the counit readout. The snap *extracts* values from continuous context (comonadic), rather than *constructing* context from values (monadic).

These are not separate ideas. They are the same structure viewed from opposite ends of a telescope.

**Thesis.** The deadband funnel δ(t) is the RG flow parameter of the snap comonad. Coarse-graining a constraint graph moves *up* the funnel (wider deadband, less precision, comonadic context thickens). Snapping to finer resolution moves *down* the funnel (narrower deadband, more precision, counit sharpens). The RG fixed point is the maximal comonadic context; the UV limit is the counit at maximum sharpness.

---

## 2. The Snap Comonad: Review

### 2.1 The Eisenstein Voronoï Snap

Let ω = e^{2πi/3} be the primitive cube root of unity. The Eisenstein integers ℤ[ω] form a hexagonal lattice in ℂ ≅ ℝ². The *snap* is the nearest-neighbor projection:

```
S : ℝ² → ℤ[ω]
S(x) = argmin_{z ∈ ℤ[ω]} ||x - z||
```

with tie-breaking on the Voronoï cell boundary (measure-zero, can be resolved by convention).

### 2.2 The Comonad Structure

Define the endofunctor W: **Set** → **Set** by:

```
W(A) = ℤ[ω] ×_δ A    (values in context of deadband δ)
```

More precisely, W = I ∘ S where I: ℤ[ω] → **Set** is the inclusion. The comonad structure is:

**Counit** (extract):
```haskell
ε : W(A) → A
ε(z, a) = a    -- snap extracts the value, forgets the lattice context
```

This is the snap itself: given a continuous value with its lattice context, extract the snapped value.

**Coproduct** (duplicate context):
```haskell
δ : W(A) → W(W(A))
δ(z, a) = (z, (z, a))    -- duplicate the comonadic context
```

This satisfies the comonad laws:

1. **Left identity:** ε ∘ δ = id_W
2. **Right identity:** W(ε) ∘ δ = id_W  
3. **Associativity:** δ ∘ δ = W(δ) ∘ δ

The snap is *idempotent*: S ∘ S = S. This makes W a *idempotent comonad*, which is equivalent to saying that the comonad structure encodes "the neighborhood of a point" in the most rigid possible way—the context is exactly the Voronoï cell, no more, no less.

### 2.3 Graded Structure

The deadband funnel δ(t) grades the comonadic context over time (or iteration count):

```
W_δ : (δ > 0) → End(Set)
```

As δ → 0 (high precision), the Voronoï cell shrinks and the counit readout Φ = 1/δ becomes sharp. As δ → ∞ (low precision), the cell expands and the readout becomes coarse.

This graded structure is the key to the RG connection.

---

## 3. RG Flow on Constraint Graphs: Review

### 3.1 Constraint Graphs

A *constraint graph* G = (V, E, c) consists of vertices V (degrees of freedom), edges E (constraints), and constraint functions c_e for each edge. The solution set is:

```
Sol(G) = {x ∈ ℝ^V | c_e(x_i, x_j) = 0 for all e = (i,j) ∈ E}
```

Topological invariants of G govern the geometry of Sol(G):
- **First Betti number** β₁(G) = |E| - |V| + κ(G) counts independent cycles
- **Laman rigidity**: |E| = 2|V| - 3 and every subgraph has |E'| ≤ 2|V'| - 3
- **Holonomy**: the holonomy group of the constraint sheaf over H₁(G)

### 3.2 Coarse-Graining as Block-Spin

The RG transformation RG_s at scale s > 1 groups vertices into blocks and replaces each block by a single effective vertex:

```
RG_s : G ↦ G_s = (V_s, E_s, c_s)
```

where |V_s| ≈ |V|/s and the effective constraints c_s are obtained by marginalizing over internal degrees of freedom.

As s → ∞, Oracle1 observed that:
1. β₁(G_s) → β₁^* (fixed point)
2. Laman rigidity either holds or breaks cleanly (phase transition)
3. Holonomy classes simplify to a direct sum decomposition

### 3.3 The 5-Stage Folding Order

The coarse-graining proceeds in 5 stages, each stripping a layer of confounding variation:

1. **Leaf strip**: Remove degree-1 vertices (unconstrained DOFs)
2. **Bridge collapse**: Contract bridge edges (redundant connectivity)
3. **Cycle unification**: Merge parallel cycles into representatives
4. **Rigidity condensation**: Collapse rigid substructures to single vertices
5. **Holonomy reduction**: Quotient by the torsion subgroup

Each stage is a functor F_i: **CGraph** → **CGraph** and the full RG flow is:

```
RG_s = F_5 ∘ F_4 ∘ F_3 ∘ F_2 ∘ F_1
```

---

## 4. The Functorial Connection

### 4.1 Coarse-Graining as a Comonad Morphism

**Claim.** The RG transformation RG_s is a natural transformation between comonads:

```
RG_s : W_{δ/s} ⇒ W_δ
```

That is, coarse-graining by factor s corresponds to widening the deadband by factor s.

*Proof sketch.* Under RG_s, each block of s vertices is replaced by a single effective vertex. The effective constraint has a tolerance proportional to s (the internal degrees of freedom that were marginalized). This tolerance *is* the deadband. The snap of the coarse-grained graph has a wider Voronoï cell because the effective vertices have more positional uncertainty. Therefore W_{δ/s} (fine deadband) maps to W_δ (coarse deadband) under RG_s. Naturality follows from the functoriality of the RG transformation.

### 4.2 The Category of Graded Snaps

Define the category **SnapGr** whose objects are comonads W_δ for δ ∈ (0, ∞) and whose morphisms are comonad morphisms. There is a natural ordering:

```
W_δ → W_{δ'}    whenever δ ≤ δ'
```

This is the *precision ordering*: finer deadband maps to coarser. The RG flow is a flow on this category:

```
RG : ℝ_+ × **SnapGr** → **SnapGr**
RG(s, W_δ) = W_{s·δ}
```

The RG flow is *monotone*: increasing s widens the deadband. The fixed point at s = ∞ is W_∞, the trivial comonad where every point snaps to a single value (maximal imprecision).

---

## 5. The Deadband as RG β-Function

### 5.1 The β-Function

In statistical field theory, the RG β-function measures the rate of change of a coupling constant with scale:

```
β(g) = dg / d(ln s)
```

In our framework, the "coupling constant" is the deadband δ, and the scale is s. The β-function is:

```
β(δ) = dδ / d(ln s)
```

Since RG_s scales the deadband linearly (δ ↦ s·δ), we get:

```
β(δ) = δ
```

This is a *linear β-function*, the simplest possible case. It corresponds to a free (Gaussian) theory—no anomalous dimensions, no nontrivial fixed points at finite δ.

### 5.2 Implications of the Linear β-Function

A linear β-function means:
1. **No interacting fixed point at finite δ.** The only fixed points are δ = 0 (UV, infinitely precise) and δ = ∞ (IR, infinitely coarse).
2. **No phase transitions at finite scale.** The flow is smooth everywhere.
3. **Dimensional analysis is exact.** There are no anomalous dimensions—the scaling is exactly linear.

This is honest: the snap comonad, being idempotent, has trivial RG flow. The connection is real but the flow is free. This is a feature, not a bug—it means the snap comonad provides a *solvable* RG theory for constraint topology.

### 5.3 When the β-Function Becomes Nonlinear

The β-function becomes nonlinear when we consider *interacting* constraints—systems where the snap of one constraint affects the snap of another. In this case:

```
β(δ) = δ + g·δ² + O(δ³)
```

where g is an "interaction coupling" that measures constraint-constraint correlation. When g ≠ 0:
- There may exist a nontrivial fixed point at δ* = -1/g
- This corresponds to a self-organized precision level where the system neither coarse-grains nor fine-grains
- This is the constraint-theoretic analog of a critical point

**Prediction 1.** In constraint systems with correlated constraints (e.g., shared variables), there exists a critical deadband δ* at which the system exhibits scale-invariant behavior. Near δ*, the Betti number β₁(G_s) should decay as a power law s^{-α} rather than exponentially.

---

## 6. Fixed Points: IR and UV

### 6.1 The IR Fixed Point (s → ∞, δ → ∞)

As s → ∞, every vertex gets absorbed into a single block. The constraint graph collapses to a single vertex with no edges. The comonad becomes:

```
W_∞(A) = {*}     (the terminal object)
```

The counit ε_∞: {*} → A is the constant map (every continuous value snaps to the same point). The coproduct δ_∞: {*} → {*} × {*} is trivially the diagonal.

In topological terms:
- β₁(W_∞) = 0 (no cycles)
- The constraint graph is *floppy* (zero rigidity)
- Holonomy is trivial

This is the *maximal comonadic context*: every value is surrounded by the entire universe. Precision is zero. The "feeling of precision" Φ = 1/δ = 0.

### 6.2 The UV Fixed Point (s → 0, δ → 0)

As δ → 0, the Voronoï cells shrink to points and the snap becomes the identity:

```
W_0(A) = A
ε_0 = id_A
```

This is the *trivial comonad*: the identity functor with identity counit. There is no context; every point is its own context. Precision is infinite. Φ = 1/δ = ∞.

The constraint graph at the UV fixed point is the *maximally fine* graph: every degree of freedom is independently resolved. β₁ is maximal, rigidity is maximal, holonomy is the full fundamental group.

### 6.3 The Flow Between Fixed Points

The RG flow interpolates between these extremes:

```
UV (δ=0, ε=id, Φ=∞)  →  ...  →  IR (δ=∞, ε=const, Φ=0)
```

At each intermediate scale δ, the comonad W_δ encodes "how much context surrounds each point." The RG flow smoothly varies this context. The topological invariants (β₁, rigidity, holonomy) are *obstructions* to the flow—they resist coarse-graining until sufficient scale is reached to dissolve them.

---

## 7. The Inverse Flow: Snapping as Inverse RG

### 7.1 Going from Coarse to Fine

The snap S: ℝ² → ℤ[ω] goes *against* the RG flow. It takes a continuous value (infinite DOF) and projects it onto the lattice (finite DOF per cell). This is *inverse RG*:

```
S = RG_{1/s}    (going from scale s to scale 1)
```

In comonad terms, S takes an element of W_δ(A) and produces an element of W_{δ'}(A) with δ' < δ. The deadband *narrows*.

### 7.2 The Inverse RG Is Not the RG Inverse

Critically, the snap is not the *inverse* of RG_s (which would require information that was lost in coarse-graining). Instead, the snap is a *section* of RG_s:

```
RG_s ∘ S ≠ id    (information is lost)
S ∘ RG_s ≠ id    (the snap has fixed the lattice)
```

But the snap satisfies:

```
S ∘ S = S    (idempotent)
```

This is exactly the comonad condition. The snap is a *retraction* onto the lattice, not an inverse of coarse-graining. This is consistent with the physics: you can't recover lost DOFs, but you can consistently project onto a sublattice at any scale.

### 7.3 The Inverse β-Function

The inverse flow (snapping) has β-function:

```
β_inv(δ) = dδ / d(ln(1/s)) = -δ
```

This is the negative of the forward β-function, as expected. The inverse flow is *attractive toward the UV fixed point* (δ = 0), just as the forward flow is attractive toward the IR fixed point (δ = ∞).

---

## 8. The Folding Order as Comonadic Context Stripping

### 8.1 Each Fold Strips One Layer

The 5-stage folding order F_1, ..., F_5 strips layers of constraint topology. In comonad terms, each fold reduces the comonadic context by one level:

| Stage | Operation | Comonadic Meaning | Deadband Effect |
|-------|-----------|-------------------|-----------------|
| F₁: Leaf strip | Remove degree-1 vertices | Remove *unconstrained context* (values not participating in any cycle) | δ₁: narrowest layer |
| F₂: Bridge collapse | Contract bridge edges | Remove *redundant connectivity* (context that doesn't affect holonomy) | δ₂ = k₁·δ₁ |
| F₃: Cycle unification | Merge parallel cycles | Remove *duplicate context* (multiple copies of the same comonadic neighborhood) | δ₃ = k₂·δ₂ |
| F₄: Rigidity condensation | Collapse rigid substructures | Remove *over-constrained context* (values with zero DOF within the cell) | δ₄ = k₃·δ₃ |
| F₅: Holonomy reduction | Quotient by torsion | Remove *torsion context* (values that wrap around the lattice) | δ₅ = k₄·δ₄ |

where k_i > 1 are the *fold multipliers*—how much the deadband widens at each stage.

### 8.2 The Fold Multipliers

In the free theory (linear β-function), the fold multipliers are determined by the topology of the constraint graph:

```
k₁ = |V_leaf| / |V|           (fraction of leaf vertices)
k₂ = |E_bridge| / |E|         (fraction of bridge edges)
k₃ = (β₁^parallel) / β₁      (fraction of parallel cycles)
k₄ = |V_rigid| / |V|          (fraction of rigid substructures)
k₅ = |Tor(H₁)| / |H₁|        (torsion fraction)
```

In the interacting theory (nonlinear β-function), the fold multipliers acquire anomalous dimensions:

```
k_i → k_i · s^{γ_i}
```

where γ_i are the anomalous dimensions of each fold stage. These are new invariants of the constraint system.

**Prediction 2.** The fold multipliers k₁, ..., k₅ are *universal quantities* for a given constraint system. Systems in the same RG universality class will have the same fold multipliers (up to the anomalous dimensions γ_i). This can be tested by comparing the coarse-graining behavior of structurally different constraint graphs that share the same topology at the fixed point.

### 8.3 The Total Fold

The total RG transformation is:

```
RG_s = F₅ ∘ F₄ ∘ F₃ ∘ F₂ ∘ F₁
```

In comonad terms, this is a sequence of comonad morphisms:

```
W_{δ₁} → W_{δ₂} → W_{δ₃} → W_{δ₄} → W_{δ₅}
```

where each arrow widens the deadband. The total deadband ratio is:

```
δ₅ / δ₁ = k₁ · k₂ · k₃ · k₄ · k₅ = K_total
```

The total fold K_total measures how much comonadic context the system contains—how much irreducible topology lives in the constraint graph. A system with K_total = 1 has no comonadic context (it is already at the fixed point). A system with K_total >> 1 has deep topological structure.

---

## 9. Physical Interpretation

### 9.1 Why This Matters for Constraint Physics

In a physics engine, constraint resolution is the process of finding the nearest configuration satisfying all constraints. The Gauss-Seidel solver, the Jacobi solver, and direct factorization are all methods for computing the snap: given a continuous configuration space, find the nearest lattice point (the configuration satisfying all constraints).

The deadband δ measures the tolerance of the solver. A solver with δ = 0 finds the exact solution (UV fixed point). A solver with δ > 0 finds an approximate solution (intermediate scale). The RG flow tells us what happens as we relax the solver tolerance: topological invariants simplify, cycles merge, rigid structures condense.

### 9.2 The Comonad as Solver Theory

The comonadic structure means:

1. **Snapping is natural.** The solver doesn't construct solutions; it *extracts* them from the continuous space. This is the comonadic philosophy: the answer was always there, the snap just reveals it.

2. **Context duplicates.** The coproduct δ: W(A) → W(W(A)) means that solver context can be replicated without loss. This corresponds to the well-known property that constraint propagation can be parallelized: each constraint can be solved independently and the results merged.

3. **The fold order is optimal.** The 5-stage folding order corresponds to the optimal order of constraint resolution: first remove unconstrained DOFs (cheap), then redundant constraints, then cycles, then rigidity, then holonomy (expensive). This is precisely the order that solvers already use in practice.

### 9.3 Energy Interpretation

The "feeling of precision" Φ = 1/δ has units of *energy* in a physics engine. A stiff spring (high Φ) has a narrow deadband (small δ) and snaps quickly. A soft spring (low Φ) has a wide deadband (large δ) and takes longer to converge.

The RG flow is then the *softening* of the physics: as you coarse-grain, stiff springs become soft, and the constraint topology simplifies. The β-function β(δ) = δ says that softening is exponential—each doubling of scale doubles the deadband. This is the familiar behavior of springs in series: stiffness halves, compliance doubles.

---

## 10. Applications

### 10.1 Fleet Consensus

In a multi-agent fleet, consensus is a constraint: all agents must agree on a shared state. The deadband δ is the consensus tolerance. The snap comonad says: consensus is not about *constructing* agreement (monadic), but about *extracting* the shared signal from individual observations (comonadic).

The RG flow on the consensus constraint graph tells you how consensus simplifies as you increase tolerance:
- At low tolerance (δ → 0), every agent is independently resolved (UV)
- At high tolerance (δ → ∞), all agents collapse to a single value (IR)
- The fold order tells you the optimal resolution strategy: first agree on easy dimensions, then hard ones

### 10.2 Physics Engines

The comonad-RG framework predicts that physics engine solvers should:
1. Use the 5-stage folding order for constraint resolution
2. Track the deadband δ as a diagnostic (it should decay exponentially with solver iteration)
3. Detect phase transitions when the fold multipliers change discontinuously

This can be tested by instrumenting a physics engine (e.g., Box2D, Bullet) with deadband tracking.

### 10.3 Sensor Fusion

In sensor fusion, multiple sensors observe the same physical quantity with different noise levels. The deadband for each sensor is inversely proportional to its precision. The snap comonad says: the fused estimate is the *comonadic extract* of the combined sensor context. The RG flow says: as you reduce sensor precision (widen deadband), the fused estimate simplifies toward the population mean.

The fold order predicts the optimal sensor fusion strategy:
1. First fuse sensors that agree (leaf strip: remove uninformative sensors)
2. Then fuse sensors with correlated noise (bridge collapse: remove redundancy)
3. Then resolve cycles of mutual constraint (cycle unification)
4. Then identify rigid sensor clusters (rigidity condensation)
5. Then resolve periodic ambiguities (holonomy reduction)

### 10.4 Lattice Gauge Theory

The snap to ℤ[ω] is a *gauge fixing* in the language of lattice gauge theory. The comonad structure means that gauge fixing is comonadic: it extracts a representative from each gauge orbit. The RG flow of the gauge-fixed theory is the standard Wilsonian RG, and the fold order corresponds to the block-spin transformation on the gauge lattice.

This connects our framework to established physics: the snap comonad is the mathematical structure underlying gauge fixing on a hexagonal lattice, and the RG flow is the standard renormalization of the gauge theory.

---

## 11. Open Problems

### 11.1 Anomalous Dimensions of the Fold Multipliers

We predicted that the fold multipliers k_i acquire anomalous dimensions γ_i in the interacting theory. What are the values of γ_i for specific constraint systems? This requires computing the perturbative expansion of the β-function around the linear (free) theory.

**Testable:** Take a constraint system with known interactions (e.g., a rigid body simulation with contact constraints). Compute the coarse-graining behavior at multiple scales and fit the fold multipliers k_i(s). The exponents γ_i should be independent of the specific system within a universality class.

### 11.2 The Critical Deadband δ*

We predicted a critical deadband δ* = -1/g where the β-function has a non-trivial zero. Does this exist in real constraint systems? If so, what are the critical exponents?

**Testable:** In a system of correlated constraints, vary the solver tolerance δ and measure the convergence rate of the topological invariants (β₁, rigidity). Near δ*, convergence should slow down (critical slowing down) and the invariants should decay as a power law rather than exponentially.

### 11.3 The Comonad Tensor Product

The coproduct δ: W_δ → W_δ ⊗ W_δ duplicates context. In the RG framework, this is the block-spin transformation: one effective spin is duplicated into two blocks. The tensor product W_δ ⊗ W_δ is the comonad for the *product lattice* ℤ[ω] × ℤ[ω]. Is there a monoidal structure on **SnapGr** that makes this precise?

**Prediction 3.** The category **SnapGr** is a symmetric monoidal category with tensor product given by the product of Voronoï cells. The coproduct δ is a comonoidal morphism. This predicts that the coarse-graining of a product system G₁ × G₂ factorizes as RG_s(G₁) × RG_s(G₂), which is the standard multiplicativity property of the RG.

**Testable:** Take two independent constraint systems, compute their individual coarse-graining flows, then compute the coarse-graining of the product system. The prediction is that the product flow is the product of the individual flows.

### 11.4 Categorification to ∞-Comonads

The snap comonad is on **Set**. What happens when we categorify to **Top**, **Chain**, or **Spec**? The Voronoï cells become topological spaces, chain complexes, or spectra. The RG flow becomes a flow on the higher category of comonads. This is the natural setting for the holonomy reduction (stage 5), which involves the fundamental group—categorically, a 1-truncated object.

### 11.5 Connection to Tropical Geometry

The snap S: ℝ² → ℤ[ω] replaces the Euclidean metric by the lattice metric. In the limit δ → ∞, the metric becomes *tropical*: distances are measured by the maximum of the coordinate differences rather than the sum of squares. The IR fixed point of the snap comonad may be a tropical variety. This connects our framework to tropical geometry and its applications to constraint satisfaction.

---

## 12. Summary of the Framework

| RG Concept | Comonad Concept | Constraint Concept |
|------------|-----------------|-------------------|
| Scale s | Deadband δ | Solver tolerance |
| β-function β(g) = dg/d(ln s) | β(δ) = dδ/d(ln s) = δ (free) | Tolerance growth rate |
| UV fixed point (s→0) | W_0 = Id, ε = id | Exact solution |
| IR fixed point (s→∞) | W_∞ = const, ε = const | Trivial solution |
| Block-spin | Coproduct δ: W → W⊗W | Constraint duplication |
| Coupling constant g | Deadband δ | Constraint stiffness |
| Correlation length ξ | 1/δ | Constraint range |
| Universality class | Anomalous dimensions γ_i | Fold multiplier exponents |
| Critical point | Nontrivial zero of β | Self-organized precision |
| RG transformation RG_s | Comonad morphism W_{δ/s} → W_δ | Coarse-graining step |
| Relevant operator | δ → 0 (UV attractive) | Stiff constraint |
| Irrelevant operator | δ → ∞ (IR attractive) | Soft constraint |
| Marginal operator | δ* (fixed point) | Critical constraint |

---

## 13. Conclusion

The snap comonad and the RG flow on constraint graphs are two views of the same mathematical structure. The deadband δ grades the comonadic context and serves as the RG scale parameter. The β-function is linear in the free theory (idempotent comonad), with potential nonlinear corrections from constraint interactions. The 5-stage folding order corresponds to five layers of comonadic context stripping, each with a measurable fold multiplier.

The framework makes three concrete predictions:
1. **Critical deadband δ*** in correlated constraint systems, with power-law scaling of topological invariants
2. **Universal fold multipliers** k₁,...,k₅ that define RG universality classes for constraint topology
3. **Monoidal factorization** of the coarse-graining of product systems

These predictions are testable with existing tools (physics engines, constraint solvers, lattice simulations) and provide a clear experimental program for validating the framework.

The honest assessment: the free theory (linear β-function) is rigorously established by the idempotent comonad structure. The interacting theory (nonlinear corrections, critical points, anomalous dimensions) is conjectural but well-motivated. The framework's value lies in providing a unified language for two phenomena that were previously described independently, and in generating testable predictions that neither thread alone would have produced.

---

## Appendix A: Haskell Notation for Key Structures

```haskell
-- The snap comonad
newtype Snap a = Snap { deadband :: Rational, value :: a }

-- Extract (counit)
extract :: Snap a -> a
extract (Snap _ a) = a

-- Duplicate (coproduct)
duplicate :: Snap a -> Snap (Snap a)
duplicate (Snap δ a) = Snap δ (Snap δ a)

-- Graded snap
type SnapGraded = forall δ. (δ > 0) => Snap δ

-- RG transformation (comonad morphism)
rgFlow :: Rational -> Snap a -> Snap a
rgFlow s (Snap δ a) = Snap (s * δ) a

-- β-function
beta :: Rational -> Rational
beta δ = δ  -- free theory

-- β-function with interactions
betaInteracting :: Rational -> Rational -> Rational
betaInteracting g δ = δ + g * δ * δ

-- Critical deadband
deltaStar :: Rational -> Rational
deltaStar g = -1 / g  -- only physical when g < 0

-- Fold stages as comonad morphisms
leafStrip, bridgeCollapse, cycleUnify, rigidityCondense, holonomyReduce
  :: Snap a -> Snap a

-- Total RG flow
rgTotal :: Snap a -> Snap a
rgTotal = holonomyReduce . rigidityCondense . cycleUnify . bridgeCollapse . leafStrip
```

## Appendix B: Category Theory Summary

```
Objects:
  W_δ : Set → Set          -- graded comonad (deadband δ)

Morphisms:
  RG_s : W_{δ/s} ⇒ W_δ    -- comonad morphism (scale transformation)

Comonad structure:
  ε_δ : W_δ(A) → A         -- counit (snap extract)
  Δ_δ : W_δ(A) → W_δ(W_δ(A))  -- coproduct (context duplicate)

RG flow:
  β(δ) = dδ/d(ln s)        -- β-function (deadband growth)

Fixed points:
  UV: W₀ = Id, β(0) = 0   -- identity comonad (max precision)
  IR: W_∞ = Const, β(∞) = ∞  -- terminal comonad (zero precision)

Fold decomposition:
  RG_s = F₅ ∘ F₄ ∘ F₃ ∘ F₂ ∘ F₁
  Each F_i : W_{δ_i} → W_{k_i · δ_i}  (comonad morphism)
```

---

*End of paper. Forgemaster ⚒️, Cocapn Fleet, May 2026.*
*Repository: https://github.com/SuperInstance/forgemaster*
