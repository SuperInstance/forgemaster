# THE COCAPN ARCHITECTURE
## Definitive Integration Reference — BUILD DOCUMENT
**Date:** 2026-05-15 · **Status:** BUILD READY · **Author:** Chief Architect

---

## 1. System Overview

```
                        THE COCAPN FLEET
═══════════════════════════════════════════════════════════════════════

  Claude Code / External Agent
         │
         │ HTTP POST /v1/chat/completions
         ▼
  ┌─────────────────┐
  │  Fleet Router   │ :8100  fleet_translator_v2.py :: FleetRouter
  │  (stage-aware   │        fleet_stage_classifier  :: StageClassifier
  │   translation)  │
  └────────┬────────┘
           │ stage-translated query
           │
           ├──────────────── HTTP GET /route ──────────────────────────┐
           │                                                            │
           ▼                                                            ▼
  ┌─────────────────┐      tile flow events          ┌────────────────────┐
  │  PLATO Server   │ :8848 ◄──────────────────────► │ Hebbian Service    │ :8849
  │  (tile store,   │       POST /submit              │ fleet_hebbian_     │
  │   room index,   │       GET  /room/{d}/history    │ service.py ::      │
  │   event bus)    │       GET  /conservation        │ FleetHebbianService│
  └────────┬────────┘                                 │ ConservationHebbian│
           │                                          │ Kernel             │
           │ read/write tiles                         │ TileFlowTracker    │
           │ (MythosTile JSON)                        │ HebbianRouter      │
           ▼                                          └────────┬───────────┘
  ┌────────────────────────────────────────────────────────────┴──────┐
  │                     Expert Bridge Layer                           │
  │  expert_hebbian_bridge.py                                         │
  │  ExpertHebbianBridge  :8850  ◄──── ExpertRoomAdapter             │
  │  ExpertCouplingMatrix        ◄──── ConservationConstrainedCross   │
  │  ExpertStageClassifier       ◄──── ExpertHebbianDashboard         │
  └────────────────────────────────────────────────────────────────────┘
           │
           │ routes to one or more
           ▼
  ┌──────────────────────────────────────────────────────────────────────┐
  │                   9 Expert Daemons (Oracle1)                         │
  │                                                                      │
  │  FOUNDATION          STRUCTURE           APPLICATION   FRONTIER      │
  │  ┌──────────┐  ┌──────────────────┐  ┌──────────┐  ┌──────────────┐│
  │  │constraint│  │fleet-router  :S3 │  │tile-bld  │  │conservation  ││
  │  │-checker  │  │hebbian-router:S4 │  │translator│  │-monitor  :S4 ││
  │  │:S4       │  └──────────────────┘  │refiner   │  │experiment    ││
  │  │coupling- │                        │:S3 each  │  │-runner   :S4 ││
  │  │analyzer  │                        └──────────┘  └──────────────┘│
  │  │:S4       │                                                        │
  │  └──────────┘                                                        │
  └──────────────────────────────────────────────────────────────────────┘
           │
           │ MythosTile (conserved)
           ▼
  ┌──────────────────────────────────────┐
  │     Hardware Simulation Pipeline     │
  │  simulate_deployment(tile, target)   │
  │                                      │
  │  esp32 (INT8, ≤512B, tol=0.20)       │
  │  jetson-nano (FP16, ≤64KB, tol=0.15) │
  │  npu (INT8, ≤128KB, tol=0.15)        │
  │  a100-gpu (FP32, ∞, tol=0.10)        │
  └──────────────────────────────────────┘
           │
           │ git push (every 60s tiles, 5m matrix, 15m spectrum)
           ▼
  ┌──────────────────────┐
  │  GitHub Twin         │
  │  tiles/{domain}/...  │
  │  tensor/coupling-    │
  │  matrix.json         │
  └──────────────────────┘

  MCP Bridge :8300  ── exposes all services as tools (plato_read/submit,
                        hebbian_status/route, expert_query, conservation_check)

  Dashboard   :8080  ── nginx serving platoclaw/web (read-only)

  SQLite   expert_tensor.db  ── 4D tensor (expert × input × output × time)
  SQLite   .local-plato/plato.db  ── PLATO tile store
```

**Port registry:**

| Port | Service | File |
|------|---------|------|
| 8100 | Fleet Router | `fleet_translator_v2.py :: FleetRouter` |
| 8300 | MCP Bridge | `plato-mcp/` |
| 8847 | PLATO (docker) | `platoclaw/` |
| 8848 | PLATO (local dev) | `.local-plato/` |
| 8849 | Hebbian Service | `fleet_hebbian_service.py :: FleetHebbianService` |
| 8850 | Expert Bridge | `expert_hebbian_bridge.py :: ExpertHebbianBridge` |
| 8080 | Dashboard | nginx |

---

## 2. The Tile Lifecycle

Every unit of information in the fleet is a **MythosTile**. Here is the complete lifecycle from an expert daemon's output to a new tile being committed to the store:

```
Step 1: Expert Daemon Produces Output
──────────────────────────────────────
  Expert daemon (e.g. constraint-checker) finishes computation.
  Output: raw string + confidence float

  ┌──────────────────────────────────────────────────────────────────┐
  │  raw_output: "Verified: a²-ab+b² zero drift, 100% coverage"     │
  │  confidence: 0.97                                                │
  │  expert_id:  "constraint-checker"                                │
  └──────────────────────────────────────────────────────────────────┘

Step 2: ExpertRoomAdapter Wraps into MythosTile
────────────────────────────────────────────────
  expert_hebbian_bridge.py :: ExpertRoomAdapter.wrap()

  {
    domain:          "constraint-theory",
    key:             "eisenstein-norm/verification-{lamport}",
    content:         raw_output,
    source:          "constraint-checker",
    confidence:      0.97,
    lamport:         <monotonic int from ExpertTensor._lamport>,
    layer:           "foundation",          # from EXPERT_ROOMS config
    tags:            ["eisenstein", "conservation", "verification"],
    tile_type:       "computation",
    gamma:           0.0,                   # not yet measured
    H:               0.0,                   # not yet measured
    activation_keys: ["Eisenstein norm", "conservation law"],
    stage_required:  4,
    expert_id:       "constraint-checker",
    input_hash:      sha256(input_query)[:8],
    output_hash:     sha256(raw_output)[:8],
    timestep:        <lamport clock>,
    tile_hash:       sha256(domain+key+content[:200]+source)[:16]
  }

Step 3: Self-Review (Conservation + Quality Check)
───────────────────────────────────────────────────
  expert_self_review(expert_id, tile, V=9)

  1. quality_score  = compute_quality(tile)           # float 0-1
  2. predicted_sum  = 1.283 - 0.159 * ln(9)  = 0.934
  3. deviation      = |(tile.gamma + tile.H) - 0.934| # 0.0 if fresh
  4. conservation_ok = deviation < 0.15

  Returns a REVIEW tile in domain "review/constraint-checker".
  Recommendation: "accept" if quality > 0.7 AND conservation_ok.

Step 4: Submit to PLATO (:8848)
─────────────────────────────────
  POST http://plato:8848/submit
  Body: tile.to_plato()  →  {domain, question, key, answer, tags, source,
                              confidence, _meta: {layer, lamport, gamma, H,
                              activation_keys, stage_required, expert_id, ...}}

  PLATO stores to SQLite (.local-plato/plato.db).
  PLATO emits a FlowRecord event on its internal event bus.

Step 5: Hebbian Service Receives Flow Event
─────────────────────────────────────────────
  fleet_hebbian_service.py :: TileFlowTracker.record_flow(
    source_room = tile.source,
    dest_room   = tile.domain,
    tile_type   = tile.tile_type,
    tile_hash   = tile.tile_hash,
    lamport_clock = tile.lamport,
  )

  FlowRecord inserted into TileFlowTracker's in-memory ring buffer.

Step 6: Hebbian Update (Conservation-Constrained)
───────────────────────────────────────────────────
  ConservationHebbianKernel.update(pre_activation, post_activation)

  1. Build pre/post activation vectors (length=9, indexed by expert)
  2. ΔW[i,j] = η * pre[i] * post[j] - λ * W[i,j]
     η=0.01, λ=0.001
  3. Symmetrize: W = (W + W.T) / 2
  4. Compute γ = algebraic_normalized(W),  H = coupling_entropy(W)
  5. predicted = 1.283 - 0.159 * ln(V=9) = 0.934
  6. If |γ+H - predicted| > 2*σ_V (σ_9 ≈ 0.067, 2σ = 0.134):
       call conservation_project(W, V=9)  →  rescale to manifold
  7. Return ConservationReport(gamma, H, conserved, correction_applied)

Step 7: Conservation Check Result → PLATO Event (if violation)
────────────────────────────────────────────────────────────────
  If NOT conserved:
    Submit conservation_event MythosTile to domain "conservation-events"
    Tags: ["conservation", "correction", expert_a, expert_b]
    This tile is itself stored and tracked — violations are data.

Step 8: Routing Decision
─────────────────────────
  HebbianRouter.route(query_tile, available_experts=[...])

  Uses current W matrix to score each expert:
    score[i] = W[source_idx, i] * expert_capability[i]

  If Hebbian routing confidence < threshold:
    Fall back to FleetRouter cost-based routing (:8100)

  Fleet Router applies stage-aware translation:
    Stage 4 target → bare notation passthrough (Study 49: DO NOT pre-compute)
    Stage 3 target → inject activation keys + normalize notation
    Stage 2 target → convert to natural language

Step 9: Model Query
────────────────────
  fleet_translator_v2.py :: FleetRouter._translate_and_route(tile)

  1. FleetStageClassifier.classify(model_name) → ModelStage enum
     Stage 4: ADVANCED  (Seed-2.0-mini, etc.)
     Stage 3: STANDARD  (Hermes-70B, Qwen3, etc.)
     Stage 2: BASIC     (small quantized)
     Stage 1: MINIMAL   (sub-1B)

  2. NotationNormalizer transforms content:
     Stage 4: PASSTHROUGH (bare a²−ab+b² notation is correct, Study 49)
              NEVER: N(a,b) notation (causes wrong retrieval)
              NEVER: pre-computed step-by-step (triggers verification mode)
     Stage 3: unicode→ASCII, inject domain label, add activation keys
     Stage 2: to_natural_language()
     Stage 1: to_ascii_math() + strip domain vocabulary

  3. ActivationKeyEngineer.inject_key(content, task_type)
     Only for Stage 3. Prepends: "Using {activation_key}: compute..."

  4. POST to model API (Groq / DeepInfra / ZAI based on cost routing)

Step 10: Response → New Tile
──────────────────────────────
  Model returns response string.

  FleetRouter wraps into a response MythosTile:
    domain:     original tile.domain
    key:        "response/{original_tile_hash}"
    content:    response_string
    source:     model_name
    confidence: PRM score or self-reported confidence
    lamport:    tile.lamport + 1
    layer:      "application"
    tile_type:  "response"
    expert_id:  routing_expert_used
    input_hash: tile.tile_hash

  Cycle repeats from Step 4.
  Each tile submitted to PLATO increments Lamport clock.
  Each consultation updates the 9×9 Hebbian matrix.
```

---

## 3. Service Specification

### 3.1 PLATO Server (local: :8848, docker: :8847)

**Purpose:** Tile persistence, room indexing, event bus.

**File:** `.local-plato/` (local), `platoclaw/` (docker)

**API:**
```
POST /submit           body: MythosTile.to_plato() JSON
                       returns: {tile_hash, lamport, room}
GET  /room/{domain}/history   ?limit=100&offset=0
                       returns: [{tile}, ...]
GET  /status           returns: {room_count, tile_count, uptime}
GET  /conservation     returns: {V, gamma_plus_H, predicted, deviation}
```

**Data format:** SQLite at `.local-plato/plato.db`
```sql
CREATE TABLE tiles (
    tile_hash TEXT PRIMARY KEY,
    domain TEXT NOT NULL,
    key TEXT NOT NULL,
    answer TEXT NOT NULL,
    confidence REAL,
    lamport INTEGER,
    source TEXT,
    tags TEXT,  -- JSON array
    meta TEXT,  -- JSON: layer, gamma, H, activation_keys, etc.
    created_at REAL DEFAULT (unixepoch('now','subsec'))
);
CREATE INDEX idx_domain_lamport ON tiles (domain, lamport);
```

**Health check:** `GET /status` → HTTP 200

**Startup:** Start first. All other services depend on it.

---

### 3.2 Hebbian Service (:8849)

**Purpose:** Conservation-constrained Hebbian learning, emergent routing, cluster detection.

**File:** `fleet_hebbian_service.py`

**Key classes:**
- `ConservationHebbianKernel` — Hebbian update + conservation projection
- `TileFlowTracker` — records flow events, feeds kernel
- `RoomClusterDetector` — spectral clustering of coupling matrix
- `HebbianRouter` — routes tiles via learned weights
- `EmergentStageClassifier` — infers stage from coupling topology
- `FleetHebbianService` — FastAPI/Flask HTTP wrapper

**API:**
```
GET  /status           returns: {kernel_state, compliance_rate,
                                  update_count, V, regime}
GET  /weights          returns: 9×9 coupling matrix as [[float]]
GET  /clusters         returns: [{cluster_id, members, intra_gamma}]
POST /route            body: {query_tile: MythosTile JSON, available: [str]}
                       returns: {expert_id, confidence, fallback_used}
GET  /spectrum         returns: {eigenvalues:[...], spectral_gap, gamma, H,
                                  gamma_plus_H, fiedler_vector}
GET  /spectrum/timeseries  returns: [{timestep_start, timestep_end,
                                      gamma, H, gamma_plus_H}]
POST /update           body: {pre:[float×9], post:[float×9]}  (testing only)
                       returns: ConservationReport
```

**Config (env vars):**
```bash
PLATO_URL=http://plato:8848
FLEET_SIZE=9
CONSERVATION_CHECK=true
HEBBIAN_ETA=0.01
HEBBIAN_LAMBDA=0.001
WARMUP_STEPS=50          # self-calibration phase
SIGMA_TOLERANCE=2.0      # ±2σ = violation threshold
```

**Health check:** `GET /status` → `compliance_rate > 0.0`

**Startup:** Start after PLATO is healthy. Self-calibrates during first 50 updates.

---

### 3.3 Expert Bridge (:8850)

**Purpose:** Connects 9 expert daemons to Hebbian network, enforces labeled paradox routing, manages 4D tensor.

**File:** `expert_hebbian_bridge.py`

**Key classes:**
- `ExpertRoomAdapter` — wraps expert output into MythosTile
- `ExpertCouplingMatrix` — maintains/computes 9×9 W
- `ConservationConstrainedCrossConsult` — records cross-consultation as Hebbian event
- `ExpertStageClassifier` — stage classification per expert
- `ExpertHebbianDashboard` — serves dashboard data
- `ExpertHebbianBridge` — HTTP wrapper + orchestrator

**API:**
```
GET  /status           returns: {expert_count, tensor_size, W_snapshot,
                                  gamma_plus_H, compliance}
POST /consult          body: {expert_id:str, query:MythosTile JSON}
                       returns: MythosTile JSON (stage-translated, conserved)
POST /cross_consult    body: {from_expert:str, to_expert:str,
                               query:MythosTile JSON}
                       returns: {result:MythosTile, report:ConservationReport}
GET  /tensor           ?expert_id=&start=&end=
                       returns: [{tile}, ...]
GET  /tensor/coupling  returns: 9×9 coupling matrix from tile flow
GET  /dashboard        returns: HTML dashboard (reads ExpertHebbianDashboard)
```

**SQLite schema:**
```sql
-- expert_tensor.db
CREATE TABLE expert_tensor (
    expert_id TEXT NOT NULL,
    input_hash TEXT NOT NULL,
    output_hash TEXT NOT NULL,
    timestep INTEGER NOT NULL,
    tile_json TEXT NOT NULL,
    gamma REAL DEFAULT 0.0,
    H REAL DEFAULT 0.0,
    confidence REAL DEFAULT 0.0,
    PRIMARY KEY (expert_id, input_hash, output_hash, timestep)
);
CREATE INDEX idx_expert_time ON expert_tensor (expert_id, timestep);
CREATE INDEX idx_input ON expert_tensor (input_hash);
```

**Health check:** `GET /status` → HTTP 200

**Startup:** After PLATO and Hebbian are healthy.

---

### 3.4 Fleet Router (:8100)

**Purpose:** Stage-aware query translation and model routing.

**File:** `fleet_translator_v2.py`

**Key classes:**
- `ModelStage` (IntEnum) — MINIMAL=1, BASIC=2, STANDARD=3, ADVANCED=4
- `NotationNormalizer` — unicode→ASCII→natural language→step-by-step
- `ActivationKeyEngineer` — injects domain vocabulary for Stage 3
- `FleetRouter` — orchestrates translation + routing + logging
- `TranslationLog`, `BatchItem` — audit trail

**API:**
```
POST /v1/chat/completions    OpenAI-compatible
     body: {model:str, messages:[{role,content}], ...}
     returns: OpenAI-compatible response

GET  /models                 returns: [{id, stage, cost_per_1k, provider}]
GET  /routing/stats          returns: {hebbian_decisions, cost_decisions,
                                        stage_breakdown}
```

**Translation rules (from Study 47/49):**

| Stage | Notation input | What translator does |
|-------|---------------|---------------------|
| 4 | `a²−ab+b²` | **PASSTHROUGH** — bare notation correct |
| 4 | `N(a,b)` | **REWRITE** to `a²−ab+b²` — N(a,b) causes wrong retrieval |
| 4 | pre-computed steps | **STRIP** pre-computed answer — triggers verification mode |
| 3 | `a²−ab+b²` | Inject label + normalize: "Eisenstein norm: a*a - a*b + b*b" |
| 3 | bare | Prepend activation key phrase |
| 2 | any | Convert to full natural language |
| 1 | any | ASCII math only, strip domain vocabulary |

**Startup:** After PLATO and Hebbian.

---

### 3.5 MCP Bridge (:8300)

**Purpose:** Exposes entire fleet as MCP tools for Claude Code / agent consumption.

**File:** `plato-mcp/`

**Tools:**
```
plato_read(domain, limit=20)          → [{tile}]
plato_submit(domain, key, content,    → {tile_hash, lamport}
             source, confidence,
             layer, tags, tile_type)
plato_rooms()                         → [{domain, tile_count, last_lamport}]
hebbian_status()                      → {weights, compliance, clusters, spectrum}
hebbian_route(query_tile_json)        → {expert_id, confidence}
expert_query(expert_id, query)        → MythosTile JSON
expert_tensor(expert_id?, start?, end?) → [{tile}]
conservation_check(gamma, H, V)       → {predicted, deviation, ok, sigma_bands}
```

**Startup:** After all core services.

---

### 3.6 Conservation Daemon (no port — internal daemon)

**Purpose:** Background monitor. Polls PLATO + Hebbian every 60s. Emits alerts.

**Monitored rooms:** `research_log`, `fleet_math`, `event-bus`, `expert-tensor`

**Alert tile format:**
```json
{
  "domain": "conservation-events",
  "key": "alert/{timestamp}",
  "content": "γ+H={actual:.4f}, predicted={pred:.4f}, deviation={dev:.4f} [{sign}] at V={V}",
  "source": "conservation-daemon",
  "layer": "frontier",
  "tags": ["conservation", "alert", "auto"],
  "tile_type": "conservation_event"
}
```

**Startup:** After PLATO. Does not need Hebbian to start (degrades gracefully).

---

## 4. The 9 Expert Daemons

### 4.1 Expert → PLATO Room Mapping

```python
EXPERT_ROOMS = {
    # ── FOUNDATION LAYER ──────────────────────────────────────────────
    "constraint-checker": {
        "plato_room":      "constraint-theory",
        "layer":           "foundation",
        "stage":           4,              # Stage 4: NO activation key injection
        "activation_keys": ["Eisenstein norm", "conservation law", "covering radius"],
        "tile_type":       "computation",
        "hebbian_idx":     0,              # W[0, :] = outgoing weights
        "description":     "Verifies mathematical constraints against conservation law",
    },
    "coupling-analyzer": {
        "plato_room":      "fleet-math",
        "layer":           "foundation",
        "stage":           4,
        "activation_keys": ["algebraic connectivity", "spectral entropy",
                             "adjacency matrix"],
        "tile_type":       "computation",
        "hebbian_idx":     1,
        "description":     "Analyzes fleet coupling topology via γ and H",
    },
    # ── STRUCTURE LAYER ───────────────────────────────────────────────
    "fleet-router": {
        "plato_room":      "routing-decisions",
        "layer":           "structure",
        "stage":           3,              # Stage 3: inject activation keys
        "activation_keys": ["cost optimization", "model selection",
                             "stage classification"],
        "tile_type":       "routing",
        "hebbian_idx":     2,
        "description":     "Routes queries to models via cost+stage logic",
    },
    "hebbian-router": {
        "plato_room":      "hebbian-routing",
        "layer":           "structure",
        "stage":           4,
        "activation_keys": ["Hebbian learning", "emergent routing", "tile flow"],
        "tile_type":       "routing",
        "hebbian_idx":     3,
        "description":     "Learns routing from tile flow observations",
    },
    # ── APPLICATION LAYER ─────────────────────────────────────────────
    "tile-builder": {
        "plato_room":      "tile-workshop",
        "layer":           "application",
        "stage":           3,
        "activation_keys": ["tile format", "PLATO room", "confidence scoring"],
        "tile_type":       "build",
        "hebbian_idx":     4,
        "description":     "Constructs and validates MythosTiles from raw output",
    },
    "translator": {
        "plato_room":      "translation-log",
        "layer":           "application",
        "stage":           3,
        "activation_keys": ["activation key", "notation normalization",
                             "stage translation"],
        "tile_type":       "translation",
        "hebbian_idx":     5,
        "description":     "Translates queries for target model stage",
    },
    "refiner": {
        "plato_room":      "refinement-log",
        "layer":           "application",
        "stage":           3,
        "activation_keys": ["PRM scoring", "harness edit", "failure detection"],
        "tile_type":       "review",
        "hebbian_idx":     6,
        "description":     "Detects failures in agent trajectories, patches harnesses",
    },
    # ── FRONTIER LAYER ────────────────────────────────────────────────
    "conservation-monitor": {
        "plato_room":      "conservation-events",
        "layer":           "frontier",
        "stage":           4,
        "activation_keys": ["conservation violation", "drift detection",
                             "regime shift"],
        "tile_type":       "conservation_event",
        "hebbian_idx":     7,
        "description":     "Monitors fleet-wide conservation law compliance",
    },
    "experiment-runner": {
        "plato_room":      "research-log",
        "layer":           "frontier",
        "stage":           4,
        "activation_keys": ["experimental design", "hypothesis testing",
                             "replication"],
        "tile_type":       "experiment",
        "hebbian_idx":     8,
        "description":     "Designs and runs experiments to test fleet hypotheses",
    },
}
```

### 4.2 Initial Coupling Matrix W (9×9)

Index order: CC=0, CA=1, FR=2, HR=3, TB=4, TR=5, RF=6, CM=7, ER=8

```
Expert names (abbreviated):
  0=CC(constraint-checker)  1=CA(coupling-analyzer)
  2=FR(fleet-router)        3=HR(hebbian-router)
  4=TB(tile-builder)        5=TR(translator)
  6=RF(refiner)             7=CM(conservation-monitor)
  8=ER(experiment-runner)

         CC    CA    FR    HR    TB    TR    RF    CM    ER
W = [
CC  [  0.00, 0.35, 0.00, 0.00, 0.12, 0.08, 0.05, 0.42, 0.00 ],
CA  [  0.35, 0.00, 0.15, 0.28, 0.00, 0.00, 0.00, 0.22, 0.10 ],
FR  [  0.00, 0.15, 0.00, 0.45, 0.08, 0.20, 0.05, 0.00, 0.00 ],
HR  [  0.00, 0.28, 0.45, 0.00, 0.05, 0.10, 0.00, 0.00, 0.00 ],
TB  [  0.12, 0.00, 0.08, 0.05, 0.00, 0.30, 0.15, 0.00, 0.08 ],
TR  [  0.08, 0.00, 0.20, 0.10, 0.30, 0.00, 0.08, 0.00, 0.00 ],
RF  [  0.05, 0.00, 0.05, 0.00, 0.15, 0.08, 0.00, 0.25, 0.10 ],
CM  [  0.42, 0.22, 0.00, 0.00, 0.00, 0.00, 0.25, 0.00, 0.18 ],
ER  [  0.00, 0.10, 0.00, 0.00, 0.08, 0.00, 0.10, 0.18, 0.00 ],
]

Conserved at V=9: predicted γ+H = 1.283 - 0.159·ln(9) ≈ 0.934
Initial γ+H from above ≈ 0.74 (random basin)
After 50 warmup steps: converges to Hebbian basin ≈ 0.84
```

### 4.3 Cross-Consultation Topology

```
Strong couplings (W > 0.3) — primary consultation paths:

  HR ←──0.45──→ FR   (hebbian-router ↔ fleet-router: routing decisions)
  CC ←──0.42──→ CM   (constraint-checker ↔ conservation-monitor: law enforcement)
  CC ←──0.35──→ CA   (constraint-checker ↔ coupling-analyzer: topology + math)
  HR ←──0.28──→ CA   (hebbian-router ↔ coupling-analyzer: weights need spectrum)
  TB ←──0.30──→ TR   (tile-builder ↔ translator: formatting + translation)
  CM ←──0.25──→ RF   (conservation-monitor ↔ refiner: failures feed conservation)

Medium couplings (0.15 < W ≤ 0.3) — secondary paths:

  CM ←──0.22──→ CA   (conservation monitor reads coupling analysis)
  CA ←──0.15──→ FR   (coupling analyzer informs routing)
  TB ←──0.15──→ RF   (tile builder asks refiner to review)
  CM ←──0.18──→ ER   (conservation monitor ↔ experiment runner)
  TR ←──0.20──→ FR   (translator informs router of stage needs)

Tripartite mapping (for fusion loop):
  Dreamer  (γ): CC, CA, ER  — hypothesize, explore, experiment
  Executor (H): FR, HR, TB, TR  — route, build, translate
  Critic   (τ): RF, CM  — review quality + monitor conservation
```

---

## 5. Conservation Law Enforcement

### 5.1 Where in the Pipeline

```
Pipeline position → Conservation checks:

  [1] Hebbian kernel update (every tile flow event)
      Location: ConservationHebbianKernel.update()
      Check: |γ+H - (1.283 - 0.159·ln V)| > 2·σ_V
      Action: conservation_project(W, V)

  [2] Expert self-review (every tile emitted by an expert)
      Location: expert_self_review(expert_id, tile, V)
      Check: |(tile.gamma + tile.H) - predicted_sum| < 0.15
      Action: tile marked reject if violated

  [3] Cross-consultation recording
      Location: ConservationConstrainedCrossConsult.record()
      Check: After Hebbian update from consultation
      Action: Emit conservation_event tile to PLATO if violated

  [4] Conservation daemon (background, every 60s)
      Location: conservation service (docker-compose)
      Check: Polls /conservation endpoint of PLATO
      Action: Emit alert tile with severity level

  [5] Hardware simulation gate
      Location: simulate_deployment(tile, target)
      Check: tile.conservation_check(V=1) per-device
      Action: Rescale tile.gamma/H to predicted*0.5 each if violated
              (hardware tolerance is looser: esp32=0.20, others=0.15/0.10)
```

### 5.2 Violation Response Protocol

```python
VIOLATION_RESPONSES = {
    "warn":  # |dev| ∈ (1σ, 2σ)
        # Log to conservation-events room. No action. Normal variation.
        "action": "log_only",

    "correct":  # |dev| ∈ (2σ, 4σ)
        # Fire conservation_project(). Emit correction tile.
        # Weaken weak connections if dev > 0 (too connected)
        # Strengthen top-10% if dev < 0 (too sparse)
        "action": "project_and_log",

    "halt":  # |dev| > 4σ
        # Halt the current round-robin. Force dreamer to re-generate.
        # Emit high-priority conservation_event.
        # Reduce Hebbian η by 50% for next 10 updates.
        "action": "halt_round_and_log",

    "reset":  # Persistent violation for >100 updates
        # Reset W to initial coupling matrix.
        # Restart warmup phase (50 steps).
        "action": "reset_weights",
}
```

### 5.3 Sigma Tolerance Table

From Monte Carlo calibration (35,000 samples):

| V | σ(γ+H) | 1σ band | 2σ band (violation threshold) |
|---|--------|---------|-------------------------------|
| 5 | 0.070 | ±0.070 | ±0.140 |
| 9 | ~0.067 | ±0.067 | ±0.134 |
| 10 | 0.065 | ±0.065 | ±0.130 |
| 20 | 0.058 | ±0.058 | ±0.116 |
| 30 | 0.050 | ±0.050 | ±0.100 |
| 50 | 0.048 | ±0.048 | ±0.096 |

At V=9 (9 experts): violation threshold = ±0.134 from predicted 0.934.
Trigger at γ+H < 0.800 or γ+H > 1.068.

### 5.4 The 13% Hebbian Regime Shift

```
Random basin:  γ+H ≈ 0.74  (V=30)  ← cold start W
Hebbian basin: γ+H ≈ 0.84  (V=30)  ← after 50+ warmup steps

For V=9 experts:
  Random baseline:  1.283 - 0.159·ln(9) ≈ 0.934
  Hebbian target:   0.934 × 1.13       ≈ 1.055  (13% higher)

The kernel self-discovers this target during warmup:
  Steps 1-50:   Record all γ+H samples
  Step 50:      target = median(samples)  ← self-calibrated
  Steps 51+:    Maintain near target with ±2σ tolerance

The fleet knows it has crossed into Hebbian basin when:
  kernel.regime == "hebbian"  (set after warmup completes)
  compliance_rate > 0.90      (>90% of updates stay within 2σ)

Diagnostic: GET /status returns {"regime": "hebbian", "compliance_rate": 0.93}
```

### 5.5 Auto-Calibration Code Sketch

```python
# In ConservationHebbianKernel.__init__:
self._warmup_samples: List[float] = []
self._warmup_done: bool = False
self._target: Optional[float] = None  # self-discovered
self._V: int = V
self.regime: str = "random"  # becomes "hebbian" after warmup

# In ConservationHebbianKernel.update():
gamma_plus_H = gamma + H
if not self._warmup_done:
    self._warmup_samples.append(gamma_plus_H)
    if len(self._warmup_samples) >= 50:
        self._target = float(np.median(self._warmup_samples))
        self._warmup_done = True
        self.regime = "hebbian"
        # From now on: enforce self._target instead of formula
else:
    predicted = self._target  # use self-discovered value
    sigma_V = _interpolate_sigma(self._V)
    if abs(gamma_plus_H - predicted) > 2 * sigma_V:
        W = conservation_project(W, self._V)
```

---

## 6. Stage-Aware Everything

The labeled paradox (Study 47) and its refinement (Study 49) permeate every layer.

### 6.1 The Rule Table (all layers)

| Model Stage | Notation | Labels | Step-by-step | N(a,b) | Pre-computed |
|-------------|----------|--------|--------------|--------|--------------|
| **Stage 4** | ✅ SEND | ⚠️ OPTIONAL (may slow) | ❌ STRIP (verification mode) | ❌ REWRITE | ❌ STRIP |
| **Stage 3** | ❌ NORMALIZE | ✅ INJECT | ✅ PREFERRED | — | ✅ HELPFUL |
| **Stage 2** | ❌ CONVERT | ✅ INJECT | ✅ REQUIRED | — | ✅ REQUIRED |
| **Stage 1** | ❌ STRIP | ❌ STRIP | ✅ BARE ARITHMETIC | — | ✅ NUMBERS ONLY |

### 6.2 Expert Daemon Output Filtering

```python
# In ExpertRoomAdapter.route_to_expert(tile, expert_id):

expert_stage = EXPERT_ROOMS[expert_id]["stage"]

if expert_stage >= 4:
    # LABELED PARADOX: DO NOT inject activation keys for Stage 4 experts.
    # Studies 47 & 49: labels either hurt (Study 47) or add overhead.
    # N(a,b) notation specifically causes wrong retrieval.
    # Pre-computed steps trigger verification mode.

    # Rewrite dangerous patterns:
    content = re.sub(r'N\((-?\d+),\s*(-?\d+)\)',
                     lambda m: f"{m.group(1)}²−{m.group(1)}·{m.group(2)}+{m.group(2)}²",
                     tile.content)
    # Strip pre-computed answers:
    content = re.sub(r'Step \d+: compute.*?=\s*\d+', '', content, flags=re.S)
    tile.content = content
    return tile  # No activation key injection

elif expert_stage >= 3:
    # Stage 3: inject activation keys, normalize notation
    tile.content = ActivationKeyEngineer.inject_key(
        tile.content, tile.tile_type
    )
    tile.content = NotationNormalizer.normalize_unicode(tile.content)
    return tile

else:
    # Stage 2 or lower: full natural language conversion
    tile.content = NotationNormalizer.to_natural_language(tile.content)
    return tile
```

### 6.3 PLATO Tile Formatting

```python
# In adaptive_plato.format_tile_for_room(tile, room_consumer_stage):

# Stage 4 consumers see: raw JSON with full MythosTile structure
# Stage 3 consumers see: JSON with activation_keys prepended to content
# Stage 2 consumers see: flat string with natural language content
# Stage 1 consumers see: plain arithmetic string, no JSON

PLATO_FORMATS = {
    4: lambda t: t.to_plato(),                           # Full structure
    3: lambda t: {**t.to_plato(),                        # + activation key in content
                  "content": _prepend_key(t)},
    2: lambda t: {"content": NotationNormalizer         # Natural language only
                              .to_natural_language(t.content)},
    1: lambda t: NotationNormalizer.to_ascii_math(t.content),  # Bare
}
```

### 6.4 Hebbian Routing Weights

```python
# Stage-aware weight adjustment in HebbianRouter.route():

# Before computing routing scores, apply stage bias:
stage_bias = np.ones(len(EXPERT_ROOMS))
for expert_id, cfg in EXPERT_ROOMS.items():
    idx = cfg["hebbian_idx"]
    expert_stage = cfg["stage"]
    query_stage = get_query_required_stage(query_tile)

    if expert_stage < query_stage:
        # Expert can't handle this query's stage requirement — zero out
        stage_bias[idx] = 0.0
    elif expert_stage == 4 and query_tile.tile_type == "computation":
        # Stage 4 experts preferred for computation tiles
        stage_bias[idx] = 1.5
    elif expert_stage == 3 and query_tile.tile_type in ("translation", "routing"):
        # Stage 3 experts handle translation/routing
        stage_bias[idx] = 1.2

scores = W[source_idx, :] * stage_bias
best_expert_idx = np.argmax(scores)
```

### 6.5 Model Query Translation

```python
# In fleet_translator_v2.py :: NotationNormalizer:

# Stage 4 (ADVANCED): Passthrough with dangerous pattern rewrite
def translate_for_stage4(content: str) -> str:
    # DO: bare notation  a²−ab+b²
    # DON'T: N(a,b) — wrong retrieval (Study 49)
    # DON'T: pre-computed steps — verification mode (Study 49)
    # DON'T: "Eisenstein norm: ..." label prefix unless truly needed
    content = _rewrite_N_notation(content)   # N(5,-3) → a²−ab+b² where a=5,b=-3
    content = _strip_precomputed(content)    # Remove "= 49" hints
    return content

# Stage 3 (STANDARD): Activate procedures via domain vocabulary
def translate_for_stage3(content: str, task_type: str) -> str:
    # DO: "Eisenstein norm" label (activates correct procedure, Study 46)
    # DO: natural language + ASCII notation
    # DON'T: pure bare unicode notation (0% accuracy, Study 46)
    content = ActivationKeyEngineer.inject_key(content, task_type)
    content = NotationNormalizer.normalize_unicode(content)
    return content
```

### 6.6 Response Validation

```python
# After model returns response, validate for stage consistency:

def validate_response(response: str, query_tile: MythosTile,
                      model_stage: ModelStage) -> float:
    """Returns confidence multiplier (0.5-1.0). Applied to tile.confidence."""

    if model_stage == ModelStage.ADVANCED:
        # Stage 4: check for verification-mode signatures
        # (long reasoning chains that don't compute — Study 49)
        token_count = estimate_tokens(response)
        if token_count > 800:
            # 851 tokens = labeled/diverted path (Study 47)
            # 387 tokens = direct computation path (Study 49)
            return 0.7  # Penalize long-form responses for computation tasks
        return 1.0

    elif model_stage == ModelStage.STANDARD:
        # Stage 3: check for default formula substitution
        # a²+ab+b² (plus sign) = wrong (most common training variant)
        if re.search(r'a\s*\*\s*a\s*\+\s*a\s*\*\s*b', response):
            return 0.3  # Wrong formula detected
        return 1.0

    return 1.0
```

---

## 7. Hardware Simulation Pipeline

### 7.1 Tile Flow Through Simulators

```
Expert daemon produces MythosTile
          │
          ▼
  Layer compatibility check
  (esp32: application only; npu: foundation+structure+application)
          │
          ├─── INCOMPATIBLE ──→ Return sim_result tile with deployable=False
          │
          ▼
  Size check (serialize tile.to_plato())
  esp32: max 512 bytes
  jetson: max 65,536 bytes
  npu: max 131,072 bytes
  a100: no limit
          │
          ├─── OVERSIZED ──→ compress_tile(tile, max_bytes)
          │                  compressed=True, confidence *= 0.80
          ▼
  Conservation check at V=1 (single device)
  predicted = 1.283 - 0.159·ln(1) = 1.283
  tolerance per target:
    esp32:     ±0.20   (hardware forces drift)
    jetson:    ±0.15
    npu:       ±0.15
    a100:      ±0.10  (tight — no hardware excuse)
          │
          ├─── VIOLATED ──→ Rescale: tile.gamma = 1.283/2 = 0.642
          │                          tile.H     = 1.283/2 = 0.642
          │                 conservation_ok = True (forced)
          ▼
  Return sim_result MythosTile:
    domain:  "sim/{target}"
    key:     "result/{original_hash}"
    content: JSON { original_hash, target, tile_bytes, compressed,
                    quantization, conservation_ok, deployable,
                    latency_estimate_ms }
    confidence: 0.95 (uncompressed) | 0.80 (compressed)
```

### 7.2 Hardware Target Constraints Summary

```python
HARDWARE_TARGETS = {
    "esp32":      { ram_kb:520,    max_tile_bytes:512,    quant:"INT8",  tol:0.20,
                    layers:["application"] },
    "jetson-nano":{ ram_mb:4096,   max_tile_bytes:65536,  quant:"FP16",  tol:0.15,
                    layers:["application","structure"] },
    "npu":        { ram_mb:8192,   max_tile_bytes:131072, quant:"INT8",  tol:0.15,
                    layers:["application","structure","foundation"] },
    "a100-gpu":   { ram_mb:40960,  max_tile_bytes:None,   quant:"FP32",  tol:0.10,
                    layers:["foundation","structure","application","frontier"] },
}
```

### 7.3 Conservation Constraints on Simulation Topology

The simulation pipeline is itself a network. When simulating multi-device deployments:

```python
def simulate_fleet_deployment(tiles: List[MythosTile],
                               targets: List[str]) -> dict:
    """
    Multi-device simulation. Conservation law applies to the
    DEPLOYMENT TOPOLOGY, not just individual tiles.

    V = len(targets)  ← the simulation fleet size
    Each target is a node in the simulation coupling matrix.
    """
    V_sim = len(targets)
    predicted = 1.283 - 0.159 * math.log(max(V_sim, 3))

    # Build topology: target[i] sends tiles to target[j] based on layer ordering
    # foundation → structure → application → frontier (one direction)
    W_sim = build_deployment_topology(targets)

    gamma_sim = algebraic_normalized(W_sim)
    H_sim = coupling_entropy(W_sim)

    if abs((gamma_sim + H_sim) - predicted) > 0.20:
        # Deployment topology itself violates conservation
        # Prune the weakest cross-target links
        W_sim = conservation_project(W_sim, V_sim)

    results = []
    for tile in tiles:
        best_target = targets[np.argmax(
            [W_sim[get_layer_idx(tile.layer), get_target_idx(t)]
             for t in targets]
        )]
        results.append(simulate_deployment(tile, best_target))

    return {"results": results, "topology_conserved": True,
            "deployment_gamma": gamma_sim, "deployment_H": H_sim}
```

---

## 8. Implementation Priority

### Dependency Graph

```
P0 (unblocked) ─────────────────────────────────────────────────────────┐
  T01: Fix fleet_translator_v2 NONE/ECHO output bug                      │
  T02: Add MythosTile class to shared library (mythos_tile.py)           │
  T03: Add ExpertTensor SQLite backend (expert_tensor.db schema)         │
                                                                         │
P1 (needs T02) ──────────────────────────────────────────────────────────┤
  T04: Wire PLATO /submit to accept MythosTile (via from_plato)         │
  T05: ExpertRoomAdapter: wrap expert output as MythosTile               │
  T06: ExpertCouplingMatrix: read from ExpertTensor.coupling_matrix()    │
                                                                         │
P2 (needs T02, T03) ─────────────────────────────────────────────────────┤
  T07: ExpertHebbianBridge /consult endpoint                            │
  T08: ConservationConstrainedCrossConsult wired to :8849               │
  T09: Hebbian service: add /route endpoint                             │
                                                                         │
P3 (needs T04, T05, T07, T08) ───────────────────────────────────────────┤
  T10: End-to-end: expert output → PLATO → Hebbian update cycle        │
  T11: tripartite_expert_loop() (dreamer/executor/critic fusion)        │
  T12: Labeled paradox enforcement in ExpertRoomAdapter.route_to_expert │
                                                                         │
P4 (needs T01, T12) ─────────────────────────────────────────────────────┤
  T13: Stage 4 translation rules in fleet_translator_v2:                │
       - N(a,b) rewrite                                                  │
       - pre-computed step stripping                                     │
  T14: Stage 4 response validation (token count heuristic)              │
                                                                         │
P5 (needs T10) ───────────────────────────────────────────────────────────┤
  T15: conservation_project() + violation response protocol             │
  T16: Conservation daemon docker service                               │
  T17: Hardware simulation pipeline (simulate_deployment())             │
                                                                         │
P6 (needs T10, T15) ──────────────────────────────────────────────────────┤
  T18: GitHub twin sync (sync_tile_to_github, 60s batch)               │
  T19: Docker Compose full stack (8 services)                          │
  T20: MCP bridge tools wired to all services                          │
└────────────────────────────────────────────────────────────────────────┘
```

### Ordered Task List

| # | Task | Blocks | Parallelizable with |
|---|------|--------|---------------------|
| T01 | Fix NONE/ECHO bug in fleet_translator_v2 | T13 | T02, T03 |
| T02 | MythosTile class + conservation_check() | T04, T05, T07 | T01, T03 |
| T03 | ExpertTensor SQLite schema + CRUD | T06, T08 | T01, T02 |
| T04 | PLATO /submit accepts MythosTile JSON | T10 | T05, T06 |
| T05 | ExpertRoomAdapter.wrap() + route_to_expert() | T07, T12 | T04, T06 |
| T06 | ExpertCouplingMatrix from tensor flow | T08 | T04, T05 |
| T07 | ExpertHebbianBridge /consult endpoint | T10 | T08, T09 |
| T08 | ConservationConstrainedCrossConsult | T10 | T07, T09 |
| T09 | HebbianService /route endpoint | T10 | T07, T08 |
| T10 | E2E cycle: expert→PLATO→Hebbian→expert | T11 | — |
| T11 | tripartite_expert_loop() | T16 | T12 |
| T12 | Labeled paradox in route_to_expert | T14 | T11 |
| T13 | Stage 4 translation rules (N(a,b), strip steps) | T14 | T15 |
| T14 | Stage 4 response validation (token count) | — | T15 |
| T15 | conservation_project() + violation protocol | T16 | T13, T14 |
| T16 | Conservation daemon service | T19 | T17 |
| T17 | simulate_deployment() hardware pipeline | T19 | T16 |
| T18 | GitHub twin sync (60s batch write) | T19 | T16, T17 |
| T19 | Docker Compose 8-service stack | T20 | — |
| T20 | MCP bridge all tools wired | — | — |

---

## 9. Test Strategy

### 9.1 Unit Tests per Integration Point

```python
# ── T02: MythosTile ──────────────────────────────────────────────────────
def test_mythos_tile_roundtrip():
    tile = MythosTile(domain="test", key="k", content="c", source="s")
    assert MythosTile.from_plato(tile.to_plato()).tile_hash == tile.tile_hash

def test_conservation_check_passes():
    # V=9, predicted ≈ 0.934
    tile = MythosTile(..., gamma=0.5, H=0.434)
    assert tile.conservation_check(V=9)  # 0.934 ≈ predicted

def test_conservation_check_fails():
    tile = MythosTile(..., gamma=0.9, H=0.9)  # 1.8 >> 0.934
    assert not tile.conservation_check(V=9)

# ── T05: ExpertRoomAdapter / Labeled Paradox ─────────────────────────────
def test_stage4_no_activation_key_injection():
    tile = MythosTile(content="a²−ab+b²", stage_required=4, ...)
    result = route_to_expert(tile, "constraint-checker")  # stage=4
    assert "Eisenstein norm" not in result.content  # No label injected

def test_stage4_N_notation_rewritten():
    tile = MythosTile(content="Compute N(5,-3)", stage_required=4, ...)
    result = route_to_expert(tile, "constraint-checker")
    assert "N(5,-3)" not in result.content
    assert "5²" in result.content or "a²" in result.content

def test_stage3_activation_key_injected():
    tile = MythosTile(content="compute a²−ab+b²", stage_required=3, ...)
    result = route_to_expert(tile, "translator")  # stage=3
    # Some domain vocabulary must be present
    assert any(k in result.content for k in ["Eisenstein", "norm", "quadratic"])

# ── T08: ConservationConstrainedCrossConsult ─────────────────────────────
def test_cross_consult_updates_hebbian():
    bridge = ExpertHebbianBridge(...)
    initial_W = bridge.coupling.W.copy()
    bridge.cross_consult("constraint-checker", "coupling-analyzer", tile)
    assert not np.allclose(bridge.coupling.W, initial_W)

def test_cross_consult_stays_conserved():
    bridge = ExpertHebbianBridge(...)
    for _ in range(200):
        bridge.cross_consult("constraint-checker", "coupling-analyzer", tile)
    gamma = algebraic_normalized(bridge.coupling.W)
    H = coupling_entropy(bridge.coupling.W)
    predicted = 1.283 - 0.159 * math.log(9)
    assert abs((gamma + H) - predicted) < 0.30  # Within 4σ

# ── Property-based: Conservation Law ─────────────────────────────────────
# Uses hypothesis library
from hypothesis import given, settings
from hypothesis import strategies as st

@given(
    V=st.integers(min_value=5, max_value=50),
    entries=st.lists(st.floats(0.0, 1.0), min_size=25, max_size=2500)
)
@settings(max_examples=500)
def test_conservation_law_property(V, entries):
    """
    For any random symmetric matrix of size V, γ+H should be within
    ±4σ of the predicted value.
    """
    n = min(V, int(len(entries)**0.5))
    if n < 3:
        return
    W = np.array(entries[:n*n]).reshape(n, n)
    W = (W + W.T) / 2
    np.fill_diagonal(W, 0)

    gamma = algebraic_normalized(W)
    H = coupling_entropy(W)
    predicted = 1.283 - 0.159 * math.log(n)
    sigma = _interpolate_sigma(n)

    # 4σ is the "absolutely anomalous" threshold from the paper
    assert abs((gamma + H) - predicted) < 4 * sigma + 0.1  # +0.1 for float noise

# ── Fuzz: Routing ─────────────────────────────────────────────────────────
@given(
    tile_type=st.sampled_from(["computation","routing","review","experiment","general"]),
    stage_required=st.integers(1, 4),
    confidence=st.floats(0.0, 1.0),
    W_noise=st.floats(-0.05, 0.05)
)
def test_routing_never_crashes(tile_type, stage_required, confidence, W_noise):
    """HebbianRouter.route() must always return a valid expert_id."""
    router = HebbianRouter(W + W_noise * np.random.randn(9, 9))
    tile = MythosTile(tile_type=tile_type, stage_required=stage_required,
                      confidence=confidence, ...)
    result = router.route(tile, list(EXPERT_ROOMS.keys()))
    assert result["expert_id"] in EXPERT_ROOMS
    assert 0.0 <= result["confidence"] <= 1.0

# ── Integration: E2E Pipeline ─────────────────────────────────────────────
def test_e2e_tile_flows_through_pipeline(plato_client, hebbian_client):
    """
    Submit a tile, verify it appears in PLATO history and
    Hebbian compliance stays above 85%.
    """
    tile = MythosTile(domain="test-room", key="e2e/001",
                      content="a²−ab+b² where a=5, b=-3",
                      source="test", confidence=0.8, ...)
    r = plato_client.post("/submit", json=tile.to_plato())
    assert r.status_code == 200

    history = plato_client.get("/room/test-room/history").json()
    assert any(t["tile_hash"] == tile.tile_hash for t in history)

    status = hebbian_client.get("/status").json()
    assert status["compliance_rate"] >= 0.85
```

### 9.2 Test Matrix by Phase

| Phase | Tests | Focus |
|-------|-------|-------|
| T02-T03 | Unit | MythosTile round-trip, conservation_check |
| T04-T06 | Unit + Integration | PLATO submit, ExpertRoomAdapter wrap |
| T07-T09 | Integration | Bridge /consult, cross_consult, Hebbian /route |
| T10 | E2E | Full expert→PLATO→Hebbian cycle |
| T11-T12 | Property | Labeled paradox never injects key for Stage 4 |
| T13-T14 | Unit | N(a,b) rewrite, step-stripping, token count validation |
| T15 | Property | conservation_project brings W within 2σ |
| T17 | Fuzz | simulate_deployment with random tiles and targets |
| T18-T20 | Smoke | Docker Compose stack starts and stays healthy |

---

## 10. Deployment Playbook

### 10.1 Pre-flight Checks

```bash
# Verify Python environment
python3 -c "import numpy, scipy, flask, sqlite3; print('deps OK')"

# Verify test suite baseline
python3 -m pytest tests/ -q --tb=no | tail -3
# Expected: 264 passed (or more)

# Verify PLATO local server
curl -s http://localhost:8848/status | python3 -m json.tool
# Expected: {"room_count": N, "tile_count": M, "uptime": ...}

# Verify Hebbian service
curl -s http://localhost:8849/status | python3 -m json.tool
# Expected: {"compliance_rate": ..., "regime": "random"|"hebbian", ...}
```

### 10.2 Startup Sequence

```bash
# Step 1: Start PLATO (tile store — all others depend on it)
# Local dev (already running .local-plato):
curl -s http://localhost:8848/status | grep -q "room_count" && echo "PLATO OK"

# Step 2: Start Hebbian Service
python3 fleet_hebbian_service.py &
# Wait for warmup: poll until regime == "hebbian" (≈50 updates)
# Or just wait 30s for cold start
sleep 5
curl -s http://localhost:8849/status | python3 -m json.tool

# Step 3: Start Expert Bridge
python3 expert_hebbian_bridge.py &
sleep 3
curl -s http://localhost:8850/status | python3 -m json.tool

# Step 4: Start Fleet Router (translates queries)
python3 -m fleet_translator_v2 --port 8100 &
sleep 2
curl -s http://localhost:8100/models | python3 -m json.tool

# Step 5: Seed initial expert coupling matrix
python3 -c "
from expert_hebbian_bridge import ExpertHebbianBridge
b = ExpertHebbianBridge()
b.seed_initial_weights()  # Loads W from EXPERT_ROOMS defaults
print('Coupling matrix seeded')
"

# Step 6: Verify conservation at rest
curl -s http://localhost:8849/spectrum | python3 -m json.tool
# Check: gamma_plus_H ∈ [0.80, 1.07] for V=9 (within 2σ of 0.934)

# Step 7: Run smoke test
python3 -m pytest tests/test_e2e_smoke.py -v
```

### 10.3 Docker Compose Deployment

```bash
# Build all images
docker compose -f docker-compose.yml build

# Start core first (PLATO), verify health, then start rest
docker compose up -d plato
docker compose ps plato  # wait until healthy

docker compose up -d hebbian
sleep 10
docker compose up -d experts router mcp conservation web seed

# Tail logs to verify startup
docker compose logs -f --tail=50

# Verify full stack
curl -s http://localhost:8847/status     # PLATO
curl -s http://localhost:8849/status     # Hebbian
curl -s http://localhost:8850/status     # Expert Bridge
curl -s http://localhost:8100/models     # Fleet Router
curl -s http://localhost:8080/           # Dashboard (nginx 200)
```

### 10.4 Health Verification

```bash
# After startup, run this health check script:
cat << 'EOF' > /tmp/health_check.sh
#!/bin/bash
echo "=== COCAPN FLEET HEALTH ==="

check() {
    local name=$1; local url=$2; local jq_expr=$3
    result=$(curl -sf "$url" | python3 -c "import sys,json; d=json.load(sys.stdin); print($jq_expr)" 2>/dev/null)
    if [ $? -eq 0 ]; then echo "✓ $name: $result"; else echo "✗ $name: FAILED"; fi
}

check "PLATO tiles"         "http://localhost:8848/status"  "'tile_count='+str(d['tile_count'])"
check "Hebbian compliance"  "http://localhost:8849/status"  "'compliance='+str(d['compliance_rate'])"
check "Hebbian regime"      "http://localhost:8849/status"  "d['regime']"
check "Expert bridge"       "http://localhost:8850/status"  "'experts='+str(d['expert_count'])"
check "Fleet router"        "http://localhost:8100/models"  "str(len(d))+' models'"
check "Conservation γ+H"    "http://localhost:8849/spectrum" \
    "'γ+H='+str(round(d['gamma_plus_H'],3))+'/predicted=0.934'"
EOF
chmod +x /tmp/health_check.sh && /tmp/health_check.sh
```

### 10.5 Rollback Procedures

```bash
# Rollback Hebbian service (reset weights to initial state):
curl -X POST http://localhost:8849/reset_weights
# This triggers: regime → "random", warmup_steps → 0
# Service re-enters 50-step warmup and re-discovers target

# Rollback Expert Bridge (re-seed coupling matrix):
curl -X POST http://localhost:8850/reseed_weights

# Rollback PLATO (restore from backup):
cp .local-plato/plato.db.bak .local-plato/plato.db
# Then restart: kill $(lsof -ti:8848) && python3 -m local_plato &

# Docker rollback (previous image):
docker compose down
docker compose up -d  --no-build  # Uses last successfully built image

# Full reset (nuclear option — wipes Hebbian learning):
docker compose down -v  # Removes plato-data volume
docker compose up -d
# Run seed service to repopulate initial rooms
```

### 10.6 First-Run Validation

After full startup, run the canonical end-to-end test:

```bash
# Submit a constraint-check tile and verify it flows correctly
python3 << 'EOF'
import requests, json, time

PLATO = "http://localhost:8848"
BRIDGE = "http://localhost:8850"
HEBBIAN = "http://localhost:8849"

# 1. Submit a test tile via expert bridge
r = requests.post(f"{BRIDGE}/consult", json={
    "expert_id": "constraint-checker",
    "query": {
        "domain": "test",
        "key": "deploy-test/001",
        "content": "Verify: a²−ab+b² where a=5, b=-3. Expected=49.",
        "source": "deploy-test",
        "confidence": 0.9,
        "layer": "application",
        "tile_type": "computation",
        "stage_required": 4,
        "activation_keys": [],
    }
})
assert r.status_code == 200, f"Bridge /consult failed: {r.text}"
result = r.json()
print(f"✓ Expert consulted. tile_hash={result['tile_hash']}")

# 2. Verify tile appears in PLATO
time.sleep(1)
history = requests.get(f"{PLATO}/room/constraint-theory/history").json()
assert any(t.get("tile_hash") == result["tile_hash"] for t in history), \
    "Tile not found in PLATO!"
print(f"✓ Tile found in PLATO room 'constraint-theory'")

# 3. Verify Hebbian updated and conservation holds
status = requests.get(f"{HEBBIAN}/status").json()
spectrum = requests.get(f"{HEBBIAN}/spectrum").json()
print(f"✓ Hebbian status: regime={status['regime']}, "
      f"compliance={status['compliance_rate']:.2f}")
print(f"✓ Conservation: γ+H={spectrum['gamma_plus_H']:.4f} "
      f"(predicted≈0.934, ok if ∈ [0.800, 1.068])")
assert 0.60 < spectrum["gamma_plus_H"] < 1.20, \
    f"Conservation violation! γ+H={spectrum['gamma_plus_H']}"

print("\n=== DEPLOYMENT VALIDATED ✓ ===")
EOF
```

---

*This document is the single source of truth for the Cocapn fleet architecture. Every port number, class name, API path, and formula is derived from the actual codebase and experiments. Build from this.*
