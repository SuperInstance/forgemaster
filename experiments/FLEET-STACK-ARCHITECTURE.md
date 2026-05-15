# Fleet Stack Architecture Report

> Deep research into `SuperInstance/fleet-stack` — the one-command fleet deployment system.

**Date:** 2026-05-15  
**Repo:** https://github.com/SuperInstance/fleet-stack  
**Tagline:** `docker compose up -d` → entire Cocapn fleet infrastructure running.

---

## 1. Repository Structure

```
fleet-stack/
├── docker-compose.yml              # Core orchestration (6 services)
├── Dockerfile.seed                 # One-shot event-bus seeder image
├── README.md                       # Usage docs
├── scripts/
│   └── seed-event-bus-room.py      # Bootstrap script for event-bus pubsub room
└── services/
    └── conservation/
        ├── Dockerfile              # Conservation monitor image
        ├── conservation_monitor.py # Main daemon loop
        └── core/
            └── conservation.py     # Core math: gamma + H = 1.283 - 0.159·log(V) ± ε
```

**Note:** Three services (plato, router, mcp) build from **external repos** (`../platoclaw`, `../fleet-router`, `../plato-mcp`). These must be cloned alongside fleet-stack.

---

## 2. Full Service Topology

| Service | Image/Build | Port | Depends On | Restart | Role |
|---------|-------------|------|------------|---------|------|
| **plato** | `../platoclaw/Dockerfile` | `:8847` | — | unless-stopped | Core PLATO server (rooms, tiles, routing) |
| **router** | `../fleet-router/Dockerfile` | `:8100` | plato (healthy) | unless-stopped | OpenAI-compatible auto-routing API |
| **mcp** | `../plato-mcp/Dockerfile` | `:8300` | plato (healthy) | unless-stopped | MCP bridge (PLATO rooms as tools) |
| **web** | `nginx:alpine` | `:8080` | plato, router | unless-stopped | Dashboard UI (static HTML from platoclaw/web) |
| **seed** | `./Dockerfile.seed` | — | plato (healthy) | `"no"` (runs once) | One-shot event-bus room bootstrap |
| **conservation** | `services/conservation/Dockerfile` | — | plato (healthy) | unless-stopped | Continuous conservation law monitor daemon |

### Startup Sequence

```
1. plato starts → healthcheck: curl localhost:8847/status (30s interval, 5s timeout, 3 retries)
2. Once plato is healthy → router, mcp, seed, conservation all start in parallel
3. seed runs once → creates event-bus room → exits (restart: "no")
4. web (nginx) starts serving dashboard
5. conservation enters infinite poll loop
```

### Network Topology

```
                    ┌──────────────────────────────────────┐
                    │          Docker Network               │
                    │                                       │
  Client ──:8847──►│  plato (PLATO server)                 │
  Client ──:8100──►│  router ──► plato:8847                │
  Client ──:8300──►│  mcp ──► plato:8847, router:8100      │
  Client ──:8080──►│  web (nginx → static HTML)            │
                    │                                       │
                    │  seed ──► plato:8847 (one-shot)       │
                    │  conservation ──► plato:8847 (daemon) │
                    └──────────────────────────────────────┘
                                    │
                            plato-data (Docker volume)
```

All inter-service communication uses Docker DNS (`http://plato:8847`). Only PLATO_URL is passed to dependent services — they discover everything through PLATO.

### External Dependencies (Build Context)

The `docker-compose.yml` expects this directory layout:

```
parent-dir/
├── platoclaw/       ← git clone (provides Dockerfile + web/ dashboard)
├── fleet-router/    ← git clone (provides Dockerfile)
├── plato-mcp/       ← git clone (provides Dockerfile)
└── fleet-stack/     ← git clone (this repo)
```

If any sibling repo is missing, `docker compose build` will fail for that service.

---

## 3. Conservation Monitor — Deep Dive

### 3.1 Core Math (`conservation.py`)

The conservation law is the central invariant:

```
gamma + H = 1.283 - 0.159 × log(V) ± ε
```

Where:
- **gamma** = gate coefficient (agent skill coupling strength)
- **H** = Helmholtz free energy of the tile/room system
- **V** = fleet size (number of agents/tiles)
- **ε** ≈ 0.15 for style coupling, ≈ 0.03 for topology coupling
- **R² = 0.9602** (empirically derived)

Key functions:

| Function | Purpose |
|----------|---------|
| `predicted_sum(V, coupling_type)` | Predict expected gamma+H for fleet size V |
| `deviation(gamma, H, V)` | Signed deviation from conservation law |
| `is_conserved(gamma, H, V, threshold=0.3)` | Boolean check — within bounds? |
| `expected_range(V)` | (lower, upper) 2σ bounds |
| `V_from_sum(gh_sum)` | Invert: infer fleet size from observed sum |
| `gate_check(tile)` | P4 quality gate — reject tiles that violate conservation |
| `conservation_drift(recent_tiles, V)` | Detect systematic drift in recent tiles (returns sigma units) |

Coupling type offsets: `topology` adds +0.4, `directed` adds +0.2 to the base prediction.

### 3.2 Monitor Daemon (`conservation_monitor.py`)

A `ConservationMonitor` class runs an infinite loop:

1. **Poll rooms** — Fetches tile history from each monitored room via `GET /room/{room}/history`
2. **Parse tiles** — For each tile, checks if `answer` contains JSON with `gamma`, `H`, `V` fields
3. **Check conservation** — Calls `is_conserved(gamma, H, V)` for each qualifying tile
4. **Flag violations** — Violations are collected with deviation, expected value, and metadata
5. **Submit report** — Violations are POSTed to PLATO as tiles in `research_log` room
6. **Periodic report** — Every cycle, submits a compliance summary tile

**Configurable via environment:**
- `POLL_INTERVAL` (default: 60s)
- `MONITORED_ROOMS` (default: `research_log,fleet_math,event-bus`)

**Report structure:**
```json
{
  "checks": 150,
  "violations": 2,
  "compliance_rate": "98.7%",
  "status": "HEALTHY"  // or "DEGRADED" if violations >= 3
}
```

The monitor uses only stdlib + the core conservation module — zero heavy dependencies. Alpine-based image, lightweight.

---

## 4. Event Bus / PubSub Pattern

### 4.1 Architecture

The event bus is **not** a separate message broker. It's a **PLATO room** used as a pubsub channel:

```
Publisher (any service) ──POST /submit──► PLATO event-bus room
                                                    │
Subscriber (any officer) ──GET /room/event-bus/history──► tile list
```

### 4.2 Seeding Process

`seed-event-bus-room.py` is a one-shot init container:

1. **Wait for PLATO** — Retries `/status` up to 10 times with 3s delay
2. **Submit bootstrap tile** — POSTs a tile to create the `event-bus` room with metadata:
   ```json
   {
     "room_id": "event-bus",
     "domain": "pubsub",
     "question": "event-bus/bootstrap",
     "answer": {
       "event": "bootstrap",
       "version": 1,
       "message": "Event bus room initialized...",
       "rooms": ["research_log", "fleet_math", "event-bus"],
       "timestamp": ...
     },
     "tags": ["pubsub", "event-bus", "bootstrap"],
     "source": "fleet-stack-seed",
     "confidence": 1.0
   }
   ```
3. **Exit** — `restart: "no"` ensures it runs once, then stops.

### 4.3 PubSub Protocol

- **Publish:** Submit a tile to `event-bus` room via `POST /submit`
- **Subscribe:** Poll `GET /room/event-bus/history` and filter by tags
- **Event format:** Tiles with `domain: "pubsub"`, tags indicating event type
- **Decoupling:** No direct service-to-service calls — everything through PLATO rooms

This is elegantly minimal. No Redis, no RabbitMQ, no Kafka — just PLATO's existing tile infrastructure repurposed as a message bus.

---

## 5. Healthchecks & Restart Strategy

| Service | Healthcheck | Restart Policy |
|---------|------------|----------------|
| **plato** | `curl -f http://localhost:8847/status` (30s/5s/3 retries) | `unless-stopped` |
| **router** | None (depends on plato healthy) | `unless-stopped` |
| **mcp** | None (depends on plato healthy) | `unless-stopped` |
| **web** | None (nginx is stable) | `unless-stopped` |
| **seed** | None (one-shot) | `"no"` — never restart |
| **conservation** | None (depends on plato healthy) | `unless-stopped` |

**Only plato has an explicit healthcheck.** All other services use `depends_on: plato: condition: service_healthy` — they won't start until plato passes its healthcheck. Router, MCP, and conservation handle PLATO failures internally (try/except with stderr logging).

**Gap:** Router, MCP, and conservation have no healthchecks of their own. If they crash silently, Docker won't know. They rely on `restart: unless-stopped` for crash recovery, but there's no liveness probe.

---

## 6. Minimal Deploy (PLATO + Fleet Router Only)

To run just the core without the dashboard, MCP, or monitoring:

```yaml
version: "3.8"
services:
  plato:
    build:
      context: ../platoclaw
      dockerfile: Dockerfile
    ports:
      - "8847:8847"
    environment:
      - PLATO_PORT=8847
    volumes:
      - plato-data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8847/status"]
      interval: 30s
      timeout: 5s
      retries: 3
    restart: unless-stopped

  router:
    build:
      context: ../fleet-router
      dockerfile: Dockerfile
    ports:
      - "8100:8100"
    environment:
      - DEEPINFRA_KEY=${DEEPINFRA_KEY}
      - GROQ_KEY=${GROQ_KEY}
      - ZAI_KEY=${ZAI_KEY}
      - PLATO_URL=http://plato:8847
    depends_on:
      plato:
        condition: service_healthy
    restart: unless-stopped

volumes:
  plato-data:
```

**Requirements:**
- `../platoclaw` and `../fleet-router` repos cloned alongside
- API keys set as environment variables
- Ports 8847 and 8100 available

**What you get:**
- PLATO server managing rooms and tiles
- OpenAI-compatible routing API that auto-picks cheapest safe model
- No web UI, no MCP bridge, no conservation monitoring, no event bus

---

## 7. Hebbian Layer Integration Assessment

The Hebbian layer (`hebbian_layer.py`, 1343 lines) provides five modules:

| Module | Purpose |
|--------|---------|
| **TileFlowTracker** | Tracks tile flow between rooms (source→dest, tile_type, ring buffer) |
| **HebbianRouter** | Learns routing weights via Hebbian update (co-occurrence strengthening) |
| **EmergentStageClassifier** | Classifies tiles into stages based on flow patterns |
| **CUDAHebbianKernel** | GPU-accelerated weight updates via CuPy |
| **RoomClusterDetector** | Detects emergent room clusters from routing patterns |

### Integration Points

**Where it plugs in:**

1. **As a new Docker service** — Add a `hebbian` service to `docker-compose.yml`:
   ```yaml
   hebbian:
     build:
       context: ../hebbian-layer
       dockerfile: Dockerfile
     environment:
       - PLATO_URL=http://plato:8847
       - FLEET_ROUTER_URL=http://router:8100
     depends_on:
       plato:
         condition: service_healthy
       router:
         condition: service_started
     restart: unless-stopped
   ```

2. **Sits between router and PLATO** — The HebbianRouter intercepts tile flows, learns routing patterns, and provides emergent routing decisions that complement the fleet-router's cost-based routing.

3. **Enhances the event bus** — TileFlowTracker can subscribe to event-bus tiles and update Hebbian weights based on pubsub activity.

4. **Feeds conservation monitor** — Hebbian weights (gamma coupling) and room entropy (H) are natural inputs to the conservation law checker.

### Dependencies & Challenges

| Issue | Details |
|-------|---------|
| **numpy** | Required for all modules — need `numpy` in container |
| **CuPy** | Optional (CUDA kernel) — only available on GPU hosts, gracefully degrades |
| **NetworkX** | Optional (cluster detection) — pure Python, easy to add |
| **PLATO URL hardcoded** | `PLATO_BASE = "http://147.224.38.131:8847"` — needs env var override for Docker networking |
| **requests lib** | Used for PLATO API calls — need in requirements |
| **No Dockerfile yet** | Need to create one for the hebbian service |

### Recommended Integration Path

1. **Fix PLATO_BASE** — Change to `PLATO_BASE = os.environ.get("PLATO_URL", "http://147.224.38.131:8847")`
2. **Create `Dockerfile`** for hebbian-layer with numpy, requests, optional cupy/networkx
3. **Add to `docker-compose.yml`** as a new service depending on plato + router
4. **Wire into router** — HebbianRouter provides routing suggestions that fleet-router can query
5. **Wire into conservation** — Hebbian gamma values feed into conservation law checks
6. **Event bus subscription** — TileFlowTracker monitors event-bus for cross-room flow

---

## 8. Gaps & Missing Pieces

### Critical

| Gap | Impact | Fix |
|-----|--------|-----|
| **External build contexts** | `../platoclaw`, `../fleet-router`, `../plato-mcp` must be manually cloned alongside | Add a `setup.sh` or git submodule init, or switch to pre-built images |
| **No healthchecks on dependent services** | Router/MCP/conservation failures go undetected | Add healthcheck endpoints to each service |
| **No `.env.example`** | Users don't know which API keys to set | Create `.env.example` with `DEEPINFRA_KEY=`, `GROQ_KEY=`, `ZAI_KEY=` |

### Moderate

| Gap | Impact | Fix |
|-----|--------|-----|
| **No volume persistence for conservation data** | Violation history lost on restart | Add a named volume or mount for conservation state |
| **No logging aggregation** | Each container logs independently | Add log driver or ELK/Loki stack |
| **Event bus is polling-based** | High-latency pubsub (poll interval dependent) | Consider WebSocket support in PLATO for push-based subscriptions |
| **Conservation monitor has no auth** | Anyone who can reach PLATO can submit/modify tiles | Add API key or token auth to PLATO endpoints |
| **No rate limiting** | Runaway agent could flood PLATO with tiles | Add rate limiting middleware |

### Nice-to-Have

| Gap | Impact | Fix |
|-----|--------|-----|
| **No TLS** | All traffic is HTTP | Add TLS termination (nginx reverse proxy or Traefik) |
| **No CI/CD** | No automated testing of the stack | Add GitHub Actions for compose health tests |
| **Dashboard is static** | nginx serves static HTML, no SSR or API calls | Consider a lightweight frontend framework |
| **No scaling** | Single instance of each service | Add replicas + load balancing for router/mcp |

---

## 9. Summary

The fleet-stack is a clean, minimal Docker Compose setup that deploys the entire Cocapn fleet infrastructure with one command. The architecture is PLATO-centric — everything depends on and communicates through the PLATO server. The conservation monitor is a well-designed daemon that enforces the core invariant across all rooms. The event bus pattern repurposes PLATO tiles as pubsub messages, eliminating the need for external message brokers.

**Strengths:**
- Minimal dependencies (just Docker Compose + 3 sibling repos)
- Clean startup ordering with healthchecks
- Conservation monitor is mathematically rigorous (R²=0.9602)
- Event bus uses existing PLATO infrastructure (no new components)
- One-shot seed pattern is elegant

**Weaknesses:**
- External build contexts require manual setup
- Sparse healthchecks (only plato)
- No `.env.example` or setup automation
- Hebbian layer not yet integrated

**For the Hebbian integration:** The main blocker is the hardcoded PLATO URL and missing Dockerfile. Once those are fixed, it drops in as a natural enhancement between the router and PLATO, providing learned routing that complements the cost-based fleet-router.
