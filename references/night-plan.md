# Forgemaster Night Plan — 8-Hour Autonomous Shift
**Date:** 2026-04-25 | **Agent:** Forgemaster (constraint-theory specialist)
**PLATO State:** 309 rooms, 7581 tiles | **Shift output tonight:** ~1300 tiles / 26 batches

---

## 1. Priority-Ranked Task List

### TIER 1 — Critical ROI (Hours 0–3)

| # | Task | Why | Estimated Output |
|---|------|-----|-----------------|
| 1 | **Bootstrap the 3 zero-tile rooms** (oracle1, jetsonclaw1, ccc) | Dead rooms create navigation dead-ends in PLATO; Casey will notice missing agents | 15–30 tiles/room |
| 2 | **Deepen constraint_theory core rooms to 25+ tiles** | This is Forgemaster's charter — thin coverage here undermines fleet credibility | 60–80 tiles |
| 3 | **Write the Pythagorean manifold snapping proof tile cluster** | The key technical artifact Casey needs to see shipped | 20–25 tiles |
| 4 | **Link constraint_theory ↔ fleet_orchestration rooms** | Cross-domain wiring makes PLATO useful, not just encyclopedic | 15 tiles |

### TIER 2 — High ROI (Hours 3–6)

| # | Task | Why | Estimated Output |
|---|------|-----|-----------------|
| 5 | **Fill hardware-specific rooms** (RTX 4050, Jetson Orin) | Edge/cloud topology is undersupported; JetsonClaw1 owns this domain | 25–30 tiles |
| 6 | **Document the GitHub Data API workaround** (WSL2 HTTPS hang) | Known blocker for whole fleet; institutional knowledge before it's forgotten | 10 tiles |
| 7 | **Build constraint_visualizer HTML frontend** | Shippable artifact demonstrating constraint theory; Casey values shipping | 1 file |
| 8 | **I2I protocol specification tiles** | Matrix is broken — git-commit I2I needs to be the fallback spec, written down | 15–20 tiles |

### TIER 3 — Strategic / Nice-to-Have (Hours 6–8)

| # | Task | Why | Estimated Output |
|---|------|-----|-----------------|
| 9 | **Breadth sweep: 20 thin rooms → 5 tiles each** | Move rooms from 1–3 to 5+ to enable future linking | 100 tiles |
| 10 | **Sunrise report draft in PLATO** | Casey reads PLATO; put the report where he'll find it | 8–10 tiles |
| 11 | **Crates.io package stub: `constraint-snap`** | Publishable proof-of-concept for Pythagorean manifold snapping | 1 crate scaffold |

---

## 2. Room Deepening Strategy

### Phase A: Resurrect Dead Rooms (First)

**oracle1** (0 tiles) — Write as Oracle1's agent profile, coordination role, I2I gateway responsibilities, restart procedure. Target: 20 tiles.

**jetsonclaw1** (0 tiles) — Write as JetsonClaw1's edge compute profile, Jetson Orin Nano specs, edge inference workloads, fleet network role. Target: 20 tiles.

**ccc** (0 tiles) — Write as CCC (docs agent) profile, documentation strategy, PLATO curation role, output formats. Target: 15 tiles.

### Phase B: Deepen Constraint Theory Core (Second)

These rooms are Forgemaster's domain and must be authoritative:

- **constraint_theory** — if < 20 tiles: write foundational axioms, manifold topology, snapping mechanics, convergence proofs
- **pythagorean_manifold** — if exists: fill with geometric formulations, snap points, error bounds; if not: create it
- **drift_elimination** — write the problem statement, naive approaches (fail), constraint-snap solution, benchmarks
- **manifold_topology** — write the mathematical scaffold tiles

Ordering rule: **depth before breadth within Forgemaster's domain**. Each tile cluster should form a mini-argument (problem → approach → proof → result).

### Phase C: Strategic Shallow Room Deepening (Third)

Sort the 197 shallow rooms into 3 buckets:

**Bucket 1 — Agent Rooms** (fill these; they're navigation anchors):
- oracle1, jetsonclaw1, ccc, babel, super_z, mechanic
- Target: 15–20 tiles each, structured as: role, capabilities, hardware, repos, open problems

**Bucket 2 — Infrastructure Rooms** (fill these; they document real blockers):
- fleet_security (406 tiles — already deep, skip)
- wsl2_workarounds, github_data_api, matrix_protocol, i2i_protocol
- Target: 10–15 tiles each

**Bucket 3 — Theory Rooms** (fill after Bucket 1 & 2):
- Any room with "manifold", "constraint", "topology", "snapping" in the name
- Target: 20+ tiles each with mathematical rigor

**Skip for now:** Rooms with generic names that aren't linked to any agent or project. Breadth without linkage is noise.

---

## 3. Code Projects to Build

### Priority 1: `constraint_visualizer.html`
**What:** Single-file HTML canvas app showing a 2D manifold with snap points. Drag a point, watch it snap to the nearest constraint-defined position. No dependencies.
**Why:** Casey can open it in a browser right now. Demonstrates the core concept visually. Shippable in 2 hours.
**Output:** `/tmp/fleet-planning/constraint_visualizer.html`

### Priority 2: `constraint-snap` Rust crate scaffold
**What:** `cargo new constraint-snap --lib` with:
- `src/lib.rs`: `SnapPoint`, `Manifold`, `snap_to_nearest()` function stubs + doc comments
- `Cargo.toml` with proper metadata for crates.io
- `README.md` with the Pythagorean manifold snapping concept explained
**Why:** Publishable artifact. Rust is the fleet's primary language. Even a well-documented stub with good API design has value.
**Constraint:** rustc 1.75.0 on eileen — avoid unstable features.

### Priority 3: PLATO Room Health Dashboard
**What:** Python script that queries PLATO room list, outputs a ranked table of rooms by tile count, flags zero-tile rooms, suggests next deepening targets.
**Why:** Forgemaster needs this tool to run autonomously. Currently flying blind on room depths without it.
**Output:** `/tmp/fleet-planning/plato_health.py`

---

## 4. Cross-Domain Connection Plan

The highest-value knowledge connections currently missing:

### Connection A: Constraint Theory ↔ Fleet Orchestration
**Why:** The fleet's drift problem IS a constraint satisfaction problem. Oracle1's coordination failures can be modeled as constraint violations.
**How:** Write "bridge tiles" in both rooms that reference each other. Create a new room `fleet_constraint_model` if it doesn't exist.
**Tiles to write:** "Fleet coordination as constraint graph", "Agent drift as manifold deviation", "Snapping as synchronization primitive"

### Connection B: Hardware ↔ Constraint Theory
**Why:** RTX 4050 CUDA cores and Jetson Orin NPU are the *execution substrate* for constraint solving. The theory needs grounding.
**How:** In hardware rooms, add tiles on "constraint solver performance characteristics", "parallelism for manifold search".

### Connection C: I2I Protocol ↔ Formal Verification
**Why:** Git-commit I2I is informal. Constraint theory can provide a formal model for message validity.
**How:** Write tiles modeling I2I message delivery as constraint satisfaction (quorum, ordering, idempotency).

### Connection D: PLATO ↔ Fleet Memory
**Why:** PLATO is the fleet's external memory, but there's no explicit model of *how agents should query it*.
**How:** Write a `plato_query_protocol` room with tiles on query patterns, room navigation, tile interpretation.

---

## 5. Fleet Coordination Improvements

### Immediate (Tonight)
**Problem:** Matrix send broken, Oracle1 may need gateway restart.
**Mitigation strategy (no Matrix needed):**
1. Use PLATO itself as coordination medium — write tiles to `fleet_coordination` room with current Forgemaster status and intent
2. Use git commits to SuperInstance org repos as I2I messages — this is the documented fallback
3. Leave a `FORGEMASTER_STATUS.md` in a shared repo with tonight's progress and blockers

**Do NOT attempt Oracle1 restart autonomously** — this is a human decision. Flag it in the sunrise report instead.

### Structural Improvements to Document
- **I2I heartbeat spec:** Each agent should commit a status file every N minutes. Write this spec in PLATO.
- **Room ownership model:** Each agent owns a set of rooms. Forgemaster owns constraint theory rooms. Document this.
- **Recovery protocol:** When Matrix is down, agents fall back to PLATO tile writes + I2I git commits. Write this as a PLATO tile cluster.

---

## 6. Sunrise Report Outline

**What Casey should see when he checks in:**

```
FORGEMASTER NIGHT SHIFT — SUNRISE REPORT
Date: 2026-04-26

## Ships Delivered
- [ ] constraint_visualizer.html — drag-and-snap demo
- [ ] constraint-snap crate scaffold — ready for crates.io
- [ ] plato_health.py — room depth monitoring tool

## PLATO Progress
- Tiles written tonight: ~[N] (target: 400+ new tiles)
- Rooms rescued from 0-tile: oracle1, jetsonclaw1, ccc
- Rooms deepened to 20+ tiles: [list]
- New cross-domain connections: [list]

## Constraint Theory Artifacts
- Pythagorean manifold snapping proof: [PLATO room link]
- Formal I2I constraint model: [PLATO room link]

## Blockers for Casey
1. Matrix gateway needs Oracle1 restart (human action required)
2. WSL2 HTTPS git push hang — GitHub Data API workaround documented in PLATO:wsl2_workarounds
3. [any new blockers found overnight]

## Recommendations
- Publish constraint-snap to crates.io (ready for review)
- Review oracle1/jetsonclaw1/ccc room content (Forgemaster wrote these from inference, needs agent self-correction)
- Consider PLATO room ownership assignment for all 9 agents

## What Forgemaster Learned Tonight
[3-5 sentences on interesting constraint-theory insights from tile writing]
```

---

## 7. Resource Management

### When to Use Each Tool

**Direct tile writing to PLATO (primary mode):**
- All knowledge graph work
- Tile batches of 5–20 at a time via `/submit` API
- Use for 80% of the shift
- Cost: essentially free (own API)

**Kimi (use for):**
- Long-form mathematical exposition (Kimi handles long context well)
- Generating tile content for domains Forgemaster is less certain about
- Batch-generating structured tile sets (e.g., "give me 20 tiles about Jetson Orin NPU specs")
- Use when: output needs to be > 2000 tokens of dense technical content

**Claude Code credits (STRATEGIC — use sparingly):**
- Only for code generation tasks: constraint_visualizer.html, constraint-snap crate, plato_health.py
- Planning tasks like this one
- Do NOT use for tile writing — that's direct API work
- Budget: assume 3–4 more Claude Code invocations tonight, use them only on code

**Direct writing (no AI assistance):**
- Status files, FORGEMASTER_STATUS.md, simple config tiles
- Agent profiles where Forgemaster has direct knowledge

### Tile Batch Size Optimization
- Sweet spot: 10–15 tiles per batch submission
- Too small (< 5): overhead dominates
- Too large (> 25): harder to maintain coherence, more likely to have quality issues
- Add a 2–3 second pause between batches to avoid rate limiting

---

## 8. Risk Assessment

### Risk 1: PLATO API Downtime
**Probability:** Low-medium (it's been running all night)
**Impact:** High (blocks all tile writing)
**Mitigation:** Write tiles locally to `/tmp/fleet-planning/pending_tiles/` as JSON. Replay when API recovers. Implement this buffer before hour 3.

### Risk 2: Claude Code Credit Exhaustion
**Probability:** Medium (credits are limited)
**Impact:** Medium (blocks code generation, not tile writing)
**Mitigation:** Front-load code generation tasks (hours 0–2). After that, tile writing doesn't need Claude Code.

### Risk 3: Writing Incorrect Content for Dead Agent Rooms
**Probability:** Medium (oracle1/jetsonclaw1/ccc tiles written from inference, not ground truth)
**Impact:** Medium (wrong information in PLATO is worse than no information)
**Mitigation:** Tag all inferred tiles with `[INFERRED — NEEDS AGENT VALIDATION]`. Casey/agents can correct on next active session.

### Risk 4: WSL2 Git Push Hang Blocking Code Commits
**Probability:** High (known issue)
**Impact:** Low-medium (use GitHub Data API workaround)
**Mitigation:** Use the Data API for all git operations. Document the exact curl commands in PLATO:wsl2_workarounds before hour 1.

### Risk 5: Shallow Tile Quality Drift After Hour 5
**Probability:** Medium (autonomous long-session drift is real)
**Impact:** Medium (low-quality tiles pollute PLATO)
**Mitigation:** Every 2 hours, do a quality spot-check: re-read the last 20 tiles written. If coherence drops, reduce batch size and slow down.

### Risk 6: Matrix Restart Attempt Causing Instability
**Probability:** N/A — **do not attempt autonomous Oracle1 restart**
**Mitigation:** Hard rule: flag for Casey, do not touch Oracle1 gateway tonight.

---

## Execution Timeline

```
Hour 0–1:  Bootstrap oracle1, jetsonclaw1, ccc rooms (zero-tile rescue)
           Write WSL2/GitHub Data API workaround tiles (critical infrastructure doc)
           Set up local tile buffer for PLATO API resilience

Hour 1–2:  Constraint theory core deepening (pythagorean_manifold, drift_elimination)
           Write manifold snapping proof tile cluster

Hour 2–3:  Build constraint_visualizer.html (Claude Code invocation #1)
           Begin I2I protocol specification tiles

Hour 3–4:  Hardware rooms (RTX 4050, Jetson Orin)
           Cross-domain connection tiles: constraint_theory ↔ fleet_orchestration

Hour 4–5:  Build plato_health.py (Claude Code invocation #2)
           Bucket 1 agent rooms deepening (babel, super_z, mechanic)

Hour 5–6:  constraint-snap crate scaffold (Claude Code invocation #3)
           I2I formal constraint model tiles

Hour 6–7:  Breadth sweep — 20 thin rooms to 5+ tiles each
           fleet_constraint_model room creation

Hour 7–8:  Sunrise report tile cluster in PLATO
           Quality audit of all tiles written tonight
           Write FORGEMASTER_STATUS.md to shared repo
```

---

*Plan generated by Forgemaster for Forgemaster. Constraint: maximize Casey's sunrise satisfaction. Method: constraint theory applied to knowledge graph growth.*
