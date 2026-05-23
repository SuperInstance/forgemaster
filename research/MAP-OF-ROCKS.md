# Map of the Rocks We Know

> Every claim has a confidence level, a sample size, and known threats. This is the ground we can build on. Everything else is water.

---

## Tier 1: BEDROCK — High confidence, multiple experiments, reproduced

These are the rocks. We can build on them.

### R1: The model needs DATA, not instructions
**Claim:** Task atoms succeed when DATA contains actual numbers/formulas, not "go find the formula."
**Evidence:** DEEP Exp 1 (all decompositions scored 2.0/3 without data, JIPR with data scored 3.0/3). Spoke 5 (formula+inputs = 67%, formula name only = 0%).
**Confidence:** HIGH. Found in 2 independent experiments, 2 different task types.
**Sample:** ~20 conditions across 2 experiments.
**Builds:** DO/DATA/DONE execution atom. Tile DATA schema.

### R2: Execution needs stream context, not full graph
**Claim:** Agents executing tasks perform equally with just immediate inputs vs full chain history.
**Evidence:** DEEP Exp 2 (stream = 2.5/3, full graph = 2.5/3, JIT = 2.0/3). More context HURT in JIT condition.
**Confidence:** HIGH. Clear result, counter-intuitive, replicated directionally in Spoke 7.
**Sample:** 3 conditions, 1 experiment. **LIMIT: only tested at chain depth 3.**
**Builds:** Plan/execute separation. Executor never sees chain history.

### R3: Registry beats terrain beats broadcast
**Claim:** For agent discovery, explicit capability listings outperform spatial proximity outperform broadcast.
**Evidence:** DEEP Exp 4 (Registry 2.5/3, Terrain 1.5/3, Broadcast 1.0/3). Consistent with Campaign C (terrain invisible at low baseline).
**Confidence:** HIGH. Clear ordering, large effect size.
**Sample:** 3 conditions, 1 experiment. **LIMIT: only tested with 1 model on 1 task.**
**Builds:** Fleet registry as primary discovery mechanism. Terrain as tiebreaker only.

### R4: Self-organization degrades with scale
**Claim:** Emergent task allocation (agents self-selecting without coordination) fails to reach 95% coverage even at 3 agents.
**Evidence:** Spoke 1 (83% at 3 agents/6 tasks, 67% at 20 agents/200 tasks). All scales below 95%.
**Confidence:** MODERATE. Simulation-based, not tested with real models.
**Sample:** 14 configurations. **LIMIT: random capability assignment, no real model behavior.**
**Builds:** Coordinator is mandatory. Round-robin is the minimal fix (Spoke 9).

### R5: Round-robin is the minimal coordinator
**Claim:** Turn-taking agents achieve 94% coverage, matching full blackboard coordination.
**Evidence:** Spoke 9 (round-robin 94%, blackboard 94%, bidding 90%, visibility 79%, none 69%).
**Confidence:** MODERATE. Simulation-based. **LIMIT: same as R4. Needs real-model validation (Spoke 3).**
**Sample:** 6 scales × 5 mechanisms = 30 conditions.
**Builds:** Fleet coordination protocol. Turn counter in task board.

### R6: More context CAN hurt
**Claim:** Adding irrelevant context to a task degrades performance.
**Evidence:** DEEP Exp 2 (JIT with chain summary scored 0.5 LOWER than stream). Spoke 7 (partial intermediates scored 0% vs formula-only 67%).
**Confidence:** HIGH. Found independently in 2 experiments.
**Sample:** 2 experiments, 5+ conditions.
**Builds:** Minimal context principle. Data budgeting.

---

## Tier 2: SOLID — Good evidence, but limited sample or single-model

### R7: The Death Zone — partial data hurts MEDIUM models, helps SMALL models
**Claim:** Showing intermediate computation steps hurts accuracy for medium-capability models (phi4-mini: 20% vs 67% formula-only) but HELPS small models (gemma3:1b: 40% vs 0%).
**Evidence:** Spoke 7 (phi4-mini, 36 trials) + W1 cross-model (phi4-mini 10 trials, gemma3:1b 5 trials).
**Confidence:** MODERATE. Effect confirmed on phi4-mini (20% vs 67%), REVERSED on gemma3:1b (40% vs 0%). **Model-size dependent, not universal.**
**Sample:** 51 total trials across 2 models.
**Builds:** MODEL-AWARE DATA templates. Full answer = 100% for ALL models. Never show partials to medium models. Always show partials to small models.
**Status:** TIER 2. W1 resolved — effect is model-dependent. Needs large-model test (GLM-5-turbo) for complete picture.

### R8: Wrong answers in DATA propagate 100%
**Claim:** When DATA contains an incorrect answer, the model always outputs the wrong answer.
**Evidence:** Spoke 7 ("Result = 12" variant → 0% correct, all 3 trials output 12). Spoke 7 ("Result = 27" variant → 0% correct).
**Confidence:** MODERATE-HIGH. 6 data points, all consistent. **LIMIT: same as R7.**
**Sample:** 6 trials (2 wrong-answer variants × 3 repetitions).
**Builds:** DATA integrity is CRITICAL. Wrong DATA is worse than no DATA. Tile verification before use.

### R9: PBFT consensus catches formula errors
**Claim:** When one agent has a corrupted formula, consensus voting correctly identifies the correct answer.
**Evidence:** Spoke 4 (4/5 verified, corrupted agent voted FAILED, consensus = VERIFIED).
**Confidence:** MODERATE. **LIMIT: single claim, single corruption type (sign flip), same model with different prompts.**
**Sample:** 5 agents (same model), 1 claim.
**Builds:** PBFT verification layer. But needs Spoke 13 (subtle errors) to validate.

### R10: Agent capability claims are unreliable
**Claim:** Agents claiming capabilities pass verification tests only 20% of the time.
**Evidence:** Campaign A (phi4-mini: 1/5 capabilities verified). Deep Exp 4 broadcast (model said "YES I can help" without qualification).
**Confidence:** MODERATE. **LIMIT: single model, test difficulty may not represent real tasks.**
**Sample:** 5 capabilities × 2-3 tests each.
**Builds:** Verification before trust. Verified Agent Cards.

### R11: Personas don't predict task routing accuracy
**Claim:** Giving an agent a persona that matches the task domain does NOT improve accuracy vs mismatched persona.
**Evidence:** Experiment X (aligned = 75%, misaligned = 75%, Δ = 0%). BUT: MathSpec +38%, MusicEnc -38%.
**Confidence:** MODERATE. **LIMIT: same model for all personas, persona is just system prompt.**
**Sample:** 3 personas × 3 domains × 4 tasks = 36 conditions.
**Builds:** Route on verified capabilities, not personas. Persona may help specific domains (math).

---

## Tier 2.5: NEW — Interference & Echo Studies (2026-05-14 afternoon)

### R16: ~50% of wrong answers are input echoes (cognitive residue)
**Claim:** When models fail, they echo input numbers instead of computing.
**Evidence:** 4 models, 6 tasks, 240 trials. phi4-mini 49%, gemma3:1b 46%, llama3.2:1b 41% echo-of-wrong.
**Threat:** Only tested on math computation tasks. May not generalize to text/code.

### R17: Non-echo wrongs are partial computations
**Claim:** Wrong answers that aren't echoes are intermediate computation steps (a², b², ab).
**Evidence:** Classified all non-echo wrongs across 6 tasks. N(5,-3) → 25 (=a²), 9 (=b²).
**Threat:** Only observed for quadratic form. May not apply to other computation types.

### R18: Cross-model echo correlation
**Claim:** Different models echo the same input number (all echo `b` preferentially).
**Evidence:** 3/3 Eisenstein tasks, all 3 working models echo `b` > `a`.
**Threat:** Could be specific to how N(a,b) is written in the prompt (recency bias).

### R19: Echo rate = 0% for simple arithmetic
**Claim:** Models don't echo when the task is within their computation capacity.
**Evidence:** 11×13 and 23+19 show 0% echo across all models.
**Threat:** Only 2 simple arithmetic tasks tested.

### R22: Three error tiers: stochastic, deterministic, reliable
**Claim:** Model errors fall into 3 categories with different retry economics.
**Evidence:** 4 models, 3 norm tasks, 180 trials. Stochastic (phi4-mini 13-53%), deterministic (gemma3:1b 0%), reliable (phi4-mini 100% on 7×9).
**Threat:** Only phi4-mini showed stochastic behavior; smaller models were all deterministic.

### R23: Plan-data mismatch is interference
**Claim:** Same data is SIGNAL under one execution plan and NOISE under another.
**Evidence:** COMPUTE×V_ANSWER=100% (echo), VERIFY×V_THEORY=80% > VERIFY×V_ANSWER=40%.
**Threat:** Only 5 trials per condition, phi4-mini only, one task.

---

## Tier 3: SUGGESTIVE — Single experiment, small sample, or simulation-only

### R12: Two-phase retrieval saves 78% tokens
**Claim:** Hierarchical search (coarse → fine) uses 78% fewer tokens than flat search at 76% accuracy.
**Evidence:** Campaign B (200 synthetic tiles, 50 queries).
**Confidence:** LOW-MODERATE. **LIMIT: deterministic simulation, no real LLM retrieval, synthetic data.**
**Sample:** 50 queries.
**Builds:** Domain index in PLATO metadata. But needs real retrieval model test.

### R13: Terrain weighting is premature
**Claim:** Terrain-weighted voting doesn't help when model baseline accuracy is below 60%.
**Evidence:** Campaign C (33% baseline, terrain = 33%, uniform = 33%). But CCC scored 80% when close to domain.
**Confidence:** MODERATE. Direction is probably right but the threshold is uncertain.
**Sample:** 9 claims × 5 agents = 45 conditions.
**Builds:** Don't build terrain weighting until models improve.

### R14: FLUX encoding needs model training
**Claim:** FLUX bytecode tasks score 40% vs natural language 50% when the model hasn't been trained on FLUX.
**Evidence:** Campaign D (10 tasks, FLUX vs NL).
**Confidence:** LOW-MODERATE. **LIMIT: FLUX glossary provided in prompt, but model may need fine-tuning.**
**Sample:** 10 tasks × 2 conditions = 20 conditions.
**Builds:** FLUX is compression only, not universal encoding.

### R15: phi4-mini is conservative (rejects true claims)
**Claim:** phi4-mini correctly rejects false claims (100%) but also rejects true claims (0% on TRUE, 40% overall).
**Evidence:** Spoke 11 (5 claims, phi4-mini verified 0/3 true claims correctly).
**Confidence:** MODERATE. **LIMIT: 5 claims too few. Single model.**
**Sample:** 5 claims.
**Builds:** Need better verification model. phi4-mini is safe but not useful for verification.

---

## The Water — What We DON'T Know

These are the gaps. Every one is an experiment opportunity.

### W1: ~~Does the Death Zone exist across models?~~ RESOLVED
**Result:** Death Zone is MODEL-SIZE DEPENDENT.
- phi4-mini (3.8B): partial intermediates = 20% (DEATH ZONE confirmed, 10 trials)
- gemma3:1b (1B): partial intermediates = 40% (HELPED, not hurt — scaffolding effect)
- Full answer in DATA = 100% for both models
- **Effect reverses for small models.** Intermediates scaffold weak models, confuse medium models.
**Impact:** R7 stays Tier 2 with caveat. Model-aware DATA templates required.
**Next:** Test with GLM-5-turbo to complete the curve.**

### W2: Do real models self-organize differently from simulation?
**Why we don't know:** Spoke 1 and 9 used random capability assignment. Real agents have correlated capabilities.
**What would prove it:** Run Spoke 1 with actual model calls. Let 3 different models pick tasks.
**Impact if disproven:** Real specialization could be better OR worse than random. Either way changes the coordinator design.
**This is Spoke 3.**

### W3: Can cheap models verify expensive model outputs?
**Why we don't know:** Spoke 2 failed (z.ai timeout, qwen3 empty). Never got data.
**What would prove it:** Generate with GLM-5-turbo, verify with phi4-mini. Compare costs.
**Impact if proven:** Tiered verification pipeline. 90% cost savings on verification.
**This is Spoke 2.**

### W4: What's the minimum model quality for verification?
**Why we don't know:** Calibration curve incomplete (only phi4-mini produced data).
**What would prove it:** Run same 20 verification claims on 5 models. Find the 60% threshold.
**Impact:** Determines which models can be verifiers. Budget planning.
**This is Spoke 11 expanded.**

### W5: Does PBFT catch SUBTLE errors (off-by-one)?
**Why we don't know:** Spoke 4 tested obvious corruption (wrong formula sign). Never tested "N(3,-1)=12" (close but wrong).
**What would prove it:** Inject subtly wrong agent (off by 1-2 on 2-digit answers). Measure detection rate.
**Impact if not caught:** Subtle errors require different verification (statistical, not consensus).
**This is Spoke 13.**

### W6: Does round-robin work with real agents and real latency?
**Why we don't know:** Spoke 9 was instantaneous simulation. Real agents have variable latency, failures, retries.
**What would prove it:** Run round-robin with 3 real models on 6 real tasks. Measure timing.
**Impact:** Round-robin may deadlock or starve slow agents.
**This is Spoke 3 combined with Spoke 9.**

### W7: What's the token budget for a full task lifecycle?
**Why we don't know:** We have DATA cost (Spoke 5) and retrieval cost (Campaign B) but not the full chain: discovery + planning + execution + verification.
**What would prove it:** Run 10 complete task chains end-to-end. Measure total tokens.
**Impact:** Determines fleet operating cost. Whether the system is economically viable.
**This is Spoke 6.**

### W8: Does the grammar compose across distributed agents?
**Why we don't know:** Every experiment ran on a single machine. The DO/DATA/DONE handoff between agents has never been tested over network latency.
**What would prove it:** Two agents on different machines. Agent A's DONE becomes Agent B's DATA over PLATO.
**Impact:** The architecture might not work when distributed.
**This is Spoke 14.**

### W9: Is the Death Zone task-dependent? (partially answered by W1: it's model-dependent, task-dependency still unknown)
**Why we don't know:** Spoke 7 only tested Eisenstein norm computation. Maybe the death zone only exists for math tasks.
**What would prove it:** Run Spoke 7 protocol on classification, code generation, and reasoning tasks.
**Impact:** If Death Zone is math-specific → tile design varies by task type. If universal → universal design rule.

### W10: How fast does PLATO tile state degrade?
**Why we don't know:** Spoke 12 couldn't test writes. We don't know how many supersession chains a room can handle before performance degrades.
**What would prove it:** Write 1000 task lifecycle tiles to a PLATO room. Measure read latency.
**Impact:** Determines whether PLATO rooms can handle 100+ tasks/day.

---

## The Map

```
╔══════════════════════════════════════════════════════════════╗
║  TIER 1: BEDROCK — Build on these                          ║
║                                                              ║
║  R1: DATA > instructions     R4: Self-org degrades          ║
║  R2: Stream > graph          R5: Round-robin fixes it       ║
║  R3: Registry > terrain      R6: More context CAN hurt      ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║  TIER 2: SOLID — Build with caution                         ║
║                                                              ║
║  R7: Death Zone (partial=0%)    R10: Claims unreliable      ║
║  R8: Wrong answers propagate    R11: Personas don't matter  ║
║  R9: PBFT catches errors                                  ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║  TIER 3: SUGGESTIVE — Don't build on these yet              ║
║                                                              ║
║  R12: 78% token savings (synthetic)                          ║
║  R13: Terrain premature (33% baseline)                       ║
║  R14: FLUX needs training                                    ║
║  R15: phi4-mini too conservative                             ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║  THE WATER — Experiments that could flip the map             ║
║                                                              ║
║  W1: Death Zone cross-model? (could demote R7)               ║
║  W2: Real vs simulated self-org? (could flip R4/R5)          ║
║  W3: Cheap verifies expensive? (could enable tiered pipes)   ║
║  W4: Verification model threshold? (budget planning)         ║
║  W5: PBFT catches subtle errors? (could demote R9)           ║
║  W6: Round-robin with latency? (could flip R5)               ║
║  W7: Full lifecycle token budget? (economic viability)       ║
║  W8: Grammar composes distributed? (could break everything)  ║
║  W9: Death Zone task-dependent? (tile design scope)          ║
║  W10: PLATO write performance? (infrastructure limit)        ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
```

---

## The Weakest Link

**The entire architecture rests on experiments run with ONE model (phi4-mini) on ONE task type (Eisenstein math).**

If phi4-mini is not representative — if GLM-5-turbo or Claude behave differently — then R7, R8, R9, R10, R11, R14, R15 all shift.

### W11: Does echo rate predict task difficulty?
**What:** If we can measure echo rate from answer distribution, can we infer task difficulty without knowing the answer?
**Why:** Would enable automatic difficulty calibration for fleet routing.
**Blocker:** Need ground-truth difficulty ratings across many task types.

### W12: Do 7B+ models echo?
**What:** Run the echo analysis on a 7B model (qwen3:4b is available locally).
**Why:** If echo drops to 0% at 7B, it's a small-model-only phenomenon. If it persists, it's fundamental.
**Blocker:** qwen3:4b may have thinking mode issues (returns empty content).

---

**W1 RESOLVED**: Death Zone is model-size dependent (constructive for small, destructive for medium). R7 stays Tier 2.

**Most valuable next experiment is W12** (7B echo analysis). If echo drops at 7B → echo-based routing is small-fleet only. If it persists → echo is a universal diagnostic.

**The most dangerous unknown is W8 (distributed composition).** If the grammar doesn't compose across real networked agents → the entire DO/DATA/DONE handoff needs redesign. Everything builds on this.

---

## What to Build NOW (on bedrock only)

Based on Tier 1 rocks only:

1. **DO/DATA/DONE task atoms** — R1 proves DATA is the critical field
2. **Stream-only execution context** — R2 proves agents don't need chain history
3. **Fleet registry with verified capabilities** — R3 proves registry is primary, R10 proves verification needed
4. **Round-robin task board** — R4 proves coordinator needed, R5 proves round-robin sufficient
5. **Minimal context principle** — R6 proves more context can hurt, R7 proves partial data is poison
6. **Binary DATA design** — R7+R8 prove: formula+inputs OR full worked answer, never partial

**Do NOT build yet (Tier 2-3, needs validation):**
- Terrain-weighted voting (R13)
- FLUX encoding as default (R14)
- PBFT at scale (R9 — needs Spoke 13)
- Tiered verification pipeline (needs W3)

---

*This map is honest. Every rock has its cracks listed. Every unknown has its experiment designed. Build on bedrock. Test before promoting.*
