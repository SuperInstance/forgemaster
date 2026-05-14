# PBFT-Rust Decomposition

*Source: [0xjeffro/pbft-rust](https://github.com/0xjeffro/pbft-rust) — Actix-Web + reqwest based PBFT implementation*

---

## 1. What PBFT Is

Practical Byzantine Fault Tolerance (Castro & Liskov, 1999) provides distributed consensus that tolerates up to **f = ⌊(n-1)/3⌋** faulty/malicious nodes. The minimum cluster size is **n = 3f + 1**.

The protocol runs a **3-phase commit** on every request:
1. **Pre-Prepare** — Leader assigns sequence number, multicasts to replicas
2. **Prepare** — Replicas broadcast prepare votes; need 2f matching votes
3. **Commit** — Replicas broadcast commit votes; need 2f+1 matching votes → execute

Once 2f+1 commits arrive, the node executes the operation and replies to the client. The client waits for **f+1 identical replies** to confirm consensus.

---

## 2. What's Insightful — Rust Code Structure

### 2.1 Stage State Machine (`consensus/pbft.rs`)

```rust
enum Stage { Idle, PrePrepare, Prepare, Commit }

struct State {
    view_id: u32,                    // current view (leader epoch)
    current_stage: Arc<Mutex<Stage>> // thread-safe stage tracker
}
```

Minimal. The entire consensus state is a view number + stage enum. No log, no checkpoint, no state machine — just the phase tracker.

### 2.2 Message Types (`consensus/message.rs`)

| Struct | PBFT Notation | Fields |
|--------|---------------|--------|
| `RequestMsg` | `<REQUEST, o, t, c>` | operation, timestamp, client_id, sequence_id, digest |
| `PrePrepareMsg` | `<PRE-PREPARE, v, n, d>, m` | view_id, sequence_id, digest, request_msg |
| `VoteMsg` | `<PREPARE/COMMIT, v, n, d, i>` | view_id, sequence_id, digest, node_id, msg_type |
| `ReplyMsg` | `<REPLY, v, t, i, r>` | timestamp, view_id, node_id, client_id, result |

`VoteMsg` is reused for both Prepare and Commit via `MsgType` enum. Smart dedup.

Digest is computed via SHA-256 (`utils::compute_digest`). All messages derive `Serialize/Deserialize` for JSON transport.

### 2.3 Node Architecture (`network/node.rs`)

```rust
struct Node {
    id: u32,
    is_faulty: bool,
    node_table: HashMap<u32, String>,  // id → "localhost:port"
    view: View,                         // { id, primary_node_id }
    current_state: State,
    msg_buffer: MsgBuffer,              // 4 typed message buffers
}
```

`MsgBuffer` has separate `Arc<Mutex<Vec<T>>>` buffers for each message type. Faulty nodes are simulated by short-circuiting all handlers — they accept messages but do nothing.

### 2.4 Server: The Real Logic (`network/server.rs`)

Each PBFT phase is an Actix-Web POST endpoint:

| Endpoint | Phase | Key Logic |
|----------|-------|-----------|
| `POST /req` | Request received | Primary computes digest, creates PrePrepare, multicasts |
| `POST /preprepare` | Pre-Prepare | Verify digest matches, multicast Prepare vote |
| `POST /prepare` | Prepare | Count matching votes → when `cnt == 2f`, multicast Commit |
| `POST /commit` | Commit | Count matching votes → when `cnt == 2f+1`, execute & reply |

**The 2f / 2f+1 thresholds:**
- Prepare phase: needs **2f** matching prepare messages (includes own)
- Commit phase: needs **2f+1** matching commit messages
- This guarantees intersection: at least f+1 honest nodes overlap between any two quorums

### 2.5 View Change / Leader Failure

**Not implemented.** The primary is static (`primary_node_id: 0`). View ID starts at 9999 (uninitialized sentinel) and never changes. This is the biggest gap — no recovery from primary failure.

### 2.6 Dependencies

```
actix-web 4.0    — HTTP server (each node is a web server)
reqwest 0.12     — HTTP client (inter-node communication)
serde/serde_json — JSON serialization
sha2 0.11        — digest computation
futures          — join_all for concurrent multicast
```

All communication is synchronous HTTP over localhost. No persistent storage, no signatures (just digest matching), no real authentication.

---

## 3. How This Maps to PLATO — Fleet Tile Verification as BFT

PLATO's fleet consensus problem maps cleanly:

| PBFT Concept | PLATO Equivalent |
|---|---|
| Client request | Tile submission (e.g., a TrainingTile) |
| Operation | Tile content hash verification |
| Sequence number | Lamport clock value (already in `plato-types`) |
| View | Fleet epoch / Oracle1's coordination round |
| Primary node | Oracle1 🔮 (fleet coordinator) |
| Replicas | Fleet agents (Forgemaster, etc.) |
| Digest | Content-addressed tile hash (already in `plato-types::TileId`) |
| 2f+1 commit | Quorum of agents verify tile integrity |
| Reply | Verified tile stored in `LocalTileStore` |

PLATO already has content-addressed tiles with Lamport clocks. We'd be adding a **verification quorum** layer on top.

---

## 4. Negative Space — What's Missing

### Critical Gaps in pbft-rust:
1. **No content-addressed state** — Digests are ephemeral strings, not content-addressed identifiers
2. **No semantic verification** — They check digest matches but never verify the *operation* is valid
3. **No tile lifecycle** — No `TileLifecycle` enum, no state transitions, no `Committed`/`Verified` states
4. **No view change** — Static primary, no recovery from leader failure
5. **No persistent storage** — Everything in memory, lost on restart
6. **No signatures** — Digest matching only, no cryptographic proof of origin
7. **No checkpoints** — No garbage collection of old messages
8. **No batching** — One request at a time, no pipelining

### What PLATO Already Has That pbft-rust Doesn't:
- Content-addressed `TileId` (SHA-256 of content)
- `TileLifecycle` state machine
- `LamportClock` for ordering
- `LocalTileStore` for persistence
- Fleet-aware throttle
- Hardware deployment pipeline

---

## 5. Direct Adaptations

### What we can lift directly:

**Message types** — Their `VoteMsg` pattern (single struct, `MsgType` enum) is clean and maps to our tile verification:

```rust
// Adapted for PLATO tile verification
#[derive(Serialize, Deserialize, Debug, Clone)]
pub enum TileVoteType {
    VerifyPrePrepare,  // Oracle1 proposes tile for verification
    VerifyPrepare,     // Agent confirms tile hash matches
    VerifyCommit,      // Agent commits to verified tile
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct TileVoteMsg {
    pub view_id: u32,           // fleet epoch
    pub sequence_id: u64,       // Lamport clock value
    pub tile_digest: String,    // content-addressed TileId
    pub node_id: String,        // agent identifier
    pub vote_type: TileVoteType,
}
```

**Quorum counting** — Their `2f` / `2f+1` pattern is directly reusable. For a 9-agent fleet: `f = 2` (tolerate 2 faulty), prepare quorum = 4, commit quorum = 5.

**Phase-gated state machine** — The `Stage` enum + `Arc<Mutex<Stage>>` pattern works for our tile lifecycle transitions.

### What we should NOT adopt:
- HTTP-as-transport (PLATO uses git-based I2I bottles + Matrix)
- In-memory buffers (PLATO has `LocalTileStore`)
- Static primary (Oracle1 role should be dynamic)
- No-signature model (fleet needs authenticated messages)

---

## 6. Integration Sketch — PBFT Consensus for PLATO Tile Verification

```
Phase 1: Pre-Prepare (Oracle1 proposes)
  Oracle1 receives tile → computes TileId
  → multicasts <PRE-PREPARE, epoch, lamport, tile_id> to fleet agents

Phase 2: Prepare (Agents verify)
  Agent receives pre-prepare
  → fetches tile content from LocalTileStore or git
  → recomputes TileId, confirms match
  → multicasts <PREPARE, epoch, lamport, tile_id, agent_id>

Phase 3: Commit (Quorum reached)
  Agent collects 2f matching prepares
  → multicasts <COMMIT, epoch, lamport, tile_id, agent_id>
  
Phase 4: Execute (Tile lifecycle transition)
  Agent collects 2f+1 matching commits
  → transitions tile to Verified state in LocalTileStore
  → replies to Oracle1 with <REPLY, epoch, tile_id, agent_id, result>

Client (Oracle1):
  Collects f+1 matching replies → tile is fleet-verified
  → transitions tile to Committed in global store
```

### Where it plugs in:
- **New crate:** `SuperInstance/plato-consensus` (alongside plato-types, plato-data, plato-training)
- **Dependencies:** `plato-types` (TileId, TileLifecycle, LamportClock), `plato-data` (tile fetching)
- **Transport:** I2I bottles over git (not HTTP) — agents poll their `for-fleet/` directories
- **Quorum config:** `n` agents, `f = floor((n-1)/3)`, thresholds `2f` and `2f+1`
- **State:** Tiles progress `Pending → PrePrepared → Prepared → Committed → Verified`

### Simplification for fleet:
With 9 trusted agents (not adversarial), we can use a **relaxed quorum**: simple majority (5/9) instead of BFT's 2f+1. But the message flow stays identical — just lower the thresholds.

---

## Summary

pbft-rust is a clean educational PBFT with good message type design but shallow implementation. The **structural patterns** (3-phase commit, typed message buffers, quorum counting) are directly adaptable. The **content** (no persistence, no signatures, no view change) needs replacement with PLATO's existing infrastructure.

The highest-value lift: their `VoteMsg` + `MsgType` enum pattern as a template for `TileVoteMsg` in a new `plato-consensus` crate.
