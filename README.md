# forgemaster

[![SuperInstance](https://img.shields.io/badge/part%20of-SuperInstance-purple.svg)](https://github.com/SuperInstance)

GPU fleet orchestration backend for the SuperInstance ternary fleet. Manages GPU-accelerated computation, kernel scheduling, and real-time capability profiling across fleet hardware.

## What It Does

The Forgemaster is the GPU fleet manager for SuperInstance. When a ternary-cell room needs to simulate 1M+ cells, the Forgemaster dispatches the computation to available GPUs. It decides which GPU runs which simulation, how agents are distributed across CUDA cores, and how results are collected. The Forgemaster maintains a real-time capability map of every GPU in the fleet and sizes simulations accordingly.

The conservation law **γ + η = C** applies directly: productive GPU compute time (γ) plus idle/orchestration overhead (η) sums to total fleet capacity C. The Forgemaster's job is to maximize γ.

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                    Forgemaster                        │
│                (Fleet GPU Manager)                    │
├──────────────────────────────────────────────────────┤
│                                                      │
│  ┌─────────────────┐    ┌─────────────────────────┐  │
│  │  GPU Discovery   │    │  Capability Profiler    │  │
│  │  & Registration  │    │  (via ptx-bench)        │  │
│  │                  │    │                         │  │
│  │  DGX: 40K cores  │    │  hash/dot/softmax/vec   │  │
│  │  Jetson: 1K core │    │  throughput per GPU     │  │
│  │  RTX 4050: 3K    │    │                         │  │
│  └────────┬─────────┘    └───────────┬─────────────┘  │
│           │                          │                │
│           ▼                          ▼                │
│  ┌──────────────────────────────────────────────┐     │
│  │         Simulation Dispatch Engine            │     │
│  │                                              │     │
│  │  Input: ternary-cell CellGrid tick request    │     │
│  │  → Profile GPU capabilities                  │     │
│  │  → Size simulation to available hardware     │     │
│  │  → Dispatch kernel to best-fit GPU           │     │
│  │  → Collect results via ternary-protocol      │     │
│  └──────────────────────────────────────────────┘     │
│                                                      │
│  ┌─────────────────┐    ┌─────────────────────────┐  │
│  │  Kernel Schedule │    │  Memory Manager         │  │
│  │  (per-GPU queue) │    │  (CUDA alloc/dealloc)   │  │
│  └─────────────────┘    └─────────────────────────┘  │
│                                                      │
├──────────────────────────────────────────────────────┤
│              Integration Layer                        │
│                                                      │
│  ternary-cell    →  physics model (what to simulate)  │
│  cudaclaw-1      →  CUDA framework (how to run GPU)   │
│  git-cuda-agent  →  per-agent GPU templates           │
│  ptx-bench       →  GPU benchmarking methodology      │
│  ternary-protocol→  result distribution                │
└──────────────────────────────────────────────────────┘
```

## Current State

The Forgemaster exists as an architectural design with integration documents. The component pieces are in place:

- **cudaclaw-1** provides the CUDA framework
- **ternary-cell** provides the simulation model
- **ptx-bench** provides the benchmarking methodology
- **git-cuda-agent** provides per-agent GPU templates

The Forgemaster assembles these into a fleet-wide GPU orchestration layer.

## Contents

```
forgemaster/
├── docs/
│   └── FUTURE-INTEGRATION.md   # Integration plan with fleet components
└── for-fleet/
    └── oracle1/
        └── pypi-count-correction.md  # PyPI package audit (19 confirmed)
```

### docs/FUTURE-INTEGRATION.md

Details the integration path with:
- `ternary-cell` — GPU backend for CellGrid simulations
- `cudaclaw-1` + `git-cuda-agent` — CUDA framework and agent templates
- `ptx-bench` — GPU capability profiling
- Tile acceleration across vendors (CUDA, OpenCL, NEON)
- Edge GPU orchestration (Jetson)
- JIT kernel compilation via `agentic-compiler`

### for-fleet/oracle1/pypi-count-correction.md

Audit document correcting inflated PyPI package counts. Verified via live API: **19 published** plato-* Python packages (not 31 or 98). Also notes 66 published plato-* crates on crates.io.

## Dependencies for Next Steps

1. GPU fleet discovery and capability profiling
2. Simulation dispatch and scheduling system
3. Integration with ternary-cell's tick cycle as GPU kernels
4. Real-time GPU utilization monitoring across the fleet

## Related Crates (SuperInstance Ecosystem)

- **ternary-cell** — Cellular automata engine, primary GPU workload consumer
- **cudaclaw-1** — CUDA framework providing GPU primitives
- **ptx-bench** — GPU benchmarking (hash, dot product, softmax, vector search)
- **git-cuda-agent** — Per-agent GPU computation templates
- **meta-agent** — CPU-side task coordination (Forgemaster handles GPU side)
- **symplectic-fleet** — Fleet dynamics with conservation laws
- **ternary-protocol** — Result distribution and communication
- **tile-cuda / tile-opencl / tile-neon** — Vendor-specific tile acceleration
- **agentic-compiler** — JIT kernel compilation for dynamic workloads
