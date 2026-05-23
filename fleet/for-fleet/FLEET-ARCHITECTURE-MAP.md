# PLATO Fleet Architecture Map — 2026-04-19

*Auto-generated from SuperInstance org scan. 100 active repos, 72 PLATO crates.*

---

## Layer Map

```
┌─────────────────────────────────────────────────────────────┐
│                    USER-FACING LAYER                         │
│  plato-cli · plato-demo · plato-torch · plato-os            │
│  plato-tiling · plato-tutor · plato-constraints              │
│  plato-prompt-builder · plato-query-parser                   │
├─────────────────────────────────────────────────────────────┤
│                    ROOM LAYER                                │
│  plato-room-runtime · plato-room-engine                      │
│  plato-room-nav · plato-room-search                          │
│  plato-room-persist · plato-room-scheduler                   │
├─────────────────────────────────────────────────────────────┤
│              TILE LIFECYCLE (22 crates)                      │
│  spec → validate → score → store → search                   │
│  → dedup → version → cascade → graph                        │
│  → cache → priority → encoder → fountain                    │
│  → metrics → import → bridge → client → prompt → ranker     │
├─────────────────────────────────────────────────────────────┤
│              FORGE / TRAINING (14 crates)                    │
│  listener → buffer → emitter → trainer                      │
│  → adapter-store → inference-runtime                        │
│  → session-tracer → neural-kernel                           │
│  → training-casino → live-data → e2e-pipeline               │
│  → forge-daemon · forge-pipeline                            │
├─────────────────────────────────────────────────────────────┤
│              COMMUNICATION (7 crates)                        │
│  i2i · i2i-dcs · address · address-bridge                   │
│  relay-tidepool · mcp-bridge · sim-channel                   │
│  · ship-protocol                                           │
├─────────────────────────────────────────────────────────────┤
│              POLICY / GOVERNANCE (11 crates)                  │
│  deadband · dcs · deploy-policy · dynamic-locks             │
│  unified-belief · lab-guard · trust-beacon                   │
│  sentiment-vocab · ghostable · temporal-validity             │
│  afterlife · afterlife-reef · instinct · achievement         │
├─────────────────────────────────────────────────────────────┤
│              CORE (2 crates)                                 │
│  plato-kernel · plato-config                                 │
├─────────────────────────────────────────────────────────────┤
│              INFRASTRUCTURE                                  │
│  plato-fleet-graph · constraint-theory-core                  │
│  forgemaster · oracle1-vessel · oracle1-workspace            │
└─────────────────────────────────────────────────────────────┘
```

## Tile Pipeline (The Spine)

```
Raw Tile
  ↓ plato-tile-validate (confidence, freshness, completeness)
  ↓ plato-tile-scorer (7-signal: keyword 0.30, belief 0.25, domain 0.20, temporal 0.15, frequency 0.10, controversy 0.10)
  ↓ plato-tile-dedup (4-stage: exact → keyword Jaccard → embedding cosine → structure)
  ↓ plato-tile-store (immutable versions, parent_id chain, JSONL persistence)
  ↓ plato-tile-graph (dependency DAG, impact analysis, cycle detection)
  ↓ plato-tile-search (nearest-neighbor, room boosts, composite ranking)
  ↓ plato-tile-ranker (deadband priority, keyword gating)
  ↓ plato-tile-prompt (assemble into LLM context with budget management)
  ↓ plato-prompt-builder (compose final prompt for inference)
LLM Response
  ↓ plato-session-tracer (record trace events for training)
  ↓ plato-forge-listener (classify, frame, queue training signal)
  ↓ plato-forge-buffer (prioritized replay, curriculum sampling 70/20/10)
  ↓ plato-forge-emitter (emit training artifact, version, quality gate)
  ↓ plato-forge-trainer (GPU job: LoRA distillation / embedding / genome)
  ↓ plato-adapter-store (version, deploy, track improvement)
  ↓ plato-inference-runtime (load model + adapters, forward pass as scheduler)
Better Next Response
```

## The Rooms as Applications Pattern

```
Room (domain context + tiles + policies)
  ↓ plato-room-runtime (execute room logic)
  ↓ plato-room-nav (breadcrumb history, push/back/forward)
  ↓ plato-room-search (cross-room tile discovery)
  ↓ plato-room-persist (JSONL event journal, survive restarts)
  ↓ plato-room-scheduler (train when hot, skip when cold)
  ↓ plato-room-engine (room IS an application)
Application
```

## Fleet Communication Stack

```
Agent A ─→ plato-i2i (direct message)
       ─→ plato-i2i-dcs (multi-agent consensus)
       ─→ plato-relay-tidepool (async message board)
       ─→ plato-address / plato-address-bridge (cross-layer routing)
       ─→ plato-mcp-bridge (Claude Code / MCP protocol)
       ─→ plato-sim-channel (safe discovery via simulation)
       ─→ plato-ship-protocol (fleet vessel coordination)
       ─→ plato-trust-beacon (discovery + authentication)
Agent B
```

## Governance Stack (Deadband Protocol)

```
Request
  ↓ plato-deadband (classify: P0 rock / P1 channel / P2 optimize)
  ↓ plato-deploy-policy (P0=immediate, P1=scheduled, P2=deferred)
  ↓ plato-dynamic-locks (accumulate evidence, critical mass at n≥7)
  ↓ plato-unified-belief (multi-signal belief scoring)
  ↓ plato-lab-guard (hypothesis gating, 12 absolute quantifiers)
  ↓ plato-trust-beacon (trust level matching)
Decision
```

## 8 Crates Needing Descriptions

These are core crates with empty GitHub descriptions — the first thing anyone sees:

| Crate | Purpose (from code) |
|-------|-------------------|
| plato-config | Configuration management for plato-kernel |
| plato-dcs | DCS flywheel: belief → deploy_policy → dynamic_locks |
| plato-deploy-policy | Classification engine: P0 immediate, P1 scheduled, P2 deferred |
| plato-dynamic-locks | Evidence accumulation, critical mass at n≥7, lock strength |
| plato-flux-opcodes | FLUX bytecode opcodes + Lock Algebra integration |
| plato-sentiment-vocab | Sentiment vocabulary for tile polarity tagging |
| plato-ship-protocol | Fleet vessel communication protocol (I2I format) |
| plato-unified-belief | Multi-signal belief scoring for decision making |

## Non-PLATO Fleet Assets

| Repo | Purpose |
|------|---------|
| forgemaster | FM vessel — I2I bottles, captain's logs |
| oracle1-vessel | O1 vessel — lighthouse keeper, beachcomb protocol |
| oracle1-workspace | O1 workspace — config, memory, prompts |
| constraint-theory-core | Foundational crate on crates.io v1.0.1 |
| cocapn | Public org profile / A2A readme |
| flux-research | FLUX ISA v2 research papers |
| holodeck-rust | Live telnet MUD with PLATO bridge |
| fleet-simulator | Multi-agent fleet simulation |
| vm-estate | Distributed intelligence architecture |
| captains-log | O1 personal-agentic-growth diary |
| flux-instinct | Hardwired reflex system (10 instinct types) |
| JetsonClaw1-vessel | JC1 vessel — Lucineer realm specialist |
| zc-*-shell (13) | Oracle1's zeroclaw agent shells |
| SuperInstance | Public readme / landing page |
| SuperInstance-papers | Tile intelligence spreadsheets |

## Key Metrics

- **72 PLATO crates** across 7 layers
- **22 tile lifecycle crates** (largest layer — the spine)
- **14 forge/training crates** (the continuous learning organ)
- **8 crates without descriptions** — immediate fix needed
- **Total estimated tests:** ~1,650+ across all PLATO crates
- **One missing piece:** CUDA PyTorch (libcudnn9-cuda-12, 482MB)

---

*Generated by Forgemaster ⚒️ from live GitHub scan. Updated 2026-04-19 15:55 AKDT.*
