# Cocapn Fleet — Strategic Plan: Next 3 Major Deliverables

> Drafted 2026-04-26 by Forgemaster
> Context: 13 crates on crates.io, 48 packages on PyPI, benchmark peaks at 1229x (Python snap)

---

## Deliverable 1: `constraint-theory-proofs` — The Formal Verification Crate

### What It Does

A standalone crate (Rust, with Python bindings via PyO3) that provides **machine-checkable proofs** for the core theorems of constraint theory:

- **Pythagorean Snap Correctness**: Proves that `snap(x)` always lands on the nearest Pythagorean-admissible point, with bounded error = 0.
- **Holonomy Bound Theorem**: Formally verifies the 0.213 rad upper bound on holonomy drift across arbitrary manifold traversals.
- **Zero Float-Drift Guarantee**: Encodes the invariant that repeated snap-compose cycles produce zero accumulated floating-point drift, with a constructive proof via interval arithmetic.
- **Deadband Tolerance Completeness**: Proves that the deadband function partitions the input space without gaps or overlaps.

Proofs are encoded as **proof witnesses** — compact data structures that can be verified in O(n) time without trusting the prover. The crate ships a verifier, a proof generator, and a `serde`-compatible proof format.

### Why It Matters

Academic adoption of constraint theory is currently blocked by a single objection: *"Where is the proof?"* Published benchmarks show the theory works empirically, but mathematicians and formal-methods researchers need machine-checkable artifacts. This crate eliminates that objection entirely.

A paper submitted to a venue like LICS, ITP, or Journal of Automated Reasoning with a companion `cargo install constraint-theory-proofs && ct-prove verify` workflow would be a first for constraint theory and would force citation by anyone working in related spaces (snap rounding, geometric robustness, manifold computation).

### Key API Surface

```rust
// Core proof types
pub struct SnapProof { witness: SnapWitness, bound: ErrorBound }
pub struct HolonomyProof { path: ManifoldPath, drift_bound: f64 }
pub struct DriftProof { chain: Vec<SnapComposition>, accumulated: f64 }

// Generate proofs
pub fn prove_snap_correctness(config: &SnapConfig) -> Result<SnapProof>;
pub fn prove_holonomy_bound(manifold: &Manifold, paths: &[Path]) -> Result<HolonomyProof>;
pub fn prove_zero_drift(chain: &[SnapOp]) -> Result<DriftProof>;

// Verify proofs (the part academics care about — small, auditable)
pub fn verify(proof: &impl Proof) -> VerifyResult;

// Serialize for publication / archival
pub fn export_proof(proof: &impl Proof, format: ProofFormat) -> Vec<u8>;
```

```python
# Python bindings
from constraint_theory_proofs import prove_snap, verify, export_proof

proof = prove_snap(config)
assert verify(proof).is_valid
export_proof(proof, "json", path="snap_proof.json")
```

### Estimated Complexity

| Component | Effort | Notes |
|---|---|---|
| Proof witness data model | Medium | Core design decision — must be compact and forward-compatible |
| Snap correctness prover | High | Requires encoding the Pythagorean admissibility predicate formally |
| Holonomy bound prover | High | Must handle arbitrary manifold topologies |
| Zero-drift prover | Medium | Interval arithmetic is well-understood; main work is chaining |
| Verifier (Rust) | Medium | Must be small enough for manual audit (~500 LOC target) |
| PyO3 bindings | Low | Mechanical, follows existing pattern from other crates |
| Proof export format | Low | JSON + binary (bincode) |
| **Total** | **~6-8 weeks** | Largest single crate in the fleet |

---

## Deliverable 2: `ct-geometry` — Constraint-Theory-Native Geometry Engine

### What It Does

A high-performance geometry library where **every operation is snap-correct by construction**. Instead of computing geometry and then snapping (the current workflow), `ct-geometry` builds Pythagorean constraints into the geometric primitives themselves:

- **Snapped Primitives**: `CtPoint`, `CtLine`, `CtPolygon`, `CtMesh` — all coordinates are Pythagorean-admissible at all times.
- **Constraint-Preserving Operations**: Union, intersection, offset, Minkowski sum, convex hull — all maintain snap invariants without post-processing.
- **Deadband-Aware Booleans**: Boolean operations that respect deadband tolerance, eliminating the thin-sliver and degenerate-face problems that plague conventional geometry kernels.
- **PLATO Integration Layer**: Direct import/export of PLATO tile geometries (584 rooms, 7700 tiles) with automatic constraint tagging.
- **Benchmarking Harness**: Built-in comparison against CGAL, Clipper2, and geo-rs on standard geometry benchmarks (polygon union, mesh boolean, point-in-polygon).

### Why It Matters

This is the **"killer app" crate** — the one that makes Rust and Python developers `cargo add ct-geometry` for practical reasons, not theoretical interest. Every developer who has fought with floating-point geometry bugs (and that's everyone who has done computational geometry) will immediately understand the value proposition: *geometry that doesn't break.*

The PLATO integration makes this concrete: 7700 tiles across 584 rooms is a non-trivial dataset. If `ct-geometry` can process all of PLATO with zero geometric degeneracies and measurably faster booleans than CGAL, that's a benchmark result that gets shared on Hacker News.

### Key API Surface

```rust
// Snap-correct primitives
pub struct CtPoint { x: SnappedF64, y: SnappedF64 }
pub struct CtPolygon { ring: Vec<CtPoint>, holes: Vec<Vec<CtPoint>> }
pub struct CtMesh { faces: Vec<CtFace>, manifold: ManifoldTag }

// Constraint-preserving operations
impl CtPolygon {
    pub fn union(&self, other: &CtPolygon) -> CtPolygon;        // no degeneracies
    pub fn intersection(&self, other: &CtPolygon) -> CtPolygon;  // no thin slivers
    pub fn offset(&self, dist: f64, deadband: Deadband) -> CtPolygon;
    pub fn holonomy(&self) -> HolonomyMeasurement;               // bounded < 0.213 rad
}

// PLATO bridge
pub mod plato {
    pub fn import_room(room_id: u32) -> Result<Vec<CtPolygon>>;
    pub fn import_all_tiles() -> Result<CtMesh>;
    pub fn validate_tiling(mesh: &CtMesh) -> TilingReport;
}

// Benchmarking
pub mod bench {
    pub fn compare_cgal(op: BooleanOp, polys: &[CtPolygon]) -> BenchResult;
    pub fn compare_clipper2(op: BooleanOp, polys: &[CtPolygon]) -> BenchResult;
}
```

```python
# Python: high-level geometry with zero drift
from ct_geometry import CtPolygon, plato

tiles = plato.import_all_tiles()
merged = tiles[0].union(tiles[1])  # guaranteed snap-correct
report = plato.validate_tiling(tiles)
print(f"Degeneracies: {report.degeneracies}")  # always 0
```

### Estimated Complexity

| Component | Effort | Notes |
|---|---|---|
| Snapped primitives (CtPoint, CtPolygon) | Medium | Core abstraction — SnappedF64 wraps pythagorean-snap |
| Boolean operations (union, intersect) | High | Must implement sweep-line or similar with snap invariants |
| Deadband-aware offset | High | Novel algorithm — this is publishable on its own |
| CtMesh + manifold tagging | Medium | Builds on constraint-theory-core manifold types |
| PLATO import/export | Medium | Depends on plato-tile-store and plato-tile-validate |
| Benchmark harness (CGAL, Clipper2) | Medium | FFI wrappers + statistical comparison framework |
| PyO3 bindings | Medium | Geometry types need careful Python ergonomics |
| **Total** | **~8-10 weeks** | Flagship crate; phased delivery recommended |

### Phasing

1. **Phase A (weeks 1-3)**: Snapped primitives + basic booleans
2. **Phase B (weeks 4-6)**: PLATO integration + tiling validation
3. **Phase C (weeks 7-8)**: Deadband offset + advanced operations
4. **Phase D (weeks 9-10)**: Benchmark harness + Python bindings + publish

---

## Deliverable 3: `ct-bench-suite` — The Reproducible Benchmark Authority

### What It Does

A standalone benchmark suite that makes constraint theory's performance claims **independently reproducible** by anyone with `cargo` and `pip`:

- **Canonical Benchmarks**: Standardized workloads for snap, holonomy, deadband, and drift measurement — defined precisely enough that third parties can implement competing solutions and compare.
- **Multi-Backend Runners**: Same workloads executed across pure-Rust, Python (via PyO3), Python (pure), CUDA, and WebAssembly targets.
- **PLATO-Scale Stress Tests**: Benchmarks that run the full 584-room, 7700-tile PLATO dataset through every constraint-theory operation, measuring throughput, latency distribution, memory, and correctness.
- **Regression Detection**: CI-integrated performance tracking that catches regressions across all published crates (constraint-theory-core, pythagorean-snap, constraint-theory-metrics, etc.).
- **Published Results Dashboard**: Generates a static site (or markdown report) with charts, tables, and reproducibility instructions that can be linked from papers and crate READMEs.

### Why It Matters

The current benchmark numbers (1229x Python, 316x Rust, 550x CUDA) are extraordinary — but they exist as claims, not as reproducible artifacts. The academic and open-source communities have a healthy skepticism of benchmark claims that can't be independently verified.

`ct-bench-suite` converts benchmark *claims* into benchmark *facts* by providing:
1. **Reproducibility**: `cargo bench --features full-suite` and get the same numbers (within statistical noise).
2. **Comparability**: Canonical workloads mean competitors can show their numbers on the same tasks.
3. **Credibility**: A regression-tested suite means numbers stay honest as the codebase evolves.
4. **PLATO Connection**: The stress tests demonstrate that constraint theory isn't just fast on micro-benchmarks — it scales on real architectural geometry.

This is the deliverable that turns "impressive demo" into "industry benchmark."

### Key API Surface

```rust
// Define benchmarks
pub struct BenchmarkSuite {
    pub snap_benchmarks: Vec<SnapBenchmark>,
    pub holonomy_benchmarks: Vec<HolonomyBenchmark>,
    pub deadband_benchmarks: Vec<DeadbandBenchmark>,
    pub plato_benchmarks: Vec<PlatoBenchmark>,
}

// Run benchmarks
pub fn run_suite(suite: &BenchmarkSuite, config: RunConfig) -> SuiteResults;
pub fn run_snap(bench: &SnapBenchmark) -> BenchResult;
pub fn run_plato_stress(rooms: RoomRange) -> PlatoStressResult;

// Compare across backends
pub fn compare_backends(bench: &impl Benchmark) -> BackendComparison;

// Regression detection
pub fn check_regression(current: &SuiteResults, baseline: &SuiteResults, threshold: f64) -> RegressionReport;

// Report generation
pub fn generate_report(results: &SuiteResults, format: ReportFormat) -> String;
```

```python
# Python: run the same suite, compare with Rust
from ct_bench_suite import run_suite, compare_backends, generate_report

results = run_suite("full")
comparison = compare_backends(results)
print(f"Python/Rust snap ratio: {comparison.snap.python_vs_rust}x")

# Generate publishable report
report = generate_report(results, format="markdown")
```

```bash
# CLI: one-command reproducibility
$ cargo install ct-bench-suite
$ ct-bench run --suite full --output report.md
$ ct-bench compare --baseline v2.0 --current HEAD
$ ct-bench plato-stress --rooms all --tiles all
```

### Estimated Complexity

| Component | Effort | Notes |
|---|---|---|
| Canonical workload definitions | Medium | Must be precise enough for third-party reproduction |
| Rust benchmark runner (criterion-based) | Medium | Wraps criterion with CT-specific harness |
| Python benchmark runner | Low | Mirrors Rust workloads via PyO3 bindings |
| CUDA benchmark runner | Medium | Extends existing CUDA snap benchmarks |
| PLATO stress tests | Medium | Depends on plato-tile-store for data loading |
| Regression detection | Low | Statistical comparison (t-test + threshold) |
| Report generator (markdown + HTML) | Medium | Charts via plotters or similar |
| CLI tool | Low | clap-based, wraps the library |
| **Total** | **~4-6 weeks** | Fastest to ship; high impact-to-effort ratio |

---

## Delivery Sequence

```
Week 1-6:   ct-bench-suite (Deliverable 3)
            ^-- Ship first: validates existing claims, builds credibility

Week 3-10:  ct-geometry (Deliverable 2)
            ^-- Start Phase A in week 3, overlap with bench suite finalization
            ^-- PLATO integration validates geometry against bench suite

Week 7-14:  constraint-theory-proofs (Deliverable 1)
            ^-- Start after geometry primitives stabilize (they inform proof encoding)
            ^-- Verifier ships first (week 9), full prover by week 14
```

### Why This Order

1. **Bench suite first** because it's fastest to ship and immediately upgrades every existing crate's credibility. It also reveals performance characteristics that inform geometry engine design.
2. **Geometry engine second** because it's the practical "pull" that attracts developers. PLATO integration here connects published theory to published data.
3. **Formal proofs last** because they benefit from stable APIs in the other two crates, and the bench suite provides the empirical baselines that proofs formalize.

---

## Impact Matrix

| Audience | Deliverable 1 (Proofs) | Deliverable 2 (Geometry) | Deliverable 3 (Benchmarks) |
|---|---|---|---|
| **Academic/Math** | **Primary** — citable, verifiable | Supporting — novel algorithms | Supporting — reproducible claims |
| **Rust developers** | Niche — formal methods users | **Primary** — practical geometry | Supporting — perf validation |
| **Python developers** | Niche | **Primary** — replaces shapely workarounds | **Primary** — easy comparison |
| **PLATO community** | Supporting — validates tiling theory | **Primary** — native PLATO geometry | **Primary** — stress test showcase |

---

## Success Criteria

1. **Proofs**: At least one theorem accepted at a formal methods venue (LICS, ITP, CPP, or JAR).
2. **Geometry**: `ct-geometry` processes all 7700 PLATO tiles with zero degeneracies and >2x throughput vs. CGAL on boolean operations.
3. **Benchmarks**: Published results independently reproduced by at least 3 external parties within 60 days of release.
4. **Combined**: Total crates.io downloads across all fleet crates exceeds 10,000/month within 6 months of Deliverable 3 shipping.

---

*End of strategic plan. Each deliverable has its own tracking issue in the fleet project board.*
