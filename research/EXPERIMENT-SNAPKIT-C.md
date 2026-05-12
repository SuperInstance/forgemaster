# EXPERIMENT: snapkit-c — Correctness, Performance & Embedded Suitability

**Date:** 2026-05-11  
**Platform:** WSL2 Linux 6.6.87.2 (x86_64), gcc (Ubuntu)  
**Library:** snapkit — Eisenstein lattice snapping, temporal beat grids, spectral analysis  

---

## Summary

| Category | Verdict |
|----------|---------|
| Correctness | ✅ PASS (8/8 core tests) |
| Performance | ✅ 23–30 Mops/sec (Eisenstein snap), ~15 Mops/sec (temporal) |
| Embedded suitability | ✅ Zero malloc, 8-byte core struct, C99, no dependencies |
| Naive vs Voronoi | ⚠️ Naive is ~20% faster (2×2 vs 3×3 search); Voronoi is for correctness guarantee |

---

## Phase 1: Correctness

### Test 1 — Covering Radius (1M random points)
```
Points tested:    1,000,000
Range:            [-500, 500] × [-500, 500]
Max snap dist:    0.577059592056421
1/√3:             0.577350269189626
Margin:           2.91e-04
Mean dist:        0.351166
Violations:       0
```
**PASS** — All snap distances strictly ≤ 1/√3.

### Test 2 — Idempotency (100K points)
```
Points tested:    100,000
Failures:         0
```
**PASS** — snap(snap(p)) == snap(p) for all points.

### Test 3 — Lattice Correctness (100K points)
```
Points tested:    100,000
Failures:         0
```
**PASS** — Snapped points reconstruct to valid Eisenstein integers and re-snap to themselves.

### Test 4 — Covering Radius Measurement (systematic)
```
Max distance in Voronoi cell of (0,0): 0.577312705559068
Achieved at: (0.500000, -0.288600)
1/√3:                                0.577350269189626
Difference:                          3.76e-05
```
**PASS** — Actual covering radius matches theory (within grid resolution).

### Test 5 — Boundary Cases
```
Edge (0,0)-(1,0) midpoint:        → (0,0) — OK (tiebreak to smaller |a|+|b|)
Edge (0,0)-(-1,1) near-midpoint:  → (0,0) — OK
All 6 Voronoi corners snap within covering radius — OK
```
**PASS** — Boundary tiebreaks are deterministic and consistent.

### Test 6 — Degenerate Cases
```
Origin (0,0):                    → (0,0) — OK
Lattice (1,0):                   → (1,0) — OK
Near-lattice (0.5, √3/2):        → (1,1) — OK
Large (+1M, +1M):                → (1577350,1154700), dist=0.466 — OK
Large (-1M, -1M):                → (-1577350,-1154700), dist=0.466 — OK
Large (+1M, -1M):                → (422650,-1154700), dist=0.466 — OK
Very large (1B, 0):              → (1000000000,0), dist=0.000 — OK
```
**PASS** — All degenerate cases handled correctly. No overflow, no crashes.

### Test 7 — Temporal Snap
```
Phase range [0,1):               0 violations out of 100K — OK
On-beat detection (t=5.0):       is_on_beat=1 — OK
Off-beat detection (t=5.5):      is_on_beat=0 — OK
Beat index (t=3.0):              beat_index=3 — OK
T0 detection (synthetic):        is_t_minus_0=1 — OK
Negative period init:            returns -1 — OK
Beat range [2,5]:                count=4 (beats at 2,3,4,5 inclusive)
```
**PASS** — All temporal functions correct. Range is inclusive of endpoints.

### Test 8 — Spectral Analysis
```
Uniform entropy (32 bins):       4.9997 bits (expected 5.0000), error=0.0003 — OK
Constant entropy:                0.0000 bits — OK
Binary entropy (2 bins):         1.0000 bits — OK
White noise ACF lag-0:           1.0000 — OK
White noise ACF lag-1:           -0.0006 ≈ 0 — OK
Random walk Hurst:               1.0000 (persistent — correct for cumulative sum)
Spectral summary sanity:         entropy=4.997, hurst=0.489, acf_lag1=-0.031, stationary=1
```
**PASS** — Entropy and autocorrelation are numerically precise. Hurst of cumulative random walk correctly returns ~1.0 (persistent series). White noise Hurst ~0.5 confirmed via spectral_summary.

### Bonus — Naive vs Voronoi Agreement
```
Disagreements:     0 out of 100,000
Max distance diff: 0.00e+00
```
**PASS** — Both algorithms always agree on the nearest lattice point.

---

## Phase 2: Performance Benchmarks

### Eisenstein Snap (10M iterations)

| Operation | -O2 (ns/op) | -O2 (Mops/s) | -O3 (ns/op) | -O3 (Mops/s) |
|-----------|-------------|--------------|-------------|--------------|
| Voronoi snap | 43.1 | 23.2 | 39.7 | 25.2 |
| Naive snap | 34.2 | 29.2 | 32.9 | 30.4 |
| Full snap (with dist) | 43.8 | 22.9 | 39.5 | 25.3 |

### Batch Snap (1M points)

| Operation | -O2 (ns/op) | -O2 (Mops/s) | -O3 (ns/op) | -O3 (Mops/s) |
|-----------|-------------|--------------|-------------|--------------|
| Batch Voronoi | 44.6 | 22.4 | 38.5 | 26.0 |
| Batch full | 66.7 | 15.0 | 56.7 | 17.6 |

### Naive vs Voronoi Speed
```
Voronoi: 0.217 sec (O2), 0.204 sec (O3)
Naive:   0.179 sec (O2), 0.164 sec (O3)
Ratio:   naive is ~1.2× faster (2×2 vs 3×3 local search)
```
Voronoi is slightly slower due to the 3×3 neighborhood search vs naive's 2×2, but provides the stronger correctness guarantee (covering radius proof).

### Temporal Snap (1M ops, -O2)

| Operation | ns/op | Mops/s |
|-----------|-------|--------|
| Single snap | 79.6 | 12.6 |
| Batch snap | 72.3 | 13.8 |
| T0 observe | 77.8 | 12.8 |

### Spectral Analysis (-O2)

| Operation | Time/call |
|-----------|-----------|
| Entropy (n=10K, 32 bins) | 11.0 µs |
| Hurst exponent (n=10K) | 225.1 µs |
| Full spectral (n=10K) | 3,789.3 µs (3.8 ms) |

### Memory Footprint

| Struct | Size |
|--------|------|
| `sk_eisenstein` | 8 bytes |
| `sk_snap_result` | 24 bytes |
| `sk_beat_grid` | 32 bytes |
| `sk_temporal_result` | 40 bytes |
| `sk_temporal_snap` | 1,096 bytes (includes 64-entry circular buffer) |
| `sk_spectral_summary` | 40 bytes |

---

## Phase 3: Embedded Suitability

### Binary Size

| Build | Text (bytes) | Binary (bytes) | Stripped (bytes) |
|-------|-------------|----------------|------------------|
| -Os (size opt) | 13,155 | 25,736 | 22,664 |
| -O2 (default) | 16,271 | 25,712 | — |
| -O3 (speed) | 25,674 | 42,144 | — |

**Library sizes:**
- `libsnapkit.a`: 13 KB (static)
- `libsnapkit.so`: 21 KB (shared)

### Zero malloc Verification
```
grep for malloc/calloc/realloc/free in source: 0 calls
nm check on compiled object: no malloc symbols
```
**✅ Zero heap allocations.** All buffers are caller-provided. Truly bare-metal compatible.

### Cross-Compilation
- ARM cross-compiler (`arm-linux-gnueabihf-gcc`): **Not available** on this host
- Library is pure C99 with no platform-specific code — should cross-compile trivially

### Stack Usage
- `sk_temporal_snap` is the largest struct at 1,096 bytes (circular buffer)
- Hurst exponent uses a VLA for centered data (n × 8 bytes)
- No recursion in the codebase
- Maximum theoretical stack depth: linear (no deep call chains)
- **⚠️ Note:** `sk_hurst_exponent` allocates a VLA of `n * sizeof(double)` on the stack. For n=10K that's 80KB. For embedded, use smaller n or provide stack-allocated version.

### Bare-Metal Compatibility Checklist

| Criterion | Status |
|-----------|--------|
| No malloc/calloc/realloc | ✅ |
| No system calls | ✅ |
| No file I/O | ✅ |
| No threads | ✅ |
| C99 compatible | ✅ |
| No dependencies beyond `<math.h>` | ✅ |
| Caller-provided buffers | ✅ |
| Deterministic output | ✅ |
| Stack-allocable structs | ✅ (except VLA in Hurst) |
| Header-only option | ✅ (`SNAPKIT_IMPLEMENTATION`) |

**Verdict: Truly bare-metal compatible.** The only concern is the VLA in `sk_hurst_exponent` for large datasets on constrained stacks. For embedded, pass n ≤ 1024 for Hurst (8KB stack).

---

## Key Findings

1. **Covering radius proven in practice:** Max snap distance 0.57706 < 1/√3 ≈ 0.57735, with 2.9×10⁻⁴ margin across 1M random points.

2. **Naive snap is faster:** The 2×2 search (naive) beats 3×3 (Voronoi) by ~20%. However, Voronoi's extra check ensures the covering radius guarantee. In practice, both always agree — the naive method might be preferred for performance-critical paths.

3. **Temporal snap is clean:** Phase always in [0,1), beat indices correct, T0 detection works on synthetic zero-crossing data.

4. **Spectral analysis is numerically solid:** Entropy within 0.0003 bits of theoretical for uniform distribution. Autocorrelation lag-0 exactly 1.0.

5. **Hurst estimation caveat:** The R/S analysis implementation is approximate. Cumulative random walks correctly show H≈1.0, but white noise Hurst may vary. This is expected — R/S analysis has known variance.

6. **Zero allocation design is genuine:** No malloc, no hidden allocations. The `sk_entropy` helper uses a 256-int stack buffer. The Hurst function uses a VLA. Everything else is caller-managed.
