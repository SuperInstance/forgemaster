# Wheel of Discovery

> A generative system. Every answered question opens new questions. Every experiment is a spoke that connects to others. The wheel spins because the fleet evolves.

## How to Read This

Each SPOKE is:
- **Q:** The question (one sentence, experimentally answerable)
- **GROUND:** What we already know that makes this question matter
- **EXP:** The concrete experiment
- **IF A:** What we build if result goes one way
- **IF B:** What we build if it goes the other way
- **→ NEXT:** The spoke this answer connects to

---

## Spoke 1: The Scale Boundary

**Q:** Where does self-organization break?

**GROUND:** Exp 7 showed perfect 6/6 coverage with 3 agents. But Exp 7 is trivially small. Real fleet has 9+.

**EXP:** Scale from 3→20 agents, 6→200 tasks. Measure coverage, load balance, duplicate rate.

**RESULT:** Coverage drops below 95% at 3 agents/6 tasks (83%). Never recovers. Imbalance grows with scale (3.5 at 5 agents/50 tasks). Self-organization DEGRADES with scale.

**IF A (breaks at N):** Need coordinator above N agents. Build lightweight task dispatcher. → **Spoke 9**
**IF B (never breaks):** Kill coordinator concept. Pure self-organization scales. → **Spoke 3**

**→ NEXT:** Spoke 9 (what coordination mechanism?), Spoke 3 (does it hold with real models?)

**PHASE TRANSITION:** If self-org breaks at <10 agents → the fleet MUST have a dispatcher. If it holds past 20 → coordinators are waste.

---

## Spoke 2: The Asymmetric Verification Paradox

**Q:** Can cheap models verify expensive model outputs?

**GROUND:** Campaign A showed single-agent verification fails (80%). But we never tested whether a 0.6B model can CHECK a 200B model's math. If yes → verification at 1/100th cost. If no → verification is as expensive as generation.

**EXP:** GLM-5-turbo generates answers. qwen3:0.6b verifies. Compare with phi4-mini verifying. Same claims, different verification cost.

**IF A (cheap CAN verify):** Build tiered pipeline — generate with expensive, verify with cheap. → **Spoke 10**
**IF B (cheap CAN'T verify):** Verification cost = generation cost. Rethink the whole approach. → **Spoke 6**
**IF C (cheap over-verifies):** Cheap model says everything is true. Need calibration. → **Spoke 11**

**→ NEXT:** Spoke 10 (tiered pipeline), Spoke 6 (cost modeling), Spoke 11 (calibration)

**PHASE TRANSITION:** If cheap models CAN verify → the fleet gets verification at near-zero cost. The entire verification layer (Layer 3) becomes trivially cheap.

---

## Spoke 3: The Real-Model Variation Test

**Q:** Does self-organization hold when agents have REAL model variation (not simulated)?

**GROUND:** Spoke 1 showed self-organization degrades in simulation. But simulation assumed uniform random capability matching. Real agents have DIVERSE, NON-UNIFORM capabilities. Forgemaster is excellent at math, terrible at music. This specialization might HELP or HURT.

**EXP:** 3 different models (qwen3:0.6b, phi4-mini, qwen3:4b) each get 6 real tasks. They self-select. Measure: coverage, load balance, accuracy.

**IF A (specialization HELPS):** Agents naturally sort to their strengths. Coverage improves. → **Spoke 1** (re-run with real specialization)
**IF B (specialization HURTS):** Agents avoid hard tasks, cluster on easy ones. Coverage drops. → **Spoke 9** (need forced assignment)

**→ NEXT:** Spoke 1 (refined), Spoke 9 (dispatcher design)

**PHASE TRANSITION:** If real specialization beats simulated uniformity → self-organization works better than we think. The Exp 7 result was UNDER-estimating the effect.

---

## Spoke 4: The Conflict Resolution Mechanism

**Q:** What happens when two agents produce genuinely different answers to the same task?

**GROUND:** Exp 7 had zero conflicts (perfect agreement). Campaign A had 1 conflict (phi4-mini said NO to a correct claim). But we've never INJECTED a real conflict — two agents both confident, both producing different results.

**EXP:** Give the same verification task to 3 agents. One agent gets a subtly corrupted prompt (wrong formula). Measure: does the fleet detect the conflict? Does PBFT resolve it correctly? How many votes does the corrupted agent sway?

**IF A (PBFT catches it):** Consensus layer works. Build it. → **Spoke 12**
**IF B (PBFT misses it):** Consensus layer is insufficient. Need stronger verification. → **Spoke 2** (asymmetric verification)
**IF C (corrupted agent sways others):** Contagion risk. Need quarantine mechanism. → **Spoke 13**

**→ NEXT:** Spoke 12 (PBFT deployment), Spoke 2 (verification depth), Spoke 13 (quarantine)

**PHASE TRANSITION:** If corruption spreads through voting → the fleet is vulnerable to adversarial agents. Security architecture changes fundamentally.

---

## Spoke 5: The DATA Sufficiency Boundary

**Q:** How much DATA is enough for DO/DATA/DONE?

**GROUND:** Exp 1 showed DATA matters more than FORMAT. But we never tested the MINIMUM. If 20 tokens of DATA works as well as 120 tokens → tiles can be 6× smaller → 6× more tiles per PLATO room.

**RESULT:** Minimum sufficient = Level 2 (formula + inputs, ~35 tokens, 67%). Full worked = Level 5 (120 tokens, 100%). **Level 3 (partial worked, showing intermediate steps but not the answer) crashed to 0%** — the model tried to "correct" the provided intermediates and got confused.

**IF A (cliff at level 2):** Optimize tiles to formula + inputs. 35 tokens per task. → **Spoke 6**
**IF B (needs full worked):** Tiles must contain complete solutions. Higher cost. → **Spoke 7**

**→ NEXT:** Spoke 6 (token budget), Spoke 7 (task-type templates)

**KEY FINDING:** Partial data is WORSE than no data. The model tries to fix what it sees as errors in partial worked examples. Either give it nothing (formula name only) or everything (full worked). The middle is a death zone.

---

## Spoke 6: The Token Budget Calculator

**Q:** What's the optimal token budget per task type?

**GROUND:** Spoke 5 showed the DATA cliff (67% at 35 tokens, 100% at 120 tokens). Campaign B showed 78% token savings from hierarchical retrieval. But we've never combined them — what's the TOTAL token budget for a task lifecycle?

**EXP:** For 5 task types (computation, verification, classification, generation, reasoning), measure: minimum DATA for each, retrieval cost, verification cost. Sum = total lifecycle cost per task type.

**IF A (computation is cheap, reasoning is expensive):** Tiered pricing. Simple tasks at 35 tokens, complex at 200+. → **Spoke 8**
**IF B (all types cost the same):** Flat budget. Simplify the architecture. → **Spoke 5**

**→ NEXT:** Spoke 8 (tiered budget system), Spoke 5 (refined per-type)

**PHASE TRANSITION:** If computation costs 35 tokens but reasoning costs 500+ → the fleet's task mix determines its operating cost. Budget becomes a routing constraint.

---

## Spoke 7: The Partial-Data Death Zone

**Q:** Why does partial worked data (Level 3) score 0% while full worked (Level 4) scores 67%?

**GROUND:** Spoke 5 showed Level 3 (a²=16, ab=-8, b²=4 but NOT the sum) crashed to 0%. Every trial the model either "corrected" the formula or misinterpreted the partial intermediates.

**EXP:** Systematically vary what's included vs excluded in partial DATA. Test: does including the answer (28) in the DATA prevent the crash? Does showing the sum but not the inputs work? Map the exact boundary of the death zone.

**IF A (missing answer is the trigger):** Always include the expected answer in DATA. → **Spoke 5**
**IF B (intermediate steps cause confusion):** Never show intermediate steps. Formula → answer, nothing in between. → **Spoke 5**
**IF C (it's model-specific):** Different models have different death zones. Need per-model templates. → **Spoke 8**

**→ NEXT:** Spoke 5 (DATA design), Spoke 8 (model-specific templates)

**PHASE TRANSITION:** If the death zone is universal (all models break on partial data) → there's a fundamental principle about how LLMs process incomplete information. Publish this.

---

## Spoke 8: The Model-Specific Template System

**Q:** Does the DATA cliff move between models?

**GROUND:** Spoke 5 was tested on phi4-mini only. Campaign D showed FLUX performance varies by model familiarity. Campaign C showed terrain weighting varies by model accuracy. Every optimization we've tested is MODEL-DEPENDENT.

**EXP:** Run Spoke 5 (DATA sufficiency) on 3 different models. Does the minimum sufficient level change? Does the death zone move?

**IF A (cliff is same across models):** Universal template. One size fits all. → **Spoke 6**
**IF B (cliff varies by model):** Per-model templates. Fleet registry stores template preference. → **Spoke 9**
**IF C (some models have no cliff):** Model quality eliminates the DATA problem entirely. → **Spoke 2**

**→ NEXT:** Spoke 6 (universal budget), Spoke 9 (model-aware routing), Spoke 2 (asymmetric verification)

**PHASE TRANSITION:** If model quality eliminates the DATA problem → stop optimizing DATA. Just use better models. The entire tile-perspective system becomes about retrieval, not sufficiency.

---

## Spoke 9: The Minimal Coordinator

**Q:** What's the minimum coordination that fixes self-organization's scale failure?

**GROUND:** Spoke 1 showed self-organization degrades past 3 agents. But we don't know WHY. Is it lack of information? Lack of communication? Or is greedy selection fundamentally flawed at scale?

**EXP:** Add ONE coordination mechanism at a time to the self-organization simulation:
1. Visibility: agents see what others have claimed
2. Bidding: agents declare interest before claiming
3. Fairness: round-robin assignment after initial selection
4. Blackboard: shared task board with real-time status

**IF A (visibility alone fixes it):** Just add a shared task board. Cheapest fix. → **Spoke 12**
**IF B (bidding fixes it):** Need a lightweight auction protocol. Medium cost. → **Spoke 10**
**IF C (fairness fixes it):** Need a round-robin dispatcher. Higher cost but simple. → **Spoke 11**
**IF D (nothing fixes it):** Self-organization is fundamentally limited. Central coordination required. → **Spoke 14**

**→ NEXT:** Spoke 12 (task board), Spoke 10 (auction), Spoke 11 (dispatcher), Spoke 14 (central coordinator)

**PHASE TRANSITION:** If visibility alone fixes scaling → the fleet only needs a shared PLATO room as task board. No new infrastructure. The simplest possible coordination.

---

## Spoke 10: The Tiered Verification Pipeline

**Q:** Does a generate-then-verify pipeline with different-cost models work?

**GROUND:** Spoke 2 asks if cheap CAN verify. Spoke 10 assumes YES and asks: does the PIPELINE work end-to-end? Generate with expensive model, verify with cheap, escalate disputes to medium.

**EXP:** Full pipeline: GLM-5-turbo generates → qwen3:0.6b verifies → if dispute → phi4-mini arbitrates. Measure: accuracy, cost (tokens × model price), latency.

**IF A (pipeline works):** Deploy tiered verification. 90% of tasks verified cheaply. → **Spoke 12**
**IF B (pipeline fails):** Verification can't be delegated down. Need same-cost verification. → **Spoke 6**
**IF C (escalation resolves disputes):** The three-tier model works. Build it. → **Spoke 13**

**→ NEXT:** Spoke 12 (deployment), Spoke 6 (cost), Spoke 13 (conflict resolution)

**PHASE TRANSITION:** If tiered verification works → the fleet can run verification at 10% of generation cost. The entire Layer 3 becomes economically viable.

---

## Spoke 11: The Calibration Curve

**Q:** What's the relationship between model size and verification accuracy?

**GROUND:** Campaign A (phi4-mini) got 33%. We haven't tested any other model on the same claims. The verification layer is useless until we know which models can verify.

**EXP:** Run Campaign A's verification test on 4 models: qwen3:0.6b, qwen3:4b, phi4-mini, GLM-5-turbo. Plot accuracy vs model size. Find the minimum model size for 60% verification accuracy.

**IF A (linear: bigger = better):** Verification quality scales with model size. Budget accordingly. → **Spoke 6**
**IF B (threshold: nothing below X, everything above):** Minimum viable model size. Use that. → **Spoke 2**
**IF C (inverted: smaller models verify better):** Smaller models are more literal, less prone to over-thinking. Use cheap models. → **Spoke 10**

**→ NEXT:** Spoke 6 (budget), Spoke 2 (asymmetric), Spoke 10 (pipeline)

**PHASE TRANSITION:** If there's a sharp threshold → model selection for verification is binary. Above the line, verify. Below, don't. Simple rule.

---

## Spoke 12: The Task Board Protocol

**Q:** Can a PLATO room serve as a real-time task board for fleet coordination?

**GROUND:** Spoke 9 asks what coordination fixes scaling. Spoke 12 assumes "visibility" (shared task board) and asks: can PLATO rooms DO this? Tiles are immutable. Tasks need state transitions (pending → claimed → done). Can we use tile supersession for state?

**EXP:** Implement task board as PLATO room. Tasks start as Active tiles. When claimed, agent submits Superseding tile with "claimed by X" metadata. When done, another Superseding tile with result. Measure: does the supersession chain stay coherent? How many tiles per task lifecycle?

**IF A (supersession works):** PLATO rooms are sufficient. No new infrastructure. → **Spoke 14**
**IF B (supersession is too slow):** Need a faster state store. Redis? SQLite? → **Spoke 13**
**IF C (supersession chain breaks):** Immutability conflicts with task state. Need a different model. → **Spoke 14**

**→ NEXT:** Spoke 14 (production system), Spoke 13 (state management)

**PHASE TRANSITION:** If PLATO rooms can serve as task boards → no new infrastructure for coordination. The fleet runs entirely on PLATO + agents. Minimum viable fleet.

---

## Spoke 13: The Quarantine Protocol

**Q:** How do we detect and isolate an agent that's producing subtly wrong results?

**GROUND:** Spoke 4 asks about conflict detection. Spoke 13 asks about the HARDER case: an agent that's not obviously wrong, just slightly off. N(3,-1)=12 instead of 13. Close enough to pass casual review, wrong enough to corrupt downstream results.

**EXP:** Inject a "subtly wrong" agent into a 5-agent fleet. The wrong agent produces answers that are off by 1-2 on a 2-digit number. Measure: how many rounds before the fleet detects the pattern? Does PBFT voting catch it? Does terrain-weighted voting help?

**IF A (PBFT catches it within 3 rounds):** Consensus is sufficient. Build it. → **Spoke 12**
**IF B (requires statistical analysis):** Need anomaly detection on verification votes. More complex. → **Spoke 11**
**IF C (never caught):** Subtle errors are undetectable by consensus. Need a different approach (provenance, audit trails). → **Spoke 14**

**→ NEXT:** Spoke 12 (deployment), Spoke 11 (calibration), Spoke 14 (audit system)

**PHASE TRANSITION:** If subtle errors are never caught by voting → the verification layer has a blind spot. The fleet needs a fundamentally different approach to quality assurance. This would be a negative result that changes the architecture.

---

## Spoke 14: The End-to-End Fleet Test

**Q:** Does the full architecture (registry + task atoms + self-org + verification) work as an integrated system?

**GROUND:** Every spoke tests one component. Spoke 14 tests the SYSTEM. No individual component has been tested in combination with all others.

**EXP:** Full fleet simulation: 5 agents register in fleet-registry. 20 tasks arrive as DO/DATA/DONE atoms. Agents self-select via task board. Results verified by PBFT. Measure: end-to-end accuracy, cost, latency, failure modes.

**IF A (system works at 80%+ accuracy):** Ship it. Start production deployment. → **DONE**
**IF B (system works but expensive):** Optimize. Identify the expensive component. → **Spoke 6**
**IF C (system fails at integration):** The components don't compose. Need architectural changes. → **Spoke 1** (restart)

**→ NEXT:** DONE (ship) or Spoke 6 (optimize) or Spoke 1 (restart)

**PHASE TRANSITION:** This is the FINAL spoke. If the system works end-to-end → we're done building and start deploying. If it fails → we loop back to whatever spoke the failure points to.

---

## The Wheel Map

```
Spoke 1 (Scale) ─────────────────→ Spoke 9 (Coordinator)
    │                                  │
    ↓                                  ↓
Spoke 3 (Real Models)           Spoke 12 (Task Board)
    │                                  │
    ↓                                  ↓
Spoke 4 (Conflicts) ──────────→ Spoke 13 (Quarantine)
    │                                  │
    ↓                                  ↓
Spoke 2 (Asymmetric Verify) → Spoke 10 (Pipeline) → Spoke 14 (End-to-End)
    │                                                      │
    ↓                                                      ↓
Spoke 11 (Calibration)         ───── DONE (Ship it!) ────→ or LOOP BACK
    │
    ↓
Spoke 5 (DATA Boundary) → Spoke 7 (Death Zone) → Spoke 8 (Model Templates)
    │
    ↓
Spoke 6 (Token Budget) ───────→ feeds into ALL spokes (cost constraint)
```

## Spoke Priority (Which to Run First)

| Priority | Spoke | Why | Blocks |
|----------|-------|-----|--------|
| **1** | Spoke 5 | DATA boundary determines tile design | Everything |
| **2** | Spoke 9 | Minimum coordinator determines fleet architecture | Spoke 12, 14 |
| **3** | Spoke 2 | Asymmetric verification determines Layer 3 cost | Spoke 10, 11 |
| **4** | Spoke 1 | Scale boundary validates/in validates coordinator | Spoke 9 |
| **5** | Spoke 11 | Calibration curve determines model selection | Spoke 2, 10 |
| **6** | Spoke 4 | Conflict resolution design | Spoke 12, 13 |
| **7** | Spoke 3 | Real-model self-organization | Spoke 9, 14 |
| **8** | Spoke 7 | Death zone characterization (fascinating but not blocking) | Spoke 5, 8 |
| **9** | Spoke 8 | Model-specific templates (follows from 5 and 7) | Spoke 6 |
| **10** | Spoke 6 | Token budget calculator (optimization, not foundation) | Spoke 14 |
| **11** | Spoke 10 | Tiered pipeline (follows from 2 and 11) | Spoke 14 |
| **12** | Spoke 12 | Task board protocol (follows from 9) | Spoke 14 |
| **13** | Spoke 13 | Quarantine (security layer, follows from 4) | Spoke 14 |
| **14** | Spoke 14 | End-to-end test (runs LAST, validates everything) | SHIPPING |

---

## Results So Far

| Spoke | Status | Key Finding |
|-------|--------|-------------|
| **1** | ✅ RUN | Self-org degrades at ALL scales (83% at 3 agents). Need coordinator. |
| **5** | ✅ RUN | Minimum sufficient DATA = formula + inputs (~35 tokens, 67%). Partial worked data = DEATH ZONE (0%). Full worked + context = 100%. |

*12 spokes remaining. Every result changes what we build next. The wheel spins.*

---

*This document is alive. Every experiment result updates it. Every spoke that gets answered connects to the next. The wheel doesn't stop until the fleet ships.*

---

## Session Results (2026-05-14)

| Spoke | Status | Key Finding | Impact |
|-------|--------|-------------|--------|
| **1** | ✅ RUN | Self-org degrades at ALL scales (83% max) | Coordinator REQUIRED |
| **4** | ✅ RUN | PBFT consensus works; corruption is self-revealing | Build consensus layer |
| **5** | ✅ RUN | Min DATA = formula + inputs (~35 tokens, 67%) | Tile budget set |
| **7** | ✅ RUN | **THE DEATH ZONE**: partial data = 0%, correct answer = 100%, wrong answer propagates | Publishable discovery |
| **9** | ✅ RUN | Round-robin = 94% coverage (minimal coordinator) | Fleet coordination design |
| **11** | ✅ RUN | phi4-mini conservative (100% on FALSE, 0% on TRUE); qwen3 can't speak | Need better verifier |
| **12** | ✅ RUN | PLATO reads work, writes need Oracle1 internal path | Local SQLite fallback |

### The Death Zone (Spoke 7) — The Session's Discovery

The most important finding. There is a region in DATA-space where more information makes the model LESS accurate:

```
Less info → 67% (model computes)
Middle info (partial steps) → 0% (DEATH ZONE)
More info (full worked + answer) → 100% (model trusts)
Wrong info → 0% (model propagates error)
```

This is not diminishing returns. It's active harm from partial information. The model treats intermediates as "corrections" to the formula and re-derives everything incorrectly.

**Tile design rule:** DATA is binary — either minimal (formula + inputs) or complete (full worked + answer). Never partial.

### Spoke Connections Discovered

```
Spoke 7 (Death Zone) ─── explains ───→ Spoke 5 (DATA cliff)
Spoke 4 (Consensus) ─── validates ───→ Spoke 9 (Round-robin coordinator)
Spoke 11 (Calibration) ─── gates ───→ Spoke 2 (Asymmetric verification)
Spoke 12 (Task Board) ─── blocked by ───→ PLATO gate endpoints
```

### Remaining Spokes (7 of 14)

| Priority | Spoke | Question |
|----------|-------|----------|
| **1** | **2** | Can cheap models verify expensive outputs? |
| **2** | **3** | Does real model specialization help self-organization? |
| **3** | **6** | Token budget per task type? |
| **4** | **8** | Does the Death Zone move between models? |
| **5** | **10** | Does tiered verification pipeline work? |
| **6** | **13** | Can we detect subtly wrong agents? |
| **7** | **14** | End-to-end fleet integration test |

*7 spokes remain. The Death Zone is the session's discovery. The wheel keeps spinning.*
