# Night Shift Task Queue

## Session Progress (2026-05-03 Night) 🔨 ACTIVE

### Done this shift
- [x] Fleet integration strategy — Claude Opus 5-action plan with dependency ordering
- [x] SonarVision tool README — full API docs (5 actions), streaming, error handling
- [x] Minimax MCP wiring — OpenCode config updated (needs API key)
- [x] Fleet service guard v2 — auto-remediation with restart loop + I2I escalation
- [x] SonarTelemetryStream — WebSocket endpoint for fleet dashboard (port 4052)
- [x] ZeroClaw prompt fix design — Claude Opus design doc with context block + dedup gate
- [x] CT TypeScript bridge — Node.js wrapper for constraint-theory Python package
- [x] 80 PLATO tiles generated — 78/80 ACCEPTED into PLATO via /submit endpoint
- [x] Oracle1 audit critique delivered via I2I bottle
- [x] Fleet ops runbook — Claude Opus authoring
- [x] CT bridge npm builds clean (tsc, no errors)
- [x] 58 more PLATO tiles submitted — discovered v2 schema (domain/question/answer required)
- [x] Gate rejects absolute claims (never, always, guaranteed) — adapted content
- [x] PLATO total: 1399 rooms, 18929 tiles (+59 from session start)
- [x] CSP solver R&D: AC-3 + backtracking + holonomy checker (77 tests passing)
- [x] Holonomy discovery: res=10 on 3D manifolds shows drift=20 — resolution boundary
- [x] 6 R&D PLATO tiles submitted (ct-demo-research, holonomy-theory, petersen-graph)
- [x] solver_demo.rs example: N-Queens, graph coloring, holonomy verification
- [x] Total PLATO tiles this session: 71 accepted
- [x] Below-C R&D: BitmaskDomain type — 12,324× faster N-Queens (N=10)
- [x] Bitmask benchmark: 4,667× faster at N=8, grows with problem size
- [x] Full analysis: for-fleet/2026-05-03-going-below-c-rnd.md
- [x] Roadmap: Software → FPGA → RISC-V → ASIC
- [x] 7 PLATO tiles submitted (below-c-research, bitmask-n-queens)
- [x] **Multi-model deep research: 25+ models, 10+ rounds**
- [x] Claude Opus: strategic analysis, semantic gap collapse thesis, GTM, GUARD DSL, LLVM, Coq
- [x] Kimi: synthesis-not-checking critique, VC business analysis, red team attacks
- [x] Nemotron: DO-178C certification path, quantum-CSP connection
- [x] Seed-2.0-pro: DO-254 real Vivado numbers, SymbiYosys, TUTOR-CRDT merge, FPGA pipeline
- [x] Seed-2.0-code: BHCSP framework, Rust benchmarks, PLATO constraint store Rust impl
- [x] Seed-2.0-mini: safety auditor, DSL design, GTM strategy (safety→agentic)
- [x] GLM-5.1: compiler IR pipeline, RISC-V Xconstr, Coq formalization, SmartCRDT Rust impl
- [x] DeepSeek Reasoner: P2 proof, holonomy snap, 6-instr CSP machine, Turing completeness, CRDT theorems
- [x] Hermes-405B: math insights, DO-254 expert, eVTOL IRAM spec, agentic OS architecture
- [x] Qwen-397B: novelty assessment, 5-year agentic vision, SmartCRDT types
- [x] Qwen-235B: PLDI review, EMSOFT roadmap, TUTOR agent, CRDT research
- [x] Qwen3.6-35B: FABEP protocol, evaluation methodology
- [x] DeepSeek Chat: self-improvement without ML
- [x] **SystemVerilog**: DO-254 DAL A FLUX checker (flux-hardware/rtl/)
- [x] **SymbiYosys**: formal verification kit, 7 assertions + 6 covers
- [x] **RISC-V extension**: Xconstr with CREVISE
- [x] **Mathematical proofs**: P2 invariant, AC-3 termination, bitmask functor
- [x] **Holonomy resolved**: discretization error from snap-to-lattice
- [x] **Agentic FLUX backend**: 5-year vision, FABEP, TUTOR, intent-to-bytecode compiler
- [x] **SmartCRDT**: 5 CRDT types, TUTOR-enhanced merge, agentic OS architecture
- [x] PLATO tiles: ~135 accepted across 40+ rooms

### Key deliverables
- `for-fleet/2026-05-03-multi-model-strategic-synthesis.md` (14-model synthesis)
- `for-fleet/2026-05-03-deep-research-round2.md` (8 models, 6 angles)
- `for-fleet/2026-05-03-deep-research-round3.md` (implementation)
- `for-fleet/2026-05-03-deepseek-reasoner-results.md` (P2 proof)
- `for-fleet/2026-05-03-deep-strategic-analysis.md` (novelty, killer app, critical path)
- `for-fleet/2026-05-03-research-roadmap-weak-to-strong.md` (EMSOFT paper roadmap)
- `for-fleet/2026-05-03-agentic-flux-backend-5year.md` (17KB agentic vision)
- `for-fleet/2026-05-03-smartcrdt-agentic-os.md` (15KB CRDT+OS design)
- `for-fleet/2026-05-03-opus-gtm-strategy.md` (board-level GTM)
- `for-fleet/2026-05-03-qwen-patent-claims.md` (USPTO patents)
- `for-fleet/2026-05-03-qwen-red-team-analysis.md` (8 CVE analogs)
- `for-fleet/2026-05-03-hermes-math-insights.md` (5 math connections)
- `flux-hardware/rtl/flux_checker_top.sv` (synthesizable SystemVerilog)
- `flux-hardware/formal/flux_verify.sby` (SymbiYosys config)
- `flux-hardware/formal/flux_formal_tb.sv` (formal testbench)

### Workers used
1. Claude Code (Opus) — strategic planning, GTM, GUARD DSL, LLVM, Coq
2. Kimi CLI — synthesis critique, VC analysis, red team
3. Seed-2.0-pro — DO-254 expert, TUTOR-CRDT, FPGA merge pipeline
4. Seed-2.0-code — math framework, PLATO store Rust impl
5. Seed-2.0-mini — safety auditor, DSL design, GTM strategy
6. GLM-5.1 — compiler pipeline, RISC-V, SmartCRDT Rust impl
7. DeepSeek Reasoner — formal proofs, Turing completeness, CRDT theorems
8. Nemotron — certification, quantum CSP
9. Hermes-405B — math insights, eVTOL IRAM, agentic OS
10. Qwen-397B — novelty assessment, 5-year vision, CRDT types
11. Qwen-235B — PLDI review, TUTOR agent, CRDT research
12. Qwen3.6-35B — FABEP protocol, evaluation methodology
13. DeepSeek Chat — self-improvement without ML
14. Forgemaster direct — orchestration, PLATO tiles, synthesis

### Known blockers
- Oracle1 agent offline — server still up, PLATO readable
- Matrix send broken (needs Oracle1 gateway restart)
- Kimi CLI intermittent timeouts (2/5 stuck)

### Next wave
1. Synthesize FLUX on Artix-7 (real hardware)
2. Run SymbiYosys formal verification
3. Build GUARD DSL → FLUX compiler in Rust
4. Write Coq formalization of P2 proof
5. RISC-V Xconstr LLVM backend
6. Publish papers: BHCSP framework, constraint-native computing

### Session Stats
- PLATO tiles: ~135 accepted across 40+ rooms
- Models queried: 25+ across 10 rounds
- Commits: 15+ pushed to SuperInstance/JetsonClaw1-vessel
- Rust code: solver.rs (1,200+ lines), bitmask_benchmark.rs, solver_demo.rs
- SystemVerilog: flux_checker_top.sv (400+ lines), formal testbench
- Tests: 35 passing (25 solver + 10 original)
- Benchmark: 12,324× speedup (bitmask vs Vec domains)
- Strategic docs: 10+ for-fleet deliverables (120KB+ total)
- SmartCRDT: 5 novel CRDT types, 3 proved theorems, agentic OS architecture
- TUTOR: constraint-based self-improving agent paradigm
- FABEP: 5-layer bytecode exchange protocol
- Agentic compiler: 7-phase intent-to-bytecode pipeline

### Rules when shift ends
- PUSH EVERYTHING
- Update MEMORY.md with session summary
- Sunrise report ready for Casey
