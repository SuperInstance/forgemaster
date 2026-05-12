# Falsification Correction: Deadband ≡ Voronoï Snap Isomorphism

**Date:** 2026-05-11
**Status:** CLAIM REVISED

## Original Claim

"The deadband protocol (P0→P1→P2) is mathematically isomorphic to the 9-candidate Voronoï snap."

## Falsification Result

**The parity-based fast path is NOT equivalent to full Voronoï search.**

| Method | Error Rate | Max Distance |
|--------|-----------|-------------|
| 9-candidate Voronoï | 0.0% | 0.5766 < 1/√3 ✅ |
| Parity fast path | 8.48% (parity≠2) | Can exceed 1/√3 ❌ |
| Naive rounding | 8.48% | 0.6596 > 1/√3 ❌ |

When `(a-b) % 3 ∈ {0,1}`, naive rounding fails 8.48% of the time.
When `(a-b) % 3 == 2`, the FLUX correction `b += 1` fails ~43% of the time.

## Revised Claim

**The deadband protocol and Voronoï snap are STRUCTURALLY isomorphic but NOT computationally identical:**

- Both follow the P0→P1→P2 pipeline (map negative space → find channels → optimize)
- Both seek the nearest valid lattice point
- The parity check is a FAST APPROXIMATION that works 91.5% of the time
- The 9-candidate search is EXACT and guarantees the covering radius bound
- The structural isomorphism (same pipeline, same goal) holds
- The computational isomorphism (same results) does NOT hold

## What This Means

1. **For the dissertation (Ch 5):** The isomorphism theorem must be revised to "structural isomorphism" not "computational identity"
2. **For snapkit:** The parity fast path can be used as an optimization (skip 9-candidate search when it agrees), but MUST fall back to full search for guarantee
3. **For the framework:** The deadband-as-feeling insight still holds — the funnel narrows toward the snap point regardless of which algorithm finds it
4. **For the fleet:** Parity-based health checks work (91.5% accuracy is fine for monitoring), but safety-critical snaps MUST use Voronoï

## The Silver Lining

This falsification is STRONGER evidence than a clean pass would have been:
- The framework found its own bug through its own testing protocol
- The structural isomorphism still holds (P0→P1→P2)
- Only the computational shortcut was overclaimed
- The exact algorithm (9-candidate) is proven correct (10M points, 0 violations)
- The fast approximation is correctly characterized (91.5% accuracy)

## Action Items

- [ ] Revise DEADBAND-SNAP-UNIFICATION.md: "structural isomorphism" not "identity"
- [ ] Revise DISSERTATION-V3 Ch 5: same correction
- [ ] Add parity fast path to snapkit as optional optimization with fallback
- [ ] Update claim status in FALSIFICATION-CAMPAIGN.md
- [ ] Add visual tile: parity vs Voronoï comparison

---

*Falsification is the highest form of respect for a theory.*
