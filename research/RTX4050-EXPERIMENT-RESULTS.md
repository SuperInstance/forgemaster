# RTX 4050 Experiment Results — Oracle1's Handoff

## Experiment 1: Backend Probe
```
✅ cpu:    CPU with AVX-512
✅ cuda:   RTX 4050 Laptop GPU (via PyTorch)
✅ fpga:   yosys 0.9
✅ fortran: GNU Fortran 11.4
❌ ebpf:   No toolchain
❌ webgpu: Not detected
❌ vulkan: No toolchain
❌ coq:    Not installed
```
4/8 backends live. CUDA confirmed working.

## Experiment 2: Task Routing

### "eisenstein integer constraint proof" (T-I-A-L-S)
- **Recommended:** deepseek/deepseek-v4-flash → **CPU backend**
- Confidence: 10% (low — casting-call database may not have enough theorem-proving entries)
- FLUX bytecode: 16 opcodes (MOV, LOAD, EQ, STORE, GTE, CALL, SIG, HALT)
- **Correct routing:** theorem proving doesn't need GPU

### "GPU parallel constraint evaluation" (T-A-L-S-I)
- **Recommended:** deepseek/deepseek-v4-flash → **CUDA backend**
- FLUX bytecode: 16 opcodes (MOV, LOAD, GT, JNZ, EQ, SIG, HALT)
- **Correct routing:** parallel evaluation needs GPU

Note: Both route to deepseek-v4-flash because the model database may be limited.
The backend routing is correct though — CPU for proofs, CUDA for parallel.

## Experiment 3: GPU vs CPU Signature Distance Matrix

### 14×14 matrix (small fleet)
| Backend | Time/trial | Speedup |
|---------|-----------|---------|
| CPU (AVX-512) | 7.5 µs | baseline |
| GPU (RTX 4050) | 32.2 µs | **0.23×** (GPU slower!) |

GPU overhead dominates for small matrices. CPU wins.

### 1000×1000 matrix (large fleet)
| Backend | Time/trial | Speedup |
|---------|-----------|---------|
| CPU (AVX-512) | 36.8 ms | baseline |
| GPU (RTX 4050) | 2.6 ms | **14.3×** |

GPU wins decisively at scale. Crossover: ~200-300 models.

### Implication for Fleet
- Small fleets (<200 devices): CPU-only signature matching is fine
- Large fleets (200+): GPU-accelerated routing via casting-call-gpu
- Insight router should auto-detect fleet size and switch paths

## Bug Found
`cast_gpu.py` line 266 uses `xp.array()` which maps to `torch.array` — 
PyTorch doesn't have `torch.array`, needs `torch.tensor`. 
Will file issue or send patch.

## Summary
- 4/8 backends detected on eileen
- Task routing works (CPU for proofs, CUDA for parallel)
- GPU wins at 14.3× for 1000-model signature matrices
- Small matrix crossover at ~200 models
- fleet-stitch shipped (#20) — manifold projection bridges to casting-call
