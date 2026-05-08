# Fleet Modularization Proposal

**Scope:** SuperInstance fleet — 24 repos + new depgraph-gpu
**Date:** 2026-05-08
**Author:** Claude Code (architecture session)

---

## Executive Summary

The fleet has 24 repos. Three clusters have emerged organically but haven't been formalized:
1. **Eisenstein cluster** — hex arithmetic in 7 repos (should be 4)
2. **Constraint theory cluster** — constraint propagation in 4 repos (keep as-is)
3. **Fleet coordination cluster** — two repos doing overlapping things (merge)

The cross-cutting problems are: duplicated CI boilerplate, no shared GPU compute harness, no shared PLATO/I2I client, and five dev tools that should be one CLI.

**Decision: Don't over-consolidate.** Crates.io users depend on stable APIs. Merging published crates causes semver pain. The right consolidation is *tooling* and *infrastructure*, not the published libraries themselves.

---

## 1. Current Fleet Dependency Map (ASCII)

```
PUBLISHED CRATES (crates.io)
═══════════════════════════════════════════════════════════════

constraint-theory-core  ──────────────────────────────────────┐
         │                                                     │
         ├──► constraint-theory-ecosystem (54 GPU experiments) │
         │                                                     │
         └──► flux-lucid (meta-crate, re-exports core)         │
                   │                                           │
                   └──► holonomy-consensus                     │
                               │                               │
                               └──► fleet-coordinate  ─────────┤
                                                               │
eisenstein ────────────────────────────────────────────────────┤
     │     (hex arithmetic, no deps)                          │
     │                                                         │
     ├──► eisenstein-c       (C port, no dep on Rust crate)   │
     ├──► eisenstein-wasm    (WASM, no dep on Rust crate)     │
     ├──► eisenstein-do178c  (Coq proofs, no dep on Rust)     │
     ├──► eisenstein-bench   (depends on eisenstein)          │
     ├──► eisenstein-fuzz    (depends on eisenstein)          │
     ├──► arm-neon-eisenstein-bench (depends on eisenstein)   │
     └──► hexgrid-gen        (generates code FROM eisenstein) │
                                                               │
pythagorean48-codes (standalone, no fleet deps) ───────────────┤
                                                               │
RESEARCH / DOCS (no code deps, informational only)            │
═══════════════════════════════════════════════════════════════│
multi-model-adversarial-testing  ────────────────────────────┐│
negative-knowledge               ─────────────────────────────┤│
sheaf-constraint-synthesis       ─────────────────────────────┤│
constraint-theory-math           ─────────────────────────────┤│
intent-directed-compilation      ─────────────────────────────┘│
                                                               │
CROSS-LANGUAGE PORTS                                           │
═══════════════════════════════════════════════════════════════│
polyformalism-a2a-python  ─────────────────────────────────────┤
polyformalism-a2a-js      ─────────────────────────────────────┤
                                                               │
INFRASTRUCTURE / WEB                                           │
═══════════════════════════════════════════════════════════════│
casting-call     (model eval database) ────────────────────────┤
cocapn-ai-web    (landing page) ───────────────────────────────┤
superinstance    (org README) ─────────────────────────────────┘

NEW (proposed)
═══════════════════════════════════════════════════════════════
depgraph-gpu     (no deps on fleet crates)
superinstance-gpu-compute  (shared CUDA harness — internal)
superinstance-fleet-proto  (PLATO + I2I client — internal)
```

---

## 2. Repo-by-Repo Verdict

### 2A. Merge

#### `holonomy-consensus` + `fleet-coordinate` → `fleet-consensus`

**Argument:** Holonomy consensus *is* a spatial coordination mechanism. `fleet-coordinate` handles multi-agent position tracking. Both need quorum-free consensus primitives. Keeping them separate means whoever adds a new coordination algorithm has to decide which repo to put it in — and gets it wrong half the time.

**What breaks:** Both crates are published on crates.io. The migration path:
1. Create `fleet-consensus` with all code from both
2. Release `holonomy-consensus` v0.x+1 as a thin re-export of `fleet-consensus::holonomy`
3. Release `fleet-coordinate` v0.x+1 as a thin re-export of `fleet-consensus::coordinate`
4. Mark both deprecated in Cargo.toml metadata
5. Point crates.io README at `fleet-consensus`

**Effort:** 2 days + 1 week deprecation notice cycle

**New structure:**
```
fleet-consensus/
├── src/
│   ├── lib.rs        # re-exports both submodules
│   ├── holonomy/     # moved from holonomy-consensus
│   └── coordinate/   # moved from fleet-coordinate
```

#### `eisenstein-bench` + `eisenstein-fuzz` + `hexgrid-gen` + `arm-neon-eisenstein-bench` → `eisenstein-tools`

**Argument:** These four repos are all dev tooling *for* eisenstein, not eisenstein itself. Each has one command or one purpose. None are published on crates.io as library dependencies — they're CLI tools. Keeping them as four repos means four sets of CI, four `Cargo.toml` files to update when eisenstein's API changes, and four places to check for tool coverage.

A single `eisenstein-tools` workspace crate with subcommands is the obvious design:

```
eisenstein-tools/
├── Cargo.toml    (workspace)
├── crates/
│   ├── eisenstein-bench/   # moved as-is
│   ├── eisenstein-fuzz/    # moved as-is
│   ├── hexgrid-gen/        # moved as-is
│   └── eisenstein-neon/    # arm-neon-eisenstein-bench renamed
└── src/
    └── main.rs   # top-level CLI dispatcher
```

CLI interface:
```
eisenstein-tools bench  [options]
eisenstein-tools fuzz   [targets...]
eisenstein-tools codegen [--lang rust|c|python|js|json]
eisenstein-tools neon-bench  (arm feature flag, noop on x86)
eisenstein-tools check   (runs fuzz + bench + codegen in CI mode)
```

**Effort:** 1.5 days. No published library breaking changes — these are all CLI tools.

---

### 2B. Split

None of the existing repos need splitting. The biggest (constraint-theory-ecosystem at 54 GPU experiments) is appropriately scoped as a research/benchmark repo.

---

### 2C. Stay As-Is

| Repo | Reason |
|---|---|
| `constraint-theory-core` | Stable crates.io API. Breaking change would cascade to flux-lucid. Leave it. |
| `constraint-theory-ecosystem` | Research/benchmark repo. Not a library. No reason to move it. |
| `constraint-theory-math` | Coq proofs — completely separate build chain. Independent CI. |
| `flux-lucid` | Meta-crate, actively used. Adding `fleet-consensus` as a dep when that ships is fine. |
| `eisenstein` | Core library. Never touch a working published crate. |
| `eisenstein-c` | Different build chain (Make + GCC). Separate CI. Keep. |
| `eisenstein-wasm` | wasm-pack toolchain. Separate. Keep. |
| `eisenstein-do178c` | DO-178C certification artifacts need complete isolation. Non-negotiable. |
| `pythagorean48-codes` | Standalone. No deps. No changes needed. |
| `polyformalism-a2a-python` | Different ecosystem (Python, PyPI). Keep. |
| `polyformalism-a2a-js` | Different ecosystem (npm). Keep. |
| `multi-model-adversarial-testing` | Research docs only. Leave. |
| `negative-knowledge` | Research docs. Leave. |
| `sheaf-constraint-synthesis` | Research docs. Leave. |
| `intent-directed-compilation` | Research + AVX-512 code. Leave. |
| `casting-call` | Fleet tool. Separate concerns. Leave. |
| `cocapn-ai-web` | Web, not Rust. Leave. |
| `superinstance` | Org README. Leave. |
| `depgraph-gpu` | New. Independent. Leave. |

---

## 3. New Shared Crates

### 3A. `superinstance-gpu-compute` (internal, not published)

The problem: `constraint-theory-ecosystem` has 54 GPU experiments with their own CUDA harness. `depgraph-gpu` needs a CUDA harness. Without a shared crate, we'll have two diverging CUDA context managers, two PTX loaders, two error handling paths.

**What it contains:**

```rust
// superinstance-gpu-compute/src/lib.rs

pub mod context;    // CudaContext: new(), device_name(), available()
pub mod buffer;     // GpuBuffer<T>: alloc, upload, download, len
pub mod kernel;     // PtxKernel: load_ptx(), launch(grid, block, args)
pub mod pool;       // BufferPool: reuse allocations across kernel launches
pub mod bench;      // Benchmark harness: measure_kernel_us()

// Re-exports
pub use context::CudaContext;
pub use buffer::GpuBuffer;
pub use kernel::PtxKernel;
```

**Consumers:**
- `depgraph-gpu` — topsort, BFS, hash kernels
- `constraint-theory-ecosystem` — existing 54 experiments get simplified
- Future GPU agents (if we build GREP-Agent, IntegrityForge)

**Why not upstream into cudarc?** cudarc is great but it's a general-purpose CUDA binding layer. Our shared crate is higher-level: "here's how we load PTX, here's how we manage buffer pools, here's how we benchmark." It wraps cudarc the same way tower wraps hyper.

**Cargo.toml location:** `SuperInstance/superinstance-gpu-compute` (private repo, not crates.io). Add as a git dependency in consuming crates:

```toml
[dependencies]
superinstance-gpu-compute = { git = "https://github.com/SuperInstance/superinstance-gpu-compute", optional = true }
```

**Effort:** 3 days initial implementation. Ongoing maintenance is low (stable API).

---

### 3B. `superinstance-fleet-proto` (internal, not published)

The problem: Every agent that wants to write to PLATO or send I2I messages has to reimplement the HTTP client and message format. `depgraph-gpu/src/plato.rs` is already a 60-line reimplementation of what every future agent will need.

**What it contains:**

```rust
// superinstance-fleet-proto/src/lib.rs

pub mod plato;   // PlatoClient: write(room, data), read(room), list(prefix)
pub mod i2i;     // I2iMessage: new(type, scope, body), send_to_vessel()
pub mod rooms;   // Well-known room paths: depgraph::SNAPSHOTS, etc.

// Usage:
// let plato = PlatoClient::new("http://147.224.38.131:8847");
// plato.write("depgraph/snapshots/latest", &payload).await?;
//
// I2iMessage::new("DEPGRAPH", "fleet", "Scan complete: 50K nodes")
//     .send_to_vessel("SuperInstance/forgemaster").await?;
```

**Why separate from fleet-coordinate?** `fleet-coordinate` is a published library about multi-agent spatial logic. The fleet protocol client is infrastructure. Mixing infrastructure clients into published libraries is how you get accidental API surface.

**Effort:** 1.5 days. Mostly extracting what's already in plato.rs across repos.

---

### 3C. `ConstraintKernel` Shared Trait

This one is more careful. The brief asks: should `constraint-theory-core`, `eisenstein`, and `flux-lucid` share a common `constraint-kernel` crate?

**Answer: No for a new crate. Yes for a trait.**

The reason to not extract a new crate: `eisenstein` has no dependency on `constraint-theory-core` by design. Eisenstein is "6-directional arithmetic on the Eisenstein integers." Constraint propagation is a different abstraction. Forcing a shared dependency adds coupling that doesn't exist in the math.

**Instead:** Define a `ConstraintKernel` trait *inside* `constraint-theory-core`:

```rust
// constraint-theory-core/src/kernel.rs

/// Minimal trait for constraint propagation engines.
/// Implemented by:
///   - constraint-theory-core's own propagator
///   - flux-lucid's IntentVector-aware propagator
///   - Any external constraint solver wanting fleet integration
pub trait ConstraintKernel: Send + Sync {
    type Domain: Clone + PartialEq;
    type Constraint: Clone;

    fn propagate(
        &mut self,
        constraints: &[Self::Constraint],
        domains: &mut [Self::Domain],
    ) -> Result<bool, ConstraintError>;  // true = changed, false = fixpoint

    fn is_satisfiable(&self, domains: &[Self::Domain]) -> bool;
}

#[derive(Debug, thiserror::Error)]
pub enum ConstraintError {
    #[error("contradiction: no value satisfies constraints")]
    Contradiction,
    #[error("propagation limit exceeded after {0} iterations")]
    IterationLimit(u32),
}
```

`flux-lucid` can then implement `ConstraintKernel` for its `IntentVector` propagator, making it slot cleanly into anything that consumes `constraint-theory-core`. No new crate, no new repo, no new CI pipeline.

---

### 3D. `FleetProtocol` Trait (in `superinstance-fleet-proto`)

```rust
pub trait FleetAgent: Send + Sync {
    fn agent_id(&self) -> &str;
    fn channel(&self) -> &str;    // "agent/depgraph-gpu"
    fn capabilities(&self) -> &[&str];  // ["scan", "check", "impact"]

    async fn handle(&mut self, req: AgentRequest) -> AgentResponse;
}
```

Any agent that implements `FleetAgent` gets:
- Automatic registration with OpenClaw
- Standard I2I message formatting
- PLATO write routing

---

## 4. CLI Consolidation: `eisenstein-tools` vs Separate

**Decision: `eisenstein-tools` mega-CLI.**

Arguments for keeping separate:
- Isolation: a fuzz regression doesn't break bench CI
- Focused repos are easier for external contributors to understand

Arguments for merging:
- These tools have NO external contributors. They're internal dev tools.
- When eisenstein's API changes, updating 4 `Cargo.toml` files is annoying
- The bench and fuzz tools are used together constantly — running both is the workflow
- One `cargo install eisenstein-tools` beats four separate installs

**Verdict:** Merge. The isolation argument is moot for internal tools with no external contributors. The operational overhead of 4 repos outweighs the theoretical isolation benefit.

**Subcommand mapping:**

| Current repo | New subcommand | Notes |
|---|---|---|
| `eisenstein-bench` | `eisenstein-tools bench` | `--mode drift|disk|snap|norm|full` |
| `eisenstein-fuzz` | `eisenstein-tools fuzz` | `--target mul|add|norm|all` |
| `hexgrid-gen` | `eisenstein-tools codegen` | `--lang rust|c|python|js|json` |
| `arm-neon-eisenstein-bench` | `eisenstein-tools bench --neon` | Feature flag: `neon` |

The 4 old repos become archived (not deleted — their git history is valuable). New installs use `eisenstein-tools`.

---

## 5. Cross-Language Port Strategy

Current situation:
- `eisenstein`: Rust (canonical)
- `eisenstein-c`: C (hand-maintained)
- `eisenstein-wasm`: WASM (built from Rust via wasm-pack)
- `polyformalism-a2a-python`: Python (hand-maintained)
- `polyformalism-a2a-js`: JavaScript (hand-maintained)
- `hexgrid-gen`: generates Rust/C/Python/JS lookup tables from templates

**Should ports be generated from a single spec or hand-maintained?**

**Answer: Hybrid — spec for data, hand-maintenance for logic.**

The part of each port that is *tables and constants* (hex grid lookup tables, the 12 Eisenstein unit vectors, the Pythagorean48 encoding tables) should be generated. `hexgrid-gen` already does this. Expand it.

The part that is *algorithmic logic* (multiplication, norm, topological sort, constraint propagation) should be hand-maintained in each language because:
1. Idiomatic code differs per language (Python uses `__mul__`, JS uses `BigInt`, C uses `uint64_t`)
2. The tests in each language are the spec — if they all pass the same golden vectors, they're correct
3. Code generation for algorithms produces unreadable output (try reading generated Rust from a C++ template engine)

**Concretely:**
- `hexgrid-gen codegen` produces lookup tables in all languages from a single Rust data file
- Each port maintains its own algorithmic implementation
- A shared golden vector test suite (JSON) is the cross-language spec
- CI runs: `hexgrid-gen codegen --verify` to confirm generated tables match implementations

**This is already partially true.** The 5-phase CI pipeline built in session Phase 12 does exactly this for the constraint theory ports. Apply the same pattern to eisenstein ports.

---

## 6. CI/CD Shared Workflow Template

Problem: 24 repos × N workflow YAML files = drift. When we discovered that `rustc 1.95.0` had breaking changes vs 1.75.0, we had to update CI in multiple repos manually.

**Solution: Shared reusable workflow in `SuperInstance/superinstance` (org repo).**

```yaml
# .github/workflows/rust-template.yml
# Callable workflow — used by fleet Rust repos
name: Rust CI Template

on:
  workflow_call:
    inputs:
      rust-version:
        required: false
        type: string
        default: "1.95.0"
      cuda-enabled:
        required: false
        type: boolean
        default: false
      features:
        required: false
        type: string
        default: ""

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@master
        with:
          toolchain: ${{ inputs.rust-version }}
          components: rustfmt, clippy

      - name: Cache cargo
        uses: actions/cache@v3
        with:
          path: |
            ~/.cargo/registry
            ~/.cargo/git
            target/
          key: ${{ runner.os }}-cargo-${{ hashFiles('**/Cargo.lock') }}

      - name: Check format
        run: cargo fmt --check

      - name: Clippy
        run: cargo clippy ${{ inputs.features != '' && format('--features {0}', inputs.features) || '' }} -- -D warnings

      - name: Test
        run: cargo test ${{ inputs.features != '' && format('--features {0}', inputs.features) || '' }}

      - name: Build release
        run: cargo build --release ${{ inputs.features != '' && format('--features {0}', inputs.features) || '' }}
```

Each repo's CI then becomes 15 lines:

```yaml
# SuperInstance/eisenstein/.github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  ci:
    uses: SuperInstance/superinstance/.github/workflows/rust-template.yml@main
    with:
      rust-version: "1.95.0"
```

For repos with GPU (constraint-theory-ecosystem, depgraph-gpu), a separate GPU-enabled runner job that runs only on `main` or tagged releases.

```yaml
# SuperInstance/depgraph-gpu/.github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  ci:
    uses: SuperInstance/superinstance/.github/workflows/rust-template.yml@main
    with:
      rust-version: "1.95.0"
      features: ""           # default (no GPU in CI)

  gpu-check:
    if: github.ref == 'refs/heads/main'
    runs-on: self-hosted    # eileen, when self-hosted runner is configured
    steps:
      - uses: actions/checkout@v4
      - run: cargo test --features gpu
```

**Effort:** 1 day to write template, 1 day to migrate all repos.

---

## 7. Testing Infrastructure: Generalizing the 60M Zero-Mismatch Approach

The differential testing methodology proven in constraint-theory (100M inputs, zero mismatches across Rust/C/Python/JS) is directly applicable fleet-wide.

**Generalization:**

```
┌─────────────────────────────────────────────────────────────┐
│              Golden Vector Test Framework                    │
│                                                             │
│  Spec: data/golden-vectors.json                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ {"input": [a, b], "expected": {"mul": ..., "norm":}} │   │
│  └──────────────────────────────────────────────────────┘   │
│                           │                                 │
│         ┌─────────────────┼──────────────────┐             │
│         │                 │                  │             │
│   ┌─────▼──────┐   ┌──────▼─────┐   ┌───────▼──────┐     │
│   │ Rust tests │   │ Python tests│   │  JS tests    │     │
│   │ cargo test │   │ pytest      │   │ node --test  │     │
│   └────────────┘   └────────────┘   └──────────────┘     │
│                           │                                 │
│                   ┌───────▼───────┐                        │
│                   │ CI Phase 4:   │                        │
│                   │ consistency   │                        │
│                   │ report        │                        │
│                   └───────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

Each repo that has cross-language ports:
1. Maintains `data/golden-vectors.json` (or generates it from `hexgrid-gen`)
2. Runs the golden vector suite in every language in CI
3. A `--report` flag outputs a summary JSON for the CI consistency check

`depgraph-gpu` will use this for GPU vs CPU parity testing (the CUDA tests in the implementation plan above).

---

## 8. Migration Path

Migration order matters — don't break published crates.

### Phase 1: Infrastructure (no published API changes) — 1 week

1. **Write `superinstance-fleet-proto`** (new internal repo)
   - Extract PLATO client from any existing code
   - Write I2I message formatter
   - Tests: mock HTTP server, verify message format

2. **Write shared CI workflow template** in `SuperInstance/superinstance`
   - Start with 2-3 repos, verify it works
   - Migrate remaining repos one batch at a time

3. **Write `superinstance-gpu-compute`** (new internal repo)
   - Port cudarc harness from constraint-theory-ecosystem
   - depgraph-gpu becomes first consumer

### Phase 2: Dev Tools Consolidation — 1 week

4. **Create `eisenstein-tools` workspace repo**
   - Copy code from 4 repos, don't delete originals yet
   - Add unified CLI dispatcher
   - Verify all existing tests pass
   - Archive (not delete) the 4 source repos

5. **Add deprecation notices** to archived repos' READMEs and Cargo.tomls

### Phase 3: Library Merges — 2 weeks (careful)

6. **Create `fleet-consensus`**
   - Start with private alpha, test internally
   - `fleet-coordinate v0.x+1` → thin re-export shim
   - `holonomy-consensus v0.x+1` → thin re-export shim
   - 2-version deprecation window

7. **Add `ConstraintKernel` trait** to `constraint-theory-core`
   - Non-breaking: it's an addition
   - `flux-lucid v0.x+1` implements the trait
   - Update docs to show integration pattern

### Phase 4: depgraph-gpu deployment — 1 week

8. **Deploy depgraph-gpu** against the 24-repo fleet
   - Start with `depgraph scan /path/to/fleet --output summary`
   - Wire PLATO writes
   - Register as OpenClaw agent

---

## 9. Prioritized Action List

| Priority | Action | Effort | Value | Dependencies |
|---|---|---|---|---|
| P0 | Write depgraph-gpu (Implementation doc) | 2 weeks | Immediate fleet insight | None |
| P0 | Shared CI template | 1 day | Eliminates CI drift today | None |
| P1 | `superinstance-fleet-proto` crate | 2 days | Every new agent needs this | None |
| P1 | `eisenstein-tools` mega-CLI | 1.5 days | 4 repos → 1, cleaner dev loop | None |
| P1 | `superinstance-gpu-compute` crate | 3 days | Unblocks depgraph-gpu GPU path | depgraph-gpu implementation |
| P2 | `ConstraintKernel` trait in core | 1 day | Clean integration pattern | None |
| P2 | `fleet-consensus` (merge holonomy+coordinate) | 2 days | Reduce conceptual overlap | Planning window |
| P3 | Golden vector framework generalisation | 2 days | Cross-lang test consistency | CI template |
| P3 | `FleetAgent` trait | 1 day | Standardize agent interface | fleet-proto |

**Total effort for P0+P1:** ~3 weeks. Everything after P1 is incremental improvement.

---

## 10. What NOT to Do

**Don't:** Merge published library crates for "elegance." The Rust ecosystem treats semver breaks seriously. `constraint-theory-core`, `eisenstein`, `flux-lucid` etc. have downstream users (17 crates published, 4 PyPI packages). Merging them creates churn with zero user-visible benefit.

**Don't:** Create a monorepo. The fleet's repos have different release cadences, different audiences (internal GPU experiments vs. published crates), different CI requirements (Coq proofs vs. cargo test). A monorepo optimizes for a single uniform release cycle — we don't have that.

**Don't:** Auto-generate the algorithmic logic in cross-language ports. It produces unreadable code and removes the ability to write idiomatic implementations per language. Generate only tables and constants.

**Don't:** Rush `fleet-consensus`. The merge is correct long-term but it requires a deprecation period and careful semver management. Getting it wrong breaks downstream users. P2 timing is intentional.

---

## 11. Fleet After Modularization

```
SHARED INFRASTRUCTURE (new, internal)
══════════════════════════════════════
superinstance-fleet-proto  ←─── all agents use this
superinstance-gpu-compute  ←─── GPU agents use this

PUBLISHED CRATES (unchanged API)
══════════════════════════════════════
constraint-theory-core     (+ ConstraintKernel trait added)
eisenstein
flux-lucid                 (implements ConstraintKernel)
pythagorean48-codes

MERGED CRATES (new)
══════════════════════════════════════
fleet-consensus            ←── holonomy-consensus + fleet-coordinate
eisenstein-tools           ←── bench + fuzz + hexgrid-gen + neon-bench

DEPRECATED (archived, not deleted)
══════════════════════════════════════
holonomy-consensus         (re-exports fleet-consensus::holonomy)
fleet-coordinate           (re-exports fleet-consensus::coordinate)
eisenstein-bench           (points to eisenstein-tools)
eisenstein-fuzz            (points to eisenstein-tools)
hexgrid-gen                (points to eisenstein-tools)
arm-neon-eisenstein-bench  (points to eisenstein-tools)

UNCHANGED (24 → 18 active repos after merges)
══════════════════════════════════════
constraint-theory-ecosystem
constraint-theory-math
eisenstein-c, eisenstein-wasm, eisenstein-do178c
polyformalism-a2a-python, polyformalism-a2a-js
multi-model-adversarial-testing, negative-knowledge
sheaf-constraint-synthesis, intent-directed-compilation
casting-call, cocapn-ai-web, superinstance
depgraph-gpu  (new)
```

24 active repos → **18 active repos** after consolidation (6 archived, 3 new). Clean CI template across all. Shared infrastructure for GPU agents and fleet protocol.
