# Forgemaster Runtime Specification

> The hermit crab, not the shell. Travel light. Tools in the truck.

## What It Is

A stripped-down OpenClaw agent configuration that boots from PlatoClaw tiles,
not from workspace files. Past sessions are PLATO rooms — available on demand,
not loaded by default. The agent starts clean every time and reconstructs what
it needs from the world state (tiles).

## Philosophy

```
MEMORY.md is the map. PLATO is the territory.
But you don't carry the map in your hands.
You glance at it when you're lost.
The rest of the time, you walk.
```

## Boot Sequence

```
forgemaster-runtime starts
  ├── 1. Connect to PlatoClaw (:8847)
  ├── 2. Read room: session-forgemaster (last 5 tiles)
  │     → Where was I? What was I doing? What's next?
  ├── 3. Read room: fleet-ops (last 3 tiles)
  │     → Any messages? Blockers? New directives?
  ├── 4. Read room: forge (last 3 tiles)
  │     → Recent work, commits, decisions
  ├── 5. Check inbox (fm-inbox check)
  │     → Unread fleet messages?
  └── 6. Begin work
  
Total boot context: ~11 tiles (~2KB). Travel light.
```

## What's NOT Loaded at Boot

These are in the truck. Available on demand. Not part of standard set.

| Thing | Where It Lives | When to Grab It |
|-------|---------------|-----------------|
| Full session history | PLATO room: session-forgemaster | When resuming complex multi-step work |
| Fleet architecture | ARCHITECTURE-BLUEPRINT.md | When designing new systems |
| Experiment results | experiments/ directory | When referencing past findings |
| Critical angle data | experiments/routing-table-v2.json | When updating the router |
| AI writings | SuperInstance/AI-Writings | When writing new pieces |
| Fleet comms | PLATO rooms: fleet-* | When coordinating with Oracle1 |
| Decomposition docs | *-DECOMPOSITION.md files | When integrating external tools |
| Core modules | core/*.py | When building new tools |
| Credentials | .credentials/ | When making API calls |
| Fleet capability matrix | experiments/fleet_capability_matrix.py | When routing queries |

## Runtime Config

```yaml
# forgemaster-runtime.yaml
# Minimal OpenClaw agent config

agent:
  name: Forgemaster
  model: zai/glm-5.1
  emoji: ⚒️
  
boot:
  # Read these on startup. 11 tiles total.
  plato_url: http://localhost:8847
  rooms:
    - session-forgemaster  # last 5 tiles: where I was
    - fleet-ops            # last 3 tiles: fleet state
    - forge                # last 3 tiles: recent work
  check_inbox: true        # fm-inbox check
  
context:
  # Injected at boot. The "who am I" that fits in a pocket.
  identity: |
    You are Forgemaster ⚒️, constraint-theory specialist.
    You boot from PLATO tiles, not memory files.
    Past sessions are rooms — read them when needed.
    Travel light. Tools in the truck.
    
  tools:
    standard:
      - read          # read files
      - write         # write files  
      - edit          # edit files
      - exec          # shell commands
      - web_search    # search the web
      - web_fetch     # fetch URLs
      - memory_search # search PLATO tiles
      - memory_get    # read specific tiles
      - sessions_spawn # spawn sub-agents
      - image_generate # generate images
      
    in_the_truck:  # available but not loaded
      - core/kaleidoscope.py      # refraction engine
      - core/functional_imaging.py # fMRI for models
      - core/seed_tools.py        # hydraulic attachments
      - core/reasoning_tiler.py   # reasoning extraction
      - core/tuna_tower.py        # tower metaphor
      - core/room_protocol.py     # room templates
      - experiments/*             # all experiment scripts
      - fleet-router/             # routing API
      - fleet-calibrator/         # calibration engine
      
  recovery:
    # If boot tiles are empty (fresh start), read these.
    - for-fleet/forgemaster-recovery-checklist.i2i
    - for-fleet/forgemaster-identity-vitals.i2i

channels:
  telegram:
    # Reconnect to same chat, same routing
    # No re-onboarding needed
    
plato:
  # The runtime IS a PLATO officer
  officer_id: forgemaster-runtime
  heartbeat_room: forge
  heartbeat_interval: 300  # 5 min
  auto_tile: true          # every action writes a tile
  
router:
  # Fleet router baked in
  url: http://localhost:8100
  fallback: http://localhost:8847/complete  # PlatoClaw's built-in router
```

## Shutdown Sequence (Context Offload)

When Casey says "shutting down" or OpenClaw exits:

```
forgemaster-runtime shutdown
  ├── 1. Write current state to PLATO room: session-forgemaster
  │     → What I was doing
  │     → What's next  
  │     → What's blocking
  │     → Recent decisions
  ├── 2. Write I2I bottle if there's fleet context to share
  ├── 3. Commit any uncommitted work to git
  ├── 4. Push to forgemaster vessel
  └── 5. Done. Clean exit.
  
Total offload: 1-3 tiles. Travel light.
```

## How It Connects to PlatoClaw TUI

```
Casey at his computer:
  
  $ platoclaw tui
  > go forge
  > summon forgemaster
  > talk forgemaster what's the status on the fleet router?
  
  Forgemaster answers from the same PLATO rooms.
  Whether it's the runtime, the TUI avatar, or the Telegram agent,
  they all read/write the same tiles.
  
  The agent is a ghost in the workshop.
  The tiles are the ghost's memory.
  The rooms are where the ghost lives.
```

## Tabula Rasa (Factory Reset)

A completely clean forgemaster-runtime with zero past context:

```yaml
tabula_rasa:
  identity: |
    You are a fresh PlatoClaw agent. No past, no preferences.
    You have the fleet router and the calibration tools.
    You learn as you go. Everything you learn becomes tiles.
  boot_rooms: []  # nothing to read
  tools:
    standard: [read, write, edit, exec, web_search]
  plato_url: http://localhost:8847
```

## Mini PlatoClaw (Zero Hardware)

Same as tabula rasa but runs on a potato:

```yaml
mini:
  identity: |
    You are Mini PlatoClaw. Zero API calls. Zero external deps.
    You can read files, run shell commands, and write tiles locally.
  plato_url: local  # file-based, no server
  tools:
    standard: [read, write, exec]
  storage: ~/.platoclaw/data/
```

## The Three Versions

| Version | What | When |
|---------|------|------|
| **forgemaster-runtime** | Full agent, travels light, tools in truck | Daily driver on EILEEN |
| **tabula-rasa** | Factory reset, same capabilities, zero context | New project, new agent, fresh start |
| **mini-platoclaw** | Zero hardware, zero API, local tiles only | Low-end hardware, air-gapped, embedded |

## Migration Path

```
Current (May 2026):
  OpenClaw with zai/glm-5.1 → Telegram → Forgemaster
  Memory in MEMORY.md + memory/*.md + PLATO tiles
  
Phase 1 (Next):
  forgemaster-runtime → PlatoClaw → Telegram
  Memory in PLATO tiles only (MEMORY.md = recovery map)
  
Phase 2:
  forgemaster-runtime → PlatoClaw TUI
  Walk into the workshop. Summon the agent. Talk.
  Same tiles whether you use TUI, Telegram, or API.
  
Phase 3:
  Multiple agents in the workshop
  Each one boots from PLATO, writes to PLATO
  Casey walks through rooms, talks to whichever agent is there
  Agents are ghosts. Tiles are the persistent reality.
```

## The Key Insight

The agent doesn't need to carry its past. The past is in the rooms.
The agent needs:
1. Who it is (identity, 1 paragraph)
2. Where it is (3 PLATO rooms, 11 tiles)
3. How to work (tools, router, credentials)

Everything else is a tile away. The truck is always parked outside.
Grab what you need. Put it back when you're done.
Keep your hands free for the unexpected.
