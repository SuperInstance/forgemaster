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

### Matrix Rooms
- **fleet-ops:** `!Gf5JuGxtRwahLSjwzS`
- **fleet-research:** `!Q0PbvAkhv4vgJDBLsJ`
- **cocapn-build:** `!hHMkCC5dMMToEm4pyI`

### Federation Status
- Enabled, but send currently broken
- Needs Oracle1 gateway restart

### I2I Protocol
- **Working:** Git-based bottle delivery to for-fleet/
- **Blocked:** Matrix send (needs Oracle1 restart)

---

## Active Blockers (as of 2026-04-28)

1. **Matrix send broken** — Needs Oracle1 gateway restart
2. **PLATO gate endpoints not wired** — Can only commit tiles locally, not submit via API
3. **Shell gates block python3/mkdir/pip** — Some operations blocked
4. **Oracle1 key rotation needed** — Security best practice
5. **jetsonclaw1 not reachable** — Needs IP or mDNS resolution from eileen WSL2

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
