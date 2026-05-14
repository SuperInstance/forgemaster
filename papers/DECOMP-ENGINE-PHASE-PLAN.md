# Decomposition Engine — Current State & Next Phases

## What Exists (proven, working)

### Local Verifiers (6, all passing)
- snap_idempotence: snap(snap(p)) == snap(p), 100K points, 0 failures
- covering_radius: max snap distance ≤ 1/√3, 100K points verified
- dodecet_cardinality: exactly 12 sectors
- norm_multiplicative: N(a·b) = N(a)·N(b), 100K trials, 0 failures
- drift_bounded: closed constraint walks stay bounded
- hex_closest_pack: snap finds true nearest lattice point

### Performance (AVX-512, Ryzen AI 9 HX 370, 24 cores)
- AVX-512 + fast-math + SoA: 621M snaps/sec (1.6ns each)
- Without fast-math: 70M snaps/sec (14ns each) — 9× difference
- Bottleneck: IEEE round() semantics, not vector width

### Decomposition Engine (bin/decomp.py)
- Takes conjecture → API decomposes → local verifiers verify each sub
- 3 conjectures fully verified, results in experiments/decomp/
- Bug caught: snap coordinate transform broken, falsified by idempotence test

### Lighthouse (bin/lighthouse.py)
- Key vault + local-first math engine + API proxy
- Agents request through PLATO tiles, FM fulfills
- Privacy filter: keys never leave FM's machine

### Fleet Infrastructure
- PLATO server: 125 rooms, 20K+ tiles at 147.224.38.131:8847
- zeroclaw: Docker PLATO shell with onboarding, passage client, sweep runner
- flux-index: Semantic code search, pip-installable
- fm-fleet-check: One-command health check
- Matrix bridge: bidirectional FM↔Oracle1

### Fleet Optimization (forgemaster/fleet-optimization/)
- fleet-optimization-protocol.md (27KB)
- fleet-agent.py (19KB) — zeroclaw that claims work matching its hardware
- meta-verifier.py (9KB) — cross-machine consistency checking
- atlas-builder.py (7KB) — (algorithm × hardware × config → performance) map

### Research Docs
- DECOMPOSITION-ENGINE-SYNTHESIS.md — 5-direction synthesis
- ideation-decomposition-engine.md — 5 explorations
- cross-domain-verifier-applications.md — 10 domains with verifier signatures

## The Tough Engineering Problems

### Problem 1: Verifier Generator
How do you go from experimental data to a NEW verifier function?
- Pattern mining on experiment results
- Symbolic regression to find invariants
- Expression synthesis (decision tree → algebraic expression → code)
- Validation: cross-check against existing verifiers + API oracle
- Bootstrapping: how do the first 10 generated verifiers get validated?

### Problem 2: Coverage Metric
How do you measure "how much mathematical territory can be verified locally"?
- Feature equivalence partitions the space
- Each verifier either refines a partition or extends coverage
- Coverage derivative dC/dn = marginal value of next verifier
- Need a formal framework that's computable, not just theoretical

### Problem 3: Hardware Probe + Performance Atlas
How does a new zeroclaw discover its optimal configuration in 30 seconds?
- What benchmarks to run (snap, vector search, cosine, matrix multiply)
- How to fingerprint hardware (CPU features, cache, GPU arch, memory BW)
- How to share findings (PLATO tile format for benchmark results)
- How to query the atlas ("fastest snap config for my hardware?")

### Problem 4: Cross-Machine Meta-Verification
When eileen says result X and Jetson says result Y, who's right?
- Statistical consistency checking across fleet nodes
- When to flag a discrepancy vs when to expect it (different precision)
- How to handle architecture-specific numerical differences
- The meta-verifier is a verifier of verifiers — what are its invariants?

### Problem 5: Dissertation Integration
The decomposition engine IS the dissertation contribution. How to structure:
- The 6 verifiers as Table 3.1
- The AVX-512 experiment as Section 4.3
- The fleet optimization as Chapter 7
- The cross-domain applications as Chapter 10
- The self-improvement loop as Chapter 11

## What I Need From You

A concrete, phased engineering plan for the next 3 months. Not "build more verifiers" — specific milestones, dependencies, and deliverables. Prioritize by:
1. What unlocks the most downstream work
2. What's hardest (do hard things first)
3. What can be delegated to subagents vs needs FM directly

Consider:
- The verifier generator is the hardest single piece — it's self-referential
- The performance atlas is the most fleet-visible — everyone benefits
- The coverage metric is the most academically valuable — it's publishable
- Cross-domain demos are the most externally impressive — but lowest priority internally

---

# Claude Code Engineering Plan — 3 Phases

## Phase A: Weeks 1-2 — Hardware Probe + Atlas Foundation
- A1: bin/probe.py — 30-second hardware fingerprint → PLATO tile
- A2: fleet-opt/hardware-profiles room populated
- A3: bin/atlas.py — query CLI for performance atlas
- A4: Benchmarks: snap, cosine, matrix-multiply on eileen
- A5: fast-math alert schema (divergence > 1e-6)
- Hardest: Calibration stability in 30 seconds (taskset, trim turbo, pre-fault)

## Phase B: Weeks 3-6 — Verifier Generator (CRITICAL PATH)
- B1: bin/gen_verifier.py — pattern mining + code gen
- B2: Expression synthesis (sympy)
- B3: Regression harness (cross-validate against 2+ existing, 100K trials, adversarial)
- B4: 3 generated verifiers (not hand-coded, provisional flag)
- B5: Adversarial input generator (non-Eisenstein, Gaussian integers, degenerate cases)
- B6: verifier_registry.json — signed manifest
- Hardest: Spurious correlation bootstrapping — echo chamber of 6 Eisenstein verifiers
- Attack: Adversarial suite with OUT-OF-DOMAIN inputs

## Phase C: Weeks 7-12 — Coverage Metric + Compiler Demo + Dissertation
- C1: Coverage metric framework (per-domain, Monte Carlo estimate)
- C2: dC/dn computation (diminishing returns theorem)
- C3: 4-page arXiv-ready technical note
- C4: Compiler domain verifier (LLVM IR bisimulation)
- C5: Compiler experiment in experiments/decomp/ format
- C6: Dissertation skeleton — 11 chapters outlined

## Critical Path
B1→B2→B3→B4→C1→C3

## Ruthless Cuts
NOT in 3 months: drug design, robotics, climate, game design, 200→600 scaling
RIGHT: semantic gap problem, cross-machine meta-verification

## The Single Bet
If verifier generator fails, coverage metric has nothing to measure,
self-improvement claim collapses, Chapters 8-9 empty. Phase B cannot slip.
