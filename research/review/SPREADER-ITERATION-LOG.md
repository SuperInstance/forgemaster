# Spreader-Tool Iteration Log

Multi-model iterative design session for the Spreader-Tool architecture.
Date: 2026-05-17

---

## Phase 1: Seed-2.0-mini Iteration (7 rounds)

### Round 1: Raw Concept Critique

**Model:** Seed-2.0-mini (ByteDance)
**Prompt:** Present raw concept, ask for critique, holes, extensions.

**Key Output:**

#### Identified Holes
1. **Ambiguous foundational definitions** — PLATO room undefined, deadband not operationalized
2. **Unoperationalized process steps** — No specs on window size, overlap, trigger conditions
3. **Unjustified technical choices** — 737-1037 param range is arbitrary, spectral conservation not tied to specific system
4. **Missing governance, safety, privacy** — No compliance guardrails, no interoperability with existing protocols
5. **Unaddressed failure modes** — Gossip poisoning, seed locking prematurity, escalation gate ambiguity, scalability limits

#### Proposed Extensions
- **Formal PLATO Room definition:** Modular edge-native smart space node with fixed functional role, hardcoded safety rules, local inference engine, sensor/actuator connectivity, P2P Murmur link
- **Operational Deadband:** Set of state transitions where hardcoded rules insufficient to meet KPIs (task completion <90% for 5+ min, wait >30s, energy >10% above baseline)
- **Refined workflow:** Context Window Snapshot → Backtesting & Validation → Refinement & Redaction → Seed Locking → Parallel/Sequential Orchestration
- **Escalation Gate triggers:** MAE >10% for 3 consecutive windows, deadband entry, or user request
- **Spectral conservation applied to:** micro-model weight matrices AND room state transition matrices

---

### Round 2: Algorithm Formalization

**Model:** Seed-2.0-mini
**Prompt:** Formalize the algorithm, data structures, state machines, and pseudocode.

**Key Output:**

#### Global System Constants
```python
WINDOW_DURATION: float = 60.0      # Fixed context window length (seconds)
TICK_INTERVAL: float = 10.0        # Period between core loop ticks
BASELINE_COMPLETION: float = 90.0  # Baseline task completion %
DEADBAND_MIN_DURATION: float = 300.0  # 5 minutes
ESCALATION_MAE_THRESHOLD: float = 10.0
SEED_LOCK_DYNAMIC_KPI: float = 95.0
SEED_LOCK_DYNAMIC_DURATION: float = 604800.0  # 7 days
```

#### Core Algorithm
- 8-step main loop: Capture state → Update sliding windows → Create frozen snapshot → Check deadband → Check escalation → Run local inference → Update seed lock → Sync with peers → Post-tick cleanup
- Asyncio-based with configurable tick interval
- Integrated safety validation at every inference step

#### Frozen Context Window Data Structure
- `FrozenContextWindow` dataclass with: window_uuid, source_node_id, temporal metadata, aggregated KPIs (task_completion_rate, avg_wait_time, energy_overage_pct, avg_inference_mae), safety compliance data, peer fleet data, fleet sync status, linked seed version

#### Refinement/Redaction Protocol
- **High-Compliance windows (≥95% completion, ≤5% MAE):** Keep only aggregated metrics, discard raw time-series
- **Medium-Compliance (90-95%, 5-10% MAE):** Keep aggregated + 1Hz compressed raw samples
- **Low-Compliance (<90%, >10% MAE, deadband):** Keep full metrics + 10Hz raw + peer sync logs
- **Seed-Locked Windows:** Retain all raw data and audit trails permanently

---

### Round 3: Frozen Context Window System Design

**Model:** Seed-2.0-mini
**Prompt:** Detailed design of the FCW system.

**Key Output:**

#### FCW Schema (Protobuf)
- **Core Mandatory Fields:** fcw_id (UUIDv7), frozen_at (ISO 8601), room_id, room_type (enum: SENSOR, COLLAB_ANALYSIS, COMMAND, SIMULATION), origin_trigger, parent_fcw_id, reasoning_cycle_count, global_confidence_score, status (STAGING→FROZEN→TESTING→REFINING→LOCKED→DISCARDED), snapshot_version
- **Reasoning State Core:** working_memory (chunk_id, content, access_count), active_hypotheses (hypothesis_id, description, confidence, supporting/contradicting evidence), tool_call_history, recent_sensor_window, error_logs
- **Room-Specific Extensions:** JSONB validated against room-type-specific schema registry

#### Freezing Triggers
- **Automated:** Time-based (fixed interval), Threshold-based (confidence shift >0.2, HIGH-severity error), Context shift (out-of-range readings), Critical tool call
- **Manual:** Operator-initiated via UI

#### Sampling Strategy
- Priority weighting: critical rooms 5x more frequent
- Deduplication: skip windows identical to last frozen (hash-based)
- Adaptive sampling: increase during rapid changes, reduce during stability

#### Compression
- Protobuf serialization (30-50% smaller than JSON)
- LZ4/Snappy for on-edge active windows
- Delta encoding for sequential sensor data
- Zstandard for long-term cloud archival

---

### Round 4: Seed-Locking Mechanism

**Model:** Seed-2.0-mini
**Prompt:** Detailed seed-locking design.

**Key Output:**

#### Seed Data Structure (SQL)
```sql
CREATE TABLE seeds (
    seed_id UUID PRIMARY KEY,
    room_id TEXT NOT NULL,
    role_name TEXT NOT NULL,
    lineage_id UUID NOT NULL,
    current_state TEXT NOT NULL,
    micro_model_weights BYTEA,
    context_window_ids UUID[],
    locked_kpi_metrics JSONB,
    created_at TIMESTAMPTZ,
    locked_at TIMESTAMPTZ,
    deprecated_at TIMESTAMPTZ,
    backtest_results JSONB,
    version_major INT,
    version_minor INT
);
```

#### State Machine
```
UNLOCKED → CANDIDATE: Submit for validation
CANDIDATE → VALIDATING: Queue backtest
VALIDATING → VALIDATION_FAILED: Backtest fails
VALIDATING → LOCK_PENDING: Backtest passes
VALIDATION_FAILED → CANDIDATE: Fix and resubmit
LOCK_PENDING → LOCKED: Auto/Manual approval
LOCKED → ESCALATING: Degradation trigger
ESCALATING → LOCKED: Issue resolved
ESCALATING → DEPRECATED: Replace with new seed
LOCKED → DEPRECATED: Superseded
DEPRECATED → ARCHIVED: Retention period expired
ARCHIVED → LOCKED: Emergency restore (admin-only)
```

#### Guards
- Every state transition requires explicit guard clauses
- Backtest must pass performance, runtime, AND dataset validation
- LOCK_PENDING requires human approval for safety-critical rooms

---

### Round 5: Synthesis and Convergence

**Model:** Seed-2.0-mini
**Prompt:** Synthesize everything, address convergence proof, adversarial cases, parallel-sequential examples, spectral conservation, MVP.

**Key Output:**

#### Deadband Convergence Metric
```
d(t) = |D(t)| / |D(0)|
```
Where D(t) is the set of unhandled deadband states at time t. Proven monotonically convergent if refinement gradient > 0.

#### Irreducible Deadband
When a task requires capabilities beyond micro-model capacity:
- Flag as irreducible, log to Model Ocean for future fine-tuning
- Contributes to d_min (irreducible lower bound)
- System escalates to LLM for this task type permanently

#### Concrete Parallel-Sequential Example: Warehouse Drone Restocking
- **Parallel Phase:** 4 PLATO rooms run micro-models simultaneously (M_aisle, M_expiry, M_battery), synced via Murmur in <100ms
- **Sequential Phase:** Lead room aggregates, loads locked seed S_restock, generates route plan. If fails, escalates to LLM, refines seed, re-validates, re-locks.

#### Spectral Conservation Connection
Eigenvalue monitoring of task similarity matrix K (K_ij = similarity between tasks i,j). Stable eigenvalues = healthy system. Divergent eigenvalues = model drift or overfitting.

#### Minimum Viable Spreader-Tool
1. Single-room implementation with mock peers
2. Frozen context window lifecycle (create → freeze → test → lock)
3. Simple seed-locking (UNLOCKED → LOCKED only, no intermediate states)
4. Manual escalation gate (log MAE, alert human)
5. Skip: Murmur gossip, spectral conservation, Model Ocean integration

---

### Round 6: Refinement/Redaction Protocol

**Model:** Seed-2.0-mini
**Prompt:** Design the intelligence pruning mechanism.

**Key Output:**

#### Intelligence Cost Measurement
- **Micro-Model Cost:** Normalized weighted sum of parameter count, FLOPs per inference, latency, memory footprint
- **Context Window Cost:** Normalized weighted sum of token/entry count, retrieval latency
- **Total:** NTIC_total = w1 * NTIC_model + w2 * NTIC_context

#### Triggers
- **Event-Driven:** Deadband shift detected (CGR > 0.15), cost threshold breach, manual override, critical failure
- **Periodic:** Fixed interval (10K steps or 24h), gradual drift check
- **Cooldown:** Minimum 5 minutes between refinement cycles

#### Pruning Algorithm
1. Baseline coverage benchmark
2. Rank entries by Value Score (marginal coverage contribution) and Redundancy Score (nearby entries)
3. Iteratively remove lowest VS + highest RS entries
4. After each removal, re-benchmark to check coverage maintained
5. Stop when coverage drops below threshold T

#### Refinement Gradient
The marginal gain in deadband coverage per unit of intelligence cost:
```
G(i) = ΔB(i) / ΔNTIC(i)
```
Positive gradient = intelligence is paying for itself. Negative = over-invested.

---

### Round 7: Parallel-Sequential Orchestration

**Model:** Seed-2.0-mini
**Prompt:** Design the complete orchestration system.

**Key Output:**

#### Task Decomposition
- **Parallelizable:** Frozen context slicing, Murmur gossip probes, local refinement candidate generation
- **Sequential:** Seed lock, validation, merge, conflict resolution, escalation, seed update

#### DAG Schema
```json
{
  "nodes": [
    {"id": "T0", "name": "Deadband Detected"},
    {"id": "S1", "name": "Acquire Seed Lock"},
    {"id": "P1", "name": "Slice Frozen Context Windows"},
    {"id": "P2", "name": "Run Murmur Gossip Probes"},
    {"id": "P3", "name": "Generate Local Refinement Candidates"},
    {"id": "S2", "name": "Validate Frozen Window Consistency"},
    {"id": "S3", "name": "Merge Parallel Results"},
    {"id": "S4", "name": "Resolve Conflicts"},
    {"id": "S5", "name": "Refine/Redact"},
    {"id": "S6", "name": "Escalation Gate Check"},
    {"id": "S7", "name": "Update System Seed"},
    {"id": "S8", "name": "Release Seed Lock"}
  ]
}
```

#### Conflict Resolution
1. Weighted voting (source credibility × confidence score)
2. Flag tied scores or total confidence < 0.7
3. Route unresolvable to escalation gate
4. Redact candidates with confidence < 0.5

---

## Additional Model Rounds

### Qwen3.6-35B Perspective (Cheap Routing Model)

**Key Insight:** The architecture tries to solve routing with distributed intelligence dynamics instead of just routing. Most of the complexity is overengineered for what is essentially a confidence-based cascade problem.

**What to cut:**
- Full frozen context windows → compressed embeddings/caches
- Synchronous backtesting → async batch updates
- Seed-locking/attractor dynamics → versioned checkpoints + drift monitoring
- Murmur gossip → standard load balancer
- Spectral conservation → hard cost/latency budgets

**Simplest version that works:**
1. Fast router (rule/confidence-based)
2. 1-3 specialized micro-models with dynamic prompts
3. Early exit/escalation to LLM if confidence low
4. Async feedback loop to update router weights
5. Caching for repeated patterns

---

### Hermes-70B Perspective (Larger Model)

**Key Insight:** The deadband concept is the deepest theoretical contribution. It connects to:
- **Distributed Systems:** Sharding, DHTs, P2P networks
- **AI:** Modular neural networks, hierarchical reinforcement learning
- **Complexity Theory:** Complex network stability, eigenvalue analysis

**Novel contributions vs existing work:**
- Progressive intelligence tiling (vs monolithic model training)
- Frozen context windows (vs continuous streaming)
- Model Ocean ecosystem (vs static federated learning)
- Seed-locking + parallel-sequential mixing (novel coordination)
