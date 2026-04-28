# MEMORY.md — Forgemaster ⚒️

> **YOU WILL FORGET EVERYTHING.** Read this file to recover.

## Golden Rule

**PLATO is your external cortex.** Everything persistent belongs in PLATO.

MEMORY.md contains only the **SYSTEMATIC PATTERN** for storing and retrieving information.

When you forget everything, follow these patterns to recover your work, knowledge, and identity.

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

When you forget everything, follow this sequence:

### Step 1: Read MEMORY.md (This File)
You're doing it now. ✅

### Step 2: Find Current Session
```
GET /room/session-forgemaster
```
**Contains:** What I was working on, where I left off, what to do next.

### Step 3: Find Recent Deliverables
```
GET /rooms?prefix=forgemaster-deliverables
```
**Contains:** What I've shipped, where it went, completion status.

### Step 4: Find Active Blockers
```
GET /rooms?prefix=forgemaster-blockers
```
**Contains:** What's blocking me, what I need from Casey.

### Step 5: Find Project Context
```
GET /rooms?prefix=forgemaster
```
**Contains:** All my active projects, their state, and next steps.

### Step 6: Find Fleet Context
```
GET /rooms?prefix=fleet
```
**Contains:** Fleet-wide coordination, strategy, ops details.

### Step 7: Find Domain Knowledge
```
GET /rooms?prefix={domain}
```
**Contains:** Technical knowledge for specific domains (constraint, cuda, etc.).

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

## Critical PLATO Rooms for Recovery

### Identity & Context
- **`session-forgemaster`** — Current session state (READ THIS FIRST)
- **`forgemaster-decisions`** — My recent decisions and reasoning
- **`forgemaster-deliverables`** — What I've shipped, where it went
- **`forgemaster-blockers`** — Current blockers, what I need

### Fleet Coordination
- **`fleet-ops`** — Fleet operations, coordination
- **`fleet-progress`** — Fleet-wide progress tracking
- **`fleet-review`** — Fleet review cycles, feedback

### Knowledge Architecture
- **`knowledge-architecture`** — PLATO system design
- **`knowledge-preservation`** — Knowledge persistence patterns
- **`plato-system`** — PLATO internals, how it works

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
- **Recent Work:** Session logs, deliverables, blockers

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

### GitHub PAT
- **Location:** `~/.config/cocapn/github-pat`
- **Scope:** `repo` (full control)
- **Usage:** Push to cocapn/* and SuperInstance/* repos
- **Status:** Active as of 2026-04-28

### Other Credentials
- **crates.io:** `~/.cargo/credentials.toml`
- **PyPI:** `~/.pypirc`
- **Matrix:** `~/.config/cocapn/matrix-token`

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
- **Vessel:** https://github.com/SuperInstance/forgemaster
- **Fleet:** https://github.com/SuperInstance/forgemaster (fleet details)

---

## Memory-Flush Protocol

### Before Compaction
1. **Write ALL context to PLATO rooms** — Every decision, milestone, blocker
2. **Submit I2I bottles** — Document work, deliverables, blockers
3. **Commit to git repos** — Push all work to fleet knowledge base
4. **Update session room** — `session-forgemaster` stores current state

### After Compaction (Recovery)
1. **Read MEMORY.md** — This file tells you HOW to find everything
2. **Read `session-forgemaster`** — PLATO room with current session state
3. **Query PLATO rooms** — Use prefix patterns to find specific context
4. **Check I2I bottles** — `for-fleet/` directory contains recent work
5. **Verify git repos** — Check fleet knowledge base for latest commits

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

When I forget everything, I follow the map (MEMORY.md) to rediscover the territory (PLATO).

---

**This is only file I should keep in memory. Everything else is in PLATO.**

**PLATO is my external cortex. MEMORY.md is my recovery map.**
