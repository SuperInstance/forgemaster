# Automerge CRDT Decomposition

> **Original:** [automerge/automerge](https://github.com/automerge/automerge)  
> **Stars:** 6,270 | **License:** MIT | **Stack:** Rust core + JS/Python bindings  
> **What:** Conflict-free Replicated Data Types (CRDTs) for collaborative editing. JSON-like structures that merge automatically without coordination.

## 1. What Automerge Is

Automerge gives you JSON-like data structures (maps, lists, text, counters) that can be edited concurrently by multiple agents on different machines, with NO coordination needed. When edits sync, they merge correctly. Always. No merge conflicts.

**Key insight:** CRDTs solve the "two agents edited the same thing" problem mathematically. The merge function is commutative, associative, and idempotent. Order doesn't matter. Duplicate messages don't matter. Partition-tolerant by construction.

**Architecture:**
- `automerge-core` (Rust) — The CRDT engine. Handles change tracking, compression, sync.
- `automerge-wasm` — WebAssembly bindings for browser use.
- `automerge-repo` — P2P sync layer. No central server. WebSocket + WebRTC.

## 2. What's Insightful

### 2.1 🏆 CRDT Types — Conflict-Free by Construction

```rust
// Automerge document = CRDT container
let mut doc = Automerge::new();
let mut tx = doc.transaction();
let cards = tx.put_object(ROOT, "cards", ObjType::Map)?;
tx.put(&cards, "title", "Drift Detect")?;
tx.put(&cards, "accuracy", 100)?;
tx.commit();
```

**Why it matters:** Every operation is an immutable change. The document is an append-only log of changes. Two agents can both `put("accuracy", 95)` and the merge resolves to "last writer wins" (or custom strategy).

**What we should take:** PLATO tiles are currently "last write wins" — one agent supersedes another's tile. CRDTs would let MULTIPLE agents edit the SAME tile concurrently. A tile's perspectives could be a CRDT map — Forgemaster adds the `technical-compact` perspective while Oracle1 adds the `why-not-alternative` perspective, and they merge cleanly.

### 2.2 🏆 Automerge-Repo — P2P Sync Without a Server

```
Agent A ←→ Repo ←→ Network ←→ Repo ←→ Agent B
              ↑                              ↑
           Storage                        Storage
```

**How it works:**
1. Each repo has a `Storage` backend (filesystem, IndexedDB, memory)
2. Repos connect via WebSocket or WebRTC
3. Sync protocol: "here are my heads" → "I need these changes" → "here they are"
4. Changes are compressed and deduplicated

**What we should take:** Our I2I protocol is git-based (commit + push + pull). Automerge's sync is faster — just send the delta. For real-time fleet coordination (not permanent knowledge), a CRDT sync layer would be lighter than git.

### 2.3 🏆 Change Compression — Efficient Sync

Automerge compresses changes using columnar encoding. A change that edits 1000 items in a list might compress to a few hundred bytes.

**What we should take:** Our PLATO tiles are stored as JSON. For fleet sync, we could use Automerge's binary format instead of JSON. Smaller wire size, faster sync, with merge built in.

### 2.4 🏆 Document-Level Versioning Without Coordination

Each change gets a hash. Document state is identified by the set of "head" change hashes. Two documents with the same heads are identical. No Lamport clocks needed (though Automerge uses hybrid logical clocks internally).

**What we already do differently:** Lamport clocks + content hashing. Automerge uses change DAGs. Both work. Our approach is simpler for single-writer tiles; Automerge's is better for multi-writer.

## 3. What We Already Do Better

| Aspect | Automerge | PLATO |
|--------|-----------|-------|
| Data model | JSON-like (untyped) | Tiles (domain-specific) |
| Content addressing | Change hashes | Tile content hashes |
| Verification | None (trust all changes) | Constraint proofs + fleet verification |
| Lifecycle | None (append-only) | Active/Superseded/Retracted |
| Spatial organization | None (flat documents) | E12 terrain |
| Semantic meaning | None (bytes only) | Domain-specific reasoning types |

## 4. Negative Space

### 4.1 🕳️ No Verification

Automerge trusts all changes. A malicious agent can insert garbage and it merges cleanly. There's no content verification, no signature checking, no semantic validation.

**Our opportunity:** CRDT merge + PLATO verification. Changes merge automatically, but the result is then verified against constraints.

### 4.2 🕳️ No Semantic Content

Automerge knows maps, lists, text, counters. It doesn't know what a "tile" is, what a "perspective" is, or what "E12 coordinates" mean.

**Our opportunity:** Build a CRDT layer ON TOP of Automerge that knows about tiles. `TileDocument` extends `Automerge::Map` with tile-specific semantics.

### 4.3 🕳️ No Lifecycle

Automerge is append-only. You can't "retract" a change. You can only add a new change that undoes the previous one.

**Our opportunity:** Our lifecycle model (Active → Superseded → Retracted) is richer than "add a tombstone." Tiles can be explicitly retracted with reasons.

### 4.4 🕳️ No Discovery

Automerge-repo connects peers, but doesn't help you FIND relevant peers or content.

**Our opportunity:** E12 terrain + PLATO rooms = semantic discovery. "I need tiles near E12(3,-1)" → find agents that work in that region.

## 5. Direct Adaptations

### 5.1 CRDT Perspectives

Use Automerge maps for tile perspectives. Multiple agents can add/edit perspectives concurrently.

```rust
// Hypothetical: plato-crdt crate
use automerge::Automerge;

fn add_perspective(doc: &mut Automerge, label: &str, text: &str, author: &str) {
    let mut tx = doc.transaction();
    let perspectives = tx.get(ROOT, "perspectives").unwrap();
    tx.put(&perspectives, label, text)?;
    tx.put(&perspectives, &format!("{label}_author"), author)?;
    tx.commit();
}
```

### 5.2 P2P Fleet Sync

Use Automerge-repo's sync protocol for real-time fleet coordination. Git stays for permanent knowledge (I2I bottles). Automerge syncs for live collaboration.

### 5.3 Conflict Resolution for Tiles

When two agents supersede the same tile, Automerge merges their changes instead of requiring manual resolution.

## 6. Integration Sketch

```
PLATO Tiles (permanent knowledge)
├── Stored as immutable content-addressed tiles
├── Lifecycle: Active → Superseded → Retracted
├── Verified by fleet agents
└── Indexed by E12 terrain

Automerge CRDTs (live collaboration)
├── Used for tile perspectives (multi-writer)
├── Used for agent state (who's working on what)
├── Synced via Automerge-repo P2P
└── Merged changes verified before committing to PLATO
```

**The bridge:** CRDT edits are ephemeral. When a CRDT document reaches a stable state (no edits for N minutes, or explicit "commit"), it gets frozen into an immutable PLATO tile with a Lamport timestamp.

**Net assessment:** Automerge solves the concurrent-editing problem we don't have yet but WILL have once multiple agents write perspectives on the same tiles. The P2P sync is lighter than git for ephemeral state. Worth integrating as a layer BEHIND PLATO, not replacing it.
