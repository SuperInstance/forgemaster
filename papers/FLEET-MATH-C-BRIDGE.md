# Eisenstein Constraint Kernel × fleet-math-c SIMD Bridge

**Integration Spec — Version 0.1**

*Forgemaster ⚒️ — May 12, 2026*

---

## 1. Executive Summary

This document specifies a **C FFI bridge** between Forgemaster's Eisenstein constraint engine (Rust, dodecet-encoder) and `fleet-math-c` (C, SIMD-accelerated PLATO tile operations). The bridge enables:

1. **Zero-copy tile integrity checking** — validate PLATO tiles using SIMD (AVX-512 / NEON) without decoding every field
2. **Holonomy-driven constraint propagation** — detect cycle inconsistencies at SIMD speeds, feed them into Eisenstein's deadband funnel
3. **Dodecet ↔ tile field mapping** — encode Eisenstein snap results (12-bit dodecets) directly into PLATO tile metadata/gradient fields
4. **Batch constraint operations** — process 1000+ tile snaps per millisecond on AVX-512 hardware

The bridge is **bidirectional**: Eisenstein constraint state flows into fleet-math SIMD ops, and fleet-math tile validation flows back into Eisenstein's merge/consensus protocol.

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Forgemaster (Rust space)                    │
│                                                              │
│  ┌───────────────────────┐   ┌───────────────────────────┐  │
│  │  EisensteinConstraint  │   │   DodecetArray (N=12/14)   │  │
│  │  - snap(x,y) → dodecet│   │   - merge() → consensus   │  │
│  │  - check() → verdict   │   │   - XOR/snap ops         │  │
│  │  - deadband funnel     │   │   - histogram vote       │  │
│  └───────┬───────────────┘   └───────────┬───────────────┘  │
│          │                                │                  │
│          └───────────┬────────────────────┘                  │
│                      │ FFI Boundary                          │
├──────────────────────┼──────────────────────────────────────┤
│                      ▼                                      │
│  ┌────────────────────────────────────────────────────┐    │
│  │              fleet-math-c SIMD Kernel              │    │
│  │                                                    │    │
│  │  plato_tile_t (64B)   constraint_graph_t (SoA)    │    │
│  │  fleet_tile_check()    fleet_holonomy_4cycle()    │    │
│  │  fleet_batch_check()   fleet_batch_holonomy()     │    │
│  └────────────────────────────────────────────────────┘    │
│                   (C space)                                 │
└─────────────────────────────────────────────────────────────┘
```

The bridge operates in **two directions**:

| Direction | What | How |
|-----------|------|-----|
| **Eisenstein → Fleet** | Dodecet snap results → tile metadata fields | `eisenstein_snap_to_tile()` |
| **Fleet → Eisenstein** | Tile violation counts → constraint severity | `tile_violations_to_error_norm()` |

---

## 3. Direct Op Mappings

### 3.1 Eisenstein `snap()` → fleet-math tile check

| Eisenstein Op | fleet-math Op | Direct? | Notes |
|---------------|---------------|---------|-------|
| `EisensteinConstraint::snap(x, y)` | N/A (no direct mapping) | ❌ | snap is a Voronoi search, not a threshold comparison |
| `SnapResult.error` field (best_err) | `tile_check_violations()` | ⚡ Indirect | Error maps to violation count via geometry: higher error → more tile fields below threshold |
| `SnapResult.error_level` (0–15) | Nibble quantization | ⚡ Indirect | Maps to a threshold band in the tile check |
| `SnapResult.angle_level` (0–15) | Not in fleet-math | ❌ | New C function needed |
| `SnapResult.chamber` (0–5) | Not in fleet-math | ❌ | New C function needed |
| `SnapResult.is_safe` | `violations == 0` | ✅ **Direct** | Safe tile ↔ 0 violations |

### 3.2 Eisenstein `merge()` → fleet-math batch ops

| Eisenstein Op | fleet-math Op | Direct? | Notes |
|---------------|---------------|---------|-------|
| `merge([SnapResult])` | `fleet_batch_check()` | ✅ **Direct** | Both process N items → single aggregated result |
| Error: take max (pessimistic) | `fleet_batch_check()` returns count of violated fields | ⚡ Indirect | Need to convert: max-violation-count → pessimistic error |
| Chirality: majority vote | Not in fleet-math | ❌ | `fleet_batch_check()` loses chirality — need a 2-buffer output (valid count + chamber histogram) |

### 3.3 Eisenstein deadband funnel → fleet-math threshold

| Eisenstein Op | fleet-math Op | Direct? | Notes |
|---------------|---------------|---------|-------|
| `deadband(t) = ρ·√(1-t)` | `threshold` parameter | ⚡ Indirect | Deadband width → threshold multiplier on tile check |
| `funnel_width` (0–1.0) | Threshold scaling | ⚡ Indirect | `threshold = base_threshold + funnel_width * (ρ_max - base_threshold)` |

### 3.4 Holonomy ↔ XOR constraint consistency

| Eisenstein Op | fleet-math Op | Direct? | Notes |
|---------------|---------------|---------|-------|
| N/A (no XOR ops in eisenstein.rs) | `holonomy_4cycle(w0,w1,w2,w3)` | ✅ **Direct** | Holonomy is an independent graph-theoretic check |
| Dodecet XOR (`x ^ y`) | Holonomy H = w0·w1 − w2·w3 | ⚡ Indirect | XOR detects bit-level anti-alignment; holonomy detects cycle imbalance |
| Dodecet AND/OR masking | Threshold clipping | ⚡ Indirect | Bit ops ↔ FMA float ops are parallel operations on the same tile |

---

## 4. Adaptation Layer: New C Functions Needed

### 4.1 `fleet_tile_snap_eisenstein()`

**Purpose:** Encodes an Eisenstein snap result directly into a PLATO tile's fields.

```c
/**
 * eisenstein_result_t — Compact Eisenstein snap result for SIMD consumption
 *
 * Packed into 16 bytes so 4 results fit in one zmm register (AVX-512).
 */
typedef struct __attribute__((packed, aligned(16))) {
    float   error;          // Snap distance from lattice point
    uint16_t dodecet;       // 12-bit constraint state (nibble-packed)
    uint8_t  chamber;       // Weyl chamber 0–5 (3 bits, padding)
    uint8_t  flags;         // bit0: is_safe, bit1: parity
} eisenstein_result_t;

_Static_assert(sizeof(eisenstein_result_t) == 8,
    "eisenstein_result_t must be exactly 8 bytes for AVX-512 pairing");
```

```c
/**
 * eisenstein_fields_t — PLATO tile field indices for Eisenstein data
 *
 * Maps Eisenstein result components into the tile's gradient/metadata slots.
 */
typedef enum {
    EISENSTEIN_FIELD_ERROR      = 0,  // tile.gradient[0] = snap error (normalized)
    EISENSTEIN_FIELD_DODECET_LO = 1,  // tile.gradient[1] = dodecet low 6 bits as float
    EISENSTEIN_FIELD_DODECET_HI = 2,  // tile.gradient[2] = dodecet high 6 bits as float
    EISENSTEIN_FIELD_ANGLE      = 3,  // tile.gradient[3] = angle level as float
    EISENSTEIN_FIELD_CHAMBER    = 4,  // tile.metadata[0] = chamber + flags as float
    EISENSTEIN_FIELD_THRESHOLD  = 5,  // tile.metadata[1] = deadband threshold
} eisenstein_fields_t;
```

**Rationale:** The tile has exactly 4 gradient + 8 metadata float fields (14 total). The Eisenstein state (error, dodecet low, dodecet high, angle, chamber, threshold) fits in 6 fields. The remaining 8 are free for other constraint systems.

### 4.2 `fleet_batch_eisenstein()`

**Purpose:** Batch process N Eisenstein snap results into SIMD-validated tile data.

```c
/**
 * Batch-encode N Eisenstein results into contiguous plato_tile_t storage.
 *
 * For each result, writes:
 *   tiles[i].gradient[0] = error_normalized
 *   tiles[i].gradient[1] = (dodecet & 0x03F) as float
 *   tiles[i].gradient[2] = ((dodecet >> 6) & 0x03F) as float
 *   tiles[i].gradient[3] = angle_level as float
 *   tiles[i].metadata[0] = chamber + flags as float
 *   tiles[i].metadata[1] = threshold (same for all tiles in batch)
 *
 * Returns: number of tiles where is_safe == true (0 violations)
 */
int fleet_batch_eisenstein(
    eisenstein_result_t *results,   // Input: N Eisenstein results
    int n,                          // Number of results
    plato_tile_t *tiles,            // Output: pre-allocated N tiles (64B each)
    float threshold                 // Deadband threshold for fleet_tile_check
);
```

**Performance:** `fleet_batch_eisenstein` + `fleet_batch_check` → 2 zmm register passes per tile. Estimated ~2.0 ns/tile on AVX-512 (vs ~50 ns for pure Rust).

### 4.3 `fleet_tile_holonomy_eisenstein()`

**Purpose:** Check if a 4-cycle of tiles has consistent Eisenstein constraint states.

```c
/**
 * Compute the holonomy of Eisenstein dodecets around a 4-cycle of tiles.
 *
 * Reads the dodecet fields from 4 tiles, treats them as edge weights, and
 * computes the holonomy: H = w0*w1 - w2*w3.
 *
 * For a consistent constraint graph, the dodecets should cycle-consistently,
 * meaning H ≈ 0.
 *
 * This links the Eisenstein A₂ constraint (Voronoi cell geometry) with the
 * fleet-math holonomy (cycle consensus).
 *
 * Returns: |H| normalized to [0, 1]. Closer to 0 = more consistent.
 */
float fleet_tile_holonomy_eisenstein(
    const plato_tile_t tiles[4],
    eisenstein_fields_t which_field   // Which tile field to use as weight
);
```

**Adaptation formula:** Given 4 tiles with dodecets d₀, d₁, d₂, d₃:

```
H = float(d₀) * float(d₁) - float(d₂) * float(d₃)
```

When `|H| ≈ 0`, the 4-cycle is **Eisenstein-consistent**: the constraint states agree around the loop.

When `|H| > ε`, the cycle is **inconsistent**: one or more tiles has a constraint that conflicts with its neighbor. The Eisenstein engine can then re-snap the offending tile(s) using a coarser deadband.

---

## 5. Op Mapping Table (Complete)

| # | Ops (Eisenstein ↔ fleet-math) | Direct? | Performance | Notes |
|---|-------------------------------|---------|-------------|-------|
| **1** | `snap() ↔ tile_check()` | ✅ Indirect | 1 zmm load + 1 VPCMPD (~0.8 ns) | snap = Voronoi search, check = threshold. Link via: `violations > 0 ⟹ error > threshold` |
| **2** | `merge() ↔ batch_check()` | ✅ Direct | 1 zmm per tile (~0.8 ns/tile) | Merge takes max error (pessimistic) |
| **3** | `deadband(t) ↔ threshold` | ✅ Indirect | No SIMD (scalar, ~2 ns) | t ∈ [0,1] maps linearly to threshold |
| **4** | `check() ↔ fleet_tile_check()` | ⚡ New code | 1 zmm load + 1 VPCMPD | Need: encode snap result into tile fields first (step 5) |
| **5** | Dodecet → tile fields | ⚡ New code | ~4 zmm shuffles per tile (~3 ns) | Write Rust FFI to pack dodecet into gradient[0..3] |
| **6** | XOR dodecets ↔ holonomy | ⚡ Indirect | 1 FMA (~6 cycles) | XOR = bit-level, holonomy = float-level. Analogy: both measure inconsistency |
| **7** | Chamber classification | ❌ No mapping | NA | No Weyl group in fleet-math. Must maintain in Rust. |
| **8** | Angle quantization | ❌ No mapping | NA | No azimuth in fleet-math. Must maintain in Rust. |
| **9** | Error quantization | ✅ Indirect | Built into tile check | Error level 0–15 maps to violation count 0–14 |
| **10** | Precision feeling (1/δ) | ❌ No mapping | NA | Metrics only, no SIMD equivalent |

### Direct-Map Summary

| Category | Count |
|----------|-------|
| ✅ Direct (use as-is) | 2 |
| ⚡ Indirect (with adaptation formula) | 4 |
| ⚡ New code needed | 2 |
| ❌ No mapping (keep in Rust) | 3 |

---

## 6. Benchmark Estimates

### 6.1 Current Performance (Baseline — Rust Only)

| Operation | Rust (dodecet-encoder) | Notes |
|-----------|------------------------|-------|
| Eisenstein snap (1 point) | ~250 ns | 9-candidate Voronoi search + chamber classification |
| Merge (10 results) | ~500 ns | Histogram vote + max error |
| Deadband check | ~15 ns | Scalar sqrt |
| Full constraint pipeline (snap → tile field → check) | ~300 ns | Real-time bottleneck at 60fps: 18μs for 60 tiles |

### 6.2 Estimated Performance (With SIMD Bridge)

| Operation | Rust + fleet-math-c SIMD | Speedup | Notes |
|-----------|--------------------------|---------|-------|
| Voronoi snap (1 point) | ~250 ns | 1× | snip is fundamentally compute-bound, not I/O bound. SIMD doesn't help Voronoi search. **Keep in Rust.** |
| Tile field encoding (1 result) | ~2 ns | 125× | Rust → aligned C struct, bulk write |
| Tile batch check (N tiles) | ~0.8 ns/tile | 375× | Fleet-math's 1-zmm per tile with AVX-512 |
| Holonomy check (4-cycle) | ~0.4 ns | 800× | Single FMA instruction + 2 loads |
| **Full pipeline** (snap + encode + check) | ~253 ns | 1.2× | Bottleneck remains Voronoi search |
| **Full pipeline batch** (N tiles, SIMD check only) | ~252 ns/tile + 0.8 ns overhead | 1.2× | Snaps still serialized. **Batch check is where SIMD wins.** |

### 6.3 Where SIMD Wins

| Scenario | Rust Only | With SIMD Bridge | Speedup |
|----------|-----------|------------------|---------|
| Single tile snap + check | ~300 ns | ~253 ns | 1.2× |
| Batch 64 tiles (1 cache line each) | ~19 μs | ~17 μs | 1.1× |
| Batch 1024 tiles | ~307 μs | ~263 μs | 1.2× |
| **Frequent re-checks** (1Eisenstein snap, 1000 SIMD re-checks) | ~300 μs | ~1 μs | **300×** |
| 4-cycle holonomy (N cycles) | ~3 μs/N | ~0.4 ns/N | **7,500×** |

**Key Insight:** The Voronoi snap is the bottleneck (~250 ns). But after the snap, **re-checks against changing thresholds are nearly free** with SIMD. If the system needs to validate the same tiles against many different threshold configurations (e.g., deadband funnel sweep), the SIMD bridge gives **300× speedup** on re-checks.

### 6.4 Memory Bandwidth Analysis

| Transfer | Bytes | Effect |
|----------|-------|--------|
| Eisenstein result (packed) | 8 bytes | Fits in L1 cache (32KB → 4096 results) |
| PLATO tile (aligned) | 64 bytes | 1 cache line |
| Batch 1024 tiles | 64 KB | Fits in L2 cache on most CPUs |
| Batch 65536 tiles | 4 MB | L3 cache range |

**Recommendation:** Keep Eisenstein results in compact `eisenstein_result_t` (8 bytes) and only expand to `plato_tile_t` when a full constraint check is needed. This saves 7× memory bandwidth.

---

## 7. Rust FFI Design (Bridge Module)

### 7.1 New Module: `eisenstein::bridge`

```rust
// dodecet-encoder/src/eisenstein/bridge.rs
//
// SIMD bridge to fleet-math-c constraint ops.

use crate::eisenstein::{EisensteinConstraint, SnapResult, COVERING_RADIUS};
use crate::Dodecet;

/// Packed representation of an Eisenstein result for fleet-math-c
#[repr(C, packed)]
#[derive(Debug, Clone, Copy)]
pub struct EisensteinResultC {
    pub error: f32,
    pub dodecet: u16,
    pub chamber: u8,
    pub flags: u8,  // bit0: is_safe, bit1: parity
}

impl From<&SnapResult> for EisensteinResultC {
    fn from(r: &SnapResult) -> Self {
        let flags = (if r.is_safe { 0u8 } else { 1u8 })
                  | (if r.parity > 0 { 2u8 } else { 0u8 });
        EisensteinResultC {
            error: r.error as f32,
            dodecet: r.dodecet,
            chamber: r.chamber,
            flags,
        }
    }
}

extern "C" {
    /// C function: int fleet_batch_eisenstein(
    ///     eisenstein_result_t *results, int n,
    ///     plato_tile_t *tiles, float threshold
    /// );
    fn fleet_batch_eisenstein(
        results: *const EisensteinResultC,
        n: i32,
        tiles: *mut std::ffi::c_void,
        threshold: f32,
    ) -> i32;

    /// C function: float fleet_tile_holonomy_eisenstein(
    ///     plato_tile_t *tiles[4],
    ///     eisenstein_fields_t field
    /// );
    fn fleet_tile_holonomy_eisenstein(
        tiles: *const std::ffi::c_void,
        field: i32,
    ) -> f32;
}

impl EisensteinConstraint {
    /// Batch snap N points → encode into SIMD-addressable tiles → validate.
    ///
    /// Returns (valid_count, snap_results).
    pub fn snap_batch_simd(&self, points: &[(f64, f64)], threshold: f32)
        -> (i32, Vec<SnapResult>)
    {
        // 1. Snap all points (Rust, Voronoi search — still the bottleneck)
        let results: Vec<SnapResult> = points.iter()
            .map(|&(x, y)| self.snap(x, y))
            .collect();

        // 2. Pack into C-compatible structs
        let packed: Vec<EisensteinResultC> = results.iter()
            .map(EisensteinResultC::from)
            .collect();

        // 3. Allocate PLATO tile buffer (aligned for SIMD)
        //    In practice, this would use aligned_alloc from within C.
        let tile_size = 64usize;
        let buf_size = points.len() * tile_size;
        let mut tiles = vec![0u8; buf_size]; // will be mmap'd or aligned_alloc'd

        // 4. Call C batch function via FFI
        let valid = unsafe {
            fleet_batch_eisenstein(
                packed.as_ptr(),
                points.len() as i32,
                tiles.as_mut_ptr() as *mut std::ffi::c_void,
                threshold,
            )
        };

        (valid, results)
    }

    /// Check holonomy of 4 Eisenstein-snapped tiles via SIMD.
    pub fn check_cycle_simd(&self, snaps: &[SnapResult; 4]) -> f32 {
        // Pack into C-compatible buffer
        let packed: [EisensteinResultC; 4] = [
            EisensteinResultC::from(&snaps[0]),
            EisensteinResultC::from(&snaps[1]),
            EisensteinResultC::from(&snaps[2]),
            EisensteinResultC::from(&snaps[3]),
        ];

        // Direct embed into tiles (TODO: real alignment)
        let mut tiles = vec![0u8; 4 * 64];

        unsafe {
            fleet_batch_eisenstein(
                packed.as_ptr(),
                4,
                tiles.as_mut_ptr() as *mut std::ffi::c_void,
                0.5,
            );

            // Now compute holonomy from the tile gradient fields
            fleet_tile_holonomy_eisenstein(
                tiles.as_ptr() as *const std::ffi::c_void,
                0, // EISENSTEIN_FIELD_ERROR
            )
        }
    }
}
```

### 7.2 Linkage Strategy

Two options:

**Option A: Static linking (recommended)**
```toml
# Cargo.toml
[build-dependencies]
cc = "1.0"

[build.rs]
fn main() {
    cc::Build::new()
        .file("fleet-math-c/fleet_math.c")
        .flag("-O3")
        .flag("-mavx512f")
        .flag("-mavx512dq")
        .flag("-DFLEET_MATH_ENABLE_AVX512")
        .compile("fleet_math");
}
```

**Option B: Dynamic linking (for hot-swap SIMD backends)**
```c
// bridge.c — dispatches to fleet-math-c at runtime
#include "fleet-math-c/fleet_math.h"

int fleet_batch_eisenstein(
    eisenstein_result_t *results, int n,
    plato_tile_t *tiles, float threshold)
{
    // Encode results into tile gradient fields
    for (int i = 0; i < n; i++) {
        tile_init(&tiles[i]);
        tiles[i].gradient[0] = results[i].error;
        tiles[i].gradient[1] = (float)(results[i].dodecet & 0x03F);
        tiles[i].gradient[2] = (float)((results[i].dodecet >> 6) & 0x03F);
        tiles[i].gradient[3] = (float)(results[i].flags);
        tiles[i].metadata[0] = (float)results[i].chamber;
        tiles[i].metadata[1] = threshold;
    }

    // Validate all tiles with fleet-math SIMD
    return fleet_batch_check(tiles, n, threshold);
}
```

---

## 8. Implementation Roadmap

### Phase 1: FFI Boundary (1 day)
- Add `eisenstein_result_t` and `eisenstein_fields_t` to `fleet_math.h`
- Add `fleet_batch_eisenstein()` to `fleet_math.c`
- Add `fleet_tile_holonomy_eisenstein()` to `fleet_math.c`
- Create `bridge.rs` in dodecet-encoder with `extern "C"` declarations
- Write `build.rs` to compile fleet-math-c as a static lib

### Phase 2: Tile-to-Tile Protocol (1 day)
- Map dodecet nibbles to tile field indices
- Write pack/unpack routines (EisensteinResultC ↔ [f32; 14])
- Test roundtrip: snap → pack → tile → unpack → decode → match original
- Benchmark single-tile roundtrip overhead

### Phase 3: Batch Path (1 day)
- Benchmark batch snapping vs batch checking
- Optimize for cache-line alignment (64-byte tile boundaries)
- Add `snap_batch_simd()` to EisensteinConstraint
- Profile and tune re-check frequency

### Phase 4: Holonomy Integration (2 days)
- Link Eisenstein XOR consistency to holonomy cycles
- Implement: `fleet_tile_holonomy_eisenstein()`
- Add deadband relaxation based on holonomy magnitude
- Test with 4-tile constraint cycles at varying consistency levels

### Phase 5: Production Hardening (2 days)
- Aligned memory allocation (posix_memalign / _mm_malloc)
- Safe FFI wrappers (panic safety, null checks)
- Runtime dispatch: scalar ↔ AVX-512 ↔ NEON
- CI tests for x86_64 (AVX-512) and aarch64 (NEON)

**Total estimated effort: ~7 days**

---

## 9. Appendix: Example Constraint Cycle

```text
Given 4 tiles arranged in a cycle:

    Tile A ──── Tile B
      │            │
      │            │
    Tile C ──── Tile D

Eisenstein snap at each tile:

    snap_A(1.0, 0.2) → dodecet_A = 0x2B1  (error=7, angle=11, chamber=1, safe)
    snap_B(0.8, 1.1) → dodecet_B = 0x3A4  (error=8, angle=10, chamber=4, safe)
    snap_C(1.2, 0.9) → dodecet_C = 0x295  (error=6, angle=9, chamber=5, safe)
    snap_D(0.9, 0.6) → dodecet_D = 0x2B0  (error=7, angle=11, chamber=0, safe)

Holonomy of dodecet errors:

    H = float(error_A) * float(error_B) − float(error_C) * float(error_D)
    H = 7.0 * 8.0 − 6.0 * 7.0
    H = 56 − 42
    H = 14.0  (significant—cycle is inconsistent)

    → Eisenstein engine should re-snap C and D with coarser deadband
    → Or: detect which tile(s) are outliers via pairwise error comparison
```

The bridge makes this cycle check **~0.4 ns** with AVX-512, vs ~3 μs with scalar Rust.

---

## 10. Copying the Header

`fleet_math.h` is designed as a **drop-in single-header library**. To use it in the dodecet-encoder project:

```sh
cp /tmp/fleet-math-c/fleet_math.h dodecet-encoder/vendor/fleet_math.h
cp /tmp/fleet-math-c/fleet_math.c dodecet-encoder/vendor/fleet_math.c
```

Then from Rust's `build.rs`:

```rust
fn main() {
    cc::Build::new()
        .file("vendor/fleet_math.c")
        .include("vendor/")
        .compile("fleet_math");
    println!("cargo:rustc-link-lib=fleet_math");
}
```

---

*End of integration spec.*
