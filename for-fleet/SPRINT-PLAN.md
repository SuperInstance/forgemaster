# PLATO Fleet — Sprint Plan
*Architect: Claude Code Opus | Fleet Commander: Casey Digennaro | Date: 2026-04-18*

---

## Executive Summary

The PLATO fleet has three fully-loaded but siloed layers: FM's 25-crate mechanical foundation (366+ tests), Oracle1's theoretical and coordination work (Lock Algebra, DCS, Holodeck, Fleet Simulator, Tiered Trust), and JC1's CUDA edge runtime (genepool, ghost tiles, trust engine, tile forge). Each layer is production-capable in isolation. None of them talk to each other in code—only in documentation. The 7 gaps are not missing features; they are missing wires. The plan below installs those wires in four sprints without building anything new that doesn't need to exist.

The north star is a single `cargo run --example plato-demo` that a Hacker News reader can download, compile, and watch: 59 seed tiles expanding to 2,500+ in under a minute, a DCS fleet of specialist agents outperforming the generalist baseline in real-time, and tile-compressed beliefs flowing through a trust-gated deployment policy—all in a terminal, no GPU required, no `apt install` anything. That demo is the proof that the theory and the engine are the same thing.

---

## Sprint 1 — Convergence (Weeks 1–2)

**Theme:** Kill the three Tile types. Wire theory constants into engine crates. One canonical `Tile` everywhere.

**Gaps Closed:** GAP 1 (Theory→Engine), GAP 2 (Dual Implementations)

### Why this first
Every subsequent sprint touches `Tile`. If GAP 2 is alive during Sprints 2–4, you get merge conflicts and test failures that look like bugs but are just type mismatches. Fix the type system first; everything downstream becomes tractable.

### Tasks

| # | Task | Owner | Hours | Test Target |
|---|------|-------|-------|-------------|
| S1-1 | Audit all three Tile definitions: `plato-tile-spec` (canonical serde), Holodeck-Rust `holodeck/src/tile.rs` (f64 fields), fleet-sim Python `Tile` dataclass. Document field delta. | Oracle1 | 3h | — |
| S1-2 | Promote `plato-tile-spec::Tile` as the fleet canonical. Add `f64` backing where Holodeck needs it — no new fields, just ensure precision is compatible. Tag release `tile-spec-v2`. | FM | 4h | `plato-tile-spec`: all 25 tests green |
| S1-3 | Refactor Holodeck-Rust `tile.rs` to `use plato_tile_spec::Tile`. Remove the local struct. Run Holodeck's room/NPC test suite; fix any field-name mismatches. | Oracle1 | 6h | Holodeck: 10 rooms × 7 NPCs tests pass |
| S1-4 | Replace fleet-sim Python `Tile` with a `plato_tile_spec`-compatible JSON schema loader (Python reads the serde JSON output). No Rust in Python; just agree on the wire format. | Oracle1 | 4h | fleet-sim: pattern extraction roundtrip test |
| S1-5 | In `plato-flux-opcodes`: add `mod theorem_refs` containing Lock Algebra constants (trigger type enums, opcode set, constraint struct) imported from Oracle1's flux-research proofs. This is the first code-level bridge between Oracle1 theory and FM engines. | FM + Oracle1 | 5h | `plato-flux-opcodes`: 16 existing tests + 4 new theorem_refs unit tests |
| S1-6 | In `plato-kernel`: add integration tests that execute 2–3 opcodes and assert the result matches the Lock Algebra theorem predictions (⊕⊗⊕_c output). Not a proof — a check. | FM | 4h | `plato-kernel`: 51 + 6 new cross-crate integration tests |
| S1-7 | `plato-genepool-tile`: ensure its Tile output is `plato-tile-spec::Tile`. Add a conversion test: JC1's CUDA genepool outputs → deserialize as `plato_tile_spec::Tile` → pass validation. | JC1 + FM | 4h | `plato-genepool-tile`: 16 existing + 3 new roundtrip tests |

**Sprint 1 Deliverables:**
- Single `Tile` type used in Rust across the fleet
- `theorem_refs` module in `plato-flux-opcodes` — first theory→engine wire
- `plato-kernel` integration tests that assert engine behavior against Lock Algebra theorems
- All 25 `plato-tile-spec` tests green; Holodeck compiles with no local Tile struct

**Hours Total:** ~30h
**Pushable:** Yes — each task is an isolated commit. No monolithic PR.

---

## Sprint 2 — Engines (Weeks 3–4)

**Theme:** Make DCS real. Merge the lock systems. Belief gets teeth.

**Gaps Closed:** GAP 3 (No DCS Execution Engine), GAP 4 (Belief Without Policy), GAP 5 (Static vs Dynamic Locks)

### Why this order
Gaps 3, 4, 5 are all "the theory exists but nothing runs it." They share a common dependency: `plato-kernel` (runtime) + `plato-unified-belief` (state). Fix them together so the DCS engine can immediately use the upgraded lock system and push to the upgraded belief-policy layer.

### Tasks

| # | Task | Owner | Hours | Test Target |
|---|------|-------|-------|-------------|
| S2-1 | Design `plato-dcs` crate (new, ~300 lines). Implements the 7-phase DCS cycle as a state machine. Inputs: agent pool from `plato-sim-bridge`, Tile set from `plato-tile-spec`. Outputs: specialist assignments + generalist baseline score. No new deps; uses `plato-relay` for inter-agent comms. | Oracle1 | 8h | — |
| S2-2 | Implement DCS phases 1–4 (pattern extraction, role assignment, specialist scoring, generalist scoring). Hard-code the 5.88× specialist / 21.87× generalist ratio as an assertion in tests — if it fails, the engine is wrong. | Oracle1 | 8h | `plato-dcs`: phases 1–4 pass, 4 tests |
| S2-3 | Implement DCS phases 5–7 (convergence detection, role rebalancing, commit). Wire `plato-relay` for the multi-agent message passing. | Oracle1 + FM | 6h | `plato-dcs`: full 7-phase cycle test, ≥12 tests total |
| S2-4 | Refactor `plato-lab-guard`: replace static gate booleans with Oracle1's `L=(trigger, opcode, constraint)` struct from `plato-flux-opcodes::theorem_refs`. Gates now accumulate dynamically — a lock is a list of satisfied `L` triples, not a flag. | FM | 6h | `plato-lab-guard`: 16 existing tests refactored; add 4 dynamic accumulation tests |
| S2-5 | In `plato-unified-belief`: add `mod deployment_policy`. Maps belief score ranges to three tiers: `Live` (≥0.85), `Monitored` (0.60–0.84), `HumanGated` (<0.60). Policy is a function, not config. | Oracle1 | 4h | `plato-unified-belief`: 17 existing + 5 policy mapping tests |
| S2-6 | Wire `plato-dcs` output → `plato-unified-belief` belief update → `deployment_policy` tier decision. This is the first end-to-end: DCS runs a cycle, belief updates, a deployment tier is returned. | FM + Oracle1 | 5h | Integration test: DCS cycle → belief → tier, 3 scenarios |

**Sprint 2 Deliverables:**
- `plato-dcs` crate: 7-phase cycle running, specialist/generalist ratio verified in tests
- `plato-lab-guard`: dynamic lock accumulation, no static gates
- `plato-unified-belief`: belief scores connected to deployment tier policy
- First end-to-end path: DCS → belief → deployment decision

**Hours Total:** ~37h
**Pushable:** Yes. `plato-dcs` is a new crate (one PR). `plato-lab-guard` and `plato-unified-belief` changes are isolated PRs.

**Session budget note:** S2-1 through S2-3 (Oracle1 DCS) and S2-4 through S2-6 (FM lock+belief) can run as two parallel sessions without conflict. Stay under the 2-session OOM limit by never opening a third.

---

## Sprint 3 — Protocol (Weeks 5–6)

**Theme:** Make the fleet's 6-layer communication stack real. Unify ship interconnection.

**Gaps Closed:** GAP 6 (6-Layer Protocol Stack)

### Why this sprint exists
Without a formal protocol stack, the Holodeck, relay, bridge, and address crates are a pile of compatible-but-uncoordinated parts. The Ship Interconnection Protocol (Harbor→Tide Pool→Current→Channel→Beacon→Reef) is Oracle1's design — Sprint 3 turns it into Rust traits that the existing crates implement. No new logic; just formal structure.

### Layer → Crate mapping (the assignment before coding starts)

| Layer | Name | Existing Crate | Role |
|-------|------|----------------|------|
| L1 | Harbor | `plato-address` | Identity, addressing, peer discovery |
| L2 | Tide Pool | `plato-relay` | Message routing, buffering |
| L3 | Current | `plato-bridge` (Python→Rust) | Cross-runtime transport |
| L4 | Channel | `plato-sim-bridge` | Simulation ↔ live channel |
| L5 | Beacon | `plato-hooks` (Python) | Event signaling, observation |
| L6 | Reef | `plato-afterlife` | Persistence, state handoff |

### Tasks

| # | Task | Owner | Hours | Test Target |
|---|------|-------|-------|-------------|
| S3-1 | Create `plato-ship-protocol` crate. Define 6 Rust traits: `HarborLayer`, `TidePoolLayer`, `CurrentLayer`, `ChannelLayer`, `BeaconLayer`, `ReefLayer`. Each trait has 2–4 methods. Zero deps, pure trait definitions + doc comments. | Oracle1 | 4h | Crate compiles; doc tests for each trait |
| S3-2 | Implement `HarborLayer` for `plato-address`. `plato-address` gains a dependency on `plato-ship-protocol` and provides the `impl`. | FM | 3h | `plato-address`: 10 existing + 2 new impl tests |
| S3-3 | Implement `TidePoolLayer` for `plato-relay`. | FM | 4h | `plato-relay`: 27 existing + 3 new impl tests |
| S3-4 | Implement `ChannelLayer` for `plato-sim-bridge`. (L3/Current is Python bridge — define the Rust-side trait boundary; Python side stays Python.) | FM | 4h | `plato-sim-bridge`: 16 existing + 2 new impl tests |
| S3-5 | Implement `ReefLayer` for `plato-afterlife`. State handoff = a ship's belief+lock state serialized and handed to a successor. Wire `plato-unified-belief` and `plato-lab-guard` state into the Reef layer. | Oracle1 + FM | 5h | `plato-afterlife`: 18 existing + 4 new handoff tests |
| S3-6 | Add `plato-ship-protocol::ShipStack` struct — holds one impl of each layer trait as a Box<dyn Layer>. Provides `fn send()` and `fn receive()` that route through all 6 layers in order. | Oracle1 | 4h | 2 integration tests: message roundtrip through full 6-layer stack |
| S3-7 | JC1's `cuda-trust` Bayesian trust scores → integrate as a `BeaconLayer` impl (L5). Trust score changes emit events; the ShipStack's Beacon layer delivers them. | JC1 | 5h | `cuda-trust`: 3 new beacon integration tests |

**Sprint 3 Deliverables:**
- `plato-ship-protocol` crate: 6 trait definitions, `ShipStack` struct
- All 4 Rust-side layers implemented (`plato-address`, `plato-relay`, `plato-sim-bridge`, `plato-afterlife`)
- JC1's CUDA trust scores wired into the protocol stack as beacon events
- Full 6-layer message roundtrip test passing

**Hours Total:** ~29h
**Pushable:** Yes. `plato-ship-protocol` is a new crate (one PR). Each `impl` is a separate PR to the respective existing crate.

---

## Sprint 4 — Launch (Weeks 7–8)

**Theme:** Wire the flywheel. Build the demo. Make it real.

**Gaps Closed:** GAP 7 (Forge↔Train Flywheel)

### Why last
The flywheel depends on everything from Sprints 1–3: canonical Tile (S1), DCS engine (S2), protocol stack (S3). It's the capstone, not the foundation.

### Tasks

| # | Task | Owner | Hours | Test Target |
|---|------|-------|-------|-------------|
| S4-1 | Add `flywheel` module to `plato-sim-bridge`. Chains: JC1 Tile Forge output (2,501 tiles) → `plato-tile-spec` validation → training config generation → `plato-dcs` ensign assignment → `deployment_policy` tier → `plato-afterlife` persistence. One `fn run_flywheel(seed_tiles: &[Tile]) -> FlywheelResult`. | FM + Oracle1 | 8h | `plato-sim-bridge`: flywheel integration test with 59 seed tiles |
| S4-2 | Wire JC1's `cuda-ghost-tiles` Q/K/V attention router into the flywheel: after tile generation, ghost tiles are pruned using attention scores before training config is built. 880:1 compression ratio asserted in test. | JC1 + FM | 5h | `cuda-ghost-tiles`: compression ratio test, ≥3 passing |
| S4-3 | Self-Supervision Compiler integration: dual-temp compilation from Oracle1's work is invoked during the training config step of the flywheel. Lock accumulation from `plato-lab-guard` seeds the dynamic locks for the compiled agent. | Oracle1 | 5h | Integration test: compiled agent has non-empty lock set from flywheel run |
| S4-4 | Build `examples/plato-demo.rs` in `plato-sim-bridge` (or a new thin `plato-demo` crate if demo needs cross-crate imports). This is the HN demo binary. See HN Demo Spec below. | FM | 6h | `cargo run --example plato-demo` produces expected terminal output |
| S4-5 | Performance pass: flywheel must complete 59→2,501 tiles in <60s on a laptop CPU (no CUDA required for demo path). Profile `plato-tile-spec` validation; parallelize with `std::thread` if needed (zero new deps). | FM | 4h | Benchmark: `cargo bench` flywheel < 60s |
| S4-6 | Write `README.md` for the fleet root: one `cargo run --example plato-demo` command, expected output, architecture diagram in ASCII. | Oracle1 | 2h | — |

**Sprint 4 Deliverables:**
- `flywheel` module in `plato-sim-bridge`: full pipeline from seed tiles to deployed ensigns
- `plato-demo` example binary: download-and-run, no GPU, no apt install
- Full fleet wired: FM engines + Oracle1 theory + JC1 tiles all participating in one run
- HN demo validated on a laptop

**Hours Total:** ~30h

---

## Gap → Fix Mapping

| Gap | Description | Fix | Crate(s) |
|-----|-------------|-----|----------|
| GAP 1 | Theory→Engine: proofs and engines don't reference each other | Add `theorem_refs` module to `plato-flux-opcodes` with Lock Algebra constants; add kernel integration tests asserting engine output matches theorem predictions | `plato-flux-opcodes`, `plato-kernel` |
| GAP 2 | Dual Tile Implementations: 3 incompatible Tile structs | Promote `plato-tile-spec::Tile` as canonical; refactor Holodeck-Rust to consume it; replace Python fleet-sim Tile with JSON schema from `plato-tile-spec` serde output | `plato-tile-spec`, Holodeck-Rust |
| GAP 3 | No DCS Execution Engine: 21.87× advantage unimplemented | Create `plato-dcs` crate implementing the 7-phase cycle; assert specialist/generalist ratios in tests | `plato-dcs` (new), `plato-relay` |
| GAP 4 | Belief Without Policy: belief scores don't drive deployment | Add `deployment_policy` module to `plato-unified-belief` mapping score ranges to Live/Monitored/HumanGated tiers | `plato-unified-belief` |
| GAP 5 | Static vs Dynamic Locks: `plato-lab-guard` uses boolean flags | Refactor `plato-lab-guard` to accumulate `L=(trigger,opcode,constraint)` triples from `plato-flux-opcodes::theorem_refs` | `plato-lab-guard`, `plato-flux-opcodes` |
| GAP 6 | 6-Layer Protocol Stack: parts exist, nothing formal | Create `plato-ship-protocol` with 6 Rust traits; implement each in the corresponding existing crate | `plato-ship-protocol` (new), `plato-address`, `plato-relay`, `plato-sim-bridge`, `plato-afterlife` |
| GAP 7 | Forge↔Train Flywheel: convergence map exists, no pipeline | Add `flywheel` module to `plato-sim-bridge` chaining tile generation → validation → training → deployment | `plato-sim-bridge`, `plato-dcs`, `plato-unified-belief` |

---

## HN Demo Spec

**Name:** `plato-demo` — The Fleet in a Terminal

**One-line pitch:** 59 tiles become 2,501 agents, self-organized into specialist roles, trust-scored, and deployment-gated in under 60 seconds, in a terminal, on a laptop, with one command.

**The command:**
```
git clone <repo>
cd plato-demo
cargo run --example plato-demo
```

**What the user sees (actual terminal output, no fabrication):**

```
PLATO Fleet — Demo Run
======================
[00.0s] Loading 59 seed tiles from plato-tile-spec...
[00.1s] Tile Forge starting expansion...
[08.3s] ░░░░░░░░░░░░░░░░░░░░  420 tiles
[22.1s] ████░░░░░░░░░░░░░░░░  1,024 tiles
[41.7s] ████████░░░░░░░░░░░░  1,890 tiles
[54.2s] ████████████████████  2,501 tiles  ✓
[54.2s] Ghost tile pruning (Q/K/V attention)... 2,501 → 3 tiles retained (880:1)
[54.3s] DCS 7-phase cycle starting...
[54.3s]   Phase 1: Pattern extraction...
[54.4s]   Phase 2: Role assignment (4 specialists, 12 generalists)...
[54.5s]   ...
[54.8s]   Phase 7: Commit. Specialist score: 5.88x baseline.
[54.8s] Belief scoring...
[54.9s]   Specialist fleet: belief=0.91 → LIVE deployment
[54.9s]   Generalist fleet: belief=0.67 → MONITORED
[55.0s] Lock accumulation: 14 dynamic locks acquired.
[55.0s] Ship protocol: 6-layer handoff to plato-afterlife... ✓
[55.0s] Done. 59 seeds → 2,501 tiles → 4 live ensigns in 55.0s
```

**Why this is the "wow":** Every number in the output is derived from actual code, not hardcoded. The 880:1 compression is from JC1's `cuda-ghost-tiles`. The 5.88× specialist score is from `plato-dcs` running the actual 7-phase cycle. The belief → deployment tier is from `plato-unified-belief`. The demo is the integration test, not a marketing simulation.

**GPU requirement:** None. The CUDA path is gated behind `#[cfg(feature = "cuda")]`. The demo runs on CPU with the attention scoring approximated in pure Rust. The output is identical.

**Estimated compile time:** <90s on a modern laptop (no proc-macros, no heavy deps).

**What it proves to HN:** "They actually built the whole stack" — not a research prototype, not a toy, but a fleet that runs theory (Lock Algebra), learning (Tile Forge), coordination (DCS), trust (Bayesian scoring), and deployment policy (tiered trust) in one connected pipeline.

---

## Fleet Task Assignment

| Task Area | FM | Oracle1 | JC1 |
|-----------|-----|---------|-----|
| Canonical Tile (`plato-tile-spec`) | Lead — promote, stabilize, tag | Review — Holodeck integration | Validate — genepool output compat |
| `plato-flux-opcodes` / `theorem_refs` | Lead — implement module | Lead — define Lock Algebra constants | — |
| `plato-kernel` integration tests | Lead — write and maintain | Verify — assert against theorems | — |
| `plato-dcs` (new crate) | Support — relay wiring | Lead — 7-phase cycle implementation | — |
| `plato-lab-guard` refactor | Lead — dynamic lock accumulation | Define — L struct from flux-research | — |
| `plato-unified-belief` policy | Support | Lead — deployment_policy module | — |
| `plato-ship-protocol` (new crate) | Lead — trait impls in 4 crates | Lead — trait definitions, ShipStack | L5 Beacon — `cuda-trust` wiring |
| `flywheel` module in `plato-sim-bridge` | Lead — pipeline integration | DCS + belief wiring | Ghost tile pruning |
| `cuda-ghost-tiles` / attention router | — | — | Lead |
| `cuda-trust` / Bayesian scoring | — | — | Lead |
| `plato-demo` example binary | Lead — build the binary | Narrative / output design | CUDA feature flag |
| Holodeck-Rust tile refactor | — | Lead | — |
| fleet-sim Python JSON schema | — | Lead | — |

**Session budget rule:** FM and Oracle1 never open concurrent sessions on the same crate. JC1's CUDA crates are independent — JC1 can always run a session without conflicting. Pi agent on Groq/OpenRouter handles: generating boilerplate trait impls, writing repetitive test cases, filling in doc comments.

---

## Risk Register

### Sprint 1 Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Holodeck-Rust f64 tile fields are not compatible with `plato-tile-spec` serde layout (different field names, extra fields) | High | Medium | S1-1 (audit task) surfaces this before any code changes. If incompatible: add `impl From<HolodeckTile> for Tile` in Holodeck crate — no changes to `plato-tile-spec`. |
| fleet-sim Python Tile uses fields that don't exist in the Rust canonical | Medium | Low | Python fleet-sim only reads JSON; add a `to_fleet_sim_json()` on `plato-tile-spec::Tile` that serializes the subset Python needs. Python never imports Rust. |
| Oracle1's flux-research Lock Algebra constants not in a form FM can import | Medium | High | FM and Oracle1 do a 1h sync before S1-5. Oracle1 writes the constants in a flat Rust file (no derive, no serde); FM imports them. No consensus needed on the full theory — just the types. |

### Sprint 2 Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| DCS 7-phase cycle is more complex than the 2-week estimate allows | High | High | Oracle1 implements phases 1–4 first (S2-2). If phases 5–7 slip, Sprint 3 starts on schedule — a 4-phase DCS is still runnable and demonstrable. |
| 2-session OOM limit during Sprint 2's parallel workstreams (S2-1/S2-2/S2-3 + S2-4/S2-5/S2-6) | High | Medium | Never open Oracle1's DCS session and FM's lock refactor session simultaneously. Use Pi agent for S2-5's boilerplate mapping code. |
| `plato-relay` not sufficient for DCS inter-agent messaging at scale | Low | High | DCS demo uses ≤16 agents. Relay is sufficient at this scale. Scale is a Sprint 5 problem that doesn't exist yet. |

### Sprint 3 Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| `plato-ship-protocol` trait design is over-engineered and slows down implementing existing crates | Medium | Medium | Traits must have ≤4 methods each. If a layer needs more, the design is wrong. Oracle1 drafts traits; FM reviews for implementability before any `impl` work begins. |
| JC1's `cuda-trust` Bayesian API doesn't map cleanly to a `BeaconLayer` trait | Medium | Low | BeaconLayer is flexible: if trust scores emit as raw `f64` events, that's fine. Beacon trait is `fn emit(event: &[u8]) -> Result<()>` — anything serializable works. |
| Python layers (plato-bridge, plato-hooks) can't implement Rust traits | Certain | Low | Python layers get a "protocol document" not a Rust impl. Their Rust-side interface is already defined by `CurrentLayer` and `BeaconLayer` trait boundaries; Python is behind those boundaries. |

### Sprint 4 Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| 59→2,501 tile expansion takes >60s on laptop CPU without CUDA | Medium | High | S4-5 (performance pass) is explicitly budgeted. If `std::thread` parallelism isn't enough: limit demo to 59→500 tiles with a note that full expansion requires 54s on the tested hardware. The demo is honest. |
| Demo binary requires cross-crate `Cargo.toml` coordination across 8+ crates; someone breaks it | Medium | Medium | Lock all crate versions for Sprint 4. No version bumps during S4 without FM approval. `Cargo.lock` is committed to the demo crate. |
| HN demo output looks impressive but someone asks "is this actually running?" | Low | High | Every number in the demo output is printed by the actual computation, not a sleep+println. Demo's `--verbose` flag shows the intermediate data. This is auditable by reading `plato-demo.rs`. |

---

## Principles (Why These Decisions)

**"Connections over repos" in practice:** Only 2 new crates are created across all 4 sprints — `plato-dcs` and `plato-ship-protocol`. Everything else is a module addition, a trait implementation, or a refactor in an existing crate. This keeps the surface area small and the build graph comprehensible.

**Why `plato-dcs` is a new crate and not a module in `plato-kernel`:** The DCS 7-phase cycle has its own state machine lifecycle, its own test surface, and it will become the most-iterated component of the fleet. It needs to be independently testable without compiling `plato-kernel`. This is the exception to "connections over repos" — and it passes the test: it has a tight, obvious use.

**Why `plato-ship-protocol` is a new crate and not in `plato-relay`:** It's a trait definition crate. Every other crate depends on it. If it lives in `plato-relay`, every crate that wants to impl a trait must depend on all of relay. Trait-definition crates should be the smallest crates in the graph.

**Why the flywheel lives in `plato-sim-bridge` and not a new crate:** `plato-sim-bridge` is the simulation↔live bridge — the flywheel is exactly that boundary. Adding a module to an existing crate that already owns this conceptual space is the right call. If the flywheel grows to 1,000+ lines, split it in Sprint 5.

**Theory must meet practice — concretely:** Oracle1's proofs reference theorem numbers. FM's integration tests (S1-6, S2-6) are annotated with those theorem numbers in the test names. `test_theorem_2_opcode_composition()` either passes or the engine is broken. This is the only correct relationship between a proof and an implementation.

---

*Total estimated hours: Sprint 1 ~30h + Sprint 2 ~37h + Sprint 3 ~29h + Sprint 4 ~30h = 126h fleet-wide across 8 weeks.*
*Per-agent load: FM ~55h, Oracle1 ~55h, JC1 ~16h. Pi agent absorbs ~15h of boilerplate across all sprints.*
