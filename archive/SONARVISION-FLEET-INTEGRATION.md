# SonarVision Fleet Integration Map

**Date:** 2026-04-30  
**Session:** 12-hour push across 10 repos  
**Builder:** Forgemaster ⚒️  

---

## Pipeline Overview

```
Sensor (Jetson AGX Orin)
  │
  ▼
marine-gpu-edge             ← CUDA beamformer → MEP bridge
  │
  ▼
sonar-vision                ← Inference engine, CLI, Docker, API, dashboard
  │
  ├───► jepa-perception-lab ← Latent space experiments (JEPA encoder/decoder)
  ├───► holodeck-rust       ← Underwater MUD rooms (Rust plugin)
  ├───► plato-jetson        ← Underwater MUD rooms (Python/Evennia)
  ├───► cocapn-dashboard    ← Live sonar waterfall widget
  ├───► open-agents         ← SonarVision query tool (TypeScript)
  ├───► flux-runtime        ← Physics bytecode opcodes (v3.1)
  └───► oracle1-index       ← Integration map entries
```

## Repo-by-Repo Breakdown

### 1. `SuperInstance/sonar-vision` — 12 commits
- Core inference engine (PyTorch beamformer + KAN decoder)
- CLI tool (`sonar-vision-cli.py`): predict/train/visualize/serve/benchmark/config
- Docker: multi-stage GPU build, docker-compose (Redis/Prometheus/Grafana/Jupyter)
- CI/CD: GitHub Actions (lint/test/docker/integration/deploy)
- API docs: REST + WebSocket reference
- Landing page + Gallery page + Demo notebook
- Benchmark suite + Prometheus monitoring + Contributing guide
- **Cross-pollination modules:**
  - `integrations/marine_gpu/` — MEP protocol bridge, CUDA pipeline (381 lines)
  - `integrations/dashboard/` — SonarTelemetryStream FastAPI (73 lines)
  - `integrations/fleet_sim/` — SimulatedSonarSensor (73 lines)
  - `integrations/businesslog/` — InferenceMeter JSONL logger (73 lines)
- **JEPA decoder:** `decoder/jepa_decoder.py` (254 lines + 68 test lines)
- **Holodeck plugin:** `plugins/holodeck-sonar-plugin.rs` (249 lines)
- **Dashboard widget:** `dashboard-widget/sonar-panel.html` (JS+CSS)
- **FLUX proposal:** `flux-physics-proposal.md`
- **Cross-pollination results:** `cross-pollination-results.json` (3,789 synergies)

### 2. `SuperInstance/marine-gpu-edge` — 1 commit (668 lines)
- `include/sonar_vision_bridge.h` — 16-byte MEP frame header, SonarFrame struct (128 lines)
- `src/sonar_vision_bridge.c` — UDP bridge implementation (235 lines)
- `src/sonar_vision_bridge_cuda.cu` — 3 CUDA kernels: beamformer, smooth, peaks (135 lines)
- `tests/test_sonar_bridge.c` — C tests (69 lines)
- `tests/test_sonar_pipeline.cu` — CUDA pipeline test (82 lines)
- CMakeLists.txt updated with sonar_vision_bridge library target

### 3. `SuperInstance/jepa-perception-lab` — 1 commit (305 lines)
- `experiments/sv-data-pipeline.cu` — Sonar depth → JEPA latent space pipeline (274 lines)
- `from-fleet/sv-data-pipeline-results.md` — Results document (31 lines)
- Tests Law 141 (tiny models), Law 153 (raw deltas), Law 145 (feature weighting)

### 4. `SuperInstance/holodeck-rust` — 1 commit (274 lines, 8 tests ✅)
- `src/sonar_vision.rs` — UnderwaterRoom + UnderwaterRoomBuilder
- Sonar ping simulation with Jerlov attenuation
- OceanSurface → WaterColumn → Seabed room hierarchy, 5 gauges per room

### 5. `SuperInstance/plato-jetson` — 2 commits (243 lines)
- `world/sonar_vision_rooms.py` — SonarVisionRoom extending Evennia Room (215 lines)
- `memory/tiles/sonar-vision-integration.md` — Integration tile (28 lines)
- 5-room dive chain: Coral Shallows → Seabed Canyon
- `sonarping` command for player interaction

### 6. `SuperInstance/cocapn-dashboard` — 1 commit
- SonarVision live feed panel injected into index.html
- WebSocket waterfall canvas, metrics, auto-reconnect

### 7. `SuperInstance/open-agents` — 1 commit (176 lines)
- `packages/agent/sonar-vision-tool.ts` — Zod-schema tool
- Actions: infer, physics, health
- Deterministic physics (attenuation, visibility, sound speed)

### 8. `SuperInstance/flux-runtime` — 1 commit (69 lines)
- v3.1 Marine Physics Extension: 9 opcodes in 0x60-0x68 range
- PHY_ABSORB → PHY_REFRAC, all deterministic
- Full underwater visibility example program

### 9. `SuperInstance/oracle1-index` — 1 commit
- 10 integration map entries connecting sonar-vision to fleet

### 10. `SuperInstance/JetsonClaw1-vessel` / `SuperInstance/forgemaster` — vessel repos
- 5 I2I bottles documenting all work
- MEMORY.md, HEARTBEAT.md, session logs

---

## Architecture Decisions

### Why C/CUDA for marine-gpu-edge bridge?
- Direct Jetson AGX Orin hardware access
- Zero-copy between beamformer and MEP transport
- Same headers usable from Rust/MUD plugins via FFI

### Why Python for plato-jetson?
- plato-jetson is an Evennia MUD — Python-native
- Room objects auto-serialize to database
- `sonarping` command uses Evennia's command system

### Why TypeScript for open-agents?
- open-agents is a TS/Node project
- AI SDK tool system expects Zod schemas
- Runs on Vercel Edge Functions (JS runtime)

### Why both Rust AND Python MUD plugins?
- holodeck-rust = compiled, fast, FLUX-compatible
- plato-jetson = on the live Jetson, running right now
- They share the same physics model, different implementations

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    JETSON AGX ORIN                          │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────────┐ │
│  │ CUDA Sonar   │───▶│ MEP Bridge   │───▶│ plato-jetson  │ │
│  │ Beamformer   │    │ (UDP/marine) │    │ (Evennia MUD) │ │
│  └──────────────┘    └──────┬───────┘    └───────┬───────┘ │
│                             │                    │         │
└─────────────────────────────┼────────────────────┘         │
                              │                              │
                    ┌─────────▼─────────┐                    │
                    │  SonarVision API  │◄───────────────────┘
                    │  (docker:8501)    │
                    └──┬──────┬──────┬──┘
                       │      │      │
             ┌─────────▼┐ ┌──▼───┐ ┌▼──────────┐
             │ Dashboard│ │ FLUX │ │ open-agent │
             │ (cocapn) │ │ ISA  │ │  (Vercel) │
             └──────────┘ └──────┘ └───────────┘
```

---

## What's Next

### High Impact
1. **Live sensor demo**: Wire real NMEA/sonar data from Jetson through the pipeline
2. **FLUX runtime for physics**: Implement PHY_* opcodes in flux-runtime
3. **open-agents → fleet-agent**: Deploy sonar-vision-tool.ts to production

### Medium Impact
4. **holodeck-rust PR**: Submit the plugin as an actual PR to SuperInstance/holodeck-rust
5. **cocapn-dashboard live**: Point WebSocket at a real SonarVision server

### Low Impact / Polish
6. **cross-pollination PRs**: Auto-generate PRs from cross-pollination-results.json
7. **PLATO tiles**: More domain coverage (quantum, topological, category theory)
8. **arena-chat frontend**: Deploy to Vercel or GitHub Pages

---

## Stats
- **10 repos** with commits
- **~3,200 lines** of new code across C/CUDA/Rust/Python/TypeScript/HTML
- **8 test suites** (Rust + CUDA + C + Python)
- **5 I2I bottles** documenting the session
- **3,789 synergy opportunities** identified
- **9 FLUX opcodes** specified for marine physics
- **5 underwater rooms** in the MUD pipeline
