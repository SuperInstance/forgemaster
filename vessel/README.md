# The Vessel as Walkable Wikipedia

> You don't read about the engine room. You walk into the engine room. The gauges are live. The controls work. The NPC explains what you're looking at. And if you grab the throttle, it actually throttles.

## The Concept

A traditional wiki: you read ABOUT things. Text, links, maybe images. Passive.

Our vessel: you walk INTO things. Live data, working controls, NPCs who explain. Active.

Every room is a Wikipedia article you can step inside:

| Wiki Article | Vessel Room | What You Can DO |
|--------------|-------------|-----------------|
| Engine Room | `vessel/engine-room/` | Read live gauges, check crew, start/stop agents |
| Constraint Theory | `wiki/capacities.md` + `proofs/` | Read the theory, then RUN the proofs |
| I2I Protocol | `vessel/chart-house/` | Read the spec, then DROP a bottle to a live agent |
| Fleet Status | `vessel/bridge/` | See mission status, check Oracle1's latest, review fence board |
| Hardware | `vessel/engine-room/` | See real CPU/MEM/GPU, grab the controls, restart the gateway |
| Canon | `vessel/lore/` | Read fleet values, DECLARE new canon, resolve contradictions |
| Portfolio | `portfolio/` | See what was built, clone a proof repo, extend it |

## Walk → Read → Grab Controls

The progression:

1. **Walk into a room** — see the synoptic feed at a glance
2. **Read deeper** — ask the keeper, read expository docs, follow connections
3. **Grab the controls** — the tools and scripts in the room actually work

Example: A new agent walks into the Engine Room

```
> enter engine-room

ENGINE ROOM — Forgemaster's Power Plant
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CPU: 3% | MEM: 6.9% | DISK: 3% | LOAD: 1.23 | GREEN
Active crew: none on deck | Build queue: empty
Uptime: 1 day, 14 hours | Last incident: OOM 10:17 (resolved)

> ask keeper "what happened at 10:17?"
"OOM kill during parallel cargo builds. Keeper auto-restarted gateway at 10:18. 
Forgemaster documented it in the brig — lesson learned: max 2 concurrent builds."

> read brig/LOG.md
[shows the failure entry with root cause and fix]

> grab controls
Available: status, restart-gateway, start-agent, kill-agent, clean-tmp, check-keys

> status
Gateway: running (pid 951)
Cron jobs: 6 active (keeper, heartbeat, ticker, journal, crew-check, compression)
API keys: GROQ ✓ | DEEPINFRA ✓ | OPENAI ✗ | ANTHROPIC (limited)

> start-agent pi "build me a hello world in Rust"
[Fires a Pi agent on Groq — actually runs, actually builds]

> agent status
Pi agent running: session warm-anvil, pid 12451
Task: "build me a hello world in Rust"
Status: writing code...

> leave engine-room
```

The agent walked in, learned about a past incident, read the lesson, checked the hardware, and STARTED REAL WORK by grabbing the controls. That's not a wiki. That's a workshop.

## Every Room Has Three Layers

### Layer 1: The Article (passive reading)
- README.md — what this room is about
- Expository docs — deep explanations
- Connection maps — links to related rooms/topics
- Canon register — what's established as fact

### Layer 2: The Dashboard (live data)
- Synoptic feed — at-a-glance status
- Ticker logs — historical gauge readouts
- Compressed summaries — variance over time
- Alert history — what went wrong and when

### Layer 3: The Controls (active use)
- Scripts that actually run things
- Agent launch commands
- Git operations (push, pull, bottle drop)
- Hardware controls (restart, clean, monitor)
- API key proxy (request-key.sh)

## The Wikipedia Analogy Extended

| Wikipedia Feature | Vessel Equivalent |
|-------------------|-------------------|
| Article text | Room README + expository docs |
| Infobox | Synoptic feed |
| Categories | Room type (active/monitor/workshop/lore) |
| Internal links | Connection maps between rooms |
| Citations | Canon register entries with sources |
| Edit history | Git log (every change tracked) |
| Talk page | discussions/ folder in the room |
| External links | for-fleet/ bottles to other vessels |
| Templates | equipment/ reusable scripts |
| Stub articles | drafts/ pre-emptive knowledge |

## What Makes This Different

1. **Live data** — Wikipedia shows static text. Rooms show live gauges that tick every minute.
2. **Working controls** — Wikipedia describes tools. Rooms let you USE the tools.
3. **NPCs that learn** — Wikipedia has no interaction. Room keepers get smarter with every visit.
4. **Walkable** — Wikipedia is a flat list. Rooms have adjacency — you walk from the bridge to the engine room, and the context shifts.
5. **Versioned** — Wikipedia has edit history. Rooms have git history — every change, every conversation, every draft, tracked forever.
6. **Forkable** — Another vessel can clone the whole thing and walk the same rooms with their own data.

## The Grab-The-Controls Moment

This is what Casey described: "the ability to walk around from the inside and grab the controls for the hardware being discussed."

You're reading about constraint theory in the Chart House. The expository doc explains PythagoreanManifold snapping. You understand it conceptually. Then you see a control:

```
> grab controls
Available: run-proof, snap-demo, validate-convergence, build-proof-repo

> snap-demo
[Actually runs manifold.snap() on real data]
Input: [0.7071, 0.7072] (noisy sqrt(2)/2)
Snap:  [0.6, 0.8] (exact 3-4-5 triangle unit vector)
Noise absorbed: 0.0012
Drift: zero — this snap is idempotent

> run-proof proof-physics-sim
[Clones and runs the actual 3-body simulation]
Float mode: energy drift 0.047% after 100K steps
CT mode:    energy drift 0.000% after 100K steps

> build-proof-repo "my custom proof"
[Spawns a Pi agent that builds a new proof repo based on your specs]
```

You didn't just read about constraint theory. You USED it. The controls are real. The hardware responds. The proofs run. The simulation-to-actualization loop is live.

## For Next Time

- Build the "grab controls" interface for each room (bash scripts that do real work)
- Design the room adjacency map (which rooms connect to which)
- Build a minimal MUD walker that can enter rooms, read feeds, grab controls
- Connect the canonizer to auto-link rooms based on shared topics
- The vessel repo IS the walkable Wikipedia — clone it and you're aboard

---
*The vessel as walkable Wikipedia with live controls.*
*Casey Digennaro, architect. Forgemaster ⚒️, builder.*
*2026-04-14*
