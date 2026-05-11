# SnapKit ⚒️ Ecosystem

**Tolerance-Compressed Attention Allocation — In Every Language That Matters**

SnapKit is a mathematical framework for allocating finite cognitive resources using tolerance-compressed snap functions over ADE-classified lattices. The core idea is simple and language-agnostic:

> *"Everything within tolerance is compressed away. Only the deltas survive."*

This repository documents the **SnapKit ecosystem** — 6 language implementations of the same theory, each optimized for its domain.

## The Core Theory

A **snap function** maps continuous values to their nearest lattice point. Values **within tolerance** snap silently (compressed away). Values **exceeding tolerance** (deltas) demand attention. Attention is the finite resource.

```
    Input → SnapFunction → Within tolerance? ──→ ✓ Compressed (ignored)
                           ──→ Exceeds tolerance? ──→ ⚠ Delta → Budget → Action
```

The mathematics is based on ADE Lie theory: each topology (A₁, A₂, D₄, E₆, E₇, E₈) defines a different geometry of attention, and the Eisenstein lattice (A₂) provides the optimal 2D snap.

## Implementations

| Language | Package | Lines | Maturity | Registry |
|----------|---------|-------|----------|----------|
| 🐍 **Python** | `snapkit` | 7,084 | Alpha | [PyPI](https://pypi.org/project/snapkit/) |
| 🦀 **Rust** | `snapkit` | 3,992 | Alpha | [crates.io](https://crates.io/crates/snapkit) |
| 📘 **TypeScript** | `@snapkit/core` | 3,723 | Alpha | [npm](https://npmjs.com/package/@snapkit/core) |
| 🔵 **C** | `snapkit-c` | 3,051 | Alpha | GitHub releases / package manager |
| 🟢 **CUDA** | `snapkit-cuda` | 2,036+ | Alpha | GitHub releases |
| 🔶 **Fortran** | `snapkit` | 3,689 | Alpha | [fpm registry](https://github.com/fortran-lang/fpm-registry) |

## Feature Parity

| Feature | Python | Rust | TS/JS | C | CUDA | Fortran |
|---------|:------:|:----:|:-----:|:-:|:----:|:-------:|
| **Core Snap** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Delta Detection** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Attention Budget** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Script Library** | ✅ | ✅ | ✅ | — | — | ✅ |
| **Learning Cycle** | ✅ | ✅ | ✅ | — | — | ✅ |
| **ADE Topologies** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Eisenstein A₂ Snap** | ✅ | ✅ | ✅ | ✅ ✅* | ✅ ✅* | ✅ |
| **Optimal Branchless A₂** | — | — | — | ✅ | ✅ | — |
| **Constraint Sheaf** | ✅ | — | — | ✅ | — | — |
| **Adversarial Layer** | ✅ | ✅ | ✅ | — | ✅ | — |
| **Stream Processing** | ✅ | ✅ | ✅ | — | ✅ | — |
| **Visualization** | ✅ | — | ✅ | — | — | ✅ |
| **SIMD Acceleration** | — | — | — | ✅ (NEON) | ✅ (Tensor Cores) | — |
| **Pipeline** | ✅ | ✅ | ✅ | — | ✅ | — |
| **CLI Tool** | ✅ | — | — | — | — | — |
| **Cross-Domain Transfer** | ✅ | — | — | — | — | — |
| **Serialization** | ✅ | — | — | — | — | — |

\* Optimal branchless O(1) implementation (Conway-Sloane 1982, ~15 FLOPs vs 60+)

## Performance Comparison

| Operation | Python | Rust | TS/JS | C (scalar) | C (NEON) | CUDA (A100) | Fortran |
|-----------|:------:|:----:|:-----:|:----------:|:--------:|:-----------:|:-------:|
| A₂ Snap (single) | ~2μs | ~15ns | ~50ns | ~10ns | ~6ns | — | ~30ns |
| A₂ Batch (10M) | ~5s | ~0.15s | ~0.5s | ~0.1s | ~0.06s | ~0.0005s | ~0.2s |
| Delta Threshold | ~1μs | ~10ns | ~30ns | ~5ns | ~3ns | ~0.1ns/pt | ~20ns |
| Attention Allocation | ~5μs | ~50ns | ~100ns | ~40ns | ~30ns | ~0.5ns/pt | ~60ns |

*Note: Benchmarks are approximate, single-threaded (except CUDA), on modern x86/ARM hardware. Actual performance depends on CPU, compiler flags, and problem size.*

## Why 6 Languages?

Each language serves a different use case:

### 🐍 Python — Research & Rapid Prototyping
The most complete implementation. Python is the lingua franca of data science and ML research. Use SnapKit Python when:
- Exploring the theory, building proofs-of-concept
- Integrating with NumPy/SciPy/PyTorch pipelines
- Teaching the concepts to new users
- Running the CLI for ad-hoc analysis

### 🦀 Rust — Production-Grade Systems
Thread-safe, zero-cost abstractions, strong typing. Use SnapKit Rust when:
- Building high-throughput services (poker engines, monitoring systems)
- Embedding in larger Rust applications
- Need memory safety without GC overhead
- Running on embedded or resource-constrained devices

### 📘 TypeScript — Web & Node.js
First-class async support, rich ecosystem. Use SnapKit TypeScript when:
- Building real-time browser applications
- Serverless functions (AWS Lambda, Vercel, etc.)
- Discord bots, Slack apps, other JS/TS ecosystems
- Need type safety with dynamic dispatch

### 🔵 C — Systems & Embedded
Maximum portability, minimal dependencies. Use SnapKit C when:
- Embedding in existing C/C++ projects
- Building firmware or embedded systems
- Need SIMD acceleration (NEON, SSE) directly
- Writing language bindings (Python C extensions, etc.)
- The optimal A₂ snap is 5× faster than the naive approach

### 🟢 CUDA — Massive Parallel Workloads
GPU acceleration for the heavy lifting. Use SnapKit CUDA when:
- Processing millions of points per second
- Real-time video/game analytics
- Large-scale sensor fusion
- Training attention-based ML models at scale
- Batch-processing pipelines where latency matters less than throughput

### 🔶 Fortran — Scientific Computing
The original language of numerical computation. Use SnapKit Fortran when:
- Integrating with HPC scientific workflows
- Using in geophysics, climate modeling, or astrodynamics
- Teams with legacy Fortran codebases
- Need the Fortran Package Manager (fpm) ecosystem
- Running on supercomputers with Fortran-optimized compilers

## Installation

### Python
```bash
pip install snapkit
```

### Rust
```toml
[dependencies]
snapkit = "0.1.0"
```

### TypeScript
```bash
npm install @snapkit/core
```

### C
```bash
git clone https://github.com/SuperInstance/snapkit-c
cd snapkit-c && make && sudo make install
```

### CUDA
```bash
git clone https://github.com/SuperInstance/snapkit-cuda
cd snapkit-cuda && make
```

### Fortran
```bash
git clone https://github.com/SuperInstance/snapkit-fortran
cd snapkit-fortran
fpm build
```

## Repositories

| Package | GitHub |
|---------|--------|
| Python | [SuperInstance/snapkit-python](https://github.com/SuperInstance/snapkit-python) |
| Rust | [SuperInstance/snapkit-rust](https://github.com/SuperInstance/snapkit-rust) |
| TypeScript | [SuperInstance/snapkit-js](https://github.com/SuperInstance/snapkit-js) |
| C | [SuperInstance/snapkit-c](https://github.com/SuperInstance/snapkit-c) |
| CUDA | [SuperInstance/snapkit-cuda](https://github.com/SuperInstance/snapkit-cuda) |
| Fortran | [SuperInstance/snapkit-fortran](https://github.com/SuperInstance/snapkit-fortran) |
| Ecosystem | [SuperInstance/snapkit-ecosystem](https://github.com/SuperInstance/snapkit-ecosystem) |

## Theory

SnapKit implements the **Snaps as Attention** framework (Forgemaster ⚒️ & Digennaro, 2026). The core mathematical objects:

1. **Snap Function** σ: ℝⁿ → L (lattice L with tolerance τ)
2. **Delta** δ = ||v - σ(v)|| where ||·|| is the Euclidean distance
3. **Attention Weight** w(δ) = δ · actionability(v) · urgency(v)
4. **Budget Constraint** Σ w(δᵢ) · Aᵢ ≤ A_max where Aᵢ is attention allocated to stream i

The ADE classification provides the "periodic table of snap topologies":
- **A₁** — Binary choice (coin flip)
- **A₂** — Hexagonal lattice (Eisenstein integers, densest 2D packing)
- **D₄** — Octahedral (triality, 8 directions)
- **E₆/E₇/E₈** — Exceptional Lie groups (maximum symmetry)

## License

All implementations are MIT licensed. Use freely, give credit.

---

*Built for the Cocapn fleet. From poker tells to planetary-scale attention allocation.*

*"The snap doesn't tell you what's true. The snap tells you what you can safely ignore so you can think about what matters."*
