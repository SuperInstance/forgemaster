# STUDY 59: Does the Three-Tier Taxonomy Hold for Code Generation?

**Date:** 2026-05-15
**Priority:** P2
**Question:** Studies 50/56 found a three-tier taxonomy for mathematical computation. Does it apply to code generation?

## Experimental Design

### 10 Code Tasks × 5 Models × 1 Condition = 50 Trials

**Tasks by difficulty:**

| Difficulty | Tasks | Skills Tested |
|:----------:|-------|---------------|
| Easy (3) | reverse_list, find_max, count_chars | Basic iteration, dict ops |
| Medium (4) | binary_search, fibonacci_memo, merge_sorted, validate_bst | Recursion, trees, memoization |
| Hard (3) | LRU cache, A* pathfinding, topological sort | Complex data structures, algorithms |

**Models spanning all three math tiers:**

| Model | Math Tier | Provider | Size |
|-------|:---------:|----------|------|
| Seed-2.0-mini | 1 | DeepInfra | ~? |
| gemma3:1b | 1 | Ollama | 1B |
| Hermes-70B | 2 | DeepInfra | 70B |
| Qwen3-235B | 2 | DeepInfra | 235B (22B MoE) |
| qwen3:0.6b | 3 | Ollama | 0.6B |

**Condition:** Bare prompt only (no scaffolding). Code extracted and tested against assertion suites.

**Scoring:**
- **Pass** — All assertions pass
- **Partial** — Function/class structure present but runtime errors
- **Fail** — No usable code or assertion failure

## Results

### Per-Model Summary

| Model | Math Tier | Easy | Medium | Hard | Total | Code Tier |
|-------|:---------:|:----:|:------:|:----:|:-----:|:---------:|
| Seed-2.0-mini | 1 | 3/3 (100%) | 4/4 (100%) | 3/3 (100%) | **10/10 (100%)** | **1** |
| gemma3:1b | 1 | 3/3 (100%) | 4/4 (100%) | 2/3 (67%) | **9/10 (90%)** | **1** |
| Hermes-70B | 2 | 3/3 (100%) | 4/4 (100%) | 2/3 (67%) | **9/10 (90%)** | **1-2** |
| Qwen3-235B | 2 | 3/3 (100%) | 4/4 (100%) | 2/3 (67%) | **9/10 (90%)** | **1-2** |
| qwen3:0.6b | 3 | 2/3 (67%) | 2/4 (50%) | 0/3 (0%) | **4/10 (40%)** | **3** |

### Tier Group Analysis

| Math Tier | Pass Rate | Partial | Fail | Code Pass Rate |
|:---------:|:---------:|:-------:|:----:|:--------------:|
| **Tier 1** | 19/20 (95%) | 1 | 0 | ~95% |
| **Tier 2** | 18/20 (90%) | 1 | 1 | ~90% |
| **Tier 3** | 4/10 (40%) | 1 | 5 | ~40% |

### Failure Details

| Model | Task | Difficulty | Failure Mode |
|-------|------|:----------:|-------------|
| Hermes-70B | topological_sort | hard | Assertion failure (ordering incorrect) |
| Qwen3-235B | lru_cache | hard | Partial — variable naming error (Chinese characters in code) |
| gemma3:1b | a_star | hard | Partial — type error in path reconstruction |
| qwen3:0.6b | reverse_list | easy | No code generated |
| qwen3:0.6b | merge_sorted | medium | Partial — IndexError |
| qwen3:0.6b | validate_bst | medium | No code generated |
| qwen3:0.6b | lru_cache | hard | No code generated |
| qwen3:0.6b | a_star | hard | No code generated |
| qwen3:0.6b | topological_sort | hard | No code generated |

## Hypothesis Evaluation

| Hypothesis | Prediction | Result | Verdict |
|------------|------------|--------|:--------:|
| **H1: Code tier ≈ math tier** | Tier 1→1, Tier 2→2, Tier 3→3 | Tier 1 = 95%, Tier 2 = 90%, Tier 3 = 40% | ⚠️ **PARTIAL** |
| **H2: Code tier ≠ math tier** | Code training differs fundamentally | Tier 1 and 2 nearly equal; large gap to Tier 3 | ⚠️ **PARTIAL** |
| **H3: No tiers in code** | All models capable at code generation | 40% vs 95% gap between Tier 3 and Tier 1 | ❌ **REJECTED** |

## Key Findings

### 1. The Tier Taxonomy PARTIALLY Transfers to Code

The three-tier structure exists in code but is **compressed**:
- **Math:** Tier 1 (100%) > Tier 2 (25-50%) > Tier 3 (0%) — sharp separations
- **Code:** Tier 1 (95%) ≈ Tier 2 (90%) >> Tier 3 (40%) — Tiers 1-2 merged

The gap between Tier 1 and Tier 2 in math is 50-100 percentage points. In code, it's only **5 percentage points**. The meaningful boundary in code is between Tier 2 and Tier 3 (50pp gap), not between Tier 1 and Tier 2.

### 2. Code is Easier Than Math for Most Models

Study 50 found that even 70B+ models struggled with basic math notation. Here, 90% of Tier 2 responses pass code tests. The difference: **code prompts fully specify the algorithm**. There's no hidden computation, no notation decoding. The model needs to emit syntactically valid code, not compute correct answers internally.

### 3. The Tier 3 Failure Mode is Different

In math, Tier 3 models compute wrong answers. In code, Tier 3 models **don't generate code at all** — 4 of 6 qwen3:0.6b failures were "no code generated" (empty or garbled output). This is a generation capability failure, not a reasoning failure.

### 4. Hard Tasks Create Separation

| Difficulty | Tier 1 | Tier 2 | Tier 3 |
|:----------:|:------:|:------:|:------:|
| Easy | 100% | 100% | 67% |
| Medium | 100% | 100% | 50% |
| Hard | 83% | 67% | 0% |

Easy and medium tasks show no Tier 1/2 separation. Hard tasks create a gradient: Tier 1 (83%) > Tier 2 (67%) >> Tier 3 (0%). Harder code problems may reveal the full three-tier structure that math exposes at all difficulty levels.

### 5. The gemma3:1b Anomaly Persists

gemma3:1b (1B params, Math Tier 1) achieves 90% on code — matching Hermes-70B (70B params, Math Tier 2). This confirms Study 50's finding: **gemma3:1b's capabilities are training-dependent, not scale-dependent**. Its code performance is indistinguishable from models 70× its size.

### 6. A* is the Hardest Task Across All Models

| Model | A* Score |
|-------|:--------:|
| Seed-2.0-mini | ✅ pass |
| Hermes-70B | ✅ pass |
| Qwen3-235B | ✅ pass |
| gemma3:1b | 🔶 partial |
| qwen3:0.6b | ❌ fail |

A* requires combining a priority queue, heuristic function, path reconstruction, and grid traversal — the most complex single-function task. Only Seed-2.0-mini passes all hard tasks cleanly.

## Implications

1. **Tier taxonomy is domain-dependent.** The three-tier structure is sharp in math (where hidden computation matters) and compressed in code (where the prompt specifies the algorithm). Future tier assessments should use domain-appropriate benchmarks.

2. **The "floor" is higher in code.** Even Tier 3 models manage 40% (vs 0% in math). Code generation has a lower barrier to entry because the prompt is the specification.

3. **Task difficulty scales tier separation.** Easy code tasks show no tiers; hard tasks begin to reveal them. To properly map code tiers, you need tasks harder than LRU cache and A*.

4. **For practical model selection:** Any Tier 1-2 model handles standard coding tasks at 90%+. The meaningful selection criterion is performance on hard/novel tasks, not routine code generation.

---

*Data: `experiments/study59_results.json` (50 trials)*
*Related: Study 50 (tier boundaries), Study 56 (cross-domain transfer)*
