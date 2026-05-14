---

## Q1: Rate-Distortion Function

With α=0.35 and a hard floor at ρ=0.261 (K=8), your R-D curve is:

**D(K) = c · K^{-0.35}, with D_min = 0.261 (K ≥ 8)**

Inverted: to halve distortion you need **2^{2.86} ≈ 7.3× more pairs**. That's expensive. The committee will note this is *worse* than random (α=0.5) and ask why you're claiming optimality.

The answer — and you must have this cold — is that α < 0.5 is the *signature of correlation*. Independent lattices give α=0.5 (disjoint coverage disks). Your cyclotomic pairs are algebraically coupled; they cover overlapping regions. The better comparison is not "vs. independent" but "vs. any zero-side-info scheme." That's where your Pareto claim lives.

The hard ceiling at K=8 is probably greedy's fault, not geometry. **You need one more experiment:** random subset selection at K=9–11 from the full 15 pairs. If the floor moves, the ceiling is algorithmic. If it doesn't, you have a genuine geometric constraint worth characterizing.

---

## Q2: Dissertation Structure

**Cut entirely:**
- Cross-domain MIDI snap (3.7× worse is a grenade in chapter 5)
- Lattice LSH cross-domain (failed for orthogonal reasons, muddies the contribution)
- Any claim about "domain universality" from P0.1 — 4/8 eigenvalue matches is not convincing

**Demote to footnote:**
- The single-pair Z[ζ₁₂] result — it's tied with hexagonal, full stop. Frame it proactively: *"We do not claim single-pair advantage. The contribution is multi-representation."* Say it in the intro. The committee will try to open with this as a dismissal; you want to have already answered it.

**Emphasize:**
- The **Zero-Side-Info Theorem** is your load-bearing contribution. Lead with it.
- α=0.35 + convergence failure (WD=0.358) — these make the thesis *credible*. The committee respects a researcher who measured the limit and reported it honestly.
- The 21% gap framed as **the information-theoretic cost of zero side information**, not a failure.

**Revised structure:**
```
Ch1: Intro — approximate identity checking as the problem
Ch2: Formal setup — covering radius, multi-lattice schemes, side information
Ch3: Zero-Side-Info Theorem + proof (core contribution)
Ch4: Empirical grounding:
     - P0.2 (single pair ties hex — no magic)
     - P0.3 (multi-rep scaling, α=0.35)
     - 86th percentile result
     - Convergence failure → structural 21% gap
     - Greedy decorrelation ceiling
Ch5: Conclusion — open questions, failed cross-domain as scope limitation
```

---

## Q3: Minimal Additional Experiments

Three experiments, ordered by necessity:

1. **Must have:** Random subset selection past K=8 — does the floor move? This determines whether α=0.35 is a property of cyclotomic structure or greedy's limitation. If the floor moves, your scaling claim changes.

2. **Must have:** Sample 10+ optimal random ensembles at K=15 and check if their lattices are geometrically close to cyclotomic basis pairs. If yes: your theorem is tight and the 21% gap is closing. If no: you need to characterize the structural difference (angle distribution mismatch is your current hypothesis — test it explicitly with angle histograms).

3. **Should have:** One higher cyclotomic order (n=15 or n=20) to confirm 86th percentile generalizes. One data point at K=15 is not enough for a scaling claim.

**Do not add:** More cross-domain experiments. The lifting map problem is a separate research problem and you don't have time to solve it here.

---

## Q4: Lifting Map — Drop It

3.7× worse than uniform is not a near-miss. It means the map is actively destructive, not just suboptimal. The 11D MIDI structure almost certainly doesn't project cleanly to 2D cyclotomic pairs — you'd need to show the domain's natural metric aligns with the Minkowski embedding, and you haven't done that.

**Drop cross-domain as a claimed contribution.** Mention the failed experiment in one paragraph at the end of Chapter 4:

> *"Preliminary experiments applying the cyclotomic scheme to 11-dimensional MIDI pitch space via a direct projection achieved 3.7× worse error than uniform quantization. We attribute this to a mismatch between the domain metric and the 2D Minkowski embedding structure. Characterizing which domains admit valid lifting maps is left to future work."*

That framing is defensible. Trying to rescue it is not — you'll spend three months on a lifting map and the committee will still ask "but does it work?"

---

## The Hostile Committee's Top 3 Attacks

1. **"Your single-pair result is just hexagonal. Where's the novelty?"** Answer: the novelty is zero-side-info multi-rep. You have a theorem. Pre-empt this in the intro.

2. **"α=0.35 is worse than random lattices. Why is this Pareto-optimal?"** Answer: Pareto in the (ρ, side-info) plane, not in ρ alone. Any scheme matching ρ=0.261 costs Ω(K) bits. Cyclotomic costs log₂(n) ≈ 6 bits.

3. **"Your cross-domain results are missing. Isn't this just a 2D curiosity?"** Answer: the theorem is stated for ℝ², the application domain is 2D approximate identity checking (e.g., constraint satisfaction, pitch-class equivalence). The question of generalization to ℝ^d is open and explicitly stated as such.

The core thesis is defensible. The α=0.35 measurement and honest convergence failure actually *strengthen* it — they show you know where the contribution ends.
