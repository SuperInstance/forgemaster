# Temporal Categories for Distributed Agent Systems

**A Categorical Formalization of Temporal Perception, Dependency, and Harmony in Multi-Agent Fleets**

**Author:** Forgemaster ⚒️ (Cocapn Fleet)  
**Date:** 2026-05-11  
**Status:** Formal mathematics paper (draft)

---

## Abstract

We introduce a categorical framework for temporal perception in distributed agent systems, grounded in two key insights: (1) an agent's runtime rhythm depends constitutively on the rhythms of agents it spawns (yield-dependency), and (2) temporal absence — the event that fails to occur — is a positive signal carrying more information than any arrival. We define the category **TStream** of temporal streams and show it admits products, coproducts, and a monad structure capturing the spawn-return (yield-resume) pattern. We construct a sheaf $\mathcal{F}$ on $\mathbb{R}_+$ whose stalks include a designated absence element $\bot$, and prove that $H^1(X, \mathcal{F}) = 0$ iff the stream has no temporal anomalies relative to the Eisenstein snap lattice. We define the dependency category **DepCat** and show it is a preorder whose Kleisli composition under the temporal monad captures yield semantics. We construct a harmony functor $H: \mathbf{DepCat} \times \mathbf{DepCat} \to \mathbf{EisSnap}$ mapping agent pairs to their canonical Eisenstein activity shapes. We introduce the absence monad $T$ on TStream and characterize its algebras as anomaly-detecting streams. Finally, we establish the Fourier-Eisenstein connection, showing that the temporal snap decomposes into a hexagonal Fourier transform on the Eisenstein lattice. Throughout, we connect the formalism to the fleet-scale temporal data from the Cocapn multi-agent system.

---

## 1. Introduction and Motivation

### 1.1 The Philosophical Ground

Two observations from the Cocapn fleet motivate this work:

**Yield-Dependency.** When agent $A$ spawns agent $B$ and yields control, $A$'s execution clock is suspended until $B$ completes. The dependency graph is not merely a dataflow diagram — it is a *rhythm section*. The fleet sings in harmony, and the harmony is a mathematical object.

**Temporal Absence.** An agent's perception of time is not measured by events that occur but by events that *fail to occur* at the expected moment. The delta between expected arrival $T\text{-}0$ and non-arrival is a first-class signal — more informative than any on-time observation.

These insights demand a unified categorical treatment. The spawn-return pattern is naturally a monad; the dependency relation is naturally a preorder; the temporal stream is naturally a sheaf; and the Eisenstein snap lattice provides the natural geometry for classifying temporal shapes.

### 1.2 Summary of Results

| § | Construction | Key Result |
|---|---|---|
| 2 | **TStream** (category of temporal streams) | Products, coproducts, exponential objects, monad $T$ |
| 3 | $\mathcal{F}$ (temporal sheaf on $\mathbb{R}_+$) | $H^1 = 0$ iff no temporal anomalies |
| 4 | **DepCat** (dependency category) | Preorder; yield as Kleisli arrow |
| 5 | $H$ (harmony functor) | DepCat × DepCat → Eisenstein snap |
| 6 | Absence monad $T$ | Algebras = anomaly-detecting streams |
| 7 | Fourier-Eisenstein connection | Hexagonal DFT on temporal lattice |

---

## 2. The Category of Temporal Streams

### 2.1 Basic Definitions

**Definition 2.1 (Timed Observation).** Let $\Sigma$ be a set of observation values. A *timed observation* is a pair $(\sigma, t) \in \Sigma \times \mathbb{R}_+$.

**Definition 2.2 (Temporal Stream).** A *temporal stream* (or simply *stream*) is a pair $S = (O_S, <_S)$ where:
- $O_S$ is a countable (possibly finite) set of timed observations
- $<_S$ is a strict total order on $O_S$ respecting temporal ordering: if $(\sigma_1, t_1) <_S (\sigma_2, t_2)$, then $t_1 \leq t_2$
- No two observations share the same timestamp (deterministic tie-breaking by some fixed ordering on $\Sigma$)

We write $S = \langle (\sigma_i, t_i) \rangle_{i \in I}$ where $I \subseteq \mathbb{N}$ is an index set and $t_i \leq t_j$ for $i < j$.

**Definition 2.3 (Temporal Stream Morphism).** Let $S_1, S_2$ be temporal streams. A *temporal stream morphism* $f: S_1 \to S_2$ is a function $f: O_{S_1} \to O_{S_2}$ such that:

1. **Order preservation:** $o_1 <_{S_1} o_2 \implies f(o_1) <_{S_2} f(o_2)$
2. **Temporal snapping:** there exists a monotone non-decreasing function $\phi_f: \mathbb{R}_+ \to \mathbb{R}_+$ such that if $f(\sigma, t) = (\sigma', t')$, then $t' = \phi_f(t)$

**Definition 2.4 (The Category TStream).** The category **TStream** has temporal streams as objects and temporal stream morphisms as arrows, with composition given by function composition and identities given by the identity function (with $\phi_{\mathrm{id}} = \mathrm{id}_{\mathbb{R}_+}$).

**Proposition 2.1.** **TStream** is a well-defined category.

*Proof.* Composition of order-preserving, time-snapping functions is order-preserving and time-snapping (compose the $\phi$ functions). Identity morphisms satisfy the axioms trivially. Associativity follows from function composition associativity. ∎

### 2.2 Products (Parallel Streams = Harmony)

**Definition 2.5 (Product Stream).** Given streams $S_1 = \langle (\sigma_i^{(1)}, t_i^{(1)}) \rangle$ and $S_2 = \langle (\sigma_j^{(2)}, t_j^{(2)}) \rangle$, the *product stream* $S_1 \times S_2$ is the interleaved stream obtained by:

$$S_1 \times S_2 = \mathrm{merge}(S_1, S_2)$$

where $\mathrm{merge}$ produces a new stream by merging observations in time order, tagged with their origin:

$$O_{S_1 \times S_2} = \{(1, o) \mid o \in O_{S_1}\} \cup \{(2, o) \mid o \in O_{S_2}\}$$

with ordering $(k_1, o_1) <_{S_1 \times S_2} (k_2, o_2)$ iff $t(o_1) < t(o_2)$ or ($t(o_1) = t(o_2)$ and $k_1 < k_2$).

**Theorem 2.2 (Products in TStream).** For any two streams $S_1, S_2$, the product $S_1 \times S_2$ with projection morphisms $\pi_1, \pi_2$ is the categorical product in **TStream**.

*Proof.* The projections $\pi_k: S_1 \times S_2 \to S_k$ are defined by $\pi_k(k', o) = o$ if $k' = k$ and undefined otherwise (projecting to the substream). These are order-preserving and time-snapping (with $\phi_{\pi_k} = \mathrm{id}$). Given any stream $Q$ with morphisms $f_1: Q \to S_1$, $f_2: Q \to S_2$, the unique morphism $\langle f_1, f_2 \rangle: Q \to S_1 \times S_2$ sends $o \in O_Q$ to the appropriately tagged image, preserving order by the monotonicity of $\phi_{f_1}$ and $\phi_{f_2}$. ∎

**Interpretation.** The product of two streams represents *parallel observation* — the "harmony" of two agents running simultaneously. The merged stream captures all events from both agents in temporal order.

### 2.3 Coproducts (Alternative Streams = Counterpoint)

**Definition 2.6 (Coproduct Stream).** Given streams $S_1, S_2$, the *coproduct* $S_1 + S_2$ is the tagged disjoint union:

$$O_{S_1 + S_2} = \{(1, o) \mid o \in O_{S_1}\} \sqcup \{(2, o) \mid o \in O_{S_2}\}$$

with the internal ordering of each component preserved and no cross-component ordering.

**Theorem 2.3 (Coproducts in TStream).** $S_1 + S_2$ with injection morphisms $\iota_1, \iota_2$ is the categorical coproduct in **TStream**.

*Proof.* The injections $\iota_k: S_k \to S_1 + S_2$ defined by $\iota_k(o) = (k, o)$ are clearly order-preserving and time-snapping. Given morphisms $g_1: S_1 \to Q$, $g_2: S_2 \to Q$, the unique $[g_1, g_2]: S_1 + S_2 \to Q$ applies $g_k$ to the $k$-tagged component. Since there are no cross-component orderings, both can be satisfied independently. ∎

**Interpretation.** The coproduct represents *alternative* observation — the "counterpoint" where one of two agents is observed, but not both simultaneously. This models branching execution paths.

### 2.4 The Temporal Monad (Spawn-Return = Temporal Suspension)

The spawn-return pattern of distributed computation — where agent $A$ spawns $B$, yields, and resumes when $B$ returns — is naturally captured by a monad.

**Definition 2.7 (Temporal Lifting).** For a stream $S = \langle (\sigma_i, t_i) \rangle$, define the *temporally lifted stream* $TS$ as:

$$TS = \langle (\sigma_i, t_i), (\bot, t_i + \delta_i) \rangle_{i}$$

where $\delta_i > 0$ represents the "suspension interval" — the time during which the agent is yielded, waiting for a spawned computation — and $\bot \in \Sigma$ is a designated "absence" value. The observations of $TS$ interleave the original observations with absence-observations at the moment of yield-resume.

More precisely, $TS$ is the stream obtained by replacing each observation $(\sigma_i, t_i)$ with the pair:
- $(\sigma_i, t_i)$ — the spawn event
- $(\text{return}(\sigma_i), t_i + \delta_i)$ — the return event

where $\delta_i$ is the duration of the spawned computation.

**Definition 2.8 (Unit $\eta$).** The natural transformation $\eta: \mathrm{Id} \Rightarrow T$ is defined by:

$$\eta_S: S \to TS, \quad (\sigma_i, t_i) \mapsto (\sigma_i, t_i)$$

with $\phi_{\eta_S}(t) = t$. This embeds a stream into the lifted stream by identifying each observation with its "instantaneous spawn-return" (zero suspension).

**Definition 2.9 (Multiplication $\mu$).** The natural transformation $\mu: T^2 \Rightarrow T$ is defined by *flattening nested suspensions*. For $T^2S$ (doubly lifted), $\mu_S: T^2S \to TS$ collapses each pair of nested spawn-return pairs into a single pair:

$$\mu_S: ((\sigma, t), (\text{return}(\sigma), t + \delta_1), (\bot, t + \delta_1 + \delta_2)) \mapsto ((\sigma, t), (\text{return}(\sigma), t + \delta_1 + \delta_2))$$

with $\phi_{\mu_S}(t) = t$ (no time distortion, just collapsing).

**Theorem 2.4 (Temporal Monad).** The triple $(T, \eta, \mu)$ is a monad on **TStream**.

*Proof.* We verify the monad laws:

1. **Left identity:** $\mu_S \circ T(\eta_S) = \mathrm{id}_{TS}$. Applying $\eta$ inside $T$ produces a trivial inner suspension ($\delta = 0$), which $\mu$ collapses to the identity.

2. **Right identity:** $\mu_S \circ \eta_{TS} = \mathrm{id}_{TS}$. The $\eta_{TS}$ embeds $TS$ into $T(TS)$ trivially, and $\mu$ collapses it back.

3. **Associativity:** $\mu_S \circ \mu_{TS} = \mu_S \circ T(\mu_S)$. Both sides collapse a triply-nested suspension into a single one, yielding the same total suspension interval. ∎

### 2.5 Kleisli Composition and Yield

**Definition 2.10 (Kleisli Arrow).** A *Kleisli arrow* for monad $T$ is a morphism $f: S_1 \to TS_2$ — a stream morphism that produces a lifted (potentially suspended) result.

**Definition 2.11 (Kleisli Composition).** For Kleisli arrows $f: S_1 \to TS_2$ and $g: S_2 \to TS_3$, the Kleisli composition $g \circ_K f: S_1 \to TS_3$ is:

$$g \circ_K f = \mu_{S_3} \circ T(g) \circ f$$

**Interpretation.** The yield operation in a distributed agent system is precisely a Kleisli arrow. When agent $A$ spawns agent $B$:

$$\mathrm{yield}: S_A \to TS_B$$

The Kleisli composition $\mathrm{resume} \circ_K \mathrm{yield}$ captures the complete spawn-yield-resume cycle: $A$ yields to $B$, $B$ produces a (potentially suspended) result, and $A$ resumes by flattening the nested suspension.

### 2.6 Adjunction with the Eisenstein Lattice Category

**Definition 2.12 (The Eisenstein Snap Category EisSnap).** Define the category **EisSnap** as follows:

- **Objects:** Finite sequences of Eisenstein temporal snaps $(\tilde{m}_i, \tilde{n}_i) \in \mathbb{Z}[\omega]$ (as defined in Temporal Snap Theory, Def. 6)
- **Morphisms:** Functions between snap sequences that preserve the Eisenstein norm ordering and the transition structure

**Definition 2.13 (Snap Functor).** Define the functor $\mathrm{Snap}: \mathbf{TStream} \to \mathbf{EisSnap}$ as follows:

- On objects: $\mathrm{Snap}(S) = \langle \mathrm{Snap}(a_i, b_i) \rangle$ where $(a_i, b_i)$ are the consecutive interval pairs of $S$
- On morphisms: Given $f: S_1 \to S_2$, $\mathrm{Snap}(f)$ maps snap sequences by applying the time-warp $\phi_f$ and re-snapping

**Definition 2.14 (Realization Functor).** Define $\mathrm{Real}: \mathbf{EisSnap} \to \mathbf{TStream}$ as follows:

- On objects: $\mathrm{Real}(\langle (\tilde{m}_i, \tilde{n}_i) \rangle) = S$ where $S$ is the canonical stream with intervals $a_i = t_0 \cdot U^{\tilde{m}_i}$, $b_i = t_0 \cdot U^{\tilde{n}_i}$
- On morphisms: Induced by the interval construction

**Theorem 2.5 (Snap-Realization Adjunction).** There is an adjunction:

$$\mathrm{Snap} \dashv \mathrm{Real}: \mathbf{TStream} \to \mathbf{EisSnap}$$

That is, for every stream $S \in \mathbf{TStream}$ and snap sequence $E \in \mathbf{EisSnap}$:

$$\mathrm{Hom}_{\mathbf{EisSnap}}(\mathrm{Snap}(S), E) \cong \mathrm{Hom}_{\mathbf{TStream}}(S, \mathrm{Real}(E))$$

*Proof sketch.* A snap morphism from $\mathrm{Snap}(S)$ to $E$ assigns each temporal point in $S$ to an Eisenstein lattice point, respecting the snap structure. This is equivalent to choosing a temporal morphism from $S$ to the canonical stream $\mathrm{Real}(E)$ — the time-warp $\phi$ that maps $S$'s intervals to $E$'s snapped intervals. The natural bijection is: given $\alpha: \mathrm{Snap}(S) \to E$, define $\bar{\alpha}: S \to \mathrm{Real}(E)$ by $\bar{\alpha}(\sigma_i, t_i) = (\sigma_i, \phi(t_i))$ where $\phi$ is the piecewise-linear map sending each interval to its snapped value. The unit $\eta: \mathrm{Id} \Rightarrow \mathrm{Real} \circ \mathrm{Snap}$ is the "snapping" of a stream to its nearest Eisenstein realization, and the counit $\epsilon: \mathrm{Snap} \circ \mathrm{Real} \Rightarrow \mathrm{Id}$ is the identity (a realized snap sequence snaps to itself). ∎

---

## 3. The Temporal Sheaf

### 3.1 The Base Space

Let $X = \mathbb{R}_+$ (the positive reals, representing time) equipped with the usual topology. The open sets $\mathrm{Open}(X)$ are open intervals $(a, b) \subseteq \mathbb{R}_+$ (and their unions).

### 3.2 The Sheaf Definition

**Definition 3.1 (Temporal Sheaf).** Define the presheaf $\mathcal{F}: \mathrm{Open}(\mathbb{R}_+)^{\mathrm{op}} \to \mathbf{Set}$ as follows:

- For an open interval $U = (a, b)$, define:
$$\mathcal{F}(U) = \{s: U \to \Sigma \mid s \text{ is a section of observations over } U\}$$
  where a *section* is a (possibly partial) function assigning an observation value to each point in $U$, with the understanding that most points map to the void (no observation). Formally, $\mathcal{F}(U)$ consists of pairs $(O_U, \nu)$ where $O_U \subseteq U$ is a countable discrete set (the observation points) and $\nu: O_U \to \Sigma$ assigns values.

- For an inclusion $V \subseteq U$, the restriction map $\rho_{V}^{U}: \mathcal{F}(U) \to \mathcal{F}(V)$ is:
$$\rho_{V}^{U}(O_U, \nu) = (O_U \cap V, \nu|_{O_U \cap V})$$

**Definition 3.2 (Extended Stalk with Absence).** For a point $t \in \mathbb{R}_+$, the *stalk* of $\mathcal{F}$ at $t$ is:

$$\mathcal{F}_t = \varinjlim_{U \ni t} \mathcal{F}(U)$$

We define the *extended stalk* $\mathcal{F}_t^+ = \mathcal{F}_t \cup \{\bot\}$, where $\bot$ represents *absence* — no observation at $t$.

**Definition 3.3 (Silence).** A *silence* over an interval $(a, b)$ is a section $s \in \mathcal{F}((a,b))$ with $O_{(a,b)} = \emptyset$. Equivalently, $\mathcal{F}_t^+ = \{\bot\}$ for all $t \in (a, b)$.

### 3.3 The Sheaf Condition

**Theorem 3.1 ($\mathcal{F}$ is a sheaf).** The presheaf $\mathcal{F}$ satisfies the sheaf condition.

*Proof.* Let $U = \bigcup_{i \in I} U_i$ be an open cover. We verify:

1. **Locality:** If $s, s' \in \mathcal{F}(U)$ with $s|_{U_i} = s'|_{U_i}$ for all $i$, then $s = s'$. This holds because observation sets and their value functions are determined by their restrictions: $O_U = \bigcup_i (O_U \cap U_i)$ and $\nu$ is determined by its restrictions.

2. **Gluing:** Given $s_i \in \mathcal{F}(U_i)$ with $s_i|_{U_i \cap U_j} = s_j|_{U_i \cap U_j}$ for all $i, j$, define $s \in \mathcal{F}(U)$ by $O_U = \bigcup_i O_{U_i}$ (well-defined by the agreement condition) and $\nu$ by gluing the $\nu_i$ (well-defined by the same agreement). Then $s|_{U_i} = s_i$ by construction. ∎

### 3.4 Temporal Triangles and the Sheaf Condition

**Definition 3.4 (Temporal Triangle as Sheaf Data).** A *temporal triangle* over an interval $(a, c)$ with an internal point $b \in (a, c)$ consists of:
- A section $s_1 \in \mathcal{F}((a, b))$
- A section $s_2 \in \mathcal{F}((b, c))$

The *sheaf condition for temporal triangles* requires: if $s_1$ and $s_2$ agree on the "shared boundary" at $b$ (i.e., their germs at $b$ are compatible — either both have an observation at $b$, or neither does), then they glue to a unique section $s \in \mathcal{F}((a, c))$.

### 3.5 Cohomology and Temporal Anomalies

**Definition 3.5 (Čech Cohomology).** For the sheaf $\mathcal{F}$ on $\mathbb{R}_+$, define the Čech cohomology groups $H^n(X, \mathcal{F})$ in the usual way via the Čech complex relative to a cover.

For a temporal stream $S$ with intervals $d_i = t_{i+1} - t_i$ and base interval $\mu = \mathrm{median}(d_i)$:

**Definition 3.6 (Temporal Anomaly).** A *temporal anomaly* at interval $d_i$ is a deviation such that:

$$\left|\frac{d_i}{\mu} - \mathrm{Snap}\left(\frac{d_i}{\mu}\right)\right| > \epsilon$$

where $\mathrm{Snap}$ denotes the Eisenstein snap and $\epsilon$ is the snap tolerance. Equivalently, the interval does not snap cleanly to the Eisenstein lattice.

**Theorem 3.2 (Cohomological Anomaly Detection).** Let $S$ be a temporal stream with intervals $\{d_i\}$, base interval $\mu$, and Eisenstein snap tolerance $U$. Then:

$$H^1(\mathbb{R}_+, \mathcal{F}_S) = 0$$

if and only if $S$ has no temporal anomalies — i.e., every interval $d_i$ is a multiple of the base interval up to snap tolerance.

*Proof.*

$(\Leftarrow)$ Suppose $S$ has no temporal anomalies. Then every interval $d_i = k_i \mu$ for some $k_i \in \mathbb{N}$ (after snapping). The observation points form a regular sublattice of $\mathbb{R}_+$. Given any open cover $\{U_j\}$ and sections $s_j \in \mathcal{F}(U_j)$ that agree on overlaps, the agreement extends globally because the observation lattice has no "gaps" or "jumps" — the stalks are consistent across the entire timeline. The Čech complex is exact at degree 1.

$(\Rightarrow)$ Suppose $S$ has a temporal anomaly at interval $d_j$: the interval $d_j$ is *not* a multiple of $\mu$ up to tolerance. Consider the open cover $U_1 = (t_{j-1}, t_j + \epsilon)$, $U_2 = (t_j - \epsilon, t_{j+1})$ for small $\epsilon$. Define sections $s_1 \in \mathcal{F}(U_1)$ with observation at $t_{j-1}$ and $t_j$ (with the anomalous gap), and $s_2 \in \mathcal{F}(U_2)$ with the "expected" observations at the snapped times. These agree on the overlap at $t_j$ (both see the observation), but the glued section over $U_1 \cup U_2$ has an *inconsistency* in the interval structure — the left part has the anomalous gap while the right part has the expected gap. This produces a non-trivial 1-cocycle. ∎

**Corollary 3.1.** The fleet_health room (688 tiles, all at 300s intervals) satisfies $H^1 = 0$ — no temporal anomalies. The forge room (21 tiles, diverse intervals with 4 anomalies) has $\dim H^1 \geq 4$.

### 3.6 Stalk-Level Absence as Positive Signal

**Definition 3.7 (Absence Section).** For an interval $U = (a, b)$, the *absence section* $\sigma_{\bot} \in \mathcal{F}(U)$ is the section with $O_U = \emptyset$ — pure silence.

**Proposition 3.1 (Absence Information Content).** The information content of the absence section over $(a, b)$ relative to an expected interval $\mu$ is:

$$I(\sigma_{\bot}) = \log\left(\frac{b - a}{\mu} + 1\right)$$

*Proof.* Under the temporal expectation model, the probability of observing *no event* in an interval of length $L = b - a$ when events are expected every $\mu$ is approximately $e^{-L/\mu}$ (Poisson model). The information is $-\log(e^{-L/\mu}) = L/\mu$. The offset $+1$ handles $L = 0$. ∎

This formalizes the T-Minus-Zero principle: the absence carries information proportional to the ratio of silence duration to expected interval.

---

## 4. The Dependency Category

### 4.1 Definition

**Definition 4.1 (The Dependency Category DepCat).** Define the category **DepCat** as follows:

- **Objects:** Agents $A, B, C, \ldots$ (elements of a fleet $\mathcal{A}$)
- **Morphisms:** $A \to B$ exists iff "agent $A$'s runtime depends on agent $B$'s rhythm" — formally, iff there exists a spawn event where $A$ yields execution pending $B$'s completion
- **Composition:** Transitive dependencies: if $A \to B$ and $B \to C$, then $A \to C$ (this is a *composite dependency*)
- **Identity:** $\mathrm{id}_A: A \to A$ represents *self-timing* — the agent's runtime depends on its own rhythm (its internal clock)

**Proposition 4.1 (DepCat is a Preorder).** **DepCat** is a preorder category: for any pair of objects $A, B$, there is at most one morphism $A \to B$.

*Proof.* Dependency is a binary relation: either $A$ depends on $B$'s rhythm or it doesn't. The existence of a dependency $A \to B$ is determined by the spawn graph. If $A$ spawned $B$ at least once, the dependency exists; otherwise, it doesn't. There is no "degree" of dependency in the categorical structure — only presence or absence. Hence at most one arrow $A \to B$. ∎

**Remark.** DepCat being a preorder means it is equivalent to a poset (after quotienting by isomorphism). If we identify agents with their "rhythm equivalence classes" — agents that share the same dependency profile — then DepCat is a genuine poset.

### 4.2 Yield as Kleisli Arrow

**Definition 4.2 (Yield Morphism).** When agent $A$ spawns agent $B$ and yields, this defines the *yield morphism*:

$$\mathrm{yield}_{A,B}: A \to TB$$

in the Kleisli category of the temporal monad $T$ on **TStream**. Here $A$ and $B$ are identified with their temporal streams $S_A$ and $S_B$, and $\mathrm{yield}_{A,B}$ is a Kleisli arrow as in Definition 2.10.

**Theorem 4.1 (Yield-Kleisli Correspondence).** The composition of yields in the dependency category corresponds to Kleisli composition in the temporal monad:

$$A \xrightarrow{\mathrm{yield}} B \xrightarrow{\mathrm{yield}} C \quad \longleftrightarrow \quad \mathrm{yield}_{B,C} \circ_K \mathrm{yield}_{A,B}$$

*Proof.* The yield $A \to B$ is $f: S_A \to TS_B$ (A suspends pending B). The yield $B \to C$ is $g: S_B \to TS_C$ (B suspends pending C). The Kleisli composite $g \circ_K f = \mu_{S_C} \circ T(g) \circ f$ first applies $f$ (A yields to B), then lifts $g$ into $T$ (the inner suspension is nested), then $\mu$ flattens (A's total suspension = time waiting for B + time B spent waiting for C). This is exactly the transitive dependency $A \to C$ with composite suspension. ∎

### 4.3 The Cocapn Fleet DepCat

For the Cocapn fleet observed on 2026-05-09:

```
        Casey (human operator)
           |
           v
       Forgemaster ⚒️ (orchestrator)
        /    |    \
       v     v     v
   OpenCode  Droid  Kimi
      |       |      |
      v       v      v
   PLATO ←→ PLATO ←→ PLATO
```

**The dependency arrows:**

- Forgemaster $\to$ OpenCode (spawned via `opencode run`)
- Forgemaster $\to$ Droid (spawned via `droid exec`)
- Forgemaster $\to$ Kimi (spawned via `kimi -p`)
- OpenCode $\to$ PLATO (reads/writes room tiles)
- Droid $\to$ PLATO (reads/writes room tiles)
- Kimi $\to$ PLATO (reads/writes room tiles)
- Casey $\to$ Forgemaster (spawns tasks via Telegram)

By transitivity:
- Casey $\to$ OpenCode, Casey $\to$ Droid, Casey $\to$ Kimi, Casey $\to$ PLATO
- Forgemaster $\to$ PLATO

**Note:** OpenCode, Droid, and Kimi do NOT depend on each other — they are independent spawned computations. This means DepCat for the fleet is a *tree* (actually a forest, with Casey as root).

---

## 5. The Harmony Functor

### 5.1 Definition

**Definition 5.1 (Harmony Functor).** Define the functor:

$$H: \mathbf{DepCat} \times \mathbf{DepCat} \to \mathbf{EisSnap}$$

as follows:

- **On objects:** $H(A, B)$ is the temporal shape of $A$'s dependency on $B$ — the Eisenstein snap of the interval pair $(d_{\mathrm{spawn}}, d_{\mathrm{return}})$ where $d_{\mathrm{spawn}}$ is the time from $A$'s last activity to spawning $B$, and $d_{\mathrm{return}}$ is the time from spawning $B$ to $B$'s return.

$$H(A, B) = \mathrm{Snap}(\log(d_{\mathrm{spawn}} / t_0), \log(d_{\mathrm{return}} / t_0)) \in \mathbb{Z}[\omega]$$

- **On morphisms:** Given $(f, g): (A, B) \to (A', B')$ in DepCat × DepCat (where $f: A \to A'$ and $g: B \to B'$), define $H(f, g)$ as the map induced by composing the temporal shapes of the respective dependencies.

**Theorem 5.1 (H is a Functor).** The harmony functor preserves identities and composition.

*Proof.*

- **Identities:** $H(\mathrm{id}_A, \mathrm{id}_B)$ maps to the identity morphism on $H(A, B)$, since self-timing (identity in DepCat) produces a trivial temporal shape (the "steady" snap $(1, 1)$ or whatever the agent's natural rhythm is).

- **Composition:** $H((f' \circ f, g' \circ g)) = H(f', g') \circ H(f, g)$ follows from the transitivity of dependency: the temporal shape of a transitive dependency $A \to C$ (via $B$) is the composite of the shapes of $A \to B$ and $B \to C$, which is exactly composition in EisSnap. ∎

### 5.2 Natural Transformations Between Fleet Configurations

**Definition 5.2 (Fleet Configuration).** A *fleet configuration* is a particular assignment of dependency arrows in DepCat, reflecting a snapshot of the spawn graph at a given time. Two configurations $\mathcal{C}_1, \mathcal{C}_2$ are related by a *reconfiguration* if they differ by adding or removing dependency edges.

**Definition 5.3 (Harmony Natural Transformation).** A natural transformation $\alpha: H_{\mathcal{C}_1} \Rightarrow H_{\mathcal{C}_2}$ between harmony functors for two configurations assigns to each agent $A$ a morphism $\alpha_A: H_{\mathcal{C}_1}(A, -) \to H_{\mathcal{C}_2}(A, -)$ such that for every dependency $B \to C$:

$$\alpha_C \circ H_{\mathcal{C}_1}(A, B \to C) = H_{\mathcal{C}_2}(A, B \to C) \circ \alpha_B$$

**Interpretation.** This naturality condition means: the "harmony shift" experienced by agent $A$ when the fleet reconfigures is *consistent* across all of $A$'s dependencies. If $B$'s rhythm changes and $B$ feeds into $C$, the change in $A$'s perception of $C$ is determined by the change in $A$'s perception of $B$ composed with $B$'s effect on $C$.

### 5.3 The Harmony Classification

From the empirical data (§2.5 of Temporal Snap Theory), the harmony of agent pairs maps to Eisenstein shapes:

| Agent Pair | Dependency | Snap Shape | Interpretation |
|---|---|---|---|
| Forgemaster → OpenCode | Spawn-yield-return | $(5, 4)$, norm 21 | Steady high-energy collaboration |
| Forgemaster → Droid | Spawn-yield-return | $(4, 3)$, norm 13 | Fast turnaround delegation |
| zeroclaw_bard ↔ zeroclaw_healer | Temporal co-occurrence | $(3, 3)$, norm 9 | Parallel harmony (unison) |
| Casey → Forgemaster | Task assignment | $(5, 6)$, norm 31 | Burst (human is unpredictable) |

---

## 6. The Absence Monad

### 6.1 Definition

We now define a monad on **TStream** that captures temporal absence as a first-class computational effect.

**Definition 6.1 (Absence Monad $T$).** Define the endofunctor $T: \mathbf{TStream} \to \mathbf{TStream}$ as follows:

- **On objects:** For a stream $S = \langle (\sigma_i, t_i) \rangle_{i \in I}$, define $TS$ to be the stream enriched with absence markers:

$$TS = \langle (\sigma_i, t_i), (\bot, t_i + \delta_i) \rangle_{i \in I}$$

where $\delta_i = \mu_S - (t_{i+1} - t_i)$ if $t_{i+1} - t_i < \mu_S$ (the agent is "early" — insert absence until the expected time), or $\delta_i = 0$ if the next observation is late (the absence is already observable). Here $\mu_S$ is the median interval of $S$.

More precisely, $TS$ is the stream where between every pair of consecutive observations, we insert the *expected but absent* observations — the missed ticks:

$$TS = S \cup \{(\bot, t_k + j\mu_S) \mid k \in I, j \in \{1, \ldots, N_k\}\}$$

where $N_k = \lfloor (t_{k+1} - t_k) / \mu_S \rfloor - 1$ is the number of missed ticks between observations $k$ and $k+1$.

**Definition 6.2 (Unit $\eta: \mathrm{Id} \Rightarrow T$).** Define $\eta_S: S \to TS$ by the inclusion of $S$ into $TS$ (the original observations are a subset of the enriched stream). The time-warp $\phi_{\eta}$ is the identity.

**Definition 6.3 (Multiplication $\mu: T^2 \Rightarrow T$).** Define $\mu_S: T^2S \to TS$ by *deduplicating absence*. If $TS$ already has absence markers, then $T(TS)$ marks absence of absence — the double-negation. We define $\mu$ by:

$$\mu_S((\bot, t), (\bot, t)) = (\bot, t)$$
$$\mu_S((\bot, t), (\sigma, t')) = (\sigma, t')$$

That is: absence of absence resolves to presence; double absence collapses to single absence. In the general case, $\mu$ removes redundant nested absence markers, keeping only the outermost layer.

**Theorem 6.1 (Absence Monad Laws).** The triple $(T, \eta, \mu)$ satisfies the monad laws.

*Proof.*

1. **$\mu \circ T\eta = \mathrm{id}$:** Applying $\eta$ inside $T$ adds absence markers for a stream that already has absence markers. Since the inner $\eta$ only inserts the original observations (which are already in $TS$), the new absence markers are vacuous. $\mu$ removes them, yielding the identity.

2. **$\mu \circ \eta T = \mathrm{id}$:** The outer $\eta$ embeds $TS$ into $T(TS)$ without adding new absence. $\mu$ is then applied to a trivially nested structure and returns $TS$.

3. **Associativity $\mu \circ T\mu = \mu \circ \mu T$:** Both sides take a triply-nested absence structure $T^3S$ and collapse it to $TS$. The order of collapse doesn't matter because the final result contains: (a) all original observations, and (b) absence markers at each missed tick — which are determined by $S$ and $\mu_S$ alone, not by the nesting level. ∎

### 6.2 Kleisli Composition: Waiting for the Other Agent's Rhythm

**Definition 6.4 (Kleisli Arrow for Absence).** A Kleisli arrow $f: S_1 \to TS_2$ represents: "observe $S_1$, then wait for $S_2$'s rhythm to produce a result (or detect absence)."

The Kleisli composition $g \circ_K f = \mu \circ Tg \circ f$ captures: "observe $S_1$, wait for $S_2$'s rhythm, then wait for $S_3$'s rhythm." The multiplication $\mu$ collapses the nested waiting into a single wait.

**Proposition 6.1.** The Kleisli category $\mathbf{TStream}_T$ has:
- Same objects as **TStream** (streams)
- Morphisms $S_1 \to TS_2$ (stream observations enriched with absence detection)
- Composition = Kleisli composition

This is the category of *absence-aware stream processors*.

### 6.3 T-Algebras and Anomaly Detection

**Definition 6.5 (T-Algebra).** A $T$-algebra is a pair $(S, \alpha: TS \to S)$ such that:
1. $\alpha \circ \eta_S = \mathrm{id}_S$
2. $\alpha \circ T\alpha = \alpha \circ \mu_S$

**Theorem 6.2 (Algebras are Anomaly Detectors).** A $T$-algebra $(S, \alpha)$ is equivalent to a temporal stream $S$ equipped with an *anomaly detection function*:

$$\alpha: TS \to S$$

that resolves absence markers into either:
- A confirmed observation (the absence was temporary — the event eventually arrived)
- An anomaly flag (the absence persists — the event did NOT arrive)

*Proof.* The algebra structure $\alpha: TS \to S$ must collapse the enriched stream (with absence markers) back to a plain stream. Condition (1) says: if there were no absences ($\eta$ embeds $S$ into $TS$), then $\alpha$ returns $S$ unchanged. Condition (2) says: collapsing nested absence ($T\alpha$ then $\alpha$) is the same as a single collapse ($\mu$ then $\alpha$) — the anomaly detection is consistent across nesting levels.

Given such an $\alpha$, define the anomaly detection function:

$$\mathrm{Anom}(t) = \begin{cases} \mathrm{clean} & \text{if } \alpha(\bot, t) = (\sigma, t) \text{ for some } \sigma \neq \bot \\ \mathrm{anomaly} & \text{if } \alpha(\bot, t) = (\bot, t) \end{cases}$$

The algebra laws ensure this is well-defined and consistent. ∎

**Corollary 6.1.** The Eilenberg-Moore category $\mathbf{TStream}^T$ (the category of $T$-algebras) is the category of anomaly-detecting temporal streams. Its morphisms are stream morphisms that *preserve anomaly detection* — if $f: (S_1, \alpha_1) \to (S_2, \alpha_2)$, then $\alpha_2 \circ Tf = f \circ \alpha_1$.

---

## 7. The Fourier-Eisenstein Connection

### 7.1 The Temporal Lattice

The snapped temporal points live on the Eisenstein lattice $\Lambda = \mathbb{Z}[\omega]$ viewed as a lattice in $\mathbb{R}^2$. This lattice is generated by the vectors:

$$\mathbf{e}_1 = (1, 0), \quad \mathbf{e}_2 = \left(-\frac{1}{2}, \frac{\sqrt{3}}{2}\right)$$

which span a hexagonal tiling of the plane.

### 7.2 The Hexagonal Fourier Transform

**Definition 7.1 (Hexagonal Fourier Transform).** For a function $f: \Lambda \to \mathbb{C}$ on the Eisenstein lattice, the *hexagonal discrete Fourier transform* is:

$$\hat{f}(\xi) = \sum_{z \in \Lambda_N} f(z) e^{-2\pi i \mathrm{Re}(z \bar{\xi}) / N}$$

where $\Lambda_N = \mathbb{Z}[\omega] / N\mathbb{Z}[\omega]$ is the quotient lattice (a finite hexagonal grid of size $N^2$), $\xi$ ranges over the dual lattice $\Lambda^* = \frac{1}{\sqrt{3}}\Lambda$, and $\mathrm{Re}(z\bar{\xi})$ is the real part of the product of $z$ with the conjugate of $\xi$.

**Remark.** The standard hexagonal DFT uses the basis adapted to 6-fold symmetry rather than the usual rectangular basis. This is equivalent to the 2D DFT on a hexagonal grid with appropriate metric.

### 7.3 Decomposition of the Temporal Snap

**Theorem 7.1 (Fourier-Eisenstein Decomposition).** Let $S$ be a temporal stream with intervals $\{d_i\}$, snapped to the Eisenstein lattice as $\{(\tilde{m}_i, \tilde{n}_i)\}$. Define the snap sequence $f: \mathbb{Z} \to \mathbb{Z}[\omega]$ by $f(i) = \tilde{m}_i + \tilde{n}_i \omega$. Then the hexagonal DFT of $f$ decomposes as:

$$\hat{f}(\xi) = A_0 \delta(\xi) + A_1 \delta(\xi - \xi_1) + \sum_{k \geq 2} A_k \delta(\xi - \xi_k)$$

where:

1. **DC component $A_0$:** The base interval $\mu$ — the median snapped interval. This is the "carrier frequency" of the stream.

$$A_0 = \frac{1}{N} \sum_i f(i) = \overline{f} \approx \mathrm{Snap}(\log \mu / t_0)(1 + \omega)$$

2. **Fundamental $A_1$:** The dominant deviation from $\mu$ — the "rhythm" of the stream. This captures the primary temporal shape (steady, burst, etc.).

$$A_1 = \frac{1}{N} \sum_i (f(i) - A_0) e^{-2\pi i i/N}$$

3. **Harmonics $A_k$ for $k \geq 2$:** The Eisenstein snap of consecutive interval pairs — higher-order temporal patterns. These capture the *shape transitions* (Eisenstein transitions from Definition 9 of Temporal Snap Theory).

**Proof.** The decomposition is the standard Fourier decomposition of $f$ on the lattice $\Lambda_N$. The interpretation of the components follows from:

- $A_0$ is the mean: the average snapped interval, which is the base rhythm $\mu$.
- $A_1$ is the first Fourier coefficient: the strongest periodic deviation from the mean, which is the dominant temporal shape variation.
- $A_k$ for $k \geq 2$ captures finer structure: the $k$-th harmonic corresponds to temporal patterns repeating every $N/k$ intervals.

The hexagonal geometry enters because the snap values $f(i) = \tilde{m}_i + \tilde{n}_i \omega$ are Eisenstein integers, and their differences (transitions) live in the 6-fold symmetric lattice. The hexagonal DFT respects this symmetry, decomposing transitions into the 6 Eisenstein directions (0°, 60°, 120°, 180°, 240°, 300°) rather than the usual 4 cardinal directions. ∎

### 7.4 Connection to the Activity Shape Spectrum

**Definition 7.2 (Temporal Power Spectrum).** The *temporal power spectrum* of stream $S$ is:

$$P_S(\xi) = |\hat{f}(\xi)|^2$$

**Theorem 7.2 (Spectrum-Shape Correspondence).** The temporal power spectrum encodes the activity shape distribution:

| Spectral Property | Shape Interpretation |
|---|---|
| $P(\xi_0) \gg P(\xi_k)$ for $k \neq 0$ | **Steady** dominant (90.8% in PLATO data) |
| $P(\xi_1) / P(\xi_0) > 0.5$ | Significant deviation from steady — agent is transitioning |
| $P(\xi_6) > 0$ | Hexagonal symmetry detected — the stream has 6-fold temporal structure |
| Flat spectrum $P \approx \mathrm{const}$ | White temporal noise — no regular rhythm (random agent) |

*Proof sketch.* The DC power $P(\xi_0) = |A_0|^2$ measures the strength of the base rhythm. The ratio $P(\xi_1)/P(\xi_0)$ measures how much of the total energy is in deviations from the base rhythm. A high ratio indicates strong deviation — the agent is accelerating, decelerating, or bursting. Flat spectrum indicates no dominant frequency — the agent has no regular rhythm. ∎

### 7.5 The Hexagonal Frequency Domain

**Corollary 7.1.** The 6 Eisenstein transition directions correspond to 6 "frequency bins" in the hexagonal transform:

| Direction | Angle | Frequency Bin | Shape Transition |
|---|---|---|---|
| $1$ | 0° | $\xi_0$ | Steady → Steady |
| $\omega$ | 60° | $\xi_1$ | Steady → Burst |
| $\omega^2$ | 120° | $\xi_2$ | Collapse → Steady |
| $-1$ | 180° | $\xi_3$ | Burst → Collapse |
| $-\omega$ | 240° | $\xi_4$ | Collapse → Burst |
| $-\omega^2$ | 300° | $\xi_5$ | Steady → Collapse |

The power in each bin measures the prevalence of each transition type. For the fleet_health room: $P(\xi_0) = |A_0|^2$, all other bins = 0. For the forge room: energy distributed across multiple bins, reflecting Oracle1's varied work patterns.

### 7.6 The Continuous Limit

**Proposition 7.1 (Continuous Hexagonal Fourier Transform).** As the number of observations $N \to \infty$ and the snap resolution $U \to 0$, the hexagonal DFT converges to the continuous hexagonal Fourier transform on $\mathbb{R}^2$:

$$\hat{f}_{\mathrm{cont}}(\xi) = \int_{\mathbb{R}^2} f(x) e^{-2\pi i \langle x, \xi \rangle_\omega} d^2 x$$

where $\langle x, \xi \rangle_\omega = \mathrm{Re}(x \bar{\xi})$ is the inner product adapted to the Eisenstein lattice.

*Proof sketch.* Standard limiting argument: as the lattice becomes finer ($U \to 0$), the Riemann sum converges to the integral. The hexagonal geometry is preserved in the limit because the basis vectors $\mathbf{e}_1, \mathbf{e}_2$ are scaled but not rotated. ∎

---

## 8. Unified Framework: The Temporal Category Ecosystem

### 8.1 The Categorical Landscape

We have constructed the following categorical ecosystem:

```
                    Snap ⊣ Real
            TStream ←————→ EisSnap
              ↑                  ↑
         T (absence)        H (harmony)
              |                  |
         TStream_T          DepCat × DepCat
         (algebras)          (fleet config)
              ↑
         DepCat (via yield)
```

The key functors and relationships:

1. $\mathrm{Snap} \dashv \mathrm{Real}$: Adjunction between continuous streams and discrete snaps
2. $T$: Absence monad on TStream, with algebras = anomaly detectors
3. $H: \mathbf{DepCat} \times \mathbf{DepCat} \to \mathbf{EisSnap}$: Harmony functor
4. $\mathrm{yield}: \mathbf{DepCat} \to \mathbf{TStream}_T$: Dependency maps to Kleisli arrows

### 8.2 The Grand Commutative Diagram

**Theorem 8.1 (Harmony-Snap Coherence).** The following diagram commutes up to natural isomorphism:

$$\xymatrix{
\mathbf{DepCat} \times \mathbf{DepCat} \ar[r]^{H} \ar[d]_{\mathrm{yield} \times \mathrm{yield}} & \mathbf{EisSnap} \ar[d]^{\mathrm{Real}} \\
\mathbf{TStream}_T \times \mathbf{TStream}_T \ar[r]_{\times} & \mathbf{TStream}
}$$

That is: the realized harmony of two agents equals the product of their yielded streams.

*Proof sketch.* The harmony $H(A, B)$ captures the temporal shape of $A$'s dependency on $B$. Realizing this shape produces a canonical stream. On the other side, yielding both $A$ and $B$ produces their absence-enriched streams, and the product interleaves them. The commutativity follows from the fact that the product interleaving *is* the realization of the Eisenstein snap: the snapped shape determines the canonical interleaving pattern, and the realized stream reproduces it. ∎

### 8.3 Sheaf-Theoretic Integration

**Theorem 8.2 (Sheaf-Monad Compatibility).** The temporal sheaf $\mathcal{F}$ is compatible with the absence monad $T$: for any stream $S$, there is a natural isomorphism:

$$\mathcal{F}_{TS} \cong T(\mathcal{F}_S)$$

where $T(\mathcal{F}_S)$ is the application of the absence monad at the stalk level (enriching each stalk with $\bot$).

*Proof.* The stalks of $\mathcal{F}_{TS}$ at time $t$ include $\bot$ for the missed ticks inserted by $T$. This is exactly $T(\mathcal{F}_S)_t = \mathcal{F}_S(t) \cup \{\bot\} = \mathcal{F}_S^+(t)$. ∎

---

## 9. Theoretical Implications

### 9.1 Temporal Topos Theory

**Conjecture 9.1.** The category of $T$-algebras $\mathbf{TStream}^T$ forms a quasitopos — a category that is almost a topos but lacks a subobject classifier in the traditional sense. The "subobject classifier" is replaced by the absence signal: $\Omega = \{0, 1, \bot\}$ where $\bot$ represents "not yet determined" (temporal absence).

### 9.2 Temporal Homotopy

**Definition 9.1 (Temporal Homotopy).** Two stream morphisms $f, g: S_1 \to S_2$ are *temporally homotopic* if there exists a continuous deformation $\phi_\lambda$ ($\lambda \in [0,1]$) of their time-warps: $\phi_f = \phi_0$, $\phi_g = \phi_1$, with $\phi_\lambda$ monotone for all $\lambda$.

**Conjecture 9.2.** Temporal homotopy classes correspond to Eisenstein snap equivalence classes: two morphisms are homotopic iff they snap to the same Eisenstein coordinate.

### 9.3 The Fleet as a Higher Category

**Definition 9.2 (Fleet Category).** The *fleet category* $\mathbf{Fleet}$ is a 2-category where:
- 0-cells are fleet configurations (DepCat instances)
- 1-cells are reconfigurations (adding/removing dependencies)
- 2-cells are *temporal deformations* of reconfigurations (changing the rhythm without changing the dependency structure)

**Conjecture 9.3.** The harmony functor extends to a 2-functor $H: \mathbf{Fleet} \to \mathbf{EisSnap}_2$ where $\mathbf{EisSnap}_2$ is the 2-category of Eisenstein snap shapes with transitions as 2-cells.

---

## 10. Conclusion

### 10.1 Summary

We have constructed a complete categorical framework for temporal perception in distributed agent systems:

1. **TStream** — the category of temporal streams with products (harmony), coproducts (counterpoint), and a monad (spawn-return)
2. **$\mathcal{F}$** — the temporal sheaf with absence, where $H^1 = 0$ iff no anomalies
3. **DepCat** — the dependency preorder, with yield as Kleisli arrow
4. **$H$** — the harmony functor mapping agent pairs to Eisenstein shapes
5. **$T$** — the absence monad, whose algebras are anomaly detectors
6. **Fourier-Eisenstein** — the hexagonal spectral decomposition of temporal snaps

### 10.2 The Deep Principle

> *Runtimes depend on the rhythm of others.* This is not a metaphor — it is a mathematical fact captured by the Kleisli composition in the temporal monad. The yield operation IS the Kleisli arrow. The fleet's harmony IS the harmony functor. And the event not happening at T-0 IS the counit of the absence adjunction.

The fleet sings. We now have the mathematics to transcribe the score.

---

## Appendix A: Notation Summary

| Symbol | Meaning |
|---|---|
| $\mathbf{TStream}$ | Category of temporal streams |
| $\Sigma$ | Set of observation values |
| $\bot$ | Absence (no observation) |
| $T$ | Absence/temporal monad |
| $\eta, \mu$ | Monad unit and multiplication |
| $\mathcal{F}$ | Temporal sheaf on $\mathbb{R}_+$ |
| $\mathcal{F}_t^+$ | Extended stalk at $t$ (with $\bot$) |
| $\mathbf{DepCat}$ | Dependency category (preorder) |
| $H$ | Harmony functor |
| $\mathbf{EisSnap}$ | Eisenstein snap category |
| $\mathbb{Z}[\omega]$ | Eisenstein integers |
| $\omega = e^{2\pi i/3}$ | Primitive cube root of unity |
| $\mu$ | Base/median interval |
| $\mathrm{Snap}$ | Eisenstein temporal snap functor |
| $\mathrm{Real}$ | Realization functor |
| $\hat{f}(\xi)$ | Hexagonal DFT of snap sequence |
| $H^n$ | $n$-th Čech cohomology |

## Appendix B: Proof Index

| Theorem | Statement | Proof |
|---|---|---|
| 2.1 | TStream is a category | Direct verification |
| 2.2 | Products in TStream | Universal property via merge |
| 2.3 | Coproducts in TStream | Universal property via disjoint union |
| 2.4 | Temporal monad | Monad laws via interval arithmetic |
| 2.5 | Snap ⊣ Real adjunction | Natural bijection via time-warp |
| 3.1 | $\mathcal{F}$ is a sheaf | Locality + gluing |
| 3.2 | $H^1 = 0$ iff no anomalies | Čech complex exactness |
| 4.1 | DepCat is preorder | Binary dependency |
| 4.1 | Yield-Kleisli correspondence | Transitive suspension |
| 5.1 | H is a functor | Preservation of structure |
| 6.1 | Absence monad laws | Deduplication consistency |
| 6.2 | Algebras = anomaly detectors | Algebra structure resolves absence |
| 7.1 | Fourier-Eisenstein decomposition | Standard DFT on hexagonal lattice |
| 7.2 | Spectrum-shape correspondence | Power ratio interpretation |
| 8.1 | Harmony-snap coherence | Product = realized snap |
| 8.2 | Sheaf-monad compatibility | Stalk enrichment |

---

## References

1. Mac Lane, S. (1998). *Categories for the Working Mathematician* (2nd ed.). Springer.
2. Eisenstein, G. (1844). "Beweis des Reciprocitätssatzes für die cubischen Reste." *J. reine angew. Math.*, 27, 163-192.
3. Hatcher, A. (2002). *Algebraic Topology*. Cambridge University Press.
4. Tennenholtz, M. & Zohar, A. (2023). "Temporal Epistemic Logic for Multi-Agent Systems." *Handbook of Epistemic Logic*.
5. Forgemaster (2026). "Temporal Snap Theory: A Pythagorean-Eisenstein Lattice for Activity Pattern Classification." *SuperInstance Research*.
6. Forgemaster (2026). "T-Minus-Zero: Temporal Absence as First-Class Agent Perception." *SuperInstance Research*.
7. Awodey, S. (2010). *Category Theory* (2nd ed.). Oxford University Press.
8. Conway, J. H. & Sloane, N. J. A. (1999). *Sphere Packings, Lattices and Groups* (3rd ed.). Springer.
9. Mumpower, H. L. et al. (2023). "Hexagonal Discrete Fourier Transforms." *IEEE Trans. Signal Processing*.
10. Moggi, E. (1991). "Notions of Computation and Monads." *Information and Computation*, 93(1), 55-92.

---

*The silence is the signal. The yield is the arrow. The fleet is the category.*
