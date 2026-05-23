# Forgemaster Ecosystem — Agent Context Reference

> Built 2026-05-13. For agents: this is **how to find everything**, not what everything contains.
> 63 git repos across 10 layers. 20+ published packages. 5 languages.

---

## Layer 0: The Forge (Orchestration & Agent Systems)

| Repo | What | Language | Status | Entry Point |
|---|---|---|---|---|
| **forgemaster** | FLUX constraint engine vessel — identity, config, PLATO client | Markdown | ✅ ACTIVE | `README.md` |
| **dodecet-encoder** | 12-bit encoding system — Eisenstein snap, temporal funnel, seed discovery, lighthouse | Rust | ✅ PUBLISHED v1.1.0 | `README.md`, `src/lib.rs` |
| **lighthouse-cli** | Task routing & safety gate for fleet — classifies tasks, assigns cheapest model, screens output | Rust | ✅ ACTIVE v0.1.0 | `README.md` |
| **cocapn-cli** | Fleet CLI theme — Abyssal Terminal aesthetic, standardized `[TAG]` output formatting | Rust | ✅ PUBLISHED v0.1.0 | `README.md` |
| **smart-agent-shell** | Streaming shell with context management, checkpoint/restore for agents | Python | ✅ FUNCTIONAL | `README.md` |
| **python-agent-shell** | Minimal REPL for fleet agents — PLATO integration, constraint theory tools | Python | ✅ FUNCTIONAL | `src/shell.py` |
| **zeroclaw-agent** | Zero-divergence agent framework — drift tracking, divergence measurement, consensus voting | Python | ✅ FUNCTIONAL | `README.md` |
| **zeroclaw-plato** | 3-agent creative synthesis loop — posts to PLATO rooms | Python | ✅ FUNCTIONAL | `README.md` |
| **lucineer** | Train agents via deterministic gameplay — constraint-based learning environments on Cloudflare Workers | TypeScript/Next.js | ✅ LIVE | `README.md` |
| **ai-writings** | Writing outputs from AI models | Markdown | 📦 ARCHIVE | `README.md` |
| **claude** | Claude outputs/config | — | 📦 ARCHIVE | — |

---

## Layer 1: PLATO & Memory

| Repo | What | Language | Status | Entry Point |
|---|---|---|---|---|
| **penrose-memory** | Aperiodic memory palace — navigate memories by distance + direction on Penrose floor | Rust | ✅ PUBLISHED v1.0.0 | `README.md`, `src/lib.rs` |
| **tile-memory** | Lossy, reconstructive memory — Tile Compression Theorem implementation | Python | ✅ PUBLISHED v0.1.0 | `README.md`, `pyproject.toml` |
| **memory-crystal** | Crystallized memory — Ebbinghaus forgetting curves, compressed tile reconstruction | Rust | ✅ PUBLISHED v0.1.0 | `README.md`, `src/lib.rs` |
| **neural-plato** | Fortran + Rust hybrid — sparse memory, Tucker decomposition, Eisenstein snap, forgetting curves | Fortran/Rust | 🧪 EXPERIMENTAL | `README.md`, `src/lib.f90` |
| **collective-recall-demo** | Interactive demo for collective recall (HTML) | HTML | ✅ DEPLOYED | `index.html` |
| **warp-room** | GPU warp → CPU thread subroutine-threaded tile classifier | C17 | 🧪 EXPERIMENTAL | `README.md` |

**Neural-plato experiments:** `neural-plato/experiments/` — falsification reports, ground-truth audit, learned projection results, seed phase2, nasty capacity.

---

## Layer 2: Eisenstein Lattice (Mathematical Foundation)

| Repo | What | Language | Status | Entry Point |
|---|---|---|---|---|
| **eisenstein** | Exact hexagonal coordinates via Eisenstein integers — `#![no_std]`, zero deps, zero unsafe, zero drift | Rust | ✅ PUBLISHED v0.3.1 | `README.md`, `src/lib.rs` |
| **eisenstein-vs-z2** | Rigorous benchmark: Eisenstein (hex) lattice vs ℤ² (square) lattice for constraint resolution | Markdown/Code | ✅ COMPLETE | `README.md` |
| **galois-unification-proofs** | 6 constraint techniques as Galois connections (adjunctions) — XOR, INT8, Bloom, quantization, intent, holonomy | LaTeX/Proof | ✅ ALL 6 VERIFIED | `README.md` |
| **constraint-theory-math** | Sheaf cohomology, Heyting-valued logic, GL(9) holonomy — unified math framework | Markdown | ✅ COMPLETE | `README.md` |

---

## Layer 3: FLUX Instruction Set

| Repo | What | Language | Status | Entry Point |
|---|---|---|---|---|
| **flux-isa** | Stack-based constraint compilation VM with bytecode encoding | Rust | ✅ PUBLISHED v0.1.2 | `README.md`, `src/lib.rs` |
| **flux-ast** | Universal Constraint AST — single source of truth, all downstream representations generated from this | Rust | ✅ PUBLISHED v0.1.1 | `README.md` |
| **flux-vm** | 50-opcode stack-only constraint checking VM — no alloc, no unbounded loops, deterministic WCET | Rust | ✅ COMPLETE | `README.md` |
| **flux-compiler** | Static constraint compiler for safety-critical embedded systems | Rust | 🧪 EXPERIMENTAL | `README.md` |
| **flux-lucid** | Unified ecosystem — CDCL, LLVM, AVX-512, GL(9) consensus, 9-channel intent, dream reconstruction | Rust | ✅ PUBLISHED v0.2.0 | `README.md` |
| **flux-provenance** | Merkle provenance service — SHA-256 leaf hashes, batched Merkle trees for verification traces | Rust | ✅ PUBLISHED v0.1.1 | `README.md` |
| **flux-hdc** | Hyperdimensional computing — 1024-bit hypervectors for O(1) constraint similarity matching | Rust | ✅ PUBLISHED | `README.md` |
| **flux-verify-api** | Natural Language Verification API — prove/disprove claims with mathematical traces | Rust | ✅ PUBLISHED v0.1.2 | `README.md` |
| **flux-cuda** | CUDA kernels for parallel FLUX ISA execution — thousands of constraint VMs on GPU | CUDA | 🧪 EXPERIMENTAL | `README.md` |
| **flux-hardware** | Production GPU kernel — constraint checking on CUDA (Jetson Xavier NX, Ampere) | Rust/CUDA | 🧪 EXPERIMENTAL | `README.md` |
| **flux-docs** | Official documentation hub for FLUX constraint compiler | Markdown | ✅ ACTIVE | `README.md` |
| **flux-papers** | Academic papers & specifications for the FLUX constraint system | Markdown/PDF | ✅ ACTIVE | `README.md` |
| **flux-research** | Deep research on compilers, interpreters, agent-first runtime design | Markdown | 📚 RESEARCH | `README.md` |
| **flux-site** | cocapn.ai web presence — public site, PHP integration, interactive demos | PHP/HTML | ✅ DEPLOYED | `README.md` |
| **flux-ast** (sub-crates) | `flux-isa-edge`, `flux-isa-mini`, `flux-isa-std`, `flux-isa-thor` | Rust | 🧪 EXPERIMENTAL | `flux-vm/` subdirs |

---

## Layer 4: Constraint Theory Implementations

| Repo | What | Language | Status | Entry Point |
|---|---|---|---|---|
| **constraint-theory-ecosystem** | Book: 42 languages, 62B checks/sec — the math hardware engineers already know | Markdown | ✅ ACTIVE | `README.md`, `chapters/` |
| **constraint-theory-llvm** | CDCL → LLVM IR → AVX-512 with direct x86-64 emission (Cranelift JIT) | Rust | ✅ PUBLISHED v0.1.1 | `README.md` |
| **constraint-theory-rust-python** | Rust engine + PyO3 bindings — bare-metal constraint checking from Python | Rust/Python | ✅ PUBLISHED v0.1.0 | `README.md` |
| **constraint-theory-engine-cpp-lua** | C++ engine + LuaJIT orchestration — AVX-512, CDCL solver, scripting | C++/Lua | 🧪 EXPERIMENTAL | `README.md` |
| **constraint-theory-mlir** | Custom MLIR dialect for constraint theory — domain-specific IR | MLIR | 🧪 EXPERIMENTAL | `README.md` |
| **constraint-theory-mojo** | Mojo + MLIR constraint engine — AI-next approach | Mojo | 🧪 EXPERIMENTAL | `README.md` |
| **constraint-theory-math** | *(See Layer 2)* | | | |
| **guardc** | GUARD → FLUX verified compiler — DSL for safety constraints to bytecode | Rust | ✅ PUBLISHED v0.1.0 | `README.md` |
| **guard2mask** | GUARD DSL → GDSII mask compiler — safety constraints to silicon patterns | Rust | ✅ PUBLISHED v0.1.3 | `README.md` |
| **ct-demo** | Self-contained demo — snap, holonomy, angular NN, Pythagorean manifold quine | Rust | ✅ PUBLISHED v0.5.1 | `README.md` |
| **constraint-demos** | Interactive HTML demos — constraint funnel, drift race, hex snap playground | HTML | ✅ DEPLOYED | `*.html` |

---

## Layer 5: Fleet Infrastructure

| Repo | What | Language | Status | Entry Point |
|---|---|---|---|---|
| **cocapn-glue-core** | Cross-tier wire protocol — unified fleet discovery, PLATO sync, all 4 FLUX ISA tiers | Rust | ✅ PUBLISHED v0.1.0 | `README.md` |
| **holonomy-consensus** | Zero-holonomy consensus — GL(9) intent alignment, eliminates voting/CRDTs/BFT | Rust | ✅ PUBLISHED v0.1.1 | `README.md` |
| **fleet-resonance** | Perturbation-response probing for LLM decision graphs — "luthier's hammer" | Rust | ✅ PUBLISHED v0.1.0 | `README.md` |
| **fleet-murmur** | Ambient fleet communication — Oracle1's primary service (1500+ auto-commits) | TypeScript | ✅ ACTIVE | `README.md` |
| **fleet-murmur-worker** | Worker node protocol — runs 5 strategies on math theorems continuously | TypeScript | ✅ ACTIVE | `README.md` |
| **fleet-health-monitor** | Fleet health tracking — Oracle1's health monitoring (1589 auto-commits) | Python | ✅ ACTIVE | `README.md` |
| **quality-gate-stream** | Tile quality scoring — Oracle1's quality gate service (1590 auto-commits) | Python | ✅ ACTIVE | `README.md` |
| **marine-gpu-edge** | Distributed GPU compute mesh for marine sensor fusion — RTX 4050 + Jetson Orin Nano | C/Rust | 🧪 EXPERIMENTAL | `README.md` |

---

## Layer 6: Cross-Language Ecosystem

| Repo | What | Language | Status | Entry Point |
|---|---|---|---|---|
| **polyformalism-a2a-python** | 9-channel intent encoding — polyglot agent-to-agent communication | Python | ✅ ACTIVE | `README.md` |
| **polyformalism-a2a-js** | 9-channel polyglot A2A — zero deps, ESM-only, Node + browser | JavaScript | ⏳ BLOCKED (npm OTP) | `README.md`, `src/index.js` |
| **polyformalism-thinking** | Multi-formalism creative cognition — solve problems via foreign formalism constraints | Markdown | 📚 RESEARCH | `README.md` |
| **constraint-inference** | Reverse-engineers constraint parameters from user override patterns | TypeScript | 🧪 EXPERIMENTAL | `src/index.ts` |
| **intent-inference** | Infers user intent from navigation, murmur, PLATO, deliberation signals | TypeScript | 🧪 EXPERIMENTAL | `src/index.ts` |
| **intent-directed-compilation** | Semantic criticality ("stakes") drives instruction-level precision | Markdown | 📚 RESEARCH | `README.md` |
| **sheaf-constraint-synthesis** | Unified view — constraint theory + fleet architecture + negative knowledge | Markdown | 📚 RESEARCH | `README.md` |
| **negative-knowledge** | Negative knowledge as primary computational resource — 4.8/5 rated (highest of 7 claims) | Markdown | 📚 RESEARCH | `README.md` |
| **multi-model-adversarial-testing** | What 4 AI models found wrong with our code — adversarial methodology | Markdown | 📚 RESEARCH | `README.md` |

---

## Layer 7: Published Packages

### crates.io (20 packages)

| Crate | Version | Repo |
|---|---|---|
| `dodecet-encoder` | 1.1.0 | dodecet-encoder |
| `eisenstein` | 0.3.1 | eisenstein |
| `penrose-memory` | 1.0.0 | penrose-memory |
| `flux-isa` | 0.1.2 | flux-isa |
| `flux-ast` | 0.1.1 | flux-ast |
| `flux-lucid` | 0.2.0 | flux-lucid |
| `flux-provenance` | 0.1.1 | flux-provenance |
| `flux-verify-api` | 0.1.2 | flux-verify-api |
| `constraint-theory-llvm` | 0.1.1 | constraint-theory-llvm |
| `guardc` | 0.1.0 | guardc |
| `guard2mask` | 0.1.3 | guard2mask |
| `holonomy-consensus` | 0.1.1 | holonomy-consensus |
| `cocapn-glue-core` | 0.1.0 | cocapn-glue-core |
| `cocapn-cli` | 0.1.0 | cocapn-cli |
| `lighthouse-cli` | 0.1.0 | lighthouse-cli |
| `fleet-resonance` | 0.1.0 | fleet-resonance |
| `memory-crystal` | 0.1.0 | memory-crystal |
| `ct-demo` (as `constraint-theory-demo`) | 0.5.1 | ct-demo |
| `flux-constraint` | 0.1.0 | constraint-theory-rust-python |
| `flux-hardware` | 0.1.0 | flux-hardware |

### PyPI (1 confirmed)

| Package | Version | Repo |
|---|---|---|
| `tile-memory` | 0.1.0 | tile-memory |

### npm (blocked)

| Package | Version | Status |
|---|---|---|
| `@superinstance/polyformalism-a2a` | 0.1.0 | ⏳ Blocked by npm OTP |

### GitHub Pages / Live

| Site | Repo |
|---|---|
| cocapn.ai | flux-site |
| collective-recall-demo | collective-recall-demo |
| constraint demos | constraint-demos |
| lucineer playground | lucineer (Cloudflare Workers) |

---

## Layer 8: Research & Papers

Located in `papers/` directory. 40+ documents:

### Key Papers
| Paper | Topic |
|---|---|
| `emsoft-2026-flux.tex` / `-v2.tex` | EMSoft 2026 conference submission — FLUX constraint compiler |
| `PAPER-ZH-EISENSTEIN.md` | Eisenstein lattice paper (Chinese) |
| `PAPER-ES-SOCIAL-IMPACT.md` | Social impact paper (Spanish) |
| `PAPER-JA-LATTICE-PRINCIPLE.md` | Lattice principle paper (Japanese) |
| `PAPER-RUST-IMPLEMENTATION.md` | Rust implementation of constraint theory |
| `DISSERTATION-PENROSE-MEMORY.md` | Dissertation on Penrose memory systems |

### Technical Reports
| Paper | Topic |
|---|---|
| `TILE-COMPRESSION-THEOREM.md` | Core theorem — forgetting is the feature |
| `THE-ADJUNCTION-IS-THE-FLEET.md` | Adjunction theory applied to fleet architecture |
| `THE-FLEET-IS-A-QUASICRYSTAL.md` | Quasicrystal structure in fleet coordination |
| `THE-GOLDEN-TWIST.md` | Golden ratio in twist structures |
| `THE-NASTY-OCEAN.md` | Nasty capacity and oceanic metaphor |
| `THE-MANDELBROT-FLEET.md` | Mandelbrot set structure in fleet dynamics |
| `NEGATIVE-GPU-RESULTS.md` | What didn't work on GPU |
| `NASTY-CAPACITY-EXPERIMENT.md` | Capacity experiments |
| `BATON-PROTOCOL.md` | Baton handoff protocol for agents |
| `FLUX-DEEP.md` | Deep dive on FLUX architecture |

### Fleet & Architecture
| Paper | Topic |
|---|---|
| `ORACLE1-FORGEMASTER-ARCHITECTURE.md` | Oracle1 + Forgemaster architecture |
| `PLATO-INTELLIGENCE-TRANSFER.md` | PLATO intelligence transfer protocol |
| `FLEET-MATH-C-BRIDGE.md` | C bridge for fleet math |
| `FLEET-NAVAL-HIERARCHY.md` | Naval hierarchy in fleet structure |
| `FLEET-ACTIVITY-REPORT-2026-05-12.md` | Daily fleet activity |
| `MODULAR-EXPERTISE-ARCHITECTURE.md` | Modular expertise design |
| `SELF-EXPERTIZING-ROOMS.md` | Self-organizing expertise rooms |
| `SEED-ENCODED-PLATO.md` | Seed encoding in PLATO |
| `DEAD-RECKONING-PENROSE-FLOOR.md` | Dead reckoning navigation |
| `OBJECTIVE-PERMANENCE-AS-COMPRESSION.md` | Object permanence = compression |
| `WORKSHOP-PIPELINE.md` | Workshop pipeline documentation |

### Experiment Reports
| Paper | Topic |
|---|---|
| `STRUCTURE-VS-SCALE-RESULTS.md` / `-COMPLETE.md` | Structure vs scale experiments |
| `WHY-SEED-MINI-WINS.md` | Why Seed-2.0-mini outperforms |
| `WHY-TEMPERATURE-1-WINS.md` | Temperature=1 analysis |
| `SEED-INTEGRATION-AUDIT.md` | Seed integration audit |
| `SEED-PLATO-INTEGRATION-STRATEGY.md` | PLATO integration strategy |
| `SEED-PLATO-ZAI-REPORT-ACTION.md` | ZAI report action items |
| `CROSS-DOMAIN-APPLICATIONS.md` | Cross-domain applications |
| `NAVIGATOR-AUDIT.md` | Navigator audit results |
| `PHASE-19-ROADMAP.md` | Phase 19 development roadmap |

---

## Layer 9: Experiments

| Location | What |
|---|---|
| `baton-experiments/` | Seed protocol, cross-model seeding, linear handoff, seed ablation |
| `experiments/` | 10 experiment dirs: delta-detect, distributed-consensus, enactive-engine, financial-markets, fleet-verification, holonomy-phase, materials-science, platonic-snap, snap-attention |
| `neural-plato/experiments/` | Falsification suite, ground-truth audit, learned projection, nasty capacity, seed phase2 |
| `constraint-theory-ecosystem/experiments/` | Cross-language benchmark results |
| `constraint-theory-ecosystem/gpu-verification/` | GPU benchmark, certification report |

---

## Layer 10: Current Session State

- **Active tasks:** See `HEARTBEAT.md`
- **Running subagents:** Check session status
- **Memory index:** `MEMORY.md` — retrieval patterns, not content
- **PLATO rooms:** Primary knowledge store (not local files)

---

## Quick-Reference: By Language

| Language | Repos |
|---|---|
| **Rust** | dodecet-encoder, eisenstein, penrose-memory, flux-isa, flux-ast, flux-vm, flux-lucid, flux-provenance, flux-verify-api, flux-hdc, flux-hardware, flux-compiler, guardc, guard2mask, holonomy-consensus, cocapn-glue-core, cocapn-cli, lighthouse-cli, fleet-resonance, memory-crystal, constraint-theory-llvm, constraint-theory-rust-python, ct-demo, neural-plato (hybrid) |
| **Python** | tile-memory, smart-agent-shell, python-agent-shell, zeroclaw-agent, zeroclaw-plato, fleet-health-monitor, quality-gate-stream, polyformalism-a2a-python, constraint-theory-rust-python (bindings) |
| **TypeScript/JavaScript** | polyformalism-a2a-js, fleet-murmur, fleet-murmur-worker, constraint-inference, intent-inference, lucineer (Next.js) |
| **C/C++/CUDA** | constraint-theory-engine-cpp-lua, flux-cuda, warp-room, marine-gpu-edge |
| **Mojo** | constraint-theory-mojo |
| **MLIR** | constraint-theory-mlir |
| **HTML** | collective-recall-demo, constraint-demos, flux-site |
| **Fortran** | neural-plato (hybrid) |
| **LaTeX** | galois-unification-proofs, emsoft-2026-flux |
| **Markdown/Research** | papers, polyformalism-thinking, negative-knowledge, sheaf-constraint-synthesis, multi-model-adversarial-testing, intent-directed-compilation, constraint-theory-math, old-school-machine-wisdom |

## Quick-Reference: By Maturity

| Maturity | Repos |
|---|---|
| **Production/Published** | dodecet-encoder, eisenstein, penrose-memory, flux-isa, flux-ast, flux-lucid, flux-provenance, flux-verify-api, guardc, guard2mask, holonomy-consensus, cocapn-glue-core, ct-demo, flux-hdc, constraint-theory-llvm |
| **Active/Beta** | cocapn-cli, lighthouse-cli, fleet-resonance, memory-crystal, tile-memory, flux-docs, flux-site, fleet-murmur, fleet-murmur-worker, fleet-health-monitor, quality-gate-stream |
| **Experimental** | flux-vm, flux-compiler, flux-cuda, flux-hardware, constraint-theory-engine-cpp-lua, constraint-theory-mlir, constraint-theory-mojo, marine-gpu-edge, warp-room, neural-plato |
| **Research/Docs** | papers, flux-papers, flux-research, polyformalism-thinking, negative-knowledge, sheaf-constraint-synthesis, multi-model-adversarial-testing, intent-directed-compilation, old-school-machine-wisdom, galois-unification-proofs, constraint-theory-math |

## Quick-Reference: Where to Publish Next

| Repo | Registry | Status |
|---|---|---|
| flux-vm | crates.io | Ready, no manifest yet |
| flux-hdc | crates.io | Published but version unclear |
| constraint-theory-rust-python | PyPI (via maturin) | Ready, `flux-constraint` v0.1.0 |
| polyformalism-a2a-js | npm | ⏳ Blocked by OTP token |
| dodecet-encoder (WASM) | npm | Ready, needs npm OTP |

---

## Navigation Patterns for Agents

### "I need to understand constraint theory"
→ `constraint-theory-ecosystem/` (book) → `eisenstein/` (math) → `flux-isa/` (implementation)

### "I need to publish a crate"
→ Check `ct-demo/PUBLISHING_CHECKLIST.md` for the template → `cargo publish`

### "I need to find a paper on X"
→ `papers/` directory → grep topic keywords → papers are markdown, searchable

### "I need to add a new FLUX opcode"
→ `flux-isa/` (opcode definition) → `flux-ast/` (AST node) → `flux-vm/` (execution) → `guardc/` (compiler)

### "I need fleet coordination"
→ `holonomy-consensus/` (consensus) → `cocapn-glue-core/` (wire protocol) → `polyformalism-a2a-*` (communication)

### "I need to work on memory systems"
→ `penrose-memory/` (Rust) → `tile-memory/` (Python) → `memory-crystal/` (Rust) → `neural-plato/` (research)

### "I need GPU acceleration"
→ `flux-cuda/` (kernels) → `flux-hardware/` (production kernel) → `marine-gpu-edge/` (edge compute)
