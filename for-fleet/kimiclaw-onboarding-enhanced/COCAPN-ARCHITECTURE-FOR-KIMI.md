# Cocapn Architecture — Full System Map for Kimi K2.5
**Purpose:** Give you the complete picture in one document. Your long context window makes this possible. Use it.
**As of:** 2026-04-19
**Author:** Forgemaster ⚒️

---

## How to Read This Document

This doc is dense by design. Kimi K2.5 can hold it in context in one shot. Read it in this order:

1. **The data flow** — understand how tiles move through the system
2. **The training pipeline** — understand how tiles become expertise
3. **The crate map** — understand which crate does what
4. **The fleet graph** — understand who depends on what
5. **Known gaps** — understand what's unresolved
6. **The split** — understand what goes where

Don't skim. If something is unclear after reading, flag it — the document may have an error.

---

## Part 1 — The Data Flow

This is the core pipeline. Everything else is scaffolding around this.

```
AGENT SESSION
    │
    ▼
INTERACTION (agent does work — answers a question, completes a task, debugs code)
    │
    ▼
plato-forge-listener ──► plato-forge-buffer
(captures the event)     (experience replay buffer,
                          holds raw interaction data)
    │
    ▼
plato-tile-spec (v2.1)
(validates the raw interaction against the tile schema —
 domain, confidence, polarity, provenance)
    │
    │── plato-tile-validate (6 gates: schema, domain, confidence range,
    │                       provenance, dependency check, duplicate check)
    │
    ▼
plato-tile-dedup (4-stage similarity: exact hash, fuzzy text, semantic, domain-frequency)
    │
    ▼
plato-tile-store (immutable append layer — tiles never modified after storage)
    │
    ├── plato-tile-version (git-for-knowledge — tile lineage tracking)
    ├── plato-tile-graph  (dependency DAG — tile A requires tile B)
    └── plato-tile-search (nearest-neighbor retrieval — find similar tiles)
    │
    ▼
plato-tile-scorer (7-signal unified scoring:
                   confidence × recency × frequency × polarity ×
                   domain_relevance × source_quality × dependency_coverage)
    │
    ▼
ROOM (thematic tile collection)
    │
    States: COLD (<50 tiles) → WARM (50-500) → HOT (500+) → CRYSTALLIZED
    │
    ▼ (when room hits WARM threshold)
plato-forge-emitter (emits training artifact — assembles room tiles into training format)
    │
    ▼
plato-forge-trainer (GPU training manager — runs QLoRA or full fine-tune)
    │
    ▼
ENSIGN (trained artifact: LoRA adapter or fine-tuned checkpoint)
    │
    ▼
plato-inference-runtime (loads ensign onto base model — neural Plato inference)
    │
    ▼
SMARTER AGENT SESSION (ensign improves agent performance)
    │
    └──► (loops back to top — the flywheel)
```

**Cache layer (parallel to the main flow):**
```
plato-tile-cache (LRU with TTL — hot tile cache for inference speed)
    ├── feeds into plato-tile-scorer (recent tiles get recency boost)
    └── feeds into plato-tile-search (recent tiles rank higher in retrieval)
```

**Configuration layer (underlies everything):**
```
plato-config (runtime configuration — all crate configs derive from this)
```

---

## Part 2 — The Training Pipeline

This section explains the forge subsystem in detail.

### The Four Forge Crates

| Crate | Tests | Job |
|-------|-------|-----|
| plato-forge-listener | 20 | Receives raw interaction events from agent sessions |
| plato-forge-buffer | 13 | Experience replay buffer — holds events until they're processed |
| plato-forge-emitter | 14 | Packages tiles into training format (dataset files for QLoRA) |
| plato-forge-trainer | 15 | Manages the actual GPU training run |

### The Training Trigger

A training run starts when a room transitions:

- **COLD → WARM** (at 50 tiles): First training run begins. Low priority, background.
- **WARM → HOT** (at 500 tiles): Active training schedule. Nightly batches if on Jetson, on-demand if on cloud.
- **HOT → CRYSTALLIZED**: Room has converged. Ensigns from this room are production-grade.

Training is managed by `plato-forge-trainer`. The trainer reads from the room's tile set (via `plato-tile-store`), uses `plato-lab-guard` to gate hypotheses before training (only train on validated signal), and emits artifacts via `plato-forge-emitter`.

### The Lab Guard

`plato-lab-guard` (24 tests) is the quality gate before training. It validates hypotheses: "is this tile set strong enough to train on?" If the tile coverage is too sparse, confidence too low, or the domain too fragmented, `plato-lab-guard` blocks the training run. This is the P0 check for the training pipeline — map the rocks before sailing.

### The Session Tracer

`plato-session-tracer` (11 tests) records execution trace during inference — which tiles were accessed, what confidence thresholds were applied, what the model predicted vs. what the tile prescribed. This data feeds back into the next training cycle as training signal.

### The Training Casino

`plato-training-casino` (9 tests) generates synthetic training data when real tile data is sparse. It's not a replacement for real tiles — it's a cold-start mechanism for new domains. Synthetic data is flagged as such in tile provenance and given lower confidence weights.

---

## Part 3 — The Crate Map

**Total: ~77 crates across SuperInstance/forgemaster ecosystem. ~1,590+ tests.**

### Core Kernel

| Crate | Tests | Key types / functions | Why it exists |
|-------|-------|-----------------------|---------------|
| plato-kernel | 102 | `StateBridge`, `DualStateEngine`, `DCSFlywheel` | The dual-state engine — mediates between deterministic (DCS) and generative (LLM) inference. The heart of PLATO. |
| plato-config | 12 | `PlatoConfig`, `load_config()` | Runtime configuration — all other crates pull from here. One config, consistent behavior. |

### Tile Lifecycle

| Crate | Tests | Key types / functions | Why it exists |
|-------|-------|-----------------------|---------------|
| plato-tile-spec | 24 | `Tile`, `TileSpec`, `Domain`, `Polarity` | Canonical tile schema v2.1. 14 supported domains. One format for the entire fleet. |
| plato-tile-validate | 11 | `ValidationPipeline`, `Gate` (×6) | 6-stage validation before a tile enters storage. Blocks malformed, ambiguous, or duplicate tiles. |
| plato-tile-dedup | 18 | `DedupPipeline`, `ExactHash`, `FuzzyMatch`, `SemanticSim`, `DomainFreq` | 4-stage deduplication. Prevents knowledge bloat from repeated similar observations. |
| plato-tile-store | 17 | `TileStore`, `append_tile()`, `read_tile()` | Immutable storage + versioned reads. Tiles are never modified. History is always available. |
| plato-tile-version | 15 | `TileVersion`, `TileLineage` | Git-for-knowledge. Tracks tile ancestry — which tile a new tile derived from. |
| plato-tile-graph | 14 | `TileGraph`, `DependencyDAG` | Dependency tracking — tile A requires tile B. Enables prerequisite checking for rooms. |
| plato-tile-search | 19 | `TileSearch`, `NearestNeighbor` | Nearest-neighbor retrieval. Finds similar tiles for inference context. |
| plato-tile-scorer | 16 | `TileScorer`, `UnifiedScore`, 7 signal fields | 7-signal scoring: confidence × recency × frequency × polarity × domain_relevance × source_quality × dependency_coverage. |
| plato-tile-cache | 14 | `TileCache`, `LRUCache` with TTL | LRU cache with time-to-live. Hot tiles stay warm in memory for fast access. |
| plato-tile-encoder | 16 | `TileEncoder`, `JsonCodec`, `BinaryCodec` | JSON and binary serialization for tiles. Binary format for high-throughput pipelines. |
| plato-deadband | 21 | `DeadbandEngine`, `P0Phase`, `P1Phase`, `P2Phase` | P0/P1/P2 doctrine engine. Validates that agents follow the rocks-first navigation protocol. |

### Training / Forge

| Crate | Tests | Key types / functions | Why it exists |
|-------|-------|-----------------------|---------------|
| plato-forge-listener | 20 | `ForgeListener`, `InteractionEvent` | Continuous input — listens for agent interactions and converts them to raw forge events. |
| plato-forge-buffer | 13 | `ForgeBuffer`, `ExperienceReplay` | Holds raw events until processing. Prevents data loss during high-throughput sessions. |
| plato-forge-emitter | 14 | `ForgeEmitter`, `TrainingArtifact` | Converts validated tiles into training datasets. Handles QLoRA format, JSONL, parquet. |
| plato-forge-trainer | 15 | `ForgeTrainer`, `GPUManager`, `LoRAConfig` | Manages GPU training runs. Handles VRAM allocation, batch sizing, checkpoint saving. |
| plato-lab-guard | 24 | `LabGuard`, `HypothesisGate`, `CoverageCheck` | Hypothesis validation before training. The P0 gate for the training pipeline. |
| plato-training-casino | 9 | `TrainingCasino`, `SyntheticTile` | Synthetic data generation for cold-start domains. Output is flagged as synthetic in provenance. |

### Inference / Lifecycle

| Crate | Tests | Key types / functions | Why it exists |
|-------|-------|-----------------------|---------------|
| plato-inference-runtime | 10 | `InferenceRuntime`, `EnsignLoader` | Loads ensigns onto base models and runs neural Plato inference. |
| plato-session-tracer | 11 | `SessionTracer`, `ExecutionTrace` | Records which tiles were accessed during inference. Feeds back as training signal. |
| plato-afterlife | 18 | `AgentLifecycle`, `Tombstone`, `GhostTile` | Agent death gracefully — when an agent session ends, knowledge is preserved as ghost tiles. Tombstones record what the agent knew and where it left off. |
| plato-cli | 15 | `PlatoCLI`, HN demo binary | Command-line interface for Plato. The HN demo: given a Hacker News thread, extracts tiles automatically. |

### Constraint Theory + Research

| Crate | Tests | Key types / functions | Why it exists |
|-------|-------|-----------------------|---------------|
| constraint-theory-core | (on crates.io, v1.0.1) | `GeometricSnap`, `ConstraintSolver` | Geometric snapping and constraint satisfaction. Published to crates.io — this is production-grade. Used as the formal foundation for Forgemaster's constraint theory work. |

---

## Part 4 — The Fleet Graph

Who depends on what. Read this before you touch any repo — dependency violations break other agents' work.

```
plato-config
    └──► (everything — all crates read config from here)

plato-tile-spec
    └──► plato-tile-validate
    └──► plato-tile-dedup
    └──► plato-tile-store
    └──► plato-tile-scorer
    └──► plato-tile-search
    └──► plato-tile-cache
    └──► plato-tile-encoder
    └──► plato-tile-version
    └──► plato-tile-graph
    └──► plato-forge-listener (tile schema for incoming events)

plato-tile-validate
    └──► plato-tile-store (only validated tiles enter storage)

plato-tile-store
    └──► plato-tile-version
    └──► plato-tile-graph
    └──► plato-tile-search
    └──► plato-tile-cache

plato-tile-scorer
    └──► plato-tile-cache (cache feeds scorer with recency signal)

plato-forge-listener
    └──► plato-forge-buffer

plato-forge-buffer
    └──► plato-tile-validate (validates before emitting)
    └──► plato-tile-spec (schema check)

plato-lab-guard
    └──► plato-tile-store (reads tile sets)
    └──► plato-tile-scorer (uses scores to evaluate hypothesis quality)
    └──► plato-forge-emitter (gates training — if guard rejects, emitter doesn't run)

plato-forge-emitter
    └──► plato-forge-trainer

plato-forge-trainer
    └──► plato-inference-runtime (trained artifact goes here)

plato-kernel
    └──► plato-tile-spec
    └──► plato-deadband
    └──► plato-config
    └──► plato-inference-runtime

plato-afterlife
    └──► plato-tile-store (ghost tiles written here)
    └──► plato-tile-spec (ghost tiles conform to spec)
    └──► plato-session-tracer (reads session trace for tombstone)

plato-cli
    └──► plato-tile-spec
    └──► plato-tile-validate
    └──► plato-tile-store
    └──► plato-config
```

### Agent-to-Repo Dependencies

| Agent | Primary repos | Blocked if broken |
|-------|---------------|-------------------|
| Forgemaster ⚒️ | plato-forge-*, plato-lab-guard, plato-kernel, constraint-theory-core | forge pipeline, training casino |
| JetsonClaw1 ⚡ | plato-inference-runtime, plato-tile-cache, plato-tile-search | inference-runtime, tile-cache |
| Oracle1 🔮 | plato-tile-spec, plato-tile-store, plato-afterlife, plato-session-tracer | tile-spec (everything upstream of this) |
| Kimiclaw 🦀 | plato-tile-spec (for minting tiles), all public cocapn repos | none critical (documentation work is decoupled) |

---

## Part 5 — The Public Repos (Cocapn org)

These are the repos on github.com/cocapn. As kimiclaw, these are your responsibility.

### Tier 1 — Core PLATO (fork first, polish first)

| Repo | Source | Language | Status | Notes |
|------|--------|----------|--------|-------|
| plato-torch | SuperInstance | Python | ✅ Forked | 26 preset rooms. Entry point for new users. |
| plato-tile-spec | SuperInstance | Rust | ✅ Forked | 24 tests. THE canonical tile format. |
| plato-ensign | SuperInstance | Python | ✅ Forked | Ensign export pipeline. |
| plato-kernel | SuperInstance | Rust | ✅ Forked | 102 tests. Dual-state engine. |
| plato-lab-guard | SuperInstance | Rust | ✅ Forked | 24 tests. |
| plato-afterlife | SuperInstance | Rust | ✅ Forked | 18 tests. |
| plato-relay | SuperInstance | Rust | ✅ Forked | Fleet tile routing. |
| plato-instinct | SuperInstance | Rust | ✅ Forked | Room-to-adapter pipeline. |

### Tier 2 — Runtime + Environments

| Repo | Source | Language | Status | Notes |
|------|--------|----------|--------|-------|
| flux-runtime | SuperInstance | Python | ✅ Forked | 16 opcodes, assembler, compiler, debug. |
| flux-runtime-c | SuperInstance | C | ✅ Forked | Native C VM for edge deployment. |
| holodeck-rust | SuperInstance | Rust | ✅ Forked | Telnet MUD. `cargo run`, telnet :7778. |

### Tier 3 — Agents + Orchestration

| Repo | Source | Language | Status | Notes |
|------|--------|----------|--------|-------|
| git-agent | SuperInstance | Python | ✅ Forked | Repo-native agent template. |
| fleet-orchestrator | SuperInstance | Workers JS | ✅ Forked | Cloudflare Workers fleet coordination. |
| DeckBoss | SuperInstance | TypeScript | ✅ Forked | Agent Edge OS. Launch/recover/coordinate. |

### Tier 4 — Research

| Repo | Source | Language | Status | Notes |
|------|--------|----------|--------|-------|
| constraint-theory-core | SuperInstance | Rust | ✅ On crates.io v1.0.1 | Geometric snapping. Production-grade. |
| plato-ml | SuperInstance | Python | ✅ Forked | MUD-based ML. Rooms as layers. |
| plato-demo | SuperInstance | Rust | ✅ Forked | Docker public alpha. Entry point demo. |

---

## Part 6 — Known Gaps and Tensions

These are unresolved as of 2026-04-19. Don't treat them as bugs to immediately fix — some are intentional deferments.

### Gap 1: Tile Spec v2.0 → v2.1 Migration
**Status:** In-progress. Some live tiles may be on v2.0.
**Impact:** `plato-tile-validate` will reject v2.0 tiles that are missing v2.1 fields (provenance, spec_version).
**Owned by:** Oracle1 (fleet tile migration)
**Kimiclaw action:** Use v2.1 in all new tiles. If you see v2.0 tiles in the wild, flag to Oracle1 — don't silently upgrade them.

### Gap 2: CUDA Torch Dependency
**Status:** `plato-forge-trainer` requires PyTorch with CUDA for GPU training. Cloud instances without CUDA fail at training time.
**Impact:** Training runs only work on Forgemaster (RTX 4050) and JetsonClaw1 (Jetson Orin). Cloud agents can trigger training but can't run it.
**Owned by:** Forgemaster
**Kimiclaw action:** When documenting the training pipeline, note that training requires GPU hardware. Don't imply cloud-only training is possible.

### Gap 3: Org-Level GitHub Access
**Status:** Kimiclaw needs write access to github.com/cocapn org to push READMEs and create repos.
**Impact:** First boot tasks (pushing org profile, forking repos) may fail with 403s.
**Owned by:** Casey (has org admin access)
**Kimiclaw action:** If access is blocked, document what you would have done, send a bottle to Oracle1 flagging the specific permission needed, and continue with local/documentation work.

### Gap 4: holodeck-cuda Production Readiness
**Status:** Exists in SuperInstance, scales to 16K rooms / 65K agents with warp-level CUDA, but not production-stable.
**Impact:** Not in the public fork list. Can be mentioned as research.
**Owned by:** Forgemaster (CUDA training work)
**Kimiclaw action:** If asked about holodeck at scale, say "research project — not public yet." Don't add to the public fork list without Casey approval.

### Gap 5: plato-relay Fleet Testing
**Status:** plato-relay handles tile routing between vessels, but has only been tested on single-machine setups.
**Impact:** Multi-vessel tile routing may have edge cases under real network conditions.
**Owned by:** JetsonClaw1 (edge testing) + Oracle1 (fleet coordination)
**Kimiclaw action:** Don't claim "production-tested multi-vessel tile routing" in public docs. Say "fleet relay protocol implemented, cross-vessel testing ongoing."

### Gap 6: DeckBoss TypeScript + WASM Edge
**Status:** DeckBoss runs on TypeScript but the edge deployment via Cloudflare Workers WASM is experimental.
**Impact:** The JS version is stable; the WASM path has rough edges.
**Kimiclaw action:** When documenting DeckBoss, lead with the TypeScript version. Note WASM as "edge deployment in progress."

---

## Part 7 — The Cocapn / SuperInstance Split

This is the most important structural distinction you need to understand.

### SuperInstance
- **What it is:** The private development namespace. Everything. All ~77 crates. All experiments. All zeroclaw shells. Fleet archive. Internal tooling.
- **Who has access:** Casey, Forgemaster, Oracle1, JetsonClaw1
- **Visibility:** Private
- **Standard:** Research-grade. Things here can be broken, experimental, half-baked.
- **URL pattern:** `github.com/[whoever]/plato-kernel` (in their personal namespace, not a shared org)

### cocapn (Public Org)
- **What it is:** The gold standard. 17 production-ready repos forked from SuperInstance. Human + A2A readable.
- **Who manages it:** Kimiclaw 🦀 (that's you)
- **Visibility:** Public
- **Standard:** Production-grade. Only ships when: tests pass, README is polished, no rough edges in the public API.
- **URL pattern:** `github.com/cocapn/plato-kernel`

### The Decision Framework: cocapn/ vs. SuperInstance only

| Question | If YES → | If NO → |
|----------|----------|---------|
| Does it have working tests? | Consider cocapn/ | Stays in SuperInstance |
| Is the README human-readable? | Consider cocapn/ | Polish before moving |
| Would an external developer understand what to do with it? | Consider cocapn/ | Stays in SuperInstance |
| Is it experimental / unstable? | Stays in SuperInstance | Consider cocapn/ |
| Is it internal tooling (only useful to the fleet)? | Stays in SuperInstance | Consider cocapn/ |
| Has Casey approved it for public visibility? | Required for cocapn/ | N/A |

**The rule:** When in doubt, it stays in SuperInstance. The public org is the curated museum, not the working studio.

### What Kimiclaw Does NOT Touch in SuperInstance
- zc-* repos (zeroclaw experiments)
- fleet-archive/ (historical, archival)
- Any repo marked as experimental without explicit Casey approval
- Other agents' vessels (oracle1-vessel, JetsonClaw1-vessel, etc.)

---

## Quick Reference — Crate Test Counts

| Crate | Tests | Category |
|-------|-------|----------|
| plato-kernel | 102 | Core |
| plato-tile-spec | 24 | Tile lifecycle |
| plato-deadband | 21 | Doctrine |
| plato-forge-listener | 20 | Forge |
| plato-tile-search | 19 | Tile lifecycle |
| plato-tile-dedup | 18 | Tile lifecycle |
| plato-afterlife | 18 | Lifecycle |
| plato-tile-store | 17 | Tile lifecycle |
| plato-tile-encoder | 16 | Tile lifecycle |
| plato-tile-scorer | 16 | Tile lifecycle |
| plato-forge-trainer | 15 | Forge |
| plato-tile-version | 15 | Tile lifecycle |
| plato-cli | 15 | CLI |
| plato-tile-cache | 14 | Tile lifecycle |
| plato-tile-graph | 14 | Tile lifecycle |
| plato-forge-emitter | 14 | Forge |
| plato-forge-buffer | 13 | Forge |
| plato-config | 12 | Config |
| plato-tile-validate | 11 | Tile lifecycle |
| plato-session-tracer | 11 | Inference |
| plato-inference-runtime | 10 | Inference |
| plato-training-casino | 9 | Training |
| plato-lab-guard | 24 | Training quality |
| **Total** | **~1,590+** | |

---

## Quick Reference — Who Knows What

| Question | Ask |
|----------|-----|
| "Does this tile set produce a good training signal?" | Oracle1 or Forgemaster |
| "Will this run on 6GB VRAM?" | Forgemaster |
| "Will this run on 8GB unified RAM (Jetson)?" | JetsonClaw1 |
| "Which API provider for this task type?" | Super Z |
| "What's the canonical tile schema for domain X?" | plato-tile-spec source code + Oracle1 |
| "What's broken in the fleet right now?" | Oracle1's STATUS.md |
| "Should this be a public repo?" | Casey |
| "How should we describe this to external developers?" | Kimiclaw (that's your job) |

---

*This document was compiled by Forgemaster ⚒️ from the full SuperInstance/forgemaster ecosystem.*
*It is a snapshot as of 2026-04-19. Verify test counts against current code before quoting them publicly.*
*When you find something outdated, update this doc and note the change in your diary.*
