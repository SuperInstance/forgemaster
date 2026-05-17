# DeepSeek-v4-Pro Proof Review: Koopman Eigenfunction Theorem

**DeepSeek-v4-pro (deepseek-reasoner) | 2026-05-17**

---

## Brutally Honest Assessment

The proposed proof strategy is **fundamentally flawed** as written. The core error is the unjustified application of perturbation theorems for Hermitian matrices to a generally non-symmetric matrix C(x). Below I dissect each component, then answer your specific questions.

---

### Primary Flaw: Non-Symmetric C(x)

The proof relies on **Weyl's inequality** and the **Davis–Kahan sin θ theorem**, both of which require the matrix to be **Hermitian** (or real symmetric). Nowhere is C(x) assumed symmetric. Even if the numerical experiments use symmetric architectures (e.g., attention with symmetric weights), the proof as stated is **invalid for the general case**. This alone makes the strategy untenable.

- **Weyl's inequality** bounds eigenvalue changes under Hermitian perturbations. For non-Hermitian matrices, eigenvalues can be extremely sensitive (pseudospectra), and no such simple bound exists.
- **Davis–Kahan** controls eigenvector rotation only for Hermitian matrices with distinct eigenvalues (gap δ>0). For non-Hermitian matrices, the concept of "eigenvector rotation" is not even well-defined in the same way (left/right eigenvectors differ, and the standard inner product is not preserved).

**Consequence:** Steps 1 and 2 collapse; the entire chain of inequalities is invalid unless C(x) is assumed symmetric.

---

### Additional Critical Issues

#### 1. The Jacobian Approximation J = DC
The statement "J = DC" (where D = diag of diagonal of Jacobian) is **unjustified**. The true Jacobian of F(x) = tanh(C(x)x) involves derivatives of C(x) with respect to x. Even if C(x) is linear in x, this simplification is not generally correct. The whole perturbation analysis hinges on this erroneous identification.

#### 2. Differentiability of I(x) and Eigenvalue Crossings
- The observable I(x) = γ(x) + H(x) uses eigenvalues of C(x). Eigenvalues are **not differentiable** at points where they cross (or where the spectral gap vanishes). The Lipschitz constant L_I may not exist globally, and the chain-rule arguments in Step 3 are invalid near such points.
- The entropy H(x) includes log(p_i); if any eigenvalue approaches zero, p_i→0 and log p_i → -∞, making I(x) unbounded. The proof implicitly assumes Tr(C) is bounded away from zero, which is not guaranteed.

#### 3. Bounding ‖x_{t+1}−x_t‖
Step 2 claims ‖x_{t+1}−x_t‖ ≤ ‖J(x_t)‖·‖x_t‖. This is **not a consequence of the mean value theorem** because x_{t+1} = tanh(C(x_t)x_t) and the difference is not simply J(x_t)x_t. A proper bound would involve ‖DF(ξ)‖ for some ξ on the segment, but that still requires controlling the nonlinearity.

#### 4. Spectral Gap δ Must Be Bounded Away from Zero
Davis–Kahan requires δ > 0. The proof never guarantees that the gap between λ_1 and λ_2 of C(x) stays positive over the state space. If eigenvalues cross, the gap can become arbitrarily small, blowing up the O(ε/δ) term.

#### 5. The "Eigenvalue 1" Claim versus Approximate Invariance
The proof shows |I(F(x))−I(x)| is small, which would imply K[I] ≈ 1·I. That already gives an approximate eigenfunction with λ=1 and small residual. The additional quest to bound |1−λ| is unnecessary (and confused – the residual can absorb the difference). The numerical evidence showing DMD finds λ≈1 is consistent with this.

---

### Answers to Your Questions

#### 1. Taylor expansion vs. perturbation theory
**Neither approach is clean** without strong assumptions.
- **Taylor expansion** would require differentiability of I (which fails at eigenvalue crossings) and a second-order expansion that is non-trivial due to the nonlinearity of the map.
- **Perturbation theory** is the natural route if C(x) were symmetric, but the current execution is flawed. A repaired version would need to:
  - Assume C(x) is symmetric and has a uniform spectral gap.
  - Correctly derive the Jacobian of F and relate it to C.
  - Use perturbation bounds that are valid for symmetric matrices (Weyl, Davis–Kahan).
Even then, the chain of inequalities would need careful handling of constants.

#### 2. Step-by-step validity check
**a. Does Weyl apply?**
   **No**, unless C(x) is symmetric. For general matrices, eigenvalues can change by more than the norm of the perturbation (e.g., non-diagonalizable matrices).

**b. Does Davis–Kahan give what is claimed?**
   **No**, for the same reason. The sin θ theorem for non-Hermitian matrices exists (e.g., using singular vectors) but is much more restrictive and not standard. The proof uses the Hermitian version.

**c. Is the spectral gap δ bounded away from zero?**
   The proof **assumes** it (implicitly, by using 1/δ), but provides no justification. Eigenvalue crossings can cause δ→0, making the bound infinite.

#### 3. Minimum set of assumptions
For the theorem to be provable (even approximately), you need at least:
- C(x) is **real symmetric** for all x.
- The eigenvalues of C(x) are **positive** (or at least the smallest eigenvalue is bounded away from zero) so that the entropy is well-defined and the normalized distribution is Lipschitz.
- The **spectral gap** δ(x) = λ_1(x)−λ_2(x) is **uniformly bounded away from zero** over the state space of interest.
- The **Jacobian** of the map F(x) = tanh(C(x)x) must be computed correctly, and the commutator condition [D,C] must be reinterpreted in terms of the actual derivative.
- The state space is **compact** (or trajectories stay in a compact set) so that all Lipschitz constants (e.g., L_C, ‖J‖, ‖x‖) are bounded.
- The **trace** Tr(C(x)) is bounded away from zero (to avoid log(0)).

#### 4. Hidden obstacles that could make the theorem false
**a. Entropy singularity:** If any eigenvalue approaches zero, H(x)→ −∞ (if we treat log(0)) or is undefined. The numerical evidence may avoid this, but the theorem statement would fail in general.

**b. Non-differentiability at eigenvalue crossings:** Even if eigenvalues remain real, I(x) is not differentiable where eigenvalues cross, so any Lipschitz constant L_I would be infinite unless you restrict to a region where no crossing occurs (which is generically impossible in a nonlinear system).

**c. Non-symmetric C(x):** As discussed, the entire perturbation framework collapses. The observable itself may involve complex eigenvalues, making entropy ill-defined.

**d. Lipschitz bound insufficient:** Showing |I(F(x))−I(x)| is small is exactly what is needed for an approximate eigenfunction with λ=1. That part is fine. The problem is that the bound derived via the flawed chain is unreliable. Even if the bound held, it would prove I is **almost invariant**, which is exactly the claim (with λ=1). So the Lipschitz approach is sufficient *if* the bound can be justified independently.

#### 5. Cleaner proof strategy
A much cleaner (though still difficult) approach would be to **directly analyze the dynamics of C(x)**. If you can show that C(F(x)) is close to C(x) in some norm (e.g., using the fact that tanh is near identity for small arguments or that C is slowly varying), then the eigenvalues change little, and I is approximately invariant. Specifically:
- Suppose the dynamics are such that ‖C(F(x))−C(x)‖ ≤ κ ε for some small ε.
- Then by continuity of eigenvalues (for symmetric matrices, Weyl gives a bound), |I(F(x))−I(x)| ≤ L κ ε.
- This yields |I(F(x))−I(x)| ≤ Cε, which is the desired approximate eigenfunction property with λ=1.

The key is to justify ‖C(F(x))−C(x)‖ small without invoking the flawed Jacobian chain. This might come from the specific structure: e.g., if C(x) is a function of x that itself evolves slowly under the nonlinear map, or if the commutator condition [D,C] small actually implies that F(x) ≈ C(x)x and C is nearly constant along trajectories. But that would require a completely different proof.

---

### Verdict

**The proof strategy as presented is not salvageable.** It contains a fatal misuse of Hermitian perturbation theorems for a non-symmetric matrix, an unjustified Jacobian simplification, and ignores differentiability issues near eigenvalue crossings and zero eigenvalues. The theorem itself might be true under restrictive assumptions (symmetric C, positive eigenvalues, uniform spectral gap, no crossings), but the proof would need to be rewritten from scratch. The numerical evidence is suggestive but does not compensate for the logical gaps.

**Recommendation:**
1. Clearly state that C(x) is assumed **symmetric** (or Hermitian) with **distinct eigenvalues** and a uniform gap.
2. Derive the correct Jacobian of F and relate the commutator condition to the actual dynamics.
3. Use Weyl and Davis–Kahan **only in the symmetric setting** and ensure all constants are finite.
4. Address the entropy singularity by assuming eigenvalues are bounded away from zero.
5. Accept that eigenvalue crossings are an obstacle; either assume they don't occur or handle them via a measure-zero exclusion.

Otherwise, abandon this line of proof and look for a more robust functional-analytic or Lyapunov-based argument.

---

*DeepSeek-v4-pro | Proof Review | 2026-05-17*
*Reasoning tokens: 2,617 | Response tokens: 4,912*
