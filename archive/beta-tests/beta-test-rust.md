# Beta Test Report: flux-fracture (Rust) + flux-engine-c (C Header)

**Tester persona:** Rust systems programmer, embedded/CAN bus background. Never heard of "FLUX" before this. Looking for a fast bounds-checking library for CAN bus validation.

**Date:** 2026-05-19  
**Environment:** Linux x86_64 (WSL2), rustc 1.75.0-compatible, gcc (C99)

---

## Step 1: Discovery

Searched GitHub for "constraint fracture rust" and "flux-fracture". Web search didn't find it directly — had to navigate to `github.com/SuperInstance/flux-fracture` manually. The SuperInstance org has a LOT of repos (constraint-theory-core, holonomy-consensus, etc.) but flux-fracture doesn't surface easily in search.

**Friction:** Search discoverability is low. If I didn't know to look for "SuperInstance", I'd never find this.

## Step 2: Understanding

The README is *excellent* at explaining the core idea. The "8 sensor readings" analogy is perfect for my embedded brain. Here's what I understood:

- **Fracture:** Build a bipartite graph (constraints × dimensions), BFS to find connected components. Each component = independent block you can solve in parallel.
- **Coalesce:** Because blocks share no dimensions, merge error masks via bitwise OR. Provably zero false negatives.
- **Adapt:** Re-run fracture when structure changes, get a delta.

**The theorem section:** Actually helpful. Short, clear, convincing. "Each violation is a Boolean event, blocks are disjoint, union = OR." Done. I believed it immediately.

**Why this helps CAN bus:** CAN messages are naturally independent — engine RPM has nothing to do with tire pressure. If you have 18 field checks across 8 messages, fracture gives you 8 parallel blocks. That's real speedup on embedded multicore.

**Confusion point:** The README talks about "dimension" a lot without clearly defining it up front. Had to read the code to understand: a "dimension" is a shared variable. If two constraints both reference variable X, they share dimension X and end up in the same block. For CAN bus, "dimension" = "message" (fields in the same CAN message are coupled).

## Step 3: Build & Test

```bash
cd /tmp
git clone https://github.com/SuperInstance/flux-fracture.git
cd flux-fracture
cargo build    # 0.86s — clean
cargo test     # 16/16 pass, 7.25s (most time on criterion compilation)
```

**Build:** Zero warnings. Zero dependencies (the crate itself — only criterion for benchmarks). This is HUGE for embedded. No transitive dependency nightmares.

**Tests:** 16 tests, all covering the four structures (independent, block diagonal, chain, fully connected) plus coalescence verification. Good coverage.

## Step 4: Examples

```bash
cargo run --example basic     # ✓ compiles, runs, output is clear
cargo run --example coalesce  # ✓ shows verification working
cargo run --example adaptive  # ✓ shows re-fracture delta detection
```

All three examples compile and produce readable output. They teach you:
1. **basic:** How to build a graph and fracture it
2. **coalesce:** How block masks merge, with verification
3. **adaptive:** How structure changes are detected (only 3 of 4 updates trigger recomputation)

**Critique:** The examples are clean but small. None of them show a real-world use case. I had to build my own CAN bus validator to see if this actually works for my domain. An example that does "check 8 sensor values with bounds, fracture, batch check, coalesce" would be worth 1000 words of README.

## Step 5: Building Something Real — CAN Bus Validator

I built a CAN bus validator with:
- 8 CAN message types (0x100–0x800)
- 18 total fields with realistic bounds
- Constraint graph: 18 constraints × 8 dimensions (one dimension per CAN message)
- Fracture splits into 8 blocks (messages are independent)
- 1000 random CAN frames validated
- Coalescence verified against monolithic check

**Result:** 8 blocks, 4.5× speedup potential. All 1000 frames: coalesced result = monolithic result. Zero false negatives.

### API Friction Points

1. **`DependencyGraph::from_adjacency(adj, n_c, n_d)`** — Flat row-major u8 array. Not the most ergonomic. Had to manually compute indices. A builder pattern would be nicer:
   ```rust
   // Current: manual index math
   adj[field_idx * n_dimensions + msg_idx] = 1;
   
   // Wish: builder
   graph_builder.add_constraint(field_idx).depends_on(msg_idx);
   ```

2. **No built-in bounds checking.** The crate handles fracture and coalescence, but you still write your own `check_frame()` function. For a "constraint" library, I expected bounds checking to be built in. The C header (`flux_engine.h`) DOES have `flux_check()` — the Rust crate doesn't.

3. **Block-local vs global indices.** When checking blocks independently, the block's `constraint_indices` are global, but the error mask is local (bit 0 = first constraint in the block). `verify_coalescence` handles the mapping, but you need to read the source to understand this. The README doesn't mention it.

4. **`coalesce_masks` returns u64.** My CAN bus only has 18 fields, so u64 is fine. But the type is hardcoded — no generics over mask width. For >64 constraints, you'd need `coalesce_arrays`.

5. **No `Block::check()` method.** Each block knows its constraint indices, but there's no helper to extract the relevant values and check them. I had to write this myself.

### Compiler Errors

Only one: my own bug (`&msg.fields.iter()` instead of `msg.fields.iter()`). The crate's API gave me no compiler errors. Types are clear, method signatures are obvious.

### What I Had to Read Source For

- How `from_adjacency` lays out the flat array (row-major, constraint × dimension)
- How block-local error masks map to global indices (bit position within block = index into `constraint_indices`)
- Whether `Fracturer::new()` has any configuration (no, it's stateless)

## Step 6: C Header (flux-engine-c)

```bash
git clone https://github.com/SuperInstance/flux-engine-c
```

**The good:** The single-header pattern works. `#define FLUX_ENGINE_IMPLEMENTATION` + `#include "flux_engine.h"` and you're rolling. 40/40 tests pass. 10 industry presets (automotive, aviation, medical, etc.) are incredibly useful.

**The friction:**

1. **`flux_check(float value, ...)` checks ONE value against ALL constraints.** The README shows checking 8 values, but the function signature is per-value. For CAN bus (check value[0] against constraint[0], value[1] against constraint[1]), you can't use `flux_check` directly — you have to call it once per field with a single-constraint slice.

2. **`flux_check_batch` checks each value against ALL constraints.** This gives you an N×N error matrix, not per-field validation. For CAN bus, I need value[i] checked against constraint[i], not all combinations.

3. **API naming inconsistency.** The Rust crate uses `coalesce_masks`. The C header uses `flux_coalesce` (not `flux_coalesce_masks`). Had to read the header to find the real name.

4. **`flux_graph_init` allocates internally (calloc).** The README doesn't mention this. On an embedded system with no heap, this is a problem. The Rust crate is all stack-allocated — nice contrast.

5. **No `flux_graph_set_edge` function.** The README example shows setting edges, but the actual API requires direct array access: `graph.adj[i * n + i] = 1`. Had to read the header to discover this.

6. **"3 lines" claim is slightly misleading.** The README shows:
   ```c
   FluxConstraint c[8];
   int n = flux_preset_automotive(c);
   uint8_t mask = flux_check(values, c, n);  // values is float*
   ```
   But `flux_check` takes `float value` (scalar), not `float*`. The example code on GitHub uses `values[i]` in a loop. The "3 lines" claim is aspirational.

**What IS genuinely 3 lines:**
```c
FluxConstraint c[8];
int n = flux_preset_automotive(c);
uint8_t mask = flux_check(some_value, c, n);  // checks one value against all 8 constraints
```

That's useful for "is this sensor reading within ANY acceptable range?" but NOT for "check each sensor against its own range."

## Step 7: What's Missing

### Documentation
- No rustdoc. Zero `///` doc comments on public API. Had to read source for everything.
- No "getting started" guide beyond the README
- No API reference
- The README explains the math well but the API poorly — method signatures are listed but not explained with examples
- No comparison to "just checking all constraints monolithically" with actual benchmark numbers in the README

### API
- **No bounds checking in the Rust crate.** You get fracture + coalesce but have to write your own validator. The C header has `flux_check` but the Rust crate doesn't.
- **No batch API.** Checking 1000 frames means writing your own loop.
- **No serialization.** Can't save/load a dependency graph.
- **No `Block::check(values, lo, hi)` helper.** Each block should be able to check its own constraints given a flat value array.
- **Generic over mask type but not really.** `coalesce_masks` is u64-only. For >64 constraints, switch to `coalesce_arrays`. No u128 or arbitrary-width option.

### Features
- **No parallel execution.** The README mentions rayon (`into_par_iter()`) but the crate doesn't use it. You'd add it yourself.
- **No incremental fracture.** `AdaptiveFracturer` re-runs full BFS on each update. For large graphs, this could be expensive.
- **No graph diffing.** `FractureDelta` tells you block count changed, but not which specific constraints moved.
- **No visualization.** For debugging, seeing the bipartite graph would help.

### Production Concerns
- **No `no_std` support.** Uses `Vec`, `String`, `VecDeque` — all heap-allocated. For bare-metal CAN controllers, this is a blocker. The C header is better here (calloc, but could be replaced).
- **No benchmark baseline.** The README claims "100× faster than Python NumPy" but there's no comparison to a simple monolithic Rust loop. The fracture overhead might not pay off for <100 constraints.
- **No formal verification of the theorem.** The "proof" is a paragraph. For safety-critical CAN validation, I'd want something more rigorous (Coq, Lean, or at least property-based testing).

## Step 8: Ratings

| Category | Score | Notes |
|----------|------:|-------|
| README clarity | **8/10** | Great analogy, clear math, weak API examples |
| Crate quality | **9/10** | Zero warnings, 16 tests, zero deps, clean code |
| API ergonomics | **6/10** | Had to read source for everything, no helpers, flat arrays |
| Would use in production | **Maybe** | Need no_std + bounds checking helpers first |
| Trust | **7/10** | Code is simple and readable, but no formal verification, no fuzzing, no unsafe audit |

### Overall Verdict

The core algorithm is sound and the implementation is clean. For a Rust systems programmer, reading the source is straightforward — it's BFS on a flat adjacency array, nothing scary. The crate does what it says: fracture constraint graphs into independent blocks and coalesce results.

**The gap:** This is a *fracture* library, not a *constraint* library. For CAN bus validation, I need bounds checking too. The C header (`flux-engine-c`) has this. The Rust crate doesn't. For production embedded work, I'd need:
1. `no_std` support (or at least `alloc`-only)
2. Built-in bounds checking (`check(values, constraints) -> mask`)
3. Better API ergonomics (builder pattern, less manual indexing)
4. Real benchmarks vs. monolithic checking (prove the fracture overhead is worth it for my constraint count)

**Would I use it?** For the CAN bus project — I'd use the *C header* on the microcontroller (it has everything in one file) and the Rust crate on the gateway/analysis side (where heap allocation is fine). The fracture algorithm itself is genuinely useful when you have >20 coupled constraints. For 8 independent CAN messages with 18 fields, the 4.5× speedup is real but the absolute time savings is tiny (nanoseconds). It'd matter more at scale.

**The single-header C library is the better product right now.** It has checking, fracture, sediment (progressive constraint tightening), and 10 industry presets. The Rust crate is the algorithm without the application layer.
