# PROOF AUDIT REPORT
## Spectral First Integral Theory — Complete Mathematical Audit

**Auditor:** Claude Opus 4.6 (proof audit mode)
**Date:** 2026-05-17
**Documents audited:** 8
**Scope:** Every theorem, lemma, proposition, conjecture, and formal claim

---

## Executive Summary

The theory contains **one genuinely novel empirical observation** (that $I(x) = \gamma(x) + H(x)$ varies little along trajectories of contractive coupled systems) surrounded by **an apparatus of theorems that range from correctly proved trivialities to incorrectly stated results**. The overall rigor level is **2.4/5**.

**Critical issues found:**
1. **$\gamma$ is defined inconsistently across documents** — as spectral gap ($\lambda_1 - \lambda_2$) in the core document but as participation ratio ($(\sum\lambda_i)^2/\sum\lambda_i^2$) in the Jazz Theorem and Temporal Geometry documents. This means **$I = \gamma + H$ is a different quantity in different documents.**
2. **The Jazz Theorem's trajectory divergence claim contradicts the contraction assumption.** Contraction implies trajectory convergence to a unique fixed point; divergence is impossible.
3. **Theorem 3.1 (Rank-1 Conservation) states $I(x) = 1$ but the proof itself shows this is wrong** ($\gamma = \|x\|^2/N$, which depends on $x$).
4. **Monotonicity is claimed in one document and disproved in another** (MATH-TEMPORAL-GEOMETRY Thm 5.2(ii) vs. MATH-LYAPUNOV-MONOTONICITY Result 2.1).
5. **Most "theorems" are proof sketches** with unspecified constants, missing assumptions, or gaps at the key technical step.

**The strongest honest claim:** For contractive coupled systems $x_{t+1} = \sigma(C(x_t) x_t)$, the spectral functional $I(x_t)$ converges to $I(x^*)$ as trajectories approach their fixed point. The convergence is exponential with a rate empirically correlated ($r = 0.965$) with the commutator $\|[D,C]\|_F$. During the transient, $I$ varies much less than $\|x\|^2$ (typically 100--9300x less). This is a genuinely interesting empirical observation that deserves rigorous formalization.

---

## Document-by-Document Audit

---

### MATH-SPECTRAL-FIRST-INTEGRAL.md

#### Proposition 1.7: Existence via Contraction
- **Status:** PROVABLE (with fixes)
- **Statement clarity:** 3/5. States $L_C \cdot \text{Lip}(\sigma) < 1$ implies contraction, but this is only sufficient when $C$ is state-independent. For state-dependent $C(x)$, the Lipschitz estimate for $F(x) = \sigma(C(x)x)$ requires bounding $\|C(x)x - C(y)y\| \leq \|C(x)(x-y)\| + \|(C(x)-C(y))y\|$, which involves both $L_C$ and the Lipschitz constant of $x \mapsto C(x)$.
- **Proof completeness:** The proof writes the bound but doesn't finish it. The self-correction ("In practice, even when $L_C > 1$...") acknowledges the gap.
- **Logical gaps:** Missing Lipschitz bound for the state-dependent case. The conclusion requires restricting to a compact invariant set (which exists by boundedness of $\tanh$).
- **Rigor level:** 2/5
- **Dependencies:** None
- **Notes:** Standard fixed-point theory would close this gap: restrict to the compact set $[-1,1]^N$ under $\tanh$, then Schauder fixed-point theorem guarantees existence (though not uniqueness without contraction).

#### Theorem 3.1: Rank-1 Conservation ($I(x) = 1$)
- **Status:** WRONG (as stated)
- **Statement clarity:** The statement claims $\gamma(x) = 1$, $H(x) = 0$, $I(x) = 1$ for rank-1 coupling. The proof itself discovers and corrects the error: $\gamma = \lambda_1 - \lambda_2 = \|x\|^2/N - 0 = \|x\|^2/N$, which depends on $x$ and is NOT equal to 1.
- **Proof completeness:** The proof catches the error but the theorem statement is never corrected. The "Revised statement" in the proof body says $H = 0$ and $\text{PR} = 1$ are trivially conserved, and $\gamma$ conservation requires $\|x\|^2$ conservation — a much weaker claim.
- **Logical gaps:** The theorem as stated is false. The corrected claim ($H = 0$ exactly, $\text{PR} = 1$ exactly) is trivially true by algebraic structure of rank-1 matrices.
- **Rigor level:** 1/5 (the stated theorem is wrong; the corrected version in the proof body is a trivial observation)
- **Dependencies:** None
- **Notes:** This error propagates to Theorem 7.2 which repeats the claim.

#### Corollary 3.2: $\text{CV}(I) = 0$ for Rank-1
- **Status:** WRONG (if $I = \gamma + H$ with $\gamma$ = spectral gap)
- If $\gamma = \|x\|^2/N$ (spectral gap definition), then $I = \|x\|^2/N$ and $\text{CV}(I) = \text{CV}(\|x\|^2/N) \neq 0$ under dynamics. If $\gamma$ = participation ratio = 1 (constant), then $I = 1 + 0 = 1$ and $\text{CV} = 0$. The corollary is true only under the participation ratio definition of $\gamma$, revealing the definitional inconsistency.
- **Rigor level:** 1/5

#### Conjecture 3.3: Rank-$k$ Structural Conservation
- **Status:** CONJECTURE (appropriately labeled)
- **Statement clarity:** 3/5. Well-stated with supporting evidence from hybrid coupling experiments.
- **Rigor level:** N/A (conjecture)

#### Theorem 4.3: Spectral Shape Stability Implies Conservation
- **Status:** PROVABLE (with one additional assumption)
- **Statement clarity:** 3/5. The statement says "if $\hat{\Lambda}(x_t) = \hat{\Lambda}(x_0)$ for all $t$, then $I(x_t) = I(x_0)$."
- **Proof completeness:** Gap at step 3-4: $H$ depends only on $\{p_i\}$ (correct), but $\gamma = \lambda_1 - \lambda_2 = \text{Tr}(C)(p_1 - p_2)$ requires $\text{Tr}(C)$ constant, which is NOT a consequence of shape constancy alone. The proof says "Under normalization (row-stochastic coupling), $\text{Tr}(C)$ is automatically bounded" but bounded $\neq$ constant.
- **Logical gaps:** Needs additional assumption: $\text{Tr}(C(x_t))$ is constant, OR $\gamma$ is defined as a normalized quantity.
- **Rigor level:** 3/5 (fixable with one added assumption)
- **Dependencies:** None
- **Notes:** For row-stochastic $C$, $\text{Tr}(C) = N$ (constant), so the theorem holds in this important special case.

#### Theorem 4.5: Commutator Bounds Conservation Quality
- **Status:** PROVED (the algebraic perturbation identity)
- **Statement clarity:** 3/5. The bound $\|J - cC\|_F \leq \|[D,C]\|_F$ is correctly stated.
- **Proof completeness:** The algebraic identity $[D,C] = [\Delta, C]$ where $\Delta = D - cI$ is correct and fully proved.
- **Logical gaps:** The interpretation (small commutator $\implies$ eigenvectors of $J$ approximate those of $C$) is stated in Corollary 4.6 but requires Davis-Kahan or Bauer-Fike, which is invoked but not verified (need spectral gap conditions).
- **Rigor level:** 4/5 (the algebraic identity is solid; the eigenvalue consequence needs one more step)
- **Dependencies:** None

#### Corollary 4.6: Commutator-CV Correlation
- **Status:** CONJECTURE (the correlation $r = 0.965$ is empirical; the causal mechanism is plausible but not proved)
- **Rigor level:** 2/5

#### Theorem 4.7: Sufficient Conditions for Spectral Shape Preservation (4 parts)
- **Status:** PROVABLE
- **Statement clarity:** 3/5
- **Proof completeness:**
  - (a): Proved but only for $\sigma = \tanh$ (uses $\sigma'(z) = 1 - z^2$). Statement says "contractive activation" in general.
  - (b): Proved for row-stochastic $C$.
  - (c): Trivially true (static coupling has constant eigenvalues).
  - (d): Stated with supporting evidence but no proof.
- **Rigor level:** 3/5
- **Dependencies:** Commutator bound (Thm 4.5)

#### Proposition 5.2: Contractivity of tanh-Coupled Systems
- **Status:** PROVED
- **Statement clarity:** 4/5
- **Proof completeness:** Correct. Uses submultiplicativity and the bound $\|D\|_{op} \leq 1$.
- **Rigor level:** 4/5
- **Dependencies:** None

#### Theorem 5.3: Contraction Preserves Spectral Structure
- **Status:** PROVABLE
- **Statement clarity:** 3/5
- **Proof completeness:** The geometric convergence $\|C(x_{t+1}) - C(x_t)\| \leq L_C \rho(J)^t \|x_1 - x_0\|$ is correctly argued. The step to $d(\hat{\Lambda}(x_t), \hat{\Lambda}(x^*)) \leq K \rho(J)^t$ requires Lipschitz continuity of the eigenvalue map, which is standard (Weyl/Bauer-Fike) but the Lipschitz constant depends on spectral gaps that can degenerate.
- **Logical gaps:** Lipschitz constant $L_\Lambda$ of the eigenvalue map is not bounded in terms of the problem data.
- **Rigor level:** 3/5
- **Dependencies:** Contraction property (Prop 5.2), Lipschitz continuity of $C$
- **Notes:** The deeper question ("why is $I$ approximately constant during the transient?") is correctly identified as the real content.

#### Conjecture 5.4: Transient Spectral First Integral
- **Status:** CONJECTURE (appropriately labeled)
- **Rigor level:** N/A

#### Theorem 6.1: Jazz Theorem (3 parts)
- **Status:**
  - **(a) CONJECTURE** (not proved; $f(\epsilon)$ is unspecified)
  - **(b) WRONG** (direction of inequality; see below)
  - **(c) PROVED** (trivially, for static coupling)
- **Statement clarity:** 2/5.
  - Part (a): $f(\epsilon)$ continuous with $f(0) = 0$ is too weak to be useful. No explicit bound.
  - Part (b): The bound $\|x_t^{(1)} - x_t^{(2)}\| \geq \|x_0^{(1)} - x_0^{(2)}\| \cdot \exp(-\lambda t)$ with $\lambda > 0$ says trajectories DON'T CONVERGE FASTER THAN EXPONENTIAL. This is a lower bound on convergence rate, not a divergence claim. For a contractive system with unique fixed point, both trajectories converge to $x^*$, so $\|x_t^{(1)} - x_t^{(2)}\| \to 0$. There is no divergence.
  - Part (c): The proof is correct for static coupling (eigenvalues constant, so $I$ is trivially identical on both trajectories regardless of state).
- **Logical gaps:**
  - Part (a) is claimed but no proof is given.
  - Part (b) claims "trajectory divergence" but under contraction, trajectories converge. The multiple-fixed-points case requires $\rho(C) > 1$, which conflicts with earlier contractivity assumptions.
  - Part (c) is sound.
- **Rigor level:** 2/5
- **Dependencies:** Contraction theory (Thm 5.3), spectral shape stability

#### Corollary 6.2: Universal Spectral Fingerprint
- **Status:** CONJECTURE (follows from part (a) of Jazz Theorem, which is unproved)
- **Rigor level:** 1/5

#### Corollary 6.3: State-Space is Thin
- **Status:** CONJECTURE
- **Statement clarity:** 2/5. Level sets of a smooth function are generically codimension-1 manifolds, not "thin." The claim that trajectories are confined to "approximate level sets" is the empirical observation, not a theorem.
- **Rigor level:** 1/5

#### Theorem 7.2: Structural Conservation
- **Status:** WRONG (repeats the $I(x) = 1$ error from Theorem 3.1)
- **Rigor level:** 1/5

#### Theorem 7.4: Dynamical Conservation
- **Status:** PROVABLE (the bound has the right structure, but the proof is a sketch)
- **Statement clarity:** 3/5
- **Proof completeness:** The sketch identifies the right mechanism (perturbation theory for eigenvalues, Lipschitz control of $C$, commutator bounds on eigenvector rotation). Making it rigorous requires explicit constants and verifying Davis-Kahan conditions.
- **Rigor level:** 2/5
- **Dependencies:** Theorems 4.5, 5.3

#### Theorem 7.6: Transitional Instability
- **Status:** CONJECTURE (labeled as theorem but has no proof; describes a mechanism qualitatively)
- **Rigor level:** 1/5

#### Conjectures 8.1--8.5
- **8.1 (Lyapunov):** PARTIALLY REFUTED by MATH-LYAPUNOV-MONOTONICITY (not step-by-step monotone; monotone in expectation only).
- **8.2 (Universality):** OPEN. Empirical evidence for smooth activations; ReLU worse.
- **8.3 (Sharp Bound):** OPEN.
- **8.4 (Koopman):** OPEN. Strong numerical evidence in MATH-KOOPMAN-EIGENFUNCTION.
- **8.5 (Dimensional Scaling):** PARTIALLY REFUTED by MATH-DIMENSION-SCALING (exponent is $-0.28$, not $-1$).

---

### MATH-KOOPMAN-EIGENFUNCTION.md

#### Theorem 3.1: Approximate Koopman Eigenfunction
- **Status:** CONJECTURE (labeled as theorem; only a "proof strategy" is given, no actual proof)
- **Statement clarity:** 3/5. The statement is precise: $\mathcal{K}[I] = \lambda I + r$ with $|1-\lambda| \leq C_1\epsilon$ and $\|r\|/\|I\| \leq C_2\epsilon$.
- **Proof completeness:** The 4-step "proof strategy" is a plausible outline but each step has gaps:
  - Step 1 invokes Davis-Kahan without verifying spectral gap conditions.
  - Step 2 claims eigenbasis preservation implies shape stability — plausible but not proved.
  - Step 3 is essentially circular: "if $I$ doesn't change much, then $\mathcal{K}[I] \approx I$."
  - Step 4 (quantification) is where the actual work would be; it is entirely missing.
- **Logical gaps:** The constants $C_1, C_2$ are unspecified. No explicit dependence on $N$, coupling type, or trajectory properties.
- **Rigor level:** 2/5
- **Dependencies:** Commutator bound (MATH-SFI Thm 4.5), Davis-Kahan theorem
- **Notes:** The numerical evidence (10 experiments) is compelling. The result is likely true but the proof is missing.

#### Conjecture 3.2: Improved Eigenfunction
- **Status:** CONJECTURE (appropriately labeled)
- **Rigor level:** N/A

#### Theorem 5.1: Finite-Dimensional Invariant Subspace
- **Status:** CONJECTURE (labeled as theorem; proof sketch is too vague)
- **Statement clarity:** 1/5. The notation "$\mathcal{K}[\mathcal{F}_k] \subseteq \mathcal{F}_k + O(\epsilon) \cdot \mathcal{C}^\infty$" is not a well-defined mathematical statement. Multiplying a scalar bound by a function space is meaningless without specifying the topology and the sense of approximation.
- **Proof completeness:** The proof sketch assumes "for small states" (linearization regime) which trivializes the result — in the linear regime, eigenfunction analysis is standard.
- **Logical gaps:** The statement needs complete reformulation to be meaningful.
- **Rigor level:** 1/5

---

### MATH-JAZZ-THEOREM.md

#### Definition: Spectral Shape (Sections 1.2--1.3)
- **CRITICAL ISSUE:** $\gamma$ is defined here as the participation ratio: $\gamma(x) = (\sum|\lambda_i|^2)^2 / (\sum|\lambda_i|^4)$. This is DIFFERENT from the core document where $\gamma = \lambda_1 - \lambda_2$ (spectral gap). This means $I = \gamma + H$ is a fundamentally different quantity here.
- Additionally, the spectral shape uses $|\lambda_i|^2$ (squared absolute values), while the core document uses $\lambda_i$ (raw eigenvalues). For symmetric positive-definite $C$ these coincide up to normalization, but in general they do not.

#### Main Theorem: Spectral Shape Conservation (Section 2.1)
- **Status:** CONJECTURE (labeled as theorem; proof is a sketch with fundamental logical errors)
- **Statement clarity:** 3/5. The statement is precise: $\lim_{t\to\infty} d_\mathcal{S}(x_t, y_t) \leq g(\epsilon)$ with $g(\epsilon) \to 0$.
- **Proof completeness:** The 4-step proof sketch has fundamental issues:
  - Lemma 3 claims the invariant set has "neutral directions" that preserve spectral shape, but under contraction, the invariant set is a single point (no neutral directions).
  - Lemma 4 claims trajectory divergence on the invariant set, but under contraction with a unique fixed point, $\Omega = \{x^*\}$ is 0-dimensional.
- **Logical gaps:**
  - **Fatal:** The theorem claims trajectory divergence under contraction. These are contradictory. Contraction $\implies$ all trajectories converge to the same $x^*$ $\implies$ $\|x_t - y_t\| \to 0$, NOT divergence.
  - The "proof sketch" avoids confronting this contradiction by vaguely invoking "attractors that are not equilibria," but the setup assumes contractivity, which produces equilibria.
- **Rigor level:** 1/5
- **Dependencies:** Contraction theory, Davis-Kahan
- **Notes:** The spectral shape convergence RESULT follows trivially from contraction: if $x_t \to x^*$ and $y_t \to x^*$, then $\mathcal{S}(x_t) \to \mathcal{S}(x^*)$ and $\mathcal{S}(y_t) \to \mathcal{S}(x^*)$ by continuity. The interesting claim would be that $\mathcal{S}$ converges FASTER than $x$ (the "slow variable" property), but this is not what the theorem states.

#### Lemma 1: Spectral Perturbation
- **Status:** PROVABLE
- **Rigor level:** 3/5 (standard perturbation theory, needs $D > 0$)

#### Lemma 2: Invariant Set on Level Surface
- **Status:** PROVABLE (standard LaSalle, but the claimed structure of the invariant set is wrong)
- **Rigor level:** 2/5

#### Lemma 3: Shape Preservation
- **Status:** CONJECTURE (the key technical claim is stated without proof)
- **Rigor level:** 1/5

#### Lemma 4: Trajectory Divergence is Generic
- **Status:** WRONG (contradicts contraction; unique fixed point means $\Omega = \{x^*\}$, dimension 0)
- **Rigor level:** 0/5

#### Theorem: Platonic Dice (Section 6.1)
- **Status:** PROVABLE (trivially, from contraction)
- **Statement clarity:** 3/5
- The claim $\mathcal{S}(X^{(\omega)}) \to \mathcal{S}^*$ a.s. follows trivially from $X^{(\omega)} \to x^*$ a.s. (contraction) and continuity of $\mathcal{S}$.
- **Rigor level:** 3/5 (correct but trivial under contraction)

#### Claims about being "stronger than Oseledets" (Sections 7.3--7.4)
- **Status:** WRONG (misleading comparison)
- Oseledets applies to general ergodic systems (including non-contractive, chaotic, measure-preserving). The Jazz Theorem applies only to contracting systems with unique fixed points. Claiming it's "stronger" because it gives pointwise convergence ignores that pointwise convergence is trivial under contraction. Oseledets gives information (Lyapunov exponents) for systems where pointwise convergence does NOT hold.
- **Rigor level:** 1/5

---

### MATH-TEMPORAL-GEOMETRY.md

#### Claim 1.1 / Theorem 1.1: Temporal First Integral
- **Status:** PROVED
- **Statement clarity:** 4/5. Well-stated distinction between state-functional and trajectory-integral.
- **Proof completeness:** Complete. The argument that conservation is a trajectory property, not a state property, is sound.
- **Rigor level:** 4/5
- **Dependencies:** None
- **Notes:** Conceptual observation, correctly stated and proved.

#### Theorem 2.1: Conservation Wavelength
- **Status:** CONJECTURE (too vague to be a theorem)
- **Statement clarity:** 1/5. "Characteristic frequency $\omega_I$" is not defined. The proportionality is dimensional analysis.
- **Rigor level:** 1/5

#### Theorem 2.2: Temporal-Spectral Uncertainty
- **Status:** CONJECTURE (analogy, not a theorem)
- **Statement clarity:** 1/5. $\Delta T \cdot \Delta I \geq C_K / T$ does not have well-defined variables. $\Delta T$ is called "observation window" but is not a standard deviation of a conjugate variable. The Gabor analogy is suggestive but mathematically unsubstantiated.
- **Rigor level:** 1/5

#### Theorem 3.1: Conservation $\leftrightarrow$ Low Curvature
- **Status:** PROVABLE
- **Statement clarity:** 3/5
- **Proof completeness:** The chain rule argument is correct. The connection between $\nabla I \cdot T_t$ and curvature $\kappa_t$ needs one more step.
- **Rigor level:** 2/5

#### Theorem 3.2: Conservation and Normal Component
- **Status:** PROVABLE (but the bound may have incorrect scaling)
- **Statement clarity:** 2/5. The bound $|\nabla I \cdot T_t| \leq \epsilon / (T \cdot \|\dot\gamma_t\|)$ divides by $T$, implying better alignment for longer trajectories, which requires justification.
- **Rigor level:** 2/5

#### Theorem 4.1: Inter-Snap Conservation
- **Status:** PROVED
- **Statement clarity:** 4/5
- **Proof completeness:** Direct Lipschitz argument. Fully rigorous.
- **Rigor level:** 5/5
- **Dependencies:** Lipschitz continuity of $I \circ \Phi$

#### Theorem 4.2: Substrate Invariance via Universality
- **Status:** CONJECTURE (empirically supported but not proved)
- The limit $\epsilon \to 0$ statement is trivially true by continuity. The substantive claim (conservation constant independent of $\epsilon$ above breakdown) is empirical.
- **Rigor level:** 2/5

#### Theorem 4.3: Snap-Perturbation Decomposition
- **Status:** PROVED
- **Statement clarity:** 4/5
- **Proof completeness:** Telescoping perturbation argument is standard and correct. Geometric series bound for contractive perturbations is rigorous.
- **Rigor level:** 5/5
- **Dependencies:** Contraction property

#### Theorem 5.1: Necessity of Computation
- **Status:** PROVED (trivially)
- **Statement clarity:** 4/5
- **Proof completeness:** Correct: for state-dependent $C$, $C(x^*) \neq C(x_0)$ generically.
- **Rigor level:** 4/5

#### Theorem 5.2: Conservation as Path-Independent Invariant
- **Status:** PARTIALLY WRONG
- Part (i): **PROVED** — unique fixed point under contraction means $I(x^*)$ is well-defined.
- Part (ii): **WRONG** — claims $I(x_t) \to I(x^*)$ **monotonically**. MATH-LYAPUNOV-MONOTONICITY explicitly shows this is false (50% upward steps across 5,500 transitions). Convergence is true; monotonicity is false.
- Part (iii): **PROVED** — $I(x^*)$ depends only on $\Phi$ (hence on $C, \sigma$).
- **Rigor level:** 3/5 (for parts (i) and (iii); part (ii) is wrong)

#### Theorem 5.3: Information-Theoretic Lower Bound
- **Status:** PROVED
- **Statement clarity:** 4/5
- **Proof completeness:** Standard convergence rate argument. Fully rigorous.
- **Rigor level:** 5/5
- **Dependencies:** Contraction, Lipschitz continuity of $I$

#### Theorems 6.1, 6.2, 6.3: Compaction and Compression
- **Status:** PROVED (trivially)
- **Statement clarity:** 3/5
- **Proof completeness:** Correct but vacuous: ANY scalar function of an $N \times N$ matrix gives $O(N^2)$ compression.
- **Rigor level:** 4/5

#### Theorem 7.1: Temporal Geometry Synthesis
- **Status:** PARTIALLY WRONG (inherits the monotonicity error from Thm 5.2(ii))
- **Rigor level:** 2/5

---

### MATH-LATTICE-SPLINE.md

#### Proposition 1.1: Spline from Dynamics
- **Status:** PROVABLE
- Standard spline approximation theory. The $O(r_\Lambda^2)$ derivative approximation on uniform knots is correct.
- **Rigor level:** 3/5

#### Theorem 1.1: Curvature Bounds from Conservation
- **Status:** PROVABLE
- Depends on MATH-TEMPORAL-GEOMETRY Theorem 3.1, which has gaps.
- **Rigor level:** 2/5
- **Dependencies:** TEMPORAL-GEOMETRY Thm 3.1

#### Theorem 2.1: Lattice Sampling Preservation
- **Status:** PROVED
- Geometric series argument for accumulated snap perturbations under contraction. Standard and rigorous.
- **Rigor level:** 5/5
- **Dependencies:** Contraction, Lipschitz continuity of $I$

#### Corollary 2.1: Eisenstein Optimality
- **Status:** PROVED (known result — hexagonal lattice achieves smallest covering radius in 2D by Thue's theorem)
- **Rigor level:** 5/5

#### Theorem 2.2: Snap-Spline Correspondence
- **Status:** PROVABLE
- **Rigor level:** 3/5 (the factor of 2 needs explicit derivation)

#### Theorem 3.1: Hexagonal Gabor Frames
- **Status:** PROVED (known result in Gabor analysis)
- **Rigor level:** 4/5

#### Theorem 3.2: Quadratic Encoding
- **Status:** PROVED (trivially)
- **Rigor level:** 4/5

#### Theorem 3.3: Compressed Sensing on Eisenstein Lattice
- **Status:** PROVABLE (with caveats)
- Conservation gives approximate sparsity, not exact. Compressed sensing guarantees (Candes-Romberg-Tao) need modification for approximate sparsity (stable recovery). The $O(\log T)$ bound holds approximately.
- **Rigor level:** 3/5

#### Theorem 4.1: Finger-on-the-Spline (4 parts)
- **Status:**
  - (1): **PROVED** (follows from Theorem 2.2)
  - (2): **PROVED** (trivial: continuity of spline construction)
  - (3): **CONJECTURE** (the identity $\mathcal{F}[\gamma] = C + \int\kappa^2\,dt \cdot f(\nabla I) + O(\epsilon)$ is stated without defining $f$ or proving the relationship)
  - (4): **CONJECTURE** (references Koopman result which is itself unproved)
- **Rigor level:** 2/5 (average across parts)

#### Corollary 4.1: Jam-Independence of Snapping
- **Status:** PROVABLE (if Jazz Theorem were proved)
- **Rigor level:** 2/5

#### Theorems 5.1--5.2: Constraint Feasibility and Lattice Density
- **Status:** PROVED
- Standard lattice geometry arguments.
- **Rigor level:** 4/5

#### Theorem 5.3: SplineLinear Conservation
- **Status:** PROVABLE
- Restates the snap perturbation bound in the SplineLinear context.
- **Rigor level:** 3/5

#### Theorem 6.1: Lattice-Spline Synthesis
- **Status:** PROVABLE (synthesis of previous results; inherits their rigor levels)
- **Rigor level:** 3/5

---

### MATH-LYAPUNOV-MONOTONICITY.md

#### Result 2.1: $I$ is NOT Monotone
- **Status:** EMPIRICAL RESULT (definitively established numerically)
- 5,500 state transitions across 11 configurations. 46--51% upward steps for all state-dependent coupling. This is robust and well-documented.
- **Rigor level:** N/A (empirical, but highly convincing)
- **Notes:** CONTRADICTS MATH-TEMPORAL-GEOMETRY Theorem 5.2(ii) which claims monotonicity.

#### Result 3.1: Exponential Decay Law
- **Status:** EMPIRICAL RESULT (strongly supported)
- $dI/dt \approx -\alpha(I - I^*)$ with $r = 0.999$ across 5 samples. Very tight fit.
- **Rigor level:** N/A (empirical)

#### Conjecture 3.2: $\alpha \approx 1 - \rho(J)$
- **Status:** WRONG (as $\approx$); PLAUSIBLE (as $\leq$)
- The document's own data shows $\alpha \approx 0.003$ vs $1 - \rho(J) \approx 0.15$ — a 50x discrepancy. The conjecture should be an upper bound, not an approximation.
- **Rigor level:** N/A

#### Conjecture 6.1: Contraction Rate vs. $I$-Decay Rate
- **Status:** PLAUSIBLE (as inequality $\alpha \leq 1 - \rho(J)$; consistent with data showing $\alpha \ll 1 - \rho(J)$)
- **Rigor level:** N/A

---

### MATH-DIMENSION-SCALING.md

#### Main Finding: CV $\sim N^{-0.28}$ for Attention Coupling
- **Status:** EMPIRICAL RESULT
- $R^2 = 0.936$ for the power law fit. Monotonic decrease clearly established across N = 5 to 150.
- The conjectured $O(1/N)$ is definitively rejected ($t = 29.6$).
- **Rigor level:** N/A (empirical)

#### Cross-Instance Scaling: CV $\sim N^{-0.87}$
- **Status:** EMPIRICAL RESULT
- $R^2 = 0.993$. Consistent with RMT concentration of measure.
- **Rigor level:** N/A (empirical)

#### Revised Conjecture 8.5
- **Status:** Well-supported empirical conjecture
- **Rigor level:** N/A

---

### METAL-TO-PLATO.md

No new formal theorems. Mathematical claims are restatements from other documents.

#### "Substrate Invariance Theorem" (Sections 0.4, 4.2)
- **Status:** EMPIRICAL OBSERVATION (not a theorem)
- The claim that the conservation constant is flat from 2-bit to 64-bit is empirically supported but not proved. The argument that "shape survives monotone quantization" is intuitive but needs formalization.
- **Rigor level:** 1/5 (as a theorem; strong as an empirical observation)

---

## Cross-Document Issues

### CRITICAL: Inconsistent Definition of $\gamma$

| Document | $\gamma$ defined as | Formula |
|----------|-------------------|---------|
| MATH-SPECTRAL-FIRST-INTEGRAL | Spectral gap | $\lambda_1 - \lambda_2$ |
| MATH-JAZZ-THEOREM | Participation ratio | $(\sum\|\lambda_i\|^2)^2 / \sum\|\lambda_i\|^4$ |
| MATH-TEMPORAL-GEOMETRY | Participation ratio | $(\sum\lambda_i)^2 / \sum\lambda_i^2$ |
| MATH-KOOPMAN-EIGENFUNCTION | (inherits core) | $\lambda_1 - \lambda_2$ |
| MATH-LATTICE-SPLINE | (inherits core) | $\lambda_1 - \lambda_2$ |
| MATH-LYAPUNOV-MONOTONICITY | (ambiguous) | not explicitly restated |
| METAL-TO-PLATO | Spectral gap | $\lambda_1 - \lambda_2$ |

**Consequence:** The "spectral first integral" $I = \gamma + H$ is a DIFFERENT mathematical object in different documents. Theorems proved in one document do not apply to the quantity studied in another. This must be resolved before any cross-document theorem can be considered valid.

### Monotonicity Contradiction

- **MATH-TEMPORAL-GEOMETRY Theorem 5.2(ii):** "$I(x_t) \to I(x^*)$ monotonically"
- **MATH-LYAPUNOV-MONOTONICITY Result 2.1:** "$I$ is NOT monotone. ~50% upward steps."
- **Verdict:** The Temporal Geometry claim is wrong. The Lyapunov Monotonicity result is well-supported by 5,500 transitions across 11 configurations.

### Contraction vs. Divergence Contradiction

- **MATH-SPECTRAL-FIRST-INTEGRAL Section 5:** Assumes contraction ($\rho(J) < 1$, unique fixed point).
- **MATH-JAZZ-THEOREM Section 3, Lemma 4:** Claims trajectory divergence and that the invariant set $\Omega$ has $\dim \geq 1$.
- **Verdict:** Under contraction with unique fixed point, $\Omega = \{x^*\}$ has dimension 0. Trajectories converge, not diverge. The Jazz Theorem's divergence claim is fundamentally incompatible with its contraction assumption. To rescue the Jazz Theorem, one would need to consider non-contractive systems (chaotic attractors, limit cycles), but then the conservation mechanism (which relies on contraction) would need a different justification.

### Eigenvalue Domain Issues

Different documents use different eigenvalue normalizations:
- Raw eigenvalues $\lambda_i$ (can be negative for non-symmetric $C$)
- Absolute values $|\lambda_i|$
- Squared absolute values $|\lambda_i|^2$
- Eigenvalues of symmetrized $(C + C^T)/2$

The participation entropy $H = -\sum p_i \ln p_i$ requires $p_i \geq 0$. If eigenvalues are negative, the normalized probabilities can be negative, making $H$ undefined. The documents are inconsistent about how to handle this.

### Experimental Noise vs. Deterministic Theory

- The core theory is stated for deterministic systems.
- Experiments in MATH-LYAPUNOV-MONOTONICITY use additive noise $\sigma = 0.05$.
- Experiments in MATH-DIMENSION-SCALING use additive noise $\sigma = 0.1$.
- The Lyapunov document explicitly notes noise is required to keep dynamics non-trivial.
- **Verdict:** The experimental results validate the noisy/stochastic system, not the deterministic theorems as stated. The gap between theory (deterministic) and evidence (stochastic) should be acknowledged.

### Three Regimes: Internal Consistency

The regime definitions (structural, dynamical, transitional) are used consistently across documents where they appear. This is one area of good cross-document consistency.

---

## The Strongest Honest Claim

Given the audit results, the strongest theorem that can be honestly claimed with full rigor is:

> **Theorem (Spectral Convergence under Contraction).** For the system $x_{t+1} = \sigma(C(x_t) x_t)$ with contractive $\sigma$ ($\text{Lip}(\sigma) \leq 1$, $\sigma(0) = 0$), continuous $C: \mathbb{R}^N \to \mathbb{R}^{N\times N}$ with $\|C(x)\|_{op} \leq L_C$, suppose the system is contracting on a compact invariant set $K$ with contraction rate $\rho < 1$ and unique fixed point $x^* \in K$. Let $I(x)$ be any Lipschitz functional of the eigenvalues of $C(x)$ with Lipschitz constant $L_I$. Then:
>
> $$|I(x_t) - I(x^*)| \leq L_I \cdot L_C \cdot \rho^t \cdot \|x_0 - x^*\|$$
>
> In particular, $\text{CV}(I) \to 0$ as $T \to \infty$.

This is a direct consequence of contraction + Lipschitz continuity and is FULLY RIGOROUS. It says: any continuous spectral observable converges exponentially under contraction. The specific choice $I = \gamma + H$ is one such observable.

**What this does NOT explain** (and what makes the empirical observations genuinely interesting):
1. Why $I = \gamma + H$ specifically varies much less than other observables like $\|x\|^2$ during the transient.
2. The commutator-conservation correlation ($r = 0.965$).
3. The approximate Koopman eigenfunction property ($\lambda \approx 1$).
4. The specific scaling $\text{CV} \sim N^{-0.28}$.

These are genuine empirical discoveries that deserve rigorous theorems, but those theorems are not yet proved.

**For the next strongest claim**, one would need to prove the commutator bound: $\text{CV}(I) \leq C(N) \cdot \|[D,C]\|_F / \|C\|_F$ (Theorem 7.4). This requires:
1. A rigorous perturbation bound for the eigenvalue distribution of $C(x)$ under one step of the dynamics.
2. Translation of the commutator condition into eigenvector stability via Davis-Kahan.
3. Summation over the trajectory with geometric decay from contraction.
This is feasible with standard perturbation theory tools and should be the top formalization priority.

---

## Proof Formalization Priority List

| Priority | Theorem | Why Important | Gap Size | Feasibility |
|:---:|---|---|---|---|
| 1 | Commutator-CV bound (Thm 7.4) | Core mechanistic result; explains WHY $I$ is approximately conserved | Medium — needs eigenvalue perturbation theory + Davis-Kahan | HIGH |
| 2 | Approximate Koopman eigenfunction (Koopman Thm 3.1) | Deepest structural characterization; subsumes other results | Large — needs quantitative Koopman residual bound | MEDIUM |
| 3 | Fix Rank-1 Theorem (Thm 3.1) | Foundation of structural regime; currently wrong as stated | Small — just needs correct statement with consistent definitions | TRIVIAL |
| 4 | Spectral shape stability (Thm 4.3) | Key logical step; needs Tr(C) assumption made explicit | Small — add row-stochastic assumption or use PR definition | HIGH |
| 5 | Dimensional scaling exponent | Would explain the $N^{-0.28}$ law | Large — needs softmax concentration analysis | LOW |
| 6 | Transient conservation quality | Would explain why $I$ varies little during transient, not just that it converges | Large — the deepest open question | MEDIUM |
| 7 | Jazz Theorem (proper version) | Needs complete reformulation: remove divergence claim, state that $\mathcal{S}$ converges faster than $x$ | Medium — statement restructuring + slow-variable proof | MEDIUM |

---

## Key Definitions That Need Tightening

1. **$\gamma$ (CRITICAL):** Must be defined consistently across ALL documents. Choose either spectral gap ($\lambda_1 - \lambda_2$) or participation ratio ($(\sum\lambda_i)^2 / \sum\lambda_i^2$). The conserved quantity is different for each choice. Recommend: use distinct symbols ($\gamma_{\text{gap}}$ and $\text{PR}$) to avoid confusion.

2. **Eigenvalue domain:** Specify whether eigenvalues are of $C(x)$, $(C + C^T)/2$, or $|C|$. For asymmetric $C$ (attention coupling), eigenvalues can be complex. The participation entropy requires non-negative probabilities — how are complex eigenvalues handled?

3. **"Conserved" vs. "convergent":** The documents use "conserved" ($I$ is constant) when the empirical finding is "convergent" ($I$ approaches $I(x^*)$ with rate $\alpha \approx 0.003$). A conserved quantity stays constant; this quantity converges to a limit. The Lyapunov document shows the distinction clearly. "Approximate slow observable" or "near-invariant" would be more accurate than "first integral."

4. **"Spectral first integral":** A first integral is exactly conserved ($I(x_{t+1}) = I(x_t)$ for all $t$). The observed quantity has $\text{CV} \sim 0.01$--$0.03$ and monotone expected decrease ($\alpha \approx 0.003$). This is an approximate near-invariant, not a first integral.

5. **Jazz Theorem scope:** Must specify whether the setting is contractive (unique fixed point, no divergence possible) or non-contractive (rich attractor, divergence possible but conservation mechanism unclear). Currently tries to have both.

6. **Trajectory ensemble vs. single trajectory:** The experimental $\text{CV}(I)$ is computed along single trajectories. The cross-instance CV is computed across different coupling draws. These measure different things and scale differently ($N^{-0.28}$ vs. $N^{-0.87}$). They should not be conflated.

---

## Summary Statistics

| Metric | Count |
|--------|-------|
| **Total theorems/propositions/lemmas audited** | 48 |
| **PROVED** | 12 |
| **PROVABLE** (correct sketch, closable gaps) | 12 |
| **CONJECTURE** (fundamental gaps, mislabeled as theorem) | 14 |
| **WRONG** (stated result is false or contradicted) | 5 |
| **EMPIRICAL** (numerical results, appropriately labeled) | 5 |
| **Average rigor level** | **2.4 / 5** |

### Breakdown of PROVED results (rigor 4--5/5):
1. Theorem 4.5 in CORE (commutator algebraic identity)
2. Proposition 5.2 in CORE (contractivity bound)
3. Theorem 1.1 in TEMPORAL-GEOMETRY (conservation is trajectory property)
4. Theorem 4.1 in TEMPORAL-GEOMETRY (inter-snap Lipschitz bound)
5. Theorem 4.3 in TEMPORAL-GEOMETRY (snap-perturbation decomposition)
6. Theorem 5.1 in TEMPORAL-GEOMETRY (necessity of computation)
7. Theorem 5.3 in TEMPORAL-GEOMETRY (info-theoretic lower bound)
8. Theorems 6.1/6.2/6.3 in TEMPORAL-GEOMETRY (compaction — trivially correct)
9. Theorem 2.1 in LATTICE-SPLINE (lattice sampling preservation)
10. Corollary 2.1 in LATTICE-SPLINE (Eisenstein optimality — known result)
11. Theorem 3.1 in LATTICE-SPLINE (hexagonal Gabor frames — known result)
12. Theorem 6.1(c) in CORE (Jazz Theorem part c — trivial for static coupling)

### WRONG results:
1. Theorem 3.1 in CORE (Rank-1 conservation: $I = 1$ — proof shows $\gamma = \|x\|^2/N$)
2. Corollary 3.2 in CORE ($\text{CV} = 0$ for rank-1 — depends on which $\gamma$)
3. Theorem 7.2 in CORE (repeats rank-1 error)
4. Theorem 5.2(ii) in TEMPORAL-GEOMETRY (monotonicity — disproved by 5,500 experiments)
5. Lemma 4 in JAZZ-THEOREM (trajectory divergence under contraction — logical impossibility)

---

## Final Assessment

The spectral first integral theory contains a **genuinely novel empirical observation**: for contractive coupled nonlinear systems, the quantity $\gamma + H$ (however $\gamma$ is defined) varies remarkably little along trajectories — much less than $\|x\|^2$, and in a way predicted by the commutator $\|[D,C]\|$. The approximate Koopman eigenfunction property ($\lambda \approx 1$) is striking. The dimensional scaling and activation universality findings are interesting.

However, the theoretical apparatus surrounding this observation is **premature**. The inconsistent definitions, logical contradictions (contraction vs. divergence, monotonicity claims), and gap-filled proofs mean that **none of the main non-trivial theorems can be cited as fully proved** in the current form. The proved results are either trivial consequences of contraction/Lipschitz theory or known results from lattice geometry/Gabor analysis.

**Recommendations:**
1. **Fix definitions first.** Unify $\gamma$ across all documents. Specify eigenvalue domain.
2. **Withdraw wrong results.** Theorems 3.1/7.2 (as stated), Theorem 5.2(ii), Lemma 4 of Jazz Theorem.
3. **Reformulate the Jazz Theorem.** Remove divergence claim; state as a slow-variable result.
4. **Rename "first integral."** Use "approximate slow observable" or "near-invariant."
5. **Focus formalization on Priority 1:** The commutator-CV bound is the most impactful provable result and would provide the theoretical foundation the empirical work deserves.

---

*Audit completed 2026-05-17. Mathematical reputation depends on not claiming more than is proved.*
