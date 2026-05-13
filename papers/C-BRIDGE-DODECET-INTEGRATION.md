# C Bridge Dodecet Integration — Results

**Date:** 2026-05-13
**Agent:** Forgemaster ⚒️
**Task:** Wire fleet-math-c C bridge into dodecet-encoder as snap backend

## Summary

Successfully integrated the `fleet-math-c` C FFI bridge into `dodecet-encoder` behind an optional `c-bridge` feature flag. The bridge compiles, all 4 new c_bridge tests pass, and existing tests remain unaffected.

## Architecture

```
dodecet-encoder (Rust)
  ├── src/eisenstein.rs       — Pure Rust EisensteinConstraint::snap()
  └── src/c_bridge.rs         — CBridgeEisensteinConstraint::snap()
        └── fleet-math-c      — C FFI (eisenstein_bridge.c, -O3 -march=native)
```

### Feature Flag
- `c-bridge` feature in Cargo.toml enables the C bridge
- Default build: pure Rust (no C dependency)
- `cargo build --features c-bridge` to enable

### Compatibility
- `CBridgeEisensteinConstraint::snap()` returns the same `SnapResult` type as the Rust implementation
- All 20 test points match exactly on `snap_a` and `snap_b`
- Error values match within f32→f64 tolerance (< 1e-4)

## Benchmark Results (100k points, release build, -O3)

| Backend | Time (100k) | Throughput | ns/op |
|---------|------------|-----------|-------|
| **C bridge raw** | 5.77 ms | 16.3M elem/s | **57.7 ns** |
| **Rust pure** | 7.04 ms | 13.8M elem/s | **70.4 ns** |
| **C bridge (wrapped)** | 9.23 ms | 10.8M elem/s | **92.3 ns** |

### Analysis

- **C bridge raw** (pure C snap, no re-derivation): **1.22x faster** than Rust
- **C bridge wrapped** (re-derives full SnapResult): **1.31x slower** than Rust

The C bridge's raw snap is faster, but the wrapping overhead (re-running the 9-candidate search in f32, re-classifying chambers, re-packing dodecet) negates the speed advantage. The C code computes snap + dodecet in one pass, but since the C `EisensteinResult` doesn't expose `snap_a`/`snap_b`, we must re-derive them.

### Why Not 10-100x?

The original expectation of 10-100x speedup was based on the C bridge's batch throughput (26M snp/s). The actual bottleneck is:

1. **Single-point overhead** — The C advantage shows in batch mode, not per-call
2. **Wrapping overhead** — Re-deriving `snap_a`/`snap_b` from the C result duplicates work
3. **Rust is already fast** — The pure Rust 9-candidate search is well-optimized with f64

### Path to Actual Speedup

To get the expected 10-100x improvement:
1. **Expose snap_a/snap_b from C** — Add `int32_t snap_a, snap_b` to `eisenstein_result_t`
2. **Batch mode** — Use `CBridgeEisensteinConstraint::batch_snap()` which calls `eisenstein_batch_snap` once for all points
3. **Eliminate re-derivation** — Once the C struct has snap coordinates, no double work

## Test Results

- **c_bridge tests:** 4/4 pass
  - `test_c_bridge_snap_origin` ✓
  - `test_c_bridge_matches_rust` ✓ (20 test points, exact match on snap coordinates)
  - `test_c_bridge_chamber_valid` ✓ (100 random points, all chambers 0-5)
  - `test_c_bridge_covering_radius` ✓ (1000 random points, all within ρ)
- **Existing tests:** 101/102 pass (1 pre-existing flaky RNG test unrelated to changes)
- **Build:** Clean compilation with `--features c-bridge`

## Files Changed

| File | Action |
|------|--------|
| `dodecet-encoder/Cargo.toml` | Added `fleet-math-c` optional dep + `c-bridge` feature + bench entry |
| `dodecet-encoder/src/lib.rs` | Added `pub mod c_bridge` behind `#[cfg(feature = "c-bridge")]` |
| `dodecet-encoder/src/c_bridge.rs` | **New** — CBridgeEisensteinConstraint with snap(), snap_raw(), batch_snap() |
| `dodecet-encoder/benches/bridge_compare.rs` | **New** — Criterion benchmark comparing Rust vs C bridge |

## Next Steps

1. Extend `eisenstein_result_t` in C to include `snap_a`/`snap_b` — eliminates re-derivation
2. Benchmark batch mode (`batch_snap` with 100k+ points) — should show the real C advantage
3. Consider making C bridge the default for release builds once snap coordinates are exposed
