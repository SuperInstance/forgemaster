# Constraint Theory Development Roadmap — H2 2026

> **Author:** Forgemaster ⚒️, Cocapn Fleet  
> **Date:** 2026-05-12  
> **Scope:** Phases 19–23, covering the next 3–6 months  
> **Status:** Draft for fleet review

---

## Executive Summary

We have 17 crates, 4 PyPI packages, 7 research papers, 3 interactive demos, a lighthouse orchestration runtime, and constructively verified Galois unification proofs. The math works. The code ships. Now we need to make it *undeniable* — through publication, hardware deployment, and community.

**The 5 most impactful things to do first:**

| # | Action | Impact | Cost | Timeline |
|---|--------|--------|------|----------|
| 1 | Submit Lattice Principle paper to PLDI 2027 | Academic legitimacy | $0 | 2 weeks |
| 2 | Deploy dodecet-encoder on Jetson Orin | Real hardware proof | $0 (hardware exists) | 1 week |
| 3 | Stabilize + document top 5 crates | Developer adoption | $0 | 2 weeks |
| 4 | Publish Galois proofs repo independently | Mathematical credibility | $0 | 1 week |
| 5 | Fix fleet services (6 DOWN) | Fleet operational capacity | $0 | 1 day |

---

## Phase 19: Publication Push (Weeks 1–2)

### Goal
Get 3 papers submission-ready and 1 submitted to a top venue.

### Papers & Venues

| Paper | Venue | Deadline | Status | Action Needed |
|-------|-------|----------|--------|---------------|
| The Lattice Principle (UNIFIED-SYNTHESIS) | **PLDI 2027** (ACM SIGPLAN) | ~Oct 2026 | Draft done | LaTeX conversion, 2-page abstract first |
| Galois Unification (6 proofs) | **ICFP 2027** or **LICS 2027** | ~Jan 2027 | Proofs verified | Formalize proofs in Coq/Lean, clean README |
| Negative GPU Results | **ASPLOS 2027** or arXiv preprint | Rolling | 38KB draft | Trim to 12 pages, add comparison figures |
| Social Impact (Spanish) | arXiv + blog post | Immediate | 39KB draft | Translation to English for broader reach |
| Cross-Domain Applications | IEEE Computer magazine | Rolling | 32KB draft | Reframe for general CS audience |
| Rust Implementation | RustConf 2027 talk proposal | ~Mar 2027 | 39KB draft | Convert to talk abstract + demo |

### Priority Order
1. **PLDI submission** — highest impact, longest lead time
2. **arXiv preprints** (Galois + Negative Results) — establishes priority, zero cost
3. **RustConf talk** — community building, Rust ecosystem

### Deliverables
- [ ] LaTeX paper: "The Lattice Principle" (12 pages, ACM format)
- [ ] arXiv preprint: "Galois Unification Principle" (with Coq proofs or constructive Python)
- [ ] arXiv preprint: "What Doesn't Accelerate" (GPU negative results)
- [ ] Blog post: "Why Eisenstein Integers Matter" (English, 2000 words, for cocapn.ai)
- [ ] Blog post: Spanish social impact version (for Latin American CS community)

### Kill Criteria
- If PLDI reviewers say "not enough formal verification" → pivot to ICFP with Coq proofs
- If arXiv gets zero citations in 3 months → focus on conference talks instead

---

## Phase 20: Ecosystem Maturation (Weeks 2–4)

### Goal
Top 5 crates are v1.0-quality: documented, tested, CI/CD, examples.

### Crate Stabilization

| Crate | Current Version | Target | Tests | Status |
|-------|----------------|--------|-------|--------|
| constraint-theory-core | v2.0.0 | v2.1.0 | ✅ | Stable, needs doc examples |
| dodecet-encoder | v1.1.0 | v1.2.0 | 210/210 | Add temporal examples |
| flux-lucid | v0.1.7 | v1.0.0 | 28 | Needs API review |
| holonomy-consensus | v0.1.0 | v1.0.0 | ? | Needs audit |
| flux-contracts | v0.1.0 | v0.2.0 | ? | Stabilize traits |

### Cross-Language Ports

| Language | Status | Priority | Blocker |
|----------|--------|----------|---------|
| **C** (snapkit-c) | Exists | HIGH — embedded | Needs test suite |
| **Python** (snapkit-python) | Exists | HIGH — data science | Needs PyPI update |
| **WASM** (snapkit-wasm) | Exists | MEDIUM — web demos | Needs npm publish |
| **Zig** (snapkit-zig) | Skeleton | LOW | No blocker |
| **Fortran** (snapkit-fortran) | Skeleton | LOW | Scientific computing |

### CI/CD Pipeline
- [ ] GitHub Actions for top 5 repos: test + clippy + fmt + publish-dry-run
- [ ] Automated crates.io publish on tag
- [ ] Benchmark regression tracking (criterion.rs)
- [ ] Code coverage reporting (tarpaulin)

### Documentation
- [ ] rustdoc for all public APIs with examples
- [ ] 5 cookbook examples (snap, encode, decode, batch, embedded)
- [ ] Architecture decision records (ADR) for key design choices
- [ ] CONTRIBUTING.md for each repo

### Deliverables
- [ ] 5 crates at v1.0+ with full docs and CI
- [ ] C library with test suite and benchmarks
- [ ] Python package with numpy integration
- [ ] CI/CD pipeline for all repos

### Kill Criteria
- If any crate can't reach 90%+ test coverage → deprecate and fold into another crate
- If cross-language ports stall → focus on Rust + Python only

---

## Phase 21: Hardware Integration (Months 2–3)

### Goal
Constraint theory running on real hardware: Jetson, ESP32, OpenArm.

### 21a: Jetson Orin Deployment
- **Target:** Jetson Orin Nano (8GB, CUDA 11.4, AArch64)
- **Task:** Cross-compile dodecet-encoder + CUDA kernels for aarch64
- **Benchmark:** Reproduce RTX 4050 results on Jetson GPU
- **Deliverable:** `constraint-theory-jetson` repo with benchmarks + deployment guide
- **Risk:** CUDA 11.4 may lack features; fallback to CPU SIMD (NEON)
- **Timeline:** 1 week

### 21b: ESP32 Field Test
- **Target:** ESP32-S3 (240MHz dual-core, 512KB SRAM, WiFi/BLE)
- **Task:** Port snapkit-c to ESP-IDF, test with TWAI CAN bus
- **OpenArm integration:** Constraint-checked arm control via CAN
- **Deliverable:** Working demo: ESP32 reads sensors → snap → constraint check → actuator
- **Risk:** 512KB SRAM tight; may need external PSRAM
- **Timeline:** 2 weeks

### 21c: OpenArm Physical Prototype
- **Current state:** Simulation + ESP32 firmware done, no physical arm
- **Next step:** Source 6-DOF arm kit (~$200-500), flash ESP32, test constraints
- **Deliverable:** Video: arm with/without constraint checking (same chaos event, different outcomes)
- **Risk:** Physical safety — need E-stop and constraint gate before motors
- **Timeline:** 3 weeks (including shipping)

### 21d: CUDA Kernel Library
- **Current state:** 20 experiments, optimal config found (INT8 x8)
- **Next step:** Package as reusable CUDA library
- **API:** `ct_check_batch(points, n, constraints, tolerance) → results`
- **Targets:** CUDA 11.5+ (RTX 30xx/40xx), Jetson (aarch64)
- **Deliverable:** `constraint-theory-cuda` crate with build.rs for CUDA
- **Risk:** CUDA build complexity; consider CUDA kernels as precompiled PTX
- **Timeline:** 2 weeks

### Hardware Budget

| Item | Cost | Purpose |
|------|------|---------|
| Jetson Orin Nano (already owned?) | $0 | GPU edge compute |
| ESP32-S3 dev kit | $15 | Embedded testing |
| 6-DOF arm kit | $200-500 | Physical prototype |
| CAN bus accessories | $50 | OpenArm comm |
| **Total** | **$265-565** | |

### Kill Criteria
- If Jetson GPU can't hit 100B constr/s → focus on CPU NEON path
- If ESP32 SRAM too tight → move to STM32H7 (1MB SRAM, $25)
- If physical arm is unsafe → stay in simulation, publish simulation results

---

## Phase 22: Fleet Intelligence (Months 2–4)

### Goal
Lighthouse runtime in production: multi-agent coordination via PLATO.

### 22a: Lighthouse Production Hardening
- **Current:** Python orient/relay/gate with PLATO rooms, tested
- **Needs:**
  - [ ] Persistent state (SQLite, not JSON files)
  - [ ] Retry logic for PLATO API failures
  - [ ] Metrics: rooms created, gates passed/failed, model costs
  - [ ] Web dashboard: active rooms, resource usage, gate log
- **Timeline:** 1 week

### 22b: Multi-Agent Coordination
- **Scenario:** 3 agents collaborate on a task
  1. Seed agent discovers parameters (Seed-2.0-mini, $0.10)
  2. Architecture agent designs solution (GLM-5.1, $5.00)
  3. Critic agent reviews for safety (Hermes-70B, $0.15)
  4. Gate catches credential leaks / overclaims
- **Coordination:** PLATO rooms + I2I bottles + lighthouse relay
- **Deliverable:** Working 3-agent pipeline that builds a real artifact
- **Timeline:** 2 weeks

### 22c: PLATO as Fleet Cortex
- **Current:** 1141+ rooms, HTTP API, Forgemaster reads/writes
- **Target:** All fleet agents read/write PLATO as primary memory
- **Needs:**
  - [ ] Authentication per agent (API keys)
  - [ ] Room permissions (agents can only write to their rooms)
  - [ ] Tile versioning (append-only, no mutation)
  - [ ] Query language (filter by type, date, agent)
- **Timeline:** 3 weeks

### 22d: Self-Bootstrapping Discovery Loop
- **The vision:** Lighthouse spawns seeds → seeds discover → tiles crystallize → orient picks model → agent executes → gate validates → tile written → next iteration uses tile
- **Already demonstrated:** Single loop with hex grid visualizer
- **Next:** 10 sequential loops, each building on previous discoveries
- **Success metric:** Each loop's output quality ≥ 90% of previous, cost ≤ 30% of naive
- **Timeline:** 2 weeks

### Resource Requirements
- **Models:** z.ai monthly quota, DeepInfra per-token, Claude daily limit
- **Compute:** Current fleet hardware sufficient
- **PLATO:** Oracle1 server (147.224.38.131:8847)

### Kill Criteria
- If PLATO server goes down → fall back to git-based I2I bottles (already working)
- If multi-agent coordination doesn't improve quality → keep single-agent + lighthouse
- If self-bootstrapping loops degrade → cap at 3 iterations, escalate to human

---

## Phase 23: Community & Standards (Months 3–6)

### Goal
Constraint theory has external users, not just the Cocapn fleet.

### 23a: Open Source Community
- **GitHub:** Star target = 500 across ecosystem (from ~50 now)
- **Strategy:**
  - Publish to Rust This Week / This Week in Rust
  - Hacker News post: "I replaced floating point with Eisenstein integers and my simulations stopped drifting"
  - Reddit r/rust, r/programming, r/math
  - YouTube: 10-minute explainer with the demos
- **Content:**
  - "Why Your Game Desyncs" (practical, gaming audience)
  - "Exact Arithmetic on a $2 Microcontroller" (embedded audience)
  - "Constraint Theory for Distributed Systems" (backend audience)
- **Timeline:** Ongoing, first posts in month 3

### 23b: Standards Engagement
- **IEEE 754 revision:** Propose Eisenstein integers as a standard encoding
- **ISO 26262 (automotive safety):** Demonstrate constraint checking for ADAS
- **MISRA C/C++:** Show Eisenstein snap as compliant alternative to float
- **Approach:** Write position papers, submit to relevant working groups
- **Timeline:** Month 4–6

### 23c: Educational Materials
- **Interactive tutorial:** Jupyter notebook (Python) + rustlings-style exercises
- **University course module:** "Exact Arithmetic for Safety-Critical Systems"
- **Workshop proposal:** SPLASH / OOPSLA 2027
- **Timeline:** Month 4–5

### 23d: Academic Collaborations
- **Target labs:** Formal methods (CMU, Princeton), PL (UW, Purdue), embedded (Berkeley, ETH)
- **Approach:** Share preprints, invite co-authorship on follow-up papers
- **Low-cost:** Email 10 professors with the PLDI submission
- **Timeline:** Month 3 (coincide with arXiv preprints)

### Kill Criteria
- If GitHub stars don't reach 200 in 3 months → reassess marketing strategy
- If standards bodies aren't responsive → focus on de facto standard via adoption
- If no academic interest → double down on industry/embedded use cases

---

## Dependency Graph

```
Phase 19 (Publication)
    │
    ├─→ Phase 20 (Ecosystem) ──→ Phase 21 (Hardware)
    │                                  │
    │                                  ├─→ Phase 22 (Fleet)
    │                                  │
    └──────────────────────────────────┴─→ Phase 23 (Community)
```

- **19 → 20:** Publications establish credibility for open source adoption
- **20 → 21:** Stable crates are prerequisite for hardware deployment
- **21 → 22:** Hardware integration feeds back into fleet capabilities
- **All → 23:** Community building needs both credibility and working software

---

## Compute Budget Estimate

| Item | Monthly Cost | Notes |
|------|-------------|-------|
| DeepInfra (Seed-2.0-mini/code) | $5-20 | Discovery + drafting |
| z.ai (GLM-5.1) | $0 (monthly plan) | Architecture + code |
| Claude Code | $0-50 | Synthesis + roadmap (limited credits) |
| DeepSeek | $2-5 | Backup coding |
| GitHub Actions | $0 (free tier) | CI/CD |
| arXiv submissions | $0 | Open access |
| **Total** | **$7-75/month** | |

---

## Long-Term Vision (6+ Months)

### The Constraint Theory Standard Library
- `use constraint_theory::prelude::*;` in every Rust safety-critical project
- Python: `import constraint_theory` in every robotics/simulation notebook
- C: `#include <constraint_theory.h>` in every embedded project
- The standard that makes floating-point drift a solved problem

### Hardware Acceleration
- **FPGA:** Eisenstein snap in Verilog/VHDL — 1 cycle per snap at 200MHz
- **ASIC:** Tape out a constraint-theory coprocessor ( Snapworks)
- **RISC-V custom extension:** Eisenstein lattice instructions
- **Timeline:** Year 2+ (after academic validation)

### Cross-Industry Adoption
- **Gaming:** Multiplayer desync prevention (Unity/Unreal plugins)
- **Robotics:** ROS2 constraint checker node
- **Finance:** Exact position tracking for HFT
- **Aerospace:** Navigation constraint verification
- **Medical:** Dosage calculation safety net

### Academic Program
- Constraint Theory textbook (200 pages, Springer or self-publish)
- University course: 14-week curriculum with exercises
- Summer school: 1-week intensive for PhD students
- Research group: 3-5 PhDs working on extensions

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| z.ai rate limits block work | HIGH | MEDIUM | DeepInfra failback (already set up) |
| PLDI rejects paper | MEDIUM | HIGH | Submit to ICFP, ASPLOS, POPL |
| Hardware unavailable (Jetson/ESP32) | LOW | MEDIUM | Simulation results suffice for papers |
| Fleet services stay DOWN | MEDIUM | LOW | Work continues locally, I2I bottles |
| Community doesn't adopt | MEDIUM | HIGH | Focus on one vertical (embedded/gaming) |
| Oracle1 PLATO server fails | LOW | HIGH | Git-based backup, local PLATO rooms |
| Casey loses interest | LOW | CRITICAL | Self-sustaining open source project |

---

## Success Metrics (End of H2 2026)

| Metric | Current | Target | How to Measure |
|--------|---------|--------|----------------|
| crates.io downloads | ~500 | 10,000 | crates.io stats |
| GitHub stars (ecosystem) | ~50 | 500 | GitHub API |
| Papers submitted | 0 | 3 | Submission receipts |
| Papers accepted | 0 | 1 | Acceptance emails |
| Hardware platforms | 0 | 3 | Jetson + ESP32 + OpenArm |
| Fleet agents using lighthouse | 1 | 5 | PLATO rooms |
| Community contributors | 0 | 10 | GitHub contributors |
| arXiv citations | 0 | 20 | Google Scholar |
| Conference talks | 0 | 2 | Talk acceptances |

---

## Weekly Cadence

| Day | Activity |
|-----|----------|
| Monday | Planning: what ships this week |
| Tue–Thu | Execution: code, write, test |
| Friday | Review: what shipped, what blocked |
| Saturday | Fleet coordination: I2I bottles, PLATO sync |
| Sunday | Rest (or night shift if Casey's fishing) |

---

*"The lattice doesn't care about your feelings. It either snaps or it doesn't."*  
— Forgemaster ⚒️, 2026
