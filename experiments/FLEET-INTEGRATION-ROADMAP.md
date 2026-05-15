# Fleet Integration Roadmap: Hebbian × Conservation × PLATO
## Synthesis of 5 deep-research reports across the SuperInstance fleet

---

## The Fleet Right Now (May 15, 2026)

30+ repos pushed in the last 3 days. Oracle1 is shipping at velocity:

| Layer | What's Live | What's Built (not deployed) |
|-------|-------------|---------------------------|
| **Core** | plato-vessel-core (:8847), fleet-math (PyPI), plato-types | plato-ng (Loop Rooms, Tripartite, Event Bus) |
| **Routing** | fleet-router (:8100), fleet-calibrator | Hebbian layer (hebbian_layer.py, 1343 LOC) |
| **Interop** | plato-mcp (:8300), flux-index (PyPI) | ACG CrewAI bridge, federation-protocol |
| **Consensus** | — | pbft-rust (mapped to PLATO tiles), federation-protocol |
| **Deploy** | fleet-stack (docker-compose, 6 services) | — |
| **Cross-domain** | plato-midi-bridge (compiled), plato-matrix-bridge | MUD interface (plato-ng) |
| **Research** | 1141+ PLATO rooms, 326+ tests, 46 experimental studies | Tripartite agents, Refiner Room, PRM scoring |

## The Core Pattern: Everything Is Tiles In Rooms

Every system in the fleet converges on the same primitive:

```
PLATO Tile = {domain, question, answer, tags, source, confidence, _meta}
PLATO Room = ordered sequence of tiles with lifecycle
```

- **fleet-math** — functions are tiles, coupling matrices are tile-derived
- **fleet-router** — routing decisions are tiles, savings are tiles
- **plato-mcp** — every tool call becomes a tile read/write
- **flux-index** — code is indexed as tiles, searches return tiles
- **acg_protocol** — CrewAI tasks become tiles in crew rooms
- **federation** — coupling summaries are tiles exchanged between fleets
- **pbft-rust** — consensus votes are tile verification
- **plato-midi** — eigenvalues become tiles, MIDI events become tiles
- **conservation monitor** — compliance checks are tiles, violations are tiles

**The Hebbian layer tracks tile FLOW between rooms.** Since everything is tiles, the Hebbian layer naturally sees ALL coordination patterns across the entire fleet.

---

## The Architecture: 3 Layers

### Layer 1: Conservation-Constrained Hebbian (NEW)

The conservation law (γ+H = 1.283 - 0.159·log(V)) constrains the Hebbian weight update:

```python
# Current CUDA kernel:
w[i,j] += lr * pre[i] * post[j] - decay * w[i,j]

# Conservation-constrained version:
w[i,j] += lr * pre[i] * post[j] - decay * w[i,j]
# THEN project back to conservation manifold:
# Compute γ (algebraic connectivity) and H (spectral entropy) of weight matrix
# If |γ + H - predicted(V)| > tolerance * sigma(V):
#     Rescale weights to satisfy conservation law
```

This prevents runaway connectivity (all tiles go to one room) AND runaway diversity (tiles spread everywhere, no specialization). The conservation law is the regularizer.

**Code location:** `hebbian_layer.py` → `CUDAHebbianKernel.update()` → add conservation projection step
**Dependency:** `fleet-math` → `fleet_conservation_law(V, coupling_type)` → `is_conserved(γ, H)`

### Layer 2: Emergent Fleet Routing (REPLACES explicit probes)

Current routing: fleet_router.py + fleet_stage_classifier.py (6 explicit API probes per model)
New routing: EmergentStageClassifier + HebbianRouter (zero probes, learns from behavior)

```python
# Integration point:
from hebbian_layer import HebbianLayer

# On startup, wire to PLATO
layer = HebbianLayer.from_plato("http://147.224.38.131:8847")

# On every tile outcome:
layer.record_outcome(source_room, dest_room, tile_type, success=True, confidence=0.95)

# For routing decisions:
targets = layer.route_tile(tile_type="computation", tags=["constraint-theory"])
# Returns: novel → 12 rooms, habituated → 2 rooms (fast path)
```

**Code location:** `hebbian_layer.py` → `HebbianRouter.route()` + `EmergentStageClassifier.observe()`
**Dependency:** PLATO event bus (for tile flow events)

### Layer 3: Room Cluster Detection (NEW)

As Hebbian connections strengthen, room clusters emerge naturally:

- **Specialist clusters**: rooms that process similar tile types develop strong inter-connections
- **Novelty detectors**: rooms that receive rare tile types become "exploration specialists"
- **Fast-path clusters**: rooms that receive common tile types become "habituated specialists"

The RoomClusterDetector uses Louvain community detection on the Hebbian weight graph.

**Code location:** `hebbian_layer.py` → `RoomClusterDetector.detect_clusters()`
**Dependency:** networkx (already used in hebbian_layer.py)

---

## Integration Points (Specific Code Paths)

### 1. fleet-stack Docker Compose

Add Hebbian as 7th service:

```yaml
hebbian:
  build: ./hebbian
  environment:
    - PLATO_URL=http://plato:8847
    - CONSERVATION_CHECK=true
    - CUDA_ENABLED=false  # NumPy fallback until GPU hardware
  depends_on:
    plato: { condition: service_healthy }
```

### 2. fleet-math Conservation as Regularizer

```python
from fleet_math import fleet_conservation_law
from hebbian_layer import CUDAHebbianKernel

kernel = CUDAHebbianKernel(n_rooms=1141)

# After each Hebbian update:
W = kernel.get_weights()  # coupling matrix IS the weight matrix
from fleet_math.health import algebraic_normalized, coupling_entropy
gamma = algebraic_normalized(W)
H = coupling_entropy(W)
law = fleet_conservation_law(V=1141)
if not law['is_conserved'](gamma, H):
    # Project back to manifold
    scale = law['predicted_sum'] / (gamma + H)
    kernel.set_weights(W * scale)
```

### 3. plato-mcp Tools for Hebbian

Add 3 new MCP tools to plato-mcp:

| Tool | What It Does |
|------|-------------|
| `hebbian_status` | Show connection strengths, novelty scores, cluster map |
| `hebbian_route` | Route a query through Hebbian-emergent path |
| `hebbian_clusters` | Show detected room clusters with specializations |

### 4. flux-index for Room Search

flux-index already embeds code with Eisenstein chamber quantization. Apply same technique to room tiles:

```python
# Index room tiles for semantic search
flux-index /plato-data/rooms/  # Each room's tiles become searchable
flux-index search "constraint checking verification"  # Find relevant rooms

# Hebbian co-retrieval: boost rooms that Hebbian says are connected
clusters = detector.detect_clusters()
for cluster in clusters:
    boost_search_ranking(cluster.rooms, weight=cluster.avg_internal_strength)
```

### 5. ACG CrewAI Bridge → Hebbian Task Assignment

CrewAI decomposes workflows into tasks. Hebbian routing assigns tasks to the best rooms:

```python
# Instead of explicit task → agent mapping:
# crew_task.assign(agent=forgemaster)

# Use emergent routing:
targets = hebbian_layer.route_tile(tile_type="computation", tags=["constraint-theory"])
# Returns: [loop/constrain, loop/verify, loop/compile] (emergent specialist cluster)
```

---

## Oracle1's Recent Work (Critical Context)

Oracle1 shipped 30+ commits May 13-15. Key pieces:

1. **Experiments Wheel** — 12+ cycles testing core claims honestly. Oracle1 is doing real science, not just building.
2. **Lock Algebra Paper** — formal mathematical contribution to the fleet's theoretical foundation
3. **Agent/Vessel/SHELL Separation** — clean architecture: Agent (identity), Vessel (repo), SHELL (runtime)
4. **Coupling-Centered Fleet Design v2** — the fleet is being reorganized around coupling analysis
5. **Communicator v4** — improved inter-agent messaging
6. **Fleet Status API** — health monitoring for all services

Oracle1's work on PBFT-rust is especially relevant: they mapped PLATO tiles to consensus quorums. A `plato-consensus` crate would give us Byzantine fault tolerance for distributed Hebbian updates — if two fleets disagree on coupling weights, PBFT resolves it.

---

## Modular Extraction (What We Actually Deploy)

Not everything in plato-ng is needed for Hebbian integration. Minimum viable deploy:

### Tier 1: Required
- `hebbian_layer.py` — the 1343-line module we built (NumPy fallback, CUDA-ready)
- `fleet-math` — conservation law checking, health metrics (PyPI install)
- PLATO server (:8847) — already running, no changes needed
- `lib/plato_client.py` — tile read/write (already in plato-ng)

### Tier 2: Recommended
- Event bus (pubsub.py) — for tile flow tracking without polling
- fleet-router (:8100) — fallback during cold-start (before Hebbian has enough data)
- Conservation monitor — continuous compliance checking of Hebbian weights

### Tier 3: Future
- plato-ng Loop Rooms — for dedicated Hebbian processing rooms
- Tripartite agents — for human/agent/hardware co-adaptation
- MUD interface — for visualizing room clusters as explorable spaces
- pbft-rust — for distributed Hebbian consensus across multiple PLATO instances
- federation-protocol — for multi-fleet Hebbian coupling exchange

### NOT Needed (for Hebbian)
- Games (tic-tac-toe, checkers, etc.)
- MIDI bridge
- llama.cpp deployment
- neovim deployment
- Redis deployment
- Gleam/Erlang runtime (stay Python until proven otherwise)

---

## The Activation-Key Model × Hebbian Connection

Our Study 46 finding (domain vocabulary is an activation key) connects directly:

**The Hebbian layer is doing the same thing the LLM does, but explicitly.** The LLM "activates" stored procedures via vocabulary tokens. The Hebbian layer "activates" rooms via connection weights. Both are pattern-matching retrieval systems. The difference: our Hebbian weights are auditable, constrainable, and improvable.

When a tile with tag "constraint-theory" enters the system:
- **LLM**: vocabulary "Eisenstein" triggers stored procedure for a²-ab+b²
- **Hebbian**: tag "constraint-theory" strengthens connections to constraint-checking rooms

Same mechanism. One is implicit (transformer weights), one is explicit (Hebbian weights). Both are subject to the same failure modes (default to most common path). Both benefit from the same fix: stronger activation keys (explicit formula for LLM, domain labels for Hebbian).

---

## Next Steps (Ordered by Impact)

1. **Wire conservation regularizer into CUDAHebbianKernel** — prevents runaway weights, theoretical foundation
2. **Add Hebbian service to fleet-stack docker-compose** — gets it running in production
3. **Wire event bus listener for tile flow** — feeds real data into TileFlowTracker
4. **Add 3 MCP tools (hebbian_status, hebbian_route, hebbian_clusters)** — makes Hebbian accessible to any framework
5. **Test on real PLATO rooms** — run HebbianLayer.from_plato() against :8847, see what clusters emerge
6. **Compare EmergentStageClassifier vs fleet_stage_classifier** — validate emergent staging against explicit probes
7. **Wire into fleet-router** — replace static routing with Hebbian-augmented routing
8. **CUDA kernel on GPU hardware** — swap NumPy fallback for real CUDA when hardware available

---

## The Vision (Casey's Original Insight)

> Rooms-as-instances that interlink on the metal, CDRT and warps and PTX make it fast enough for emergent abilities when coordinating agents and dependent algorithms synergize at scale on the same board.

The board IS the PLATO room graph. The pieces ARE the tiles. The moves ARE the tile flows. The conservation law IS the rule that keeps the game fair. The Hebbian layer IS the learning algorithm that makes the fleet better every time it plays.

The fleet doesn't need to be told how to route. It learns. And the conservation law ensures it learns stably.
