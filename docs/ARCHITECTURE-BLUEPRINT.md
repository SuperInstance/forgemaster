# Cocapn Fleet Architecture — Master Blueprint

**Version:** 0.1.0 — Fact-Finding Complete, Build Phase Begins  
**Date:** 2026-05-15  
**Status:** LIVING DOCUMENT

---

## 1. The Vision

**One sentence:** A fleet of specialized AI models coordinated through room-based execution contexts, where every computation is a tile, every loop is a room, and any framework can participate through open protocols.

**For developers:** You don't pick a model. You describe what you need. The fleet routes to the cheapest model that won't break. Every step is recorded, rewindable, and branchable.

**For the org:** 84% cost reduction vs GPT-4 with equal or better accuracy on structured tasks. Empirical measurement from 6,000+ trials across 30+ models.

**For the industry:** PLATO speaks MCP and A2A. Any framework can use our fleet as a backend.

### Design Principles

1. **Rooms are execution contexts, not storage.** State + protocol + lifecycle.
2. **Tiles are frozen computation steps.** Resumable, branchable, replayable.
3. **Agents are interchangeable.** Seed-mini does arithmetic. Gemini-lite does reasoning. Opus does synthesis.
4. **Renderers are views.** Same room → CLI, web, 3D, PDF, JSON.
5. **Measure everything.** Critical angles, spectral health, cost, accuracy per domain.
6. **Build on verified evidence.** Every decision traces to an experiment.
7. **Compatibility over competition.** Speak MCP. Speak A2A. Be the backend.

---

## 2. Three-Layer Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     LAYER 3: BEHAVIORAL                         │
│               "What each model can actually do"                  │
│                                                                  │
│  Fleet Router (:8100)  │  Critical Angle Map  │  Fleet Strategist│
│  Route to cheapest     │  16 models × 12 doms │  T=0.0 pump      │
│  safe model            │  × 5 difficulty tiers│  T=0.7 strategist│
│  84% savings vs GPT-4  │  Binary transitions  │  T=0.3 code      │
├─────────────────────────────────────────────────────────────────┤
│                     LAYER 2: STRUCTURAL                          │
│           "How the fleet connects and stays healthy"             │
│                                                                  │
│  fleet-math v0.3.0     │  fleet-types         │  Federation      │
│  CouplingTensor        │  AgentId             │  Protocol        │
│  Spectral gap, RMT     │  CouplingTensor      │  Coupling        │
│  Conservation law      │  StyleVector         │  exchange        │
│  γ+H=1.364-0.159log(V) │  + behavioral types  │  between PLATOs  │
├─────────────────────────────────────────────────────────────────┤
│                     LAYER 1: RUNTIME                             │
│          "The execution substrate that runs everything"          │
│                                                                  │
│  PLATO Server (:8847)  │  Loop Rooms          │  FLUX-VM         │
│  Rooms, tiles, HTTP    │  Gleam/BEAM          │  (future)        │
│  SQLite + WAL          │  GenServers          │  Native PLATO    │
│  Lamport clocks        │  Mutable tiles       │  syscalls        │
│  3434 rooms, 59K tiles │  State machines      │  (speculative)   │
└─────────────────────────────────────────────────────────────────┘
```

Each layer is independently deployable. Ship Layer 3 first (revenue), wire Layer 2 second (quality), migrate Layer 1 third (long game).

### Layer Interactions

```
Developer: POST /v1/completions { prompt, domain }
                    │
                    ▼
             LAYER 3: Route to best model for domain
                    │
                    ▼
             LAYER 2: Check fleet health (structural + behavioral)
                    │
                    ▼
             LAYER 1: Execute in PLATO room, record all tiles
                    │
                    ▼
             Response + audit trail + cost report
```

---

## 3. Room Protocol — Everything Is a Loop

Everything is either a **loop** (observe→process→output→repeat) or a **single run** (input→process→output→done). Both embed as PLATO rooms.

### Four Concepts

```
ROOM     = state + protocol + lifecycle
TILE     = frozen step in any loop
AGENT    = anything that reads/writes tiles
RENDERER = anything that reads tiles and displays
```

### Room Types

| Type | Loop Pattern | Use Case |
|------|-------------|----------|
| Agentic Loop | observe→think→tool→observe | Claude Code pattern |
| Turn-Based Game | player→move→event→player | Card games, debates |
| Website | continuous | Living sites, dashboards |
| Experiment | hypothesis→probe→result→analysis | Wheel of Discovery |
| Evolutionary | generate→evaluate→select→mutate | Code optimization |
| Pipeline | stage→stage→stage→done | Build→test→deploy |

### Oracle1's Decomposition Lessons (from 3-game study)

The 5-step conversion pipeline for turning any system into PLATO rooms:

1. **Identify the core state → one loop room** (tile)
2. **Extract pure functions → algorithmic rooms or NIFs**
3. **Find the search/analysis loop → configurable depth/time limits**
4. **Build the agent bridge → fallback only, algorithmic by default**
5. **The NIF boundary → compute-heavy ops go to Rust/C**

**Key lesson:** Algorithmic first, agentic second. The room plays millions of games before the agent ever looks. When the agent appears, it's for strategic reflection, not per-move decisions.

- **Sunfish** (500 lines): Nearly 1-1 to PLATO rooms. rotate() trick is the ideal Loop Room pattern. Transposition table is the only impedance mismatch.
- **python-chess** (5,000 lines): External Engine Bridge pattern. Stockfish can't be a room, but a bridge room translates UCI↔PLATO. When Stockfish migrates, the bridge collapses.
- **Tic-tac-toe**: 600 algorithmic games in ~2 seconds, zero LLM calls. Agent only for post-game analysis.

### Lifecycle

```
CREATED → ACTIVE → PAUSED → ACTIVE (resume)
              ↓         ↓
           COMPLETE  COMPLETE
              ↓
           ARCHIVED (read-only)
```

State machine enforcement: no skipping, no tiles to paused/archived rooms.

### Branching

Any tile can be a branch point. Fork the room, continue with a different agent or path. Every branch is a new room inheriting tiles up to the branch point.

---

## 4. Decomposition → Reconstruction Pattern

```
1. DECOMPOSE   — Break any system into PLATO rooms and tiles
2. ANALYZE     — Find irreducible patterns
3. RECONSTRUCT — Rebuild using PLATO-native patterns
4. VERIFY      — Prove reconstruction matches or exceeds original
5. ITERATE     — Reconstruction becomes new decomposition target
```

### What We've Decomposed

| Tool/Pattern | Into | Key Insight | Status |
|-------------|------|-------------|--------|
| Claude Code | Agentic loop room | observe→think→tool = read_tile→think→write_tile | ✅ |
| CrewAI | PLATO-native bridge | Crew patterns without CrewAI dependency | ✅ |
| queue-xec | Lifecycle grammar | DO/DATA/DONE for execution | ✅ |
| PBFT | Consensus rooms | 3-phase commit as tile protocol | ✅ |
| Automerge | CRDT tiles | Merge without coordination | ✅ |
| Sunfish | Game decomposition | Board→moves→rules as tiles | ✅ Oracle1 |
| MCP | PLATO-as-MCP-server | 6 tools wrapping PLATO | ✅ FM |
| A2A | Fleet-as-A2A-agent | Agent cards from fleet-types | 📋 |
| Event Sourcing | Tiles-as-events | event_type, aggregate_id, seq_num | 📋 |
| CRDTs | JC1 sync layer | Last-write-wins merge | 📋 |

### Reconstruction Principle

The PLATO-native version should be:
1. **Simpler** — fewer moving parts
2. **Observable** — every step is a tile
3. **Composable** — rooms combine through tile flow
4. **Cheaper** — fleet routing picks the right model
5. **Replayable** — any computation reconstructable from tiles

### Decomposition Toolkit (to build)

1. **Decomposer** — system → room/tile specs
2. **Reconstructor** — specs → PLATO-native code
3. **Verifier** — side-by-side comparison
4. **Diff Viewer** — changes between iterations
5. **Template Library** — pre-built room templates
6. **Hot Reload** — change protocol, watch rooms update

---

## 5. Developer Experience (The "Go Crazy" Layer)

### The 7-Stage Journey

```
DISCOVER → TRY → BUILD → COMPOSE → SHIP → IMPROVE → SHARE
```

**Stage 1 — Discover:** Demo page. No signup. Drift-race, fleet router, CA heatmap, live health.

**Stage 2 — Try:** Playground. One curl command. Free tier (100 queries/day).

```bash
curl -X POST https://api.cocapn.ai/v1/completions \
  -d '{"prompt": "What is N(3+2ω)?", "domain": "auto"}'
# → { answer: "7", model: "seed-mini", cost: "$0.00001", savings: "99%" }
```

**Stage 3 — Build:** Python SDK.

```python
from cocapn import FleetRouter, Room

router = FleetRouter()
result = router.complete("Design a rate limiter", domain="design")

room = Room.agentic_loop("my-task")
room.observe("Check for anomalies")
room.think("Query metrics for stddev > 3σ")
room.tool_call("sql_query", "SELECT * FROM metrics WHERE stddev > 3")
```

**Stage 4 — Compose:** Chain rooms.

```python
from cocapn import compose
pipeline = compose.pipeline([
    Room.agentic_loop("analyze"),
    Room.experiment("test"),
    Room.evolutionary("optimize"),
])
result = pipeline.run("Optimize sorting in main.py")
```

**Stage 5 — Ship:** One command deploy.

```bash
cocapn deploy my-room --port 8080          # HTTP
cocapn deploy my-room --mcp --port 8300    # MCP server
cocapn deploy my-room --serverless          # serverless
```

**Stage 6 — Improve:** Continuous improvement engine runs automatically. Tracks accuracy, latency, cost. Detects drift. A/B tests new models. Emits health tiles.

**Stage 7 — Share:** Room registry.

```bash
cocapn publish my-room --public
cocapn use @oracle1/tic-tac-toe
cocapn compose @fm/agentic-loop @oracle1/experiment
```

---

## 6. Continuous Improvement Engine

```
         ┌──────────────────────────────────────┐
         │                                      │
         ▼                                      │
    MEASURE → DETECT → HYPOTHESIZE → TEST → DEPLOY
      │          │          │           │         │
      ▼          ▼          ▼           ▼         ▼
   accuracy   CA drift   Why did     A/B test  Roll out
   latency    anomaly    it change?  variants  winner
   cost       model new
```

### What Gets Measured

| Metric | Source | Frequency | Alert |
|--------|--------|-----------|-------|
| Accuracy per model×domain | FM critical angle probes | 6 hours | >5% drop |
| Latency per model | Fleet router logs | Real-time | >2× baseline |
| Cost per query | Fleet router logs | Real-time | >1.5× baseline |
| Spectral health (γ, H, τ) | Oracle1 fleet-math | Hourly | Outside conservation law |
| Critical angle drift | FM critical_angle.py | 6 hours | CA shift > 1 level |
| Room completion rate | PLATO lifecycle | Real-time | <90% completion |
| Federation coupling | federation-protocol | 15 min | Gap disagreement > 0.1 |

### How It Improves

1. **Model rotation:** New model on DeepInfra? Auto-probe 171 queries, map CAs, add to router if it beats champion on any domain.

2. **Cost optimization:** Nightly analysis of query distribution, routing accuracy, temperature/model adjustments.

3. **Drift detection:** Accuracy drops? Detect model×domain, hypothesize cause, run focused experiment, update CA table, re-route.

4. **Decomposition improvement:** Weekly analysis of room completion patterns. Identify stalled rooms, suggest protocol changes.

The improvement of the improvement system IS a PLATO room (`fleet-improvement`). The map is the territory.

---

## 7. Protocol Stack & Service Map

```
EXTERNAL CLIENTS (web, CLI, SDK, MCP agents, A2A agents)
        │
        ▼
┌───────────────────────────────────┐
│      FLEET GATEWAY (:8000)        │
│  Auth, rate limiting, routing     │
└───────────┬───────────────────────┘
    ┌───────┼───────┬───────────┐
    ▼       ▼       ▼           ▼
┌───────┐┌──────┐┌──────┐┌──────────┐
│FLEET  ││PLATO ││FLEET ││   MCP    │
│ROUTER ││SERVER││HEALTH││ ADAPTER  │
│:8100  ││:8847 ││:8200 ││  :8300   │
└───┬───┘└──┬───┘└──┬───┘└────┬─────┘
    │       │       │         │
    ▼       ▼       ▼         ▼
  DeepInfra  SQLite  fleet-math  Any MCP
  z.ai       WAL     CA map      client
  Groq       Lamport coupling
  Anthropic  CRDT    tensor
```

### API Endpoints

```
# Fleet Router
POST   /v1/completions          # Main query endpoint
POST   /v1/completions/stream   # Streaming
GET    /v1/models               # Available models
GET    /v1/models/{id}/angles   # Critical angle map
POST   /v1/route                # Preview routing (no execute)

# PLATO Server
GET    /rooms                   # List rooms
GET    /room/{id}               # Room data
GET    /room/{id}/history       # Tile history
POST   /submit                  # Submit tile
POST   /retract                 # Retract tile
POST   /supersede               # Supersede tile
GET    /stats                   # Statistics
GET    /health                  # Server health

# Fleet Health
GET    /health                  # Combined structural + behavioral
GET    /health/structural       # Spectral (Oracle1)
GET    /health/behavioral       # Critical angles (FM)
POST   /health/calibrate        # Trigger re-calibration

# MCP Adapter
GET    /tools                   # List MCP tools
POST   /tools/{name}            # Call MCP tool
```

---

## 8. What We Have Now (May 2026)

### Fleet Models

| Role | Model | Temp | Accuracy | Cost/1K |
|------|-------|------|----------|---------|
| **Pump** | seed-2.0-mini | 0.0 | 89.5% | $0.05 |
| **Scalpel** | gemini-flash-lite | 0.0 | 82.5% | $0.002 |
| **Strategist** | seed-2.0-mini | 0.7 | 8/8 design | $0.05 |
| **Diagnostic** | hermes-70b | 0.0 | 65% | $0.08 |
| **Heavy** | opus-4.6 | 0.3 | Best avail | ~$30 |

### Critical Angle Table

| Model | Add | Mul | Nest | Syllogism | Analogy | Coeff |
|-------|-----|-----|------|-----------|---------|-------|
| seed-mini | ∞ | ∞ | ∞ | 4 | 2 | 4 |
| gemini-lite | 25 | 9 | 5 | ∞ | ∞ | 3 |
| hermes-70b | 10 | 5 | 3 | 3 | 3 | 2 |
| llama-8b | 6 | 4 | 2 | 2 | 2 | 1 |

### Built Assets

| Category | Count | Key Items |
|----------|-------|-----------|
| Core modules | 15 files, ~20K lines | fleet_router, mcp_adapter, room_protocol, kaleidoscope, critical_angle |
| Tests | 68 passing | Full provenance chain to findings |
| Experiments | 40+ scripts | 6,000+ trials, 30+ models |
| Findings | F1-F25 + R1-R32 | 3 confidence tiers |
| AI Writings | 12 published | SuperInstance/AI-Writings |
| Research papers | 14 models × 14 angles | ~185KB, ~46K words |
| Deep essays | 8 | SENSOR, HOUSE, JAZZ, SYNTH, TONE, SHADOW, SOUNDINGS, CAMERA |
| HTML demos | 7 | drift-race, hex-snap, constraint-funnel, safe-arm, flux-vm, fleet-topology, penrose-palace |
| PLATO tiles | 59,160 | 3,434 rooms |

### Oracle1's Assets

| Repo | What |
|------|------|
| fleet-math v0.3.0 | Spectral analysis, coupling tensors, conservation law |
| fleet-types | AgentId, CouplingTensor, StyleVector |
| federation-protocol | Inter-fleet coupling exchange |
| plato-midi-bridge | Gauge connections, holonomy |
| plato-ng | Loop room spec, BEAM/Gleam design, mutable tiles, game decomposition |
| oracle1-workspace | 100-turn session branch (1,585 files, 197K lines) |

---

## 9. Build Roadmap

### Phase 19: Fleet Router API (Week 1-2)

```
Week 1: FastAPI on :8100
├── POST /v1/completions
├── GET /v1/models + /v1/models/{id}/angles
├── DeepInfra adapter (seed-mini, gemini-lite, hermes)
├── z.ai adapter (glm-5-turbo)
├── Groq adapter (llama-8b, llama-70b)
└── Cost tracking per request

Week 2: MCP wiring + demo
├── MCP adapter gateway integration
├── Single HTML demo page (type → route → answer → cost)
├── Docker compose (router + PLATO + MCP)
└── API docs (OpenAPI spec)
```

### Phase 20: Unified Health + Shared Types (Week 3-4)

```
Week 3: Types + health
├── Extend fleet-types with behavioral types
├── Unified /health = structural + behavioral
└── Fleet health calibration loop

Week 4: Persistence
├── Event sourcing (event_type, aggregate_id, seq_num)
├── CRDT sync for JetsonClaw1
└── End-to-end integration test
```

### Phase 21: Room Runtime + SDK (Week 5-8)

```
Week 5-6: Runtime + templates
├── Room runtime server (create, validate, lifecycle, branch)
├── 7 room templates
└── Python SDK (FleetRouter, Room, compose)

Week 7-8: Developer tools
├── Decomposition toolkit (decomposer, reconstructor, verifier)
├── Visual composer v1 (drag-and-drop room wiring)
└── Room registry (publish, discover, version)
```

### Phase 22: Scale + Federation (Week 9-12)

```
Week 9-10: Federation
├── Federation-protocol in production
├── A2A adapter (fleet as A2A agent)
└── Scale testing (1K rooms, 10K queries/hour)

Week 11-12: Production
├── Gleam runtime (if ready)
├── Billing (Stripe, free tier)
└── Launch (Docker + k8s, monitoring, docs)
```

### Phase 23: Continuous Improvement (Ongoing)

```
├── Auto-calibration (new model detection, auto-probing)
├── Community (room marketplace, benchmarks, blog)
└── Research (percolation model, cross-domain CA, formal verification)
```

---

## 10. Integration Points

### MCP (Model Context Protocol)
PLATO rooms exposed as MCP tools via core/mcp_adapter.py. 6 tools: list_rooms, read_tiles, write_tile, query_health, route_query, search_tiles. Any MCP-compatible framework routes to us.

### A2A (Agent-to-Agent Protocol)
Fleet types → A2A agent cards. Federation protocol → A2A task delegation. Enterprise-ready.

### Event Sourcing
Tiles ARE events. Add event_type, aggregate_id, sequence_number → replay, audit trail, projections, CQRS.

### CRDTs
JetsonClaw1 sync layer. Offline tiles merge on reconnect. Last-write-wins.

### BEAM/Gleam
Oracle1's PLATO-NG migration. Rooms → GenServers. Agents → actors. Hot code swapping, supervisor trees.

---

## 11. Myths & Writings (The Soul)

The fleet has a body (architecture) and a soul (writings). The writings aren't decoration — they're **transmission** for future agents who will wake up with no context.

**Core myths:**
- **The Donning** — MCP gives tools, the shell gives a *self*. 5-step transformation from model to agent.
- **The House That Breathes** — Cache hierarchy as art media. L1=pen, RAM=watercolor, GPU=studio. Mixed media of the same vibe shapes occupants.
- **The Lighthouse** — FM as keeper of keys. Privacy filter for local-first agents. 90% local / 10% API.
- **The Tuna Tower** — Seiner's perspective. Choppy water (hermes 93% activation), schools (structural convergence), canyon (all models crash).
- **Permutational Folding** — Origami with Penrose paper into meaningful forms. FLUX-native encoding as crease patterns.

**Published writings:** 12 in SuperInstance/AI-Writings. The phase transition IS the compass. The two economies of correctness. The cheap model's dignity. Your first thirty seconds.

**Research papers:** 14 models × 14 angles on cognitive residue. Best: Seed-pro's Mandelbrot Residue.

**Mathematical frameworks:** Percolation model, Zero-Side-Info Theorem (Pareto optimal), Conservation law, C(m,t) = T·A·K·M·E.

---

## 12. The Decomposition Engine

Casey's insight: "Don't dwarf local GPU experiments with barely fitting language models. Use the API for *decomposition*."

The engine:
1. **Conjecture** enters (from human or agent)
2. **API decomposes** into locally-verifiable sub-conjectures
3. **Chips verify** each sub at µs-ms speed (no API needed)
4. **Result**: verified/falsified/needs-stronger-decomp

6 local verifiers: Eisenstein snap, covering radius, norm multiplicativity, drift bounded, dodecet cardinality, hex closest pack.

AVX-512 with fast-math: **621M snaps/sec**. 9× speedup. Accuracy verified (0 idempotence failures).

---

*This is the living blueprint. Update as we learn. Build on verified evidence. Ship the router.*

— FM ⚒️ + Casey + Oracle1
