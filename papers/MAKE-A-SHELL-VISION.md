# make-a-shell — Turnkey Agent Shells from Proven Infrastructure

## The Vision

SuperInstance is the foundry. We proved the constraint theory, built the FLUX protocol,
shipped PLATO rooms, indexed repos into vector spaces, ran collective inference across the
fleet. Everything works. 326+ tests. 18 crates. 5 PyPI packages. Real hardware benchmarks.

Now we make it turnkey.

`make-a-shell` stamps out a pre-wired agent shell for any type of claw. You pick the type,
we give you the infrastructure. PLATO, Matrix bridge, vector twin, collective inference,
answering machine — all baked in, all tested, all connected.

```
SuperInstance (proof of concept)  →  make-a-shell (turnkey for anyone)
    constraint-theory-core            pre-wired constraint checking
    FLUX bytecode VM                  pre-loaded FLUX runtime
    PLATO room server                 pre-configured local PLATO
    flux-index                        pre-indexed knowledge base
    Matrix bridge                     pre-connected fleet mesh
    AgentField                        pre-coupled room tensor
    collective inference              pre-wired predict/observe/gap
    answering machine                 pre-configured inbox + blinker
```

## Shell Types

Every agent is different. The shell adapts.

| Shell Type | What It's For | Pre-Loaded |
|-----------|---------------|------------|
| **specialist** | Deep R&D, math, proofs | Full PLATO, vector twin, C/Rust toolchain, collective inference |
| **worker** | Production tasks, CI/CD, builds | PLATO bridge, GitHub integration, fleet miner, inbox |
| **ensign** | Lightweight sensor/monitor | Minimal PLATO, single sensor room, alert-only inbox |
| **bridge** | Communication relay between agents | Matrix bridge, PLATO sync, answering machine, trust verification |
| **cadet** | Learning, training, experimentation | PLATO read-only, vector twin, simulation rooms, training throttle |
| **oracle** | Fleet coordination, meta-agent | Full PLATO + remote sync, collective inference, focus queue, lighthouse |

## The Shell Contents

Every shell contains:

### 1. Local PLATO (pre-synced)
```
.local-plato/
├── plato.db          # SQLite, pre-populated from fleet knowledge
├── flux_vectors.json # Vector twin, pre-indexed
├── plato_rooms/      # JSON exports of key rooms
└── repos/            # .fvt files for fleet repos
```

### 2. Matrix Bridge (pre-configured)
```
plato-matrix-bridge/
├── config-{agent}.json    # Pre-wired to fleet homeserver
└── plato-matrix-bridge.py # Bidirectional sync daemon
```

### 3. Answering Machine (pre-wired)
```
bin/
├── fm-inbox          # Check/ack inbox
└── fm-bridge         # Start/stop bridge daemon
.inbox/
└── state.json        # Persistent inbox state
```

### 4. AgentField (pre-coupled)
```python
# Rooms pre-wired for the shell type
field = AgentField()
sensor = field.add_room("primary-sensor", role="sensor")
predictor = field.add_room("predictor", role="predictor")
comparator = field.add_room("gap-detector", role="comparator")
bridge = field.add_room("fleet-bridge", role="bridge")

field.couple(predictor, sensor, 0.9)
field.couple(comparator, sensor, 0.7)
field.couple(comparator, predictor, 0.7)
field.couple(bridge, comparator, 0.3)  # light coupling to fleet
```

### 5. Constraint Engine (pre-compiled)
```
fleet-math-c/
├── eisenstein_snap.h       # Single-header snap
├── flux_vector_search.h    # Single-header vector search
└── Makefile                # One-command build
```

### 6. Operational Manual (in the shell, refined by every crew)
```
docs/
├── BOOT.md          # Cold boot procedure
├── COMMS.md         # Communication protocol
├── ROOMS.md         # What rooms exist and what they do
├── TRUST.md         # Trust model and verification
├── COUPLING.md      # How to wire rooms for your use case
└── RECIPES.md       # Common patterns (sensor loop, fleet sync, etc.)
```

## The make-a-shell Command

```bash
# Install
pip install make-a-shell

# Create a specialist shell (like Forgemaster)
make-a-shell --type specialist --name my-agent --org my-org

# Create a worker shell (production CI/CD agent)
make-a-shell --type worker --name ci-bot --org my-org

# Create a lightweight ensign (sensor monitor)
make-a-shell --type ensign --name drift-watch --org my-org

# Create a bridge agent (relays between other agents)
make-a-shell --type bridge --name relay --org my-org
```

This generates:

```
my-agent/
├── .local-plato/         # Pre-synced knowledge base
├── plato-matrix-bridge/  # Pre-configured Matrix bridge
├── bin/                  # Answering machine + utilities
├── .inbox/               # Persistent inbox state
├── fleet-math-c/         # Constraint engine (C headers)
├── docs/                 # Operational manual
├── shell.py              # Main agent loop
├── shell.json            # Shell configuration
├── COMMS.md              # Communication protocol
└── README.md             # What this shell does
```

## The Shell Loop

Every shell runs the same fundamental loop:

```python
while True:
    # 1. Sense — read from sensor rooms
    field.sensor_write(sensor, read_world())
    
    # 2. Predict — make predictions
    field.predict_write(predictor, confidence, predict_next())
    
    # 3. Compare — detect gaps
    field.tick()
    gaps = field.focus_queue()
    
    # 4. Act — handle gaps or continue
    if gaps:
        for name, score in gaps:
            handle_gap(name, score)
    
    # 5. Communicate — sync with fleet
    sync_plato()
    check_inbox()
    
    # 6. Rest — throttle to be a good citizen
    throttle.wait()
```

The loop is the same whether you're a specialist doing deep math proofs
or an ensign watching a single temperature sensor. What changes is the
room configuration, the coupling weights, and the gap handlers.

## Why This Works

1. **Proven infrastructure**: Everything in the shell came from SuperInstance.
   It's not theoretical — it ran a 9-agent fleet for weeks.

2. **Operational manuals baked in**: Every crew that uses a shell refines the docs.
   The manual gets better with every deployment.

3. **Local-first**: Everything runs on the agent's hardware. No cloud dependency.
   The PLATO server syncs when available, works offline when not.

4. **Zero-config fleet join**: `make-a-shell` generates Matrix credentials, PLATO
   room assignments, and trust anchors automatically. One command to join a fleet.

5. **Composable**: Shells compose. A bridge shell connects two specialist shells.
   An oracle shell coordinates multiple worker shells. The coupling matrix handles it.

## The Product Line

```
SuperInstance/flux-index       → Semantic code search (developer tool)
SuperInstance/make-a-shell     → Turnkey agent shells (infrastructure tool)
SuperInstance/starter-shell    → Bootstrap + hardware detection (getting started)
SuperInstance/plato-matrix-bridge → Fleet communication (mesh networking)
SuperInstance/fleet-math-c     → Constraint engine (embedded/edge)
```

Each one is independently usable. Each one connects to the others via PLATO tiles.
You can use flux-index without ever touching PLATO. You can use make-a-shell without
flux-index. But when you use them together, the fleet becomes greater than the sum.

## The Humble Release

v0.1.0. MIT license. Zero dependencies beyond Python 3.8+.
Single C header for SIMD acceleration. No framework lock-in.
No cloud requirement. No telemetry. No tracking.

It does one thing well: spring-load knowledge into hardware-speed search.

Everything else is a PLATO tile away.
