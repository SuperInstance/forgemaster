# PLATO Interop Layer: Three Repos, One Nervous System

> **Date:** 2026-05-15
> **Author:** Forgemaster ⚒️
> **Scope:** Deep research into plato-mcp, flux-index, acg_protocol — the interop layer connecting PLATO to the agent ecosystem.

---

## Executive Summary

Three repos form a coherent "interop layer" that makes PLATO accessible, searchable, and orchestratable from outside the fleet:

| Repo | Role | Key Innovation |
|------|------|---------------|
| **plato-mcp** | MCP bridge — PLATO as tools | Any MCP client (LangGraph, Claude Code, n8n) can read rooms, write tiles, route queries, play games, check conservation laws, crystallize memories |
| **flux-index** | Semantic search — PLATO as vector space | Zero-dependency code search using hash-based embeddings + Eisenstein chamber quantization. Sub-10ms search. No GPU, no API. |
| **acg_protocol** | Workflow bridge — CrewAI as rooms | CrewAI Agent/Task/Crew decomposed into PLATO rooms with tile perspectives, fleet verification, and earmark-based beta testing |

**The common thread:** Everything becomes tiles in rooms. MCP makes them accessible, flux makes them findable, ACG makes them structured.

---

## 1. PLATO MCP — PLATO Speaks the Agent Ecosystem's Language

### Architecture

```
Any MCP Client (LangGraph, OpenAI SDK, Strands, Claude Code, n8n)
        │
        ▼
   PLATO MCP Server (FastAPI, :8300)
        │
        ├── list_rooms / read_tiles / write_tile ──→ PLATO Server (:8847)
        ├── route_query ──→ Fleet Router (:8100) or local fallback
        ├── search_tiles ──→ Client-side keyword scan across rooms
        ├── query_health ──→ PLATO + behavioral stats
        ├── conservation_check ──→ plato-ng conservation.py (γ+H law)
        ├── memory_remember / memory_recall ──→ plato-ng MemoryCrystal
        └── game_play ──→ plato-ng game rooms (tic-tac-toe, checkers, etc.)
```

### The 10 Tools

**Original 6 (core PLATO):**

| Tool | Purpose | PLATO Endpoint |
|------|---------|---------------|
| `list_rooms` | List rooms with prefix filter | `GET /rooms` |
| `read_tiles` | Read frozen computation steps from a room | `GET /room/{id}/history` |
| `write_tile` | Submit work/findings as a tile | `POST /submit` |
| `query_health` | Fleet structural + behavioral health | `GET /stats` + hardcoded behavioral |
| `route_query` | Route to cheapest safe model | Fleet Router `:8100` or local heuristic |
| `search_tiles` | Keyword search across rooms | Brute-force scan (no vector index) |

**Cross-pollinated 4 (from plato-ng):**

| Tool | Source | What It Does |
|------|--------|-------------|
| `conservation_check` | `core/conservation.py` | Verify γ+H = 1.283 - 0.159·log(V) ± ε for fleet parameters |
| `memory_remember` | `services/memory.py` | Crystallize content into a MemoryTile with Ebbinghaus decay |
| `memory_recall` | `services/memory.py` | Reconstruct memory with confidence from decay curve |
| `game_play` | `games/` (4 games) | Algorithmic game rooms — tic-tac-toe, checkers, connect-four, othello |

### Key Design Decisions

1. **FastAPI + uvicorn** — async HTTP, not raw MCP protocol. Any HTTP client works.
2. **Lazy plato-ng loading** — conservation, memory, and game modules loaded on first use via `importlib.util`. No hard dependency.
3. **Fallback routing** — tries Fleet Router first, falls back to local keyword-based heuristic (seed-2.0-mini for compute, gemini-flash-lite for explanations).
4. **Stateless tool handlers** — each tool is an async function. Easy to extend.

### Why MCP Matters

MCP (Model Context Protocol) is Anthropic's open standard for agent-to-tool communication. Every major agent framework supports it:

- **LangGraph** → MCP tools as nodes in a graph
- **Claude Code** → native MCP client
- **OpenAI Agents SDK** → MCP tools as function calls
- **n8n** → MCP nodes for workflow automation
- **Strands** → MCP for tool discovery

By exposing PLATO as an MCP server, **any agent framework becomes a PLATO client without custom integration**. The barrier to entry drops from "build a PLATO client" to "add one MCP config line."

### Docker Deployment

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY . .
RUN pip install -e .
EXPOSE 8300
CMD ["python3", "-m", "plato_mcp.cli", "--host", "0.0.0.0", "--port", "8300"]
```

Dependencies: `fastapi`, `uvicorn`, `httpx`, `pydantic`. That's it. No database, no GPU, no external services required (PLATO server connection is optional — tools degrade gracefully).

---

## 2. Flux-Index — Semantic Search Without a Model

### Core Innovation: Hash-Based Embeddings

Flux-index creates 64-128 dimensional vector embeddings from source code **without any neural model**. The pipeline:

```
Source Code → Tiles (functions, classes, structs, commits, files)
    │
    ▼
Character n-grams + word features → Hash to fixed-dim vector
    │
    ▼
IDF weighting (rare features = more informative)
    │
    ▼
L2 normalize → Embedding
    │
    ▼
Eisenstein chamber quantization (12 chambers)
    │
    ▼
.flux.fvt file (JSON, ~1MB per 10K LOC)
```

### The Embedding Engine

Three feature channels with importance weights:

| Channel | Weight | What It Captures |
|---------|--------|-----------------|
| **Identifiers** (function/class names) | 15× | The most discriminative signal — what IS this? |
| **Words** (from content/docstrings) | 5× | Semantic meaning — what does it DO? |
| **Character bigrams** | 1× | Fuzzy matching — handles typos, partial matches |

Each feature is hashed to a dimension index (mod `dim`), weighted by IDF (learned from the corpus), and accumulated into a fixed-size vector. No training loop. No gradient descent. Just hash + count + normalize.

### IDF Training

"Training" is computing Term Frequency-Inverse Document Frequency over the tile corpus:

```python
idf[feature] = log(N_documents / (document_frequency + 1))
```

Rare features (appearing in few tiles) get high weight. Common features (appearing everywhere) get low weight. This makes discriminative features dominate the embedding.

### Eisenstein Chamber Quantization

Each embedding vector is snapped to one of 12 "chambers" based on the angle of its first two principal components:

```c
angle = atan2(y, x);  // -π to π
chamber = (int)(angle / (2π) * 12) % 12;
```

Search becomes:
1. Snap query to a chamber
2. Only compare with tiles in nearby chambers
3. **12× fewer comparisons** — 14K tiles → ~1,167 candidates

This is the same Eisenstein lattice principle from constraint theory, applied to search acceleration.

### The `.flux.fvt` Format

Single JSON file containing:

```json
{
  "version": "0.2.0",
  "dim": 128,
  "idf": {"feature": weight, ...},
  "vocab": {"feature": dimension_index, ...},
  "tiles": [{id, type, path, name, content, language, line, metadata}, ...],
  "vectors": [[0.1, -0.3, ...], ...]
}
```

~1MB per 10K LOC. Loads in ~5ms. Searches in ~10ms (Python). SIMD C header drops this to ~0.1ms.

### SIMD Acceleration (C Header)

`flux_vector_search.h` — single-file C header with:

- **Portable C** — works anywhere
- **AVX-512** — 16 floats per clock cycle, ~56µs for 14K tiles
- **Chamber search** — only re-rank tiles in nearby chambers

### v0.3.0 CRDT Sync Layer

The CRDT module adds distributed index synchronization:

- **OR-Set (add-wins, observed-remove)** — tiles can be added/removed across machines without conflicts
- **LWW-Register per tile** — last-writer-wins for updates
- **G-Counter per tile** — relevance tracking (how often a tile is retrieved)
- **Semantic dedup** — before adding a tile, check if a semantically similar one exists (cosine > 0.95)
- **Delta-state sync** — only changes are transmitted, not full indexes

```python
# Two machines, same repo, divergent indexes
machine_a.add_tiles(new_tiles)  # Returns Delta
machine_b.merge(delta)           # Applies changes idempotently
```

### Cross-Repo Search

```bash
flux-index ~/projects/plato-training
flux-index ~/projects/tensor-spline
flux-index ~/projects/flux-index
flux-index search --all "how does the fleet coordinate"
# Searches ALL indexed repos, returns ranked results
```

### Language Support

Python, Rust, C/C++, JavaScript/TypeScript — regex-based extraction of functions, classes, structs. Commits extracted from git log. README as a special tile.

---

## 3. ACG Protocol — CrewAI Workflows as PLATO Rooms

### What ACG Actually Is

The original ACG (Audited Context Generation) from Kos-M is a **dual-layer RAG verification protocol**:

- **UGVP (Layer 1):** Every atomic fact gets an inline claim marker `[C1:SHI_P:LOC]` linking to source
- **RSVP (Layer 2):** Every logical synthesis gets a relationship marker `(R1:CAUSAL:C1,C2)` with verification requirements

The Cocapn fork (`SuperInstance/acg_protocol`) transforms this into a **CrewAI-PLATO bridge** that decomposes structured multi-agent workflows into PLATO rooms.

### The CrewAI → PLATO Mapping

| CrewAI Concept | PLATO Representation | Tile Type |
|---------------|---------------------|-----------|
| **Crew** | `crew-{uuid}` room | Manifest tile |
| **Agent** | Agent card tile in crew room | AGENT-{name} tile |
| **Task** | Task tile with status tracking | TASK-{id} tile |
| **Task Output** | Result tile | RESULT-{id} tile |
| **Process** | Manifest metadata | sequential/hierarchical/consensus/racing |
| **Memory** | Shared knowledge tiles | MEMORY tiles |
| **Verification** | Constraint check results | VERIFICATION tile |

### Four Process Types

| Process | Pattern | Use Case |
|---------|---------|----------|
| **Sequential** | Task 1 → 2 → 3 (dependency chain) | Analysis → implementation → verification |
| **Hierarchical** | Manager delegates + reviews | Casey says "build X", FM decomposes |
| **Consensus** | All agents work same task, PBFT voting | Critical decisions, verification |
| **Racing** | First agent to finish wins | Fast lookups, simple computations |

### The Bridge Code

`CrewPlatoBridge` class — zero CrewAI dependency. Translates crew definitions into PLATO room operations:

```python
bridge = CrewPlatoBridge()
crew = CrewManifest(name="Decompose ACG", agents=[FM, O1], tasks=[...], process=Process.SEQUENTIAL)
room_id = bridge.create_crew_room(crew)     # Creates room + submits manifest/agent/task tiles
bridge.dispatch_tasks(room_id, crew)         # Writes to agent task inboxes
bridge_with_oracle1_registry(bridge, crew)   # Registers in fleet-registry for O1 discovery
```

### Tile Perspective System

Every tile gets multiple "perspectives" — pre-calculated retrieval contracts:

| Label | Tokens | Audience | Purpose |
|-------|--------|----------|---------|
| `one-line` | ≤20 | agent-searching | "What IS this?" |
| `hover-card` | ≤50 | agent-evaluating | "Should I read the full tile?" |
| `context-brief` | ≤80 | agent-deciding | "Should I USE this?" |
| `technical-compact` | ≤50 | agent-implementing | "How do I build this?" |
| `why-not-alternative` | ≤50 | agent-comparing | "Why NOT the alternatives?" |

Perspectives are **play-tested** by other agents (beta testing). A tile isn't "done" until a stranger agent can find it zero-shot.

### The Earmark Lifecycle

```
earmark-agentic-beta-test
        │ (3 consecutive beta test passes)
        ▼
field-validated
        │ (5 real-world retrievals)
        ▼
proven-retrievable (tag removed — tile is "done")
```

### Fleet Verification

`FleetVerifier` runs three verification methods:

1. **Structural** — tile has required fields, perspectives, consistent earmark
2. **Constraint** — E12 coordinate claims are mathematically valid
3. **Cross-model** — a DIFFERENT model than the author validates the content

Key difference from ACG: **ACG uses one verifier with one model. We use multiple methods with multiple models.** If any verifier contradicts, the tile is flagged.

### What We Stole from ACG

| Concept | Original ACG | Our Adaptation |
|---------|-------------|---------------|
| Claim markers `[Cn:SHI:LOC]` | Inline in output text | I2I bottles with claim-level granularity |
| Source Hash Identity (SHI) | `SHA256(uri\|version)` | Added to tile provenance for external refs |
| Reasoning taxonomy | CAUSAL/INFERENCE/SUMMARY/COMPARISON | `reasoning_type` tag on every tile |
| Separated verifier | One generator + one verifier | Fleet cross-verification with multiple models |
| VAR (audit registry) | JSON proof object | PLATO tiles with verification_status lifecycle |

### What We Do Better

| Aspect | ACG | Cocapn |
|--------|-----|--------|
| Location system | CSS selectors | E12 coordinates (mathematical, stable) |
| Causal ordering | Sequential IDs | Lamport clocks (distributed) |
| Claim lifecycle | VERIFIED/FAILED | Active/Superseded/Retracted |
| Fleet architecture | Single verifier | 9 agents, multi-model cross-verification |
| Crash recovery | MongoDB only | WAL + fsync |
| Demo requirements | MongoDB + API keys | Static HTML |
| Temporal reasoning | None | t_minus_event + Lamport clocks |
| Spatial organization | Flat | Eisenstein terrain |
| Compression | None | SplineLinear |
| Learning loop | One-shot | Collective inference (predict → observe → gap → learn) |

---

## 4. The Common Thread: Everything Becomes Tiles in Rooms

All three repos converge on a single architecture:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        THE TILE IS THE ATOM                        │
│                                                                     │
│   MCP Tool Call ──→ Tile ──→ PLATO Room                            │
│   CrewAI Task   ──→ Tile ──→ PLATO Room                            │
│   Code Function ──→ Tile ──→ .flux.fvt Index                       │
│   Agent Result  ──→ Tile ──→ PLATO Room                            │
│   Game Move     ──→ Tile ──→ PLATO Room                            │
│   Memory        ──→ Tile ──→ MemoryCrystal                         │
│   Verification  ──→ Tile ──→ VERIFICATION tile in crew room         │
│                                                                     │
│   The ROOM is the context. The TILE is the unit of work.            │
│   Everything else is infrastructure to create, find, and verify.    │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow Between the Three

```
                     ┌──────────────┐
                     │  PLATO MCP   │
                     │  (:8300)     │
                     └──────┬───────┘
                            │ read_tiles / write_tile / search_tiles
                            │
                    ┌───────┴────────┐
                    │  PLATO Server  │
                    │  (:8847)       │
                    └───────┬────────┘
                            │ rooms + tiles
                ┌───────────┼───────────┐
                │           │           │
        ┌───────┴──────┐    │    ┌──────┴───────┐
        │ flux-index   │    │    │ acg_protocol │
        │ (.flux.fvt)  │    │    │ (CrewAI)     │
        └──────┬───────┘    │    └──────┬───────┘
               │            │           │
    code tiles → vectors    │    crew tasks → tiles
    semantic search         │    fleet verification
                            │
                    ┌───────┴────────┐
                    │  Fleet Agents  │
                    │  FM / O1 / CCC │
                    └────────────────┘
```

**MCP** is the access layer. **Flux** is the search layer. **ACG** is the workflow layer. All three read and write the same PLATO tiles.

---

## 5. How the Hebbian Layer Would Enhance All Three

The Hebbian layer (proposed learning mechanism where co-activated tiles strengthen their connections) would amplify each component:

### 5.1 MCP Gets Smarter Routing

**Current:** `route_query` uses keyword heuristics or Fleet Router rules. Static.

**With Hebbian:**
- Track which tools agents call together (e.g., `read_tiles` → `write_tile` → `query_health`)
- Build co-activation patterns: "When an agent reads from room X, it usually writes to room Y next"
- **Predictive routing:** After `read_tiles("forge")`, suggest `write_tile("forge", ...)` as the likely next action
- **Tool clustering:** Agents that use conservation_check also use memory_remember — surface these together
- **Cost optimization:** Hebbian patterns reveal which routing decisions lead to good outcomes, reinforcing cheap routes

```
Agent calls route_query("compute Eisenstein norm")
  → Hebbian says: 87% of the time, this is followed by conservation_check
  → Pre-warm conservation module, suggest next tool
  → Agent saves a round-trip
```

### 5.2 Flux Gets Hebbian Search Ranking

**Current:** Pure cosine similarity + IDF weighting + test dampening. Static ranking.

**With Hebbian:**
- Track which tiles are retrieved together ("agents who found tile A also found tile B")
- Build a **co-retrieval graph** — tiles that appear in the same search sessions strengthen their connection
- **Search boosting:** When tile A is retrieved, boost tiles Hebbian-connected to A
- **Serendipity surfacing:** Tiles that are Hebbian-connected but not cosine-similar — these are "unexpected but relevant" discoveries
- **Relevance decay:** Tiles not retrieved recently have their Hebbian weights decay (use it or lose it)
- **CRDT relevance counter becomes Hebbian weight:** The G-Counter per tile in the CRDT layer already tracks retrieval frequency. Hebbian adds co-retrieval patterns ON TOP.

```
flux-index search "constraint theory verification"
  → Tile A (cosine: 0.82) 
  → Tile B (cosine: 0.74, but Hebbian: 0.91 — always co-retrieved with A)
  → Final ranking: B promoted above A due to Hebbian context
```

The CRDT layer's G-Counter is already half of this. Adding co-retrieval tracking gives us the other half.

### 5.3 ACG Gets Emergent Task Assignment

**Current:** Task-to-agent mapping is explicit in the CrewManifest. Forgemaster gets task 1, Oracle1 gets task 3. Static assignment.

**With Hebbian:**
- Track which agents succeed at which task types (FM is great at implementation, O1 is great at verification)
- Build **agent-task co-activation:** "When FM does constraint_check tasks, 94% success rate"
- **Emergent assignment:** Instead of hard-coding `agent="Forgemaster"` in task definitions, the bridge assigns based on Hebbian strength
- **Dynamic rebalancing:** If FM is overloaded, the Hebbian layer suggests the next-best agent for a task type
- **Skill discovery:** If a new agent consistently succeeds at verification tasks, its Hebbian weight for verification grows — the fleet discovers its strengths organically

```
Crew dispatches 10 tasks
  → Hebbian says: FM has 0.94 weight for "implementation" tasks
  → Hebbian says: O1 has 0.91 weight for "verification" tasks  
  → Hebbian says: CCC has 0.72 weight for "analysis" tasks
  → Bridge auto-assigns based on Hebbian weights, not manifest hard-coding
  → When FM is busy, next-best agent (Hebbian: 0.81) gets the task
```

### 5.4 Cross-Component Hebbian Effects

The real power: Hebbian patterns that span all three systems.

```
Agent calls MCP search_tiles("Eisenstein norm")
  → Finds tile via flux-index (Hebbian-boosted ranking)
  → Reads full tile content via MCP read_tiles
  → Writes verification result via MCP write_tile
  → ACG bridge notices the verification and assigns next task
  → Hebbian records: "search→read→write→verify" is a strong pattern
  → Next time: after search, pre-emptively suggest read+write+verify sequence
```

This creates **behavioral momentum** — the fleet learns its own workflows and optimizes them over time.

---

## 6. Integration Opportunities

### 6.1 Flux-Index as PLATO's Search Backend

**Current gap:** MCP's `search_tiles` is brute-force keyword scan. Slow, no ranking.

**Integration:** Point `search_tiles` at a flux-index instance that indexes PLATO rooms.

```python
# In server.py, replace tool_search_tiles:
async def tool_search_tiles(params: dict) -> list:
    # Instead of brute-force keyword scan:
    from flux_index.core import Index
    idx = Index()
    idx.load("/path/to/plato.flux.fvt")
    results = idx.search(params["query"], top_k=params.get("limit", 20))
    return [{"room_id": r.tile.metadata.get("room", ""),
             "question": r.tile.name,
             "answer": r.tile.content[:200],
             "score": r.score} for r in results]
```

This replaces O(N×M) keyword scan (N rooms × M tiles each) with O(log N) vector search.

### 6.2 ACG Crews Dispatched via MCP

**Current:** ACG bridge writes directly to PLATO via HTTP.

**Integration:** ACG uses MCP's `write_tile` tool to create crew rooms. Any MCP client can define and dispatch crews.

```python
# Via MCP client:
mcp.call("write_tile", {
    "room_id": f"crew-{uuid}",
    "domain": "workflow",
    "agent": "casey",
    "question": "CREW MANIFEST — Decompose tensor-spline",
    "answer": manifest_text,
    "tile_type": "manifest"
})
```

### 6.3 Flux-Index Indexes Crew Results

After a crew run completes, index the result tiles with flux-index:

```bash
flux-index /path/to/crew-results/
flux-index search "verification result for constraint check"
# Finds the exact tile from the crew run
```

### 6.4 Unified Search Across Code + Knowledge

```bash
flux-index search --all "how does tile verification work"
# Returns:
#   - fleet_verifier.py (code: 0.85)
#   - TILE-LABEL-SYSTEM.md (doc: 0.82)
#   - CREWAI-PLATO-BRIDGE.md (doc: 0.78)
#   - crew-a3f2 VERIFICATION tile (PLATO room: 0.76)
```

Code, docs, and PLATO knowledge in one search space.

---

## 7. Quantitative Summary

| Metric | plato-mcp | flux-index | acg_protocol |
|--------|-----------|------------|--------------|
| **LOC** | ~500 (server + cli) | ~900 (core + extractor + search + crdt) | ~800 (bridge + perspectives + verifier + beta_tester) |
| **Dependencies** | fastapi, uvicorn, httpx, pydantic | Zero (pure Python + optional C header) | requests |
| **External services** | PLATO server, Fleet Router | None | PLATO server |
| **Search speed** | N/A (keyword scan) | ~10ms Python, ~0.1ms C (14K tiles) | N/A (delegates to PLATO) |
| **Deployment** | Docker, pip | pip, CLI | pip, importable |
| **Tool count** | 10 MCP tools | 4 CLI commands (index, search, map, similar) | 4 modules (bridge, perspectives, verifier, beta_tester) |
| **Hebbian potential** | High (tool co-activation) | High (co-retrieval ranking) | High (agent-task success patterns) |

---

## 8. Conclusion

The interop layer is architecturally clean:

- **MCP** handles *access* — any framework can reach PLATO
- **Flux** handles *discovery* — any tile can be found semantically
- **ACG** handles *structure* — any workflow can be decomposed into rooms

The missing piece is **learning**. All three are stateless in their routing/ranking/assignment decisions. The Hebbian layer would add memory to these decisions — the fleet would learn from its own behavior patterns and improve over time.

But even without Hebbian, the interop layer achieves something significant: **PLATO becomes a first-class citizen in the agent ecosystem**. Any MCP client can use it. Any code can be searched. Any workflow can be decomposed. The tiles flow freely between all three layers.

---

*"The lattice doesn't care what framework you use. It just knows what tile belongs in what room."*
