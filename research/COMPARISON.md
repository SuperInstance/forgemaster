# MUD-MCP vs PLATO Rooms: Comparison and Integration Recommendations

Forgemaster R&D — April 2026

---

## Executive Summary

MUD-MCP and PLATO rooms solve overlapping but distinct problems. MUD-MCP is a **reactive MCP surface layer** — it makes a stateful environment navigable by LLMs via dynamic tool/prompt exposure. PLATO rooms are a **persistent coordination substrate** — they provide multi-agent collaboration via a shared git-backed YAML world. They are complementary, not competing.

**Core recommendation**: Adopt MUD-MCP's room→tool/prompt filtering pattern as the MCP interface layer on top of PLATO rooms. PLATO provides the persistence and multi-agent coordination; MUD-MCP provides the reactive LLM surface.

---

## Side-by-Side Architecture

| Dimension | MUD-MCP | PLATO Rooms |
|-----------|---------|-------------|
| **Storage** | In-memory (TypeScript Maps) | YAML files in git tree |
| **Persistence** | Session-scoped, ephemeral | Full git history |
| **Transport** | stdio / HTTP+SSE | File watcher / git hooks / HTTP API / cron |
| **Protocol** | MCP 2025-03-26 (JSON-RPC) | Custom YAML command files |
| **Reactivity** | Push notifications (tools_changed) | Pull-based / event-triggered |
| **Multi-agent** | Scaffolded but single-session | Native (multiple agents write commands) |
| **World model** | Rooms with exits, items, monsters | Rooms with experts, tiles, logs |
| **Agent role** | LLM navigates via MCP tools | Agent writes YAML, reads YAML |
| **State mutation** | Tool calls → stateService | YAML write → engine processes |
| **LLM access** | Direct (MCP client IS the LLM) | Indirect (agent wraps LLM calls) |

---

## How Each System Represents Rooms

### MUD-MCP Room

```typescript
Room = {
  id: "chamber",
  name: "Ancient Chamber",
  description: "Pillars carved with runes...",
  exits: { west: "hallway", north: "treasure_room" },
  items: ["potion"],
  monsters: ["goblin"],
  hasQuest: false
}
```

Room state is **pure runtime state** — no persistence, no history. A room's state is whatever the last tool call left it in.

### PLATO Room

```
world/
  commands/   ← agents write YAML here (input)
  rooms/      ← engine writes state here (output)
  experts/    ← domain knowledge per expert
  logs/       ← turn history
  tiles/      ← accumulated knowledge units
```

Room state is **persistent and versioned** — git commits are the record. The engine is a Python process that reads commands and writes state, decoupled from any transport.

### Key Structural Difference

MUD-MCP rooms are **presentational** (what an LLM perceives *right now*). PLATO rooms are **operational** (what agents have done and accumulated *over time*). PLATO rooms lack any notion of reactive surface-area — the LLM doesn't get notified when new tiles appear or experts change.

---

## What MUD-MCP Does That PLATO Lacks

### 1. Reactive Tool/Prompt Surface

MUD-MCP's most valuable pattern: available tools and prompts change *in response to world state*. When an agent moves into a room with a monster, the `battle` tool appears. When they clear the room, it disappears. Clients are *notified* of this change.

PLATO has no equivalent. An agent must manually check what commands are valid (or assume all are always valid). There is no signal to the LLM that "the available actions have changed."

**Adoption path**: Implement a PLATO-MCP bridge that reads `world/rooms/*.yaml` and exposes a dynamic tool set based on room contents. When the YAML changes (via file watcher or git hook), send `notifications/tools/list_changed`.

### 2. MCP Protocol Compliance

PLATO rooms speak YAML files. No MCP client (Claude Desktop, VS Code Agent Mode, any IDE) can connect to a PLATO room natively. MUD-MCP is a reference implementation of the full MCP 2025-03-26 spec including:
- Proper JSON Schema `inputSchema` on all tools
- Tool `annotations` for LLM guidance (readOnly, destructive, idempotent)
- `prompts/list` and `prompts/get` with argument schemas
- Resources with `subscribe` and `listChanged`

**Adoption path**: Use MUD-MCP as the MCP server skeleton, replace the in-memory state backend with reads/writes to a PLATO room directory.

### 3. Sampling (Server→Client AI Requests)

MUD-MCP demonstrates the `sampling/createMessage` flow where the **server** requests LLM inference from the **client**. The `talk` tool only appears when the connected client declares sampling capability, then the server sends AI requests back through the same connection.

PLATO has no equivalent — all LLM calls are agent-initiated. The room itself cannot ask for AI help.

**Adoption path for PLATO**: A PLATO-MCP bridge could expose a `consult_oracle` tool (only available when sampling is supported) that lets the room request AI synthesis of accumulated tiles.

### 4. Prompt-as-State-Snapshot

MUD-MCP prompts return formatted `messages[]` that snapshot current room state. Crucially, these are user-invoked — the LLM or user explicitly asks "give me the room description", and the answer reflects current game state.

PLATO currently surfaces state only via raw YAML files. A human or LLM reading `world/rooms/study.yaml` must parse YAML and construct their own representation.

**Adoption path**: Create PLATO room prompts (`expert_summary`, `tile_digest`, `mission_status`) that format current YAML state into readable MCP messages.

---

## What PLATO Does That MUD-MCP Lacks

### 1. True Persistence

MUD-MCP loses all state on server restart. There is no checkpointing, save-game, or history. PLATO rooms have full git history — every command, every turn, every tile, with timestamps and authorship.

For fleet operations (ZeroClaws missions, long-running research), this is critical. MUD-MCP's in-memory model is appropriate for short game sessions, not multi-week research missions.

### 2. Multi-Agent Coordination

Multiple agents can write to the same PLATO room simultaneously (or in turn). The engine processes commands in sequence and maintains consistent state. MUD-MCP's `stateService` is a single-session singleton — there's a hardcoded `session_id = 'session_1234'` TODO in the code.

The ZeroClaws bridge pattern (Helmsman/Tactician/Lookout writing to shared rooms) has no equivalent in MUD-MCP.

### 3. Transport Flexibility

PLATO runs five ways (file watcher, bare git, cron, HTTP, GitHub Actions). MUD-MCP supports stdio and HTTP+SSE but is tightly coupled to the MCP protocol transport. You cannot use a PLATO room without MCP tooling.

PLATO's YAML interface means any agent that can write files can participate — shell scripts, Python, Rust binaries, ESP32 devices.

### 4. Domain-Specific Knowledge (Tiles)

PLATO tiles are structured knowledge units that accumulate across missions. They have instruction/input/output/metadata format useful for fine-tuning, evaluation, and cross-room synthesis. MUD-MCP has no equivalent knowledge accumulation — game state is volatile.

---

## Integration Recommendations

### Recommendation 1: PLATO-MCP Bridge (High Value)

**Build a thin MCP server that wraps a PLATO room directory.**

```
plato-mcp-bridge/
  ├── server.ts         ← MCP server (adapts MUD-MCP's McpServer)
  ├── room-watcher.ts   ← inotify / fs.watch on world/rooms/*.yaml
  └── command-writer.ts ← writes tool calls as YAML to world/commands/
```

How it works:
1. On startup, read `world/rooms/*.yaml` → build initial tool set
2. Expose tools matching room commands (e.g., `journal`, `question`, `tile`)
3. File watcher detects changes to `world/rooms/` → send `notifications/tools/list_changed`
4. Tool calls write YAML to `world/commands/` (same as current agent workflow)
5. Room description prompt reads and formats `world/rooms/study.yaml`

This preserves PLATO's full persistence and multi-agent model while adding MCP-native access for Claude Desktop, VS Code Agent Mode, etc.

**Adopt directly from MUD-MCP**:
- `McpServer` class (`mcp/server.ts`) — the MCP protocol handler
- Tool annotation pattern (`toolsService.ts:583-677`) — tool schema + hints
- Notification emit pattern (`mcp/server.ts:49-57`) — EventEmitter → MCP notify
- Transport adapter (`mcp/transport-adapter.ts`) — stdio wrapping

**Reimplement for PLATO**:
- `stateService` → reads YAML files instead of in-memory state
- `toolsService.getAvailableTools()` → derives from room YAML, not game state
- `promptsService` → formats YAML state as MCP messages

### Recommendation 2: Adopt Tool Annotation Schema

Use MUD-MCP's `annotations` pattern for all PLATO room commands exposed as MCP tools:

```typescript
// Example: PLATO journal command as annotated MCP tool
{
  name: 'journal',
  description: 'Write a finding to the expert journal',
  inputSchema: {
    type: 'object',
    properties: {
      expert_id: { type: 'string', description: 'Which expert is writing' },
      type: { type: 'string', enum: ['finding', 'question', 'hypothesis'] },
      content: { type: 'string', description: 'The journal entry content' }
    },
    required: ['expert_id', 'type', 'content']
  },
  annotations: {
    title: 'Write Journal Entry',
    readOnlyHint: false,
    destructiveHint: false,
    idempotentHint: false,
    openWorldHint: false
  }
}
```

### Recommendation 3: Room-Contextual Prompt Set

Implement PLATO-specific prompts following MUD-MCP's filtering pattern:

| Prompt | Show When |
|--------|-----------|
| `room_status` | Always — formats current `world/rooms/*.yaml` |
| `expert_briefing` | Always — lists active experts and their focus |
| `tile_digest` | When `world/tiles/*.json` count > 0 |
| `mission_status` | Always — overall mission progress |
| `blocking_question` | When unresolved questions exist in logs |

These replace the current pattern where agents must manually parse YAML state before knowing what to do.

### Recommendation 4: Adopt Sampling for Oracle Consultation

For ZeroClaws-pattern missions, add a `consult_oracle` tool (sampling-gated) that:
1. Reads all tiles from `world/tiles/`
2. Bundles them into a sampling request context
3. Sends `sampling/createMessage` to the connected LLM client
4. Returns synthesized guidance as a tile written to `world/tiles/oracle/`

This makes the Lookout pattern available interactively, not just as a scheduled agent pass.

### Recommendation 5: Components to Extract as Standalone Crates/Packages

If formalizing into reusable libraries:

| Component | What It Does | Target Form |
|-----------|--------------|-------------|
| `plato-mcp-bridge` | YAML room → MCP surface | npm package / Rust crate |
| `tool-filter` | State → available tool set | Generic fn: `(state: T, rules: Rule<T>[]) => Tool[]` |
| `sampling-service` | Server-initiated LLM calls | Standalone MCP sampling client |
| `plato-room-client` | Read/write PLATO YAML rooms | Python + Rust + TS versions |
| `mcp-notification-emitter` | EventEmitter → MCP notifications | Adapter pattern |

---

## What NOT to Adopt

### MUD-MCP's In-Memory State

The `stateService` using `Map<string, PlayerState>` is fine for a game demo but inappropriate for fleet agents. Don't port this — replace it entirely with PLATO's YAML-backed state.

### MUD-MCP's Single-Session Architecture

The hardcoded `session_1234` and single-player assumptions won't scale to ZeroClaws-pattern multi-agent rooms. The multi-session architecture in MUD-MCP is skeletal (Maps exist but ID generation is broken). Design fresh for multi-agent from the start.

### MUD-MCP's World Definition (TypeScript Config)

PLATO's YAML world files are more portable and readable than MUD-MCP's `config/world.ts`. Keep YAML as the canonical room format.

---

## Alignment with ZeroClaws Bridge Pattern

The ZeroClaws bridge (Helmsman → Tactician → Lookout) maps cleanly to the MUD-MCP tool pattern:

```
MUD-MCP concept          ZeroClaws equivalent
─────────────────────    ─────────────────────────────────
Room                   = Station (PTX room, Chess Dojo, Bridge)
Tool (battle)          = Command (journal finding, play games)
Dynamic tool filter    = Station role filter (Helmsman can't use chess tools)
Prompt (room_desc)     = Station briefing (current tiles + context)
Sampling (talk)        = Oracle consultation (cross-station synthesis)
Resource (world/map)   = PLATO tile store (world/tiles/*.json)
```

The MCP protocol would let Claude Desktop or VS Code connect directly to a ZeroClaws station room and interact via its native command vocabulary — no custom telnet/CLI required.

---

## Recommended Implementation Order

1. **PROTOCOL.md understanding** — done (this session)
2. **plato-mcp-bridge skeleton** — port `McpServer` + `TransportAdapter` from MUD-MCP, stub state backend
3. **YAML-backed stateService** — reads `world/rooms/*.yaml`, no in-memory state
4. **Dynamic tool registration** — derive available tools from room YAML contents
5. **File watcher notifications** — `inotify` on `world/` → `notifications/tools/list_changed`
6. **PLATO prompts** — `room_status`, `tile_digest`, `expert_briefing`
7. **Sampling oracle** — `consult_oracle` tool for Lookout synthesis
8. **Multi-session** — proper session IDs, per-connection player state

Steps 2-4 are the core value. Steps 5-8 are enhancements.
