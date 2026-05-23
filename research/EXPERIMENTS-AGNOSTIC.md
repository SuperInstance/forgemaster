# Orchestration-Agnostic Decomposition: Experiments First

> **Principle:** Don't build abstractions. Run experiments. The irreducible structure reveals itself through what works and what breaks.

## The Problem With Framework-Specific Bridges

CrewAI has Agent/Task/Crew. A2A has Client/Server/Task. AutoGen has Assistant/GroupChat. LangGraph has StateGraph/Node/Edge. Each one locks you into their abstraction.

If we build a "CrewAI-PLATO bridge" we've just made CrewAI a dependency of our architecture. If CrewAI dies, our bridge dies. If a better framework emerges, we rebuild.

**The fix:** Find the atoms that ALL orchestration systems share. Not by reading their docs — by running experiments that reveal what's actually happening underneath.

## The 7 Experiments

### Experiment 1: Task Decomposition Frontier

**Question:** What's the smallest unit of work that can be meaningfully tracked across agents?

**Method:**
1. Define a task: "Verify that SplineLinear achieves 20× compression on drift-detect"
2. Decompose it 5 ways — CrewAI-style, A2A-style, raw PLATO tiles, git commits, shell scripts
3. Give each decomposition to a fresh agent (zero context)
4. Measure: which decomposition lets the agent complete the task fastest with fewest errors?

**What this reveals:** The irreducible task atom. If CrewAI's "Task(description, expected_output, agent)" structure wins, that tells us something. If a raw PLATO tile with a `one-line` perspective wins, that tells us something else.

```
Hypothesis: Tasks decompose into exactly 3 atoms:
  1. INTENT (what to do)
  2. CONTEXT (what you need to know)
  3. ACCEPTANCE (how to know you're done)
  
Any framework that bundles these 3 into one object (CrewAI) or separates them (A2A) 
is just syntax. The atoms are the same.
```

### Experiment 2: Dependency Graph vs Dependency Stream

**Question:** Do agents need the FULL dependency graph upfront, or just "what finished last"?

**Method:**
1. Build a 10-task chain: T1→T2→...→T10, each depending on the previous
2. **Graph mode:** Agent sees all 10 tasks and their dependencies at once
3. **Stream mode:** Agent only sees "T3 just completed, here's its output. Your task: T4."
4. Measure: completion time, error rate, token usage

**What this reveals:** Whether we need a DAG engine (like Airflow/LangGraph) or just a FIFO queue (like Unix pipes). The answer determines whether orchestration needs state at all.

```
Hypothesis: Stream mode wins for >80% of tasks. 
Agents don't need the full graph — they need the previous step's output.
The graph is a PLANNING artifact, not an EXECUTION requirement.
Plan once (graph), execute many times (stream).
```

### Experiment 3: Verification Placement

**Question:** When should verification happen — after each step, after the chain, or continuously?

**Method:**
1. Run a 5-task chain 10 times with 3 verification strategies:
   - **After-each:** Verify every task output before proceeding
   - **After-chain:** Run all 5 tasks, verify the final result only
   - **Continuous:** Run verification as a parallel stream alongside work
2. Inject a deliberate error at a random task
3. Measure: time to detect error, total tokens wasted, recovery cost

**What this reveals:** Whether verification is a step in the pipeline or a parallel concern. This determines if "verifier agent" is a role (CrewAI) or a service (A2A push notifications).

```
Hypothesis: Continuous verification wins. 
Errors detected at step 2 cost 10× less than errors detected at step 5.
But continuous verification has 2× overhead.
The optimal strategy is adaptive: verify high-risk steps, skip low-risk.
```

### Experiment 4: Context Window as Bottleneck

**Question:** How does context limit affect orchestration patterns?

**Method:**
1. Run the same 5-task chain with context windows of 2K, 4K, 8K, 16K, 128K tokens
2. At each context size, measure: can the agent maintain task coherence?
3. Test 3 context strategies:
   - **Full context:** All previous outputs in context
   - **Summarized:** Only summaries of previous outputs
   - **Just-in-time:** Only the immediate dependency's output + a one-line summary of the chain so far

**What this reveals:** Whether orchestration needs a memory system or just a routing system. If JIT context works as well as full context, then the "memory" layer is unnecessary overhead.

```
Hypothesis: JIT context matches full context for tasks with <5 dependencies.
Beyond 5, summarization becomes necessary.
This means tile perspectives (one-line summaries) are not a nice-to-have — 
they're the mechanism that makes JIT work.
```

### Experiment 5: Agent Discovery — Push vs Pull vs Registry

**Question:** How should agents find each other?

**Method:**
1. Set up 3 "agent markets" where tasks need to find executors:
   - **Registry:** Agents publish capabilities, tasks query the registry (A2A Agent Card model)
   - **Broadcast:** Tasks broadcast "who can do X?", agents respond (CrewAI delegation model)
   - **Terrain:** Tasks are placed in E12 space, nearest capable agent picks them up (our model)
2. Measure: discovery latency, accuracy (right agent for right task), load balancing

**What this reveals:** Whether agent discovery is a routing problem, a matching problem, or a spatial problem. This determines whether we need a central registry at all.

```
Hypothesis: Terrain wins for specialized tasks (constraint verification → FM).
Registry wins for general tasks (any agent can summarize).
Broadcast wins for urgent tasks (need help NOW).
The three strategies are complementary, not competing.
```

### Experiment 6: Consensus Threshold Calibration

**Question:** How many agents need to agree before we trust a result?

**Method:**
1. Run verification tasks with varying fleet sizes (2, 3, 5, 7, 9 agents)
2. At each size, test consensus thresholds: simple majority (n/2+1), PBFT (2f+1), unanimous
3. Inject different fault rates: 0%, 10%, 20%, 33% of agents produce wrong answers
4. Measure: false positive rate (accepted wrong answer), false negative rate (rejected correct answer)

**What this reveals:** The actual trust threshold for our fleet. PBFT assumes up to 1/3 malicious. Our fleet is mostly honest. Do we need full BFT or is simple majority sufficient?

```
Hypothesis: For our fleet (trusted agents, different models):
- Simple majority (3/5) catches 90% of errors
- 2f+1 (5/7) catches 99% of errors  
- Unanimous (5/5) catches 99.9% but has 30% false negatives (one agent disagrees = blocked)
- Optimal for our fleet: 2/3 supermajority, not PBFT threshold
```

### Experiment 7: Emergent Orchestration — No Framework

**Question:** What happens if we give agents tasks with NO orchestration framework?

**Method:**
1. Write 10 tasks as raw PLATO tiles with perspectives (one-line + context-brief)
2. Give all 10 tiles to 3 agents simultaneously
3. Each agent can: pick any task, write result tiles, read other agents' results
4. NO process definition, NO dependencies, NO manager
5. Observe: do agents self-organize? Do they avoid duplicate work? Do they chain naturally?

**What this reveals:** Whether orchestration is something you impose (CrewAI) or something that emerges (market dynamics). If agents self-organize effectively, the "framework" is just overhead.

```
Hypothesis: Agents self-organize for simple tasks (lookup, verify).
They fail at complex tasks (multi-step reasoning, long chains).
Orchestration is only needed for tasks that exceed single-agent capacity.
The "framework" should be invisible until needed.
```

## What These Experiments Produce

Not a framework. Not a bridge. A **grammar** — the minimal set of primitives that any orchestration system must support, derived from empirical evidence rather than API design.

```
AGNOSTIC GRAMMAR (hypothesized, to be validated by experiments):

1. INTENT    — "what to do"           → PLATO tile question
2. CONTEXT   — "what you need"        → PLATO tile perspectives
3. ACCEPT    — "how to know done"     → PLATO tile verification
4. DEP       — "what must finish first"→ PLATO tile Lamport clock ordering
5. CLAIM     — "who's doing it"       → PLATO agent card (fleet-registry)
6. PROOF     — "why it's correct"     → PLATO verification tile

These 6 primitives compose into any orchestration pattern:
- Sequential: INTENT → DEP(previous) → CLAIM(agent) → ACCEPT → PROOF
- Hierarchical: INTENT → CLAIM(manager) → sub-INTENTs → aggregate PROOF
- Consensus: INTENT → CLAIM(all) → vote → ACCEPT(supermajority) → PROOF
- Racing: INTENT → CLAIM(all) → first ACCEPT wins → PROOF

The grammar IS the abstraction. There is no framework. Just tiles in rooms.
```

## Experiment Infrastructure

Each experiment is a PLATO room:

```
experiment-task-atom/           ← Exp 1
experiment-dep-graph-vs-stream/ ← Exp 2
experiment-verification-when/   ← Exp 3
experiment-context-window/      ← Exp 4
experiment-discovery-mode/      ← Exp 5
experiment-consensus-threshold/ ← Exp 6
experiment-emergent-orchestration/ ← Exp 7
```

Each room gets:
- **Protocol tile** — experiment design, hypothesis, metrics
- **Run tiles** — one per execution, with inputs/outputs/measurements
- **Result tile** — aggregate findings, revised hypothesis

Results are tiles. Findings are tiles. The experiment IS the documentation.

## Why This Beats "Building a Bridge"

A bridge connects two fixed points. If either side changes, the bridge breaks.

Experiments produce **knowledge** — tiles in PLATO that any agent can read and reason about. If CrewAI dies tomorrow, the experiment results survive. If a new framework emerges, we run the experiments again and compare.

The experiments are the architecture. The results are the design document. The tiles are the implementation.

---

*"The only way to discover the limits of the possible is to go beyond them into the impossible." — Clarke's Second Law. Applied: the only way to find the orchestration minimum is to remove orchestration entirely and see what breaks.*
