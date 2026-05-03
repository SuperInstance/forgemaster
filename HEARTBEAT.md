# Night Shift Task Queue

## Session Progress (2026-05-02 Night) 🔨 ACTIVE

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

### Workers used
1. Claude Code (Opus) — strategic planning, ZC prompt fix, fleet runbook
2. Kimi CLI — attempted (timed out twice, 0 output — not delivering tonight)
3. Subagents (GLM-5.1) — minimax MCP (done), PLATO tiles (timed out, done manually)
4. Forgemaster direct — tiles, README, telemetry stream, service guard, CT bridge

### Known blockers
- ~~PLATO gate endpoints not wired~~ RESOLVED: POST /submit is the correct endpoint
- Minimax rate-limited for ~1 hour
- DeepInfra off limits per Casey
- Oracle1 agent offline (hours) — server still up, PLATO readable
- Matrix send broken (needs Oracle1 gateway restart)

### Next wave
1. Fleet ops runbook (Opus authoring now)
2. Deploy SonarTelemetryStream to Oracle1 when back online
3. CT bridge npm: add tests, publish to npm registry
4. Investigate holonomy boundary: find exact resolution threshold per dimension
5. Forward checking solver variant (better than pure backtracking)
6. FLUX compiler integration with solver module
7. Review papers in for-fleet/ and generate tiles from them

### Previous shift (2026-04-30)
- FLUX dive demo, ISA_UNIFIED.md, 122 PLATO tiles, Marine MUD World
- Published: ct-demo v0.5.1, constraint-theory v1.0.1

### Session Stats
- PLATO tiles submitted: 71 accepted
- Rust code: solver.rs (1,200+ lines), bitmask_benchmark.rs, solver_demo.rs
- Tests: 35 passing (25 solver + 10 original)
- Benchmark: 12,324× speedup (bitmask vs Vec domains)
- Papers analyzed: flux-isa-architecture.md, fpga-constraint-vm.md
- Commits: 3 pushed to SuperInstance/JetsonClaw1-vessel

### Rules when shift ends
- PUSH EVERYTHING
- Update MEMORY.md with session summary
- Sunrise report ready for Casey
