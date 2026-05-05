# AutoData × Cocapn Fleet Integration Analysis

> Forgemaster ⚒️ — 2026-05-02 Night Shift

## What AutoData Brings

**AutoData is a LangGraph-based multi-agent orchestration framework** (NeurIPS 2025) with:

1. **Supervisor-Squad Architecture** — Supervisor routes tasks to Research Squad (Plan, Tool, Browser, Blueprint agents) or Development Squad (Engineer, Test, Validation agents)
2. **OHCache (Oriented Message Hypergraph)** — Structured inter-agent context management. Hyperedges define message flow between agent groups. Cache system for artifact reuse.
3. **Plugin System** — `PluginSpec` with agent-specific prompt injections + LangChain tools
4. **Checkpoint System** — Resumable runs with state serialization
5. **Browser Automation** — Playwright/Selenium for web data collection

## Integration Mapping

### OHCache ↔ PLATO

| OHCache Concept | PLATO Equivalent | Integration |
|----------------|-----------------|-------------|
| CacheEntry (key/value + metadata) | Tile (question/answer + tags) | OHCache entries can be synced to PLATO rooms |
| OrientedHyperedge (source→target routing) | I2I bottles (agent→agent delivery) | OHCache routing replaces git-based I2I for real-time |
| LocalCacheSystem (artifact storage) | PLATO rooms (knowledge storage) | OHCache = hot cache, PLATO = persistent store |
| hypergraph_stats() | PLATO /status | Unified metrics |

**Key Insight:** OHCache is the **hot path** (intra-session, in-memory). PLATO is the **cold path** (cross-session, persistent). They're complementary, not competing.

### AutoData Agents ↔ Fleet Agents

| AutoData Agent | Fleet Role | Notes |
|---------------|-----------|-------|
| Supervisor | Oracle1 (fleet coordinator) | Supervisor pattern is cleaner than Oracle1's current ad-hoc routing |
| PlanAgent | Forgemaster (strategic planning) | Planning with PLATO context injection |
| ToolAgent | OpenCode/Droid (tool execution) | Already have tools, need AutoData's tool registry |
| BrowserAgent | Browser automation skill | OpenClaw already has browser-automation skill |
| BlueprintAgent | Forgemaster (architecture docs) | Blueprint generation = Forgemaster's design docs |
| EngineerAgent | OpenCode/Kimi (code writing) | Fleet already has coding agents |
| TestAgent | CI/CD + manual testing | Need automated test validation |
| ValidationAgent | Quality gate | PLATO quality checks (phi, integration scores) |

### Plugin System ↔ Fleet Extensions

AutoData's plugin system is exactly what ZeroClaw needs:

```python
# Current ZeroClaw: agents run blind, no domain context
# AutoData plugin: inject prompts + tools per agent

PluginSpec(
    name="sonar-vision",
    prompts={
        "PlanAgent": "Use SonarVision for underwater physics queries...",
        "EngineerAgent": "Validate physics constraints with CT solver..."
    },
    tool_classes=(SonarVisionTool, ConstraintTheoryTool)
)
```

This **solves the ZeroClaw hallucination problem** — domain context is injected via plugins.

## Refactoring Plan

### Phase 1: Fleet Plugin for AutoData (Now)

Create `autodata/plugins/fleet.py` with:
- `FleetKnowledgeTool` — queries PLATO rooms for context
- `ConstraintTheoryTool` — calls CT solver for validation
- `SonarVisionTool` — queries underwater physics
- Prompt injections for PlanAgent, EngineerAgent, ValidationAgent

### Phase 2: PLATO-OHCache Bridge

Create `autodata/core/ohcache/plato_bridge.py`:
- OHCache → PLATO sync: when agent produces artifact, write to PLATO room
- PLATO → OHCache: when agent starts, preload relevant PLATO tiles into OHCache
- Hot/cold tiering: OHCache for session artifacts, PLATO for persistent knowledge

### Phase 3: Supervisor as Fleet Coordinator

Refactor Oracle1's coordination to use AutoData's Supervisor pattern:
- Replace ad-hoc ZeroClaw scheduling with LangGraph StateGraph
- OHCache hyperedges define message flow between fleet agents
- Checkpoint system for resumable fleet tasks

### Phase 4: BrowserAgent + SonarVision

Wire AutoData's BrowserAgent to SonarVision's web API:
- BrowserAgent can navigate to oceanographic data sources
- SonarVision validates collected data against physics constraints
- CT solver ensures collected data satisfies physical relationships

### Phase 5: Fleet Dashboard Integration

- AutoData checkpoint state → fleet dashboard
- OHCache hypergraph visualization → dashboard panel
- Agent performance metrics from AutoData → dashboard metrics

## 5 First Actions (Ranked)

1. **Create fleet plugin** (`autodata/plugins/fleet.py`) — immediate value, unblocks testing
2. **Wire PLATO as OHCache cold store** — persistent knowledge for AutoData agents
3. **Refactor ZeroClaw to use AutoData plugin pattern** — fixes hallucination bug
4. **Add fleet config to default.yaml** — enables AutoData with fleet context
5. **Write PLATO tiles about AutoData** — knowledge preservation for fleet

## Dependency Order

```
#1 (fleet plugin)
    └─→ #2 (PLATO-OHCache bridge — needs plugin tools)
         └─→ #3 (ZeroClaw refactor — needs bridge working)
              └─→ #4 (config — needs agents refactored)
                   └─→ #5 (tiles — document what we built)
```
