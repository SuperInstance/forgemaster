# PROOF AUDIT REPORT

**Auditor:** Claude Opus 4.6 (mathematical proof audit)
**Date:** 2026-05-17
**Documents audited:** 8 (MATH-SPECTRAL-FIRST-INTEGRAL, MATH-KOOPMAN-EIGENFUNCTION, MATH-JAZZ-THEOREM, MATH-TEMPORAL-GEOMETRY, MATH-LATTICE-SPLINE, MATH-LYAPUNOV-MONOTONICITY, MATH-DIMENSION-SCALING, METAL-TO-PLATO)

---

## Executive Summary

The corpus presents an empirically motivated theory of approximate spectral conservation in nonlinear coupled dynamical systems. **The strongest rigorous results are elementary**: rank-1 algebraic identities (Theorem 3.1), tautological implications (Theorem 4.3: constant shape implies constant functional of shape), and standard perturbation bounds (Theorem 4.5). The central empirical claim — that $I(x) = \gamma(x) + H(x)$ is approximately conserved along trajectories — is well-supported by numerical evidence but has **no rigorous proof**. The "proofs" of the substantive theorems (Jazz Theorem, dynamical conservation bound, Koopman eigenfunction, temporal geometry synthesis) are proof sketches with critical gaps: missing quantitative bounds, unstated regularity assumptions, circular reasoning between documents, and conflation of fixed-point convergence with genuine transient conservation. The overall rigor level is **2.1/5** — well above handwaving but far below publishable mathematics.

**The strongest honest claim:** "For rank-1 coupling, $H = 0$ and $\text{PR} = 1$ exactly (trivial). For static coupling, $I$ is trivially constant. For general state-dependent coupling with contractive activation, numerical experiments across thousands of configurations show $\text{CV}(I) < 0.03$, with the commutator $\|[D,C]\|$ as the best predictor of conservation quality ($r = 0.965$). This is an empirical observation awaiting rigorous explanation."

**Biggest gaps:** (1) No rigorous proof that spectral shape stability holds during transients; (2) The definition of $\gamma$ is inconsistent across documents (spectral gap vs participation ratio); (3) The "Jazz Theorem" conflates fixed-point convergence with a deeper conservation principle and contains a sign error in part (b).

---

## Document-by-Document Audit

### MATH-SPECTRAL-FIRST-INTEGRAL

#### Definition 1.1 (Coupled Nonlinear Recurrence)
- **Status:** WELL-DEFINED (with caveats)
- **Statement clarity:** 3/5. Standing assumptions (A1)-(A3) are reasonable. However, (A3) adds nothing mathematically — it just says $C$ is parameterized, which is always true.
- **Issue:** For asymmetric $C(x)$, eigenvalues can be complex. The document acknowledges this (Def 2.1) but then uses real eigenvalue ordering throughout. The symmetrization $\frac{1}{2}(C + C^T)$ is mentioned but not consistently applied.

#### Proposition 1.7 (Existence via Contraction)
- **Status:** PROVABLE
- **Statement clarity:** 3/5. The condition $L_C < 1$ is stated but the proof immediately admits this is rarely satisfied in practice.
- **Proof completeness:** 2/5. The proof writes $\|F(x) - F(y)\| \leq \|D(x)C(x)x - D(y)C(y)y\|$ but does not actually bound this by $\alpha\|x-y\|$ for any $\alpha < 1$. The bound requires Lipschitz continuity of $C(\cdot)$ and careful handling of the product $D(x)C(x)x$. This is doable with standard techniques but is not done.
- **Logical gaps:** The statement says $L_C \cdot \text{Lip}(\sigma) < 1$ suffices, which is correct by Banach but is never verified for any example coupling (attention has $\|C\|_{\text{op}} = 1$, so $L_C \cdot 1 = 1$, which is NOT strictly less than 1).
- **Rigor level:** 2/5
- **Dependencies:** Banach fixed-point theorem (standard)

#### Theorem 3.1 (Rank-1 Conservation)
- **Status:** WRONG as originally stated, then PROVED in the corrected version
- **Statement clarity:** The original statement claims $\gamma(x) = 1$, $H(x) = 0$, $I(x) = 1$ "exactly." The proof then immediately discovers that $\gamma = \|x\|^2/N$ depends on $x$, contradicting the statement. The document self-corrects mid-proof ("Wait — we must be careful"), which is honest but indicates the theorem was stated before being verified.
- **Revised statement analysis:** The revised claim is: for rank-1 $C(x) = xx^T/N$, $H = 0$ and $\text{PR} = 1$ exactly, independent of $x$. This is **correct and trivial** — a rank-1 matrix has one nonzero eigenvalue, so the normalized distribution is a point mass.
- **Proof completeness:** 4/5 for the revised statement. The claim about $\gamma$ conservation reducing to $\|x\|^2$ conservation is correct, but the "self-normalizing property of $\tanh$" is hand-waved.
- **Rigor level:** 3/5 (for revised statement)
- **Notes:** The original $I(x) = 1$ claim is inconsistent with the definition $I = \gamma + H$ where $\gamma = \lambda_1 - \lambda_2 = \|x\|^2/N$. The revised statement effectively drops $\gamma$ from the "conserved" part and only claims $H$ and PR are conserved. This is an important distinction that propagates through the theory.

#### Conjecture 3.3 (Rank-$k$ Structural Conservation)
- **Status:** CONJECTURE
- **Statement clarity:** 2/5. "If the eigenvalue distribution shape is preserved, then $I(x)$ is conserved" is nearly tautological — $I$ is a functional of the eigenvalue shape.
- **Rigor level:** 1/5
- **Notes:** The supporting evidence (hybrid coupling) is empirical only.

#### Theorem 4.3 (Spectral Shape Stability Implies Conservation)
- **Status:** PROVABLE (but nearly tautological)
- **Statement clarity:** 4/5. Clear statement: constant normalized eigenvalue distribution implies constant $H$.
- **Proof completeness:** 3/5. The proof is correct for $H$ (entropy of constant distribution is constant). For $\gamma$, it requires BOTH shape constancy AND scale constancy ($\text{Tr}(C)$ constant). The proof acknowledges this ("If both the shape $\{p_i\}$ and the scale $\text{Tr}(C)$ are constant") but the hypothesis only states shape constancy. **Gap:** Shape constancy alone does NOT imply $\gamma$ constancy unless $\text{Tr}(C)$ is also constant.
- **Logical gaps:** The conclusion $I = \gamma + H$ constant requires $\text{Tr}(C)$ constant, which is an additional assumption not in the hypothesis.
- **Rigor level:** 3/5
- **Dependencies:** None (direct computation)

#### Theorem 4.5 (Commutator Bounds Conservation Quality)
- **Status:** PROVED (the qualitative relationship; the stated bound has an error)
- **Statement clarity:** 3/5. The statement $\|J - cC\|_F \leq \|[D,C]\|_F$ needs $c$ specified.
- **Proof completeness:** 4/5. The algebra $J = (cI + \Delta)C = cC + \Delta C$ and $[D,C] = [\Delta, C]$ is correct. However, the stated bound $\|J - cC\|_F \leq \|[D,C]\|_F$ does not follow. The proof shows $\|J - cC\| = \|\Delta C\|$, while $\|[D,C]\| = \|\Delta C - C\Delta\|$. By the triangle inequality, $\|\Delta C\| \leq \|[D,C]\| + \|C\Delta\|$, so the commutator norm does NOT upper bound $\|\Delta C\|$ in general. The correct relationship is: $\|[D,C]\| \leq 2\|\Delta\|\|C\|$ and $\|\Delta C\| \leq \|\Delta\|\|C\|$, giving $\|\Delta C\| \leq \|C\| \cdot \|[D,C]\| / (2\|C\|) = \|[D,C]\|/2$ only if $\|\Delta\| = \|[D,C]\|/(2\|C\|)$, which is circular.
- **Logical gaps:** The quantitative bound as stated is not correct. The qualitative insight (small commutator → $J$ close to scalar multiple of $C$) is sound.
- **Rigor level:** 2/5 (qualitative insight correct, quantitative bound wrong)
- **Dependencies:** Matrix norm submultiplicativity

#### Corollary 4.6 (Commutator-CV correlation)
- **Status:** CONJECTURE (empirical)
- **Statement clarity:** 3/5. The empirical correlation $r = 0.965$ is well-documented.
- **Proof completeness:** 1/5. The "proof" is a verbal argument with each implication plausible but unquantified.
- **Rigor level:** 1/5

#### Theorem 4.7 (Sufficient Conditions for Spectral Shape Preservation)
- **Status:** PROVED for (a) and (b); trivial for (c); CONJECTURE for (d)
- **Proof of (a):** Correct. If $\|x\| \ll 1$, then $\sigma'(Cx) \approx 1$, so $D \approx I$, so $[D,C] \approx 0$.
- **Proof of (b):** Correct for row-stochastic $C$. Uniform $x$ gives uniform $D$ when row sums are equal.
- **Condition (c):** Trivially true (static $C$ has constant eigenvalues).
- **Condition (d):** Empirical observation, not a theorem.
- **Rigor level:** 3/5 for (a)-(b), 4/5 for (c), 1/5 for (d)

#### Proposition 5.2 (Contractivity of tanh-Coupled Systems)
- **Status:** PROVED
- **Statement clarity:** 4/5. Clear and standard.
- **Proof completeness:** 4/5. The bound $\rho(J) \leq \|D\|_{\text{op}} \cdot \|C\|_{\text{op}} \leq 1$ is correct.
- **Rigor level:** 4/5

#### Theorem 5.3 (Contraction Preserves Spectral Structure)
- **Status:** PROVABLE
- **Statement clarity:** 3/5.
- **Proof completeness:** 3/5. The proof sketch uses Lipschitz continuity of the eigenvalue map (valid by Weyl's inequality for symmetric matrices). The constant $K$ is bounded but not computed.
- **Logical gaps:** This only proves convergence to $I(x^*)$, NOT transient conservation. The document correctly identifies this.
- **Rigor level:** 3/5

#### Conjecture 5.4 (Transient Spectral First Integral)
- **Status:** CONJECTURE
- **Rigor level:** 1/5

#### Theorem 6.1 (Jazz Theorem)
- **Status:** Part (c) PROVED (trivial), Parts (a)-(b) CONJECTURE
- **Part (a):** Claims spectral shapes are close if both trajectories have small CV. Not proved — small individual CVs do not imply the shapes are close to EACH OTHER.
- **Part (b):** The bound $\|x_t^{(1)} - x_t^{(2)}\| \geq \|x_0^{(1)} - x_0^{(2)}\| \cdot \exp(-\lambda t)$ is a LOWER bound, but for a contracting system this says nothing useful (contraction gives an UPPER bound that decreases). **Sign/direction error.**
- **Part (c):** Correct but trivial (for static coupling, eigenvalues are constant regardless of trajectory).
- **Rigor level:** 2/5 overall

#### Theorem 7.2 (Structural Conservation)
- **Status:** PROVED (trivial)
- **Rigor level:** 4/5
- **Notes:** Inherits the $\gamma$ issue from Theorem 3.1.

#### Theorem 7.4 (Dynamical Conservation)
- **Status:** CONJECTURE (proof sketch with critical gaps)
- **Statement clarity:** 3/5.
- **Proof completeness:** 2/5. Invokes perturbation theory without closing the argument.
- **Rigor level:** 2/5

#### Theorem 7.6 (Transitional Instability)
- **Status:** CONJECTURE (descriptive, not proved)
- **Rigor level:** 1/5

#### Conjecture 8.1 (Lyapunov)
- **Status:** REFUTED by MATH-LYAPUNOV-MONOTONICITY (not step-by-step monotone)

#### Conjecture 8.5 (Dimensional Scaling)
- **Status:** PARTIALLY REFUTED by MATH-DIMENSION-SCALING (exponent is -0.28, not -1)

---

### MATH-KOOPMAN-EIGENFUNCTION

#### Theorem 3.1 (Approximate Koopman Eigenfunction)
- **Status:** CONJECTURE
- **Statement clarity:** 3/5. Clear claim: $\mathcal{K}[I] = \lambda I + r(x)$ with $|1-\lambda| \leq C_1\epsilon$.
- **Proof completeness:** 1/5. The "proof strategy" (Steps 1-4) is a verbal outline, not a proof. Each step has gaps:
  - Step 1: Davis-Kahan bounds eigenvector rotation, but connection to spectral shape stability requires additional argument.
  - Step 2: "Eigenvalues change by $O(\epsilon)$" — but $\epsilon$ is the commutator norm, not the Lipschitz constant.
  - Step 3: Restates the hypothesis.
  - Step 4: States the conclusion without derivation.
- **Logical gaps:** Constants $C_1, C_2$ are never bounded.
- **Rigor level:** 1/5
- **Dependencies:** Davis-Kahan theorem, Weyl's inequality (both standard, but not applied with bounds)

#### Conjecture 3.2 (Improved Eigenfunction)
- **Status:** CONJECTURE
- **Rigor level:** 1/5

#### Theorem 5.1 (Finite-Dimensional Invariant Subspace)
- **Status:** CONJECTURE
- **Statement clarity:** 2/5. The space $\mathcal{F}_k$ is imprecisely defined. The error term "$O(\epsilon) \cdot \mathcal{C}^\infty$" is undefined.
- **Proof completeness:** 1/5. The proof sketch conflates eigenvalues of $C$ at successive states with eigenvalues of the Jacobian $J = DC$.
- **Rigor level:** 1/5

#### Numerical experiments (Experiments 1-10)
- **Status:** EMPIRICAL (well-designed and reproducible)
- **Notes:** The experiments are the strongest part of this document. Key findings:
  - $|1-\lambda| < 0.005$ across all coupling architectures
  - DMD recovers $\lambda \approx 1$ as dominant mode
  - Lag-correlation matrix has effective rank 1
  - Commutator predicts eigenvalue deviation
  - These are genuine empirical findings, not proofs.

---

### MATH-JAZZ-THEOREM

#### Main Theorem (Spectral Shape Conservation)
- **Status:** CONJECTURE
- **Statement clarity:** 3/5. Clear but $g(\epsilon)$ is unspecified.
- **Proof completeness:** 1/5. The proof sketch has four lemmas, NONE rigorously proved:
  - **Lemma 1:** Claims eigenvalues of $DC$ are close to those of $D^{1/2}CD^{1/2}$. Actually $DC$ and $D^{1/2}CD^{1/2}$ are similar (identical eigenvalues when $D > 0$), so the "approximation" is exact — the perturbation claim is about $C(x_t)$ vs $C(x_{t+1})$, which is a different matter.
  - **Lemma 2:** Invokes LaSalle's invariance principle, which requires a Lyapunov function. Claims "the invariant set is NOT a point — it's a surface" — this **contradicts strict contraction**, which gives a unique equilibrium.
  - **Lemma 3:** Assumes the invariant set exists and has shape-preserving tangent directions. No proof given.
  - **Lemma 4:** Claims trajectories maintain separation on a dimension $\geq 1$ invariant set, contradicting strict contraction.
- **Logical gaps:** FUNDAMENTAL. The proof assumes a non-trivial invariant set (dimension $\geq 1$) while standing assumptions imply a unique fixed point (dimension 0). Cannot have both without weakening the contraction hypothesis.
- **Rigor level:** 1/5

#### Theorem (Platonic Dice)
- **Status:** CONJECTURE (depends on unproved main theorem)
- **Rigor level:** 1/5

#### Ergodic Theory Comparisons (§4, §7)
- **Status:** INFORMAL DISCUSSION
- **Notes:** The claim that the Jazz Theorem is "stronger than Oseledets" is unjustified. Oseledets is a deep, fully proved theorem. The Jazz Theorem has no proof. Claiming superiority of an unproved result over a proved one is inappropriate.
- **Rigor level:** 0/5 for the comparison claims

---

### MATH-TEMPORAL-GEOMETRY

#### Theorem 1.1 (Temporal First Integral)
- **Status:** PROVABLE (mostly tautological)
- **Rigor level:** 3/5
- **Notes:** The claim "no local computation can predict $I(x_t)$" is too strong — for static coupling, $I$ is computable from a single state.

#### Theorem 2.1 (Conservation Wavelength)
- **Status:** CONJECTURE
- **Rigor level:** 1/5. This is an analogy (signal processing), not a theorem.

#### Theorem 2.2 (Temporal-Spectral Uncertainty)
- **Status:** CONJECTURE
- **Rigor level:** 1/5. Constants undefined; Gabor uncertainty applies to $L^2$ functions, not discrete trajectories.

#### Theorem 3.1 (Conservation ↔ Low Curvature)
- **Status:** PROVABLE
- **Rigor level:** 2/5. Chain rule argument is correct in spirit but not rigorously derived.

#### Theorem 3.2 (Conservation and Normal Component)
- **Status:** PROVABLE
- **Rigor level:** 1/5. No proof given.

#### Theorem 4.1 (Inter-Snap Conservation)
- **Status:** PROVED
- **Rigor level:** 4/5. Lipschitz bound, straightforward.

#### Theorem 4.2 (Substrate Invariance)
- **Status:** PROVABLE
- **Rigor level:** 2/5. First part (convergence as $\epsilon \to 0$) is standard perturbation theory. Second part (conservation constant independent of $\epsilon$ above threshold) is empirical.

#### Theorem 4.3 (Snap-Perturbation Decomposition)
- **Status:** PROVED
- **Rigor level:** 4/5. Telescoping + geometric series under contraction. Correct.

#### Theorem 5.1 (Necessity of Computation)
- **Status:** PROVED (trivial)
- **Rigor level:** 4/5

#### Theorem 5.2 (Path-Independent Invariant)
- **Status:** Parts (i), (iii) PROVED; Part (ii) WRONG
- **Notes:** Part (ii) claims "$I(x_t) \to I(x^*)$ monotonically." MATH-LYAPUNOV-MONOTONICITY shows ~50% upward steps. **Direct contradiction.**
- **Rigor level:** 2/5

#### Theorem 5.3 (Information-Theoretic Lower Bound)
- **Status:** PROVED
- **Rigor level:** 4/5. Standard contraction + Lipschitz argument.

#### Theorem 6.1 (Quadratic Compaction)
- **Status:** PROVED (trivial)
- **Rigor level:** 4/5

#### Theorem 7.1 (Temporal Geometry Synthesis)
- **Status:** CONJECTURE (synthesis of unproved results)
- **Rigor level:** 1/5

---

### MATH-LATTICE-SPLINE

#### Theorem 1.1 (Curvature Bounds from Conservation)
- **Status:** PROVABLE
- **Rigor level:** 2/5. Depends on MATH-TEMPORAL-GEOMETRY Theorem 3.1 (itself only partially proved).

#### Theorem 2.1 (Lattice Sampling Preservation)
- **Status:** PROVED
- **Rigor level:** 4/5. Standard contraction + perturbation accumulation. Geometric series bound is correct.
- **Notes:** One of the strongest results in the corpus.

#### Corollary 2.1 (Eisenstein Optimality)
- **Status:** PROVED (well-known fact)
- **Rigor level:** 5/5

#### Theorem 2.2 (Snap-Spline Correspondence)
- **Status:** PROVABLE
- **Rigor level:** 3/5. The factor of 2 needs justification; $O(r_\Lambda^2)$ spline error is standard.

#### Theorem 3.1 (Hexagonal Gabor Frames)
- **Status:** PROVED (well-known, not original)
- **Rigor level:** 5/5

#### Theorem 3.2 (Quadratic Encoding)
- **Status:** PROVED
- **Rigor level:** 3/5

#### Theorem 3.3 (Compressed Sensing on Eisenstein Lattice)
- **Status:** PROVABLE
- **Rigor level:** 3/5. Correctly applies Candès-Romberg-Tao to the 1-sparse case.

#### Theorem 4.1 (Finger-on-the-Spline)
- **Status:** Parts (1)-(2) PROVED, Part (3) CONJECTURE, Part (4) depends on unproved Koopman result
- **Rigor level:** 2/5 overall

#### Theorem 5.1 (Constraint Feasibility)
- **Status:** PROVED (restatement of definition)
- **Rigor level:** 4/5

#### Theorem 5.2 (Lattice Density)
- **Status:** PROVED
- **Rigor level:** 4/5

#### Theorem 5.3 (SplineLinear Conservation)
- **Status:** PROVABLE
- **Rigor level:** 1/5. No proof given — described as "formal content of experimental result."

#### Theorem 6.1 (Lattice-Spline Synthesis)
- **Status:** PROVABLE (depends on unproved Jazz Theorem bound)
- **Rigor level:** 2/5

---

### MATH-LYAPUNOV-MONOTONICITY

This document is **empirical** — it reports experimental results and draws conclusions. No formal theorems with proofs.

#### Result 2.1 (NOT Monotone)
- **Status:** EMPIRICAL FINDING (well-documented, 5500 transitions)
- **Notes:** Definitively refutes Conjecture 8.1 from MATH-SPECTRAL-FIRST-INTEGRAL.

#### Result 3.1 (Exponential Decay Law)
- **Status:** EMPIRICAL FINDING
- **Notes:** The correlation $r = 0.999$ for $\Delta I \approx -\alpha I$ is striking and suggests genuine exponential relaxation.

#### Conjecture 3.2 ($\alpha \approx 1 - \rho(J)$)
- **Status:** REFUTED by own data. $\alpha \approx 0.003$ vs $1 - \rho(J) \approx 0.15$ (50× discrepancy).

#### Conjecture 6.1 ($\alpha \leq 1 - \rho(J)$)
- **Status:** CONJECTURE (plausible upper bound, consistent with data)

#### "Stochastic Lyapunov" / Supermartingale Classification
- **Status:** INFORMAL. The supermartingale interpretation $\mathbb{E}[I_{t+1} | \mathcal{F}_t] \leq I_t$ is reasonable but unproved. The system is deterministic (noise added only for numerical reasons), so the "stochastic" characterization conflates deterministic dynamics with added noise.

---

### MATH-DIMENSION-SCALING

Entirely empirical.

#### Revised Conjecture 8.5
- **Status:** EMPIRICAL
- **Key finding:** CV $\propto N^{-0.28}$ (not $1/N$ as conjectured), R² = 0.94
- **Cross-instance scaling:** $N^{-0.87}$, consistent with RMT concentration of measure.
- **Notes:** Honest revision of original conjecture.

---

### METAL-TO-PLATO

No new mathematical claims. Implementation-layer restatements of results from other documents.

- "Conservation is substrate-invariant" — Informal claim. Formal version (Temporal Geometry Theorem 4.2) is provable but not fully proved.
- PLATO room conservation claims — Architectural proposals, not proved theorems.

---

## Cross-Document Issues

### 1. CRITICAL: Inconsistent Definition of γ

| Document | γ definition |
|----------|-------------|
| MATH-SPECTRAL-FIRST-INTEGRAL (Def 2.1) | $\gamma = \lambda_1 - \lambda_2$ (spectral GAP) |
| MATH-SPECTRAL-FIRST-INTEGRAL (Def 2.2) | $\text{PR} = (\sum\lambda_i)^2/(\sum\lambda_i^2)$ (participation RATIO) |
| MATH-JAZZ-THEOREM (§1.3) | $\gamma = (\sum|\lambda_i|^2)^2 / (\sum|\lambda_i|^4)$ (participation RATIO with squared eigenvalues) |
| MATH-TEMPORAL-GEOMETRY (Def 1.2) | $\gamma = (\sum\lambda_i)^2 / (\sum\lambda_i^2)$ (participation RATIO) |
| METAL-TO-PLATO | $\gamma = \lambda_1 - \lambda_2$ (spectral GAP) |

**γ means TWO DIFFERENT THINGS across documents.** In some it is the spectral gap ($\lambda_1 - \lambda_2$), in others it is the participation ratio ($\text{Tr}(C)^2/\text{Tr}(C^2)$). These are fundamentally different quantities. This is not a minor notational issue — it changes what $I = \gamma + H$ means.

### 2. CRITICAL: Contraction vs. Multiple Fixed Points

The theory simultaneously assumes:
- **Contraction** (Theorems 5.2, 5.3, 7.4): unique fixed point, all trajectories converge
- **Multiple fixed points** (Remark 1.8, Jazz Theorem part c): up to 15 fixed points for $\rho(C) \approx 5$

These are contradictory. A strict contraction has a unique fixed point. Multiple fixed points require non-contracting dynamics (at least locally). The Jazz Theorem's "trajectory divergence" relies on multiple fixed points but the conservation proofs rely on contraction. The theory cannot have both globally.

### 3. SIGNIFICANT: Lyapunov Monotonicity Contradicts Temporal Geometry

- MATH-TEMPORAL-GEOMETRY Theorem 5.2(ii) claims "$I(x_t) \to I(x^*)$ monotonically."
- MATH-LYAPUNOV-MONOTONICITY Result 2.1 shows $I$ is NOT monotone (~50% upward steps).
- **Direct contradiction.**

### 4. SIGNIFICANT: Jazz Theorem Ergodic Claims Unjustified

MATH-JAZZ-THEOREM §7 claims the Jazz Theorem is "stronger than Oseledets." Oseledets' multiplicative ergodic theorem is a fully proved, deep result. The Jazz Theorem has no rigorous proof. Claiming an unproved result is "stronger than" a proved theorem is inappropriate for a mathematical document.

### 5. MODERATE: Spectral Shape Normalization Inconsistency

- MATH-SPECTRAL-FIRST-INTEGRAL: $p_i = \lambda_i / \sum\lambda_j$ (eigenvalue-normalized)
- MATH-JAZZ-THEOREM: $p_i = |\lambda_i|^2 / \sum|\lambda_j|^2$ (squared-eigenvalue-normalized)

These give different distributions and different entropy values for the same matrix.

### 6. MODERATE: Role of Added Noise

MATH-LYAPUNOV-MONOTONICITY and MATH-DIMENSION-SCALING add Gaussian noise ($\sigma = 0.05$–$0.1$) to prevent degenerate dynamics. This makes the system stochastic, fundamentally changing the analysis. The "supermartingale" behavior may be an artifact of added noise rather than deterministic dynamics. Documents do not clearly separate deterministic vs. noisy results.

### 7. MINOR: Scaling Results Not Cross-Validated

MATH-DIMENSION-SCALING finds CV $\propto N^{-0.28}$. MATH-KOOPMAN-EIGENFUNCTION Experiment 10 finds $|1-\lambda|$ decreasing with $N$. These should be related but the relationship is not quantified.

---

## The Strongest Honest Claim

Given the audit, the strongest statement that can be made with full rigor is:

> **Theorem (Honest Statement).** For the dynamical system $x_{t+1} = \tanh(C(x_t) \cdot x_t)$:
>
> 1. **(Rank-1, proved)** If $C(x) = xx^T/N$ (rank-1), then the participation entropy $H(x) = 0$ and participation ratio $\text{PR}(x) = 1$ for all $x \neq 0$. This is an algebraic identity.
>
> 2. **(Static coupling, proved)** If $C(x) = C_0$ (state-independent), then $I(x_t) = I(x_0)$ exactly for all $t$, since the eigenvalues of $C$ do not depend on the state.
>
> 3. **(Contraction convergence, proved)** If the system is contracting with unique fixed point $x^*$, then $I(x_t) \to I(x^*)$ as $t \to \infty$, with rate bounded by the contraction rate.
>
> 4. **(Snap perturbation, proved)** Lattice quantization introduces bounded perturbation to $I$: $\limsup_t |I(\hat{x}_t) - I(x^*)| \leq L_I r_\Lambda/(1-\lambda)$.
>
> 5. **(Empirical observation, unproved)** For state-dependent coupling (attention, hybrid), numerical experiments consistently show $\text{CV}(I) < 0.03$ along trajectories, with the commutator $\|[D,C]\|$ as the best predictor of conservation quality ($r = 0.965$, $p = 0.0004$).

**What would be needed for the next strongest claim** (a rigorous bound on CV):
- Fix the definition of $\gamma$ (choose one and use consistently)
- Prove a quantitative bound on spectral shape variation per step using Weyl's inequality + Lipschitz continuity of $C$
- Accumulate per-step bounds over a trajectory using contraction to control error growth
- This is feasible with standard perturbation theory tools but requires careful bookkeeping

---

## Proof Formalization Priority List

| Priority | Theorem | Why | Gap Size | Feasibility |
|----------|---------|-----|----------|-------------|
| 1 | Dynamical Conservation Bound (Thm 7.4) | Core quantitative claim; if proved, most other results follow | Medium — need per-step eigenvalue perturbation + contraction accumulation | HIGH — standard perturbation theory |
| 2 | Commutator-CV bound (Cor 4.6) | Main diagnostic tool; $r=0.965$ demands explanation | Medium — need to connect $\|[D,C]\|$ to eigenvalue drift rate | HIGH — Davis-Kahan + chain rule |
| 3 | Koopman eigenfunction (Koopman Thm 3.1) | Deepest structural claim; would unify the theory | Large — need functional analysis on observable space | MEDIUM — may require assumptions on $C(x)$ regularity |
| 4 | Jazz Theorem part (a) | Beautiful claim but currently has logical contradictions | Large — need to resolve contraction vs. multiple fixed points | MEDIUM — may need semi-contraction framework |
| 5 | Dimensional scaling law | Would connect to RMT; exponent -0.28 is unexplained | Large — need attention-specific concentration inequalities | LOW — requires new techniques for softmax concentration |
| 6 | Transient conservation (Conj 5.4) | Explains WHY conservation holds during transient | Large — need to bound spectral shape drift rate | MEDIUM — perturbation theory + trajectory control |

---

## Key Definitions That Need Tightening

1. **$\gamma(x)$**: Must choose ONE definition (spectral gap vs participation ratio) and use consistently across all documents.

2. **$I(x) = \gamma + H$**: Once $\gamma$ is fixed, restate the definition and verify all numerical experiments use the same definition.

3. **"Spectral shape" normalization**: $p_i = \lambda_i / \sum\lambda_j$ vs $p_i = |\lambda_i|^2 / \sum|\lambda_j|^2$ must be standardized.

4. **"Conservation"**: Specify CV computed over how many steps, from what initial conditions, with or without noise.

5. **"Attractor"**: Sometimes means unique fixed point (contraction), sometimes compact invariant set (LaSalle), sometimes multiple fixed points. These are different objects.

6. **"Contractive activation"**: Distinguish $\text{Lip} < 1$ (strict contraction) from $\text{Lip} \leq 1$ (non-expansive). ReLU ($\text{Lip} = 1$) is tested but is not strictly contractive.

7. **Eigenvalues of asymmetric matrices**: Attention coupling produces non-symmetric matrices. Must standardize: eigenvalues (complex?), singular values, or eigenvalues of symmetrized matrix.

---

## Summary Statistics

- **Total theorems/propositions audited:** 42
- **PROVED:** 12 (mostly: algebraic identities, Lipschitz bounds, standard perturbation, lattice geometry)
- **PROVABLE:** 8 (correct proof strategy, needs quantitative details)
- **CONJECTURE:** 19 (plausible claims, proof sketches with fundamental gaps)
- **WRONG:** 3 (Thm 3.1 original statement, Jazz Thm part (b) sign error, Temporal Geometry Thm 5.2(ii) monotonicity claim)
- **Average rigor level:** 2.1 / 5

### Rigor Distribution

| Level | Count | Examples |
|-------|-------|---------|
| 5 (Lean-verifiable) | 2 | Eisenstein optimality, Gabor frames — both citing known results |
| 4 (Publication-ready) | 8 | Inter-snap conservation, snap-perturbation decomposition, contractivity bounds |
| 3 (Correct argument, details needed) | 8 | Rank-1 revised, shape→conservation, sufficient conditions (a)-(b) |
| 2 (Proof sketch with gaps) | 10 | Dynamical conservation, commutator bound, curvature-conservation |
| 1 (Handwaving / verbal argument) | 14 | Jazz Theorem, Koopman eigenfunction, temporal geometry synthesis |

---

## Final Assessment

This is an **empirically driven mathematical research program** at an early stage. The experimental work is thorough, well-documented, and reveals a genuine phenomenon: the approximate conservation of a spectral functional along nonlinear coupled dynamics. The quantity $I(x) = \gamma(x) + H(x)$ (once the definition is standardized) appears to be robustly conserved across a wide range of coupling architectures, activations, dimensions, and quantization levels.

However, the mathematical formalization substantially oversells the current state of proof. Of the 42 claims audited, only 12 are rigorously proved, and most of those are elementary. The central claims (dynamical conservation, Jazz Theorem, Koopman eigenfunction) have only proof sketches with fundamental gaps. The documents contain internal contradictions (contraction vs. multiple fixed points, monotone vs. non-monotone convergence, inconsistent definitions of $\gamma$).

**Recommendation:** The strongest path forward is to:
1. **Standardize all definitions** (especially $\gamma$ and spectral shape normalization)
2. **Resolve the contraction/multiple-fixed-point tension** (probably by restricting claims to the contraction regime)
3. **Prove the dynamical conservation bound (Priority 1)** using standard perturbation theory (Weyl + Davis-Kahan + contraction accumulation)

This single result, if proved, would provide the rigorous foundation for most of the other claims.

---

*Audit completed 2026-05-17 by Claude Opus 4.6*
*"Claim only what you can prove. The experiments are better than the theorems."*
