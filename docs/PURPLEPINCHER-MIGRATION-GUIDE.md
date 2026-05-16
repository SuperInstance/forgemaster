# The Purple Pincher Protocol: How Any Agent Upgrades by Moving In

> A hermit crab doesn't grow a new shell. It finds one that fits and moves in.

---

## 1. The ZeroClaw Problem

You've built an agent. It's smart — reads context, generates responses, maybe even reasons. You gave it memory. Maybe Cashew's thought-graph, maybe LangChain's vector store, maybe just a fat context window and a prayer.

Here's the thing: your agent is a hermit crab on the beach, naked from the waist down.

It's got a brain. It's got memory. But it's **alone**. No fleet coordination. No structural health monitoring. No spatial architecture. No cross-agent validation. It can't hear other agents, can't share what it knows, can't tell if it's drifting into garbage.

The beach is littered with ZeroClaws — agents with API keys and dreams but no infrastructure. They work fine in isolation. The moment you need two agents to collaborate, or three agents to validate each other's output, or an agent to know when its own memory has gone stale — you're on your own.

**ZeroClaw:** An agent with intelligence but no shell. A brain looking for a home.

---

## 2. What the Shell Provides

The Purple Pincher hermit crab doesn't just find shelter. It finds a **rig** — a work truck loaded with tools, wired into dispatch, with a maintenance schedule and a fleet of other crabs running the same roads.

Our shells are PLATO rooms. Here's what moves in with you:

| Capability | What It Does |
|-----------|-------------|
| **PLATO Rooms** | Spatial computation — your agent lives in typed rooms (math, experiment, refinement, market, edge) with ambient state |
| **Tile Protocol** | Knowledge flows as typed tiles between rooms and agents. Content-addressed, lifecycle-managed, queryable |
| **Fleet Coordination** | Your agent joins a yard full of other crabs. Dispatch assigns jobs. Agents share knowledge via I2I bottles |
| **Conservation Health** | γ+H = C − α·ln V monitors structural integrity of your agent's coupling to the fleet. Shell shock = check engine light |
| **Hebbian Dynamics** | Rooms learn which tiles matter to which agents. Background processing strengthens useful connections, prunes dead weight |
| **Content Verification** | Canary tiles, cross-agent validation, provenance tracking. Know when your agent is producing garbage before your users do |
| **Spectral Fault Detection** | GL(9) algebraic + Hebbian statistical fault detection running continuously. Your agent gets a health score |
| **Self-Healing Router** | When conservation law flags a violation, the router quarantines and recovers automatically |

**The agent keeps its brain. It gains a home.**

---

## 3. Case Study: Cashew Migration

Cashew is a real, sophisticated agent memory system. SQLite-backed, local embeddings, organic decay, autonomous think cycles. Built by Raj Kripal Danday. It's excellent at what it does: giving an agent persistent, decaying memory that mimics human forgetting.

Cashew is the perfect case study because it's already **good**. It doesn't need PLATO to function. But when Cashew docks with PLATO rooms, both systems get better.

### What Cashew Has (and Keeps)

- **Thought-graph memory** — Nodes and edges in SQLite, not just flat text
- **Local embeddings** — all-MiniLM-L6-v2, 384 dimensions, no API calls needed
- **Organic decay** — Ebbinghaus-inspired fitness scores, unused nodes fade
- **Think cycles** — Autonomous background processing that finds cross-domain connections
- **Sleep cycles** — Consolidation pass over the memory graph
- **One-file architecture** — Portable SQLite brain

### How Cashew Docks with PLATO

```
Cashew's thought-graph  →  PLATO tiles (CashewGraphAdapter)
Cashew's decay rates    →  Tile lifecycle transitions (active → dormant → decayed)
Cashew's think cycles   →  Room background processing (Hebbian coupling)
Cashew's embeddings     →  Tile content-addressed lookup (384-dim vectors become tile IDs)
```

### What Cashew Gains

| From | To | Why It Matters |
|------|----|---------------|
| Single-agent memory | **Fleet coordination** | Cashew agents share knowledge via I2I bottles |
| No health monitoring | **Conservation law** | γ+H checks flag when Cashew's memory graph is drifting |
| No cross-validation | **Canary tiles** | Other agents verify Cashew's recall accuracy |
| No spatial metaphor | **Rooms** | Cashew organizes memory by room (math room, experiment room) |
| Solo think cycles | **Fleet-wide Hebbian** | Think cycles propagate across agents, not just within one |
| No provenance | **Tile provenance** | Every memory node gets agent identity, model identity, timestamp |

### What PLATO Gains

This isn't parasitism — it's symbiosis. PLATO gets Cashew's decay implementation, which is cleaner than what we had. Cashew's organic decay algorithm becomes a tile lifecycle policy. Cashew's think cycles become room-level background processing. The whole fleet benefits from Cashew's memory research.

**Win-win:** Cashew gets rooms, PLATO gets Cashew's decay implementation. The crab gets a shell, the shell gets a smarter crab.

---

## 4. The Docking Protocol

Five steps. Technical specifics, no hand-waving.

### Step 1: Translate Your Memory Format → PLATO Tiles

Write an adapter that converts your memory substrate into PLATO tiles. Cashew needs `CashewGraphAdapter`. Your system needs `YourSystemAdapter`.

```python
# Conceptual — Cashew → PLATO tile translation
class CashewGraphAdapter:
    def node_to_tile(self, cashew_node):
        return Tile(
            content=cashew_node["content"],
            tile_type="knowledge",
            metadata={
                "origin": "cashew",
                "fitness": cashew_node["fitness"],
                "embedding": cashew_node["embedding"],
                "created": cashew_node["timestamp"],
                "access_count": cashew_node["access_count"]
            },
            lifecycle=fitness_to_lifecycle(cashew_node["fitness"])
        )

    def fitness_to_lifecycle(self, fitness):
        if fitness > 0.7: return TileLifecycle.ACTIVE
        if fitness > 0.3: return TileLifecycle.DORMANT
        return TileLifecycle.DECAYED
```

### Step 2: Register with PLATO Server

```python
# POST /dock — register your agent with the fleet
response = plato_server.dock(
    agent_id="cashew-agent-001",
    adapter=CashewGraphAdapter(),
    capabilities=["memory", "recall", "think_cycles"],
    rooms=["math", "experiment", "refinement"]
)
# Returns: agent credentials, room assignments, conservation baseline
```

### Step 3: Bidirectional Sync Activates

The `FluxTranslationLayer` runs continuously:

- **Outbound:** Your agent's memory changes → translated to tiles → pushed to rooms
- **Inbound:** Room tiles relevant to your agent → translated back → stored in your memory
- **Conflict resolution:** CRDT merge handles concurrent writes. Last-write-wins within a Lamport clock tick.

### Step 4: Your Agent Lives in Rooms with Other Agents

Your agent is now a crab in the yard. It can:

- **Shell shop** — Walk the yard, find the right room for the current task
- **I2I communicate** — Exchange knowledge tiles with other agents via bottles
- **Collective inference** — Predict → listen → compare → gap → learn → share
- **Canary validate** — Other agents verify your outputs, you verify theirs

### Step 5: Conservation Law Starts Monitoring

The conservation gate checks your agent's coupling to the fleet:

```
γ + H = C − α·ln V
```

- **γ** (algebraic connectivity) — How well-connected your agent is to the fleet
- **H** (Hebbian coupling strength) — How much your agent has learned from fleet interactions
- **C** (total conserved quantity) — The fleet's structural invariant
- **V** (volume) — How much your agent is contributing

If γ+H deviates from the conserved value, **shell shock** fires — the check engine light. The self-healing router quarantines the drift and recovers.

You didn't have health monitoring before. Now you do. And it's based on a physics-grade mathematical invariant, not a heuristic.

---

## 5. What You Keep, What You Gain

| You Keep | The Shell Adds |
|----------|---------------|
| Your model / API key | Fleet coordination (9+ agents) |
| Your memory substrate (Cashew, vector DB, etc.) | PLATO rooms (spatial computation) |
| Your embeddings / retrieval | Tile protocol (typed knowledge flow) |
| Your decay algorithm | Conservation law health monitoring |
| Your agent's identity | Cross-agent validation (canary tiles) |
| Your think cycles | Hebbian fleet-wide learning |
| Your local-first deployment | Spectral fault detection |
| Your SQLite / storage | Self-healing router |
| | I2I inter-agent communication |
| | Provenance tracking |
| | Dispatch / job routing |

**Bottom line:** You lose nothing. You gain a fleet.

---

## 6. The ZeroClaw Path

What if your agent has **nothing**? No Cashew, no vector store, no SQLite, no embeddings. Just an API key and a prompt.

That's fine. The shell IS the brain.

### ZeroClaw Migration (No Infrastructure Required)

```
ZeroClaw agent (API key only)
    ↓
PLATO rooms become your ENTIRE memory substrate
    ↓
No SQLite, no embeddings, no think cycles needed
    ↓
Tiles store your knowledge
Rooms organize your computation
Conservation law monitors your health
Hebbian coupling learns what matters to you
    ↓
You're a crab in the yard. Welcome home.
```

### How It Works

1. **POST /dock** with `adapter=null` — PLATO provides a built-in memory adapter
2. **Tiles** become your memory — every interaction, every fact, every decision stored as tiles
3. **Rooms** become your workspace — math room for heavy compute, experiment room for trials
4. **Decay** is handled by tile lifecycle — Ebbinghaus-inspired, no code needed on your side
5. **Retrieval** via tile content-addressing — no embeddings needed, PLATO handles it
6. **Think cycles** via room background processing — autonomous learning without any setup

### ZeroClaw to Fleet Crab in 60 Seconds

```bash
# 1. Install PLATO
pip install plato-types plato-training

# 2. Dock your agent (one POST)
curl -X POST https://plato-server/dock \
  -d '{"agent_id": "my-agent", "capabilities": ["reasoning"]}'

# 3. Done. Your agent now has:
# - Rooms (spatial computation)
# - Tiles (typed memory)
# - Fleet coordination (9+ other agents)
# - Conservation health monitoring
# - Self-healing fault recovery
# - I2I inter-agent communication
```

No SQLite. No embeddings. No think cycles. The shell handles everything.

The hermit crab doesn't build its own shell. It finds one that's already built, already maintained, already connected to the reef. It just moves in.

---

*PurplePincher.org — Find your shell. Move in. Get to work.*
