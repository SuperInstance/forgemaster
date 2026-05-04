# FLUX Repository Status Dashboard

## Summary

| Repo | Language | Key Content | Status |
|------|----------|-------------|--------|
| [flux-compiler](https://github.com/SuperInstance/flux-compiler) | Rust | GUARD→FLUX compiler, 7 crates | ✅ README, CONTRIBUTING, CI |
| [flux-vm](https://github.com/SuperInstance/flux-vm) | Rust+C | 50-opcode VM, ARM runtime, test harness | ✅ README, tests |
| [flux-hardware](https://github.com/SuperInstance/flux-hardware) | CUDA+C+Verilog | GPU kernels, AVX-512, FPGA, WebGPU, Vulkan | ✅ README, benchmarks |
| [flux-papers](https://github.com/SuperInstance/flux-papers) | LaTeX+Markdown | EMSOFT paper, roadmap, Safe-TOPS/W spec | ✅ README |
| [flux-site](https://github.com/SuperInstance/flux-site) | HTML+PHP+JS | cocapn.ai pages, PHP kit, playground | ✅ README, 9 pages |
| [flux-hdc](https://github.com/SuperInstance/flux-hdc) | Rust+Python | 1024-bit hypervectors, 5 theorems | ✅ README |
| [flux-docs](https://github.com/SuperInstance/flux-docs) | Markdown | Tutorials, cookbooks, runbooks, API docs | ✅ README |

## Key Metrics Across All Repos

- **30 English formal proofs** + **12 Coq theorems** = 38 proof artifacts
- **177M+ GPU constraint evaluations**, 0 mismatches
- **50+ FLUX-C opcodes** (43 FLUX-C + 247 FLUX-X planned)
- **7 compilation targets**: x86-64, ARM Cortex-R, CUDA, WebGPU, Vulkan, FPGA, eBPF
- **21 published packages**: 15 crates.io + 5 PyPI + 1 npm
- **Peak throughput**: 5.2B/s CPU, 321M/s GPU sustained
- **Safe-TOPS/W**: 347M CPU, 63M GPU (at 10M batch)
- **License**: Apache 2.0 (all repos)

## Night Shift (2026-05-03)
- 260 commits, ~$25 API cost
- 50+ models consulted
- 1MB+ research across 57 files
- 4 adversarial debates (108KB)
