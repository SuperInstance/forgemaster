# M11: The Information Asymmetry Theorem

**Status:** ✅ Proven  
**Date:** 2026-05-11  
**Classification:** Pure Shannon information theory — 5-line proof  

---

## 1. Precise Statement

**Theorem (Information Asymmetry in Eisenstein Lattice Snaps).**  
Let $M$ denote the miss rate of a snap system on an Eisenstein lattice, where each snap trial independently results in a hit (probability $1-M$) or miss (probability $M$). Define the Shannon self-information of an event as $I(\text{event}) = -\log_2 P(\text{event})$.

Then:

**(a)** If $M > \tfrac{1}{2}$, then $I(\text{hit}) > I(\text{miss})$ — hit events carry more information than miss events.

**(b)** If $M < \tfrac{1}{2}$, then $I(\text{miss}) > I(\text{hit})$ — miss events carry more information than hit events.

**(c)** If $M = \tfrac{1}{2}$, then $I(\text{hit}) = I(\text{miss})$ — information is balanced.

---

## 2. Proof

### Part (a): $M > \frac{1}{2} \implies I(\text{hit}) > I(\text{miss})$

We compute:

$$I(\text{hit}) = -\log_2(1 - M), \qquad I(\text{miss}) = -\log_2(M)$$

Then:

$$I(\text{hit}) > I(\text{miss})$$
$$\iff -\log_2(1 - M) > -\log_2(M)$$
$$\iff \log_2(M) > \log_2(1 - M) \qquad \text{(multiply by } -1 \text{, flip inequality)}$$
$$\iff M > 1 - M \qquad \text{(since } \log_2 \text{ is strictly monotone increasing)}$$
$$\iff 2M > 1$$
$$\iff M > \tfrac{1}{2} \qquad \blacksquare$$

### Part (b): $M < \frac{1}{2} \implies I(\text{miss}) > I(\text{hit})$

By the same chain of equivalences, $I(\text{miss}) > I(\text{hit})$ iff $M < 1 - M$ iff $M < \tfrac{1}{2}$.  $\blacksquare$

### Part (c): $M = \frac{1}{2} \implies I(\text{hit}) = I(\text{miss})$

At $M = \tfrac{1}{2}$, both events have equal probability, so $I(\text{hit}) = I(\text{miss}) = -\log_2(\tfrac{1}{2}) = 1$ bit.  $\blacksquare$

---

## 3. Numerical Verification

| Miss Rate $M$ | $P(\text{hit})$ | $I(\text{hit})$ (bits) | $I(\text{miss})$ (bits) | Ratio $I(\text{hit})/I(\text{miss})$ | $I(\text{hit}) > I(\text{miss})$? |
|:-:|:-:|:-:|:-:|:-:|:-:|
| 0.10 | 0.90 | 0.152 | 3.322 | 0.05 | **NO** |
| 0.30 | 0.70 | 0.515 | 1.737 | 0.30 | **NO** |
| 0.50 | 0.50 | 1.000 | 1.000 | 1.00 | **EQUAL** |
| 0.60 | 0.40 | 1.322 | 0.737 | 1.79 | **YES** |
| 0.70 | 0.30 | 1.737 | 0.515 | 3.38 | **YES** |
| 0.80 | 0.20 | 2.322 | 0.322 | 7.21 | **YES** |
| 0.90 | 0.10 | 3.322 | 0.152 | 21.85 | **YES** |
| 0.95 | 0.05 | 4.322 | 0.074 | 58.40 | **YES** |
| 0.99 | 0.01 | 6.644 | 0.015 | 458.2 | **YES** |

The cross-over is exactly at $M = 0.5$, as predicted. All numerical results confirm the theorem.

---

## 4. Implications for the Dissertation's Central Claim

The dissertation claims an **information asymmetry** in the Eisenstein lattice snap system: that hits are more "informative" than misses under typical operating conditions.

This theorem **confirms and sharpens** that claim with a precise mathematical foundation:

1. **The asymmetry is real and rigorous.** It follows directly from Shannon's information theory — the rarer an event, the more bits of information it carries. When the miss rate exceeds 50%, hits are the rarer event and therefore carry more information.

2. **The claim depends on $M > 0.5$.** The asymmetry is not an intrinsic property of the snap system itself — it is a consequence of the regime. If the system were tuned to hit more often than it misses ($M < 0.5$), the asymmetry would reverse: misses would become the more informative events.

3. **The cross-over at $M = 0.5$ is sharp.** There is no ambiguous zone — the inequality reverses exactly at the equiprobable point.

4. **The dissertation must state the condition.** Any claim about information asymmetry must include the condition "$M > 0.5$" (or the observed miss rate). Without this qualifier, the claim is incomplete.

---

## 5. Connection to Forge Data

The forge data reports:

- **14 out of 19 shapes** observed in the snap system
- **~70% miss rate** ($M \approx 0.70$)

At $M = 0.70$:

$$I(\text{hit}) = -\log_2(0.30) \approx 1.737 \text{ bits}$$
$$I(\text{miss}) = -\log_2(0.70) \approx 0.515 \text{ bits}$$
$$\text{Ratio} = \frac{1.737}{0.515} \approx 3.4\times$$

**Each successful hit carries approximately 3.4× more Shannon information than each miss.**

This means:
- The 5 successful snaps (30% of ~19 trials) carried **disproportionately more information** than the 14 misses
- Each hit resolved 3.4× more uncertainty than each miss
- The total information contributed by hits: $5 \times 1.737 = 8.69$ bits
- The total information contributed by misses: $14 \times 0.515 = 7.20$ bits
- Despite being outnumbered ~3:1, hits contributed more total information (8.69 > 7.20 bits)

This is the **information-theoretic justification** for why the dissertation's focus on hit events is well-founded: in the $M > 0.5$ regime, hits are the high-information signal worth studying.

---

## 6. General Principle

> **Rarity = Information.** In any binary event system, the rarer outcome carries more Shannon information. The cross-over point is always at $p = 0.5$ (equiprobable).

This is not specific to Eisenstein lattices. It is a universal property of Shannon entropy. The theorem's power lies not in its novelty (it's elementary information theory) but in **precisely connecting it to the empirical regime** of the forge data, where $M \approx 0.70$ places us firmly in the "hits are more informative" territory.

---

*Proof verified numerically. No dependencies on lattice structure — this is pure probability theory.*
