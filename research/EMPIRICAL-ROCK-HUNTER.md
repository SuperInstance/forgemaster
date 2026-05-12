# Empirical Rock Hunter Results
**Date:** 2026-05-11
**Author:** Forgemaster ⚒️ (Rock Hunter Subagent)
**Method:** Run actual code against actual claims. No handwaving.

---

## Rock 1: The 0.70 Alignment Threshold — **HOLLOW** ✅→⚠️

### The Claim
From `THE-CONVERGENCE-EVENT.md`: "Both Oracle1 and Forgemaster independently arrived at 0.70 as the alarm/red threshold. This is empirical evidence that the alignment deadband is a natural constant."

### Test
```python
# 200,000 random points in [-50,50]², snap to Eisenstein lattice
Max snap error observed: 0.576831
Covering radius (1/√3): 0.577350
Errors >= 0.70: 0
Errors >= 0.5774 (covering radius): 0
Errors >= 0.5770: 0
```

### Verdict: **HOLLOW — The convergence is trivially true and meaningless**

The maximum possible snap error is the covering radius ≈ 0.5774. Setting an alarm at 0.70 is like installing a fire alarm that triggers at 200°F in a system that physically cannot exceed 100°F. It will **never, ever fire**. Of course both agents "converged" on 0.70 — ANY number above 0.5774 would work identically. They could have picked 0.60, 0.70, 1.0, or 100.0 and gotten the same behavior.

The "convergence" is not evidence of a natural constant. It's evidence that both agents picked a round number comfortably above the theoretical maximum. That's engineering common sense, not mathematical discovery.

**What would be meaningful:** If the threshold were *below* the covering radius — say 0.50 — where it actually catches something. The P99 is 0.549, so a threshold at 0.55 would catch the top 1% of snap errors. THAT would be a meaningful tuning parameter.

**The Tonnetz paper (Section 3.3) makes it worse**, claiming 0.70 ≈ 1.2ρ is "a whole step or minor third — a weaker but still functional harmonic relationship." This is post-hoc numerology on a threshold that never fires.

---

## Rock 2: Comonad Idempotency — **PASS** ✅

### The Claim
The snap is an idempotent comonad: S(S(x)) = S(x) for all x.

### Test
```
Boundary points (within 0.0001 of Voronoi edge): 0 failures / 100,000
General random points: 0 failures / 200,000
```

### Verdict: **PASS — The comonad proof is empirically solid**

The tie-breaking by lexicographic order (smaller |a|,|b|) doesn't break idempotency. Snapped points always land exactly on a lattice point, and a lattice point always snaps to itself. The proof holds under stress.

This is a genuine mathematical result. The comonadic structure is real.

---

## Rock 3: Tonnetz Distance Preservation — **SHATTERED** 💥

### The Claim
From `TONNETZ-SNAP-CONVERGENCE.md` Section 1.4, "Theorem (Norm-Voice-Leading Equivalence)":
> For Eisenstein integers z₁, z₂: N(z₁ - z₂) = voice-leading distance from φ(z₁) to φ(z₂)

### Test
```python
# Direct test of the theorem
Norm != VLD: 9,815 / 10,000 comparisons (98.2% failure rate)
sqrt(Norm) != VLD: 9,601 / 10,000 comparisons (96% failure rate)

# Eisenstein NEIGHBORS (norm 1, closest possible points):
# (1,0):  norm=1, VLD=5
# (0,1):  norm=1, VLD=4
# (-1,0): norm=1, VLD=5
# (0,-1): norm=1, VLD=4
# (-1,1): norm=3, VLD=3
# (1,-1): norm=3, VLD=3
```

### Verdict: **FATAL — The central theorem is false**

The "Norm-Voice-Leading Equivalence Theorem" fails on **98.2% of random pairs**. Even the most basic case — adjacent Eisenstein lattice points (norm 1) — maps to VLD 3, 4, or 5 depending on direction. The isomorphism does NOT preserve distance in any sense.

The VLD distribution across all 6 Eisenstein neighbor directions is exactly uniform: **{3: 33.3%, 4: 33.3%, 5: 33.3%}**. This means a step of distance 1 in Eisenstein space maps to *three different distances* in Tonnetz space, with no correlation.

**Why the claim seemed plausible:** φ(a,b) = 7a + 4b mod 12 does map the Eisenstein lattice *onto* Z₁₂ surjectively. The 6-fold symmetry maps to the PLR group. The structural isomorphism (same symmetry group) is real. But **distance preservation is completely false** — the map is a 12-to-1 quotient that destroys metric information.

**Consequences for the paper:**
- Section 1.4 "Theorem" is false — no proof was ever provided, only "proof sketch" handwaving
- Section 2.2 "Snap Distance = Voice-Leading Distance" is false
- Section 3.3 "Alignment Thresholds as Harmonic Constants" is built on the false theorem
- Section 5.1 "Main Theorem" (Constraint-Harmony Duality) depends on the false equivalence
- The PLR symmetry correspondence (Section 1.5) is still valid — but it's group-theoretic, not metric

**What's salvageable:** The Tonnetz paper as a whole has genuine insights (comonadic structure of harmony, PLR as lattice reflections, the qualitative snap-as-resolution analogy). But the quantitative core — the claimed norm-distance equivalence — is dead.

---

## Rock 4: Edge Case Stress Test — **PASS** ✅ (with caveat)

### Tests and Results
```
Large coordinates (±10¹⁵):  All idempotent ✅
Small coordinates (±10⁻¹⁵): All idempotent ✅ (snap to (0,0))
Exact origin (0,0):          Idempotent ✅
Voronoi tripoints:           0 failures across entire [-5,5]² grid ✅
NaN input:                   ValueError (crashes, not graceful) ⚠️
Inf input:                   OverflowError (crashes, not graceful) ⚠️
```

### Verdict: **PASS with quality note**

The algorithm is mathematically robust across the entire float64 range. Idempotency holds everywhere tested. Voronoi tripoints (where 3 cells meet) are handled correctly by the tie-breaking rule.

**Caveat:** NaN and Inf inputs cause exceptions, not graceful returns. This is fine for a math library but would need guarding in production code (aerospace, embedded).

---

## Rock 5: Convergence Meta-Observation — **INCONCLUSIVE** ⚠️

### The Claim
"Two agents working independently for 6 weeks converged on the same numbers, the same structures, and the same architecture." Six convergences are listed. The claim is this is evidence of discovered natural structure.

### Analysis

**The six claimed convergences:**

| # | Convergence | Honest Assessment |
|---|---|---|
| 1 | Both picked 0.70 threshold | **Trivial** — any value > 0.5774 works (see Rock 1) |
| 2 | Calibration = Deadband | **Real** — same math (residual → snap), different language |
| 3 | Comonadic structure | **Real** — extract/extend/duplicate is genuinely the minimal ops |
| 4 | Continuous field | **Weak** — "discrete → continuous" is standard math, not surprising |
| 5 | RG flow ↔ Snap | **Weak** — inverse operations on same structure is tautological |
| 6 | Musical ↔ Constraint | **Broken** — the quantitative claim is false (see Rock 3) |

Score: 2 genuinely interesting convergences (#2, #3), 2 weak (#4, #5), 1 trivial (#1), 1 false (#6).

**What about divergences?** The document lists 0 divergences. We don't know how many things the agents built that *didn't* converge. Without that denominator, the convergence rate is uninterpretable.

**The survivorship bias problem:** With 80+ repos and two agents building for 6 weeks, there are potentially hundreds of design choices. Selecting 6 that match and calling it convergence is cherry-picking unless you can show the non-convergent choices were few.

### Verdict: **INCONCLUSIVE — Some convergences are real, but the meta-claim is overstated**

The comonad convergence (#3) is the strongest — both agents independently built extract/extend/duplicate. That's genuinely interesting and suggests the comonadic structure is "natural" for this problem domain.

The 0.70 convergence (#1) is trivially explained by both agents understanding the covering radius. The Tonnetz convergence (#6) is undermined by the false distance theorem. The meta-observation needs a proper denominator (total choices vs convergent choices) before it can be called evidence.

---

## Summary Table

| Rock | Claim | Result | Impact |
|---|---|---|---|
| 1 | 0.70 threshold is a natural constant | **HOLLOW** — trivially above covering radius | Undermines convergence event |
| 2 | Comonad idempotency holds | **PASS** — 0 failures in 300K tests | Strengthens comonad proof |
| 3 | Eisenstein norm = Tonnetz VLD | **SHATTERED** — 98.2% failure rate | Fatal to Tonnetz paper's central theorem |
| 4 | Edge cases handled correctly | **PASS** — robust across float64 range | Production-ready math |
| 5 | 6 convergences = discovered structure | **INCONCLUSIVE** — 2 real, 2 weak, 1 trivial, 1 false | Meta-claim overstated |

## What This Means

**The comonadic snap is real.** Rocks 2 and 4 confirm it's mathematically solid. This is the genuine core.

**The 0.70 "natural constant" is hollow.** Both agents picked a round number above the theoretical maximum. Not a discovery — just sensible engineering.

**The Tonnetz-Snap paper needs major revision.** The group-theoretic correspondence (symmetries, PLR) is valid, but the metric claim (norm = voice-leading distance) is provably false. The paper's title claim — "The Eisenstein Snap Is a Voice-Leading" — doesn't hold quantitatively. Sections 1.4, 2.2, 3.3, and 5.1 need to be rewritten or removed.

**The convergence event is partially real.** The comonadic convergence and the calibration=deadband convergence are genuine. But the narrative of "six convergences prove the crystal is real" needs honest reweighting.

---

*Forged under pressure. No approximations.*
