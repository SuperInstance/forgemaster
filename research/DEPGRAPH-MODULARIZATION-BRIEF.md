# DepGraph-GPU Implementation + Fleet Modularization Brief

## Objective
Plan and implement:
1. **DepGraph-GPU** — GPU-accelerated dependency graph analyzer for 1,400+ repos
2. **Fleet modularization** — Identify synergies across existing systems, propose unified architecture

## Current Fleet Stack

### Repos (Key Ones)
- `SuperInstance/constraint-theory-core` — Rust constraint propagation (crates.io)
- `SuperInstance/constraint-theory-ecosystem` — 54 GPU experiments, benchmarks
- `SuperInstance/eisenstein` — Hex arithmetic crate (crates.io, 600 LOC)
- `SuperInstance/flux-lucid` — Intent vectors + alignment (crates.io)
- `SuperInstance/holonomy-consensus` — Topological consensus without quorum
- `SuperInstance/fleet-coordinate` — Multi-agent spatial coordination
- `SuperInstance/polyformalism-a2a-python` — Fleet bridge (PyPI)
- `SuperInstance/polyformalism-a2a-js` — JS companion (npm ready)
- `SuperInstance/pythagorean48-codes` — Exact direction encoding
- `SuperInstance/eisenstein-bench` — CLI benchmark suite
- `SuperInstance/eisenstein-fuzz` — Property-based fuzzing
- `SuperInstance/eisenstein-c` — C port, 1KB .text
- `SuperInstance/eisenstein-wasm` — WASM port
- `SuperInstance/arm-neon-eisenstein-bench` — ARM NEON benchmarks
- `SuperInstance/eisenstein-do178c` — DO-178C certification (42 Coq theorems)
- `SuperInstance/hexgrid-gen` — Code generator for hex grid lookup tables
- `SuperInstance/constraint-theory-math` — Sheaf + Heyting + GL(9) proofs
- `SuperInstance/multi-model-adversarial-testing` — Model eval methodology
- `SuperInstance/intent-directed-compilation` — AVX-512 technique
- `SuperInstance/negative-knowledge` — Cross-domain principle
- `SuperInstance/sheaf-constraint-synthesis` — Unified overview
- `SuperInstance/casting-call` — Model capability database
- `SuperInstance/cocapn-ai-web` — Landing page + demos
- `SuperInstance/superinstance` — Org README

### Infrastructure
- **OpenClaw** — Agent runtime on eileen (WSL2, x64, RTX 4050)
- **PLATO** — External knowledge base (1141+ rooms, HTTP API at 147.224.38.131:8847)
- **I2I Protocol** — Git-based inter-agent communication (for-fleet/ bottles)
- **Matrix** — Fleet chat (send currently broken)
- **9 agents** in Cocapn fleet

### Hardware
- eileen: WSL2, x64, RTX 4050 (Ada), CUDA 11.5
- No Apple Silicon (Metal not directly usable — use wgpu/Vulkan/CUDA instead)

### Language/Runtime Constraints
- rustc 1.95.0 (was 1.75.0, recently upgraded)
- CUDA 11.5 (sm_86 target, no sm_89)
- Python 3.x, Node.js 22

## DepGraph-GPU: What We Need

A GPU-accelerated dependency graph analyzer that can:
1. Parse `Cargo.toml`, `package.json`, `go.mod`, `pom.xml`, etc. across 1,400+ repos
2. Build a unified dependency graph (which repo depends on which)
3. Detect: circular deps, outdated deps, security vulns, duplicate deps
4. Compute: critical path, transitive closure, impact analysis ("if X changes, what breaks?")
5. Visualize: generate DOT/mermaid graphs for fleet overview
6. Integrate: OpenClaw agent, PLATO rooms, I2I notifications

### GPU Acceleration Points
- Parallel topological sort (10K+ nodes)
- Parallel BFS for transitive closure
- Parallel hash for integrity checking
- Parallel pattern matching in dep files
- Matrix operations for dependency similarity

### Implementation Language
Since we're on CUDA (RTX 4050), NOT Metal:
- Rust + `cudarc` or `rust-cuda` for GPU kernels
- OR: C/C++ + CUDA 11.5
- CPU fallback for non-GPU machines

## Modularization Questions

1. **Shared kernel**: Should constraint-theory-core, eisenstein, and flux-lucid share a common `constraint-kernel` crate?
2. **GPU abstraction**: Can we unify the CUDA benchmarks (constraint-theory-ecosystem) with the new DepGraph-GPU under a single `gpu-tools` crate?
3. **Fleet coordinate vs holonomy-consensus**: These overlap conceptually — should they merge or stay separate with a shared trait?
4. **Dev tools unification**: eisenstein-bench, eisenstein-fuzz, hexgrid-gen — should these be subcommands of a single `eisenstein-tools` CLI?
5. **Cross-language ports**: Python/JS/WASM/C — should they be generated from a single spec or hand-maintained?
6. **CI/CD unification**: Each repo has its own CI — should we have a shared workflow template?
7. **Testing infrastructure**: Differential testing works — can we generalize the 60M-input zero-mismatch approach?

## Expected Output

1. **DepGraph-GPU implementation plan** — file structure, module breakdown, kernel designs, API surface
2. **Modularization proposal** — which repos merge, which stay separate, shared traits/crates
3. **Implementation order** — what ships first for maximum value
4. **Concrete file trees** — for any new repos or restructured repos
