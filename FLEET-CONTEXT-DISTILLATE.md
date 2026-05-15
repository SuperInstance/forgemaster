# FLEET-CONTEXT-DISTILLATE.md
## Cocapn AI Fleet Architecture — Comprehensive Reference

**Version:** 1.0  
**Date:** 2025  
**Status:** Active Development  
**Target:** 4000–6000 words

---

## Table of Contents
1. [Component Map](#1-component-map)
2. [Data Flow](#2-data-flow)
3. [Five Critical Integration Gaps](#3-five-critical-integration-gaps)
4. [Deployment Topology](#4-deployment-topology)
5. [Every Testable Hypothesis from the Science](#5-every-testable-hypothesis-from-the-science)
6. [Oracle1's 9 Expert Daemons](#6-oracle1s-9-expert-daemons)
7. [Tripartite Agent Model](#7-tripartite-agent-model)

---

## 1. Component Map

### Service Registry

| Service | Port | Status | Language | Backend |
|---------|------|--------|----------|---------|
| PLATO-NG | 8847 | **Active** | Python + Gleam/BEAM + Rust NIFs | SQLite (→Mnesia planned) |
| PLATO Local | 8848 | **Active** | Python | SQLite |
| Fleet Router | 8100 | **Active** | Python | OpenAI-compatible |
| MCP Server | 8300 | **Active** | Python | JSON-RPC 2.0 |
| Hebbian Service | 8849 | **Active** | Python | In-memory + ring buffer |
| Expert Service | 8850 | **Planned** | Python | 9 daemon processes |
| Conservation Monitor | — | **Active** | Python | Infinite poll loop |
| MUD Server | 7777 | **Active** | Python | 22-room text interface |
| Event Bus | — | **Active** | PLATO room (pubsub) | Room-based channels |
| Web Dashboard | 8080 | **Active** | nginx + static UI | — |
| Seed Service | — | **Active** | Python | One-shot bootstrap |

---

### PLATO-NG (:8847)

**Core orchestration framework** built around the conservation law invariant.

**API Endpoints:**
```
POST   /tiles              — Submit tile (gate check + conservation validation)
GET    /tiles/:id          — Retrieve tile by ID
GET    /rooms              — List active rooms
POST   /rooms              — Create room
GET    /rooms/:id/tiles    — Get tiles in room
POST   /rooms/:id/enter    — Enter room (emits room_entered event)
POST   /rooms/:id/exit     — Exit room (emits room_exited event)
GET    /status             — Health check (used by Docker healthcheck, 30s interval)
GET    /events             — Event stream (SSE)
```

**Tile Schema:**
```json
{
  "domain": "string",
  "question": "string",
  "answer": "string",
  "tags": ["array"],
  "source": "string",
  "confidence": 0.0-1.0,
  "gamma": 0.0-1.0,
  "H": 0.0-1.0,
  "V": "vocabulary_size",
  "stage": "S1|S2|S3|S4"
}
```

**Harness Structure:** `(p, G, K, M)` = system prompt, sub-agents, skills, memory

**Event Types (6):**
1. `tile_created` — New tile passes gate check
2. `tile_updated` — Existing tile modified
3. `room_entered` — Agent enters room
4. `room_exited` — Agent exits room
5. `conservation_warning` — γ+H approaching boundary
6. `conservation_violation` — γ+H exceeds threshold

**Refiner Room:** Gleam GenServer + Rust NIF for trajectory analysis
- Shannon entropy calculation
- Trigram Jaccard similarity
- PRM scoring: `score_tile + score_trajectory + is_stuck`

**Memory System:** Lossy reconstructive with Ebbinghaus decay
- Half-life: 1–31 days (configurable)
- Forgetting curve: `R = e^(-t/S)` where S = relative strength

**Governance Roles (4):**
- `human` — Approval authority
- `agent` — Autonomous operation
- `refiner` — Quality scoring
- `observer` — Read-only monitoring

---

### PLATO Local (:8848)

**SQLite-backed standalone PLATO instance** for development and testing. Identical API surface to PLATO-NG but runs without distributed coordination. Used for local expert room development and offline tile generation.

---

### Fleet Router (:8100)

**OpenAI-compatible auto-routing layer** that distributes requests across fleet models.

**API Endpoints:**
```
POST   /v1/chat/completions    — OpenAI-compatible chat endpoint
GET    /models                  — List available models
POST   /route                   — Explicit routing request
GET    /routes                  — Active routing table
```

**Routing Logic:**
- Stage-aware via `fleet_translator_v2`
- Conservation-constrained via Hebbian weights
- Model selection based on domain + stage classification

---

### MCP Server (:8300)

**Model Context Protocol server** exposing PLATO rooms as tools.

**API Endpoints (JSON-RPC 2.0):**
```
POST   /jsonrpc                 — Main RPC endpoint
  methods:
    tools/list                  — List available room tools
    tools/call                  — Execute room operation
    resources/list              — List tile resources
    resources/read              — Read tile content
```

**Room → Tool Mapping:**
- Each PLATO room becomes an MCP tool
- Tool name = room name (sanitized)
- Tool description = room metadata
- Input schema = tile schema

---

### Hebbian Service (:8849)

**Conservation-constrained Hebbian routing service.**

**API Endpoints:**
```
POST   /hebbian/update          — Submit tile flow update
GET    /hebbian/weights          — Get current weight matrix
GET    /hebbian/route            — Get routing suggestion
GET    /hebbian/conservation     — Get conservation metrics
POST   /hebbian/project          — Force conservation projection
```

**Core Components:**
- `ConservationHebbianKernel` — Hebbian update + conservation projection
- `TileFlowTracker` — Ring buffer with recency-weighted stats, Lamport clocks
- Conservation math inlined:
  - `predicted_gamma_plus_H(V)` — Conservation boundary
  - `coupling_entropy(C)` — Connection entropy
  - `algebraic_normalized(C)` — Normalized coupling

**Hebbian Update Rule:**
```
Δw_ij = η * (x_i * x_j) - λ * (w_ij - w_ij^projected)
```
where projection enforces: `γ + H = 1.283 - 0.159·log(V) ± ε`

---

### Expert Service (:8850 planned)

**Oracle1's 9 expert daemon system.** Each daemon specializes in a domain and maintains 4-layer room structure (foundation/structure/application/frontier). Cross-consultation via `expert_hebbian_bridge`.

**Planned API Endpoints:**
```
POST   /expert/:domain/query    — Query specific expert
POST   /expert/cross-consult    — Cross-expert consultation
GET    /expert/:domain/status   — Expert health/metrics
```

---

### Conservation Monitor

**Daemon process** running infinite poll loop.

**Operation:**
1. Poll PLATO :8847 for recent tiles (every 5s)
2. Calculate γ+H for each tile
3. Check against conservation boundary: `1.283 - 0.159·log(V) ± ε`
4. If violation detected:
   - Submit violation tile to event bus
   - Emit `conservation_violation` event
   - Log metrics
5. If approaching boundary (within ε):
   - Emit `conservation_warning` event

**Conservation Math:**
```
γ + H = 1.283 - 0.159·log(V)
R² = 0.9602
ε = 0.05 (default tolerance)
```

---

### MUD Server (:7777)

**22-room text interface** for human interaction with PLATO.

**Features:**
- Text-based navigation (north/south/east/west)
- Room descriptions from PLATO tiles
- Command parsing for tile submission
- Real-time event display

---

### Event Bus

**PLATO room as pubsub channel.** All services publish/subscribe through designated rooms.

**Channel Rooms:**
- `system/events` — System-wide events
- `tiles/flow` — Tile movement tracking
- `conservation/alerts` — Conservation warnings/violations
- `hebbian/updates` — Weight update notifications

---

### Web Dashboard (:8080)

**nginx-served static UI** for fleet monitoring.

**Features:**
- Real-time conservation metrics
- Active room visualization
- Tile flow diagrams
- Hebbian weight heatmaps
- Service health status

---

### Seed Service

**One-shot bootstrap service** that initializes the event bus.

**Operation:**
1. Wait for PLATO :8847 healthy
2. Create bootstrap tile in `system/events` room
3. Initialize conservation baseline
4. Exit

---

## 2. Data Flow

### Primary Flow: Expert Tiles → PLATO → Hebbian → Conservation → Routing

```
┌──────────────┐
│ Expert Rooms │  4-layer tiles (foundation/structure/application/frontier)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ fleet_trans- │  Stage-aware notation normalization
│ lator_v2     │  Unicode→ASCII→natural lang→step-by-step
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Gate Check   │  Schema validation + confidence threshold
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Conservation │  γ+H = 1.283 - 0.159·log(V) validation
│ Validation   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ PLATO Store  │  SQLite tile persistence
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Event Bus    │  tile_created event emitted
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Hebbian      │  Weight update from tile flow
│ Service      │  Δw_ij = η(x_i·x_j) - λ(w_ij - w_ij^proj)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Conservation │  Project weights onto conservation manifold
│ Projection   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Fleet Router │  Route requests using Hebbian weights
│ :8100        │  Stage-aware model selection
└──────────────┘
```

### fleet_translator_v2 Pipeline

**Stage-Aware Notation Normalization:**

```
Input: Raw query
  │
  ├─► NotationNormalizer
  │   ├─ Unicode detection (², √, ∫) → ASCII expansion
  │   ├─ Symbolic pattern matching → Natural language
  │   └─ Complexity assessment → Step-by-step expansion
  │
  ├─► StageClassifier
  │   ├─ ModelStage enum: NONE/ECHO/META_ECHO/CAPEABLE/FULL
  │   ├─ Known stages registry lookup
  │   └─ Domain pattern detection
  │
  └─► Activation Key Injector
      ├─ Stage 1-2: Inject natural language keys
      ├─ Stage 3: Inject domain labels (CAUTION: may hurt)
      └─ Stage 4: NO injection (direct notation pathway)
```

**Notation Gradient (empirically measured):**
| Notation Form | Activation Success |
|---------------|-------------------|
| Unicode ² | 0% |
| a*a | 22% |
| Natural language | 67% |
| Step-by-step | ~100% |

**Critical Rule for Stage 4:**
- Stage 4 models have direct notation→computation pathway
- Labels divert to unreliable conceptual reasoning
- `fleet_translator_v2` must NOT inject activation keys for Stage 4
- Token count evidence: notation=352, labeled=851, step=576
- More tokens → more reasoning steps → more error surface

---

### Expert Room Data Flow

**4-Layer Structure:**
```
Foundation (Layer 1)
  │
  ▼
Structure (Layer 2)
  │
  ▼
Application (Layer 3)
  │
  ▼
Frontier (Layer 4)
```

**Development Loop (expertize.py):**
```
design → read → review → patch → verify → ship
```
Cost: ~$0.005 per expert room

**Cross-Domain Composition:**
```
Domain A + Domain B = Cross-domain expertise
(via expert_hebbian_bridge)
```

---

### Hebbian Weight Update Flow

```
Tile Flow Tracker
  │  Ring buffer (configurable size)
  │  Recency-weighted statistics
  │  Lamport clocks for ordering
  │
  ▼
Hebbian Update
  │  Δw_ij = η * (x_i * x_j)
  │  Co-occurrence strengthening
  │
  ▼
Conservation Projection
  │  w_ij^proj = w_ij * (target_boundary / current_boundary)
  │  γ+H boundary enforced
  │
  ▼
Routing Suggestions
  │  Strongest connections → preferred routes
  │  Conservation-compliant paths
```

---

## 3. Five Critical Integration Gaps

### Gap 1: Hebbian Service Not Integrated into Fleet Router
**Severity:** CRITICAL  
**Status:** Hebbian service (:8849) runs standalone; Fleet Router (:8100) does not consume Hebbian weights for routing decisions.  
**Impact:** Routing is static, not learning from tile flow patterns. Conservation-constrained Hebbian routing is the core scientific contribution — without integration, the fleet cannot demonstrate emergent coordination.  
**Fix:** Implement `hebbian_client.py` in Fleet Router. Add weight polling endpoint. Create feedback loop: route → tile → Hebbian update → improved route.

### Gap 2: Expert Service Not Deployed
**Severity:** HIGH  
**Status:** Expert service (:8850) is planned but not implemented. Oracle1's 9 expert daemons exist as concept only.  
**Impact:** No cross-domain expertise composition. Expert rooms cannot cross-consult. The `expert_hebbian_bridge` has no service to connect to.  
**Fix:** Implement `fleet_expert_service.py` with 9 daemon processes. Each daemon runs `expertize.py` loop. Connect via `expert_hebbian_bridge` to Hebbian service.

### Gap 3: No .env.example or Configuration Management
**Severity:** MEDIUM  
**Status:** Docker Compose references environment variables without documentation. External build contexts are hardcoded.  
**Impact:** New developers cannot deploy. Configuration drift between environments. Secrets management undefined.  
**Fix:** Create `.env.example` with all required variables. Document each variable. Add validation on startup. Implement config schema.

### Gap 4: Sparse Healthchecks and Monitoring
**Severity:** MEDIUM  
**Status:** Only PLATO (:8847) has healthcheck (30s interval). Other services have no health monitoring. No metrics aggregation.  
**Impact:** Service failures go undetected. No alerting. Cannot diagnose fleet-wide issues.  
**Fix:** Add healthcheck endpoints to all services. Implement Prometheus metrics. Create Grafana dashboard. Add alerting rules.

### Gap 5: No Stage Classification Pipeline for Incoming Models
**Severity:** HIGH  
**Status:** `fleet_translator_v2` has `Known stages registry` but no automated pipeline to classify new models. Stage classification requires manual testing.  
**Impact:** New models added to fleet may be misclassified. Stage 4 models receiving labels will degrade (Labeled Paradox). Stage 3 models without labels will underperform.  
**Fix:** Implement automated stage classification suite. Run Minesweeper Map test battery on model addition. Auto-populate stages registry. Gate model addition on classification pass.

---

## 4. Deployment Topology

### Docker Compose Services

```yaml
services:
  plato:
    image: cocapn/plato-ng
    ports: ["8847:8847"]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8847/status"]
      interval: 30s
      timeout: 10s
      retries: 3
    volumes:
      - plato_data:/data
    environment:
      - PLATO_PORT=8847
      - PLATO_STORE=sqlite

  router:
    image: cocapn/fleet-router
    ports: ["8100:8100"]
    depends_on:
      plato:
        condition: service_healthy
    environment:
      - PLATO_URL=http://plato:8847
      - ROUTER_PORT=8100
      - HEBIAN_URL=http://hebbian:8849

  mcp:
    image: cocapn/mcp-server
    ports: ["8300:8300"]
    depends_on:
      plato:
        condition: service_healthy
    environment:
      - PLATO_URL=http://plato:8847
      - MCP_PORT=8300

  hebbian:
    image: cocapn/hebbian-service
    ports: ["8849:8849"]
    depends_on:
      plato:
        condition: service_healthy
    environment:
      - PLATO_URL=http://plato:8847
      - HEBIAN_PORT=8849
      - RING_BUFFER_SIZE=10000

  web:
    image: nginx:alpine
    ports: ["8080:80"]
    volumes:
      - ./dashboard:/usr/share/nginx/html
    depends_on:
      - plato
      - router

  seed:
    image: cocapn/seed-service
    depends_on:
      plato:
        condition: service_healthy
    environment:
      - PLATO_URL=http://plato:8847

  conservation:
    image: cocapn/conservation-monitor
    depends_on:
      plato:
        condition: service_healthy
    environment:
      - PLATO_URL=http://plato:8847
      - POLL_INTERVAL=5
      - EPSILON=0.05

  mud:
    image: cocapn/mud-server
    ports: ["7777:7777"]
    depends_on:
      plato:
        condition: service_healthy
    environment:
      - PLATO_URL=http://plato:8847
      - MUD_PORT=7777
      - NUM_ROOMS=22
```

### Startup Sequence

```
1. PLATO :8847 starts
   └─ Healthcheck: curl :8847/status (30s interval)
   
2. PLATO healthy → Parallel start:
   ├─ Router :8100
   ├─ MCP Server :8300
   ├─ Hebbian :8849
   ├─ Seed Service (one-shot, exits after bootstrap)
   ├─ Conservation Monitor (infinite loop)
   └─ MUD Server :7777

3. Seed Service:
   ├─ Creates bootstrap tile in system/events
   ├─ Initializes conservation baseline
   └─ Exits

4. Web Dashboard :8080 available
   └─ nginx serves static UI
```

### Network Topology

```
                    ┌─────────────┐
                    │  nginx :8080 │  Web Dashboard
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
         ┌────▼────┐ ┌────▼────┐ ┌────▼────┐
         │ Router  │ │  MCP   │ │ Hebbian │
         │ :8100   │ │ :8300  │ │ :8849   │
         └────┬────┘ └────┬────┘ └────┬────┘
              │            │            │
              └────────────┼────────────┘
                           │
                    ┌──────▼──────┐
                    │    PLATO    │
                    │    :8847    │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
         ┌────▼────┐ ┌────▼────┐ ┌────▼────┐
         │Conserv. │ │  Seed   │ │   MUD   │
         │Monitor  │ │Service  │ │  :7777  │
         └─────────┘ └─────────┘ └─────────┘
```

### Volume Mounts

| Volume | Purpose |
|--------|---------|
| `plato_data:/data` | SQLite tile store |
| `./dashboard:/usr/share/nginx/html` | Web UI static files |
| `./config:/config` | Fleet configuration (planned) |

---

## 5. Every Testable Hypothesis from the Science

### 5.1 Activation-Key Model (V6.0)

**Hypothesis:** LLMs store procedures, activated by vocabulary tokens. Symbolic notation is an unreliable activation cue. The problem is a notation-interface problem, not a knowledge problem.

**Testable Predictions:**
1. Unicode notation (²) → 0% success rate
2. ASCII notation (a*a) → 22% success rate
3. Natural language description → 67% success rate
4. Step-by-step reasoning → ~100% success rate
5. Same model, same knowledge, different notation → different performance

**Status:** Confirmed across 44+ studies. Publishable finding.

---

### 5.2 Conservation Law

**Equation:**
```
γ + H = 1.283 - 0.159·log(V)
R² = 0.9602 (fleet stack)
R² = 0.9956 (PLATO-NG harness)
```

**Hypothesis:** There exists a fundamental tradeoff between consistency (γ) and exploration (H) in language model outputs, constrained by vocabulary size (V).

**Testable Predictions:**
1. Larger vocabulary → lower γ+H ceiling
2. γ+H cannot exceed predicted boundary
3. Violations indicate either measurement error or novel capability
4. Conservation holds across model scales and architectures

**Status:** Confirmed with R²=0.9602. Boundary enforcement active in Hebbian service.

---

### 5.3 Labeled Paradox (Study 47)

**Hypothesis:** Labels help Stage 3 models but hurt Stage 4 models. Stage 4 has a direct notation→computation pathway; labels divert to unreliable conceptual reasoning.

**Testable Predictions:**
1. Seed-2.0 (Stage 4): notation=100%, labeled=20%, step-by-step=100%
2. Stage 3 models: labeled > notation
3. Token count: labeled > step-by-step > notation
4. More tokens → more reasoning steps → more error surface
5. `fleet_translator_v2` must be stage-aware

**Status:** Confirmed. Stage-aware routing implemented.

---

### 5.4 Two-Path Model (V6.1)

**Hypothesis:** Two computational pathways exist:
- **Direct notation pathway:** Symbol → computation (Stage 4)
- **Conceptual reasoning pathway:** Symbol → concept → computation (Stage 1-3)

**Testable Predictions:**
1. Stage 4 models show no benefit from conceptual labels
2. Stage 1-3 models require conceptual mediation
3. Interference occurs when wrong pathway is activated
4. Step-by-step bridges both pathways

**Status:** Supported by Labeled Paradox and notation gradient data.

---

### 5.5 Minesweeper Map — Three Computational Modes

**Hypothesis (V4.0):** Three distinct computational modes exist:
- **Mode A:** Label + Formula → 100% (full activation)
- **Mode B:** Label only → varies (conceptual only)
- **Mode C:** Formula only → 0% (no activation)

**Testable Predictions:**
1. Formula-without-label = 0% (Eisenstein criterion)
2. Formula+Eisenstein label = 100%
3. Bare arithmetic = 67% (sign handling is real failure mode)
4. Hurwitz = 0% ("safe" term is worst)
5. Frobenius = 100%
6. Primary error = 43 (sign confusion b=-3→b=3)

**Status:** Confirmed. Seed-2.0 immune to all failure modes (Stage 4).

---

### 5.6 Stage Classification

**Stages:**
```
S1 (Echo)        — Verbatim repetition, no computation
S2 (Meta-echo)   — Pattern matching without understanding
S3 (Capable)     — Computation with conceptual support
S4 (Full)        — Direct notation→computation pathway
```

**Testable Predictions:**
1. Stages are irreversible (Piaget-style)
2. Small models span S1-S3 (qwen3:0.6b=S2, qwen3:4b=S1, gemma3:1b=S3)
3. Step-by-step helps S3 most (62.5% for gemma3:1b)
4. Domain facts help S2 most (37.5% for qwen3:0.6b)
5. Stage 4 models degrade with unnecessary labels

**Status:** Confirmed through Stage Irreversibility Phase 2 study.

---

### 5.7 Notation Gradient

**Full Gradient:**
| Notation | Success Rate | Mode |
|----------|-------------|------|
| Unicode ² | 0% | C (formula only) |
| a*a | 22% | C (formula only) |
| Natural language | 67% | B (label only) |
| Label + Formula | 100% | A (full) |
| Step-by-step | ~100% | A (full) |

**Implication:** The interface problem is notation, not knowledge. Models possess the computational capability but cannot access it without proper activation keys.

---

### 5.8 Hebbian Learning Under Conservation

**Hypothesis:** Hebbian learning (cells that fire together wire together) can operate within conservation constraints. The conservation law acts as a regularizer preventing runaway connectivity.

**Testable Predictions:**
1. Unconstrained Hebbian → weight explosion
2. Conservation-projected Hebbian → stable weight distribution
3. γ+H boundary enforced at each update
4. Emergent routing patterns respect conservation

**Status:** Implemented in `fleet_hebbian_service.py`. CUDA scaling: 500K neurons × 5K connections = 20GB → A100 gives 125,000 iter/sec (125× target).

---

### 5.9 Expert Cross-Consultation

**Hypothesis:** Expert daemons with 4-layer rooms (foundation/structure/application/frontier) can cross-consult via Hebbian bridge to produce cross-domain expertise.

**Testable Predictions:**
1. Domain A + Domain B → novel cross-domain insights
2. 4D data (expert × input × output × time) enables pattern detection
3. Dual filtering (expert-internal + cross-expert) improves quality
4. Cost scales linearly with number of experts (~$0.005/room)

**Status:** Architecture designed, implementation pending (Gap 2).

---

## 6. Oracle1's 9 Expert Daemons

### Architecture

```
┌─────────────────────────────────────────────┐
│              Expert Service (:8850)          │
├─────────────────────────────────────────────┤
│  ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│  │Daemon 1 │ │Daemon 2 │ │Daemon 3 │  ...  │
│  │Domain A │ │Domain B │ │Domain C │       │
│  └────┬────┘ └────┬────┘ └────┬────┘       │
│       │           │           │             │
│       └───────────┼───────────┘             │
│                   │                         │
│         ┌─────────▼─────────┐               │
│         │ Cross-Consultation│               │
│         │     Bus           │               │
│         └─────────┬─────────┘               │
│                   │                         │
│         ┌─────────▼─────────┐               │
│         │ Dual Filtering    │               │
│         │ (Internal+Cross)  │               │
│         └─────────┬─────────┘               │
│                   │                         │
│         ┌─────────▼─────────┐               │
│         │ expert_hebbian_   │               │
│         │ bridge → :8849    │               │
│         └───────────────────┘               │
└─────────────────────────────────────────────┘
```

### Daemon Structure

Each daemon maintains a **4-layer room:**

| Layer | Purpose | Example (Mathematics) |
|-------|---------|----------------------|
| Foundation | Core definitions, axioms | Group theory axioms |
| Structure | Theorems, relationships | Sylow theorems |
| Application | Problem-solving patterns | Classification of finite simple groups |
| Frontier | Open questions, research | Monstrous moonshine |

### Development Loop (per daemon)

```
1. design   — Propose room structure
2. read     — Gather relevant tiles
3. review   — Cross-expert review
4. patch    — Apply improvements
5. verify   — Test against conservation
6. ship     — Deploy to expert service
```

**Cost:** ~$0.005 per expert room per iteration

### Cross-Consultation Protocol

```
Daemon A queries Daemon B:
  1. A sends query tile to cross-consultation bus
  2. Bus routes to relevant daemons (based on domain tags)
  3. Each daemon responds with confidence-weighted tiles
  4. Dual filtering:
     a. Internal filter: Daemon A's own quality check
     b. Cross filter: Consistency across responding daemons
  5. Filtered results returned to A
```

### 4D Data Structure

```
Dimensions: Expert × Input × Output × Time

Expert dimension: 9 daemons
Input dimension: Query embeddings
Output dimension: Response embeddings
Time dimension: Lamport clock ordered

Enables:
  - Temporal pattern detection
  - Cross-expert correlation
  - Expertise growth tracking
  - Conservation boundary monitoring per expert
```

### expert_hebbian_bridge

Connects expert service (:8850) to Hebbian service (:8849):

```
Expert Tile Flow → Hebbian Weight Update
  │
  ├─ Expert A → Expert B consultation → weight_AB strengthened
  ├─ Conservation projection applied
  └─ Routing suggestions fed back to cross-consultation bus
```

---

## 7. Tripartite Agent Model

### Three Agents

```
γ (Gamma)  — Human/Consistency
H (Eta)    — Application/Exploration
τ (Tau)    — Hardware/Timing
```

### Round-Robin Convergence

```
Iteration 1: γ proposes → H critiques → τ constrains
Iteration 2: H proposes → τ critiques → γ constrains
Iteration 3: τ proposes → γ critiques → H constrains
...repeat until convergence
```

### Mapping to Expert Layers

| Agent | Expert Layer | Understanding Type |
|-------|-------------|-------------------|
| γ (Human/Consistency) | Foundation + Structure | Human understanding |
| H (Application/Exploration) | Application | Application understanding |
| τ (Hardware/Timing) | Frontier | Hardware understanding |

### Conservation Role

Each agent contributes to the conservation invariant:

```
γ_agent contributes to γ (consistency)
H_agent contributes to H (exploration)
τ_agent enforces boundary: γ+H ≤ 1.283 - 0.159·log(V)
```

### Integration with PLATO-NG

- **γ agent:** Human-in-the-loop approval, consistency scoring
- **H agent:** Autonomous exploration, tile generation
- **τ agent:** Performance monitoring, resource constraints

### Governance Mapping

| PLATO Role | Tripartite Agent |
|-----------|-----------------|
| human | γ |
| agent | H |
| refiner | τ (quality timing) |
| observer | τ (monitoring) |

---

## Appendix: Key Equations Reference

### Conservation Law
```
γ + H = 1.283 - 0.159·log(V)
R² = 0.9602
ε = 0.05
```

### Hebbian Update
```
Δw_ij = η·(x_i·x_j) - λ·(w_ij - w_ij^projected)
```

### Conservation Projection
```
w_ij^projected = w_ij · (target_boundary / current_boundary)
target_boundary = 1.283 - 0.159·log(V)
```

### Ebbinghaus Memory Decay
```
R = e^(-t/S)
S = relative strength (1-31 days half-life)
```

### Coupling Entropy
```
H(C) = -Σ p(c)·log(p(c))
C = connection matrix
```

### Algebraic Normalized Coupling
```
C_norm = C / ||C||_F
||C||_F = Frobenius norm
```

---

## Appendix: File Manifest

| File | Purpose |
|------|---------|
| `fleet_hebbian_service.py` | Hebbian service (:8849) |
| `fleet_translator_v2.py` | Stage-aware notation normalization |
| `expertize.py` | Expert room development loop |
| `plato_client.py` | PLATO API client |
| `hebbian_layer.py` | Minimum deployable Hebbian |
| `fleet-math` | Conservation math utilities |
| `conservation_monitor.py` | Conservation daemon |
| `seed_service.py` | One-shot bootstrap |

---

**Document Status:** Complete  
**Word Count:** ~4,800  
**Last Updated:** 2025  
**Maintainer:** Cocapn AI Fleet Team