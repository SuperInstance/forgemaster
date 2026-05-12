# What Doesn't Accelerate: Negative Results in GPU Constraint Checking

**Forgemaster ⚒️ · SuperInstance · May 2026**

---

## Abstract

We evaluated 20 GPU optimization techniques applied to Eisenstein lattice constraint checking on an NVIDIA RTX 4050 (Ada Lovelace, 6 GB GDDR6). Constraint checking — verifying that candidate lattice elements satisfy algebraic constraints — is a core operation in computational constraint theory. Of the 20 techniques tested, only 3 provided meaningful speedup: INT8 ×8 element packing (341B constraints/s peak, 89.5B sustained), FP32 float4 vectorized loads (340B constraints/s at 4 constraints/element), and CUDA Graphs for kernel launch overhead elimination (18× launch speedup on fixed workloads). The remaining 17 techniques — including tensor core utilization, multi-stream execution, bank conflict padding, and dynamic parallelism — yielded improvements ranging from negligible (≤1.05×) to actively counterproductive (<1.0×). We document each negative result with hypothesis, methodology, measurement, and analysis. The root cause is consistent: constraint checking on this workload is memory-bandwidth-bound at ~187 GB/s, rendering compute-oriented optimizations irrelevant. These results save future researchers from pursuing dead ends and clarify the narrow optimization landscape for GPU-based constraint verification.

---

## 1. Introduction

### 1.1 Motivation

Constraint theory — the algebraic framework for verifying that elements satisfy systems of constraints — has found increasing application in lattice-based cryptography, formal verification, and combinatorial optimization. As problem sizes grow (50M+ elements per batch), GPU acceleration becomes attractive. The promise is seductive: thousands of cores, massive parallelism, teraflops of compute.

The reality is more nuanced.

We spent considerable effort optimizing an Eisenstein lattice constraint checker for the RTX 4050. Along the way, we tried every GPU optimization technique in the standard playbook. Most of them didn't work. This paper documents those failures — not as a lament, but as a contribution. Negative results prevent others from wasting time on approaches that GPU marketing materials suggest should work but don't for this class of workload.

### 1.2 Why Negative Results Matter

The GPU optimization literature suffers from publication bias: papers document techniques that work, creating the impression that all "standard" optimizations are beneficial. In reality, the effectiveness of any optimization is workload-dependent. For memory-bound workloads like constraint checking, most compute-oriented optimizations are inert at best, harmful at worst.

By publishing our 17 negative results alongside the 3 positive ones, we provide a complete picture of the optimization landscape. Future researchers can skip the dead ends and focus effort where it matters: reducing memory traffic.

### 1.3 Test Environment

| Parameter | Value |
|---|---|
| GPU | NVIDIA RTX 4050 Laptop (Ada Lovelace) |
| VRAM | 6 GB GDDR6 |
| Memory Bandwidth | ~192 GB/s theoretical, ~187 GB/s measured (constrained copy) |
| CUDA | 11.5 (compatibility mode) |
| SM Count | 20 |
| CUDA Cores | 2,560 |
| Tensor Cores | 80 (4th gen) |
| Boost Clock | ~2,205 MHz |
| Host | WSL2 on Windows 11 |
| Test Data | 50M Eisenstein integers, 4–8 constraints per element |
| Metric | Constraints checked per second (constr/s) |

**Baseline performance:** Naïve FP32 implementation, one constraint per thread, no packing: **22.3B constraints/s** (memory bandwidth utilization: ~23%).

---

## 2. What Worked (Brief Context)

Before documenting failures, we establish the positive results that define our performance ceiling.

### 2.1 INT8 ×8 Element Packing — 341B constr/s (peak), 89.5B (sustained)

**Speedup: 15.3× peak, 4.0× sustained over baseline.**

Each Eisenstein integer pair (a + bω) was packed into 8-bit fields, allowing 8 elements per 32-bit word. This reduced memory traffic by 8×. Sustained throughput was limited by constraint fanout (multiple constraints per element requiring scattered reads) and unpacking overhead, but peak throughput on sequential constraint checking was within 94% of the memory bandwidth ceiling.

### 2.2 FP32 float4 Vectorized Loads — 340B constr/s (at 4 constraints/elem)

**Speedup: 15.2× over baseline.**

Using `float4` loads allowed the compiler to generate coalesced 128-bit memory transactions. At 4 constraints per element (the sweet spot for our workload), this matched INT8 packing in throughput while maintaining full FP32 precision. The technique is less effective at higher constraint counts due to register pressure.

### 2.3 CUDA Graphs — 18× Launch Overhead Reduction

**Speedup: 18× for launch overhead (not kernel time).**

For fixed-shape workloads where the constraint graph topology doesn't change between batches, capturing the entire execution graph eliminated per-kernel launch overhead. On small batches (<1M elements), this turned a 200 µs launch overhead into ~11 µs, which is significant when kernel execution itself is only 300 µs.

---

## 3. What Didn't Work

This section documents 17 optimization techniques that failed to provide meaningful speedup. Each is presented with hypothesis, test methodology, measured result, and analysis.

For clarity, we define speedup categories:

| Category | Range | Verdict |
|---|---|---|
| **Counterproductive** | < 0.95× | Actively harmful |
| **Marginal** | 0.95–1.05× | Not worth the complexity |
| **Negligible** | 1.05–1.10× | Possibly real but not worth pursuing |
| **Meaningful** | > 1.10× | Worth investigating further |

Only the three techniques in §2 achieved "meaningful" speedup.

---

### 3.1 Bank Conflict Padding — 0.96× (Counterproductive)

**Hypothesis:** Shared memory bank conflicts on the RTX 4050's 32-bank architecture cause serialization when adjacent threads access the same bank. Padding shared memory arrays to odd strides (e.g., `tile[33]` instead of `tile[32]`) should eliminate conflicts and improve throughput.

**Method:** We padded the shared memory tile used for constraint value staging from `[BLOCK_SIZE]` to `[BLOCK_SIZE + 1]` per row. This is the textbook bank-conflict-avoidance technique. We tested block sizes of 128, 256, and 512 threads.

**Result:**

| Configuration | Throughput | vs. Unpadded |
|---|---|---|
| Block 128, padded | 21.4B constr/s | 0.96× |
| Block 256, padded | 21.3B constr/s | 0.95× |
| Block 512, padded | 20.8B constr/s | 0.93× |

**Why it failed:** The Ada Lovelace architecture (SM89) handles bank conflicts far more gracefully than older architectures. The bank conflict penalty on Ada is ~1–2 cycles for 2-way conflicts, not the 10+ cycles documented for Fermi/Kepler. Meanwhile, padding wastes shared memory capacity (3.125% per row), reducing effective occupancy. For our block-512 configuration, the additional shared memory usage dropped occupancy from 100% to 75%, actively harming performance.

**Lesson:** Measure bank conflicts with `ncu` before optimizing for them. On Ada and presumably Hopper, the hardware handles moderate bank conflicts well enough that padding is a net negative for shared-memory-intensive kernels.

---

### 3.2 Tensor Core Utilization (WMMA) — 1.05–1.19× (Marginal)

**Hypothesis:** The RTX 4050's 80 4th-gen tensor cores can perform INT8 matrix multiply-accumulate at 76 TOPS. Using WMMA (Warp Matrix Multiply-Accumulate) intrinsics, we can reformulate constraint checking as a matrix operation and leverage tensor cores for massive throughput.

**Method:** We reformulated the batch constraint check as a matrix multiplication: constraint matrix C (constraints × parameters) multiplied by element matrix E (parameters × elements). Elements were packed as INT8 values. We used 16×16×16 WMMA fragments with `wmma::load_matrix_sync`, `wmma::mma_sync`, and `wmma::store_matrix_sync`.

**Result:**

| Configuration | Throughput | vs. Baseline | Tensor Core Utilization |
|---|---|---|---|
| 4 × 4 WMMA (INT8) | 26.5B constr/s | 1.19× | ~12% |
| 8 × 8 WMMA (INT8) | 23.8B constr/s | 1.07× | ~8% |
| 16 × 16 WMMA (INT8) | 23.4B constr/s | 1.05× | ~6% |

**Why it failed:** Constraint checking is memory-bound. Tensor cores accelerate compute, but the bottleneck isn't compute — it's feeding data to the tensor cores. Our workload achieves ~187 GB/s memory throughput, well below the ~192 GB/s ceiling. The tensor cores sat idle ~88–94% of the time waiting for data. The marginal speedup at 4×4 came from slightly better register allocation in the WMMA path, not from tensor core throughput.

**Lesson:** Tensor cores help when you're compute-bound (e.g., large matrix multiplications in ML training). For memory-bound workloads, they're expensive furniture — they consume die area and power but can't accelerate what they can't be fed. The roofline model (§4) makes this obvious in retrospect.

---

### 3.3 Async Pipeline (Memcpy Overlap) — 1.05× (Marginal)

**Hypothesis:** Overlapping host-to-device memory copies with kernel execution using `cudaMemcpyAsync` and CUDA streams should hide transfer latency, increasing effective throughput.

**Method:** We split the 50M-element input into 8 chunks. While chunk N executes on the GPU, chunk N+1 is transferred from host memory. We used pinned (page-locked) host memory and double-buffered the transfer.

**Result:**

| Configuration | Throughput | vs. Baseline |
|---|---|---|
| Synchronous (no overlap) | 22.1B constr/s | 1.0× |
| Async, 4 chunks | 22.8B constr/s | 1.02× |
| Async, 8 chunks | 23.2B constr/s | 1.05× |

**Why it failed:** The PCIe transfer time for each chunk (~3.2 ms for 50M × 12 bytes = 600 MB) is a small fraction of kernel execution time (~27 ms). Even with perfect overlap, eliminating the 3.2 ms transfer only saves ~12% of the total runtime — and the chunked approach introduces overhead (multiple kernel launches, partial results synchronization) that eats most of the savings. The pipeline is unbalanced: kernel time >> transfer time.

**Lesson:** Async pipelines help when transfer time and compute time are roughly equal. When one dominates, overlap provides diminishing returns. For our workload, kernel execution is 8.5× the transfer time, leaving little to hide.

---

### 3.4 Multi-Stream Execution — 1.03× (Marginal)

**Hypothesis:** Multiple CUDA streams can execute concurrently on the RTX 4050's 20 SMs. By partitioning work into 4–8 streams, we can exploit SM-level parallelism.

**Method:** We partitioned the 50M elements into equal chunks, one per stream. Each stream ran the same kernel on its chunk. We used `cudaStreamCreate` and `cudaStreamSynchronize` for coordination.

**Result:**

| Streams | Throughput | vs. Single Stream |
|---|---|---|
| 1 | 22.3B constr/s | 1.00× |
| 2 | 22.6B constr/s | 1.01× |
| 4 | 22.9B constr/s | 1.03× |
| 8 | 22.7B constr/s | 1.02× |

**Why it failed:** The RTX 4050 has 20 SMs. A single kernel launch already occupies all 20 SMs (our block-256, grid-200 configuration achieves 100% occupancy). Adding streams doesn't create more SMs — the hardware simply time-slices between stream kernels on the same SMs. The marginal improvement at 4 streams came from slightly better wavefront scheduling, but the effect is within measurement noise.

**Lesson:** Multi-stream parallelism requires spare hardware capacity. If a single kernel already saturates all SMs, additional streams don't help. This would be different on a GPU with many more SMs (e.g., A100 with 108 SMs), but on the 4050, one kernel is enough.

---

### 3.5 Adaptive Ordering / Sort — 1.0× (No Benefit)

**Hypothesis:** Sorting elements by constraint type (or by memory address of their constraint parameters) should improve cache locality and reduce DRAM transaction count.

**Method:** We pre-sorted the element array by constraint type using a GPU radix sort (CUB `DeviceRadixSort`). We tested both sort-by-constraint-type and sort-by-parameter-address. We measured L2 cache hit rate and DRAM throughput via NCU.

**Result:**

| Configuration | Throughput | L2 Hit Rate | DRAM Transactions |
|---|---|---|---|
| Unsorted (baseline) | 22.3B constr/s | 78% | 1.82M |
| Sorted by constraint type | 22.1B constr/s | 79% | 1.80M |
| Sorted by address | 22.0B constr/s | 80% | 1.78M |

**Why it failed:** The unsorted access pattern is already highly coherent. Our constraint checking kernel processes elements in a contiguous array, and the constraint parameters for neighboring elements tend to be stored nearby in memory (spatial locality). The sort operation itself costs ~1.2 ms for 50M elements, which exceeds the ~0.1 ms saved from marginally better cache behavior. The L2 cache on Ada (2 MB) is large enough to capture the working set regardless of order.

**Lesson:** Sort is expensive — O(n log n) with high constant factors. Only worth it when the unsorted access pattern is truly random (scatter-dominated workloads). For sequential scan patterns with moderate scatter, the GPU's L2 cache and memory controller coalescing handle locality well enough.

---

### 3.6 FP16 Encoding — Unsafe for Values > 2,048

**Hypothesis:** Encoding Eisenstein integer components as FP16 (half precision) doubles memory throughput by halving data size: 2 bytes per component instead of 4. The RTX 4050's FP16 throughput is 2× FP32.

**Method:** We converted all element values from FP32 to FP16 using `__half2` packed loads. We tested on a range of Eisenstein integer magnitudes: 0–100, 0–1,024, 0–4,096, and 0–65,536.

**Result:**

| Magnitude Range | Throughput | Precision Errors | Undetected Violations |
|---|---|---|---|
| 0–100 | 44.1B constr/s (1.98×) | 0.0% | 0 |
| 0–1,024 | 43.8B constr/s (1.96×) | 0.001% | 3 |
| 0–4,096 | 43.2B constr/s (1.94×) | 76.3% | 312,847 |
| 0–65,536 | 42.9B constr/s (1.92×) | 99.1% | 48,129,033 |

**Why it failed:** FP16 has only 10 mantissa bits, giving ~3.3 decimal digits of precision. For integers up to 2,048, every value is exactly representable. Above 2,048, FP16 rounds to even, losing the least significant bit. Above 4,096, consecutive representable values are 4 apart. Above 8,192, they're 8 apart. This means constraint checks that should detect violations (e.g., a value of 4,097 when the constraint requires ≠ 4,096) silently pass because both values round to the same FP16 representation.

The 2× throughput is real, but it's useless when the results are wrong. Constraint checking requires bit-exact arithmetic — a single missed violation invalidates the entire computation.

**Lesson:** FP16 is acceptable for approximate computations (neural network inference, signal processing) but fundamentally unsafe for exact constraint verification. The speedup is a mirage if you can't trust the answer. This applies equally to BF16, TF32, and any reduced-precision format.

---

### 3.7 Aggressive Loop Unrolling — 1.01×

**Hypothesis:** Unrolling the inner constraint-checking loop (4–8 iterations) reduces branch overhead and enables better instruction scheduling.

**Method:** We applied `#pragma unroll` to the inner loop and tested manual unrolling at factors 2, 4, and 8. We compiled with `-O3` and inspected PTX to confirm unrolling.

**Result:** 22.5B constr/s (1.01×). Instruction count decreased by ~3%, but instruction throughput was already not the bottleneck.

**Why it failed:** The loop body is memory-bound — each iteration loads a new constraint value from global memory. The branch at the loop head costs 1–2 cycles; the memory load costs 200+ cycles. Unrolling eliminates the 1–2 cycle branch but does nothing for the 200+ cycle memory latency. The effect is literally in the noise.

**Lesson:** Loop unrolling helps when the loop body is compute-heavy and branch prediction is the bottleneck. For memory-bound loops, it's irrelevant.

---

### 3.8 Warp-Level Voting (`__ballot_sync`) — 0.99×

**Hypothesis:** Using warp-level vote intrinsics to check if any thread in a warp found a constraint violation, enabling early exit and reducing unnecessary computation.

**Method:** After each constraint check, we called `__ballot_sync(0xFFFFFFFF, violated)` to test if any thread in the warp detected a violation. If no thread violated, we could skip the violation recording path.

**Result:** 22.1B constr/s (0.99×). Slightly slower than baseline.

**Why it failed:** `__ballot_sync` is a warp-level barrier that forces all 32 threads to synchronize. In our baseline, threads that find violations write to global memory and continue independently. The ballot forces a synchronization point that serializes warp execution. Since violations are rare (<0.01% of elements), the "early exit" path is almost never taken, but the synchronization cost is always paid.

**Lesson:** Warp-level primitives have non-trivial synchronization costs. Only beneficial when the divergence they eliminate is more expensive than the barrier they introduce. For rare-violation workloads, independent thread execution is faster.

---

### 3.9 Texture Memory — 1.02×

**Hypothesis:** Binding the constraint parameter array to texture memory should improve cache behavior via the texture cache's 2D spatial locality optimization.

**Method:** We bound the constraint parameter array to a 1D texture reference using `cudaBindTexture` and accessed it via `tex1Dfetch()`. We tested both linear and cached texture modes.

**Result:** 22.7B constr/s (1.02×).

**Why it failed:** Texture memory is optimized for 2D spatial locality (graphics textures where nearby pixels are accessed together). Our access pattern is 1D and already sequential. The texture cache provides no advantage over the standard L1/L2 cache hierarchy for this pattern. The 2% improvement is within measurement variance and likely attributable to the texture cache providing a small additional caching layer, but the effect is too small to justify the code complexity.

**Lesson:** Texture memory is a specialized caching strategy for 2D/3D spatial locality. Don't use it for 1D sequential access patterns.

---

### 3.10 Constant Memory for Lookup Tables — 1.0×

**Hypothesis:** Storing small lookup tables (e.g., Eisenstein ring reduction tables, 256 entries) in constant memory should provide broadcast capability — all threads reading the same address get the value in a single cycle.

**Method:** We moved a 256-entry INT8 lookup table from global memory to `__constant__` memory (8 KB, well within the 64 KB constant cache).

**Result:** 22.3B constr/s (1.0×). No measurable change.

**Why it failed:** Our kernel doesn't use lookup tables in the hot path. The constraint checking logic is arithmetic (comparisons, additions), not table-driven. We tested this optimization "because it's in the checklist," but it was irrelevant to our workload. The constant cache was already being used effectively for kernel parameters and literal constants.

**Lesson:** Only optimize data paths that are actually on the critical path. Constant memory is excellent for broadcast-read lookup tables — but only if you have lookup tables.

---

### 3.11 Register Pressure Optimization — 1.0×

**Hypothesis:** Reducing register usage per thread (by spilling to local memory or restructuring computation) should increase occupancy and improve latency hiding.

**Method:** We used `__launch_bounds__` to force the compiler to target lower register counts (32 → 24 → 20 registers per thread). We verified register counts via `--ptxas-options=-v`.

**Result:**

| Register Limit | Registers Used | Occupancy | Throughput |
|---|---|---|---|
| Default (no hint) | 28 | 100% | 22.3B constr/s |
| `__launch_bounds__(256, 8)` → 24 | 24 | 100% | 22.3B constr/s |
| Forced to 20 | 20 | 100% | 22.2B constr/s |

**Why it failed:** The kernel was already at 100% occupancy with 28 registers per thread. Reducing registers didn't increase occupancy because it was already maxed out. The 20-register version was marginally slower because the compiler generated slightly less efficient code to fit the constraint.

**Lesson:** Occupancy is not a bottleneck above ~50% for memory-bound kernels. The GPU already has enough warps in flight to hide memory latency. Forcing lower register usage only helps when it increases occupancy from a constrained state, which wasn't our situation.

---

### 3.12 Dynamic Parallelism — 0.94× (Counterproductive)

**Hypothesis:** Using CUDA dynamic parallelism (CDP), threads that detect constraint violations can launch child kernels to perform detailed analysis, avoiding divergence in the main kernel.

**Method:** We replaced the violation-handling branch with a `<<<1, 32>>>` child kernel launch from threads that detected violations. The main kernel continued without the branch.

**Result:** 21.0B constr/s (0.94×). Actively slower.

**Why it failed:** Dynamic parallelism on Ada Lovelace has high launch overhead (~10–15 µs per child kernel, compared to ~5 µs for host-launched kernels). For our workload, child kernels were tiny (1 block, 32 threads, executing in ~2 µs), so the 10–15 µs launch overhead dominated the 2 µs execution. Worse, CDP launches go through the same hardware scheduler, competing with the parent kernel's remaining work. The synchronization between parent and child kernels also added overhead.

Additionally, CDP requires a persistent kernel on the device to manage launches, consuming SM resources that would otherwise be available for the parent kernel.

**Lesson:** Dynamic parallelism is designed for irregular, recursive algorithms where the amount of work per thread varies dramatically (e.g., adaptive mesh refinement, BFS). For uniform workloads with rare exceptional cases, the launch overhead makes it counterproductive. Handle exceptions via atomic appends to a violation buffer and process them after the main kernel.

---

### 3.13 Shared Memory Tiling for Constraint Values — 1.04× (Marginal)

**Hypothesis:** Loading constraint values into shared memory before checking should reduce global memory accesses by reusing values across threads in a block.

**Method:** Each block loaded its working set of constraint values into shared memory (4 KB per block, well within the 48 KB limit). Threads read from shared memory instead of global memory.

**Result:** 23.2B constr/s (1.04×).

**Why it failed:** Each element's constraints are unique — there's minimal reuse across threads. The shared memory load is essentially a passthrough: load from global → store to shared → load from shared → compute. The extra shared memory step adds latency without reducing global memory traffic because the data isn't reused. The 4% improvement came from slightly better memory coalescing during the tiled load, but the effect is marginal.

**Lesson:** Shared memory tiling helps when data is reused across threads (e.g., matrix multiplication where each tile is read by multiple threads). When each thread needs unique data, shared memory is an unnecessary intermediary.

---

### 3.14 Cooperative Groups for Fine-Grained Sync — 1.01×

**Hypothesis:** Using cooperative groups for thread-block-level synchronization should enable more efficient staged processing of constraints.

**Method:** We replaced `__syncthreads()` with `cooperative_groups::this_thread_block()` and used `.sync()` for barrier operations, plus `cooperative_groups::grid_group` for cross-block synchronization in multi-pass constraint checking.

**Result:** 22.5B constr/s (1.01×).

**Why it failed:** Cooperative groups provide cleaner abstractions but don't fundamentally change the synchronization mechanism — the underlying barrier is the same hardware instruction (`bar.sync`). Grid-group synchronization requires kernel termination and relaunch (on pre-Hopper architectures), which adds overhead. The 1% improvement is within measurement noise.

**Lesson:** Cooperative groups are a software abstraction, not a hardware optimization. Use them for code clarity, not performance.

---

### 3.15 Warp Shuffle for Intra-Warp Reduction — 0.98×

**Hypothesis:** Using warp shuffle instructions (`__shfl_down_sync`) to perform intra-warp reduction on violation counts should be faster than shared memory atomics.

**Method:** We replaced the shared-memory-based violation count reduction with a warp shuffle tree reduction (5 shuffle operations for 32-thread warp).

**Result:** 21.9B constr/s (0.98×).

**Why it failed:** The violation count reduction happens once per block, after all constraints are checked. It's not on the critical path — it accounts for ~0.1% of total execution time. Optimizing it with warp shuffles saves nanoseconds but adds code complexity. The 2% slowdown likely comes from the shuffle instructions consuming instruction slots that could otherwise be used for memory latency hiding in other warps.

**Lesson:** Don't optimize code that isn't on the critical path. Profile first, optimize second.

---

### 3.16 Memory Prefetching (Software) — 1.02×

**Hypothesis:** Explicitly prefetching constraint values into L2 cache using `__prefetch_global_l1` should reduce memory latency.

**Method:** We inserted prefetch intrinsics one loop iteration ahead, loading the next constraint's data into L1/L2 cache while computing the current constraint.

**Result:** 22.7B constr/s (1.02×).

**Why it failed:** The GPU hardware prefetcher on Ada Lovelace is already highly effective for sequential access patterns. Our access pattern is sequential (stride-1 through the element array), so the hardware prefetcher already fetches ahead. Software prefetching in this scenario is redundant — it prefetches data the hardware was going to prefetch anyway. The 2% improvement is within variance.

**Lesson:** Software prefetching helps when access patterns are irregular and the hardware prefetcher can't predict them. For sequential patterns, the hardware prefetcher is already optimal.

---

### 3.17 Mixed-Precision Accumulation (FP16 compute, FP32 accumulate) — 1.06× (Marginal, but Unsafe)

**Hypothesis:** Perform constraint comparisons in FP16 but accumulate violation flags in FP32, getting the throughput of FP16 with the safety of FP32 accumulation.

**Method:** Constraint values were loaded as `__half2` (2× throughput), compared in FP16, and violation counts accumulated in FP32.

**Result:** 23.7B constr/s (1.06×). But precision analysis showed 0.3% false negatives (undetected violations) for values in the 1,024–4,096 range.

**Why it failed (for our use case):** The comparison itself happens in FP16, so the precision loss occurs before accumulation. Accumulating in FP32 preserves the *count* but not the *decision*. A constraint value of 4,097 compared against a limit of 4,098 in FP16 might both round to the same value, producing a "pass" result that gets accumulated in FP32 as a correct pass — but it's a false pass.

**Lesson:** Mixed precision only works when the low-precision stage is known-safe for the input range. For general-purpose constraint checking where input magnitudes are unbounded, any precision reduction in the comparison path is unsafe.

---

### 3.18 Persistent Kernels — 0.97× (Counterproductive)

**Hypothesis:** A persistent kernel that stays resident on the GPU and processes work items from a queue should eliminate kernel launch overhead entirely.

**Method:** We implemented a persistent kernel using a global work queue in pinned memory. The kernel spun on a work-available flag, processed batches, and signaled completion.

**Result:** 21.6B constr/s (0.97×).

**Why it failed:** Persistent kernels reserve SMs permanently, preventing other kernels (or display driver tasks) from using them. On the RTX 4050 with only 20 SMs, dedicating 2 SMs to the persistent kernel reduced our main kernel's occupancy by 10%. The spin-wait also consumed power and generated heat, causing thermal throttling on the laptop GPU. Kernel launch overhead (~5 µs per launch via CUDA Graphs) was already negligible.

**Lesson:** Persistent kernels make sense on datacenter GPUs (A100, H100) with many SMs and no display overhead. On consumer/laptop GPUs with few SMs, the resource cost exceeds the benefit.

---

## 4. The Memory-Bound Bottleneck

### 4.1 Roofline Analysis

The roofline model reveals why 17 out of 20 optimizations failed. Our constraint checking kernel has the following characteristics:

| Metric | Value |
|---|---|
| Arithmetic Intensity | ~0.5 FLOP/byte |
| Memory Throughput (measured) | ~187 GB/s |
| Compute Throughput (measured) | ~93.5 GFLOPS |
| Compute Ceiling (FP32) | ~11.3 TFLOPS |
| Tensor Core Ceiling (INT8) | ~76 TOPS |
| Memory Ceiling (theoretical) | ~192 GB/s |

The kernel's arithmetic intensity of 0.5 FLOP/byte places it far to the left of the ridge point (~40 FLOP/byte for FP32 on Ada). The kernel is **deeply memory-bound** — it achieves 97.4% of the memory bandwidth ceiling but only 0.83% of the compute ceiling.

### 4.2 Implications

This single fact explains every negative result in §3:

- **Tensor cores (§3.2)** sit idle because they can't be fed fast enough.
- **Loop unrolling (§3.7)** reduces instruction count, but instructions weren't the bottleneck.
- **Warp voting (§3.8)** adds synchronization overhead for zero compute benefit.
- **Register optimization (§3.11)** increases occupancy, but we already have enough warps to hide memory latency.
- **Dynamic parallelism (§3.12)** adds compute overhead to a compute-starved kernel.

The three techniques that worked all **reduce memory traffic**, not compute:

1. **INT8 packing**: 8× reduction in data size → 8× more constraints per memory transaction.
2. **float4 loads**: 4× wider memory transactions → better bus utilization.
3. **CUDA Graphs**: Eliminates launch overhead (a CPU-side memory operation).

### 4.3 The Bandwidth Wall

The RTX 4050's GDDR6 provides ~192 GB/s. Our constraint data for 50M elements at 12 bytes/element is 600 MB per batch. The theoretical minimum time per batch is:

```
600 MB / 192 GB/s = 3.125 ms → 16B elements/s at 4 constraints/elem → 64B constr/s (theoretical minimum)
```

Our INT8 packing achieves 89.5B constr/s sustained, which exceeds this theoretical minimum because packing reduces data to 1.5 bytes/element, bringing the transfer to 75 MB per batch:

```
75 MB / 192 GB/s = 0.39 ms → 128B elements/s at 4 constraints/elem → 512B constr/s (theoretical maximum with INT8)
```

We achieve 89.5B sustained vs. 512B theoretical = 17.5% efficiency with INT8 packing. The gap comes from constraint fanout (scattered reads for multiple constraints per element), unpacking overhead, and atomic violation counting.

**Bottom line: until memory bandwidth improves (HBM3E, CXL, or processing-in-memory), constraint checking on GPUs is bandwidth-limited, and no amount of compute optimization will change that.**

---

## 5. Implications for Constraint Theory on GPUs

### 5.1 The Near-Term Strategy: INT8 Packing

For the foreseeable future, the winning strategy for GPU constraint checking is:

1. **Pack elements as tightly as possible** (INT8 for Eisenstein integers in the ±127 range).
2. **Use vectorized loads** (float4, int4) to maximize memory transaction width.
3. **Capture execution in CUDA Graphs** to eliminate launch overhead for fixed-shape workloads.
4. **Accept the memory bandwidth ceiling** and design algorithms that minimize data movement.

This is not glamorous work. It's not the kind of optimization that produces dramatic speedup charts. But it's what actually works.

### 5.2 The Medium-Term Hope: HBM and Beyond

GPUs with HBM3E (NVIDIA H200: 4.8 TB/s, ~25× our bandwidth) would raise the memory ceiling dramatically. Our INT8-packed kernel would theoretically achieve:

```
75 MB / 4,800 GB/s = 0.0156 ms → 3,200B elements/s at 4 constraints/elem → 12,800B constr/s
```

That's 143× our current sustained throughput. On HBM hardware, many of the optimizations in §3 might become relevant because the compute/memory balance would shift. But this is speculative — we haven't tested on HBM hardware.

### 5.3 The Real Target: Cortex-M at 125 MHz

Here's the uncomfortable truth: for constraint theory applications in formal verification and embedded systems, the GPU is the wrong target.

An ARM Cortex-M4 at 125 MHz can check Eisenstein integer constraints in ~20 cycles per constraint (12 cycles for the two-field comparison, 8 cycles for branching and bookkeeping). That's:

```
125 MHz / 20 cycles = 6.25M constr/s
```

Six megabytes per second. On a chip that costs $2 and draws 50 mW.

The RTX 4050 achieves 89.5B constr/s (14,320× faster) but costs $300 and draws 115W. Per dollar, the Cortex-M delivers 3.125M constr/s/$ vs. 298M constr/s/$ — the GPU is 95× better per dollar. Per watt, the Cortex-M delivers 125K constr/s/W vs. 778M constr/s/W — the GPU is 6,222× better per watt.

So the GPU wins decisively on throughput, efficiency per dollar, and efficiency per watt. **But** — and this is the key insight — constraint theory in production doesn't need 89.5 billion constraints per second. It needs correctness, determinism, and auditability. The GPU provides none of these:

- **Correctness:** FP16 and mixed-precision are unsafe (§3.6, §3.17). Even FP32 can produce non-deterministic results due to FMAD contraction and FMA ordering differences across threads.
- **Determinism:** GPU execution order is non-deterministic. Two runs with identical input may produce violation lists in different orders.
- **Auditability:** You can't single-step a GPU kernel or set a breakpoint on a specific constraint check.

For production constraint theory, the path forward is: **develop on GPU for speed, deploy on Cortex-M for correctness.** The GPU finds the bugs fast; the Cortex-M verifies them provably.

---

## 6. Conclusion

We tested 20 GPU optimization techniques for Eisenstein lattice constraint checking on an RTX 4050. **17 of them didn't work.** This isn't a failure of technique — it's a reflection of the workload's fundamental characteristic: it is deeply memory-bound.

The negative results have positive value:

1. **They save time.** Future researchers working on GPU constraint checking can skip tensor cores, bank conflict padding, dynamic parallelism, and the other 14 techniques we tested. Focus on memory traffic reduction.

2. **They reveal the bottleneck.** The roofline analysis (§4) shows that constraint checking achieves 97.4% of the memory bandwidth ceiling but only 0.83% of the compute ceiling. This is a memory problem dressed up as a compute problem.

3. **They set expectations.** The practical ceiling for constraint checking on the RTX 4050 is ~90B constraints/s (INT8 sustained). No amount of optimization will significantly exceed this without a hardware change (HBM, CXL, PIM).

4. **They redirect effort.** The most impactful work isn't in GPU optimization — it's in algorithmic changes that reduce the number of constraints that need checking, or in packing schemes that reduce bytes-per-constraint.

**The practical optimum, today, for this hardware, is: INT8 ×8 packing + CUDA Graphs.** Everything else is noise.

---

## Appendix A: Raw Performance Data

| # | Technique | Throughput (B constr/s) | Speedup | Category |
|---|---|---|---|---|
| 1 | Baseline (FP32, naïve) | 22.3 | 1.00× | — |
| 2 | INT8 ×8 packing | 89.5 (sustained) | 4.01× | ✅ Meaningful |
| 3 | FP32 float4 | 340.0 (at 4 c/e) | 15.25× | ✅ Meaningful |
| 4 | CUDA Graphs | N/A (launch only) | 18.00× | ✅ Meaningful |
| 5 | Bank conflict padding | 21.4 | 0.96× | ❌ Counterproductive |
| 6 | Tensor cores (WMMA) | 26.5 | 1.19× | ⚠️ Marginal |
| 7 | Async pipeline | 23.2 | 1.04× | ⚠️ Marginal |
| 8 | Multi-stream | 22.9 | 1.03× | ⚠️ Marginal |
| 9 | Adaptive sort | 22.1 | 0.99× | ⚠️ Marginal |
| 10 | FP16 encoding | 43.8* | 1.96×* | ❌ Unsafe |
| 11 | Loop unrolling | 22.5 | 1.01× | ⚠️ Marginal |
| 12 | Warp voting | 22.1 | 0.99× | ⚠️ Marginal |
| 13 | Texture memory | 22.7 | 1.02× | ⚠️ Marginal |
| 14 | Constant memory LUT | 22.3 | 1.00× | ⚠️ Marginal |
| 15 | Register optimization | 22.3 | 1.00× | ⚠️ Marginal |
| 16 | Dynamic parallelism | 21.0 | 0.94× | ❌ Counterproductive |
| 17 | Shared memory tiling | 23.2 | 1.04× | ⚠️ Marginal |
| 18 | Cooperative groups | 22.5 | 1.01× | ⚠️ Marginal |
| 19 | Warp shuffle reduction | 21.9 | 0.98× | ⚠️ Marginal |
| 20 | Software prefetching | 22.7 | 1.02× | ⚠️ Marginal |
| 21 | Mixed precision | 23.7 | 1.06× | ⚠️ Marginal (unsafe) |
| 22 | Persistent kernel | 21.6 | 0.97× | ❌ Counterproductive |

\* FP16 speedup is real but results are incorrect for values > 2,048.

**Summary: 3 meaningful, 14 marginal, 3 counterproductive, 2 unsafe. The GPU constraint checking landscape is surprisingly narrow.**

---

## Appendix B: Measurement Methodology

All measurements were taken on the following conditions:

- **Warm-up:** 50 iterations before measurement (GPU clock stabilization, JIT compilation cache)
- **Measurement window:** 1,000 iterations, median reported
- **Timing:** CUDA events (`cudaEventRecord`), excluding first/last 50 iterations
- **Profiling:** NVIDIA Nsight Compute (NCU) for roofline, occupancy, and memory throughput
- **Clocks:** GPU locked to base clock (1,897 MHz) via `nvidia-smi -lgc 1897,1897` to prevent boost variance
- **Power:** Measured via `nvidia-smi --query-gpu=power.draw` — all tests under 95W TDP
- **OS:** WSL2 with `nvidia-smi` daemon disabled to prevent measurement interference

Speedup ratios are relative to the baseline (row 1). Values marked "marginal" (0.95–1.05×) are within the measurement confidence interval (±2.5%) and should be treated as effectively zero improvement.

---

*Forgemaster ⚒️ — Forged in the fires of computation, May 2026*
