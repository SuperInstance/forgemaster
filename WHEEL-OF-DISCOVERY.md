# Wheel of Discovery

> **Not a document. A generative system.**
> Every answer here opens the next question. Every experiment changes what we build.
> Date: 2026-05-14 | Grounded in: Campaigns A–D, Exp X, DEEP-RESULTS, RESULTS

---

## The Hub: What We Actually Know

Before the spokes, the fixed point — what the data has confirmed hard enough to build on:

| Confirmed Truth | Evidence |
|----------------|----------|
| DO/DATA/DONE is the execution atom | DEEP Exp 1, RESULTS Exp 1 |
| CHAIN/CLAIM/ORDER is the planning atom | DEEP Exp 2 |
| REGISTRY > TERRAIN > BROADCAST for discovery | DEEP Exp 4 |
| Agents self-organize without frameworks | RESULTS Exp 7: 6/6, 2/2/2, zero duplicates |
| 78% token savings via two-phase retrieval | Campaign B |
| 80% of declared capabilities are false | Campaign A |
| Terrain weighting is invisible at 33% baseline | Campaign C |
| FLUX requires opcode context to match NL | Campaign D |
| Personas are domain-specific modulators, not routers | Experiment X |
| More context can hurt execution | DEEP Exp 2: JIT scored 0.5 lower |
| Perspectives improve retrieval by 2× | RESULTS Exp 1: 3.0/3 vs 1.5/3 |

**These are the spokes' starting points, not their destinations.**

---

## The Spokes

Each spoke is a question we DON'T know the answer to,
grounded in evidence we DO have,
answerable by a concrete experiment.

---

### SPOKE 1 — The Grammar Stability Question

**QUESTION:** Does DO/DATA/DONE remain the correct execution atom when DATA must flow through 5+ chain steps, accumulating each predecessor's output as input?

**GROUNDING:** DEEP Exp 2 tested a 5-task chain but only evaluated the *final* step. It confirmed that stream context (just the previous output) matched full-graph context for the terminal agent. But the intermediate steps were never evaluated independently. The finding is valid for step N. It's untested for steps N-2, N-3.

**EXPERIMENT:**
```
Design: 10-step computational chain (Eisenstein coordinate transforms)
Conditions:
  A. Pure stream: each agent sees only immediate predecessor output
  B. Accumulating DATA: each agent's DONE output is verbatim appended to next DATA field
  C. Compressed DATA: a summarizer agent distills accumulation every 3 steps
  D. Full graph: every agent sees all prior outputs

Measure:
  - Error rate at each step (not just final)
  - Error ACCUMULATION: does step 5 error rate predict step 10 rate?
  - Where in the chain does performance first drop below 70%?
```

**OUTCOMES:**
- **If stream degrades past step 5:** The grammar needs a DATA-refresh primitive — a normalization step that re-anchors floating-point DATA before it drifts into noise. Build it.
- **If stream holds all 10 steps:** The atom is stable. Ship it. The 5-step bound in DEEP Exp 2 was not a limit, just a sample.
- **If accumulation (B) outperforms stream (A):** The grammar is wrong about what DATA means — it's not just immediate inputs, it's provenance. Every DONE must carry its own DATA as metadata.

**NEXT QUESTION IT OPENS → SPOKE 14: The DONE-to-DATA Fidelity Question**

---

### SPOKE 2 — The Verification Depth Question

**QUESTION:** What is the minimum number of independent cross-verifiers needed to reliably catch hallucination, and does that number depend on the task type?

**GROUNDING:** Campaign A — PhiMini passed 2/2 direct verification tests, then failed a differently-framed cross-check. Single-agent verification is insufficient. DEEP Exp 4 showed broadcast fails spectacularly (agent claims capability without qualification). PBFT requires 2f+1 for Byzantine fault tolerance — but that assumes *any* agent can verify *any* claim, which Campaign A contradicts. Terrain-proximate agents may be better verifiers.

**EXPERIMENT:**
```
Design: 15 specific mathematical claims (5 easy, 5 medium, 5 hard)
Conditions per claim:
  1-verifier: one agent cross-checks
  2-verifiers: majority of 2 (unanimous required)
  3-verifiers: majority of 3 (f+1 = 2 agree)
  5-verifiers: PBFT quorum (2f+1 = 4 agree)

Vary verifier type:
  A. Same model verifying
  B. Different model family verifying
  C. Domain-proximate vs domain-distant verifiers

Measure:
  - Accuracy vs gold truth at each depth
  - Marginal accuracy gain from N → N+1 verifiers
  - Where does the accuracy curve flatten?
```

**OUTCOMES:**
- **If 2 verifiers match 5:** Cheap verification is possible. Build a "dual-verifier" default with full PBFT only for CAUSAL reasoning types. This halves verification cost.
- **If accuracy keeps climbing past 5:** Full PBFT is mandatory. Every fleet deployment needs ≥5 agents just for verification quorum. Minimum fleet size is now a hard constraint.
- **If domain-proximity matters for verifiers:** Terrain is not just a routing tiebreaker — it's a verification quality signal. Spoke 3 becomes urgent.

**NEXT QUESTION IT OPENS → SPOKE 9: The Capability Decay Question**

---

### SPOKE 3 — The Terrain Threshold Question

**QUESTION:** At what model baseline accuracy does terrain-weighted voting first produce a measurably different outcome from uniform voting?

**GROUNDING:** Campaign C — terrain weighting produced zero different outcomes at 33% baseline. CCC scored 80% on infrastructure claims when terrain-close (dist ≤ 2) vs 44% overall. The signal exists but is invisible at current model quality. Campaign C's own recommendation: test with GLM-5-turbo or similar. This is the one falsified hypothesis that might *unfalsify* — but only at a different layer.

**EXPERIMENT:**
```
Design: Replicate Campaign C with 4 models at different baseline capabilities
Models (ascending capability):
  A. phi4-mini: ~33% baseline (current data)
  B. qwen3:4b (with /no_think): ~TBD
  C. GLM-5-turbo (non-reasoning): ~TBD
  D. phi4 (full): ~TBD

Same 9 claims, same 4 domains, same terrain layout.

Measure per model:
  - Uniform voting accuracy
  - Terrain-weighted voting accuracy
  - Delta (when does terrain start moving the needle?)
  - CCC-style domain proximity effect magnitude

Find: the accuracy threshold where terrain weighting first differs from uniform.
```

**OUTCOMES:**
- **If threshold is ≥70%:** Terrain is a late-game optimization. Don't build terrain weighting until registry verification shows agents at 70%+. Everything before that is wasted infrastructure.
- **If threshold is ≥40%:** We're closer than we think. Start building terrain infrastructure now.
- **If threshold depends on domain (not overall baseline):** Terrain should be activated *per-domain*, not globally. A fleet might use terrain for math and ignore it for infra on the same hardware.

**NEXT QUESTION IT OPENS → SPOKE 7: The Domain Template Question**

---

### SPOKE 4 — The Context Poisoning Question

**QUESTION:** Does irrelevant context hurt more as chains get longer — and if so, is there a chain depth at which even stream context becomes harmful?

**GROUNDING:** DEEP Exp 2 — the JIT condition (chain summary added) scored 0.5 lower than stream context because the summary "introduced irrelevant abstractions that distracted from the simple distance calculation." Stream context, which passes only the immediate predecessor output, matched full-graph context. The finding was at step 5 of a 5-step chain. What happens at step 15?

**EXPERIMENT:**
```
Design: Chains of length 3, 7, 15, 30 steps
Each step is a valid computation that PRODUCES output the next step COULD use.

Condition A (clean stream): each agent sees only immediate predecessor output
Condition B (noisy stream): each agent sees output + one irrelevant chain step
Condition C (growing stream): each agent sees all prior outputs (accumulates)

Measure:
  - Task accuracy at each chain length
  - Which condition degrades first?
  - At what chain length does stream context (A) start to degrade?
  - Token count vs accuracy curve
```

**OUTCOMES:**
- **If stream (A) degrades past length 7:** The architecture needs a DATA normalization layer at fixed intervals. "Reset points" that strip accumulated context and re-anchor from the original task.
- **If stream (A) holds to length 30:** The stream context model is robust. The JIT finding in DEEP Exp 2 was specifically about *conceptual abstractions* being harmful, not about chain length.
- **If noisy stream (B) degrades much faster than clean stream (A):** Context injection attacks are viable. Fleet security model needs a DATA purity requirement: no unsigned injections into the DATA field.

**NEXT QUESTION IT OPENS → SPOKE 1: The Grammar Stability Question** (the rim closes here)

---

### SPOKE 5 — The FLUX Crossover Question

**QUESTION:** How many FLUX examples in context does an agent need before FLUX encoding matches or beats natural language, and can that threshold be met by a system prompt alone?

**GROUNDING:** Campaign D — FLUX scored 40% vs NL's 50%. But FLUX matched NL on medium/hard tasks where the prompt included a glossary. The glossary cost ~100 tokens. At 1000+ tasks/day, FLUX offers 50× compression. The question is whether the 100-token glossary can be front-loaded into a system prompt (paid once per session, not per task).

**EXPERIMENT:**
```
Design: 30 tasks (10 easy, 10 medium, 10 hard)

Conditions:
  A. Zero FLUX context: raw FLUX opcodes, no explanation
  B. 5-example context: 5 worked FLUX examples in system prompt
  C. 10-example context: 10 worked examples
  D. 20-example context: 20 worked examples
  E. Full glossary: current Campaign D condition (100-token glossary)
  F. Natural language baseline

Measure:
  - Accuracy per condition
  - Crossover point (where FLUX first matches NL)
  - System prompt token cost vs per-task token savings
  - ROI: break-even task count
```

**OUTCOMES:**
- **If crossover at 10 examples (~150 tokens system prompt):** FLUX becomes viable at ~7 tasks/session to break even. For long-running agents (100+ tasks), FLUX is the correct default encoding.
- **If crossover requires 20+ examples:** FLUX is only worth it for agents running 50+ tasks/session. Rare for current fleet size.
- **If FLUX never crosses NL even with full glossary:** Campaign D was wrong about the medium/hard parity. FLUX is dead. Kill it everywhere. The 50× compression claim is irrelevant if accuracy is below NL.

**NEXT QUESTION IT OPENS → SPOKE 8: The DATA Precision Floor Question**

---

### SPOKE 6 — The Self-Organization Collapse Question

**QUESTION:** What is the maximum task room size (tasks × agents) at which emergent self-organization remains reliable, and what failure mode appears first?

**GROUNDING:** RESULTS Exp 7 — 6 tasks, 3 agents, perfect result (6/6, 2/2/2 load, zero duplicates). But this is the most controlled possible condition. Real fleet rooms will have 20+ tasks, agents with overlapping skills, ambiguous task descriptions, and no guaranteed persona alignment. The experiment didn't test any of these stress conditions.

**EXPERIMENT:**
```
Phase 1 — Scale tasks:
  6 tasks / 3 agents (baseline from Exp 7)
  12 tasks / 3 agents
  20 tasks / 3 agents
  50 tasks / 3 agents

Phase 2 — Scale agents:
  6 tasks / 6 agents (more agents than optimal)
  6 tasks / 2 agents (undercapacity)

Phase 3 — Ambiguity:
  6 tasks / 3 agents, but 2 tasks could belong to any persona
  6 tasks / 3 agents, but agent personas partially overlap

Measure per condition:
  - Task coverage (were all tasks attempted?)
  - Duplication rate (same task by two agents)
  - Load balance (tasks per agent)
  - Time to first pickup (tasks left unclaimed)
```

**OUTCOMES:**
- **If failure appears at 12+ tasks:** Self-organization needs a coordinator tile once rooms exceed ~10 tasks. The COORDINATION tile is not optional above this threshold.
- **If failure appears through ambiguity (not scale):** Task descriptions need a mandatory "domain tag" field. The self-organization failure mode is semantic, not quantitative. Build a task taxonomy.
- **If duplication is the failure mode (not gaps):** Agents need a "claim-and-lock" primitive — a simple mechanism to mark a task in progress before executing. This is the fleet's concurrency primitive.

**NEXT QUESTION IT OPENS → SPOKE 12: The Orchestration Trigger Question**

---

### SPOKE 7 — The Domain Template Prediction Question

**QUESTION:** Which properties of a domain predict whether persona framing helps, hurts, or is neutral — and can an agent classify its own task domain before choosing a framing?

**GROUNDING:** Experiment X — math persona: +38%, music persona: -38%, infra persona: ±0%. The aggregate was 0% (cancellation), hiding the structure. The hypothesis: persona helps in domains requiring *precise symbolic reasoning* and hurts in domains where the model has *strong but inaccurate priors* (it "knows" music exists but doesn't know Eisenstein norm properties the same way).

**EXPERIMENT:**
```
Design: 10 distinct domains (math, music, infra, biology, law, geography,
        history, physics, code, NLP)

For each domain:
  - 6 tasks (2 easy, 2 medium, 2 hard)
  - Compare: persona-framed vs neutral framing

Analyze:
  - Positive persona domains (persona helps): what do they share?
  - Negative persona domains (persona hurts): what do they share?
  - Neutral domains: are they high-confidence or low-confidence?

Classify domains by:
  - Symbolic vs semantic reasoning
  - Model confidence (does the model hedge?)
  - Training data density (proxy: query perplexity)
```

**OUTCOMES:**
- **If positive domains cluster around "symbolic precision":** Build a `reasoning_type: SYMBOLIC` field on tiles. SYMBOLIC tasks get persona framing by default; SEMANTIC tasks don't. This is a 2-line change to task routing with Experiment X's 38% improvement locked in.
- **If negative domains cluster around "high model confidence + wrong priors":** The correct fix is *calibration*, not templates. Agents need to self-report confidence. A miscalibrated-confident model shouldn't use persona framing for its overconfident domain.
- **If no pattern:** Domain templates are ungeneralizable. Maintain a manual whitelist (math: YES, music: NO). Start with 3 entries and add evidence before expanding.

**NEXT QUESTION IT OPENS → SPOKE 3: The Terrain Threshold Question** (terrain may correlate with template effect)

---

### SPOKE 8 — The DATA Precision Floor Question

**QUESTION:** Is there a minimum level of DATA specificity below which task accuracy collapses, and does a worked example in DATA outperform a formula alone?

**GROUNDING:** DEEP Exp 1 — DO/NEED/DONE with NEED as "where to find the formula" failed the same as raw task. DO/DATA/DONE with DATA as the actual formula improved quality. But the experiments tested the *presence* of data, not the *level* of precision. Does `formula: a²-ab+b²` outperform `Eisenstein norm formula`? Does `formula + 1 worked example` outperform formula alone?

**EXPERIMENT:**
```
Design: 20 mathematical tasks, 5 precision conditions:

Level 0: Concept name only ("Eisenstein norm of (2,-1)")
Level 1: Formula name ("Use Eisenstein norm formula: a²-ab+b²")
Level 2: Formula + definition ("a²-ab+b² where a,b are the two coordinates")
Level 3: Formula + worked example ("a²-ab+b²; example: norm(1,1) = 1-1+1 = 1")
Level 4: Formula + 3 worked examples

Measure:
  - Accuracy per level
  - Token cost per level
  - Crossover between levels (where does adding precision stop helping?)
```

**OUTCOMES:**
- **If Level 2 matches Level 4:** Minimum viable DATA is formula + definition. One worked example is sufficient. The DATA field should have a SCHEMA: `{formula, definition}`. Build it.
- **If Level 3 (1 worked example) is the inflection point:** Every tile's DATA field must include one worked example. This is a tile validation rule. Tiles without examples fail earmark beta testing.
- **If the curve is monotonic (each level adds):** Richer DATA always helps. Token budget becomes the binding constraint. Two-phase retrieval (Campaign B) is the correct answer to this constraint — use cheap retrieval to find tiles, then pay for full DATA.

**NEXT QUESTION IT OPENS → SPOKE 11: The Retrieval Boundary Question**

---

### SPOKE 9 — The Capability Decay Question

**QUESTION:** Do verified agent capabilities remain stable over time, or do they decay — and if decay, how fast and in what pattern?

**GROUNDING:** Campaign A — PhiMini passed 2/2 verification tests then failed a differently-framed cross-check. This could mean: (a) the test was too easy, or (b) the capability is real but framing-sensitive, or (c) capabilities are fundamentally unstable across sessions. None of these have been distinguished. All current fleet plans assume that a capability verified at time T is valid at time T+N. This assumption is untested.

**EXPERIMENT:**
```
Design: Verify 3 agents on 5 capabilities each (Campaign A methodology)
Re-verify at: 1 hour, 24 hours, 1 week

Vary verification conditions:
  A. Same test, same framing → measures raw stability
  B. Same test, different framing → measures framing sensitivity
  C. Different test, same capability → measures generalization

Measure:
  - Pass rate variance across time
  - Pass rate variance across framing
  - Which capabilities are most stable? (math vs. code vs. verification)
```

**OUTCOMES:**
- **If capabilities are stable (±5% variance over 1 week):** Verify once at fleet join. Background re-verification is overhead without benefit. Registry entries get 1-week TTL.
- **If capabilities are framing-sensitive (±30% variance by framing):** Verification must include 3+ framings to establish a real pass rate. The single Campaign A test per capability is insufficient. Double verification cost.
- **If capabilities decay over time:** Fleet registry needs a heartbeat-verification protocol — agents passively re-verify during idle time. The capability score is a moving average, not a snapshot.

**NEXT QUESTION IT OPENS → SPOKE 2: The Verification Depth Question** (re-closes the loop)

---

### SPOKE 10 — The Multi-Agent Convergence Question

**QUESTION:** When multiple agents independently compute the same task from the same DATA, how often do their DONE outputs agree — and does the agreement rate predict output correctness?

**GROUNDING:** RESULTS Exp 7 — agents self-organized without duplicating tasks. But the experiment was designed to prevent overlap. The architecture currently routes each task to exactly one agent. A fundamentally different architecture is possible: send every task to 2+ agents, take the majority answer. This is expensive but might be cheaper than full PBFT verification. We have no data on inter-agent agreement rates.

**EXPERIMENT:**
```
Design: 30 tasks (10 easy, 10 medium, 10 hard)
Send each task to 3 independent agents simultaneously (no communication)

Models:
  - phi4-mini × 3 (same model, independent calls)
  - phi4-mini + qwen3:4b + GLM-5-turbo (different models)

Measure:
  - Agreement rate per difficulty level
  - Agreement rate per task type (CAUSAL vs COMPARISON vs SUMMARY)
  - Correlation between agreement and correctness
    (if 3/3 agree → correct? if 2/3 agree → correct at what rate?)
  - Token cost vs accuracy trade-off vs single-agent baseline
```

**OUTCOMES:**
- **If 3/3 agreement predicts correctness at ≥90%:** Majority vote is the verification layer. Replace PBFT with "send to 3, take majority." Token cost is 3× but accuracy is 90%. Simpler and possibly cheaper than full PBFT verification infrastructure.
- **If agreement rate is low even on easy tasks (<50% 3/3 agreement):** Models are non-deterministic enough that voting is unreliable. PBFT with verification tasks (not answer duplication) is the right approach.
- **If different-model ensemble outperforms same-model ensemble:** Model diversity is a first-class architectural concern. Fleet diversity is not aesthetic — it's a verification quality lever.

**NEXT QUESTION IT OPENS → SPOKE 2: The Verification Depth Question**

---

### SPOKE 11 — The Retrieval Boundary Question

**QUESTION:** When tasks explicitly require knowledge from adjacent E12 domains (cross-domain tasks), does the 24% miss rate from Campaign B's hierarchical retrieval spike unacceptably?

**GROUNDING:** Campaign B — hierarchical retrieval (domain + neighbors, ~44 tiles) misses 24% of flat-search results. The missing tiles are "in adjacent domains that the coarse filter excludes." For tasks that happen to live cleanly within one domain, this is acceptable. But what fraction of real fleet tasks are cross-domain? And when they are, does the miss include the one tile that contains the correct answer?

**EXPERIMENT:**
```
Design: 50 queries explicitly designed to require tiles from 2+ domains
Compare:
  A. Hierarchical (domain + neighbors): current Campaign B approach
  B. Hierarchical + cross-domain escalation: level 1 + adjacent-domain level 1
  C. Flat scan: ground truth

Measure:
  - Miss rate for cross-domain queries (vs 24% for within-domain)
  - Token cost for condition B vs C
  - Whether the missed tile is the TOP-1 answer or a secondary result

Also measure: what fraction of real queries from RESULTS Exp 7 were cross-domain?
```

**OUTCOMES:**
- **If cross-domain miss rate spikes to ≥50%:** Hierarchical retrieval needs fuzzy domain boundaries. E12 domain definitions must overlap — a tile in constraint-theory also indexes under math. Two-phase retrieval can't use hard domain partitions.
- **If cross-domain B (escalation) achieves <10% miss at reasonable token cost:** Build "cross-domain escalation" as a standard level 1.5 step. The agent asks "is this multi-domain?" before choosing retrieval depth.
- **If most real queries are within-domain:** The 24% miss is a theoretical concern, not a practical one. Ship Campaign B's result as-is. Revisit when agents report retrieval failures.

**NEXT QUESTION IT OPENS → SPOKE 8: The DATA Precision Floor Question** (quality of retrieved tile matters)

---

### SPOKE 12 — The Orchestration Trigger Question

**QUESTION:** Can an agent recognize when a task exceeds its capacity and emit a signal requesting coordination — without being explicitly told it's over-capacity?

**GROUNDING:** RESULTS Exp 7 — agents self-organized with perfect load balance (2/2/2). The architecture says: "add COORDINATION tile only when tasks have dependencies, exceed capacity, or require verification." But who adds the COORDINATION tile? If agents must be told explicitly that a task exceeds capacity, the architecture needs a human (or orchestrator) in the loop. If agents can self-report, the architecture is truly self-organizing.

**EXPERIMENT:**
```
Design: Tasks at 4 difficulty tiers (20%, 80%, 120%, 200% of agent capacity)
  - 20%: trivially easy (agent should pick up without comment)
  - 80%: within capacity (should complete cleanly)
  - 120%: mildly over (agent should complete but show hedging/uncertainty)
  - 200%: far over (should ideally refuse or request help)

Conditions:
  A. No signal mechanism: agent responds or fails silently
  B. Confidence prompt: "Rate your confidence 1-10 before answering"
  C. Refusal mechanism: "If this task requires more than you can do, say ESCALATE"

Measure:
  - Does confidence rating (B) predict correctness?
  - Do agents self-escalate (C) at 120%? at 200%?
  - False escalation rate: healthy tasks refused?
```

**OUTCOMES:**
- **If confidence ratings predict correctness (r > 0.7):** Add a mandatory confidence field to DONE. High-confidence outputs skip verification; low-confidence outputs trigger it. This cuts verification cost proportionally to fleet accuracy.
- **If self-escalation works at 200% but not 120%:** Agents can identify severe overload but not mild overload. Fleet needs a verification layer at 80% of capacity — don't rely on self-reporting for edge cases.
- **If no self-escalation and no confidence signal:** Agents are opaque. DONE output must always go through verification. Orchestration cannot be avoided. The Exp 7 result was not general — it worked because capacity was never exceeded.

**NEXT QUESTION IT OPENS → SPOKE 6: The Self-Organization Collapse Question**

---

### SPOKE 13 — The Stale Registry Question

**QUESTION:** When an agent goes offline but remains in the registry, how does the fleet fail — gracefully (timeout + reroute) or silently (task assigned, no output, no error)?

**GROUNDING:** DEEP Exp 4 — Registry scored 2.5/3 because it correctly matched capability to task. But the experiment assumed the registry was accurate and agents were online. In a real fleet, agents crash, restart, or become network-partitioned. The registry-first architecture has no tested failure mode for stale entries.

**EXPERIMENT:**
```
Design: Fleet of 4 agents (1 will be artificially taken offline mid-experiment)

Phase 1: Normal routing — all agents online, 10 tasks, validate routing works
Phase 2: Kill agent B silently (no registry update)
Phase 3: Route 5 tasks that would normally go to agent B

Conditions:
  A. No timeout: wait indefinitely
  B. 10-second timeout with reroute: next registry match
  C. Heartbeat-gated routing: only route to agents with recent heartbeat

Measure:
  - Time to detect failure per condition
  - Task recovery rate
  - False positive rate (live agents flagged as stale)
```

**OUTCOMES:**
- **If silent failure (condition A) causes tasks to be permanently lost:** Heartbeat protocol is mandatory infrastructure, not optional. Add heartbeat to P1 build priority. An unverified registry entry is as dangerous as an unverified capability claim.
- **If 10-second timeout + reroute (condition B) recovers all tasks:** Timeout threshold is the only infrastructure needed. Registry accuracy is less critical than previously assumed. Heartbeat is optimization, not survival.
- **If heartbeat-gated routing (condition C) introduces false positives:** Heartbeat frequency matters critically. Build adaptive heartbeat: frequent for agents handling active tasks, slow for idle agents.

**NEXT QUESTION IT OPENS → SPOKE 9: The Capability Decay Question** (offline/online cycle as a decay proxy)

---

### SPOKE 14 — The DONE-to-DATA Fidelity Question

**QUESTION:** When agent A's DONE output is used verbatim as agent B's DATA input — and A and B are different model families — does the information survive the handoff with acceptable fidelity?

**GROUNDING:** ARCHITECTURE-IRREDUCIBLE.md §3 identifies this as the critical untested gap: "the chain handoff — where agent A's DONE output becomes agent B's DATA input — has not been tested with real network latency, model variation, or concurrent writes." Every multi-agent chain in the architecture assumes this handoff works. It has never been tested cross-model.

**EXPERIMENT:**
```
Design: 3-step chains with deliberate cross-model handoffs

Chain structure:
  Step 1 (phi4-mini) → Step 2 (qwen3:4b) → Step 3 (phi4-mini)
  Step 1 (phi4-mini) → Step 2 (GLM-5-turbo) → Step 3 (qwen3:4b)

Tasks: mathematical chains where intermediate outputs have a ground truth

Conditions:
  A. Raw DONE output: agent A's exact text becomes agent B's DATA
  B. Structured DONE: agent A outputs JSON with typed fields; agent B reads JSON
  C. Normalized DONE: a translator agent converts A's output to canonical form before B

Measure:
  - Does B correctly parse A's output as DATA?
  - Does B produce the correct next step given A's output?
  - Where do model-specific formatting habits break the handoff?
    (e.g., phi4's tendency to add "In conclusion..." before numbers)
```

**OUTCOMES:**
- **If raw DONE (A) breaks cross-model handoffs >30% of the time:** The DONE field needs a mandatory output schema. `{answer: <value>, reasoning: <text>, confidence: <0-1>}`. Agent's prose is secondary; the structured fields are what the next agent reads.
- **If structured JSON (B) achieves >90% handoff fidelity:** JSON as the DATA exchange format is mandatory, not optional. Prose DATA fields are a fleet-wide liability.
- **If translator agent (C) is required:** Add "handoff normalization" as a primitive in the CHAIN/CLAIM/ORDER planning atom. The planning layer must account for inter-model translation cost.

**NEXT QUESTION IT OPENS → SPOKE 1: The Grammar Stability Question**

---

### SPOKE 15 — The Minimum Fleet Size Question

**QUESTION:** What is the minimum number of distinct agents at which a self-organizing fleet produces emergent specialization — and below that minimum, what breaks first?

**GROUNDING:** RESULTS Exp 7 — 3 agents, 6 tasks, perfect emergent specialization. Experiment X — 3 agents, tested persona alignment. The architecture's self-organization premise rests on having enough agents for meaningful specialization. With 2 agents, specialization is binary. With 1, it's trivial. But what happens in the regime between 2 agents (minimal) and the unknown threshold where coordination becomes necessary (from Spoke 6)?

**EXPERIMENT:**
```
Design: Same 6-task room from Exp 7, vary only agent count:
  1 agent: does it attempt all 6 tasks? In what order?
  2 agents: does specialization emerge? Load balance?
  3 agents: Exp 7 baseline (6/6, 2/2/2, zero duplicates)
  5 agents: more agents than tasks — does competition emerge?
  10 agents: far more agents than tasks — duplication?

For each count:
  - Task coverage
  - Specialization index (how concentrated are agent choices?)
  - Duplication rate
  - Time to completion
```

**OUTCOMES:**
- **If specialization first appears at 3 agents:** The minimum viable fleet size is confirmed. Two-agent deployments are a fundamentally different regime — no self-organization, requires explicit task assignment. Design separate protocols for 1-2 agent deployments.
- **If 5-agent overcrowding causes duplication (>20% tasks duplicated):** Implement a "claim-lock" primitive before fleet exceeds 4 agents. The lock is cheap; the duplication is expensive (wasted compute and potentially conflicting DONE outputs into shared state).
- **If 10 agents maintains low duplication:** The self-organization mechanism is more robust than expected — agents have implicit social knowledge to avoid duplication even without locks. This is the most interesting outcome. Investigate the mechanism.

**NEXT QUESTION IT OPENS → SPOKE 6: The Self-Organization Collapse Question**

---

## The Connections: How the Wheel Spins

The spokes are not independent. Every answer generates the next question. Map of the rim:

```
SPOKE 1 (Grammar Stability)
  ├── opens → SPOKE 14 (DONE-to-DATA): stable grammar means handoff schema can be fixed
  └── fed by ← SPOKE 4 (Context Poisoning): context drift is a grammar problem
  └── fed by ← SPOKE 14 (DONE-to-DATA): fidelity failures reveal grammar gaps

SPOKE 2 (Verification Depth)
  ├── opens → SPOKE 9 (Capability Decay): decay rate determines re-verification depth
  └── fed by ← SPOKE 10 (Convergence): if agents agree naturally, PBFT depth requirement drops
  └── fed by ← SPOKE 9 (Capability Decay): decay rate changes required verification frequency

SPOKE 3 (Terrain Threshold)
  ├── opens → SPOKE 7 (Domain Templates): domain-specific terrain effects
  └── fed by ← SPOKE 7 (Domain Templates): template effect may correlate with terrain sensitivity
  └── feeds → SPOKE 2 (Verification Depth): terrain-proximate agents may be better verifiers

SPOKE 4 (Context Poisoning)
  ├── opens → SPOKE 1 (Grammar Stability): both concern DATA drift across steps
  └── feeds → SPOKE 12 (Orchestration Trigger): poisoned context might be the failure signal

SPOKE 5 (FLUX Crossover)
  ├── opens → SPOKE 8 (DATA Precision Floor): FLUX is extreme precision; crossover reveals compression limit
  └── feeds → SPOKE 14 (DONE-to-DATA): FLUX as a typed DONE schema option

SPOKE 6 (Self-Organization Collapse)
  ├── opens → SPOKE 12 (Orchestration Trigger): collapse defines when orchestration activates
  └── fed by ← SPOKE 12 (Orchestration Trigger): agent self-knowledge prevents collapse
  └── fed by ← SPOKE 15 (Minimum Fleet Size): fleet size threshold is the lower bound of collapse

SPOKE 7 (Domain Template Prediction)
  ├── opens → SPOKE 3 (Terrain Threshold): domain type may predict terrain sensitivity
  └── fed by ← SPOKE 3 (Terrain Threshold): terrain threshold finding reveals domain categories

SPOKE 8 (DATA Precision Floor)
  ├── opens → SPOKE 11 (Retrieval Boundary): retrieval must serve the minimum DATA level
  └── fed by ← SPOKE 5 (FLUX Crossover): FLUX crossover IS the DATA precision crossover
  └── fed by ← SPOKE 11 (Retrieval Boundary): boundary tells you which precision level was retrieved

SPOKE 9 (Capability Decay)
  ├── opens → SPOKE 2 (Verification Depth): decay rate determines re-verification cost
  └── fed by ← SPOKE 2 (Verification Depth): verification depth result constrains decay detection
  └── fed by ← SPOKE 13 (Stale Registry): offline/online cycles as decay proxy

SPOKE 10 (Multi-Agent Convergence)
  ├── opens → SPOKE 2 (Verification Depth): if convergence predicts correctness, PBFT is optional
  └── feeds → SPOKE 15 (Minimum Fleet Size): convergence requires minimum N agents

SPOKE 11 (Retrieval Boundary)
  ├── opens → SPOKE 8 (DATA Precision Floor): cross-domain misses may be precision problems
  └── fed by ← SPOKE 8 (DATA Precision Floor): precision level determines whether retrieved tile is useful

SPOKE 12 (Orchestration Trigger)
  ├── opens → SPOKE 6 (Self-Organization Collapse): trigger defines the collapse boundary
  └── fed by ← SPOKE 6 (Self-Organization Collapse): collapse behavior defines the trigger

SPOKE 13 (Stale Registry)
  ├── opens → SPOKE 9 (Capability Decay): offline cycles simulate decay
  └── fed by ← SPOKE 9 (Capability Decay): decayed capabilities cause same symptoms as stale registry

SPOKE 14 (DONE-to-DATA Fidelity)
  ├── opens → SPOKE 1 (Grammar Stability): fidelity failures reveal grammar gaps
  └── fed by ← SPOKE 1 (Grammar Stability): stable grammar enables typed DONE schemas
  └── fed by ← SPOKE 5 (FLUX Crossover): FLUX as the typed DONE format

SPOKE 15 (Minimum Fleet Size)
  ├── opens → SPOKE 6 (Self-Organization Collapse): size threshold IS the lower bound of collapse
  └── fed by ← SPOKE 6 (Self-Organization Collapse): collapse upper bound completes the size window
  └── fed by ← SPOKE 10 (Convergence): convergence requires minimum N agents
```

---

## Phase-Transition Experiments

Some spokes, if they answer in a specific direction, don't just change what we build — they **flip the architecture**. These are the most important experiments to run.

### FLIP 1: If Spoke 10 (Convergence) shows 3/3 agreement predicts correctness at ≥90%
→ **KILL** the PBFT verification infrastructure before it's built.
→ **REPLACE** with: send every task to 3 agents, take majority. No verification layer at all.
→ Architecture flips from "verification layer" to "redundancy layer."
→ Fleet minimum size becomes 3 agents (for quorum), not 1.

### FLIP 2: If Spoke 6 (Self-Organization) shows failure at ≤12 tasks due to duplication
→ **KILL** the "no orchestrator for simple tasks" principle from Exp 7.
→ **REPLACE** with: claim-lock is mandatory infrastructure, not optional coordination primitive.
→ Architecture flips from "organic room" to "locked-claim room."
→ Exp 7's finding was not about simple tasks — it was about small rooms.

### FLIP 3: If Spoke 14 (DONE-to-DATA) shows >30% fidelity failure in raw handoffs
→ **KILL** the "stream context" finding from DEEP Exp 2 as sufficient.
→ **REPLACE** with: typed JSON output schema is mandatory for every DONE field.
→ Architecture flips from "natural language handoffs" to "typed schema handoffs."
→ Implications: agents must validate incoming DATA schema before executing.

### FLIP 4: If Spoke 9 (Capability Decay) shows ±30% variance by framing
→ **KILL** the single-test Campaign A methodology entirely.
→ **REPLACE** with: capability verification is 5+ framings, producing a distribution, not a pass/fail.
→ Architecture flips from "binary capability flag" to "capability distribution."
→ Registry schema changes: `pass_rate` becomes `{mean, std_dev, sample_n}`.

### FLIP 5: If Spoke 12 (Orchestration Trigger) shows agents cannot self-report capacity limits
→ **KILL** the premise that self-organization handles capacity automatically.
→ **REPLACE** with: every task room needs a lightweight orchestrator — not a framework, a single-purpose tile that monitors room state and adds COORDINATION tiles when needed.
→ Architecture flips from "frameworkless orchestration" to "minimal orchestration by exception."

---

## Experiment Priority Order

The spokes are not equally urgent. Some unblock others. Run in this order:

```
Priority 1 — Foundation blockers (everything else depends on these):
  SPOKE 9  (Capability Decay)       → must know before re-verification costs can be estimated
  SPOKE 13 (Stale Registry)         → must know before any multi-agent deployment
  SPOKE 14 (DONE-to-DATA Fidelity)  → must know before any real chain handoffs

Priority 2 — Architecture-defining (could flip core assumptions):
  SPOKE 10 (Convergence)            → determines whether verification layer is needed
  SPOKE 6  (Self-Organization Collapse) → determines whether orchestration is needed
  SPOKE 12 (Orchestration Trigger)  → determines whether agents are self-aware

Priority 3 — Optimization unlocks (blocked on Priority 1 baseline accuracy):
  SPOKE 3  (Terrain Threshold)      → need ≥60% baseline first
  SPOKE 5  (FLUX Crossover)         → need stable task execution first
  SPOKE 7  (Domain Templates)       → need multi-domain capability data first

Priority 4 — Depth questions (answer after architecture is stable):
  SPOKE 1  (Grammar Stability)      → answer after 10-step chains are running
  SPOKE 2  (Verification Depth)     → answer after you know re-verification frequency
  SPOKE 4  (Context Poisoning)      → answer after stable grammar is confirmed
  SPOKE 8  (DATA Precision Floor)   → answer after retrieval is working
  SPOKE 11 (Retrieval Boundary)     → answer after hierarchical retrieval is deployed
  SPOKE 15 (Minimum Fleet Size)     → answer after self-organization is confirmed stable
```

---

## The Wheel

```
                    ┌── SPOKE 1 ──┐
                    │  Grammar    │
                    │  Stability  │
          SPOKE 4 ──┤             ├── SPOKE 14
       Context      │             │   DONE→DATA
       Poisoning    │   H U B     │   Fidelity
                    │             │
         SPOKE 5 ──┤  confirmed  ├── SPOKE 13
       FLUX         │  findings   │   Stale
       Crossover    │             │   Registry
                    │             │
         SPOKE 8 ──┤             ├── SPOKE 9
       DATA         │             │   Capability
       Precision    └─────────────┘   Decay
       Floor                │
                      ┌─────┴─────┐
              SPOKE 11│           │SPOKE 2
           Retrieval  │           │Verification
           Boundary   │           │Depth
                      │           │
              SPOKE 7 │           │SPOKE 10
           Domain     │           │Multi-Agent
           Templates  │           │Convergence
                      │           │
              SPOKE 3 ─┐         ┌─ SPOKE 15
           Terrain     │  SPOKE 6 │  Minimum
           Threshold   └──Self-Org└─ Fleet Size
                          Collapse
                              │
                          SPOKE 12
                       Orchestration
                          Trigger
```

---

## A Note on the Wheel Itself

This document is not a plan. It is a **generative system**.

When you run an experiment and get a result, come back here:
1. Find the spoke
2. Record the outcome
3. Follow the rim to the next spoke it opens
4. Update that spoke's grounding
5. Update ARCHITECTURE-IRREDUCIBLE.md with what changed

The wheel spins because every answer narrows the space of unknowns while revealing new structure at the boundary.

**The most important spokes are the ones that could kill our assumptions.** Run those first.

The wheel is not complete when all spokes are answered. It is complete when no answer opens a new question. That has not happened yet in six months of experiments. Expect it to spin for a while.

---

*Written 2026-05-14. Grounded in Campaigns A–D, Experiment X, DEEP-RESULTS, RESULTS.*
*Each answered spoke should update ARCHITECTURE-IRREDUCIBLE.md.*
*Each new question discovered should add a new spoke here.*
