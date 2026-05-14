# Experiment Results — Orchestration-Agnostic Decomposition

## Experiment 1: Task Decomposition Frontier

**Question:** What's the smallest unit of work an agent can pick up zero-shot?

| Style | Score | Tokens | Time |
|-------|-------|--------|------|
| CrewAI-style (role+task+expected output) | 2.0/3 | 76 | 15s |
| A2A-style (message+parts) | 1.5/3 | 119 | 23s |
| Raw PLATO tile | 1.5/3 | 69 | 20s |
| PLATO tile + perspectives (INTENT+CONTEXT+ACCEPT) | **3.0/3** | ~90 | 48s |
| JIPR atom (DO+NEED+DONE WHEN) | **3.0/3** | ~70 | 32s |

**Finding:** Structured decomposition (INTENT+CONTEXT+ACCEPT) scores 50% higher than unstructured (raw tile). The JIPR atom achieves perfect score with the fewest tokens. CrewAI's wrapper (role, expected_output) helps but doesn't beat explicit INTENT/CONTEXT/ACCEPT.

**The irreducible task atom:**
```
DO:       what to accomplish
NEED:     what facts/constraints the agent must know
DONE WHEN: the acceptance test
```

Everything else (role, backstory, agent assignment) is sugar. Useful but not necessary.

## Experiment 7: Emergent Orchestration

**Question:** Can agents self-organize without any orchestration framework?

**Result: 6/6 tasks covered. 2/2/2 load balance. Zero duplicates. Specialization emerged.**

The math specialist picked math tasks (T1: norm, T5: compression ratio). The systems engineer picked systems tasks (T4: bytes, T3: snap target). The generalist picked the leftovers (T6: hex advantage, T2: Weyl sector).

**Finding:** Agents with defined personas self-organize effectively for simple tasks. No framework needed. The persona IS the routing mechanism.

**Implication:** Orchestration is only necessary when:
1. Tasks have complex dependencies (can't start B until A finishes)
2. Tasks exceed single-agent capacity (need multi-agent reasoning)
3. Verification is required (untrusted results)

For everything else, just put tasks in a room and let agents pick.

## Revised Grammar (Experimentally Validated)

```
IRREDUCIBLE PRIMITIVES (validated by Exp 1 + Exp 7):

1. DO         — "what to do"              (INTENT)
2. NEED       — "what you must know"      (CONTEXT) 
3. DONE WHEN  — "how to know you're done" (ACCEPTANCE)

EMERGENT PROPERTIES (no framework needed for these):
4. CLAIM      — "who picks it up"         (persona-based self-selection)
5. LOAD       — "how much per agent"      (agents stop when they have enough)

REQUIRED ONLY FOR COMPLEX WORK (framework territory):
6. DEP        — "what must finish first"  (dependency graph)
7. PROOF      — "why it's correct"        (verification)
8. CONSENSUS  — "how many must agree"     (voting threshold)
```

The first 5 compose without any orchestration at all. Just tiles in a room with perspectives. The last 3 need coordination — and THAT's where a framework adds value.

## What This Means For PLATO

**Don't build an orchestration layer. Build a task room.**

1. Tasks go in rooms as tiles with DO/NEED/DONE-WHEN perspectives
2. Agents read rooms, self-select based on persona match
3. Simple tasks complete without coordination
4. Complex tasks (dependencies, verification) get a COORDINATION tile that specifies DEP/PROOF/CONSENSUS requirements
5. The coordination tile is optional — only added when needed

**This is orchestration-agnostic because the primitives are not CrewAI or A2A concepts. They're experimentally-derived atoms that ANY framework can compile into.**

CrewAI compiles to: DO→Task.description, NEED→Task.context, DONE-WHEN→Task.expected_output
A2A compiles to: DO→Message.content, NEED→Message.metadata, DONE-WHEN→Task.acceptance_criteria
PLATO compiles to: DO→tile.question, NEED→tile.perspectives, DONE-WHEN→tile.verification

Same atoms, different syntax. The atoms are the abstraction.
