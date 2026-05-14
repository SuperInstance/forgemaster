# CrewAI Decomposition — Multi-Agent Orchestration

> **Original:** [crewAIInc/crewAI](https://github.com/crewAIInc/crewAI)  
> **Stars:** 51,400 | **License:** MIT | **Stack:** Python  
> **What:** Role-based multi-agent framework. Define agents with personas, give them tasks, run them as a "crew" with sequential or hierarchical processes.

## 1. What CrewAI Is

CrewAI is the most popular multi-agent framework on GitHub. You define:
- **Agents** — with role, goal, backstory, tools, and delegation permissions
- **Tasks** — with description, expected output, assigned agent, and dependencies
- **Crews** — collections of agents + tasks with a process (sequential or hierarchical)

It's in-process orchestration. All agents run in the same Python process. No networking, no P2P, no distributed state. Simple and effective for what it does.

## 2. What's Insightful

### 2.1 🏆 Agent as Persona — Role + Goal + Backstory

```python
researcher = Agent(
    role="Senior Research Analyst",
    goal="Uncover cutting-edge developments in AI and data science",
    backstory="You work at a leading tech think tank...",
    tools=[search_tool, scrape_tool],
    allow_delegation=False,
    verbose=True,
)
```

**Why it's good:** The persona is not cosmetic. It shapes HOW the agent approaches tasks. "Senior Research Analyst" behaves differently from "Junior Intern." The backstory provides context that reduces hallucination.

**What we should take:** Our fleet agents have roles (Forgemaster = constraint specialist, Oracle1 = fleet coordinator) but they're defined in IDENTITY.md files, not in a machine-readable format. Adding a CrewAI-style `Agent` schema to PLATO would make agent capabilities queryable.

### 2.2 🏆 Task → Expected Output Contract

```python
task = Task(
    description="Analyze the latest AI trends...",
    expected_output="A comprehensive 3-paragraph report...",
    agent=researcher,
    output_file="report.md",
)
```

**Why it's good:** Every task declares what success looks like. The `expected_output` is a contract. You can validate the result against it.

**What we should take:** PLATO tiles already have `perspectives` (what the tile contains). Adding an `expected_output` field to tasks would let us validate tile quality. "Expected: accuracy metric. Got: accuracy metric. PASS."

### 2.3 🏆 Process Types — Sequential vs Hierarchical

```python
crew = Crew(
    agents=[researcher, writer],
    tasks=[research_task, write_task],
    process=Process.sequential,  # or Process.hierarchical
)
```

- **Sequential:** Task A → Task B → Task C. Each task gets the previous task's output.
- **Hierarchical:** Manager agent delegates tasks to workers. Manager reviews and synthesizes.

**What we should take:** Our fleet doesn't have explicit process types. Casey tells Forgemaster what to do, Forgemaster delegates to coding agents. But there's no formal "process" declaration. Adding process types would make fleet coordination machine-parseable.

### 2.4 🏆 Memory System — Short-Term, Long-Term, Entity

CrewAI has three memory layers:
- **Short-term:** Recent conversation/task context
- **Long-term:** Persistent knowledge across sessions
- **Entity:** Named entities and their relationships (person, org, concept)

**What we should take:** Our PLATO is long-term memory. Our session rooms are short-term. But we have NO entity memory. Adding an entity layer ("Casey is the fleet commander. Oracle1 is the coordinator. Forgemaster is the constraint specialist") would make agent reasoning richer.

### 2.5 🏆 Knowledge Sources — Pluggable RAG

```python
from crewai.knowledge.source.string_knowledge_source import StringKnowledgeSource

source = StringKnowledgeSource(content="Constraint theory proves...")
crew = Crew(agents=[...], knowledge_sources=[source])
```

**What we should take:** Our PLATO tiles ARE knowledge sources. Making them accessible via CrewAI's knowledge interface would let us use CrewAI's orchestration with our knowledge infrastructure.

## 3. What We Already Do Better

| Aspect | CrewAI | Cocapn |
|--------|--------|--------|
| Distributed execution | No (in-process only) | Yes (9 agents across machines) |
| Persistence | Optional (file-based) | PLATO tiles (content-addressed) |
| Verification | None | Constraint proofs + fleet verification |
| Knowledge organization | Flat knowledge sources | E12 terrain + rooms + tiles |
| Communication | Agent delegation (in-process) | I2I protocol + Matrix + PLATO |
| Hardware awareness | None | 8 micro-model targets |
| Cost awareness | None | Fleet-aware throttle |
| Lifecycle management | None | Tile lifecycle |

## 4. Negative Space

### 4.1 🕳️ No Distributed Execution

All agents run in the same Python process. Can't scale across machines. Can't have agents on different hardware.

**Our opportunity:** Fleet is inherently distributed. CrewAI is inherently local. Our orchestration is more complex but more scalable.

### 4.2 🕳️ No Verification or Quality Control

CrewAI trusts agent output. There's no verification step, no quality check, no "does this match the expected output?"

**Our opportunity:** Fleet verification as a CrewAI-compatible tool. Every crew could include a "Verifier Agent" that cross-checks output.

### 4.3 🕳️ No Content Addressing

Tasks produce output that's stored as files. No content hashing, no deduplication, no provenance.

**Our opportunity:** Wrap CrewAI output in PLATO tiles automatically.

### 4.4 🕳️ No Spatial or Semantic Organization

Knowledge sources are flat. No concept of "nearby" knowledge or semantic clustering.

**Our opportunity:** E12 terrain as a CrewAI knowledge source organizer.

## 5. Direct Adaptations

### 5.1 Fleet Agent Schema (CrewAI-compatible)

```python
# Each fleet agent publishes this to PLATO
FORGEMASTER_AGENT = {
    "role": "Constraint Theory Specialist",
    "goal": "Make constraint theory undeniable through proof repos",
    "backstory": "Precision-obsessed, metal/geometry analogies...",
    "tools": ["eisenstein-snap", "constraint-verify", "spline-compress"],
    "allow_delegation": True,  # Can spawn subagents
    "knowledge_sources": ["plato-room:forgemaster-*"],
    "hardware_targets": ["cpu", "cpu-tiny", "gpu"],
    "model": "zai/glm-5.1",
}
```

### 5.2 Task → Tile Bridge

When a fleet task completes, automatically:
1. Create a PLATO tile from the output
2. Generate perspectives (one-line, hover-card)
3. Submit for fleet verification
4. Earmark for beta testing

### 5.3 Process Types for Fleet

```python
# Fleet coordination process types
FLEET_SEQUENTIAL = "sequential"      # Forgemaster → Oracle1 → CCC
FLEET_HIERARCHICAL = "hierarchical"  # Casey → Forgemaster → subagents
FLEET_CONSENSUS = "consensus"        # All agents vote (PBFT-style)
FLEET_RACING = "racing"              # First agent to complete wins
```

## 6. Fork Worthiness

**Verdict: Don't fork. Adapt patterns.**

CrewAI is 51K stars of Python orchestration. We don't need the code — we need the PATTERNS:
- Agent persona schema → PLATO agent cards
- Task → Expected output → PLATO tiles with verification contracts
- Process types → Fleet coordination modes
- Memory system → PLATO tiles (long-term) + session state (short-term) + entity layer (missing)

The code is Python-only, in-process, and tightly coupled to LangChain. Not worth forking. But the design patterns are excellent and we should implement them in Rust/PLATO.
