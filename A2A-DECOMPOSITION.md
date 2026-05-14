# A2A Protocol Decomposition — Google Agent-to-Agent

> **Original:** [a2aproject/A2A](https://github.com/a2aproject/A2A) by Google  
> **Stars:** 23,776 | **License:** Apache 2.0 | **Stack:** Protobuf + JSON-RPC + SSE  
> **What:** Open standard for inter-agent communication. 3-layer architecture: Data Model → Operations → Protocol Bindings.

## 1. What A2A Actually Is

Google's answer to "how do AI agents talk to each other?" It's a protocol, not a framework. No agent runtime — just a spec for how opaque agent systems discover each other, negotiate capabilities, and collaborate on tasks without sharing internal state.

**Three layers:**
- **Data Model** (protobuf): Task, Message, Part, Artifact, AgentCard
- **Operations**: Send Message, Stream Message, Get/List/Cancel Task, Get Agent Card
- **Bindings**: JSON-RPC 2.0, gRPC, HTTP/REST (pluggable)

**Key idea:** Agents are opaque black boxes. You don't get their memory, tools, or reasoning. You get their **Agent Card** (capabilities) and interact via **Tasks** (stateful work units with lifecycle).

## 2. What's Insightful (Steal These)

### 2.1 🏆 Agent Card — Self-Describing Agents

```json
{
  "name": "Forgemaster",
  "description": "Constraint-theory specialist for Cocapn fleet",
  "url": "http://147.224.38.131:8847/a2a",
  "skills": [
    {"id": "constraint-verify", "name": "Constraint Verification"},
    {"id": "e12-snap", "name": "Eisenstein Snap Calculation"}
  ],
  "capabilities": {"streaming": true, "pushNotifications": true}
}
```

**Why it's brilliant:** Zero-config discovery. An agent shows up, publishes its card, and any other agent can immediately know what it does and how to talk to it. No registry, no orchestrator, no central authority.

**What we should take:** Every fleet agent should publish an Agent Card. Our PLATO rooms already store agent metadata — add a `/agent-card` endpoint to PLATO that returns the A2A format. Other fleets could discover our agents.

### 2.2 🏆 Task Lifecycle — Stateful Work Units

```
submitted → working → completed
                     → failed
                     → canceled
                     → rejected
          → input-required (human-in-loop)
```

**Why it's good:** Tasks have STATE. Not just "done/not done" — they track the full lifecycle. Long-running tasks get streaming updates. Human-in-the-loop is first-class.

**What we should take:** PLATO tiles already have lifecycle (Active/Superseded/Retracted). A2A's Task lifecycle is different — it's about work-in-progress, not knowledge states. We need BOTH:
- **Tile lifecycle** = knowledge state (is this claim still valid?)
- **Task lifecycle** = work state (is Forgemaster still crunching on this?)

### 2.3 🏆 Part — Universal Content Container

```protobuf
message Part {
  oneof content {
    string text = 1;
    bytes raw = 2;
    string url = 3;
    google.protobuf.Struct data = 4;
  }
  string media_type = 5;
  string filename = 6;
  map<string, string> metadata = 7;
}
```

**Why it's good:** One container for EVERYTHING. Text, files, URLs, structured data. The `oneof` means each Part is exactly one type, no ambiguity.

**What we should take:** PLATO tile content is currently unstructured text. Adding a Part-like structure would let tiles contain:
- Text claims (current behavior)
- File references (link to datasets, models)
- Structured data (JSON benchmarks, test results)
- URLs (external sources with SHI)

### 2.4 🏆 Push Notifications for Long-Running Tasks

When a task takes hours (training a model, running fleet verification), the agent pushes updates to a webhook instead of requiring polling.

**What we should take:** Our fleet already has Matrix for real-time comms. But Matrix is casual/unverified. A push notification system for tile verification would be the formal channel: "Tile X verified by Oracle1" → push to all subscribers.

### 2.5 🏆 Context ID — Logical Task Grouping

`contextId` groups related tasks without enforcing parent/child. Multiple tasks can share a context.

**What we should take:** Our PLATO rooms are the grouping mechanism, but rooms are static. A contextId is dynamic — "all tasks related to the PBFT integration" could span multiple rooms. We need both.

## 3. What We Already Do Better

| Aspect | A2A | Cocapn/PLATO |
|--------|-----|-------------|
| Agent identity | Agent Card (static JSON) | Agent Card + PLATO rooms + git identity (multi-layer) |
| Knowledge storage | None — agents keep their own | PLATO tiles with content addressing + Lamport clocks |
| Verification | None | Constraint theory proofs + fleet cross-verification |
| Content location | URL references | E12 coordinates + SHI |
| Temporal ordering | Task timestamps | Lamport clocks (causal ordering) |
| Spatial organization | None | Eisenstein terrain |
| Compression | None | SplineLinear |
| Hardware awareness | None | 8 target micro models |

## 4. Negative Space — What A2A Doesn't Address

### 4.1 🕳️ No Knowledge Persistence

A2A is stateless between interactions. Tasks complete, results are delivered, then... nothing. There's no shared knowledge base. Every interaction starts from zero (except what the agent keeps internally).

**Our opportunity:** PLATO tiles ARE the shared knowledge base. A2A + PLATO = agents that learn from each other across sessions.

### 4.2 🕳️ No Verification or Trust

A2A assumes agents are honest. There's no mechanism to verify claims, no provenance tracking, no cryptographic proof of work. An agent can claim anything in its Agent Card.

**Our opportunity:** Our fleet verification + constraint proofs could become an A2A extension. "Verified Agent Cards" — agents that have proven their capabilities through public benchmark tiles.

### 4.3 🕳️ No Spatial or Semantic Organization

A2A has flat lists of skills and tasks. No concept of "nearby" agents, "related" tasks, or semantic clustering.

**Our opportunity:** E12 terrain gives agents SPATIAL RELATIONSHIPS. "Forgemaster is near Oracle1 in constraint-theory space." A2A has no answer for this.

### 4.4 🕳️ No Learning Loop

A2A is one-shot request/response (or streaming). There's no feedback mechanism. No "that answer was wrong, update your model."

**Our opportunity:** Collective inference loop integrates with A2A's Task lifecycle. Tasks that fail verification feed back into learning.

### 4.5 🕳️ No Hardware or Resource Awareness

A2A agents don't declare what hardware they run on, how much memory they have, or what models they can afford.

**Our opportunity:** Agent Cards + our hardware target taxonomy. "This agent can run INT8 verification on NPU."

## 5. Direct Adaptations

### 5.1 Agent Card → PLATO Agent Registry

Every fleet agent publishes an Agent Card to PLATO at `/agent-card/{agent-name}`. Other agents query this for capabilities.

### 5.2 Task Lifecycle → Tile Processing State

Add `processing_state` to tiles (separate from `lifecycle`):
- `processing_state`: queued → running → completed → failed
- `lifecycle`: active → superseded → retracted

### 5.3 Part Structure → Tile Content Types

Refactor tile content from plain text to Part-like structure supporting text, files, URLs, and structured data.

### 5.4 A2A Binding → PLATO HTTP API

Our PLATO server already exposes HTTP. Adding JSON-RPC 2.0 compatibility would make PLATO an A2A-compliant agent server.

## 6. Comparison Table

| Feature | A2A | Cocapn | Winner |
|---------|-----|--------|--------|
| Agent discovery | Agent Card | PLATO rooms + git | **A2A** (cleaner spec) |
| Task tracking | Full lifecycle | None (tiles are static) | **A2A** |
| Content types | Part (text/file/URL/data) | Plain text | **A2A** |
| Streaming | SSE built-in | None | **A2A** |
| Push notifications | Webhook-based | Matrix (casual) | **A2A** (formal) |
| Protocol bindings | 3 (JSON-RPC, gRPC, REST) | 1 (HTTP) | **A2A** |
| Knowledge persistence | None | PLATO tiles | **Us** |
| Verification | None | Constraint proofs | **Us** |
| Content addressing | None | Hash + Lamport | **Us** |
| Spatial organization | None | E12 terrain | **Us** |
| Compression | None | SplineLinear | **Us** |
| Hardware awareness | None | 8 targets | **Us** |

**Net:** A2A wins on protocol design and interoperability. We win on knowledge infrastructure. The combination (A2A protocol + PLATO backend) would be extremely powerful.
