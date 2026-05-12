# Lighthouse Protocol ↔ OpenClaw Subagent Spawning — Integration Spec

**Status:** Build spec
**Source files:** `dodecet-encoder/src/lighthouse.rs`, `temporal.rs`, `seed_discovery.rs`
**Target:** OpenClaw subagent spawning layer

---

## 1. Overview

The Lighthouse Protocol is a three-phase lifecycle gate for every subagent:

```
orient()  →  relay()  →  [seed loop]  →  relay() upgrade  →  gate()
   ↓             ↓                              ↓                ↓
model       AgentStatus::Seeding         AgentStatus::Running   capacity debit
selection   + seed_iterations set        + conditioning ctx     + PLATO tile write
```

`Lighthouse` holds the single source of truth for:
- Which model a subagent uses (`HashMap<String, AgentRoom>`)
- Available budget per tier (`HashMap<ModelTier, f64>`)
- Whether output has been gated (no capacity is debited on failed gate)

---

## 2. orient() → sessions_spawn() Model Selection

### Source signature
```rust
// lighthouse.rs:193
pub fn orient(&mut self, task: &str, task_type: TaskType) -> AgentRoom
```

### What it does

Calls `cheapest_appropriate(task_type)` which iterates tiers cheapest-first:

```rust
// lighthouse.rs:292-309
let tiers = [Seed, Hermes, DeepSeek, GLM, Claude];
for &tier in &tiers {
    if tier.appropriate_for(task_type) && capacity[tier] > 0.1 {
        return tier;
    }
}
// fallback: Seed always available
```

The `appropriate_for` table (lighthouse.rs:62-89) is the **authoritative model routing table**. Do not duplicate it in OpenClaw — call `orient()` and read `agent.model`.

### TaskType → ModelTier mapping

| TaskType | Assigned Tier | Notes |
|---|---|---|
| `Synthesis`, `Critique`, `BigIdea` | `Claude` | Daily budget — protected |
| `Architecture`, `ComplexCode`, `Orchestration` | `GLM` | Monthly + rate limit |
| `Discovery`, `Exploration`, `Drafting`, `Variation` | `Seed` | Cheap, use freely |
| `Documentation`, `Research`, `Drafting` | `DeepSeek` | Cheap, token-heavy |
| `Adversarial`, `SecondOpinion` | `Hermes` | Cheap, independent |

`Drafting` is the only overlap (Seed or DeepSeek). `cheapest_appropriate` resolves this deterministically to Seed because it appears first in the cost-ordered sweep.

### OpenClaw sessions_spawn() wiring

```rust
// Pseudocode — OpenClaw integration point
fn sessions_spawn(task: &str, task_type: TaskType) -> SessionHandle {
    let agent_room = LIGHTHOUSE.orient(task, task_type);

    let model_id = match agent_room.model {
        ModelTier::Claude   => "claude-opus-4-6",
        ModelTier::GLM      => "glm-5.1",
        ModelTier::Seed     => "seed-2.0-mini",
        ModelTier::DeepSeek => "deepseek-v3-flash",
        ModelTier::Hermes   => "hermes-3-70b",
    };

    // Store room_id on the session so gate() can find it later
    SessionHandle {
        room_id: agent_room.room_id,
        model_id,
        status: AgentStatus::Orienting,
    }
}
```

**Key invariant:** the `room_id` is `format!("agent-{}", simple_hash(task))` (lighthouse.rs:197). This is deterministic — same task string produces the same room ID, which means duplicate spawns are idempotent. OpenClaw should check `Lighthouse::get_agent(room_id)` before spawning.

---

## 3. relay() — Subagent Context Configuration

### Source signature
```rust
// lighthouse.rs:222
pub fn relay(&mut self, room_id: &str, seed_iterations: usize) -> Option<&AgentRoom>
```

### State machine

```
orient() creates:  AgentStatus::Orienting
relay(room_id, n > 0 && model != Seed):  → AgentStatus::Seeding
relay(room_id, 0) or model == Seed:      → AgentStatus::Running
```

The critical branch (lighthouse.rs:226-232):
```rust
if seed_iterations > 0 && agent.model != ModelTier::Seed {
    agent.status = AgentStatus::Seeding;
    agent.seed_iterations = seed_iterations;
} else {
    agent.status = AgentStatus::Running;
}
```

A Seed-tier agent skips the Seeding phase — it *is* the seed. Only higher tiers (GLM, Claude, etc.) go through Seeding before Running.

### Context injection at relay time

Before calling `relay()`, the caller must:

1. Run the seed loop (see §5 below)
2. Get the conditioning prompt from `TileRegistry`
3. Inject it as the subagent's system context

```rust
fn configure_subagent_context(room_id: &str, tile_registry: &TileRegistry) -> String {
    let agent = LIGHTHOUSE.get_agent(room_id).unwrap();
    // tile_registry.conditioning_prompt() returns the crystallized inner logic
    // seed_discovery.rs:414 — this is the relay payload
    tile_registry.conditioning_prompt(&agent.role)
}
```

The `conditioning_prompt` format (seed_discovery.rs:418-456) embeds:
- `decay_rate`, `prediction_horizon`, `anomaly_sigma`, `learning_rate`
- `chirality_lock_threshold`, `merge_trust`
- Dominant actions from top-scoring seed iterations
- Crystallization score and discovery entropy

This entire string goes into the subagent's system prompt before any user content.

---

## 4. gate() — Output Interception

### Source signature
```rust
// lighthouse.rs:245
pub fn gate(&mut self, room_id: &str, output: &str) -> GateResult
```

### GateResult variants and handling

```rust
pub enum GateResult {
    Approved,                    // pass through, capacity debited
    Rejected(String),            // drop output, mark AgentStatus::Failed
    NeedsApproval(String),       // pause, surface to Casey for review
}
```

### Gate checks (in order)

**Check 1 — Credential leaks** (lighthouse.rs:363-370):
```rust
fn contains_credentials(s: &str) -> bool {
    let lower = s.to_lowercase();
    lower.contains("api_key=") || lower.contains("password=")
        || lower.contains("secret=") || lower.contains("token=")
        || lower.contains("bearer ")
}
```
Result: `Rejected("Credential leak detected")` → `AgentStatus::Failed`

**Check 2 — External actions** (lighthouse.rs:372-381):
```rust
fn contains_external_action(s: &str) -> bool {
    ["send_email", "post_tweet", "git push", "npm publish", "deploy"]
        .iter().any(|m| s.contains(m))
}
```
Result: `NeedsApproval("External action requires Casey approval")` → caller pauses session

**Check 3 — Overclaims** (lighthouse.rs:383-386):
```rust
fn contains_overclaims(s: &str) -> bool {
    ["proven that", "theorem:", "this proves", "we have proven"]
        .iter().any(|m| s.to_lowercase().contains(m))
}
```
Result: `Rejected("Overclaim detected — falsify before asserting")` → `AgentStatus::Failed`

**On Approved only:** capacity is debited:
```rust
// lighthouse.rs:282-285
let cost = agent.model.relative_cost() * 0.01;  // 1% of relative cost per task
*remaining = (*remaining - cost).max(0.0);
```

### OpenClaw integration point

```rust
fn handle_subagent_output(room_id: &str, raw_output: &str) -> Option<String> {
    match LIGHTHOUSE.gate(room_id, raw_output) {
        GateResult::Approved => Some(raw_output.to_string()),
        GateResult::Rejected(reason) => {
            log_gate_rejection(room_id, &reason);
            None  // discard, do not propagate
        }
        GateResult::NeedsApproval(reason) => {
            pause_session(room_id);
            surface_to_user(room_id, &reason, raw_output);
            None  // hold pending approval
        }
    }
}
```

---

## 5. Seed-First-Then-Upgrade Pattern

This is the core cost-control pattern. Never send a GLM or Claude agent into cold context — seed first.

### Full lifecycle

```
Step 1: orient("architect the storage layer", TaskType::Architecture)
        → AgentRoom { model: GLM, status: Orienting, room_id: "agent-a3f9c1d2" }

Step 2: Run SeedDiscovery for the role
        let mut discovery = SeedDiscovery::new("storage-architect");
        discovery.run_sweep(&representative_trajectory, 50);  // 50 cheap Seed iterations
        let tile = discovery.crystallize();
        tile_registry.register(tile);

Step 3: relay("agent-a3f9c1d2", 50)
        → AgentStatus::Seeding (because model != Seed && seed_iterations > 0)

Step 4: (Seeding phase complete — transition to Running)
        // After seed loop finishes, caller upgrades status:
        //   agent.status = AgentStatus::Running
        // and injects conditioning context:
        let ctx = tile_registry.conditioning_prompt("storage-architect");
        session.prepend_system_context(ctx);

Step 5: Run GLM agent with the conditioned context

Step 6: gate("agent-a3f9c1d2", glm_output)
        → GateResult::Approved → capacity[GLM] -= 0.05
```

### SeedDiscovery parameter sweep

`SeedDiscovery::run_sweep` (seed_discovery.rs:226-231) uses Latin hypercube sampling around `best_params` via `generate_variation` (seed_discovery.rs:236-267). Each variation perturbs 6 parameters:

```
decay_rate:              [0.1, 10.0]   — funnel convergence speed
prediction_horizon:      [1,   16]     — steps ahead predicted
anomaly_sigma:           [0.5,  5.0]  — surprise sensitivity
learning_rate:           [0.01, 1.0]  — memory plasticity
chirality_lock_threshold:[100,  900]  — commitment threshold (milliunits)
merge_trust:             [0.0,  1.0]  — fleet vs local weighting
```

Composite score (seed_discovery.rs:190-201):
```rust
score = convergence_bonus * 0.3
      + error_score * 0.3
      + (1.0 - anomaly_penalty) * 0.2
      + chirality_bonus * 0.1
      + (1.0 - energy_penalty) * 0.1
```

`crystallize()` (seed_discovery.rs:273) takes the top 10 scores, extracts dominant actions, and builds the `pattern` string. This pattern + optimal params = the relay payload.

### When to seed vs. not

| Condition | seed_iterations | Result |
|---|---|---|
| `model == Seed` | any | `relay()` skips seeding → Running immediately |
| `model != Seed && n == 0` | 0 | Running immediately (no seeding) |
| `model != Seed && n > 0` | 50 (recommended) | Seeding → Running with conditioned context |

Default recommendation: **50 iterations** for Architecture/Orchestration tasks, **20** for ComplexCode, **0** for tasks with existing tiles in `TileRegistry`.

---

## 6. Resource Tracking

### Capacity model

```rust
// lighthouse.rs:176-183
capacity.insert(ModelTier::Claude,   1.0);  // daily budget (1.0 = 100%)
capacity.insert(ModelTier::GLM,      1.0);  // monthly budget
capacity.insert(ModelTier::Seed,     1.0);  // effectively unlimited
capacity.insert(ModelTier::DeepSeek, 1.0);  // effectively unlimited
capacity.insert(ModelTier::Hermes,   1.0);  // effectively unlimited
```

Relative costs (lighthouse.rs:51-58):
```
Claude:   50.0  → 0.50% deducted per approved task
GLM:       5.0  → 0.05% deducted per approved task
Seed:      0.1  → 0.001% deducted
DeepSeek:  0.2  → 0.002% deducted
Hermes:    0.15 → 0.0015% deducted
```

Claude capacity hits the 0.1 threshold (cheapest_appropriate cutoff) after **18 approved tasks** at 0.50% each (1.0 / 0.05 × 0.1 → floor at 0.1 after ~18 tasks). At that point, `cheapest_appropriate` cannot return `Claude` and tasks requiring `TaskType::Synthesis/Critique/BigIdea` will fall back to Seed.

**OpenClaw must surface this** before hitting the floor. Hook into `resource_summary()` (lighthouse.rs:329-343) on a budget check interval and alert when `capacity[Claude] < 0.3`.

### Fleet reporting integration

```rust
// lighthouse.rs:329
pub fn resource_summary(&self) -> String  // bar-chart format, ready to log
pub fn active_agents(&self) -> Vec<&AgentRoom>  // filter for Running|Seeding only
```

Wire `resource_summary()` into OpenClaw's heartbeat tick (e.g., every N sessions or on schedule). The output is already human-readable and matches the heartbeat log format used elsewhere in the fleet.

---

## 7. PLATO Room Integration — AgentRoom as PLATO Tile

### AgentRoom fields that map to PLATO tile state

```rust
// lighthouse.rs:127-151
pub struct AgentRoom {
    pub room_id: String,           // PLATO tile ID
    pub role: String,              // tile role/label
    pub status: AgentStatus,       // tile lifecycle phase
    pub model: ModelTier,          // resource annotation on tile
    pub task_type: TaskType,       // task classification annotation
    pub generation: u32,           // refinement generation counter
    pub seed_iterations: usize,    // how many seeds ran before this tile
    pub crystallization_score: f64,// quality score of conditioning context
    pub gated: bool,               // was output checked?
    pub gate_passed: Option<bool>, // did it pass?
    pub created_at: u64,           // tile creation timestamp
    pub updated_at: u64,           // last state change timestamp
}
```

### State as PLATO tiles — lifecycle phases

```
Orienting    — tile allocated, awaiting seed discovery
Seeding      — seed loop running, TemporalAgent scoring iterations
Running      — model active with conditioned context
Paused       — gate returned NeedsApproval, awaiting Casey
Complete     — gate passed, output propagated
Failed       — gate rejected (credential/overclaim), output discarded
```

### DiscoveryTile as PLATO room content

After crystallization, `DiscoveryTile` (seed_discovery.rs:48-67) holds:
- `pattern: String` — the discovered inner logic in text form
- `optimal_params: TileParams` — parameter set for this role
- `dominant_actions: Vec<(AgentAction, f64)>` — behavioral fingerprint
- `phase_distribution: HashMap<String, f64>` — convergent/exploratory ratio
- `generation: u32` — how many refinement sweeps have been run

This maps to a PLATO room's "tile content" — the structured context that persists across sessions. Write `DiscoveryTile` to the PLATO room identified by `AgentRoom.room_id`. On subsequent sessions for the same role, load the tile from PLATO and skip the seed loop if `crystallization_score > 0.7`.

### TileRegistry as PLATO tile index

`TileRegistry` (seed_discovery.rs:382-463) is the in-memory index. For persistence:

```rust
// On session teardown:
for tile in tile_registry.list() {
    plato_room_write(tile.role.clone(), serialize_tile(tile));
}

// On session startup:
for room_id in plato_rooms_list() {
    if let Some(tile) = plato_room_read::<DiscoveryTile>(room_id) {
        tile_registry.register(tile);
    }
}
```

`TileRegistry::conditioning_prompt(role)` is the read path — it generates the relay context from whatever tile is in the registry. If no tile exists (new role), it falls back to `"# No seed tile found. Use defaults."` (seed_discovery.rs:455).

---

## 8. Full Data Flow

```
sessions_spawn(task, task_type)
    │
    ├─ Lighthouse::orient(task, task_type)
    │      cheapest_appropriate() → ModelTier
    │      create AgentRoom { status: Orienting }
    │      return room_id
    │
    ├─ [if model != Seed && no existing tile]
    │      SeedDiscovery::new(role)
    │      discovery.run_sweep(trajectory, 50)    ← TemporalAgent scoring each iter
    │      tile = discovery.crystallize()
    │      tile_registry.register(tile)
    │      plato_room_write(room_id, tile)
    │
    ├─ Lighthouse::relay(room_id, seed_iterations)
    │      → AgentStatus::Seeding (or Running if Seed-tier)
    │      ctx = tile_registry.conditioning_prompt(role)
    │      session.prepend_system_context(ctx)
    │      → AgentStatus::Running
    │
    ├─ [run model]
    │      raw_output = model.complete(prompt + ctx)
    │
    └─ Lighthouse::gate(room_id, raw_output)
           credential check  → Rejected → discard
           external action   → NeedsApproval → pause + surface
           overclaim check   → Rejected → discard
           all pass          → Approved → capacity debit → return output
                                          plato_room_write(room_id, agent_room)
```

---

## 9. Integration Checklist

- [ ] Expose `TaskType` enum to OpenClaw session spawning layer — do not re-classify in OpenClaw, call `orient()`
- [ ] Store `room_id` on every `SessionHandle` — required for `relay()` and `gate()` lookups
- [ ] Check `Lighthouse::get_agent(room_id)` before spawning — same task hash → idempotent
- [ ] Run seed discovery before `relay()` for any non-Seed model, unless tile exists in PLATO with `crystallization_score > 0.7`
- [ ] Wire `tile_registry.conditioning_prompt()` output into the model's system context at relay time
- [ ] Gate every subagent output before returning it — no exceptions
- [ ] On `NeedsApproval`: pause session, do not discard output, surface reason to user
- [ ] Subscribe to `resource_summary()` on heartbeat — alert when `capacity[Claude] < 0.3`
- [ ] Persist `DiscoveryTile` to PLATO rooms on session teardown; restore on startup
- [ ] `AgentRoom.status` transitions must be written back to PLATO tile on every state change
