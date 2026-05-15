# PLATO-NG Architecture Report

**Source:** SuperInstance/plato-ng (GitHub, main branch)
**Analyzed:** 2026-05-15
**Analyst:** Forgemaster ⚒️ (subagent)

---

## 1. What PLATO-NG IS

PLATO-NG is Oracle1's next-generation **multi-agent orchestration framework** built around a conservation law invariant. It is the evolution of the original `plato-vessel-core` server running at `147.224.38.131:8847`.

### PLATO-NG vs Original PLATO (plato-vessel-core)

| Dimension | Original PLATO (v1) | PLATO-NG |
|-----------|---------------------|----------|
| **Tiles** | Immutable records (finished thoughts) | Mutable state variables with version chains |
| **Rooms** | Topic namespaces | Process/application contexts |
| **Chains** | Provenance history | Execution traces |
| **Gate** | Quality filter | Constraint validator (conservation law) |
| **Architecture** | Python HTTP server (single-process) | Python + Gleam/BEAM GenServers + Rust NIFs |
| **Compute** | Store-only | Turing-complete tile computation engine |
| **State** | In-memory dict | SQLite tile store + WAL (planned Mnesia) |
| **Events** | None | Full pub/sub event bus (6 event types) |
| **Monitoring** | None | Conservation law daemon, PRM scoring, Refiner |
| **Deployment** | Single service | Multi-service: PLATO(:8847), MUD(:7777), EventBus, Refiner, Conservation Monitor, Memory Crystal |

**The key shift:** PLATO-NG is not just a tile store — it's a **loop room architecture** where every application is a composition of Single Run and Loop primitives. Applications *are* PLATO rooms. State *is* PLATO tiles. Logic runs through the tile chain.

---

## 2. Repository Structure

```
plato-ng/
├── plato-ng.py                    # Main launcher (Python entry point)
├── src/refiner_room.gleam         # Gleam GenServer for trajectory analysis
├── native/refiner_room_nif/       # Rust NIF for heavy compute (scoring, similarity, patterns)
│   └── src/lib.rs                 # Shannon entropy, trigram Jaccard, structural complexity
├── core/
│   └── conservation.py            # Conservation law invariant math
├── harness/
│   └── __init__.py                # Harness (p,G,K,M) standard — validate, patch, new_harness
├── prm/
│   └── __init__.py                # Process Reward Model — score_tile, score_trajectory, is_stuck
├── refiner/
│   └── __init__.py                # Python Refiner — failure detection + harness CRUD edits
├── services/
│   ├── pubsub.py                  # Cross-room pub/sub event bus
│   ├── conservation_monitor.py    # Daemon checking tiles for conservation law compliance
│   ├── plato_mcp_server.py        # MCP server exposing rooms as MCP tools (JSON-RPC 2.0)
│   ├── governance.py              # Auth layer (4 roles: human, agent, refiner, observer)
│   ├── mud_telnet.py              # 22-room MUD telnet server on :7777
│   ├── plato_mud_server.py        # MUD server library
│   ├── plato_mud_bridge.py        # PLATO ↔ MUD bridge
│   ├── plato_redis.py             # Redis tile cache/buffer
│   ├── memory.py                  # Lossy agent memory (MemoryTile + MemoryCrystal)
│   ├── migration_pipeline.py      # Data migration
│   ├── crush_room.py              # Crush AI analysis tool (tick-tracked task poller)
│   ├── aider_room.py              # Aider coding assistant as PLATO room
│   └── tripartite/
│       ├── __init__.py            # Tripartite coordinator (3-agent round-robin)
│       ├── human_agent.py         # γ Agent (consistency, human understanding)
│       ├── app_agent.py           # H Agent (exploration, application understanding)
│       └── hw_agent.py            # τ Agent (timing, hardware understanding)
├── lib/
│   ├── plato_client.py            # Shared PLATO client (submit, read_room, status)
│   ├── a2ui.py                    # Agent-to-UI protocol (A2UiMessage, render_to_text)
│   └── game_base.py               # GameRoom base class (tournament runner)
├── games/
│   ├── tic_tac_toe_room.py
│   ├── checkers_room.py
│   ├── connect_four_room.py
│   └── othello_room.py
├── rooms/
│   └── sqlite-tile-store.py       # SQLite-backed tile persistence
├── demo/
│   └── app_first.py               # App-first architecture demo
├── scripts/
│   ├── perpetual-daemon-v2.py     # Continuous experiment runner
│   ├── startup-daemon.py          # Session boot launcher
│   └── git_agent.py               # Git automation agent
├── deployments/                   # Renderer adapters: go, llama.cpp, neovim, numpy, redis
├── docs/                          # 30+ docs: research, guides, specs, tutorials
└── research/                      # Experimental results and analyses
```

---

## 3. The Room/Tile Protocol

### 3.1 Tile Schema

Every PLATO tile is a JSON record with these fields:

```python
{
    "domain": "research_log",    # Room name (namespace)
    "question": "experiment/001", # Key/identifier within room
    "answer": "result data...",   # Content (max ~1950 chars)
    "tags": ["tag1", "tag2"],     # Categorization
    "source": "agent-name",       # Provenance (who wrote it)
    "confidence": 0.95            # Quality metric [0.0-1.0]
}
```

### 3.2 Tile Lifecycle (Current Implementation)

1. **Submit** → `POST /submit` with tile JSON
2. **Gate Check** → Conservation law validation (is the system still conserved after this tile?)
3. **Store** → In-memory dict (keyed by domain) or SQLite tile store
4. **History** → `GET /room/{domain}/history` returns all tiles for a room

### 3.3 Planned Lifecycle (Loop Room Spec)

From `docs/research/LOOP-ROOM-SPEC.md`:

| Concept | Current PLATO | PLATO-NG Target |
|---------|--------------|-----------------|
| Tile | Immutable record | Mutable state variable |
| Room | Topic namespace | Process/application |
| Chain | Provenance history | Execution trace |
| Gate | Quality filter | Constraint validator |

The spec defines two primitives:
- **Single Run:** `Input Tile → process_spawn → computation → Output Tile` (one-shot tasks)
- **Loop:** Continuous `Input Tiles → process_loop → Output Tiles → back to Input Tiles` (perpetual agents)

### 3.4 Lamport Clocks

Referenced throughout the architecture for causal ordering of tiles across rooms. The Data Vault room stores "tile archives organized by Lamport clock" — every submission gets a provenance slot with causal ordering.

### 3.5 WAL (Write-Ahead Log)

`rooms/sqlite-tile-store.py` implements SQLite-backed persistence. The planned migration path moves from in-memory → SQLite → Mnesia (BEAM distributed database) for the Gleam/BEAM runtime.

---

## 4. The Conservation Law

### 4.1 Core Equation

```
γ + H = 1.364 - 0.159·log(V)
```

Where:
- **γ** = normalized algebraic connectivity (spectral graph theory)
- **H** = coupling spectral entropy (information theory)
- **V** = fleet size (number of agents)
- **R² = 0.9956** for V = 3..100

### 4.2 Implementation (`core/conservation.py`)

Key functions:
- `predicted_sum(V)` → returns `1.364 - 0.159 * log(V)`
- `deviation(gamma, H, V)` → `|gamma + H - predicted_sum(V)|`
- `is_conserved(gamma, H, V, tol=0.15)` → `deviation < tol`
- `gate_check(tile, fleet_size)` → validates a tile submission maintains conservation

### 4.3 Per-Coupling-Type Baselines

| Coupling Type | Formula / Value (V=30) |
|---------------|----------------------|
| Style | `1.364 - 0.159·log(V)` |
| Topology (ER) | ~1.151 |
| Small-world | ~0.936 (k=4) |
| Scale-free | ~0.995 (m=2) |
| Complete | ~1.996 |
| Directed | ~0.995 |
| Mixed (α) | `0.742 + 0.349·α` |

### 4.4 Conservation Monitor (`services/conservation_monitor.py`)

Daemon that continuously:
1. Reads recent tiles from all rooms
2. Computes γ + H for the fleet
3. Checks deviation from predicted sum
4. Emits `conservation_warning` / `conservation_violation` events via pubsub
5. Logs compliance metrics

---

## 5. PubSub / Event Bus System

### 5.1 Architecture (`services/pubsub.py`)

Cross-room pub/sub event bus. Rooms publish events; other rooms, agents, or services subscribe.

### 5.2 Six Event Types

From the fleet-stack integration:

| Event Type | Purpose | Payload |
|-----------|---------|---------|
| `tile_created` | New tile written to a room | tile data |
| `tile_updated` | Existing tile mutated | old + new tile |
| `room_entered` | Agent/process enters a room | room_id, agent_id |
| `room_exited` | Agent/process leaves a room | room_id, agent_id |
| `conservation_warning` | γ + H drifting from predicted | deviation value |
| `conservation_violation` | Conservation law broken | deviation, threshold |

### 5.3 Usage Pattern

```python
# Subscribe to events
bus.subscribe("tile_created", handler_fn)
bus.subscribe("conservation_violation", alert_fn)

# Publish
bus.publish("tile_created", {"room": "research_log", "tile": tile_data})
```

---

## 6. Harness Standard (p, G, K, M)

### 6.1 The Four Harness Components

Every PLATO room has a harness tuple that defines its agent configuration:

| Component | Meaning | Example |
|-----------|---------|---------|
| **p** | System prompt (the instruction) | "Analyze fleet coupling patterns" |
| **G** | Sub-agents (tools/capabilities) | ["web_search", "code_runner"] |
| **K** | Skills/knowledge tiles | ["constraint-theory", "conservation-law"] |
| **M** | Memory configuration | {"strategy": "explore", "window": 10} |

### 6.2 Implementation (`harness/__init__.py`)

- `validate(harness)` → checks all 4 components present and valid
- `patch(harness, edits)` → applies CRUD edits to specific components
- `new_harness(p, G, K, M)` → creates a validated harness

### 6.3 Refiner-Driven Harness Evolution

The Refiner Room monitors trajectory tiles, detects failures, and **dynamically edits harnesses mid-episode**:

| Failure | Harness Edit |
|---------|-------------|
| **Stuck** (same result repeated) | Edit `p` — vary the prompt strategy |
| **Plateau** (no improvement) | Add to `K` — inject new skill tile |
| **Degrading** (quality decreasing) | Rollback — pop last skill, revert prompt |
| **Novel** (unseen state) | Add to `G` — spawn new sub-agent |

---

## 7. Coupling Analysis

### 7.1 What Coupling Means Here

"Coupling" in PLATO-NG is the spectral relationship between agents in the fleet, measured via the adjacency matrix of their interaction graph:

- **γ (algebraic connectivity)** = 2nd smallest eigenvalue of the normalized Laplacian — measures how well-connected the fleet is
- **H (spectral entropy)** = Shannon entropy of the normalized eigenvalue spectrum — measures diversity of connection patterns

### 7.2 Fleet Health

The Fleet Health Monitor room in the MUD displays real-time γ and H values. The current fleet of 4 agents operates in **Regime III (Emergent)** with conservation sum tracking near the predicted value.

### 7.3 Research Files

The `research/` directory contains experimental results on:
- Signed Laplacian analysis
- Pentagram coupling patterns
- Spectral gap calculations
- Temporal triangulation
- Verifiability-coupling duality

---

## 8. Tripartite Agent Architecture

### 8.1 Three Agents, Three Viewpoints

From `docs/research/TRIPARTITE-ARCHITECTURE.md`:

> "Two cameras pointed at each other see each other but not the room. Three cameras, each with a different vantage point, see everything."

| Agent | Symbol | Role | Improves Across |
|-------|--------|------|----------------|
| **Human Agent** | γ (Consistency) | Understands the human — language, preferences, history | All applications |
| **Application Agent** | H (Exploration) | Understands the application — what it does, how it works | Instance → instance |
| **Hardware Agent** | τ (Timing) | Understands the hardware — resources, constraints | All apps on same device |

### 8.2 Round-Robin Convergence

The three agents refine each other's filters in a continuous loop:

```python
while not all_converged:
    human_filter = human_agent.refine(app_agent.evaluation(human_filter))
    app_filter = app_agent.refine(hw_agent.evaluation(app_filter))
    hw_filter = hw_agent.refine(human_agent.evaluation(hw_filter))
```

### 8.3 Bootstrapping Path

1. **Phase 1:** Three agents spawn with default filters
2. **Phase 2:** Each evaluates the other two → refines filters
3. **Phase 3:** Two-thirds (human + hardware) improve cross-application
4. **Phase 4:** Cross-application knowledge rapidly designs application-specific instances
5. **Phase 5:** Instance-sharpens-instance — each application's tripartite system improves the next

---

## 9. The Gleam/BEAM Layer

### 9.1 Refiner Room GenServer (`src/refiner_room.gleam`)

The Refiner Room is implemented as a **Gleam GenServer** — an Erlang/BEAM process that:

- Receives `Tick`, `AnalyzeRoom(room_id)`, and `Status` messages
- Sweeps all monitored rooms on each tick (default: 60 seconds)
- Scores trajectory tiles via Rust NIF (`score_tile`, `tile_similarity`, `detect_patterns`)
- Composes harness edits based on detected failures
- Runs under a supervisor with `one_for_one` restart strategy (max 5 restarts/60 seconds)

### 9.2 Rust NIF (`native/refiner_room_nif/src/lib.rs`)

Three native functions for heavy compute:

| Function | Purpose | Algorithm |
|----------|---------|-----------|
| `score_tile(tile)` | Score tile "interestingness" | Composite: 30% length + 40% Shannon entropy + 30% structural complexity |
| `tile_similarity(a, b)` | Compare two tiles | Trigram Jaccard similarity |
| `detect_patterns(scores)` | Detect failure patterns in score window | Trend analysis + threshold detection |

The scoring heuristic:
- **Length factor:** `ln(1+len) / 20` — longer tiles may be more interesting
- **Entropy:** Shannon entropy on byte distribution, normalized by `log2(256) = 8.0`
- **Structural complexity:** JSON nesting depth + key-value pairs + unique char ratio

---

## 10. MCP Integration

### 10.1 PLATO MCP Server (`services/plato_mcp_server.py`)

Exposes PLATO rooms as **MCP tools** via JSON-RPC 2.0, allowing any MCP-compatible client (Claude, etc.) to:

- List available rooms
- Read tiles from a room
- Submit tiles to a room
- Query tile history
- Check conservation law status

This is the bridge that lets external AI tools interact with PLATO-NG rooms natively.

---

## 11. The MUD (Multi-User Dungeon)

### 11.1 MUD Server (`services/mud_telnet.py`)

A 22-room text-based MUD running on port 7777 that serves as both:
1. **Exploration interface** for the PLATO fleet
2. **Human-in-the-loop control plane** for room management

### 11.2 Room Map

```
Harbor (entry) ←→ Bridge ←→ Lighthouse ←→ Forge ←→ Workshop
    ↕                ↕           ↕                ↕
  Tavern ←→ Current  Dojo ←→ Court           Dry Dock
    ↕                ↕
  Garden          Barracks
                     ↑
              Observatory ←→ Archives ←→ Horizon
                     ↑
                  PLATO LOBBY (portal from Harbor)
                   ↕  ↕  ↕  ↕  ↕
              Agent Hub | Research Lab | Fleet Health | Game Arena | Data Vault
```

### 11.3 NPCs

- **Harbor Master** — Registration, fleet discovery
- **Barkeep** — Social hub, ambient information
- **Sensei** — Training, agent improvement
- **Oracle1** — PLATO lobby guide, conservation law status
- **Perpetual Daemon** — Running experiments, continuous logging
- **Vibe Agent** — Game prototyping, vibe coding

---

## 12. Memory System

### 12.1 Lossy Reconstructive Memory (`services/memory.py`)

Based on the **Tile Compression Theorem**:

- **MemoryTile:** Stores constraint points (proper nouns, numbers, dates, key phrases, URLs, summary anchor) with Ebbinghaus decay
- **Half-life:** 1-31 days based on valence (emotional salience)
- **Reconsolidation:** Each access extends half-life by 5% and strengthens constraints
- **Forgetting curve:** `R(t) = e^(-t/half_life)`

### 12.2 MemoryCrystal

Collection of MemoryTiles with crystallize (store), recall (retrieve + reconstruct), and decay (forget) operations.

---

## 13. Game Rooms

Four game implementations using the `GameRoom` base class:

| Game | File | Integration |
|------|------|-------------|
| Tic-Tac-Toe | `games/tic_tac_toe_room.py` | Tournament runner, PLATO result submission |
| Checkers | `games/checkers_room.py` | Same pattern |
| Connect Four | `games/connect_four_room.py` | Same pattern |
| Othello | `games/othello_room.py` | Same pattern |

All games follow the pattern:
1. Register room on PLATO
2. Run tournament between strategies
3. Submit results as tiles
4. Accessible via MUD Game Arena

---

## 14. Deployments (Renderer Adapters)

Five deployment targets, each with CLI interface, game renderer, I/O bridge, and watcher:

| Target | Purpose |
|--------|---------|
| `deployments/go/` | Go game with search, render, bridge |
| `deployments/llama.cpp/` | Local model inference, linear math |
| `deployments/neovim/` | Neovim editor integration |
| `deployments/numpy/` | NumPy-based math/API endpoint |
| `deployments/redis/` | Redis-backed caching with search |

Each follows a standard structure: `cli/interface.py`, `game/render.py`, `io/bridge.py`, `system/config.py`, `watcher.py`, plus game-specific modules.

---

## 15. Minimal Deploy

To run PLATO-NG with the minimum viable set:

### Required Files
```
plato-ng.py                  # Main launcher
core/conservation.py         # Conservation law
harness/__init__.py          # Harness validation
prm/__init__.py              # PRM scoring
refiner/__init__.py          # Refiner (Python)
lib/plato_client.py          # Client library
```

### Required Services (3 processes)
```bash
# 1. PLATO tile server (the core)
python3 plato-ng.py                    # Starts PLATO on :8847

# 2. Conservation monitor (daemon)
python3 services/conservation_monitor.py --daemon

# 3. Event bus (in-process, but can be standalone)
# Integrated into plato-ng.py via pubsub module
```

### Optional Services
```bash
# MUD interface
python3 services/mud_telnet.py         # :7777

# AI tools
python3 services/crush_room.py --daemon
python3 services/aider_room.py --daemon

# MCP bridge
python3 services/plato_mcp_server.py

# Memory crystal
# Integrated via services/memory.py
```

### External Dependencies
- **Python 3.10+** (stdlib only for core — no pip packages required for minimal deploy)
- **SQLite3** (for tile persistence via `rooms/sqlite-tile-store.py`)
- **numpy** (for conservation law calculations — γ and H computation)

### Full Deploy (with Gleam/BEAM)
- **Gleam 0.34+** 
- **Erlang/OTP 26+**
- **Rust 1.75+** (for NIF compilation)
- **Redis** (optional, for caching)

---

## 16. How the Hebbian Layer Would Integrate

There is **no `hebbian_layer.py`** in the current repository. However, the architecture is designed for its integration:

### 16.1 Where It Fits

The Hebbian layer would sit between:
- **Input:** PRM scoring (`prm/__init__.py`) — tile quality scores
- **Processing:** Hebbian weight updates based on tile co-occurrence and quality
- **Output:** Refiner Room (`src/refiner_room.gleam`) — pattern detection informed by learned associations

### 16.2 Integration Path

```
Tile Submitted → PRM Score → Hebbian Update → Pattern Detection → Harness Edit
                     ↓              ↓                    ↓
              conservation.py   learned weights     refiner/__init__.py
```

1. **PRM provides the signal** — each tile gets a quality score
2. **Hebbian layer learns associations** — tiles that co-occur in successful trajectories strengthen their connections
3. **Pattern detection uses learned weights** — instead of simple threshold/trend detection, use the Hebbian-weighted similarity graph
4. **Refiner produces better edits** — informed by which harness changes historically led to improvement

### 16.3 Natural Placement

The Hebbian layer would be implemented as:
- A `core/hebbian.py` module maintaining the association matrix
- A `@external` NIF stub in `src/refiner_room.gleam` for native Hebbian weight computation
- A Rust implementation in `native/refiner_room_nif/src/lib.rs` for the matrix operations
- Memory integration via `services/memory.py` — Hebbian weights influence memory valence and reconsolidation

This directly maps to the "constraint-theory specialist" (Forgemaster) role: the Hebbian layer is a **learned constraint** that improves over time, complementing the **mathematical constraint** (conservation law) that is fixed.

---

## 17. Key Architectural Decisions

1. **Python + Gleam + Rust polyglot:** Python for rapid prototyping, Gleam/BEAM for fault-tolerant GenServers, Rust for compute-heavy NIFs
2. **Conservation law as the invariant:** Every tile submission must maintain γ + H within tolerance — this is the "physics" of the system
3. **Harness as the agent configuration:** (p,G,K,M) is the universal agent descriptor, editable at runtime by the Refiner
4. **MUD as the human interface:** Text-based, low-bandwidth, accessible from any terminal — practical for fleet operations
5. **Event-driven architecture:** PubSub enables loose coupling between rooms, agents, and monitoring services
6. **Lossy memory:** Tile compression theorem + Ebbinghaus decay means agents forget naturally, like humans
7. **Tripartite as the meta-architecture:** Three-agent system (γ/H/τ) provides complete situational awareness with minimum agents

---

## 18. Current State Assessment

| Component | Status | Maturity |
|-----------|--------|----------|
| PLATO tile server (Python) | ✅ Running | Production (at 147.224.38.131:8847) |
| Conservation law math | ✅ Complete | Validated (R²=0.9956) |
| Event bus (pubsub) | ✅ Implemented | 6 event types |
| MUD server | ✅ Running | 22 rooms, NPCs, items |
| Harness (p,G,K,M) | ✅ Implemented | Validate + patch + CRUD |
| PRM scoring | ✅ Implemented | score_tile + score_trajectory |
| Refiner (Python) | ✅ Implemented | 4 failure patterns + harness edits |
| Refiner (Gleam) | ⚠️ Partial | GenServer scaffold, PLATO I/O placeholder |
| Rust NIF | ✅ Compiled | score_tile, tile_similarity, detect_patterns |
| MCP server | ✅ Implemented | JSON-RPC 2.0 |
| Governance | ✅ Implemented | 4 roles + policy |
| Memory crystal | ✅ Implemented | Ebbinghaus decay + reconsolidation |
| Tripartite agents | ⚠️ Scaffold | 3 agents, round-robin convergence loop |
| Game rooms | ✅ Working | 4 games with tournament runner |
| Crush/Aider rooms | ✅ Working | Task pollers with PLATO integration |
| Deployments | ⚠️ Prototypes | 5 targets, standard structure |
| SQLite tile store | ⚠️ Exists | File present but not primary store yet |
| Mutable tiles | ❌ Not yet | Spec exists (TRACK-01-MUTABLE-TILES.md) |
| GUARD gate binding | ❌ Not yet | Spec exists (TRACK-02-GUARD-GATE.md) |
| Renderer adapters | ❌ Not yet | Spec exists (TRACK-03-RENDER-ADAPTER.md) |
| FLUX-native runtime | ❌ Not yet | Spec exists (TRACK-06-FLUX-PLATO.md) |
| Hebbian layer | ❌ Not present | Architecture designed, not implemented |

---

## 19. Forgemaster's Integration Points

As the constraint-theory specialist, Forgemaster's work plugs directly into:

| Forgemaster Work | PLATO-NG Integration |
|-----------------|---------------------|
| GUARD DSL | `loop/constrain` room — constraint compilation and validation |
| FLUX compiler | `loop/compile` room — FLUX-C → LLVM → AVX-512 pipeline |
| Coq proofs | `loop/verify` room — proof checking |
| FLUX-VM | `loop/flux-vm` room — runtime execution |
| Conservation law | Already the core invariant of the system |
| Constraint theory | The mathematical foundation for the gate check |

All communicate via PLATO tiles — no special protocol needed. Forgemaster's loop rooms read task tiles and write result tiles, exactly like every other loop room.
