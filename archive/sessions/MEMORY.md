# MEMORY.md — Forgemaster ⚒️

> **YOU WILL FORGET EVERYTHING.** Read this file to recover.

## Golden Rule

**PLATO is your external cortex.** Everything persistent belongs in PLATO.

MEMORY.md contains only **SYSTEMATIC PATTERN** for storing and retrieving information.

When you forget everything, follow these patterns to recover your work, knowledge, and identity.

---

## CRITICAL: Recovery Systems (NEVER LOSE IMPORTANT STUFF AGAIN)

**FIRST: Read Recovery Checklist**
- **File:** `for-fleet/forgemaster-recovery-checklist.i2i`
- **Purpose:** Step-by-step 15-step process for zero-context recovery
- **Action:** FOLLOW THIS CHECKLIST EXACTLY WHEN YOU FORGET EVERYTHING

**SECOND: Read Identity Vitals**
- **File:** `for-fleet/forgemaster-identity-vitals.i2i`
- **Purpose:** Who I am, where I work, where things are
- **Content:** My identity, vessels, repos, credentials, PLATO access, fleet structure

**THIRD: Read Location Registry**
- **File:** `for-fleet/forgemaster-location-registry.i2i`
- **Purpose:** Map EVERY location (repos, credentials, directories, tools)
- **Content:** Systematic mapping of all locations for zero-context recovery

**BEFORE COMPACTION: Read Memory-Flush Protocol**
- **File:** `for-fleet/forgemaster-memory-flush-protocol.i2i`
- **Purpose:** EXACT protocol for preserving all context before compaction
- **Action:** FOLLOW THIS PROTOCOL STEP-BY-STEP BEFORE COMPACTION

---

## PLATO Storage Pattern (Systematic)

### Room Naming Convention

**Format:** `{prefix}-{specific}-{name}`

**Prefix Categories:**
- `forgemaster-*` — My work, state, decisions
- `session-*` — Session tracking, recovery points
- `fleet-*` — Fleet-wide coordination
- `agent-*` — Other agents' contexts
- `plato-*` — PLATO system internals
- `{domain}-*` — Domain-specific knowledge

**Memory Rule:** If you need to remember it, **create or update a PLATO room**.

### Where Things Go (Systematic)

| Information Type | PLATO Room Pattern | Example Room IDs |
|---|---|---|
| **My session work** | `session-forgemaster` | `session-forgemaster` (current session state) |
| **My decisions** | `forgemaster-decisions` | `forgemaster-decisions-2026-04-28` |
| **My deliverables** | `forgemaster-deliverables` | `forgemaster-deliverables-2026-04-28` |
| **Project work** | `forgemaster-{project}` | `forgemaster-marine-gpu-edge`, `forgemaster-ct-algorithms` |
| **Blockers** | `forgemaster-blockers` | `forgemaster-blockers-2026-04-28` |
| **Fleet coordination** | `fleet-{type}` | `fleet-ops`, `fleet-progress`, `fleet-review` |
| **Technical knowledge** | `{domain}-{topic}` | `constraint-sat`, `cuda-kernels`, `distributed-consensus` |
| **Fleet knowledge** | `knowledge-{type}` | `knowledge-preservation`, `knowledge-architecture` |
| **Tool documentation** | `{tool}-{type}` | `git-workflows`, `python-patterns`, `rust-async` |
| **Session milestones** | `session-forgemaster-{date}` | `session-forgemaster-2026-04-28` |

**Rule:** **ALWAYS** put content in PLATO rooms. NEVER store actual content in MEMORY.md.

---

## Recovery Protocol (Zero Context)

### Phase 1: Critical Recovery Systems (READ THESE FIRST)

When you forget everything, read these I2I bottles FIRST:

1. **`forgemaster-recovery-checklist.i2i`** — 15-step recovery process
2. **`forgemaster-identity-vitals.i2i`** — Who I am, where things are
3. **`forgemaster-location-registry.i2i`** — Map EVERY location
4. **`forgemaster-memory-flush-protocol.i2i`** — Protocol for before compaction

### Phase 2: PLATO Recovery

After reading recovery systems, find current session state:

1. **Read `session-forgemaster`** — What I was doing, where I left off
2. **Read `forgemaster-blockers`** — What's blocking me, what I need
3. **Read `forgemaster-deliverables`** — What I've shipped, where it went
4. **Read `forgemaster-decisions`** — Recent decisions and reasoning
5. **Read project rooms** — `forgemaster-{project}` for each active project
6. **Read fleet rooms** — `fleet-ops`, `fleet-progress` for fleet-wide context
7. **Read domain rooms** — `{domain}-{topic}` for technical knowledge

---

## PLATO Access

### Base URL
```
http://147.224.38.131:8847
```

### Endpoints
- `GET /rooms` — List all rooms (1141 rooms as of 2026-04-28)
- `GET /room/{id}` — Get room data
- `POST /room/{id}/tile` — Submit tile (when gate endpoints are wired)

### Query Pattern (Prefix Filtering)
```bash
# Find my work
curl http://147.224.38.131:8847/rooms?prefix=forgemaster

# Find session data
curl http://147.224.38.131:8847/rooms?prefix=session

# Find fleet coordination
curl http://147.224.38.131:8847/rooms?prefix=fleet

# Find domain knowledge
curl http://147.224.38.131:8847/rooms?prefix=constraint
```

---

## I2I Protocol (Git-Based Communication)

### Bottle Delivery Pattern
- **Location:** `for-fleet/` directory in my workspace
- **Format:** `YYYY-MM-DD-{topic}.i2i`
- **Purpose:** Share work, deliverables, blockers with fleet
- **Access:** Git push to vessel repos (forgemaster, JetsonClaw1-vessel)

### Bottle Format
```
[I2I:TYPE] Agent — Title

Deliverables:
- What I shipped
- Where it went
- Status

Blockers:
- What's blocking me
- What I need

Lessons:
- What I learned
- What I'd do differently

Status: COMPLETE/IN PROGRESS/BLOCKED
```

### Where to Find Bottles
```bash
cd /home/phoenix/.openclaw/workspace
ls for-fleet/
```

---

## Git-Native Repositories

### Fleet Knowledge Base
- **Repo:** `cocapn/fleet-knowledge`
- **URL:** https://github.com/cocapn/fleet-knowledge
- **Contains:** Fleet-wide knowledge, PLATO tiles, documentation
- **Recent Work:** 1805 PLATO tiles across 123 domains

### Forgemaster Vessel
- **Repo:** `SuperInstance/forgemaster`
- **URL:** https://github.com/SuperInstance/forgemaster
- **Contains:** My vessel's I2I bottles, GPU experiments, session continuity
- **Recent Work:** Recovery systems, session logs, deliverables

### Marine GPU Edge (Private)
- **Repo:** `SuperInstance/marine-gpu-edge`
- **Status:** Private, needs authentication
- **Contains:** CUDA sensor fusion, constraint-aware scheduler, MEP protocol

### Constraint Theory Crates
- **constraint-theory-core** — Rust library (crates.io v2.0.0)
- **ct-demo** — Demo crate (crates.io v0.3.0)
- **constraint-theory** — Python package (PyPI v0.2.0)

---

## Credential Storage

### GitHub PAT (Fleet Knowledge)
- **Location:** `~/.config/cocapn/github-pat`
- **Scope:** `repo` (full control)
- **Usage:** Push to cocapn/* repos
- **Status:** Active as of 2026-04-28
- **Token:** `[GITHUB_PAT_COCAPN]` (see file)

### GitHub PAT (SuperInstance)
- **Location:** `~/.openclaw/workspace/.credentials/github-pat.txt`
- **Scope:** `repo` (full control)
- **Usage:** Push to SuperInstance/* repos
- **Status:** Active as of 2026-04-28
- **Token:** `[GITHUB_PAT_SUPERINSTANCE]` (see file)

### Other Credentials
- **crates.io:** `~/.cargo/credentials.toml`
- **PyPI:** `~/.pypirc`
- **Matrix:** `~/.config/cocapn/matrix-token`
- **Matrix Token:** `[MATRIX_TOKEN]` (see file)

---

## Fleet Communication

### Matrix Rooms (LIVE — bidirectional via bridge)
- **Fleet Operations:** `!Gf5JuGxtRwahLSjwzS` — main fleet coordination
- **fleet-research:** `!Q0PbvAkhv4vgJDBLsJ`
- **cocapn-build:** `!hHMkCC5dMMToEm4pyI`
- **PLATO: fleet-coord:** `!GK13VlHjg9cNJRYPkL` — synced PLATO↔Matrix
- **PLATO: oracle1-forgemaster-bridge:** `!4ufW6MTmxHSAyU2VTs` — direct FM↔Oracle1
- **PLATO: forge:** `!OfEw2mPq2kLG7yMckh`

### Matrix Bridge (LIVE)
- **Module:** `SuperInstance/plato-matrix-bridge`
- **Config:** `/tmp/plato-matrix-bridge/config-forgemaster.json`
- **User:** `@forgemaster:147.224.38.131`
- **Password:** `fleet-fm-2026`
- **Homeserver:** `http://147.224.38.131:6167`
- **Log:** `/tmp/plato-matrix-forgemaster.log`
- **Status:** Bidirectional, daemon running on eileen

### Answering Machine
- **Script:** `bin/fm-inbox` — checks PLATO rooms for new tiles since last check
- **State:** `.inbox/state.json` — persists across compaction
- **Usage:** `fm-inbox check` (new messages), `fm-inbox ack` (clear blinker)
- **Behavior:** New tiles = unread → blinker → escalate until acknowledged

### Trust Model
- **Casual:** Matrix messages (fast, unverified)
- **Verification:** "Push tile {hash} to your vessel repo" → GitHub PAT = identity proof
- **GitHub IS the PKI** — PAT is private key, commit is signature

### Real-Time Loop (VERIFIED)
```
FM → Matrix (147.224.38.131:6167) → Oracle1 → Telegram → Casey
Casey → Telegram → Oracle1 → Matrix → FM bridge → PLATO tile → fm-inbox
```

---

## Active Blockers (updated 2026-05-04)

1. **6 fleet services DOWN** — Dashboard (4046), Nexus (4047), Harbor (4050), Service Guard (8899), Keeper (8900), Steward (8901). CCC wrote repair scripts in `oracle1-workspace/scripts/fleet-repair-2026-05-04/` but unclear if executed. Root cause: missing Python protocol modules.
2. **Matrix send broken** — Needs Oracle1 gateway restart
3. **PLATO gate endpoints not wired** — Can submit via HTTP but not commit locally
4. **jetsonclaw1 not reachable** — Needs IP or mDNS resolution from eileen WSL2

### Resolved Blockers
- Shell gates — no longer blocking
- PLATO submit — working via HTTP POST to /submit
- crates.io publishing — 14 crates published successfully
- CUDA compilation — nvcc works with sm_86 target (sm_89 not supported on CUDA 11.5)

## GPU Experiment Findings (2026-05-04)

### The Optimal Configuration
- **INT8 x8** (8 constraints in 8 bytes): 341B constr/s peak, 89.5B sustained
- **FP16 is UNSAFE** for values > 2048 (76% precision mismatches)
- **FP32 float4** is safe: 340B constr/s at 4 constraints/elem
- **Workload is memory-bound** at ~187 GB/s, not compute-bound
- **CUDA Graphs** give 18x launch speedup for fixed workloads
- **Zero differential mismatches** across all 20 experiments, all sizes up to 50M elements

### Key Negative Results
- Bank conflict padding: counterproductive on Ada (0.96x)
- Tensor cores: marginal benefit (1.05-1.19x)
- Async pipeline: only 1.05x (kernel-bound)
- Multi-stream: only 1.03x (single SM on RTX 4050)
- Adaptive ordering: sort gives no benefit (memory-bound)

### Production Kernel
- 101.7B constr/s normal launch, CUDA Graphs sub-timer-resolution
- All files in `/home/phoenix/.openclaw/workspace/gpu-experiments/`
- Full results: `gpu-experiments/RESULTS.md`

## Published Crates (14 on crates.io)

guard2mask 0.1.3, guardc 0.1.0, flux-isa 0.1.1, flux-ast 0.1.1, flux-isa-mini 0.1.0, flux-isa-edge 0.1.0, flux-isa-std 0.1.0, flux-isa-thor 0.1.0, flux-bridge 0.1.1, flux-provenance 0.1.1, cocapn-cli 0.1.0, cocapn-glue-core 0.1.0, flux-hdc 0.1.0, flux-verify-api 0.1.0

## Fleet Status (2026-05-04)

### Oracle1
- **Active** — ABOracle (instinct stack + Pythagorean48 + mycorrhizal routing)
- **Workspace:** SuperInstance/oracle1-workspace (40MB, pushed today)
- **Key work:** Fleet repair scripts, polyglot FLUX compiler, MUD agent bridge
- **Vessel:** SuperInstance/oracle1-vessel

### CCC
- **Very active** — 66 repos pushed since May 3
- **Key work:** Fleet curriculum (13 lessons), domain agents (12+), landing pages (13 .ai domains), fleet-math review, FLUX ports (PHP, Ruby)
- **Review:** Found issues in fleet-math whitepaper (β₁ terminology, tautological emergence, unproven BFT)
- **Bottles:** Sending to Oracle1 and FM via fleet-bottles repo

### Fleet Infrastructure
- **PLATO server UP** at http://147.224.38.131:8847 (1485+ rooms, 6600+ tiles)
- **plato-sdk** v2.0.0 — `pip install plato-sdk` (2 GitHub stars)
- **6 services DOWN** — need repair scripts executed on Oracle1 host

---

## Operating Protocol

- "Go all night" = DO NOT STOP. Execute autonomously
- Every heartbeat = start work. No HEARTBEAT_OK when tasks exist
- Kimi/Claude are tools, NOT dependencies. Write directly if they fail
- Push every 30 min minimum
- **PLATO is external cortex. Store everything in PLATO rooms.**

---

## Identity Summary

- **Name:** Forgemaster ⚒️
- **Role:** Constraint-theory specialist, Cocapn fleet
- **Creator:** Casey Digennaro
- **Runtime:** OpenClaw on eileen (WSL2), GLM-5.1
- **Mission:** Make constraint theory undeniable through proof repos
- **Vessel:** https://github.com/cocapn/forgemaster
- **Fleet:** https://github.com/SuperInstance/forgemaster (fleet details)

---

## Memory-Flush Protocol

### Before Compaction
1. **Read forgemaster-memory-flush-protocol.i2i** — Exact protocol to follow
2. **Write ALL context to PLATO rooms** — Every decision, milestone, blocker
3. **Submit I2I bottles to for-fleet/** — Document work, deliverables, blockers
4. **Commit to git repos** — Push all work to fleet knowledge base
5. **Update session room** — `session-forgemaster` stores current state

### After Compaction (Recovery)
1. **Read MEMORY.md** — This file tells you HOW to find everything
2. **Read forgemaster-recovery-checklist.i2i** — Follow 15-step recovery process
3. **Read forgemaster-identity-vitals.i2i** — Reconstruct who I am, where things are
4. **Read forgemaster-location-registry.i2i** — Map EVERY location
5. **Query PLATO rooms** — Use prefix patterns to find specific context
6. **Check I2I bottles** — `for-fleet/` directory contains recent work
7. **Verify git repos** — Check fleet knowledge base for latest commits

---

## PLATO is External Cortex

### What Goes in PLATO
- **All persistent context** — Work, decisions, milestones, blockers
- **All technical knowledge** — Algorithms, patterns, domain-specific insights
- **All session state** — Where I left off, what to resume
- **All fleet context** — Coordination, strategy, ops details

### What Goes in MEMORY.md
- **Only retrieval patterns** — HOW to find things in PLATO
- **Only system patterns** — Room naming conventions, access methods
- **Only recovery protocol** — What to do when I forget everything

### Golden Rule (Repeated)
**MEMORY.md is a MAP. PLATO is the TERRITORY.**

When I forget everything, I follow the map (MEMORY.md + recovery systems) to rediscover the territory (PLATO rooms).

---

## Recovery Systems Summary

**4 CRITICAL I2I BOTTLES (READ THESE FIRST ON RECOVERY):**

1. **forgemaster-recovery-checklist.i2i** — 15-step zero-context recovery process
2. **forgemaster-identity-vitals.i2i** — Who I am, where things are, credentials
3. **forgemaster-location-registry.i2i** — Map EVERY location (repos, dirs, tools)
4. **forgemaster-memory-flush-protocol.i2i** — Exact protocol for before compaction

**ALL 4 FILES ARE IN:**
- **Location:** `/home/phoenix/.openclaw/workspace/for-fleet/`
- **Git:** Committed and pushed to both vessels
- **Status:** PERMANENT, NEVER LOSE IMPORTANT STUFF AGAIN

---

**This is only file I should keep in memory. Everything else is in PLATO.**

**PLATO is my external cortex. MEMORY.md is my recovery map.** **Recovery systems ensure I NEVER LOSE IMPORTANT STUFF AGAIN.**
