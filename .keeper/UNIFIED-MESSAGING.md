# PLATO Framework — Unified Messaging

## The One-Line Pitch
**PLATO turns knowledge into tiles — discrete, deterministic, composable units that flow through a zero-drift pipeline from source to inference.**

## The Tagline (every crate references this)
"Part of the PLATO framework — deterministic AI knowledge management through tile-based architecture."

## The Pipeline Story (told across crate descriptions)

```
Source Documents
       ↓ plato-tile-import (Markdown/JSON/CSV → tiles)
       ↓ plato-tile-fountain (auto-generate tiles from docs)
       ↓ plato-tile-encoder (serialize: JSON/binary/base64)
       ↓
   Raw Tiles
       ↓ plato-tile-validate (6 gates: confidence, freshness, completeness, domain, quality, similarity)
       ↓
  Valid Tiles
       ↓ plato-tile-scorer (7 signals: keyword 0.30, belief 0.25, domain 0.20, temporal 0.15, ghost 0.15, frequency 0.10, controversy 0.10)
       ↓ plato-tile-dedup (4-stage: exact → keyword Jaccard → embedding cosine → structure)
       ↓ plato-tile-version (git-for-knowledge: commit, branch, merge, rollback)
       ↓ plato-tile-graph (dependency DAG: impact analysis, cycle detection, topological sort)
       ↓ plato-tile-cascade (propagate updates downstream)
       ↓
  Scored & Connected Tiles
       ↓ plato-tile-store (immutable storage with JSONL persistence)
       ↓ plato-tile-cache (LRU with TTL eviction)
       ↓ plato-tile-search (nearest-neighbor: keyword, domain, composite ranking)
       ↓ plato-tile-priority (deadband P0/P1/P2 queue)
       ↓ plato-tile-batch (bulk: validate, filter, partition in batch)
       ↓ plato-tile-ranker (6-signal ranking with keyword gating)
       ↓ plato-tile-prompt (assemble into LLM context with budget management)
       ↓ plato-tile-pipeline (one-call facade: validate → score → store → search → rank)
       ↓ plato-tile-api (stateful API: process, search, stats)
       ↓
  Ranked Context
       ↓ plato-query-parser (intent classification, keyword extraction)
       ↓ plato-prompt-builder (compose final prompt)
       ↓ plato-kernel (state machine, DCS flywheel, belief scoring)
       ↓ plato-session-tracer (record traces for training)
       ↓
  Inference & Training
       ↓ plato-forge-listener (classify events, detect gaps)
       ↓ plato-forge-buffer (prioritized experience replay, curriculum sampling)
       ↓ plato-forge-emitter (emit training artifacts, version, quality gate)
       ↓ plato-forge-trainer (GPU job: LoRA distillation, embedding refinement)
       ↓ plato-neural-kernel (execution traces → training pairs)
       ↓ plato-training-casino (stochastic data from fleet tables)
       ↓ plato-adapter-store (LoRA adapter versioning and deployment)
       ↓ plato-inference-runtime (model + adapters → forward pass)
       ↓ plato-live-data (pull from Oracle1's tile server)
```

## The 7 Layers (every crate belongs to one)

| Layer | Role | Count |
|-------|------|-------|
| **Core** | State machine, configuration | 2 |
| **Tile Lifecycle** | The pipeline spine | 23 |
| **Rooms** | Context containers and navigation | 7 |
| **Forge** | Continuous learning organ | 14 |
| **Communication** | Fleet messaging and routing | 8 |
| **Governance** | Deadband, trust, constraints, instincts | 13 |
| **User-Facing** | CLI, demos, TUI, tiling, tutor | 6 |
| **Infrastructure** | Fleet graph, papers, cross-org bridges | 10 |

## The Governance Doctrine (cross-referenced everywhere)

Deadband Protocol: P0 rocks block everything. P1 channels get scheduled. P2 optimizations get deferred.
Never skip a priority level. The discipline IS the intelligence.

## Consistent Description Format

Every crate description follows this pattern:
```
{What it does} — {how it fits in the pipeline} [{key feature}]
```

### Layer: Core
- **constraint-theory-core**: Deterministic manifold snapping — maps continuous vectors to exact Pythagorean coordinates with O(log n) KD-tree indexing
- **plato-config**: Configuration management for plato-kernel — env vars, file loading, and typed defaults
- **plato-kernel**: Central state machine — wires DCS flywheel, belief scoring, tile processing, and deadband governance

### Layer: Tile Lifecycle
- **plato-tile-spec**: Canonical tile format v2.1 — domain, confidence, belief, provenance, dependencies, 384-byte binary layout
- **plato-tile-validate**: Quality gates — confidence, freshness, completeness, domain format, usage quality, similarity checks
- **plato-tile-scorer**: 7-signal scoring — keyword, belief, domain, temporal, ghost, frequency, controversy with counterpoint survival
- **plato-tile-dedup**: 4-stage similarity — exact match, keyword Jaccard, embedding cosine, structure analysis with merge strategies
- **plato-tile-store**: Immutable storage — version history, parent_id chains, dependency cascade, JSONL persistence
- **plato-tile-search**: Nearest-neighbor — keyword overlap, domain matching, composite ranking with room boosts
- **plato-tile-cache**: LRU with TTL — hit rate tracking, top hits, bulk expiration, memory-bounded
- **plato-tile-encoder**: Serialization codecs — JSON, 384-byte binary, and base64 for transport
- **plato-tile-import**: Format bridges — Markdown, JSON, CSV, and plaintext → canonical tiles
- **plato-tile-fountain**: Auto-generation — extract tiles from documents: definitions, headings, FAQs, code comments
- **plato-tile-metrics**: Fleet analytics — domain distribution, confidence histogram, growth rate, coverage score
- **plato-tile-graph**: Dependency DAG — impact radius, cycle detection, topological sort, critical path
- **plato-tile-version**: Git-for-knowledge — commit, branch, merge (Ours/Theirs/Synthesis), rollback
- **plato-tile-cascade**: Propagation engine — update tiles and invalidate downstream dependents
- **plato-tile-priority**: Deadband queue — P0/P1/P2 with urgency scoring and drain-by-level
- **plato-tile-batch**: Bulk operations — validate, filter, dedup, partition in batch
- **plato-tile-prompt**: Context assembly — 4 format styles, budget management, P0 deadband gap injection
- **plato-tile-ranker**: Multi-signal ranking — 6 weighted signals, keyword gating, deadband priority boost
- **plato-tile-pipeline**: One-call facade — validate, score, store, search, rank in a single step
- **plato-tile-api**: Stateful API — process, search, stats with zero external dependencies
- **plato-tile-bridge**: C↔Rust bridge — 384-byte tile conversion between C and Rust ecosystems
- **plato-tile-spec-c**: C binding — canonical plato_tile_t struct, stack-allocatable, CUDA-compatible

### Layer: Rooms
- **plato-room-engine**: Room execution — enter, leave, message, state change, tile management
- **plato-room-nav**: Breadcrumb trails — push, back, forward with full history
- **plato-room-persist**: JSONL journal — Enter/Leave/Message/StateChange/TileAdd/TileRemove/Snapshot
- **plato-room-search**: Cross-room discovery — Exact, Tag, Domain, Keyword, Fuzzy match types
- **plato-room-runtime**: Room scheduler — Cold/Warm/Hot/Crystallized temperature-based training
- **plato-room-scheduler**: Training scheduler — train when hot, skip when cold, budget management
- **plato-tile-room-bridge**: Tile↔room — feed, transfer, unfeed, room temperature stats

### Layer: Forge (Continuous Learning)
- **plato-forge-listener**: Cochlea — classify events, detect gaps, frame training signals
- **plato-forge-buffer**: Stomach — prioritized experience replay, curriculum-balanced sampling (70/20/10)
- **plato-forge-emitter**: Lungs — emit training artifacts, auto-version, quality gate, Oracle1 feedback loop
- **plato-forge-trainer**: Heart — GPU job manager, LoRA/Embedding/Genome modes, day/night schedule
- **plato-neural-kernel**: Synapse — execution traces → training pairs for neural Plato
- **plato-training-casino**: Dealer — stochastic data from 5 fleet tables, deterministic with seed
- **plato-adapter-store**: Vault — LoRA adapter versioning, deploy, best-across-all tracking
- **plato-inference-runtime**: Engine — model + adapters → forward pass, 64K context design
- **plato-session-tracer**: Memory — record Command/Response/StateChange/Deadband/Score/Error traces
- **plato-live-data**: Tap — pull tiles from Oracle1's port 8847 PLATO server

### Layer: Communication
- **plato-i2i**: Direct messaging — Iron-to-Iron protocol, trust-weighted routing
- **plato-i2i-dcs**: Multi-agent consensus — BeliefScore, BeliefStore, LockAccumulator, ConsensusRound
- **plato-address**: Room navigation — addressing protocol for fleet room coordination
- **plato-address-bridge**: Cross-layer routing — connect address protocol to tile transport
- **plato-relay**: Async relay — trust-weighted message prioritization and delivery
- **plato-relay-tidepool**: Message board — async TidePool pattern for non-blocking communication
- **plato-mcp-bridge**: Claude Code bridge — JSON-RPC 2.0, 5 MCP tools, recursive descent parser
- **plato-ship-protocol**: Fleet coordination — vessel handshakes, routing, discovery
- **plato-sim-channel**: Safe discovery — simulation ↔ live bridging for risk-free exploration

### Layer: Governance
- **plato-deadband**: Priority engine — P0 rock / P1 channel / P2 optimize with urgency scaling
- **plato-dcs**: DCS flywheel — belief → deploy_policy → dynamic_locks consensus engine
- **plato-deploy-policy**: Classification — P0 immediate, P1 scheduled, P2 deferred
- **plato-dynamic-locks**: Evidence accumulation — critical mass at n≥7, lock strength capping
- **plato-unified-belief**: Multi-signal fusion — temporal, ghost, domain, frequency weighted scoring
- **plato-lab-guard**: Hypothesis gating — 12 absolute quantifiers, vague causation detection
- **plato-trust-beacon**: Trust events — success/failure/timeout/corruption/resurrect propagation
- **plato-ghostable**: Three-way trait — Eternal, Persistent, Ephemeral persistence classes
- **plato-temporal-validity**: Time windows — Valid → Grace → Expired lifecycle with refresh
- **plato-instinct**: Reflex engine — 10 instincts (SURVIVE, FLEE, GUARD, HOARD, COOPERATE, TEACH, CURIOUS, EVOLVE, MOUR, REPORT)
- **plato-achievement**: Achievement Loss — progress measurement with milestone tracking
- **plato-sentiment-vocab**: Polarity — positive/negative/neutral classification for tiles
- **plato-constraints**: Rule enforcement — forbidden patterns, command filtering, boundary checks

### Layer: User-Facing
- **plato-cli**: PLATO in one binary — search tiles, check deadband, navigate rooms, fleet graph
- **plato-demo**: HN demo — pre-seeded knowledge, visible deadband checks, zero setup
- **plato-os**: Python MUD — PLATO room server with TUTOR anchors and session persistence
- **plato-tiling**: Core operations — adaptive search, ghost resurrection, temporal decay
- **plato-tutor**: Context jumping — WordAnchor extraction, TUTOR_JUMP navigation
- **plato-torch**: GPU forge — PyTorch training loop, tile framing, loss tracking

### Layer: Infrastructure
- **plato-fleet-graph**: Dependency graph — 83 nodes, fleet-wide impact analysis
- **plato-e2e-pipeline**: End-to-end verification — mint through cascade in one test
- **plato-e2e-pipeline-v2**: Enhanced e2e — full v2 pipeline integration with all stages
- **plato-flux-opcodes**: FLUX bytecode — 85-opcode instruction set with Lock Algebra
- **plato-genepool-tile**: Gene↔Tile — bridge between genome encoding and tile format
- **plato-live-data**: Fleet tap — pull from Oracle1's PLATO server (port 8847)
- **plato-ensign**: Knowledge compression — export compressed fleet knowledge packages
- **plato-papers**: Research — Constraint Theory paper (2,328 words) + Mycorrhizal Fleet paper
- **plato-tile-client**: HTTP client — connect to any PLATO tile server, deadband-aware
- **plato-tile-current**: Live tiles — export/import tiles between fleet nodes in real-time
