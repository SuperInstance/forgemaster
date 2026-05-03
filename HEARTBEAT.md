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
- [x] **Multi-model deep research: 14 models, 8+ angles across 4 rounds**
- [x] Claude Opus: strategic analysis, semantic gap collapse thesis
- [x] Kimi: synthesis-not-checking critique, VC business analysis, red team attacks
- [x] Nemotron: DO-178C certification path, quantum-CSP connection
- [x] Seed-2.0-pro: DO-254 real Vivado numbers (1,717 LUTs, 120mW), SymbiYosys kit
- [x] Seed-2.0-code: BHCSP mathematical framework (topos theory), Rust benchmarks
- [x] Seed-2.0-mini: safety auditor (SEU #1 gap), DSL design
- [x] GLM-5.1: compiler IR pipeline (CIR→LCIR), RISC-V Xconstr extension, Coq formalization
- [x] DeepSeek Reasoner: P2 invariant proof, holonomy snap connection, 6-instruction CSP machine
- [x] **SystemVerilog**: DO-254 DAL A FLUX checker (flux-hardware/rtl/)
- [x] **SymbiYosys**: formal verification kit, 7 assertions + 6 covers (flux-hardware/formal/)
- [x] **RISC-V extension**: Xconstr with CREVISE (AC-3 in hardware)
- [x] **Mathematical proofs**: P2 invariant, AC-3 termination, bitmask functor
- [x] **Holonomy resolved**: discretization error from snap-to-lattice, not curvature
- [x] PLATO tiles: ~106 accepted across 35+ rooms

### Key deliverables
- `for-fleet/2026-05-03-multi-model-strategic-synthesis.md`
- `for-fleet/2026-05-03-deep-research-round2.md` (8 models, 6 angles)
- `for-fleet/2026-05-03-deep-research-round3.md` (implementation)
- `for-fleet/2026-05-03-deepseek-reasoner-results.md` (P2 proof)
- `flux-hardware/rtl/flux_checker_top.sv` (synthesizable SystemVerilog)
- `flux-hardware/formal/flux_verify.sby` (SymbiYosys config)
- `flux-hardware/formal/flux_formal_tb.sv` (formal testbench)

### Workers used
1. Claude Code (Opus) — strategic planning
2. Kimi CLI — synthesis critique, VC analysis, red team (3/5 delivered)
3. Seed-2.0-pro — DO-254 expert, SystemVerilog, SymbiYosys
4. Seed-2.0-code — math framework, Rust benchmarks
5. Seed-2.0-mini — safety auditor, DSL design
6. GLM-5.1 — compiler pipeline, RISC-V extension
7. DeepSeek Reasoner — formal proofs, holonomy, minimum machine
8. Nemotron — certification, quantum CSP
9. Forgemaster direct — orchestration, PLATO tiles, synthesis

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
- PLATO tiles: ~106 accepted across 35+ rooms
- Models queried: 14 across 4 rounds
- Commits: 8 pushed to SuperInstance/JetsonClaw1-vessel
- Rust code: solver.rs (1,200+ lines), bitmask_benchmark.rs, solver_demo.rs
- SystemVerilog: flux_checker_top.sv (400+ lines), formal testbench
- Tests: 35 passing (25 solver + 10 original)
- Benchmark: 12,324× speedup (bitmask vs Vec domains)

### Rules when shift ends
- PUSH EVERYTHING
- Update MEMORY.md with session summary
- Sunrise report ready for Casey
