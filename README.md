# Forgemaster — GPU Fleet Orchestration and Build Pipeline Coordinator

**Forgemaster** is a Rust service that orchestrates GPU-accelerated computation across a heterogeneous fleet of devices. It maintains a real-time capability map of available GPUs — their core counts, memory, utilization, kernel throughput — and dispatches simulation workloads to the best-matching hardware. In the SuperInstance constellation, it is the silicon-level scheduler.

## Why It Matters

Modern AI fleets span GPU types that differ by 100× in capability: an NVIDIA DGX has 40,000+ CUDA cores; a Jetson Orin Nano has 1,024; an RTX 4050 laptop GPU sits between at ~3,000. A simulation that takes 2 seconds on a DGX could take 3 minutes on a Jetson. Without an intelligent dispatcher, workloads land on whatever GPU is physically closest, not the one that will finish fastest.

The Forgemaster solves this by profiling each GPU's **capability vector** — a tuple of (hashing throughput, dot-product throughput, softmax throughput, vector-search throughput, memory bandwidth) — and maintaining it in real-time as utilization shifts. When a room requests GPU compute, the Forgemaster solves a bin-packing problem: which GPU, given current load, will complete this kernel fastest?

It also coordinates **multi-crate builds**: compiling, linking, and packaging agent artifacts across a workspace of interdependent Rust crates, respecting dependency ordering and caching intermediate results.

## How It Works

### GPU Capability Profiling

Each GPU is characterized by a capability profile derived from micro-benchmarks:

```
CapabilityVector {
    cuda_cores: u32,           // physical core count
    memory_bytes: u64,         // VRAM
    utilization: f32,          // 0.0–1.0, real-time
    hashing_throughput: f64,   // hashes/sec (SHA-256 on 1KB blocks)
    dotproduct_throughput: f64, // GFLOPS (matrix multiply)
    softmax_throughput: f64,    // rows/sec (1024-dim softmax)
    vectorsearch_throughput: f64, // queries/sec (384-dim cosine)
}
```

The Forgemaster periodically re-benchmarks each GPU. If a DGX drops from 85% to 15% utilization (a big job just finished), it becomes eligible for dispatch again.

### Dispatch as Optimization

Given a kernel with resource requirements (core count, memory, estimated runtime), the Forgemaster selects the GPU that minimizes expected completion time:

```
T_expected = T_kernel(C_capability) × (1 + queue_depth) + T_transfer(input_size, bandwidth)
```

This is a variant of the **makespan minimization** problem — NP-hard in the general case, but tractable for fleet sizes of 10–50 GPUs using greedy heuristics: sort by `T_expected`, assign to the minimum.

**Big-O:** Dispatch selection is O(G × K) where G = number of GPUs and K = number of queued kernels. For typical fleet sizes (G < 50, K < 100), this is sub-millisecond.

### Build Pipeline Coordination

For multi-crate builds, the Forgemaster constructs a **dependency DAG** (Directed Acyclic Graph) from `Cargo.toml` manifests:

```
forgemaster
├── fleet-auth (no deps)
├── fleet-metrics (depends on: fleet-auth)
├── fleet-vector-api (depends on: fleet-auth, fleet-metrics)
└── forgemaster (depends on: all of the above)
```

Topological sort gives the build order. Parallel builds run for independent subtrees. The time complexity is O(V + E) for the topological sort, where V = crates and E = dependency edges.

### Comparison to Alternatives

| System | Scope | GPU-aware? | Build coordination? |
|---|---|---|---|
| Kubernetes scheduler | Pods → nodes | Via device plugins | No |
| Slurm | HPC jobs → nodes | Yes (CUDA-aware) | No |
| Bazel | Build only | No | Yes |
| **Forgemaster** | **Both** | **Yes** | **Yes** |

## Quick Start

```rust
use forgemaster::stub;

fn main() {
    println!("{}", stub::hello());
    // "hello from forgemaster"
}
```

The crate is scaffolded. The planned public API:

```rust
pub struct GpuFleet { /* ... */ }
impl GpuFleet {
    pub fn register_gpu(&mut self, gpu: GpuDescriptor);
    pub fn profile_all(&mut self);
    pub fn dispatch(&self, kernel: KernelRequest) -> DispatchDecision;
}

pub struct BuildPipeline { /* ... */ }
impl BuildPipeline {
    pub fn from_workspace(path: &Path) -> Result<Self>;
    pub fn build(&self, target: &str) -> Result<BuildResult>;
}
```

## API

### `stub::hello() -> &'static str`

Placeholder returning `"hello from forgemaster"`. Full GPU dispatch and build pipeline APIs are under development.

### Planned: `GpuFleet`

Manages the real-time GPU registry. `dispatch()` returns a `DispatchDecision` containing the selected GPU ID, estimated runtime, and transfer cost.

### Planned: `BuildPipeline`

Parses Cargo workspace manifests, builds the dependency DAG, and coordinates parallel compilation with artifact caching.

## Architecture Notes

The Forgemaster operates at the **silicon layer** of the SuperInstance constellation. In the conservation law **γ + η = C**, it manages γ (generation energy) at the hardware level — ensuring that every CUDA core in the fleet is doing useful work. A DGX sitting idle at 5% utilization is wasted γ; the Forgemaster's job is to drive every GPU toward its optimal operating point.

The Forgemaster dispatches kernels for `ternary-cell` simulations, `fleet-vector-api` embedding generation, and any other GPU-intensive fleet workload. See the [SuperInstance Architecture](https://github.com/SuperInstance/SuperInstance/blob/main/ARCHITECTURE.md) for how GPU dispatch integrates with the room-as-codespace model.

## References

1. NVIDIA CUDA Programming Guide — [https://docs.nvidia.com/cuda/cuda-c-programming-guide/](https://docs.nvidia.com/cuda/cuda-c-programming-guide/)
2. Topkis, D. M. "Bin Packing with Item Sizes from a Finite Set" — makespan minimization theory
3. Slurm Workload Manager Documentation — [https://slurm.schedmd.com/documentation.html](https://slurm.schedmd.com/documentation.html)

## License

MIT
