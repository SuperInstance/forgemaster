# Spreader-Tool: Claude Opus Development Briefing

**Purpose:** Self-contained briefing for Claude Code Opus to produce schemas, development guides, and initial implementation code.  
**Audience:** Claude Opus — knows NOTHING about SuperInstance or PLATO.  
**Date:** 2026-05-17

---

## Who We Are

**SuperInstance** is an AI fleet architecture built around PLATO rooms — edge-deployable, modular inference containers that run micro-models for specific tasks. Think of a PLATO room as a smart node in a distributed system: it has its own inference engine, its own task domain, its own sensors/actuators, and it talks to other rooms via a P2P gossip protocol called Murmur. The fleet has 9 AI agents coordinating across 1,400+ repositories.

The SuperInstance ecosystem includes: **plato-types** (tile lifecycle, Lamport clocks), **tensor-spline** (Eisenstein lattice weight parameterization — novel compression), **plato-data** (data loading pipelines), and **plato-training** (micro-model training and hardware deployment). These are 4 independent, pip-installable Python packages. The fleet has already deployed micro-models to 8 hardware targets with real results: 100% accuracy on drift-detect for 5/6 targets, sub-millisecond inference on all CPU targets. The SplineLinear compression achieves 20× parameter reduction at same accuracy.

## What We're Building

**The Spreader-Tool** is a mechanism for "intelligence tiling" — progressively filling the gaps in a micro-model's coverage by freezing snapshots of successful reasoning, validating them, and locking them as deployable "seeds."

Here's the problem it solves: In open logic systems (where inputs aren't bounded), micro-models inevitably encounter situations they can't handle. These situations fall into the **deadband** — the gap between what hardcoded rules can handle and what requires full LLM inference. The deadband is expensive (escalating to LLM every time) and dangerous (if the system just fails silently).

The Spreader-Tool watches for deadband entry, captures the system's reasoning state at that moment (a **Frozen Context Window**), and uses those captures to progressively "tile" the deadband with validated intelligence. When enough tiles cover a region, they get locked into a **Seed** — a guaranteed-good checkpoint that can be deployed to any room handling that task type.

**Analogy:** Imagine a self-driving car that encounters a new intersection type. Instead of sending every frame to the cloud, it freezes a snapshot of what it was thinking, flags the gap, and gradually builds up a "known good" response pattern for that intersection type. Once validated, that pattern becomes a seed that any car in the fleet can use.

## The Architecture

### Core Algorithm (8-Step Loop)

Every PLATO room runs this loop on a configurable tick interval (default: 10 seconds):

```
1. CAPTURE STATE — sample room state, KPIs, peer sync status
2. UPDATE SLIDING WINDOWS — aggregate into rolling windows (default: 60s)
3. CREATE FROZEN SNAPSHOT — if trigger conditions met → freeze FCW
4. CHECK DEADBAND — are KPIs below thresholds?
5. CHECK ESCALATION — if deadband AND MAE > threshold → escalate to LLM
6. RUN LOCAL INFERENCE — micro-model inference using locked seed
7. UPDATE SEED LOCK — evaluate candidates, validate, lock if qualified
8. SYNC WITH PEERS — Murmur gossip: share FCWs, seed updates, status
```

### Deadband Definition

A room is "in deadband" when ANY of these thresholds are breached for the minimum duration:

| Metric | Threshold | Duration |
|--------|-----------|----------|
| Task completion rate | < 90% | 5+ minutes |
| Average wait time | > 30 seconds | sustained |
| Energy over baseline | > 10% | sustained |
| Inference MAE | > 10% | 3 consecutive windows |

### Data Structures

#### FrozenContextWindow (FCW)

The immutable snapshot of reasoning state:

```python
@dataclass
class FrozenContextWindow:
    # Core identity
    fcw_id: UUID                    # UUIDv7, time-ordered
    frozen_at: datetime             # ISO 8601
    room_id: str
    room_type: RoomType             # SENSOR | COLLAB_ANALYSIS | COMMAND | SIMULATION
    origin_trigger: TriggerType     # TIME | THRESHOLD | CONTEXT_SHIFT | CRITICAL_CALL | MANUAL
    parent_fcw_id: Optional[UUID]   # lineage tracking
    
    # Reasoning state
    working_memory: List[MemoryChunk]       # [(chunk_id, content, access_count)]
    active_hypotheses: List[Hypothesis]     # [(id, description, confidence, evidence_for, evidence_against)]
    tool_call_history: List[ToolCall]
    sensor_window: SensorData               # recent readings
    error_logs: List[ErrorEntry]
    
    # Lifecycle
    status: FCWStatus               # STAGING → FROZEN → TESTING → REFINING → LOCKED → DISCARDED
    snapshot_version: int
    reasoning_cycle_count: int
    global_confidence_score: float  # 0.0 - 1.0
    
    # Room-specific extensions (JSONB validated against schema registry)
    extensions: dict
```

#### Seed

A validated, performance-guaranteed checkpoint:

```python
@dataclass
class Seed:
    seed_id: UUID
    room_id: str
    role_name: str                  # what task this seed handles
    lineage_id: UUID                # evolution chain tracking
    
    # The actual intelligence
    micro_model_weights: bytes      # serialized (SplineLinear-compressed in production)
    context_window_ids: List[UUID]  # FCWs that informed this seed
    locked_kpi_metrics: dict        # performance at lock time
    
    # Lifecycle
    state: SeedState                # UNLOCKED → CANDIDATE → VALIDATING → LOCK_PENDING → LOCKED → DEPRECATED → ARCHIVED
    version_major: int
    version_minor: int
    
    # Validation
    backtest_results: dict          # performance/runtime/dataset validation results
    
    # Timestamps
    created_at: datetime
    locked_at: Optional[datetime]
    deprecated_at: Optional[datetime]
```

#### Seed State Machine

```
UNLOCKED ──submit──→ CANDIDATE ──queue──→ VALIDATING ──pass──→ LOCK_PENDING ──approve──→ LOCKED
                                  │                          │                            │
                              fail│                      fail │               escalate──→ ESCALATING
                                  ↓                          ↓                   │         │
                          VALIDATION_FAILED            (back to       resolved───┘    deprecated
                          (fix & resubmit)              CANDIDATE)                       
                                                                       superseded──→ DEPRECATED ──→ ARCHIVED
                                                                                         
                    ARCHIVED ──emergency_restore──→ LOCKED (admin only)
```

### Refinement/Redaction Protocol

Not all intelligence is worth keeping. The system measures cost:

```
NTIC_total = w1 × NTIC_model + w2 × NTIC_context
```

And prunes based on a refinement gradient:

```
G(i) = ΔB(i) / ΔNTIC(i)

G > 0 → intelligence pays for itself (expand)
G ≈ 0 → diminishing returns (hold)
G < 0 → over-invested (prune)
```

Redaction tiers by compliance:
- **High compliance (≥95% completion, ≤5% MAE):** Keep aggregated metrics only
- **Medium (90-95%, 5-10% MAE):** Aggregated + 1Hz compressed samples
- **Low (<90%, >10% MAE, deadband):** Full metrics + 10Hz raw + peer logs
- **Seed-locked:** Everything, permanently

### Parallel-Sequential DAG

The orchestration DAG for multi-room operations:

```
T0: Deadband Detected
 │
 ├──→ P1: Slice Frozen Context Windows     ─┐
 ├──→ P2: Run Murmur Gossip Probes         ─┤  PARALLEL
 ├──→ P3: Generate Local Refinement Candidates ┘
 │                                          
 S1: Acquire Seed Lock          ←──────────┘
 │
 S2: Validate Frozen Window Consistency      SEQUENTIAL
 │
 S3: Merge Parallel Results
 │
 S4: Resolve Conflicts
 │
 S5: Refine/Redact
 │
 S6: Escalation Gate Check
 │
 S7: Update System Seed
 │
 S8: Release Seed Lock
```

Conflict resolution: weighted voting (source credibility × confidence score), with escalation for ties or total confidence < 0.7.

### Convergence Theory

```
d(t) = |D(t)| / |D(0)|    (deadband coverage ratio)

Proven monotonically convergent if G(i) > 0 for all refinement steps.

d_min exists (irreducible deadband) — tasks beyond micro-model capacity.
These are permanently escalated to LLM and logged to Model Ocean.
```

## Connection to Existing Code

### Repos to Reference

| Repo | URL | What It Has | Why It Matters |
|------|-----|-------------|----------------|
| **plato-types** | `github.com/SuperInstance/plato-types` | Tile lifecycle, Lamport clocks, TrainingTile | Spreader tiles are a new tile type — extends this |
| **tensor-spline** | `github.com/SuperInstance/tensor-spline` | SplineLinear compression, LowRank, Hierarchical | Used to compress seed weights for edge deployment |
| **plato-data** | `github.com/SuperInstance/plato-data` | CSV/JSONL/PLATO/fleet data loading | Load FCW data for backtesting |
| **plato-training** | `github.com/SuperInstance/plato-training` | Micro-models, hardware deploy, rooms, PyTorch/TF rooms | Spreader integrates into the Room protocol here |
| **forgemaster** | `github.com/SuperInstance/forgemaster` | Forgemaster agent code, fleet coordination | Agent that runs the Spreader |
| **casting-call** | `github.com/SuperInstance/casting-call` | Model capability database | Which models to cast into which Spreader roles |

### Existing Code Patterns to Follow

1. **Tile types** in `plato-types`: `TrainingTile`, `TileLifecycle`, `LamportClock`. The Spreader introduces new tile types: `FrozenContextWindowTile`, `SeedTile`.

2. **Room protocol** in `plato-training`: `PyTorchRoom`, `TensorFlowRoom`. The Spreader adds a `SpreaderRoom` mixin that any room can use.

3. **SplineLinear** in `tensor-spline`: `SplineLinear.forward()`, `SplineLinear.save()`, `SplineLinear.load()`. Used for compressing seed weights.

4. **Micro-models** in `plato-training/training/micro_models.py`: 8 task types, 8 hardware targets. Seeds wrap these with validation.

5. **CLI pattern** in `plato-training/cli.py`: 470-line CLI using click. Spreader adds `plato-spread` subcommands.

6. **Tests** in `plato-training/tests/`: 69 tests passing. Pattern: pytest with fixtures for room configs.

### What's Already Built

- Micro-model training pipeline (8 tasks × 8 targets = 48 combos)
- Hardware deployment (CPU, NPU, GPU, TPU variants)
- SplineLinear compression (20× at same accuracy)
- LoRA adapter save/load
- Training throttle (fleet-aware)
- Lamport clocks for ordering
- LocalTileStore (content-addressed)
- CLI with full lifecycle management

### What's NOT Built (Spreader adds this)

- Frozen Context Window creation, lifecycle, storage
- Seed locking state machine and validation
- Deadband detection and monitoring
- Refinement/redaction protocol
- Parallel-sequential DAG orchestration
- Murmur integration for peer sync
- Escalation gate with LLM routing
- Spectral conservation monitoring
- Model Ocean integration

## Development Guide

### Phase 1: MVP (2-3 weeks) — Prove the concept in a single room

**Goal:** One room can detect deadband, freeze context windows, and lock seeds. No peers, no Murmur, no spectral monitoring.

**Files to create, in order:**

```
spreader/
├── __init__.py
├── types.py                    # FCW, Seed, SeedState, FCWStatus enums
├── deadband.py                 # DeadbandDetector class
├── frozen_context.py           # FCW creation, lifecycle, storage
├── seed_lock.py                # Seed state machine (simplified: UNLOCKED→CANDIDATE→LOCKED)
├── backtest.py                 # Backtest validation for seeds
├── spreader_room.py            # SpreaderRoom mixin (add to any PLATO room)
├── store.py                    # LocalSpreaderStore (content-addressed FCW/Seed storage)
├── cost.py                     # NTIC calculation, refinement gradient
├── redaction.py                # Refinement/redaction protocol
└── cli.py                      # plato-spread CLI
```

**Implementation order:**

1. `types.py` — All data structures, enums, dataclasses. No dependencies.
2. `deadband.py` — DeadbandDetector with configurable thresholds. Depends on types.
3. `frozen_context.py` — FCW lifecycle (create → freeze → test → lock). Depends on types.
4. `store.py` — Content-addressed storage for FCWs and Seeds. Depends on types.
5. `backtest.py` — Validate a seed candidate against historical FCWs. Depends on types, store.
6. `seed_lock.py` — Simplified state machine (3 states only for MVP). Depends on types, backtest.
7. `cost.py` — NTIC and refinement gradient calculations. Depends on types.
8. `redaction.py` — Pruning protocol. Depends on cost, store.
9. `spreader_room.py` — Mixin that wires everything together into the 8-step loop. Depends on all above.
10. `cli.py` — Command-line interface for manual operations. Depends on all above.

**Tests to write alongside:**

```
tests/
├── test_types.py               # Data structure validation
├── test_deadband.py            # Threshold detection, edge cases
├── test_frozen_context.py      # FCW lifecycle transitions
├── test_store.py               # Content-addressed storage, retrieval
├── test_backtest.py            # Validation pass/fail cases
├── test_seed_lock.py           # State machine transitions, guards
├── test_cost.py                # NTIC calculation, gradient computation
├── test_redaction.py           # Pruning with coverage guarantees
└── test_spreader_room.py       # Integration test: full 8-step loop
```

### Phase 2: Core (4-6 weeks) — Multi-room with real coordination

Adds Murmur integration, full seed state machine, escalation gate, DAG orchestration.

**Additional files:**

```
spreader/
├── murmur_sync.py              # Peer sync via Murmur gossip protocol
├── escalation.py               # Automatic LLM escalation gate
├── dag.py                      # Parallel-sequential DAG orchestration
├── conflict.py                 # Weighted voting conflict resolution
├── full_seed_lock.py           # Complete 8-state seed machine (replaces simplified version)
└── protobuf/
    ├── fcw.proto               # Protobuf schema for FCWs
    └── seed.proto              # Protobuf schema for Seeds
```

### Phase 3: Fleet (6-8 weeks) — Production scale

Adds spectral monitoring, Model Ocean, SplineLinear compression, fleet-wide propagation.

**Additional files:**

```
spreader/
├── spectral.py                 # Eigenvalue monitoring of task similarity matrix
├── model_ocean.py              # Irreducible deadband logging + model selection
├── compression.py              # SplineLinear seed weight compression
├── fleet_propagation.py        # Fleet-wide seed propagation via Murmur
├── adaptive_sampling.py        # Priority weighting, deduplication
└── safety.py                   # Safety validation at every inference step
```

## Schemas for Other Agents

### GLM-5.1 Subagent Schema

When spawning GLM-5.1 coding agents to implement individual modules:

```json
{
  "agent": "glm-5.1",
  "task_template": {
    "module": "<module_name>",
    "input_types": ["<types this module depends on>"],
    "output_type": "<what this module produces>",
    "interfaces": ["<methods/classes to implement>"],
    "tests_required": ["<test descriptions>"],
    "constraints": [
      "python 3.10+",
      "type hints required",
      "dataclasses for all data structures",
      "asyncio for I/O operations",
      "pytest for tests",
      "No external ML dependencies in types/deadband/store",
      "pytorch only in backtest and seed_lock"
    ]
  }
}
```

### CRUSH Agent Integration Points

CRUSH agents (automated code review) should validate:

1. **State machine guards:** Every SeedState transition has explicit guard clauses
2. **Immutability:** FCWs never modified after FROZEN status
3. **Cost tracking:** Every intelligence operation logged to NTIC
4. **Backtest coverage:** Seeds must pass performance + runtime + dataset validation
5. **Redaction compliance:** No raw data retained for high-compliance windows

## Key Insights from Research

### From Seed-2.0-mini (Primary Architect)

1. **The irreducible deadband is honest engineering.** Some tasks can't be handled by micro-models. The system must acknowledge this and escalate permanently rather than thrashing.
2. **Refinement gradient G(i) = ΔB/ΔNTIC** quantifies whether intelligence is worth its cost. This is the single most important metric.
3. **Redaction tiers prevent storage blowup.** High-compliance windows are aggressively pruned; low-compliance windows are preserved for analysis.

### From Qwen3.6-35B (Simplifier)

1. **The simplest version is a confidence-based cascade.** Router → micro-model → escalate. Everything else is optimization.
2. **Async backtesting is strictly better than sync.** Never block the 8-step loop for validation.
3. **Compressed embeddings work for MVP.** Full FCW schemas are Phase 2.

### From Hermes-70B (Theorist)

1. **Deadband connects to deep theory.** It's not just an engineering gap — it's related to sharding, DHTs, hierarchical RL, and phase transitions.
2. **The genuinely novel contributions are:** progressive intelligence tiling, frozen context windows, Model Ocean ecosystem, seed-locking + parallel-sequential mixing.
3. **Spectral conservation (eigenvalue monitoring) catches what cost budgets miss.** It detects distributional shift, not just cost overruns.

### Synthesis: What to Believe

- **Qwen is right about the MVP.** Build the simple router-cascade first.
- **Seed is right about the full architecture.** The complexity is justified for production.
- **Hermes is right about what's novel.** The deadband concept and intelligence tiling are the research contributions worth publishing.
- **Build Qwen's version first, then add Seed's complexity incrementally.**

## What to Build First (Ordered List)

This is the exact priority order for implementation:

1. **`spreader/types.py`** — All data structures (FCW, Seed, enums, dataclasses). ~200 lines. Every other module imports this.

2. **`spreader/deadband.py`** — DeadbandDetector class. ~100 lines. Input: KPI metrics. Output: boolean (in deadband or not) + deadband severity score.

3. **`spreader/frozen_context.py`** — FCW lifecycle manager. ~250 lines. Create, freeze, test, refine, lock, discard. Immutable after frozen.

4. **`spreader/store.py`** — Content-addressed storage. ~150 lines. Store/retrieve FCWs and Seeds by hash. File-based for MVP (SQLite or filesystem).

5. **`spreader/backtest.py`** — Seed validation. ~200 lines. Run candidate seed against historical FCWs. Pass/fail on performance, runtime, and dataset criteria.

6. **`spreader/seed_lock.py`** — Simplified 3-state machine (UNLOCKED → CANDIDATE → LOCKED). ~150 lines. Guard clauses for each transition.

7. **`spreader/cost.py`** — NTIC calculation and refinement gradient. ~100 lines. Input: seed/FCW metadata. Output: cost scores, gradient values.

8. **`spreader/redaction.py`** — Pruning protocol. ~200 lines. Tiered redaction with coverage guarantees. Stops pruning when coverage drops below threshold.

9. **`spreader/spreader_room.py`** — The 8-step loop as a mixin. ~300 lines. Wires deadband detection, FCW creation, seed locking, and redaction into the room tick cycle.

10. **`spreader/cli.py`** — Command-line interface. ~200 lines. Subcommands: `deadband-status`, `freeze`, `list-fcws`, `seed-candidates`, `lock-seed`, `backtest`, `redact`.

11. **`tests/`** — One test file per module. ~150 lines each. Total ~1,500 lines of tests.

**Total MVP: ~2,000 lines of code + ~1,500 lines of tests.**

---

*This briefing is self-contained. No additional context about SuperInstance, PLATO, or the fleet is needed to begin implementation.*
