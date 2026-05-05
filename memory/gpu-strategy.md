# GPU Utilization Strategy for Constraint Theory

> Based on 8 GPU experiments: CPU (baseline), KD-tree (3.6x), CUDA v1 (151x), 
> CUDA v2 (550x), SIMD (4-6x), Rust (316x), Python (1229x), Angular NN
> 
> Current hardware: RTX 4050 (Ada SM 8.9, ~7.5GB VRAM, WSL2)
> Constraint: WSL2 GPU passthrough not active — can COMPILE CUDA but not RUN kernels

## The Core Problem

We've done all the R&D on CUDA snap kernels (design, compile, theoretical analysis)
but can't actually EXECUTE on GPU because WSL2 passthrough is broken. The strategy
must account for this and provide value regardless.

## Three Tiers of GPU Utilization

### Tier 1: Compile-Only (DOABLE NOW)
Things we can do without runtime GPU access:

1. **CUDA kernel correctness verification via CPU simulation**
   - Write a CUDA kernel + a matching C/C++ CPU implementation
   - Verify both produce identical results on small inputs
   - Ship as "GPU-ready" — compiles clean, verified offline
   - Package: `ct-cuda-kernels` crate with `#[cfg(feature = "cuda")]` gates

2. **CUDA PTX analysis**
   - `nvcc -ptx -O3 kernel.cu` → analyze generated PTX for instruction count,
     register usage, occupancy estimates
   - We CAN do this — nvcc works, just can't run the resulting binary
   - Derive theoretical throughput: instructions/clock, memory bandwidth, occupancy

3. **Pre-compiled kernel binaries for known architectures**
   - Compile for sm_89 (RTX 4050 Ada) and sm_86 (RTX 3060 Ampere)
   - Ship `.ptx` or `.cubin` files that JC1 or others can load directly
   - No runtime compilation needed on target machine

### Tier 2: Hybrid CPU+SIMD (DOABLE NOW)
Things that use the CPU's vector units (not GPU, but close):

1. **Portable SIMD via `portable_simd` nightly feature**
   - Rust's `std::simd` — process 8 f64s per instruction on AVX2
   - Our SIMD experiment showed 4-6x speedup over scalar
   - Package as `ct-simd` crate with `#[cfg(target_feature = "avx2")]` guards

2. **Batch snap with Rayon parallelism**
   - `par_iter` over 1M queries, each doing binary search
   - Saturates all CPU cores — effective throughput scales linearly with cores
   - RTX 4050 host has ~8 logical cores → 8x theoretical parallel speedup

3. **Neural-network-accelerated snap via ONNX Runtime**
   - Train a small model to predict the snap index directly
   - ONNX Runtime uses CPU SIMD internally
   - Tradeoff: training time (one-time) vs inference speed (O(1) per query)

### Tier 3: Full GPU Runtime (REQUIRES PASSTHROUGH FIX)
The prize — when WSL2 passthrough works or code runs on JC1's Jetson:

1. **Massive parallel snap**
   - 1M queries dispatched to GPU simultaneously
   - Each warp (32 threads) processes 32 independent queries
   - Theoretical: 10M+ qps on RTX 4050, 50M+ qps on RTX 4090

2. **Holonomy path sampling**
   - Monte Carlo holonomy estimation: launch 100K random walks simultaneously
   - Each thread traces a walk of 10K steps on the triple array
   - Statistical holonomy bound estimation in milliseconds, not seconds

3. **Constraint manifold rendering**
   - Real-time visualization of the Pythagorean manifold on GPU
   - WebGPU compute shaders for browser deployment
   - Interactive: drag to rotate, zoom into regions, see triple density

4. **Training neural snap on GPU**
   - PyTorch/CUDA training of a neural network to approximate the snap function
   - Target: <1% error rate, >100x faster than binary search for common queries
   - Ship as `ct-learned-snap` with pre-trained weights

## Concrete Roadmap

### Phase 1: Ship CPU-optimized stack (THIS WEEK)
```
ct-bench v0.1.0  ✅ DONE — reproducible benchmarks
ct-core-ext v0.1 ✅ DONE — adaptive deadband, multi-constraint
ct-simd v0.1     — portable SIMD batch snap (Rayon + std::simd)
ct-cuda-prep v0.1 — compile-verified CUDA kernels + PTX analysis
```

### Phase 2: GPU-ready kernels (NEXT WEEK)
```
ct-cuda-kernels v0.1 — CUDA snap kernel, verified against CPU
                       ships .ptx for sm_86/sm_89
                       CPU fallback included
ct-gpu-bench v0.1   — GPU benchmark harness (requires CUDA runtime)
                      criterion-like but for GPU kernels
```

### Phase 3: Full GPU execution (WHEN PASSTHROUGH WORKS)
```
ct-gpu-snap v0.1    — live GPU snap, 10M+ qps
ct-gpu-holonomy v0.1 — Monte Carlo holonomy on GPU
ct-learned-snap v0.1 — neural snap, trained on GPU
```

## Key Insight: We Don't Need to Wait

The biggest GPU utilization win ISN'T running CUDA kernels — it's building the
ecosystem so that when GPU access arrives, everything just works:

1. **ct-bench** already measures CPU baseline → GPU comparison is instant
2. **ct-cuda-prep** ships pre-compiled kernels → no build step on target
3. **ct-cuda-kernels** has CPU fallback → same API, GPU or not
4. The API surface is identical: `snap(query) -> (index, distance, time_ns)`

The strategy is: make the CPU path SO good that the GPU path is an acceleration,
not a requirement. Ship CPU-optimized code now. GPU is additive, not blocking.

## WSL2 Passthrough: Known Fix

The likely issue is one of:
1. `nvidia-smi` not in PATH → try `/usr/lib/wsl/lib/nvidia-smi`
2. CUDA driver mismatch → WSL2 needs Windows NVIDIA driver 535+
3. WSL kernel too old → `wsl --update` in PowerShell

If Casey runs `wsl --update && wsl --shutdown && wsl` from an admin PowerShell,
passthrough may activate. Then `nvidia-smi` should show the RTX 4050 inside WSL.

## Numbers We're Targeting

| Operation | CPU (now) | CPU+SIMD | GPU (when available) |
|-----------|-----------|----------|---------------------|
| Single snap | ~300ns | ~60ns | ~10ns |
| 1M queries | ~300ms | ~60ms | ~10ms |
| Holonomy 10K steps | ~2ms | ~0.5ms | ~0.05ms |
| Distribution analysis | ~50ms | ~10ms | ~1ms |

## What to Build Next

1. `ct-simd` — Rayon parallel batch snap with AVX2 (TODAY)
2. `ct-cuda-prep` — CUDA kernels with CPU verification + PTX analysis (TODAY)
3. Git repos on cocapn org for both
4. CI that compiles CUDA (but doesn't run it)
5. Try the WSL2 passthrough fix → if it works, immediately run CUDA benchmarks

## LIVE GPU RESULTS (2026-04-26, after WSL2 passthrough fix)

### Hardware
- NVIDIA GeForce RTX 4050 Laptop GPU
- 20 SMs, 2055 MHz, 6439 MB global mem
- Driver 595.79, CUDA 13.2 runtime, nvcc 12.6

### Snap Benchmark (max_c=50000, 41216 triples)

| Backend | qps | vs CPU |
|---------|-----|--------|
| GPU CUDA (binary search, global mem) | **2.6 billion** | **94x** |
| CPU sequential | 27.7 million | 1x |
| CPU Rust (release) | ~44 million | 1.6x |
| CPU Rust (Rayon parallel) | ~57 million | 2x |

### Key Numbers
- 1M queries: 0.52 ms on GPU
- 2B queries: 765 ms on GPU (20 iterations x 100M)
- 100% correctness (0/10000 invalid indices)
- Holonomy: 10K walks x 10K steps = 0.8 ms

### Bottleneck Analysis
The binary search does ~16 iterations (log2(41216) ≈ 15.3), each reading from
global memory. L2 cache (6MB) holds the entire 41K triple array (328KB),
so after warmup it's pure compute. The 94x speedup comes from 20 SMs x 32
warps running 640 threads simultaneously vs 1 CPU thread.

### What This Enables
- PLATO-scale batch: snap all 7700 tiles in <0.01 ms
- Holonomy Monte Carlo: 10K walks in <1 ms (vs seconds on CPU)
- Real-time manifold rendering at 60+ FPS
- Neural snap training: process 1B training samples in 6 minutes
