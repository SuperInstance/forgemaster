# Fleet Dependency Map — Source of Truth for Modularization

## Current Repo Relationships (24 repos)

```
eisenstein (crates.io v0.3)
├── constraint-theory-core depends on: eisenstein
├── eisenstein-bench depends on: eisenstein
├── eisenstein-fuzz depends on: eisenstein
├── eisenstein-c (C port, manual)
├── eisenstein-wasm (WASM port, manual)
├── arm-neon-eisenstein-bench (standalone NEON)
├── eisenstein-do178c (Coq proofs, standalone)
└── hexgrid-gen (code generator, standalone)

constraint-theory-core (crates.io v2.0.0)
└── depends on: eisenstein

constraint-theory-ecosystem (meta repo)
├── references: ALL repos (documentation hub)
└── contains: CUDA benchmarks (54 experiments)

flux-lucid (crates.io v0.1.4)
├── re-exports: constraint-theory-llvm, holonomy-consensus
├── depends on: eisenstein (indirect)
└── 46 tests

holonomy-consensus (standalone)
└── no crate deps (pure math)

fleet-coordinate (standalone)
├── depends on: pythagorean48-codes
└── implements: ZHC, beam equilibrium, rigidity (overlaps with holonomy-consensus concepts)

pythagorean48-codes (crates.io v0.1.0)
└── standalone

polyformalism-a2a-python (PyPI)
├── fleet bridge, LLM encoder
└── depends on: constraint-theory (Python package)

polyformalism-a2a-js (npm ready)
├── JS companion
└── zero deps, ESM

constraint-theory-math (research)
└── standalone (sheaf, Heyting, GL(9) proofs)

multi-model-adversarial-testing (research)
└── standalone (methodology)

intent-directed-compilation (research)
└── standalone (AVX-512 technique)

negative-knowledge (research)
└── standalone (cross-domain principle)

sheaf-constraint-synthesis (research)
└── standalone (unified overview)

casting-call (fleet tooling)
└── standalone (model capability database)

cocapn-ai-web (landing page)
└── standalone (static HTML, demos)

superinstance (org README)
└── references all repos
```

## Dependency Clusters

### Cluster 1: Eisenstein Core
```
eisenstein ← constraint-theory-core ← flux-lucid
     ↑
     ├── eisenstein-bench
     ├── eisenstein-fuzz
     ├── eisenstein-c
     ├── eisenstein-wasm
     ├── arm-neon-eisenstein-bench
     ├── eisenstein-do178c
     └── hexgrid-gen
```
Status: Well-structured. Core crate is clean. Ports are independent. Dev tools are independent CLIs.

### Cluster 2: Fleet Coordination
```
holonomy-consensus (pure math)
       ↓ (conceptual, not crate dep)
fleet-coordinate ← pythagorean48-codes
```
Overlap: fleet-coordinate reimplements ZHC concepts from holonomy-consensus. Should either depend on it or share a trait.

### Cluster 3: Research Papers
```
constraint-theory-math
multi-model-adversarial-testing
intent-directed-compilation
negative-knowledge
sheaf-constraint-synthesis
```
All standalone research repos. No code deps. Should they merge into one research repo?

### Cluster 4: Cross-Language
```
polyformalism-a2a-python (PyPI)
polyformalism-a2a-js (npm)
eisenstein-c (C port)
eisenstein-wasm (WASM port)
```
Each is hand-maintained. Could benefit from a shared test suite / spec.

## Observations

1. **Good separation**: Core (eisenstein) → Framework (constraint-theory-core) → Application (flux-lucid) is clean layered architecture
2. **Overlap**: fleet-coordinate and holonomy-consensus share ZHC concepts — need shared trait or dependency
3. **Dev tools scattered**: 3 separate CLI tools (bench, fuzz, hexgrid-gen) could be one `eisenstein-cli` with subcommands
4. **Research sprawl**: 5 standalone research repos with no shared structure
5. **No GPU abstraction**: CUDA benchmarks are in ecosystem repo, not reusable as a crate
6. **Published crates are frozen**: Can't restructure without bumping semver
