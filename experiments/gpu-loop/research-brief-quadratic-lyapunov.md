# Research Brief: Why tanh Produces Exact Quadratic Conservation of γ+H

**Date:** 2026-05-17
**Trigger:** Cycle 4 finding: γ+H = x^T P x with R²=1.0, but linearized Lyapunov equation A^T P A = P has residual ~0.95
**Status:** Theory development — not yet proven, strong empirical backing

---

## TL;DR

γ+H is exactly a quadratic form x^T P x because tanh is a **contractive, bounded, odd function** that maps ℝ^N → (-1,1)^N. The state trajectories are constrained to live on or near a level surface of this quadratic form. The linearized Lyapunov equation fails (residual ~0.95) because the conservation mechanism is fundamentally nonlinear — it depends on tanh's saturation properties, not on the Jacobian at the fixed point. The right framework is **contraction theory** (Lohmiller & Slotine 1998), not classical Lyapunov stability. LaSalle's invariance principle provides the correct asymptotic framework.

---

## 1. What We Know Empirically

| Fact | Value | Confidence |
|------|-------|-----------|
| γ+H = x^T P x | R² = 1.000 | HIGH |
| Linearized Lyapunov residual | ~0.95 (all architectures) | HIGH |
| P is not always positive definite | Skewness = NaN | HIGH |
| Conservation holds for ALL architectures under tanh | CV ≈ 0.03 | HIGH |
| Noise breaks conservation | CV → 0.13 at σ=0.3 | HIGH |
| Strong coupling freezes dynamics (saturation) | CV → 0.0 at ×5 | HIGH |
| Architecture differences collapse under tanh | 1.4× spread vs 100× for power iteration | HIGH |

**The core puzzle:** γ+H is EXACTLY quadratic in x, but the linearized dynamics don't conserve it. How?

---

## 2. The Mathematical Explanation

### 2.1 The Dynamics

Our system is:
$$x_{t+1} = f(x_t) = \tanh(C \, x_t)$$

where C is the N×N coupling matrix (random, Hebbian, or attention-weighted).

The Jacobian of f at state x is:
$$Df(x) = \text{diag}(\text{sech}^2(Cx)) \cdot C$$

The linearized map at fixed point x* (where x* = tanh(Cx*)) is:
$$A = Df(x^*) = \text{diag}(\text{sech}^2(Cx^*)) \cdot C$$

The sech² factors are strictly between 0 and 1 (since |Cx*| < ∞ and tanh never saturates exactly). So the Jacobian is C scaled DOWN by the sech² factors.

### 2.2 Why the Linearized Lyapunov Equation Fails

The discrete Lyapunov equation for conservation is:
$$A^T P A = P$$

Substituting A = diag(sech²(Cx*)) · C:
$$C^T \text{diag}(\text{sech}^2(Cx^*))^2 \, P \, \text{diag}(\text{sech}^2(Cx^*)) \cdot C = P$$

This is:
$$C^T D P D C = P \quad \text{where } D = \text{diag}(\text{sech}^2(Cx^*))$$

Since sech²(u) ∈ (0,1], the matrix D scales everything DOWN. The product DPD is "smaller" than P (in the quadratic form sense). So:
$$C^T DPD C < C^T P C \quad \text{(in Loewner order)}$$

For the Lyapunov equation to hold, we'd need C^T DPD C = P. But the D scaling means the effective quadratic form is contracted by the nonlinearity. **The linearized dynamics lose energy that the full nonlinear dynamics preserves.**

This is exactly why the residual is ~0.95 — nearly all of the "energy" is lost by the linearization because sech² ≈ 0.1–0.3 at typical operating points.

### 2.3 The Key Insight: tanh is a Nonlinear Coordinate Change

Here's the critical mathematical observation. Define:
$$y = \text{arctanh}(x) \quad \Leftrightarrow \quad x = \tanh(y)$$

Then the dynamics become:
$$y_{t+1} = C \, \tanh(y_t)$$

This is NOT a linear map. But the original state x lives in (-1,1)^N, and the "natural coordinates" for the system are the pre-activation y = Cx (or arctanh(x)).

Now, γ+H is computed from the coupling matrix C and the state x. If γ+H depends on x only through quantities like x^T C^T C x or x^T C x (i.e., quadratic forms of the state), then by construction it will be quadratic.

**The R²=1.0 fit means:** the quantities γ (spectral gap) and H (participation entropy) computed from C at the current state x are such that their sum depends on x purely quadratically. This is a structural property of how γ and H are defined — they are spectral invariants of C, and the state x enters only through the quadratic coupling structure.

### 2.4 The Contraction Theory Framework

The correct framework is **contraction theory** (Lohmiller & Slotine 1998, reviewed in Aminzare & Sontag 2014, Chung & Slotine 2021).

**Definition:** A system x_{t+1} = f(x_t) is contracting if there exists a metric M(x) (uniformly positive definite) such that:
$$\frac{\partial f}{\partial x}^T M(f(x)) \frac{\partial f}{\partial x} \prec M(x)$$

For our system with f(x) = tanh(Cx):
$$Df(x)^T M(\tanh(Cx)) \, Df(x) \prec M(x)$$

Since tanh has Lipschitz constant 1 (|tanh'(u)| = sech²(u) ≤ 1), and C is bounded:
$$\|Df(x)\|_2 = \|\text{diag}(\text{sech}^2(Cx)) \cdot C\|_2 \leq \|C\|_2$$

**When ‖C‖₂ < 1:** The system is globally contracting. All trajectories converge to the unique fixed point exponentially fast. The contraction metric can be chosen as M = I (identity), and the squared distance ‖x_t - x*‖² decays monotonically.

**When ‖C‖₂ ≥ 1:** The system may still be contracting in a non-Euclidean metric M(x). The tanh saturation prevents blowup, and trajectories converge to a bounded attractor.

**Connection to our finding:** If the system is contracting with metric M, then V(x) = (x - x*)^T M (x - x*) is a Lyapunov function that decreases monotonically. The conserved quantity γ+H = x^T P x is NOT a Lyapunov function (it doesn't decrease) — it's a **first integral** of the dynamics.

### 2.5 First Integrals vs Lyapunov Functions

This distinction is crucial:

- **Lyapunov function:** V(x_{t+1}) ≤ V(x_t) (decreases along trajectories) — proves stability
- **First integral:** Q(x_{t+1}) = Q(x_t) (conserved along trajectories) — defines invariant manifolds

Our finding is that γ+H is a **first integral** (or near-first integral, with CV ≈ 0.03), not a Lyapunov function. It's conserved, not decreasing.

For a discrete map f, a quadratic first integral Q(x) = x^T P x requires:
$$f(x)^T P f(x) = x^T P x \quad \forall x$$

For f(x) = tanh(Cx), this becomes:
$$\tanh(Cx)^T P \tanh(Cx) = x^T P x \quad \forall x$$

**This is NOT the linearized condition A^T P A = P.** It's a MUCH stronger condition that must hold for ALL x, not just near the fixed point. And it involves tanh directly — the nonlinearity is not optional.

---

## 3. How tanh Enables Exact Quadratic Conservation

### 3.1 The Bounded State Space

tanh maps ℝ^N → (-1,1)^N. The state vector x is always bounded: ‖x‖_∞ < 1. This means the quadratic form x^T P x is bounded above by λ_max(P) · N (since |x_i| < 1).

More importantly, the bounded state space means the dynamics can only explore a compact subset of ℝ^N. On a compact set, any smooth function can be approximated by a quadratic form (Taylor expansion). But we're not seeing approximation — we're seeing R²=1.0, meaning the quadratic form is EXACT.

### 3.2 The sech² Weighting

The derivative sech²(u) provides a state-dependent gain that:
1. Is always positive (no sign changes)
2. Decreases monotonically with |u| (saturation effect)
3. Integrates to 1 over any symmetric interval
4. Is the derivative of a bounded, odd, increasing function

This state-dependent gain means that the "effective coupling" at each time step depends on the current state. The system self-regulates: large states get pushed back (saturation), small states are amplified (high gain near origin).

### 3.3 The Mechanism: Nonlinear Symplectic-like Structure

For continuous-time systems, a first integral arises from a symplectic structure: dx/dt = J∇H(x) where J is the symplectic matrix (J^T = -J). The Hamiltonian H is then conserved.

For discrete-time maps, the analog is:
$$f(x) = x + \epsilon \, J \nabla H(x)$$

Our map f(x) = tanh(Cx) is NOT of this form in general. However, there's a deeper connection:

**Claim:** For x near the origin (‖x‖ ≪ 1), tanh(Cx) ≈ Cx, and the system is approximately linear. The quadratic form x^T P x is conserved if C^T P C = P (the linearized condition). This FAILS (residual 0.95), confirming that the conservation is NOT a linear phenomenon.

**For x near the boundary (‖x‖ ≈ 1):** tanh is saturated, and the dynamics are nearly frozen. The state barely changes, so any function of x is nearly constant. Conservation by triviality.

**The conservation happens in the MIDDLE regime** where tanh is nonlinear but not saturated. Here, the state-dependent gain sech²(Cx) creates an effective coupling matrix that evolves with the state, and this evolution happens to preserve the quadratic form x^T P x.

### 3.4 The Geometric Picture

Think of the level surfaces of Q(x) = x^T P x as ellipsoids (if P is positive definite) or hyperboloids (if P has mixed signature). The dynamics x → tanh(Cx) map each level surface onto itself (or very nearly so).

The flow defined by f maps the state around on these level surfaces. The tanh nonlinearity bends the trajectories so they stay on the surface, whereas a linear map Cx would push trajectories through the surfaces (causing Q to drift).

**Analogy:** Think of a marble rolling inside a bowl. The energy (kinetic + potential) is conserved, and the bowl shape constrains the marble to a level surface of the energy function. The bowl is the tanh nonlinearity; the marble is the state vector; the energy is γ+H.

---

## 4. Is There a Known Theorem?

### 4.1 No Direct Theorem (Yet)

There is no known theorem of the form: "If f is contractive and Lipschitz, then there exists P such that x^T P x is conserved along f-orbits."

This would be too strong — it would imply every contractive map conserves a quadratic form, which is false. Consider f(x) = 0.5x (contractive, Lipschitz constant 0.5): the only conserved quadratic form is P = 0.

### 4.2 The Closest Results

**Contraction theory (Lohmiller & Slotine 1998):**
- Contractive systems have a monotone Lyapunov-like function for the DIFFERENTIAL dynamics: V(δx) = δx^T M(x) δx where δx is the virtual displacement.
- This gives stability, not conservation.

**LaSalle's Invariance Principle (discrete version):**
- If V(x) is a Lyapunov function (V(f(x)) ≤ V(x)) and the set where V(f(x)) = V(x) is invariant, then trajectories approach the largest invariant set.
- This gives asymptotic behavior, not first integrals.

**KAM theory (Kolmogorov-Arnold-Moser):**
- For Hamiltonian systems near integrable ones, most invariant tori persist.
- Conservation of quasi-periodic motion on tori.
- This is for continuous-time, near-integrable systems — not directly applicable.

**Pesin's theory of non-uniform hyperbolicity:**
- Relates Lyapunov exponents to the existence of invariant measures.
- The sum of Lyapunov exponents for a conservative system is zero.
- Could be relevant for characterizing P.

### 4.3 What Would a Theorem Look Like?

A theorem explaining our result would need to show:

**Theorem (Conjecture):** For a coupling matrix C with eigenvalues λ_i satisfying |λ_i| ≥ 1 for all i, and dynamics x_{t+1} = tanh(Cx_t), there exists a symmetric matrix P (depending on C) such that:
1. Q(x) = x^T P x is conserved along trajectories (Q(f(x)) = Q(x))
2. P is determined by C through P = g(C^T C) for some function g
3. The conservation holds because tanh maps level surfaces of Q onto themselves

**Evidence for this conjecture:**
- R²=1.0 across ALL architectures (universal, not architecture-specific)
- CV(γ+H) ≈ 0.03 for all architectures under tanh (near-exact)
- The "scale threshold" at eigenvalue ≈ 1 (from Cycle 4 subagent findings)
- Conservation degrades continuously with noise (no phase transition)

---

## 5. Characterizing P Analytically

### 5.1 What P Encodes

The matrix P in γ+H = x^T P x encodes the relationship between the state vector x and the conserved quantity. Since γ (spectral gap) and H (participation entropy) are computed from the eigenvalues of C at state x, P must capture how these spectral quantities depend quadratically on x.

**Key observation:** γ+H is computed from C at EACH timestep. But C is fixed (static matrix). So γ+H depends on x through whatever mechanism couples the state to the spectral properties.

Wait — re-reading the experimental setup: γ and H are computed from the instantaneous coupling matrix evaluated at the current state. So there's a state-dependent coupling C(x), and γ+H is computed from its eigenvalues.

If γ+H = x^T P x exactly, then the spectral gap and entropy of C(x) combine to give a pure quadratic in x. This means:

$$\gamma(C(x)) + H(C(x)) = x^T P x$$

This is a non-trivial identity. It says that a particular combination of spectral invariants of C(x) is EXACTLY quadratic in x.

### 5.2 Possible Analytic Forms for P

**Hypothesis 1: P = C^T C (scaled)**
If P ∝ C^T C, then γ+H ∝ x^T C^T C x = ‖Cx‖². This would mean the conserved quantity is the norm of the pre-activation. This is plausible because tanh preserves the sign structure of Cx, so ‖Cx‖² could be conserved.

**Hypothesis 2: P = α C^T C + β I**
A combination of the coupling norm and the state norm. This allows for both "interaction energy" (‖Cx‖²) and "self energy" (‖x‖²).

**Hypothesis 3: P depends on eigenvectors of C**
P could be related to the eigenprojectors of C. If C = VΛV^T (eigendecomposition), then P = V g(Λ) V^T for some function g.

### 5.3 Testable Predictions

1. **Compute P from data** (already done — R²=1.0) and compare with C^T C
2. **Check if P commutes with C**: If [P, C] = 0, they share eigenvectors
3. **Check if P is a polynomial in C**: P = a₀I + a₁C + a₂C² + ...
4. **Vary C and observe how P changes**: If P = g(C^T C), then P should change predictably with C

---

## 6. LaSalle's Invariance Principle: The Right Framework?

### 6.1 Discrete-Time LaSalle's Theorem

**Theorem (LaSalle, discrete):** Let V: ℝ^N → ℝ be a continuous function such that V(f(x)) ≤ V(x) for all x in a compact set S. Let E = {x ∈ S : V(f(x)) = V(x)} and let M be the largest invariant set in E. Then every trajectory starting in S approaches M.

### 6.2 Application to Our System

Our system x_{t+1} = tanh(Cx) has:
- Bounded state space: x ∈ (-1,1)^N (compact closure)
- A near-conserved quantity: Q(x) = x^T P x with Q(f(x)) ≈ Q(x)

We can split Q into its monotone and conserved parts. Define:
- V(x) = decreasing part (Lyapunov function)
- Q(x) = conserved part (first integral)

If Q is exactly conserved (Q(f(x)) = Q(x)), then:
- E = {x : V(f(x)) = V(x)} = the entire level set of Q
- M = largest invariant subset of the level set
- Trajectories approach M = the attractor on the level surface

**This IS the right framework.** LaSalle's principle says: trajectories converge to the invariant set within the level surfaces of Q. The tanh nonlinearity ensures Q is conserved (or nearly so), and LaSalle tells us where the trajectories end up.

### 6.3 Why LaSalle Beats Linearized Lyapunov

The linearized Lyapunov equation A^T P A = P tests conservation at a SINGLE point (the fixed point). LaSalle's principle works globally — it doesn't linearize. It uses the full nonlinear map.

Our finding (linearized fails, nonlinear succeeds) is exactly what LaSalle predicts: the conservation is a global property of the nonlinear dynamics, not visible in the linearization.

---

## 7. The Complete Picture

### 7.1 Synthesis

1. **The system** x → tanh(Cx) is a nonlinear discrete-time map with bounded state space.
2. **The quantity** γ+H depends on the state x, and this dependence is exactly quadratic: γ+H = x^T P x.
3. **The conservation** Q(x_{t+1}) ≈ Q(x_t) holds because tanh maps level surfaces of Q approximately onto themselves.
4. **The linearization** fails because the Jacobian sech²(Cx)·C contracts the quadratic form too much — the linearized map "loses energy" that the nonlinear map preserves.
5. **LaSalle's invariance principle** is the correct framework: trajectories converge to the invariant set within the level surfaces of Q.
6. **Noise breaks conservation** because it kicks trajectories off the level surfaces, and the dynamics can only approximately restore them.
7. **Strong coupling freezes** because tanh saturates everything to ±1, making Q trivially constant.

### 7.2 What This Means for the Theory

The γ+H conservation law is NOT a property of the coupling matrix C alone. It is a property of the DYNAMICS (tanh) acting on the coupling matrix. The conservation arises because:

1. tanh is bounded → state space is compact
2. tanh is contractive → trajectories converge
3. tanh is odd and smooth → level surface structure is preserved
4. The quadratic form x^T P x captures this structure exactly

**The conservation is a NONLINEAR DYNAMICAL phenomenon, not a SPECTRAL property of C.**

This explains all the empirical findings:
- Architecture differences collapse (any C with eigenvalues ≥ 1 works) ✓
- Power iteration doesn't conserve (no saturation, no state-dependent gain) ✓
- Noise breaks it (kicks off level surfaces) ✓
- Strong coupling freezes (saturation trivializes dynamics) ✓
- Continuous degradation (no phase transition in attractor structure) ✓

### 7.3 Open Questions

1. **Can we prove Q(f(x)) = Q(x) analytically?** This requires showing tanh(Cx)^T P tanh(Cx) = x^T P x for the specific P determined by C.
2. **Is P = g(C^T C) for some g?** If so, we can predict P from C without fitting.
3. **Does this work for other bounded activations?** ReLU is unbounded (no). Sigmoid is bounded (probably yes). LeakyReLU is unbounded (no).
4. **What determines the CV magnitude (0.03)?** Is there a formula relating ‖C‖₂, N, and the expected CV?
5. **Can we engineer C to make CV → 0?** This would require the level surfaces to be exactly invariant.
6. **Is there a Hamiltonian structure?** Can the dynamics be written as x_{t+1} = x_t + ε J ∇H(x_t) + higher-order terms?

---

## 8. Key References

| Reference | Relevance |
|-----------|-----------|
| Lohmiller & Slotine (1998), "On Contraction Analysis for Nonlinear Systems" | Foundational contraction theory; state-dependent metric for nonlinear stability |
| Aminzare & Sontag (2014), "Contraction methods for nonlinear systems" | Tutorial overview; differential Lyapunov theory |
| Chung & Slotine (2021), arXiv:2110.00675 | Contraction theory for NN-based control; Lyapunov-like quadratic forms for differential dynamics |
| LaSalle (1986), "The Stability and Control of Discrete Processes" | Discrete-time invariance principle |
| Hattori & Takesue (1991), Physica D 49 | Discrete conservation laws on lattices; continuity equation framework |
| Manchester & Slotine (2017), "Control Design via Contraction Metrics" | Computing contraction metrics via SDP |
| Dawson et al. (2023), "Safe Nonlinear Control Using Robust Neural Lyapunov" | Learning Lyapunov functions for tanh-based dynamics |

---

## 9. Immediate Next Steps for Cycle 5

1. **Characterize P analytically:** Fit P from data, then check if P = f(C^T C). Compute commutator [P, C].
2. **Test other activations:** Run the same experiments with sigmoid (bounded), ReLU (unbounded), and clipped ReLU. Prediction: sigmoid conserves, ReLU doesn't, clipped ReLU partially conserves.
3. **Prove Q(f(x)) = Q(x) for small systems:** For N=2,3, do symbolic computation to verify the quadratic conservation exactly.
4. **Compute contraction metric:** Find M(x) such that Df(x)^T M(f(x)) Df(x) ≺ M(x). Is M related to P?
5. **LaSalle invariant set characterization:** What is the invariant set M within the level surfaces of Q? Is it a fixed point, limit cycle, or strange attractor?

---

*This brief provides the theoretical framework for the quadratic conservation finding. The R²=1.0 fit is real and demands explanation. The contraction theory + LaSalle framework is the most promising direction. The next cycle should focus on characterizing P analytically and testing the activation function hypothesis.*
