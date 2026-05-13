# TensorTile SIMD Benchmark Results

**Date:** 2026-05-13  
**Machine:** eileen (WSL2, AMD EPYC with AVX-512)  
**Compiler:** rustc 1.95.0  
**Profile:** `--release` (bench)

## CPU SIMD Capabilities

```
AVX-512:    avx512f avx512dq avx512bw avx512vl avx512cd avx512ifma avx512vbmi avx512_vbmi2 avx512_vnni avx512_bitalg avx512_vpopcntdq avx512_vp2intersect avx512_bf16
AVX2:       avx avx2 f16c fma
SSE:        sse sse2 sse4_1 sse4_2 ssse3
```

Full AVX-512 support confirmed. The hardware CAN do 16-wide float SIMD.

---

## Claim Under Test

> The paper (§4, "Vectorization") claims **16× throughput** for tile-local ops on AVX-512.

---

## Benchmark 1: TensorTile Operations (tensor_tile_bench)

Operations on real `TensorTile` structs (Thick = 5×5, Thin = 3×8).

### tensor_fill — `fill_from_source()` on N tiles
| N tiles | Time | Per-tile |
|---------|------|----------|
| 100 | 11.07 µs | 111 ns |
| 500 | 54.77 µs | 110 ns |
| 1000 | 122.6 µs | 123 ns |

### tensor_threshold — `apply_threshold(0.5)` on N tiles
| N tiles | Time | Per-tile |
|---------|------|----------|
| 100 | 409 ns | 4.1 ns |
| 500 | 2.13 µs | 4.3 ns |
| 1000 | 4.05 µs | 4.1 ns |

### tensor_norm — `l1_norm()` on N tiles
| N tiles | Time | Per-tile |
|---------|------|----------|
| 100 | 505 ns | 5.0 ns |
| 500 | 3.72 µs | 7.4 ns |
| 1000 | 5.25 µs | 5.3 ns |

### tensortiling_constraint — constraint check on tiling
| N tiles | Time |
|---------|------|
| 100 | 2.73 µs |
| 500+ | killed (OOM) |

---

## Benchmark 2: SIMD Comparison (simd_compare)

10,000 tiles, contiguous flat buffers (250,000 f32 elements), comparing explicit `#[inline(never)]` scalar vs `#[inline(always)]` auto-vectorizable patterns.

### Threshold (apply threshold to all elements)
| Variant | Time | Speedup vs scalar |
|---------|------|-------------------|
| scalar (`#[inline(never)]`) | 34.57 µs | 1.0× (baseline) |
| auto_vec (`#[inline(always)]`) | 12.61 µs | **2.74×** |

### L1 Norm (sum of absolute values)
| Variant | Time | Speedup vs scalar |
|---------|------|-------------------|
| scalar | 155.4 µs | 1.0× |
| auto_vec | 155.7 µs | **1.00×** (no measurable gain) |

### Fill (fill tensor data)
| Variant | Time | Speedup vs scalar |
|---------|------|-------------------|
| scalar | 635.0 µs | 1.0× |
| auto_vec | 637.0 µs | **1.00×** (no measurable gain) |

---

## Verdict: 16× Claim — **DISPROVEN for auto-vectorization**

### What we actually measured

| Operation | Auto-vec speedup | Claimed speedup | Gap |
|-----------|-----------------|-----------------|-----|
| Threshold | 2.74× | 16× | 5.8× short |
| L1 Norm | 1.00× | 16× | 16× short |
| Fill | 1.00× | 16× | 16× short |

### Why the gap exists

1. **The 16× figure is theoretical peak**, not achievable through auto-vectorization. It represents the zmm register width (512-bit = 16 × 32-bit floats).

2. **Auto-vectorization ceiling:** LLVM's auto-vectorizer achieves 2-3× on simple branchless loops with known bounds. It doesn't generate AVX-512 intrinsics from scalar Rust code by default without `target-cpu=native` or explicit feature flags.

3. **The threshold 2.74× is real:** The `#[inline(always)]` + branchless pattern helped LLVM vectorize the comparison loop. This is genuine SIMD speedup — just not 16×.

4. **L1 norm and fill are already optimized:** LLVM vectorizes the scalar versions of these too (`.iter().map().sum()` generates SIMD reductions). The `#[inline(never)]` doesn't prevent this — LLVM still vectorizes the loop body. Both variants hit the same performance ceiling.

### What would be needed for 16×

To actually achieve 16× scalar throughput, you need:

1. **Explicit AVX-512 intrinsics** (`std::arch::x86_64::_mm512_*`) or `std::simd` with `lane_count = 16`
2. **`RUSTFLAGS="-C target-cpu=native"`** or `target-feature=+avx512f` to enable AVX-512 codegen
3. **Aligned memory** (64-byte aligned allocations for zmm loads)
4. **Data layout optimization** — tiles should use SoA (structure of arrays) not AoS (array of structures) for cross-tile vectorization
5. **Manual loop unrolling** with prefetch hints

### What we CAN confirm

- **2.74× real speedup** on threshold ops from compiler auto-vectorization
- **The hardware is capable** — full AVX-512 instruction set is present
- **The code structure IS vectorizable** — contiguous arrays, simple ops, known bounds
- **Per-tile operations are fast:** 4-5 ns for threshold/norm on individual tiles
- **The paper's claim is achievable in principle** — just not via auto-vectorization alone

---

## Recommendations

1. **Add `RUSTFLAGS="-C target-cpu=native"` to `.cargo/config.toml`** — this alone may improve auto-vec results by enabling AVX-512 codegen
2. **Use `std::simd` (available on rustc 1.95.0)** for explicit SIMD in hot paths
3. **Restructure TensorTiling to use SoA layout** for batch operations across tiles
4. **Target realistic speedups:** 4-8× from explicit SIMD is achievable; 16× requires fusing multiple ops
5. **Benchmark with `target-cpu=native` before writing intrinsics** — the gap may close significantly

---

## Files

- `/penrose-memory/benches/tensor_tile_bench.rs` — TensorTile operation benchmarks
- `/penrose-memory/benches/simd_compare.rs` — Scalar vs auto-vec comparison
- `/penrose-memory/Cargo.toml` — Updated with criterion + bench targets
