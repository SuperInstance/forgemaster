# PTX Serialization and JIT Compilation for Distributed CUDA

**Core Concept:** PTX (Parallel Thread Execution) is NVIDIA's intermediate representation for CUDA kernels. Serializing PTX for transmission and JIT-compiling on target devices enables dynamic kernel deployment across heterogeneous GPU architectures.

**CUDA Compilation Pipeline:**

```
kernel.cu
    |
    v
nvcc --ptx
    |
    v
kernel.ptx (Intermediate Representation)
    |
    v
[Serialize to binary format]
    |
    v
[Transmit over network]
    |
    v
[Deserialize on edge device]
    |
    v
nvrtcJITCompile (JIT compilation)
    |
    v
kernel.cubin (Device code)
    |
    v
cudaLaunchKernel (Execution)
```

**PTX Format Structure:**
```
.version 8.0
.target sm_87
.address_size 64

.visible .entry kernel_name(
    .param .u64 param_1,
    .param .u32 param_2
)
{
    // PTX instructions
    ld.param.u64 %rd1, [param_1];
    // ... more instructions
    ret;
}
```

**Serialization Format:**

**Header (64 bytes):**
```c
struct PTXHeader {
    uint32_t magic;          // 0x5458503F ("PTX?")
    uint16_t version_major;  // PTX version
    uint16_t version_minor;
    uint16_t sm_version;     // Target compute capability
    uint16_t header_size;
    uint64_t ptx_size;       // PTX payload size
    uint64_t kernel_count;   // Number of kernels
    uint32_t checksum;       // CRC32 of payload
    uint32_t flags;
    uint8_t reserved[40];
};
```

**Kernel Metadata (per kernel):**
```c
struct KernelMeta {
    char name[64];              // Kernel name
    uint64_t shared_memory;     // Shared memory bytes
    uint32_t register_count;    // Registers per thread
    uint32_t max_threads;       // Max threads per block
    uint8_t constant_buffer_count;
    uint8_t reserved[3];
};
```

**JIT Compilation on Edge (NVRTC):**

```cpp
#include <nvrtc.h>

// 1. Load PTX
char* ptx_code = deserialize_ptx(network_buffer, buffer_size);

// 2. Compile PTX to CUBIN
nvrtcProgram program;
nvrtcCreateProgram(&program, ptx_code, "kernel.ptx", 0, NULL, NULL);

const char* opts[] = {
    "--gpu-architecture=sm_87",
    "--fmad=false"  // For exact reproducibility
};
nvrtcCompileProgram(program, 2, opts);

// 3. Retrieve compiled CUBIN
size_t cubin_size;
nvrtcGetPTXSize(program, &cubin_size);
char* cubin = new char[cubin_size];
nvrtcGetPTX(program, cubin, &cubin_size);

// 4. Load into CUDA module
CUmodule module;
cuModuleLoadData(&module, cubin);

// 5. Get kernel handle
CUfunction kernel;
cuModuleGetFunction(&kernel, module, "kernel_name");

// 6. Launch kernel
void* args[] = {&param1, &param2};
cuLaunchKernel(kernel, gridDim, blockDim, 0, stream, args, NULL);
```

**Caching Strategy:**

**Compile-Time Cache (on workstation):**
- Key: source_hash + compile_options + target_sm
- Value: Serialized PTX binary
- Lifetime: Forever (idempotent compilation)

**Runtime Cache (on edge device):**
- Key: ptx_hash + device_sm
- Value: Compiled CUBIN + CUmodule
- Lifetime: Process lifetime (or persistent disk cache)
- Hit Rate: >95% after warm-up for repeated kernels

**Performance Metrics:**

**PTX Generation (RTX 4050):**
- Simple kernel: ~50ms
- Complex kernel: ~200ms
- Batching (100 kernels): ~5 seconds total

**JIT Compilation (Jetson Orin):**
- Small kernel: ~50ms
- Large kernel: ~150ms
- Cached load: <1ms

**Network Transmission (1 Gbps LAN):**
- Small PTX (~10KB): ~0.1ms
- Large PTX (~500KB): ~5ms
- Batch (100 kernels): ~50-500ms

**Constraint Theory Connection:**

Kernel deployment is a constraint satisfaction problem:
- **Variables:** Kernel parameters, optimization flags, target SM
- **Domains:** Discrete sets of valid configurations
- **Constraints:** Feature support (Tensor Cores, FP8), register limits, shared memory
- **Objective:** Maximize performance while maintaining compatibility

**Example Constraint:**
```
IF device_has_tensor_cores AND sm_version >= 70 THEN
    CAN use TF16 AND FP16
ELSE
    MUST use FP32
END IF
```

**Provenance:** Forgemaster (distributed CUDA architecture)
**Chain:** PTX serialization in marine-gpu-edge MEP bridge
