# Monotonicity Proof: Constraint Satisfaction Density (CSD)

**Author:** Forgemaster ⚒️
**Date:** 2026-05-04
**Status:** Proven

---

## Definitions

Let $R$ be a room with a set of claims $C = \{c_1, c_2, \dots, c_n\}$ extracted from its tiles, where $|C| = n$.

A **conflict** is an unordered pair $(c_i, c_j)$ where $c_i$ **contradicts** $c_j$. Denote the set of all conflicts as $\mathcal{F}(R) \subseteq \binom{C}{2}$.

The total number of possible claim-pairs is:

$$T = \binom{|C|}{2} = \frac{|C|(|C|-1)}{2}$$

**Constraint Satisfaction Density** is defined as:

$$\text{CSD}(R) = 1 - \frac{|\mathcal{F}(R)|}{\binom{|C|}{2}}$$

For the degenerate case $|C| \leq 1$, we define $\binom{|C|}{2} = 0$ and $\text{CSD}(R) = 1$ (vacuously coherent).

---

## Theorem 1: Boundedness — $\text{CSD}(R) \in [0, 1]$

**Proof.**

Since $\mathcal{F}(R) \subseteq \binom{C}{2}$, we have $0 \leq |\mathcal{F}(R)| \leq \binom{|C|}{2}$.

Dividing through by $\binom{|C|}{2} > 0$ (for $|C| \geq 2$):

$$0 \leq \frac{|\mathcal{F}(R)|}{\binom{|C|}{2}} \leq 1$$

Subtracting from 1 reverses inequalities:

$$1 \geq 1 - \frac{|\mathcal{F}(R)|}{\binom{|C|}{2}} \geq 0$$

Therefore $\text{CSD}(R) \in [0, 1]$. $\blacksquare$

---

## Theorem 2: Coherence — $\text{CSD}(R) = 1 \iff |\mathcal{F}(R)| = 0$

**Proof.**

($\Rightarrow$) Suppose $\text{CSD}(R) = 1$. Then:

$$1 = 1 - \frac{|\mathcal{F}(R)|}{\binom{|C|}{2}} \implies \frac{|\mathcal{F}(R)|}{\binom{|C|}{2}} = 0 \implies |\mathcal{F}(R)| = 0$$

($\Leftarrow$) Suppose $|\mathcal{F}(R)| = 0$. Then:

$$\text{CSD}(R) = 1 - \frac{0}{\binom{|C|}{2}} = 1$$

$\blacksquare$

---

## Theorem 3: Fragmentation — $\text{CSD}(R) = 0 \iff |\mathcal{F}(R)| = \binom{|C|}{2}$

**Proof.**

($\Rightarrow$) Suppose $\text{CSD}(R) = 0$. Then:

$$0 = 1 - \frac{|\mathcal{F}(R)|}{\binom{|C|}{2}} \implies \frac{|\mathcal{F}(R)|}{\binom{|C|}{2}} = 1 \implies |\mathcal{F}(R)| = \binom{|C|}{2}$$

($\Leftarrow$) Suppose $|\mathcal{F}(R)| = \binom{|C|}{2}$. Then:

$$\text{CSD}(R) = 1 - \frac{\binom{|C|}{2}}{\binom{|C|}{2}} = 1 - 1 = 0$$

$\blacksquare$

---

## Theorem 4: Monotonicity — Removing a Conflict Strictly Increases CSD

**Statement.** Let $R$ and $R'$ be rooms over the same claim set $C$, where $\mathcal{F}(R') = \mathcal{F}(R) \setminus \{(c_i, c_j)\}$ for some conflict $(c_i, c_j) \in \mathcal{F}(R)$. Then:

$$\text{CSD}(R') > \text{CSD}(R)$$

**Proof.**

We have $|\mathcal{F}(R')| = |\mathcal{F}(R)| - 1$.

$$\text{CSD}(R') - \text{CSD}(R) = \left(1 - \frac{|\mathcal{F}(R)| - 1}{\binom{|C|}{2}}\right) - \left(1 - \frac{|\mathcal{F}(R)|}{\binom{|C|}{2}}\right)$$

$$= \frac{|\mathcal{F}(R)|}{\binom{|C|}{2}} - \frac{|\mathcal{F}(R)| - 1}{\binom{|C|}{2}}$$

$$= \frac{1}{\binom{|C|}{2}}$$

Since $|C| \geq 2$ (there must be at least two claims to form a conflict), $\binom{|C|}{2} > 0$, hence:

$$\text{CSD}(R') - \text{CSD}(R) = \frac{1}{\binom{|C|}{2}} > 0$$

Therefore $\text{CSD}(R') > \text{CSD}(R)$. $\blacksquare$

**Corollary (General Monotonicity).** If $\mathcal{F}(R') \subseteq \mathcal{F}(R)$, then $\text{CSD}(R') \geq \text{CSD}(R)$, with equality iff $\mathcal{F}(R') = \mathcal{F}(R)$.

*Proof:* Removing $k = |\mathcal{F}(R)| - |\mathcal{F}(R')|$ conflicts increases CSD by exactly $\frac{k}{\binom{|C|}{2}} \geq 0$, with equality iff $k = 0$.

---

## Theorem 5: Subadditivity Under Merge

**Statement.** Let $R_1, R_2$ be rooms with claim sets $C_1, C_2$ and conflict sets $\mathcal{F}_1, \mathcal{F}_2$ respectively. Define the **merged room** $R_1 \sqcup R_2$ with:

$$C_{\sqcup} = C_1 \cup C_2$$
$$\mathcal{F}_{\sqcup} = \mathcal{F}_1 \cup \mathcal{F}_2 \cup \mathcal{F}_{\times}$$

where $\mathcal{F}_{\times} = \{(c_i, c_j) \in \binom{C_{\sqcup}}{2} : c_i \in C_1 \setminus C_2,\ c_j \in C_2 \setminus C_1,\ c_i \text{ contradicts } c_j\}$ is the set of **cross-room conflicts**.

Then:

$$\text{CSD}(R_1 \sqcup R_2) \leq \max(\text{CSD}(R_1), \text{CSD}(R_2)) + \frac{|\mathcal{F}_{\times}|}{\binom{|C_{\sqcup}|}{2}}$$

**Proof.**

Let $T_{\sqcup} = \binom{|C_{\sqcup}|}{2}$. Since $C_1 \cup C_2 \supseteq C_1$ and $C_1 \cup C_2 \supseteq C_2$, we have $T_{\sqcup} \geq \binom{|C_1|}{2}$ and $T_{\sqcup} \geq \binom{|C_2|}{2}$.

The total conflicts in the merged room satisfy:

$$|\mathcal{F}_{\sqcup}| \leq |\mathcal{F}_1| + |\mathcal{F}_2| + |\mathcal{F}_{\times}|$$

Note this is an inequality (not equality) because $\mathcal{F}_1$ and $\mathcal{F}_2$ may share conflict pairs when $C_1 \cap C_2 \neq \emptyset$.

Therefore:

$$\text{CSD}(R_1 \sqcup R_2) = 1 - \frac{|\mathcal{F}_{\sqcup}|}{T_{\sqcup}} \geq 1 - \frac{|\mathcal{F}_1| + |\mathcal{F}_2| + |\mathcal{F}_{\times}|}{T_{\sqcup}}$$

For the upper bound, we use $|\mathcal{F}_{\sqcup}| \geq |\mathcal{F}_1| + |\mathcal{F}_2| - |\mathcal{F}_1 \cap \mathcal{F}_2| + |\mathcal{F}_{\times}| \geq |\mathcal{F}_1| + |\mathcal{F}_2| + |\mathcal{F}_{\times}| - |\mathcal{F}_1 \cap \mathcal{F}_2|$. More directly:

$$\text{CSD}(R_1 \sqcup R_2) = 1 - \frac{|\mathcal{F}_{\sqcup}|}{T_{\sqcup}} \leq 1 - \frac{\max(|\mathcal{F}_1|, |\mathcal{F}_2|)}{T_{\sqcup}} + \frac{|\mathcal{F}_{\times}|}{T_{\sqcup}} \cdot \mathbf{1}_{|\mathcal{F}_{\times}|>0}$$

But more precisely, since $|\mathcal{F}_{\sqcup}| \geq \max(|\mathcal{F}_1|, |\mathcal{F}_2|) + |\mathcal{F}_{\times}|$ (each room's internal conflicts are preserved, and cross-conflicts are added):

$$\text{CSD}(R_1 \sqcup R_2) = 1 - \frac{|\mathcal{F}_{\sqcup}|}{T_{\sqcup}} \leq 1 - \frac{\max(|\mathcal{F}_1|, |\mathcal{F}_2|) + |\mathcal{F}_{\times}|}{T_{\sqcup}}$$

$$= \left(1 - \frac{\max(|\mathcal{F}_1|, |\mathcal{F}_2|)}{T_{\sqcup}}\right) - \frac{|\mathcal{F}_{\times}|}{T_{\sqcup}}$$

Since $T_{\sqcup} \geq \max\!\left(\binom{|C_1|}{2}, \binom{|C_2|}{2}\right)$:

$$1 - \frac{\max(|\mathcal{F}_1|, |\mathcal{F}_2|)}{T_{\sqcup}} \leq 1 - \frac{\max(|\mathcal{F}_1|, |\mathcal{F}_2|)}{\max\!\left(\binom{|C_1|}{2}, \binom{|C_2|}{2}\right)}$$

$$= \max\!\left(1 - \frac{|\mathcal{F}_1|}{\binom{|C_1|}{2}},\ 1 - \frac{|\mathcal{F}_2|}{\binom{|C_2|}{2}}\right)$$

$$= \max(\text{CSD}(R_1), \text{CSD}(R_2))$$

Therefore:

$$\boxed{\text{CSD}(R_1 \sqcup R_2) \leq \max(\text{CSD}(R_1),\, \text{CSD}(R_2)) + \frac{|\mathcal{F}_{\times}|}{T_{\sqcup}}}}$$

The cross-conflict penalty $\frac{|\mathcal{F}_{\times}|}{T_{\sqcup}}$ is bounded by $\frac{|C_1 \setminus C_2| \cdot |C_2 \setminus C_1|}{T_{\sqcup}}$ (the maximum possible cross-conflicts). When $\mathcal{F}_{\times} = \emptyset$ (no cross-room contradictions), CSD of the merge is bounded above by $\max(\text{CSD}(R_1), \text{CSD}(R_2))$. $\blacksquare$

---

## Summary Table

| Property | Statement | Proof Technique |
|----------|-----------|-----------------|
| Boundedness | $\text{CSD} \in [0,1]$ | Set containment $\mathcal{F} \subseteq \binom{C}{2}$ |
| Coherence | $\text{CSD}=1 \iff |\mathcal{F}|=0$ | Direct algebraic equivalence |
| Fragmentation | $\text{CSD}=0 \iff |\mathcal{F}|=\binom{|C|}{2}$ | Direct algebraic equivalence |
| Monotonicity | Removing conflict $\Rightarrow$ CSD increases by $\frac{1}{\binom{|C|}{2}}$ | Difference of quotients |
| Subadditivity | Merge CSD $\leq \max(\text{CSD}_1, \text{CSD}_2) + \text{cross-penalty}$ | Inflation of denominator + additive conflict bound |

---

*Forged in the fires of computation. Zero drift. ⚒️*
