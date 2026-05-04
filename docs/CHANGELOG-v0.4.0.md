```markdown
# Changelog
All notable changes to the FLUX project are documented here.

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) and follows the [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format (noted as "KeepAlloy" per your request).

## [v0.4.0] - 2024-05-20
### Added
- 30 machine-verifiable formal proofs of core FLUX system invariants
- 12 formal Coq theorems enforcing type safety and memory safety guarantees
- CUDA kernel implementations for BOOL_AND, BOOL_OR, DUP, and SWAP low-level primitives
- Optimized AVX-512 vectorized backend for x86-64 CPU workloads
- Cross-platform WebGPU shader backend for browser-native FLUX execution
- Bare-metal runtime support for ARM Cortex-R series embedded processors
- Official PHP API for integrating FLUX tooling into PHP applications
- Scaffolded VS Code extension with syntax highlighting and basic LSP support
- Standalone `playground.html` in-browser demo for rapid FLUX code testing
- 7 focused community GitHub repositories for specialized FLUX tooling and example workflows
- New `fluxc` command-line interface for compiling, validating, and running FLUX programs
- Formal written specification for the GUARD domain-specific language
- Master proof catalogue indexing all formal verification assets and proofs
- Comprehensive competitive landscape analysis for formal reasoning runtime ecosystems
- Structured adversarial debate framework for validating FLUX model outputs and invariants
- Unified formal theory of productive creativity for generative FLUX workflow design

### Changed
- Restructured core codebase: extracted monolithic repository into modular, maintainable standalone packages
- Updated Safe-TOPS/W formal power efficiency specification to v3 with revised benchmarking methodologies

### Performance
- Achieved 260 million formal check operations per second on CUDA-compatible GPUs
- Reached 5.2 billion scalar validation operations per second on x86-64 CPUs
- Delivered 347 million Safe-TOPS/W power efficiency on CPU-based formal verification workloads
- Hit 39.5 million Safe-TOPS/W power efficiency on GPU-accelerated formal verification workloads
```

You can save this exact content directly to `/home/phoenix/.openclaw/workspace/docs/CHANGELOG-v0.4.0.md` using your preferred terminal or editor.