# ROADMAP

**Generated:** 2026-05-17 | **Synthesized from:** 11 source documents, 3 audits, 1 multi-model design session, 1 zero-shot beta test

---

## 1. Vision Statement

SuperInstance builds mathematically-grounded micro-intelligence: tiny models (737-100K params) that know their limits, escalate when they should, and progressively tile their own knowledge gaps — eliminating the false choice between expensive LLM inference and dumb hardcoded rules.

---

## 2. Current State (Honest Assessment)

### What Exists Today

| Category | Count | Details |
|----------|-------|---------|
| GitHub repos | 80+ | Across SuperInstance org + cocapn namespace |
| Published packages | 6 | 2 on crates.io, 4 on PyPI |
| Total tests | 655+ | Across 30+ repos |
| Languages | 6 | Rust, Python, JS/TS, C, Fortran, Mojo |
| Code volume | 200K+ lines | Excluding tests and docs |
| Hardware targets | 8 | CPU, GPU, NPU, TPU, WASM, embedded (ESP32, RP2040, ARM) |

**Published packages (installable right now):**
- `constraint-theory-core` 2.0.0 (Rust/crates.io) — Eisenstein integers, zero-drift
- `spectral-conservation` 0.1.0 (Rust/crates.io) — Conservation law tracker
- `constraint-theory` 0.2.0 (Python/PyPI) — Bindings
- `plato-model-ocean` 0.1.0 (Python/PyPI) — Evolving model ecosystem
- `plato-escalation-gate` 0.1.0 (Python/PyPI) — LLM escalation classifier (737 params, 4KB)
- `plato-room-intelligence` 0.1.0 (Python/PyPI) — Multi-head room model with provenance

### What Works Well

1. **The math stack is solid.** Eisenstein integers expanded to a 9-repo ecosystem spanning microcontrollers to formal verification (DO-178C). Zero dependencies, `no_std`, runs on anything.
2. **The PLATO ML stack is coherent.** Four independently-installable packages form a real pipeline: types → data → training → intelligence. 116 tests in plato-training alone. Honest performance tables (they show the bad numbers too).
3. **SplineLinear compression is novel and proven.** 20x parameter reduction at same accuracy on drift-detect. This is publishable.
4. **The escalation gate concept is sharp.** 737 parameters, 4KB, decides when to call an LLM. Runs on WASM. This is the clearest product in the portfolio.
5. **Zero-shot beta test passes.** 10/12 repos are navigable by an agent with zero prior context. Install commands work. Code examples run.

### What's Broken or Missing

1. **The Spreader-Tool doesn't exist yet.** The central novel contribution (intelligence tiling) is fully designed but has zero implementation.
2. **No production deployment.** All validation is synthetic. No external users running any package in production.
3. **Web presence has dead links.** `crab-trap.lucineer.com` returns 404 and is referenced on the two most visible pages.
4. **Demo pages are 404.** `narrows.html` and `eisenstein-playground.html` don't exist.
5. **`fleet.cocapn.ai` is unverifiable.** May require JS/auth; can't confirm it works.
6. **Org-level GETTING-STARTED.md is a 404.** The forgemaster version works, but the org-level link doesn't resolve.

### Credibility Gaps (from Audits)

| Gap | Severity | Days Open |
|-----|----------|-----------|
| `fleet-spread` claims 147 tests, actually has ~46 | HIGH | 10+ days |
| `constraint-theory-ecosystem` claims "47 implementations, 62B checks/sec, 15 Coq theorems" — numbers appear inflated | HIGH | 10+ days |
| `quality-gate-stream` is a workspace dump, not a focused package | MEDIUM | 10+ days |
| Keel command count inconsistency (9 vs 16) | LOW | Active |

**The pattern:** Technical quality is high but marketing claims outrun verification. Every inflated number a PhD reviewer or CTO finds reduces trust across the entire portfolio.

---

## 3. Three-Year Horizon

### Year 1: Foundation (2026-2027)

**Milestone:** Ship the Spreader-Tool MVP, get 3 external adopters using published packages, submit spectral conservation paper.

- Spreader-Tool implemented and tested in single-room configuration
- Spectral conservation paper submitted to NeurIPS/ICML
- 3 external projects using `plato-escalation-gate` or `plato-model-ocean` in production
- All credibility gaps closed (no inflated claims anywhere)
- Interactive demos live on the web

### Year 2: Scale (2027-2028)

**Milestone:** Multi-room Spreader-Tool deployed to real fleet, 2nd paper (intelligence tiling), 50+ stars on core repos.

- Full Spreader-Tool with Murmur gossip, fleet-wide seed propagation
- Intelligence tiling paper (the novel contribution) submitted
- Model Ocean validated on real workloads (not synthetic data)
- SDK/CLI that lets anyone spin up a PLATO room in 5 minutes
- Community contributions beyond Casey's fleet

### Year 3: Impact (2028-2029)

**Milestone:** Spreader-Tool adopted by at least one external team for edge AI, spectral conservation referenced in other papers.

- Spreader-Tool running in production edge deployments (IoT, robotics, or warehouse)
- Patent or defensive publication on progressive intelligence tiling
- Eisenstein integer arithmetic adopted in at least one external embedded project
- Conference talk or workshop presentation

---

## 4. Six-Month Roadmap

### Q3 2026 (June - August): Foundation Quarter

**Spreader-Tool:**
- [ ] Phase 1 MVP complete: `types.py`, `deadband.py`, `frozen_context.py`, `store.py`, `backtest.py`, `seed_lock.py`, `cost.py`, `redaction.py`, `spreader_room.py`, `cli.py`
- [ ] ~2,000 lines implementation + ~1,500 lines tests
- [ ] Single-room proof-of-concept running on synthetic data
- [ ] Internal demo: one PLATO room detecting deadband and locking seeds

**PLATO Stack:**
- [ ] Close all credibility gaps (fleet-spread test count, ecosystem claims)
- [ ] Publish plato-training benchmarks on real hardware (not just fleet-internal)
- [ ] Model Ocean: at least one non-synthetic validation scenario

**Publication:**
- [ ] Spectral conservation paper: finalize falsification methodology, submit draft
- [ ] SplineLinear compression: write up 20x result as technical report

**DX:**
- [ ] Fix all dead links (crab-trap, demos)
- [ ] Org-level GETTING-STARTED.md resolves
- [ ] Pin repos on GitHub org page
- [ ] All repos have GitHub descriptions

### Q4 2026 (September - November): Integration Quarter

**Spreader-Tool:**
- [ ] Phase 2 begins: Murmur integration, full seed state machine, DAG orchestration
- [ ] Multi-room coordination: 2-4 rooms sharing frozen windows
- [ ] Escalation gate wired to real LLM endpoint
- [ ] Protobuf serialization for FCWs

**PLATO Stack:**
- [ ] tensor-spline: compress Spreader seed weights with SplineLinear
- [ ] plato-model-ocean: integrate with Spreader (Model Ocean receives irreducible deadband)
- [ ] plato-escalation-gate: wire into Spreader's escalation step

**Publication:**
- [ ] Spectral conservation: respond to reviews / camera-ready
- [ ] Intelligence tiling: outline paper (the genuinely novel contribution)
- [ ] Blog post series: "What is a deadband?" (accessible version)

**Ecosystem:**
- [ ] First external user running a published package (track via GitHub issues/stars)
- [ ] Interactive Eisenstein playground deployed
- [ ] Documentation site with search

---

## 5. The Architecture (10,000 feet)

```
┌────────────────────────────────────────────────────────────────────────┐
│                          APPLICATIONS                                   │
│   platoclaw · plato-mcp · cocapn-cli · plato-shell-bridge              │
├────────────────────────────────────────────────────────────────────────┤
│                     SPREADER-TOOL (NEW)                                 │
│   deadband detection → frozen context windows → seed locking           │
│   intelligence tiling → refinement/redaction → fleet propagation       │
├────────────────────────────────────────────────────────────────────────┤
│                       INTELLIGENCE                                      │
│   plato-model-ocean (evolve) · escalation-gate (route)                 │
│   room-intelligence (multi-head) · plato-training (train+deploy)       │
├────────────────────────────────────────────────────────────────────────┤
│                        RUNTIME                                          │
│   flux-vm · flux-lucid · plato-engine · plato-vessel-core              │
├────────────────────────────────────────────────────────────────────────┤
│                       CONSTRAINTS                                       │
│   spectral-conservation · eisenstein · dodecet-encoder                  │
│   constraint-theory-core · penrose-memory · guardc                     │
├────────────────────────────────────────────────────────────────────────┤
│                         DATA                                            │
│   plato-types · plato-data · tensor-spline · flux-provenance           │
├────────────────────────────────────────────────────────────────────────┤
│                      INFRASTRUCTURE                                     │
│   fleet-murmur (gossip) · fleet-router · fleet-health-monitor          │
│   plato-hardware-engine · fleet-calibrator                             │
└────────────────────────────────────────────────────────────────────────┘
```

### Data Flow (Spreader-Tool in Context)

```
Room State (sensors, KPIs)
    │
    ▼
[Sliding Window Aggregation] ← plato-data
    │
    ▼
[Deadband Detection] ← spectral-conservation (eigenvalue drift)
    │
    ├── NOT in deadband → [Local Inference] ← locked seed (tensor-spline compressed)
    │
    └── IN deadband ──┐
                      ▼
            [Freeze Context Window] → stored as FCW tile (plato-types)
                      │
                      ▼
            [Escalation Check] ← plato-escalation-gate (737 params)
                      │
                      ├── Escalate → LLM → response fed back to Model Ocean
                      │
                      └── Don't escalate → [Refine locally]
                                              │
                                              ▼
                                    [Seed Candidate] → [Backtest] → [Lock]
                                              │
                                              ▼
                                    [Murmur Gossip] → propagate to fleet
```

### Where Spreader-Tool Fits

The Spreader-Tool is the **middle layer** — it sits between the intelligence layer (which provides the models) and the runtime layer (which runs them). Its job is to decide:
1. When the system doesn't know enough (deadband detection)
2. What to remember (frozen context windows)
3. When a solution is proven good (seed locking)
4. What's not worth remembering (redaction)
5. Who else needs to know (fleet propagation)

---

## 6. The Research Agenda

### Publishable Contributions

| Contribution | Novelty Level | Status | Target Venue |
|-------------|---------------|--------|--------------|
| **Spectral conservation in coupled nonlinear systems** | Moderate (novel monitoring method) | Paper draft complete (5,130 words), 20 cycles of adversarial falsification, regime classification table | NeurIPS/ICML 2026 |
| **Progressive intelligence tiling (Spreader-Tool)** | High (no prior art for this exact approach) | Full design, no implementation | AAAI/NeurIPS 2027 |
| **SplineLinear compression (20x at same accuracy)** | Moderate (novel parameterization) | Implemented, validated on 6 hardware targets | Technical report → workshop paper |
| **Eisenstein integers for embedded ML** | Low-moderate (novel application) | 9-repo ecosystem, no_std, DO-178C path | Embedded systems conference |
| **Model Ocean (evolutionary micro-intelligence)** | Moderate (novel ecosystem framing) | Implemented, synthetic-only validation | GECCO or similar |

### What's Genuinely Novel (per Hermes-70B analysis)

1. **Progressive intelligence tiling** — vs monolithic model training. The idea that you can tile a knowledge gap incrementally, with frozen snapshots, rather than retraining a whole model.
2. **Frozen context windows** — vs continuous streaming. Discrete, immutable snapshots of reasoning state as the unit of intelligence.
3. **Model Ocean ecosystem** — vs static federated learning. An evolving population of models with ecological niches.
4. **Seed-locking + parallel-sequential mixing** — vs single-model deployment. Formal validation before deployment, with explicit state machines.

### What Needs Proof

| Claim | Current Evidence | What's Needed |
|-------|-----------------|---------------|
| SplineLinear 20x compression at same accuracy | Validated on drift-detect (100%) | Validate on all 8 tasks, compare to SOTA compression |
| Spectral invariant I(x) = gamma + H holds across regimes | 20 falsification cycles, CV < 0.03 | External replication, larger-scale systems |
| Deadband converges monotonically when G(i) > 0 | Theoretical proof | Empirical validation on real workloads |
| Model Ocean outperforms single model | Synthetic validation only | Real-world benchmark comparison |
| Escalation gate saves cost vs always-escalate | Architecture argument only | A/B test on real system |

---

## 7. The Developer Experience (DX) Roadmap

### Immediate Fixes (This Week)

| Fix | Effort | Impact |
|-----|--------|--------|
| Fix `fleet-spread` test count (run tests, count, update README) | 10 min | Removes #1 credibility killer |
| Audit `constraint-theory-ecosystem` numbers (count dirs, verify claims) | 30 min | Removes #2 credibility killer |
| Remove or fix `crab-trap.lucineer.com` link on org README + PLATO landing | 5 min | Removes dead-link first impression |
| Make org-level GETTING-STARTED.md resolve (redirect or create in .github) | 15 min | Fixes 404 in onboarding flow |
| Sync Keel command count (9 vs 16 — pick one) | 5 min | Removes inconsistency |

### Short-Term Improvements (This Month)

| Fix | Effort | Impact |
|-----|--------|--------|
| Pin 4 repos on org page (eisenstein, spectral-conservation, plato-training, constraint-theory-core) | 5 min | Guides newcomers to strongest work |
| Add GitHub descriptions to all 80+ repos | 2 hours | Discoverability via search |
| Deploy interactive Eisenstein playground | 1-2 days | Live demo for math-path newcomers |
| Create ASSEMBLY-GUIDE.md in public .github repo | 10 min | Architecture understanding without cloning forgemaster |
| Archive or clean up quality-gate-stream | 1 hour | Remove workspace dump from public view |

### Medium-Term DX Goals (This Quarter)

| Goal | Effort | Impact |
|------|--------|--------|
| Documentation site with search (all 6 published packages) | 1 week | Professional presentation |
| `plato-spread` CLI installable via pip | 2 weeks | Spreader-Tool accessible without cloning |
| CI badges on all published package repos | 1 day | Trust signal for outsiders |
| Contribution guide with "good first issue" labels | 2 days | Enable external contributors |
| Blog post: "What SuperInstance Builds" (non-technical) | 1 day | SEO, social sharing |

---

## 8. Agent Architecture Schemas

### GLM-5.1 Subagent (Coding Agent — Cheap, Fast)

**Use for:** Implementing individual modules from spec. One file at a time.

```json
{
  "agent": "glm-5.1",
  "role": "implementer",
  "constraints": {
    "language": "python 3.10+",
    "typing": "all functions type-hinted",
    "data_structures": "dataclasses only",
    "async": "asyncio for all I/O",
    "testing": "pytest, one test file per module",
    "deps_allowed": ["torch (backtest/seed_lock only)", "uuid", "datetime", "dataclasses", "typing", "pathlib"],
    "deps_forbidden": ["external ML in types/deadband/store", "requests", "flask", "django"]
  },
  "task_template": {
    "input": "module spec (interfaces, types, behavior)",
    "output": "implementation file + test file",
    "max_scope": "single module (< 300 lines)",
    "must_pass": "all tests green, mypy clean, no import cycles"
  },
  "example_tasks": [
    "Implement spreader/types.py from FCW and Seed dataclass specs",
    "Implement spreader/deadband.py: DeadbandDetector class with configurable thresholds",
    "Implement spreader/store.py: content-addressed filesystem storage for FCW/Seed"
  ]
}
```

### CRUSH Review Agent (Validation — Medium Cost)

**Use for:** Code review of implemented modules. Catches state machine bugs, immutability violations, cost tracking gaps.

```json
{
  "agent": "crush",
  "role": "reviewer",
  "validation_checklist": [
    "State machine guards: every SeedState transition has explicit guard clause",
    "Immutability: FCWs never modified after FROZEN status (no setattr on frozen fields)",
    "Cost tracking: every intelligence operation logs to NTIC (no silent compute)",
    "Backtest coverage: seeds must pass performance + runtime + dataset validation",
    "Redaction compliance: no raw data retained for high-compliance windows",
    "No circular imports between spreader modules",
    "All public functions have type hints",
    "Test coverage > 80% per module",
    "No hardcoded magic numbers (use constants from types.py)"
  ],
  "rejection_criteria": [
    "Any state transition without guard clause",
    "Mutable field access on frozen FCW",
    "Missing NTIC logging on compute path",
    "Seed locked without passing all three backtest categories"
  ],
  "output": "pass/fail + specific line-level feedback"
}
```

### Seed-2.0-mini (Architecture Agent — Cheap, Systematic)

**Use for:** Generating specs, formalizing protocols, producing pseudocode for handoff to coding agents.

```json
{
  "agent": "seed-2.0-mini",
  "role": "architect",
  "strength": "systematic formalization, complete specs",
  "weakness": "over-engineers — output must be filtered by human or Qwen",
  "task_template": {
    "input": "concept description + constraints + existing code patterns",
    "output": "formal spec: data structures, state machines, pseudocode, interface definitions",
    "review_by": "qwen (simplification pass) then human (approval)"
  },
  "example_tasks": [
    "Design protobuf schema for fleet-wide FCW sync via Murmur",
    "Formalize conflict resolution protocol for multi-room seed merges",
    "Produce state machine spec for adaptive sampling frequency"
  ]
}
```

### Claude Opus (Synthesis Agent — Expensive, Deep)

**Use for:** High-level synthesis, cross-cutting decisions, paper writing, roadmap updates.

```json
{
  "agent": "claude-opus",
  "role": "synthesizer",
  "when_to_use": [
    "Synthesizing inputs from multiple agents/sources",
    "Making architectural decisions that affect 3+ modules",
    "Writing research paper sections",
    "Evaluating whether a contribution is genuinely novel",
    "Resolving disagreements between other agents",
    "Updating this roadmap"
  ],
  "when_not_to_use": [
    "Implementing a single module (use GLM-5.1)",
    "Reviewing code (use CRUSH)",
    "Generating specs (use Seed-2.0-mini)",
    "Iterating on a single file (use any cheap model)"
  ],
  "cost_guard": "invoke only when 3+ modules affected or cross-cutting decision required"
}
```

---

## 9. Component Dependency Graph

### Critical Path (Spreader-Tool MVP)

```
[plato-types] ─────────────────────────────────────────────┐
     │                                                      │
     ▼                                                      ▼
[spreader/types.py] ──┬──────────────────────────────── [spreader/store.py]
     │                │                                     │
     ▼                ▼                                     ▼
[spreader/deadband.py] [spreader/frozen_context.py]    [spreader/backtest.py]
     │                │                                     │
     │                │                     ┌───────────────┘
     │                │                     ▼
     │                │              [spreader/seed_lock.py]
     │                │                     │
     ▼                ▼                     ▼
[spreader/cost.py] ──→ [spreader/redaction.py]
     │                │                     │
     └────────────────┴─────────────────────┘
                      │
                      ▼
           [spreader/spreader_room.py] ← wires everything into 8-step loop
                      │
                      ▼
              [spreader/cli.py]
```

### Cross-Package Dependencies (for Spreader Phase 2+)

```
spreader/spreader_room.py
    ├── imports plato-types (TileLifecycle, LamportClock)
    ├── imports plato-data (load historical FCWs for backtesting)
    ├── imports tensor-spline (SplineLinear for seed weight compression)
    ├── imports plato-escalation-gate (the 737-param gate)
    ├── imports plato-model-ocean (irreducible deadband → ocean)
    └── imports spectral-conservation (eigenvalue drift detection)
```

### What Must Be Built Before What

| Must Exist First | Before Building | Reason |
|-----------------|-----------------|--------|
| `spreader/types.py` | Everything else in spreader/ | All modules import types |
| `spreader/store.py` | backtest, redaction | Need storage to validate against |
| `spreader/deadband.py` | spreader_room.py | Room needs to detect deadband |
| `spreader/frozen_context.py` | backtest, seed_lock | Seeds are built from FCWs |
| `spreader/backtest.py` | seed_lock | Can't lock without validation |
| `spreader/cost.py` | redaction | Redaction uses NTIC scores |
| All of the above | `spreader/spreader_room.py` | Room integrates everything |
| `spreader/spreader_room.py` | `spreader/cli.py` | CLI wraps the room |

---

## 10. Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| 1 | **No external adopters** — packages remain Casey-only | HIGH | HIGH | Target 3 specific external projects by Q4 2026. Write "Why use this" sections. Submit to Awesome lists. Present at meetups. |
| 2 | **Credibility erosion from inflated claims** — PhD reviewers find fleet-spread's 147-test claim, dismiss everything | HIGH | HIGH | Fix TODAY. Run every test count, verify every benchmark, remove every claim that can't be reproduced by a stranger. |
| 3 | **Spreader-Tool never ships** — stays in design documents forever | MEDIUM | HIGH | Strict 2-week MVP deadline. Build Qwen's simple version first. Ship working code before adding complexity. |
| 4 | **Spectral conservation paper rejected** — theoretical contribution not accepted | MEDIUM | MEDIUM | Have fallback venue (workshop paper, arxiv). Strengthen empirical section with larger-scale experiments. |
| 5 | **Scope creep** — 80+ repos grow to 120+ without any reaching maturity | HIGH | MEDIUM | Freeze new repo creation. Focus on shipping 6 published packages to 1.0. Archive anything that's a workspace dump. |
| 6 | **Bus factor = 1** — Casey is the only contributor | HIGH | HIGH | Comprehensive docs. Automated CI. GETTING-STARTED.md that actually works. Court 2-3 contributors via good-first-issues. |
| 7 | **Gossip poisoning in fleet sync** — malicious FCWs propagated via Murmur | LOW | HIGH | Cryptographic signing of FCWs, quorum-based validation (Phase 2). Not a risk for single-room MVP. |
| 8 | **Storage blowup from FCWs** — frozen windows accumulate faster than pruned | MEDIUM | MEDIUM | Aggressive deduplication, tiered compression, retention limits baked into MVP redaction protocol. |
| 9 | **Model drift makes locked seeds stale** — distribution shifts faster than re-validation | MEDIUM | MEDIUM | Periodic re-validation (spectral monitoring), deprecation workflow, 7-day lock threshold is tunable. |
| 10 | **Dead web presence damages trust** — crab-trap 404, demo 404s suggest abandoned project | HIGH | MEDIUM | Fix all dead links this week. Set up uptime monitoring. Don't link to things that don't exist yet. |

---

## 11. The Build Order (Next 30 Days)

### Week 1: Credibility + Foundation

**Day 1-2: Kill credibility gaps**
- [ ] `fleet-spread`: run `cargo test`, count actual tests, update README
- [ ] `constraint-theory-ecosystem`: count directories, verify Coq theorems, correct numbers
- [ ] Remove `crab-trap.lucineer.com` from org README and PLATO landing (or redeploy)
- [ ] Fix org-level GETTING-STARTED.md (create in .github or redirect)
- [ ] Remove demo links that 404

**Day 3-4: Spreader types and deadband**
- [ ] Create `spreader/` directory in appropriate repo (likely plato-training or new spreader-tool repo)
- [ ] Implement `spreader/__init__.py`
- [ ] Implement `spreader/types.py` (~200 lines): FCW dataclass, Seed dataclass, SeedState enum, FCWStatus enum, TriggerType enum, RoomType enum
- [ ] Write `tests/test_types.py` (~100 lines)
- [ ] Implement `spreader/deadband.py` (~100 lines): DeadbandDetector class with configurable thresholds
- [ ] Write `tests/test_deadband.py` (~80 lines)

**Day 5: Frozen context + store**
- [ ] Implement `spreader/frozen_context.py` (~250 lines): FCW lifecycle manager
- [ ] Write `tests/test_frozen_context.py` (~120 lines)
- [ ] Implement `spreader/store.py` (~150 lines): content-addressed filesystem storage
- [ ] Write `tests/test_store.py` (~100 lines)

### Week 2: Seed Locking + Cost

**Day 6-7: Backtest and seed lock**
- [ ] Implement `spreader/backtest.py` (~200 lines): validate candidate seeds
- [ ] Write `tests/test_backtest.py` (~120 lines)
- [ ] Implement `spreader/seed_lock.py` (~150 lines): simplified 3-state machine (UNLOCKED → CANDIDATE → LOCKED)
- [ ] Write `tests/test_seed_lock.py` (~100 lines)

**Day 8-9: Cost and redaction**
- [ ] Implement `spreader/cost.py` (~100 lines): NTIC calculation, refinement gradient G(i)
- [ ] Write `tests/test_cost.py` (~80 lines)
- [ ] Implement `spreader/redaction.py` (~200 lines): tiered pruning with coverage guarantees
- [ ] Write `tests/test_redaction.py` (~100 lines)

**Day 10: Integration**
- [ ] Implement `spreader/spreader_room.py` (~300 lines): 8-step loop mixin
- [ ] Write `tests/test_spreader_room.py` (~150 lines): integration test
- [ ] All tests passing, no import cycles, mypy clean

### Week 3: CLI + DX

**Day 11-12: CLI and packaging**
- [ ] Implement `spreader/cli.py` (~200 lines): deadband-status, freeze, list-fcws, seed-candidates, lock-seed, backtest, redact
- [ ] Write `tests/test_cli.py` (~100 lines)
- [ ] Create `pyproject.toml` / `setup.py` for pip-installable package
- [ ] Verify: `pip install -e .` works, `plato-spread --help` works

**Day 13-14: Documentation**
- [ ] Write README.md for spreader-tool repo (install, quickstart, architecture diagram)
- [ ] Update ECOSYSTEM-MAP.md with Spreader-Tool layer
- [ ] Update GETTING-STARTED.md to mention Spreader-Tool under "Full Ecosystem" path
- [ ] Pin spreader-tool repo on org page

**Day 15: DX improvements**
- [ ] Add GitHub descriptions to all repos missing them
- [ ] Pin repos on org page (eisenstein, spectral-conservation, plato-training, spreader-tool)
- [ ] Deploy Eisenstein playground (if ready) or create stub page explaining "coming soon"

### Week 4: Validation + Publication Prep

**Day 16-18: End-to-end validation**
- [ ] Run Spreader-Tool on one of plato-training's 8 tasks (drift-detect recommended)
- [ ] Generate synthetic deadband scenarios, verify FCW creation + seed locking
- [ ] Measure: how many ticks to first locked seed? How much deadband reduction?
- [ ] Document results honestly (including what didn't work)

**Day 19-20: Spectral conservation paper prep**
- [ ] Finalize falsification methodology section
- [ ] Add larger-scale experiments (if compute available)
- [ ] Internal review pass
- [ ] Prepare submission package

**Day 21: Zero-shot re-test**
- [ ] Run zero-shot beta test again on all repos + new spreader-tool
- [ ] Fix anything that fails
- [ ] Update BETA-TEST-ZERO-SHOT.md with results

---

## Summary

The SuperInstance/Cocapn ecosystem has genuine technical depth: zero-drift arithmetic, 20x compression, 737-parameter escalation gates, and a fully-designed intelligence tiling mechanism. The math is real. The code works. The architecture is coherent.

What's missing is execution: the Spreader-Tool needs to be built, inflated claims need to be corrected, dead links need to be fixed, and external users need to be acquired. The next 30 days are about closing the gap between what's designed and what's deployed.

**Build Qwen's simple version first. Then add Seed's complexity. Then write Hermes's papers.**

---

*This roadmap will be updated monthly. Next review: 2026-06-17.*
