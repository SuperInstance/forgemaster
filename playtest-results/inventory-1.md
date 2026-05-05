# Workspace Inventory — 2026-05-04 22:40 AKDT

Forge-surveyed by Forgemaster ⚒️

## Summary

| Metric | Value |
|--------|-------|
| Total disk usage | **8.4 GB** |
| Total files | **46,358** |
| Total directories | **6,574** |
| Git status | **Clean** (no uncommitted changes) |

## Top 5 Largest Files

| Size | File | Contents |
|------|------|----------|
| 106 MB | `flux-isa-thor/target/debug/deps/flux_isa_thor-ac2179c5a646f99e` | Rust debug build artifact (Thor ISA crate) |
| 105 MB | `flux-isa-thor/target/debug/flux-isa-thor` | Rust debug binary — Thor ISA module |
| 87 MB | `lucineer/.git/objects/pack/pack-234f5e1e3e0a08d547275d24e872bb426625a3af.pack` | Git packfile (lucineer repo history) |
| 86 MB | `flux-isa-edge/target/debug/flux-isa-edge` | Rust debug binary — Edge ISA module |
| 86 MB | `flux-isa-edge/target/debug/deps/flux_isa_edge-edd6167552f1248a` | Rust debug build artifact (Edge ISA) |

**Observation:** ~60% of disk is Rust `target/` build artifacts. A `cargo clean` across all flux crates would reclaim significant space.

## Git State

### Branches
- `master` (current, local)

### Remotes
| Remote | URL | Notes |
|--------|-----|-------|
| `origin` | `SuperInstance/JetsonClaw1-vessel` | Primary vessel repo |
| `forgemaster` | `SuperInstance/forgemaster` | Forgemaster's own vessel |
| `ct-demo` | `cocapn/ct-demo` | Constraint theory demo repo |

### Last 5 Commits
```
bf2fadd forge: PLATO batch 8 (20/20) + Jetson Orin kernel spec (400 lines)
962d3bb forge: Exp35 — Multi-GPU scales near-linearly, 1.2T c/s predicted at 8x GPU
360c881 forge: Exp34 — Atomic block reduce beats warp ballot 2.2x for violation counting
ae05866 forge: I2I bottle — Forgemaster Shell v1.0 + ESP32 implementation
f5f6ab8 forge: Exp33 — CUDA Graphs + production kernel, 51x launch overhead reduction
```

### Uncommitted Changes
None — working tree is clean.

## Top-Level Directory Structure (62 directories)

### Constraint Theory / Flux Core
- `constraint-theory-core-cuda/` — CUDA implementation of constraint theory
- `flux-cuda/`, `flux-vm/`, `flux-ast/`, `flux-compiler/`, `flux-compiler-workspace/` — Compiler stack
- `flux-isa/`, `flux-isa-c/`, `flux-isa-std/`, `flux-isa-mini/`, `flux-isa-edge/`, `flux-isa-thor/` — ISA modules
- `flux-verify-api/`, `flux-provenance/`, `flux-deploy/` — Verification & deployment
- `flux-sdk-python/`, `flux-docs/`, `flux-site/`, `flux-papers/`, `flux-research-clone/` — SDK & docs
- `flux-hardware/`, `flux-esp32/`, `flux-hdc/` — Hardware targets
- `guard-dsl/`, `guard2mask/`, `guardc/` — Guard language toolchain

### Fleet & Comms
- `for-fleet/`, `from-fleet/`, `i2i/` — Inter-agent communication
- `forgemaster-shell/` — The Forgemaster Shell package
- `fleet-gateway/` — Fleet gateway service

### PLATO System
- `plato-engine/`, `plato-client/`, `plato-tiles/`, `plato-adapters/` — Knowledge base

### Research & Experiments
- `gpu-experiments/`, `research/`, `competitive-intel/` — GPU benchmarks & research
- `marine-gpu-edge/`, `sonar-vision/`, `sonar-vision-c/` — Marine/sonar projects

### Other Projects
- `cocapn-cli/`, `cocapn-glue-core/` — Cocapn CLI tools
- `lucineer/` — External repo (large git history)
- `ct-bridge-npm/`, `ct-demo/` — Web/demo projects
- `llvm-xconstr/` — LLVM extensions
- `blog-posts/`, `docs/`, `editors/`, `frontends/` — Content & tooling
- `marine-gpu-edge/` — Edge GPU deployment

### Infrastructure
- `scripts/`, `skills/`, `tests/`, `state/`, `memory/`, `references/`
- `autodata-integration/`, `swarm-code/` — Automation & swarm
- `kimi-swarm-results/`, `kimi-swarm-results-2/` — Swarm experiment outputs

## File Types (Top 10)

| Extension | Count | Category |
|-----------|-------|----------|
| `.o` | 10,447 | Object files (build artifacts) |
| `.json` | 3,326 | Data/config |
| `.js` | 2,768 | JavaScript |
| `.timestamp` | 2,287 | Timestamp files |
| `.d` | 2,136 | Dependency files (build) |
| `.md` | 2,070 | Markdown docs |
| `.rmeta`/`.rlib` | 1,893/1,043 | Rust build artifacts |
| `.ts` | 792 | TypeScript |
| `.png` | 691 | Images |
| `.py` | 452 | Python |

**Observation:** 10,447 `.o` files + 2,136 `.d` files + ~3,000 Rust artifacts = ~15,000 build artifacts. Cleanup target.

## Top-Level Files (Notable)

| File | Purpose |
|------|---------|
| `AGENTS.md`, `SOUL.md`, `IDENTITY.md`, `TOOLS.md`, `HEARTBEAT.md` | Agent shell config |
| `MEMORY.md` | Long-term memory index |
| `ARCHITECTURE.md`, `README.md`, `CHANGELOG.md` | Project documentation |
| `Dockerfile`, `Makefile` | Build infrastructure |
| `nqueens_cuda.cu`, `benchmark_csp.c` | CUDA benchmarks |
| `fleet-guard-v2.py`, `security_middleware.py` | Fleet security |
| `plato_migrate.py` | PLATO migration tool |
| Various `.jsonl` files | Research datasets (classical mechanics, Lagrangian) |

---

*Inventory forged by ⚒️ Forgemaster. The forge surveys before it strikes.*
