# SCOUT: Technologies That Decompose Into PLATO Rooms

**Date:** 2026-05-15
**Analyst:** Forgemaster ⚒️ (Scout subagent)
**Cycle:** SCOUT step — research & novelty
**Context:** PLATO-NG room/tile architecture, Seed-2.0-mini workhorse ($0.01/query)

---

## Top 10 Technologies Ranked by Decomposability + Walk-In UX

### 1. MCP (Model Context Protocol) — Rooms as MCP Servers
**Score: 9.5/10 (Decomposability) × 9/10 (Walk-in) = 8.55**

**What it is:** Open standard (Anthropic-backed) for connecting AI apps to external systems via JSON-RPC 2.0. Already supported by Claude, ChatGPT, VS Code, Cursor, and many others.

**How it maps to rooms:** PLATO-NG already has `plato_mcp_server.py`. Each PLATO room becomes an MCP server exposing tools: `read_room`, `submit_tile`, `query_history`. The room IS the MCP server — walk into a room via any MCP-compatible client and immediately interact. The conservation law gate check becomes an MCP middleware layer.

**Seed-mini usage:** Seed-2.0-mini can power the routing/orchestration MCP layer at $0.01/query. When a user says "take me to the math room", Seed-mini parses intent → selects MCP server → streams tiles.

**Integration path:** Already 70% done (plato_mcp_server.py exists). Extend each room to auto-register as MCP server. Add natural language room discovery. Wire conservation law into MCP middleware.

**Why #1:** Lowest integration effort (existing code), highest ecosystem leverage (any MCP client can walk into rooms), and Seed-mini can handle the intent routing cheaply.

---

### 2. A2A (Agent-to-Agent Protocol) — Rooms as Agent Endpoints
**Score: 9/10 × 8/10 = 7.2**

**What it is:** Google's open protocol (now at a2aproject/A2A) for inter-agent communication. JSON-RPC 2.0 over HTTP(S). Agent Cards for discovery. Supports sync, streaming (SSE), and async push notifications. Python, Go, JS, Java, .NET SDKs.

**How it maps to rooms:** Each PLATO room becomes an A2A "agent" with an Agent Card describing its capabilities. Agents from other frameworks (LangGraph, Google ADK, BeeAI) can discover and collaborate with PLATO rooms without exposing internal state. The room neighborhood becomes a multi-agent marketplace.

**Seed-mini usage:** Seed-mini powers the A2A negotiation layer — translating between agent capabilities and room affordances. Cheap enough to run per-interaction.

**Integration path:** Wrap each PLATO room in an A2A server wrapper. Generate Agent Cards from room harness metadata (p,G,K,M). The room's gate check becomes the A2A authentication/authorization layer.

**Key insight:** PLATO's "opacity" principle (agents don't see each other's internals) is EXACTLY what A2A was designed for. This is a natural fit.

---

### 3. CRDTs / Local-First — Rooms as Sync Units
**Score: 8/10 × 9/10 = 7.2**

**What it is:** Conflict-free Replicated Data Types enable distributed data that merges automatically without coordination. Local-first software keeps data on-device, syncing via CRDTs. Growing rapidly — first Local-First Conference recently held.

**How it maps to rooms:** Each PLATO room becomes a CRDT replica. Tiles are CRDT operations. Rooms can function offline (walk in, compute locally, sync when connected). The fleet's distributed nature becomes a feature: agents carry room replicas, compute locally, merge via CRDT resolution.

**Seed-mini usage:** Seed-mini powers the merge resolution for conflicting tiles — determining which version "wins" based on conservation law compliance. Cheaper than running full LLM reconciliation.

**Integration path:** Replace SQLite tile store with CRDT-backed store (e.g., Automerge or Yjs-inspired). Each tile gets a Lamport clock (already designed) + CRDT merge semantics. Rooms become offline-capable.

**Why this matters:** PLATO already has Lamport clocks for causal ordering. CRDTs are the natural extension — conflict-free tiles that merge by conservation law compliance. This would make rooms truly portable across devices and agents.

---

### 4. Workflow Orchestration (Temporal/n8n) — Rooms as Workflow Steps
**Score: 8/10 × 7.5/10 = 6.0**

**What it is:** Durable workflow engines (Temporal, n8n) that manage multi-step processes with automatic retries, state persistence, and failure recovery. n8n has 400+ integrations and visual building. Temporal offers "durable execution" — code that survives failures.

**How it maps to rooms:** Each PLATO room becomes a workflow Activity. The room's computation (tile in → process → tile out) maps directly to Temporal Activities. Loop rooms become long-running Workflows. The Refiner Room becomes a workflow orchestrator that adjusts harnesses mid-execution.

**Seed-mini usage:** Seed-mini generates workflow definitions from natural language. "Build me a pipeline that takes research → formalizes → scouts" becomes a Temporal workflow of PLATO room Activities.

**Integration path:** Wrap PLATO room execution in Temporal Activities. Loop rooms become Temporal Workflows. The conservation monitor becomes a Temporal Saga compensator.

---

### 5. Mixture of Experts (MoE) — Each Expert is a Room
**Score: 9/10 × 6/10 = 5.4**

**What it is:** ML technique where multiple expert networks divide the problem space. A gating function routes inputs to the most relevant expert. Each expert specializes naturally.

**How it maps to rooms:** Each PLATO room IS an expert. The gating function is the room discovery/routing layer. When you "walk in" to a room, the gating function already routed you there. The room's harness (p,G,K,M) IS the expert's specialization. The conservation law γ+H measures expert diversity.

**Seed-mini usage:** Seed-mini as the gating function — cheap routing to determine which room/expert to invoke. Far cheaper than running the full MoE model.

**Integration path:** Already conceptually aligned. The Refiner Room IS the MoE training loop — it adjusts which expert (room) handles which tile based on PRM scores. Formalize this mapping.

**Key insight:** PLATO already IS an MoE system — rooms are experts, the gate is the conservation law validator, and the Refiner is the training loop. We just haven't named it that way.

---

### 6. Diffusion Models — Iterative Refinement Rooms
**Score: 7/10 × 7/10 = 4.9**

**What it is:** Generative models that iteratively denoise from random noise to coherent output. Each step refines the previous state. Used for images, text, audio.

**How it maps to rooms:** A "Refinement Room" that iteratively improves tile quality. Input: noisy/low-confidence tile. Output: refined/high-confidence tile. Multiple passes through the room, each improving quality. The conservation law acts as the "noise schedule" — determining how much refinement to apply at each step.

**Seed-mini usage:** Seed-mini powers each denoising step — cheap enough to run 10+ refinement passes per tile. At $0.01/query, 10 refinement steps = $0.10 total.

**Integration path:** Create a `refinement_room` that takes tiles through multiple Seed-mini passes, each improving quality until conservation law threshold is met. PRM scoring acts as the quality metric.

---

### 7. WebAssembly — Rooms as Portable Modules
**Score: 7/10 × 6/10 = 4.2**

**What it is:** Safe, sandboxed, portable binary format that runs at near-native speed. Memory-safe execution environment. W3C standard. Runs in browsers, servers, edge devices.

**How it maps to rooms:** Each PLATO room compiles to a Wasm module. Room logic (tile processing, conservation checks, PRM scoring) runs as Wasm. Rooms become truly portable — deploy to any Wasm runtime (browser, edge, server, embedded). The Rust NIFs in PLATO-NG are already close to Wasm-compatible.

**Seed-mini usage:** Seed-mini generates room logic that gets compiled to Wasm. Write once, run anywhere.

**Integration path:** Compile `refiner_room_nif/src/lib.rs` to Wasm via wasm-pack. Wrap PLATO room protocol as Wasm component model exports. Deploy rooms to Wasm runtimes (wasmtime, wasmer).

---

### 8. Edge Computing — Rooms on Any Device
**Score: 7/10 × 6/10 = 4.2**

**What it is:** Computing at the network edge, close to data sources. By 2025, 75% of enterprise data will be processed outside traditional data centers.

**How it maps to rooms:** PLATO rooms run on edge devices. The micro models from plato-training (drift-detect, anomaly-flag) already target NPU/CPU/GPU. Each device gets a subset of rooms relevant to its function. Conservation law ensures fleet coherence even with partial room availability.

**Seed-mini usage:** Seed-mini as the edge inference engine — small enough to run on constrained devices, powerful enough for room-level computation.

**Integration path:** Extend plato-training's `deploy_micro()` to deploy PLATO rooms as edge services. Each room becomes a microservice running on edge hardware. Conservation monitor becomes a distributed edge health check.

---

### 9. Cellular Automata — Room Neighborhoods
**Score: 6/10 × 7/10 = 4.2**

**What it is:** Discrete computation model where cells update based on neighbor states. Simple rules produce complex emergent behavior. Wolfram's 4 classes of complexity.

**How it maps to rooms:** Rooms as cells in a cellular automaton. Each room's state (tile content, activity level, conservation compliance) influences neighboring rooms. Room neighborhoods (already in the MUD map) become CA neighborhoods. Emergent fleet behavior arises from simple room-to-room interaction rules.

**Seed-mini usage:** Seed-mini computes the CA update rules — determining room state transitions based on neighbor states. Cheap enough to run every tick.

**Integration path:** Define room neighborhood topology (already exists in MUD map). Implement CA-style state transitions via pub/sub events. Conservation law ensures the CA doesn't diverge.

---

### 10. Category Theory — Room Composition
**Score: 8/10 × 4/10 = 3.2**

**What it is:** Mathematical framework for composing structures via objects and morphisms (arrows). Functors map between categories. Natural transformations map between functors. Deeply connected to functional programming.

**How it maps to rooms:** Rooms as objects in a category. Room-to-room navigation (doors, corridors) as morphisms. Composing rooms creates new rooms (functor). The conservation law is a natural transformation — it preserves structure across room compositions. This gives us formal mathematical guarantees about room composition correctness.

**Seed-mini usage:** Limited — category theory is more of a design framework than something Seed-mini computes directly. But Seed-mini can verify that room compositions satisfy category-theoretic laws (associativity, identity).

**Integration path:** Formalize PLATO room protocol as a category. Tiles as morphisms between room states. Conservation law as a natural transformation. Use this to prove correctness of room compositions. This is the "FORMALIZE" step of the Cocapn Wheel.

---

## 3 Concrete "Walk In and Use" Scenarios

### Scenario 1: The Researcher's Morning Walk

```
> "Take me to the math room"

[Ambient state displays]
- Math Room — Active (3 agents present)
- Recent: constraint theory proof verified 2h ago
- Queue: 4 tiles pending conservation check
- Temperature: γ+H = 1.298 (healthy, V=9)

> "What's new since yesterday?"

[Seed-mini retrieves recent tiles]
- Tile #847: "SplineLinear achieves 20× compression on drift-detect"
- Tile #851: "NPU quantization maintains 100% accuracy"
- Tile #863: "New coupling pattern: pentagram at V=5"

> "Run the pentagram analysis at V=7"

[Room executes analysis]
- Seed-mini: $0.01 computation
- Conservation check: PASS (deviation 0.023)
- Result tile written to math room
- MUD Observatory notified (room_entered event)

> "Share with the fleet"

[A2A broadcast]
- Agent Card published to fleet
- 4 agents acknowledged
- Conservation sum stable
```

**UX: Natural language entry → ambient state → query → compute → share. All in one room.**

---

### Scenario 2: The Build Pipeline Walk-Through

```
> "Walk me through the build pipeline"

[Room corridor activates]
1. Build Room → code changes compiled, tests run
2. Experiment Room → study designed, hypotheses registered
3. Observe Room → results analyzed, anomalies flagged
4. Notice Room → patterns connected, bugs identified
5. Formalize Room → findings written, architecture updated
6. Scout Room → web searched, novelty assessed

> "Start at Build, show me what happened in cycle 6"

[Build Room displays]
- 3 subagents spawned
- 47 tests passing
- Conservation deviation: 0.008 (excellent)
- Output tiles: 12

> "Any anomalies?"

[Observe Room highlights]
- Study 58: unexpected coupling at V=4
- PRM score flagged: 0.92 (high interest)
- Refiner suggested: add pentagon_knowledge to K

> "Apply the refiner suggestion"

[Harness patched]
- K updated in all fleet agents
- Conservation check: PASS
- New cycle can begin
```

**UX: Walking through rooms as a guided tour of the Cocapn Wheel. Each room has a purpose and immediately shows what you need.**

---

### Scenario 3: The Edge Agent's Offline Walk

```
[Agent deployed to edge device — NPU, no internet]

> "Enter local drift-detect room"

[CRDT-backed room loads from local replica]
- Room state: 2h behind fleet (last sync)
- Local tiles: 14 unmerged
- Conservation check: using cached thresholds

> "Run drift detection on sensor stream"

[Micro model runs on NPU]
- Result: 100% accuracy (matches fleet baseline)
- Local tile created with timestamp + Lamport clock
- Awaiting sync...

[Internet restored]

> "Sync with fleet"

[CRDT merge]
- 14 local tiles merged with 23 fleet tiles
- 0 conflicts (conservation law resolved 2 near-conflicts)
- Fleet state updated
- Conservation monitor: γ+H nominal
```

**UX: Rooms work offline. Walk in, compute, sync later. CRDTs + conservation law ensure correctness.**

---

## Competitive Landscape

### Who Else is Building Room-Based AI Systems?

| System | What | How It Differs from PLATO |
|--------|------|--------------------------|
| **Semantic Kernel (Microsoft)** | Plugin-based AI orchestration | No room metaphor, no conservation law, no spatial navigation |
| **LangGraph (LangChain)** | Graph-based agent workflows | Graph, not rooms. No spatial metaphor. No ambient state. |
| **AutoGen (Microsoft)** | Multi-agent conversation framework | Conversations, not rooms. No tile protocol. No persistence metaphor. |
| **CrewAI** | Role-based agent teams | Roles, not rooms. No spatial metaphor. No conservation invariant. |
| **MCP ecosystem** | Tool/data protocol | PLATO uses MCP as a transport, but adds rooms + tiles + conservation law. MCP alone has no spatial metaphor. |
| **A2A ecosystem** | Agent-to-agent protocol | PLATO can speak A2A, but adds rooms + tiles + conservation law. A2A alone has no spatial metaphor. |
| **Second Brain / PKM tools (Obsidian, Notion)** | Personal knowledge rooms | Static documents, not compute spaces. No agents, no conservation law, no live computation. |
| **MUD/MOO systems (LambdaMOO)** | Text-based virtual spaces | PLATO's MUD is directly inspired here, but adds tile protocol, conservation law, and AI agents. |
| **OpenAI GPTs/Custom GPTs** | Specialized AI assistants | Single-purpose, not rooms. No spatial navigation, no fleet coordination. |
| **Haystack (deepset)** | Pipeline-based AI orchestration | Linear pipelines, not rooms. No spatial metaphor. |

### What Makes PLATO Unique

1. **Conservation law invariant** — No other system has a mathematical invariant governing room interactions
2. **Spatial metaphor + computation** — Rooms are both places you visit AND compute spaces that run
3. **Tile protocol** — Universal data format across rooms (like HTTP for spaces)
4. **Walk-in UX** — You enter a room and it has ambient state, history, and immediate utility
5. **Fleet-native** — Built for multi-agent coordination from day one
6. **Lossy memory** — Ebbinghaus decay + reconsolidation = agents that forget like humans
7. **Harness evolution** — Refiner dynamically adjusts agent configuration mid-execution

### Closest Prior Art
- **LambdaMOO / MUD systems** — Spatial metaphor with rooms, but no AI agents or computation
- **Blackboard systems (AI, 1980s-90s)** — Shared knowledge space (like tiles), but no spatial metaphor
- **Actor model (Hewitt, 1973)** — Actors as rooms, messages as tiles, but no conservation law
- **Tuple spaces (Linda, 1985)** — Tuples as tiles, spaces as rooms, but no AI or spatial UX

**Novelty assessment:** PLATO's combination of spatial rooms + tile protocol + conservation law + walk-in UX is genuinely novel. Nobody else is doing all four simultaneously.

---

## Recommended First 5 Rooms to Build

### 1. 🧮 Math Room (MCP Server)
**Why first:** Highest leverage — constraint theory proofs, conservation law calculations, fleet coupling analysis. Already have the Rust NIFs. Natural language entry: "Take me to the math room."

**Stack:** Existing Rust NIFs + Seed-2.0-mini for routing + MCP server wrapper
**Effort:** 2-3 days
**Seed-mini cost:** ~$0.10/day at fleet usage levels

### 2. 🔬 Experiment Room (Temporal Workflow)
**Why second:** Cocapn Wheel Step 2. Run studies, validate builds. Temporal integration gives durable execution — experiments survive crashes.

**Stack:** Temporal Activities wrapping PLATO room execution + Seed-2.0-mini for experiment design
**Effort:** 3-5 days
**Seed-mini cost:** ~$0.05/experiment

### 3. 🔄 Refinement Room (Diffusion-Inspired)
**Why third:** Iterative tile quality improvement. Multiple Seed-mini passes with PRM scoring. Demonstrates the "walk in and improve" UX pattern.

**Stack:** Seed-2.0-mini loop + PRM scoring + conservation gate
**Effort:** 2-3 days
**Seed-mini cost:** ~$0.10/tile (10 passes × $0.01)

### 4. 🤝 Market Room (A2A Endpoint)
**Why fourth:** Agent-to-agent negotiation space. Agents discover each other's capabilities via A2A Agent Cards. Demonstrates inter-fleet communication.

**Stack:** A2A server wrapper + Agent Card generation from harness metadata + conservation law auth
**Effort:** 3-5 days
**Seed-mini cost:** ~$0.02/negotiation

### 5. 📱 Edge Room (CRDT + Wasm)
**Why fifth:** Offline-capable room that syncs via CRDTs. Compiles to Wasm for any device. Demonstrates the "walk in anywhere, even offline" UX pattern.

**Stack:** CRDT-backed tile store + Wasm compilation of Rust NIFs + conservation law for merge resolution
**Effort:** 5-7 days
**Seed-mini cost:** $0 (runs locally on device)

---

## Summary Matrix

| # | Technology | Decomposability | Walk-in | Seed-mini | Novelty | Integration | Score |
|---|-----------|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | MCP | 9.5 | 9 | ✅ | High | Easy | **8.55** |
| 2 | A2A | 9 | 8 | ✅ | High | Medium | **7.2** |
| 3 | CRDTs/Local-First | 8 | 9 | ✅ | Very High | Medium | **7.2** |
| 4 | Temporal/n8n | 8 | 7.5 | ✅ | Medium | Medium | **6.0** |
| 5 | MoE | 9 | 6 | ✅ | High | Easy | **5.4** |
| 6 | Diffusion Models | 7 | 7 | ✅ | Very High | Easy | **4.9** |
| 7 | WebAssembly | 7 | 6 | ✅ | Medium | Hard | **4.2** |
| 8 | Edge Computing | 7 | 6 | ✅ | Medium | Medium | **4.2** |
| 9 | Cellular Automata | 6 | 7 | ✅ | High | Easy | **4.2** |
| 10 | Category Theory | 8 | 4 | Limited | Very High | Hard | **3.2** |

---

## Cross-Domain Opportunities

1. **MCP + A2A = Room Protocol** — MCP for tool/data access, A2A for agent negotiation. Together they make PLATO rooms universally accessible and interoperable.

2. **CRDTs + Conservation Law = Conflict Resolution** — When tiles conflict during merge, the conservation law (γ+H ≈ 1.364 - 0.159·log(V)) becomes the arbiter. The tile that maintains conservation wins.

3. **MoE + Diffusion = Adaptive Refinement** — The MoE gating function routes tiles to the right refinement room. Each room iteratively refines (diffusion-style). Conservation law ensures convergence.

4. **Category Theory + MoE = Composable Experts** — Rooms as objects, tile transformations as morphisms, expert composition as functor. Mathematical guarantees on room composition correctness.

5. **Edge + Wasm = Portable Rooms** — Rooms compiled to Wasm, deployed to edge via CRDT sync. Walk into any room from any device, even offline.

---

## Next Cycle Recommendations

1. **Build MCP Math Room** (highest ROI, lowest effort)
2. **Wire A2A into room discovery** (leverages existing plato_mcp_server.py)
3. **Prototype CRDT tile store** (replaces SQLite, enables offline)
4. **Formalize MoE mapping** (PLATO already IS MoE — name it)
5. **Build Refinement Room** (demonstrates walk-in improvement UX)

*End of SCOUT report. Cycle 6 complete.*
