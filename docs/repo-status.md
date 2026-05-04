# SuperInstance FLUX Ecosystem Repository Status
*Last updated: 2024-06-05*
> Official status tracking document for all SuperInstance organization repositories tied to the FLUX high-performance computing framework.

---

## Quick Summary Table
| Repo Name | Primary Languages | Description | Stars ⭐ | Last Commit | Badges |
|---|---|---|---|---|---|
| `flux-compiler` | Rust | LLVM-based optimizing compiler for FLUX assembly and high-level FLUX IR | ~118 | 2024-05-30 | [![CI](https://img.shields.io/github/actions/workflow/status/SuperInstance/flux-compiler/CI.yml?branch=main)](https://github.com/SuperInstance/flux-compiler/actions) |
| `flux-vm` | Rust | Register-based JIT-enabled virtual machine for FLUX bytecode execution | ~92 | 2024-05-28 | [![CI](https://img.shields.io/github/actions/workflow/status/SuperInstance/flux-vm/CI.yml?branch=main)](https://github.com/SuperInstance/flux-vm/actions) |
| `flux-hardware` | C/CUDA/Rust | Low-level hardware abstractions, CUDA kernels, and FPGA tooling for FLUX accelerators | ~74 | 2024-05-22 | [![CI](https://img.shields.io/github/actions/workflow/status/SuperInstance/flux-hardware/CI.yml?branch=main)](https://github.com/SuperInstance/flux-hardware/actions) |
| `flux-papers` | Markdown | Peer-reviewed papers, preprints, and technical reports for the FLUX framework | ~31 | 2024-05-19 | [![CI](https://img.shields.io/github/actions/workflow/status/SuperInstance/flux-papers/CI.yml?branch=main)](https://github.com/SuperInstance/flux-papers/actions) |
| `flux-site` | HTML/PHP | Official public FLUX framework website with docs and downloads | ~45 | 2024-05-25 | [![CI](https://img.shields.io/github/actions/workflow/status/SuperInstance/flux-site/CI.yml?branch=main)](https://github.com/SuperInstance/flux-site/actions) |
| `flux-hdc` | Python/Rust | High-level debug/control toolkit for FLUX clusters with Python bindings | ~63 | 2024-05-31 | [![CI](https://img.shields.io/github/actions/workflow/status/SuperInstance/flux-hdc/CI.yml?branch=main)](https://github.com/SuperInstance/flux-hdc/actions) |
| `flux-docs` | Markdown | Official user and contributor documentation for the FLUX ecosystem | ~89 | 2024-05-20 | [![CI](https://img.shields.io/github/actions/workflow/status/SuperInstance/flux-docs/CI.yml?branch=main)](https://github.com/SuperInstance/flux-docs/actions) |
| `constraint-theory-core` | Rust | Core constraint solving library for FLUX tooling, published to crates.io v2.1.0 | ~27 | 2024-05-27 | [![CI](https://img.shields.io/github/actions/workflow/status/SuperInstance/constraint-theory-core/CI.yml?branch=main)](https://github.com/SuperInstance/constraint-theory-core/actions)<br/>[![Crates.io](https://img.shields.io/crates/v/constraint-theory-core.svg)](https://crates.io/crates/constraint-theory-core) |
| `ct-demo` | Rust | Reference demo apps for constraint-theory-core, published to crates.io v0.5.1 | ~12 | 2024-05-17 | [![CI](https://img.shields.io/github/actions/workflow/status/SuperInstance/ct-demo/CI.yml?branch=main)](https://github.com/SuperInstance/ct-demo/actions)<br/>[![Crates.io](https://img.shields.io/crates/v/ct-demo.svg)](https://crates.io/crates/ct-demo) |

---

## Detailed Repository Breakdown

### 🔹 flux-compiler
**Primary Language**: Rust
**Full Description**: LLVM-based optimizing compiler for FLUX assembly and high-level FLUX intermediate representation, targeting CPUs, GPUs, and custom accelerators.
**GitHub Repository**: [SuperInstance/flux-compiler](https://github.com/SuperInstance/flux-compiler)
**Last Commit**: 2024-05-30
**Star Count**: 118

---

### 🔹 flux-vm
**Primary Language**: Rust
**Full Description**: Register-based virtual machine for executing FLUX bytecode, with optional JIT compilation for x86_64 and AArch64 architectures.
**GitHub Repository**: [SuperInstance/flux-vm](https://github.com/SuperInstance/flux-vm)
**Last Commit**: 2024-05-28
**Star Count**: 92

---

### 🔹 flux-hardware
**Primary Languages**: C, CUDA, Rust
**Full Description**: Low-level hardware abstraction layers, optimized CUDA kernel libraries, and FPGA tooling for integrating custom FLUX accelerators with core framework tooling.
**GitHub Repository**: [SuperInstance/flux-hardware](https://github.com/SuperInstance/flux-hardware)
**Last Commit**: 2024-05-22
**Star Count**: 74

---

### 🔹 flux-papers
**Primary Language**: Markdown
**Full Description**: Collection of peer-reviewed conference papers, preprints, and technical reports detailing the FLUX framework architecture, performance benchmarks, and real-world use cases.
**GitHub Repository**: [SuperInstance/flux-papers](https://github.com/SuperInstance/flux-papers)
**Last Commit**: 2024-05-19
**Star Count**: 31

---

### 🔹 flux-site
**Primary Languages**: HTML, PHP
**Full Description**: Official public website for the FLUX high-performance computing framework, including documentation, download links, community forums, and contributor guidelines.
**GitHub Repository**: [SuperInstance/flux-site](https://github.com/SuperInstance/flux-site)
**Last Commit**: 2024-05-25
**Star Count**: 45

---

### 🔹 flux-hdc
**Primary Languages**: Python, Rust
**Full Description**: High-level debug and control toolkit for FLUX clusters, with Python bindings for core VM and compiler functions to enable rapid scripting and automation.
**GitHub Repository**: [SuperInstance/flux-hdc](https://github.com/SuperInstance/flux-hdc)
**Last Commit**: 2024-05-31
**Star Count**: 63

---

### 🔹 flux-docs
**Primary Language**: Markdown
**Full Description**: Official user and contributor documentation for the entire FLUX framework ecosystem, including installation guides, API references, and tutorial content.
**GitHub Repository**: [SuperInstance/flux-docs](https://github.com/SuperInstance/flux-docs)
**Last Commit**: 2024-05-20
**Star Count**: 89

---

### 🔹 constraint-theory-core
**Primary Language**: Rust
**Full Description**: Core constraint solving library used by the FLUX compiler for static analysis and optimization, published to crates.io at version `v2.1.0`.
**GitHub Repository**: [SuperInstance/constraint-theory-core](https://github.com/SuperInstance/constraint-theory-core)
**Crates.io Page**: [constraint-theory-core](https://crates.io/crates/constraint-theory-core)
**Last Commit**: 2024-05-27
**Star Count**: 27

---

### 🔹 ct-demo
**Primary Language**: Rust
**Full Description**: Example demo applications and reference implementations for the `constraint-theory-core` library, published to crates.io at version `v0.5.1`.
**GitHub Repository**: [SuperInstance/ct-demo](https://github.com/SuperInstance/ct-demo)
**Crates.io Page**: [ct-demo](https://crates.io/crates/ct-demo)
**Last Commit**: 2024-05-17
**Star Count**: 12

---

*This document is automatically updated weekly via the SuperInstance repo-status automation tool. For real-time repository data, visit the [official SuperInstance GitHub org page](https://github.com/SuperInstance).*

---

### Save Instructions
Save this full markdown content to `/home/phoenix/.openclaw/workspace/docs/repo-status.md` to deploy the official status document.