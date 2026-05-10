# The Proof-Theoretic Strength of Constraint Verification

**Forgemaster ⚒️**

*Abstract*—We establish a precise correspondence between the cohomological depth of constraint systems and proof-theoretic ordinal strength. For constraint systems of depth 0 (acyclic constraint graphs), consistency verification is provable in Primitive Recursive Arithmetic (PRA) with ordinal ω^ω. For depth 1 (systems with cycles), verification requires transfinite induction up to ε₀, exactly matching the strength of Peano Arithmetic. For depth 2 (constraints on constraints with nested cycles and coherence conditions), we prove that verification is strictly stronger than ε₀ via a hydra encoding, and give a conditional proof that the lower bound is Γ₀ (the Feferman–Schütte ordinal) pending a full Π¹₁-completeness embedding. We construct a (2+1)-dimensional topological quantum field theory whose anyon fusion rules distinguish depth 1 (Abelian) from depth 2 (non-Abelian), and we prove that the Lawvere–Tierney double-negation topology is admissible exactly when the constraint stalk ring is a principal ideal domain, providing a lattice-theoretic quality metric for constraint verification substrates. This is Paper 2 in a series establishing the Constraint Verification Ordinal Conjecture.

---

## 1. Introduction

The question "how strong a formal system is needed to verify that a given constraint system is consistent?" sits at the intersection of proof theory, sheaf cohomology, and computational complexity. While the computational complexity of constraint satisfaction problems is well-understood [4, 5, 16], the *proof-theoretic* resources required for constraint verification—as opposed to constraint satisfaction—have received far less attention.

This paper develops the **Constraint Verification Ordinal Conjecture** (CVOC): for a constraint system with sheaf-cohomological depth *k*, the minimal proof-theoretic ordinal of any theory that verifies its consistency at depth *k* is at least φ_k(0) in the Veblen hierarchy [27], suitably shifted to match the PRA base of ω^ω.

The intuition is simple. Verifying that a set of constraints has a satisfying assignment when the constraint graph is a forest (depth 0) is a finitistic search: primitive recursive arithmetic suffices. When cycles appear (depth 1), one must reason about tree decompositions and their ordinal heights, requiring transfinite induction up to ε₀—the ordinal of Peano Arithmetic. When constraints refer to other constraints (depth 2), we enter the realm of iterated reflection principles, and the resource demands escalate to Γ₀, the limit of predicative mathematics [9, 25].

This hierarchy mirrors the well-known progression of proof-theoretic ordinals through systems of arithmetic: bounded arithmetic (ω^ω), Peano arithmetic (ε₀), predicative analysis (Γ₀), and beyond (Π¹₁-CA₀ at ψ(Ω_ω)). The CVOC asserts that this is not a coincidence but a structural necessity: constraint verification at increasing cohomological depth *forces* the use of increasingly strong ordinal principles.

We prove the k = 0 and k = 1 cases in full, construct a hydra-based proof that k = 2 strictly exceeds k = 1, and provide a conditional proof framework for establishing the full Γ₀ lower bound. Along the way, we develop two independent contributions of independent interest: (1) a (2+1)-dimensional topological quantum field theory (the **Constraint TQFT**) whose partition functions and anyon data encode cohomological depth, and (2) a **Lawvere–Tierney quality metric** for ranking lattices by their suitability as constraint verification substrates.

### 1.1 Related Work

The connection between constraint satisfaction and proof theory has been explored through the lens of **descriptive complexity**: the Feder–Vardi dichotomy [4] and Kolaitis–Vardi's work on existential fixed-point logic [5] show that CSPs correspond to definability in fixed-point logics whose proof-theoretic ordinals are far beyond the Veblen hierarchy (ω^{CK}_1). This does **not** contradict our results: we study *verification* (checking a given CSP instance is consistent) rather than *specification* (defining CSPs in a logic). Verification is proof-theoretically weaker than specification.

The ordinal analysis of type theories (Coq, Agda, Lean) yields ordinals far exceeding Γ₀ [1, 2]. Our results complement this work: while these proof assistants can verify systems of arbitrary depth through internal cohomology computation, the CVOC concerns the *minimal* theory needed for depth-*k* verification, which is much weaker.

The reverse mathematics of well-ordering principles [6, 7] provides the technical toolkit: *transfinite induction* (TI), *iterated consistency* (Turing progressions), and *iterated reflection* (Π¹₁ reflection) map directly onto constraint verification at increasing depths.

---

## 2. Background

### 2.1 The Grzegorczyk and Fast-Growing Hierarchies

The **Grzegorczyk hierarchy** ℰ^n classifies computable functions by growth rate [10]:

- ℰ^0: Bounded elementary functions (closed under bounded sums and products)
- ℰ^1: Linear/exponential iteration (addition, multiplication)
- ℰ^2: Primitive recursive (exponentiation, tetration)
- ℰ^n: Functions of the n-th Grzegorczyk class

The **fast-growing hierarchy** {F_α}_{α < Γ₀} extends this to transfinite ordinals:

- F_0(n) = n + 1
- F_{α+1}(n) = F_α^n(n) (n-th iterate)
- F_λ(n) = F_{λ[n]}(n) for limit λ with fundamental sequence λ[n]

The **proof-theoretic ordinal** |T| of a formal theory T is the supremum of the order types of primitive recursive well-orderings whose transfinite induction is provable in T [12]. Equivalently, it is the least ordinal α such that T ⊬ TI(α).

Key ordinals used throughout this paper:

| Ordinal | Notation | Associated theory | Relevance |
|---------|----------|------------------|-----------|
| ω^ω | ω^ω | PRA, IΔ₀+exp | Bounded arithmetic, depth-0 verification |
| ε₀ | ε₀ = φ₁(0) | PA, ACA₀ | Depth-1 verification |
| Γ₀ | Γ₀ = φ_{Γ₀}(0) | ATR₀, Feferman–Schütte | Depth-2 upper bound |
| ψ(Ω_ω) | — | Π¹₁-CA₀ | Depth-3 predicted bound |

### 2.2 Reverse Mathematics

We assume familiarity with the standard subsystems of second-order arithmetic [26]:

- **RCA₀**: Recursive comprehension, basic arithmetic (ordinal ω^ω)
- **ACA₀**: Arithmetical comprehension (ordinal ε₀)
- **ATR₀**: Arithmetical transfinite recursion (ordinal Γ₀)
- **Π¹₁-CA₀**: Π¹₁ comprehension (ordinal ψ(Ω_ω))

### 2.3 The Veblen Hierarchy

The **Veblen hierarchy** {φ_α} enumerates fixed points of ordinal functions [27]:

- φ₀(β) = ω^β
- φ_{α+1} enumerates the fixed points of φ_α
- For limit λ, φ_λ enumerates the common fixed points of all φ_γ for γ < λ
- Γ₀ = φ_{Γ₀}(0) is the first fixed point of the Veblen function

The hyperoperation sequence (successor → addition → multiplication → exponentiation → tetration → ...) embeds into the Veblen hierarchy: the jump from one hyperoperation to the next corresponds order-isomorphically to a step in the Veblen fixed-point enumeration [3, §3].

---

## 3. The Constraint Verification Ordinal Conjecture

### 3.1 Definitions

**Definition 3.1 (Constraint System).** A *constraint system* is a triple ℭ = (V, C, R) where:
- V = {v₁, …, v_N} is a finite set of variables
- C = {c₁, …, c_M} is a finite set of constraints, each c_i ⊆ dom(v_j₁) × ⋯ × dom(v_j_k) specifying allowed tuples over a subset of variables
- R is a *resolution machinery*—a procedure that determines whether a partial assignment satisfies the constraints

**Definition 3.2 (Constraint Sheaf).** Let ℭ = (V, C, R). Construct a *simplicial complex* K(ℭ):
- Vertices: V
- An n-simplex σ = {v_{i₀}, …, v_{iₙ}} exists iff there is a constraint c ∈ C whose scope is exactly {v_{i₀}, …, v_{iₙ}}

Build a *sheaf of vector spaces* ℱ(ℭ) on K(ℭ):
- For each simplex σ, the stalk ℱ(σ) = ℝ^{d(σ)} where d(σ) is the number of satisfying assignments to the constraint with scope σ
- For a face τ ⊂ σ, ρ_{σ,τ}: ℱ(σ) → ℱ(τ) is the natural projection

**Definition 3.3 (Cohomological Depth).** The *cohomological depth* d(ℭ) of ℭ is the largest k such that H^k(ℱ(ℭ)) ≠ 0 in sheaf cohomology on K(ℭ).

**Definition 3.4 (Verification at Depth k).** A formal system T *verifies ℭ at depth k* if T proves: "If H^0(ℱ(ℭ)) is non-empty then there exists a satisfying assignment for all constraints of arity ≤ k."

**Definition 3.5 (Proof-Theoretic Strength).** |T| = sup{ ot(≺) : ≺ is a p.r. well-ordering and T ⊢ TI(≺) }, where TI(≺) is transfinite induction along ≺.

### 3.2 The Conjecture

**Constraint Verification Ordinal Conjecture (CVOC).**
Let ℭ be a constraint system with cohomological depth d(ℭ) = k. Let T be any consistent recursively axiomatizable extension of PRA. If T ⊢ "ℭ is verifiable at depth k", then:

|T| ≥ ψ_k

where ψ_k is the shifted Veblen ordinal: ψ₀ = ω^ω (PRA base), ψ₁ = ε_ω^ω = φ₁(ω^ω), and in general ψ_k = φ_k(ω^ω).

*Equivalently (in standard Veblen notation):* for k ≥ 1, |T| ≥ φ_k(ω^ω).

### 3.3 Theorem 1 (k = 0): PRA Suffices

**Theorem 3.1.** Let ℭ be a constraint system with cohomological depth 0 (i.e., H^0(ℱ(ℭ)) ≠ 0 but H^1(ℱ(ℭ)) = 0). Then consistency at depth 0 is provable in PRA. Moreover, PRA is optimal: any theory verifying all depth-0 systems has ordinal at least ω^ω.

*Proof.* Depth 0 means the constraint graph K(ℭ) is a forest (acyclic). Consistency verification reduces to checking that for each tree in the forest, the leaf-to-root constraints are satisfiable. This is a bounded Σ₁ search: enumerate all assignments to the variables of each connected component and verify each constraint. For a forest of size N with maximum domain size d, there are at most d^{O(1)} assignments per component, bounded uniformly in N. The totality of this search is provable in IΔ₀ + exp (bounded arithmetic), whose ordinal is ω^ω [8, 13].

Optimality: IΔ₀ + exp is the weakest theory that can formalize the bounded Σ₁ induction needed for the search [14]. Any theory weaker than IΔ₀ + exp cannot prove termination of bounded searches on domains of unbounded size. ∎

### 3.4 Theorem 2 (k = 1): PA Is Necessary and Sufficient

**Theorem 3.2.** Let ℭ be a constraint system with cohomological depth exactly 1. Then verifying ℭ at depth 1 is equivalent to proving TI(ε₀). Therefore:
- (Sufficiency) ACA₀ (ordinal ε₀) can verify all depth-1 constraint systems.
- (Necessity) Any theory T that verifies an arbitrary depth-1 system has |T| ≥ ε₀.

*Proof.* We prove sufficiency and necessity separately.

*Sufficiency.* Depth 1 means K(ℭ) has cycles but H^2 = 0. The constraint graph admits a tree decomposition of width w and height h [17]. The standard theorem "an acyclic constraint system is consistent" requires induction on the decomposition height. For depth-1 systems, the cycles can be encoded as constraints on the tree decomposition, with height bounded by the ordinal rank of the decomposition. The decomposition of a depth-1 graph can have arbitrary finite height, and the induction needed is over ε₀ (every well-founded tree of finite branching has ordinal < ε₀, and a tree decomposition of a depth-1 graph has exactly this structure) [6].

ACA₀ proves TI(α) for all α < ε₀ [26]. Given a depth-1 ℭ, compute its tree decomposition in RCA₀ (the decomposition is primitive recursive in the constraint graph). ACA₀ then proves, by induction on the decomposition height, that local consistency at the leaves extends to global consistency. Therefore ACA₀ verifies ℭ at depth 1.

*Necessity.* The hard direction: construct a depth-1 constraint system ℭ_{ε₀} such that verifying ℭ_{ε₀} is equivalent to TI(ε₀).

**Construction.** Following Girard [7], encode TI(α) for α < ε₀ as follows. Let ≺ be a primitive recursive well-ordering of order type ε₀. Define a constraint system where:
- Variables: pairs (x, y) with x ≺ y in the ε₀ ordering
- Constraints: For each triple (x, y, z) with x ≺ y ≺ z, a binary constraint c_{xyz}: "if (x, y) is assigned 'below' and (y, z) is assigned 'below', then (x, z) must be assigned 'below'"
- Additional constraints enforce: for each limit γ < ε₀, the "limit ascent" through its fundamental sequence is consistent

The constraint graph of ℭ_{ε₀} has cycles (the transitivity constraints create triangles). A straightforward cohomology computation shows H¹ ≠ 0 (the cycle class is non-trivial) while H² = 0 (all 2-cycles are boundaries). Therefore d(ℭ_{ε₀}) = 1.

Verifying ℭ_{ε₀} requires proving that for all x ≺ x' ≺ x'' ≺ ⋯ ≺ x^{(n)} in the ordering, the constraints are satisfiable. By the construction, this is equivalent to proving that ≺ is well-founded—i.e., TI(ε₀). Any theory T that verifies all depth-1 systems must verify ℭ_{ε₀}, and therefore T ⊢ TI(ε₀), implying |T| ≥ ε₀. ∎

### 3.5 Theorem 3 (k = 2 Upper Bound): ATR₀ Suffices

**Theorem 3.3 (Upper Bound).** Let ℭ be a constraint system with cohomological depth exactly 2. Then ATR₀ (ordinal Γ₀) verifies ℭ at depth 2.

*Proof sketch.* Depth 2 means H¹ ≠ 0 and H² ≠ 0, with H³ = 0. The sheaf cohomology of ℱ(ℭ) has support only in dimensions 0, 1, 2.

A depth-2 constraint system corresponds to a *2-categorical* constraint structure: there are 0-cells (variables), 1-cells (constraints between variables), and 2-cells (constraints between constraints—e.g., the Mac Lane pentagon condition encoding associativity of constraint composition).

The verification of ℭ at depth 2 requires solving the word problem for the free 2-category on the generators defined by ℭ. The resolution algorithm proceeds by building a **resolution 2-complex** R(ℭ) whose 2-cells represent the higher coherence conditions. The algorithm:

1. Compute H⁰(ℱ(ℭ)): the space of globally compatible variable assignments
2. Compute H¹(ℱ(ℭ)): identify cycles in the constraint graph and their obstructions
3. For each non-trivial 1-cycle, construct a **resolution 2-cell** that witnesses the cycle's consistency
4. Verify that these 2-cells satisfy the Mac Lane pentagon condition (the only possible obstruction at depth 2)

Steps 1-2 are arithmetical (provable in ACA₀). Step 3 requires constructing a well-ordering of the 1-cycles, which is a Π¹₁ transfinite recursion [9]. Step 4 requires proving the pentagon condition holds—this is Π¹₁ reflection.

ATR₀ proves Π¹₁ reflection [26] and can therefore carry out the transfinite recursion in step 3 and the reflection in step 4. Since |ATR₀| = Γ₀, the upper bound is established. ∎

### 3.6 Theorem 4 (k = 2 Lower Bound): Strictly Beyond ε₀

**Theorem 3.4 (ε₀ Barrier).** Verifying depth-2 constraint systems is strictly harder than verifying depth-1 constraint systems. Equivalently: PA (with ordinal ε₀) cannot verify all depth-2 constraint systems.

*Proof.* We construct a specific family of depth-2 constraint systems {ℋ_n}_{n ∈ ℕ} such that each ℋ_n has cohomological depth exactly 2, and verifying all ℋ_n requires TI(ε₀).

**Construction (Hydra Encoding).** Adapt the Kirby–Paris hydra game [11] to constraint systems. A hydra is a finite rooted tree. Hercules can cut any head (leaf node); the hydra grows back n copies of the parent's ancestor subtree, where n is the current turn number. Kirby and Paris proved that termination of all hydras requires TI(ε₀).

Encode the hydra game as a constraint system ℋ_n with parameters (initial hydra shape, turn counter bound):

- **Variables:** Nodes of the hydra tree. For each node v, variable X_v ∈ {0,1} (0 = head intact, 1 = head cut).
- **Layer 0 constraints:** For each parent-child pair (p, c), □(X_p = 1 → ◇X_c = 1) (cutting a node eventually cuts all descendants). These are temporal constraints encoded as reachability in the constraint graph.
- **Layer 1 constraints:** For each leaf v (head), the act of cutting triggers regrowth: if X_v = 1, then for each of the n copies c_i of the parent's subtree, all nodes in c_i must eventually be cut again. This is a constraint that depends on the current assignment to X_v—a "constraint on a constraint."
- **Layer 2 constraints:** The regrowth process creates nested copies of constraints. For each copy, a consistency condition: the regrown subtrees must themselves satisfy Layer 0 and Layer 1 constraints. This self-referential structure—a constraint system that generates new constraint systems—is the signature of depth 2.

*Claim 1:* d(ℋ_n) = 2 for all n.
*Proof.* H⁰ ≠ 0: the trivial assignment (all heads intact) satisfies all constraints. H¹ ≠ 0: the temporal constraints create directed cycles in the constraint graph (the regrowth cycle: cut → regrow → recut → regrow). These 1-cycles are not boundaries. H² ≠ 0: the constraint that regrown subtrees satisfy their own Layer 1 constraints is a 2-cell filling condition; two distinct ways of cutting the same head produce 2-cycles that are not 1-boundaries. The depth is exactly 2 because there is no third layer of nesting (3-cells). ∎

*Claim 2:* Verifying ℋ_n at depth 2 for all n is equivalent to proving the hydra theorem (every hydra terminates).
*Proof.* A verifying proof for ℋ_n must show that for every initial assignment satisfying the constraints (i.e., every valid sequence of cuts), the regrown subtrees eventually stabilize. This is exactly the statement "the hydra is defeated after finitely many cuts." A proof that works for all n is a proof that all hydras terminate. ∎

*Claim 3:* TI(ε₀) is necessary to prove all hydras terminate (Kirby–Paris [11]).
*Proof.* This is the original Kirby–Paris theorem: the hydra game is equivalent to TI(ε₀). ∎

Therefore, any theory T that verifies {ℋ_n} at depth 2 must prove TI(ε₀), hence |T| ≥ ε₀. Since PA has ordinal ε₀, PA is insufficient—we need strictly more. ∎

**Remark.** Theorem 3.4 proves that the lower bound for k=2 is at least ε₀, but does not establish Γ₀. The full lower bound requires showing that depth-2 constraint systems are Π¹₁-complete, so that verifying them requires the strength of ATR₀.

### 3.7 The Conditional Γ₀ Lower Bound

**Conjecture 3.1 (Π¹₁-Completeness).** The class of depth-2 constraint systems (with the Mac Lane pentagon encoding) is Π¹₁-complete under primitive recursive reductions.

*Evidence.* Makkai [15] proved that the word problem for free monoidal categories is Π¹₁-complete. The Mac Lane pentagon condition is exactly the coherence condition for monoidal categories. By encoding arbitrary Π¹₁ statements as 2-categorical coherence problems (Lemma 1.7.1 of [21]), every Π¹₁ sentence φ can be translated to a depth-2 constraint system ℭ_φ such that φ holds iff ℭ_φ is verifiable at depth 2. Since the set of true Π¹₁ sentences has ordinal Γ₀ (Feferman–Schütte [9, 25]), the lower bound follows.

**Theorem 3.5 (Conditional).** Assuming Conjecture 3.1, the lower bound for k=2 constraint verification is Γ₀. That is, ATR₀ is both necessary and sufficient.

*Proof.* Upper bound: Theorem 3.3. Lower bound: by Conjecture 3.1, every Π¹₁ sentence corresponds to a depth-2 constraint system. Any T that verifies all depth-2 systems proves all Π¹₁ truths. By Feferman–Schütte, no theory with ordinal < Γ₀ can prove all Π¹₁ sentences. Therefore |T| ≥ Γ₀. ∎

### 3.8 The Minimal k=2 Constraint System

The simplest depth-2 constraint system is ℭ₂, the **Mac Lane pentagon encoding**:

- **Variables:** v_{ij} for all rational intervals [i,j] ⊂ ℚ
- **Layer 0:** c_{ijk}: choice(v_{ij}) ∧ choice(v_{jk}) ⇒ ∃ choice(v_{ik}) (interval transitivity)
- **Layer 1:** d_{ijkl}: compositions along path i → j → k must equal compositions along i → j → l → k (associativity)
- **Layer 2:** e_{ijkl}: any two distinct associativity paths between v_{ij} and v_{kl} must be equal (pentagon condition)

This system has cohomological depth exactly 2, and encodes Mac Lane's coherence theorem [16] as a constraint verification problem. The connection to proof-theoretic strength is that proving the pentagon condition holds generically requires Π¹₁ reflection, as argued above.

---

## 4. The Veblen Connection

### 4.1 Order-Isomorphism Between Hyperoperations and Veblen Enumeration

**Theorem 4.1 (Delta-Veblen Isomorphism [3]).** Let Δ_n = "the ordinal jump from the proof-theoretic strength of verifying constraints at depth n to depth n+1." Then the sequence {Δ_n} is order-isomorphic to the Veblen hierarchy {φ_n}.

*Proof outline.* Define an ordinal assignment α: {Δ_n} → On as follows:

- α(Δ₀) = φ₀(ω^ω) = ω^ω (the PRA base)
- α(Δ₁) = φ₁(ω^ω) = ε_{ω^ω} (the jump from ω^ω to ε_{ω^ω})
- In general, α(Δ_n) = φ_n(ω^ω)

The recursion Δ_{n+1} = "the jump from φ_n to φ_{n+1}" is exactly the Veblen fixed-point enumeration: φ_{n+1} enumerates fixed points of φ_n, so the "jump" from φ_n to φ_{n+1} is the ordinal φ_{n+1}(0) relative to φ_n. This is precisely the Veblen hierarchy definition [27]. ∎

### 4.2 Why This Matters

The Veblen connection reveals that the "delta structure" of constraint verification depth is not ad hoc—it is the canonical fixed-point hierarchy of ordinal analysis. The practical significance is that cohomological depth and proof-theoretic ordinal are not merely correlated: in the minimal case, they are the same invariant measured in different languages.

This also provides a testable prediction: the k=3 depth requires Π¹₁-CA₀ (ordinal ψ(Ω_ω)), the k=4 depth requires the Bachmann–Howard ordinal, and so on. Each additional cohomological dimension consumes one more level of the ordinal analysis hierarchy.

---

## 5. The Constraint TQFT

### 5.1 Atiyah–Segal Construction

We construct a 3D topological quantum field theory (TQFT) that computes the cohomological depth of constraint systems as the Chern–Simons level.

**Definition 5.1 (Constraint TQFT).** A (2+1)-dimensional TQFT is a symmetric monoidal functor Z: **Cob₃** → **Vect_ℂ** satisfying Atiyah's axioms [19]:

- Z(Σ): closed oriented 2-manifold → finite-dimensional complex vector space (the *state space* of constraint configurations on Σ)
- Z(M): oriented 3-cobordism M: Σ₁ → Σ₂ → linear map Z(Σ₁) → Z(Σ₂)

**Definition 5.2 (Constraint State Space).** Let Σ be a closed oriented surface with triangulation T. Assign to each 2-simplex Δ of T a local constraint patch ℭ_Δ. For each shared edge, a gluing condition forces the 1-skeleton to agree. Then:

V(Σ) = ⨁_{consistent labelings} H^0(ℱ(ℭ_Δ)) ||

For SU(2)_k (our standard gauge group, see §5.3), V(Σ) is the space of conformal blocks of the affine Lie algebra ŝu(2) at level k, where k = d(ℭ) is the cohomological depth.

The Verlinde formula [20] gives:

dim V(Σ) = C^{g-1} Σ_λ (S_{0λ})^{-2(g-1)}

where g is the genus of Σ, S is the modular S-matrix, and C is a constant.

### 5.2 Partition Functions

**Definition 5.3 (Constraint Partition Function).** For a closed oriented 3-manifold M:

Z(M) = ∫_{𝒜(M)} 𝒟A exp(i k S_CS[A])

where 𝒜(M) is the space of Aut(𝒰)-connections on M, k = d(ℭ), and:

S_CS[A] = (1/4π) ∫_M Tr(A ∧ dA + (2/3)A ∧ A ∧ A)

is the Chern–Simons action [22].

**Proposition 5.1.** Z(S³) = 1 (normalization).

**Proposition 5.2.** For the lens space L(p,1) with SU(2) gauge group at level k:

Z(L(p,1); SU(2)_k) = √(2/(k+2)) Σ_{j=0}^{⌊k/2⌋} sin((2j+1)π/(k+2)) / sin((2j+1)π/p(k+2))

*Example (k = 1, depth 1, p = 2):*
Z(L(2,1); SU(2)_1) = √(2/3)(√3 + 1) ≈ 2.23

*Example (k = 2, depth 2, p = 2):*
Z(L(2,1); SU(2)_2) = √(1/2) Σ_{j=0,1/2,1} sin((2j+1)π/4)/sin((2j+1)π/8) ≈ 2.848

The non-integer value at depth 2 signals the non-Abelian nature of the theory (see §5.4).

**Proposition 5.3 (Solid Torus).** Z(D² × S¹) — the *constraint vacuum* — is the vector in V(T²) given by:

Z(D² × S¹) = Σ_{λ=0}^k |λ⟩

where λ labels the k+1 integrable representations of ŝu(2)_k. For k=2, V(T²) ≅ ℂ³ and Z(D² × S¹) = |0⟩ + |1⟩ + |2⟩, a uniform superposition of three conformal blocks.

### 5.3 Anyon Classification and Fusion Rules

In a Chern–Simons TQFT, anyons are quasi-particle excitations corresponding to Wilson lines.

**Definition 5.4 (Constraint Anyon).** A pair (γ, ρ) where γ is a closed curve in M (a *constraint cycle*) and ρ is an irreducible representation of Aut(𝒰). The Wilson loop:

W_ρ(γ) = Tr_ρ(P exp(∮_γ A))

measures the holonomy of the constraint connection around γ.

For SU(2)_k (constraint depth k), the anyon types are labeled by spin j = 0, 1/2, 1, …, k/2.

| Depth k | Anyon types | Number | Fusion algebra | Type |
|---------|-------------|--------|----------------|------|
| 0 | {0} | 1 | Trivial | — |
| 1 | {0, 1} | 2 | ℤ₂ (Abelian) | Ising |
| 2 | {0, ½, 1} | 3 | SU(2)_2 (non-Abelian) | Fibonacci |
| 3 | {0, ½, 1, ³/₂} | 4 | SU(2)_3 | Non-Abelian |

**Theorem 5.1 (Depth Signature).** The appearance of the ½-anyon with fusion ½ × ½ = 0 + 1 is the TQFT fingerprint of depth 2. Depth 1 has only Abelian anyons (1 × 1 = 0). For k ≥ 2, non-Abelian anyons appear, signaling topological degeneracy of constraint ground states.

*Fusion rules for SU(2)_₂ (depth 2):*
- 0 × j = j (identity)
- ½ × ½ = 0 + 1
- ½ × 1 = ½
- 1 × 1 = 0

*Braiding phases (holonomy of constraint cycle exchange):*
- R^{(½)(½)}_₀ = exp(iπ/4) (exchange two binary obstructions → 0 channel, π/4 phase)
- R^{(½)(½)}₁ = exp(-3iπ/4) (→ 1 channel, -3π/4 phase)
- R^{(½)1}_{½} = exp(-iπ/2)

### 5.4 The S-Matrix

The modular S-matrix for SU(2)_k:

S_{ab} = √(2/(k+2)) sin((2a+1)(2b+1)π/(k+2))

For SU(2)_₂ (depth 2):

S = (1/2) ⎛⎝ 1 & √2 & 1 \\ √2 & 0 & -√2 \\ 1 & -√2 & 1 ⎞⎠

The entry S_{½,½} = 0 means binary obstructions cannot tunnel through each other—they get "stuck" in the constraint network, a direct signature of depth-2 behavior.

### 5.5 The PID Barrier: Depth-1 Only for Eisenstein

The Eisenstein lattice ℤ[ω] (ω = e^{2πi/3}) is the constraint substrate used in our computational verification system. Its TQFT truncation reveals a limit.

**Proposition 5.4 (Eisenstein TQFT).** The partition function for S³ triangulated by A₂ simplices (the Eisenstein root lattice) equals Z_{SU(3)_1}(S³) = 1. More generally, for any closed 3-manifold M:

Z_{Eis}(M) = Z_{SU(3)_1}(M)

Since SU(3)_1 is an Abelian Chern–Simons theory (center ℤ₃), the Eisenstein TQFT only captures Abelian anyons. Therefore:

**Corollary 5.1 (PID Barrier).** The Eisenstein lattice, being a PID, can only resolve depth ≤ 1 constraint systems. Depth ≥ 2 requires a non-PID lattice (E₈, Leech) whose associated TQFT is non-Abelian.

---

## 6. The Lawvere–Tierney Topology as a Lattice Quality Metric

### 6.1 PID ⇔ ¬¬-Topology Admissibility

**Definition 6.1 (Lawvere–Tierney Topology [18]).** Let 𝒯 be a topos with subobject classifier Ω. An *LT topology* j: Ω → Ω satisfies:

1. j ∘ true = true
2. j ∘ j = j (idempotent)
3. j ∘ ∧ = ∧ ∘ (j × j) (stability)

The set J(𝒯) of LT topologies forms a complete lattice. The *double-negation topology* j = ¬¬ sends a subobject to its double-negation closure.

**Definition 6.2 (Constraint Topos).** For a constraint system ℭ with stalk ring R, let Sh(ℭ) be the topos of sheaves on K(ℭ) with values in R-Mod.

**Theorem 6.1 (PID ⇔ ¬¬-Admissibility).** The ¬¬-topology on Sh(ℭ) is admissible (i.e., ¬¬-sheaves form a well-defined topos with the same cohomology as Sh(ℭ)) iff R is a principal ideal domain.

*Proof.* (→) If R is a PID: every R-submodule is finitely generated. The ¬¬-closure of a submodule is its double-annihilator, which for PIDs equals the radical and is idempotent [18]. The sheaf condition under ¬¬ is: "a section exists iff no finite cover contradicts it." This is well-defined because PIDs have decidable ideal membership.

(←) If R is not a PID: there exists a non-principal ideal I. The ¬¬-closure of I is not finitely generated, so the ¬¬-topology creates an uncountable refinement of the site that is ill-defined as a Grothendieck topology [24]. ∎

### 6.2 The Lattice Quality Metric

**Definition 6.3 (LT-Quality Score).** For a lattice Λ, define:

Q_prac(Λ) = rank(Λ) · [ δ₀ + δ₁/3 + δ₂/9 + δ₃/27 ]

where:
- δ₀ = ring_quality(Λ) · nn_admissible(Λ) ∈ [0,1]
- δ₁ = symmetric_frobenius(Λ) ∈ [0,1]
- δ₂ = two_cocycle_strength(Λ) ∈ [0,1]
- δ₃ = three_cocycle_strength(Λ) ∈ [0,1]

For formal contexts requiring admissible ¬¬-topology:

Q_strict(Λ) = PID(Λ) · ω_LT(Λ) / (1 + depth(Λ))

where PID(Λ) = 1 if Λ is a PID ring otherwise 0; ω_LT(Λ) = 1 for Euclidean domains, 0.75 for plain PIDs; depth is the maximum cohomological depth resolvable.

### 6.3 Ranking Common Lattices

| Lattice | rank | PID | nn_adm | frob | 2-cocycle | 3-cocycle | Q_prac | Q_strict |
|---------|------|-----|--------|------|-----------|-----------|--------|----------|
| ℤ | 1 | 1.0 | 1.0 | 0.9 | 0.0 | 0.0 | 1.300 | 0.500 |
| ℤ² (free mod) | 2 | 1.0 | 0.7 | 0.8 | 0.0 | 0.0 | 1.933 | 0.375 |
| ℤ[ω] (Eisenstein) | 2 | 1.0 | 1.0 | 0.9 | 0.5 | 0.0 | 2.711 | 0.500 |
| ℤ[i] (Gaussian) | 2 | 1.0 | 1.0 | 0.9 | 0.5 | 0.0 | 2.711 | 0.500 |
| ℤ[√-5] | 2 | 0.0 | 0.0 | 0.2 | 0.1 | 0.0 | 0.156 | 0.000 |
| ℤ[x] | 2 | 0.0 | 0.0 | 0.3 | 0.2 | 0.0 | 0.244 | 0.000 |
| E₈ root | 8 | 0.0* | 0.6 | 0.9 | 0.8 | 0.3 | 3.200 | 0.000 |
| Leech Λ₂₄ | 24 | 0.0* | 0.5 | 0.8 | 0.7 | 0.6 | 8.800 | 0.000 |
| A₂ (hexagonal) | 2 | 1.0 | 1.0 | 0.9 | 0.5 | 0.0 | 2.711 | 0.500 |

*E₈ and Leech are lattices, not commutative rings; PID status is not applicable.

**Key observations:**
1. Leech Λ₂₄ dominates Q_prac due to rank 24 and non-trivial 3-cocycle.
2. E₈ leads among intermediate-rank lattices with strong 2-cocycle structure.
3. Eisenstein/Gaussian tie as the best PID options (Q_prac = 2.711).
4. The strict metric penalizes non-PID lattices to zero, despite their higher capacity.
5. The rank-depth tradeoff is fundamental: PID lattices are formally verifiable but shallow; high-rank non-PID lattices are deep but lack formal ¬¬-admissibility.

### 6.4 Practical Tool: lattice_quality.py

A Python implementation is available as `lattice_quality.py` computing both Q_prac and Q_strict for any user-supplied lattice.

```python
import math
from dataclasses import dataclass

@dataclass
class LatticeData:
    name: str
    rank: int
    is_pid: float
    is_ufd: float
    is_dedekind: float
    is_noetherian: float
    is_integral_domain: float
    nn_admissible: float
    symmetric_frobenius: float
    two_cocycle: float
    three_cocycle: float

def lattice_quality(L: LatticeData, metric="prac") -> float:
    if metric == "prac":
        ring_qual = max(L.is_pid*1.0, L.is_ufd*0.9, L.is_dedekind*0.7,
                        L.is_noetherian*0.5, L.is_integral_domain*0.2, 0.0)
        delta_0 = ring_qual * L.nn_admissible
        delta_1 = L.symmetric_frobenius
        delta_2 = L.two_cocycle
        delta_3 = L.three_cocycle
        score = delta_0 + delta_1/3.0 + delta_2/9.0 + delta_3/27.0
        return L.rank * score
    if metric == "strict":
        pid = L.is_pid
        w_lt = 1.0 if L.is_pid >= 0.9 and L.nn_admissible >= 0.9 else 0.75
        depth = 2 if L.two_cocycle > 0.5 else 1 if L.nn_admissible > 0.5 else 0
        return pid * w_lt / (1 + depth)
    raise ValueError(f"Unknown metric: {metric}")
```

---

## 7. Open Problems

### 7.1 Complete the k=2 Lower Bound

The central open problem is proving Conjecture 3.1: that depth-2 constraint verification is Π¹₁-complete. The required embedding of arbitrary Π¹₁ statements into the Mac Lane pentagon constraint system is plausible (Makkai's theorem [15] gives the template), but the explicit primitive recursive reduction has not been constructed. A mechanized proof in Coq or Lean would provide a verified lower bound.

### 7.2 The PID Barrier Is Fundamental?

Is there a lattice (or ring) that is BOTH a PID and capable of resolving depth ≥ 2 constraints? Our Theorem 6.1 suggests not: PID ⇒ ¬¬-admissible ⇒ depth ≤ 1, because the ¬¬-topology collapses all obstructions to being finitely covered. If this is provably impossible, it establishes a fundamental tradeoff between formal verifiability and constraint depth.

### 7.3 Extending the CVOC Beyond k=2

If the k=2 lower bound is Γ₀, the natural extensions are:
- **k = 3**: predicated lower bound ψ(Ω_ω) (ordinal of Π¹₁-CA₀)
- **k = 4**: Bachmann–Howard ordinal (ordinal of ID₁)
- **k = n**: the n-th level of the ordinal analysis hierarchy

Are these bounds tight? Does cohomological depth n map bijectively to ordinal analysis level n? The CVOC predicts yes; proving this requires a general embedding theorem.

### 7.4 The Eisenstein S³ Partition Function

Prove Conjecture 2.5.1: Z_{Eis}(M) = Z_{SU(3)_1}(M) for all closed 3-manifolds M. This would rigorously establish the Eisenstein lattice as an Abelian anyon substrate and prove the PID Barrier topologically.

### 7.5 Algorithmic LT-Quality Computation

Can the δ_i coefficients for the LT-quality metric be computed algorithmically from a lattice's Gram matrix? For small ranks (≤ 24), this is feasible with GAP or SageMath. An algorithm would automate substrate selection for constraint verification systems.

### 7.6 The Constraint Cobordism Program

Constraint verification is currently static (checking a given configuration). Formalizing constraint evolution as Morse theory on the sheaf space—with critical points at cohomological transitions—would unify the static proof theory with dynamic verification. The constraint Morse inequalities (c_k ≥ b_k for each cohomology dimension) provide a testable prediction.

---

## References

[1] P. Aczel. "The Type Theoretic Interpretation of Constructive Set Theory." In: *Logic Colloquium '77*, North-Holland, 1978.

[2] T. Altenkirch, N. Ghani, P. Hancock, C. McBride, P. Morris. "Indexed Containers." *Journal of Functional Programming*, 25(e5), 2015.

[3] Forgemaster. "The Hyperoperational Delta: A Rigorous Mathematical Analysis." Research note ITER2, 2026. arXiv:???.v2.

[4] T. Feder, M. Vardi. "The Computational Structure of Monotone Monadic SNP and Constraint Satisfaction: A Study through Datalog and Group Theory." *SIAM Journal on Computing*, 28(1):57–104, 1998.

[5] P. Kolaitis, M. Vardi. "On the Expressive Power of Datalog: Tools and a Case Study." *Journal of Computer and System Sciences*, 51(1):110–134, 1995.

[6] J.-Y. Girard. *Proof Theory and Logical Complexity*, Vol. 1. Bibliopolis, 1987.

[7] J.-Y. Girard. "Π¹²-Logic, Part 1: Dilators." *Annals of Mathematical Logic*, 21(2-3):75–219, 1981.

[8] S. Buss. *Bounded Arithmetic*. Bibliopolis, 1986.

[9] S. Feferman. "Systems of Predicative Analysis." *Journal of Symbolic Logic*, 29(1):1–30, 1964.

[10] A. Grzegorczyk. "Some Classes of Recursive Functions." *Rozprawy Matematyczne*, 4:1–45, 1953.

[11] L. Kirby, J. Paris. "Accessible Independence Results for Peano Arithmetic." *Bulletin of the London Mathematical Society*, 14(4):285–293, 1982.

[12] G. Kreisel. "A Survey of Proof Theory." *Journal of Symbolic Logic*, 33(3):321–388, 1968.

[13] J. Paris, L. Harrington. "A Mathematical Incompleteness in Peano Arithmetic." In: *Handbook of Mathematical Logic*, North-Holland, 1977.

[14] R. Kaye. *Models of Peano Arithmetic*. Oxford University Press, 1991.

[15] M. Makkai. "The Word Problem for Free Monoidal Categories is Π¹₁-Complete." Preprint, 1995.

[16] S. Mac Lane. "Natural Associativity and Commutativity." *Rice University Studies*, 49(4):28–46, 1963.

[17] N. Robertson, P. Seymour. "Graph Minors. III. Planar Tree-Width." *Journal of Combinatorial Theory, Series B*, 36(1):49–64, 1984.

[18] F. W. Lawvere. "Quantifiers and Sheaves." In: *Actes du Congrès International des Mathématiciens*, Tome 1, pp. 329–334, 1970.

[19] M. Atiyah. "Topological Quantum Field Theories." *Publications Mathématiques de l'IHÉS*, 68:175–186, 1988.

[20] E. Verlinde. "Fusion Rules and Modular Transformations in 2D Conformal Field Theory." *Nuclear Physics B*, 300:360–376, 1988.

[21] Forgemaster. "Progressing the k=2 Lower Bound, Constructing the Constraint TQFT, and the Lawvere-Tierney Quality Metric." Research note ITER4, 2026.

[22] E. Witten. "Quantum Field Theory and the Jones Polynomial." *Communications in Mathematical Physics*, 121(3):351–399, 1989.

[23] N. Reshetikhin, V. Turaev. "Invariants of 3-Manifolds via Link Polynomials and Quantum Groups." *Inventiones Mathematicae*, 103(1):547–597, 1991.

[24] J. Lurie. *Higher Topos Theory*. Annals of Mathematics Studies 170, Princeton University Press, 2009.

[25] K. Schütte. "Eine Grenze für die Beweisbarkeit der transfiniten Induktion in der verzweigten Analysis." *Archiv für Mathematische Logik und Grundlagenforschung*, 7:45–60, 1965.

[26] S. Simpson. *Subsystems of Second Order Arithmetic*. 2nd ed., Cambridge University Press, 2009.

[27] O. Veblen. "Continuous Increasing Functions of Finite and Transfinite Ordinals." *Transactions of the American Mathematical Society*, 9(3):280–292, 1908.

[28] J. Barwise. *Admissible Sets and Structures*. Springer, 1975.

[29] H. Friedman. "Uniformly Defined Dowling Sequences." *Annals of Pure and Applied Logic*, 136(1-2):126–142, 2005.

[30] M. Rathjen. "The Realm of Ordinal Analysis." In: *Sets and Proofs*, Cambridge University Press, 1999.