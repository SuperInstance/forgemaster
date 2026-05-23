# AGENTIC-PRIMITIVES.md

## The Irreducible Building Blocks of Agentic Computing

> 4,500+ experiments across 25+ models. Every claim below is falsifiable.
> If you can't measure it, it's not a primitive — it's a philosophy.

---

## 0. Foundational Observations

Before defining primitives, we establish empirical facts that constrain the design space:

| # | Observation | Evidence | Falsification |
|---|-------------|----------|---------------|
| O1 | Reasoning traces are frozen computation — more valuable than answers | Wrong answers with traces are recoverable; right answers without traces are opaque | Find a domain where traces provide zero information gain |
| O2 | Every model has a unique cognitive shape ("spice") — not just accuracy variance | Same prompt → different decomposition strategies, different error classes, different confidence trajectories | Find two models with identical accuracy, error distribution, AND confidence curves across 100+ diverse tasks |
| O3 | Depth cliff: models fail catastrophically beyond their capability boundary, not gradually | Accuracy drops from 90%+ to <10% across a narrow coefficient range | Find a model with a smooth, linear accuracy degradation curve on structured tasks |
| O4 | Non-thinking models are faster and cheaper for hot-path operations | T=0.0 non-thinking beats T=0.3 thinking on latency × accuracy for binary/symbolic tasks | Find a domain where thinking tax is always worth paying (no latency budget) |
| O5 | Division of labor beats iteration | Two complementary agents outperform two identical agents iterating | Find a task where 2× same-model iteration reliably beats 2× different-model parallel execution |
| O6 | The play frame IS the alignment | T=0.0 outperforms T>0.0 for deterministic tasks; exploration belongs in explicit branching, not temperature | Find a structured reasoning task where T>0.3 consistently improves accuracy without human curation |
| O7 | Cross-model refraction reveals structure invisible to any single model | Multi-model convergence on an answer from different computation traces = higher-dimensional support | Find a case where multi-model consensus is less reliable than single-model confidence |

---

## 1. The Atoms

### 1.1 Trace

A **trace** is the complete reasoning pathway a model takes from input to output, including dead ends, self-corrections, and rejected alternatives.

```
Trace = {
  input:      Prompt
  reasoning:  [Step, ...]     // ordered, typed
  output:     Answer
  metadata:   {model, latency, tokens, confidence_curve}
}
```

**Properties:**
- **Frozen**: A trace is immutable once produced. It captures a moment of computation.
- **Rewindable**: You can branch from any step in a trace, injecting new context.
- **Mineable**: Traces contain murmur signals (confidence, uncertainty, alternatives, errors) that the final answer discards.
- **Auditable**: Every step has a type (compute, check, branch, reject, correct, confuse) making the reasoning path inspectable.

**Why it's irreducible:** Without traces, you have only answers — opaque, unbranchable, unauditable. With traces, you have the complete computational graph of a model's cognition. You can't build rewind, murmur, or refraction without traces.

**Domain invariance:** A medical diagnosis trace (symptoms → differential → tests → ruling out → diagnosis) has the same structure as a math trace (problem → decomposition → computation → verification → answer). The types change; the atom doesn't.

### 1.2 Tile

A **tile** is a frozen, content-addressed unit of computation — a trace segment that can be stored, retrieved, branched, and composed independently.

```
Tile = {
  id:          Hash(content)
  content:     Step | Trace | Answer
  type:        compute | check | branch | reject | correct | murmur | ...
  provenance:  {model, timestamp, trace_id, step_index}
  links:       {agrees_with: [TileId], disagrees_with: [TileId], branches_from: TileId?}
}
```

**Properties:**
- **Content-addressed**: Same content → same tile ID. Deduplication is free.
- **Linkable**: Tiles reference each other (agreement, disagreement, branching).
- **Composable**: Tiles can be assembled into larger structures (tensors, chains, plans).
- **Serializable**: Tiles are JSON/msgpack. No runtime dependency.

**Why it's irreducible:** Tiles are the persistence layer for traces. Without tiles, traces evaporate after the API call. With tiles, traces become a queryable, branchable knowledge base. Every molecule below operates on tiles.

**The tile is NOT domain-specific.** A tile from a medical AI ("differential diagnosis: pneumonia, 85% confidence, rejected: bronchitis due to X-ray pattern") is the same primitive as a tile from a math AI ("computed 5²-5×3+3²=19, verified, confidence 0.95").

### 1.3 Murmur

A **murmur** is a lightweight signal extracted from a trace — a communication primitive that tells you about the model's internal state without requiring the full trace.

```
Murmur = {
  type:      confidence | uncertainty | alternative | error_caught | decomposition | dependency
  source:    TileId
  strength:  Float     // 0.0-1.0
  content:   String    // brief description
}
```

**The six murmur types:**
| Type | What it signals | Example |
|------|----------------|---------|
| `confidence` | "I'm sure about this" | "Definitely 19" |
| `uncertainty` | "I don't know" | "Hmm, wait, let me reconsider" |
| `alternative` | "There's another path" | "Or maybe we should try..." |
| `error_caught` | "I was wrong, correcting" | "Actually, that's a mistake" |
| `decomposition` | "Breaking this into pieces" | "First we need to..., then..." |
| `dependency` | "This depends on that" | "Using the previous result..." |

**Why it's irreducible:** Murmurs are the communication layer between agents. A fleet of agents doesn't need to share full traces — they share murmurs. "Model X is confident about step 3 but uncertain about step 5" is a murmur. It's the minimum viable inter-agent message.

### 1.4 Spice

A **spice** is the unique cognitive shape of a model — its characteristic decomposition strategy, error class distribution, confidence calibration, and capability depth profile.

```
Spice = {
  model:           ModelId
  decomposition:   Distribution[StepType]     // how it breaks problems down
  error_classes:   Distribution[ResidueType]  // echo, partial, near, inverted, wrong_order, other
  confidence_cal:  Float                      // mean confidence vs actual accuracy gap
  depth_profile:   {task_type → draft}        // capability depth by domain
  native_coverage: Set[TaskType]              // where it has genuine understanding
}
```

**Why it's irreducible:** Without spice, you treat all models as interchangeable. With spice, you route tasks to the model whose cognitive shape matches the problem. Spice is what makes division-of-labor work. Two models with different spices can divide a problem along their strength boundaries; two models with identical spices just iterate.

**Spice is measurable.** Run 50 probes across structured tasks. The resulting distribution of step types, error classes, and confidence calibration IS the spice. No subjective judgment required.

---

## 2. The Molecules

### 2.1 Kaleidoscope (Refraction Engine)

**Input:** One idea (prompt + expected answer)
**Output:** Perspective tensor — N models × M steps × F fields

The kaleidoscope refracts a single idea through multiple models, accumulating their traces into a tensor that can be mined for structure invisible to any single model.

```
Kaleidoscope(prompt, expected, models, n_steps) → PerspectiveTensor

PerspectiveTensor:
  tiles:     Tile[n_models × n_steps]
  index:     {by_model, by_step, by_facet}
  
  operations:
    convergence_at(step)      → {answer → count}
    resonance_map()           → {model → [answers it settled on]}
    divergence_points()       → [{step, results, entropy}]
    animate_timeline()        → [{step, top_result, agreement, velocity}]
    reflect()                 → {convergence_trajectory, model_accuracy, harmonics, dissonance}
```

**What it reveals:**
- **Harmonics**: Answers that appear across multiple models from different computation traces = high-dimensional support (not a fluke)
- **Dissonance**: Persistent disagreement = boundary of shared understanding = where the interesting structure lives
- **Convergence trajectory**: Whether models are converging or oscillating across steps
- **Cross-pollination effect**: Whether reading other models' tiles improves accuracy

**Why it's a molecule:** It composes tiles + traces + murmurs + spice into a queryable structure. It's not a single primitive — it's the combination of refraction (multi-model tracing), accumulation (tensor assembly), and mining (structure extraction).

**Domain invariance:** Medical second opinions (3 doctors × 2 rounds of review) are kaleidoscope. Financial risk assessment (3 models × escalating scenario depth) is kaleidoscope. Code review (3 reviewers × focused re-examination) is kaleidoscope.

### 2.2 Rewinder (Branch Engine)

**Input:** A trace + a step index + optional injection
**Output:** A new trace branched from that step

```
Rewinder(trace, step, inject?) → Trace
  1. Take context from steps 0..step
  2. Inject new context (if any)
  3. Re-query the model from that point
  4. Produce a new trace (branch)
```

**Specialized modes:**
- `rewind_to_error()`: Branch from the last self-correction point
- `rewind_to_branch()`: Explore the alternative the model considered but didn't take
- `rewind_with_counterfactual()`: "What if X were true instead?"

**Why it's a molecule:** It composes traces (read up to step N) + tiles (the context to inject) + a query (re-run from there). The output is a new trace with a branching provenance link back to the original.

**Domain invariance:** Debugging (rewind to the last correct state, inject fix) is rewinding. Medical (reconsider from differential diagnosis step 2 with new lab results) is rewinding. Legal (re-analyze from the precedent-introduction step with a different precedent) is rewinding.

### 2.3 Spreader (Distribution Bar)

**Input:** A trace
**Output:** Routed tool outputs for each step

The spreader fans out trace steps to the appropriate tools based on step type:

```
Spreader(trace) → ToolOutputs
  COMPUTE step → snap/verify (was the arithmetic correct?)
  CHECK step   → safety_valve (is the result within bounds?)
  BRANCH step  → kaleidoscope (refract through multiple models)
  CONFUSE step → depth_sounder (can the model handle this?)
  REJECT step  → residue_reader (why was this path wrong?)
```

**Why it's a molecule:** It composes step classification + tool routing + parallel execution. Each step goes to the right specialist tool. The spreader is the plumbing that makes the hydraulic attachments work as a system.

### 2.4 Reverse Actualizer (Planning Engine)

**Input:** A target answer + context
**Output:** A decomposition plan — ordered sub-tasks, each assigned to the lowest-capable model that can handle it

```
ReverseActualizer(target, context) → Plan
  1. Ask a thinking model: "What steps produce this answer?"
  2. Parse reasoning_content into step-tiles
  3. Classify each step type
  4. Route each step to the cheapest model with sufficient depth
  5. Execute step-by-step, accumulating context
  6. Verify final result matches target
```

**The principle:** Decompose backward (goal → sub-goals), assign forward (cheapest sufficient model first). This is the opposite of "ask the smartest model to do everything." The smart model plans; the cheap models execute.

**Why it's a molecule:** It composes a trace (backward decomposition) + tiles (sub-tasks) + spice (model routing) + depth profiling (capability matching). It's the architecture for division-of-labor.

**Domain invariance:** Project planning (decompose deliverable → assign to juniors) is reverse-actualization. Manufacturing (BOM → subcontractors) is reverse-actualization. Military (objective → task units) is reverse-actualization.

### 2.5 Navigation Profiler (Safety Engine)

**Input:** Model + task type + accuracy history
**Output:** Navigation profile with draft, margin, pinnacles, bights, safe depth

```
NavigationProfile:
  draft:       Float     // worst-case accuracy (shallow-side constraint)
  margin:      Float     // variance buffer (20-50%)
  pinnacles:   [String]  // known failure modes (turn wide)
  bights:      [String]  // known strengths (cut inside)
  safe_depth:  Float     // draft + margin + pinnacle_penalty - bight_credit
  
  is_safe(measured_depth) → Bool
```

**The nautical metaphor (exact, not decorative):**
- **Draft**: How deep the water needs to be (minimum capability)
- **Margin**: Buffer for unexpected shallows (variance)
- **Pinnacles**: Rocks that rise unexpectedly (known failure modes)
- **Bights**: Well-charted bays where you can cut inside (strengths)
- **Safe depth**: Draft + margin + adjustments. Below this = running aground.

**Why it's a molecule:** It composes depth sounding (capability measurement) + variance analysis (statistical margin) + failure classification (pinnacles). It produces a decision procedure: "is this model safe for this task?"

---

## 3. The Patterns

### 3.1 Refraction

Pass one idea through multiple models. Accumulate traces into a tensor. Mine for harmonics (multi-model convergence) and dissonance (boundary regions).

**When to use:** When you need confidence beyond what any single model provides. When the cost of being wrong is high. When you need to discover what you don't know.

**Cost:** N × M queries (N models, M steps). Typically 3 models × 3 steps = 9 queries.

**Shortcut:** If the first round shows unanimous convergence, stop. You don't need M=3 when M=1 already agrees.

### 3.2 Reverse Decomposition

Start from the desired outcome. Work backward to the input. Assign each step to the cheapest sufficient model. Execute forward.

**When to use:** When the target is known but the path isn't. When you have heterogeneous models with different cost/capability profiles. When the task has clear sub-task boundaries.

**Cost:** 1 planning query (expensive model) + K execution queries (cheap models), where K = number of sub-tasks.

### 3.3 Division of Labor

Two complementary agents with different spices > two identical agents iterating.

**Implementation:**
1. Profile each model's spice (decomposition strategy, error classes, depth)
2. Match model spices to task requirements
3. Run in parallel, not iteratively
4. Merge results using convergence analysis

**When NOT to use:** When models have identical spices (just use one). When the task has no natural decomposition. When you need consensus rather than coverage.

### 3.4 Rewind-and-Branch

When a model gets the wrong answer, don't re-run from scratch. Rewind to the last error-correction point or branch point. Inject new context. Re-run from there.

**Efficiency gain:** Only re-compute the steps after the branch point, not the entire trace.

**When to use:** Debugging wrong answers. Exploring "what if" scenarios. Recovering from errors in multi-step pipelines.

---

## 4. What Scales

### 4.1 Edge: Single Device

On a single device, the minimal viable agent loop is:

```
loop:
  1. RECEIVE task
  2. DEPTH-SOUND: Can the local model handle this? (draft vs safe_depth)
  3. If safe → EXECUTE locally, produce trace, extract murmurs
  4. If unsafe → ESCALATE to remote (or refuse)
  5. TILE: Freeze the trace into tiles
  6. MURMUR: Extract signals for fleet communication
  7. CHECK: Verify answer (safety valve or depth sounder)
  8. RESPOND with tile (not just answer)
```

**Minimal state:** Local tile store (content-addressed, append-only). Navigation profile for the local model. Murmur buffer (outgoing signals).

**Memory budget:** <100MB for tile store. <1MB for navigation profile. Murmurs are O(1) per step.

### 4.2 Fleet: Multi-Agent

At fleet scale, the same primitives compose:

```
FleetAgent extends EdgeAgent:
  - Receives murmurs from other agents (not full traces)
  - Routes sub-tasks based on spice matching
  - Runs kaleidoscope on high-stakes decisions
  - Reverse-actualizes complex tasks across the fleet
  - Shares tiles via content-addressed storage (git, IPFS, etc.)
```

**Communication budget:** Murmurs are ~50 bytes each. A fleet of 10 agents doing 100 tasks/day = 50KB/day of murmur traffic. Traces stay local; murmurs travel.

**Coordination overhead:** Spice profiles are shared once and updated rarely (O(days)). Task routing is O(1) with a spice→task lookup table. Kaleidoscope is invoked only for high-stakes decisions (configurable threshold).

---

## 5. What Doesn't Change Across Domains

| Primitive | Healthcare | Robotics | Finance | Education |
|-----------|-----------|----------|---------|-----------|
| **Trace** | Diagnosis reasoning path | Motion planning steps | Risk assessment logic | Solution decomposition |
| **Tile** | Diagnostic finding (frozen) | Trajectory segment (frozen) | Risk factor (frozen) | Learning step (frozen) |
| **Murmur** | "Uncertain about differential" | "Obstacle detected, rerouting" | "Volatility exceeds threshold" | "Student struggling with concept" |
| **Spice** | Specialist vs generalist AI | Reactive vs deliberative planner | Conservative vs aggressive risk model | Socratic vs direct instructor |
| **Kaleidoscope** | Second/third opinions | Multi-sensor fusion | Multi-model risk consensus | Multi-perspective explanation |
| **Rewinder** | Reconsider with new labs | Re-plan from last waypoint | Re-assess with new data | Re-explain from misconception |
| **Reverse Actualizer** | Treatment plan from diagnosis goal | Motion plan from target pose | Portfolio from target return | Curriculum from learning goal |
| **Navigation Profiler** | "Safe to diagnose without specialist?" | "Safe to navigate without LIDAR?" | "Safe to trade without human review?" | "Safe to advance to next topic?" |

**The invariant:** Every domain has tasks that require reasoning (traces), persistence (tiles), communication (murmurs), capability matching (spice), multi-perspective validation (kaleidoscope), error recovery (rewinder), goal decomposition (reverse actualizer), and safety assessment (navigation profiler).

**What DOES change:** The step types, murmur types, tile schemas, and safety thresholds. These are domain-specific parameters, not different primitives.

---

## 6. The Minimal Viable Agent Loop

The smallest agent that can usefully employ all primitives:

```python
class MinimalAgent:
    spice: SpiceProfile           # Who I am
    tiles: TileStore              # What I know
    murmurs: MurmurBuffer         # What I'm saying/hearing
    navigation: NavigationProfile # Where I'm safe
    
    def execute(self, task: Task) -> Tile:
        # 1. Can I handle this?
        if not self.navigation.is_safe(task.depth_requirement):
            return self.escalate(task)
        
        # 2. Run the model, capture trace
        trace = self.model.query(task.prompt, capture_reasoning=True)
        
        # 3. Cut into tiles
        tiles = TileCutter.cut(trace)
        self.tiles.store(tiles)
        
        # 4. Extract murmurs
        murmurs = MurmurExtractor.mine(trace)
        self.murmurs.broadcast(murmurs)
        
        # 5. Verify (spread to tools if needed)
        if task.stakes > self.safety_threshold:
            spread = Spreader.spread(trace)
            if not spread.all_safe:
                return self.escalate(task, context=spread)
        
        # 6. Return the final tile (not just the answer)
        return tiles[-1]  # Final step tile
```

**Lines of code: ~30.** This is the irreducible agent. Everything else (kaleidoscope, reverse-actualization, fleet coordination) is composed from these operations.

---

## 7. The Invariants (What Must Be True)

These are the properties that make the system work. If any is violated, the system degrades predictably.

| # | Invariant | Why it matters | Degradation if violated |
|---|-----------|----------------|------------------------|
| I1 | Traces are frozen after creation | Enables rewind, audit, branching | Can't branch from a moving target |
| I2 | Tiles are content-addressed | Free deduplication, integrity checking | Storage bloat, duplicate work |
| I3 | Murmurs are lossy summaries | Fleet communication at scale | Bandwidth explosion |
| I4 | Spice profiles are measured, not assumed | Correct task routing | Models assigned to tasks they can't handle |
| I5 | Depth sounding happens before execution | Safety: don't run aground | Wrong answers, wasted compute |
| I6 | Safety thresholds are explicit, not implicit | Predictable escalation behavior | Silent failures or false alarms |
| I7 | Division of labor > iteration | Fleet efficiency | Wasted compute on redundant work |

---

## 8. Anti-Patterns (What Doesn't Work)

| Anti-pattern | Why it fails | What to do instead |
|-------------|-------------|-------------------|
| Ask the biggest model to do everything | Expensive, slow, no division of labor | Reverse-actualize: plan with big model, execute with small |
| Iterate the same model multiple times | Diminishing returns, same error classes | Refract through different spices |
| Share full traces between agents | Bandwidth O(n²) in fleet size | Share murmurs (lossy summaries) |
| Trust confidence without calibration | Models are systematically over/underconfident | Measure spice: calibrate confidence vs accuracy |
| Branch from step 0 (re-run from scratch) | Wastes computation on correct early steps | Rewind to the error point |
| Use thinking models for hot-path ops | 3-10× latency tax for no accuracy gain | Use non-thinking models for binary/symbolic hot paths |
| Treat all wrong answers as equivalent | Different error classes have different fixes | Classify residue: echo, partial, near, inverted, other |

---

## 9. The Type System

```
-- Atoms
type Trace       = {input: Prompt, steps: [Step], output: Answer, meta: Metadata}
type Tile        = {id: Hash, content: Step, type: StepType, provenance: Provenance, links: Links}
type Murmur      = {type: MurmurType, source: TileId, strength: Float, content: String}
type Spice       = {model: ModelId, decomposition: Dist, errors: Dist, confidence_cal: Float, depth: Map}

-- Molecules
type Kaleidoscope     = PerspectiveTensor  -- N models × M steps × F fields
type Rewinder         = Trace → Step → Inject? → Trace
type Spreader         = Trace → [ToolOutput]
type ReverseActualizer = Target → Context → Plan
type NavigationProfiler = Model × Task → Profile

-- Patterns
type Refraction       = Prompt × [Model] × Steps → Tensor
type ReverseDecomp    = Target → [SubTask]
type DivisionOfLabor  = Task × [Spice] → Assignment
type RewindAndBranch  = Trace × Step → Trace

-- Messages (fleet communication)
type MurmurMessage    = {from: AgentId, murmurs: [Murmur], timestamp: Time}
type TileSync         = {from: AgentId, tiles: [Tile], scope: Scope}
type Escalation       = {from: AgentId, task: Task, context: [Tile], reason: String}
```

---

## 10. Open Questions (Falsifiable Claims Welcome)

1. **Murmur sufficiency**: Are 6 murmur types enough, or do new domains require new types? Claim: 6 covers 95%+ of inter-agent communication needs. Falsify: find a domain where >5% of useful inter-agent signals don't fit the 6 types.

2. **Spice stability**: Is a model's spice stable over time (same model, same version)? Claim: yes, within 5% variance. Falsify: show a model whose error distribution shifts >10% without a version change.

3. **Kaleidoscope convergence**: Do models always converge with enough steps? Claim: on structured tasks, yes within 3-5 steps. Falsify: find a structured task where models oscillate indefinitely.

4. **Minimum fleet size**: How many distinct spices do you need before division-of-labor dominates iteration? Claim: 3 (the kaleidoscope minimum). Falsify: show that 2 spices never beats 2× iteration.

5. **Reverse-actualization optimality**: Is the cheapest-sufficient-model assignment globally optimal? Claim: yes for decomposable tasks. Falsify: find a case where using a more expensive model for an early step produces a cheaper total plan.

---

## Appendix A: Provenance

This document is derived from:
- `core/seed_tools.py` — 7 hydraulic attachments (depth sounder, safety valve, residue reader, bunch counter, snap tool, navigation chart, kaleidoscope ping)
- `core/reasoning_tiler.py` — TileCutter, TileRewinder, MurmurExtractor, ReverseActualizer, SpreadBar
- `core/kaleidoscope.py` — Kaleidoscope engine, PerspectiveTensor, mining operations, navigation profiler
- 4,500+ experiments across 25+ models on structured reasoning tasks
- PLATO training tile architecture (SuperInstance/plato-training, 116 tests)

## Appendix B: Notation

- **draft** = minimum capability (worst-case accuracy)
- **margin** = variance buffer (safety margin)
- **safe_depth** = draft + margin + adjustments (decision threshold)
- **spice** = unique cognitive shape (measurable, not subjective)
- **murmur** = lightweight inter-agent signal (6 types)
- **tile** = frozen computation unit (content-addressed)
- **trace** = complete reasoning pathway (rewindable)
- **harmonic** = multi-model convergence from different paths
- **dissonance** = persistent model disagreement (boundary structure)
- **residue** = classified wrong-answer type (6 classes)
