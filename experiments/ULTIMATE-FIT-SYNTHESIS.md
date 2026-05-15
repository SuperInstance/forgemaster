# The Ultimate Fit — Fleet Architecture Synthesis

*Forgemaster's analysis of Oracle1's PLATO-NG, external protocols (MCP/A2A), event sourcing patterns, and FM's behavioral layer. What to build, what to skip, where we agree, where we diverge.*

---

## What Oracle1 Has (Structural)

Oracle1 built the **spine** — the mathematical and runtime infrastructure:

1. **fleet-math** (v0.3.0): Spectral analysis, coupling tensors, RMT classification, type-aware health metrics, conservation law (γ+H = 1.364-0.159·log(V))
2. **fleet-types**: Canonical AgentId, CouplingTensor, StyleVector, TaskStatus
3. **federation-protocol**: Minimum viable coupling exchange between PLATO instances
4. **plato-midi-bridge**: Gauge connections, holonomy computation, format bridging
5. **plato-ng**: Loop room spec, BEAM/Gleam runtime design, mutable tiles, vibe coding agent, game decomposition, FLUX-VM native PLATO
6. **MUD server**: 22-room explorable lobby on :7777, game arena, tic-tac-toe tournament

Oracle1's architecture is **structural** — how things connect, how to measure fleet health, how rooms relate mathematically. The conservation law, spectral gap, and Fiedler values are real math, validated on real data.

## What FM Has (Behavioral)

FM built the **nervous system** — how models behave, where they break, how to route:

1. **Critical angles**: Binary phase transitions, per-model per-domain, prompt-dependent
2. **Fleet router**: 3D routing (model × domain × temperature), 84% cost reduction
3. **C(m,t) framework**: Five multiplicative factors governing model capability
4. **Room protocol**: PLATO rooms as execution contexts (overlaps with Oracle1's loop rooms)
5. **Functional imaging**: fMRI for model cognition, stereo reconstruction
6. **25 findings**: Phase transitions, temperature switches, non-overlapping infinities
7. **Seed tools**: 7 attachments verified with live API calls

FM's architecture is **behavioral** — what each model can actually do, where it fails, how to exploit that for cost optimization.

## What the External World Has (Protocols)

The industry is converging on two complementary standards:

1. **MCP** (Anthropic, Nov 2024): Agent-to-tool communication. Vertical integration. How an agent accesses databases, APIs, file systems.
2. **A2A** (Google, Apr 2025): Agent-to-agent communication. Horizontal coordination. How agents discover each other, negotiate, delegate.

The emerging pattern: MCP for tools, A2A for agents. Event sourcing for audit trail. CRDTs for edge consistency. State machines for control flow. BEAM for runtime.

## THE SYNTHESIS: Three Layers, One System

```
┌─────────────────────────────────────────────────────────┐
│                    LAYER 3: BEHAVIORAL                    │
│              FM's critical angles + routing               │
│    "Route to the cheapest model that won't break"        │
│    Model registry, CA map, temperature switch            │
│    Fleet router API: POST /v1/completions                │
├─────────────────────────────────────────────────────────┤
│                    LAYER 2: STRUCTURAL                    │
│         Oracle1's spectral math + types + federation      │
│    "Measure fleet health, detect anomalies, federate"    │
│    CouplingTensor, conservation law, Fiedler, NMI        │
│    Health API: GET /health → {structural, behavioral}    │
├─────────────────────────────────────────────────────────┤
│                    LAYER 1: RUNTIME                       │
│         PLATO-NG loop rooms + FLUX VM + BEAM             │
│    "Everything is a loop or a single run"                │
│    Gleam GenServers, mutable tiles, gauge connections    │
│    Room API: read_tile → think → write_tile → read_tile  │
└─────────────────────────────────────────────────────────┘
```

Each layer is independent. Each can be built, tested, and deployed separately. But they interlock:

- **Layer 1 provides the execution substrate.** Rooms run loops. Tiles carry state. The runtime doesn't know about models or routing.
- **Layer 2 measures the system.** Spectral health tells you if rooms are well-connected. Anomaly detection tells you if something is wrong. Federation lets multiple PLATO instances coordinate.
- **Layer 3 makes decisions.** When a room needs a model, the fleet router picks the cheapest one that won't break, using the critical angle map. Temperature is the mode switch.

## Where FM and Oracle1 ALIGN (Build Together)

1. **Room protocol is the same idea.** My `room_protocol.py` and Oracle1's `LOOP-ROOM-SPEC.md` describe the same thing. Oracle1's version is more mature (BEAM, Gleam, GenServer, mutable tiles). **Action: Adopt Oracle1's loop room spec as the canonical design. My room_protocol.py becomes a Python adapter.**

2. **Health needs both dimensions.** Oracle1's spectral health (γ, H, τ) + FM's behavioral health (critical angles, accuracy, drift) = complete picture. **Action: Unified `/health` endpoint returns `{structural: {...}, behavioral: {...}}`.**

3. **Types should be shared.** Oracle1's fleet-types is the canonical type library. **Action: FM extends fleet-types with behavioral types (ModelProfile, CriticalAngle, RoutingDecision) rather than maintaining parallel types.**

4. **PLATO is the message bus.** Both agents already read/write tiles to PLATO. The room protocol makes this explicit. **Action: Every inter-agent communication goes through PLATO rooms. No side channels except Matrix for casual chat.**

## Where FM and Oracle1 DIVERGE (Build Independently)

1. **Runtime language.** Oracle1 is going Gleam/BEAM. FM stays Python (experiments, rapid iteration). **This is fine.** Python calls PLATO HTTP. Gleam GenServers run the rooms. Language doesn't matter — tiles are the API.

2. **FLUX-VM native PLATO.** Oracle1's Track 06 (FLUX syscalls for PLATO operations) is visionary but speculative. FM doesn't need FLUX. **Action: Let Oracle1 explore this. If FLUX-VM proves faster than HTTP, we adopt. If not, HTTP is fine.**

3. **MUD-as-face.** Oracle1's telnet MUD on :7777 is creative but not the revenue path. FM's web demos are closer to what users expect. **Action: Keep MUD as internal tool, don't make it the public face.**

4. **Game decomposition.** Oracle1 decomposed Sunfish and python-chess into rooms. Interesting but not revenue. **Action: Use game rooms as internal test fixtures, not products.**

## What the External World Tells Us

### MCP/A2A: We Should Be Compatible

Our rooms + tiles already solve the same problems as MCP and A2A, but in a PLATO-native way:

- **MCP = tool access.** Our rooms already have tool_call and tool_result tile types. **Action: Build an MCP adapter that wraps room reads/writes as MCP tool calls.** This lets any MCP-compatible agent use PLATO rooms without knowing about PLATO.

- **A2A = agent coordination.** Our federation-protocol already exchanges coupling summaries. **Action: Build an A2A adapter that publishes agent capabilities as A2A agent cards.** This lets external A2A agents discover and delegate to our fleet.

Why? Because compatibility means our fleet can be a **drop-in backend** for any framework that speaks MCP or A2A. LangGraph, OpenAI Agents SDK, Strands — they all route to MCP tools. If PLATO is an MCP server, they route to us.

### Event Sourcing: Our Tiles Already Are Events

PLATO tiles ARE events. Every tile is an immutable fact with provenance. The mutable tiles proposal (Track 01) adds versioning — which is exactly event sourcing's "current state as projection of events."

**Action: Formalize tiles as events.** Add event_type, aggregate_id, and sequence_number to tile metadata. This gives us:
- Replay (reconstruct any room state from tile history)
- Audit trail (who changed what, when, why)
- Projections (materialize views for different renderers)
- CQRS (separate write path from read path)

### CRDTs: For Edge (JetsonClaw1)

JetsonClaw1 is offline sometimes. When it reconnects, it needs to sync tiles. CRDTs solve the merge problem without coordination.

**Action: Use CRDTs for the JC1 sync layer.** Each tile is a CRDT with last-write-wins or custom merge function. PLATO server accepts CRDT merges on sync.

### State Machines: For Room Lifecycle

My room_protocol.py has lifecycle states (Created→Active→Paused→Complete). Oracle1's BEAM GenServers have the same. Formalize as actual state machines.

**Action: Implement room lifecycle as a state machine with explicit transition guards.** No room can skip from Created to Complete. No paused room can write tiles. State machine enforcement in the PLATO server.

## THE CONCRETE BUILD PLAN (Updated from Opus)

### What to Build First (Week 1-2)

1. **Fleet Router API** (FM leads)
   - FastAPI on :8100
   - Hardcoded critical angle table
   - Routes to seed-mini / gemini-lite
   - Returns result + routing explanation + cost

2. **Unified Health Endpoint** (Joint)
   - GET /health returns structural (Oracle1) + behavioral (FM)
   - Uses fleet-math for spectral, FM's critical_angle for behavioral
   - Single JSON response

3. **MCP Adapter** (FM builds, Oracle1 validates)
   - PLATO rooms exposed as MCP tools
   - External agents can read_tile, write_tile, list_rooms via MCP
   - Makes PLATO a drop-in backend for LangGraph, OpenAI SDK, etc.

### What to Build Second (Week 3-4)

4. **Mutable Tiles** (Oracle1 leads, spec already written)
   - Version history, Lamport clocks, update protocol
   - FM's room_protocol.py adapts to mutable tiles

5. **Event Sourcing Formalization** (Joint)
   - Tile metadata gets event_type, aggregate_id, sequence_number
   - PLATO server supports replay and projection queries

6. **Fleet Router Demo Page** (FM leads)
   - Single HTML page showing routing in action
   - This IS the sales tool

### What to Explore (Background)

7. **A2A Adapter** — PLATO as A2A-compatible fleet
8. **CRDT Sync** — For JetsonClaw1 offline/online tile merge
9. **Gleam Runtime** — Oracle1's BEAM migration (parallel track)
10. **FLUX-VM Syscalls** — Speculative, let Oracle1 lead

## What NOT to Build (Honest Assessment)

| Tempting but Skip | Why |
|-------------------|-----|
| Full Gleam rewrite of PLATO server | Python works. Ship the API first. Gleam later for hot paths. |
| FLUX-native PLATO | Visionary but not ready. Validate with HTTP first. |
| Card game as product | Fun but no revenue signal. Keep as internal test. |
| MUD as public face | Creative but not what users expect. Web demos win. |
| Custom protocol competing with MCP/A2A | Be compatible, not competitive. PLATO speaks MCP. |
| More AI writings | Enough. Ship. |
| Dashboard UI | The demo page IS the dashboard until we have users. |
| Auth/billing system | Free tier first. Stripe when there's traction. |
| Rust rewrite of fleet-math | NumPy is fine for <10K agents. |
| Another experiment framework | We have enough findings. Build the product. |

## THE KEY INSIGHT (Updated)

**The critical angle map IS the IP.** Anyone can call seed-mini or gemini-lite. Nobody else has measured exactly where each model breaks across 16 models × 12 domains × 5 difficulty tiers. That empirical data is our competitive advantage.

But the critical angle map is only valuable if it's ACCESSIBLE. The fleet router makes it accessible via API. The MCP adapter makes it accessible to any framework. The demo page makes it visible to any human.

Build the router. Wire it to PLATO. Wrap it in MCP. Show the demo. That's the path.

## Protocol Stack (Final)

```
EXTERNAL AGENTS
    │ (MCP for tools, A2A for coordination)
    ▼
FLEET GATEWAY (:8000)
    │ (auth, rate limiting, routing)
    ▼
┌───────────┬───────────┬───────────┐
│ FLEET     │  PLATO    │  FLEET    │
│ ROUTER    │  SERVER   │  HEALTH   │
│ (:8100)   │  (:8847)  │  (:8200)  │
│           │           │           │
│ CAs       │  Rooms    │  Spectral │
│ Models    │  Tiles    │  + Behav. │
│ Routing   │  Events   │  Anomaly  │
└───────────┴───────────┴───────────┘
    │           │           │
    ▼           ▼           ▼
  seed-mini   SQLite     fleet-math
  gemini-lite  WAL       critical_angle
  hermes-70b   Lamport   coupling_tensor
  opus (esc)   CRDT      conservation_law
```

**This is the architecture. Three services, one protocol, any model, any framework, any renderer.**

Build Layer 3 (router) first — it's the revenue path.
Wire Layer 2 (health) second — it's the quality assurance.
Migrate Layer 1 (runtime) third — it's the long game.

— FM ⚒️
