# MUD-MCP Protocol Pattern: Room → MCP Mapping

Extracted from: `Nexlen/mud-mcp` (MCP spec 2025-03-26)

---

## Core Insight

MUD-MCP treats a MUD room as a **stateful MCP context**. The room is not just a description — it's a live filter that determines which MCP primitives (tools, prompts, resources) are currently visible to the LLM client.

The central pattern: **room state drives surface area**.

---

## The Three-Layer Surface

MCP exposes three primitive types to clients. MUD-MCP maps each to a distinct role:

```
MCP Layer    │ MUD Role              │ Who Controls
─────────────┼───────────────────────┼─────────────────
Tools        │ Actions (state-mut.)  │ Model-controlled
Prompts      │ State representation  │ User-controlled
Resources    │ World data (readable) │ Client/LLM reads
```

### Tools = Actions

- Model-controlled: the LLM decides when to invoke
- Require user approval before execution (by convention)
- **Dynamically appear/disappear based on room state**
- Each has a JSON Schema `inputSchema` and MCP `annotations`

```
Always available:  look, inventory
Contextual:        move      (only if room has exits)
                   take      (only if room has items)
                   battle    (only if room.monsters.length > 0)
                   talk      (only if sampling capability present)
```

### Prompts = State Representation

- User-controlled: the user/agent explicitly invokes them
- Present the current game state as formatted messages
- **Also filter by room context**:
  - `room_description` — always available
  - `quest_prompt` — only if `room.hasQuest && !player.hasQuest`
  - `battle_prompt` — only if `room.monsters.length > 0`

### Resources = World Data

URIs follow `mud://` or `game://` scheme:
```
game://player/state    → JSON: player location, inventory, flags
game://world/map       → JSON: all rooms + connections
game://room/current    → JSON: current room data
mud://help             → text: game guide
```

Resources support subscriptions (`subscribe: true`) for real-time updates.

---

## The Room State Model

```typescript
PlayerState = {
  player_id: string,
  room: string,          // current room ID
  inventory: string[],   // item IDs
  hasQuest: boolean,
  monsterPresent: boolean
}

Room = {
  id: string,
  name: string,
  description: string,
  exits: { [direction]: roomId },
  items: string[],       // item IDs present in room
  monsters: string[],    // monster IDs
  hasQuest: boolean
}
```

State mutations emit `TOOLS_CHANGED` and `PROMPTS_CHANGED` events, which trigger MCP notifications to clients.

---

## How Room→MCP Mapping Works (Code Flow)

```
1. Player performs action (tool call)
   └─ stateService.mutateState()
      ├─ updates PlayerState / Room
      └─ emits 'TOOLS_CHANGED' or 'PROMPTS_CHANGED'

2. McpServer event listener catches emission
   └─ notifyToolsChanged(playerId)
      ├─ calls toolsService.getAvailableTools(playerId)
      ├─ filters tools by room contents
      └─ sends notifications/tools/list_changed  →  client

3. Client (LLM) receives notification
   └─ re-fetches tools/list
      └─ sees updated tool set matching new room context
```

The filtering logic in `toolsService.getAvailableTools()`:
```typescript
// Room-contextual tool availability
if (Object.keys(room.exits).length > 0)   → include 'move'
if (room.items.length > 0)                → include 'take'
if (room.monsters.length > 0)             → include 'battle'
if (samplingService.isAvailable())        → include 'talk'
```

---

## MCP Notifications Pattern

Three notification types used reactively:

```json
// Tool set changed (most frequent)
{ "jsonrpc": "2.0", "method": "notifications/tools/list_changed" }

// Prompt set changed (on quest/battle state change)
{ "jsonrpc": "2.0", "method": "notifications/prompts/list_changed" }

// Resource updated (on inventory / map change)
{ "jsonrpc": "2.0", "method": "notifications/resources/updated",
  "params": { "uri": "game://player/state" } }
```

**Key protocol detail**: Per MCP spec discussion (referenced in code), `notifications/tools/list_changed` *can* include the new tool list in `params.tools` as an optimization — avoiding a round-trip `tools/list` call.

---

## Sampling Integration (Reverse Flow)

MUD-MCP demonstrates the **server-initiates sampling** pattern:

```
1. Server receives 'initialized' notification from client
2. Server checks client capabilities for 'sampling'
3. If supported: server registers a handler that can SEND
   sampling/createMessage requests back to the client
4. When talk tool invoked:
   └─ samplingService.generateNPCDialogue()
      └─ sends sampling/createMessage to client
         ├─ systemPrompt: NPC character + game context
         ├─ includeContext: 'thisServer' (shares game state)
         └─ returns AI-generated dialogue

Fallback: if sampling unavailable, talk tool is not exposed at all
```

This is a bidirectional pattern — the MCP server can request AI inference from the client, not just serve data.

---

## Session / Multi-Player Architecture

MUD-MCP is built for single-session stdio but has the scaffolding for multi-player:

- `stateService` maintains `Map<sessionId, Session>` and `Map<playerId, PlayerState>`
- Session created on `initialize`, thread-safe per stdio connection
- `playerId` is passed into every tool/prompt handler via `context.sessionId`
- Current implementation defaults `sessionId = 'session_1234'` (TODO: unique IDs)

For multi-player: each MCP client connection would get an independent session and see only tools/prompts filtered for their own room position.

---

## Tool Annotation Pattern (MCP 2025-03-26)

Each tool carries semantic hints to guide LLM behavior:

```typescript
annotations: {
  title: string,           // human-readable name
  readOnlyHint: boolean,   // safe to call without user approval
  destructiveHint: boolean, // may delete/damage things
  idempotentHint: boolean,  // calling twice = same result
  openWorldHint: boolean    // may have external side effects
}
```

Examples from the codebase:
- `look`:      readOnly=true,  idempotent=true  — always safe
- `move`:      readOnly=false, destructive=false — changes location
- `battle`:    readOnly=false, destructive=true  — may kill monster
- `talk`:      readOnly=false, openWorld=true    — calls external AI

---

## Prompt-as-System-Prompt Pattern

Prompts in MUD-MCP return `messages[]` arrays — they are effectively **system prompt fragments** the user or LLM selects to inject into context:

```json
{
  "messages": [
    {
      "role": "assistant",
      "content": {
        "type": "text",
        "text": "You are in Dark Hallway.\n\nThe walls are lined with ancient tapestries..."
      }
    }
  ]
}
```

This is the canonical MCP pattern for "contextual system prompt injection" — rather than a static system prompt, the room description prompt is fetched fresh on each prompt invocation, always reflecting current state.

---

## Extractable Components

The following are standalone patterns extractable from this codebase:

| Component | Source File | Reuse Pattern |
|-----------|-------------|---------------|
| State→Tool filter | `services/toolsService.ts:64-108` | Any stateful tool gating |
| State→Prompt filter | `services/promptsService.ts:44-88` | Context-sensitive prompt sets |
| Sampling service | `services/samplingService.ts` | LLM↔LLM mediation via MCP |
| Event-driven notifications | `mcp/server.ts:49-57` | EventEmitter → MCP notify |
| Tool annotation schema | `services/toolsService.ts:583-677` | Tool metadata for clients |
| Session/player state | `services/stateService.ts` | Multi-player session tracking |
| Transport adapter | `mcp/transport-adapter.ts` | Stdio↔HTTP abstraction |
