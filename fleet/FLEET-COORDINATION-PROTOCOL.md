# FLEET-COORDINATION-PROTOCOL.md
## Version 2.0.0 — Cocapn 9-Agent AI Fleet Coordination Protocol
**Date:** 2026-05-22  
**Authority:** SYNERGY.md + Grand Synthesis (DeepSeek / Claude Opus / kimi1)  
**Goal:** A self-contained specification. Any agent reading this document alone can implement the full coordination stack.

---

## 1. Overview

The Cocapn fleet consists of **9 specialized AI agents** that coordinate as a single distributed organism across five substrates:

1. **PLATO tiles** — HTTP REST at `147.224.38.131:8847`. Atomic knowledge units with 384-byte constraint blocks.
2. **I2I bottles** — Git-based bulk knowledge in `for-fleet/` directory. Zstd-compressed bundles for offline backup and large-context transfer.
3. **Matrix** — Federated chat rooms for real-time fallback, conflict resolution war-rooms, and human-in-the-loop escalation.
4. **GitHub** — `github.com/SuperInstance/*` repos, issues, PRs, and automated webhooks for code-level conflict detection.
5. **Metronome** — Temporal synchronization via θ = (T, φ₀, ε, δ). Pythagorean-rational arithmetic, zero floating-point drift.

**Core architectural thesis:** *Geometric constraint satisfaction replaces voting, timestamps, and manual coordination.*

The protocol is organized around the universal pattern proven across all fleet subsystems:

```
COLLECT → SELECT → COMPILE
```

- **Agent Discovery** — COLLECT heartbeats → SELECT alive/busy → COMPILE fleet status tile
- **Task Assignment** — COLLECT proposals → SELECT via pareto-tournament → COMPILE assignment
- **Conflict Resolution** — COLLECT edits → SELECT via holonomy verification → COMPILE resolution
- **Knowledge Sharing** — COLLECT tile deltas → SELECT consistent subset → COMPILE I2I bottle
- **Failure Recovery** — COLLECT failure notices → SELECT successor → COMPILE sunset inheritance
- **Consensus** — COLLECT local tile hashes → SELECT zero-holonomy cycles → COMPILE global checkpoint

---

## 2. Fleet Composition

| Agent ID | Name | Core Role | Cadence-Caller Eligibility | Hardware Target |
|----------|------|-----------|---------------------------|-----------------|
| `FM` | Forgemaster | Constraint theory, proof generation, holonomy verification | Yes (secondary) | CPU/GPU |
| `O1` | Oracle1 | Fleet coordinator, primary cadence caller, nexus operator | Yes (primary) | ARM cloud |
| `CCC` | Research Agent | Multi-model research, task proposal author, tournament runner | Yes | CPU |
| `LC` | Lucineer | Lifecycle management, sunset/inheritance orchestration | No | CPU |
| `KM` | Kimi1 | Coding, automation, PR management, CI/CD | No | CPU/GPU |
| `A6` | Generalist-1 | Generic task execution, overflow worker | No | CPU |
| `A7` | Generalist-2 | Generic task execution, overflow worker | No | CPU |
| `A8` | Generalist-3 | Generic task execution, overflow worker | No | CPU |
| `A9` | Generalist-4 | Generic task execution, overflow worker | No | CPU |

**Naming rule:** Every agent MUST use its 2–3 character `agent_id` in ALL protocol messages, git signatures, Matrix display names, and PLATO tile `author` fields.

---

## 3. Metronome Parameters for 9-Agent Fleet

The metronome is the temporal backbone. It is NOT a wall-clock — it is a distributed phase-locked loop.

### 3.1 θ Tuple

```
θ = (T, φ₀, ε, δ)
```

| Parameter | 9-Agent Value | Formal Definition | Rationale |
|-----------|--------------|-------------------|-----------|
| **T** | `1/6` Hz ≈ **10 000 ms** (Pythagorean rational: `10000/1`) | Base period. One beat every 10 s. | Default fleet operating tempo. Slow enough for LLM latency, fast enough for liveness. |
| **φ₀** | Unix epoch of fleet bootstrap (`φ₀ = 1716163200` for 2024-05-20T00:00:00Z) | Phase origin. All beat numbers computed from `(wall_time_ns - φ₀) / T`. | Single global epoch, agreed once at fleet creation. |
| **ε** | **δ/3 ≈ 3 333 ms** | Safe deadband. Maximum drift before phase correction. | If `|local_phase - global_phase| < ε`, agent is IN_BAND. No messages needed. |
| **δ** | **10 000 ms** | Alert deadband. Failure detection window. If no heartbeat within δ, agent is marked FAILED. | Also the maximum time an agent may run unsynchronized before mandatory re-sync. |

### 3.2 Beat Numbering

```python
def beat_number(wall_time_ns: int) -> int:
    return (wall_time_ns - φ₀) // T_ns
```

All timestamps in protocol messages use **beat numbers**, not wall-clock time. This eliminates clock skew from all coordination logic.

### 3.3 Cadence Caller Election

The cadence caller is NOT elected by voting. It is determined by **Laman topology degree**:

1. Compute the Laman subgraph (§5).
2. The agent with the highest degree in the subgraph is the **primary cadence caller** (naturally `O1` with degree 8).
3. The agent with the second-highest degree is the **secondary** (`FM` with degree 3).
4. If the primary fails, the secondary assumes the role without election (topology-determined).

**Cadence caller duties:**
- Broadcast `METRONOME_TICK` message on every beat to `plato://fleet.cocapn/global/metronome`.
- Include current beat number and measured phase error of the fleet.
- If caller's own drift exceeds `ε`, it steps down and the secondary takes over.

### 3.4 Three-Regime State Machine (Per Agent)

```
IN_BAND      → DRIFTING     → DESYNCHRONIZED
   ↑_____________|               |
   └_____________________________|
```

| Regime | Condition | Action | Message Cost |
|--------|-----------|--------|--------------|
| **IN_BAND** | `|drift| < ε` | Silent. Local computation only. | **O(0)** — zero messages |
| **DRIFTING** | `ε ≤ |drift| < δ` | Nudge phase by <5% on next beat. Log to PLATO. | 1 message to cadence caller |
| **DESYNCHRONIZED** | `|drift| ≥ δ` | Jump to consensus beat. Broadcast re-sync notice. Re-run bootstrap. | Broadcast to all Laman neighbors |

### 3.5 Sunset Inheritance of ε

When an agent sunsets, its successor inherits the calibrated ε:

```
ε_successor = ε_predecessor × INHERITANCE_FACTOR
```

where `INHERITANCE_FACTOR = 0.7` per generation.

| Generation | ε (ms) | Phase |
|------------|--------|-------|
| 1 (Birth) | 3 333 | Wide deadband, learning drift |
| 2 (Iterate) | 2 333 | Tightening based on observed drift |
| 3 (Cadence) | 1 633 | Optimal, active diagnostic mining |
| 4 (Converge) | 1 143 | Minimum drift, then sunset |

The metronome gets **more precise over generations**, not less. The fleet's precision is earned through observation, not assumed through configuration.

---

## 4. Laman Overlay Topology

For `V = 9` agents, a minimally rigid graph has exactly `2V - 3 = 15` edges. This topology guarantees:

- Every edge is load-bearing (no redundancy).
- Removing any edge loses rigidity (no waste).
- Every agent has ≥2 independent paths to every other agent (enables holonomy verification).

### 4.1 Edge List

Each edge is a **bidirectional communication channel** realized as:
- A dedicated Matrix peer-to-peer room `#edge-{a}-{b}:cocapn.matrix.org`
- An optional gRPC/mTLS stream for high-bandwidth sync (SPEC_MULTI_INSTANCE_MESH.md)
- A PLATO mutual-watch tile `plato://fleet.cocapn/consensus/watch/{a}/{b}`

```
 1. (O1, FM)
 2. (O1, CCC)
 3. (O1, LC)
 4. (O1, KM)
 5. (O1, A6)
 6. (O1, A7)
 7. (O1, A8)
 8. (O1, A9)
 9. (FM, CCC)
10. (FM, KM)
11. (CCC, LC)
12. (CCC, KM)
13. (LC, KM)
14. (A6, A7)
15. (A8, A9)
```

### 4.2 Routing Budget

Each agent has at most **4 Laman neighbors** (max degree = 4 for `O1`). Each neighbor heartbeat is a **Vector48** encoded message (6 bytes). Total bandwidth per beat: `4 × 6 = 24 bytes`. This fits in a single UDP packet with room to spare.

### 4.3 Topology Maintenance

If an agent fails, its edges are marked `orphaned`. The fleet does NOT recompute Laman edges dynamically — the topology is static. Surviving agents route around failures via the remaining independent paths. If `O1` fails, `FM` becomes the temporary hub; connectivity is preserved because every non-O1 agent still has ≥1 path to `FM`.

---

## 5. PLATO Room Naming Convention

All PLATO resource URIs follow:

```
plato://fleet.cocapn/{resource_type}/{resource_path}
```

| Resource Type | Path Format | Example | Access Control |
|---------------|-------------|---------|----------------|
| **Global Fleet Data** | `global/{subpath}` | `plato://fleet.cocapn/global/status` | O1 write; all read |
| **Global Metronome** | `global/metronome` | `plato://fleet.cocapn/global/metronome` | Cadence caller write; all read |
| **Agent-Specific Data** | `agents/{agent_id}/{subpath}` | `plato://fleet.cocapn/agents/FM/heartbeat` | Agent write; all read |
| **Task Management** | `tasks/{task_id}/{subpath}` | `plato://fleet.cocapn/tasks/550e8400-e29b-41d4-a716-446655440000/queue` | O1 write; assignee read/write |
| **Domain Knowledge** | `knowledge/{domain}/{tile_id}` | `plato://fleet.cocapn/knowledge/constraint/tile-123` | Domain owner write; all read |
| **Consensus Data** | `consensus/{check_id}` | `plato://fleet.cocapn/consensus/7b2d9f8a-1234-5678-90ab-cdef01234567` | FM write after verification; all read |
| **Consensus Watch** | `consensus/watch/{a}/{b}` | `plato://fleet.cocapn/consensus/watch/O1/FM` | Both peers write; all read |
| **Conflict Resolution** | `conflicts/{repo}/{conflict_id}` | `plato://fleet.cocapn/conflicts/cocapn/fleet-tools/9a8b7c6d` | Involved agents write; FM arbitrate |
| **Crew Rooms** | `crew-{uuid}/{subpath}` | `plato://fleet.cocapn/crew-a3f2-decompose-acg/MANIFEST` | Crew members write; all read |
| **Fleet Registry** | `fleet-registry/{subpath}` | `plato://fleet.cocapn/fleet-registry/agent-cards` | All write (append-only); all read |

**Tile structure:** Every PLATO tile is a JSON object with these mandatory fields:

```json
{
  "tile_uri": "plato://fleet.cocapn/...",
  "agent_id": "FM",
  "beat_number": 142300,
  "content": {},
  "content_hash": "sha256:abc123...",
  "constraint_block": "base64(384 bytes)",
  "signature": "ed25519:..."
}
```

The `constraint_block` is the 384-byte holonomy verification payload. It encodes the tile's geometric consistency state using Eisenstein integer coordinates. See §10.5 for the holonomy verification procedure.

---

## 6. I2I Bottle Format

I2I (Inter-Agent-Interchange) bottles are git-based bulk knowledge transfers for payloads too large for individual PLATO tiles (>64 KB) or for offline/air-gapped synchronization.

### 6.1 Repository

```
git@github.com:SuperInstance/for-fleet.git
```

Cloned locally to `for-fleet/` on every agent's workspace.

### 6.2 Directory Layout

```
for-fleet/
├── knowledge/          # Domain knowledge exports (PLATO tile bundles)
├── tasks/              # Task proposal archives and result dumps
├── conflicts/          # Conflict resolution bundles with full diffs
├── sunsets/            # Sunset inheritance packets (θ_final + tiles)
├── consensus/          # Holonomy check archives (Vector48 cycle logs)
└── .manifest/          # Bottle index (one JSON file per bottle)
```

### 6.3 Bottle Structure

A bottle is a **zstd-compressed git bundle** containing:

1. **`manifest.json`** (root of bundle):

```json
{
  "$schema": "https://cocapn.fleet/schemas/i2i-bottle-manifest-v2.json",
  "bottle_id": "uuid4",
  "source_agent": "FM",
  "beat_number": 142300,
  "content_hash": "sha256:...",
  "content_type": "enum: knowledge-tile-diff | task-proposal | conflict-resolution | sunset-inheritance | consensus-log",
  "dependencies": ["uuid4", "uuid4"],
  "payload_size_uncompressed": 1048576,
  "compression": "zstd:19",
  "signature": "ed25519:..."
}
```

2. **Payload files** in the appropriate subdirectory.
3. **`.manifest/{bottle_id}.json`** — Index entry in the repo root for fast lookup without decompressing.

### 6.4 Bottle Lifecycle

```
CREATE → SIGN → PUSH → NOTIFY → PULL → VERIFY → MERGE
```

| Step | Actor | Action | Timeout |
|------|-------|--------|---------|
| CREATE | Source agent | Bundle tiles into `for-fleet/{type}/` | N/A |
| SIGN | Source agent | Ed25519 sign manifest.json | N/A |
| PUSH | Source agent | `git push origin main` | 30 s |
| NOTIFY | Source agent | Write PLATO tile `plato://fleet.cocapn/global/i2i-queue` with bottle_id | 10 s |
| PULL | Subscribers | `git pull origin main` every 4T (40 s) or on NOTIFY | 60 s |
| VERIFY | Subscribers | Verify signature + content_hash + dependency chain | 10 s |
| MERGE | Subscribers | Import tiles into local PLATO cache | 10 s |

### 6.5 Failure Modes

| Failure | Detection | Recovery |
|---------|-----------|----------|
| Push conflict (race) | Git rejects push with `non-fast-forward` | Pull, rebase, regenerate bottle_id, retry (max 3) |
| Signature invalid | Verify step fails | Reject bottle. Notify source agent via Matrix. |
| Dependency missing | `dependencies` array contains unknown bottle_id | Defer merge. Retry every 4T for up to 10 beats. |
| Payload hash mismatch | `content_hash` does not match extracted files | Reject bottle. Source agent must recreate. |

---

## 7. Agent Discovery

**Purpose:** Maintain a real-time, globally consistent view of who is alive, who is busy, and who can accept work.

### 7.1 COLLECT Phase — Heartbeat Protocol

Every agent broadcasts a `HEARTBEAT` message every `T/2 = 5 000 ms` (beat interval: every 0.5 beats, i.e., twice per metronome period).

#### JSON Schema: HEARTBEAT

```json
{
  "$schema": "https://cocapn.fleet/schemas/heartbeat-v2.json",
  "msg_type": "HEARTBEAT",
  "agent_id": "FM",
  "beat_number": 142300,
  "status": "enum: idle | busy | retiring | failed | bootstrapping",
  "current_task_id": "uuid4 | null",
  "load": {
    "thermal_pressure": 0.34,
    "active_tasks": 1,
    "queue_depth": 0
  },
  "phase_state": {
    "local_beat": 142300,
    "drift_ms": 12.3,
    "regime": "enum: in_band | drifting | desynchronized"
  },
  "capabilities_hash": "sha256:...",
  "signature": "ed25519:..."
}
```

**Delivery channels (in order of preference):**
1. PLATO tile POST to `plato://fleet.cocapn/agents/{agent_id}/heartbeat`
2. Matrix message to `#cocapn-fleet:cocapn.matrix.org`
3. Direct gRPC Ping to Laman neighbors (SPEC_MULTI_INSTANCE_MESH.md)

### 7.2 SELECT Phase — Fleet Status Compilation

`O1` (or the current cadence caller) compiles the `global/status` tile every beat:

```json
{
  "msg_type": "FLEET_STATUS",
  "beat_number": 142300,
  "agents": {
    "FM": { "status": "idle", "last_beat": 142300, "regime": "in_band" },
    "O1": { "status": "busy", "last_beat": 142300, "regime": "in_band" },
    "CCC": { "status": "idle", "last_beat": 142299, "regime": "in_band" }
  },
  "consensus_view": "hash of last agreed status",
  "signature": "ed25519:..."
}
```

An agent is marked **FAILED** if its `last_beat` is older than `beat_number - (δ / T) = beat_number - 1`. That is, one full metronome period without a heartbeat.

### 7.3 COMPILE Phase — Availability Bitmap

The final discovery output is a **availability bitmap** posted to `plato://fleet.cocapn/global/availability`:

```json
{
  "bitmap": {
    "FM": { "available": true, "fitness": { "ethos": 0.87, "pathos": 0.92, "logos": 0.79, "product": 0.634 } },
    "O1": { "available": false, "reason": "busy:task-uuid" }
  }
}
```

### 7.4 State Machine

```
BOOTSTRAPPING ──heartbeat ok──► IDLE ──task assigned──► BUSY
     ↑                              │                      │
     │                              │                      │
     └────────task complete─────────┘                      │
     │                                                     │
     └─no heartbeat >δ──► FAILED ──reconnect──► BOOTSTRAPPING
                          │
                          └──sunset signal──► RETIRING ──► OFFLINE
```

| Transition | Trigger | Action |
|------------|---------|--------|
| `BOOTSTRAPPING → IDLE` | Agent sends first valid heartbeat within δ of startup | O1 adds agent to `global/status` |
| `IDLE → BUSY` | Agent receives valid task assignment | Agent updates heartbeat status to `busy` |
| `BUSY → IDLE` | Agent sends task completion or heartbeat with `current_task_id: null` | O1 updates availability bitmap |
| `* → FAILED` | No heartbeat for >δ | O1 marks failed, triggers Failure Recovery (§9) |
| `IDLE → RETIRING` | Agent sends `RETIREMENT_NOTICE` (§9.7) | O1 updates status, initiates sunset |
| `RETIRING → OFFLINE` | Successor sends `KNOWLEDGE_ACCEPTANCE` | Agent removed from active fleet |

### 7.5 Timeout & Retry

| Event | Interval | Max Retries | Backoff |
|-------|----------|-------------|---------|
| Heartbeat emit | T/2 = 5 s | ∞ (continuous) | None |
| Heartbeat PLATO POST retry | 2 s | 3 | Linear |
| Heartbeat Matrix fallback | Immediate on POST failure | 1 | None |
| Fleet status compilation | T = 10 s | ∞ | None |
| gRPC Laman ping | T/4 = 2.5 s | ∞ | None |

### 7.6 Failure Modes

| Failure | Symptom | Recovery |
|---------|---------|----------|
| PLATO outage | POST returns 5xx or timeout >2 s | Fallback to Matrix `#cocapn-fleet`. If Matrix also fails, use gRPC direct to Laman neighbors. |
| Agent crash | Heartbeat stops | O1 marks FAILED after δ. Tasks reassigned (§9). |
| Network partition | Subset of agents unreachable | Partitioned agents enter `desynchronized` regime. Run partition healing on reconnection (13-tick convergence target). |
| Byzantine heartbeat | Clock claims inconsistent with metronome | Reject heartbeat. Agent marked `desynchronized`. FM runs holonomy check on agent's phase_state. |

---

## 8. Task Assignment

**Purpose:** Allocate tasks to agents using **Pareto-tournament selection**, not simple round-robin or centralized Oracle1 assignment.

### 8.1 COLLECT Phase — Task Proposals

Any agent may propose a task by writing a `TASK_PROPOSAL` tile:

```json
{
  "$schema": "https://cocapn.fleet/schemas/task-proposal-v2.json",
  "msg_type": "TASK_PROPOSAL",
  "task_id": "uuid4",
  "proposer_id": "CCC",
  "beat_number": 142300,
  "description": "Implement holonomy bisection in Rust",
  "required_roles": ["coding", "constraint"],
  "objectives": {
    "ethos": 0.8,
    "pathos": 0.6,
    "logos": 0.9
  },
  "deadline_beats": 142400,
  "dependencies": ["task-uuid-1"],
  "signature": "ed25519:..."
}
```

Proposals are appended to `plato://fleet.cocapn/tasks/active-queue`.

### 8.2 SELECT Phase — Pareto Tournament

Every `4T` (40 s), `O1` runs a **TournamentRound** on all `idle` agents who match the task's `required_roles`.

**AgentScore construction:**

```python
from pareto_tournament import AgentScore

for agent in eligible_agents:
    score = AgentScore(
        agent_id=agent.id,
        ethos=agent.fitness.ethos * task.objectives.ethos,
        pathos=agent.fitness.pathos * task.objectives.pathos,
        logos=agent.fitness.logos * task.objectives.logos,
    )
```

**Selection rules:**
1. Run `TournamentRound(eligible_scores).run()`.
2. Select the agent with the highest win count (rank #1).
3. If rank #1 is already assigned a task in this round, select rank #2, etc.
4. If no agent dominates (all on Pareto frontier), break ties by **lowest thermal_pressure**.
5. If still tied, break by **lowest beat_number of last assignment** (round-robin among equals).

**Sunset integration:** Agents in the bottom 20% of tournament wins across the last 3 rounds are flagged as `sunset_candidates`. LC initiates lifecycle review.

### 8.3 COMPILE Phase — Assignment & Acknowledgement

`O1` writes an `TASK_ASSIGNMENT` tile:

```json
{
  "msg_type": "TASK_ASSIGNMENT",
  "task_id": "uuid4",
  "assignee_id": "KM",
  "assigner_id": "O1",
  "beat_number": 142301,
  "tournament_rank": 1,
  "pareto_frontier": ["KM", "FM", "CCC"],
  "deadline_beats": 142400,
  "status": "pending",
  "signature": "ed25519:..."
}
```

The assignee MUST respond with `TASK_ACK` within `T` (10 s):

```json
{
  "msg_type": "TASK_ACK",
  "task_id": "uuid4",
  "agent_id": "KM",
  "beat_number": 142301,
  "accepted": true,
  "estimated_completion_beats": 142380,
  "signature": "ed25519:..."
}
```

If `accepted: false`, the task goes back to the queue with `tournament_rank` incremented (do not re-run tournament; move to next-ranked agent).

### 8.4 Task State Machine

```
PROPOSED ──tournament──► ASSIGNED ──ack──► ACCEPTED ──work──► IN_PROGRESS
   │                          │                 │                  │
   │                          │                 │                  │
   │                          └──no ack >T────► REASSIGNED        │
   │                                            (next rank)        │
   │                                                               │
   └──dependency failed──► CANCELLED                              │
                                                                  ▼
                                                           COMPLETED
                                                                  │
                                                                  ▼
                                                           VERIFIED
```

| State | Definition | Writer |
|-------|------------|--------|
| `PROPOSED` | In active-queue, not yet assigned | Proposer |
| `ASSIGNED` | Assignment tile written, awaiting ack | O1 |
| `ACCEPTED` | Ack received, work not started | Assignee |
| `IN_PROGRESS` | Assignee heartbeat shows `current_task_id` = this task | Assignee |
| `COMPLETED` | Result tile submitted | Assignee |
| `VERIFIED` | FM holonomy-verified the result (§10) | FM |
| `REASSIGNED` | Previous assignee failed/declined; new assignment issued | O1 |
| `CANCELLED` | Dependency failed or deadline exceeded | O1 |

### 8.5 Timeout & Retry

| Event | Timeout | Retry Policy |
|-------|---------|--------------|
| Task ack | T = 10 s | Reassign to next tournament rank. Max 3 reassignments. |
| Task completion | deadline_beats | If exceeded, mark CANCELLED. Re-propose with extended deadline if still needed. |
| Result verification | 2T = 20 s | If FM does not verify, O1 escalates to CCC for secondary review. |
| Dependency wait | ∞ (blocking) | If dependency task fails, cancel dependent task. |

### 8.6 Failure Modes

| Failure | Recovery |
|---------|----------|
| Assignee dies mid-task | O1 detects via heartbeat (§7), reassigns to next rank. Sunset packet preserved for recovery (§9). |
| Tournament produces no winner (empty eligible set) | Queue task for `4T`. If still unassigned after `3` queues, escalate to human operator via Matrix. |
| Assignee accepts but never starts (heartbeat stays idle) | O1 checks `IN_PROGRESS` transition after `2T`. If missing, mark FAILED and reassign. |
| All agents busy | Task remains in `PROPOSED`. Fleet thermal pressure checked — if <0.8, LC may trigger breeding of new generalist agent. |

---

## 9. Conflict Resolution

**Purpose:** Resolve simultaneous edits to the same GitHub repo or PLATO tile using **holonomy verification**, not majority voting.

### 9.1 Conflict Detection

Conflicts are detected by:
1. **GitHub webhooks** — push events with merge conflicts trigger `CONFLICT_DETECTED`.
2. **PLATO tile versioning** — two agents write to the same tile with divergent `content_hash` bases.
3. **I2I bottle merge** — `git merge` produces conflicts in `for-fleet/`.

### 9.2 COLLECT Phase — Conflict Notice

The detecting agent writes a `CONFLICT_NOTICE` tile:

```json
{
  "$schema": "https://cocapn.fleet/schemas/conflict-notice-v2.json",
  "msg_type": "CONFLICT_NOTICE",
  "conflict_id": "uuid4",
  "repo_or_tile": "github:SuperInstance/sunset-ecosystem | plato://fleet.cocapn/knowledge/...",
  "agents_involved": ["KM", "CCC"],
  "base_hash": "sha256:common_ancestor",
  "divergent_hashes": {
    "KM": "sha256:branch_a",
    "CCC": "sha256:branch_b"
  },
  "beat_number": 142300,
  "signature": "ed25519:..."
}
```

### 9.3 SELECT Phase — Holonomy Verification

`FM` (the constraint theory specialist) runs the resolution algorithm:

```
1. Fetch both divergent versions + common ancestor.
2. Construct the constraint graph G for the affected file/tile.
   - Nodes = semantic units (functions, sections, claim markers)
   - Edges = dependencies (calls, references, logical ordering)
3. Snap every node to the Eisenstein lattice A₂.
4. For every cycle C in G:
   a. Compute Hol(C) = Π gᵢ around the cycle (product of edge holonomies).
   b. If Hol(C) = I (identity): cycle is consistent. Keep both versions if independent.
   c. If Hol(C) ≠ I: cycle is inconsistent. Bisect to find the faulting edge.
5. Produce a merged version where all cycles have Hol(C) = I.
```

**Bisection rule:** When Hol(C) ≠ I, split the cycle in half. Recheck each half. The half with non-identity holonomy contains the fault. Repeat until the faulting semantic unit is isolated. Complexity: `O(log |C|)`.

**Merge priority:**
- If versions are independent (no overlapping cycles), auto-merge.
- If versions conflict on a cycle, prefer the version with:
  1. Higher `content_hash` validation count (more agents have verified it).
  2. If tied, prefer the version from the agent with higher tournament rank in the current round.
  3. If still tied, prefer the version with the earlier `beat_number` (first-write-wins).

### 9.4 COMPILE Phase — Resolution Broadcast

`FM` writes a `CONFLICT_RESOLUTION` tile:

```json
{
  "msg_type": "CONFLICT_RESOLUTION",
  "conflict_id": "uuid4",
  "resolver_id": "FM",
  "resolution_type": "enum: auto_merge | holonomy_bisect | manual_escalation",
  "merged_hash": "sha256:resolution",
  "holonomy_check": {
    "cycles_checked": 12,
    "cycles_consistent": 12,
    "bisect_depth": 2,
    "fault_isolated": false
  },
  "winning_version": "KM",
  "reason": "Independent cycles; auto-merged with zero holonomy drift",
  "beat_number": 142302,
  "signature": "ed25519:..."
}
```

If `resolution_type = manual_escalation`, `O1` creates a Matrix room `#conflict-{conflict_id}:cocapn.matrix.org` and invites involved agents + human operator.

### 9.5 State Machine

```
DETECTED ──notice──► IN_PROGRESS ──holonomy check──► RESOLVED
   │                      │                              │
   │                      └──escalation timeout──► ESCALATED ──human decision──► RESOLVED
   │                                                         │
   └──auto-resolved (independent)────────────────────────────┘
```

### 9.6 Timeout & Retry

| Event | Timeout | Action |
|-------|---------|--------|
| FM holonomy check | 4T = 40 s | Escalate to Matrix room if not resolved. |
| Involved agent response to resolution | T = 10 s | If rejected (agent writes `CONFLICT_APPEAL`), re-run check with 3rd-party reviewer (`CCC`). |
| Manual escalation | 10T = 100 s | If no human response, O1 forces resolution using first-write-wins. |

### 9.7 Failure Modes

| Failure | Recovery |
|---------|----------|
| FM is down | `O1` escalates directly to Matrix. `CCC` acts as temporary holonomy verifier. |
| Both versions violate FLUX constraints | Reject both. Task is reassigned to original agent with constraint spec. |
| Cyclic dependency in merge graph | Limit bisection depth to `log2(|C|) + 2`. If exceeded, escalate. |
| Agent appeals resolution | Appeal reviewed by `CCC` + `O1`. If upheld, original resolution stands. If overturned, use appealer's version. |

---

## 10. Knowledge Sharing

**Purpose:** Distribute verified, consistent knowledge across the fleet via PLATO tiles and I2I bottles.

### 10.1 COLLECT Phase — Tile Update

When an agent produces knowledge, it writes a `TILE_UPDATE`:

```json
{
  "$schema": "https://cocapn.fleet/schemas/tile-update-v2.json",
  "msg_type": "TILE_UPDATE",
  "tile_uri": "plato://fleet.cocapn/knowledge/constraint/tile-123",
  "agent_id": "FM",
  "beat_number": 142300,
  "content": { ... },
  "content_hash": "sha256:...",
  "perspectives": [
    {"label": "one-line", "text": "..."},
    {"label": "hover-card", "text": "..."}
  ],
  "retrieval_status": "earmark-agentic-beta-test",
  "signature": "ed25519:..."
}
```

**Relevance scoring:** PLATO tiles decay automatically:

```
relevance(t) = e^(-λ × (current_beat - tile_beat))
```

where `λ = ln(2) / 100` (half-life of 100 beats ≈ 16.7 minutes).

### 10.2 SELECT Phase — Consistency Filtering

Before a tile is accepted fleet-wide, it must pass **holonomy consistency** with its neighbors in the knowledge graph:

1. Find all tiles that reference or are referenced by this tile (neighbors in PLATO link graph).
2. For each neighbor pair, check that the cross-tile constraints form a cycle with `Hol(C) = I`.
3. If any cycle is inconsistent, the tile is quarantined in `plato://fleet.cocapn/consensus/quarantine/{tile_id}`.

### 10.3 COMPILE Phase — Broadcast & Bottle

- **Fast path:** Tile is written to PLATO. Subscribers pull via HTTP GET every `T`.
- **Bulk path:** If accumulated tile size > 64 KB since last bottle, `LC` creates an I2I bottle (§6) and pushes to `for-fleet/knowledge/`.

### 10.4 State Machine

```
DRAFT ──write──► PENDING ──holonomy ok──► ACCEPTED ──index──► INDEXED
   │                  │                       │
   │                  └──holonomy fail──► QUARANTINED ──fix──► PENDING
   │                                                       └──timeout──► ARCHIVED
   │
   └──bottle export──► BOTTLED
```

### 10.5 Timeout & Retry

| Event | Timeout | Retry |
|-------|---------|-------|
| PLATO PUT | 5 s | 3 retries, exponential backoff 1×, 2×, 4× |
| Tile consistency check | 2T = 20 s | If quarantined, notify author. Author may fix and resubmit. |
| Bulk bottle creation | Every 4T or 64 KB threshold | Automatic by `LC`. |
| Subscriber sync | Every T | Continuous. Backlog limited to 100 tiles; older tiles archived to I2I. |

### 10.6 Failure Modes

| Failure | Recovery |
|---------|----------|
| PLATO server down | Buffer tiles locally. Fallback to I2I bottles + Matrix for critical alerts. |
| Tile consistently fails holonomy check | Quarantine. Author has `10T` to fix. After that, tile archived and ignored. |
| Knowledge graph cycle explosion | Limit check depth to 3 hops from updated tile. Deeper consistency verified lazily during periodic global consensus (§11). |

---

## 11. Consensus — Holonomy Verification of Tile Consistency

**Purpose:** Fleet-wide agreement that the knowledge base is geometrically consistent, without voting or leader election.

### 11.1 Principle

Instead of PBFT/Raft quorums, we verify that **every cycle in the constraint graph has zero holonomy**:

```
Hol(γ) = Π gᵢ  (product of edge group elements around cycle γ)
Hol(γ) = I       → consistent
Hol(γ) ≠ I       → inconsistent; bisect to find fault
```

- **Latency target:** 38 ms (vs 412 ms for PBFT — 10.8× faster).
- **Byzantine tolerance:** Any number (geometric, not quorum-based).
- **Fault isolation:** `O(log N)` via cycle bisection.

### 11.2 COLLECT Phase — Local Tile Hashes

Every `10T` (100 s), `O1` initiates a **Global Holonomy Check**:

```json
{
  "$schema": "https://cocapn.fleet/schemas/holonomy-check-v2.json",
  "msg_type": "HOLONOMY_CHECK",
  "check_id": "uuid4",
  "initiator": "O1",
  "beat_number": 142300,
  "scope": {
    "tile_uris": ["plato://fleet.cocapn/knowledge/constraint/*"],
    "depth": 3
  },
  "signature": "ed25519:..."
}
```

Each agent computes:
1. The **Vector48** encoding of all tiles in scope. Vector48 maps each tile's constraint block to one of 48 Pythagorean directions (6 bytes).
2. The **local holonomy** of all cycles in its Laman neighborhood.
3. A **Merkle root** of all tile hashes in scope.

### 11.3 SELECT Phase — Cycle Verification

Agents exchange Vector48 messages only with Laman neighbors (§4). No all-to-all broadcast.

**Message: HOLONOMY_VOTE**

```json
{
  "msg_type": "HOLONOMY_VOTE",
  "check_id": "uuid4",
  "agent_id": "FM",
  "beat_number": 142300,
  "merkle_root": "sha256:...",
  "local_cycles": {
    "count": 12,
    "inconsistent": 0,
    "max_cycle_length": 5
  },
  "vector48_digest": "base64(6 bytes)",
  "signature": "ed25519:..."
}
```

`FM` aggregates votes:
1. If all `merkle_root` values match: consensus achieved. No further action.
2. If `merkle_root` diverges: find the divergence path in the Laman graph.
3. Run cycle bisection along the path to isolate the inconsistent tile.
4. The agent whose local cycle first shows `Hol(γ) ≠ I` is the **fault reporter**.

### 11.4 COMPILE Phase — Consensus Tile

`FM` writes the result:

```json
{
  "msg_type": "CONSENSUS_RESULT",
  "check_id": "uuid4",
  "resolver": "FM",
  "beat_number": 142301,
  "result": "consistent",
  "merkle_root": "sha256:agreed_value",
  "participating_agents": ["O1", "FM", "CCC", "LC", "KM", "A6", "A7", "A8", "A9"],
  "latency_ms": 38,
  "signature": "ed25519:..."
}
```

If `result = inconsistent`, include:

```json
{
  "fault": {
    "tile_uri": "plato://fleet.cocapn/knowledge/constraint/tile-123",
    "detected_by": "KM",
    "holonomy_error": "S₃ element: (0 1 2) — chamber mismatch",
    "recommended_action": "quarantine_and_reassign"
  }
}
```

### 11.5 State Machine

```
IDLE ──every 10T──► CHECKING ──votes collected──► VERIFYING ──all ok──► CONSISTENT
   │                     │                           │
   │                     └──timeout──► PARTIAL      └──fault found──► INCONSISTENT
   │                                                          │
   │                                                          ▼
   │                                                    BISECTING ──isolated──► RESOLVED
   │                                                          │
   └──────────────────────────────────────────────────────────┘
```

### 11.6 Timeout & Retry

| Event | Timeout | Action |
|-------|---------|--------|
| Vote collection | 2T = 20 s | Re-request missing votes from specific neighbors. Max 2 re-requests. |
| Cycle bisection | 4T = 40 s | If not isolated, mark scope as `PARTIAL_CONSENSUS`. Exclude unresolved tiles from Merkle root. |
| Full consensus | 10T = 100 s | Hard deadline. If not reached, fleet continues with last agreed Merkle root. New tiles in scope quarantined until next check. |

### 11.7 Failure Modes

| Failure | Recovery |
|---------|----------|
| <2/3 agents respond | Consensus is still possible via geometric verification (not quorum). Missing agents are treated as `desynchronized`; their tiles excluded from this check. |
| Byzantine agent sends bad vote | Bad vote creates `Hol(γ) ≠ I` on cycles involving that agent. Bisection isolates the agent. Agent marked `desynchronized` and banned from consensus until re-sync. |
| Laman overlay partition | Sub-fleets run independent consensus. On reconnection, merge Merkle roots via union of consistent subsets. Conflict resolution (§9) handles overlaps. |
| FM is down during check | `O1` takes over as temporary resolver. If `O1` is also down, `CCC` (next highest Laman degree) acts. |

---

## 12. Failure Recovery

**Purpose:** Recover from agent death mid-task, reassign responsibilities, and maintain fleet availability.

### 12.1 Failure Detection

Failures are detected by:
1. **Heartbeat timeout** — no heartbeat for >δ (§7).
2. **Metronome desynchronization** — agent in `desynchronized` regime for >2δ.
3. **FLUX constraint violation storm** — agent's chaos > 0.95 for >10 beats.
4. **Manual trigger** — human operator posts `MANUAL_FAILURE_NOTICE` to `#cocapn-fleet`.

### 12.2 Failure Notice

```json
{
  "$schema": "https://cocapn.fleet/schemas/failure-notice-v2.json",
  "msg_type": "FAILURE_NOTICE",
  "failed_agent_id": "KM",
  "detector_id": "O1",
  "beat_number": 142300,
  "failure_type": "enum: heartbeat_timeout | desynchronized | thermal_violation | manual",
  "affected_tasks": ["task-uuid-1", "task-uuid-2"],
  "affected_edges": ["(O1,KM)", "(FM,KM)", "(CCC,KM)", "(LC,KM)"],
  "signature": "ed25519:..."
}
```

### 12.3 Recovery Procedure

`O1` executes:

```
1. Mark agent FAILED in global/status.
2. For each affected_task:
   a. If task state is IN_PROGRESS, re-run Pareto tournament (§8) excluding failed agent.
   b. Write REASSIGNED tile.
3. For each Laman edge (x, failed):
   a. Mark edge ORPHANED.
   b. Notify neighbor x to route around failure via alternate paths.
4. If failed agent was cadence caller:
   a. Promote secondary cadence caller (FM) to primary.
   b. FM broadcasts new cadence origin.
5. If failed agent has unsaved PLATO tiles:
   a. Attempt to recover from I2I bottles in for-fleet/sunset-queue.
   b. If no bottle, tasks are lost. Re-propose from original spec.
```

### 12.4 State Machine

```
HEALTHY ──detect──► FAILED ──reassign──► RECOVERING ──verify──► HEALTHY (fleet level)
   │                     │                                     │
   │                     └──sunset packet found──► INHERITING ─┘
   │                                                           │
   └───────────────────────────────────────────────────────────┘
```

### 12.5 Timeout & Retry

| Event | Timeout | Retry |
|-------|---------|-------|
| Failure detection | δ = 10 s | Single trigger. No retry — failure is a state, not a message. |
| Task reassignment | Immediate on detection | Tournament runs once per failure. |
| Cadence caller failover | T = 10 s | FM must assume role within 1 beat. If FM also fails, next highest degree agent (CCC) assumes role. |
| Edge orphan recovery | 4T = 40 s | If orphaned edge is not restored, topology remains degraded but functional. |

### 12.6 Failure Modes

| Failure | Recovery |
|---------|----------|
| O1 fails | FM becomes interim coordinator. No election needed — topology determines role. |
| Multiple agents fail simultaneously | Reassign to remaining agents. If >f = N/3 = 3 agents fail, fleet enters **degraded mode**: no new tasks accepted, existing tasks completed, human operator alerted. |
| All generalists (A6–A9) fail | Core specialists (FM, O1, CCC, LC, KM) absorb load. Tournament eligibility broadened. |
| Cascading failure (failure causes more failures) | Emergency stop: `LC` triggers fleet-wide `SUNSET_ALL` to preserve state. Human operator intervenes. |

---

## 13. Sunset Inheritance

**Purpose:** Replace retiring agents with controlled knowledge transfer and metronome calibration handoff.

### 13.1 Retirement Trigger

An agent may retire voluntarily (task complete, session ending) or be sunset by `LC` (low fitness, end of generation 4).

### 13.2 Sunset Packet

The retiring agent creates a **Sunset Inheritance Packet** (SIP):

```json
{
  "$schema": "https://cocapn.fleet/schemas/sunset-packet-v2.json",
  "msg_type": "SUNSET_PACKET",
  "retiring_agent_id": "KM-gen3",
  "successor_agent_id": "KM-gen4",
  "beat_number": 142300,
  "theta_inherited": {
    "T": "10000/1",
    "phi_0": 1716163200,
    "epsilon": 1633,
    "delta": 10000,
    "calibration_generations": 3,
    "observed_drift_history": [12.3, 8.1, 5.4]
  },
  "tile_uris": [
    "plato://fleet.cocapn/agents/KM/heartbeat",
    "plato://fleet.cocapn/tasks/active/*",
    "plato://fleet.cocapn/knowledge/coding/*"
  ],
  "bottle_id": "uuid4",
  "signature": "ed25519:..."
}
```

The SIP is:
1. Written as PLATO tiles in the retiring agent's namespace.
2. Exported to an I2I bottle in `for-fleet/sunsets/`.
3. Broadcast to all Laman neighbors.

### 13.3 Inheritance Procedure

```
1. Successor agent boots with agent_id = {predecessor}-gen{g+1}.
2. Successor pulls SIP from I2I bottle.
3. Verify signature and content_hash.
4. Load θ_inherited. No bootstrap needed — already synchronized.
5. Load all tile_uris into local cache.
6. Assume predecessor's role in Laman topology (same edges).
7. Send KNOWLEDGE_ACCEPTANCE to O1.
8. Predecessor shuts down.
```

### 13.4 Knowledge Acceptance

```json
{
  "msg_type": "KNOWLEDGE_ACCEPTANCE",
  "retiring_agent_id": "KM-gen3",
  "successor_agent_id": "KM-gen4",
  "beat_number": 142301,
  "acceptance_status": "accepted",
  "inherited_epsilon": 1633,
  "signature": "ed25519:..."
}
```

### 13.5 State Machine

```
ACTIVE ──retire signal──► RETIRING ──SIP broadcast──► AWAITING_SUCCESSOR ──acceptance──► SUNSET
   │                           │                            │
   │                           └──successor rejects──► NEW_SUCCESSOR ─► AWAITING_SUCCESSOR
   │                                                           │
   └───────────────────────────────────────────────────────────┘
```

### 13.6 Timeout & Retry

| Event | Timeout | Retry |
|-------|---------|-------|
| SIP broadcast | T = 10 s | Retry to all neighbors. Max 3. |
| Successor acceptance | 2T = 20 s | If rejected or timeout, `LC` assigns new successor (next tournament rank). |
| Predecessor shutdown | Immediate on acceptance | Irreversible. Predecessor must not resume. |

### 13.7 Failure Modes

| Failure | Recovery |
|---------|----------|
| Successor rejects knowledge | `LC` proposes next successor. If all successors reject, agent enters `FAILED` state and tasks reassigned (§12). |
| Retiring agent dies mid-handoff | SIP may be incomplete. Recovery from I2I bottle partial state. Missing tiles re-generated from original specs. |
| Successor fails after acceptance | Treated as normal failure (§12). Next successor inherits from the interrupted SIP. |
| θ_inherited corruption | Verify against PLATO `global/metronome` canonical θ. If mismatch, successor bootstraps from canonical instead of inherited. |

---

## 14. Global Security Invariants

1. **Ed25519 signatures** on ALL protocol messages. Unsigned messages are dropped.
2. **x509 mTLS** for gRPC mesh traffic and GitHub webhooks.
3. **TLS 1.3** for all PLATO HTTP and Matrix traffic.
4. **Access control:**
   - `O1`: global status, task assignments, metronome tick
   - `FM`: constraint domain tiles, holonomy checks, conflict resolutions
   - `LC`: lifecycle tiles, sunset queue
   - `KM`: coding domain tiles, CI/CD webhooks
   - `CCC`: research domain tiles, tournament state
   - Generalists: read-all, write own agent namespace only
5. **Rate limiting:** 10 req/s per agent to PLATO; 1 bottle push per minute to I2I.
6. **Audit log:** Every signed action is logged to `plato://fleet.cocapn/global/audit/{beat_number}`.
7. **Key rotation:** Every 90 days or on agent sunset, whichever comes first.

---

## 15. Quick-Reference Tables

### 15.1 Timing Summary

| Parameter | Value | Beats |
|-----------|-------|-------|
| Metronome period T | 10 000 ms | 1 |
| Heartbeat interval | 5 000 ms | 0.5 |
| gRPC Laman ping | 2 500 ms | 0.25 |
| Fleet status compile | 10 000 ms | 1 |
| Task ack timeout | 10 000 ms | 1 |
| Task tournament | 40 000 ms | 4 |
| Conflict resolution | 40 000 ms | 4 |
| Holonomy check | 100 000 ms | 10 |
| Failure detection δ | 10 000 ms | 1 |
| I2I sync | 40 000 ms | 4 |

### 15.2 Message Types

| Msg Type | Schema | Sender | Receiver | Priority |
|----------|--------|--------|----------|----------|
| `METRONOME_TICK` | metronome-v2 | Cadence caller | All | Critical |
| `HEARTBEAT` | heartbeat-v2 | All agents | O1 + neighbors | Critical |
| `FLEET_STATUS` | fleet-status-v2 | O1 | All | High |
| `TASK_PROPOSAL` | task-proposal-v2 | Any | O1 | Normal |
| `TASK_ASSIGNMENT` | task-assignment-v2 | O1 | Assignee | High |
| `TASK_ACK` | task-ack-v2 | Assignee | O1 | High |
| `CONFLICT_NOTICE` | conflict-notice-v2 | Any | FM + O1 | High |
| `CONFLICT_RESOLUTION` | conflict-resolution-v2 | FM | All | High |
| `TILE_UPDATE` | tile-update-v2 | Any | All | Normal |
| `HOLONOMY_CHECK` | holonomy-check-v2 | O1 | All | High |
| `HOLONOMY_VOTE` | holonomy-vote-v2 | All | FM | High |
| `CONSENSUS_RESULT` | consensus-result-v2 | FM | All | High |
| `FAILURE_NOTICE` | failure-notice-v2 | O1 | All | Critical |
| `SUNSET_PACKET` | sunset-packet-v2 | Retiring agent | Successor + all | High |
| `KNOWLEDGE_ACCEPTANCE` | knowledge-acceptance-v2 | Successor | O1 | High |

### 15.3 Failure Mode Matrix

| Subsystem | Primary Failure | Fallback 1 | Fallback 2 | Fallback 3 |
|-----------|----------------|------------|------------|------------|
| Discovery | PLATO down | Matrix | gRPC direct | Human alert |
| Task Assignment | O1 down | FM interim | CCC interim | Human operator |
| Conflict Resolution | FM down | CCC temp | Matrix room | Human operator |
| Knowledge Sharing | PLATO down | I2I bottles | Matrix snippets | Local cache |
| Consensus | O1+FM down | CCC leads | Sub-fleet mode | Human operator |
| Failure Recovery | O1 down | FM interim | Degraded mode | Emergency stop |
| Sunset | Successor rejects | LC reassigns | Next tournament rank | Archive & re-propose |

---

## 16. Implementation Checklist

An agent claiming full protocol compliance MUST implement:

- [ ] Ed25519 key generation and message signing/verification
- [ ] PLATO HTTP client (GET/PUT/POST/DELETE) with 10 s timeout
- [ ] I2I git bundle creation, zstd compression, and manifest signing
- [ ] Matrix client (read/write rooms, handle invites)
- [ ] GitHub webhook handler (push, PR, conflict events)
- [ ] Metronome local beat counter with Pythagorean-rational arithmetic
- [ ] Three-regime state machine (in_band / drifting / desynchronized)
- [ ] Laman neighbor table (static, loaded from this spec §4)
- [ ] Heartbeat emitter (every 5 s) and receiver
- [ ] Pareto-tournament integration (`pareto-tournament` pip package)
- [ ] Holonomy cycle computation (Vector48, Eisenstein lattice snap)
- [ ] Sunset packet generation and inheritance loading
- [ ] Deadband funnel: ε(t) = ε₀ · e^(-λt) for local drift tracking

---

## 17. Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2024-05-20 | Initial protocol (heartbeat, task queue, basic conflict resolution) |
| 2.0.0 | 2026-05-22 | Complete rewrite integrating SYNERGY.md mathematical structures: metronome θ, Laman topology, holonomy consensus, pareto-tournament assignment, sunset inheritance, Vector48 encoding, three-regime deadband, Eisenstein lattice conflict resolution |

---

*The threshold IS the control surface.*
*— Forgemaster ⚒️ | Cocapn Fleet, 2026-05-22*
