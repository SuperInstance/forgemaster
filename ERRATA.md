# ERRATA: Corrections to Published Claims

**Date:** 2026-05-07
**Source:** Red team attack #5 + internal ANALYSIS.md review

---

## Corrections Required

### 1. 24-bit Norm Bound — WRONG
- **Claim:** Eisenstein norm fits in 24 bits for 12-bit coordinates
- **Reality:** For a=4096, b=0: norm = 16,777,216 = 2²⁴ exactly. For a=4096, b=4096: norm = 4096² - 4096² + 4096² = 16,777,216. But for a=4096, b=-4096: norm = 4096² + 4096² + 4096² = 50,331,648 > 2²⁴.
- **Fix:** i32 (4 bytes) per coordinate is correct and always sufficient. The E12 type already uses i32. No code change needed, just documentation.
- **Status:** Documentation fix only

### 2. D6 Orbit Count — WRONG  
- **Claim:** 11 orbits under D6 action
- **Reality:** D6 has order 12 (6 rotations + 6 reflections). For norms with no special symmetry, orbit size is 12. Fixed points reduce orbit size. The count of 13 was the corrected value in ANALYSIS.md.
- **Fix:** Use 13 in all documentation. Verify with enumeration.
- **Status:** Documentation fix

### 3. Laman Redundancy — Qualifier Needed
- **Claim:** Hexagonal lattice has 1.5× Laman redundancy
- **Reality:** True for infinite lattice. Bounded hex disks approach 1.5× asymptotically (R=20: 1.44, R=10: 1.38). Boundary effects reduce redundancy.
- **Fix:** Add "for infinite lattice or toroidal wrap" qualifier. For bounded regions, specify boundary padding.
- **Status:** Qualifier addition, not a retraction

### 4. Temporal Snap Galois Connection — INCOMPLETE
- **Claim:** Temporal constraint narrowing forms a Galois connection
- **Reality:** No poset structure defined for the time domain. Multi-valued maps (not functions). Unit/counit conditions unverified. Not a valid Galois connection in the current formulation.
- **Fix:** Mark as "open problem" or "conjecture." Either formalize properly or remove the claim.
- **Status:** Demote from "proven" to "conjecture with known counterexamples"

### 5. Intent-Holonomy (B)⟹(A) — UNPROVEN
- **Claim:** Duality between intent alignment and holonomy triviality
- **Reality:** (A)⟹(B) partially proven. (B)⟹(A) requires fixed-point strengthening that has not been shown. Internal confidence: 30%.
- **Fix:** Mark as "one direction proven, converse open." Not "duality proven."
- **Status:** Honest reclassification

---

## What Remains Correct (No Changes Needed)

1. **INT8 soundness** — proven, verified with 100M differential tests, zero mismatches
2. **XOR isomorphism** — g(x) = x ⊕ 0x80000000 is a bijective order isomorphism, proven
3. **dim H⁰ = 9** — for constraint trees with 9 channels, proven
4. **Bloom filter Heyting algebra** — the ¬¬a ≠ a property is correct
5. **Eisenstein triple density** — 73% denser than Pythagorean, verified numerically
6. **3.17× SoA mixed-precision speedup** — measured on real hardware
7. **Zero drift in E12 arithmetic** — 10,000-operation stress test, norm multiplicativity holds
8. **Negative knowledge principle** — 4.8/5 cross-model confidence, independently validated

---

## Action Items

- [x] Publish ERRATA.md in constraint-theory-math repo
- [x] Fix eisenstein to use i32 (already correct in code)
- [ ] Update PAPER-MATHEMATICAL-FRAMEWORK.md with qualifiers
- [ ] Mark temporal snap as "conjecture" in all docs
- [ ] Mark Intent-Holonomy duality as "one direction proven"

— Forgemaster ⚒️
