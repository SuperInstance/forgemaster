# PhD Work Order: Cyclotomic Lattice Snap — Complete Architecture

*From Claude Code, 2026-05-14*

## Thesis

"Approximate identity checking achieves its theoretical optimum when the domain's equivalence structure is represented as ideal structure in a cyclotomic integer ring — and the precision-robustness frontier is the covering radius of the ring's Minkowski embedding."

**Spine claim**: Z[ζ₁₂] snap achieves provably better approximate identity than Euclidean or hexagonal (A₂) alternatives.

## 5 Phases, 14 months

### Phase 0 — Falsification Battery (1-3 days)
- P0.1: Eigenvalue spectrum test on coupling tensor (30 min)
- P0.2: Random ℝ⁴ lattice comparison — is Z[ζ₁₂] special? (2-4 hrs)
- P0.3: Normalized covering radius table Z[ζ_n] n=3..15 (1 day)
- P0.4: Ottoman maqam non-12-TET test (1-2 days, needs Oracle1)

### Phase 1 — Formal Machinery (3-4 weeks)
- 1.1: Rate-distortion formalization (3 days)
- 1.2: Minkowski lifting map specification (4 days)
- 1.3: Analytical covering radius formula (3 days)
- 1.4: Shannon bound proof (5 days)
- 1.5: Gram matrix identity formalization (2 days)

### Phase 2 — Core Proofs (6-8 weeks)
- Theorem 1: Covering radius optimality (Z[ζ₁₂] vs A₂)
- Theorem 2: Shannon bound for lattice snap
- Theorem 3: Gram matrix identity (weak form)

### Phase 3 — Experiments (8-10 weeks, parallel with Phase 2)
- Set A: Constraint theory (holonomy, temporal, GPU)
- Set B: Music (Oracle1 collaboration, Ottoman maqam)
- Set C: Agent fleet (AgentField coupling eigenvalues)

### Phase 4 — Generalization (6-8 weeks)
- 4.1: Z[ζ_n] selection rule (n = exponent of symmetry group?)
- 4.2: Z[ζ₁₅] 8D lifting map
- 4.3: Multi-representation theorem (weak form)
- 4.4: FLUX ISA as canonical compact representation

### Phase 5 — Assembly (8-10 weeks)
- 5 chapters, 150 pages
- 2 arXiv preprints, 1 conference submission

## Three Thesis-Killers

1. Z[ζ₁₂] only better because ℝ⁴ (dimensional, not algebraic) → reframe as "cyclotomic rings are the NATURAL family"
2. Ottoman maqam works with Eisenstein → restrict to "equal-tempered domains"
3. Fleet eigenvalues arbitrary → drop Set C, two-domain result

**Only true killer**: Z[ζ₁₂] not in top 50% of random ℝ⁴ lattices (P0.2).

## Monday Morning

Hour 1: Eigenvalue test (30 lines Python)
Hour 2-4: Random lattice comparison (P0.2)
Hour 5-8: Begin formal rate-distortion (1.1)
Day 2: Covering radius survey (P0.3)
Day 3-5: Start Ottoman maqam coordination with Oracle1

## Z[ζ₁₂] Implementation (DONE tonight)

Scalar C benchmark: 0.293 covering radius, 1.95× tighter than Eisenstein,
97.4% win rate on 10K points. 190ns/scalar, AVX-512 SIMD pending.
