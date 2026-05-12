# Fleet-Spread Audit Report

**Repository:** `SuperInstance/fleet-spread`
**Auditor:** Forgemaster ⚒️
**Date:** 2026-05-07

---

## Executive Summary

`fleet-spread` is a well-architected, mathematically-grounded Rust library for fleet graph analysis. It has a clear v1→v2 migration story, real math (Laman rigidity, Betti numbers, ZHC holonomy, Pythagorean48 encoding), and 147 tests. The code is structurally sound but has some cosmetic issues. **Grade: B+** (strong architecture, minor implementation roughness).

---

## Module-by-Module Analysis

### 1. `src/graph.rs` — Fleet Graph Data Structures

**Grade: A-**

**What it does:** Defines the core data model: `FleetGraph`, `Vertex`, `Edge`, `TrustValue`. Provides graph operations (components, Betti numbers, degree calculation).

**Math correctness:** Betti number calculation `β₁ = E - V + C` is correct for connected graphs. Laman count `E = 2V - 3` is correct for 2D rigidity. Subgraph enumeration for Laman checking is correct in principle (checks all subgraphs for E ≥ 2V - 3 condition).

**Structure:** Clean separation of concerns. `TrustValue` has `value`, `confidence`, and `history` — the history vector enables the empirical specialist's drift detection. Example: `TrustValue::new(0.9, 0.8)` creates a trust of 0.9 with confidence 0.8, with an empty history that can grow over time.

**Issues:**
- No adjacency list — component detection iterates edges each time
- No cycle basis extraction at graph level (topological specialist does it inline)

---

### 2. `src/library_gate.rs` — Specialist Selection

**Grade: A**

**What it does:** Implements the v2 architecture insight: don't run all 5 specialists, select the one that matches. Uses a priority-ordered gate table against `FleetGraphState` metrics.

**Math correctness:** The gate table priority is logically sound:
1. V < 3 → Systems (insufficient data)
2. ZHC degraded → Geometric
3. Trust noisy → Algebraic
4. β₁ rising → Topological
5. Agent count changed → Empirical
6. Stable (β₁=0, stable≥10s) → None

**Is it implemented or just designed?** **Implemented.** Full Rust code with `select()` method, `LibraryGate` struct, priority ordering, `FleetGraphState` factories for testing. 147 tests verify selection logic.

**Key strength:** The skip decision (returning `Option::None`) is a deliberate design choice — the absence of signal *is* the signal. This is architecturally elegant.

**Issues:**
- `FleetGraphState::from_graph()` sets `zhc_loop_residual: 0.0` as default — this means the ZHC check uses defaults rather than computed values at selection time

---

### 3. `src/captain.rs` — Deliberation Engine (781 lines)

**Grade: B**

**What it does:** The captain reads specialist reports, produces adjudicated findings, checks hard constraints (safety/P0 only), and generates a deliberation report with probability-weighted reasoning.

**Does it produce real synthesis?** **Partially.** The captain's `DeliberationEngine` does:
- Expert inquiry (wide scan of all findings)
- Probability distribution with entropy calculation
- Hard constraint checking (safety margin, spares, trust threshold, emergence ceiling, ZHC tolerance, time window)
- P0 = safety, never negotiable

However, in v2 the captain only sees ONE specialist's output. The "deliberation" is more of a quality gate — checking if the single report passes hard constraints — than true synthesis. The v1-style synthesis (cross-specialist tensions, robust findings) is deprecated and its code remains vestigial.

**Structure:** 781 lines is a lot. The `AdjudicatedFinding` and `ProbabilityDistribution` structs are solid. The `ProbablityDistribution` misspelling (missing `i` in "Probability") is in the codebase — cosmetic but notable.

**Issues:**
- The hard constraints are fleet-agnostic (no parametrization from agent count or graph size)
- v2 reduced the captain's role to a quality check rather than true deliberation — the architecture hasn't fully caught up with the v2 design

---

### 4. `src/specialists/mod.rs` — Specialist Trait Definitions

**Grade: A**

**What it does:** Defines the `Specialist` trait, `SpecialistReport`, `Finding`, and `FindingType` enums (Confirmed, Inferred, Question). Provides `add_finding()`, `add_unanswered()`, `set_raw_data()` builder pattern.

**Structure:** Clean trait with one method `analyze(&self, graph: &FleetGraph) -> SpecialistReport`. The `SpecialistReport` has `specialist_id`, `findings`, `unanswered`, `confidence`, `raw_data` fields. `information_content()` method gives a heuristic for synthesis gain calculation.

**Math correctness:** No math here — pure type definitions. Clean.

---

### 5. `src/specialists/systems.rs` — S0 Systems Specialist

**Grade: A-**

**What it does:** Laman rigidity analysis. Checks `E = 2V - 3` for 2D rigidity. Enumerates proper subgraphs to verify the Laman condition holds for all subgraphs (no over-constrained substructures).

**Math correctness:** This is genuine Laman's theorem. The `E = 2V - 3` check on the whole graph is necessary but not sufficient — the subgraph enumeration catches over-constrained subgraphs (e.g., K3,3 or other minimally rigid subgraphs with internal constraints). This is correct rigidity theory.

**Structure:** Clean implementation. Subgraph enumeration uses bitmask iteration (`0..(1 << V)`).

**Issues:**
- Subgraph enumeration is O(2^V) — not practical for V > 20. This is an acknowledged limitation (Laman checking is NP-hard in general).
- No caching: every call recomputes subgraphs

---

### 6. `src/specialists/topological.rs` — S1 Topological Specialist

**Grade: A-**

**What it does:** Analyzes graph topology using Betti numbers (β₁ = E - V + C) and cycle basis. Component analysis via DFS. Computes component-level stats (size, edges, rigidity possibility).

**Math correctness:** Betti number calculation is correct for H¹ cohomology. Cycle basis extraction finds independent cycles. Component analysis correctly identifies disconnected components.

**Structure:** Well-modularized. Has `CycleBasis` struct, `ComponentStats` struct. Configurable cycle threshold.

**Issues:**
- Cycle basis extraction could be more efficient (uses path-based approach rather than spanning tree + fundamental cycles)
- No incremental computation — full DFS on every call

---

### 7. `src/specialists/geometric.rs` — S2 Geometric Specialist

**Grade: B+**

**What it does:** Bridges fleet-spread graph structure with `fleet-coordinate`'s ZHC consensus for rigorous holonomy analysis. Has a `with_threshold()` builder method. The `analyze_with_zhc()` method optionally accepts a `FleetGraphState`.

**Math correctness:** The ZHC (Zariski Homeomorphic Consensus) integration is real — it connects to fleet-coordinate's `ZhcConsensus` for actual 3D holonomy matrices. This replaced the old trust-as-rotation approximation (which was incorrect). However, the backwards compatibility fallback still uses the approximation.

**Structure:** Good backwards compatibility design — optional ZHC integration means the geometric specialist works without fleet-coordinate if needed. The `with_threshold` builder is clean.

**Issues:**
- Backwards compatibility fallback is a crutch — if fleet-coordinate is in Cargo.toml, it should always be used
- Trust-holonomy approximation is acknowledged as incorrect in the comments but still present

---

### 8. `src/specialists/algebraic.rs` — S3 Algebraic Specialist

**Grade: B+**

**What it does:** Pythagorean48 encoding analysis. Measures encoding stability, drift across hops, and consistency of trust vector representation.

**Math correctness:** Pythagorean48 is a real encoding scheme (48-dimensional Pythagorean representation for trust vectors). The encoding check verifies `Σ vᵢ² = 1`. Drift measurement across hops is geometrically sound.

**Structure:** ~305 lines. Clean modularization with `EncodingStats`, `DriftMeasurement` structs. Trigonometric representation for trust vectors.

**Issues:**
- Pythagorean48 dimension choice (48) is not clearly motivated in code — why 48?
- The encoding check `Σ vᵢ² = 1` doesn't account for floating-point drift over multiple hops
- No adaptive thresholds based on hop count

---

### 9. `src/specialists/empirical.rs` — S5 Empirical Specialist

**Grade: B**

**What it does:** Analyzes actual trust values from PLATO room. Anomaly detection (2 standard deviations), drift detection (20% change), trust distribution statistics (mean, std, min, max, skewness). Pattern violation checking (perfect trust, zero trust, high trust + low confidence).

**Structure:** Good practical analysis. The `TrustDistribution`, `AnomalyReport`, `DriftReport`, `PatternViolation` structs are well-designed. The builder pattern `with_plato_url()` is clean.

**Math correctness:** Standard deviation, z-score, skewness calculations are correct. The `mean1 vs mean2` drift detection (split-half) is a reasonable heuristic. 2σ anomaly threshold is standard.

**Issues:**
- **PLATO room integration is a placeholder.** `query_plato_room()` returns `Err("PLATO room query requires HTTP client")`. This means the empirical specialist can't actually access historical data in the current build.
- Without PLATO data, the specialist uses only the graph's embedded `history` vectors — which are empty by default
- The sync context limitation means the specialist admits "PLATO room query not implemented in sync context"
- **Critical:** The specialist cannot actually detect trends or compare against historical baselines without PLATO integration
- Skewness calculation uses population formula (divide by n) rather than sample (divide by n-1) — minor but notable

---

### 10. `src/synthesis.rs` — Synthesis Layer

**Grade: B**

**What it does:** v1 MoE-style synthesis (all 5 specialists) is deprecated since v0.2.0. v2 uses `SpecialistValueReport` from `quality.rs` for single-specialist assessment. The old code (`SynthesisReport`, `RobustFinding`, `Tension`, `BlindSpots`) remains but is marked deprecated.

**Structure:** The v1 synthesis is thorough — `find_robust_findings()` groups claims by semantic similarity, `find_tensions()` looks for contradictory patterns, `collect_blind_spots()` dedupes unanswered questions. The v2 `assess_single_specialist()` is a thin wrapper.

**Issues:**
- The old v1 code is deprecated but still functional and tested — should be cleaned up
- `normalize_claim()` is crude (splits on non-alphanumeric, removes stop words) — works for surface-level matching only
- `are_contradictory()` uses a lookup table of 7 opposite pairs — misses most real contradictions

---

### 11. `src/quality.rs` — Quality Metrics

**Grade: B+**

**What it does:** Defines `SingleSpecialistQuality` and `SpecialistValueReport`. `QualityAssessment` enum: `Excellent`, `Good`, `Fair`, `Poor`, `Insufficient`.

**Structure:** Clean quality gate for v2. `SpecialistValueReport::from_specialist()` assesses if a single specialist's output is valuable.

---

### 12. `src/constants.rs` — AgentConstants

**Grade: A-**

**What it does:** Three presets (`default_fleet`, `conservative`, `aggressive`) for bilateral constant-matching. `matches_task()` method checks compatibility with `TaskRequirements`. Fire drill detection (urgency ≥ 0.9).

**Structure:** Clean, well-commented. The `is_valid()` check ensures sane ranges.

---

### 13. `src/graph_state.rs` — FleetGraphState

**Grade: A-**

**What it does:** Lightweight snapshot of fleet topology for library gate selection. Contains V, E, β₁, ZHC loop residual, trust vector entropy, agent count, last_change_s, is_connected. Factory methods for common states.

**Structure:** `from_graph()` creates from a `FleetGraph`. Factory methods (`stable_rigid()`, `rising_beta()`, `degraded_zhc()`, etc.) are excellent for testing.

---

### 14. `src/task.rs` — TaskRequirements

**Grade: A-**

**What it does:** Task requirements for bilateral constant-matching. Three presets (`routine`, `urgent`, `critical`). Fire drill detection.

---

### 15. README.md

**Grade: A**

**What it does:** Excellent README. Documents v2 architecture vision, gate selection table, v1 vs v2 comparison, specialist dimensions, deadband protocol, P0/P1/P2 priorities, synthesis gain interpretation.

**Note:** The README diagram and text describe 4 specialists (missing S5 Empirical) — the gate table mentions 5 but the architecture diagram shows only 4. Minor doc inconsistency.

---

## Cross-Cutting Questions

### Is the library gate selection actually implemented or just designed?

**Implemented.** Full Rust code in `src/library_gate.rs` with:
- Priority-ordered gate table
- `select()` returning `Option<Box<dyn Specialist>>`
- `select_and_run()` returning `(String, SpecialistReport)`
- Test factories for all gate conditions
- 147 tests verifying selection logic

The `FleetGraphState` is the input; the gate returns exactly one specialist or `None`. This is production-ready, not a design sketch.

### Does the captain deliberation produce real synthesis?

**Partially in v2, fully in v1.**

In v2, the captain acts as a quality gate on a single specialist's output — it checks hard constraints (P0 safety, emergency ceiling, ZHC tolerance) but doesn't synthesize multiple perspectives. The v1 code (`SynthesisEngine`) does full synthesis (cross-specialist agreement, tension detection, blind spot collection) but is deprecated.

**The v2 captain is a quality checker, not a synthesis engine.** The README describes it as a deliberator, but the implementation is closer to a constraint validator.

### Are the 5 specialists genuinely different or boilerplate variations?

**Genuinely different.** Each analyzes a different mathematical dimension:

| Specialist | Math | Unique Contribution |
|------------|------|-------------------|
| **S0: Systems** | Graph rigidity (Laman) | Is the graph structurally rigid? |
| **S1: Topological** | Betti numbers (H¹) | Are there emergent cycles? |
| **S2: Geometric** | ZHC holonomy | Are loops closing correctly? |
| **S3: Algebraic** | Pythagorean48 encoding | Is the trust encoding stable? |
| **S5: Empirical** | Statistics (σ, skewness) | Are trust values anomalous? |

These are not parameter variations of the same algorithm — they target fundamentally different fleet phenomena. The only overlap is S0 and S1 both analyze graph structure, but at different levels (rigidity vs. topology).

### What's the connection to holonomy-consensus and constraint-theory?

1. **holonomy-consensus** provides the ZHC closure check used by the Geometric specialist (S2). When ZHC loop degrades (high residual), the geometric specialist activates and reports holonomy anomalies. The connection is the `analyze_with_zhc()` method which optionally takes a `FleetGraphState` with ZHC data.

2. **constraint-theory-ecosystem** is the mathematical foundation. fleet-spread implements:
   - **Laman's theorem** (Systems specialist): `E = 2V - 3` rigidity condition
   - **H¹ cohomology** (Topological specialist): `β₁ = E - V + C` Betti number
   - **Pythagorean encoding** (Algebraic specialist): trust as 48-dimensional unit vectors
   - **ZHC closure** (Geometric specialist): differential geometry for trust loops

3. **fleet-coordinate** is the runtime neighbor. fleet-spread uses fleet-coordinate's `ZhcConsensus` struct for the geometric specialist. fleet-coordinate depends on fleet-spread's graph analysis for rigidity certification.

## Key Issues

### Structural
1. **S5 Empirical has no PLATO integration** — `query_plato_room()` returns an error. Without it, the specialist uses only graph-internal history vectors which are empty by default. The anomaly and drift detection are effectively non-functional for new graphs.
2. **V2 captain is underpowered** — reduced to a quality check rather than true deliberation. The v1 synthesis code is deprecated but the v2 replacement doesn't match what the README describes.
3. **Systems specialist subgraph enumeration is O(2^V)** — fine for small graphs, breaks at V > 20 without a warning.
4. **Dead code** — `SynthesisReport`, `RobustFinding`, `Tension`, `BlindSpots` are deprecated but functional. Should be either removed or clearly marked as archived.

### Cosmetic
1. **Typo:** `ProbablityDistribution` (missing 'i')
2. **README diagram shows 4 specialists** (missing S5 Empirical)
3. **README arrow flow** uses `S1-S4` while code uses `S0-S3` (zero-indexed)

### Strengths
1. **Real math** — Laman rigidity, Betti numbers, ZHC holonomy, Pythagorean48. This isn't boilerplate ML; it's constraint theory.
2. **Clean v2 architecture** — library gate is a genuinely good design pattern
3. **147 tests** — good coverage across selection logic, specialist analysis, synthesis
4. **Test factories** — `FleetGraphState` factory methods make testing the gate table trivial
5. **Backwards compatibility** — geometric specialist works without fleet-coordinate via fallback
6. **Fire drill pattern** — `urgency >= 0.9` matches all agents is a good escape hatch

## Overall Grade: B+

A well-architected Rust library with real mathematical foundations. The v2 library gate architecture is elegant and production-ready. The main weaknesses are the non-functional PLATO integration (S5), the underpowered v2 captain, and the deprecated v1 synthesis code that should be cleaned up.

**Score:** 85/100 — Would ship, but wouldn't put on a critical path without addressing the PLATO integration and subgraph enumeration scaling.
