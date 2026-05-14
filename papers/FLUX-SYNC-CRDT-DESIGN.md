# Smart CRDT × flux-index — The Sync Layer

## The Problem flux-index Doesn't Solve (Yet)

`flux-index` works great on one machine. You index a repo, search it locally. Done.

But in a fleet, you have **N machines**, each indexing different repos. Machine A indexes plato-training. Machine B indexes dodecet-encoder. Machine C indexes both. Right now, to search across all of them, you scan `/tmp` for `.flux.fvt` files.

What happens when:
- Machine A indexes a new repo — how does Machine B learn about it?
- Machine A re-indexes with better embeddings — how does Machine C get the update?
- Two machines index the same repo concurrently — how do you merge?
- A tile is deleted (file removed from repo) — how does that propagate?

This is exactly the CRDT problem. And the Eisenstein lattice gives us a *semantic* merge function.

## The Insight: Lattice-Merged Indexes

A `.fvt` file is a set of (tile, vector) pairs. When two machines index the same repo, they produce two sets. The merge question is: **which tiles survive?**

Traditional CRDTs answer this syntactically (last-writer-wins, add-wins, etc.). But we can do better because we have **embeddings** — we know what the tiles *mean*.

### Semantic OR-Set

An OR-Set (Observed-Remove Set) is a CRDT where:
- `add(element)` adds it with a unique tag
- `remove(element)` removes it (but only observed adds)
- Merge: add-wins — if concurrent add and remove, add wins

For flux-index, the "elements" are tiles, and the "tags" are content hashes. But we add a **semantic layer**:

Two tiles are "the same" if their cosine similarity > threshold (say 0.95). This means:
- Re-indexing a file that's been reformatted but not changed → same tile (semantic match)
- File genuinely changed → new tile (semantic miss)
- File renamed → same tile (content hash matches)

This is a **Semantic OR-Set**: the equality test is embedding-based, not hash-based.

### Delta-State Sync

Instead of shipping entire `.fvt` files (which can be MB), ship **deltas**:
- "I added 3 tiles, removed 1, updated embeddings for 5"
- Delta = {added: [...], removed: [...], updated: [...]}
- Merge is associative, commutative, idempotent (CRDT properties)

Each delta carries a **dot** = {replica_id, sequence_number}:
```
delta_1 = {dot: {machine_a, 1}, added: [tile_x, tile_y]}
delta_2 = {dot: {machine_a, 2}, removed: [tile_z]}
delta_3 = {dot: {machine_b, 1}, added: [tile_w]}
```

Merge is: apply all dots not yet seen. Idempotent by tracking seen dots.

### The Covering Radius as Merge Threshold

Here's where the Eisenstein lattice comes back:

Two tiles from different machines might describe the same function with slightly different embeddings (different IDF weights, different tokenization). The question: are they "the same tile"?

The covering radius $1/\sqrt{3}$ defines the merge threshold:
- If `cosine_sim(tile_a, tile_b) > 1 - 1/√3 ≈ 0.423` → **merge** (same semantic content)
- If below → **keep both** (different content)

Wait — that's too loose. Let me think again.

Actually, the covering radius works differently here. In the Eisenstein lattice, two points within $1/\sqrt{3}$ snap to the same lattice point. For embeddings, two tiles within cosine distance $θ$ are "in the same chamber."

The merge threshold should be **tight** — maybe 0.95 cosine similarity — because we want to detect actual changes. The covering radius tells us the *minimum* discriminable distance (anything closer is indistinguishable), not the merge threshold.

Better framing: The Eisenstein snap gives us a **discretization of embedding space**. Instead of comparing continuous cosine similarities, we snap each tile's embedding to a dodecet chamber. Two tiles in the same chamber are candidates for merge. Then we do exact comparison within the chamber.

This is the **two-level merge**:
1. **Chamber match** (cheap): snap embedding → same chamber? Candidate for merge.
2. **Semantic match** (precise): cosine > 0.95? Actually the same.

### Causal Ordering for Index Versions

When Machine A re-indexes, the new index causally supersedes the old one. This is a **Lamport clock** — exactly what PLATO already uses.

Each `.fvt` file gets a Lamport timestamp. Merge = take the higher timestamp for each tile. This is a **LWW-Register (Last Writer Wins)** per tile.

Combined with the semantic OR-Set:
```
merge(index_a, index_b):
  for each tile in index_a:
    if tile has semantic match in index_b:
      # Same content — take higher Lamport clock
      if tile_b.clock > tile_a.clock:
        keep tile_b
      else:
        keep tile_a
    else:
      # Unique to A — keep it
      keep tile_a
  for each tile in index_b:
    if no semantic match in index_a:
      keep tile_b
```

This converges. Always. No coordination needed.

## The G-Counter for Tile Access

A G-Counter (grow-only counter) tracks how many times each tile has been "useful" (clicked, accessed, returned in search results). This is a **relevance signal** that propagates across machines.

Machine A searches for "auth flow" → tile_42 scores 0.8, user clicks it → increment tile_42's G-Counter.

Machine B syncs with A → receives G-Counter delta → tile_42 now has higher relevance. When Machine B searches "authentication", tile_42 gets a small score boost.

This is **federated learning of search relevance** — without any central server. The G-Counter deltas are the "model updates," and the merge function is addition (a CRDT semilattice).

## The Architecture

```
Machine A                    Machine B
┌─────────────────┐          ┌─────────────────┐
│  flux-index      │          │  flux-index      │
│  ┌──────────┐    │  delta   │  ┌──────────┐    │
│  │ .fvt     │◄──┼─────────►├──►│ .fvt     │    │
│  │ + CRDT   │    │  sync    │  │ + CRDT   │    │
│  │ + clocks │    │          │  │ + clocks │    │
│  └──────────┘    │          │  └──────────┘    │
│  ┌──────────┐    │          │  ┌──────────┐    │
│  │ G-Ctr    │    │  counter │  │ G-Ctr    │    │
│  │ clicks   │◄──┼─────────►├──►│ clicks   │    │
│  └──────────┘    │          │  └──────────┘    │
└─────────────────┘          └─────────────────┘

Sync via:
  - PLATO tiles (persistent, async)
  - Matrix messages (instant, ephemeral)
  - Git push/pull (strongest, batch)
  - Direct TCP (fastest, local network)
```

## The Product

```bash
# Index locally (works offline)
flux-index ~/projects/my-api

# Sync with fleet (when connected)
flux-index sync --fleet cocapn

# Search everything everywhere
flux-index search --all --fleet "authentication middleware"

# See what's new from other machines
flux-index log --delta
```

`flux-index sync` ships delta-CRDTs to other fleet members. No central server. No conflict. No coordination. Just tiles flowing where they're useful.

## Why This Matters for the Dissertation

This is Chapter 11 material — the fleet coordination layer. The same CRDT principles that make PLATO tiles converge across agents also make flux-index converge across machines. The Eisenstein lattice provides:
1. **Chamber quantization** for cheap merge candidate detection
2. **Covering radius** as the minimum discriminable distance
3. **Dodecet snap** as the discretization of embedding space
4. **Lamport clocks** (already in PLATO) for causal ordering

One lattice. Three scales. Sensor → Room → Fleet. Now also: Machine → Machine.

## Open Questions

- **Embedding drift across machines**: Different IDF weights produce different embeddings for the same content. Solution: ship IDF weights as part of the delta, or agree on a shared vocabulary.
- **Merge threshold tuning**: 0.95 might be too tight for cross-machine (different tokenizers). Need empirical testing.
- **G-Counter decay**: Old click data should decay. PN-Counter with decay, or a sliding window.
- **Security**: Untrusted machines could poison the index. Solution: trust anchors via GitHub PAT (same as PLATO).
- **Scale**: 10K tiles per machine × 100 machines = 1M tiles. Delta-state keeps this manageable.

## The Name

`flux-sync` — the CRDT sync layer for `flux-index`.

Or maybe it's just part of flux-index. `flux-index sync`.

Simple. One tool. Index, search, sync. Local-first, fleet-aware.
