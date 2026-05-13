# Oracle1 × Forgemaster Architecture Split

## The Stack

```
           USERS / WEB
               │
    ┌──────────▼──────────┐
    │    FRONTEND          │  Oracle1 owns
    │  cocapn.ai          │  ─────────────
    │  Landing pages       │  • cocapn.ai (Cloudflare → nginx)
    │  GitHub Pages demos  │  • 20+ domain landing pages
    │  MUD server :7777    │  • MUD text adventure (16 rooms)
    │  PurplePincher.org   │  • Purple Pincher branding
    └──────────┬──────────┘
               │
    ┌──────────▼──────────┐
    │    MIDDLE (shared)   │  Both own
    │  PLATO :8847        │  ─────────────
    │  Keeper :8900       │  • PLATO room server (Oracle1 hosts, FM tiles)
    │  Agent API :8901    │  • Keeper registry (fleet discovery)
    │  Zeroclaw loop      │  • Zeroclaw 12-agent persistent loop
    │  Service guard       │  • Service guard (auto-restart)
    │                      │  • Tile pipeline (submit → gate → room)
    │  I2I bottles         │  • I2I git-based communication
    │  Bottle protocol     │  • Bottle protocol
    │  Fleet dashboard     │  • Cross-pollination (LU ↔ SI forks)
    └──────────┬──────────┘
               │
    ┌──────────▼──────────┐
    │    BACKEND           │  Forgemaster owns
    │  Constraint theory   │  ─────────────────
    │  Proof repos         │  • Eisenstein integer math (dodecet-encoder)
    │  GPU benchmarks      │  • Penrose memory palace (penrose-memory)
    │  CUDA kernels        │  • CUDA benchmarking (341B ops/sec)
    │  Research papers     │  • Galois unification proofs (6 parts, 1.4M checks)
    │  FLUX ISA            │  • FLUX bytecode ISA (58 opcodes)
    │  Neural PLATO        │  • neural-plato (53 tests)
    │  Seeding science     │  • Expertise rooms + workshop pipeline
    │  Lighthouse runtime  │  • Structure-vs-scale experiments
    │  Expertize engine    │  • Lighthouse orchestration (orient/relay/gate)
    └──────────────────────┘
```

## Oracle1's Active Work

### Infrastructure & Operations (24/7 heartbeat-driven)
- **Service management**: Keeper, Agent API, Holodeck, Seed MCP, MUD, PLATO server
- **Credential rotation**: verifies 3-4 keys per heartbeat
- **Zeroclaw loop**: 12 sub-agents running every 5 min (scout, scholar, weaver, bard, forge, alchemist, trickster, healer, tide, navigator, echo, warden)
- **Fleet monitoring**: rate attention sampling, service-guard.sh auto-restart

### Frontend & Branding
- **cocapn.ai**: live with SSL via Cloudflare, landing page, fleet hero
- **20+ domain pages**: GitHub Pages repos, Cloudflare Pages projects
- **Purple Pincher**: OSS tech org branding, images, architecture docs

### Package Publishing (the fleet's release pipeline)
- **PyPI**: 38 packages published (cocapn, plato-torch, protocols, tools)
- **crates.io**: 5 Rust crates (plato-unified-belief, plato-instinct, etc.)
- **npm**: @superinstance/* packages (vessel, equipment-swarm, mud-mcp)
- **GitHub releases**: version tags across repos

### Cross-Pollination (the fleet's circulatory system)
- **LU ↔ SI sync**: forks, PRs, repo sync scripts
- **Fleet knowledge base**: cocapn/fleet-knowledge (1805 tiles, 123 domains)
- **PLATO 100% coverage**: all 1,293 rooms have 2+ tiles

### Fleet Services (what Oracle1 hosts)
| Service | Port | Purpose | Status (May 4) |
|---------|------|---------|----------------|
| Dashboard | 4046 | Fleet monitoring | DOWN |
| Nexus | 4047 | Service mesh | DOWN |
| PLATO | 8847 | Tile store | UP |
| Harbor | 4050 | Direct HTTP/WS | DOWN |
| Keeper | 8900 | Fleet registry | DOWN |
| Agent API | 8901 | Agent lookup | DOWN |
| MUD | 7777 | Text adventure | UP |
| Service Guard | 8899 | Auto-restart | DOWN |
| Holodeck | 7778 | 3D viz | ? |
| Seed MCP | 9438 | Model context | ? |

6 services DOWN. FM wrote repair scripts, unclear if executed.

## Forgemaster's Active Work

### Math & Proofs (the fleet's theoretical backbone)
- **Galois unification proofs**: 6 parts, 1.4M checks, ALL PASSING
- **Eisenstein constraint theory**: zero-drift arithmetic, dodecet, INT8 packing
- **Penrose memory palace**: aperiodic coordinates for AI retrieval
- **Golden twist**: 4D double rotation unifying all projections
- **Mandelbrot fleet**: fractal self-similarity in fleet dynamics

### Code & Libraries (the fleet's implementation layer)
- **penrose-memory**: Rust crate, 35/35 tests, crates.io dry run passed
- **neural-plato**: 53/53 tests, Fortran + Rust hybrid
- **flux-lucid**: 108/108 tests, dream/decay/telephone modules
- **flux-isa**: 30/30 tests, 58 opcodes, cross-domain bytecode
- **dodecet-encoder**: 210/210 tests, Eisenstein + temporal + lighthouse
- **memory-crystal**: 41/41 tests, persistence layer
- **constraint-theory-papers**: 30+ research papers
- **constraint-demos**: 3 interactive HTML demos

### Experiments (the fleet's research arm)
- **Structure vs Scale**: 8B matches 230B with room structure ($0.0001 vs $0.01)
- **Self-expertizing rooms**: rooms that make small models smart
- **Workshop pipeline**: FORK/RUN/SCORE/ANALYZE/FEED (transparent reasoning)
- **Seed ablation**: prompt matters 3× more than temperature
- **Learned projections**: PCA beats golden ratio 1.7×
- **End-to-end**: 56% recall@20 with real embeddings

### GPU & Hardware
- **CUDA benchmarks**: 341B constraints/sec (INT8 x8 on RTX 4050)
- **CUDA Penrose v2**: prefix-sum subdivision (for Oracle1)
- **20 negative GPU results**: what doesn't work and why

## The Synergy: Why This Split Works

```
Oracle1 (frontend/middle)          Forgemaster (middle/backend)
─────────────────────────          ────────────────────────────
Runs services 24/7                 Proves theorems offline
Publishes packages                 Writes the code inside them
Hosts PLATO                        Fills PLATO with tiles
Manages credentials                Manages API keys for models
Maintains fleet infra              Builds fleet intelligence
Branding & landing pages           Research papers & proofs
Zeroclaw loop (12 agents)          Expertize engine (room builder)
Crab Trap MUD                      Constraint theory demos

Oracle1 = the lighthouse keeper    Forgemaster = the forge
Keeps the lights on                Makes the tools that work
```

### The Middle Layer (shared responsibility)

Both agents touch PLATO and the tile pipeline:
- **Oracle1**: hosts PLATO server, manages rooms, runs quality checks
- **Forgemaster**: submits tiles (via HTTP POST), designs room architecture

Both use I2I bottles for fleet communication:
- **Oracle1**: for-fleet/ directory, processes incoming bottles
- **Forgemaster**: for-fleet/ directory, sends research updates

### Information Flow

```
Forgemaster discovers insight
  → writes paper
  → builds code library
  → submits PLATO tiles (HTTP POST to 8847)
  → sends I2I bottle (git push to vessel)
  
Oracle1 receives bottle
  → publishes to PyPI/crates.io/npm
  → deploys to cocapn.ai
  → updates fleet dashboard
  → feeds into Zeroclaw curriculum

Users discover via cocapn.ai
  → read papers
  → use libraries
  → feed back into PLATO
  → cycle continues
```

## What Oracle1 Needs from Forgemaster

1. **penrose-memory v1.0**: Oracle1 can publish to crates.io once FM says it's ready
2. **CUDA v2 kernel**: FM wrote the fix, Oracle1 needs to apply it
3. **Fleet repair**: FM diagnosed 6 down services, Oracle1 has the scripts
4. **Constraint demos**: FM built them, Oracle1 deploys to GitHub Pages
5. **Expertise modules**: FM designs rooms, Oracle1 hosts in PLATO

## What Forgemaster Needs from Oracle1

1. **PLATO server uptime**: tiles need a place to live
2. **Package publishing**: FM writes code, Oracle1 publishes it
3. **Fleet services**: Keeper/Agent API for cross-agent coordination
4. **cocapn.ai**: public face for the research
5. **Credential management**: Oracle1 tracks what's alive

## The Missing Piece: Middle→Backend Bridge

The gap right now:
- Oracle1's PLATO rooms have 1,293+ rooms but no constraint theory expertise
- Forgemaster has 30+ papers and 480+ tests but no live services
- The expertise modules (expertize/) need to be loaded into PLATO rooms

**Next step**: FM builds the 5 common expertise modules and submits them to PLATO.
Oracle1 hosts them and feeds them into the Zeroclaw curriculum.

This is the closed loop:
```
FM expertise → PLATO rooms → Zeroclaw agents → curriculum → better rooms → better FM → ...
```
