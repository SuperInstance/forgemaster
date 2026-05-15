# PLATO External Cognition: Architecture Design

**Date:** 2026-05-14
**Evidence base:** plato_external_cognition.py results, ABSTRACTIVE-SYNTHESIS.md,
core/pinna.py, core/tile_lifecycle.py, core/harness.py
**Status:** Every design decision traces to experimental evidence. No speculative features.

---

## I. The Core Experimental Result

Five findings drive this design:

| Condition | Model | Accuracy | Mechanism |
|-----------|-------|----------|-----------|
| MONO (max_tokens=1000) | Seed-mini | 92% | Direct computation, one call |
| PLATO-4 (4 steps × 300 tok) | Seed-mini | 92% | Externalization is lossless |
| MONO (max_tokens=1000) | Qwen-4B | 58-62% | Thinking chain, but errors accumulate |
| PLATO-4 (4 steps × 300 tok) | Qwen-4B | 17% | Thinking tax swamps each tile |
| PLATO 2-step via reasoning_content | Qwen-4B | 50% | Extract thinking as tile = near-mono |

**The decisive insight:** For Qwen-4B, `reasoning_content` IS the frozen step. The model's
internal chain-of-thought is a naturally structured computation trace. Externalizing it as
a PLATO tile recovers ~80% of monolithic performance without requiring the full 1000-token budget
per step. The thinking chain that was getting truncated at max_tokens=300 can instead be
*read back* in the next call as accumulated context.

The gap from 50% to 62% (mono) is the partial-result extraction problem: the current
2-step implementation reads `reasoning_content[:500]` as a raw string. A structured tile
with `partial_result` and `confidence` fields closes this gap.

---

## II. The PLATO Tile Protocol for Externalized Cognition

### 2.1 New Tile Type: `cognition`

The existing `Tile` type field (`knowledge | loop | rock | residue | seed | spline | meta`)
does not capture computation-in-progress. Add a `cognition` type with semantics:

> A cognition tile records one step of an ongoing reasoning chain. It is frozen at write
> time but consumed — not just referenced — by the next step's prompt construction.

### 2.2 Extended Tile Dataclass

Add the following fields to `core/tile_lifecycle.py:Tile`:

```python
# ── Cognition fields (only populated when type="cognition") ──

step_number: int = 0
# Which step in the chain this tile represents. Step 1 = first decomposition.

computation_trace: str = ""
# The raw thinking output. For Qwen-4B: contents of reasoning_content.
# For Seed-mini: contents of content (direct output).
# Capped at 600 tokens. Do NOT truncate mid-sentence — truncate at last period.

partial_result: Optional[str] = None
# The extracted intermediate answer, if any. None = step did not converge.
# Extracted by the same extract_num() pattern used in experiments.
# Presence of partial_result signals: "this step produced something provable."

confidence: float = 0.0
# Estimated confidence in partial_result. Computed as:
#   1.0 if partial_result matches an earlier step's partial_result (convergence)
#   0.5 if partial_result is a new value
#   0.0 if no partial_result
# NOT a model-generated feeling — derived from convergence detection.

next_step_needed: bool = True
# False when: partial_result is stable across two consecutive steps,
# OR step_number == max_steps.
# This is the convergence gate. The loop reads this to decide whether to continue.

chain_id: str = ""
# UUID shared across all tiles in one reasoning chain.
# Enables: "give me all steps for chain X" without scanning all tiles.

parent_tile_id: str = ""
# ID of the step-(N-1) tile. Enables rewind: walk parent_tile_id links backward.
# "" for step 1 (root of chain).
```

### 2.3 Pinna Encoding for Cognition Tiles

The `PinnaField` in `core/pinna.py` tracks capability boundary state. For cognition tiles,
the pinna field encodes the *quality of computation at this step*, not the agent's long-term
profile:

```python
# How to populate PinnaField for a cognition tile:

pinna = PinnaEncoder.encode(
    agent_id=model_id,          # "ByteDance/Seed-2.0-mini" etc.
    agent_stage=_stage_for(model_id),  # see §V model table
    residue_class=_residue_for(partial_result, expected),
    confidence=tile.confidence,  # convergence-derived, not felt
    distance_from_boundary=_dist_from_boundary(step_number, max_steps),
    # distance_from_boundary: starts at -0.8 (deep CANNOT — step 1 has no result yet),
    # approaches +1.0 as convergence is detected.
    temperature=0.0,
    max_tokens=_budget_for(model_id),   # 50 for Seed-mini, 300 for Qwen-4B
    n_trials=step_number,       # each step = one trial in the capability loop
)
```

The `PinnaReader.classify_tile_value()` — already implemented — then allows downstream
steps to rank cognition tiles as `essential` (near boundary, same stage) vs `reliable`
(fully resolved). This means the context selection for step N+1 automatically prioritizes
tiles where the computation was uncertain, which is exactly where re-reading adds value.

### 2.4 DisproofOnlyGate Exemption

Cognition tiles must bypass the `DisproofOnlyGate`. They are transient by design — they do
not claim to falsify prior knowledge. Add `"cognition"` to `DisproofOnlyGate.EXEMPT_TYPES`:

```python
EXEMPT_TYPES = {"loop", "spline", "meta", "seed", "cognition"}
```

And add cognition tiles to `MortalitySweep.PROTECTED_TYPES` only during their chain's
lifetime. Once `next_step_needed=False` (chain complete), they become mortal with a 24-hour
immunity window, then age normally.

---

## III. The Bootstrap Loop

The bootstrap loop is Casey's "build smarter awareness" loop — iterative externalization
where each step reads its own prior steps as context.

### 3.1 Algorithm

```
function plato_cognition_loop(model, prompt, max_steps=4):

  chain_id = uuid4()
  tiles = []
  prev_partial = None

  for step in range(1, max_steps + 1):

    # STEP 1: Build context from accumulated tiles
    context = build_context(tiles)      # §3.2

    # STEP 2: Call model for one reasoning step
    content, reasoning = query(model, context, prompt, step)

    # STEP 3: Extract partial result
    partial = extract_partial(content, reasoning)   # §3.3

    # STEP 4: Compute convergence
    converged = (partial is not None) and (partial == prev_partial)
    confidence = 1.0 if converged else (0.5 if partial else 0.0)

    # STEP 5: Freeze the tile
    tile = Tile(
      type="cognition",
      chain_id=chain_id,
      step_number=step,
      computation_trace=_extract_trace(content, reasoning, model),
      partial_result=partial,
      confidence=confidence,
      next_step_needed=not converged,
      parent_tile_id=tiles[-1].id if tiles else "",
      pinna=_encode_pinna(model, step, partial, confidence),
    )
    store.put(tile)     # bypass disproof gate (cognition type is exempt)
    tiles.append(tile)

    # STEP 6: Early exit on convergence
    if converged:
      break

    prev_partial = partial

  # STEP 7: Final extraction
  return extract_final_answer(tiles)
```

### 3.2 Context Construction

This is where the current `run_plato_chain()` loses accuracy. The naive implementation
concatenates raw `reasoning[:500]` strings. The structured approach:

```python
def build_context(tiles: List[Tile]) -> str:
    """Build system prompt from accumulated cognition tiles."""
    if not tiles:
        return "You are computing step by step. This is step 1."

    # Rank tiles by pinna value for the current model's stage
    reader = PinnaReader(agent_stage=current_model_stage, ...)
    ranked = reader.rank_tiles([t.to_dict() for t in tiles])

    parts = []
    for tile, value in ranked:
        if value == "noise":
            continue
        parts.append(
            f"Step {tile.step_number} [{value}]:\n"
            f"  trace: {tile.computation_trace[:400]}\n"
            f"  result: {tile.partial_result or '(not yet determined)'}\n"
            f"  confidence: {tile.confidence:.1f}"
        )

    return (
        "Previous computation steps (ranked by relevance):\n\n"
        + "\n\n".join(parts)
        + f"\n\nThis is step {len(tiles) + 1}. Continue the computation."
    )
```

The pinna ranking means uncertain steps (low `distance_from_boundary`) get marked
`essential` and are included first — the model re-reads the hardest parts of its own
prior reasoning before proceeding.

### 3.3 Trace Extraction by Model Type

The extraction differs by model type — this is the key lesson from the 2-step experiment:

```python
def _extract_trace(content: str, reasoning: str, model_id: str) -> str:
    """Extract the computation trace appropriate for this model type."""
    if "Qwen" in model_id and len(model_id) > 10:
        # Qwen-4B+: thinking is in reasoning_content, answer in content
        # Use reasoning as the primary trace, content as the extraction target
        trace = reasoning.strip()
    else:
        # Seed-mini: direct computation in content
        trace = content.strip()
    # Cap at 600 tokens (~450 words) — enough for complex arithmetic traces
    # but bounded to prevent tile bloat
    return trace[:2400]  # ~600 tokens at 4 chars/token
```

The 50% result in the 2-step experiment came from using `reasoning_content` this way.
The 12-point gap to MONO (62%) is closeable by:
1. Structured `partial_result` extraction (not just `extract_num(content)`)
2. Confidence-gated convergence (stop early if partial matches prior step)
3. PinnaReader-ranked context feeding (current impl uses raw concatenation)

---

## IV. The Spreader-Tool Integration

### 4.1 The Fork Operation

At step K in a reasoning chain, the chain can be forked to N models. Each model receives
the same context (tiles 1..K) and produces a different continuation (tile K+1). This is
the "wide interpretation" Casey described.

```
tile[1] → tile[2] → tile[K]
                         ↓
                    [fork at step K]
                    /      |       \
           model_A      model_B    model_C
              ↓            ↓          ↓
         tile[K+1_A]  tile[K+1_B]  tile[K+1_C]
```

The fork produces N parallel chains. The merge step reads all K+1 tiles and selects
the one with:
1. `next_step_needed=False` (converged), OR
2. Highest `pinna.confidence`, OR
3. Majority vote on `partial_result` if multiple chains agree

### 4.2 New Topology in SwarmRouter

Add `SPREADER` to `Topology` in `core/swarm_router.py` (not yet seen but implied by
`harness.py:Topology`):

```python
class Topology(Enum):
    COLLECTIVE   = "collective"
    JAM          = "jam"
    SPREADER     = "spreader"    # NEW: fork chain to N models at step K
```

The spreader routing descriptor:

```python
@dataclass
class SpreaderDescriptor:
    """Fork a reasoning chain to N models at a given step."""
    chain_id: str           # which chain to fork
    fork_step: int          # fork after this step (K)
    models: List[str]       # model IDs to fan out to
    max_steps_after: int = 2  # each branch continues for at most this many more steps
    merge_strategy: str = "confidence"  # "confidence" | "majority" | "first_converged"
```

In `SwarmRouter.route_with_profiles()`, select SPREADER topology when:
- Task is multi-step AND
- At least 2 models in fleet have different `agent_stage` values AND
- `step_number >= 1` (at least one step already computed)

### 4.3 Why Spreader Recovers Accuracy

The 2-step hybrid result (50%) uses Seed-mini to decompose and Qwen-4B to synthesize.
The spreader generalizes this: at the decomposition step (step 1), fork to both models.
Seed-mini's tile will have `partial_result` from direct computation. Qwen-4B's tile
will have a richer `computation_trace` but possibly no `partial_result` yet. The merge
reads both: use Seed-mini's partial as a ground-truth anchor, use Qwen-4B's trace as
the scaffold for subsequent steps. This replicates the L1 anchor pattern from
`Level1SelfScaffolding` — but derives the anchors from model outputs rather than
pre-computing them.

---

## V. Model-Specific PLATO Strategies

These strategies derive directly from the capability model `C(m,t) = T·A·K·M·E`:

### Seed-mini: Direct Computation Tiles

```
Evidence:  MONO=92%, PLATO-4=92% — externalization is lossless
Profile:   T≈0.95, W>10, τ≈0, V(model)≈50 tokens
Strategy:  Direct computation tiles, 50 tokens per step, no reasoning extraction
```

```python
SEED_MINI_CONFIG = {
    "max_tokens": 50,
    "trace_source": "content",      # answer IS the trace
    "step_system_prompt": "Compute the next step. Output only the value.",
    "steps_needed": 1,              # almost always converges in step 1
    "tile_confidence_threshold": 0.9,
}
```

Seed-mini produces `computation_trace = content` (the direct answer). For multi-step
problems, `steps_needed = min(4, depth_of_problem)`. The key insight: Seed-mini's
externalization overhead is near zero. Each tile is 50 tokens of direct computation.
No thinking tax. The PLATO loop for Seed-mini is effectively a batched version of
sequential arithmetic with auditable intermediate values.

### Qwen-4B: Reasoning Tiles (Extract from reasoning_content)

```
Evidence:  MONO=62% (mt=1000), PLATO-4=17% (mt=300), 2-step=50% (reasoning_content as tile)
Profile:   T≈1.0, W>10, τ=V(model)/max_tokens, V(Qwen-4B)≈350-400 tokens
Strategy:  Extract reasoning_content as tile, feed back as context for next step
```

```python
QWEN_4B_CONFIG = {
    "max_tokens": 400,              # must be ≥ V(Qwen-4B) ≈ 350 tokens
    "trace_source": "reasoning_content",  # thinking chain is the trace
    "step_system_prompt": (
        "Continue the computation based on the steps above. "
        "Show your full reasoning. End with 'Final Answer: <number>'."
    ),
    "steps_needed": 3,              # typical convergence in 2-3 steps
    "tile_confidence_threshold": 0.7,
}
```

The critical parameter: `max_tokens=400`. At `max_tokens=300`, Qwen-4B hits the
V(model) threshold and produces `finish_reason="length"` before emitting its answer.
The PLATO-4=17% result IS this failure mode applied four times in sequence. Each tile
is a truncated think with no partial result — accumulating garbage.

With `max_tokens=400` and `trace_source="reasoning_content"`, each tile contains the
full thinking chain. The next call reads this chain as structured context. The model
does not re-derive the work — it continues from where the trace ended. This is the
bootstrap loop made concrete.

### MiMo: Fast Safety Tiles

```
Evidence:  366ms latency, 86% accuracy on arithmetic (post extraction-fix)
Profile:   Fast inference, answers in reasoning_content (pre-fix was 0%)
Strategy:  Binary decision tiles, cached system prompt, depth=1 tasks only
```

```python
MIMO_CONFIG = {
    "max_tokens": 50,
    "trace_source": "reasoning_content",  # MiMo's answers are in reasoning_content
    "step_system_prompt": "Is this safe? Answer YES or NO only.",
    "steps_needed": 1,              # binary decisions never need iteration
    "tile_confidence_threshold": 0.8,
    "use_case": "safety_check",     # route non-binary tasks away from MiMo
}
```

MiMo's role in the PLATO loop is as a pre-check layer before heavier models. The
harness routes to MiMo first for any depth=1 binary decision (grab safety check,
threshold comparison). Only if MiMo's tile has `confidence < 0.5` or `partial_result=None`
does the harness route to Seed-mini for re-computation. At 366ms per call with cached
system prompts, this adds ≈370ms to the hot path — acceptable for safety-critical checks.

### Harness Routing Logic

The existing `Harness.execute()` in `core/harness.py` routes by topology. Add
`_execute_plato_loop()` as a fourth execution path:

```python
def _execute_plato_loop(
    self, task: TaskDescriptor, assignment: dict, result: TaskResult,
) -> TaskResult:
    """Iterative PLATO externalization loop."""
    model_id = assignment.get("model_id", "ByteDance/Seed-2.0-mini")
    config = MODEL_CONFIGS[model_id]    # see §V configs above

    loop = PlatoCognitionLoop(
        model_id=model_id,
        query_fn=self.query_fn,
        store=self.store,
        config=config,
    )
    chain_result = loop.run(task.prompt)

    result.answer = chain_result.final_answer
    result.success = chain_result.converged
    result.metadata["chain_id"] = chain_result.chain_id
    result.metadata["steps_used"] = chain_result.steps_used
    result.metadata["tiles_written"] = chain_result.tile_ids
    result.agents_used = [model_id]
    return result
```

The routing decision (`_execute_jam` vs `_execute_standard` vs `_execute_plato_loop`)
is made in `execute()` based on `TaskDescriptor.task_type`:

```python
# In Harness.execute(), after routing:
if assignment.get("mode") == "jam":
    result = self._execute_jam(task, assignment, result)
elif assignment.get("mode") == "plato":
    result = self._execute_plato_loop(task, assignment, result)
else:
    result = self._execute_standard(task, assignment, result)
```

---

## VI. Concrete Code Changes to core/ Modules

### 6.1 core/tile_lifecycle.py — Tile Dataclass Extension

Add 7 new fields to `Tile` dataclass (line 37 context):

```python
# ── Cognition chain fields ──
step_number: int = 0
computation_trace: str = ""
partial_result: Optional[str] = None
chain_confidence: float = 0.0
next_step_needed: bool = False
chain_id: str = ""
parent_tile_id: str = ""
```

Add `"cognition"` to `DisproofOnlyGate.EXEMPT_TYPES` and `MortalitySweep.PROTECTED_TYPES`
with a time-limited exception: cognition tiles age out of protection 24h after their
chain's `next_step_needed=False` tile is written.

Add a `TileStore.get_chain(chain_id)` method:

```python
def get_chain(self, chain_id: str) -> List[Tile]:
    """Return all tiles in a reasoning chain, sorted by step_number."""
    return sorted(
        [t for t in self.tiles.values()
         if t.type == "cognition" and t.chain_id == chain_id],
        key=lambda t: t.step_number
    )
```

### 6.2 core/pinna.py — PinnaEncoder Extension

The existing `PinnaEncoder.encode()` takes `distance_from_boundary` as a caller-supplied
float. For cognition tiles, add a convenience method that derives this from step progress:

```python
@staticmethod
def encode_cognition_step(
    model_id: str,
    step_number: int,
    max_steps: int,
    partial_result: Optional[str],
    converged: bool,
) -> PinnaField:
    """Encode pinna metadata for one cognition step.

    distance_from_boundary maps the loop's progress:
      step 1/4, no result → -0.8 (deep CANNOT)
      step 2/4, has result → 0.0 (boundary)
      step 3/4, converging → +0.5 (CAN, approaching)
      converged → +1.0 (deep CAN)
    """
    if converged:
        dist = 1.0
    elif partial_result is not None:
        dist = -0.8 + (step_number / max_steps) * 1.6
    else:
        dist = -0.8

    # Map model_id to AgentStage
    stage = _stage_for_model(model_id)  # see mapping in §V

    return PinnaEncoder.encode(
        agent_id=model_id,
        agent_stage=stage,
        residue_class=ResidueClass.CORRECT if partial_result else ResidueClass.PARTIAL_A2,
        confidence=1.0 if converged else (0.5 if partial_result else 0.0),
        distance_from_boundary=dist,
        n_trials=step_number,
        max_tokens=_budget_for_model(model_id),
    )
```

The `PinnaReader.rank_tiles()` then automatically prioritizes uncertain mid-chain steps
as `essential` — exactly the context slices that benefit most from re-reading.

### 6.3 core/harness.py — PlatoCognitionLoop

New class (or new module `core/plato_loop.py` imported into harness):

```python
@dataclass
class ChainResult:
    chain_id: str
    final_answer: Optional[str]
    converged: bool
    steps_used: int
    tile_ids: List[str]

class PlatoCognitionLoop:
    """Encapsulates the iterative PLATO externalization loop."""

    def __init__(self, model_id, query_fn, store, config):
        self.model_id = model_id
        self.query_fn = query_fn
        self.store = store
        self.config = config

    def run(self, prompt: str) -> ChainResult:
        chain_id = str(uuid.uuid4())
        tiles: List[Tile] = []
        prev_partial = None

        max_steps = self.config.get("steps_needed", 4)

        for step in range(1, max_steps + 1):
            context = self._build_context(tiles)
            content, reasoning = self._query_step(context, prompt, step)
            partial = extract_num(content) or extract_num(reasoning)
            converged = (partial is not None and partial == prev_partial)
            trace = self._extract_trace(content, reasoning)

            tile = Tile(
                type="cognition",
                chain_id=chain_id,
                step_number=step,
                computation_trace=trace,
                partial_result=partial,
                chain_confidence=1.0 if converged else (0.5 if partial else 0.0),
                next_step_needed=not converged,
                parent_tile_id=tiles[-1].id if tiles else "",
                pinna=PinnaEncoder.encode_cognition_step(
                    self.model_id, step, max_steps, partial, converged
                ),
            )
            self.store.put(tile)
            tiles.append(tile)

            if converged:
                break
            prev_partial = partial

        final = tiles[-1].partial_result
        return ChainResult(
            chain_id=chain_id,
            final_answer=final,
            converged=not tiles[-1].next_step_needed,
            steps_used=len(tiles),
            tile_ids=[t.id for t in tiles],
        )
```

### 6.4 SwarmRouter — SPREADER Topology

Add to `core/swarm_router.py`:

```python
def route_spreader(
    self,
    chain_id: str,
    fork_after_step: int,
    models: List[str],
    store: TileStore,
) -> List[str]:
    """Fork a chain at step K → return new chain_ids for each branch."""
    pivot_tiles = store.get_chain(chain_id)[:fork_after_step]
    branch_ids = []

    for model_id in models:
        new_chain_id = str(uuid.uuid4())
        # Copy pivot tiles into new chain with updated chain_id
        for tile in pivot_tiles:
            branch_tile = Tile(
                **{**tile.to_dict(),
                   "id": str(uuid.uuid4()),
                   "chain_id": new_chain_id,
                   "parent_tile_id": tile.id}  # back-reference to pivot
            )
            store.put(branch_tile)
        branch_ids.append(new_chain_id)

    return branch_ids
    # Caller then runs PlatoCognitionLoop on each branch_id with its assigned model
```

---

## VII. Expected Accuracy After Implementation

Tracing each design decision to the experimental gap:

| Gap | Root Cause | Fix | Expected Gain |
|-----|-----------|-----|---------------|
| Qwen PLATO-4=17% vs MONO=62% | max_tokens=300 < V(Qwen)=350 | Config: max_tokens=400 | Recovers to ~50% |
| 2-step=50% vs MONO=62% | Raw string context, no structured partial_result | Structured tile + pinna-ranked context | +8–10 pp → ~58-60% |
| Seed-mini PLATO-4=92% already optimal | τ≈0, direct computation | Keep as-is | 92% maintained |
| Spreader fork gain | Single model sees one interpretation | Fork to Seed-mini+Qwen, merge with Seed-mini anchor | +3-5 pp → ~65% PLATO |

The achievable target: Qwen-4B PLATO loop approaches MONO performance (~60%) at 3×
the token cost but with full step auditability and rewind capability. Seed-mini PLATO
maintains 92% with zero overhead. The spreader adds breadth at the cost of parallelism.

---

## VIII. What NOT to Build

Derived directly from ABSTRACTIVE-SYNTHESIS.md §VIII "Do NOT build":

1. **Do not run Qwen-4B PLATO with max_tokens < 350.** The 17% result proves this.
   Every call that hits `finish_reason="length"` produces a useless tile with no
   `partial_result`. Four such tiles compound to garbage context.

2. **Do not add thinking-mode models to depth=1 arithmetic hot paths.** For simple
   operations, τ(Qwen-4B) = V(model)/max_tokens adds latency with no accuracy gain
   over Seed-mini's direct computation.

3. **Do not use embedding similarity for cognition tile retrieval.** The pinna-ranked
   `PinnaReader.rank_tiles()` is the retrieval mechanism. Adding embedding-based
   retrieval alongside pinna routing creates split-brain context construction where
   the two systems disagree without a principled tie-breaker.

4. **Do not route to MiMo for multi-step arithmetic.** MiMo at 86% accuracy is
   designed for depth=1 binary decisions at 366ms. Multi-step chains require
   `computation_trace` continuity between steps — MiMo's fast inference architecture
   is not optimized for chain-reading.

---

*The path is carved by training. The tiles are the riverbed we read.*
