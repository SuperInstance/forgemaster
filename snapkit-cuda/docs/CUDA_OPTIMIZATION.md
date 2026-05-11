# CUDA Optimization Notes — snapkit-cuda

## Architecture Overview

```
Host → [pinned memory] → cudaMemcpyAsync → Kernel: batch snap
                                          → Kernel: delta threshold
                                          → Kernel: attention weight
                                          → Reduce: top-K
Host ← [pinned memory] ← top-K results (small)
```

## Core Kernel: Eisenstein Snap (A₂)

### Math
The Eisenstein lattice ℤ[ω] = {a + bω : a,b ∈ ℤ} where ω = (-1 + i√3)/2.
A point (x,y) is mapped to lattice coordinates:
- `b = round(2y/√3)`
- `a = round(x + b/2)`

This is O(1) per point with no branching → ideal GPU kernel.

### PTX Optimization
In `ptx/eisenstein_snap.ptx`:
- **`cvt.rni.s32.f32`** — hardware round-to-nearest-even (no __float2int_rn overhead)
- **`fma.rn.f32`** — fused multiply-add for delta computation (single instruction)
- **`ld.global.ca`** (cached at L1) for input reads
- **`st.global.cs`** (cache streaming) for output writes

### Memory Access Pattern
- **SoA layout**: separate arrays for x, y, a, b, delta → fully coalesced
- **Warp per row**: all threads in a warp access consecutive addresses
- **Alignment**: all arrays are 128-byte aligned (cudaMalloc default)

### Occupancy Targets
- 256 threads/block, 128 registers/thread → ~32-48 warps/SM on sm_86
- PTX kernel uses ~16 registers → higher occupancy ~64 warps/SM

## Memory Hierarchy

| Memory | Usage | Latency |
|--------|-------|---------|
| Global (SoA) | Input points, output coords | ~400 cycles |
| Const | Stream tolerances (≤16 streams) | ~20 cycles |
| Texture | (Future) Script patterns | Cached |

## PTX Assembly Strategy

### sm_86 (RTX 4050)
- Hand-optimized PTX in `eisenstein_snap.ptx`
- Uses `mov.b32` for register-to-register
- `ld.global.ca.f32` for cached loads
- `fma.rn.f32` for fused multiply-add
- `cvt.rni.s32.f32` for hardware rounding

### sm_89 (RTX 4060+)
- `eisenstein_snap_sm89.ptx` — 2× ILP by dual-issue snap operations
- Interleaves two points' computation per thread
- Uses `st.async` for asynchronous stores

## Delta Detection

### Memory Bound
Delta detection is ~memory-bound at 187 GB/s.
Expected: ~3B deltas/sec on RTX 4050.
Optimization path: use `__ldg()` for read-only data.

### Warp-Level Reduction
For top-K detection:
```cuda
__shfl_down_sync(0xFFFFFFFF, val, 16);  // warp-level
__shfl_down_sync(0xFFFFFFFF, val, 8);
__shfl_down_sync(0xFFFFFFFF, val, 4);
__shfl_down_sync(0xFFFFFFFF, val, 2);
__shfl_down_sync(0xFFFFFFFF, val, 1);
```

## CUDA Graphs

For fixed-topology workloads (same snap function, streaming data):
- Capture kernel sequence once
- 18× launch latency reduction
- API: `snapkit_capture_graph()` / `snapkit_launch_graph()`

## Multi-Stream Pipeline

```
Stream 0: [snap][threshold][weight][reduce]
Stream 1: [snap][threshold][weight][reduce]
...
Stream 15:[snap][threshold][weight][reduce]
       ↓
       Global top-K merge (small, CPU)
```

Each stream operates independently; only top-K merge is serialized.

## Compiler Flags

```makefile
# Release
-gencode arch=compute_86,code=sm_86
-ptxas-options=-v  # Verbose PTX
-use_fast_math     # Fast math (__sinf, __expf, etc.)
-maxrregcount=24   # Force low register count

# Debug
-G           # Device debug
-lineinfo    # Source line info in PTX
```

## Profiling

```bash
# Kernel timing via events
cudaEventRecord(start) → kernel → cudaEventRecord(stop)

# Nsight Systems
nsys profile -o snapkit ./batch_eisenstein

# Occupation
ncu --set full -o snapkit ./batch_eisenstein
```

## Performance Targets

| Metric | Target | Measured |
|--------|--------|----------|
| Eisenstein snap | >200 Gpts/s | — |
| Delta threshold | >3 B deltas/s | — |
| A₂ → A₃ ratio | >3× | — |
| A₂ → D₄ ratio | >2× | — |
| GPU vs CPU | >100× | — |
| CUDA Graphs | <5 µs launch | — |

## Known Issues

1. **NaN propagation**: Current delta computation returns NaN if input is NaN.
   Mitigation: warp-level `__isnanf()` check or early exit.

2. **Overflow**: For very large values (|x|,|y| > 1e7), `a` and `b` may overflow int32.
   Mitigation: Use `clamp` in host code or long long for extreme ranges.

3. **Determinism**: Summation order may vary between runs for top-K reduction.
   Mitigation: Use fixed sort order or atomics.

## Future Optimizations

1. **Vectorized loads**: `uint2` or `float2` load for paired xy coordinates
   - Tradeoff: Forces interleaved layout (AoS) vs SoA
   - Benchmark both for your use case

2. **Persistent threads**: Kernel that stays resident and processes work as it arrives
   - Benefit: Zero launch latency
   - Danger: Starvation if not enough work

3. **Cooperative groups**: Grid-wide synchronization for multi-step pipeline
   - Coalesced reads across steps
   - Available on sm_86+ via `cudaCG`

4. **Tensor Cores**: IMMA for integer lattice matching
   - Only if a,b can be represented as INT8
   - 341B operations/sec theoretical on RTX 4050
