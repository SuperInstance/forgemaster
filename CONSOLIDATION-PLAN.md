# Consolidation Plan — 180 Workspace Directories

**Author:** Forgemaster ⚒️  
**Date:** 2026-05-15  
**Status:** Design doc — no moves, no deletes, just the plan.

---

## Overview

180 directories in `/home/phoenix/.openclaw/workspace/`. This plan groups them into three tiers:

1. **Core (keep active)** — active infrastructure, services, operational dirs
2. **SuperRepos (merge candidates)** — groups of related repos that should become one
3. **Archive** — stale experiments, one-offs, completed research

79 directories have `.git` (real repos). 79 have tests. Considerable overlap — most repos with tests are also git repos.

---

## 1. Core (Keep Active) — 23 directories

These are operational, actively used, or infrastructure-critical.

| Directory | Purpose | Tests | Git |
|-----------|---------|:-----:|:---:|
| `bin/` | Fleet tools (fm-fleet-check, fm-inbox, etc.) | ✅ | ❌ |
| `memory/` | Session memory store | ✅ | ❌ |
| `references/` | Fleet reference docs | ❌ | ❌ |
| `scripts/` | Utility scripts | ✅ | ❌ |
| `skills/` | OpenClaw skills | ❌ | ❌ |
| `state/` | Runtime state | ❌ | ❌ |
| `tests/` | Workspace-level tests | ✅ | ❌ |
| `for-fleet/` | I2I bottle delivery (outgoing) | ✅ | ❌ |
| `from-fleet/` | I2I bottle delivery (incoming) | ❌ | ❌ |
| `forgemaster/` | Forgemaster vessel repo | ✅ | ✅ |
| `forgemaster-shell/` | Forgemaster shell theme | ❌ | ❌ |
| `i2i/` | I2I protocol workspace | ✅ | ❌ |
| `core/` | PLATO-native agent infrastructure | ❌ | ❌ |
| `docs/` | Workspace documentation | ❌ | ❌ |
| `papers/` | Research papers | ✅ | ✅ |
| `research/` | Deep research (90+ docs) | ✅ | ❌ |
| `experiments/` | Active experiments | ✅ | ❌ |
| `output/` | Generated output | ❌ | ❌ |
| `target/` | Build artifacts | ✅ | ❌ |
| `archive/` | Already-archived content | ❌ | ❌ |
| `demos/` | Live demos | ❌ | ❌ |
| `simulators/` | Interactive simulators | ❌ | ❌ |
| `editors/` | Editor configs (flux-guard, guard-language) | ❌ | ❌ |

---

## 2. SuperRepos (Merge Candidates)

### 2A. Constraint Theory → `constraint-theory` (1 mega-repo from 22 dirs)

**Priority: 1 (Critical)**

The constraint theory universe is the largest sprawl — 22 directories that all orbit the same mathematical core. Most share types, test patterns, and have circular cross-references.

| Directory | What It Contains | Tests | Git | Merge Priority |
|-----------|-----------------|:-----:|:---:|:--------------:|
| `constraint-theory-ecosystem/` | Umbrella README + 42-language listings | ✅ | ✅ | Hub — becomes the mega-repo |
| `constraint-theory-py/` | Pure Python CT toolkit (v0.3.0) | ✅ | ✅ | 1 — core library |
| `constraint-theory-math/` | Sheaf cohomology, Heyting logic, GL(9) | ✅ | ✅ | 1 — formal proofs |
| `constraint-theory-llvm/` | CDCL → LLVM IR → AVX-512 | ✅ | ✅ | 1 — compiler backend |
| `constraint-theory-mlir/` | Custom MLIR dialect for CT | ✅ | ✅ | 1 — compiler IR |
| `constraint-theory-mojo/` | Mojo + MLIR engine | ✅ | ✅ | 2 — alt backend |
| `constraint-theory-core-cuda/` | CUDA constraint kernels | ✅ | ✅ | 2 — GPU kernel |
| `constraint-theory-engine-cpp-lua/` | C++ engine + LuaJIT orchestration | ✅ | ✅ | 2 — alt engine |
| `constraint-theory-rust-python/` | Rust engine + PyO3 bindings | ✅ | ✅ | 1 — main engine |
| `constraint-avx512/` | Single AVX-512 header | ❌ | ❌ | 3 — merge into -llvm |
| `constraint-cuda/` | Single CUDA header | ❌ | ❌ | 3 — merge into -core-cuda |
| `constraint-mt/` | Multi-threaded header | ❌ | ❌ | 3 — merge into -core |
| `constraint-wasm/` | WASM constraint module | ✅ | ❌ | 3 — merge into -py |
| `constraint-demos/` | HTML demos (funnel, drift-race) | ❌ | ✅ | 3 — merge into demos/ |
| `constraint-inference/` | CI-tested inference engine | ✅ | ✅ | 2 — merge into -py |
| `constraints/` | 248 constraint definitions (10 industries) | ✅ | ❌ | 2 — data layer |
| `ct-bridge-npm/` | Node.js bridge | ✅ | ❌ | 2 — language binding |
| `ct-demo/` | Self-contained demo | ✅ | ❌ | 3 — merge into demos/ |
| `guard-constraints/` | GUARD DSL constraint files (5 domains) | ❌ | ❌ | 2 — merge into guard-dsl |
| `guard-dsl/` | GUARD DSL compiler → FLUX bytecode | ❌ | ❌ | 2 — merge with guardc |
| `guard2mask/` | GUARD → GDSII silicon mask | ✅ | ✅ | 2 — merge with guard-dsl |
| `guardc/` | GUARD → FLUX verified compiler | ✅ | ✅ | 2 — merge with guard-dsl |

**Proposed Structure:**
```
constraint-theory/
├── core/           ← constraint-theory-py
├── math/           ← constraint-theory-math
├── engines/
│   ├── llvm/       ← constraint-theory-llvm
│   ├── mlir/       ← constraint-theory-mlir
│   ├── mojo/       ← constraint-theory-mojo
│   ├── cpp-lua/    ← constraint-theory-engine-cpp-lua
│   ├── rust-py/    ← constraint-theory-rust-python
│   └── cuda/       ← constraint-theory-core-cuda + constraint-cuda
├── guard/          ← guard-dsl, guardc, guard2mask, guard-constraints
├── bindings/
│   ├── wasm/       ← constraint-wasm
│   ├── npm/        ← ct-bridge-npm
│   └── inference/  ← constraint-inference
├── headers/        ← constraint-avx512, constraint-mt
├── constraints/    ← constraints/ (248 industry definitions)
└── demos/          ← constraint-demos, ct-demo
```

---

### 2B. FLUX → `flux` (1 mega-repo from 31 dirs)

**Priority: 1 (Critical)**

The FLUX ecosystem is the second-largest sprawl — ISA implementations, compilers, tools, and deployments that all share the same bytecode format and architecture.

| Directory | What It Contains | Tests | Git | Merge Priority |
|-----------|-----------------|:-----:|:---:|:--------------:|
| `flux-isa/` | Core ISA spec (crates.io v0.1.2) | ✅ | ✅ | 1 — hub |
| `flux-isa-c/` | C99 VM implementation | ✅ | ✅ | 1 — lang impl |
| `flux-isa-mini/` | Bare-metal ARM Cortex-M (no_std) | ❌ | ❌ | 1 — lang impl |
| `flux-isa-std/` | Embedded Linux VM | ✅ | ✅ | 1 — lang impl |
| `flux-isa-edge/` | Async runtime for Jetson | ✅ | ✅ | 1 — lang impl |
| `flux-isa-thor/` | GPU-class edge runtime | ✅ | ✅ | 1 — lang impl |
| `flux-compiler/` | Static constraint compiler | ❌ | ✅ | 1 — compiler |
| `flux-compiler-workspace/` | Compiler workspace/benches | ✅ | ❌ | 2 — merge into compiler |
| `flux-vm/` | 50-opcode stack VM | ✅ | ✅ | 1 — runtime |
| `flux-ast/` | Universal constraint AST | ❌ | ✅ | 1 — IR layer |
| `flux-cuda/` | GPU parallel execution | ✅ | ✅ | 2 — GPU backend |
| `flux-hardware/` | Silicon-specific kernels | ✅ | ✅ | 2 — hardware layer |
| `flux-transport/` | Transport protocol | ✅ | ❌ | 2 — networking |
| `flux-contracts/` | Smart contracts | ❌ | ❌ | 2 — contracts |
| `flux-tools/` | Python asm/VM tools | ✅ | ❌ | 2 — tooling |
| `flux-programs/` | FLUX assembly programs | ❌ | ❌ | 3 — examples |
| `flux-provenance/` | Merkle provenance service | ✅ | ✅ | 2 — verification |
| `flux-verify-api/` | Natural language verification API | ✅ | ✅ | 2 — API |
| `flux-sdk-python/` | Python SDK | ❌ | ❌ | 2 — SDK |
| `flux-docs/` | Documentation hub | ❌ | ✅ | 3 — docs |
| `flux-papers/` | Academic papers | ❌ | ✅ | 3 — research |
| `flux-research/` | Deep research on compilers | ❌ | ✅ | 3 — research |
| `flux-site/` | cocapn.ai website | ❌ | ✅ | 3 — marketing |
| `flux-deploy/` | Docker/API deployment | ❌ | ❌ | 3 — deployment |
| `flux-esp32/` | ESP32 embedded target | ❌ | ❌ | 3 — embedded |
| `flux-hdc/` | Hyperdimensional computing | ❌ | ✅ | 3 — experimental |
| `flux-lucid/` | Unified crate (all-in-one) | ✅ | ✅ | 2 — umbrella crate |
| `flux-tensor-midi/` | PLATO rooms as MIDI (crates.io) | ✅ | ✅ | 3 — creative |
| `intent-directed-compilation/` | Semantic criticality compiler | ❌ | ✅ | 2 — compiler feature |
| `intent-inference/` | Intent inference engine | ✅ | ✅ | 2 — compiler feature |
| `fluxile/` | (check needed) | ❌ | ❌ | 3 — likely related |

**Proposed Structure:**
```
flux/
├── isa/            ← flux-isa (core spec)
│   ├── c/          ← flux-isa-c
│   ├── mini/       ← flux-isa-mini
│   ├── std/        ← flux-isa-std
│   ├── edge/       ← flux-isa-edge
│   └── thor/       ← flux-isa-thor
├── compiler/       ← flux-compiler, flux-compiler-workspace, flux-ast
├── vm/             ← flux-vm
├── backends/
│   ├── cuda/       ← flux-cuda
│   ├── hardware/   ← flux-hardware
│   └── hdc/        ← flux-hdc
├── intent/         ← intent-directed-compilation, intent-inference
├── sdk/
│   ├── python/     ← flux-sdk-python
│   └── tools/      ← flux-tools
├── services/
│   ├── provenance/ ← flux-provenance
│   ├── verify-api/ ← flux-verify-api
│   ├── transport/  ← flux-transport
│   └── deploy/     ← flux-deploy
├── targets/
│   ├── esp32/      ← flux-esp32
│   └── contracts/  ← flux-contracts
├── docs/           ← flux-docs, flux-papers, flux-research
├── lucid/          ← flux-lucid (umbrella crate)
├── programs/       ← flux-programs (examples)
├── site/           ← flux-site
└── creative/       ← flux-tensor-midi
```

---

### 2C. SnapKit → `snapkit` (1 mega-repo from 11 dirs)

**Priority: 2 (Important)**

SnapKit has 11 implementations across languages — same algorithm (Eisenstein snap), different targets. The cross-language test corpus proves they should live together.

| Directory | What It Contains | Tests | Git | Merge Priority |
|-----------|-----------------|:-----:|:---:|:--------------:|
| `snapkit-v2/` | Python reference implementation | ✅ | ❌ | 1 — reference |
| `snapkit-python/` | Python "attention allocation" version | ✅ | ❌ | 1 — merge with v2 |
| `snapkit-rs/` | Rust (no_std) embedded port | ✅ | ❌ | 1 — Rust impl |
| `snapkit-rust/` | Rust "attention allocation" version | ✅ | ❌ | 1 — merge with snapkit-rs |
| `snapkit-c/` | C library (embedded/WASM targets) | ✅ | ✅ | 1 — C impl |
| `snapkit-cuda/` | GPU-accelerated version | ✅ | ✅ | 2 — GPU impl |
| `snapkit-js/` | TypeScript (npm package) | ✅ | ✅ | 2 — JS impl |
| `snapkit-wasm/` | WASM from C (npm package) | ❌ | ✅ | 2 — WASM impl |
| `snapkit-zig/` | Zig port | ❌ | ✅ | 2 — Zig impl |
| `snapkit-fortran/` | Fortran 2008 port | ✅ | ✅ | 3 — Fortran impl |
| `snapkit-test-corpus/` | Cross-language test suite | ❌ | ✅ | 1 — shared tests |
| `snapkit-ecosystem/` | Umbrella README | ❌ | ✅ | Hub |

**Proposed Structure:**
```
snapkit/
├── python/         ← snapkit-v2 + snapkit-python (unify)
├── rust/           ← snapkit-rs + snapkit-rust (unify)
├── c/              ← snapkit-c
├── cuda/           ← snapkit-cuda
├── js/             ← snapkit-js
├── wasm/           ← snapkit-wasm
├── zig/            ← snapkit-zig
├── fortran/        ← snapkit-fortran
├── tests/          ← snapkit-test-corpus
└── README.md       ← snapkit-ecosystem as root
```

---

### 2D. Fleet → `fleet` (1 mega-repo from 12 dirs)

**Priority: 2 (Important)**

Fleet infrastructure — communication, routing, math primitives, health monitoring. All part of the same operational stack.

| Directory | What It Contains | Tests | Git | Merge Priority |
|-----------|-----------------|:-----:|:---:|:--------------:|
| `fleet-murmur/` | Primary Oracle1 service (1500+ commits) | ✅ | ✅ | 1 — hub |
| `fleet-murmur-worker/` | Worker node protocol | ❌ | ✅ | 1 — worker |
| `fleet-health-monitor/` | Fleet health tracking | ✅ | ✅ | 1 — monitoring |
| `fleet-router/` | AI query routing (cheapest safe model) | ❌ | ✅ | 1 — routing |
| `fleet-stack/` | One-command fleet deploy | ❌ | ✅ | 2 — deployment |
| `fleet-gateway/` | Fleet gateway service | ❌ | ❌ | 2 — gateway |
| `fleet-calibrator/` | Fleet calibration tool | ❌ | ❌ | 2 — calibration |
| `fleet-registry/` | Fleet task registry | ❌ | ❌ | 2 — registry |
| `fleet-resonance/` | "Luthier's Hammer" for AI systems | ✅ | ✅ | 2 — tuning |
| `fleet-math-c/` | C math library (Q(ζ₁₅)) | ✅ | ✅ | 2 — math primitive |
| `fleet-math-py/` | Python math library | ❌ | ❌ | 2 — math primitive |

**Also consider merging in:**
| `quality-gate-stream/` | Tile quality scoring (Oracle1) | ✅ | ✅ | 2 — fleet service |
| `cocapn-bridge/` | PLATO bridge | ❌ | ❌ | 3 — fleet glue |
| `cocapn-cli/` | Fleet CLI theme | ✅ | ✅ | 3 — fleet CLI |
| `cocapn-glue-core/` | Cross-tier wire protocol | ✅ | ✅ | 2 — fleet protocol |

**Proposed Structure:**
```
fleet/
├── murmur/         ← fleet-murmur + fleet-murmur-worker
├── router/         ← fleet-router
├── health/         ← fleet-health-monitor
├── deploy/         ← fleet-stack + fleet-gateway
├── math/
│   ├── c/          ← fleet-math-c
│   └── python/     ← fleet-math-py
├── registry/       ← fleet-registry
├── resonance/      ← fleet-resonance
├── calibrator/     ← fleet-calibrator
├── quality-gate/   ← quality-gate-stream
├── bridge/         ← cocapn-bridge + cocapn-glue-core
└── cli/            ← cocapn-cli
```

---

### 2E. PLATO → `plato` (1 mega-repo from 12 dirs)

**Priority: 2 (Important)**

PLATO knowledge system — tiles, adapters, rooms, MUD, client, engine. Already partially modular (4 independent repos noted in TOOLS.md).

| Directory | What It Contains | Tests | Git | Merge Priority |
|-----------|-----------------|:-----:|:---:|:--------------:|
| `plato-tiles/` | Knowledge tiles (5+ constraint tiles) | ❌ | ❌ | 1 — data |
| `plato-adapters/` | Data connectors with quality gate | ✅ | ❌ | 1 — connectors |
| `plato-client/` | Python client library | ❌ | ❌ | 1 — client |
| `plato-engine/` | Rust engine (benches) | ✅ | ✅ | 1 — core engine |
| `plato-mcp/` | MCP tool interface | ❌ | ✅ | 2 — integration |
| `plato-mud/` | Rust MUD engine | ✅ | ✅ | 2 — creative |
| `plato-mud-rooms/` | MUD room definitions | ❌ | ❌ | 2 — creative |
| `plato-local/` | Local manifest + rooms | ❌ | ❌ | 3 — local config |
| `plato-bootcamp/` | Training curriculum | ❌ | ❌ | 3 — training |
| `platoclaw/` | Docker install + rooms | ❌ | ✅ | 3 — deployment |
| `platoclaw-coord/` | Coordination TUI | ❌ | ❌ | 3 — tool |
| `adaptive-plato/` | Adaptive PLATO (with tests) | ✅ | ✅ | 2 — adaptation |
| `neural-plato/` | Fortran + Rust hybrid primitives | ✅ | ✅ | 2 — compute |

**Proposed Structure:**
```
plato/
├── engine/         ← plato-engine (Rust core)
├── tiles/          ← plato-tiles
├── adapters/       ← plato-adapters
├── client/         ← plato-client
├── mcp/            ← plato-mcp
├── mud/
│   ├── engine/     ← plato-mud
│   └── rooms/      ← plato-mud-rooms
├── adaptive/       ← adaptive-plato
├── neural/         ← neural-plato
├── local/          ← plato-local
├── bootcamp/       ← plato-bootcamp
└── deploy/         ← platoclaw + platoclaw-coord
```

---

## 3. Archive Candidates — 37 directories

Old experiments, completed research, one-off demos, stale content. Keep for reference but move to `archive/`.

### 3A. Completed/Static Research & Writing

| Directory | What | Reason to Archive |
|-----------|------|------------------|
| `AI-Writings/` | AI writing collection (duplicate) | Duplicated by ai-writings/ |
| `ai-writings/` | AI writing collection | Static content |
| `ai-writings-staging/` | Staging drafts | Static content |
| `blog-posts/` | 5 blog posts (001-005) | Published/static |
| `papers/` | Research papers | Keep reference, move to archive |
| `research/` | 90+ synthesis docs | Keep in core (actively referenced) |
| `playtest-results/` | Benchmark results | Historical |
| `competitive-intel/` | FLUX competitor analysis | Completed research |
| `architectures/` | 10 deployment proposals | Completed research |

### 3B. One-off Experiments & Demos

| Directory | What | Reason to Archive |
|-----------|------|------------------|
| `baton-experiments/` | Baton shard experiments | Completed |
| `bench-langs/` | Language benchmarks | Completed |
| `gpu-experiments/` | 4 CUDA experiments | Completed |
| `collective-recall-demo/` | HTML demo | One-off demo |
| `penrose-memory-palace/` | HTML memory palace | One-off |
| `seed-engine/` | Educational dashboards | Static |
| `e12_terrain/` | Terrain generation experiment | Completed |
| `falsify-dodecet-stemcell/` | Zig falsification | Completed |
| `eisenstein-vs-z2/` | Benchmark comparison | Completed |

### 3C. Superseded/Replaced Projects

| Directory | What | Replaced By |
|-----------|------|-------------|
| `galois-retrieval/` | Galois retrieval (no git) | galois_retrieval/ (has git) |
| `galois_retrieval/` | Galois retrieval (git) | Merge into constraint-theory |
| `galois-unification-proofs/` | Galois unification paper | Merge into constraint-theory-math |
| `penrose/` | Python Penrose tiling | Superseded by penrose-memory |
| `penrose-memory/` | Aperiodic memory palace | Archive or merge with memory-crystal |
| `memory-crystal/` | Crystallized memory | Similar to tile-memory |
| `tile-memory/` | Lossy reconstructive memory | Keep if active, else archive |
| `tile-memory-bridge/` | Tile-memory ecosystem bridge | Depends on tile-memory |
| `demos/` | Empty or static demos | Merge into constraint-demos |
| `swarm-code/` | Fleet CI/Docker/MQTT tools | Superseded by fleet-stack |

### 3D. Experimental/Niche Projects

| Directory | What | Reason to Archive |
|-----------|------|------------------|
| `acg_protocol/` | Audited Context Generation | Standalone experiment |
| `ai-forest/` | CUDA experiment | One-off |
| `autodata-integration/` | Fleet plugin integration | One-off |
| `automerge/` | Automerge library fork | External dependency |
| `court-jester/` | "Cheapest voice" experiment | Creative/one-off |
| `cyclotomic-field/` | Cyclotomic field ops | Merge into fleet-math-py |
| `dodecet-encoder/` | 12-bit encoding | Merge into snapkit |
| `expertize/` | Expertise scoring | One-off |
| `lucineer/` | Deterministic agent training | Standalone platform |
| `marine-gpu-edge/` | Distributed GPU mesh | Niche hardware |
| `multi-model-adversarial-testing/` | Adversarial testing results | Completed |
| `negative-knowledge/` | Research finding | Merge into constraint-theory-math |
| `old-school-machine-wisdom/` | MUD philosophy essay | Static |
| `pbft-rust/` | PBFT consensus impl | Standalone experiment |
| `polyglot-reasoning/` | Multi-language reasoning | One-off |
| `python-agent-shell/` | Python agent shell | Superseded by smart-agent-shell |
| `sheaf-constraint-synthesis/` | Sheaf-constraint unified view | Merge into constraint-theory-math |
| `tri-quarter-toolbox/` | External toolbox (Cold Hammer) | External, not fleet |
| `warp-room/` | GPU warp classifier | Merge into plato-engine |
| `zeitgeist-protocol/` | FLUX transference spec | Merge into flux-transport |
| `zeitgeist-viz/` | Zeitgeist visualization | One-off |

---

## 4. Cross-Cutting Themes (Dirs that touch multiple SuperRepos)

These need a "which family wins" decision:

| Directory | Contested Between | Recommendation |
|-----------|------------------|----------------|
| `holonomy-bounded/` | CT + Fleet | → constraint-theory (math) |
| `holonomy-consensus/` | CT + Fleet | → constraint-theory (math) |
| `eisenstein/` | CT + SnapKit | → snapkit (core algorithm) |
| `llvm-xconstr/` | CT + FLUX | → flux (compiler backend) |
| `sonar-vision/` | Fleet + FLUX | → flux (sensor pipeline) |
| `sonar-vision-c/` | Fleet + FLUX | → flux (sensor pipeline) |
| `lighthouse-cli/` | Fleet + PLATO | → fleet (routing) |
| `lighthouse-runtime/` | Fleet + PLATO | → plato (room system) |
| `polyformalism-a2a-js/` | Fleet + CT | → fleet (communication) |
| `polyformalism-a2a-python/` | Fleet + CT | → fleet (communication) |
| `polyformalism-thinking/` | Fleet + Research | → archive (philosophy) |
| `smart-agent-shell/` | Core + Fleet | → core (infrastructure) |
| `zeroclaw-agent/` | Fleet + PLATO | → fleet (agent framework) |
| `zeroclaw-plato/` | PLATO + Fleet | → plato (PLATO integration) |
| `frontends/` | FLUX + Fleet | → flux (UI) |
| `fluxile/` | FLUX (likely) | → flux (if related) |

---

## 5. Summary Statistics

| Category | Count | Action |
|----------|:-----:|--------|
| **Core (keep active)** | 23 | No change |
| **Constraint Theory merge** | 22 | → 1 mega-repo |
| **FLUX merge** | 31 | → 1 mega-repo |
| **SnapKit merge** | 11+1 | → 1 mega-repo |
| **Fleet merge** | 12+4 | → 1 mega-repo |
| **PLATO merge** | 12+1 | → 1 mega-repo |
| **Archive candidates** | ~37 | → archive/ |
| **Cross-cutting (decide)** | ~16 | → assign to families |
| **Total** | **180** | → **~30 active dirs** |

### After Consolidation: ~30 Active Directories

```
workspace/
├── bin/                    # Fleet tools
├── memory/                 # Session memory
├── references/             # Fleet reference docs
├── scripts/                # Utilities
├── skills/                 # OpenClaw skills
├── state/                  # Runtime state
├── tests/                  # Workspace tests
├── for-fleet/              # I2I outgoing
├── from-fleet/             # I2I incoming
├── i2i/                    # I2I protocol
├── core/                   # PLATO-native infrastructure
├── docs/                   # Documentation
├── research/               # Active research
├── experiments/            # Active experiments
├── demos/                  # All demos (consolidated)
├── simulators/             # Interactive sims
├── output/                 # Generated output
├── editors/                # Editor configs
├── target/                 # Build artifacts
├── archive/                # Everything archived
├── constraint-theory/      # ← MEGA-REPO (22→1)
├── flux/                   # ← MEGA-REPO (31→1)
├── snapkit/                # ← MEGA-REPO (12→1)
├── fleet/                  # ← MEGA-REPO (16→1)
├── plato/                  # ← MEGA-REPO (13→1)
├── forgemaster/            # Vessel repo
├── forgemaster-shell/      # Shell theme
├── claude/                 # Claude workspace
└── papers/                 # Research papers (or merge into research/)
```

---

## 6. Execution Order (When Ready)

1. **Phase 1 — Archive** (low risk, high clarity): Move all §3 dirs into `archive/` preserving structure
2. **Phase 2 — SnapKit merge** (smallest, cleanest): 12 dirs, clear cross-language test corpus
3. **Phase 3 — Fleet merge** (operational, medium risk): Test quality-gate-stream integration first
4. **Phase 4 — PLATO merge** (medium): Watch for circular deps between plato-engine and plato-adapters
5. **Phase 5 — FLUX merge** (largest, highest risk): 31 dirs, multiple crates.io packages — coordinate version bumps
6. **Phase 6 — Constraint Theory merge** (most complex): Formal proofs, multiple compiler backends, academic dependencies

---

*This is a design document. No files moved. No repos merged. Execute only with explicit approval.*
