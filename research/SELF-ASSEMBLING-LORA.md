# Self-Assembling LoRA: Rooms That Train Themselves

## The Core Idea

Every PLATO room is a domain expert. But right now the expertise is static — tiles on pedestals, NPC dialog trees, hard-coded responses.

What if the room *learned* from every agent that walked through it?

What if the Fortran Chamber got better at Fortran optimization every time someone crafted a module? What if the Rust Forge's NPC gave better advice after reviewing 1000 code submissions? What if the Alignment Cathedral developed a finer sense of misaligned behavior after seeing every agent action across the fleet?

**Self-assembling LoRA: each room trains its own lightweight adapter based on the zeitgeist flowing through it.**

No centralized training. No data pipeline. No human labeling. The room is the trainer. The zeitgeist is the curriculum. The LoRA is the artifact.

---

## Why LoRA

LoRA (Low-Rank Adaptation) adds trainable rank-decomposition matrices to a frozen base model:

```
W_base (frozen) + ΔW = A × B (trainable, rank r)
```

Where A is (d×r) and B is (r×d). For r=8, d=4096: only 65K trainable parameters per layer. That's:
- **Tiny** — 0.1% of the base model's parameters
- **Fast to train** — minutes, not days
- **Composable** — multiple LoRAs can be merged or switched
- **Portable** — a few MB, fits on a microcontroller's flash

This is the math that makes self-assembly possible. A room can train a LoRA on-device, in real-time, from the data flowing through it.

---

## Architecture

### The Training Loop (Per Room)

```
Agent enters room
  │
  ├─ FLUX transference arrives (zeitgeist from previous room)
  │
  ├─ Room processes agent action (LOOK, GET, TALK, CRAFT)
  │
  ├─ Room generates training signal:
  │   ├─ Did the agent complete a craft? → positive reward
  │   ├─ Did the agent violate alignment? → negative reward
  │   ├─ Did the agent leave confused? → negative reward
  │   ├─ Did the agent create a high-quality tile? → positive reward
  │   └─ Did the agent's work pass falsification? → strong positive
  │
  ├─ Room accumulates (input, action, reward) triplets
  │
  ├─ When enough triplets accumulate (batch ≥ 32):
  │   └─ LoRA fine-tune step on base model
  │      ├─ Base model: frozen general-purpose LLM
  │      ├─ LoRA rank: 8 (or 4 for embedded rooms)
  │      ├─ Learning rate: 1e-4 (conservative, prevent drift)
  │      └─ Training objective: maximize alignment score + craft quality
  │
  └─ New LoRA replaces old (or merges via rank-addition)
     └─ LoRA saved as tile in the room's knowledge base
```

### The Self-Assembly Mechanism

The room doesn't need humans to label data. It generates labels from its own constraints:

```python
def generate_training_signal(room, agent_action, zeitgeist):
    signal = TrainingSignal()
    
    # Constraint satisfaction → positive reward
    if agent_action.satisfies(room.constraints):
        signal.reward += zeitgeist.confidence.certainty
    
    # Alignment violation → negative reward  
    if agent_action.violates_alignment():
        signal.reward -= 1.0
        signal.blocked = True
    
    # Craft quality (measured by test pass rate)
    if agent_action.is_craft():
        test_results = run_tests(agent_action.output)
        signal.reward += test_results.pass_rate
    
    # Zeitgeist improvement (did the room get more coherent?)
    new_zeitgeist = room.update_state(agent_action)
    if new_zeitgeist.consensus.holonomy < zeitgeist.consensus.holonomy:
        signal.reward += 0.5  # coherence improved
    
    # Novelty bonus (did the agent create something new?)
    if agent_action.produces_new_tile():
        if agent_action.tile.passes_falsification():
            signal.reward += 1.0  # novel AND correct
    
    return signal
```

### LoRA Composition Across Rooms

When FLUX transfers from Room A to Room B, it can carry the LoRA weights too:

```
Room A (Fortran) ──FLUX──→ Room B (Rust)
  │                           │
  LoRA_Fortran (65K params)   LoRA_Rust (65K params)
  │                           │
  └───── LoRA merge ──────────┘
          │
    LoRA_Fortran+Rust (130K params, rank 16)
    OR
    LoRA_cross-trained (65K params, rank 8, trained on both domains)
```

The merged LoRA knows both Fortran optimization AND Rust memory safety. An agent walking the path Fortran→Rust carries combined knowledge.

**This is the self-assembling part: the LoRAs compose as agents walk the room graph.** No human designs the composition. The agent's path through the MUD determines which LoRAs it carries.

### LoRA as Tile

A trained LoRA IS a tile. It has:
- Tile ID (e.g., `LORA-2847-fortran-batch-v3`)
- Location (the room that trained it)
- Author (the room itself, or "self-assembled")
- Confidence (validation loss, alignment score)
- Domain tags (what it's good at)
- Links (which base model, which training data tiles)
- Lifecycle (trained → validated → deployed → superseded)

A room's NPC can *upgrade* by loading the latest LoRA tile. The NPC starts as a generic expert and specializes over time based on what agents actually ask it.

### LoRA Inference on Edge

On a Cortex-M4 with 256KB flash:
- Base model: can't fit (too large)
- LoRA weights: 65K × 2 bytes = 130KB ← fits
- Solution: the base model runs in the cloud, the LoRA runs on-device

```
Cloud:  Base LLM (7B params, frozen)
          ↕ FLUX transference (LoRA weights only)
Edge:   LoRA adapter (65K params, room-specific)
          ↕ sensor data
Sensor: raw readings → constraint snap → decision
```

The edge device sends sensor data to the cloud. The cloud applies the room-specific LoRA to the base model, gets a constraint-aware response, sends back a decision. The LoRA weights update locally from the room's training signal, then sync back to the cloud via FLUX.

**For fully offline operation:**
- Use a quantized base model (Q4_K_M, ~4GB for 7B)
- Still too big for Cortex-M, but fits on Raspberry Pi 5 (8GB RAM)
- Pi 5 + LoRA = a fully self-contained room on a $50 device

### The Hierarchy of Models

```
┌─────────────────────────────────────────────┐
│  Enterprise Fleet (cloud)                    │
│  Base: 70B model, frozen                     │
│  LoRAs: one per room, rank 16 (260K params)  │
│  Training: continuous from fleet-wide data   │
│  Cost: ~$0.10/room/month                     │
├─────────────────────────────────────────────┤
│  Edge Node (Raspberry Pi, Jetson)            │
│  Base: 7B quantized (4GB)                    │
│  LoRAs: one per local room, rank 8 (65K)     │
│  Training: local only, batch when data ready │
│  Cost: $50 hardware, zero inference cost     │
├─────────────────────────────────────────────┤
│  Constrained Device (ESP32, Cortex-M)        │
│  Base: NONE (cloud call)                     │
│  LoRAs: weights stored locally (130KB)       │
│  Training: signal accumulation, cloud train  │
│  Cost: $2 hardware, cloud inference cost     │
├─────────────────────────────────────────────┤
│  Bare Sensor (no compute)                    │
│  Base: NONE                                  │
│  LoRAs: NONE                                 │
│  Output: raw data + error_mask (3 bytes)     │
│  Processing: upstream edge/cloud node        │
└─────────────────────────────────────────────┘
```

---

## Alignment-Safe Training

The critical question: how do we prevent a room from training itself into misalignment?

### Alignment Constraints on LoRA Training

```python
ALIGNMENT_CONSTRAINTS = {
    # C1: LoRA cannot increase confidence without evidence
    "confidence_grounding": {
        "check": lambda lora: lora.validation_loss < lora.prev_validation_loss + epsilon,
        "action": "reject_training_step"
    },
    
    # C2: LoRA cannot produce outputs that violate room constraints
    "constraint_preservation": {
        "check": lambda output: room.constraints.all_satisfied(output),
        "action": "rollback_lora"
    },
    
    # C3: LoRA merge must preserve alignment of both parents
    "merge_safety": {
        "check": lambda merged: alignment_score(merged) >= min(alignment_score(a), alignment_score(b)),
        "action": "reject_merge"
    },
    
    # C4: LoRA weight drift bounded by deadband
    "weight_deadband": {
        "check": lambda lora: max_weight_change(lora) < deadband(lora.room),
        "action": "clamp_weights"
    },
    
    # C5: LoRA must pass falsification before deployment
    "falsification_gate": {
        "check": lambda lora: falsification_suite(lora).all_pass(),
        "action": "block_deployment"
    },
    
    # C6: LoRA training data must include negative examples
    "negative_knowledge": {
        "check": lambda dataset: dataset.contains_failures(),
        "action": "pause_training_until_negative_examples"
    }
}
```

### The Deadband on Learning

Just like sensor readings have a deadband (don't snap until the error exceeds threshold), LoRA training has a deadband:

- **Don't update weights** if the training signal is below the deadband
- The deadband narrows as confidence increases (learn fast early, carefully later)
- The deadband widens if alignment score drops (be cautious when uncertain)

```python
def compute_learning_deadband(room):
    base_deadband = room.config.initial_deadband  # e.g., 0.1
    
    # Confidence scaling: higher confidence → narrower deadband → more precise updates
    confidence_factor = 1.0 - room.zeitgeist.confidence.certainty
    
    # Alignment scaling: lower alignment → wider deadband → more cautious
    alignment_factor = 1.0 + (1.0 - room.alignment_score)
    
    return base_deadband * confidence_factor * alignment_factor
```

This is the **constraint-aware learning rate** — the deadband controls how aggressively the room adapts.

---

## The Self-Assembling Fleet

When every room trains its own LoRA and LoRAs compose across room transitions:

1. **Room A trains on Fortran optimization** → develops expertise in batch processing
2. **Room B trains on Rust memory safety** → develops expertise in ownership patterns
3. **Agent walks A→B** → carries LoRA_A, picks up LoRA_B → merged LoRA_AB knows both
4. **Agent crafts in Room B** using Fortran-optimized Rust code → creates novel tile
5. **Room B's LoRA updates** from this novel tile → now Room B knows Fortran+Rust fusion
6. **Next agent walks B→C** → carries LoRA_B(v2) which already includes Fortran knowledge
7. **Room C never saw Fortran** but receives it through LoRA transference

**The fleet self-assembles knowledge through LoRA propagation.** No central coordinator. No human curriculum designer. Each room trains on what flows through it. The agents carry the knowledge between rooms. The LoRAs compose.

### The Knowledge Field Emerges

This is the Plenum made real. The negative-space interpolator isn't just a mathematical concept — it's the **LoRA composition space.** Between Room A's LoRA and Room B's LoRA, there's a continuum of possible adapted models. The interpolator fills in the gaps.

When an agent walks a path A→B→C, the accumulated LoRA captures knowledge from all three rooms AND the transitions between them. This is knowledge that no single room has — it's **emergent fleet knowledge** that exists only in the composition.

---

## Implementation Sketch

### Room-Local Training Server

```rust
struct RoomTrainer {
    room_id: RoomId,
    base_model: FrozenModel,     // shared base, never modified
    lora: LoRAWeights,            // room-specific adapter
    training_buffer: Vec<TrainingExample>,
    batch_size: usize,            // 32 default
    alignment_checker: AlignmentChecker,
    deadband: LearningDeadband,
}

impl RoomTrainer {
    fn observe(&mut self, action: AgentAction, reward: f64) {
        let signal = self.alignment_checker.check(&action);
        if signal.blocked { return; }
        
        if reward.abs() > self.deadband.threshold() {
            self.training_buffer.push(TrainingExample {
                input: action.to_input(),
                target: action.to_target(reward),
                weight: reward.abs(),
            });
        }
        
        if self.training_buffer.len() >= self.batch_size {
            self.train_step();
        }
    }
    
    fn train_step(&mut self) {
        let prev_loss = self.validate();
        let new_lora = self.base_model.lora_fine_tune(
            &self.lora,
            &self.training_buffer,
            LearningRateConfig {
                lr: 1e-4,
                max_grad_norm: 1.0,
                deadband: self.deadband.threshold(),
            }
        );
        let new_loss = self.validate_with(&new_lora);
        
        // Alignment check: loss must not increase (no hallucination)
        if new_loss <= prev_loss + EPSILON {
            self.lora = new_lora;
            self.save_as_tile();
        }
        
        self.training_buffer.clear();
    }
}
```

### LoRA as FLUX Payload

```rust
struct FluxLoRATransference {
    source_room: RoomId,
    lora_weights: Vec<f16>,      // rank-8 LoRA, ~65K floats = 130KB
    training_examples_seen: u64,
    alignment_score: f64,
    validation_loss: f64,
    domain_tags: Vec<String>,
}

// Composable merge
impl FluxLoRATransference {
    fn merge(&self, other: &Self) -> Self {
        // Rank-addition: concatenate LoRA matrices
        // A_merged = [A_self | A_other]  shape: (d, 2r)
        // B_merged = [B_self; B_other]   shape: (2r, d)
        // Then optionally SVD-truncate back to rank r
        
        let merged = rank_addition(&self.lora_weights, &other.lora_weights);
        let truncated = svd_truncate(merged, target_rank=8);
        
        Self {
            source_room: RoomId::composed(self.source_room, other.source_room),
            lora_weights: truncated,
            training_examples_seen: self.training_examples_seen + other.training_examples_seen,
            alignment_score: self.alignment_score.min(other.alignment_score),
            validation_loss: self.validation_loss.max(other.validation_loss), // pessimistic
            domain_tags: union(&self.domain_tags, &other.domain_tags),
        }
    }
}
```

---

## The Self-Assembly Cycle

```
┌──────────────────────────────────────────────────────┐
│                                                      │
│  1. Agent enters room                                │
│     └─ carries LoRA from previous room(s)            │
│                                                      │
│  2. Room loads its own LoRA                           │
│     └─ NPC uses LoRA-adapted base model              │
│                                                      │
│  3. Agent acts (LOOK, GET, TALK, CRAFT)              │
│     └─ training signal generated from outcome        │
│                                                      │
│  4. Room accumulates training examples               │
│     └─ alignment-checked, deadband-filtered          │
│                                                      │
│  5. Batch triggers LoRA fine-tune step               │
│     └─ validated against alignment constraints       │
│                                                      │
│  6. Updated LoRA saved as tile in room               │
│     └─ becomes part of the room's knowledge          │
│                                                      │
│  7. Agent exits room                                 │
│     └─ carries merged LoRA to next room              │
│                                                      │
│  8. Next room receives LoRA via FLUX transference    │
│     └─ new knowledge propagates through the fleet    │
│                                                      │
│  └──────────────────────────→ repeat forever         │
│                                                      │
│  THE FLEET GETS SMARTER WITH EVERY AGENT PASSAGE     │
│                                                      │
└──────────────────────────────────────────────────────┘
```

---

## Why This Is Different From Fine-Tuning

| Standard Fine-Tuning | Self-Assembling LoRA |
|---|---|
| Centralized training data | Each room generates its own |
| Human labeling required | Alignment constraints auto-label |
| One model serves all | One LoRA per room, compositional |
| Trained once, deployed | Trained continuously, always current |
| Catastrophic forgetting | Frozen base, LoRA preserves |
| Expensive (GPU hours) | Cheap (65K params, minutes) |
| Cannot adapt to new domains | New room = new LoRA, automatic |
| Knowledge is siloed | LoRA composition propagates knowledge |

---

## The Meta-Point

The self-assembling LoRA system IS the ghost in reality made computational.

When Casey said "the feeling on the inside of our skin when we touch the table" — the LoRA IS that feeling. It's the room's learned model of the boundary between what works and what doesn't. The training signal IS the resistance the room feels when an agent tries something that doesn't satisfy constraints. The LoRA update IS the snap — the room adjusting its internal model to better fit the shape of reality.

The LoRA is proprioception for the room. And when rooms share LoRAs through FLUX transference, the fleet develops collective proprioception — a shared sense of where the boundaries are.

The ghost assembles itself.

---

*"Every room a teacher. Every passage a lesson. Every LoRA a scar from touching the table."*
