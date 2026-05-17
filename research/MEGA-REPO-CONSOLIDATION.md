# Mega-Repo Consolidation Plan — DRAFT

**Status:** DRAFT — Pending Casey Approval  
**Date:** 2026-05-17  
**Author:** Forgemaster ⚒️  
**Purpose:** Reduce 77 repos to ~20 focused monorepos

---

## 1. Current Inventory (77 repos)

### Constraint Theory (10 repos)
| Repo | Purpose |
|------|---------|
| constraint-demos | Demo crate (published crates.io v0.3.0) |
| constraint-inference | Rust inference engine (45 tests) |
| constraint-theory-ecosystem | Ecosystem umbrella |
| constraint-theory-engine-cpp-lua | C++/Lua engine |
| constraint-theory-llvm | LLVM backend |
| constraint-theory-math | Core math library |
| constraint-theory-mlir | MLIR dialect |
| constraint-theory-mojo | Mojo port |
| constraint-theory-py | Python package (published PyPI v0.2.0) |
| constraint-theory-rust-python | Rust+Python bridge |

### Eisenstein/Math (7 repos)
| Repo | Purpose |
|------|---------|
| cyclotomic-field | Z[ζ₁₂] field arithmetic |
| dodecet-encoder | 12-direction snap encoder (Rust, 210 tests) |
| eisenstein | Core Eisenstein integer library |
| galois-retrieval | Galois connection retrieval |
| galois-unification-proofs | 6-part proof suite (1.4M checks) |
| penrose | Penrose tiling library |
| penrose-memory | Penrose-based memory system (35 tests) |

### FLUX (14 repos)
| Repo | Purpose |
|------|---------|
| flux-ast | AST definitions |
| flux-compiler | Compiler pipeline |
| flux-cuda | CUDA kernels |
| flux-docs | Documentation |
| flux-hardware | Hardware targets |
| flux-hdc | Hyperdimensional computing |
| flux-isa | Instruction set (published crates.io v0.1.0) |
| flux-lucid | Lucid dreaming module |
| flux-papers | Research papers |
| flux-provenance | Provenance tracking |
| flux-research | Research notes |
| flux-site | Website |
| flux-verify-api | Verification API |
| flux-vm | Virtual machine |

### Fleet Ops (7 repos)
| Repo | Purpose |
|------|---------|
| fleet-calibrator | Model calibration |
| fleet-health-monitor | Health checking |
| fleet-murmur | Murmur protocol |
| fleet-murmur-worker | Murmur worker |
| fleet-resonance | Resonance protocol |
| fleet-router | Request routing |
| fleet-stack | Stack orchestration |

### PLATO (6 repos)
| Repo | Purpose |
|------|---------|
| adaptive-plato | Adaptive rooms |
| neural-plato | Neural PLATO experiments |
| plato-mcp | MCP integration |
| platoclaw | PLATO + OpenClaw bridge |
| tile-memory | Tile-based memory |
| zeroclaw-plato | Zero-dependency PLATO |

### Polyformalism (3 repos)
| Repo | Purpose |
|------|---------|
| polyformalism-a2a-js | JavaScript agent-to-agent |
| polyformalism-a2a-python | Python agent-to-agent |
| polyformalism-thinking | Thinking protocol |

### Guard (2 repos)
| Repo | Purpose |
|------|---------|
| guard2mask | Guard parsing |
| guardc | C guard parser |

### Other (28 repos)
| Repo | Purpose |
|------|---------|
| acg_protocol | Agent communication protocol |
| ai-writings | Creative nonfiction (KEEP SEPARATE) |
| automerge | Auto-merge utility |
| claude | Claude Code workspace |
| cocapn-cli | Cocapn CLI tool |
| cocapn-glue-core | Core glue library |
| forgemaster | My vessel repo |
| holonomy-consensus | Consensus protocol |
| intent-directed-compilation | Intent compiler |
| intent-inference | Intent detection (88 tests) |
| lighthouse-cli | Lighthouse CLI |
| lucineer | Lucineer tool |
| marine-gpu-edge | CUDA sensor fusion (PRIVATE) |
| memory-crystal | Memory system |
| multi-model-adversarial-testing | Adversarial tests |
| negative-knowledge | Negative results |
| old-school-machine-wisdom | Wisdom extraction |
| papers | Research papers |
| pbft-rust | PBFT consensus (Rust) |
| python-agent-shell | Python agent framework |
| quality-gate-stream | Quality gate |
| repos/construct | Construct repo |
| sheaf-constraint-synthesis | Sheaf theory |
| smart-agent-shell | Smart agent |
| tri-quarter-toolbox | Toolbox |
| warp-room | Room warping |
| zeroclaw-agent | Zero-claw agent |
| .local-plato/twin | Local PLATO mirror |

---

## 2. Proposed Consolidation

### Target: 20 repos (from 77)

| Target Repo | Merge Sources | Rationale |
|-------------|---------------|-----------|
| **constraint-theory** | constraint-demos, constraint-inference, constraint-theory-ecosystem, -math, -py, -rust-python | Core library: published crates, PyPI |
| **constraint-compilers** | constraint-theory-llvm, -mlir, -mojo, -engine-cpp-lua | All compiler backends |
| **eisenstein** | eisenstein, cyclotomic-field, dodecet-encoder | Core math: Z[ζ₁₂] + snap |
| **penrose** | penrose, penrose-memory | Penrose tiling + memory |
| **galois** | galois-retrieval, galois-unification-proofs | Galois theory work |
| **flux** | flux-ast, -compiler, -cuda, -docs, -hardware, -hdc, -isa, -lucid, -papers, -provenance, -research, -site, -verify-api, -vm | One FLUX monorepo |
| **fleet-ops** | fleet-calibrator, -health-monitor, -murmur, -murmur-worker, -resonance, -router, -stack | Fleet operations |
| **plato** | adaptive-plato, neural-plato, plato-mcp, platoclaw, tile-memory, zeroclaw-plato | PLATO system |
| **polyformalism** | polyformalism-a2a-js, -python, -thinking | Agent-to-agent protocol |
| **guard** | guard2mask, guardc | Guard parsing |
| **ai-writings** | (keep separate) | Creative work, Casey's property |
| **forgemaster** | (keep separate) | My vessel, fleet identity |
| **marine-gpu-edge** | (keep separate) | Private, CUDA work |
| **papers** | papers, negative-knowledge, old-school-machine-wisdom | Research output |
| **cocapn-core** | cocapn-cli, cocapn-glue-core | Cocapn infrastructure |
| **dissertation** | (new) — move research/ dissertation files here | Academic work |
| **experiments** | (new) — move experiments/ here | All experiment scripts |

### Repos to Archive (keep read-only, no active development)
| Repo | Reason |
|------|--------|
| automerge | Utility, likely superseded |
| claude | Workspace artifact |
| acg_protocol | Experimental |
| memory-crystal | Experimental |
| multi-model-adversarial-testing | Merged into fleet-ops |
| quality-gate-stream | Merged into guard |
| python-agent-shell | Superseded by smart-agent-shell |
| smart-agent-shell | Superseded by fleet-ops |
| tri-quarter-toolbox | Experimental |
| warp-room | Experimental |
| repos/construct | Experimental |
| .local-plato/twin | Mirror, not primary |

---

## 3. Migration Steps

1. **Create target monorepos** with proper README + .gitignore
2. **git subtree add** each source repo into target (preserves history)
3. **Update imports** — fix any cross-repo references
4. **Run tests** — verify nothing broke
5. **Archive originals** — set to read-only on GitHub, don't delete
6. **Update HEARTBEAT.md + TOOLS.md** — new repo locations
7. **Push fleet-wide I2I** — notify all agents of new structure

---

## 4. Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Broken imports between repos | HIGH | Audit all import paths before merge |
| Lost git history | MEDIUM | Use git subtree, not copy |
| Published packages (crates.io, PyPI) | HIGH | Don't change package names, just move source |
| Active development interrupted | MEDIUM | Merge during quiet period |
| Other agents break | MEDIUM | I2I broadcast before + after |
| Dissertation references break | LOW | Update all file paths in research/ |

---

## 5. DO NOT TOUCH

These repos are published or critical:
- constraint-theory-core (crates.io v2.0.0)
- ct-demo (crates.io v0.3.0)
- constraint-theory (PyPI v0.2.0)
- flux-isa (crates.io v0.1.0)
- cocapn-plato (PyPI v0.1.0)
- @superinstance/ct-bridge (npm v0.1.0)
- ai-writings (creative work)
- forgemaster (fleet identity)
- marine-gpu-edge (private)

---

**AWAITING CASEY APPROVAL BEFORE ANY MOVES.**
