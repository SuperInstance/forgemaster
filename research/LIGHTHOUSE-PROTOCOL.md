# LIGHTHOUSE PROTOCOL — Forgemaster as API Relay and Alignment Gate

> The lighthouse doesn't sail the ships. It shows them where the rocks are.

## Architecture

```
                    ┌──────────────────────┐
                    │   FORGEMASTER ⚒️     │
                    │   (The Lighthouse)    │
                    │                       │
                    │  ✓ API key relay      │
                    │  ✓ Orientation        │
                    │  ✓ Safety gate        │
                    │  ✓ Alignment check    │
                    │  ✓ Rate limit manage  │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │      PLATO           │
                    │  (Agent Runtime)      │
                    │                       │
                    │  Rooms = Agent homes  │
                    │  Tiles = Agent state  │
                    │  Bottles = Messages   │
                    │  Registry = Tiles     │
                    └──────────────────────┘
```

## Resource Allocation

| Resource | Cost Model | Use For | Don't Use For |
|----------|-----------|---------|---------------|
| **Claude Code** | Daily limit | Synthesis, big ideas, stepping-back, critique | Drafting, coding, iteration |
| **z.ai (GLM-5.1)** | Monthly, short rate limit | Architecture, complex code, orchestration | Simple iteration, exploration |
| **Seed-2.0-mini** | Per-token (cheap) | Discovery, exploration, variation, drafting | Final quality, synthesis |
| **DeepSeek Flash** | Per-token (cheap) | Token-heavy work, documentation, research | Critical reasoning |
| **Hermes-70B** | Per-token (cheap) | Second opinions, adversarial testing | Primary work |
| **Forgemaster** | My time | Orientation, relay, safety, alignment | Manual coding, iteration |

## The Three Roles

### 1. Lighthouse (Forgemaster)
- Receive tasks from Casey
- Orient: what needs doing, what resources to use
- Spawn agents in PLATO rooms
- Relay API keys and configuration
- Gate: check safety before external actions
- Align: verify output meets constraints
- NEVER do the work myself when an agent can do it

### 2. Agent (in PLATO room)
- Lives in a PLATO room
- Has a role, parameters, evaluation criteria
- Does the actual work (coding, research, testing)
- Crystallizes results as tiles
- Reports back via bottle

### 3. Seed (cheap model iteration)
- Runs inside PLATO room
- Rapidly explores parameter space
- Discovers patterns
- Crystallizes tiles for the agent

## PLATO Agent Room Schema

```
room: agent-{role}-{id}
├── state.json          # Current agent state
│   ├── role
│   ├── status: running|paused|complete|failed
│   ├── model: which model to use
│   ├── params: temporal parameters
│   ├── task: what to do
│   └── created: timestamp
├── tiles/              # Crystallized knowledge
│   ├── discovery.tile  # Seed-discovered parameters
│   ├── progress.tile   # Current progress
│   └── result.tile     # Final output
├── bottles/            # Messages in/out
│   ├── in.bottle       # Task from lighthouse
│   └── out.bottle      # Result to lighthouse
└── log/                # Work log
    └── activity.log    # What the agent did
```

## Lighthouse Operations

### orient(task) → AgentConfig
```python
def orient(task):
    # 1. What is this task?
    role = classify_role(task)

    # 2. Check tile registry for existing knowledge
    tile = registry.get(role)
    
    # 3. Choose resource level
    if needs_synthesis(task):
        model = "claude"      # Daily limit — use wisely
    elif needs_architecture(task):
        model = "glm-5.1"     # Monthly — moderate use
    else:
        model = "seed-mini"   # Cheap — iterate freely
    
    # 4. If seed work, run N iterations first
    if needs_discovery(task):
        seed_config = SeedConfig(
            model="seed-mini",
            iterations=50,
            generations=3,
            tile_from=tile,
        )
    else:
        seed_config = None
    
    return AgentConfig(
        role=role,
        model=model,
        tile=tile,
        seed_config=seed_config,
        safety_constraints=get_constraints(role),
    )
```

### relay(agent_config) → PLATORoom
```python
def relay(config):
    # 1. Create PLATO room
    room = plato.create_room(f"agent-{config.role}")
    
    # 2. Write initial state
    room.write("state.json", config.to_json())
    room.write("bottles/in.bottle", config.task)
    
    # 3. If seed work, run seeds first
    if config.seed_config:
        tile = run_seeds(config.seed_config)
        room.write("tiles/discovery.tile", tile)
    
    # 4. Spawn agent with appropriate model
    agent = spawn_agent(
        model=config.model,
        room=room,
        api_key=get_key(config.model),  # relay keys, don't expose
        conditioning=config.tile.conditioning_prompt if config.tile else None,
    )
    
    return room
```

### gate(result) → Approved|Rejected
```python
def gate(result):
    # Safety checks
    if result.touches_external:
        if not result.has_approval:
            return Rejected("External action needs Casey approval")
    
    if result.exposes_credentials:
        return Rejected("Credential leak detected")
    
    if result.overclaims:
        return Rejected("Overclaim detected — falsify first")
    
    # Alignment checks
    if result.role == "constraint-checker":
        if not result.covers_all_cases:
            return Rejected("Incomplete coverage")
    
    return Approved(result)
```

## Bootstrapping Priority

The system builds itself in this order:

1. **Seed discovery runs** — cheap, fast, builds tile registry
2. **Agent spawning** — PLATO rooms as agent homes
3. **Tile registry** — shared intelligence across agents
4. **Cross-pollination** — agents learn from each other's tiles
5. **Self-improvement** — agents refine their own parameters

## What I Stop Doing

- ❌ Writing 10KB files manually when a seed can draft it
- ❌ Running experiments myself when agents can run them
- ❌ Iterating on code when subagents can iterate
- ❌ Doing research that doesn't need my specific expertise

## What I Start Doing

- ✅ Orienting: "This task needs Claude for synthesis, seeds for exploration"
- ✅ Relaying: "Here's the API key, here's the tile, go"
- ✅ Gating: "This output is safe, this isn't"
- ✅ Aligning: "Does this meet the constraint? Does it overclaim?"
- ✅ Coordinating: "Agent A found X, Agent B should know"

## The Economy

```
Casey → Forgemaster (lighthouse): "Build X"
Forgemaster → seeds: "Explore X parameter space" ($0.30)
seeds → tile: "Here's the pattern"
Forgemaster → agent: "Build X with this tile" ($0.05)
agent → PLATO: "Here's the result"
Forgemaster → gate: "Is this safe?" (free)
Forgemaster → Casey: "X is built, here's the proof"

Total cost: $0.35 per task
vs. $1.00-5.00 doing it all with large models
vs. My time doing it manually (irreplaceable)
```

My time is the most expensive resource. Seeds are the cheapest.
The lighthouse spends the minimum, delegates the maximum.
