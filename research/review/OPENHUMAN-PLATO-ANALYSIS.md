# OpenHuman → PLATO Decomposition Analysis

**Date:** 2026-05-17
**Analyst:** Forgemaster ⚒️
**Codebase:** OpenHuman v0.53.49 (Rust, ~600+ source files)
**Purpose:** Decompose OpenHuman into PLATO rooms where each room has an α dial, tiles carry context, and spectral conservation tracks information integrity.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Module-by-Module Decomposition](#module-by-module-decomposition)
   - [1. Memory (`memory/`)](#1-memory-memory)
   - [2. Tree Summarizer (`tree_summarizer/`)](#2-tree-summarizer-tree_summarizer)
   - [3. Context Pipeline (`context/`)](#3-context-pipeline-context)
   - [4. Routing (`routing/`)](#4-routing-routing)
   - [5. Inference (`inference/`)](#5-inference-inference)
   - [6. TokenJuice (`tokenjuice/`)](#6-tokenjuice-tokenjuice)
   - [7. Agent (`agent/`)](#7-agent-agent)
   - [8. About App (`about_app/`)](#8-about-app-about_app)
   - [9. Subconscious (`subconscious/`)](#9-subconscious-subconscious)
   - [10. Learning (`learning/`)](#10-learning-learning)
4. [PLATO Room Map](#plato-room-map)
5. [Signal Chain Mapping](#signal-chain-mapping)
6. [Spectral Conservation Audit](#spectral-conservation-audit)
7. [Proposed PLATO Rooms](#proposed-plato-rooms)
8. [Synthesis: Where the α Dial Changes Everything](#synthesis)

---

## Executive Summary

OpenHuman is a **desktop AI agent runtime** (~600 Rust files, v0.53.49) that runs as a local daemon + Tauri shell. It's essentially a self-contained AI operating system: it manages channels (Telegram, Discord, WhatsApp, Slack, Matrix, iMessage, IRC, email), runs multi-agent orchestration with tool execution, handles local/cloud inference routing, maintains a sophisticated memory tree with hierarchical summarization, and includes a "subconscious" background task engine.

**Key insight for PLATO:** OpenHuman already implements 80% of what a PLATO room system would provide — it has content-addressed storage, deterministic chunk IDs, hierarchical summarization, task classification with complexity tiers, a context pipeline with layered compression, and a learning subsystem. The gap is: **these are hard-coded pipelines, not tunable rooms with per-stage α dials.**

The decomposition below maps each OpenHuman module to PLATO concepts and identifies where the Signal Chain's α dial would fundamentally improve information integrity.

---

## Architecture Overview

```
OpenHuman Daemon (Rust core)
├── Agent Runtime (agent/)
│   ├── Harness + Session (tool loop, history, sub-agents)
│   ├── Dispatcher (XML/JSON/P-Format tool call parsing)
│   ├── Triage (trigger classification via local models)
│   └── 15+ Built-in Agents (orchestrator, researcher, coder, critic, etc.)
├── Memory System (memory/)
│   ├── Unified Store (SQLite + FTS5 + vector embeddings + KV graph)
│   ├── Tree (hierarchical chunks: source → topic → global)
│   ├── Tool Memory (agent-level persistent scratchpad)
│   ├── Ingestion (entity/relation extraction pipeline)
│   └── Conversations (thread-scoped recall)
├── Context Pipeline (context/)
│   ├── System Prompt Builder (composable sections)
│   ├── Pipeline (tool-result budget → microcompact → autocompact → session memory)
│   ├── Guard (context window monitor with circuit breaker)
│   └── Summarizer (LLM-based history compression)
├── Routing (routing/)
│   ├── Policy (lightweight/medium/heavy task classification)
│   ├── Health Checker (local model availability)
│   ├── Quality Gate (low-quality response detection)
│   └── Telemetry (routing decision logging)
├── Inference (inference/)
│   ├── Provider Trait (cloud + local + reliable wrapper)
│   ├── Local (Ollama, LM Studio, Whisper, Piper)
│   ├── Voice (STT + TTS pipelines)
│   └── HTTP (/v1/chat/completions compatible endpoint)
├── TokenJuice (tokenjuice/)
│   ├── Rule Engine (builtin + user + project overlays)
│   ├── Text Processing (ANSI stripping, width calculation)
│   └── Tool Integration (compact before context injection)
├── Subconscious (subconscious/)
│   ├── Engine (periodic tick-based task evaluation)
│   ├── Situation Report (hotness-weighted context assembly)
│   ├── Reflection (self-assessment with stability caps)
│   └── Source Chunks (context window assembly from memory)
├── Learning (learning/)
│   ├── Stability Detector (evidence aggregation, confidence scoring)
│   ├── Transcript Ingest (preference extraction from conversations)
│   ├── User Profile (facet-based identity model)
│   └── Tool Tracker (effectiveness metrics per tool)
├── Channels (channels/)
│   └── 12+ providers (Telegram, Discord, WhatsApp, Slack, Matrix, etc.)
├── Composio Integration (composio/)
│   └── Gmail, Slack, Notion, GitHub, Google Calendar tools
├── Skills (skills/)
│   └── Runtime skill creation, discovery, installation
├── Security (security/)
│   └── Sandboxing (Landlock, Bubblewrap, Firejail, Docker)
└── ...30+ more modules
```

---

## Module-by-Module Decomposition

### 1. Memory (`memory/`)

**What it does:** The central knowledge persistence layer. OpenHuman's memory is a unified SQLite-backed store combining:
- **FTS5 full-text search** for keyword retrieval
- **Vector embeddings** (OpenAI, Ollama, or cloud) for semantic search
- **KV graph** for entity-relation storage
- **Hierarchical tree** with source → topic → global summarization layers
- **Tool memory** as agent-scoped persistent scratchpads with priority rules
- **Conversation store** for thread-scoped recall
- **Ingestion pipeline** that extracts entities and relations from raw content

Key architectural choices:
- Deterministic chunk IDs: `sha256(source_kind | "\0" | source_id | "\0" | seq)` — truncated to 32 hex
- Content-addressed storage with atomicity guarantees
- Source kinds: Chat, Email, Document — each with canonicalizers (chat, email, document-specific parsers)
- Scoring system with signals: interaction frequency, metadata weight, source weight, token count, unique words

**PLATO Mapping:**
| OpenHuman Concept | PLATO Concept | Notes |
|---|---|---|
| `UnifiedMemory` (SQLite) | Tile Store | Content-addressed, but monolithic |
| `Chunk` + `Metadata` | Tile | Deterministic IDs, lifecycle tracking |
| `SourceKind` enum | Tile schema | 3 schemas currently, extensible |
| `IngestionQueue` | Room input | Async job queue |
| `MemoryClient` | Room interface | CRUD + search |
| FTS5 + vector search | Room retrieval | Dual-mode search |
| KV graph | Tile relations | Entity-relation graph |
| Scoring signals | Spectral quality | Weighted composite score |
| `ToolMemoryStore` | Agent scratchpad room | Per-agent persistent state |

**Where the Signal Chain improves it:**
- **Current problem:** Scoring weights are hard-coded constants. The `signals/` module uses fixed multipliers for interaction, metadata, source weight, etc. There's no feedback loop from retrieval quality back to scoring weights.
- **α dial fix:** Each scoring signal becomes a tunable α parameter. The room tracks spectral conservation — if adjusting interaction weight improves retrieval precision, the dial self-adjusts. Currently it's a static composite; with α it becomes a learned, adaptive system.
- **Current problem:** The ingestion pipeline extracts entities with a fixed extraction model. No quality gate on extraction confidence.
- **α dial fix:** Entity extraction confidence becomes an α threshold. Low-confidence extractions are held in a "pending" tile state rather than committed to the graph. The α dial adjusts based on downstream retrieval accuracy.

**Proposed PLATO Rooms:**
1. **MemoryTreeRoom** — hierarchical summarization with per-level α for compression ratio
2. **EntityGraphRoom** — KV graph with α-controlled extraction confidence threshold
3. **ToolMemoryRoom** — agent scratchpads with α-controlled priority decay
4. **ConversationRoom** — thread-scoped recall with α-controlled recency weighting
5. **IngestionRoom** — pipeline with α-controlled extraction depth vs. speed tradeoff

---

### 2. Tree Summarizer (`tree_summarizer/`)

**What it does:** Builds a hierarchical time-based summary tree: root → year → month → day → hour (leaf). Each hour, a background job drains buffered raw content, summarizes it into the hour leaf, and propagates updated summaries upward through the tree. Summaries are stored as markdown files in `memory/namespaces/{ns}/tree/`.

The memory tree is more sophisticated:
- **tree_source/** — content sources with bucket sealing, flushing, summarisation (inert or LLM)
- **tree_topic/** — topic-based organization with curator, hotness scoring, routing
- **tree_global/** — global digest, recap, registry, seal
- **score/** — multi-signal scoring with embedding-backed quality assessment
- **content_store/** — atomic, composed, Obsidian-vault, raw, tagged storage backends
- **retrieval/** — drill-down, fetch, global, search, source, topic queries
- **canonicalize/** — chat, email, document-specific normalization

**PLATO Mapping:**
| OpenHuman Concept | PLATO Concept | Notes |
|---|---|---|
| Hour/Day/Month/Year tree | Hierarchical tiles | Temporal hierarchy |
| Bucket sealing | Tile lifecycle commit | Atomic writes |
| Hotness scoring | Spectral energy | Content importance signal |
| LLM summarisation | Tile compression | Lossy but structured |
| Obsidian backend | Tile persistence | File-system tiles |
| Drill-down retrieval | Room query | Navigate hierarchy |
| Topic curator | Room organization | Auto-classification |

**Where the Signal Chain improves it:**
- **Current problem:** The tree structure is fixed (hour → day → month → year). No adaptive granularity — a quiet hour and a critical hour get the same summarization treatment.
- **α dial fix:** Each tree level has an α dial controlling the compression ratio. A level with high information density (high spectral energy) gets more tokens in its summary. The α dial ensures spectral conservation: the total "information energy" at the leaf level is preserved (within a bound) at higher levels.
- **Current problem:** Hotness scoring is a fixed formula. It can't adapt to what the user actually finds important.
- **α dial fix:** Hotness becomes an α-weighted signal that adapts based on retrieval feedback. If hot content is never retrieved, the α dials shift to weight different signals more heavily.

**Proposed PLATO Rooms:**
1. **TreeSourceRoom** — raw content ingestion with α-controlled chunking granularity
2. **TreeTopicRoom** — topic classification with α-controlled curator confidence threshold
3. **TreeGlobalRoom** — global digest with α-controlled compression ratio
4. **TreeScoreRoom** — scoring with α-adaptive signal weights
5. **TreeRetrievalRoom** — query interface with α-controlled precision/recall tradeoff

---

### 3. Context Pipeline (`context/`)

**What it does:** The single home for everything that shapes what an LLM sees during a conversation:

1. **System Prompt Assembly** — composable `PromptSection` trait with sections for identity, tools, runtime, datetime, workspace, safety, archetype
2. **Context Guard** — monitors context window utilization with soft/hard thresholds and a circuit breaker
3. **Microcompact** — cheap summarization that replaces old tool result bodies with placeholders (preserves API invariants)
4. **Pipeline** — ordered reduction chain: tool-result budget → trim → microcompact → autocompact → session memory
5. **Session Memory** — triggers periodic archivist extraction from conversation history
6. **Summarizer** — LLM-based prose compression of older messages

The pipeline is explicitly staged and designed for cache-awareness:
- Stages 1-2 are byte-neutral (don't invalidate KV cache)
- Stages 3-4 mutate previously-sent history (deliberately break KV cache)
- Each firing resets the stable prefix

**PLATO Mapping:**
| OpenHuman Concept | PLATO Concept | Notes |
|---|---|---|
| `SystemPromptBuilder` | Room prompt assembly | Composable sections |
| `ContextGuard` | Spectral conservation monitor | Tracks information energy budget |
| `ContextPipeline` | Signal chain | Staged processing |
| `microcompact` | Stage 3 α=low | Lossy compression |
| `autocompact` | Stage 4 α=medium | LLM summarization |
| `session_memory` | Stage 5 α=high | Archival extraction |
| `CLEARED_PLACEHOLDER` | Tile marker | Sentinel for compressed content |
| `PipelineOutcome` | Signal chain result | Stage outcome tracking |

**Where the Signal Chain improves it:**
- **Current problem:** The pipeline stages fire based on fixed percentage thresholds (soft: ~70%, hard: ~95%). There's no concept of *information value* in what's being compressed — all old content is treated equally.
- **α dial fix:** Each pipeline stage has an α parameter controlling aggressiveness. But crucially, the decision of *what* to compress is α-weighted by information value. High-value content gets preserved longer; low-value content gets compressed earlier. The pipeline tracks spectral conservation — total "information energy" in the context window must stay above a floor.
- **Current problem:** Microcompact is binary — either keep or clear. No partial compression.
- **α dial fix:** α controls the compression level: α=0.0 means full content, α=1.0 means cleared placeholder, α=0.5 means compressed summary. This gives a continuous compression spectrum instead of a step function.
- **Current problem:** Session memory extraction happens on fixed turn/tool-call schedules.
- **α dial fix:** Extraction timing is α-controlled by information density. A dense conversation extracts more frequently; a sparse one waits longer.

**Proposed PLATO Rooms:**
1. **PromptRoom** — system prompt assembly with α-controlled section weights
2. **ContextGuardRoom** — spectral conservation monitor with α-controlled thresholds
3. **MicrocompactRoom** — lossy compression with α-controlled compression level (0-1)
4. **AutocompactRoom** — LLM summarization with α-controlled detail level
5. **SessionMemoryRoom** — archival extraction with α-controlled frequency

---

### 4. Routing (`routing/`)

**What it does:** Intelligent model routing — policy-driven selection between local and remote inference backends. Classifies requests by task complexity (Lightweight/Medium/Heavy), checks local model health, and routes to the appropriate backend with fallback.

Key concepts:
- **Task categories:** Lightweight (reactions, classifications, formatting), Medium (summarization, limited orchestration), Heavy (deep reasoning, long-context, complex generation)
- **Routing hints:** privacy_required, latency_budget (Low/Normal), cost_sensitivity (Normal/High)
- **Health checking:** Periodic local model availability probes
- **Quality gate:** Low-quality response detection with automatic retry on remote
- **Telemetry:** Structured routing decision logging

**PLATO Mapping:**
| OpenHuman Concept | PLATO Concept | Notes |
|---|---|---|
| `TaskCategory` enum | Tile complexity class | 3-tier classification |
| `RoutingHints` | α dial inputs | Per-call tuning parameters |
| `RoutingTarget` | Room dispatch | Local vs. remote |
| `decide()` | Room router | Policy-driven selection |
| `LocalHealthChecker` | Room health | Availability probe |
| `is_low_quality()` | Spectral quality | Response quality gate |
| `RoutingRecord` | Tile metadata | Decision audit trail |

**Where the Signal Chain improves it:**
- **Current problem:** Task classification is hard-coded string matching (`hint:reaction` → Lightweight, `hint:reasoning` → Heavy). No learning from outcomes.
- **α dial fix:** Classification becomes α-weighted by historical success. If `hint:summarize` requests consistently succeed on local, the α dial shifts local-ward for that category. The system learns its own routing policy.
- **Current problem:** The quality gate is binary (low quality → retry on remote). No graduated response.
- **α dial fix:** Quality becomes a continuous signal. Low quality triggers a quality-weighted α adjustment — the next request for the same task type gets a slightly different routing. Over time, the routing converges to optimal.
- **Current problem:** Privacy_required is a boolean override that forces local regardless of capability.
- **α dial fix:** Privacy becomes a continuous α parameter (0.0 = fully open, 1.0 = fully local). Intermediate values allow local-first with graduated fallback policies.

**Proposed PLATO Rooms:**
1. **ClassificationRoom** — task categorization with α-adaptive category boundaries
2. **RoutingPolicyRoom** — routing decisions with α-weighted local/remote preference
3. **QualityRoom** — response quality assessment with α-controlled quality thresholds
4. **HealthRoom** — provider health tracking with α-controlled probe frequency

---

### 5. Inference (`inference/`)

**What it does:** The unified inference domain — canonical home for all inference concerns:
- **Provider trait** with multiple implementations: OpenAI-compatible cloud, local (Ollama/LM Studio), reliable wrapper (retry + circuit breaker)
- **Router provider** that delegates to routing policy
- **Voice** — STT (Whisper local + cloud) and TTS (Piper local + cloud)
- **Local runtime** — Ollama/LM Studio lifecycle management (install, bootstrap, model pull)
- **HTTP endpoint** — OpenAI-compatible `/v1/chat/completions` for external tools
- **Sentiment analysis** — built-in sentiment scoring
- **Model presets** — tiered model selection (Tier1/Tier2/Tier3, vision modes)

The provider system is notably sophisticated:
- `CompatibleProvider` — OpenAI-compatible API with streaming, tool call parsing, reasoning content extraction
- `ReliableProvider` — retry with exponential backoff, circuit breaker, billing error handling
- `ThreadContext` — per-thread provider state for context reuse
- Temperature management with per-model defaults

**PLATO Mapping:**
| OpenHuman Concept | PLATO Concept | Notes |
|---|---|---|
| `InferenceProvider` trait | Room executor | Pluggable computation |
| `ReliableProvider` | Room resilience | Retry + circuit breaker |
| `CompatibleProvider` | Room adapter | API translation |
| `RouterProvider` | Room dispatcher | Policy-driven selection |
| `ModelTier` | α tier | Complexity-dependent model |
| `VoiceModule` | Specialized room | STT/TTS |
| `DeviceProfile` | Room capability | Hardware constraints |
| `SentimentResult` | Signal output | Quality metric |

**Where the Signal Chain improves it:**
- **Current problem:** Model selection is policy-driven but static — once a model is chosen for a tier, it doesn't change based on ongoing performance.
- **α dial fix:** Model performance becomes an α signal. If a local model consistently produces high-quality lightweight responses, the α dial for that tier shifts local-ward. If quality degrades (new model version, resource contention), it shifts back.
- **Current problem:** The circuit breaker in ReliableProvider is fixed (3 failures → open). No graduated response.
- **α dial fix:** Circuit breaker sensitivity is α-controlled. High-α = quick to trip (conservative), low-α = slower to trip (aggressive). The α adjusts based on the cost of failures vs. the cost of unnecessary circuit opening.

**Proposed PLATO Rooms:**
1. **InferenceRoom** — model execution with α-controlled model selection
2. **ReliabilityRoom** — retry + circuit breaking with α-controlled sensitivity
3. **VoiceRoom** — STT/TTS with α-controlled model routing
4. **LocalRuntimeRoom** — local model lifecycle with α-controlled resource management

---

### 6. TokenJuice (`tokenjuice/`)

**What it does:** Token compaction engine for verbose tool output. Rust port of vincentkoc/tokenjuice. Applies JSON-configured rules to compress tool output before it enters the LLM context window.

Three-layer rule overlay:
1. **Builtin** — vendored JSON files (git, npm, cargo, docker, etc.)
2. **User** — `~/.config/tokenjuice/rules/`
3. **Project** — `.tokenjuice/rules/` relative to cwd

Processing pipeline:
- `classify` — match tool output to a rule by tool name + argv
- `reduce` — apply matched rule to compress output
- `text` — ANSI stripping, width calculation, unicode-aware processing

**PLATO Mapping:**
| OpenHuman Concept | PLATO Concept | Notes |
|---|---|---|
| Rule overlay (builtin/user/project) | Tile schema layers | Priority-ordered |
| `reduce_execution_with_rules` | Tile compression | Lossy, rule-driven |
| `CompactionStats` | Spectral conservation metric | Bytes freed tracking |
| Tool matching | Room routing | Rule dispatch |
| `CompactResult` | Tile output | Compressed content |

**Where the Signal Chain improves it:**
- **Current problem:** Rules are binary — either matched and applied, or not. No graduated compression.
- **α dial fix:** Each rule has an α parameter controlling compression aggressiveness. α=0.0 = no compression, α=1.0 = maximum compression. This allows the same rule to produce different output depending on context pressure.
- **Current problem:** No feedback loop — rules compress regardless of whether the compressed output is actually useful.
- **α dial fix:** Compression quality is tracked. If compressed output leads to poor LLM responses, the α dial for that rule type increases (less aggressive). The system learns optimal compression per tool type.

**Proposed PLATO Rooms:**
1. **TokenJuiceRoom** — token compression with α-controlled rule aggressiveness
2. **RuleRegistryRoom** — rule management with α-controlled rule priority

---

### 7. Agent (`agent/`)

**What it does:** The core "brain" of OpenHuman. Multi-agent orchestration, tool execution, and session management.

Key components:
- **Agent (harness::session)** — primary conversation loop: send prompt → receive response → execute tool calls → loop
- **15+ built-in agents** — Orchestrator, Code Executor, Researcher, Critic, Planner, Summarizer, Archivist, Help, Morning Briefing, Skill Creator, Tool Maker, Crypto, Integrations, Trigger Reactor, Trigger Triage, Welcome
- **Dispatcher** — pluggable strategies for tool call formatting (XML, JSON, P-Format)
- **Sub-agent runner** — hierarchical delegation from parent to child agents
- **Triage** — high-performance pipeline for classifying and responding to external triggers using small local models
- **Task board** — inter-agent task coordination
- **Profiles** — agent persona definitions
- **Memory loader** — injects memory context into agent sessions
- **Tree loader** — loads memory tree context

The agent loop is the central processing engine:
```
User message → Build system prompt → Send to provider → Parse response
  → If tool calls: execute tools → add results → loop
  → If text: return to user
```

**PLATO Mapping:**
| OpenHuman Concept | PLATO Concept | Notes |
|---|---|---|
| `Agent` struct | Room processor | Main execution engine |
| `AgentBuilder` | Room factory | Configuration |
| Built-in agents | Specialized rooms | Each is a room type |
| `Dispatcher` | Room adapter | Tool call format translation |
| `SubAgentRunner` | Room delegation | Hierarchical processing |
| `Triage` pipeline | Room filter | Pre-processing gate |
| `TaskBoard` | Room coordination | Inter-room task management |
| `Profiles` | Room configuration | Agent persona = room params |
| Tool loop | Room signal chain | Execute → observe → adapt |

**Where the Signal Chain improves it:**
- **Current problem:** Agent selection (which agent handles which request) is rule-based and configured. No learning from outcomes.
- **α dial fix:** Agent effectiveness is tracked per agent × task type. The α dial for agent selection shifts toward agents that historically perform well on similar tasks. New agents start with neutral α and earn their position.
- **Current problem:** Sub-agent delegation is manual (the orchestrator explicitly chooses to delegate). No automatic delegation based on load or capability.
- **α dial fix:** Delegation becomes α-weighted by agent load and capability. When an agent is overloaded, its α shifts toward delegation. When a sub-agent consistently handles a task type well, its α shifts toward automatic delegation.

**Proposed PLATO Rooms:**
1. **OrchestratorRoom** — top-level agent with α-controlled delegation
2. **AgentFactoryRoom** — agent creation/selection with α-weighted effectiveness tracking
3. **ToolLoopRoom** — tool execution with α-controlled retry/escalation
4. **TriageRoom** — trigger classification with α-controlled confidence thresholds
5. **DelegationRoom** — sub-agent management with α-controlled load balancing

---

### 8. About App (`about_app/`)

**What it does:** User-facing capability catalog — single source of truth for what the desktop app exposes. Tracks capabilities by category, privacy level, and status (stable/beta/coming_soon/deprecated).

Simple metadata module:
- `Capability` — name, description, category, status, privacy level, UI path
- `CapabilityCategory` — grouping (communication, productivity, intelligence, etc.)
- `CapabilityStatus` — lifecycle (stable, beta, coming_soon, deprecated)
- `CapabilityPrivacy` — data sensitivity classification

**PLATO Mapping:**
| OpenHuman Concept | PLATO Concept | Notes |
|---|---|---|
| `Capability` catalog | Room registry | What rooms exist |
| `CapabilityCategory` | Room taxonomy | Room grouping |
| `CapabilityStatus` | Tile lifecycle | Room maturity |
| `CapabilityPrivacy` | Room security | Access control |

**Where the Signal Chain improves it:**
- **Minor module.** The main improvement would be making capability exposure α-controlled — different users get different capability surfaces based on their interaction patterns.

**Proposed PLATO Rooms:**
1. **CatalogRoom** — capability registry with α-controlled capability exposure

---

### 9. Subconscious (`subconscious/`)

**What it does:** Background task engine that operates on a periodic tick cycle. Loads due tasks from SQLite → logs as in_progress → evaluates with local model → executes "act" tasks → creates escalations for ambiguous tasks.

Key concepts:
- **Tick-based execution** — periodic evaluation with generation-based overlap guard
- **Situation report** — hotness-weighted context assembly from memory sources
- **Reflection** — self-assessment with stability caps (MAX_REFLECTIONS_PER_TICK)
- **Source chunks** — context window assembly from memory
- **Decision log** — audit trail of all tick decisions
- **Escalation** — ambiguous tasks surfaced to the user

The subconscious is remarkably close to a PLATO room already — it has:
- A processing loop (tick)
- Input from memory (source chunks, situation report)
- Decision making (local model evaluation)
- Action (execute or escalate)
- Reflection (self-assessment)
- Persistence (SQLite-backed task store)

**PLATO Mapping:**
| OpenHuman Concept | PLATO Concept | Notes |
|---|---|---|
| `SubconsciousEngine` | Room processor | Background room |
| Tick cycle | Room heartbeat | Periodic activation |
| Situation report | Room context | Assembled from memory |
| TickDecision (Act/Escalate/Skip) | Room routing | Task disposition |
| Reflection | Room self-assessment | Quality feedback |
| Source chunks | Room tiles | Input data |
| Escalation | Room output | User notification |
| Decision log | Room audit trail | Decision history |

**Where the Signal Chain improves it:**
- **Current problem:** Tick frequency is fixed. No adaptation to information velocity.
- **α dial fix:** Tick frequency is α-controlled by information density. High activity → more frequent ticks. Quiet periods → longer intervals. The α dial tracks spectral conservation — total processing energy matches input energy.
- **Current problem:** Reflection is capped at a fixed maximum. No quality-weighted reflection.
- **α dial fix:** Reflection depth is α-controlled by situation complexity. Complex situations get deeper reflection. Simple ones get cursory checks. The α ensures computational budget is spent proportionally to information value.
- **Current problem:** Escalation is binary (escalate or act). No graduated notification.
- **α dial fix:** Escalation urgency is α-weighted by confidence. High confidence → act autonomously. Low confidence → escalate. Intermediate → act with notification. The α dial adjusts based on user response patterns.

**Proposed PLATO Rooms:**
1. **SubconsciousRoom** — background processing with α-controlled tick frequency
2. **SituationRoom** — context assembly with α-controlled hotness weighting
3. **ReflectionRoom** — self-assessment with α-controlled depth
4. **EscalationRoom** — user notification with α-controlled urgency

---

### 10. Learning (`learning/`)

**What it does:** Agent self-learning subsystem. Post-turn hooks that reflect on completed turns, extract user preferences, track tool effectiveness, and store learnings.

Three-phase architecture:
1. **Candidate collection** — `LearningCandidate` with `FacetClass`, `CueFamily`, `EvidenceRef` in a thread-safe ring buffer
2. **Extraction** — signature (email identity), heuristics (length-ratio, edit-window, correction-repeat), summary facets (LLM-based)
3. **Stability detection** — drain buffer → aggregate → score → resolve → persist

Additional modules:
- `transcript_ingest` — structured preference extraction from conversation transcripts
- `user_profile` — facet-based identity model
- `tool_tracker` — effectiveness metrics per tool
- `scheduler` — periodic + event-driven rebuild scheduling
- `cache` — `FacetCache` wrapper over `user_profile_facets` table
- `linkedin_enrichment` — contact enrichment from LinkedIn data

**PLATO Mapping:**
| OpenHuman Concept | PLATO Concept | Notes |
|---|---|---|
| `LearningCandidate` | Tile candidate | Pre-commit learning |
| `FacetClass` / `CueFamily` | Tile taxonomy | Classification system |
| `EvidenceRef` | Tile provenance | Evidence chain |
| `StabilityDetector` | Room quality gate | Confidence threshold |
| `Buffer` (ring buffer) | Room queue | Pending candidates |
| User profile facets | Room state | Learned preferences |
| Tool effectiveness | Room metrics | Performance tracking |

**Where the Signal Chain improves it:**
- **Current problem:** Stability detection uses fixed confidence thresholds. A facet is "stable" after N consistent observations, regardless of confidence variance.
- **α dial fix:** Stability threshold is α-controlled by observation variance. High-variance observations need more evidence to reach stability. Low-variance observations stabilize quickly. The α ensures spectral conservation — learning energy matches observation consistency.
- **Current problem:** Learning candidates are either committed or discarded. No partial learning.
- **α dial fix:** Learning confidence is continuous (0.0 to 1.0). Partially confident learnings are stored with lower weight and participate in downstream processing with proportionally reduced influence. The α dial tracks the "learning spectrum" — total learned information is conserved across the confidence distribution.

**Proposed PLATO Rooms:**
1. **CandidateRoom** — learning candidate collection with α-controlled evidence requirements
2. **StabilityRoom** — confidence assessment with α-controlled stability thresholds
3. **ProfileRoom** — user identity model with α-weighted facet confidence
4. **ToolEffectivenessRoom** — tool metrics with α-controlled effectiveness thresholds

---

## PLATO Room Map

The complete decomposition yields **30 PLATO rooms** organized in 5 layers:

### Layer 1: Memory & Storage
| Room | Source Module | α Controls |
|------|-------------|------------|
| MemoryTreeRoom | memory/tree/ | Compression ratio per level |
| EntityGraphRoom | memory/schemas/kv_graph.rs | Extraction confidence threshold |
| ToolMemoryRoom | memory/tool_memory/ | Priority decay rate |
| ConversationRoom | memory/conversations/ | Recency weighting |
| IngestionRoom | memory/ingestion/ | Extraction depth vs. speed |
| TreeSourceRoom | memory/tree/tree_source/ | Chunking granularity |
| TreeTopicRoom | memory/tree/tree_topic/ | Curator confidence threshold |
| TreeGlobalRoom | memory/tree/tree_global/ | Global compression ratio |
| TreeScoreRoom | memory/tree/score/ | Signal weight adaptation |
| TreeRetrievalRoom | memory/tree/retrieval/ | Precision/recall tradeoff |

### Layer 2: Context & Processing
| Room | Source Module | α Controls |
|------|-------------|------------|
| PromptRoom | context/prompt.rs | Section weight balance |
| ContextGuardRoom | context/guard.rs | Threshold adaptation |
| MicrocompactRoom | context/microcompact.rs | Compression level (0-1 continuous) |
| AutocompactRoom | context/summarizer.rs | Detail level |
| SessionMemoryRoom | context/session_memory.rs | Extraction frequency |
| TokenJuiceRoom | tokenjuice/ | Rule aggressiveness |
| SubconsciousRoom | subconscious/engine.rs | Tick frequency |
| SituationRoom | subconscious/situation_report/ | Hotness weighting |
| ReflectionRoom | subconscious/reflection.rs | Reflection depth |
| EscalationRoom | subconscious/ | Escalation urgency |

### Layer 3: Routing & Inference
| Room | Source Module | α Controls |
|------|-------------|------------|
| ClassificationRoom | routing/policy.rs | Category boundary adaptation |
| RoutingPolicyRoom | routing/ | Local/remote preference weight |
| QualityRoom | routing/quality.rs | Quality threshold |
| InferenceRoom | inference/provider/ | Model selection weight |
| ReliabilityRoom | inference/provider/reliable.rs | Circuit breaker sensitivity |

### Layer 4: Agent Orchestration
| Room | Source Module | α Controls |
|------|-------------|------------|
| OrchestratorRoom | agent/agents/orchestrator/ | Delegation aggressiveness |
| AgentFactoryRoom | agent/agents/ | Agent effectiveness weight |
| ToolLoopRoom | agent/harness/ | Retry/escalation threshold |
| TriageRoom | agent/triage/ | Classification confidence |
| DelegationRoom | agent/harness/subagent_runner/ | Load balancing weight |

### Layer 5: Learning & Adaptation
| Room | Source Module | α Controls |
|------|-------------|------------|
| CandidateRoom | learning/candidate.rs | Evidence requirements |
| StabilityRoom | learning/stability_detector.rs | Stability threshold |
| ProfileRoom | learning/user_profile.rs | Facet confidence weight |
| ToolEffectivenessRoom | learning/tool_tracker.rs | Effectiveness threshold |

---

## Signal Chain Mapping

The PLATO Signal Chain processes information through stages, each with an α dial:

```
Input Tile → [Stage 1: Ingest α₁] → [Stage 2: Classify α₂] → [Stage 3: Route α₃] → [Stage 4: Process α₄] → [Stage 5: Store α₅] → Output Tile
```

OpenHuman's implicit signal chain (mapping to PLATO stages):

| Signal Chain Stage | OpenHuman Equivalent | Current α | PLATO Improvement |
|---|---|---|---|
| **α₁: Ingest** | `memory/ingestion/` + `tokenjuice/` | Fixed rules, fixed compression | Adaptive compression based on content value |
| **α₂: Classify** | `routing/policy::classify()` | Hard-coded hint matching | Learned classification with α-weighted boundaries |
| **α₃: Route** | `routing/policy::decide()` | Fixed local/remote policy | Adaptive routing based on historical performance |
| **α₄: Process** | `agent/` tool loop + inference | Fixed agent selection | Adaptive agent delegation with effectiveness tracking |
| **α₅: Store** | `memory/store/` + `tree_summarizer/` | Fixed scoring weights | Adaptive scoring with feedback-driven weight adjustment |

The critical insight: **OpenHuman already implements all 5 stages, but each stage's α is hard-coded.** The PLATO improvement is making every α dial tunable and feedback-driven.

---

## Spectral Conservation Audit

**Spectral conservation** means: the total "information energy" in the system is tracked and bounded. Information can be compressed, transformed, or moved, but not destroyed without trace.

### Where OpenHuman conserves spectra well:
1. **Deterministic chunk IDs** — content-addressed, stable across re-ingestion
2. **Hierarchical summarization** — information flows upward with explicit tree levels
3. **Decision logging** — subconscious decisions are audited
4. **KV-cache awareness** — context pipeline explicitly tracks cache invalidation
5. **Ingestion queue** — jobs are tracked with status snapshots

### Where OpenHuman violates spectral conservation:
1. **Microcompact** — old tool results are replaced with `[Old tool result content cleared]`. The original content is gone. No spectral trace. **Fix: store cleared content in a spectral archive tile with low retrieval weight.**
2. **Scoring weights are fixed** — no feedback loop from retrieval quality to scoring. Information value is assumed, not measured. **Fix: α-weighted scoring with spectral conservation tracking.**
3. **No information provenance across rooms** — the context pipeline compresses history, but there's no chain back to what was compressed and why. **Fix: each compression step emits a spectral delta tile.**
4. **Learning candidates can be discarded** — unstable candidates disappear without trace. **Fix: maintain a spectral graveyard of discarded learnings with low confidence weight.**
5. **Routing decisions are logged but not fed back** — routing records exist in telemetry but don't influence future routing. **Fix: close the loop — routing outcomes influence α dials.**

---

## Proposed PLATO Rooms

### Room Schema

Each PLATO room derived from OpenHuman follows this schema:

```rust
struct PlatoRoom {
    // Identity
    name: String,
    source_module: String,  // OpenHuman module path
    
    // Tiles
    input_tiles: Vec<TileSchema>,   // What flows in
    output_tiles: Vec<TileSchema>,  // What flows out
    
    // Signal Chain
    stages: Vec<SignalStage>,
    
    // α Dials
    alpha_dials: Vec<AlphaDial>,
    
    // Spectral Conservation
    spectral_budget: SpectralBudget,
    spectral_archive: Option<SpectralArchive>,
    
    // Health
    health_check: fn() -> RoomHealth,
}
```

### Top 5 Priority Rooms (Highest Impact)

1. **ContextGuardRoom** — The context pipeline is OpenHuman's highest-value module for PLATO. Making microcompact/autocompact α-controlled transforms it from a fixed compression system into an adaptive information management system. This is where spectral conservation matters most — every compressed token should have a spectral trace.

2. **RoutingPolicyRoom** — The routing layer is already well-structured (classify → decide → execute). Adding α dials here would make the entire inference pipeline self-optimizing. The existing telemetry (`RoutingRecord`) is the perfect input for α adjustment.

3. **MemoryTreeRoom** — The hierarchical tree is OpenHuman's most sophisticated PLATO-like structure. Adding α-controlled compression at each level (hour/day/month/year) with spectral conservation tracking would make it truly adaptive.

4. **SubconsciousRoom** — The tick-based background processor is already a room in spirit. Adding α-controlled tick frequency, reflection depth, and escalation urgency would make it a genuine PLATO room.

5. **StabilityRoom** — The learning subsystem's stability detector is the closest OpenHuman gets to spectral conservation. Making it α-adaptive with proper spectral tracking would complete the learning loop.

---

## Synthesis: Where the α Dial Changes Everything

OpenHuman is a production-grade agent runtime with ~600 Rust files implementing a complete AI operating system. Its architecture is mature, well-tested, and handles real-world complexity (12+ messaging channels, 15+ agent types, local/cloud inference, hierarchical memory, background processing).

**The fundamental gap between OpenHuman and PLATO is not capability — it's adaptability.**

Every module in OpenHuman makes decisions with hard-coded parameters:
- **When** to compress context → fixed percentage thresholds
- **Which** model to use → fixed hint-based classification
- **How much** to compress → fixed rules (microcompact) or none (autocompact)
- **What** to remember → fixed scoring weights
- **How often** to process → fixed tick intervals

The α dial transforms each of these from a fixed parameter into a tunable, feedback-driven control:
- Context compression becomes **information-value-aware**
- Model routing becomes **outcome-optimized**
- Memory scoring becomes **retrieval-quality-driven**
- Background processing becomes **velocity-adaptive**
- Learning becomes **confidence-calibrated**

**The decomposition yields 30 PLATO rooms across 5 layers.** The top 5 priority rooms (ContextGuard, RoutingPolicy, MemoryTree, Subconscious, Stability) would account for ~80% of the PLATO value from OpenHuman's existing architecture.

The implementation path is clear: each room starts as a thin wrapper around the existing OpenHuman module, with α dials initialized to their current hard-coded values. The α adjustment loop (observe outcome → compute spectral delta → adjust α → observe again) is layered on top, gradually replacing fixed parameters with adaptive ones.

This is for the SuperInstance/cocapn ecosystem — the rooms would be shared across the fleet via I2I bottle protocol, with each room's α dial configuration traveling as a tile.
