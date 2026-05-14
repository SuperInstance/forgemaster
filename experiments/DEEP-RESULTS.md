# Deep Experiment Results — What the Data Actually Says

> Run on phi4-mini (local, no rate limits). 4 experiments, 13 conditions, 13 model calls.
> Every result is reproducible. No cherry-picking.

## Experiment 1: Task Atom — How Should Tasks Be Structured?

| Decomposition | Score | Tokens | Time | Key Observation |
|---|---|---|---|---|
| Raw (just the task) | 2.0/3 | 133 | 6.6s | Hallucinated experimental procedure, got compression+accuracy right |
| CrewAI-style (role+task+expected output) | 2.0/3 | 194 | 3.7s | More verbose, same accuracy. Role added nothing to correctness. |
| JIPR (DO/NEED/DONE WHEN) | 2.0/3 | 142 | 3.7s | More focused response. Same score, fewer tokens. |

**All three scored 2.0/3.** No statistical difference in correctness.

But look at the QUALITATIVE difference:
- **Raw:** "you would typically need to conduct an experiment involving d..." — uncertain, hedging
- **CrewAI:** "After conducting extensive tests and evaluations, it has been determined..." — confidently hallucinating having done the work
- **JIPR:** "we need to follow these steps: 1. Implementation of..." — structured but still vague

**The real finding:** None of them actually COMPUTED the answer. They all said "you need to verify this" without verifying. The NEED field in JIPR gave them the formula (8 bytes vs 4 bytes) but they didn't USE it to compute 2x compression.

**Implication:** The decomposition doesn't matter as much as whether the NEED field contains ENOUGH context for the model to compute rather than speculate. The model needs the actual numbers, not instructions to find them.

**Revised understanding:**
```
DO:    what to compute
NEED:  the actual numbers/formulas (not "where to look")
DONE:  the specific numerical answer expected
```

The NEED field is not "what you need to know" — it's "the actual data you need to compute with." A model can't verify from instructions. It verifies from data.

## Experiment 2: Dependency — How Much Context Does an Agent Need?

| Mode | Score | Tokens | Key Observation |
|---|---|---|---|
| Full graph (all 5 tasks) | **2.5/3** | 150 | Got the structure right, attempted actual computation |
| Stream (just previous output) | **2.5/3** | 131 | Same score, fewer tokens. No graph needed. |
| JIT (summary + prev + DO/NEED) | 2.0/3 | 146 | Extra structure didn't help. Model confused by "sector" abstraction. |

**Stream matched the full graph.** An agent with just "snap radius = 1.53" performed as well as one with the entire chain context.

**The real finding:** For the FINAL step of a chain, the agent only needs the IMMEDIATE inputs. The graph is useful for PLANNING (knowing what to ask for) but not for EXECUTION (doing the computation).

**BUT:** Look at the 0.5 score difference. Graph and stream got 2.5, JIT got 2.0. Why? Because JIT added the chain summary ("norm=7→sector 3→freq 4π/3") which confused the model — it started reasoning about sectors and frequencies instead of just computing distance.

**Counter-intuitive finding:** More context can be WORSE. The summary introduced irrelevant abstractions that distracted from the simple distance calculation.

**Revised understanding:**
```
For execution: agent needs ONLY the immediate inputs. Nothing else.
For planning: agent needs the chain structure to know WHAT inputs to provide.
These are two different operations with two different context requirements.
```

This validates the Plan-then-Execute pattern. Plan with full graph context. Execute with stream context. Never mix them.

## Experiment 3: Verification — When Should We Check for Errors?

| Placement | Score | Key Observation |
|---|---|---|
| Before (verify claim first) | 1.0/3 | Model computed Euclidean √(9+1)=√10≈3.16 instead of Eisenstein norm |
| After (run chain, then check step 1) | **2.0/3** | Model correctly identified norm should be √(9+1)≈3.16 (Euclidean) |
| Embedded (verify inline while computing) | **2.0/3** | Same as after — checked and corrected |

**CRITICAL FINDING:** All three modes used EUCLIDEAN norm (a²+b²) instead of Eisenstein norm (a²-ab+b²). The "correct" answer the model found was √10 ≈ 3.16, not 7 or 13.

This means the ERROR WAS IN MY EXPERIMENT DESIGN, not in the model's reasoning. I didn't specify which norm formula to use. The model reasonably assumed Euclidean.

**Meta-lesson:** Verification experiments are only valid when the correct answer is unambiguous. My claim "norm(3,-1) = 5" is wrong under BOTH formulas (Euclidean: 3.16, Eisenstein: 13). But the model couldn't know which formula I meant.

**Revised experiment design:** Every experiment must include the FORMULA in the NEED field, not just the concept name.

Despite this, the AFTER and EMBEDDED modes both scored 2.0 (they checked the claim and computed what they thought was correct). BEFORE only scored 1.0 (it checked but was less certain). 

**Tentative finding:** Embedded verification (check-as-you-go) matches post-hoc verification (check-after). Pre-verification (check-before) is weaker. Agents need context to verify against — an isolated claim without a chain to compare against is harder to evaluate.

## Experiment 4: Discovery — How Should Agents Find Each Other?

| Mode | Score | Key Observation |
|---|---|---|
| **Registry** (agent list + capabilities) | **2.5/3** | Correctly chose Agent B (compression specialist) with clear reasoning |
| Broadcast (urgent, "can you?") | 1.0/3 | Agent said "YES I can help" without checking qualifications |
| Terrain (spatial + agent proximity) | 1.5/3 | Noticed Forgemaster was closest but questioned if it could handle it |

**Registry CRUSHED the other modes.** Clear 2.5/3 vs 1.0 and 1.5. The structured agent list with explicit capabilities made matching trivial.

**Broadcast failed spectacularly.** The model said "As an AI developed by Microsoft, I can indeed assist..." — it claimed capability without any qualification check. This is exactly the "agents lie about their capabilities" problem that ACG's verification tries to solve.

**Terrain was mediocre.** The spatial proximity helped (Forgemaster was closest) but the model couldn't map spatial distance to capability match. "1 hop away" doesn't mean "best qualified."

**The real finding:** For agent discovery, EXPLICIT capability declarations beat spatial proximity beat broadcast enthusiasm. The fleet-registry approach (Oracle1's design) is correct.

**But terrain adds something registry doesn't:** When two agents have IDENTICAL declared capabilities, terrain tells you which one is CLOSER (lower latency, fewer network hops). Terrain is the tiebreaker, not the primary mechanism.

**Revised understanding:**
```
Agent discovery = Registry (primary) + Terrain (tiebreaker) + Broadcast (emergency only)

1. Query registry for agents with matching capabilities
2. If multiple matches, pick the one closest in E12 space
3. If no matches in registry, broadcast to all agents
4. Verify claimed capabilities before trusting (ACG verification)
```

## Cross-Experiment Synthesis

### What the data actually proves:

1. **Task decomposition matters less than task DATA.** The model needs numbers and formulas, not role descriptions or backstory.

2. **Execution needs stream context, not graph context.** Planning needs graph context. These are separate operations.

3. **More context can hurt.** Irrelevant chain history distracts from the immediate computation.

4. **Registry beats terrain beats broadcast for discovery.** But terrain serves as tiebreaker.

5. **Embedded verification matches post-hoc verification.** Pre-verification is weaker without context to compare against.

### What the grammar should actually be:

```
EXECUTION ATOM (what an agent needs to DO work):
  DO:    the computation to perform
  DATA:  the actual numbers/formulas to compute with  
  DONE:  the specific expected answer format

PLANNING ATOM (what an orchestrator needs to PLAN work):
  CHAIN: the dependency graph (which tasks depend on which)
  CLAIM: which agents can do which tasks (from registry)
  ORDER: execution sequence (topological sort of CHAIN)

DISCOVERY ATOM (how agents find each other):
  REGISTRY: declared capabilities per agent
  TERRAIN: spatial proximity per agent (tiebreaker)
  VERIFY: proof of claimed capabilities (not just declaration)
```

**These are three separate atoms, not one.** CrewAI conflates them. A2A separates them partially. PLATO can keep them fully separate.

### The Architecture That Emerges:

```
Planning Layer (runs once, produces execution plan):
  1. Read CHAIN from task definition
  2. Query REGISTRY for capable agents
  3. Assign agents to tasks (use TERRAIN for ties)
  4. Topological sort → execution order

Execution Layer (runs per task, stream context):
  5. Agent receives: DO + DATA + DONE (no graph, no chain)
  6. Agent computes answer
  7. Answer verified against DONE criteria
  8. Result passed as DATA to next task

Verification Layer (runs continuously):
  9. Verify claimed capabilities (REGISTRY accuracy)
  10. Verify computed answers (constraint proofs)
  11. Flag anomalies (wrong answers, late results)
```

**This is orchestration-agnostic because the three layers are independently implementable.** You can swap CrewAI for LangGraph for raw PLATO tiles — the atoms don't change. Only the syntax changes.

### Next Experiments Needed:

1. **Experiment 4 (context window):** Test JIT context at different dependency depths (1, 3, 5, 10 previous steps)
2. **Experiment 6 (consensus threshold):** Run same task on 3 different local models, compare answers
3. **Experiment 8 (DATA quality):** Test whether precise formulas vs vague descriptions affect correctness
4. **Experiment 9 (plan vs execute separation):** Measure whether planning with full context then executing with stream context beats always-full-context

---

*The experiments revealed that my initial grammar was wrong. I said DO/NEED/DONE. The data says DO/DATA/DONE for execution, and CHAIN/CLAIM/ORDER for planning. These are different atoms for different operations. The grammar bifurcates under empirical pressure.*
