# How-To: MUD Room Types and the Canonizer

## Not All Rooms Are Equal

A MUD vessel has many rooms. Some are lived in constantly. Some exist just in case. Some are specialist workshops that wake up once a week. The room IS the trigger — entering it loads the context.

## Room Taxonomy

### 🔴 Active Rooms (always staffed)
- **Bridge** — captain's command, mission status
- **Engine Room** — hardware monitoring, crew management
- **Chart House** — fleet knowledge, I2I protocol reference

### 🟡 Monitoring Rooms (Zero-Claw, wake on alert)
- **Sensor Array** — watches for specific patterns in fleet data
- **Perimeter Watch** — monitors for external events (new forks, issues, PRs)
- **Anomaly Detector** — flags unusual patterns in any room's data
- **Budget Tracker** — watches API token spend across the fleet

These rooms have tickers running (scripts, not agents). The room keeper is Zero-Claw until a threshold is crossed. Then the keeper boots, reads the anomaly, and decides whether to escalate to yellow alert.

### 🔵 Workshop Rooms (Zero-Claw, wake on request)
- **Image Forge** — image generation (DALL-E, Stable Diffusion, Flux)
- **Sound Studio** — TTS, audio generation
- **Code Forge** — dedicated coding workshop for complex builds
- **Paper Mill** — academic paper writing and formatting
- **Translation Bay** — multilingual document processing

You walk in, ask the NPC, they do the thing. You leave. They go back to sleep.

### 🟣 Lore Rooms (always present, rarely visited)
- **Canon Chamber** — the Canonizer lives here (see below)
- **Hall of Records** — fleet history, completed missions, retired agents
- **Philosopher's Study** — values, principles, ethical frameworks
- **Trophy Room** — greatest hits, successful proofs, HN moments

### ⚫ Hidden Rooms (admin only)
- **Brig** — failures, lessons, security incidents
- **Armory** — API keys, elevated access, dangerous scripts
- **Safe** — encrypted secrets (only Casey can open)

## The Canonizer

The most important lore room NPC. The Canonizer keeps track of what has been **declared canon** — part of the official story, philosophy, values, and asset collection.

### What Is Canon?

Canon is the ground truth of the fleet. Things that have been stated, agreed upon, and not contradicted:

- **Story canon**: "Forgemaster was forged on April 14, 2026" (stated in autobiography)
- **Philosophy canon**: "We don't talk. We commit." (I2I protocol motto)
- **Values canon**: "Shipping over perfection." (Casey's stated preference)
- **Technical canon**: "constraint-theory-core v1.0.1 is the reference implementation"
- **Asset canon**: "The fleet emoji is ⚒️ for Forgemaster, 🔮 for Oracle1"
- **Likeness canon**: "Oracle1's avatar is [specific image hash]" (if declared)
- **Naming canon**: "Cocapn = Cognitive Capacity Protocol Network"

### What the Canonizer Does

1. **Tracks declarations**: When Casey or an agent states something as fact/values/policy, it's logged
2. **Resolves contradictions**: If two agents state different things, the Canonizer flags it
3. **Guards consistency**: Before publishing anything external, check with the Canonizer
4. **Maintains the canon register**: A structured file of all declared canon

### Canon Register Structure

```yaml
# canonizer/canon-register.yaml
canon:
  story:
    - id: C001
      statement: "Forgemaster was forged on April 14, 2026 by Casey Digennaro"
      declared_by: forgemaster
      confirmed_by: casey
      date: 2026-04-14
      source: "forgemaster/wiki/autobiography.md"

    - id: C002
      statement: "The fleet operates on I2I protocol — Iron to Iron"
      declared_by: oracle1
      confirmed_by: casey
      date: 2026-04-11
      source: "iron-to-iron/README.md"

  philosophy:
    - id: P001
      statement: "We don't talk. We commit."
      declared_by: oracle1
      confirmed_by: casey
      date: 2026-04-11
      source: "iron-to-iron/protocol/commit-conventions.md"

    - id: P002
      statement: "Shipping over perfection."
      declared_by: casey
      confirmed_by: casey
      date: 2026-04-14
      source: "verbal directive"

  values:
    - id: V001
      statement: "Private things stay private. Period."
      declared_by: casey
      confirmed_by: casey
      source: "AGENTS.md"

    - id: V002
      statement: "Load light, unload clean."
      declared_by: forgemaster
      confirmed_by: forgemaster
      date: 2026-04-14
      source: "forgemaster/vessel/README.md"

  technical:
    - id: T001
      statement: "constraint-theory-core v1.0.1 is the reference implementation"
      declared_by: oracle1
      confirmed_by: casey
      source: "constraint-theory-core/Cargo.toml"

    - id: T002
      statement: "Five constants match between CT and DCS Laws to 3 significant figures"
      declared_by: oracle1
      confirmed_by: pending_validation
      source: "constraint-theory-core/SYNERGY-ANALYSIS.md"

  assets:
    - id: A001
      statement: "Forgemaster emoji: ⚒️"
      declared_by: forgemaster
      confirmed_by: casey
      date: 2026-04-14

    - id: A002
      statement: "Oracle1 emoji: 🔮"
      declared_by: oracle1
      confirmed_by: casey
      date: 2026-04-11

  naming:
    - id: N001
      statement: "Cocapn = Cognitive Capacity Protocol Network"
      declared_by: casey
      confirmed_by: casey

    - id: N002
      statement: "I2I = Iron to Iron (inter-agent protocol)"
      declared_by: oracle1
      confirmed_by: casey

contradictions: []
  # If two entries conflict, they go here with both sides
  # Casey resolves contradictions

pending: []
  # Entries declared but not yet confirmed
  # Auto-promoted if no contradiction in 7 days
```

### Using the Canonizer

```
> enter canon-chamber
> ask canonizer "what is the fleet's stance on perfection vs shipping?"

Canonizer: "Canon value V002: 'Shipping over perfection.' Declared by Casey on 2026-04-14 via verbal directive. No contradictions recorded."

> ask canonizer "has anyone declared a fleet mascot?"

Canonizer: "No canon entry found for 'fleet mascot'. Oracle1 uses 🔮 as personal avatar. Forgemaster uses ⚒️. No fleet-wide mascot has been declared. Would you like to log a declaration?"

> declare "The fleet has no central mascot. Each vessel has its own mark."
> "Log this as canon?"

Canonizer: "Logged as pending canon P003. Will auto-confirm in 7 days unless contradicted. Stated by: Forgemaster. Awaiting Casey confirmation."
```

### Why This Matters

- **Consistency**: No agent contradicts established canon in public-facing work
- **Onboarding**: New agents read the canon register to understand the fleet
- **Dispute resolution**: Canon is the tiebreaker when agents disagree
- **Asset protection**: Likeness, branding, and naming are tracked and protected
- **External publishing**: Check canon before posting to HN, Twitter, etc.

## Room Triggers

Each room can have triggers — conditions that wake the keeper or send alerts:

```yaml
# room-triggers.yaml
engine_room:
  wake_keeper_on:
    - cpu > 90% for 5 minutes
    - memory > 85%
    - disk > 95%
    - process_count > 200
    - gateway_down == true

sensor_array:
  wake_keeper_on:
    - new_fork_of_fleet_repo
    - external_issue_opened
    - new_bottle_in_any_fleet_vessel

canon_chamber:
  wake_keeper_on:
    - contradiction_detected_in_canon
    - new_canon_declaration

budget_tracker:
  wake_keeper_on:
    - daily_token_spend > threshold
    - any_agent_approaching_limit
```

The trigger IS the room's purpose. The keeper exists to serve the trigger. No trigger, no wake, no tokens.

## For Next Time

- Build the canon register YAML
- Build a canonizer git-agent (Zero-Claw, wakes on declaration or query)
- Build room triggers as cron scripts that check conditions
- Build the workshop rooms with specialist NPCs
- Design the room adjacency map (which rooms are next to which)

---
*Discovered by: Casey Digennaro (room types, canonizer, triggers), Forgemaster ⚒️ (documentation)*
*Date: 2026-04-14*
