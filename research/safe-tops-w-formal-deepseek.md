## Formal Definition of Safe-TOPS/W

Let \( \mathcal{S} \) be the set of all computational systems (e.g., processors, accelerators, or software-hardware stacks). For each system \( S \in \mathcal{S} \), we define:

- **Peak Constraint‑Check Throughput** \( T(S) \in \mathbb{R}_{\geq 0} \): the maximum number of primitive constraint checks (e.g., bounds checks, invariance assertions, safety monitors) that \( S \) can execute per second under nominal operating conditions.
- **Average Power** \( P(S) \in \mathbb{R}_{> 0} \): the steady‑state electrical power consumption in watts during the execution of these checks, measured under a representative workload.
- **Certification Status** \( \text{Cert}(S) \in \{\text{True}, \text{False}\} \): a Boolean valued function that is **True** if and only if there exists a machine‑checkable mathematical proof that for every admissible input, every constraint check executed by \( S \) returns the correct result (according to a formal specification of the constraint). Otherwise, \( \text{Cert}(S) = \text{False} \).

The **certified constraint‑check throughput** is then
\[
C_{\text{certified}}(S) \;=\; \begin{cases}
T(S) & \text{if } \text{Cert}(S) = \text{True},\\
0    & \text{if } \text{Cert}(S) = \text{False}.
\end{cases}
\]

Finally, **Safe‑TOPS/W** is defined as
\[
\text{Safe-TOPS/W}(S) \;=\; \frac{C_{\text{certified}}(S)}{P(S)},
\]
with the convention that \( 0 / P(S) = 0 \).

---

## Formal Proofs of Desired Properties

We prove four properties: monotonicity, zero‑default, soundness, and compositionality. Throughout, assume \( P(S) > 0 \) for all systems (a reasonable physical assumption).

### 1. Monotonicity

**Definition (Improvement).**  
System \( S' \) is an *improvement* of system \( S \) (denoted \( S' \succeq S \)) if  
\[
T(S') \ge T(S),\quad P(S') \le P(S),\quad \text{and}\quad \text{Cert}(S') = \text{Cert}(S).
\]  
That is, the throughput does not decrease, the power does not increase, and the certification status remains unchanged.

**Theorem (Monotonicity).**  
If \( S' \succeq S \), then \( \text{Safe-TOPS/W}(S') \ge \text{Safe-TOPS/W}(S) \).

*Proof.*  
Consider two cases:

- **Case 1:** \( \text{Cert}(S) = \text{False} \). Then \( \text{Cert}(S') = \text{False} \) by the definition of improvement. Hence \( C_{\text{certified}}(S) = C_{\text{certified}}(S') = 0 \), and both metrics are zero. Thus \( 0 \ge 0 \).

- **Case 2:** \( \text{Cert}(S) = \text{True} \). Then \( \text{Cert}(S') = \text{True} \), and \( C_{\text{certified}}(S) = T(S) \), \( C_{\text{certified}}(S') = T(S') \). Because \( T(S') \ge T(S) \) and \( P(S') \le P(S) \), we have
  \[
  \frac{T(S')}{P(S')} \ge \frac{T(S)}{P(S)} = \text{Safe-TOPS/W}(S).
  \]
  Hence \( \text{Safe-TOPS/W}(S') \ge \text{Safe-TOPS/W}(S) \).

Monotonicity holds under the natural notion of improvement that preserves certification. Note that a system that loses certification (e.g., through a design change that invalidates the proof) is not considered an improvement, as \( \text{Cert} \) would change. ∎

### 2. Zero‑Default

**Theorem (Zero‑Default).**  
If \( \text{Cert}(S) = \text{False} \), then \( \text{Safe-TOPS/W}(S) = 0 \).

*Proof.*  
Immediate from the definition: \( C_{\text{certified}}(S) = 0 \) implies the numerator is zero, and \( 0 / P(S) = 0 \). ∎

This property encodes a **hard safety gate**: a system that lacks a formal correctness proof contributes zero safe performance, regardless of its raw throughput.

### 3. Soundness

**Definition (Soundness).**  
A metric \( M(S) \) is *sound* with respect to a property \( \Pi \) if \( M(S) > 0 \) implies that \( S \) satisfies \( \Pi \), and conversely, if \( S \) satisfies \( \Pi \) then \( M(S) > 0 \) (assuming non‑zero power).

**Theorem (Soundness).**  
Safe‑TOPS/W is sound with respect to the property “\( S \) has a mathematical proof that all constraint checks are correct.”

*Proof.*  
Let \( \Pi(S) \) be the statement “\( \text{Cert}(S) = \text{True} \)”.

- **Forward direction:** Suppose \( \text{Safe-TOPS/W}(S) > 0 \). Then \( C_{\text{certified}}(S) > 0 \), which by definition forces \( \text{Cert}(S) = \text{True} \). Hence \( \Pi(S) \) holds.
- **Reverse direction:** Suppose \( \Pi(S) \) holds, i.e., \( \text{Cert}(S) = \text{True} \). Then \( C_{\text{certified}}(S) = T(S) \), and since \( T(S) > 0 \) for any operating system and \( P(S) > 0 \), we have \( \text{Safe-TOPS/W}(S) = T(S)/P(S) > 0 \).

Thus the metric is a faithful indicator of proven safety. ∎

Note that soundness does *not* assert that a system with a proof is “safe” in an absolute sense (the proof could be flawed or the specification incomplete). It only guarantees that the metric is non‑zero *exactly* when a formal correctness argument exists. This aligns with the rigorous interpretation of “certified.”

### 4. Compositionality

**Definition (Composition).**  
Let \( S_1, S_2, \dots, S_n \) be a collection of systems that are *compositionally independent*: they operate in parallel with no shared state, no interference, and each has its own power supply and throughput. The composite system \( S = \bigoplus_{i=1}^n S_i \) is formed by running them concurrently. Its power is the sum of the individual powers (assuming no overhead), and its throughput is the sum of the individual throughputs, because the constraint checks are independent.

**Assumption (Composable Proofs).**  
If each \( S_i \) has an individual proof \( \mathcal{P}_i \) of correctness, then there exists a proof \( \mathcal{P} = \mathcal{P}_1 \wedge \mathcal{P}_2 \wedge \cdots \wedge \mathcal{P}_n \) that the composite system \( S \) also performs all constraint checks correctly (since independence ensures no cross‑interference). Conversely, if the composite system has a proof, it does not necessarily imply that each component individually is certified.

**Theorem (Compositionality).**  
Under the assumptions of independence and composable proofs, the Safe‑TOPS/W of the composite system is a deterministic function of the components’ certified throughputs and powers:
\[
\text{Safe-TOPS/W}\!\left( \bigoplus_{i=1}^n S_i \right) \;=\; \frac{\sum_{i=1}^n C_{\text{certified}}(S_i)}{\sum_{i=1}^n P(S_i)}.
\]

*Proof.*  
Because the proofs compose, we have
\[
\text{Cert}\!\left( \bigoplus_{i=1}^n S_i \right) = \text{True} \quad \Longleftrightarrow \quad \forall i:\ \text{Cert}(S_i) = \text{True}.
\]
If any component is uncertified, the composite is uncertified and the metric is zero (the numerator is zero because each component’s \( C_{\text{certified}} \) is zero). If all are certified, then \( C_{\text{certified}}(S_i) = T(S_i) \) for each \( i \). By independence,
\[
C_{\text{certified}}\!\left( \bigoplus_{i=1}^n S_i \right) = \sum_{i=1}^n T(S_i) = \sum_{i=1}^n C_{\text{certified}}(S_i),
\]
and
\[
P\!\left( \bigoplus_{i=1}^n S_i \right) = \sum_{i=1}^n P(S_i).
\]
The claim follows by substitution. ∎

This result shows that Safe‑TOPS/W is *compositional* in the sense that the metric of the whole is obtained by dividing the sum of individual certified throughputs by the sum of individual powers. However, it is **not** additive: the metric of the whole is not equal to the sum (or any simple function) of the individual metrics alone—it depends on the absolute power and throughput values, not just their ratios.

---

## Why Safe‑TOPS/W Is Necessary and Controversial

### Necessity: The Blind Spot of TOPS/W

The conventional metric **TOPS/W** (trillions of operations per second per watt) measures raw computational efficiency without any regard for correctness. In safety‑critical domains—autonomous driving, medical diagnosis, industrial control, avionics—an incorrectly computed result can be catastrophic. A high TOPS/W figure may come from aggressive hardware optimisations (e.g., reduced‑precision arithmetic, speculative execution, relaxed memory ordering) that introduce silent data corruption or violate formal safety constraints.

Consider an accelerator that achieves 100 TOPS/W by using approximate multipliers that occasionally produce floating‑point errors. For a generic deep‑learning workload, such errors might be benign. But for an autonomous vehicle’s braking system, a single mis‑computed distance could lead to a collision. TOPS/W treats that risk as zero; Safe‑TOPS/W correctly assigns zero performance because no proof of correctness exists.

Moreover, the **zero‑default** property forces designers to invest in formal verification *before* the metric rewards them. This aligns industrial incentives with safety: to claim any safe performance, a system must first demonstrate a mathematical guarantee. In industries where formal methods are already mandated (e.g., DO‑178C in avionics), Safe‑TOPS/W provides a unified efficiency measure that respects existing certification standards.

### Controversy: Why Vendors Resist

**1. Binary penalty for missing proof.**  
A system that is immensely fast and empirically safe but lacks a mathematical proof receives a score of zero. Vendors argue that many real‑world systems are “safe enough” through extensive testing, fault‑tolerant design, or years of deployment. The metric dismisses this entire class of systems, potentially excluding them from procurement decisions.

**2. Cost and feasibility of formal verification.**  
Producing a machine‑checkable proof for a complex processor or large software stack is exceedingly expensive—often