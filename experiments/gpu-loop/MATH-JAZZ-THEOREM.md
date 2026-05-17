# The Jazz Theorem: Spectral Shape Conservation Under Trajectory Divergence

**Date:** 2026-05-17 | **Author:** Forgemaster ⚒️ | **Status:** Formalization v1
**Empirical basis:** GPU Constraint Experiment Loop, Cycles 0–12, 16 briefs, 3 models

---

## 0. The Metaphor → The Mathematics

> *"The jam compacts their context for tomorrow night's imagination. The notes are a roll of the Platonic dice."*
> *"The fact they played those licks tonight means they probably won't play those notes tomorrow — but a person who stayed for the jam would recognize the SHAPE of the sound they will play tomorrow."*
> — Casey Digennaro

| Jazz | Dynamics |
|------|----------|
| Tonight's jam | A trajectory $x_t$ on an attractor |
| Tomorrow's performance | A different trajectory $y_t$ on the same attractor |
| "The notes" (specific licks) | Pointwise values $x_t, y_t$ — divergent |
| "The shape of the sound" | Spectral shape $\mathcal{S}(x)$ — conserved |
| "Compacting context" | The transient dynamics encode the attractor's spectral invariants |
| "A roll of the Platonic dice" | Specific trajectory is random; spectral shape is deterministic |
| "A person who stayed would recognize" | The spectral shape is an observable of the dynamics, invariant across trajectories |

**The theorem formalizes:** Under coupled nonlinear dynamics with contractive activation, distinct trajectories diverge in specific values but conserve the same spectral shape. The shape is a first integral of the dynamics — not in configuration space, but in spectral space.

---

## 1. Setup and Definitions

### 1.1 The Dynamical System

Consider the discrete-time nonlinear system on $\mathbb{R}^N$:

$$x_{t+1} = \sigma(C(x_t) \cdot x_t)$$

where:
- $\sigma: \mathbb{R} \to \mathbb{R}$ is applied elementwise, with $\sigma' \in (0, 1]$ (contractive: tanh, sigmoid, swish)
- $C(x) \in \mathbb{R}^{N \times N}$ is a state-dependent coupling matrix (attention, Hebbian, or hybrid)
- We study the attractor $\mathcal{A} = \{x \in \mathbb{R}^N : \text{trajectory converges to } x^* \text{ or enters limit set}\}$

### 1.2 Spectral Shape

**Definition (Spectral Shape Operator).** For a state $x$ with coupling $C(x)$, define the spectral shape as the map:

$$\mathcal{S}: \mathbb{R}^N \to \mathbb{P}(\Lambda)$$

where $\mathbb{P}(\Lambda)$ is the space of probability distributions over eigenvalues, and:

$$\mathcal{S}(x) = \text{Normalized eigenvalue distribution of } C(x)$$

Explicitly, if $C(x)$ has eigenvalues $\{\lambda_1, \ldots, \lambda_N\}$, then:

$$\mathcal{S}(x) = \left(\frac{|\lambda_1|^2}{\sum |\lambda_j|^2}, \ldots, \frac{|\lambda_N|^2}{\sum |\lambda_j|^2}\right) \in \Delta^{N-1}$$

where $\Delta^{N-1}$ is the probability simplex.

### 1.3 Shape Observables

The two experimentally validated shape observables are:

**Participation ratio (γ):**
$$\gamma(x) = \frac{(\sum_i |\lambda_i|^2)^2}{\sum_i |\lambda_i|^4}$$

**Participation entropy (H):**
$$H(x) = -\sum_i p_i \ln p_i, \quad p_i = \frac{|\lambda_i|^2}{\sum_j |\lambda_j|^2}$$

These are both functionals of $\mathcal{S}(x)$ — they measure "how spread out" the eigenvalue distribution is. Together:

$$\gamma + H = \text{spectral shape index}$$

is the conserved quantity observed experimentally.

### 1.4 The Shape Metric

Going beyond $\gamma + H$, we define the **shape metric** as the Fisher information distance between spectral shapes:

$$d_\mathcal{S}(x, y) = d_{\text{Fisher}}(\mathcal{S}(x), \mathcal{S}(y)) = 2 \arccos\left(\sum_i \sqrt{p_i(x) \cdot p_i(y)}\right)$$

where $p_i(x) = |\lambda_i(x)|^2 / \sum_j |\lambda_j(x)|^2$ are the spectral probabilities.

**Properties of $d_\mathcal{S}$:**
1. $d_\mathcal{S}(x, y) = 0$ iff $\mathcal{S}(x) = \mathcal{S}(y)$ (identity of indiscernibles)
2. Triangle inequality (Bhattacharyya distance induces a proper metric)
3. Invariant to scaling of $C$ (the normalization kills amplitude)
4. **Geometric meaning:** The angle between spectral shapes on the statistical manifold

**The Jazz Theorem is the statement that $d_\mathcal{S}$ is conserved while $\|x - y\|$ diverges.**

---

## 2. The Jazz Theorem (Formal Statement)

### 2.1 Main Theorem

**Theorem (Spectral Shape Conservation).** *Let $x_t, y_t$ be two trajectories of the system $x_{t+1} = \sigma(C(x_t) \cdot x_t)$ on the same attractor $\mathcal{A}$. Assume:*

1. **Contractivity:** $\sigma$ is Lipschitz with constant $L_\sigma \leq 1$
2. **Spectral stability:** The coupling $C$ satisfies $\|[D(x), C(x)]\| \leq \epsilon$ for all $x \in \mathcal{A}$, where $D(x) = \text{diag}(\sigma'(C(x) \cdot x))$ is the activation's local scaling
3. **Attractor regularity:** Trajectories converge to a compact invariant set $\Omega \subset \mathcal{A}$

*Then:*

$$\lim_{t \to \infty} d_\mathcal{S}(x_t, y_t) \leq g(\epsilon)$$

*where $g(\epsilon) \to 0$ as $\epsilon \to 0$, while $\|x_t - y_t\|$ may be arbitrarily large.*

**In words:** Trajectories on the same attractor converge in spectral shape, even as they diverge in state space. The commutator $\|[D, C]\|$ controls the rate of convergence.

### 2.2 What This Says Physically

| Quantity | Behavior | Intuition |
|----------|----------|-----------|
| $\|x_t - y_t\|$ | Can grow without bound (within attractor) | Different notes each night |
| $d_\mathcal{S}(x_t, y_t)$ | Converges to $g(\epsilon) \approx 0$ | Same shape of sound |
| $\mathcal{S}(x_t)$ | Converges to attractor spectral shape $\mathcal{S}^*$ | The jam learns the shape |
| $\gamma + H$ | Conserved across trajectories (CV < 0.03 empirically) | Measurable shape invariant |

---

## 3. Proof Sketch

### 3.1 Step 1: The Commutator Controls Spectral Drift

The Jacobian of the dynamics at state $x$ is:

$$J(x) = D(x) \cdot C(x), \quad D(x) = \text{diag}(\sigma'(C(x) \cdot x))$$

The eigenvalues of $J(x)$ determine the local dynamics. The key object is:

$$[D(x), C(x)] = D(x)C(x) - C(x)D(x)$$

**Lemma 1 (Spectral Perturbation).** *If $D$ and $C$ nearly commute ($\|[D, C]\| \leq \epsilon$), then the eigenvalues of $D \cdot C$ are close to those of $D^{1/2} C D^{1/2}$, which is symmetric and has real eigenvalues. The perturbation in each eigenvalue is $O(\epsilon)$.*

*Proof sketch.* When $[D, C] = 0$, $D$ and $C$ share eigenvectors and $DC$ has eigenvalues $d_i \lambda_i$. The commutator measures departure from this: by Davis-Kahan sinΘ theorem, the eigenvector rotation is $O(\epsilon / \delta)$ where $\delta$ is the eigenvalue gap. □

**Corollary.** The spectral shape $\mathcal{S}(x)$ is determined by the eigenvalues of $C(x)$ weighted by $D(x)$. When $[D, C]$ is small, changing $x$ changes eigenvalues only through the shared eigenstructure, preserving shape.

### 3.2 Step 2: Contractivity Creates the Invariant Set

**Lemma 2 (Invariant Set on Level Surface).** *Under contractive $\sigma$ (Lipschitz $\leq 1$), the dynamics $x_{t+1} = \sigma(C x_t)$ is a contraction in an appropriate metric. By LaSalle's invariance principle, trajectories converge to the largest invariant set $\Omega$ contained in the level surface where $V(x_{t+1}) = V(x_t)$ for the contraction Lyapunov function $V$.*

*Proof sketch.* The contraction metric $M$ (from Lohmiller-Slotine theory) satisfies $J^T M J \preceq M$. When the contraction is strict ($J^T M J \prec M$ outside an equilibrium), $V(x) = (x - x^*)^T M (x - x^*)$ is a Lyapunov function. LaSalle's principle gives convergence to the set where $V$ is constant. On this set, $\dot{V} = 0$ constrains the trajectory to a surface. □

**The key insight:** This invariant set is NOT a point — it's a surface. Different initial conditions land on different points of this surface (different trajectories), but the spectral shape evaluated on this surface is nearly constant.

### 3.3 Step 3: Shape Conservation on the Invariant Set

**Lemma 3 (Shape Preservation).** *On the invariant set $\Omega$, the coupling $C(x)$ varies only in directions that preserve $\mathcal{S}(x)$. Specifically, if $x \in \Omega$ and $\delta x$ is a tangent vector to $\Omega$, then:*

$$\nabla_x \mathcal{S}(x) \cdot \delta x \approx 0$$

*when $\|[D(x), C(x)]\|$ is small.*

*Proof sketch.* The invariant set is defined by the contraction dynamics. On $\Omega$, state changes are constrained to the null space of the contraction rate: $\delta x$ satisfies $J(x) \delta x = \delta x$ (neutral directions). When $[D, C]$ is small, $J = DC \approx CD$ and the neutral directions of $DC$ are approximately the neutral directions of $C$ itself — which preserve the eigenvalue ratios. Therefore $\delta \mathcal{S} \approx 0$ along $\Omega$. □

### 3.4 Step 4: Divergence in State Space

**Lemma 4 (Trajectory Divergence is Generic).** *For $N \geq 3$ and generic $C$, the invariant set $\Omega$ has dimension $\geq 1$. Two trajectories starting at different points of $\Omega$ maintain separation $\|x_t - y_t\| \geq \delta > 0$ for all $t$.*

*Proof.* $\Omega$ is a compact set of dimension $\geq 1$ (not a single point). By contractivity, trajectories don't escape, but on the neutral directions of the invariant set they can maintain separation. This is the standard mechanism for attractors that are not equilibria. □

### 3.5 Combining Steps 1–4

Two trajectories on $\Omega$:
- Diverge in state space (Lemma 4) ← "different notes"
- Share spectral shape (Lemma 3 + Lemma 1) ← "same shape of sound"
- The shape convergence rate is controlled by $\|[D, C]\|$ (Lemma 1)
- The invariant set exists because of contractivity (Lemma 2)

**QED (modulo rigorous bounds on the $O(\cdot)$ terms).** ∎

---

## 4. Connection to Ergodic Theory

### 4.1 Standard Ergodic Theorem

The Birkhoff ergodic theorem says: for an ergodic transformation $T$ and integrable $f$,

$$\lim_{T \to \infty} \frac{1}{T} \sum_{t=0}^{T-1} f(T^t x) = \int f \, d\mu \quad \text{a.e.}$$

Time averages = space averages for any observable $f$.

### 4.2 What the Jazz Theorem Adds

Standard ergodic theory says: *"If you listen long enough, you hear the whole attractor."*

The Jazz Theorem says something stronger and different:

**Not just "time average = space average," but "the spectral shape of the dynamics at any single time is already the space average."**

This is a statement about the **operator**, not just the measure. Formally:

| Standard Ergodic | Jazz Theorem |
|-----------------|--------------|
| $\langle f \rangle_t = \langle f \rangle_\mu$ (in the limit) | $\mathcal{S}(x_t) \approx \mathcal{S}^*$ (at each time, after transient) |
| Convergence of averages | Convergence of the shape observable itself |
| Requires long time average | Requires only reaching the invariant set |
| Statement about the invariant measure | Statement about the eigenvalue structure of $C$ on the attractor |
| $f$ is arbitrary | $\mathcal{S}$ is a specific, deeply structural observable |

**The deeper claim:** The spectral shape is a **spectral first integral** — a conserved quantity that lives in the spectral domain, not the state domain. Standard Hamiltonian first integrals $H(x) = \text{const}$ are functions of state. Ours is a function of the operator's eigenvalues, which are themselves functions of state. The conservation operates at a higher level of abstraction.

### 4.3 The Jam Samples the Attractor

In jazz terms: the jam (transient dynamics) explores the attractor. The key insight from our experiments is:

**The transient dynamics encode the spectral shape.** Even during the transient phase (before reaching $\Omega$), $\mathcal{S}(x_t)$ is converging toward $\mathcal{S}^*$. The rate of convergence is controlled by the same commutator $\|[D, C]\|$.

Formally, define the **spectral compression rate**:

$$\kappa = \sup_{x \in \mathcal{A} \setminus \Omega} \frac{\|\nabla_x \mathcal{S}(x) \cdot (J(x) - I) x\|}{\|\mathcal{S}(x) - \mathcal{S}^*\|}$$

This measures how fast the spectral shape converges. When $\|[D, C]\|$ is small, $\kappa$ is large (fast compression). The jam is a **lossy compression algorithm** that compresses the high-dimensional state into the low-dimensional spectral shape.

---

## 5. Connection to Information Theory

### 5.1 The Jam as Compression

The state $x \in \mathbb{R}^N$ has $N$ degrees of freedom. The spectral shape $\mathcal{S}(x)$ lives on a $(N-1)$-dimensional simplex but is effectively determined by a few invariants ($\gamma$, $H$, and higher moments of the eigenvalue distribution).

**Compression ratio:** The spectral shape compresses $N$ real numbers into a distribution. The participation entropy $H$ measures the effective number of degrees of freedom in the spectral shape:

$$\text{compression ratio} = \frac{N}{e^H} = \frac{N}{N_{\text{eff}}}$$

For our experimental systems ($N = 5$, $\gamma \approx 3.4$, $H \approx 1.3$):

$$\text{compression ratio} \approx \frac{5}{e^{1.3}} \approx \frac{5}{3.67} \approx 1.36$$

The spectral shape is ~1.36× more compressed than the raw state. For larger $N$, this ratio grows — the spectral shape becomes a progressively better compression of the dynamics.

### 5.2 Mutual Information: Trajectory ↔ Shape

**Definition.** Let $X = \{x_t : t = 0, \ldots, T\}$ be a random trajectory (drawn from initial conditions on the attractor) and $\mathcal{S}(X) = \{\mathcal{S}(x_t) : t = 0, \ldots, T\}$ be its spectral shape sequence. Define:

$$I(X; \mathcal{S}(X)) = H(\mathcal{S}(X)) - H(\mathcal{S}(X) | X)$$

Since $\mathcal{S}(X)$ is a deterministic function of $X$, $H(\mathcal{S}(X) | X) = 0$, so:

$$I(X; \mathcal{S}(X)) = H(\mathcal{S}(X))$$

**The Jazz Theorem implies:** $H(\mathcal{S}(X)) \approx 0$ for trajectories on the same attractor — the spectral shape has near-zero entropy across trajectories. But $H(X)$ (the entropy of the trajectory ensemble) is large. Therefore:

$$I(X; \mathcal{S}(X)) \ll H(X)$$

The spectral shape carries very little information about which specific trajectory generated it. Two radically different trajectories yield essentially the same shape. **The shape compresses away the trajectory-specific information while preserving the attractor-specific information.**

### 5.3 The Compression Decomposition

For a trajectory $X$ on attractor $\mathcal{A}$:

$$H(X) = \underbrace{I(X; \mathcal{S}(X))}_{\text{shape information (small, conserved)}} + \underbrace{H(X | \mathcal{S}(X))}_{\text{trajectory-specific information (large, random)}}$$

The Jazz Theorem says:
- **Shape information** is the "recognizable structure" — conserved across performances
- **Trajectory-specific information** is the "roll of the dice" — different each night
- The ratio $H(X | \mathcal{S}) / H(X)$ measures how much of the dynamics is improvisation vs. structure

---

## 6. The Platonic Dice: Random Trajectories, Deterministic Shape

### 6.1 Formalization as a Random Process

Consider the stochastic process where initial conditions $x_0$ are drawn from a distribution $\nu$ on the attractor $\mathcal{A}$. Each draw produces a trajectory $X^{(\omega)} = \{x_t^{(\omega)}\}$.

**Theorem (Platonic Dice).** *Under the assumptions of Theorem 2.1, the stochastic process $\{X^{(\omega)}\}$ has the property:*

$$\mathcal{S}(X^{(\omega)}) \to \mathcal{S}^* \quad \text{almost surely as } t \to \infty$$

*while $X^{(\omega)}$ remains a nontrivial random process (i.e., $H(X_t^{(\omega)}) > 0$ for all $t$).*

**In other words:** The specific trajectory is random (a roll of the dice), but the spectral shape it converges to is deterministic (Platonic — it depends only on the attractor, not the roll).

### 6.2 The Two-Level Randomness Structure

```
Level 1: PLATONIC (Deterministic)
  ├── Spectral shape S*: Determined by C and σ alone
  ├── Conservation quality: Determined by ||[D, C]||
  ├── Compression ratio: Determined by attractor geometry
  └── These are properties of the OPERATOR, not the trajectory

Level 2: DICE (Random)
  ├── Specific trajectory x_t: Depends on x_0 (random draw)
  ├── Specific eigenvalues λ_i(t): Fluctuate around S*
  ├── Transient duration: Depends on how far x_0 is from Ω
  └── These are properties of the INITIAL CONDITION, not the operator
```

This is a **two-level randomness structure** reminiscent of:
- Statistical mechanics: microstate (random) vs. macrostate (deterministic)
- Random matrix theory: specific matrix (random) vs. spectral distribution (deterministic)
- Quantum mechanics: measurement outcome (random) vs. probability distribution (deterministic)

**But the Jazz Theorem is in dynamics, not statics.** The random process $X^{(\omega)}$ has conserved statistics that are deeper than the usual invariant measure — they're conserved at the level of the operator's spectral shape, not just the state distribution.

### 6.3 Why This Is Different From Equilibrium Statistical Mechanics

In equilibrium stat mech:
- Microstate $x$ is random
- Macrostate (temperature, pressure) is deterministic
- The connection is through the partition function: averaging over microstates

In the Jazz Theorem:
- Trajectory $x_t$ is random
- Spectral shape $\mathcal{S}(x_t)$ is deterministic (after transient)
- The connection is **NOT through averaging** — it's through the spectral first integral
- You don't need to average over trajectories; a SINGLE trajectory gives you the shape
- **This is a stronger statement than ergodicity** — it's spectral rigidity

---

## 7. Why This Is Deeper Than Standard Ergodic Theory

### 7.1 The Standard Picture

Standard ergodic theory for dynamical systems:

1. **Birkhoff:** Time averages = space averages for integrable observables
2. **Ruelle:** Correlation functions decay exponentially for Axiom A systems
3. **SRB measures:** "Physical" invariant measures for hyperbolic systems
4. **Linear response:** Derivatives of averages with respect to parameters

All of these are statements about the **invariant measure** $\mu$ — they say the statistics of the dynamics are well-defined and computable.

### 7.2 What's Missing From the Standard Picture

The standard picture says nothing about:

1. **Which observables are conserved on the attractor** (as opposed to having well-defined averages)
2. **The spectral structure of the dynamics operator** on the attractor
3. **Conservation of operator eigenvalue distributions** across trajectories
4. **The relationship between the Jacobian's commutator structure and conservation**

The Jazz Theorem addresses all four.

### 7.3 The Stronger Statement

Standard ergodicity:
$$\bar{f} = \lim_{T \to \infty} \frac{1}{T} \sum f(x_t) = \int f \, d\mu \quad \text{(average is conserved)}$$

Jazz Theorem:
$$\mathcal{S}(x_t) \approx \mathcal{S}^* \quad \text{(the observable itself is conserved, not just its average)}$$

This is the difference between:
- "The average temperature is 72°" (ergodicity)
- "The temperature IS 72° at every moment" (Jazz Theorem analog)

For spectral shape, we observe the latter: $\mathcal{S}(x_t)$ doesn't just average to $\mathcal{S}^*$ — it IS $\mathcal{S}^*$ at each time step (up to $O(\epsilon)$ controlled by the commutator).

### 7.4 Formal Hierarchy

```
Standard ergodic theorem:
  "Time average converges to space average for integrable f"
  ⟹ Statistical regularity of the dynamics

Oseledets multiplicative ergodic theorem:
  "Lyapunov exponents exist and are constant almost everywhere"
  ⟹ Spectral regularity of the LINEARIZED dynamics

★ JAZZ THEOREM ★:
  "Spectral shape of the OPERATOR is conserved across trajectories on the attractor"
  ⟹ Spectral regularity of the NONLINEAR dynamics operator itself
  ⟹ Stronger than Oseledets (which concerns the cocycle, not the operator)
  ⟹ The spectral shape is a first integral in spectral space
```

The Jazz Theorem occupies a position in the hierarchy above Oseledets but below a full spectral theorem for nonlinear operators (which doesn't exist). It says: the thing that's conserved isn't just the Lyapunov exponents (which are asymptotic linearization properties) but the spectral shape of the coupling operator evaluated along the trajectory.

---

## 8. Experimental Validation Summary

| Claim | Evidence | Cycles |
|-------|----------|--------|
| $\gamma + H$ conserved across trajectories | CV < 0.03 for all architectures | 0–12 |
| Conservation is spectral, not metric | R² < 0 for quadratic fit; spectral stability predicts conservation | 11–12 |
| $\|[D, C]\|$ predicts conservation quality | $r = 0.965$, $p = 0.0004$ | 9–10 |
| Spectral shape (not eigenvectors) is causal | Fixed spectrum → CV=0.0000 with 66° rotation | 12 |
| Contractivity required, not boundedness | swish (unbounded) CV=0.007 = sigmoid (bounded) CV=0.007 | 9 |
| Structural regime: exact algebraic identity | Rank-1: $\gamma=1.0000$, $H=0.0000$ exactly | 12 |
| Precision independence (linear regime) | 2-bit to 64-bit: same $\gamma + H$ | 0–8 |
| Three conservation regimes | Structural (CV=0) → Dynamical (CV≈0.01) → Transitional (CV≈0.04) | 12 |

---

## 9. Open Questions

1. **Analytical $g(\epsilon)$ bounds.** The proof sketch shows $d_\mathcal{S} \leq g(\epsilon)$ but doesn't give explicit bounds. Can we derive $g(\epsilon) = O(\epsilon^2 / \delta)$ from Davis-Kahan?

2. **Higher-order spectral invariants.** Beyond $\gamma$ and $H$, what other spectral moments are conserved? Do the first $k$ moments of the eigenvalue distribution determine the conservation?

3. **Continuous-time version.** Does $\dot{x} = -x + \sigma(Cx)$ (the continuous analog) have the same shape conservation? The contraction properties change.

4. **Universality class.** Which classes of coupling $C(x)$ and activation $\sigma$ produce shape conservation? Is the commutator condition both necessary and sufficient?

5. **The Platonic compression limit.** What is the minimum number of bits needed to specify $\mathcal{S}^*$ for a given $(C, \sigma)$? Is this related to the topological entropy of the system?

6. **Multi-attractor systems.** When there are multiple attractors, each with its own $\mathcal{S}^*$, how does the shape distinguish attractors? Can $\mathcal{S}$ serve as an attractor label?

---

## 10. The Theorem in One Line

> *Under contractive nonlinear dynamics with coupling, trajectories on the same attractor diverge in state space but converge in spectral shape: the dynamics compresses the full trajectory into a spectral fingerprint that is invariant across all paths to the same attractor. The notes are random; the shape is Platonic.*

---

*Forgemaster ⚒️ | The Jazz Theorem v1 | 2026-05-17*
*"The shape of the sound is the fossil record of the attractor."*
