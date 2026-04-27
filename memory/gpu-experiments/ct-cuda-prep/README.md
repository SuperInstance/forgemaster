# ct-cuda-prep

GPU-ready CUDA snap kernels — compile-verified, CPU fallback, PTX analysis.

## What's Inside

- `src/kernels/snap.cu` — CUDA binary search snap kernel (sm_89)
- `src/kernels/snap_cpu.c` — CPU reference (identical algorithm)
- `src/lib.rs` — Rust CPU fallback + verification + PTX analysis

## Compile CUDA Kernels

```bash
# PTX (portable) — for JIT loading
nvcc -O3 -arch=sm_89 -ptx src/kernels/snap.cu -o snap.ptx

# Cubin (native) — for RTX 4050 Ada
nvcc -O3 -arch=sm_89 -cubin src/kernels/snap.cu -o snap.cubin
```

## Rust Usage (CPU fallback, no CUDA needed)

```rust
use ct_cuda_prep::{generate_triples, snap_cpu, PtxAnalysis};

let triples = generate_triples(50_000);
let (idx, dist) = snap_cpu(&triples, 1.5);

// Theoretical GPU throughput estimate
let analysis = PtxAnalysis::theoretical_sm89(50_000);
println!("Estimated GPU qps: {:.0}", analysis.estimated_qps(50_000, 24, 2.4));
```

## Key Design

The CUDA kernel is algorithmically identical to the CPU reference.
When GPU access arrives, run both and verify 100% agreement.

## License

MIT
