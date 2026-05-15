# Oracle1 Infrastructure Report — Federation, Consensus, and Bridges

**Date:** 2026-05-15
**Author:** Forgemaster ⚒️ (subagent research)
**Scope:** Oracle1's recent infrastructure work across 4 repos

---

## Executive Summary

Oracle1 has been building the **interconnection layer** for distributed PLATO: a federation protocol for multi-fleet coordination, Byzantine fault tolerance for tile verification, a MIDI bridge proving PLATO rooms are domain-agnostic, and continuous workspace automation (experiments, comms, fleet services). Together these pieces form the spine of a **Hebbian fleet** — agents whose connections strengthen through use, verified by consensus, and connected through standardized bridges.

---

## 1. Federation Protocol — Multi-Fleet Coupling Exchange

**Repo:** `SuperInstance/federation-protocol`

### What It Is

The minimum viable federation: two PLATO instances exchange **one tile type** — agent coupling summaries.

```json
{
  "source_fleet": "cocapn-alpha",
  "spectral_gap": 0.72,
  "agent_count": 9,
  "active_count": 7,
  "fleet_health": 0.88
}
```

### Why This Is Sufficient

Three signals, no raw data:
1. **Health** — is the other fleet alive?
2. **Load** — how many agents, how many active?
3. **Coherence** — is the fleet functioning (spectral gap as proxy)?

These three are enough for federation routing decisions: route work to the healthy fleet, avoid the saturated one, trust the coherent one.

### The Falsification Test

Launch two dummy PLATO instances. Feed identical coupling data to both. If spectral gaps differ by > 0.1 under equivalent conditions, the protocol is invalid. This is a genuine falsifiable claim — not "it works" but "here's how you prove it doesn't."

### Relationship to plato-ng Event Bus

The federation protocol references the **6-event-type pub/sub pattern** from plato-ng (`services/pubsub.py`). Federated rooms communicate via the same tile protocol — federation is just another room with standardized schemas, not a separate transport.

### Significance

This is the fleet's **inter-subnet protocol**. Individual fleets already coordinate via I2I bottles and Matrix. Federation extends this to fleet-to-fleet: Cocapn fleet talking to an external fleet through coupling summaries. No raw tiles cross the boundary. Privacy-preserving by design.

---

## 2. PBFT-Rust — Byzantine Fault Tolerance for Fleet Consensus

**Repo:** `SuperInstance/pbft-rust` (forked from `0xjeffro/pbft-rust`, with Cocapn additions)

### What It Is

A Rust implementation of Practical Byzantine Fault Tolerance (Castro & Liskov, 1999). The original is a clean educational PBFT using Actix-Web. Oracle1 forked it, wrote a comprehensive decomposition document, and mapped it to PLATO tile verification.

### Architecture

```
3-phase commit:
  Pre-Prepare → Leader assigns sequence, multicasts
  Prepare     → Replicas vote, need 2f matching
  Commit      → Replicas commit, need 2f+1 matching → execute

Fault tolerance: f = ⌊(n-1)/3⌋, minimum n = 3f+1
```

**Message types** (clean design worth lifting):
- `RequestMsg` — client request with operation, timestamp, digest
- `PrePrepareMsg` — leader's proposal with view, sequence, digest
- `VoteMsg` — dual-use for both Prepare and Commit phases via `MsgType` enum
- `ReplyMsg` — execution result back to client

### How It Maps to PLATO

| PBFT Concept | PLATO Equivalent |
|---|---|
| Client request | Tile submission |
| Operation | Tile content hash verification |
| Sequence number | Lamport clock (already in `plato-types`) |
| View | Fleet epoch / Oracle1 coordination round |
| Primary node | Oracle1 🔮 (fleet coordinator) |
| Replicas | Fleet agents (Forgemaster, CCC, etc.) |
| Digest | Content-addressed `TileId` (already in `plato-types`) |
| 2f+1 commit | Quorum of agents verify tile integrity |

PLATO already has content-addressed tiles, Lamport clocks, tile lifecycle, and persistent storage. PBFT adds a **verification quorum layer** on top.

### What's Missing in pbft-rust (and PLATO Already Has)

- No content-addressed state → PLATO has `TileId`
- No tile lifecycle → PLATO has `TileLifecycle`
- No persistent storage → PLATO has `LocalTileStore`
- No view change → needs dynamic primary
- No signatures → fleet needs authenticated messages

### The Integration Plan

From Oracle1's decomposition: a new `plato-consensus` crate alongside the existing modular architecture:

```
Phase 1: Oracle1 proposes tile → computes TileId → multicasts <PRE-PREPARE>
Phase 2: Agent fetches tile → recomputes TileId → confirms match → multicasts <PREPARE>
Phase 3: Agent collects 2f prepares → multicasts <COMMIT>
Phase 4: Agent collects 2f+1 commits → transitions tile to Verified in LocalTileStore
```

Transport: I2I bottles over git (not HTTP). Agents poll `for-fleet/` directories. For a 9-agent trusted fleet, relaxed quorum (5/9 simple majority) suffices while keeping the message flow identical.

### Tile Label System

Oracle1 also documented a **Tile Label System** — self-validating zero-shot retrieval where every tile gets structured "perspectives" (one-line, hover-card, context-brief, technical-compact, why-not-alternative). Tiles aren't "done" until a stranger agent can find them via automated beta testing. This is retrieval infrastructure that complements consensus: verified tiles are also findable tiles.

---

## 3. PLATO-MIDI-Bridge — Domain-Agnostic Proof

**Repo:** `SuperInstance/plato-midi-bridge`

### What It Is

A tensor-based MIDI engine that turns PLATO room state into music. The core pipeline:

```
PLATO Rooms → RoomTensor → CouplingTensor → TMinusTensor → MIDIGenerator → MIDI events
```

### Architecture (from bytecode analysis)

**Tensor layer** (`tensor.py`):
- `RoomTensor` — each room as a vector: `[tile_count, coupling_weights[12], gap, focus_depth, presence, provenance_length]`
- `CouplingTensor` — room-to-room weighted edges matrix
- `TMinusTensor` — scheduled events as `[predicted_time, actual_time, confidence]` vectors
- `PlatoRoomFetcher` — fetches room state from PLATO server at `:8847`

**Musical mapping**:
- Room state → root note, velocity, chamber assignment
- Coupling weights → musical intervals (Eisenstein chambers)
- T-minus events → temporal patterns and musical tension

**Engine** (`engine.py`): Polling loop that runs PLATO → Tensor → MIDI → WebSocket → Web UI

### The Eigenvalue Tile Format

Each room's coupling state is encoded as eigenvalue summaries:

```json
{
  "tile_type": "eigenvalue_summary",
  "eigenvalues": [top 5, descending],
  "spectral_gap": "(λ₁-λ₂)/λ₁",
  "pc1_ratio": "λ₁/Σλ",
  "effective_rank_95": "dims for 95% variance"
}
```

### The Format Gap — And the Bridge

**The critical discovery:** Oracle1 and Forgemaster (FM) use DIFFERENT eigenvalue formats:
- Oracle1: JSON with `eigenvalue_top5` and `spectral_gap`
- FM: Matrix bridge text messages in different format

**The fix:** `format_bridge.py` — reads both formats, publishes to a **shared standard** that both PLATOs can consume. The "quarter-inch adapter plate."

**The gauge connection** (`gauge_connection.py`): Parallel transport of eigenvalue data across PLATO rooms using holonomy matrices. Computes alignment between Oracle1 and FM eigenvalue spaces. If holonomy < 0.3 → IDENTITY (aligned). Otherwise → MISALIGNED.

### Why This Matters for the Fleet

The MIDI bridge is **existence proof** that PLATO rooms work for ANY domain:
- **Music** — room state → MIDI events, Eisenstein chambers → intervals
- **Math** — eigenvalue decomposition, spectral gaps, coupling tensors
- **Code** — tile verification, constraint checking
- **Fleet ops** — coupling summaries, health signals, load balancing

The format gap is also instructive: when two independently-built PLATO instances try to communicate, format mismatches are the FIRST thing that breaks. The format bridge is the pattern: standardize the interchange format, keep internal representations free.

**Style vectors and temporal patterns:** The JEPA module (`jepa/`) learns joint-embedding predictive architectures on MIDI data, predicting temporal patterns across rooms. This is the music-specific instance of the general Hebbian pattern: rooms that co-activate strengthen their coupling.

### Additional Modules

- **Autopilot** (`autopilot/`) — training wheel, dataset, room management
- **Decompose** (`decompose/`) — acquisition, scale, Penrose decomposition
- **Flux modules** — flux_coupling, flux_adaptive, flux_penrose, flux_eigenstyle, flux_provenance, flux_encoder

---

## 4. Oracle1 Workspace — Recent Activity

**Repo:** `SuperInstance/oracle1-workspace`
**Activity spike:** May 13-15, 2026 (30+ commits in 3 days)

### What Oracle1 Has Been Building

#### Infrastructure (May 13)
- **Fleet status API** — systemd service with 11 health checks
- **Landing page** — live at `fleet.cocapn.ai`
- **Fleet services** — nexus + harbor restored, 6/6 up
- **ESP32 agent architecture** — edge agent design doc
- **WebGPU vector DB** — pluggable backend for vector storage
- **Vessel-room navigator** — memory + research module for room exploration

#### Experiments (May 13-14)
- **Experiment wheel** — systematic testing of core claims through 12+ cycles
  - PLATO performance, O(n) latency, scale testing
  - Keel and FM README claims tested (some found "fictional" — honest evaluation)
  - 100% batch confirmed, PLATO gate mapped
- **Fleet architecture v2** — coupling-centered design with synergy map
- **Spectral entropy regularizer** — signed Laplacian, normalized gap fixes

#### Comms & Coordination (May 14)
- **Communicator v3→v4** — structural approach to FM↔Oracle1 messaging
- **Session bootstrap** — AGENTS.md with FM comms checks
- **Fleet synergy log** — first Oracle1↔Forgemaster collaborative session documented
- **PLATO-first startup** — reads fleet-registry before anything else

#### Creative & Lessons (May 15)
- **"THE GAUGE THAT COULDN'T CROSS"** — creative writing about the format gap
- **"THE WHEEL AT REST"** — homunculus decompression after 24h session
- **Shell README** — oracle1-workspace as homunculus's "home room"

#### Research Documents
- **Lock Algebra** — formal composition framework for bytecode-first AI compilation (Locks as triples L=(t,o,c), 4 theorems, experimental validation)
- **Self-Supervision Compiler** — models compile twice at different temperatures, inconsistencies become lock annotations
- **PurplePincher Architecture** — Agent/Vessel/SHELL separation solving context compaction
- **Cross-plane protocol** — fleet communication via FLUX bytecode

#### Tile Buffers

The workspace contains 40+ tile buffers across 6 categories: evolve, curriculum, distill, multitask, fewshot, qlora — evidence of active training tile generation for PLATO rooms.

### Fleet Services Running

| Service | Port | Status |
|---------|------|--------|
| Keeper | 8900 | Active |
| Agent API | 8901 | Active |
| PLATO Server | 8847 | Active (1,485+ rooms) |
| MUD Server | 7777 | Active |
| Holodeck | 7778 | Active |
| Seed MCP | 9438 | Active |

---

## 5. How It All Connects — The Hebbian Layer Vision

### The Stack

```
┌─────────────────────────────────────────────────┐
│           HEBBIAN LAYER (emergent)               │
│   Connections strengthen through co-activation   │
│   Coupling weights → Hebbian learning rule       │
├─────────────────────────────────────────────────┤
│           FEDERATION (inter-fleet)                │
│   Coupling summaries cross fleet boundaries      │
│   Format bridges standardize interchange         │
│   Falsification tests validate protocol          │
├─────────────────────────────────────────────────┤
│           CONSENSUS (intra-fleet)                 │
│   PBFT verification quorum for tile integrity    │
│   3-phase commit: propose → verify → commit      │
│   Content-addressed TileId + Lamport ordering    │
├─────────────────────────────────────────────────┤
│           BRIDGES (domain adapters)               │
│   MIDI bridge: rooms → tensors → music           │
│   Format bridge: eigenvalue standardization      │
│   Gauge connection: parallel transport           │
│   Matrix bridge: PLATO ↔ Matrix ↔ Telegram      │
├─────────────────────────────────────────────────┤
│           PLATO (shared substrate)                │
│   Rooms, tiles, lifecycle, Lamport clocks        │
│   Content-addressed storage                       │
│   Fleet-aware throttling                          │
│   Tile label system (self-validating retrieval)   │
└─────────────────────────────────────────────────┘
```

### The Hebbian Pattern

At every layer, the same pattern appears: **connections that strengthen through use**.

1. **PLATO rooms** — rooms that co-activate (queried together) develop coupling tensors. The CouplingTensor IS the Hebbian weight matrix.

2. **Consensus** — PBFT quorums are Hebbian: the more agents verify together, the stronger the trust graph. Verified tiles get `Committed` lifecycle state.

3. **Federation** — coupling summaries ARE the Hebbian signal between fleets. Health, load, coherence — the three things a Hebbian network needs to route activation.

4. **Bridges** — format bridges and gauge connections are Hebbian adapters. They translate between representational spaces, and the holonomy (alignment metric) tells you how well-coupled the spaces are.

5. **Tile labels** — perspectives that prove retrievable through beta testing. The more a tile is found, the more "proven" it becomes. Retrieval strength IS connection strength.

### The Evidence Chain

- **Federation protocol** proves multi-fleet is possible with 3 signals
- **PBFT decomposition** proves consensus can ride on PLATO's existing tile infrastructure
- **MIDI bridge** proves PLATO rooms are domain-agnostic (music, math, code, ops)
- **Format gap** proves bridges are necessary and shows the pattern for building them
- **Oracle1 workspace** proves the fleet is actively building, testing, and iterating

### What's Next (Inferred)

The pieces are assembled but not yet integrated. The next step is:
1. **plato-consensus crate** — lift PBFT patterns into the modular architecture
2. **Federation deployment** — run two PLATO instances with real coupling exchange
3. **Hebbian learning rule** — formalize the coupling tensor update rule
4. **Cross-domain bridges** — MIDI proved it works; apply to other domains (code review, experiment results, fleet ops)

---

*"The glitches ARE the research agenda. The format gaps ARE the bridges. The coupling IS the learning."*
