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
3. Batch submit 80 tiles to PLATO when gate opens
4. CT bridge npm package scaffolding
5. More PLATO tiles (push toward 200+)

### Previous shift (2026-04-30)
- FLUX dive demo, ISA_UNIFIED.md, 122 PLATO tiles, Marine MUD World
- Published: ct-demo v0.5.1, constraint-theory v1.0.1

### Rules when shift ends
- PUSH EVERYTHING
- Update MEMORY.md with session summary
- Sunrise report ready for Casey
