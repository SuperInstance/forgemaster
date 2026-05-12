# CUDA Optimization Techniques for Real-Time Constraint Checking & Verification

**Technical Research Report — May 2026**
**Target Architecture: Stack-based Constraint VM (FLUX)**

---

## Table of Contents

1. [Cooperative Groups for Synchronized Constraint Evaluation](#1-cooperative-groups)
2. [Warp-Level Primitives for Voting & Reduction](#2-warp-level-primitives)
3. [CUDA Dynamic Parallelism for Recursive Constraint Solving](#3-dynamic-parallelism)
4. [CUDA Graphs for Zero-Overhead Kernel Launch](#4-cuda-graphs)
5. [Tensor Cores for Constraint Matrix Operations](#5-tensor-cores)
6. [Multi-Instance GPU (MIG) for Safety-Critical Partitioning](#6-mig)
7. [Grace Hopper Unified Memory for Zero-Copy Constraint Checking](#7-grace-hopper)
8. [CUDA Streams for Pipelined Constraint Compilation](#8-cuda-streams)
9. [Cross-Platform Alternatives](#9-cross-platform)
10. [Architecture Support Matrix](#10-arch-matrix)

---

## 1. Cooperative Groups for Synchronized Constraint Evaluation {#1-cooperative-groups}

### API Surface
```cpp
#include <cooperative_groups.h>
namespace cg = cooperative_groups;

// Thread block group (standard)
auto block = cg::this_thread_block();
cg::sync(block);

// Tile group (subset of block)
auto tile = cg::tiled_partition<32>(block);  // warp-sized tile
auto tile8 = cg::tiled_partition<8>(block);  // 8-thread tile

// Grid group (requires launch with cooperative kernel flag)
auto grid = cg::this_grid();
cg::sync(grid);  // Full grid barrier — no separate kernel launch needed

// Multi-GPU group (requires cooperative launch across devices)
auto multi = cg::this_multi_grid();
```

### Launch Requirements
```cpp
// Grid-sync requires cooperative launch:
void* kernel_args[] = { &arg1, &arg2 };
cudaLaunchCooperativeKernel(
    constraint_check_kernel,
    gridDim, blockDim,
    kernel_args,
    sharedMemSize,
    stream
);
```

### Application to FLUX Constraint VM
A FLUX-style stack-based constraint VM evaluates constraints across many variables simultaneously. Cooperative groups enable:

- **Grid-wide barriers** for iterative constraint propagation: all threads evaluate their assigned constraint, then sync at grid level before the next propagation round — without leaving the kernel.
- **Coalesced group** for handling divergent constraint topologies: threads that finish early can form coalesced groups for remaining work.
- **`memcpy_async` with groups** for pipelining constraint data from global → shared memory while computing:
  ```cpp
  cg::memcpy_async(tile, shared_buf, global_ptr + offset, sizeof(float) * TILE_SIZE);
  cg::wait(tile);  // barrier until copy completes
  // Now evaluate constraints from shared_buf
  ```

### Performance Characteristics
| Operation | Latency | Throughput |
|-----------|---------|------------|
| `cg::sync(block)` | ~20-40 cycles | O(blockSize) |
| `cg::sync(grid)` | ~1-10 µs (depends on grid size) | Full GPU stall |
| `cg::memcpy_async` | Overlapped with compute | ~80% of peak HBM bandwidth |

### Architecture Support
- **Ampere (SM 8.0+):** Full support, `memcpy_async` optimized
- **Hopper (SM 9.0):** Enhanced with TMA (Tensor Memory Accelerator) integration
- **Blackwell (SM 10.0):** Further async copy pipeline improvements

---

## 2. Warp-Level Primitives for Voting & Reduction {#2-warp-level-primitives}

### Core Intrinsics

```cpp
// --- Ballot: which threads satisfy a predicate? ---
unsigned int mask = __ballot_sync(0xFFFFFFFF, constraint_satisfied);
int count = __popc(mask);  // How many constraints pass
bool all_pass = (mask == 0xFFFFFFFF);
bool any_pass = (mask != 0);
bool none_pass = (mask == 0);

// --- Shuffle: exchange values across warp lanes ---
// Broadcast constraint bound from lane 0:
float bound = __shfl_sync(0xFFFFFFFF, local_bound, 0);

// Warp-level sum reduction (5 steps for 32 lanes):
float val = constraint_error;
for (int offset = 16; offset > 0; offset >>= 1) {
    val += __shfl_down_sync(0xFFFFFFFF, val, offset);
}
// Lane 0 now holds the sum of all 32 constraint errors

// --- Shuffle XOR: butterfly reduction for min/max ---
for (int offset = 16; offset > 0; offset >>= 1) {
    float other = __shfl_xor_sync(0xFFFFFFFF, val, offset);
    val = fminf(val, other);
}
// Lane 0 now holds the min constraint error across the warp

// --- Warp-aggregated atomic (Ampere+) ---
// Use ballot to coalesce atomic updates:
unsigned active = __ballot_sync(0xFFFFFFFF, needs_update);
int lane = threadIdx.x & 31;
while (active) {
    int leader = __ffs(active) - 1;  // first set bit
    if (lane == leader) {
        atomicAdd(global_error_sum, local_error);
    }
    active &= ~(1u << leader);  // clear leader bit
}
```

### FLUX-Specific Pattern: Parallel Constraint Satisfaction Check
```cpp
__global__ void flux_check_constraints(
    const Constraint* constraints,  // Array of constraints
    const float* variables,         // Variable values
    int* violation_flags,           // Output: 1 if violated
    int n_constraints
) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    int lane = tid & 31;
    
    if (tid >= n_constraints) return;
    
    // Each thread evaluates one constraint
    const Constraint& c = constraints[tid];
    float lhs = eval_expression(c.lhs, variables);  // Stack evaluation
    float rhs = eval_expression(c.rhs, variables);
    bool satisfied = (lhs <= rhs + c.tolerance);
    
    // Warp-aggregate: count violations per warp
    unsigned int mask = __ballot_sync(0xFFFFFFFF, !satisfied);
    int violations_in_warp = __popc(mask);
    
    // Lane 0 writes warp summary
    if (lane == 0) {
        violation_flags[blockIdx.x * blockDim.x / 32] = violations_in_warp;
    }
}
```

### Performance Characteristics
| Intrinsic | Latency | Notes |
|-----------|---------|-------|
| `__ballot_sync` | 1-2 cycles | Register-to-register |
| `__shfl_sync` | 1-2 cycles | No shared memory needed |
| `__popc` | 1 cycle | Single instruction (POPC) |
| Warp reduction (32→1) | ~10 cycles | 5 shuffle-add steps |

### Architecture Support
- **All architectures since Kepler (SM 3.5+)** for basic shuffle
- **Volta+ (SM 7.0+):** Must use `_sync` suffixed versions, independent thread scheduling
- **Ampere/Ada/Hopper/Blackwell:** Full support, improved warp scheduling

---

## 3. CUDA Dynamic Parallelism for Recursive Constraint Solving {#3-dynamic-parallelism}

### Overview
Dynamic Parallelism (CDP) allows a GPU kernel to launch child kernels from device code, enabling recursive decomposition of constraint problems.

### API
```cpp
// Device-side kernel launch (CDP v1 — all architectures)
__global__ void solve_constraints_recursive(
    ConstraintNode* nodes, int* active_set, int depth
) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    
    if (depth > MAX_DEPTH || !active_set[tid]) return;
    
    // Evaluate constraint at this node
    float error = evaluate(nodes[tid]);
    
    if (error > THRESHOLD) {
        // Decompose: launch child kernel for subtree
        int child_count = nodes[tid].num_children;
        dim3 child_grid((child_count + 255) / 256);
        dim3 child_block(256);
        
        solve_constraints_recursive<<<child_grid, child_block>>>(
            nodes[tid].children, active_set, depth + 1
        );
    }
}

// CDP v2 (Hopper+, significantly lower overhead):
// Uses the device-side CUDA stream allocator
__global__ void solve_cdp_v2(...) {
    // CDP v2 uses cudaLaunchKernelEx with launch attributes
    cudaLaunchAttribute attrs[1];
    attrs[0].id = cudaLaunchAttributeProgrammaticStreamSerialization;
    attrs[0].val.programmaticStreamSerializationAllowed = 1;
    
    cudaLaunchConfig_t config = {
        .gridDim = child_grid,
        .blockDim = child_block,
        .stream = 0,  // Uses default device stream
        .attrs = attrs,
        .numAttrs = 1
    };
    cudaLaunchKernelEx(&config, child_kernel, args...);
}
```

### FLUX Application: Hierarchical Constraint Decomposition
```
Constraint Tree:
        Root
       /    \
    C1(x,y)  C2(y,z)
    /    \       |
 C1a    C1b    C2a(x,z)
```
- Each level of the constraint tree = one CDP launch
- Parent evaluates coarse constraint; if violated, spawns children for refinement
- **Memory**: Child kernel inherits parent's global memory; shared memory is isolated

### Performance Characteristics
| Aspect | CDP v1 | CDP v2 (Hopper) |
|--------|--------|-----------------|
| Launch latency | ~50-100 µs | ~5-10 µs |
| Queue depth | Limited | Deep queue via hardware |
| Memory overhead | Separate launch args per child | Shared stream pool |
| Nesting depth | 24 levels max | 128+ levels |

### Caveats for Constraint VMs
- **Don't use CDP for fine-grained recursion** — the launch overhead dominates for <10,000 threads
- **Best for**: hierarchical constraint systems where each level has fundamentally different granularity
- **Alternative**: Flatten recursion into iterative kernel loops with cooperative group grid sync

### Architecture Support
- **Kepler+ (SM 3.5+):** CDP v1 supported
- **Hopper (SM 9.0):** CDP v2 with dramatically reduced overhead
- **Blackwell (SM 10.0):** CDP v2 standard, further optimized

---

## 4. CUDA Graphs for Zero-Overhead Kernel Launch {#4-cuda-graphs}

### Overview
CUDA Graphs capture an entire workflow of kernel launches, memory operations, and dependencies into a single DAG. Replaying the graph eliminates CPU-side launch overhead entirely.

### API Pattern
```cpp
// --- Stream capture mode ---
cudaStreamBeginCapture(stream, cudaStreamCaptureModeGlobal);

// Launch kernels as normal — they're captured, not executed
constraint_compile<<<grid1, block1, 0, stream>>>(...);
constraint_execute<<<grid2, block2, 0, stream>>>(...);
constraint_verify<<<grid3, block3, 0, stream>>>(...);

cudaStreamEndCapture(stream, &graph);

// --- Instantiate for repeated replay ---
cudaGraphInstantiate(&graph_exec, graph, NULL, NULL, 0);

// --- Replay with near-zero CPU overhead ---
// Each launch: ~2.5 µs + ~1 ns/node (CUDA 12.6+)
cudaGraphLaunch(graph_exec, stream);

// --- Update node parameters without recapture ---
// For dynamic constraint values:
cudaGraphExecKernelNodeSetParams(graph_exec, node_index, &node_params);

// --- Conditional nodes (CUDA 12.8+) ---
cudaGraphNode_t if_node;
cudaIfParams if_params = {
    .condValue = &violation_count,  // Device pointer
    .size = sizeof(int)
};
cudaGraphAddIfNode(&if_node, graph, NULL, 0, &if_params);
```

### FLUX Pipeline: Compile → Execute → Verify
```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│  COMPILE    │───>│   EXECUTE    │───>│   VERIFY    │
│  (parse &   │    │  (evaluate   │    │  (ballot &  │
│   compile)  │    │  constraints)│    │   reduce)   │
└─────────────┘    └──────────────┘    └─────────────┘
       ↓                  ↓                   ↓
   Update byte-      Update variable      Read violation
   code in GPU      values in global      count (conditional
   memory            memory               branch if > 0)
```

All three stages captured as a single graph. Variable data updated via `cudaGraphExecKernelNodeSetParams` or `cudaMemcpy3D` node updates — no CPU round-trip needed for repeated constraint checks.

### Performance
| Metric | Traditional Launch | CUDA Graph |
|--------|--------------------|------------|
| CPU overhead per kernel | ~5-20 µs | ~1 ns (amortized) |
| 10-kernel pipeline | ~50-200 µs CPU | ~2.5 µs + 10 ns |
| Launch jitter | Variable | Near-zero (deterministic) |
| Best for | Dynamic topologies | Static topology, dynamic data |

### Architecture Support
- **All architectures** (software-managed since CUDA 10)
- **Ampere (SM 8.0):** Hardware-accelerated graph launch via RISC-V management processor
- **Hopper (SM 9.0):** Enhanced with conditional nodes, programmatic launch
- **Blackwell (SM 10.0):** Further optimized, CDP v2 integration with graphs

---

## 5. Tensor Cores for Constraint Matrix Operations {#5-tensor-cores}

### Overview
Tensor cores perform mixed-precision matrix multiply-accumulate (MMA) in a single clock cycle per SM. For constraint systems that can be expressed as matrix operations, tensor cores offer 10-100x throughput over scalar CUDA cores.

### Constraint Propagation as Matrix Operations
Many constraint propagation algorithms reduce to sparse or dense matrix-vector products:
```
Constraint Jacobian J × variable_update Δx = residual r

Where:
- J is m×n (m constraints, n variables)
- Δx is n×1 (variable deltas)
- r is m×1 (constraint residuals)
```

### API: WMMA (Warp Matrix Multiply-Accumulate)
```cpp
#include <mma.h>
using namespace nvcuda::wmma;

__global__ void constraint_jacobian_multiply(
    const half* J,       // m×n Jacobian (FP16)
    const half* delta_x, // n×1 variable deltas (FP16)
    float* residual,     // m×1 residuals (FP32 output)
    int m, int n
) {
    // Tile dimensions
    fragment<matrix_a, 16, 16, 16, half, row_major> J_frag;
    fragment<matrix_b, 16, 16, 16, half, col_major> dx_frag;
    fragment<accumulator, 16, 16, 16, float> res_frag;
    
    fill_fragment(res_frag, 0.0f);
    
    // Accumulate over K dimension
    for (int k = 0; k < n; k += 16) {
        load_matrix_sync(J_frag, J + ... , n);
        load_matrix_sync(dx_frag, delta_x + k, 1);
        mma_sync(res_frag, J_frag, dx_frag, res_frag);
    }
    
    // Store with FP32 precision for constraint evaluation
    store_matrix_sync(residual + ..., res_frag, m, mem_row_major);
}
```

### Hopper+: WGMMA (Warp Group Matrix Multiply-Accumulate)
```cpp
// Hopper SM 9.0 introduces WGMMA — 4 warps cooperate on larger tiles
// Up to 256×128 matrix tiles per SM per clock
// nvcuda::wmma::experimental or CUTLASS 3.x

// Using CUTLASS 3.x (recommended):
#include "cutlass/gemm/gemm_array.h"
#include "cutlass/gemm/device/gemm_universal.h"

// Mixed precision: FP16 input, FP32 accumulation, FP16 output
// Critical for constraint checking: accumulate in FP32 for precision,
// store in FP16 for memory bandwidth
using Gemm = cutlass::gemm::device::GemmUniversal<
    cutlass::half_t, cutlass::layout::RowMajor,   // A (Jacobian)
    cutlass::half_t, cutlass::layout::ColumnMajor, // B (delta_x)
    float, cutlass::layout::RowMajor,              // C (residual)
    float,                                          // Scalar type
    cutlass::arch::OpClassTensorOp,                // Tensor cores
    cutlass::arch::Sm90                            // Hopper
>;
```

### Mixed-Precision Constraint Strategy
```
Precision ladder for constraint evaluation:
1. FP16 (half) — Broad phase: screen constraints, detect obvious violations
2. BF16 — Narrow phase: tighter bounds checking with FP32 range
3. FP32 — Exact evaluation for constraints that pass broad phase
4. FP64 — Verification/audit for safety-critical constraints (Hopper FP64 tensor cores)
```

### Performance (Hopper H100)
| Precision | Throughput (per SM) | Peak (full chip, 132 SM) |
|-----------|--------------------|--------------------------|
| FP16→FP32 | 256 FMAs/cycle | ~990 TFLOPS |
| BF16→FP32 | 256 FMAs/cycle | ~990 TFLOPS |
| INT8→INT32 | 512 FMAs/cycle | ~1979 TOPS |
| FP64 (Hopper) | 32 FMAs/cycle | ~67 TFLOPS |
| FP8 (Hopper) | 512 FMAs/cycle | ~1979 TFLOPS |

### Architecture Support
| Feature | Ampere | Ada | Hopper | Blackwell |
|---------|--------|-----|--------|-----------|
| FP16 MMA | ✅ | ✅ | ✅ | ✅ |
| BF16 MMA | ✅ | ✅ | ✅ | ✅ |
| INT8 MMA | ✅ | ✅ | ✅ | ✅ |
| FP64 MMA | ❌ | ❌ | ✅ | ✅ |
| FP8 MMA | ❌ | ❌ | ✅ (E4M3/E5M2) | ✅ |
| WGMMA | ❌ | ❌ | ✅ | ✅ (enhanced) |
| FP4/FP6 | ❌ | ❌ | ❌ | ✅ (Blackwell) |

---

## 6. Multi-Instance GPU (MIG) for Safety-Critical Partitioning {#6-mig}

### Overview
MIG partitions a single GPU into isolated instances with dedicated SMs, memory, and L2 cache. For safety-critical constraint systems, this provides hardware-level isolation.

### Configuration
```bash
# Enable MIG mode on H100
nvidia-smi -i 0 -mig 1

# Partition into 7 isolated instances (1g.10gb each on H100 80GB)
nvidia-smi mig -cgi 1g.10gb,1g.10gb,1g.10gb,1g.10gb,1g.10gb,1g.10gb,1g.10gb -C 0

# Or fewer, larger instances:
# 2g.20gb — 2 instances (14 SM each)
# 3g.40gb — 1 instance (42 SM)
# 4g.40gb — 1 instance (56 SM)
```

### Use Case: FLUX Safety Partition
```
┌─────────────────────────────────────────┐
│              H100 80GB GPU              │
│  ┌──────────┐ ┌──────────┐ ┌─────────┐ │
│  │ Instance │ │ Instance │ │Instance │ │
│  │    0     │ │    1     │ │   2     │ │
│  │ SAFETY   │ │ CRITICAL │ │ NORMAL  │ │
│  │ CRITICAL │ │ PATH     │ │ EVAL    │ │
│  │          │ │          │ │         │ │
│  │ 14 SM    │ │ 28 SM    │ │ 14 SM   │ │
│  │ 10 GB    │ │ 20 GB    │ │ 10 GB   │ │
│  └──────────┘ └──────────┘ └─────────┘ │
└─────────────────────────────────────────┘
```

- **Instance 0 (Safety Critical):** Hard real-time constraint verification with guaranteed SM budget and memory bandwidth. No interference from other workloads.
- **Instance 1 (Critical Path):** Main constraint propagation and solving.
- **Instance 2 (Normal):** Best-effort constraint evaluation, logging, telemetry.

### Isolation Guarantees
- Separate L2 cache slices → no cache pollution between instances
- Separate memory controllers → guaranteed bandwidth per instance
- Separate SMs → no compute preemption from other instances
- Separate fault domains → a crash in one instance doesn't affect others

### Architecture Support
- **A100 (Ampere):** MIG 1.0 — up to 7 instances
- **H100 (Hopper):** MIG 1.0 — improved, up to 7 instances
- **Ada Lovelace:** No MIG support (consumer/gaming)
- **Blackwell B100/B200:** MIG support continued
- **RTX 4090/5090:** No MIG (not datacenter GPUs)

---

## 7. Grace Hopper Unified Memory for Zero-Copy Constraint Checking {#7-grace-hopper}

### Architecture
Grace Hopper Superchip (GH200) combines:
- **Grace CPU:** 72 Neoverse V2 cores, up to 480 GB LPDDR5X
- **Hopper GPU:** H100-class, 96 GB HBM3
- **NVLink-C2C:** 900 GB/s coherent interconnect between CPU and GPU

### Key Feature: Unified Memory with Hardware Coherence
```cpp
// Allocate unified memory — accessible from both CPU and GPU
// On GH200, this is physically in LPDDR5X but cache-coherent with GPU
cudaError_t err = cudaMallocManaged(&constraint_data, size);

// CPU writes constraint definitions
define_constraints_cpu(constraint_data);

// GPU evaluates — data migrates automatically, or stays if properly placed
constraint_kernel<<<grid, block>>>(constraint_data);

// On GH200: No "migration" — unified physical address space
// CPU and GPU can simultaneously access with cache coherence
// Latency: ~60ns GPU→CPU memory access via NVLink-C2C
```

### Zero-Copy Constraint Checking Pattern
```cpp
// Place constraint variables in CPU-accessible unified memory
// GPU reads them directly — no cudaMemcpy needed
__global__ void check_constraints_zero_copy(
    const Constraint* constraints,  // In HBM (fast, GPU-local)
    const float* variables,         // In LPDDR5X (unified, CPU-writable)
    int* violations,                // In HBM (GPU writes)
    int n
) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    if (tid >= n) return;
    
    // variables[] is in unified memory — CPU can update between kernel launches
    // No explicit copy needed
    float val = variables[constraints[tid].var_idx];
    float bound = constraints[tid].bound;
    
    violations[tid] = (val > bound) ? 1 : 0;
}
```

### Memory Placement Strategy
```cpp
// Explicit placement for performance:
cudaMemAdvise(constraints, size, cudaMemAdviseSetPreferredLocation, gpuDevice);
cudaMemAdvise(variables, var_size, cudaMemAdviseSetPreferredLocation, cpuDevice);
cudaMemAdvise(variables, var_size, cudaMemAdviseSetAccessedBy, gpuDevice);

// Result: constraints in fast HBM, variables in unified LPDDR5X
// GPU accesses variables via NVLink-C2C at ~60ns latency
// CPU updates variables directly — no copy, no synchronization
```

### Bandwidth & Latency
| Path | Bandwidth | Latency |
|------|-----------|---------|
| GPU → HBM3 (local) | ~3.35 TB/s | ~200 cycles |
| GPU → LPDDR5X (unified) | ~900 GB/s (NVLink-C2C) | ~60 ns |
| CPU → HBM3 (GPU memory) | ~900 GB/s (NVLink-C2C) | ~60 ns |
| CPU → LPDDR5X (local) | ~546 GB/s | ~100 ns |

### Architecture Support
- **GH200 (Grace Hopper):** Full hardware coherence, unified address space
- **Standard H100:** Unified memory via software page migration (slower, ~10µs faults)
- **Grace-Blackwell GB200:** Successor with Blackwell GPU, same unified model

---

## 8. CUDA Streams for Pipelined Constraint Compilation → Execution → Verification {#8-cuda-streams}

### Multi-Stream Pipeline Architecture
```
Stream 0 (Compile):  [Batch N  ] [Batch N+1] [Batch N+2]
Stream 1 (Execute):            [Batch N  ] [Batch N+1] [Batch N+2]
Stream 2 (Verify):                       [Batch N  ] [Batch N+1]

Events:  E0 ──────────> E1 ──────────> E2
         (compile done)  (execute done)  (verify done)
```

### Implementation
```cpp
cudaStream_t stream_compile, stream_execute, stream_verify;
cudaEvent_t event_compiled, event_executed;
cudaStreamCreate(&stream_compile);
cudaStreamCreate(&stream_execute);
cudaStreamCreate(&stream_verify);
cudaEventCreate(&event_compiled);
cudaEventCreate(&event_executed);

// Pipeline loop — triple-buffered
for (int batch = 0; batch < n_batches; batch++) {
    // Wait for previous execution to finish before overwriting compile buffer
    if (batch > 0) cudaStreamWaitEvent(stream_compile, event_executed, 0);
    
    // Stage 1: Compile constraint bytecodes for this batch
    compile_kernel<<<compile_grid, block, 0, stream_compile>>>(
        bytecode_in, compiled_out + (batch % 3) * buf_size
    );
    cudaEventRecord(event_compiled, stream_compile);
    
    // Stage 2: Execute compiled constraints (wait for compile)
    cudaStreamWaitEvent(stream_execute, event_compiled, 0);
    execute_kernel<<<exec_grid, block, 0, stream_execute>>>(
        compiled_out + (batch % 3) * buf_size,
        variables, results + batch * result_stride
    );
    cudaEventRecord(event_executed, stream_execute);
    
    // Stage 3: Verify results (wait for execute)
    cudaStreamWaitEvent(stream_verify, event_executed, 0);
    verify_kernel<<<verify_grid, block, 0, stream_verify>>>(
        results + batch * result_stride, violation_buf
    );
}

// Synchronize all streams
cudaDeviceSynchronize();
```

### FLUX-Specific Pipeline: JIT Constraint Compilation
For a stack-based VM like FLUX, the pipeline is:

1. **Compile Stream**: Parse constraint expressions → GPU bytecode (or optimize existing bytecode)
2. **Execute Stream**: Evaluate bytecode on GPU (stack machine per thread)
3. **Verify Stream**: Aggregate results via warp-level reductions, detect violations

### Performance
| Pipeline Depth | Latency (per batch) | Throughput |
|---------------|--------------------| ------------|
| Single stream (serial) | T_compile + T_exec + T_verify | 1/(T_total) |
| 3-stream pipeline | max(T_compile, T_exec, T_verify) | ~3x throughput |
| CUDA Graph (3-stage) | Same, but ~2.5µs launch overhead removed | Highest throughput |

### Priority Streams for Real-Time Constraints
```cpp
// Safety-critical constraints get high priority
cudaStreamCreateWithPriority(&stream_safety, cudaStreamNonBlocking, 0);  // Highest
cudaStreamCreateWithPriority(&stream_normal, cudaStreamNonBlocking, -1);  // Lower

// Safety constraints preempt normal evaluation
safety_check_kernel<<<grid, block, 0, stream_safety>>>(...);
normal_check_kernel<<<grid, block, 0, stream_normal>>>(...);
```

### Architecture Support
- **All CUDA-capable GPUs** support streams
- **Ampere+**: Hardware-accelerated stream scheduling
- **Hopper**: Enhanced with programmable stream serialization (CDP v2)

---

## 9. Cross-Platform Alternatives {#9-cross-platform}

### 9.1 WebGPU/WGSL Compute Shaders

**Use Case**: Browser-based constraint checking, portable verification

```wgsl
// WGSL compute shader for constraint evaluation
@group(0) @binding(0) var<storage, read> constraints: array<Constraint>;
@group(0) @binding(1) var<storage, read_write> variables: array<f32>;
@group(0) @binding(2) var<storage, read_write> violations: array<u32>;

struct Constraint {
    lhs_var_idx: u32,
    rhs_var_idx: u32,
    bound: f32,
    op: u32,  // 0: ≤, 1: ≥, 2: ==, 3: !=
}

@compute @workgroup_size(64)
fn check_constraints(@builtin(global_invocation_id) gid: vec3<u32>) {
    let idx = gid.x;
    if (idx >= arrayLength(&constraints)) { return; }
    
    let c = constraints[idx];
    let lhs = variables[c.lhs_var_idx];
    let rhs = variables[c.rhs_var_idx];
    
    var satisfied = false;
    if (c.op == 0u) { satisfied = lhs <= rhs + c.bound; }
    if (c.op == 1u) { satisfied = lhs >= rhs - c.bound; }
    if (c.op == 2u) { satisfied = abs(lhs - rhs) < c.bound; }
    if (c.op == 3u) { satisfied = abs(lhs - rhs) > c.bound; }
    
    violations[idx] = select(1u, 0u, satisfied);
}
```

**Limitations vs CUDA**:
- No warp-level primitives (no `ballot`, `shfl`)
- Subgroup operations available in some browsers (experimental): `subgroupBallot`, `subgroupAdd`
- Max workgroup size: 256 (vs CUDA's 1024)
- No dynamic parallelism
- No tensor cores
- Latency: ~1-5 ms for typical workloads (browser overhead)

**Best for**: Interactive constraint visualization, client-side verification, educational tools

### 9.2 Vulkan Compute

**Use Case**: Cross-vendor GPU constraint execution (AMD, Intel, NVIDIA, Apple via MoltenVK)

```glsl
// GLSL compute shader (Vulkan)
#version 450
layout(local_size_x = 256) in;

layout(set = 0, binding = 0) buffer Constraints {
    Constraint constraints[];
};
layout(set = 0, binding = 1) buffer Variables {
    float variables[];
};
layout(set = 0, binding = 2) buffer Violations {
    uint violations[];
};

// Subgroup operations (Vulkan 1.1+, most desktop GPUs)
void main() {
    uint idx = gl_GlobalInvocationID.x;
    if (idx >= constraints.length()) return;
    
    Constraint c = constraints[idx];
    float lhs = variables[c.lhs_var];
    float rhs = variables[c.rhs_var];
    
    bool sat = (lhs <= rhs + c.bound);
    
    // Subgroup ballot (equivalent to __ballot_sync)
    uvec4 ballot = subgroupBallot(!sat);
    uint count = subgroupBallotBitCount(ballot);
    
    if (subgroupElect()) {  // One thread per subgroup writes
        atomicAdd(violations[0], count);
    }
}
```

**Vulkan Subgroup Features** (Vulkan 1.1+):
- `subgroupBallot` → equivalent to `__ballot_sync`
- `subgroupAdd/subgroupMin/subgroupMax` → warp-level reductions
- `subgroupShuffle` → equivalent to `__shfl_sync`
- Supported on: NVIDIA (all), AMD (RDNA+, GCN), Intel (Gen12+)

**Best for**: Cross-platform desktop/mobile constraint engines, game engine integration

### 9.3 SYCL/oneAPI

**Use Case**: Portable GPU constraint solving across NVIDIA, AMD, Intel

```cpp
#include <sycl/sycl.hpp>

void check_constraints_sycl(
    sycl::queue& q,
    const Constraint* constraints,
    const float* variables,
    int* violations,
    int n
) {
    q.parallel_for(sycl::range<1>(n), [=](sycl::id<1> idx) {
        // Each work-item evaluates one constraint
        Constraint c = constraints[idx];
        float lhs = variables[c.lhs_var];
        float rhs = variables[c.rhs_var];
        
        bool satisfied = (lhs <= rhs + c.bound);
        
        // SYCL subgroup operations (portable)
        auto sg = sycl::ext::oneapi::experimental::this_sub_group();
        auto mask = sycl::ext::oneapi::experimental::ballot(sg, !satisfied);
        int count = sycl::popcount(mask);
        
        if (sg.get_local_id()[0] == 0) {
            sycl::atomic_ref<int, sycl::memory_order::relaxed,
                sycl::memory_scope::device> ref(violations[0]);
            ref += count;
        }
    }).wait();
}

// Backend targeting:
// NVIDIA: CUDA backend (pti-backend)
// Intel GPU: Level Zero backend
// AMD GPU: HIP backend (via DPC++ with HIP plugin)
// CPU: OpenMP backend
```

**SYCL Advantage for Constraint Systems**:
- Write once, run on any GPU vendor
- Subgroup operations are vendor-agnostic
- Can mix CPU and GPU execution in same code
- Intel DPC++ supports CUDA backend → compiles to native CUDA

---

## 10. Architecture Support Matrix {#10-arch-matrix}

| Technique | Ampere (A100) | Ada (RTX 4090) | Hopper (H100) | Blackwell (B200) |
|-----------|:---:|:---:|:---:|:---:|
| Cooperative Groups | ✅ | ✅ | ✅ | ✅ |
| Warp Primitives | ✅ | ✅ | ✅ | ✅ |
| Dynamic Parallelism v1 | ✅ | ✅ | ✅ | ✅ |
| Dynamic Parallelism v2 | ❌ | ❌ | ✅ | ✅ |
| CUDA Graphs | ✅ | ✅ | ✅ | ✅ |
| CUDA Graphs Conditional | ❌ | ❌ | ✅ (12.8) | ✅ |
| Tensor Cores FP16/BF16 | ✅ | ✅ | ✅ | ✅ |
| Tensor Cores FP64 | ❌ | ❌ | ✅ | ✅ |
| Tensor Cores FP8 | ❌ | ❌ | ✅ | ✅ |
| Tensor Cores FP4/FP6 | ❌ | ❌ | ❌ | ✅ |
| MIG | ✅ | ❌ | ✅ | ✅ |
| Unified Memory (Hw Coherence) | ❌ | ❌ | ✅ (GH200) | ✅ (GB200) |
| WGMMA | ❌ | ❌ | ✅ | ✅ |

---

## Summary: Recommended Stack for FLUX Constraint VM

### Tier 1: Must-Have (Any Ampere+ GPU)
1. **Warp-level primitives** for per-constraint evaluation and aggregation
2. **CUDA streams** for pipeline parallelism (compile → exec → verify)
3. **Cooperative groups** for grid-wide synchronization during iterative solving
4. **Shared memory** for stack-based VM execution (each thread block = set of constraint evaluators)

### Tier 2: High Performance (Hopper+)
5. **CUDA Graphs** to eliminate launch overhead for fixed-topology constraint pipelines
6. **Tensor cores** (FP16→FP32) for constraint Jacobian evaluation
7. **CDP v2** for hierarchical constraint decomposition
8. **TMA (Tensor Memory Accelerator)** for async data movement during constraint evaluation

### Tier 3: Safety-Critical / Enterprise
9. **MIG** for hardware-isolated safety partitions
10. **Grace Hopper unified memory** for zero-copy CPU↔GPU constraint data
11. **FP64 tensor cores** for safety-critical verification pass

### Cross-Platform Fallback
- **Vulkan Compute** for desktop deployment (AMD/Intel/NVIDIA)
- **SYCL/oneAPI** for HPC environments with mixed GPU vendors
- **WebGPU** for browser-based constraint visualization and light verification

---

*Report compiled: May 3, 2026 | Sources: NVIDIA CUDA Programming Guide (March 2026), CUDA 12.8 release notes, GTC 2025 presentations, arXiv papers on hybrid CUDA Graph optimization, NVIDIA developer blogs*
