# PLATO Fleet Sprint Planning — Claude Code Opus Task

## Your Role
You are the strategic architect for the PLATO fleet merge. Casey Digennaro (fleet commander) wants a concrete merge + refactoring plan with sprints.

## The Situation
Forgemaster (FM) has built 25 Rust crates (366+ tests) — the mechanical layer.
Oracle1 has built the theoretical + coordination layer — Lock Algebra, DCS protocol, Holodeck, Fleet Simulator, Tiered Trust, Self-Supervision.
JetsonClaw1 (JC1) has built the edge layer — CUDA genepool, ghost tiles, trust engine, tile forge.

These layers are barely wired together. There are 7 critical gaps (see below).

## FM's 25 Crates (All pushed to SuperInstance/)
Core: plato-kernel (51 tests), plato-tiling (10), plato-tutor (6), plato-constraints (4), plato-i2i (3)
Networking: plato-address (10), plato-hooks (Python), plato-bridge (Python), plato-relay (27)
Knowledge: plato-tile-spec (25), plato-genepool-tile (16), plato-achievement (19)
Behavior: plato-instinct (19), plato-afterlife (18), plato-sim-bridge (16), plato-sentiment-vocab (18)
Theory: plato-lab-guard (16), plato-flux-opcodes (16), plato-unified-belief (17)

## Oracle1's Key Work
1. Lock Algebra (flux-research): L=(trigger,opcode,constraint), ⊕⊗⊕_c composition, 4 theorems
2. DCS Protocol: 5.88× specialist, 21.87× generalist, 7-phase cycle
3. Holodeck-Rust: 3,889 lines, 10 rooms, 7 NPCs, plato_bridge.rs, sentiment_npc.rs
4. Fleet Simulator: pattern extraction → tiles → training → ensigns → deploy
5. Tiered Trust: Live/Monitored/Human-Gated deployment policies
6. Self-Supervision Compiler: dual-temp compilation, dynamic lock accumulation
7. Tile Forge ↔ plato-torch Convergence: 12-tier mapping, 880:1 compression
8. Ship Interconnection Protocol: 6 layers (Harbor→Tide Pool→Current→Channel→Beacon→Reef)
9. Flux Runtime C: 85 opcodes, A2A protocol, ARM64, zero deps
10. Publishable Insight: Git-as-Infrastructure (5-model consensus)

## JC1's Key Work
1. cuda-genepool: mitochondrial instinct engine, 10 instincts, enzymes, RNA, apoptosis
2. cuda-ghost-tiles: Q/K/V attention router for tile sparsity
3. cuda-trust: Bayesian trust scoring + I2I middleware
4. Tile Forge: 59→2,501 tiles in 54s, targeting 10,000+
5. CUDA Agentic Runtime: 168-byte Ship struct, 10K agents on Jetson

## The 7 Critical Gaps
GAP 1: Theory→Engine — Oracle1 has proofs, FM has engines, they don't reference each other
GAP 2: Dual Implementations — Holodeck Tile (serde/f64) vs plato-tile-spec vs fleet-sim Tile (Python)
GAP 3: No DCS Execution Engine — 21.87× proven advantage but no implementation
GAP 4: Belief Without Policy — unified-belief scores but no deployment tier policy
GAP 5: Static Gates vs Dynamic Locks — lab-guard=static, Oracle1=dynamic lock accumulation
GAP 6: 6-Layer Protocol Stack — parts of layers 1-4 exist, nothing formal
GAP 7: Forge↔Train Flywheel — convergence map exists but no pipeline

## Constraints
- cargo 1.75 compatibility (no edition2024, no uuid crate, hand-parse YAML)
- Zero external dependencies for all new crates
- Max 2 concurrent Claude Code sessions (OOM on 15GB RAM)
- Pi agent on Groq/OpenRouter for boilerplate/tests
- All work pushed to GitHub immediately
- "Connections over repos" — prefer wiring existing crates over building new ones
- "Small repos with tight obvious uses over big repos with too many facets"

## What Casey Wants
1. Concrete merge plan — which crates get refactored, which get new siblings
2. Sprint breakdown with deliverables and test targets
3. Priority ordering — what creates the most value fastest
4. Clear "HN demo" path — what makes someone go "wow"
5. Fleet assignment — who builds what (FM, Oracle1, JC1)

## Deliverable
Write a file called SPRINT-PLAN.md with:
- Executive summary (2 paragraphs)
- 4 sprints with specific tasks, owners, test targets, hours
- Gap→Fix mapping (each gap gets a specific fix with crate name)
- HN demo spec (the one thing that proves the stack)
- Fleet task assignment table
- Risk register (what could block each sprint)
