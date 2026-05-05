# flux-hardware

High-performance constraint propagation kernels across silicon generations.

## Overview

`flux-hardware` delivers portable, vectorized constraint-satisfaction primitives that scale from embedded FPGAs to data-center GPUs. The library unifies six backend targets under a single ISA-inspired interface: CUDA for NVIDIA GPUs, AVX-512 for x86 CPUs, Vulkan/WebGPU for cross-vendor graphics compute, SystemVerilog for FPGA acceleration, eBPF for kernel-space enforcement, and Fortran for legacy HPC integration.

Every backend implements the same three core operations—**bitmask AC-3** (arc consistency), **flux VM batch** (batched constraint evaluation), and **domain reduce** (value elimination)—so workloads can migrate across hardware without algorithmic changes. The code is hand-optimized at the assembly, RTL, and shader level; there are no hidden frameworks between the algorithm and the silicon.

The repository is organized by backend rather than by algorithm. This keeps build systems simple, lets CI pipelines target only the hardware they own, and makes it trivial to vendor a single directory into a larger project. All kernels use plain C structs for configuration, so language bindings can be generated with standard FFI tooling instead of custom wrappers.

## Hardware Targets

| Target | Technology | Key Files | Typical Use Case |
|---|---|---|---|
| GPU | CUDA 12+ | `cuda/bitmask_ac3.cu`, `flux_vm_batch.cu`, `domain_reduce.cu` | Data-center batch solving |
| x86 CPU | AVX-512 C | `cpu/avx512_*.c` | Low-latency single-node inference |
| Cross-GPU | Vulkan / WebGPU | `gpu_shaders/*.comp`, `webgpu/*.wgsl` | Browser & mobile compute |
| FPGA | SystemVerilog | `fpga/flux_checker_top.sv` | Deterministic edge deployment |
| Kernel | eBPF | `ebpf/constraint_enforce.bpf.c` | In-kernel policy verification |
| HPC | Fortran 2008 | `fortran/constraint_kernels.f90` | Legacy climate/physics codes |

## Quick Start

Each backend directory is self-contained. Pick your target and run the commands below.

**CUDA**
```bash
cd cuda && make ARCH=sm_89 && ./bench_bitmask_ac3
```

**AVX-512**
```bash
cd cpu && make avx512 && ./bench_cpu --threads=1
```

**Vulkan / WebGPU**
```bash
cd gpu_shaders && ./build_shaders.py && cargo run --example wgpu_runner
```

**FPGA**
```bash
cd fpga && vivado -mode batch -source synth.tcl
```

**eBPF**
```bash
cd ebpf && clang -target bpf -c constraint_enforce.bpf.c -o enforce.o
sudo bpftool prog load enforce.o /sys/fs/bpf/flux_enforce
```

**Fortran**
```bash
cd fortran && gfortran -O3 -march=native constraint_kernels.f90 -o fkernel && ./fkernel
```

## Benchmark Results

All numbers reported in billions of constraint checks per second (B/s).

| Backend | Threads / Units | Throughput |
|---|---|---|
| AVX-512 | 1 | **22.3 B/s** |
| AVX-512 | Multi-threaded | **70.1 B/s** |
| CUDA (A100) | 1 GPU | **1.02 B/s** |

AVX-512 single-thread performance is measured on an Intel Sapphire Rapids clocked at 3.4 GHz with Turbo disabled. Multi-threaded scaling uses 32 physical cores (64 threads) and achieves roughly 3.1× parallel efficiency. The CUDA figure is from an NVIDIA A100 80 GB PCIe running CUDA 12.4; throughput is memory-bandwidth limited on the domain-reduce kernel.

## Architecture

```
┌─────────────────────────────────────────────┐
│         flux-hardware  ( unified API )      │
├──────────┬──────────┬──────────┬────────────┤
│  CUDA    │ AVX-512  │  Vulkan  │   FPGA     │
│  Kernels │    C     │  WGSL    │    SV      │
│  .cu     │   .c     │  .comp   │   .sv      │
├──────────┴──────────┴──────────┼────────────┤
│        Domain Reduce           │  eBPF /    │
│        Bitmask AC-3            │  Fortran   │
│        Flux VM Batch           │  Backends  │
└────────────────────────────────┴────────────┘
```

The diagram above shows the layered design. The top row represents the backend-specific implementations; the bottom row lists the three shared primitives. New silicon targets only need to implement these three kernels to gain full compatibility with the rest of the ecosystem. Because each primitive is stateless and operates on flat memory buffers, integration into an existing scheduler or runtime requires only a thin wrapper around the launch call.

## Building

Each subdirectory is self-contained and carries its own Makefile or build script. There is no top-level build system—this is intentional so that CI pipelines can compile only the targets they intend to test.

**Prerequisites**
- GNU Make, CMake ≥ 3.20, or Cargo (depending on target)
- CUDA Toolkit 12.0+ (GPU path)
- Clang/LLVM 16+ (eBPF and Vulkan SPIR-V)
- Intel oneAPI or GCC 13+ (AVX-512)
- Vivado 2023.2+ (FPGA path)
- gfortran 12+ (Fortran path)

Run `make check` inside any backend directory to execute its unit tests. Run `make bench` to reproduce the published throughput numbers. For a full validation sweep across every supported target, run `./scripts/full_check.sh` from the repository root. The script returns a consolidated JSON report and exits with a non-zero status if any backend fails its correctness suite.

If you are cross-compiling for an embedded or FPGA target, set the `FLUX_TARGET` environment variable before invoking make. Valid values are `x86_64`, `aarch64`, `sm_80`, `sm_89`, `sm_90`, `xilinx_u55c`, and `agilex7`. The build system will adjust compiler flags, memory alignments, and kernel tile sizes automatically.

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) or http://www.apache.org/licenses/LICENSE-2.0 for details.
