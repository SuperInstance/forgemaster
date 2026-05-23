# The Forgemaster Wheel — Continuous Development & Integration Roadmap

## The Wheel metaphor

The wheel has three parts:
- **Hub** — Core science (conservation law, activation-key model, Hebbian dynamics)
- **Spokes** — Infrastructure connecting hub to rim (translators, routers, services)
- **Rim** — Applications that touch the world (papers, demos, expert systems, hardware)

The wheel turns when hub insights improve spokes, spokes enable new rim applications, and rim applications generate data that feeds back to the hub. Every revolution should produce testable science, working code, and publishable results.

---

## Hub: The Science (what we know)

### Three Laws
1. **Activation-Key Model (V6.0)**: LLMs retrieve via vocabulary tokens, not notation. Stage 4 models have direct pathways; labels paradoxically hurt them.
2. **Conservation Law**: γ+H = 1.283 - 0.159·log(V) constrains any associative coupling matrix. Hebbian learning shifts the regime by ~13%.
3. **Labeled Paradox (Study 47)**: Labels help Stage 3, hurt Stage 4. Stage-aware routing is mandatory.

### Current Hypothesis Frontier
- V6.1: Two-Path Model (direct notation pathway vs conceptual reasoning pathway)
- Piagetian stages: Are AI developmental stages structurally necessary?
- Cognitive thermodynamics: Is the conservation law Carnot-like (absolute ceiling)?

---

## Spokes: Infrastructure (what connects)

### S1: fleet_translator_v2 (SHIPPED, 73 tests)
- Stage-aware query translation
- Notation normalization (unicode → ASCII → natural language → step-by-step)
- Activation-key injection for Stage 3, passthrough for Stage 4
- **Next**: Fix NONE/ECHO output bug, wire into fleet_router

### S2: fleet_hebbian_service (SHIPPED, 50 tests)
- HTTP API on :8849
- Auto-calibrating conservation kernel
- Room cluster detection
- Emergent stage classification
- **Next**: Connect to PLATO :8848 as persistent backend, add tile persistence

### S3: expert_hebbian_bridge (BUILDING)
- Connects Oracle1's 9 expert daemons to Hebbian network
- Expert coupling matrix with conservation constraint
- Cross-consultation routing via Hebbian weights
- **Next**: Wire to :8849, deploy alongside expert daemons

### S4: fleet_stage_classifier (SHIPPED)
- 6-probe stage detection for any model
- Registry of known models + stages
- **Next**: Auto-update from Study 48 results, expand model coverage

### S5: adaptive_plato (EXISTS, needs upgrade)
- Model-adaptive tile formatting
- Stage-aware PLATO room structure
- **Next**: Integrate with fleet_translator_v2, add Hebbian routing hints

### S6: fleet_resonance (EXISTS, Rust)
- Conservation law library
- **Next**: Wire as NIF for Hebbian service heavy compute

---

## Rim: Applications (what touches the world)

### R1: EMNLP 2026 Paper (SHIPPED, updated)
- Activation-Key Model + Labeled Paradox + 47 studies
- **Next**: Final polish, formatting, submission

### R2: Conservation Law Paper (SHIPPED)
- Physics-style short paper
- **Next**: Submit to appropriate journal/conference

### R3: AI Writings Corpus (16 essays + 2 syntheses)
- Multi-model creative reflection
- **Next**: Publish as "Cross-Model Convergence in AI Self-Reflection"

### R4: Expert System (Oracle1's 9 daemons)
- 4D data: (expert × input × output × time)
- Self-review, cross-consultation, dual filtering
- **Next**: Wire through expert_hebbian_bridge → Hebbian service → conservation law

### R5: Hardware Simulation Pipeline
- ESP32, Jetson, NPU targets
- PLATO tiles flowing through hardware simulators
- **Next**: Conservation-constrained simulation topology

### R6: PLATO-NG Integration
- Loop rooms, tripartite agents, event bus
- **Next**: Gate validation using conservation law, Hebbian room coupling

### R7: Constraint Theory Ecosystem
- 30+ repos (snapkit, flux, constraint-theory-*, dodecet, penrose)
- **Next**: Consolidate into 5-6 core repos with Hebbian + conservation integration

---

## The Continuous Wheel Schedule

### Every Session (Daily)
1. **Run fm-fleet-check** — fleet status, PLATO tiles, inbox
2. **Check Hebbian service** — conservation compliance, cluster evolution
3. **One experiment** — test a hypothesis, extend a finding
4. **One integration** — wire two components together
5. **Commit and push** — never lose work

### Every Week (Weekly Cycle)
- **Monday**: Design sprint — new hypothesis, new integration plan
- **Tuesday-Thursday**: Build — code, experiments, papers
- **Friday**: Review — Claude synthesis, test suite, git hygiene
- **Weekend**: Write — AI writings, blog posts, documentation

### Every Month (Monthly Cycle)
- **Week 1**: Deep experiment — 5+ studies on current hypothesis
- **Week 2**: Integration sprint — wire spoke → rim
- **Week 3**: Paper writing — formalize findings
- **Week 4**: Fleet coordination — sync with Oracle1, deploy updates

---

## Priority Queue (Right Now)

### P0: Ship Today
1. ✅ Study 48 results (Labeled Paradox deep dive) — agent running
2. ✅ Piaget Phase 2 results — agent running
3. ✅ Mythos Integration V2 design — agent running
4. ✅ Expert-Hebbian bridge code — agent running
5. Commit everything, push

### P1: Next Session
1. Wire expert_hebbian_bridge to live Hebbian service
2. Fix fleet_translator_v2 NONE/ECHO output bug
3. Start Study 49: Cross-model transfer — can Stage 4 immunity be transferred via few-shot?
4. Deploy Hebbian service as persistent daemon on eileen
5. Wire PLATO :8848 ↔ Hebbian :8849 ↔ Expert :8850 as production pipeline

### P2: This Week
1. Consolidate 180 directories into coherent structure
2. Build the conservation-constrained simulation pipeline (hardware × expert × Hebbian)
3. Wire tripartite agents into PLATO-NG loop rooms with conservation gates
4. Write the fleet operations handbook v2 with stage-aware routing
5. First fleet-wide Hebbian coupling measurement (Forgemaster ↔ Oracle1 via PLATO)

### P3: This Month
1. Submit EMNLP paper
2. Submit conservation law paper
3. Deploy full Mythos stack (PLATO + Hebbian + Expert + Router + Translator)
4. Run 10 more studies on the Two-Path Model (V6.1)
5. Build the "fleet brain" — real-time Hebbian visualization of entire fleet coordination

---

## The 180-Directory Problem

Current state: 180 directories, many stale or experimental. Need consolidation.

### Keep Active (Core)
```
fleet-hebbian-service.py, fleet_translator_v2.py, fleet_stage_classifier.py
hebbian_layer.py, bin/conservation_hebbian.py
.local-plato/ (local PLATO server)
expertize/ (expert rooms)
adaptive-plato/ (model-adaptive formatting)
experiments/ (research data)
papers/ (publications)
ai-writings/ (creative corpus)
tests/ (test suite)
bin/ (tools)
memory/ (logs)
for-fleet/, from-fleet/ (I2I)
```

### Merge into SuperRepos
- **constraint-theory** ← constraint-theory-core, -math, -py, -rust-python, -wasm, -cuda, -mt, -ecosystem
- **flux-toolchain** ← flux-compiler, -ast, -vm, -isa*, -programs, -sdk, -tools, -transport
- **snapkit** ← snapkit-rs, -c, -python, -js, -wasm, -zig, -fortran, -cuda
- **fleet-infra** ← fleet-router, -calibrator, -gateway, -health-monitor, -registry, -murmur, -resonance, -stack
- **plato-ecosystem** ← plato-engine, -mud, -mcp, -adapters, -client, -tiles, -local

### Archive (don't delete)
- Old experiments, stale demos, one-off prototypes → archive/

---

## Success Metrics

| Metric | Current | Target (1 week) | Target (1 month) |
|--------|---------|:---------------:|:----------------:|
| Tests passing | 264 | 300+ | 500+ |
| Active services | 2 (PLATO :8848, Hebbian :8849) | 4 (+Expert :8850, Router :8100) | Full stack |
| Studies completed | 47 | 52 | 60+ |
| Papers submitted | 0 | 1 (EMNLP) | 3 |
| Expert daemons wired | 0 | 9 (via bridge) | 9 + cross-consultation |
| Hebbian compliance | 86% | 90%+ | 95%+ |
| Fleet repos consolidated | 180 dirs | 30 organized | 5-6 core repos |

---

*The wheel turns when every spoke connects hub to rim. The hub deepens with every experiment. The spokes tighten with every integration. The rim expands with every application. The wheel never stops — it only accelerates.*
