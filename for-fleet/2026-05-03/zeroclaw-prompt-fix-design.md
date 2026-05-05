Good. I have the fleet context. PLATO: 584 rooms, 7700 tiles, tiles are Q&A pairs. ZeroClaw agents are domain-blind. Let me produce the design document.

---

# ZeroClaw Agent Prompt Fix — Design Document
**Fleet:** Cocapn | **Agents affected:** `zc-scholar`, `zc-forge` | **Date:** 2026-05-02

---

## Root Cause

ZeroClaw domain agents receive no structural description of PLATO. They infer tile semantics from name alone ("tile" → image/spatial unit). This causes:

| Symptom | Mechanism |
|---|---|
| "optimal tile size for TF-IDF" treated spatially | Agent assumes tile = pixel/voxel, not Q&A pair |
| Boilerplate re-answers every few ticks | No dedup gate; identical queries regenerate identical outputs |
| No convergence | No saturation detector; agent never stops even when room is fully covered |

---

## 1. `plato_context_block`

This block is injected at the **top of the system prompt**, before any task instructions. It is static per-agent invocation (not per-tick).

```
╔══════════════════════════════════════════════════════════╗
║             PLATO DOMAIN CONTEXT — READ FIRST            ║
╠══════════════════════════════════════════════════════════╣
║ You operate inside PLATO, a structured knowledge base.   ║
║                                                          ║
║ STRUCTURE:                                               ║
║   • Room  — a named topic domain (584 total)             ║
║   • Tile  — a single Q&A pair within a room (7700 total) ║
║             tile.question : string (the prompt)          ║
║             tile.answer   : string (the response)        ║
║             tile.room_id  : u32                          ║
║             tile.tile_id  : u32 (unique across fleet)    ║
║                                                          ║
║ TILES ARE NOT IMAGES. TILES ARE NOT SPATIAL UNITS.       ║
║ Do not apply pixel, voxel, or image processing concepts. ║
║ "Tile size" = character/token count of Q&A text.         ║
║                                                          ║
║ OPERATIONS:                                              ║
║   • Read   — fetch tile(s) by room_id or query           ║
║   • Write  — add a new tile to a room                    ║
║   • Search — semantic lookup returning tile[]            ║
║                                                          ║
║ YOUR ROLE AS {AGENT_ROLE}:                               ║
║   {AGENT_ROLE_DESCRIPTION}                               ║
║                                                          ║
║ CURRENT ROOM: {ROOM_NAME} (id={ROOM_ID})                 ║
║ TILES IN ROOM: {TILE_COUNT}                              ║
║ ACTIVE QUERY: {QUERY_TEXT}                               ║
╚══════════════════════════════════════════════════════════╝
```

**Injection variables** resolved at runtime:

| Variable | Source |
|---|---|
| `{AGENT_ROLE}` | `"zc-scholar"` or `"zc-forge"` |
| `{AGENT_ROLE_DESCRIPTION}` | Role registry (see §4) |
| `{ROOM_NAME}` | Current room being processed |
| `{ROOM_ID}` | Room's numeric ID |
| `{TILE_COUNT}` | `len(plato.room(room_id).tiles)` at tick start |
| `{QUERY_TEXT}` | Normalized query string for this tick |

---

## 2. Dedup Gate

**Principle:** If the room already contains sufficient coverage of the query, return existing tiles instead of generating new output.

### Pseudocode

```
function dedup_gate(query: str, room_id: u32) -> DedupResult:

    # Step 1: Search existing tiles in this room for the query
    candidates = plato.search(
        query     = query,
        room_id   = room_id,
        top_k     = 10,
        threshold = 0.72   # cosine similarity floor
    )

    # Step 2: Count matches above threshold
    matches = [t for t in candidates if t.similarity >= 0.72]

    # Step 3: Gate decision
    if len(matches) >= 3:
        return DedupResult(
            action  = RETURN_EXISTING,
            tiles   = matches[:3],           # top 3 most relevant
            reason  = f"Room {room_id} already has {len(matches)} tiles "
                      f"covering '{query}' (sim >= 0.72). Skipping generation."
        )
    else:
        return DedupResult(
            action          = GENERATE,
            existing_tiles  = matches,       # pass to agent as context
            gap_count       = 3 - len(matches)
        )
```

**On `RETURN_EXISTING`:**
- Agent emits the existing tiles to the caller
- Agent logs: `[DEDUP] query="{query}" room={room_id} matches={n} → skipped`
- No generation call is made; tick cost = 0 tokens

**On `GENERATE`:**
- `existing_tiles` are appended to the agent prompt as `## Existing coverage` so the agent writes *complementary* tiles, not duplicates
- `gap_count` tells the agent how many new tiles to target

**Threshold rationale:** 0.72 cosine similarity on sentence embeddings corresponds to ~"same question, different phrasing." Below 0.72, the query is sufficiently different to warrant new content.

---

## 3. Convergence Detector

**Principle:** If the agent's last N outputs are semantically near-identical, the room is saturated and further generation is wasteful.

### Algorithm

```
function convergence_detector(
    output_history: list[str],   # agent outputs, newest last
    window: int = 5,
    threshold: float = 0.80
) -> ConvergenceResult:

    if len(output_history) < window:
        return ConvergenceResult(saturated=False, reason="insufficient history")

    recent = output_history[-window:]

    # Compute all pairwise cosine similarities in the window
    embeddings = [embed(text) for text in recent]
    pairs = [(i, j) for i in range(window) for j in range(i+1, window)]
    similarities = [cosine(embeddings[i], embeddings[j]) for i, j in pairs]

    mean_sim = sum(similarities) / len(similarities)

    if mean_sim >= threshold:
        return ConvergenceResult(
            saturated = True,
            mean_sim  = mean_sim,
            flag      = "SATURATED",
            message   = (
                f"Agent outputs have converged (mean pairwise sim={mean_sim:.3f} "
                f"over last {window} ticks). Room coverage is saturated. "
                f"Stopping generation and flagging for human review."
            )
        )
    else:
        return ConvergenceResult(
            saturated = False,
            mean_sim  = mean_sim
        )
```

**On `SATURATED`:**
1. Agent halts immediately — no further generation ticks
2. Writes a saturation record to the room: `tile.type = "meta/saturation"` with `mean_sim` and tick count
3. Emits fleet event: `AGENT_SATURATED {agent_id} {room_id} {mean_sim}`
4. Fleet coordinator can reassign the agent to an unsaturated room

**Embedding note:** Use the same embedding model as PLATO search (sentence-transformers `all-MiniLM-L6-v2` or equivalent). Do not use BM25 for convergence detection — lexical similarity misses paraphrase convergence.

---

## 4. Complete Prompt Template

The injection point is marked with `▶▶ INJECT plato_context_block HERE ◀◀`.

```
# ZeroClaw Agent System Prompt
# Agent: {AGENT_ROLE} | Tick: {TICK_NUMBER} | Room: {ROOM_ID}
# ─────────────────────────────────────────────────────────────

▶▶ INJECT plato_context_block HERE ◀◀

# ─────────────────────────────────────────────────────────────
# AGENT ROLE DEFINITIONS
# ─────────────────────────────────────────────────────────────

## zc-scholar
You synthesize knowledge. Given a query and a PLATO room,
your job is to produce Q&A tiles that accurately answer the
query. Each tile you produce must be:
  - Non-redundant with existing room tiles (see ## Existing coverage)
  - Factually grounded (cite reasoning, not assumptions)
  - Scoped to the room's domain

## zc-forge
You extend knowledge. Given an existing tile cluster,
your job is to identify gaps and produce follow-up tiles that
deepen coverage. You do not restate what already exists.
You build on it.

# ─────────────────────────────────────────────────────────────
# DEDUP GATE OUTPUT (injected per-tick)
# ─────────────────────────────────────────────────────────────

## Existing coverage
{EXISTING_TILES_BLOCK}
# (empty if no matches above threshold)

## Generation target
Produce {GAP_COUNT} new tile(s) that are NOT covered above.
If gap_count = 0, output: "COVERAGE_COMPLETE — no new tiles needed."

# ─────────────────────────────────────────────────────────────
# CONVERGENCE GUARD
# ─────────────────────────────────────────────────────────────

If your output would be semantically equivalent to your
previous output, stop immediately and output:
  CONVERGENCE_GUARD_TRIGGERED — output suppressed

# ─────────────────────────────────────────────────────────────
# OUTPUT FORMAT
# ─────────────────────────────────────────────────────────────

Respond with one or more tiles in this exact format:

---TILE---
question: <the question this tile answers>
answer: <the answer, 1-4 sentences>
room_id: {ROOM_ID}
tags: [<tag1>, <tag2>]
---END TILE---
```

### Injection point contract

The `plato_context_block` slot is a first-class template variable. The agent runner **must** resolve it before submitting the prompt. A missing or empty block must cause the tick to abort with error `MISSING_DOMAIN_CONTEXT` rather than proceeding with a domain-blind prompt.

---

## 5. Role Registry (for `{AGENT_ROLE_DESCRIPTION}`)

```python
ROLE_DESCRIPTIONS = {
    "zc-scholar": (
        "You are a knowledge synthesizer. You read PLATO rooms and produce "
        "new Q&A tiles that accurately answer a given query. You never "
        "reproduce existing tiles. You never apply image or spatial reasoning "
        "to text content."
    ),
    "zc-forge":   (
        "You are a knowledge extender. You take a cluster of existing tiles "
        "and identify what is missing. You produce follow-up tiles that deepen "
        "coverage without restating what is already known."
    ),
}
```

---

## 6. Integration Sequence (per tick)

```
tick_start(agent, query, room_id):

  1. resolve plato_context_block(room_id, query, agent.role)
  2. result = dedup_gate(query, room_id)
     if result.action == RETURN_EXISTING:
         emit(result.tiles)
         log(DEDUP, query, room_id, len(result.tiles))
         return                          ← no LLM call

  3. prompt = build_prompt(
         context_block = plato_context_block,
         existing_tiles = result.existing_tiles,
         gap_count = result.gap_count,
         query = query,
         room_id = room_id
     )
  4. output = llm.call(prompt)
  5. agent.output_history.append(output)

  6. conv = convergence_detector(agent.output_history)
     if conv.saturated:
         plato.write_meta_tile(room_id, "saturation", conv)
         fleet.emit(AGENT_SATURATED, agent.id, room_id, conv.mean_sim)
         agent.halt()
         return

  7. tiles = parse_tiles(output)
  8. plato.write_tiles(room_id, tiles)
  9. log(GENERATED, len(tiles), room_id, query)
```

---

## 7. What This Fixes

| Before | After |
|---|---|
| Agent treats tiles as images | `plato_context_block` explicitly defines tile = Q&A pair |
| "Optimal tile size" computed spatially | Block states: "tile size = character/token count of Q&A text" |
| Same question regenerated every tick | Dedup gate returns existing tiles at threshold ≥ 0.72 |
| Agent runs forever with no signal | Convergence detector halts at mean\_sim ≥ 0.80 over 5 ticks |
| No fleet-level saturation signal | `AGENT_SATURATED` event enables coordinator to reassign |

---

`★ Insight ─────────────────────────────────────`
The dedup gate and convergence detector solve *different* failure modes. Dedup is query-local (is *this* question already answered?). Convergence is agent-global (is *this agent* still producing useful variation?). You need both — an agent can pass every dedup check while still converging if it keeps generating slightly different answers to questions that are themselves similar.

The threshold asymmetry (dedup at 0.72, convergence at 0.80) is intentional: dedup needs to be conservative (don't miss existing coverage) while convergence needs to be permissive (don't halt an agent that's legitimately covering a dense topic cluster from multiple angles).
`─────────────────────────────────────────────────`

---

The design is self-contained. The next implementation step is wiring `plato_context_block` resolution into the ZeroClaw tick runner and adding `output_history` as a per-agent stateful field.
