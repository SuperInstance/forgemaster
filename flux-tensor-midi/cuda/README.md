# FLUX-Tensor-MIDI — CUDA Implementation

GPU-accelerated implementation for large-scale ensemble simulation. When you have hundreds or thousands of RoomMusicians, CPU-based timing checks and harmony computation become the bottleneck. CUDA parallelizes all the embarrassingly parallel operations.

## Kernels

| Kernel | Input | Output | Use Case |
|--------|-------|--------|----------|
| `check_t_zero_kernel` | N rooms' timing state | N states + deltas + missed ticks | **The killer app** — check all rooms' T-0 simultaneously |
| `eisenstein_rhythmic_snap_kernel` | N interval pairs | N Eisenstein classifications | Batch rhythm analysis |
| `flux_batch_distance_kernel` | N rooms' flux vectors | N×N distance matrix | Pairwise harmony pre-compute |
| `flux_batch_cosine_kernel` | N rooms' flux vectors | N×N cosine matrix | Pairwise similarity |
| `harmony_batch_jaccard_kernel` | N rooms' flux vectors | N×N Jaccard matrix | Active-channel overlap |
| `harmony_batch_connectome_kernel` | N×M listening matrix | N×N alignment matrix | Structural similarity |

## Building

```bash
mkdir build && cd build
cmake .. -DCUDA_TOOLKIT_ROOT_DIR=/usr/local/cuda
make
ctest --output-on-failure
```

### Requirements
- CUDA Toolkit 11.5+
- CMake 3.18+
- sm_75+ GPU (Turing / Ampere / Hopper)

### Targets
- **sm_86** (default): Jetson Orin, RTX 3000 series
- **sm_75**: Jetson Xavier, RTX 2000 series
- Override with `-DCMAKE_CUDA_FLAGS="-arch=sm_XX"`

## Architecture

```
EnsembleGPU
  ├── d_saliences [N×9]     ← FLUX vectors
  ├── d_intervals [N]       ← T-0 intervals
  ├── d_t_last [N]          ← Last observation times
  ├── d_tzero_states [N]    ← Output: ON_TIME/LATE/SILENT/DEAD
  ├── d_tzero_deltas [N]    ← Output: Timing delta
  └── d_harmony_matrix [N×N]← Output: Pairwise harmony
```

One `ensemble_cuda_tick()` call:
1. Batch T-0 check → states + deltas
2. Batch Jaccard → harmony matrix
3. All on GPU, zero host roundtrips

## Performance

For N=1000 rooms:
- **CPU**: ~1000 T-0 checks serially → O(N) per tick
- **GPU**: 1 kernel launch, ~4 blocks of 256 threads → O(N/1024) wall time
- **Harmony**: N²/2 pairs on CPU → N²/1024 on GPU (for N=1000, ~500x speedup)

## Use Cases

- **Jetson Orin (sm_87)**: Real-time 100+ room ensemble
- **RTX 4090 (sm_89)**: Simulation of 10,000+ rooms for research
- **Multi-GPU**: Partition rooms across GPUs for extreme scale

## License

MIT
