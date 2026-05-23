# Spreader-Tool Architecture

**Date:** 2026-05-17  
**Status:** Design Phase — Multi-model review complete  
**Synthesized from:** 7-round Seed-2.0-mini iteration + Qwen3.6-35B + Hermes-70B critique

---

## 1. Core Concept: Intelligence Tiling for Deadband in Open Logic Systems

### The Problem

In edge-deployed PLATO rooms, micro-models handle inference for bounded tasks. But systems are **open** — new inputs, shifting distributions, novel edge cases appear constantly. There's a region where hardcoded rules fail and full LLM inference is too expensive or slow. This region is the **deadband**.

### Deadband (Formal Definition)

The set of state transitions where existing rules and micro-models cannot maintain KPIs within acceptable bounds. Operationally:

| Condition | Threshold |
|-----------|-----------|
| Task completion rate | < 90% sustained for 5+ minutes |
| Average wait time | > 30 seconds |
| Energy consumption | > 10% above baseline |
| Inference MAE | > 10% for 3 consecutive windows |

### The Spreader-Tool

A mechanism that **spreads intelligence** — progressively tiling the deadband with frozen context windows, locked seeds, and micro-model refinements until coverage is sufficient. It doesn't deploy a bigger model; it deploys smarter structure.

**Key insight:** The deadband is the research agenda. The gaps between what micro-models can do and what the system needs ARE the work.

---

## 2. The Spreader Algorithm (Formalized)

### Global Constants

```python
WINDOW_DURATION: float = 60.0       # Fixed context window length (seconds)
TICK_INTERVAL: float = 10.0         # Period between core loop ticks
BASELINE_COMPLETION: float = 90.0   # Baseline task completion %
DEADBAND_MIN_DURATION: float = 300.0  # 5 minutes
ESCALATION_MAE_THRESHOLD: float = 10.0
SEED_LOCK_KPI: float = 95.0         # Must sustain for seed lock
SEED_LOCK_DURATION: float = 604800.0  # 7 days sustained performance
```

### Core 8-Step Loop

```
1. CAPTURE STATE
   └─ Sample room state: sensor readings, KPIs, peer sync status

2. UPDATE SLIDING WINDOWS
   └─ Aggregate into rolling windows of WINDOW_DURATION

3. CREATE FROZEN SNAPSHOT
   └─ If trigger conditions met → freeze a FrozenContextWindow

4. CHECK DEADBAND
   └─ Evaluate: is this room in deadband? (KPIs below thresholds)

5. CHECK ESCALATION
   └─ If deadband AND MAE > threshold → escalate to LLM

6. RUN LOCAL INFERENCE
   └─ Micro-model inference on current state using locked seed

7. UPDATE SEED LOCK
   └─ Evaluate seed candidates, validate, lock if qualified

8. SYNC WITH PEERS
   └─ Murmur gossip: share frozen windows, seed updates, status
```

### Convergence Metric

```
d(t) = |D(t)| / |D(0)|
```

Where D(t) is the set of unhandled deadband states at time t. The system converges monotonically if the refinement gradient G(i) > 0 for all refinement steps.

**Irreducible deadband:** When tasks require capabilities beyond micro-model capacity, the system flags them as irreducible, logs to Model Ocean for future fine-tuning, and permanently escalates that task type to LLM. This establishes d_min — the irreducible lower bound.

---

## 3. Frozen Context Windows (FCW)

### What They Are

Immutable snapshots of a PLATO room's reasoning state at a point in time. They're the "tiles" of intelligence that the Spreader spreads across the deadband.

### FCW Schema

```
FCW (FrozenContextWindow)
├── Core
│   ├── fcw_id: UUIDv7
│   ├── frozen_at: ISO 8601
│   ├── room_id, room_type (SENSOR|COLLAB_ANALYSIS|COMMAND|SIMULATION)
│   ├── origin_trigger, parent_fcw_id
│   ├── reasoning_cycle_count, global_confidence_score
│   ├── status: STAGING → FROZEN → TESTING → REFINING → LOCKED → DISCARDED
│   └── snapshot_version
├── Reasoning State
│   ├── working_memory: [(chunk_id, content, access_count)]
│   ├── active_hypotheses: [(id, description, confidence, evidence_for, evidence_against)]
│   ├── tool_call_history
│   ├── recent_sensor_window
│   └── error_logs
└── Extensions
    └── room_specific: JSONB (validated against room-type schema registry)
```

### Freezing Triggers

| Type | Condition |
|------|-----------|
| Time-based | Fixed interval (configurable per room) |
| Threshold | Confidence shift > 0.2, HIGH-severity error |
| Context shift | Sensor readings out of expected range |
| Critical tool call | Post-call capture |
| Manual | Operator-initiated |

### Sampling Strategy

- **Priority weighting:** Critical rooms sampled 5x more frequently
- **Deduplication:** Skip windows identical to last frozen (hash-based)
- **Adaptive:** Increase frequency during rapid changes, reduce during stability

### Compression

| Stage | Method | Purpose |
|-------|--------|---------|
| On-edge active | LZ4/Snappy | Speed |
| Wire transfer | Protobuf | 30-50% smaller than JSON |
| Sequential data | Delta encoding | Sensor streams |
| Long-term archival | Zstandard | Maximum compression |

---

## 4. Seed Locking Mechanism

### What Is a Seed?

A seed is a validated, performance-guaranteed snapshot of a micro-model's weights + context that can be deployed with confidence. Think of it as a "known-good checkpoint" for a specific room/task combination.

### Seed Data Structure

```sql
CREATE TABLE seeds (
    seed_id         UUID PRIMARY KEY,
    room_id         TEXT NOT NULL,
    role_name       TEXT NOT NULL,
    lineage_id      UUID NOT NULL,        -- tracks evolution chain
    current_state   TEXT NOT NULL,         -- state machine position
    micro_model_weights BYTEA,            -- serialized weights
    context_window_ids   UUID[],           -- FCWs that informed this seed
    locked_kpi_metrics   JSONB,            -- performance at lock time
    created_at      TIMESTAMPTZ,
    locked_at       TIMESTAMPTZ,
    deprecated_at   TIMESTAMPTZ,
    backtest_results JSONB,
    version_major   INT,
    version_minor   INT
);
```

### State Machine

```
UNLOCKED ──→ CANDIDATE ──→ VALIDATING ──→ LOCK_PENDING ──→ LOCKED
                │               │                              │
                │          VALIDATION_FAILED                   ├──→ ESCALATING ──→ LOCKED (resolved)
                │               │                              │              └──→ DEPRECATED
                └─── (fix) ←────┘                              └──→ DEPRECATED ──→ ARCHIVED
                                                                     ↑
                                                              (superseded by new seed)
```

### Guards

- Every state transition requires explicit guard clauses
- Backtest must pass **performance**, **runtime**, AND **dataset** validation
- LOCK_PENDING requires human approval for safety-critical rooms
- LOCKED → DEPRECATED requires a superior replacement seed to exist

---

## 5. Refinement/Redaction Protocol

### Intelligence Cost Measurement

```
NTIC_total = w1 × NTIC_model + w2 × NTIC_context

NTIC_model   = normalize(params, FLOPs, latency, memory)
NTIC_context = normalize(token_count, retrieval_latency)
```

### Redaction Tiers

| Compliance Level | Criteria | What's Kept |
|-----------------|----------|-------------|
| **High** (≥95% completion, ≤5% MAE) | System working well | Aggregated metrics only; discard raw time-series |
| **Medium** (90-95%, 5-10% MAE) | Borderline | Aggregated + 1Hz compressed samples |
| **Low** (<90%, >10% MAE, deadband) | System struggling | Full metrics + 10Hz raw + peer sync logs |
| **Seed-Locked** | Audit trail | Everything, permanently |

### Pruning Algorithm

```
1. Establish baseline coverage benchmark
2. Rank entries by:
   - Value Score (VS): marginal coverage contribution
   - Redundancy Score (RS): similarity to nearby entries
3. Iteratively remove: lowest VS + highest RS
4. After each removal: re-benchmark coverage
5. Stop when coverage drops below threshold T
```

### Refinement Gradient

```
G(i) = ΔB(i) / ΔNTIC(i)
```

- G > 0: Intelligence is paying for itself — keep expanding
- G ≈ 0: Diminishing returns — hold
- G < 0: Over-invested — prune

### Triggers

- **Event-driven:** Deadband shift (CGR > 0.15), cost threshold breach, manual override, critical failure
- **Periodic:** 10K steps or 24 hours, whichever comes first
- **Cooldown:** Minimum 5 minutes between refinement cycles

---

## 6. Parallel vs Sequential Orchestration

### Task Decomposition

| Category | Tasks | Why |
|----------|-------|-----|
| **Parallelizable** | FCW slicing, Murmur gossip probes, local refinement candidate generation | No shared mutable state |
| **Sequential** | Seed lock, validation, merge, conflict resolution, escalation, seed update | Requires ordering guarantees |

### DAG Schema

```
T0: Deadband Detected
 │
 ├──→ P1: Slice Frozen Context Windows     ─┐
 ├──→ P2: Run Murmur Gossip Probes         ─┤ (parallel)
 ├──→ P3: Generate Local Refinement Candidates ┘
 │                                          │
 S1: Acquire Seed Lock          ←──────────┘
 │
 S2: Validate Frozen Window Consistency
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

### Conflict Resolution

1. **Weighted voting:** source credibility × confidence score
2. **Flag** tied scores or total confidence < 0.7
3. **Route** unresolvable to escalation gate
4. **Redact** candidates with confidence < 0.5

### Concrete Example: Warehouse Drone Restocking

**Parallel Phase:** 4 PLATO rooms run micro-models simultaneously (M_aisle, M_expiry, M_battery), synced via Murmur in <100ms.

**Sequential Phase:** Lead room aggregates, loads locked seed S_restock, generates route plan. If fails → escalate to LLM → refine seed → re-validate → re-lock.

---

## 7. Connection to Existing SuperInstance Components

| Component | Spreader-Tool Integration |
|-----------|--------------------------|
| **Murmur** | P2P gossip protocol for peer sync of frozen windows and seed status. Spreader uses Murmur as the transport layer for parallel operations. |
| **Micro-models** | The inference engines inside each PLATO room. Seeds are frozen snapshots of micro-model weights + context. The Spreader determines WHEN to freeze, validate, and lock. |
| **Escalation Gate** | Spreader feeds the gate: when deadband can't be reduced, it escalates. The gate decides whether to call LLM, flag for human review, or log to Model Ocean. |
| **Model Ocean** | Repository of all model capabilities. Spreader logs irreducible deadband to Model Ocean for future fine-tuning. Also queries Ocean to select best micro-model for a given room/task. |
| **Spectral Conservation** | Eigenvalue monitoring of task similarity matrix K (K_ij = similarity between tasks i,j). Stable eigenvalues = healthy system. Divergent eigenvalues = model drift or overfitting. Spreader triggers refinement when spectral drift detected. |
| **PLATO Rooms** | The runtime containers. Each room has its own deadband, its own frozen windows, its own seeds. Spreader operates per-room with fleet-wide coordination. |
| **SplineLinear** | Compression for micro-model weights. Seeds store SplineLinear-compressed weights for efficient edge deployment. |

---

## 8. Qwen's Simplification Critique — What to Cut

Qwen3.6-35B argued the architecture overengineers what is essentially a **confidence-based cascade problem**. Key recommendations:

### Valid Cuts (for MVP)

| Original | Qwen's Simplification | Verdict |
|----------|----------------------|---------|
| Full frozen context windows | Compressed embeddings/caches | ✅ Use for MVP, upgrade later |
| Synchronous backtesting | Async batch updates | ✅ Correct — async is better |
| Complex seed-locking state machine | Versioned checkpoints + drift monitoring | ⚠️ Oversimplified — need at least UNLOCKED→CANDIDATE→LOCKED |
| Murmur gossip | Standard load balancer | ❌ Murmur is core to P2P architecture |
| Spectral conservation | Hard cost/latency budgets | ❌ Spectral monitoring catches what budgets miss |

### What Qwen Got Right

The **simplest version that works** is:
1. Fast router (rule/confidence-based)
2. 1-3 specialized micro-models with dynamic prompts
3. Early exit/escalation to LLM if confidence low
4. Async feedback loop to update router weights
5. Caching for repeated patterns

This is essentially the **MVP of the Spreader-Tool**. The full architecture adds progressive tiling, seed-locking, and spectral monitoring on top of this foundation.

---

## 9. Hermes's Deadband Theory Connection

Hermes-70B identified the deadband concept as the **deepest theoretical contribution**, connecting it to:

### Distributed Systems
- **Sharding:** Each PLATO room is a shard of intelligence. Deadband = shard can't handle its partition.
- **DHTs:** Murmur gossip is essentially a distributed hash table for frozen windows and seeds.
- **P2P networks:** Fleet coordination without central authority.

### AI/ML
- **Modular neural networks:** Each room is a module. The Spreader decides when modules need upgrading.
- **Hierarchical reinforcement learning:** Deadband = reward signal that triggers learning at the next level up.
- **Progressive training:** Intelligence tiling = progressive neural network growing.

### Complexity Theory
- **Complex network stability:** Eigenvalue analysis of the task similarity matrix.
- **Phase transitions:** Deadband entry/exit as phase transitions in the system's operating regime.
- **Irreducible deadband = computational irreducibility** — some problems simply require more compute.

### What's Genuinely Novel

| Contribution | vs Existing Work |
|-------------|-----------------|
| Progressive intelligence tiling | vs monolithic model training |
| Frozen context windows | vs continuous streaming |
| Model Ocean ecosystem | vs static federated learning |
| Seed-locking + parallel-sequential mixing | vs single-model deployment |

---

## 10. Implementation Roadmap

### Phase 1: MVP (2-3 weeks)

Single-room implementation. Proves the concept.

1. **Single PLATO room** with mock peers (no real Murmur)
2. **Frozen context window lifecycle:** create → freeze → test → lock
3. **Simplified seed-locking:** UNLOCKED → CANDIDATE → LOCKED (skip intermediate states)
4. **Manual escalation gate:** log MAE, alert human
5. **Skip entirely:** Murmur gossip, spectral conservation, Model Ocean integration
6. **Use compressed embeddings** for FCWs (Qwen's simplification)

### Phase 2: Core (4-6 weeks)

Multi-room with real fleet coordination.

1. **Murmur integration** for real peer sync
2. **Full seed-locking state machine** with backtesting
3. **Escalation gate** with automatic LLM routing
4. **Refinement/redaction protocol** with cost measurement
5. **Parallel-sequential DAG** for multi-room orchestration
6. **Protobuf serialization** for FCWs

### Phase 3: Fleet (6-8 weeks)

Full production deployment.

1. **Spectral conservation monitoring** (eigenvalue analysis)
2. **Model Ocean integration** (irreducible deadband logging + model selection)
3. **SplineLinear compression** for seed weights
4. **Fleet-wide seed propagation** via Murmur
5. **Adaptive sampling** and deduplication
6. **Safety validation** at every inference step

---

## 11. Open Questions and Risks

### Open Questions

1. **Optimal FCW size:** How much context to freeze? Too small = insufficient for inference. Too large = storage/cost blowup. Needs empirical tuning.
2. **Seed lock duration:** Is 7 days the right threshold? Too short = thrashing. Too long = stale seeds.
3. **Refinement gradient threshold:** When is G(i) "close enough to zero" to stop? Needs domain-specific calibration.
4. **Conflict resolution weighting:** How to weight source credibility in multi-room merges? No theoretical basis yet.
5. **Spectral conservation sensitivity:** How sensitive is eigenvalue analysis to noise? May produce false positives in high-variance environments.

### Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Gossip poisoning** — malicious or corrupted peers spreading bad frozen windows | High | Cryptographic signing of FCWs, quorum-based validation |
| **Seed locking prematurity** — locking a seed before it's truly stable | Medium | Strict backtest requirements, human approval for safety-critical rooms |
| **Cascading deadband** — one room's deadband triggers adjacent rooms | High | Circuit breakers, deadband isolation, backpressure |
| **Storage blowup** — FCWs accumulating faster than they're pruned | Medium | Aggressive deduplication, tiered compression, retention limits |
| **Model drift** — locked seeds becoming stale as distribution shifts | Medium | Periodic re-validation, spectral monitoring, deprecation workflow |

---

*Architecture synthesized from 7-round Seed-2.0-mini iteration, Qwen3.6-35B simplification critique, and Hermes-70B theoretical analysis.*
