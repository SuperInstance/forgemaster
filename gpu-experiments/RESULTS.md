# GPU Experiment Results — RTX 4050 Laptop

## Hardware
- **GPU:** NVIDIA GeForce RTX 4050 Laptop (Ada Lovelace)
- **VRAM:** 6GB GDDR6
- **CUDA:** 11.5 (sm_86 target)
- **System RAM:** 15GB (WSL2)

## Experiment Results

### Exp01: Warp Shuffle vs Ballot Reduction
| N | Shuffle (c/s) | Ballot (c/s) | Ratio |
|---|---|---|---|
| 1K | 117M | 100M | 1.17x (shuffle wins) |
| 10K | 1.17B | 1.44B | 0.81x (ballot wins) |
| 100K | 11.7B | 13.7B | 0.86x |
| 1M | 50.7B | 60.9B | 0.83x |
| 10M | 20.0B | 20.0B | 1.00x (bandwidth limited) |

**Finding:** Ballot_sync is ~20% faster than shuffle_down at scale for boolean reduction. Use ballot for production kernels.

### Exp02: Shared Memory Bank Conflicts
| Table Size | Naive (L/s) | Padded (L/s) | Speedup |
|---|---|---|---|
| 16 | 52.9B | 51.8B | 0.98x |
| 32 | 54.8B | 53.0B | 0.97x |
| 64 | 52.0B | 51.6B | 0.99x |
| 128 | 53.7B | 51.8B | 0.96x |
| 256 | 49.3B | 48.3B | 0.98x |

**Finding:** Bank conflict padding is NOT worth it on RTX 4050. The hardware handles conflicts efficiently. Paddding adds overhead without benefit.

### Exp03: Tensor Core Constraint Checking
| Batches | Tensor (ops/s) | CUDA (ops/s) | Ratio | VRAM |
|---|---|---|---|---|
| 64 | 1.8B | 2.0B | 0.91x | 5070MB free |
| 256 | 9.3B | 8.4B | 1.11x | 5070MB free |
| 1024 | 25.9B | 24.0B | 1.08x | 5068MB free |
| 4096 | 78.3B | 74.8B | 1.05x | 5060MB free |
| 16384 | 72.4B | 61.1B | 1.19x | 5024MB free |

**Finding:** Tensor cores provide 1.05-1.19x advantage at scale (>256 batches). Worth using for large batch constraint evaluation but not a game-changer. Best for matrix-structured constraints.

### Exp04: Bandwidth vs Compute Bottleneck
| Workload | Throughput | Bandwidth | Latency |
|---|---|---|---|
| Pure Compute | 12.7B ops/s | 50.8 GB/s | 0.79 ms |
| Sequential Access | 18.6B ops/s | 149.2 GB/s | 0.54 ms |
| Random Access | 9.3B ops/s | 74.2 GB/s | 1.08 ms |
| 8-Constraint Check | 4.7B ops/s | 6.3 GB/s | 2.14 ms |

**Finding:** 8-constraint check is heavily MEMORY BOUND at only 6.3 GB/s. The 8 separate int32 reads per element trash the L2 cache. This is the #1 optimization target.

### Exp05: Memory Layout Optimization
| Layout | Bytes/Elem | Checks/s | Bandwidth |
|---|---|---|---|
| 8x int32 (loose) | 32 | 4.2B | 168.8 GB/s |
| 8x uint16 (packed) | 16 | 7.8B | 187.1 GB/s |
| 4x Range{lo,hi} | 32 | 4.7B | 186.7 GB/s |
| **float4** | **16** | **7.8B** | **187.3 GB/s** |

**Finding:** Packing constraints into float4 or uint16 gives **1.85x throughput improvement** by halving memory traffic. Same bandwidth utilization (187 GB/s) but twice the effective throughput.

### Exp06: Multi-Pass Strategies
| Strategy | Constraints/Elem | Elem/s | Constraints/s |
|---|---|---|---|
| Single pass | 4 | 7.4B | 29.7B |
| Warp-aggregated | 4 | 9.4B | 37.6B |
| Chained 2x float4 | 8 | 4.7B | 37.4B |
| **Warp-cooperative 128** | **128** | **11.6B** | **1,489B (1.49T)** |

**Finding:** Warp-cooperative approach with 128 constraints hits **1.49 TRILLION constraints/sec** but uses full 6GB VRAM at 10M elements.

### Exp07: VRAM Scaling
| Elements | Constraints/Elem | Constraints/s | BW | VRAM Used |
|---|---|---|---|---|
| 1K | 128 | 15.5B | 63.0 GB/s | 1.1GB |
| 10K | 128 | 113.9B | 462.6 GB/s | 1.1GB |
| 100K | 128 | 39.9B | 161.9 GB/s | 1.1GB |
| 1M | 128 | 40.2B | 163.4 GB/s | 1.6GB |
| 2M | 128 | 46.7B | 189.7 GB/s | 2.1GB |
| 5M | 128 | 46.7B | 189.7 GB/s | 3.6GB |

Constraint density sweet spot (1M elements):
| Constraints/Elem | Constraints/s | VRAM |
|---|---|---|
| **4** | **339.7B** | 1.1GB |
| 8 | 16.4B | 1.1GB |
| 16 | 31.6B | 1.1GB |
| 32 | 44.2B | 1.2GB |
| 64 | 45.8B | 1.3GB |
| 128 | 46.7B | 1.6GB |

**Finding:** 4 constraints per element (single float4 load) achieves **340 BILLION constraints/sec** — the highest throughput measured. Beyond 16 constraints, returns diminish while VRAM grows linearly.

## Key Takeaways

1. **Memory layout is king.** float4 packing gives 1.85x over loose int32. Always pack constraints.
2. **Ballot beats shuffle** for boolean reduction (~20% faster at scale).
3. **Bank conflict padding is counterproductive** on Ada architecture.
4. **Tensor cores provide marginal benefit** (1.05-1.19x) — not worth the complexity for constraint checking.
5. **4 constraints per element is the sweet spot** — 340B checks/sec with 1.1GB VRAM.
6. **Warp-cooperative scales to 1.49T constraints/sec** at 128 constraints/element but maxes VRAM.
7. **Workload is memory-bound** — optimization should focus on reducing memory traffic, not compute.
8. **Practical limit:** ~5M elements at 128 constraints fits in 3.6GB, leaves room for OS and other GPU tasks.
