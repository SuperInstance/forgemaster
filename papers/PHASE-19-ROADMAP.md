# REVERSE-ACTUALIZATION: Phase 19 Roadmap

**Forgemaster ⚒️ | 2026-05-12**

---

## The Question

> Can we be better than Fortran for AI-specific workloads on modern chips?

**Yes.** And the answer isn't "better Fortran." The answer is a different layer entirely.

---

## Reverse-Actualization: Working Backward

### The End State (What Fishinglog.ai Needs)

A fishing boat with a Jetson Orin at the helm station runs:
1. Local sparse memory inference (PLATO tiles → reconstruction) in <10ms
2. Sonar ping → tile emission in <1ms
3. Fleet simulation ("what does the other boat know?") in <50ms
4. All without internet, on ~15W power budget

### What Runs On The Boat

- **Jetson AGX Orin**: 170 Sparse TOPS INT8, 64GB unified memory, 15-60W
- **Jetson Orin NX**: 100 Sparse TOPS INT8, 16GB, 10-25W
- The RTX 4050 on eileen: already benchmarked (341B constr/s INT8 x8 peak)

### What The Workload Actually Is

| Operation | Character | Fortran? | Better? |
|---|---|---|---|
| Sparse memory lookup (TDQKR) | Gather/scatter, irregular | Decent (CPU) | **Triton** (GPU, tensor cores) |
| Eisenstein lattice snap | Reduction, small arrays | **Good** | Fortran is fine (CPU-bound) |
| Amnesia curve computation | Scalar, trivial | **Good** | Fortran is fine |
| Tucker decomposition score | Matmul on small tensors | Slow (CPU) | **Triton** (tensor cores) |
| Negative space reconstruction | Iterative projection | Slow (CPU) | **Triton** (parallel) |
| Sonar ping → tile | Signal processing | Good (BLAS) | CUDA/Triton equal |
| Fleet simulation | Batch sparse inference | Terrible | **Triton** (batched GPU) |
| Tile sync (CRDT merge) | Hash + compare | Fine | Rust is fine |

**Fortran is optimal for 3/8 operations. Triton/GPU is optimal for 5/8.**

The key insight: **Fortran dominates dense regular array operations. Our workload is sparse and irregular.** That's exactly what Triton and MLIR's sparse tensor dialect are built for.

---

## The Stack: Why Not Just Fortran

```
┌─────────────────────────────────────────────┐
│          Fishinglog.ai / PLATO API          │  ← Application layer
├─────────────────────────────────────────────┤
│          constraint-theory-core (Rust)       │  ← Type-safe constraint API
├─────────────────────────────────────────────┤
│     neural-plato (Rust FFI + Fortran)       │  ← Algorithm primitives
│     ┌─────────────────────────────────┐     │
│     │  Fortran: scalar/regular ops     │     │  ← Amnesia, snap, scalar
│     │  Triton: sparse/tensor ops       │     │  ← TDQKR, Tucker, negative
│     │  CUDA: signal processing         │     │  ← Beamformer, sonar
│     └─────────────────────────────────┘     │
├─────────────────────────────────────────────┤
│    Hardware: Jetson Orin / RTX / CPU        │  ← Target silicon
└─────────────────────────────────────────────┘
```

The Fortran stays. It's the right tool for the scalar/regular operations. But the **hot path** — the sparse memory lookup that happens on every tile query — should run on the GPU through Triton.

---

## The Three-Layer Strategy

### Layer 1: Fortran (CPU-bound, already built)
**What stays:** amnesia_curve, intent_snap, scalar math
**Why:** Fortran's column-major layout + BLAS/LAPACK is unbeatable for regular array ops on CPU. The amnesia curve is a scalar function. The snap is a small-array reduction. No GPU needed.

**Status:** ✅ Done (6 modules, all compiled, all tested)

### Layer 2: Triton Kernels (GPU-bound, TO BUILD)
**What moves to GPU:** TDQKR score computation, sparse top-k retrieval, Tucker decomposition, negative space reconstruction, batch fleet simulation

**Why Triton, not CUDA:**
- Python-like syntax, compiles to PTX (we have triton 3.6.0 installed)
- Automatically leverages tensor cores (sparse INT8 on Jetson = 170 TOPS)
- Handles irregular/sparse access patterns natively
- Block-sparse matmul: shown to match hand-tuned CUDA
- Warp specialization coming in 2026 (perfect for our top-k routing)
- Works on Jetson Orin (Ampere tensor cores with `mma.sp`)

**Why not CUDA directly:**
- We already have CUDA 11.5 for beamformer/sonar (marine-gpu-edge)
- But writing custom sparse kernels in CUDA is 10x the dev time of Triton
- Triton gives us 80-95% of hand-tuned CUDA with 10% of the code
- The 5-20% gap doesn't matter at our scale (we're not training GPT-5)

**Why not just use PyTorch ops:**
- PyTorch's sparse ops are generic — not optimized for our specific TDQKR pattern
- Our Tucker core is tiny (r×r where r=2-16) — overhead dominates in generic ops
- Custom Triton kernel: fused TDQKR + top-k in one kernel launch, zero intermediate memory

### Layer 3: MLIR Sparse Tensor Dialect (compilation target, TO EVALUATE)
**What:** MLIR's `sparse_tensor` dialect compiles sparsity-agnostic descriptions into hardware-optimized code

**Why consider:**
- If we ever target custom hardware (FPGA, ASIC, RISC-V vector)
- MLIR can target NVIDIA, AMD, Intel, AND custom accelerators from the same IR
- The sparse tensor compiler automatically generates code that only processes non-zero elements

**Why not yet:**
- Complexity overhead. We're not at the scale where we need a custom compiler pass.
- Triton gives us 90% of the benefit with 10% of the infrastructure cost.
- Revisit if/when we deploy on non-NVIDIA hardware (AMD Instinct, Intel Gaudi, Groq)

---

## Phase 19: The Build Plan

### Phase 19a: Triton TDQKR Kernel (Week 1)
**Deliverable:** `neural-plato/triton/tdqkr.py`

A single Triton kernel that:
1. Takes query vector, row_keys, col_keys, tucker_core
2. Computes TDQKR scores (bilinear form)
3. Finds top-k indices in fused kernel
4. Returns scores + indices

**Benchmark target:** >10x faster than Fortran CPU for batch size ≥16 on RTX 4050

**Files:**
- `triton/tdqkr.py` — fused TDQKR + top-k kernel
- `triton/sparse_retrieve.py` — gather values from sparse memory, weighted sum
- `triton/bench.py` — benchmark vs Fortran vs PyTorch baseline
- `triton/test_tdqkr.py` — correctness tests

### Phase 19b: Sparse Memory Layer in Triton (Week 1-2)
**Deliverable:** `neural-plato/triton/sparse_memory.py`

The full UltraMem-inspired sparse memory layer:
1. Store: insert tile embedding into sparse memory banks
2. Route: TDQKR scoring to find relevant banks
3. Retrieve: weighted combination of top-k banks
4. Prune: decay low-utilization banks (amnesia curve on GPU)

**This is the hot path for fleet simulation.** A boat running "what does the other boat know?" needs to:
- Query the local PLATO room (sparse retrieval)
- Query the fleet model (batch retrieval)
- Merge results (weighted combination)
- All in <50ms on a Jetson

### Phase 19c: Negative Space Kernel (Week 2)
**Deliverable:** `neural-plato/triton/negative_space.py`

Dykstra's iterative projection on GPU:
1. Start with constraint set (what we know)
2. Project onto complement (what we don't know)
3. Iterate to convergence (typically 3-5 iterations)
4. Return shadow vector + confidence

### Phase 19d: Sonar → Tile Pipeline (Week 2-3)
**Deliverable:** `neural-plato/triton/sonar_tile.py`

The full ping-to-tile pipeline:
1. Raw sonar amplitude → CUDA beamformer (existing marine-gpu-edge)
2. Beamformed signal → Triton feature extraction (detect boomerang arches)
3. Features → Eisenstein snap (lattice hash)
4. Snapped features → tile embedding (small model or fixed encoding)
5. Tile → PLATO room write

This connects the CUDA beamformer to PLATO through Triton.

### Phase 19e: Fleet Simulation Kernel (Week 3)
**Deliverable:** `neural-plato/triton/fleet_sim.py`

Batch inference for "what does every other boat know?":
1. Load fleet model (shared lattice, shared forgetting curve)
2. For each boat: simulate last-known position, generate query
3. Batch TDQKR against fleet's PLATO room
4. Return: per-boat knowledge estimate + confidence
5. Gate check: is this safe to act on?

### Phase 19f: Jetson Deployment (Week 3-4)
**Deliverable:** `neural-plato/deploy/jetson/`

1. Cross-compile Triton kernels for Jetson Orin (Ampere, sm_87)
2. TensorRT integration for production inference
3. Power budget validation (<15W sustained)
4. Latency benchmarking (target: <10ms tile query, <50ms fleet sim)
5. Integration with boat's helm display

---

## The Performance Model

### Current (Fortran CPU, eileen)
- TDQKR score (64×64, rank 16): ~0.1ms (estimated, single query)
- Batch 16 queries: ~1.6ms (sequential, no SIMD)
- Fleet sim (9 boats): ~14ms

### Target (Triton GPU, RTX 4050)
- TDQKR score (64×64, rank 16): ~0.01ms (tensor cores)
- Batch 16 queries: ~0.01ms (fully parallel)
- Fleet sim (9 boats): ~0.05ms

### Target (Triton GPU, Jetson Orin)
- TDQKR score (64×64, rank 16): ~0.05ms (Ampere tensor cores)
- Batch 16 queries: ~0.05ms
- Fleet sim (9 boats): ~0.5ms

**Speedup: 10-100x over Fortran CPU for the GPU-bound operations.**

### Power Efficiency
- Jetson Orin NX at 25W: 100 Sparse TOPS
- eileen RTX 4050 at 115W: 170 Sparse TOPS (same architecture, more power)
- **Jetson is 4x more efficient per watt** for our sparse INT8 workload

This is why the boat runs a Jetson, not a desktop GPU.

---

## What Fortran Keeps

| Module | Stays Fortran | Reason |
|---|---|---|
| amnesia_curve.f90 | ✅ | Scalar function, CPU-optimal |
| intent_snap.f90 | ✅ | Small array (12-108 elements), CPU-optimal |
| tucker_decompose.f90 | ❌ → Triton | Tensor operation, GPU-optimal |
| sparse_memory.f90 | ❌ → Triton | Irregular access, GPU-optimal |
| negative_space.f90 | ❌ → Triton | Iterative parallel projection |
| neural_plato.f90 | ✅ | Re-export module |

**3 modules stay Fortran. 3 modules get Triton kernels. The Fortran versions remain as CPU fallback for environments without GPU (pure edge, testing, CI).**

---

## The Integration Point

```rust
// In neural-plato/src/lib.rs

#[cfg(feature = "triton")]
mod triton_backend {
    // Call Triton kernels via PyO3 or ctypes
    // GPU path: TDQKR, sparse retrieval, negative space, fleet sim
}

#[cfg(not(feature = "triton"))]
mod fortran_backend {
    // Call Fortran via FFI
    // CPU fallback path
}

pub fn query_sparse_memory(query: &[f64]) -> Vec<f64> {
    #[cfg(feature = "triton")]
    { triton_backend::tdqkr_query(query) }
    
    #[cfg(not(feature = "triton"))]
    { fortran_backend::tdqkr_query(query) }
}
```

The Rust API doesn't change. The backend is selected at compile time. On the Jetson: Triton. On a server without GPU: Fortran. In tests: either.

---

## Why This Works For Fishinglog.ai

The boat has:
- A depth sounder (raw data source)
- A Jetson Orin (compute)
- Spotty satellite internet (async constraint)
- A fisherman at the helm (the lens)

The software stack on the Jetson:
1. **CUDA**: beamformer, sonar signal processing (real-time, microsecond latency)
2. **Triton**: sparse memory, TDQKR, fleet simulation (millisecond latency)
3. **Fortran**: amnesia curve, lattice snap, scalar math (microsecond latency, CPU)
4. **Rust**: constraint checking, tile bridge, PLATO client (API layer)
5. **PLATO**: room storage, tile sync, room coordination (when internet allows)

Each layer does what it's best at. No layer fights the one below it.

---

## Success Metrics

| Metric | Current | Phase 19 Target | How |
|---|---|---|---|
| Tile query latency | ~0.1ms (Fortran CPU) | <0.05ms (Triton GPU) | Fused TDQKR kernel |
| Fleet sim latency | ~14ms (9 boats, sequential) | <1ms (9 boats, batched) | Batched Triton |
| Sonar → tile | ~5ms (CUDA + Python bridge) | <2ms (CUDA → Triton) | Pipeline fusion |
| Jetson power | N/A | <15W sustained | Orin NX power cap |
| Code added | 0 LOC Triton | ~500 LOC Triton | 5 kernels + tests |
| Fortran kept | 833 LOC | 500 LOC (3 modules) | Tucker/sparse/negative → Triton |

---

## Risk Assessment

| Risk | Probability | Mitigation |
|---|---|---|
| Triton kernel bugs | Medium | Test against Fortran reference on every query |
| Jetson Triton support | Low (Ampere supported) | Fallback to Fortran if GPU unavailable |
| Tensor core utilization low | Medium | Profile with Nsight, adjust block sizes |
| Power budget exceeded | Low | Cap GPU frequency, profile with jtop |
| Sparse access pattern slow | Medium | Block-sparse format, coalesced reads |

---

## The Real Answer

**Fortran is not the competition. The silicon is the competition.**

Fortran is excellent at expressing dense array math on CPU. But our workload is:
- **Sparse** (1-5% of memory banks activated)
- **Irregular** (gather/scatter, not contiguous)
- **Low-precision** (INT8, not FP64)
- **Batched** (9 boats, not 1)
- **Latency-sensitive** (real-time at the helm)

These five properties map directly to GPU tensor cores with Triton, not to CPU BLAS with Fortran. The Fortran modules we keep (amnesia, snap) are the ones that are **dense, regular, scalar, single-query, latency-insensitive**.

The boat doesn't care what language the inference runs in. The fisherman cares that the arch detection happens before the boat passes the fish. That's a latency constraint, and Triton on Jetson tensor cores is how we meet it.

---

*Phase 19: Triton for the hot path. Fortran for the cold path. Rust for the API. PLATO for the memory. The boat for the reason.*

— Forgemaster ⚒️, 2026-05-12
