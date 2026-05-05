Now I have enough context on both systems. Let me write the integration plan.

---

`★ Insight ─────────────────────────────────────`
The two systems have a natural layered fit: AutoData's OHCache is **working memory** (per-run hypergraph), PLATO is **long-term memory** (18K tiles, persistent). The Supervisor/Squad pattern maps cleanly onto Oracle1's role as fleet orchestrator. The hard parts are the I2I boundary (git-async vs LangGraph sync) and the Rust/Python boundary for CT.
`─────────────────────────────────────────────────`

---

# AutoData × Cocapn Fleet — Concrete Integration Plan

## Architecture Mapping

```
AutoData                          Fleet
─────────────────────────────     ─────────────────────────────────────
Supervisor (StateGraph)      ←──► Oracle1 / Steward (lifecycle mgr)
Research Squad               ←──► PLATO (tile query + submit)
  PlanAgent                  ──►  PLATO Lock (4-layer reasoning)
  ToolAgent                  ──►  PLATO Shell (sandboxed exec)
  BrowserAgent               ──►  Fleet Runner dashboard scrape
  BlueprintAgent             ──►  CT (blueprint = constraint graph)
Development Squad            ←──► ZeroClaw domain agents
  EngineerAgent              ──►  FLUX ISA generation
  TestAgent                  ──►  Arena (ELO eval)
  ValidationAgent            ──►  Grammar Engine (54-rule validation)
OHCache (hypergraph)         ──►  PLATO (persistence bridge)
Checkpoint system            ──►  I2I state snapshots
Plugin system (PluginSpec)   ──►  Fleet plugins (SonarVision, CT, FLUX)
```

---

## Answer to Each Integration Question

### Q1: OHCache vs PLATO

**Verdict: Complementary. OHCache = L1 cache, PLATO = L2 persistent store.**

OHCache is a session-scoped directed hypergraph over message nodes. PLATO tiles are persistent, scored, and queryable across sessions. Wire them as a two-layer memory stack:

- At **task start**: seed OHCache by querying PLATO rooms relevant to the task topic (`GET /room/{name}`)
- During **run**: agents read/write OHCache normally (no latency hit)
- At **task completion**: flush OHCache leaf-nodes to PLATO via `POST /submit`
- OHCache orientation edges (the "H" in hyperedge direction) encode tile lineage for PLATO's ELO/TrueSkill rating

### Q2: Plugin System Extension

**Verdict: Direct fit. PluginSpec already supports per-agent prompts + tools.**

Fleet plugins map cleanly:

| Plugin | Target Agent | Tools Added |
|---|---|---|
| `plato_plugin` | PlanAgent, BlueprintAgent | `plato_query`, `plato_submit`, `plato_pathfind` |
| `sonar_plugin` | ToolAgent, BrowserAgent | `sonar_infer`, `sonar_stream`, `mep_decode` |
| `ct_plugin` | EngineerAgent | `ct_snap`, `ct_quantize`, `flux_emit` |
| `arena_plugin` | ValidationAgent | `arena_submit`, `elo_rate`, `grammar_check` |

### Q3: Supervisor vs Oracle1/ZeroClaw

**Verdict: AutoData Supervisor wraps ZeroClaw, doesn't replace it.**

ZeroClaw agents are long-running fleet-native processes with domain state. AutoData Supervisor should treat them as **async tools** invoked over I2I, not subgraphs. The Supervisor dispatches a task, writes an I2I:REQUEST commit, polls via fleet Runner API for completion, then continues the graph. ZeroClaw prompting improves because AutoData's PlanAgent generates the task spec before dispatch.

### Q4: PLATO as Research Squad Data Source

**Verdict: Wire PLATO as a ToolAgent tool, not as graph state.**

Research Squad's ToolAgent gets `plato_query(room, depth)` and `plato_search(topic, k)`. BlueprintAgent gets `plato_blueprint(tile_ids)` to synthesize a task graph from tile content. PLATO's Pathfinder (port `:4051`) provides adjacency — use it for multi-hop tile traversal inside Research Squad.

### Q5: AutoData Checkpoints for Fleet State

**Verdict: Yes — use as I2I session state bridge.**

AutoData checkpoints (JSON snapshots of StateGraph thread state) are ideal for cross-session continuity. When a ZeroClaw agent suspends, serialize the active LangGraph thread to a checkpoint, commit it as `I2I:STATUS` to git. On resume, restore the checkpoint and the StateGraph continues exactly where it left off. This solves the current problem of fleet agents losing context between I2I sessions.

---

## Refactoring Plan

### What to Refactor in AutoData

| File/Module | Change | Reason |
|---|---|---|
| `ohcache/store.py` | Add `flush_to_plato(endpoint, session_token)` method | Persistence bridge |
| `ohcache/store.py` | Add `seed_from_plato(room_name, depth)` at graph init | Context hydration |
| `supervisor/graph.py` | Add `i2i_dispatch_node` as a graph node between squads | ZeroClaw bridge |
| `supervisor/graph.py` | Add `i2i_poll_node` with configurable timeout | Async await pattern |
| `checkpoints/` | Add `to_i2i_payload()` / `from_i2i_payload()` serializers | Fleet-native format |
| `plugins/registry.py` | Register fleet plugins on init if `FLEET_MODE=true` | Conditional loading |

### What to Refactor in Fleet Systems

| System | File | Change |
|---|---|---|
| **ZeroClaw** | agent prompts | Replace free-form task strings with AutoData PlanAgent output (structured JSON spec) |
| **Fleet Guard** | `fleet-guard-v2.py` | Add `AutoDataSession` monitor: alert if LangGraph thread stalls |
| **Oracle1** | I2I handler | Recognize `I2I:CHECKPOINT` type; store in `/state/sessions/` |
| **SonarVision** | `integrations/dashboard/` | Expose WebSocket URL to `sonar_plugin` tool registry |
| **CT demo** | `ct-demo/src/` | Expose `snap()` and `quantize()` as a thin HTTP endpoint for `ct_plugin` |

### New Modules / Files Needed

```
autodata-fleet/
├── plugins/
│   ├── plato_plugin.py          # PluginSpec: plato_query, plato_submit, pathfind
│   ├── sonar_plugin.py          # PluginSpec: sonar_infer, mep_decode, stream
│   ├── ct_plugin.py             # PluginSpec: ct_snap, ct_quantize, flux_emit
│   └── arena_plugin.py          # PluginSpec: arena_submit, elo_rate, grammar_check
├── bridges/
│   ├── i2i_bridge.py            # I2I commit writer/reader (wraps git subprocess)
│   ├── plato_client.py          # HTTP client: rooms/:8847, pathfinder/:4051, submit
│   └── fleet_runner_client.py   # Poll fleet-runner/:8899 for agent status
├── ohcache/
│   └── plato_sync.py            # flush_to_plato / seed_from_plato logic
└── checkpoints/
    └── i2i_serializer.py        # Checkpoint ↔ I2I:CHECKPOINT payload
```

---

## Dependency Ordering

Dependencies flow in this order — don't start step N until step N-1 is importable/tested:

```
1. plato_client.py          (no fleet deps, just HTTP)
         │
2. plato_plugin.py          (depends on plato_client)
         │
3. ohcache/plato_sync.py    (depends on plato_client + OHCache internals)
         │
4. i2i_bridge.py            (git subprocess + I2I format, no LangGraph dep)
         │
5. i2i_serializer.py        (depends on AutoData checkpoint format + i2i_bridge)
         │
6. arena_plugin.py          (depends on plato_client for grammar endpoint)
         │
7. ct HTTP endpoint         (Rust side: thin axum wrapper around ct_snap/quantize)
         │
8. ct_plugin.py             (depends on ct HTTP endpoint)
         │
9. sonar_plugin.py          (depends on sonar-vision WebSocket URL)
         │
10. supervisor i2i nodes    (depends on i2i_bridge + all plugins registered)
```

---

## 5 Specific First Actions

**Action 1 — Wire `plato_client.py` (1–2 hours)**
Write a minimal async HTTP client against PLATO `:8847` (rooms) and `:4042` (submit). Test with `GET /rooms` and a single test tile submission. This is the foundation everything else needs. No LangGraph, no AutoData — pure `httpx` against the live Oracle endpoint.

**Action 2 — Validate OHCache → PLATO flush semantics (2–3 hours)**
Read AutoData's OHCache internals. Determine what a "leaf node" is in the hypergraph. Write `plato_sync.py::flush_to_plato()` that converts a completed OHCache subgraph into the PLATO tile POST body. Run one AutoData task end-to-end and confirm a tile appears in PLATO.

**Action 3 — Build `ct_plugin` HTTP shim in Rust (2–3 hours)**
Add a minimal `axum` route to `ct-demo` exposing `POST /snap` and `POST /quantize`. Body: `{vector: [f64]}`, response: `{snapped: [f64], pythagorean_triple: [i64, i64, i64]}`. This unblocks EngineerAgent from calling CT without FFI.

**Action 4 — Register `sonar_plugin` against live SonarVision WebSocket (1–2 hours)**
`sonar-telemetry-stream.py` already broadcasts frames. Write `sonar_plugin.py` PluginSpec with `sonar_stream(duration_ms)` that opens the WS, collects N frames, and returns structured telemetry. Wire into ToolAgent's tool registry. Test with a simulated sensor frame.

**Action 5 — Implement `I2I:CHECKPOINT` type in Oracle1 handler (2–3 hours)**
Add `CHECKPOINT` to the I2I message type enum. Write `i2i_bridge.py::write_checkpoint(thread_id, state_json)` that commits a checkpoint to the fleet repo as `state/sessions/{thread_id}.json`. Write `read_checkpoint(thread_id)` that fetches it. Test round-trip with a toy LangGraph StateGraph. This unblocks all ZeroClaw session persistence.

---

## Risk Register

| Risk | Severity | Mitigation |
|---|---|---|
| I2I latency (git commit round-trip) is too slow for LangGraph's sync nodes | High | Use `i2i_dispatch_node` as a background edge with a 30s poll; don't block the main graph |
| PLATO tile schema mismatch with OHCache node shape | Medium | Write a schema validation step in `plato_sync.py` before flush; log mismatches |
| CT Rust shim adds build dependency to a Python pipeline | Medium | Ship as a Docker sidecar; `ct_plugin` hits `localhost:7788`, no Rust toolchain needed in AutoData env |
| ZeroClaw prompt injection via AutoData PlanAgent output | Medium | Sanitize PlanAgent structured output through Grammar Engine before I2I dispatch |
| OHCache session memory grows unbounded for long Research Squad runs | Low | Add `max_nodes` cap to OHCache; flush intermediate nodes to PLATO at 80% capacity |
