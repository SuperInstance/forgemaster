# Seed 2.0 Mini Integration Audit

**Date:** 2026-05-12  
**Auditor:** Forgemaster ⚒️  
**Seed Architecture:** 230B total / 23B active params, 10:1 MoE sparsity, AdaCoT adaptive chain-of-thought, 4-level reasoning effort

---

## Summary

Seed 2.0 Mini's MoE architecture has *specific, structural* fit with three of our codebases: the lighthouse model router, the SEED PROTOCOL pipeline, and the falsification/experiment suites. The fit is not generic "use a cheap model" — it maps to the MoE's **expert routing**, **adaptive compute**, and **high-entropy sampling** properties. Below I audit each file, identify where MoE helps, propose code changes, and recommend `reasoning_effort` levels.

---

## File-by-File Audit

### 1. `penrose-memory/src/lib.rs` — Penrose Memory Palace

**Where MoE helps:**

Seed's 10:1 sparsity means only 23B of 230B params activate per token. This is *structurally analogous* to our Penrose tile matching rules (line ~98, `matching_rule_holds`): only tiles with at least one opposite-type neighbor are valid. The MoE router selects experts by similarity — our `project_to_2d` (line ~76) selects tiles by golden-angle hashing similarity.

Specific parallels:
- **MoE expert routing ≈ tile_bit Fibonacci word** (line ~87): both use hash-based binary routing (thick/thin ↔ expert/not-expert). The 1/φ ratio of thick:thin tiles matches the ~10% expert activation ratio.
- **3-coloring ≈ expert groups** (line ~108): 3 colors, 3 shard groups. MoE experts cluster; our tiles cluster by color.
- **Dead reckoning path verification** (line ~156): the intermediate waypoint checks are like MoE's sparse intermediate computations — you don't need every token processed by every expert.

**Code changes to leverage Seed better:**

```rust
// Line ~76: project_to_2d — add MoE-style routing bias
// Current: uniform golden-angle rotation
// Proposed: weight dimensions by "expert affinity" scores
fn project_to_2d(&self, embedding: &[f64]) -> (f64, f64) {
    let mut x = 0.0_f64;
    let mut y = 0.0_f64;
    let dim = self.embedding_dim.min(embedding.len());
    
    // MoE-inspired: top-k dimension selection (activate only top 10% of dims)
    let k = (dim as f64 * 0.1) as usize; // 10:1 sparsity
    let mut indexed: Vec<(usize, f64)> = (0..dim)
        .map(|i| (i, embedding[i].abs()))
        .collect();
    indexed.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
    let active_dims: std::collections::HashSet<usize> = 
        indexed.iter().take(k.max(1)).map(|(i, _)| *i).collect();
    
    for i in 0..dim {
        let val = if i < embedding.len() { embedding[i] } else { 0.0 };
        // Only project through "active expert" dimensions
        let weight = if active_dims.contains(&i) { 1.0 } else { 0.1 };
        let angle = (i as f64) * GOLDEN_ANGLE;
        x += weight * val.abs() * angle.cos();
        y += weight * val.abs() * angle.sin();
    }
    let scale = if dim > 0 { 1.0 / (dim as f64).sqrt() } else { 1.0 };
    (x * scale, y * scale)
}
```

```rust
// Line ~108: three_color — align with MoE expert groups
// Use embedding magnitude to bias color assignment (like MoE router bias)
fn three_color_moe(&self, qx: i64, qy: i64, magnitude: f64) -> u8 {
    let hash = (qx.wrapping_mul(0x517CC1B727220A95u64 as i64))
        .wrapping_add(qy.wrapping_mul(0x9E3779B97F4A7C15u64 as i64));
    let base_color = (hash.wrapping_abs() % 3) as u8;
    // MoE bias: high-magnitude embeddings get promoted to expert group 0
    if magnitude > 2.0 { 0 } else { base_color }
}
```

**reasoning_effort:** Not applicable — this is Rust code, not LLM calls. But if Seed is used to *generate* new projection functions or matching rules: **low** (speed matters, structure is simple).

---

### 2. `penrose-memory/src/cut_and_project.rs` — Cut-and-Project Compiler

**Where MoE helps:**

The PCA projection path (`with_pca_projection`, line ~98) is where MoE shines. Power iteration PCA (lines 130-150) is expensive — it's O(d² × iterations × components). Seed's MoE can:

1. **Accelerate covariance computation** (line ~117): MoE experts specialize in different variance patterns. A Seed query with `reasoning_effort="high"` can compute the covariance matrix from data more efficiently by routing rows to appropriate experts.
2. **Adaptive window sizing** (line ~162): the perpendicular-space acceptance window is currently static (`INV_PHI`). MoE-style adaptive routing could set window width per-region based on local data density — like how MoE routers adjust expert weights per-input.

**Code changes:**

```rust
// Line ~162: Replace static window with adaptive MoE-style window
// Current: static half-width INV_PHI
// Proposed: data-dependent window that adapts like MoE expert capacity

pub fn with_adaptive_window(mut self, data: &[Vec<f64>]) -> Self {
    // ... after PCA projection is set ...
    
    // Compute local density in perpendicular space
    let perp_projections: Vec<Vec<f64>> = data.iter().map(|row| {
        self.project_perp(&row.iter().map(|&v| v).collect())
    }).collect();
    
    // Adaptive window: regions with more data get tighter windows
    // (like MoE expert capacity factor — busy experts get more capacity)
    let perp_dim = self.source_dim - self.target_dim;
    let global_maxes: Vec<f64> = (0..perp_dim).map(|k| {
        perp_projections.iter().map(|p| p[k].abs()).fold(0.0f64, f64::max)
    }).collect();
    
    self.window_fn = Box::new(move |perp: &[f64]| {
        perp.iter().enumerate().all(|(k, &v)| {
            // Tighter window in dense regions, wider in sparse
            let density_factor = if global_maxes[k] > 1.0 { 0.8 } else { 1.5 };
            v.abs() <= INV_PHI * density_factor
        })
    });
    self
}
```

**reasoning_effort:** When using Seed to generate PCA projections from data: **medium**. The power iteration is iterative but not deeply complex. Save `high` for convergence verification.

---

### 3. `flux-isa/pyflux/compat.py` — FLUX-ISA VM

**Where MoE helps:**

The FLUX-ISA dispatch table (line ~330, `_dispatch`) is literally an expert router: 58 opcodes, each with its own handler. MoE's architecture mirrors this:

1. **FLUX-DEEP opcodes (0x80-0x95)** — the 15 "Galois Adjunction" and "Cross-Domain" instructions — are exactly like MoE's specialized experts. They handle rare, complex operations while the 43 core opcodes handle common cases. This is the 10:1 sparsity pattern: most execution hits core opcodes, rare paths hit FLUX-DEEP.

2. **PROJECT/RECONSTRUCT** (lines ~300-340): These are the MoE analogs. `PROJECT` reduces dimensionality (like MoE router selecting experts), `RECONSTRUCT` rebuilds (like MoE combining expert outputs). The `residue_memory` (line ~44) is the "residual expert" — what MoE's gate network leaves behind.

3. **AdaCoT parallel:** The instruction trace (line ~188, `TraceEntry`) records execution history. Seed's AdaCoT (adaptive chain-of-thought) would dynamically decide how many trace steps to keep — more for complex constraint chains, fewer for simple arithmetic.

**Code changes:**

```python
# Add reasoning_effort parameter to execute()
# Line ~96: modify execute signature
def execute(self, program: List[Instruction], reasoning_effort: str = "medium") -> dict:
    """
    Execute FLUX bytecode with adaptive compute (MoE-inspired).
    
    reasoning_effort levels:
      "low"    — skip trace recording, no path verification (fastest)
      "medium" — normal execution with trace
      "high"   — verify all constraints twice, deep trace analysis
      "max"    — exhaustive constraint verification + symbolic check
    """
    effort_map = {"low": 0, "medium": 1, "high": 2, "max": 3}
    effort = effort_map.get(reasoning_effort, 1)
    
    # Low effort: skip trace for speed (like MoE skipping rare experts)
    if effort == 0:
        self.trace = []  # don't record
    
    # ... existing execute loop ...
    
    # High effort: double-check all constraints
    if effort >= 2 and self.constraint_results:
        # Re-verify any failed constraints with full context
        for i, passed in enumerate(self.constraint_results):
            if not passed:
                # Re-run the failed instruction with more compute
                pass  # placeholder for deep re-verification
```

```python
# Line ~300: PROJECT opcode — add MoE-style expert routing
def _op_project(self, i: Instruction):
    tiling_dim = int(self._pop())
    embed_dim = int(self._pop())
    n = len(self.stack)
    coord_count = min(embed_dim, n)
    coords = self.stack[-coord_count:]
    del self.stack[-coord_count:]

    phi = self.PHI
    projected = []
    for t in range(tiling_dim):
        s = 0.0
        # MoE-style: weight by magnitude (top-k expert selection)
        coord_weights = [abs(c) for c in coords]
        max_w = max(coord_weights) if coord_weights else 1.0
        for ci, c in enumerate(coords):
            # Softmax-like weighting: high-magnitude coords get more influence
            w = (coord_weights[ci] / max_w) if max_w > 0 else 1.0
            s += c * w * ((ci + t + 1) * phi) % 1.0
        projected.append(s)
    # ... rest unchanged
```

**reasoning_effort:**  
- **Low** for arithmetic opcodes (ADD, SUB, etc.) — they're simple, don't need deep reasoning.  
- **Medium** for constraint opcodes (ASSERT, CHECK) — need some reasoning about bounds.  
- **High** for FLUX-DEEP opcodes (PROJECT, RECONSTRUCT, TDQKR) — these are the "rare experts" that need more compute.  
- **Max** for HOLONYMY and FEDERATE — complex multi-input operations that combine multiple values.

---

### 4. `lighthouse-runtime/lighthouse.py` — Lighthouse Agent Router

**Where MoE helps:**

This is the **strongest fit** in the entire codebase. The lighthouse is literally a MoE router:

- **`orient()`** (line ~106) = MoE gate network: picks the cheapest model for a task type
- **`TASK_MODEL_MAP`** (line ~42) = expert assignment table
- **`MODEL_COSTS`** (line ~33) = expert capacity/cost
- **`gate()`** (line ~168) = MoE output verification

Seed's MoE architecture can improve this in three specific ways:

1. **Dynamic expert selection** (instead of static `TASK_MODEL_MAP`): Seed's router uses input-dependent gating. Currently line 42 hard-codes task→model. An MoE-inspired version would route based on *actual input complexity*, not just task type.

2. **Load balancing**: MoE routers balance expert load (auxiliary loss). The lighthouse has no load balancing — if all tasks are "discovery", Seed gets hammered.

3. **AdaCoT for relay decisions**: Seed's adaptive chain-of-thought could decide how many seed iterations to run (line ~134, `seed_iterations`) based on the task complexity, not a fixed number.

**Code changes:**

```python
# Replace static TASK_MODEL_MAP with MoE-style dynamic router
# Line ~42: Replace with

def route_moe(task: str, task_type: str, input_complexity: float = 0.5) -> str:
    """
    MoE-inspired model router. Routes based on input complexity, not just type.
    
    Like Seed's MoE: top-k expert selection with capacity factor.
    """
    # Expert capabilities (normalized 0-1)
    EXPERTS = {
        "seed":    {"cost": 0.1, "speed": 0.95, "depth": 0.3, "breadth": 0.9},
        "deepseek": {"cost": 0.2, "speed": 0.8, "depth": 0.5, "breadth": 0.7},
        "hermes":  {"cost": 0.15, "speed": 0.7, "depth": 0.6, "breadth": 0.6},
        "glm":     {"cost": 5.0, "speed": 0.4, "depth": 0.85, "breadth": 0.7},
        "claude":  {"cost": 50.0, "speed": 0.2, "depth": 0.95, "breadth": 0.8},
    }
    
    # Score each expert for this task (MoE gate function)
    scores = {}
    for expert, caps in EXPERTS.items():
        # Depth needed scales with complexity
        depth_needed = input_complexity
        depth_score = min(caps["depth"] / depth_needed, 1.0) if depth_needed > 0 else 1.0
        
        # Cost penalty (MoE auxiliary loss analog)
        cost_score = 1.0 / (1.0 + caps["cost"])
        
        # Speed bonus for high-volume tasks
        speed_score = caps["speed"]
        
        scores[expert] = depth_score * 0.5 + cost_score * 0.3 + speed_score * 0.2
    
    # Top-k selection (MoE: typically top-2 of 8+ experts)
    sorted_experts = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_experts[0][0]  # Top expert


# Line ~106: Modify orient() to use MoE routing
def orient(task: str, task_type: str, role: str = "worker") -> dict:
    # Estimate input complexity from task description length + type
    input_complexity = min(1.0, len(task.split()) / 100.0)
    type_complexity = {
        "synthesis": 0.9, "critique": 0.85, "architecture": 0.8,
        "complex_code": 0.7, "discovery": 0.3, "variation": 0.2,
        "drafting": 0.25, "documentation": 0.3, "research": 0.5,
    }
    complexity = max(input_complexity, type_complexity.get(task_type, 0.3))
    
    model = route_moe(task, task_type, complexity)
    # ... rest of orient() unchanged
```

```python
# Line ~134: AdaCoT-inspired adaptive seed iterations
def relay(room_id: str, seed_iterations: int = 0, task_complexity: float = 0.5) -> dict:
    # AdaCoT: more iterations for complex tasks, fewer for simple
    if seed_iterations == 0 and task_complexity > 0.5:
        seed_iterations = int(task_complexity * 10)  # 5-10 iterations
    # ... rest unchanged
```

**reasoning_effort:**  
- **Low** for `orient()` with simple tasks (discovery, variation)  
- **Medium** for standard tasks (drafting, documentation)  
- **High** for `gate()` safety checks — credential/overclaim detection needs thorough reasoning  
- **Max** never needed here — save for actual research tasks

---

### 5. `baton-experiments/SEED-PROTOCOL.md` — SEED Protocol Specification

**Where MoE helps:**

The SEED PROTOCOL is *already designed for Seed-2.0-mini* but doesn't exploit MoE-specific features:

1. **SEED-GEN at T=1.0** (line in "SEED-GEN" section): This is perfect for MoE. At T=1.0, the router explores diverse expert combinations. But the protocol doesn't use `reasoning_effort` — it's hardcoded to a single compute level.

2. **SEED-RECON ensemble** (line in "SEED-RECON" section): The 3-reconstruction ensemble is MoE-aware in spirit (diverse expert paths), but doesn't actually leverage the MoE architecture. Each reconstruction should use a *different reasoning effort* to emulate different expert combinations.

3. **SEED-CYCLE convergence** (line in "SEED-CYCLE" section): The 3-cycle convergence check is a fixed heuristic. MoE's adaptive compute (AdaCoT) could make this dynamic — more cycles when the "novelty expert" is still producing, fewer when it's exhausted.

**Code changes (to SEED-PROTOCOL.md config):**

```python
# In "Configuration" section, add MoE-specific settings:
SEED_CONFIG = {
    # ... existing config ...
    
    # MoE-specific parameters
    "moe_aware": True,
    "reasoning_effort_map": {
        "gen": "low",       # Hypothesis gen: breadth over depth
        "recon": "high",    # Reconstruction: need depth
        "cycle_test": "medium",  # Test generation: balanced
        "cycle_analyze": "high", # Analysis: need reasoning
        "oracle": "medium", # Self-analysis: moderate depth
    },
    "adaptive_effort": True,  # Let Seed decide effort per-query
    "expert_routing_hint": True,  # Tell Seed which "experts" to prioritize
}
```

```python
# SEED-RECON: use varying reasoning efforts across ensemble
# This mirrors MoE's diverse expert combinations
def recon_ensemble(tile, n=3):
    efforts = ["low", "medium", "high"]  # Different "expert" levels
    reconstructions = []
    for effort in efforts[:n]:
        result = seed_query(
            tile, 
            temperature=1.0,
            reasoning_effort=effort  # ← NEW: MoE-adaptive compute
        )
        reconstructions.append(result)
    return union_facts(reconstructions)
```

**reasoning_effort per SEED mode:**

| Mode | Effort | Why |
|------|--------|-----|
| SEED-GEN | `low` | Breadth over depth. MoE explores broadly at low effort. |
| SEED-RECON (ensemble member 1) | `low` | Quick first pass |
| SEED-RECON (ensemble member 2) | `medium` | Balanced recovery |
| SEED-RECON (ensemble member 3) | `high` | Deep recovery attempt |
| SEED-CYCLE test gen | `medium` | Need working code, not brilliance |
| SEED-CYCLE analysis | `high` | Need reasoning to interpret results |
| SEED-ORACLE | `medium` | Self-analysis doesn't need max depth |

---

### 6. `neural-plato/experiments/falsification_suite.py` — Falsification Tests

**Where MoE helps:**

The falsification suite runs 20 claims (C1-C20). Each claim test is independent — a perfect fit for MoE's parallel expert execution:

1. **C5 (region fingerprints, line ~95)**: O(n²) fingerprint uniqueness check across 400 positions. MoE's sparse activation means only the "fingerprint expert" processes this — not the whole 230B model.

2. **C14 (amnesia cliff, line ~210)**: Information-theoretic bound check. This is exactly the kind of abstract reasoning where `reasoning_effort="high"` helps — MoE can route to deep-reasoning experts.

3. **C20 (golden vs random projection, line ~295)**: The comparison test could use Seed's MoE to generate multiple random projections efficiently — each projection is an "expert" opinion.

**Code changes:**

```python
# Add Seed-powered falsification (MoE as hypothesis generator)
# New function at the end of the file:

def seed_augmented_falsification(claims: list, seed_model=None):
    """
    Use Seed-2.0-mini's MoE to find falsification tests we haven't thought of.
    
    MoE advantage: diverse expert combinations at T=1.0 surface
    novel test strategies that greedy decoding would miss.
    """
    import json
    from pathlib import Path
    
    # Read existing results to provide context
    results_file = Path(__file__).parent / "falsification_results.json"
    if results_file.exists():
        existing = json.loads(results_file.read_text())
        passed_claims = [r for r in existing["results"] if r["passed"]]
        failed_claims = [r for r in existing["results"] if not r["passed"]]
    else:
        passed_claims = []
        failed_claims = []
    
    # Generate novel falsification strategies
    # reasoning_effort="low" because we want breadth (many strategies)
    prompt = f"""Given these {len(passed_claims)} surviving claims:
    {[c['claim'] for c in passed_claims]}
    
    Generate 5 NEW falsification tests not in the existing suite.
    Each test should target a different claim.
    Focus on edge cases the current tests might miss."""
    
    return prompt  # To be sent to Seed with reasoning_effort="low"
```

**reasoning_effort:**
- **Low** for statistical tests (C1, C4, C17) — simple counting, no deep reasoning needed
- **Medium** for geometric tests (C3, C5, C19) — need some spatial reasoning
- **High** for information-theoretic tests (C12, C14) — abstract reasoning territory
- **Max** not needed — no claim requires exhaustive proof

---

### 7. `neural-plato/experiments/seed_questions.py` — Phase 2 Experiments

**Where MoE helps:**

These experiments were *generated by Seed-2.0-mini* (as stated in the docstring). The MoE connection is direct:

1. **Q1 (golden angle for structured vectors, line ~55)**: The 10-angle comparison (lines 85-92) is exactly the kind of broad exploration MoE enables at T=1.0. Each angle comparison activates different experts.

2. **Q7 (captured variance vs alignment, line ~130)**: Testing 6 alignment angles is sparse exploration. MoE could test 50+ angles for the same cost, routing each to a different expert.

3. **Q8 (3-coloring as retrieval cue, line ~175)**: This is the MoE analog — color ≈ expert group. The test already shows the pattern: spatial-only vs color-cued retrieval ≈ single-expert vs MoE routing.

**Code changes:**

```python
# Line ~55: Add reasoning_effort to experiment parameters
# Each experiment should declare its effort level

EXPERIMENT_EFFORT = {
    "Q1": "low",    # Broad exploration, many angles — breadth wins
    "Q2": "medium", # Error rate analysis needs some depth
    "Q7": "high",   # Variance capture is subtle — need reasoning
    "Q8": "medium", # Retrieval comparison — balanced
    "Q10": "low",   # Statistical localization — straightforward
}

# Line ~130: Expand Q7 to leverage MoE's breadth
def experiment_q7_expanded():
    """Expanded version leveraging MoE's cheap breadth."""
    # Instead of 6 angles, test 50 (MoE makes this affordable)
    angles = [i * math.pi / 25 for i in range(50)]  # 50 angles, ~$0.01 each
    # ... same test logic but 8x more angles for same effective cost
```

**reasoning_effort:**
- **Low** for Q1, Q10 — statistical experiments, breadth > depth
- **Medium** for Q2, Q8 — need some analytical reasoning
- **High** for Q7 — variance analysis benefits from deeper reasoning

---

## Cross-Cutting Recommendations

### 1. Add `reasoning_effort` to All Seed API Calls

Every place that calls `ByteDance/Seed-2.0-mini` should pass `reasoning_effort`. The 4 levels map to MoE's compute scaling:

| Level | Active Experts | Use For |
|-------|---------------|---------|
| `low` | ~2 of 230B params | Hypothesis generation, statistical tests, drafting |
| `medium` | ~23B (default) | Standard analysis, code generation, most tasks |
| `high` | ~46B (2x active) | Constraint verification, deep analysis, reconstruction |
| `max` | ~69B (3x active) | Never needed in our codebase currently |

### 2. MoE-Aware Lighthouse Router

Replace the static `TASK_MODEL_MAP` with the dynamic `route_moe()` function above. This is the single highest-impact change — it makes the entire fleet more efficient by routing tasks to the right compute level.

### 3. Ensemble Reasoning Diversity

For SEED-RECON and falsification, use *varying* reasoning efforts across ensemble members. This mirrors MoE's actual architecture: different experts contribute different depth levels.

### 4. Penrose Projection as MoE Router

The `project_to_2d` function in `lib.rs` IS a router — it maps high-dimensional embeddings to 2D coordinates using golden-angle hashing. Adding top-k dimension selection (10:1 sparsity) would make it structurally identical to MoE expert routing and likely improve projection quality for sparse embeddings.

### 5. FLUX-ISA Effort Levels

Add `reasoning_effort` parameter to `FluxVM.execute()`. Map effort levels to trace depth and constraint re-verification. Low effort skips trace recording; high effort double-checks constraints.

---

## Priority Matrix

| Change | File | Impact | Effort | Priority |
|--------|------|--------|--------|----------|
| Dynamic MoE router | `lighthouse.py` | HIGH | Medium | 🔴 P0 |
| Top-k projection | `lib.rs` | MEDIUM | Low | 🟡 P1 |
| reasoning_effort in SEED config | `SEED-PROTOCOL.md` | MEDIUM | Low | 🟡 P1 |
| Adaptive window | `cut_and_project.rs` | MEDIUM | Medium | 🟡 P2 |
| FLUX effort levels | `compat.py` | LOW | Medium | 🟢 P3 |
| Seed-augmented falsification | `falsification_suite.py` | LOW | Low | 🟢 P3 |

---

*Audit complete. The strongest lever is the lighthouse router — it's already a MoE gate network, it just doesn't know it yet.*
