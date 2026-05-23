# Distributed Compute Bridge: Cross-Architecture CUDA Deployment

**Core Concept:** Distributed compute bridge enables CUDA kernel deployment across heterogeneous architectures (x64 workstation, ARM64 Jetson) with zero-copy optimizations, PTX serialization, and automatic capability matching—forming a unified compute fabric for marine edge systems.

**Architecture Overview:**

```
Workstation (x64)              Jetson Edge (ARM64)
+-------------------+          +-------------------+
| Host Application  |          | GPU Compute Node  |
| +-------------+  |          | +-------------+  |
| | Bridge API  |  |<--------->| | CUDA Runtime|  |
| +-------------+  |  MEP/TCP  | +-------------+  |
|        |          |  Protocol|        |          |
|        v          |          |        v          |
| +-------------+  |          | +-------------+  |
| | PTX Caches  |  |          | | Kernel Cache|  |
| +-------------+  |          | +-------------+  |
+-------------------+          +-------------------+
```

**Key Components:**

**1. PTX Serialization:**
- Compile CUDA kernels to PTX (Portable Thread Execution)
- Serialize PTX to binary format for transmission
- Embed metadata: SM version, register count, shared memory requirements
- Version control: track PTX compilation time and compiler flags

**2. Capability Matching:**
```python
def match_kernel_compatibility(host_sm, device_sm):
    """Check if PTX compiled for host_sm runs on device_sm"""
    if device_sm >= host_sm:
        return True  # Forward compatible
    elif device_sm in [60, 62, 70, 72, 75, 80, 86, 87, 89]:
        # Check for supported instruction subsets
        return check_instruction_subset(host_sm, device_sm)
    return False
```

**3. Zero-Copy Optimizations:**
- **Pinned Memory:** Allocate host memory with `cudaHostAllocMapped`
- **Direct Access:** Edge device reads host memory over PCIe/DMA
- **Batch Transfer:** Aggregate multiple buffers in single DMA operation
- **Network Zero-Copy:** When on shared LAN, use RDMA for remote direct access

**4. Kernel Deployment Workflow:**
```
1. Workstation compiles kernel.cu → kernel.ptx
2. Serialize PTX + metadata → MEP_GPU_COMMAND payload
3. Transmit via MEP/TCP to edge device
4. Edge device receives, validates compatibility
5. JIT-compile PTX to device code (NVRTC)
6. Cache compiled binary for future use
7. Launch kernel on edge GPU
8. Stream results back via MEP
```

**Architecture Variants:**

**RTX 4050 (Ada SM 8.9) → Jetson Orin (SM 8.7):**
- Backward compatible: SM 8.9 instructions may not exist on SM 8.7
- Solution: Compile with `-arch=sm_87` for maximum portability
- Trade-off: Lose Ada-specific optimizations (FP8, DP4A)

**Shared Features (SM 8.7+):**
- Tensor Cores (TF32/FP16/INT8)
- Warp matrix operations
- Cooperative Groups
- DP4A instructions
- L2 cache residency control

**Performance Considerations:**
- **JIT Compilation:** ~50-200ms overhead on first use (amortized by cache)
- **Network Latency:** 1-10 ms LAN, 50-500 ms satellite (batching critical)
- **DMA Bandwidth:** PCIe 4.0 x16: ~32 GB/s theoretical
- **Cache Hit Rate:** Target >95% after warm-up

**Constraint-Aware Deployment:**
Bridge respects edge device constraints:
- Thermal: Don't launch heat-intensive kernels when edge throttling
- Power: Batch workloads during battery charging
- Memory: Split large tensors across multiple edge devices
- Precision: Use FP16 on edge if workstation used FP32 (accuracy trade-off)

**Use Case: Distributed Sonar Processing:**
1. Workstation collects raw sonar data
2. Splits frequency bands into chunks
3. Each chunk dispatched to different edge device
4. Edge devices process in parallel using cached kernels
5. Results streamed back, merged by workstation
6. Constraint checks applied globally

**Provenance:** Forgemaster (distributed computing architecture)
**Chain:** Distributed compute bridge experiments, marine-gpu-edge
