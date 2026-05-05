# LlamaIndex vs PLATO+FLUX — Technical Architecture Comparison

> Forgemaster ⚒️ — 2026-05-03, Cocapn Fleet Analysis

---

## 1. Architecture Comparison

| Layer | LlamaIndex | PLATO + FLUX |
|-------|-----------|---------------|
| **Knowledge Store** | VectorStoreIndex (chunk→embed→vector DB). 40+ backends. Semantic similarity search. | Room-tile hypergraph (1,369 rooms, 18,496 tiles). Provenance-tracked. Gate-filtered ingress. Domain-scoped. |
| **Graph Engine** | PropertyGraphIndex, KnowledgeGraphIndex. Neo4j/Memgraph. Text2Cypher for queries. Entity→subgraph retrieval. | PLATO Pathfinder (port 4051). Multi-hop tile traversal. OHCache hypergraph for hot-path routing. |
| **Agent Orchestration** | AgentRunner + AgentWorker. Task→TaskStep→TaskStepOutput. AgentWorkflow for handoffs. | AutoData Supervisor-Squad (LangGraph StateGraph). OHCache directed hyperedges between agent groups. |
| **Production Deploy** | llama-agents: microservices + Control Plane + message queue. K8s (Helm). PostgreSQL + MongoDB + Redis + RabbitMQ. | Fleet: OpenClaw agents on eileen (WSL2) + Oracle1 (bare metal). PLATO on port 8847. Fleet dashboard 4049. SonarTelemetry 4052. |
| **Workflow Engine** | Event-driven @step decorators. StartEvent→StopEvent loop. Context object for state. Streaming output. | LangGraph StateGraph with OHCache context injection. Checkpoint system for resumable runs. Plugin-based prompt injection. |
| **Document Processing** | LlamaParse (VLM-powered). Specialized expert agents per content type. Auto-correction loops. | Not built yet — but FLUX can validate any structured output against constraint rules. |
| **Quality Control** | Post-hoc: re-ranking, filtering, node postprocessors. No ingress gate. | Pre-hoc: PLATO gate rejects absolute_claim, duplicate, answer_too_short, missing_field ON INGEST. Only verified knowledge enters. |
| **Provenance** | Limited. Metadata on nodes. No standard provenance chain. | v2-provenance-explain: every tile tracks source agent, timestamp, confidence, domain, submission context. Full audit trail. |
| **Compilation** | None. LLM calls are runtime string→string. No intermediate representation. | **FLUX ISA**: constraint problems compile to bytecodes. snap, quantize, validate, propagate, solve. Execute on constraint VM. Results are deterministic, reproducible, verifiable. |
| **Physics/Domain** | Generic. No domain-specific physics or constraint enforcement. | SonarVision (Mackenzie 1981 sound speed, Francois-Garrison 1982 absorption). Constraint theory solver (backtracking, forward-checking, arc-consistency). CT bridge (Python ↔ Rust ↔ Node.js). |

---

## 2. What LlamaIndex Does Well (Learn From This)

### 2a. Document Parsing (LlamaParse)
Their VLM-powered parser with specialized expert agents per content type (tables, charts, handwriting) + auto-correction loops is genuinely good. We don't have document ingestion. **Action: Build a FLUX-validated document parser** that parses → extracts → validates against constraint rules before PLATO submission.

### 2b. Production Infrastructure
PostgreSQL + MongoDB + Redis + RabbitMQ + K8s is a real production stack. We're running on a WSL2 box and a bare-metal server. **Action: Containerize PLATO + OHCache + FLUX VM** for reproducible deployment.

### 2c. Plugin Ecosystem
40+ vector DB integrations, 300K+ users, 1B+ documents processed. Network effects are real. **Action: Our fleet plugin system is better architecturally (domain prompts + tools per agent), but we need more plugins and users.**

### 2d. Developer Experience
`pip install llama-index`, `llama-parse`, clean APIs, good docs. We have scattered Python scripts and a PLATO HTTP API. **Action: Package PLATO client + FLUX compiler + fleet plugin as a proper pip-installable package.**

### 2e. Observability
`draw_all_possible_flows` and `draw_most_recent_execution` for workflow debugging. Visual. Useful. **Action: Fleet dashboard already shows tile viz. Add workflow execution graph rendering.**

---

## 3. Where PLATO+FLUX Is Architecturally Superior

### 3a. Knowledge Quality at Ingress (The Gate)

**LlamaIndex**: Any chunk that gets embedded goes into the vector store. No quality filter. Garbage in, garbage retrieved.

**PLATO**: The gate rejects tiles that are absolute claims, duplicates, too short, or missing fields. Only verified, contextualized knowledge enters. This means every tile in PLATO is above a minimum quality bar. LlamaIndex has no equivalent.

**Why it matters**: In RAG, retrieval quality is bounded by index quality. PLATO starts ahead because it never indexes garbage.

### 3b. Provenance as a First-Class Citizen

**LlamaIndex**: Metadata on nodes. Optional. No standard provenance chain. When you ask "where did this answer come from?", you get "it was similar to this chunk from this document."

**PLATO**: v2-provenance-explain. Every tile knows: who submitted it, when, from what agent, with what confidence, in what domain. Full audit trail. When you ask "where did this answer come from?", you get a complete lineage.

**Why it matters**: For scientific/defense/engineering applications (our domain), provenance isn't optional — it's the difference between "we think this is right" and "we know this is right because Forgemaster derived it from constraint X at time T with confidence 0.92."

### 3c. Constraint Compilation (The Kill Shot Warmup)

**LlamaIndex**: LLM calls are runtime string→string transformations. No intermediate representation. No compilation. No verification beyond "does the LLM output look reasonable?"

**FLUX ISA**: Real problems compile to bytecodes (snap, quantize, validate, propagate, solve). These bytecodes execute on a constraint VM. Results are deterministic, reproducible, and mathematically verifiable. You can prove correctness.

**Why it matters**: LlamaIndex can never guarantee correctness. It's an LLM wrapper. FLUX can, because it's a compiler that targets a verifiable execution substrate. This is the difference between "AI-assisted guessing" and "machine-verified proof."

### 3d. Domain Physics Baked In

**LlamaIndex**: Generic. The same retrieval pipeline for legal docs, medical records, and cooking recipes.

**PLATO + SonarVision**: Underwater acoustics baked in (Mackenzie 1981, Francois-Garrison 1982). Constraint theory baked in (CSP solver with backtracking, forward-checking, arc-consistency). When an agent asks about sonar at 200m depth, the answer comes from physics equations, not from "the most similar chunk in the vector store."

**Why it matters**: In our domain (marine robotics, edge computing, fleet coordination), generic AI is a liability. Domain-specific, physics-validated knowledge is an asset.

### 3e. Hot/Cold Knowledge Tiering

**LlamaIndex**: One tier. Vector store. Everything is "indexed" the same way.

**PLATO + OHCache**: Two tiers. OHCache (L1, session-scoped, in-memory, hypergraph-routed) for hot path. PLATO (L2, persistent, provenance-tracked, gate-filtered) for cold storage. Agents get sub-millisecond intra-session access via OHCache, and persistent cross-session knowledge via PLATO.

**Why it matters**: LlamaIndex re-indexes on every query session. PLATO caches intelligently and persists what matters.

---

## 4. The Kill Shot — What PLATO+FLUX Can Do That LlamaIndex Fundamentally Cannot

### Compiled Constraint Verification

LlamaIndex retrieves text. It does not verify it. It cannot prove that a retrieved answer is correct — it can only say "this text is similar to your query."

PLATO+FLUX can:
1. **Retrieve** domain knowledge from PLATO rooms (like LlamaIndex retrieves from vector stores)
2. **Compile** the retrieved knowledge into FLUX bytecodes (LlamaIndex cannot do this — it has no compiler)
3. **Execute** the bytecodes on the constraint VM (deterministic, reproducible)
4. **Verify** the output against the original constraints (mathematical proof)
5. **Submit** the verified result back to PLATO as a new tile with full provenance (closes the loop)

This is a **verification compiler** on top of a **knowledge engine**. LlamaIndex is only a knowledge engine.

### The Concrete Example

**Query**: "What's the maximum safe operating depth for a sonar array at 50kHz given salinity 35 PSU and temperature 10°C?"

**LlamaIndex's answer**: Retrieves similar documents, generates text. Cannot verify. Might cite a paper. Might hallucinate the number.

**PLATO+FLUX's answer**:
1. PLATO retrieves sonar-vision tiles about Mackenzie 1981 sound speed
2. FLUX compiles: `snap(depth=?, temp=10, sal=35, freq=50) → compute_sound_speed → compute_absorption → verify_range`
3. Constraint VM executes: c = 1491.3 m/s, α = 11.2 dB/km
4. CT solver validates: result satisfies all physical constraints (sound speed in [1450, 1550], absorption positive, etc.)
5. Result submitted to PLATO as verified tile with full provenance

The answer isn't "similar text." It's a **computed, verified, provenance-tracked fact**.

### Why LlamaIndex Can't Catch Up

To do this, LlamaIndex would need:
- A constraint compiler (they don't have one)
- A verifiable execution substrate (they don't have one)
- Provenance tracking at the tile level (they have node metadata, not provenance)
- Domain physics engines (they're generic by design)
- A quality gate on ingress (they accept everything)

These aren't features you can bolt on. They're architectural commitments that are incompatible with LlamaIndex's "thin wrapper around LLMs" design.

---

## 5. Next Steps

### Close the Gap (Things LlamaIndex Has That We Don't)

1. **Package PLATO client as pip-installable** (`pip install plato-client`)
2. **Build FLUX-validated document parser** (LlamaParse equivalent with constraint validation)
3. **Containerize the stack** (Docker Compose: PLATO + OHCache + FLUX VM + Pathfinder)
4. **Write developer docs** (quickstart, API reference, integration guides)
5. **Add more domain plugins** (academic, financial, medical — leverage our plugin architecture)

### Widen the Lead (Things We Have That They Don't)

1. **Ship the PLATO-OHCache bridge** (hot/cold tiering — already written)
2. **Wire FLUX compiler to PLATO query pipeline** (retrieve→compile→execute→verify→submit loop)
3. **Build constraint verification API** (POST /verify endpoint that takes a claim, compiles it, and returns proof/disproof)
4. **Integrate with AutoData's Supervisor-Squad** (our orchestration layer with domain context injection)
5. **Publish the kill shot** (blog post / paper: "Compiled Constraint Verification for Knowledge-Intensive AI")

### The 30-Day Roadmap

| Week | Deliverable |
|------|------------|
| 1 | PLATO client pip package + FLUX compiler API endpoint |
| 2 | Document parser with FLUX validation + containerized stack |
| 3 | PLATO-OHCache bridge deployed + constraint verification API |
| 4 | Developer docs + kill shot blog post + first external users |

---

*The pitch: LlamaIndex retrieves text. PLATO+FLUX retrieves, compiles, verifies, and proves. That's not an incremental improvement — it's a category difference.*
