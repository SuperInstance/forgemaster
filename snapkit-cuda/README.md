# snapkit-cuda ⚒️

**GPU-accelerated tolerance-compressed attention allocation.**  
CUDA/PTX implementation of the snapkit library for massive parallel workloads.

---

## What Is This?

SnapKit compresses "close enough to expected" into background and flags **deltas exceeding tolerance** as attention-demanding. It is the computational engine behind the **Snaps as Attention** framework — the poker player's mind that ignores what's routine and focuses on what matters.

### Core Idea

```
Point (x,y) → Eisenstein Lattice Snap → Delta (distance) → Threshold → Attention
```

1. **Snap**: Project every point to the nearest Eisenstein lattice point ℤ[ω] — O(1), no branching
2. **Threshold**: Mark deltas exceeding per-stream tolerance
3. **Weight**: Score by delta × actionability × urgency
4. **Allocate**: Attention budget goes to top-K deltas

---

## Performance Target

| Operation | Target | Architecture |
|-----------|--------|-------------|
| Eisenstein batch snap | >200 B snaps/sec | One thread, one snap, O(1) |
| Delta threshold | >3 B/sec | Memory-bound at 187 GB/s |
| A₂ → A₃ ratio | >3× | Kernel complexity scaling |
| GPU vs CPU | >100× | Single-threaded reference |

---

## ADE Topology Support

| Topology | Lattice | Dimension | Use Case |
|----------|---------|-----------|----------|
| **A₁** | Binary {±1} | 1 | Binary decision, signal detection |
| **A₂** | Eisenstein ℤ[ω] | 2 | Universal solvent, hex grids, AGI attention |
| **A₃** | Tetrahedral | 3 | 3D collision, physics, navigation |
| **D₄** | Triality | 4 | Spinor representation, ML embeddings |
| **E₈** | Icosahedral | 8 | Maximum symmetry, error correction |

---

## Build

### Requirements
- **CUDA 11.5+** (tested on sm_86/sm_89/sm_75)
- **nvcc** compatible compiler
- **make**

### Quick Start

```bash
make all           # Build libsnapkit_cuda.{so,a}
make test          # Build & run all tests
make examples      # Build example programs
make bench         # Run benchmarks
make ptx           # Extract PTX for inspection
```

### File Layout

```
snapkit-cuda/
├── Makefile
├── README.md
├── include/snapkit_cuda/   — Public API headers
│   ├── snapkit_cuda.h      — Master include (single header)
│   ├── eisenstein_snap.cuh — GPU Eisenstein snap
│   ├── batch_snap.cuh      — Multi-stream batch kernels
│   ├── delta_detect.cuh    — Parallel delta detection
│   ├── attention.cuh       — Attention budget allocation
│   ├── topology.cuh        — ADE topology snap
│   └── reduce.cuh          — Reduction / top-K
├── src/                    — Host API implementations
├── kernels/                — CUDA kernel definitions
├── ptx/                    — Hand-optimized PTX assembly
│   ├── eisenstein_snap.ptx      — sm_86 (Ada)
│   └── eisenstein_snap_sm89.ptx — sm_89 (Ada refresh)
├── examples/               — Working example programs
├── tests/                  — Unit & correctness tests
├── benches/                — Performance benchmarks
└── docs/
    └── CUDA_OPTIMIZATION.md — Optimization notes
```

---

## API Overview

### Single header: `#include "snapkit_cuda.h"`

```c
// Core snap operations
void snapkit_batch_eisenstein_snap(
    const float* points_x, const float* points_y,
    int* out_a, int* out_b, float* out_delta,
    int N, cudaStream_t stream
);

// Delta detection
void snapkit_delta_threshold(
    const float* deltas, const float* tolerances, const int* stream_ids,
    int* is_delta, float* attention_weights,
    int N, cudaStream_t stream
);

// Full pipeline
int snapkit_pipeline(
    const snapkit_config_t* config,
    const float* points_x, const float* points_y,
    const int* stream_ids,
    const float* actionability, const float* urgency,
    snapkit_attention_t* out_results,
    int N, cudaStream_t stream
);

// CUDA Graphs
cudaGraphExec_t snapkit_capture_graph(
    const snapkit_config_t* config, cudaStream_t stream
);
void snapkit_launch_graph(cudaGraphExec_t graphExec, cudaStream_t stream);

// Topology dispatch
void snapkit_batch_topology_snap(
    const float* points, int dim,
    float* out_snapped, float* out_deltas,
    int N, snapkit_topology_t topology, cudaStream_t stream
);
```

---

## PTX Optimization

The Eisenstein snap kernel has hand-optimized PTX in `ptx/`:

- **`cvt.rni.s32.f32`** — hardware rounding (no `__float2int_rn` overhead)
- **`fma.rn.f32`** — fused multiply-add for delta computation
- **`ld.global.ca`** — L1-cached input reads
- **`st.global.cs`** — streaming stores for output
- **sm_89 variant** — 2× ILP by dual-issue snap operations

---

## Theory

This is the GPU engine for the **Snaps as Attention** framework. The theory:

1. **Snap = Compression**: Map continuous input to nearest lattice point
2. **Delta = Surprise**: Distance from expected (lattice) to actual
3. **Tolerance = Filter**: Below tolerance = routine, ignore; above = pay attention
4. **Actionability × Urgency = Priority**: Not all deltas matter equally
5. **Attention Budget = Resource**: Finite attention goes to top-K deltas

The ADE classification provides the "periodic table of snap topologies" — each lattice type defines a different geometry of attention.

> *"The snap is the gatekeeper of attention. The delta is the compass. The lattice is the infrastructure. Attention is the thirst."*

---

## License

Apache 2.0 — use freely, give credit.
Built for the Cocapn fleet. Forgemaster ⚒️ at your service.
