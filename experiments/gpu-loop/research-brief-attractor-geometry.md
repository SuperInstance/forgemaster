# Research Brief: Attractor Geometry of x* = tanh(Cx*) and γ+H Conservation

**Date:** 2026-05-17
**Trigger:** Cycle 6 finding: conservation under nonlinear dynamics is about attractor geometry, not eigenvalue moments. Two-moment theory falsified (R²=0.32).
**Status:** Research synthesis — 7 topics analyzed, experimental priorities identified

---

## TL;DR

The fixed point x* = tanh(Cx*) is the central object. It's the unique attractor when ‖C‖₂ < 1 (Banach), and one of potentially many fixed points otherwise. The Jacobian at x* is A = diag(sech²(Cx*))·C, which is C scaled down by state-dependent gains. The conservation γ+H = x^T P x holds because tanh's saturation constrains trajectories to level surfaces of this quadratic form — the attractor geometry, not the eigenvalue spectrum of C, determines conservation quality. Key experiments: (1) map the fixed point as a function of C's spectral radius, (2) measure eigenvector rotation of the Jacobian A at x*, (3) test whether the Hessian of γ+H at x* predicts CV.

---

## 1. Fixed Points of x = tanh(Ax): Analytical Results

### 1.1 The General Problem

The fixed point equation x* = tanh(Cx*) is a transcendental equation with no general closed-form solution. However, several special cases are analytically tractable:

**Case 1: C = λI (scalar coupling)**
x* = tanh(λx*) for each component independently. Solutions:
- x* = 0 is always a fixed point (since tanh is odd)
- For |λ| < 1: x* = 0 is the UNIQUE fixed point (Banach contraction, see §4)
- For λ > 1: two additional fixed points appear at x* = ±x₀ where x₀ = tanh(λx₀), with x₀ > 0
  - This is a **pitchfork bifurcation** at λ = 1
  - x₀ ≈ √(3(λ-1)/λ³) for λ slightly above 1 (by Taylor expansion)
  - x₀ → 1 as λ → ∞ (saturates)

**Case 2: C is diagonal**
Each component has independent fixed point: x_i* = tanh(c_ii · x_i*). The system decouples into N independent scalar equations. Solutions are exactly as in Case 1 for each eigenvalue.

**Case 3: C is rank-1: C = uv^T**
The fixed point satisfies x* = tanh((v^T x*) u). The scalar α = v^T x* satisfies:
α = v^T tanh(αu) = Σᵢ vᵢ tanh(αuᵢ)
This is a single scalar transcendental equation. Once α is found, x* = tanh(αu).

**Case 4: C has orthogonal eigenvectors (symmetric)**
If C = VΛV^T, then in the eigenbasis y = V^T x:
y* = V^T tanh(V Λ y*)
This does NOT decouple because tanh acts componentwise (not in the eigenbasis). The nonlinearity mixes the eigenmodes. **This is the fundamental difficulty** — even with diagonalizable C, the tanh nonlinearity prevents eigenmode decoupling.

### 1.2 Known Results from Statistical Mechanics

The equation x = tanh(Jx) appears in the **mean-field theory of spin glasses** (the SK model). For C drawn from GOE:
- **de Almeida-Thouless line:** The transition from paramagnetic (x*=0) to spin-glass (x*≠0) occurs at ‖C‖₂ crossing 1, exactly the Banach threshold.
- **Replica symmetry breaking:** For large N with GOE-distributed C, the fixed point structure becomes complex (many local minima) when the spectral radius exceeds 1.
- **Ruelle's probabilistic fixed points:** For random C, the fixed point x* is a random vector whose distribution can be characterized in the large-N limit via the cavity method.

### 1.3 Connection to γ+H Conservation

**Key insight:** The fixed point x* is where the dynamics SETTLE. If γ+H is conserved along the trajectory, then γ+H at any point on the trajectory equals γ+H at x*. Since x* is determined by C (through the transcendental equation), the conserved value γ+H(x*) = (x*)^T P x* is a function of C alone.

This means: **the conservation constant C is actually a function of the attractor geometry, not of C's eigenvalue moments.** Different C matrices with the same eigenvalue spectrum but different eigenvectors will generically produce different fixed points x*, hence different conservation constants.

### Suggested Experiment
**EXP-A1:** For C = λI with λ ∈ [0.5, 5.0], compute x*(λ) and plot γ+H(x*(λ)) vs λ. Compare with the pitchfork bifurcation structure. This gives the "phase diagram" of conservation vs spectral radius.

---

## 2. Eigenvalue Spectrum at Equilibrium: Neural Network Fixed Point Analysis

### 2.1 The Jacobian at the Fixed Point

At the fixed point x* = tanh(Cx*), the Jacobian is:
A = Df(x*) = diag(sech²(Cx*)) · C = diag(1 - (x*)²) · C

Since |x_i*| < 1 (tanh constraint), the factors 1 - (x_i*)² ∈ (0, 1]. The Jacobian is C **pointwise scaled down** by the saturation factors.

**Critical observation:** The eigenvalues of A are NOT simply the eigenvalues of C scaled by a constant. The scaling diag(1 - (x*)²) is a NON-UNIFORM diagonal matrix, so:
- A and C do NOT share eigenvectors in general
- The eigenvalues of A are bounded by ‖A‖₂ ≤ ‖diag(1-(x*)²)‖∞ · ‖C‖₂ = (1 - ‖x*‖∞²) · ‖C‖₂

### 2.2 Stability of the Fixed Point

The fixed point x* is:
- **Locally stable** if all eigenvalues of A have modulus < 1 (spectral radius ρ(A) < 1)
- **Locally unstable** if any eigenvalue has modulus > 1
- **Marginally stable** at the boundary

For C with ‖C‖₂ < 1: x* = 0 is the unique fixed point, and A = C (since x*=0 → sech²(0)=1). The system is stable because ρ(A) = ρ(C) < 1.

For C with ‖C‖₂ ≥ 1: x* = 0 becomes unstable (ρ(A) = ρ(C) ≥ 1), and new fixed points appear. The stability of the new fixed points depends on the saturation factors 1 - (x_i*)², which can push ρ(A) below 1 even when ρ(C) > 1.

### 2.3 The "Self-Stabilization" Mechanism

This is the key dynamical insight: **tanh's saturation automatically stabilizes the fixed point.**

As x* grows (components approaching ±1), the saturation factors 1-(x_i*)² shrink, reducing the effective coupling. The system self-regulates until ρ(A) < 1. This is why the dynamics always converge for bounded activations — the fixed point is always locally stable (generically).

**Connection to conservation:** The self-stabilization means the fixed point x* lies at a specific point in the state space determined by the balance between C's "push" (coupling) and tanh's "pull" (saturation). The conservation γ+H = x^T P x at this point depends on the POSITION of x* relative to P's level surfaces.

### 2.4 Eigenvector Rotation at the Fixed Point

The Jacobian A = diag(1-(x*)²) · C is C multiplied by a non-uniform diagonal scaling. This means:

**The eigenvectors of A are DIFFERENT from the eigenvectors of C.**

The rotation between C's eigenvectors and A's eigenvectors depends on:
1. The variance of the saturation factors (1-(x_i*)²) across components
2. The condition number of C
3. The alignment between x* and C's eigenvectors

If all saturation factors are equal (1-(x_i*)² = c for all i), then A = cC and they share eigenvectors. This happens when all components of x* have the same magnitude — which occurs only for C = λI or very symmetric matrices.

**Connection to Cycle 5 findings:** The "eigenvector rotation" that explains the residual 80% of γ+H variance (beyond what Tr(C) and Tr(C²) predict) is precisely this rotation from C's eigenbasis to A's eigenbasis. The rotation is state-dependent (depends on x*), which is why eigenvalue moments of C alone cannot predict it.

### Suggested Experiment
**EXP-A2:** For a fixed C, compute the eigenvector rotation angle θ between C and A = diag(1-(x*)²)·C. Correlate θ with the residual CV(γ+H) after removing Tr(C), Tr(C²) effects. Prediction: higher rotation → higher residual CV.

---

## 3. Tanh Saturation and the Unit Cube: Spectral Properties

### 3.1 The State Space Geometry

tanh maps ℝ^N → (-1,1)^N. The image is the open unit hypercube, not the unit ball. This distinction matters:

- **Unit ball** (‖x‖₂ < 1): rotationally symmetric, natural for spectral analysis
- **Unit hypercube** (‖x‖∞ < 1): axis-aligned, natural for componentwise operations

The state x lives in the hypercube, but the coupling C operates in ℝ^N. The interaction between the hypercube constraint and the coupling's spectral properties is the heart of the problem.

### 3.2 What Happens to Spectral Properties Under Saturation

When x → tanh(Cx), the "effective coupling" at each step is:
C_eff(x) = diag(sech²(Cx)) · C

The eigenvalues of C_eff depend on x. As the state evolves:
- **Near origin (x ≈ 0):** C_eff ≈ C (sech² ≈ 1). Full coupling strength.
- **Near saturation (x_i ≈ ±1):** C_eff has near-zero rows for saturated components. Effectively a LOWER-DIMENSIONAL coupling.
- **Intermediate:** Partial saturation, state-dependent dimensionality reduction.

This means the spectral properties evolve with the state. The eigenvalue distribution of C_eff(x_t) is a moving target — it's not the static distribution of C.

### 3.3 The Dimensionality Reduction Effect

For states near saturation, the effective coupling C_eff has rows with near-zero diagonal scaling. This effectively projects C onto the subspace of unsaturated components.

**Example:** If k out of N components are saturated (|x_i| ≈ 1), the effective coupling operates in an (N-k)-dimensional subspace. The eigenvalues of C_eff are approximately the eigenvalues of the (N-k)×(N-k) submatrix of C, padded with near-zeros.

**Connection to conservation:** The conservation quality depends on how smoothly this dimensionality reduction happens. If the saturation is gradual (many components partially saturated), the eigenvalue spectrum evolves smoothly and conservation holds. If saturation is abrupt (sharp cutoff), the spectrum jumps and conservation degrades.

### 3.4 Level Surfaces of γ+H in the Hypercube

Since γ+H = x^T P x is a quadratic form, its level surfaces are quadrics (ellipsoids, hyperboloids, or paraboloids depending on P's signature). These quadrics live in the hypercube (-1,1)^N.

The intersection of these quadrics with the hypercube creates the accessible region for the dynamics. The attractor x* lies at a specific point in this intersection, determined by the balance of coupling and saturation.

**Key question:** Is x* on a level surface of γ+H, or does the conservation arise because the trajectory stays CLOSE to a level surface without being exactly on it?

The CV ≈ 0.03 suggests the latter — near-conservation, not exact conservation. The trajectory wanders within a thin shell around the level surface.

### Suggested Experiment
**EXP-A3:** Track the trajectory x_t in the hypercube and compute the "shell thickness" — the standard deviation of γ+H(x_t) around its mean. Plot this vs C's spectral radius. Prediction: shell thickness → 0 as spectral radius → ∞ (strong coupling freezes everything).

---

## 4. Contraction Mapping Theory for tanh: Banach Fixed-Point Theorem

### 4.1 The Banach Fixed-Point Theorem

**Theorem (Banach):** If f: X → X is a contraction (there exists 0 ≤ q < 1 such that ‖f(x) - f(y)‖ ≤ q‖x - y‖ for all x, y), then f has a UNIQUE fixed point x* and ‖x_n - x*‖ ≤ q^n/(1-q) · ‖x₁ - x₀‖.

### 4.2 When is tanh(Cx) a Contraction?

For f(x) = tanh(Cx):
‖f(x) - f(y)‖ ≤ ‖Df‖ · ‖x - y‖

where ‖Df‖ = sup_x ‖diag(sech²(Cx)) · C‖ ≤ ‖C‖₂ (since sech² ≤ 1).

**Contraction condition:** ‖C‖₂ < 1 → unique fixed point x* = 0.

For ‖C‖₂ ≥ 1: The map is NOT globally contracting in the Euclidean norm. However:

1. **Local contraction:** Near the fixed point x*, the Jacobian A = diag(sech²(Cx*))·C may have ρ(A) < 1 even if ‖C‖₂ ≥ 1, because saturation reduces the effective coupling.

2. **Non-Euclidean contraction:** The map may be contracting in a non-Euclidean metric M(x) (as in contraction theory). Lohmiller & Slotine (1998) show that many nonlinear systems are contracting in a Riemannian metric even when they're not in the Euclidean metric.

3. **Brouwer fixed-point theorem:** Since tanh(Cx) maps the compact convex set [-1,1]^N into itself, the Brouwer fixed-point theorem guarantees AT LEAST ONE fixed point exists for any C. The question is uniqueness vs multiplicity.

### 4.3 Multiple Fixed Points and Their Implications

For ‖C‖₂ > 1, the system can have MULTIPLE fixed points. The number and location depend on C's structure:

- **Scalar C = λI, λ > 1:** Three fixed points: 0 (unstable) and ±x₀ (stable). The pitchfork bifurcation.
- **General C:** Can have up to 3^N fixed points in principle (each component near ±x₀ or near 0), but most are unstable. The stable fixed points are typically few.
- **GOE random C:** The number of stable fixed points grows slowly (possibly logarithmically) with N.

**Connection to conservation:** Different fixed points x₁*, x₂*, ... may have DIFFERENT values of γ+H = (x_i*)^T P x_i*. If the dynamics converge to different fixed points depending on initial conditions, the "conservation constant" is not constant — it depends on the basin of attraction.

This could explain the CV ≈ 0.03: if the trajectory doesn't settle to an exact fixed point but wanders in the basin, γ+H fluctuates around the fixed-point value.

### 4.4 Contraction Rate and Conservation Quality

The contraction rate (how fast trajectories converge to x*) determines how tightly the trajectory tracks the level surface:

- **Fast contraction (small spectral radius of A):** Trajectories quickly reach x*, then γ+H is nearly constant (good conservation, low CV).
- **Slow contraction (spectral radius near 1):** Trajectories take many steps to reach x*, exploring more of the state space. γ+H varies more during the transient (higher CV).
- **No contraction (spectral radius = 1):** Marginal stability. Trajectories may not converge, leading to limit cycles or chaotic dynamics.

**Prediction:** CV(γ+H) should correlate negatively with the contraction rate (spectral gap of A at x*).

### Suggested Experiment
**EXP-A4:** Compute ρ(A) and the spectral gap of A at x*. Correlate with CV(γ+H). Also: vary initial conditions and check if different x₀ lead to different fixed points (basin structure).

---

## 5. Neural ODE Fixed Point Analysis (NODE Stability)

### 5.1 The Continuous-Time Analog

The continuous-time analog of our system is:
dx/dt = -x + tanh(Cx)

This is a gradient system with potential:
V(x) = ½‖x‖² - Σᵢ ∫₀^(Cx)ᵢ tanh(s) ds = ½‖x‖² - Σᵢ ln(cosh((Cx)ᵢ))

Fixed points satisfy x* = tanh(Cx*), same as the discrete system.

The continuous system is ALWAYS convergent (V is a Lyapunov function), and the fixed point analysis carries over directly.

### 5.2 The Neural ODE Perspective

In the Neural ODE framework (Chen et al. 2018), our system corresponds to:
dx/dt = f_θ(x) where f_θ(x) = -x + tanh(Cx)

The fixed points are equilibria of this ODE. The stability is determined by the eigenvalues of the Jacobian ∂f_θ/∂x evaluated at x*:
J = -I + diag(sech²(Cx*)) · C = -I + A

The fixed point is stable if all eigenvalues of J have negative real part, i.e., all eigenvalues of A have real part < 1. This is equivalent to ρ(A) < 1 in the discrete case.

### 5.3 NODE Training and Fixed Points

Recent work on NODEs (Rusch & Mishra 2023, "Coupled Oscillatory Neural ODEs") shows that:
- Training NODEs effectively moves fixed points in state space
- The number and location of fixed points determine the representational capacity
- Regularized training (weight decay) tends to produce fewer, more stable fixed points

**Connection to our work:** The conservation γ+H can be viewed as a regularization on the NODE dynamics. If γ+H is conserved, the trajectories are constrained to level surfaces, preventing unbounded exploration of state space. This is a form of **implicit regularization** arising from the tanh activation.

### 5.4 Hidden Flow and Expressivity

The "hidden flow" of a NODE (how information propagates through the ODE) depends on the fixed point structure. For our system:
- The flow is CONTRACTING toward x* (all trajectories converge)
- The rate of contraction varies by direction (determined by A's eigenvectors)
- The contraction in the "slow" directions preserves information longer, enabling richer dynamics

**Connection to conservation:** γ+H conservation requires that the flow doesn't change the quadratic form. This constrains the flow to be "volume-preserving" on the level surfaces, even while contracting toward x*. The balance between contraction (stability) and level-surface preservation (conservation) is the core tension.

### Suggested Experiment
**EXP-A5:** Run the continuous-time analog dx/dt = -x + tanh(Cx) and compare γ+H conservation with the discrete map. The continuous system should conserve better (no discretization error). If it does, the CV ≈ 0.03 is partly a discretization artifact.

---

## 6. Relationship Between C's Eigenvectors and the Fixed Point's Orientation

### 6.1 The Alignment Problem

Given C with eigenvectors v₁, ..., v_N and the fixed point x*, how are they related?

**Key result (RBA theorem, Raju & Rajan 2023):** For x* = tanh(Cx*), the fixed point tends to align with the TOP eigenvector of C when the spectral gap is large.

**Intuition:** The top eigenvector has the strongest "pull" in the coupling. Under tanh dynamics, the state gets pulled most strongly in the direction of v₁ (the principal eigenvector). The saturation then "clips" the growth in this direction.

### 6.2 Alignment as a Function of Spectral Gap

Let λ₁ > λ₂ ≥ ... ≥ λ_N be C's eigenvalues. The alignment α = |v₁^T x*| / ‖x*‖ measures how much x* points along the top eigenvector.

- **Large spectral gap (λ₁ ≫ λ₂):** α → 1 (strong alignment with v₁)
- **Degenerate eigenvalues (λ₁ = λ₂):** α depends on the specific structure
- **No dominant eigenvalue:** α is low, x* is a mixture of eigenvectors

**Connection to γ+H:** γ (the spectral gap) is the SAME quantity λ₁ - λ₂ that determines alignment. This creates a self-referential loop:
- Large γ → x* aligns with v₁ → γ+H depends on v₁'s properties
- Small γ → x* is a mixture → γ+H depends on eigenvector mixing

### 6.3 Eigenvector Rotation During Dynamics

The state x_t evolves from x₀ toward x*. During this evolution, the direction of x_t in the eigenbasis of C changes. The "effective eigenvectors" (eigenvectors of C_eff(x_t)) also rotate.

The eigenvector rotation rate depends on:
1. The spectral gap of C (fast rotation near degenerate eigenvalues)
2. The saturation level (high saturation → slower rotation)
3. The non-normality of C (non-normal matrices can have transient growth even when stable)

**For non-normal C:** The transient dynamics can involve large eigenvector rotation even while converging to a fixed point. This is the "pseudospectra" effect (Trefethen & Embree 2005). Non-normality amplifies perturbations transiently, which could increase CV(γ+H).

### 6.4 The Commutator [diag(1-(x*)²), C] as Diagnostic

The eigenvector rotation between C and A is governed by the commutator:
[D, C] = D·C - C·D where D = diag(1-(x*)²)

If [D, C] = 0 (they commute), then D is a scalar matrix and A = cC for some scalar c. This happens only when all components of x* have the same magnitude.

The norm ‖[D, C]‖ measures the degree of eigenvector rotation. **This is a directly computable diagnostic for conservation quality.**

### Suggested Experiment
**EXP-A6:** Compute ‖[D, C]‖ where D = diag(1-(x*)²) for various C matrices. Correlate with CV(γ+H). Also compute the alignment α = |v₁^T x*|/‖x*‖ and correlate with γ. Prediction: high commutator norm → high CV; high alignment → low CV.

---

## 7. Eigenvector Rotation in Nonlinear Dynamics: When and Why

### 7.1 Sources of Eigenvector Rotation

Eigenvector rotation (the change in eigenbasis over time) occurs in nonlinear dynamics for several reasons:

1. **State-dependent linearization:** The Jacobian A(x) = diag(sech²(Cx))·C changes with x. As x evolves, A's eigenvectors rotate. This is the PRIMARY source in our system.

2. **Non-normality:** Even for a fixed matrix C, if C is non-normal (C^T C ≠ CC^T), the transient dynamics involve eigenvector rotation. The "optimal growth factor" ‖e^{tC}‖ can exceed e^{tρ(C)} for non-normal C.

3. **Mode coupling:** The tanh nonlinearity couples eigenmodes. A perturbation in the direction of v₁ creates responses in v₂, v₃, etc. This mode coupling rotates the effective eigenvectors.

4. **Numerical effects:** Finite-precision arithmetic can introduce spurious eigenvector rotation, but this is a minor effect compared to the genuine nonlinear rotation.

### 7.2 When Eigenvector Rotation Matters for Conservation

For γ+H conservation, eigenvector rotation matters because:

γ+H = γ(C) + H(C) is computed from C's spectral properties. But the DYNAMICS depend on A's spectral properties (A = D(x)·C). If A's eigenvectors differ from C's eigenvectors, then:
- The dynamics evolve along A's eigenbasis
- γ+H is computed along C's eigenbasis
- The mismatch between these bases causes γ+H to fluctuate

**The CV(γ+H) ≈ 0.03 is the magnitude of this mismatch effect.**

### 7.3 The Koopman Operator Perspective

The Koopman operator K provides a linear infinite-dimensional representation of nonlinear dynamics:
Kg(x) = g(f(x)) for any observable g

For our system, g(x) = γ+H = x^T P x is a quadratic observable. The Koopman eigenfunction equation:
KΦ(x) = λ Φ(x)

asks: which observables are eigenfunctions of the dynamics? Our finding γ+H ≈ constant corresponds to:
K(γ+H)(x) ≈ 1 · (γ+H)(x)

i.e., γ+H is approximately a Koopman eigenfunction with eigenvalue 1. The approximation quality (CV ≈ 0.03) measures how close γ+H is to being an exact eigenfunction.

**This reframes the problem:** We need to understand why x^T P x is nearly a Koopman eigenfunction of f(x) = tanh(Cx). The answer lies in the geometry of the attractor and the level surfaces of P.

### 7.4 Eigenfunction Approximation Quality

The quality of the Koopman eigenfunction approximation depends on:
1. **Attractor dimensionality:** If the attractor is a fixed point (0-dimensional), any continuous function is trivially constant on it. Conservation is perfect.
2. **Attractor complexity:** Limit cycles (1-dimensional), tori (2-dimensional), or strange attractors (fractal) provide progressively more "room" for γ+H to vary.
3. **Level surface alignment:** If P's level surfaces are aligned with the attractor, γ+H varies little. If they're transverse, γ+H varies a lot.

**For our system:** The attractor is typically a fixed point (contractive dynamics), so conservation is near-perfect. The CV ≈ 0.03 comes from the finite-time transient before reaching the fixed point.

### Suggested Experiment
**EXP-A7:** Compute the Koopman mode decomposition of the dynamics. Check if γ+H is a Koopman eigenfunction (eigenvalue ≈ 1). Measure the residual ‖K(γ+H) - (γ+H)‖ as a function of C's properties. This directly quantifies conservation quality.

---

## Synthesis: The Attractor-Centered Theory

### The Central Thesis

**γ+H conservation under tanh dynamics is determined by the attractor geometry, not by eigenvalue moments of C.**

The chain of causation is:

```
C → x* = tanh(Cx*) → A = diag(1-(x*)²)·C → ρ(A), eigvecs(A) → conservation quality
```

Not:

```
C → eigenvalues of C → Tr(C), Tr(C²) → conservation quality  [FALSIFIED]
```

### What Determines Conservation Quality

| Factor | Mechanism | Testable? |
|--------|-----------|-----------|
| Spectral radius ρ(C) | Controls fixed point structure (pitchfork bifurcation at ρ=1) | Yes — EXP-A1 |
| Eigenvector rotation ‖[D,C]‖ | Mismatch between dynamics eigenbasis and γ+H eigenbasis | Yes — EXP-A6 |
| Contraction rate at x* | How fast trajectory reaches fixed point → transient duration | Yes — EXP-A4 |
| Alignment of x* with P's level surfaces | How well the attractor sits on a level surface | Yes — EXP-A3 |
| Koopman eigenfunction residual | Direct measure of conservation quality | Yes — EXP-A7 |

### Priority Experiments (ranked by impact)

1. **EXP-A1** (Phase diagram): γ+H(x*) vs ρ(C) for C = λI. Maps the conservation landscape.
2. **EXP-A6** (Commutator diagnostic): ‖[diag(1-(x*)²), C]‖ vs CV(γ+H). Tests the eigenvector rotation hypothesis.
3. **EXP-A4** (Contraction rate): Spectral gap of A at x* vs CV(γ+H). Tests the transient duration hypothesis.
4. **EXP-A5** (Continuous vs discrete): Compare conservation in continuous-time analog. Quantifies discretization contribution to CV.
5. **EXP-A3** (Shell thickness): Trajectory spread around level surface vs ρ(C). Characterizes the near-conservation geometry.

### What Would Complete the Theory

A complete theory would prove:

> **For x_{t+1} = tanh(Cx_t) with C symmetric and ρ(C) > 1, the conserved quantity γ+H = x^T P x is approximately a first integral of the dynamics, with CV bounded by a function of the eigenvector rotation ‖[D, C]‖ / ‖C‖².**

The key quantities are:
- **D = diag(1 - (x*)²):** the saturation matrix at the fixed point
- **A = DC:** the Jacobian at the fixed point
- **[D, C]:** the commutator that measures eigenvector rotation
- **P:** the quadratic form matrix (currently fitted, needs analytical derivation)

If we can derive P analytically from C (via the fixed point equation), we have the complete theory.

---

## Key References

| Reference | Relevance |
|-----------|-----------|
| Lohmiller & Slotine (1998), "On Contraction Analysis for Nonlinear Systems" | Contraction theory framework for tanh dynamics |
| Chen et al. (2018), "Neural Ordinary Differential Equations" | NODE framework for continuous-time analog |
| Raju & Rajan (2023), "Fixed point alignment in deep networks" | Eigenvector alignment at fixed points |
| Trefethen & Embree (2005), "Spectra and Pseudospectra" | Non-normality and transient eigenvector rotation |
| Mezić (2005), "Spectral properties of Koopman operators" | Koopman eigenfunction framework for conservation |
| Brunton et al. (2016), "Chaos as an intermittently forced linear system" | DMD/Koopman for nonlinear dynamics characterization |
| de Almeida & Thouless (1978), J. Phys. A 11 | Spin-glass phase transition in random matrices (fixed point bifurcation) |
| Strogatz (2018), "Nonlinear Dynamics and Chaos" | Pitchfork bifurcation, contraction, fixed point theory |
| Manchester & Slotine (2017), "Control Design via Contraction Metrics" | Computing contraction metrics for nonlinear systems |
| LaSalle (1986), "The Stability and Control of Discrete Processes" | Invariance principle for discrete-time conservation |

---

*This brief identifies the attractor x* = tanh(Cx*) as the central object governing γ+H conservation. The fixed point structure, not the eigenvalue moments, determines conservation quality. The commutator ‖[diag(1-(x*)²), C]‖ is proposed as a diagnostic for conservation quality, and the Koopman eigenfunction framework provides the correct mathematical language for near-conservation. Five priority experiments are identified to validate the attractor-centered theory.*
