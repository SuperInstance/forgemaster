# FLUX CUDA — Parallel Constraint Execution on GPU

CUDA kernels for parallel FLUX ISA execution and constraint solving. Runs thousands of constraint VMs simultaneously on GPU — designed for JetsonClaw1 (Jetson Xavier NX) and Ampere-class GPUs.

## Architecture

```
┌─────────────────────────────────────────────┐
│              Host (CPU)                      │
│  flux_cuda_init() → allocate pinned memory  │
│  flux_cuda_batch_execute() → launch kernel  │
│  flux_cuda_csp_solve() → parallel search    │
│  flux_cuda_sonar_physics() → batch physics  │
└──────────────┬──────────────────────────────┘
               │ CUDA Stream (async)
┌──────────────▼──────────────────────────────┐
│              Device (GPU)                    │
│                                              │
│  ┌─────────────┐  ┌─────────────────────┐   │
│  │ FLUX VM     │  │ CSP Solver          │   │
│  │ 1 block/inst│  │ 1 block/problem     │   │
│  │ shared stack│  │ backtracking search │   │
│  │ warp reduce │  │ forward checking    │   │
│  └─────────────┘  └─────────────────────┘   │
│                                              │
│  ┌─────────────────────────────────────┐     │
│  │ Sonar Physics                       │     │
│  │ Mackenzie 1981 sound speed          │     │
│  │ Francois-Garrison 1982 absorption   │     │
│  │ Ray tracing (multi-path)            │     │
│  └─────────────────────────────────────┘     │
└──────────────────────────────────────────────┘
```

## Build

### Prerequisites
- CUDA Toolkit 11.0+ (`nvcc` in PATH)
- GPU with compute capability ≥ 7.2 (Jetson Xavier) or ≥ 8.6 (Ampere)

### Build Library
```bash
make              # builds libflux_cuda.a and libflux_cuda.so
make static       # builds libflux_cuda.a only
make shared       # builds libflux_cuda.so only
```

### Build & Run Tests
```bash
make test
```

### Clean
```bash
make clean
```

### Cross-compile for Jetson (from x86 host)
```bash
# Install NVIDIA cross-compile toolkit, then:
make NVCC=/usr/local/cuda/bin/nvcc
```

## API Reference

### Device Management

```c
flux_cuda_error_t flux_cuda_init(void);
flux_cuda_error_t flux_cuda_device_info(flux_cuda_device_info_t* info);
void              flux_cuda_cleanup(void);
```

### Batch FLUX VM Execution

Executes N copies of the same FLUX bytecode with different inputs in parallel. One CUDA block per instance, shared-memory stack, warp-level violation reduction.

```c
flux_cuda_error_t flux_cuda_batch_execute(
    const flux_vm_batch_desc_t*  desc,      // bytecode + inputs
    int                          instance_count,
    flux_vm_batch_result_t*      results);  // outputs + violation flags
```

**FLUX ISA Opcodes:**

| Opcode | Hex | Operands | Description |
|--------|-----|----------|-------------|
| NOP    | 0x00 | — | No operation |
| PUSH   | 0x01 | double | Push immediate |
| LOAD   | 0x02 | index | Load input[i] |
| STORE  | 0x03 | index | Store to output[i] |
| ADD    | 0x10 | — | a + b |
| SUB    | 0x11 | — | a - b |
| MUL    | 0x12 | — | a × b |
| DIV    | 0x13 | — | a / b |
| NEG    | 0x14 | — | -a |
| SQRT   | 0x15 | — | √a |
| ABS    | 0x16 | — | |a| |
| MIN    | 0x17 | — | min(a,b) |
| MAX    | 0x18 | — | max(a,b) |
| CMP_EQ | 0x20 | — | a == b → 1/0 |
| CMP_LT | 0x22 | — | a < b → 1/0 |
| CMP_GT | 0x23 | — | a > b → 1/0 |
| ASSERT | 0x30 | — | Pop; flag violation if 0 |
| JMP    | 0x40 | int16 | Relative jump |
| JZ     | 0x41 | int16 | Jump if top-of-stack == 0 |
| HALT   | 0xFF | — | Stop execution |

### Parallel CSP Solver

Solves N independent constraint satisfaction problems in parallel using GPU backtracking with forward checking.

```c
flux_cuda_error_t flux_cuda_csp_solve(
    const flux_csp_problem_desc_t* problem_desc,
    const flux_csp_batch_t*        batch,
    int                            problem_count);
```

**Algorithm:** Each thread explores a different initial branch. Forward checking prunes domains. First solution found is written atomically via `atomicCAS`. Supports up to 64 variables, 128 values per domain, 512 constraints per problem.

### Arc Consistency

GPU-accelerated AC-3 with parallel arc processing. Each thread handles one arc `(xi, xj)`, prunes domain of `xi`. Repeats until fixed point.

```c
flux_cuda_error_t flux_cuda_arc_consistency(
    const flux_csp_problem_desc_t* problem_desc,
    flux_arc_batch_t*              batch,
    int                            problem_count);
```

### Batch Sonar Physics

Computes sound speed (Mackenzie 1981) and absorption (Francois-Garrison 1982) for thousands of depth/temperature/salinity/frequency combinations.

```c
flux_cuda_error_t flux_cuda_sonar_physics(flux_sonar_batch_t* batch);
```

**Equations:**

Mackenzie 1981 sound speed (m/s):
```
c(D,T,S) = 1448.96 + 4.591T - 5.304×10⁻²T² + 2.374×10⁻⁴T³
          + 1.340(S-35) + 1.630×10⁻²D + 1.675×10⁻⁷D²
          - 1.025×10⁻²T(S-35) - 7.139×10⁻¹³TD³
```

Francois-Garrison 1982 absorption (dB/km):
```
α(f) = A₁P₁f₁f²/(f₁²+f²) + A₂P₂f₂f²/(f₂²+f²) + A₃P₃f²
```

## Performance Notes

| Operation | Instances | Jetson Xavier NX | RTX 3080 |
|-----------|-----------|-------------------|----------|
| FLUX VM batch | 1,000 | ~0.3 ms | ~0.05 ms |
| FLUX VM batch | 10,000 | ~1.2 ms | ~0.15 ms |
| CSP solve (4-var) | 1,000 | ~0.5 ms | ~0.08 ms |
| Sonar physics | 10,000 | ~0.2 ms | ~0.03 ms |
| Arc consistency | 1,000 | ~0.4 ms | ~0.06 ms |

*Estimates based on kernel profiling. Actual performance depends on problem complexity and occupancy.*

**Tuning parameters:**
- `max_stack` in `flux_vm_batch_desc_t` — smaller = more shared memory available per SM
- Thread block size auto-selected based on problem count
- Stream-based async — overlap kernel execution with host processing

## Jetson Deployment Guide

### 1. Build on Jetson
```bash
ssh jetsonclaw1
cd /path/to/flux-cuda
make clean && make
```

### 2. Verify GPU
```bash
./test_flux_cuda
# Should show: Device: Xavier (SM 7.2, ...)
```

### 3. Monitor GPU Usage
```bash
sudo tegrastats  # Jetson-specific
# or
nvidia-smi -l 1  # General
```

### 4. Power Mode
For maximum GPU performance on Jetson Xavier NX:
```bash
sudo nvpmodel -m 0    # MAXN mode (15W)
sudo jetson_clocks    # Max clocks
```

### 5. Memory Constraints
Jetson Xavier NX has 8GB shared CPU/GPU memory. Keep total allocations under 6GB to leave room for OS:
- 10,000 FLUX instances × 256 doubles stack = ~20MB (manageable)
- 1,000 CSP problems × 64 vars × 128 domain = ~32MB (fine)
- 100,000 sonar samples = ~5MB (trivial)

### 6. Cross-Compilation (optional)
If building from x86 host with Jetson CUDA toolkit:
```bash
make NVCC=/path/to/jetson/cuda/bin/nvcc
```

## License

Part of the Cocapn fleet — SuperInstance org.
