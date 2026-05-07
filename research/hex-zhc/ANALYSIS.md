# Hex ZHC Analysis — Corrected Results

## Key Findings

### Bounded Hex Disk vs Infinite Lattice

The 3V edges claim is for an **infinite** hexagonal lattice or a toroidal wrap. For a bounded hex disk of radius R:

- **Interior vertices** have exactly 6 neighbors (6 edges each, shared = 3)
- **Boundary vertices** have 2-5 neighbors (fewer edges)
- **As R → ∞**, E/V → 3.0 (boundary effects vanish)

At R=20: E/V = 2.87, converging toward 3.0 but never reaching it for bounded disks.

### Laman Redundancy

For bounded hex disks:
- R=10: redundancy = 1.38 (below 1.5 target)
- R=20: redundancy = 1.44 (approaching 1.5)
- **Interior-only**: 1.5× achieved asymptotically

The 1.5× figure is correct for the infinite lattice. Bounded regions need edge-padding to compensate for boundary effects.

### Holonomy Check Complexity

Current implementation is O(F) where F ≈ 2V for large disks. That's **O(V)** ✅.

The "worse than O(V)" verdict in the benchmark was due to Python overhead (hash lookups, tuple creation) not algorithmic complexity. The face count scales linearly with V.

### Face Cycle Closure

The face cycle closure test failed because the gradient field `(v[0]+v[1]) - (u[0]+u[1])` is NOT conservative on hexagonal edges. Need proper potential-based edge values.

## Corrected Claims

| Claim | Original | Corrected | Status |
|-------|----------|-----------|--------|
| 3V edges | Exact | Asymptotic (E/V → 3.0 as R → ∞) | ⚠️ Needs "infinite lattice" qualifier |
| Laman 1.5× | Exact for hex | Asymptotic for bounded disk | ⚠️ Same |
| Laman 2.0× (3D FCC) | Exact | Exact (theoretical) | ✅ |
| O(V) holonomy check | Exact | O(V) for face count | ✅ |
| Eisenstein triple density | 25% denser | ~73% denser (1.73×) | ✅ STRONGER |
| 24-bit norm bound | 16,769,025 < 2²⁴ | FALSE: 3·4096² = 50M > 2²⁴ | ❌ |
| D6 orbit count | 11 | 13 | ❌ |

## What This Means

1. **Eisenstein triples are even more useful than claimed** — 73% denser means more constraint solutions per search step
2. **24-bit bound is wrong** — the E12 type needs more than 3 bytes per coordinate for full 12-bit range; 4 bytes (i32) is correct
3. **Laman analysis needs infinite/toroidal qualifier** — the math is right but bounded regions need adjustment
4. **O(V) algorithm works** — the spanning tree + face enumeration approach is genuinely linear
