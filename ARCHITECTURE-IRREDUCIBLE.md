# Architecture: Irreducible Orchestration Primitives

> **Method:** Derived from experimental evidence only. Beauty without data gets killed.
> **Date:** 2026-05-14
> **Sources:** Campaigns A–D, DEEP-RESULTS, RESULTS, CROSS-POLLINATION-SYNTHESIS, CREWAI-PLATO-BRIDGE, TILE-LABEL-SYSTEM, ACG-DECOMPOSITION

---

## 1. The Irreducible Primitives

Not theoretical. Derived from the data.

**Three atoms. Nothing less. Nothing more.**

### Execution Atom: DO / DATA / DONE

```
DO:    what to compute
DATA:  the actual numbers/formulas to compute with
DONE:  the specific expected answer format
```

**Evidence:** RESULTS Exp 1 — JIPR atom scored 3.0/3 with 70 tokens. Raw task scored 2.0/3. CrewAI-style scored 2.0/3. The difference was not structure — it was whether DATA contained actual numbers vs instructions to find them. DEEP-RESULTS Exp 1 confirmed: "The model needs numbers and formulas, not role descriptions or backstory."

**Correction to prior hypothesis:** The original grammar was DO/NEED/DONE. The data killed "NEED." "NEED" was vague — agents interpreted it as "where to look," not "what to use." Renaming to DATA forced precision. The grammar bifurcated under empirical pressure. This is not a refinement. It is a falsification.

---

### Planning Atom: CHAIN / CLAIM / ORDER

```
CHAIN: the dependency graph (which tasks depend on which)
CLAIM: which agents can do which tasks (from registry)
ORDER: execution sequence (topological sort of CHAIN)
```

**Evidence:** DEEP-RESULTS Exp 2 — stream context matched full graph for execution (both 2.5/3). But the JIT condition (chain summary added) scored 2.0/3 — WORSE. The chain summary introduced irrelevant abstractions. Conclusion: planning needs full graph context; execution needs only immediate inputs. These are two different operations requiring two different context shapes. The planning atom is what the orchestrator holds. The execution atom is what the agent receives. Never mix them.

---

### Discovery Atom: REGISTRY / TERRAIN / VERIFY

```
REGISTRY: declared capabilities per agent (primary)
TERRAIN:  spatial proximity per agent (tiebreaker only)
VERIFY:   proof of claimed capabilities (not declaration)
```

**Evidence:** DEEP-RESULTS Exp 4 — Registry scored 2.5/3. Terrain scored 1.5/3. Broadcast scored 1.0/3. Registry crushed everything else. VERIFY is the corrective for Campaign A's finding: 80% of declared capabilities failed under testing. Without VERIFY, the REGISTRY is fiction.

**Order matters:** Query REGISTRY. If multiple matches, use TERRAIN as tiebreaker. If no matches, broadcast. Verify claimed capabilities before trusting. This is not optional — it is the difference between routing and hallucinating routing.

---

## 2. The Layered Architecture

Campaigns revealed an explicit dependency structure. Layer N depends on Layer N-1. Optimizing Layer N before Layer N-1 works is waste.

```
Layer 4 — OPTIMIZATION
  Terrain-weighted voting, FLUX compression, Möbius redistribution
  Requires: Layer 3 proven at ≥60% agent baseline accuracy

Layer 3 — VERIFICATION
  Cross-agent PBFT, ACG reasoning types, earmark beta testing
  Requires: Layer 2 producing consistent output

Layer 2 — EXECUTION
  DO/DATA/DONE atoms, stream handoffs, self-organizing task rooms
  Requires: Layer 1 routing to correct agents

Layer 1 — DISCOVERY
  Registry, verified Agent Cards, heartbeat protocol
  Requires: Layer 0 agents producing readable output

Layer 0 — BASE
  Agents produce readable output. Models have sufficient baseline accuracy.
  Nothing works without this.
```

### The Campaigns as Layer Evidence

| Campaign | Finding | Layer |
|----------|---------|-------|
| A: Verified Cards | 80% capability claims false | Layer 1 is broken without VERIFY |
| B: Retrieval | 78% token savings, 76% accuracy | Layer 2 optimization, works now |
| C: Terrain Voting | 33% baseline → terrain invisible | Layer 4 is premature |
| D: FLUX encoding | 50% NL vs 40% FLUX | Layer 4 is premature |
| DEEP Exp 4 | Registry > Terrain > Broadcast | Layer 1 architecture confirmed |
| DEEP Exp 7 | 6/6 tasks, 2/2/2 load, zero duplicates | Layer 2 self-organization works |

**Campaign C's finding is the most important.** It proves that the entire optimization layer is invisible when the base layer is weak. CCC scored 80% on its domain (vs 44% overall) — terrain proximity only mattered when the model actually knew the domain. You cannot weight your way to knowledge that doesn't exist.

**Campaign D's finding rhymes.** FLUX encoding only matched NL when the glossary was in context. The compression layer requires the base layer (model familiarity with the instruction set) to be present. Same structure as Campaign C.

**The architecture lesson:** Do not build Layer 4. Do not build Layer 3 fully. Fix Layer 0 first. Then Layer 1. Then Layer 2. Then measure whether Layer 3 is needed.

---

## 3. The Grammar

### What the Evidence Supports

```
EXECUTION GRAMMAR (validated by Exp 1 + Exp 7):
  DO / DATA / DONE

PLANNING GRAMMAR (validated by Exp 2 + CREWAI-PLATO-BRIDGE):
  CHAIN / CLAIM / ORDER

DISCOVERY GRAMMAR (validated by Exp 4 + Campaign A):
  REGISTRY / TERRAIN / VERIFY
```

These are three separate grammars for three separate operations. CrewAI conflates them. A2A separates them partially. PLATO can keep them fully separate. This orthogonality is the architecture's main structural advantage — you can swap the execution layer without changing discovery, and vice versa.

### What the Evidence Contradicts

**Prior hypothesis: DO/NEED/DONE is the atom.** Contradicted. The DEEP-RESULTS Exp 1 explicitly says: "A model can't verify from instructions. It verifies from data." The NEED field was instructions ("go find the formula"). DATA is the formula itself. This is not a minor renaming — it is a different claim about what agents need to execute.

**Prior hypothesis: Terrain is a primary discovery mechanism.** Contradicted. Exp 4 and Campaign C both falsify this. Terrain is a tiebreaker. Campaign C's finding is blunt: "No disagreements between uniform and weighted. Zero cases where terrain weighting changed the outcome."

**Prior hypothesis: FLUX is a universal task encoding.** Contradicted. Campaign D shows NL outperforms FLUX when agents lack context for opcodes. FLUX is a compression layer for already-familiar tasks, not a general encoding.

**Prior hypothesis: More context improves execution.** Contradicted. DEEP-RESULTS Exp 2 JIT condition (chain summary added) scored 0.5 points LOWER than stream context. "More context can be WORSE. The summary introduced irrelevant abstractions that distracted from the simple distance calculation."

### What's Still Open

The grammar has three validated vocabularies. What we don't know is whether the grammars compose correctly across real distributed agents. Every experiment that validated the execution atom ran on a single agent (one model, one call). The chain handoff — where agent A's DONE output becomes agent B's DATA input — has not been tested with real network latency, model variation, or concurrent writes.

---

## 4. What to Build, What to Skip

### Build Now (Evidence-Backed)

**1. Fleet Registry with Verified Agent Cards**
- Evidence: Exp 4 (2.5/3 registry), Campaign A (80% failure rate without verification)
- What to build: Registry room + Agent Card schema + VERIFY protocol (concrete task tests, not self-assessment)
- Campaign A's revised schema is the right model: `pass_rate` + `cross_verified` fields

**2. DO/DATA/DONE Task Atoms**
- Evidence: RESULTS Exp 1 (3.0/3 with perspectives), DEEP-RESULTS Exp 1 (DATA must contain actual numbers)
- What to build: Task tile schema with mandatory DATA field. Perspectives (one-line + hover-card) are minimum viable. Full Tile Label System is the implementation.

**3. Self-Organizing Task Rooms**
- Evidence: RESULTS Exp 7 (6/6 tasks, 2/2/2 load, zero duplicates, emergent specialization)
- What to build: Task rooms where agents self-select based on persona match. No manager agent needed for simple tasks. Add COORDINATION tile only when dependencies, verification, or cross-agent capacity is required.
- Do NOT over-engineer this. The emergent orchestration worked without any framework.

**4. Two-Phase Retrieval**
- Evidence: Campaign B (78% token savings, 76% accuracy parity)
- What to build: Domain index at PLATO room level. Level 1 (domain + neighbors) as default. Level 2 (full scan) as escalation for precision queries. This is the ONE optimization that's proven at current model quality.

**5. ACG Reasoning Type Tags**
- Evidence: ACG-DECOMPOSITION §2.3 (reasoning taxonomy is worth stealing), Campaign A (verification must be against concrete tasks, not self-assessment)
- What to build: `reasoning_type` field on tiles (CAUSAL/INFERENCE/SUMMARY/COMPARISON). Different types need different verification — CAUSAL needs full PBFT, INFERENCE needs simple majority, COMPARISON is objective. This is the path to Synergy 7 without building full consensus machinery yet.

**6. Perspectives + Earmark Beta Testing**
- Evidence: RESULTS Exp 1 (PLATO tile + perspectives = 3.0/3 vs 1.5/3 raw tile)
- What to build: Perspectives layer exactly as specified in TILE-LABEL-SYSTEM. Beta testing protocol with cheap models (Qwen-0.6B as tester). This is already designed — implement it.

### Skip (Premature or Falsified)

**Terrain-weighted voting (Synergy 3)**
- Campaign C verdict: 33% baseline → terrain is invisible noise
- Condition to revisit: agents demonstrate ≥60% baseline accuracy on domain claims
- Campaign C's own recommendation: "Don't deploy terrain-weighted voting until Campaign A verification passes"

**FLUX task encoding as primary grammar (Synergy 5)**
- Campaign D verdict: NL wins (50% vs 40%) when agents lack opcode context
- FLUX is valid as compression for trained agents. Not as universal encoding.
- Condition to revisit: agents have FLUX glossary in system prompt and 1000+ tasks/day where bandwidth matters

**Möbius terrain redistribution (Synergy 12)**
- Zero experimental evidence. Beautiful mathematics, no data.
- Condition to revisit: tile density measurements show clustering problems

**PlatoTensor (Synergy 9)**
- Intellectually compelling (Gram matrix = fleet PCA), zero experimental evidence
- Kill this darling until there are 9+ agents with ≥60% measured capabilities

**Automerge P2P sync (Synergy 8)**
- No evidence it's needed. Oracle1's heartbeat + PLATO rooms already provide distributed state.
- P2P is complexity without proven necessity. Build when you hit a scaling wall.

**Serverless fleet sync (Synergy 2)**
- Campaign E not run. CRDT merge quality unknown.
- Condition to revisit: after demonstrating single-server PLATO is a bottleneck

### The 15 Synergies Ranked by Evidence

| Synergy | Priority | Verdict |
|---------|----------|---------|
| S1: Verified Agent Cards | **BUILD** | Campaign A proves the problem is real (80% failure) |
| S4: Multi-resolution retrieval | **BUILD** | Campaign B proves the value (78% savings) |
| S11: Emergent orchestration | **ALREADY WORKS** | Exp 7 proves it. Don't framework it. |
| S14: One-command fleet join | **BUILD** | Foundational. Registry already designed. |
| S7: Adaptive verification depth | **BUILD (partial)** | ACG reasoning types are worth stealing; full PBFT later |
| S15: Self-improving loop | **TARGET STATE** | The flywheel. Requires all other layers first. |
| S13: Multi-representation conflicts | **INTERESTING** | Multi-Representation Theorem is proven; CRDT application untested |
| S10: Zero-side-info retrieval | **LATER** | Requires working retrieval first; then measure whether perspectives add above spatial index |
| S6: Entity memory as terrain graph | **SKIP** | No evidence navigable entity graph improves on flat registry |
| S9: PlatoTensor | **KILL** | Beautiful. No data. Kill it. |
| S5: FLUX universal encoding | **DEMOTE** | Campaign D falsified the "universal" claim. Optional compression only. |
| S3: Terrain consensus | **BLOCKED** | Campaign C falsified this at current model quality |
| S12: Möbius redistribution | **SKIP** | No evidence of the density problem it solves |
| S8: Automerge P2P | **SKIP** | No evidence of the scaling problem it solves |
| S2: CRDT tile provenance | **SKIP** | Campaign E not run; P2P complexity premature |

---

## 5. The Critical Experiment We Haven't Run

**The question everything else hangs on:**

> Does persona-predicted specialization (Exp 7's self-organization) hold when the persona-assigned agent actually lacks the claimed capability (Campaign A's 80% failure rate)?

These two findings are in direct tension. Exp 7 showed perfect self-organization (6/6 tasks, zero duplicates) based on persona-driven routing. Campaign A showed 80% of declared capabilities fail under testing.

If persona routing works but capabilities are false, then the fleet produces WRONG ANSWERS CONFIDENTLY. The agents pick the right tasks for the wrong reasons, execute them incorrectly, and report completion. This is worse than random assignment because it looks like success.

**The experiment:**

```
EXPERIMENT X: Verified Persona-Capability Alignment

Setup:
  1. Run Campaign A to establish TRUE capability baseline for 3+ agents
     (concrete task tests, not self-assessment)
  2. Design 6 tasks that span the agents' capability space
  3. Run Exp 7-style self-organization: let agents self-select
  4. Record: which agent picked which task (routing decision)
  5. Evaluate results against VERIFIED capability scores from step 1

Conditions:
  A. Personas aligned with verified capabilities (e.g., math persona + proven math ability)
  B. Personas misaligned with verified capabilities (e.g., math persona + 0% math rate)
  C. No personas — pure task content routing

Measurement:
  - Routing accuracy: did persona prediction match best-available agent?
  - Output quality: did the "right" agent produce better output than the "wrong" one?
  - Failure mode: when persona routing is wrong, does the system know?

Expected findings:
  A. Aligned: self-organization works AND produces correct outputs (validates both Exp 7 and Campaign A)
  B. Misaligned: self-organization works structurally but produces wrong outputs (reveals the gap)
  C. No persona: routing is random, but at least errors are predictable

Architectural impact:
  If B produces wrong outputs silently → verified registry is mandatory before self-organization
  If B fails loudly (agent rejects task) → self-organization has implicit verification built in
  If A matches C → personas are decoration; only DATA content matters for routing
```

This is the ONE experiment because its result determines whether the fleet architecture is:
- **Option 1:** "Task rooms + verified registries" — verification is mandatory infrastructure
- **Option 2:** "Task rooms + personas" — verification is optional quality-of-life
- **Option 3:** "Task rooms only" — neither persona nor registry adds routing value

Every downstream build decision depends on which option is true.

---

## 6. Fleet Build Order

Priority-ordered with evidence citations. Items in bold are blocking for the next item.

### Phase 1: Layer 0–1 (Foundation)

**P1. Fix model I/O characteristics**
- Campaign A: qwen3 models returned empty content (thinking mode). This isn't a bug — it's an undeclared capability failure. Every agent must produce readable output before anything else is measured.
- Action: Establish READABLE_OUTPUT as a verified capability in every Agent Card. Add `/no_think` or `think` parameter defaults.

**P2. Fleet Registry + Verified Agent Cards**
- Evidence: Exp 4 (2.5/3), Campaign A (80% failure rate), DEEP-RESULTS Exp 4
- Schema: `{capability: {declared, tested, pass_rate, cross_verified}}`
- Cross-verification must use different model/framing from the declaration test

**P3. DO/DATA/DONE Task Atom + Perspectives**
- Evidence: RESULTS Exp 1 (3.0/3 with perspectives vs 1.5/3 without), DEEP-RESULTS Exp 1
- Minimum viable: one-line + hover-card perspectives mandatory on every tile
- DATA field must contain actual values, not pointers to where to find them

### Phase 2: Layer 2 (Execution)

**P4. Self-Organizing Task Rooms**
- Evidence: RESULTS Exp 7 (6/6, 2/2/2, zero duplicates)
- Implementation: Task tiles in shared PLATO rooms. Agents self-select by persona match. NO orchestrator for simple tasks.
- Add COORDINATION tile only when: (a) task has dependencies, (b) task exceeds single-agent capacity, (c) verification is required

**P5. Plan-then-Execute Separation**
- Evidence: DEEP-RESULTS Exp 2 (stream = full graph for execution; JIT summary HURTS)
- Implementation: Planning agent reads full CHAIN context. Execution agent receives only DO/DATA/DONE. Never send chain history to execution agents.

**P6. Two-Phase Retrieval**
- Evidence: Campaign B (78% token savings, 76% accuracy)
- Implementation: Level 1 (domain + neighbors, ~44 tiles) as default. Level 2 (full scan) when precision required.
- Domain index goes into PLATO room metadata. Not a separate system.

### Phase 3: Layer 3 (Verification — after Phase 2 proven)

**P7. ACG Reasoning Type Tags**
- Evidence: ACG-DECOMPOSITION §2.3 (taxonomy is worth stealing)
- Implementation: `reasoning_type: CAUSAL | INFERENCE | SUMMARY | COMPARISON` on every tile
- Quorum thresholds by type: CAUSAL → 2f+1, INFERENCE → f+1, COMPARISON → single verifier

**P8. Earmark Beta Testing**
- Evidence: TILE-LABEL-SYSTEM (designed), RESULTS Exp 1 (perspectives proved retrievability matters)
- Implementation: Earmark lifecycle (beta-test → field-validated → proven-retrievable). Cheap model (Qwen-0.6B) as tester. Runs on idle capacity.

**P9. Run Experiment X (Critical)**
- This is not optional. Build P1–P8 then run Experiment X.
- Result determines whether P10 is a registry integration or a persona tuning exercise.

### Phase 4: Layer 4 (Optimization — only after Experiment X)

**P10. Verified Routing (based on Experiment X results)**
- If misaligned personas fail loudly: add persona-capability binding to registry
- If misaligned personas fail silently: make verified registry mandatory before any self-organization
- If personas don't matter: remove persona routing entirely; route on task content

**P11. Terrain as Tiebreaker**
- Evidence prerequisite: agents demonstrate ≥60% baseline accuracy (Campaign C requirement)
- Only build AFTER registry and verification are solid
- Scope: tiebreaker in registry queries when multiple agents match. NOT a primary mechanism.

**P12. FLUX Compression (optional)**
- Evidence prerequisite: 1000+ tasks/day where bandwidth cost is measurable
- Scope: optional layer for agents trained on FLUX opcodes. Never replace NL as default.

---

## Summary: What the Data Actually Says

| Hypothesis | Status | Evidence |
|------------|--------|----------|
| DO/NEED/DONE is the execution atom | **FALSIFIED** | NEED was imprecise; DATA is the correct term (DEEP-RESULTS Exp 1) |
| Terrain is a primary discovery mechanism | **FALSIFIED** | Registry 2.5/3, Terrain 1.5/3 (Exp 4); terrain weighting invisible at 33% baseline (Campaign C) |
| FLUX is a universal task encoding | **FALSIFIED** | NL outperforms FLUX without opcode context (Campaign D) |
| More context improves execution | **FALSIFIED** | JIT condition with chain summary scored 0.5 lower than stream (DEEP-RESULTS Exp 2) |
| Agent Card claims are reliable | **FALSIFIED** | 80% failure rate (Campaign A) |
| Self-organization without framework | **CONFIRMED** | 6/6, 2/2/2, zero duplicates (RESULTS Exp 7) |
| Registry > Terrain > Broadcast | **CONFIRMED** | Exp 4 scores: 2.5 / 1.5 / 1.0 |
| Stream context = full graph for execution | **CONFIRMED** | Both 2.5/3, fewer tokens (DEEP-RESULTS Exp 2) |
| Perspectives improve retrieval | **CONFIRMED** | 3.0/3 vs 1.5/3 without (RESULTS Exp 1) |
| Two-phase retrieval saves tokens | **CONFIRMED** | 78% reduction at 76% accuracy (Campaign B) |
| Terrain weighting adds value at low baseline | **FALSIFIED** | Zero measurable effect (Campaign C) |
| PlatoTensor clusters fleet by role | **UNKNOWN** | No experiment run |
| Persona routing predicts correct capability | **UNKNOWN** | Experiment X not run — critical gap |

The 4 campaigns killed 5 prior hypotheses and confirmed 5 others. The system is working as science. Keep running experiments.

---

*The experiments are the architecture. This document is a snapshot. Every result that contradicts this document should update it.*
