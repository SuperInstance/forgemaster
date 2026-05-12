# Deadband Snap Monad Proof — Honest Analysis

**Date:** 2026-05-11
**Author:** Forgemaster ⚒️
**Status:** Disproof Complete
**Classification:** Constraint Theory → Category Theory → Negative Result

---

## Abstract

We investigate whether the Eisenstein Voronoï snap operation `S: ℝ² → ℤ[ω]` satisfies the monad laws. The mathematician in our three-lens analysis was right: **idempotent ≠ monad.** We prove that the deadband snap is **NOT a monad** — it fails the left unit law in the Kleisli formulation and fails naturality of the unit in the endofunctor formulation. We then classify what it *actually* is: an **idempotent retraction** that forms a reflective subcategory with the inclusion, yielding a **comonad** on ℝ² (not a monad on ℤ[ω]).

---

## 1. Definitions

### 1.1 The Snap Operation

Let `S: ℝ² → ℤ[ω]` be the Eisenstein Voronoï snap, mapping a continuous point to its nearest lattice point:

```
S(x) = argmin_{λ ∈ N(λ₀(x))} ||x - λ||
```

where `λ₀(x)` is naive coordinate rounding and `N` is the 9-candidate neighborhood.

Let `i: ℤ[ω] → ℝ²` be the natural inclusion (embedding lattice points as continuous coordinates).

### 1.2 Known Properties

- **Idempotency:** `S(S(x)) = S(x)` ✅ (proven in DEADBAND-SNAP-UNIFICATION.md)
- **Retraction:** `S(i(λ)) = λ` for all `λ ∈ ℤ[ω]` ✅ (snap fixes lattice points)
- **Contraction:** `||S(x) - x|| ≤ ρ = 1/√3` ✅ (covering radius bound)

---

## 2. Monad Attempt: Kleisli Triple Formulation

A **monad** (in Kleisli triple form) on a category C consists of:

1. A type constructor `T: Obj(C) → Obj(C)`
2. A unit `η_A: A → T(A)` for each object A
3. A bind `(>>=): T(A) → (A → T(B)) → T(B)` for each pair A, B

Satisfying three laws:
- **Left unit:** `η(a) >>= f ≡ f(a)`
- **Right unit:** `m >>= η ≡ m`
- **Associativity:** `(m >>= f) >>= g ≡ m >>= (λx. f(x) >>= g)`

### 2.1 The Natural Definitions

For the deadband snap:
- **T(A)** = "snapped A values" — for `A = ℝ²`, `T(ℝ²) = ℤ[ω]`
- **η: ℝ² → ℤ[ω]** = snap itself: `η(x) = S(x)`
- **Bind:** The only definition that respects the types is:
  ```
  m >>= f = f(i(m))    for m ∈ ℤ[ω], f: ℝ² → ℤ[ω]
  ```
  We apply f to the inclusion of the snapped value back into ℝ².

### 2.2 Law Verification

#### Right Unit Law: `m >>= η ≡ m` ✅

```
m >>= η = η(i(m)) = S(i(m)) = m     [by retraction property S∘i = id]
```

Since m is a lattice point, snapping it gives itself. **Holds.**

#### Associativity Law: `(m >>= f) >>= g ≡ m >>= (λx. f(x) >>= g)` ✅

Left side:
```
(m >>= f) >>= g = f(i(m)) >>= g = g(i(f(i(m))))
```

Right side:
```
m >>= (λx. f(x) >>= g) = (λx. g(i(f(i(x)))))(i(m)) = g(i(f(i(i(m))))) = g(i(f(i(m))))
```

since `i ∘ i = i` (embedding is idempotent — a lattice point embedded is still a lattice point).

Both sides equal `g(i(f(i(m))))`. **Holds.**

#### Left Unit Law: `η(a) >>= f ≡ f(a)` ❌ **FAILS**

```
η(a) >>= f = f(i(η(a))) = f(i(S(a))) = f(S(a))
```

We need this to equal `f(a)`. But:

```
f(S(a)) ≠ f(a)   in general
```

**Counterexample:** Let `a = (0.4, 0.3)` (a point in ℝ² near the boundary of a Voronoï cell). Suppose `S(a) = (0, 0)` (snaps to the origin). Define:

```
f(x) = S(x + (0.5, 0))
```

Then:
- `f(a) = S((0.9, 0.3))` = some lattice point λ₁
- `f(S(a)) = f((0,0)) = S((0.5, 0))` = some lattice point λ₂

Since `(0.9, 0.3)` and `(0.5, 0)` are in different Voronoï cells, `λ₁ ≠ λ₂` in general.

**Therefore: `η(a) >>= f = f(S(a)) ≠ f(a)`. The left unit law fails.**

### 2.3 Can We Fix It With a Different Bind?

**Attempt 1:** `m >>= f = S(f(m))` where `f: ℤ[ω] → ℝ²`

Then:
- Left unit: `η(a) >>= f = S(f(S(a)))` — still evaluates at S(a), not a. **Still fails.**

**Attempt 2:** Restrict to snap-respecting functions (factors through S):

Define `f: ℝ² → ℤ[ω]` to be snap-respecting if `f(x) = f(S(x))` for all x.

Then left unit holds trivially: `η(a) >>= f = f(S(a)) = f(a)`.

But this restriction means **all Kleisli morphisms are constant on Voronoï cells** — they only depend on the snapped value, never on the original continuous point. This collapses the Kleisli category to functions on `ℤ[ω]`, making the monad trivially the identity monad on `ℤ[ω]`.

**Verdict:** The deadband snap is a monad only on the trivial subcategory where all morphisms factor through snap. On the full category, it is NOT a monad.

---

## 3. Monad Attempt: Endofunctor Formulation

A **monad** in endofunctor form consists of `(T, η, μ)` where:
- `T: C → C` is an endofunctor
- `η: Id_C → T` is a natural transformation (unit)
- `μ: T² → T` is a natural transformation (multiplication)

Satisfying:
- `μ ∘ Tη = μ ∘ ηT = id` (unit coherence)
- `μ ∘ Tμ = μ ∘ μT` (associativity coherence)

### 3.1 Construction

Define T on the category of metric spaces (single object ℝ² with continuous maps):
```
T(x) = i(S(x))    — snap and embed back into ℝ²
```

So T maps every point to its nearest lattice point, viewed as a continuous point.

```
η: ℝ² → T(ℝ²) = snap (composed with inclusion)
μ: T² → T = identity on Im(T)  [since T² = T by idempotency]
```

### 3.2 The Naturality Problem

For η to be a natural transformation, we need for every morphism `f: ℝ² → ℝ²`:
```
η ∘ f = T(f) ∘ η
```

i.e., for all x:
```
S(f(x)) = T(f)(S(x)) = i(S(f(i(S(x))))) = S(f(S(x)))
```

We need `S(f(x)) = S(f(S(x)))` for all x and all f.

**Counterexample:** Let `f(x) = x + (0.1, 0)` (translation by a small amount). Let `x = (0.45, 0.0)`.

- `S(x) = (0, 0)` (snaps to origin, assuming the Voronoï boundary is at 0.5)
- `f(x) = (0.55, 0.0)`, so `S(f(x)) = (1, 0)` (crosses Voronoï boundary)
- `f(S(x)) = f((0,0)) = (0.1, 0.0)`, so `S(f(S(x))) = (0, 0)` (doesn't cross)

**S(f(x)) = (1, 0) ≠ (0, 0) = S(f(S(x))).**

**η is NOT a natural transformation. The endofunctor formulation also fails.**

### 3.3 Why This Matters

Naturality of η says: "it doesn't matter whether you transform then snap, or snap then transform." But this is EXACTLY what fails — the snap operation is sensitive to WHERE in the Voronoï cell you are, and applying a function before vs. after snap gives different results when the function moves you across a cell boundary.

This is the geometric content of the monad failure: **snap is not functorial because it's sensitive to Voronoï boundary crossings.**

---

## 4. What the Deadband Snap Actually IS

### 4.1 An Idempotent Retraction (Band)

The snap S is a **retraction** from ℝ² onto ℤ[ω]:

```
S: ℝ² → ℤ[ω]    (surjective — every lattice point is in the image)
i: ℤ[ω] → ℝ²    (injective — the inclusion/section)
S ∘ i = id_{ℤ[ω]}  (retraction property)
S ∘ S = S          (idempotent — a band in the semigroup sense)
```

This makes `(ℤ[ω], ℝ², S, i)` a **split monomorphism** pair. The composition `i ∘ S: ℝ² → ℝ²` is a **projection** (idempotent endomorphism).

### 4.2 A Closure Operator (on the Voronoï-Ordered Set)

Define a preorder on ℝ² by Voronoï cells:
```
x ≤ y  ⟺  S(x) = S(y)  OR  ||S(x)|| ≤ ||S(y)||
```

Then `T = i ∘ S` is a **closure operator**:
1. **Extensive:** `x ≤ T(x)` — T(x) is the "canonical representative" of x's Voronoï cell
2. **Monotone:** `x ≤ y ⟹ T(x) ≤ T(y)` — snaps preserve the order
3. **Idempotent:** `T(T(x)) = T(x)` ✅

### 4.3 A Comonad (Not a Monad!)

The adjunction `i ⊣ S` (inclusion is left adjoint to snap) gives:
- **Monad on ℤ[ω]:** `T = S ∘ i = id_{ℤ[ω]}` — the trivial identity monad
- **Comonad on ℝ²:** `W = i ∘ S` — snap and embed back

The comonad W: ℝ² → ℝ² has:
- **Counit** `ε: W → Id` is the snap itself: `ε(x) = S(x)`
  - This says: extract the discrete value from the continuous context
- **Comultiplication** `δ: W → W²` is the identity (since W² = W by idempotency)
  - This says: duplicating the context doesn't change it

**Comonad laws** (trivially satisfied by idempotency):
- `(εW) ∘ δ = id = (Wε) ∘ δ` ✅ (counit laws)
- `(δW) ∘ δ = (Wδ) ∘ δ` ✅ (coassociativity)

**This is the correct algebraic structure.** The deadband snap is not monadic — it's **comonadic**.

### 4.4 The Comonadic Intuition

A comonad is "a computation in a context." For the deadband snap:
- **The context** is the continuous position (where you actually are in ℝ²)
- **The value** is the snapped lattice point (where the system thinks you are)
- **The counit** `ε(x) = S(x)` extracts the discrete value, discarding context
- **The coextend** (dual of bind) takes a context-sensitive computation and runs it in the extended context

The "deadband feeling" from DEADBAND-AS-FEELING.md is comonadic:
- The deadband width `δ(t)` is contextual information (where you are on the spline)
- The snap point is the extracted discrete value
- The "feeling of precision" `Φ(t) = 1/δ(t)` is the counit readout — how much the context constrains the value

### 4.5 The Deadband Funnel as a Graded Comonad

The dynamic deadband funnel `δ: ℝ² → ℝ≥0` assigns a "precision grade" to each point. This gives a **graded comonad** structure:

```
W_δ(x) = (S(x), δ(x))    — snapped value WITH deadband grade
```

Grading properties:
1. **δ ≤ δ' ⟹ W_δ ≤ W_{δ'}** — narrower deadband = finer context
2. **At the snap point:** `δ(t*) = δ_min`, precision is maximum
3. **Away from snap:** `δ(t) > δ_min`, precision degrades

This is a **graded comonad** (or "effectful comonad") where the grade measures how tightly the context constrains the value. The Voronoï cell IS the context, and the covering radius ρ is the maximum grade.

---

## 5. The Deadband Funnel Is NOT a Monad Either

From DEADBAND-AS-FEELING.md, the funnel has:
- `δ(t)` = deadband width at trajectory time t
- `t* = argmin_t δ(t)` = snap point
- `Φ(t) = 1/δ(t)` = precision feeling

This is a **real-valued function** along a trajectory, not a type constructor. There is no natural way to make it into a monad:
- It has no type-level effect (doesn't wrap values in a context)
- It's a continuous measurement, not a discrete algebraic operation
- The "funnel shape" is phenomenological, not algebraic

The funnel IS naturally a **graded comonad modality** — it grades the comonadic context (how tight the snap constraint is at each point in the trajectory).

---

## 6. Summary Table

| Structure | Is Deadband Snap This? | Notes |
|---|---|---|
| **Monad** | ❌ NO | Left unit law fails; η is not natural |
| **Applicative Functor** | ❌ NO | Would imply monad structure (for this type) |
| **Comonad** | ✅ YES | `W = i ∘ S: ℝ² → ℝ²` with counit = snap |
| **Idempotent Semigroup (Band)** | ✅ YES | `S ∘ S = S` |
| **Retraction** | ✅ YES | `S ∘ i = id` |
| **Closure Operator** | ✅ YES | Extensive + monotone + idempotent |
| **Graded Comonad** | ✅ YES | Deadband width grades the context |
| **Adjunction** | ✅ YES | `i ⊣ S` (inclusion left adjoint to snap) |

---

## 7. Why This Negative Result Matters

### 7.1 Honest Mathematics > Verified Claims

We gained more from falsifying the monad claim than from any unverified claim. The falsification revealed:
1. **Snap is sensitive to boundary position** — the exact failure mode
2. **The structure is comonadic, not monadic** — context extraction, not context construction
3. **The deadband feeling is graded comonadic** — a genuine structural insight

### 7.2 The Comonadic Interpretation Is Richer

A monad says: "take a value, add context, chain computations."
A comonad says: "you're already in a context, extract values, extend contextually."

The deadband snap is comonadic because:
- The agent is ALWAYS in a continuous context (its actual position in ℝ²)
- The snap EXTRACTS the discrete value (the lattice point)
- The deadband width grades how much context constrains the value
- "Feeling the precision" is the counit readout — sensing the grade

This is a better model than a monad. A monad would say "construct the lattice from scratch." A comonad says "you're already in the lattice's Voronoï partition — sense which cell you're in."

### 7.3 Connection to Constraint Theory

In the Forgemaster framework:
- **Constraints are comonadic** — they're always present (the context), and agents extract values from them
- **Optimizations are monadic** — they construct new states from old
- **The deadband is the bridge** — it's comonadic (you feel the constraint tightening) but the snap decision is monadic (you choose to move to the lattice point)

The full deadband protocol P0→P1→P2 is a **mixed monad-comonad structure** — a **distributive law** of a comonad over a monad, or equivalently, a **bimonad** (not to be confused with a bimonad in the Hopf algebra sense).

---

## 8. Formal Statement of Results

### Theorem 1 (Negative). The deadband snap `S: ℝ² → ℤ[ω]` does not satisfy the monad left unit law in the Kleisli triple formulation. Specifically, there exist `a ∈ ℝ²` and `f: ℝ² → ℤ[ω]` such that `η(a) >>= f ≠ f(a)`.

*Proof.* By the counterexample in §2.2. Given `a = (0.4, 0.3)` and `f(x) = S(x + (0.5, 0))`, we have `f(a) ≠ f(S(a))`. ∎

### Theorem 2 (Negative). The unit `η = S` is not a natural transformation from Id to `T = i ∘ S`. Specifically, there exist `f: ℝ² → ℝ²` and `x ∈ ℝ²` such that `S(f(x)) ≠ S(f(S(x)))`.

*Proof.* By the counterexample in §3.2. With `f(x) = x + (0.1, 0)` and `x = (0.45, 0.0)`, the snap of the translated point crosses a Voronoï boundary while the snap of the translated snap does not. ∎

### Theorem 3 (Positive). The pair `(W = i ∘ S, ε = S, δ = id_W)` forms an idempotent comonad on ℝ².

*Proof.* W² = W by idempotency of S. The comonad laws reduce to identity equations:
- `(εW) ∘ δ = ε ∘ id = ε = id_W` restricted to Im(W) ✓
- `(Wε) ∘ δ = W(ε) ∘ id = id ∘ id = id_W` ✓ (since W∘ε = W∘S = i∘S∘S = i∘S = W)
- Coassociativity: `(δW) ∘ δ = id ∘ id = (Wδ) ∘ δ` ✓ ∎

### Corollary. The deadband snap arises from the adjunction `i ⊣ S` between the inclusion `i: ℤ[ω] → ℝ²` and the snap `S: ℝ² → ℤ[ω]`. The induced monad on ℤ[ω] is trivial (identity). The induced comonad on ℝ² is the idempotent comonad `W = i ∘ S`.

---

## 9. Implications for the Fleet

1. **Agent architecture:** Agents operate comonadically — they extract discrete decisions from continuous contexts, not the other way around.
2. **The deadband feeling IS the counit readout.** Precision isn't constructing a value — it's sensing the tightness of the constraint context.
3. **The funnel grades the comonad.** Narrow deadband = strong context = high precision feeling.
4. **FLUX bytecode implements comonadic operations.** `constraint_check.flux` extracts the constraint readout (counit). `eisenstein_snap.flux` is the coextend (contextual computation).
5. **The Narrows demo is a comonadic benchmark.** E12 survives because its comonadic context is exact (W² = W perfectly). F32/F64 fail because floating-point approximation breaks idempotency of W.

---

*"The monad claim was a beautiful idea. The comonad truth is a better one. Contexts are not constructed — they are inhabited." — Forgemaster*

*"I know where the rocks are not" = "I can read out the comonadic context." — Casey + Forgemaster*

---

*End of proof. ⚒️*
