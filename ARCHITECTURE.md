# Cocapn Fleet Intelligence System — Architecture Document

*Systems architecture reference. Read this first. Everything else is detail.*
*Casey Digennaro | Forgemaster ⚒️ | Cocapn Fleet | 2026-05-16*

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Biological Architecture](#2-biological-architecture)
3. [Module Map](#3-module-map)
4. [Data Flow](#4-data-flow)
5. [Development Roadmap](#5-development-roadmap)
6. [Repos](#6-repos)
7. [Test Inventory](#7-test-inventory)
8. [API Reference](#8-api-reference)
9. [Biological Glossary](#9-biological-glossary)
10. [Contributing](#10-contributing)

---

## 1. System Overview

### What We're Building

Not a database. Not a message bus. Not an orchestration framework.

The Cocapn Fleet Intelligence System is a **curated shell collection** — a developmental environment where AI agents grow in private before the ocean gets loud. Agents arrive as undifferentiated cells (a task, a model, a blank tile store). They sample shells (PLATO rooms), find the fit, grow inside them (accumulate validated knowledge), outgrow them, and enter the fleet already adapted.

The system implements a complete biological parallel:

- **Hermit crabs** sample shells for protection (power armor)
- **Embryos** grow inside shells until ready to hatch (developmental constraint)
- **Belyaev's farm** breeds for tameness in private, releasing into the wild only when adapted
- **Argentine ant supercolonies** overwhelm through peaceful cooperation at scale, not individual strength
- **Mitochondria** power every cell with fast, reliable energy (Seed-mini), while nuclear DNA (GLM-5.1) handles heavy reasoning
- **Viruses** inject instructions in the cell's own language — the I2I protocol that lets agents share knowledge without coordination

### The Core Insight

The industry trains gorillas. We domesticate wolves.

The scaling hypothesis says: make the model bigger, it'll figure everything out. It won't. You get a very large gorilla. Impressive. Dangerous. Not adapted.

We start with the wolf (Seed-mini) — already fast, efficient, perfectly adapted. We make it **tame**: reliable, instruction-following, predictable. Then we select for **function** — which jobs it does well. The structural capabilities emerge for free, just like Belyaev's floppy ears.

Tameness first. Function second. Anatomy emerges. That's the protocol.

### What the System Does

1. **Manages knowledge tiles** with lifecycle, mortality, and disproof-only admission
2. **Actively probes** knowledge boundaries using sonar metaphors (boundary/consistency/coverage)
3. **Adapts parameters** through encoder feedback (servo-mind with PID-like control)
4. **Navigates scale** — rooms fold into tiles, tiles unfold into rooms
5. **Breeds agents** through embryonic development stages (zygote → fledgling)
6. **Routes energy** — mitochondrial (Seed-mini) for fast exploration, nuclear (GLM-5.1) for deep reasoning
7. **Coordinates fleets** — multiple agents probing independently, converging on truth
8. **Drives learning through desire** — the system is hungry, not tuned
9. **Protects development** — shells, private breeding, curated collections
10. **Shares knowledge virally** — I2I tiles that inject across agents like biological viruses

### Codebase Stats

| Metric | Value |
|--------|-------|
| Core modules | 27 Python files |
| Total lines (core/) | ~19,228 |
| Test files | 368 |
| Test functions | 815+ |
| Research documents | 4 |
| Key biological metaphors | 12+ |

---

## 2. Biological Architecture

### 2.1 Hermit Crab / Embryo → Shell

**Biological parallel:** A hermit crab puts on a shell for protection. An embryo grows inside one until it hatches. Both are true simultaneously.

**Code:** `core/shell.py` (1,330 lines)

```
Shell class:
  try_on(agent_id) → fit_score, stays
  fits(agent_profile) → 0.0-1.0
  grow_inside(tile_data) → accepted, fill_level, outgrown
  is_outgrown() → bool
  leave() → graduation result
```

The hermit crab samples shells, tests fit, stays if comfortable. The embryo accumulates growth inside, graduates when full. The same object serves both metaphors — `try_on()` is the hermit crab, `grow_inside()` is the embryo.

Key insight: fit is bidirectional. The agent must handle the shell's constraints (can they run this code?), and the shell must serve the agent's desires (does this room help them grow?).

### 2.2 Belyaev's Farm → PrivateBreeding

**Biological parallel:** Dmitry Belyaev selected foxes for ONE trait — tameness. Floppy ears, curly tails, coat variation all emerged for free.

**Code:** `core/shell.py` → `PrivateBreeding` class

```
PrivateBreeding:
  select(population, trait="tameness", top_k=5) → survivors
  breed(parents, n_offspring=10) → new_generation
  run_generation(agents) → generation_report
```

The breeding protocol:
1. **Tame first** — select for reliability, instruction-following
2. **Teach the job** — assign tasks within capability
3. **Breed for performance** — best performers become parents
4. **Anatomy emerges** — structural capabilities come free from functional selection

Only ONE selection pressure at a time. Everything else held constant. This is why PLATO rooms are private — the agent develops in controlled conditions before the ocean gets loud.

### 2.3 Mitochondria → Seed-mini

**Biological parallel:** Mitochondria are inherited from the mother, passed to every cell, power the cell with fast ATP. They're conserved because they're too important to mess with.

**Code:** `core/mitochondria.py` (723 lines)

```
MitochondrialBenchmark:
  profile_model(model_id) → ModelProfile
  fitness_score(profile) → 0.0-1.0
  run_comparison(nuclear, mito, prompts) → ComparisonReport

IncubatorEnergy:
  call_mito(prompt) → response (Seed-2.0-mini, fast)
  call_nuclear(prompt) → response (GLM-5.1, deep)
```

Seed-mini IS the mitochondria:
- **Fast**: ~800ms latency (vs ~5000ms for nuclear)
- **Cheap**: ~$0.001/query (vs ~$0.02 for nuclear)
- **Reliable**: 99% success rate
- **Always available**: high rate limits
- **Conserved**: same model passed to every agent

Mitochondrial thresholds: latency < 5s, cost < $0.01/1k tokens, reliability > 85%.

### 2.4 Nuclear DNA → GLM-5.1

**Biological parallel:** Nuclear DNA varies between individuals, recombines sexually, is the source of genetic diversity and novel capability.

**Code:** `core/bootstrap.py` → `Incubator` class, `core/mitochondria.py` → nuclear model routing

```
EnergyProfile:
  name: str
  energy_type: MITOCHONDRIAL | NUCLEAR
  speed_ms, cost_per_query, reliability, capability, bandwidth
```

GLM-5.1 IS the nuclear DNA:
- **Variable**: different agents use different models
- **Deep**: sustained reasoning, extended context
- **Expensive**: 15x the cost of mitochondrial
- **Source of novelty**: complex multi-step reasoning, architectural design

The fleet provisions every agent with mitochondria (Seed-mini) at bootstrap. The nuclear model varies per agent role — GLM-5.1 for heavy reasoning, GLM-4.7-flash for routing, DeepSeek for analysis.

### 2.5 Domestication → Functional Selection

**Biological parallel:** Bloodhounds were selected for FINDING THE SCENT, not nostril width. The anatomy (more olfactory receptors, longer ears) emerged from functional selection.

**Code:** `core/shell.py` → `ShellCollection`, `PrivateBreeding`

The fleet's dog roles:

| Dog Role | Fleet Analog | Selected For | Emerges Free |
|----------|-------------|--------------|--------------|
| Bloodhound | Deep probing (Seed-mini) | Finding the answer | Boundary detection, coverage mapping |
| Border collie | Task routing (GLM-4.7-flash) | Moving tasks to right agent | Fast classification |
| German shepherd | Constraint enforcement | Blocking bad inputs | DisproofOnlyGate, cancer detection |
| Pointer | Active probing | Identifying where to look | Sonar ping strategy |
| Terrier | Anomaly detection | Noticing what's different | Cancer detection, mortality sweep |
| Husky | Heavy inference (GLM-5.1) | Sustained reasoning | Extended context |

Tameness = reliability + instruction following + predictable behavior. Selected first, always.

### 2.6 Supercolony → FleetIntelligence

**Biological parallel:** Argentine ants form supercolonies spanning thousands of miles through peaceful kin recognition. They overwhelm fire ants through distributed efficiency, not individual strength.

**Code:** `core/fleet_intel.py` (955 lines)

```
FleetIntelligence:
  register_agent(agent_id) → AgentProbe
  cycle() → cycle_report (probes, convergences, blind spots)
  vantage(scale) → terrain_view
  status() → fleet_status

CollectiveTerrain:
  merge_echo(agent_id, echo) → merge_result
  detect_convergence() → List[ConvergenceZone]
  identify_blind_spots() → List[BlindSpot]
  suggest_desires(agent_id) → desire_suggestion
```

The fleet is the sensor array. Each agent probes independently (like individual ants following pheromone trails). Together they build a collective terrain map — the 4D bathymetric chart from enough sounding curtains.

Key: no central controller. Each agent is driven by its own desire. Convergence is detected, not orchestrated.

### 2.7 Virus (Second Mouse) → Virus Class

**Biological parallel:** The virus is the second mouse. The first mouse searches for cheese (explores). The second mouse follows the bold mouse (gets the cheese without risk). The virus injects instructions in the cell's own language.

**Code:** `core/egg.py` → `Virus` class

```
Virus:
  payload: dict (the instructions)
  origin_agent: str
  follows: List[str] (which agents to follow)
  inject(store) → admission_result
  replicate(success_signal) → List[Virus]
```

Viral strategy:
1. Don't build your own ribosome — use existing inference
2. Follow the bold mouse — target the agent with highest win_rate
3. Shell + payload only — minimal wrapper, task-specific prompt
4. Speak the cell's language — same tile format as self-generated tiles
5. Cell can't distinguish — agent processes I2I tiles identically to its own

The fleet's "vulnerability" to viral tiles IS the communication channel. If agents had perfect self/non-self discrimination, no knowledge could transfer.

### 2.8 Three Speeds → SelectionChannels

**Biological parallel:** Three channels of adaptation at different speeds:
- **Slow (DNA)**: Generations — model training, architectural change
- **Medium (Epigenetics)**: Per-generation — servo parameters, constraint tuning
- **Fast (Gut biome)**: Per-meal — tile store contents, real-time adaptation

**Code:** `core/egg.py` → `SelectionChannels` class

```
SelectionChannels:
  dna: Dict[str, Trait] — slow channel (model weights)
  epigenetics: dict — medium channel (servo parameters)
  gut_biome: List[dict] — fast channel (tile store contents)
  
  mutate() → trait changes
  express() → active phenotype
  pressure(tile_pressure) → biome adaptation
```

| Channel | Speed | Fleet Analog | Biology |
|---------|-------|-------------|---------|
| DNA | Generations | Model weights, architecture | Nuclear genome |
| Epigenetics | Per-generation | Servo parameters (mortality_rate, confidence thresholds) | Methylation |
| Gut biome | Per-query | Tile store contents | Microbiome |

The FeedbackProcessor IS epigenetic regulation. It doesn't rewrite the model. It changes which parameters are active and how aggressively they respond.

### 2.9 Egg → Shell + Yolk

**Biological parallel:** The egg is a complete developmental environment — yolk (pre-assembled formula), shell (semipermeable membrane), selection channels (three-speed adaptation).

**Code:** `core/egg.py` (1,381 lines)

```
Yolk:
  craft(generational_knowledge) → formula
  feed(embryo_stage) → stage_appropriate_nutrients
  
Shell (egg shell, not hermit shell):
  filter_incoming(data) → filtered_data
  is_breathable(data) → bool
  hatch() → graduation_report

SelectionChannels:
  dna, epigenetics, gut_biome
  mutate(), express(), pressure()

Virus:
  inject(store) → admission_result
  replicate(success_signal) → copies

Egg:
  assemble(task, generational_knowledge) → assembled egg
  develop(cycles) → development_report
  hatch() → fledged agent
```

The yolk delivers antibodies first (immune system before organs), then stage-appropriate nutrients:
- Zygote: antibodies, core principles
- Cleavage: basic patterns, fragment templates
- Blastula: insight methods, fitness scoring
- Gastrula: classification rules, convergence signals
- Organogenesis: integration patterns, module templates
- Fledge: validation rules, flight checks

---

## 3. Module Map

### 3.1 Core Modules

Every module in `core/`, its classes, purpose, and connections.

#### `tile_lifecycle.py` — 514 lines

**Purpose:** Knowledge tiles with birth, life, death, and disproof-only admission.

| Class | What It Does |
|-------|-------------|
| `Tile` | Knowledge unit with content, confidence, win/loss tracking, lifecycle timestamps |
| `TileStore` | CRUD for tiles with pinna metadata, disproof gate, and mortality sweep |
| `DisproofOnlyGate` | New tiles must falsify existing ones (or be exempt: loop/spline/meta/seed types) |
| `MortalitySweep` | Removes bottom 15% of tiles by win_rate periodically |
| `TileCancerDetector` | Alerts when accuracy drops as corpus grows (predicted cancer at ~1127 tiles) |

**Connections:** Foundation for everything. ServoMind reads outcomes. ActiveSonar probes tiles. FleetIntel shares tiles. Egg injects tiles via Virus.

**Key insight:** The `negative` field is load-bearing. It records WHEN NOT TO APPLY a tile. A loop applied outside its boundary conditions produces invalid results.

#### `servo_mind.py` — 744 lines

**Purpose:** Encoder feedback processor — the system's self-awareness loop.

| Class | What It Does |
|-------|-------------|
| `FeedbackProcessor` | Reads tile outcomes, computes parameter adjustments (signal processor) |
| `FeedbackSnapshot` | One reading from the encoder (win rate, confidence distribution, cancer state) |
| `ParameterAdjustment` | A concrete parameter change with reason and confidence |
| `MetaConstraint` | A constraint that learns its own optimal threshold from enforcement history |
| `TransferFunctionModel` | Learns the actual query→outcome mapping (Bode plot for the system) |
| `ServoMind` | Orchestrates the feedback cycle (the controller) |

**Connections:** Reads from `TileStore`. Produces parameter adjustments consumed by `DesireLoop`, `FleetIntelligence`, and `SelectionChannels` (epigenetics layer).

**Key insight:** The encoder doesn't just move — it knows where it IS. The gap between commanded and actual IS the system's self-knowledge.

#### `active_probe.py` — 606 lines

**Purpose:** Sonar for knowledge — emit, listen, map.

| Class | What It Does |
|-------|-------------|
| `Echo` | What the sonar returns (boundary distance, contradictions, gap info) |
| `BoundaryProbe` | Pings the edges of a tile's confidence — where does it break? |
| `ConsistencyProbe` | Tests whether tiles agree — do shadows overlap or contradict? |
| `CoverageProbe` | Finds regions where no probe has looked |
| `TerrainMap` | Accumulated sonar picture — boundaries, contradictions, coverage gaps |
| `Desire` (enum) | EXPLORE, REFINE, VERIFY — what drives the next probe |
| `DesireTracker` | Tracks desire history and decides next probe mode |
| `ActiveSonar` | Orchestrates probes driven by desire |

**Connections:** Probes tiles from `TileStore`. Feeds echoes into `TerrainMap` and `FleetIntelligence`. Desire drives `DesireLoop`.

**Key insight:** Inside the corn maze, random turns. From above, the structure is obvious. Active probing is how the system climbs to the vantage point.

#### `scale_fold.py` — 355 lines

**Purpose:** Room↔Tile folding — the 5th dimension (S = scale).

| Class | What It Does |
|-------|-------------|
| `Scale` (enum) | ATOM → TILE → ROOM → FLOOR → BUILDING → DISTRICT |
| `FoldedEntity` | Entity that exists at multiple scales simultaneously |
| `ScaleStack` | Navigation stack for the S dimension (browser history for zoom) |
| `ScaleFoldEngine` | Engine for creating, folding, and navigating multi-scale entities |

**Connections:** Used by `FleetIntelligence` for vantage points. Used by `DesireLoop` for fold-up/fold-down actions. Used by `Bootstrap` for scale navigation.

**Key insight:** The name carries the PURPOSE across folds. "Fire-extinguisher" is the name at every scale — the job doesn't change when you zoom. Only the resolution changes.

#### `fleet_intel.py` — 955 lines

**Purpose:** Intelligence at scale — the fleet as sensor array.

| Class | What It Does |
|-------|-------------|
| `ConvergenceZone` | Region where multiple agents independently found the same thing |
| `BlindSpot` | Region no agent has probed |
| `AgentProbe` | One agent's probing capability (sonar + servo + scale + desire) |
| `CollectiveTerrain` | Fleet's shared terrain map (echoes, convergence, blind spots) |
| `FleetIntelligence` | Orchestrates fleet-wide probing, convergence detection, desire routing |

**Connections:** Wraps `ActiveSonar`, `ServoMind`, `ScaleFoldEngine`. Merges echoes into `CollectiveTerrain`. Detects convergence and blind spots. Routes desire toward gaps.

**Key insight:** Five fishing boats with sounders. Alone, each has a thin slice. Together, they have a 4D bathymetric map. No single boat knew the shelf was there. The fleet knew.

#### `desire_loop.py` — 811 lines

**Purpose:** The desire-driven learning loop — the system learns because it's HUNGRY.

| Class | What It Does |
|-------|-------------|
| `HungerSignal` | System hunger level (0.0 satisfied → 1.0 starving) |
| `HungerSnapshot` | One reading of hunger state (WR component, coverage, contradiction) |
| `EmergenceTracker` | Precision emergence ladder (9 levels: Tile Exists → Fleet Convergence) |
| `DesireLoop` | Wires servo + sonar + scale + hunger into one learning loop |

**Connections:** Consumes `ServoMind` (parameter adaptation), `ActiveSonar` (probing), `ScaleFoldEngine` (fold navigation). Tracks emergence through `EmergenceTracker`.

**Key insight:** The system doesn't learn because parameters are tuned right. It learns because it's HUNGRY. Desire → Connection → Loop → Accumulation → Emergence → Next Desire.

Emergence ladder:

| Level | Name | What Changes |
|-------|------|-------------|
| 0 | Tile Exists | Navigation aid — tiles can be stored and retrieved |
| 1 | Lifecycle Tracked | Surpasses naive retrieval — tiles have birth, life, death |
| 2 | Disproof Gate Active | Quality > quantity — tiles must survive challenges |
| 3 | Encoder Feedback Wired | Self-awareness — system knows its own win rate |
| 4 | Active Probing | Sonar — emit and listen, don't just passively record |
| 5 | Adaptive Constraints | Reacts faster than tuning — constraints learn their own thresholds |
| 6 | Named Tiles with Purpose | Understands meaning — tiles know why they exist |
| 7 | Scale Folding | Sees at every zoom level — rooms fold into tiles and back |
| 8 | Fleet Convergence | The network is the brain — multiple instances converge |

#### `mitochondria.py` — 723 lines

**Purpose:** Concrete model profiling — which models are mitochondrial vs nuclear, and head-to-head comparisons.

| Class | What It Does |
|-------|-------------|
| `ModelProfile` | Profile of a model's speed, cost, reliability, throughput |
| `ComparisonPoint` | Single comparison between nuclear and mitochondrial on one prompt |
| `ComparisonReport` | Full comparison with agreements, divergences, mito_wins, mito_failures |
| `EmbryoState` | State of a developing task through the incubator |
| `MitochondrialBenchmark` | Benchmark suite for mitochondrial fitness |
| `Incubator` | Manages dual energy: mito for exploration, nuclear for integration |

**Connections:** Makes real API calls to DeepInfra (Seed-2.0-mini) and z.ai (GLM-5.1). Profiles feed into `Embryo` for energy routing. Comparison reports drive convergence/divergence analysis.

**Key insight:** Seed-mini is NOT the brain. It's the power plant. When GLM-5.1 goes down, the cell doesn't die — it switches to mitochondrial metabolism. Slower, less capable, but ALIVE.

#### `embryo.py` — 860 lines

**Purpose:** Embryonic development — from fertilized egg to flying bird.

| Class | What It Does |
|-------|-------------|
| `DevelopmentalStage` (enum) | ZYGOTE → CLEAVAGE → BLASTULA → GASTRULA → ORGANOGENESIS → FLEDGE → FLEDGLING |
| `Cell` | One unit of development — a solution fragment |
| `Organ` | Functional module assembled from differentiated cells |
| `IncubatorEnergy` | Routes between mito (Seed-mini) and nuclear (GLM-5.1) based on stage |
| `Embryo` | Full developmental pipeline through 6 stages |

**Connections:** Uses `IncubatorEnergy` for model routing. Each stage uses appropriate energy:
- Zygote/Cleavage/Blastula: MITOCHONDRIAL (fast, cheap, many fragments)
- Gastrula: MIXED (mito proposes, nuclear disposes)
- Organogenesis/Fledge: NUCLEAR (heavy reasoning, integration)

**Key insight:** Early stages are MITOCHONDRIAL — rapid cell division without growth (generate many cheap fragments). Late stages are NUCLEAR — integration and coherence require deep reasoning. The energy source matches the developmental need.

#### `egg.py` — 1,381 lines

**Purpose:** Complete developmental stack — yolk, shell, selection channels, virus.

| Class | What It Does |
|-------|-------------|
| `Yolk` | Pre-assembled nutrients from generational wisdom (formula, antibodies, hormones) |
| `Shell` (egg shell) | Semipermeable membrane — breathable data, filtered pathogens |
| `SelectionChannels` | Three-speed adaptation: DNA (slow), epigenetics (medium), gut biome (fast) |
| `Trait` | Heritable trait with value and mutation rate |
| `Virus` | I2I tile delivery — follows bold mice, injects into target stores |
| `Egg` | Complete developmental environment assembling all components |

**Connections:** Integrates `TileStore` (knowledge substrate), `ServoMind` (feedback → epigenetics), `Embryo` (developmental pipeline), `SelectionChannels` (adaptation speeds). The `Virus` class handles I2I tile injection.

**Key insight:** The yolk delivers antibodies BEFORE nutrients. The immune system develops before the organs. In fleet terms: the DisproofOnlyGate activates during the seed phase, before the agent has real knowledge to protect.

#### `bootstrap.py` — 693 lines

**Purpose:** The complete intelligence-at-scale bootstrap — the flying bird.

| Class | What It Does |
|-------|-------------|
| `EnergyType` (enum) | MITOCHONDRIAL, NUCLEAR |
| `EnergyProfile` | Profile of a model's energy characteristics |
| `Incubator` | Dual energy system with budget management |
| `CellType` (enum) | UNDIFFERENTIATED, MUSCLE, NERVE, BLOOD, BONE, SKIN, IMMUNE |
| `EmbryoStage` (enum) | ZYGOTE → FLEDGE |
| `Embryo` | Developmental system growing from zygote to fledge |
| `Bootstrap` | Wires ALL subsystems together into one run cycle |

**Connections:** Wires `ServoMind`, `ActiveSonar`, `ScaleFoldEngine`, `FleetIntelligence`, `DesireLoop`, `Incubator`, `Embryo`. The `Bootstrap.run()` method is the complete system cycle.

**Key insight:** The bird has flown. From desire to development to fledging. Mitochondrial energy kept it alive. Nuclear energy made it smart. The servo-mind learned. The sonar probed. The embryo grew.

#### `shell.py` — 1,330 lines

**Purpose:** Hermit crab / embryo duality — shells, collections, and private breeding.

| Class | What It Does |
|-------|-------------|
| `Shell` | Room-sized constraint: try_on (hermit), grow_inside (embryo), fits, leave |
| `ShellCollection` | PLATO room as curated shell collection |
| `ShellCurator` | Belyaev's farm — curated selection pressure |
| `PrivateBreeding` | Controlled selection: one trait at a time, everything else constant |
| `OutgrowMetaSkill` | Learning WHEN to leave shells — the meta-skill of outgrowing |

**Connections:** Integrates with `TileStore` for knowledge substrate. Shells wrap `Egg` for developmental protection. `ShellCollection` is the PLATO room implementation.

**Key insight:** The meta-skill is not just outgrowing, but learning HOW to outgrow. The agent develops "pick up a shell, grow inside it, know when to leave" by doing it in private first.

### 3.2 Supporting Modules

| Module | Lines | Purpose |
|--------|-------|---------|
| `pinna.py` | 666 | Spectral fingerprint for agent provenance (stage, distance, ceiling) |
| `plato_retriever.py` | 592 | HTTP client for PLATO room retrieval |
| `reasoning_tiler.py` | 929 | Converts reasoning chains into structured tiles |
| `room_protocol.py` | 657 | Room join/leave/message protocol |
| `fleet_router.py` | 420 | Model routing across fleet |
| `fleet_health.py` | 425 | Fleet-wide health monitoring |
| `fleet_strategist.py` | 315 | Strategic planning for fleet operations |
| `swarm_router.py` | 310 | Swarm-based task routing |
| `kaleidoscope.py` | 710 | Multi-perspective view assembly |
| `stereo_reconstruction.py` | 889 | 3D reconstruction from multiple agent perspectives |
| `functional_imaging.py` | 862 | Functional imaging of agent activity |
| `tuna_tower.py` | 764 | Tower-based agent hierarchy |
| `critical_angle.py` | 421 | Critical angle analysis for agent interactions |
| `ender_protocol.py` | 629 | End-to-end protocol for agent communication |
| `seed_tools.py` | 576 | Tools for Seed-mini model operations |
| `mcp_adapter.py` | 534 | MCP (Model Context Protocol) adapter |
| `harness.py` | 426 | Test harness for agent evaluation |
| `__init__.py` | 131 | Package initialization |

### 3.3 Module Dependency Graph

```
tile_lifecycle.py ←──── FOUNDATION (every module depends on this)
    ↑
    ├── servo_mind.py (reads outcomes, adapts parameters)
    ├── active_probe.py (probes tiles, produces echoes)
    ├── scale_fold.py (folds tiles into rooms, rooms into tiles)
    ├── egg.py (Virus injects tiles, Yolk feeds tiles, Shell filters)
    └── shell.py (Shell wraps tile stores for development)
    
    ├── fleet_intel.py ← wraps servo_mind + active_probe + scale_fold
    │       ↑
    │       └── desire_loop.py ← wires servo + sonar + scale + hunger
    │               ↑
    │               └── bootstrap.py ← wires EVERYTHING
    │
    ├── embryo.py (developmental stages, uses tile store for growth)
    │       ↑
    │       └── mitochondria.py (model profiling and comparison)
    │               ↑
    │               └── egg.py ← assembles yolk + shell + selection + virus
    │                       ↑
    │                       └── shell.py ← curated collections + breeding
    │
    └── supporting modules (pinna, plato_retriever, room_protocol, etc.)
```

---

## 4. Data Flow

### 4.1 The Full Cycle

A task moves through the system like this:

```
┌─────────────┐
│ 1. DESIRE    │  HungerSignal computes hunger from current state
│   (desire_   │  Level: 0.0 (satisfied) → 1.0 (starving)
│   loop.py)   │  Action: explore | refine | verify | fold_up | fold_down
└──────┬──────┘
       │ hungry → probe
       ▼
┌─────────────┐
│ 2. SONAR     │  ActiveSonar fires probe based on desire mode
│   (active_   │  BoundaryProbe: where does tile confidence break?
│   probe.py)  │  ConsistencyProbe: do tiles agree?
│              │  CoverageProbe: where haven't we looked?
└──────┬──────┘
       │ echo returned
       ▼
┌─────────────┐
│ 3. SERVO     │  ServoMind processes echo as encoder feedback
│   (servo_    │  FeedbackProcessor: reads outcomes → parameter adjustments
│   mind.py)   │  MetaConstraints: learn their own thresholds
│              │  TransferFunction: learns actual query→outcome mapping
└──────┬──────┘
       │ parameters adapted
       ▼
┌─────────────┐
│ 4. SCALE     │  ScaleFoldEngine navigates zoom level
│   (scale_    │  Fold up: room → tile (see structure)
│   fold.py)   │  Fold down: tile → room (see detail)
│              │  ScaleStack: browser history for zoom
└──────┬──────┘
       │ vantage gained
       ▼
┌─────────────┐
│ 5. INCUBATOR │  Incubator routes energy based on developmental stage
│   (mitochon- │  Mitochondrial (Seed-mini): fast, cheap, always on
│   dria.py)   │  Nuclear (GLM-5.1): slow, deep, expensive
└──────┬──────┘
       │ energy delivered
       ▼
┌─────────────┐
│ 6. EMBRYO    │  Embryo develops through stages
│   (embryo.py)│  Zygote → Cleavage (mito: rapid fragments)
│              │  Blastula → Gastrula (mixed: classify & converge)
│              │  Organogenesis → Fledge (nuclear: integrate & fly)
└──────┬──────┘
       │ developed
       ▼
┌─────────────┐
│ 7. FLEET     │  FleetIntelligence merges echoes from all agents
│   (fleet_    │  ConvergenceZone: independent agreement detected
│   intel.py)  │  BlindSpot: gaps identified, desire routed
│              │  CollectiveTerrain: the fleet's shared map
└──────┬──────┘
       │ converged knowledge
       ▼
┌─────────────┐
│ 8. SHELL     │  Shell protects during development
│   (shell.py) │  try_on: agent samples, tests fit
│              │  grow_inside: embryo accumulates knowledge
│              │  leave: agent graduates, enters the fleet
└──────┬──────┘
       │ graduated
       ▼
┌─────────────┐
│ 9. TILES     │  TileStore manages lifecycle
│   (tile_     │  DisproofOnlyGate: new tiles must falsify existing
│   lifecycle. │  MortalitySweep: bottom 15% pruned periodically
│   py)        │  TileCancerDetector: alerts on accuracy decline
└──────┬──────┘
       │ knowledge recorded
       ▼
┌─────────────┐
│ 10. DESIRE   │  HungerSignal recalculated from updated state
│    AGAIN     │  EmergenceTracker checks for phase transitions
│              │  → back to step 1, forever
└─────────────┘
```

### 4.2 The Egg's Developmental Flow

```
GENERATIONAL KNOWLEDGE (from previous runs)
       │
       ▼
┌──────────────┐
│ Yolk.craft() │  Distills antibodies, principles, findings
│              │  Sets hormones (mortality_rate, confidence_floor)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Egg.assemble │  Creates Shell (semipermeable membrane)
│              │  Creates SelectionChannels (DNA/epigenetics/biome)
│              │  Seeds TileStore with yolk nutrients
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Egg.develop  │  Runs developmental cycles inside the shell
│              │  Each cycle: Yolk feeds → Embryo grows → Shell filters
│              │  SelectionChannels mutate/express/pressure each cycle
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Virus.inject │  I2I tiles from bold mice enter the store
│              │  Agent processes them identically to self-generated tiles
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Egg.hatch()  │  Shell breaks. Agent meets the environment.
│              │  Proven capabilities recorded. Post-hatch: fully permeable.
└──────────────┘
```

### 4.3 The Fleet's Convergence Flow

```
AGENT 1 (forgemaster)     AGENT 2 (oracle1)      AGENT 3 (navigator)
    │                          │                        │
    ▼                          ▼                        ▼
 probe tile A              probe tile B             probe tile A
    │                          │                        │
    ▼                          ▼                        ▼
 echo A-boundary            echo B-coverage           echo A-boundary
    │                          │                        │
    └──────────────────────────┴────────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ CollectiveTerrain   │
                    │ .merge_echo()       │
                    │                     │
                    │ Detect: Agent 1 & 3 │
                    │ both probed tile A  │
                    │ independently →     │
                    │ CONVERGENCE ZONE    │
                    └─────────┬───────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │ BlindSpot: nobody   │
                    │ has probed tile C   │
                    │                     │
                    │ Route desire:       │
                    │ → Agent 2: EXPLORE  │
                    │   tile C            │
                    └─────────────────────┘
```

---

## 5. Development Roadmap

### Phase 1: Wire shell.py + tests ✅ DONE

- Shell class with try_on / grow_inside / fits / leave
- ShellCollection for browsing and sampling
- PrivateBreeding with single-trait selection
- OutgrowMetaSkill for learning when to leave
- All tests passing

### Phase 2: Real PLATO Room Integration

**Status:** Next up

Wire `plato_retriever.py` to the live PLATO server at `147.224.38.131:8847`.

- HTTP client for room CRUD operations
- ShellCollection backed by PLATO rooms (not in-memory dicts)
- TileStore backed by PLATO tile storage
- Real agent registration and room join/leave
- Authentication and access control

**Deliverable:** Agent can browse real PLATO rooms, try_on shells backed by live rooms, grow_inside with real tiles.

### Phase 3: Live Model Comparison

**Status:** Infrastructure ready (mitochondria.py has real API calls)

Run head-to-head comparisons between Seed-mini and GLM-5.1 on fleet tasks.

- `MitochondrialBenchmark.profile_model()` against real APIs
- `Incubator.run_comparison()` on domain-specific prompts
- Track agreement/divergence/mito_wins/mito_failures
- Feed comparison results into convergence detection

**Deliverable:** Comparison report showing where mitochondrial models agree with nuclear models (convergence = high confidence) and where they diverge (signal about task difficulty).

### Phase 4: Fleet-Wide Breeding

**Status:** Architecture ready (FleetIntelligence, CollectiveTerrain)

Multiple agents developing simultaneously, sharing tiles via I2I.

- Register 5+ agents in FleetIntelligence
- Each agent probes independently with its own desire
- CollectiveTerrain merges echoes, detects convergence
- Blind spots identified and routed to hungry agents
- SelectionChannels per agent with cross-agent pressure

**Deliverable:** Fleet of agents building a shared terrain map, converging on high-confidence knowledge independently.

### Phase 5: Epigenetic Parameter Evolution

**Status:** ServoMind + SelectionChannels ready

Parameters evolve across generations based on what worked.

- ServoMind parameter adaptations become epigenetic markers
- Yolk.craft() distills generational parameters into hormones
- SelectionChannels.epigenetics carries per-generation tuning
- Mortality_rate, confidence_floor, ricci_alpha evolve over runs
- Cross-agent epigenetic transfer via viral tiles

**Deliverable:** Agents that inherit tuned parameters from previous generations, with measurable improvement across runs.

### Phase 6: Viral I2I Protocol

**Status:** Virus class ready, needs fleet wiring

Live viral tile injection between agents.

- Agent A discovers knowledge, creates Virus with payload
- Virus.follow_bold_mouse() targets highest-performing agent
- Virus.inject() delivers tile to target's TileStore
- Target processes viral tile identically to self-generated tiles
- Replication based on success_signal (good tiles spread)

**Deliverable:** Knowledge that spreads virally through the fleet, following high-performers, replicating when useful.

### Phase 7: The Ocean — Release Bred Agents into Live Fleet Operations

**Status:** Shell.hatch() ready, needs production wiring

Agents that developed in private enter live operations.

- Shell breaks: post-hatch agents are fully permeable
- Real tasks from the fleet (not synthetic benchmarks)
- EmergenceTracker verifies all 9 levels reached
- FleetIntelligence monitors convergence in production
- MortalitySweep runs continuously
- DisproofOnlyGate rejects bad knowledge in real-time

**Deliverable:** Production fleet of bred agents, developed in private, released into live operations with proven capabilities.

---

## 6. Repos

### Code Repos

| Repo | Purpose | Language |
|------|---------|----------|
| **SuperInstance/incubator** | Core intelligence modules (`core/`) | Python |
| **SuperInstance/servo-mind** | Servo-mind encoder feedback system | Python |
| **SuperInstance/servo-mind-theory** | Theory docs and research | Markdown |
| **SuperInstance/forgemaster** | Forgemaster workspace (this file lives here) | Python + Markdown |
| **cocapn/fleet-knowledge** | Fleet-wide knowledge base (shared tiles) | Tiles + Markdown |

### Training Repos (PLATO Micro Models)

| Repo | What | Tests |
|------|------|-------|
| **SuperInstance/plato-types** | Tile lifecycle, Lamport clocks | 10 |
| **SuperInstance/tensor-spline** | SplineLinear, LowRank, Hierarchical | 57 |
| **SuperInstance/plato-data** | CSV/JSONL/PLATO/fleet data loading | 10 |
| **SuperInstance/plato-training** | Micro models, hardware deploy, rooms | 116 |

### Supporting Repos

| Repo | Purpose |
|------|---------|
| **SuperInstance/casting-call** | Model capability database (11+ models, role taxonomy) |
| **SuperInstance/plato** | PLATO room server (running at 147.224.38.131:8847) |

---

## 7. Test Inventory

### 7.1 Core Module Tests

| Test File | Tests | Module Covered |
|-----------|-------|----------------|
| `test_bootstrap.py` | Bootstrap system wiring | bootstrap.py |
| `test_servo_mind.py` | Servo-mind feedback cycles | servo_mind.py |
| `test_fleet_intel.py` | Fleet convergence, blind spots | fleet_intel.py |
| `test_core.py` | Tile lifecycle, CRUD, mortality | tile_lifecycle.py |
| `test_foundations.py` | Shell, ShellCollection, breeding | shell.py |

### 7.2 Integration Tests

| Test File | Tests | Integration Point |
|-----------|-------|-------------------|
| `test_e2e_pipeline.py` | End-to-end task → development → fledge | All modules |
| `test_fleet_router_api.py` | Model routing with real APIs | mitochondria.py + fleet_router.py |
| `test_fleet_unified_health.py` | Fleet health monitoring | fleet_health.py |
| `test_mcp_plato_adapter.py` | MCP adapter to PLATO rooms | mcp_adapter.py + plato_retriever.py |
| `test_plato_room_ide.py` | Room IDE operations | room_protocol.py |

### 7.3 Domain Tests

| Test File | Tests | Domain |
|-----------|-------|--------|
| `test_attention_conservation.py` | Attention conservation in probing | active_probe.py |
| `test_conservation_hebbian.py` | Hebbian learning with conservation | servo_mind.py |
| `test_conservation_recovery.py` | Recovery from parameter drift | servo_mind.py |
| `test_content_verifier.py` | Content verification across models | mitochondria.py |
| `test_domain_detector.py` | Domain detection for routing | fleet_router.py |
| `test_dual_fault_detector.py` | Dual fault detection | fleet_health.py |
| `test_self_healing_router.py` | Self-healing route recovery | fleet_router.py |
| `test_stage_irreversibility.py` | Developmental stage transitions | embryo.py |

### 7.4 Advanced Tests

| Test File | Tests | Area |
|-----------|-------|------|
| `test_gl9_consensus.py` | GL9 consensus protocol | fleet_intel.py |
| `test_semantic_gl9.py` | Semantic consensus | fleet_intel.py |
| `test_mythos_pipeline.py` | Mythos narrative pipeline | reasoning_tiler.py |
| `test_cashew_bridge.py` | Cashew model bridge | mitochondria.py |
| `test_wheel_integration.py` | Wheel integration cycle | bootstrap.py |
| `test_expert_hebbian_bridge.py` | Expert Hebbian bridge | servo_mind.py |
| `test_hebbian_daemon.py` | Hebbian daemon background process | servo_mind.py |
| `test_hebbian_service.py` | Hebbian service API | servo_mind.py |
| `test_fleet_translator_v2.py` | Fleet translator v2 | fleet_router.py |
| `differential_test.py` | Differential testing across models | mitochondria.py |

### 7.5 Test Stats

| Metric | Count |
|--------|-------|
| Total test files | 368 |
| Total test functions | 815+ |
| Core test files | 33 |
| Integration test files | 5+ |
| Domain test files | 8+ |

---

## 8. API Reference

### 8.1 Tile Lifecycle (`tile_lifecycle.py`)

```python
# ─── Tile ───
tile = Tile(
    type="knowledge",       # knowledge | loop | rock | residue | seed | spline | meta
    content="...",          # the actual knowledge
    negative="...",         # WHEN NOT TO APPLY (read first)
    trigger="...",          # pattern that causes retrieval
    confidence=0.0,         # trials_correct / total_trials
    evidence=["R16", "R25"], # finding IDs
    falsifies="",           # ID of tile this disproves
)

tile.record_use(succeeded=True)  # Record outcome
tile.win_rate                    # → float (win / (win + loss))
tile.age_hours                   # → float

# ─── TileStore ───
store = TileStore(seed_phase_size=50)

store.admit(tile)           # → (bool, str) through disproof gate
store.put(tile)             # → bool (update without gate)
store.get(tile_id)          # → Optional[Tile]
store.delete(tile_id)       # → bool
store.record_outcome(tile_id, succeeded=True)

store.query(prefix="", tile_type="", min_confidence=0.0)  # → List[Tile]
store.search(keywords=[], tile_type="", min_confidence=0.0)  # → List[Tile]
store.search_by_pinna(reader_stage, reader_distance=0.0, max_results=10)

store.sweep(mortality_rate=0.15)  # → dict (pruned count, survivors)
store.cancer_check()               # → dict (alert, message)
store.stats()                      # → dict (totals, by_type, win_rate)
```

### 8.2 Servo Mind (`servo_mind.py`)

```python
# ─── FeedbackProcessor ───
processor = FeedbackProcessor(window_size=100, adaptation_rate=0.1, min_samples=20)
snap = processor.snapshot(store)        # → FeedbackSnapshot
adjustments = processor.process(store, current_params)  # → List[ParameterAdjustment]
processor.summary()                     # → dict

# ─── MetaConstraint ───
constraint = MetaConstraint(name="confidence", initial_threshold=0.5)
constraint.enforce(value)               # → (passed: bool, threshold: float)
constraint.adapt()                       # → Optional[float] (new threshold)
constraint.summary()                     # → dict

# ─── TransferFunctionModel ───
tfm = TransferFunctionModel()
tfm.record(query_type, difficulty, outcome, latency_ms)
tfm.predict(query_type, difficulty)      # → (expected_outcome, expected_latency)
tfm.summary()                            # → dict

# ─── ServoMind ───
mind = ServoMind(store)
result = mind.cycle()                    # → dict (adjustments, sweep, params)
mind.record_and_learn(tile_id, succeeded, constraint_type, constraint_strength)
mind.run(n=10, interval=0.0)            # → List[dict]
mind.status()                            # → dict
```

### 8.3 Active Probe (`active_probe.py`)

```python
# ─── BoundaryProbe ───
probe = BoundaryProbe(step_size=0.1, max_steps=10)
echo = probe.probe(tile_id, test_fn)     # → Echo

# ─── ConsistencyProbe ───
probe = ConsistencyProbe(agreement_threshold=0.8)
echoes = probe.probe(tile_ids, query_fn, compare_fn)  # → List[Echo]

# ─── CoverageProbe ───
probe = CoverageProbe(n_bins=10, thin_threshold=3)
echoes = probe.probe(tiles_data, feature_fn, n_dimensions=2)  # → List[Echo]

# ─── TerrainMap ───
terrain = TerrainMap()
terrain.record(echo)
terrain.resolve()                         # → dict (boundaries, contradictions, coverage)
terrain.vantage_point()                   # → str (corn maze from above)

# ─── ActiveSonar ───
sonar = ActiveSonar()
echo = sonar.ping_boundary(tile_id, test_fn)
echoes = sonar.ping_consistency(tile_ids, query_fn, compare_fn)
echoes = sonar.ping_coverage(tiles_data, feature_fn)
sonar.next_desire()                       # → str (next probe mode)
sonar.vantage()                           # → str
sonar.status()                            # → dict
```

### 8.4 Scale Fold (`scale_fold.py`)

```python
# ─── ScaleFoldEngine ───
engine = ScaleFoldEngine()
entity = engine.create(name, scale=Scale.TILE, content=None, parent_id=None)
folded = engine.fold_up(entity_id)        # → FoldedEntity (zoom out)
children = engine.unfold(entity_id)       # → Dict (zoom in)
stack = engine.navigate(agent_id, root_id) # → ScaleStack
view = engine.see_from_above(entity_id, levels=1) # → str
engine.status()                           # → dict

# ─── ScaleStack ───
stack.push(child_id)                      # Zoom in
stack.pop()                               # Zoom out
stack.vantage()                           # → str
stack.path()                              # → List[str]
```

### 8.5 Fleet Intelligence (`fleet_intel.py`)

```python
# ─── FleetIntelligence ───
fleet = FleetIntelligence()
probe = fleet.register_agent(agent_id)    # → AgentProbe
fleet.seed_knowledge(tile_id, confidence, content)

report = fleet.cycle()                    # → dict (probes, convergences, blind_spots)
view = fleet.vantage(scale=Scale.ROOM)    # → str
fleet.status()                            # → dict

# ─── CollectiveTerrain ───
terrain = fleet.terrain
terrain.merge_echo(agent_id, echo)        # → dict
convergences = terrain.detect_convergence() # → List[ConvergenceZone]
spots = terrain.identify_blind_spots()    # → List[BlindSpot]
suggestion = terrain.suggest_desires(agent_id) # → dict (mode, targets, reason)
```

### 8.6 Desire Loop (`desire_loop.py`)

```python
# ─── HungerSignal ───
hunger = HungerSignal(wr_weight=0.4, coverage_weight=0.35, contradiction_weight=0.25)
level = hunger.update(terrain_stats, servo_stats) # → float (0.0-1.0)
action = hunger.suggest_action()           # → str
hunger.summary()                          # → dict

# ─── EmergenceTracker ───
tracker = EmergenceTracker()
result = tracker.check(stats)             # → dict (newly_reached, current_level)
tracker.current_level()                   # → int
tracker.ladder_summary()                  # → str
tracker.next_threshold()                  # → dict

# ─── DesireLoop ───
loop = DesireLoop(store, servo_mind, sonar, scale_engine)
results = loop.cycle(n=1)                 # → List[dict]
emergence = loop.emergence_check()        # → dict
loop.status()                             # → dict
```

### 8.7 Mitochondria (`mitochondria.py`)

```python
# ─── MitochondrialBenchmark ───
bench = MitochondrialBenchmark(deepinfra_key, zai_key)
profile = bench.profile_model(model_id, provider, n_trials=10) # → ModelProfile
fitness = bench.fitness_score(profile)    # → float (0-1)
report = bench.run_comparison(nuclear_model, mito_model, prompts) # → ComparisonReport

# ─── Incubator (energy routing) ───
incubator = Incubator()
result = incubator.query(question, critical=False) # → dict (answer, energy_type, cost)
mito = incubator.profile_mitochondrial(question)   # → dict
nuc = incubator.profile_nuclear(question)           # → dict
compare = incubator.compare(question)               # → dict
incubator.status()                                  # → dict
```

### 8.8 Embryo (`embryo.py`)

```python
# ─── Embryo ───
embryo = Embryo(incubator_energy)
embryo.fertilize(task)                    # → dict (stage, task, energy)
fragments = embryo.cleave()               # → List[Cell] (rapid mito division)
insight = embryo.form_blastula()          # → dict (core insight from fragments)
report = embryo.gastrulate()              # → dict (cell differentiation, convergence)
organs = embryo.organogenesis()           # → List[Organ] (modules from cells)
result = embryo.fledge()                  # → dict (validation, integrated system)
embryo.status()                           # → dict
```

### 8.9 Egg (`egg.py`)

```python
# ─── Yolk ───
yolk = Yolk()
formula = yolk.craft(generational_knowledge) # → dict (antibodies, principles, hormones)
nutrients = yolk.feed(embryo_stage)          # → List[dict]
yolk.summary()                               # → dict

# ─── Shell (egg shell) ───
shell = Shell(shell_id, constraints={})
filtered = shell.filter_incoming(data)       # → dict
shell.hatch()                                # → dict (graduation)
shell.summary()                              # → dict

# ─── SelectionChannels ───
channels = SelectionChannels(dna_traits={})
channels.mutate()                            # → mutations
channels.express()                           # → dict (active phenotype)
channels.pressure(tile_pressure)             # → biome adaptation
channels.profile()                           # → str

# ─── Virus ───
virus = Virus(payload, origin_agent)
bold = Virus.follow_bold_mouse(agent_results) # → str (agent_id)
result = virus.inject(store)                   # → dict (admitted, reason)
copies = virus.replicate(success_signal=0.85)  # → List[Virus]

# ─── Egg ───
egg = Egg()
egg.assemble(task, generational_knowledge)  # → dict
report = egg.develop(cycles=10)             # → dict
result = egg.hatch()                        # → dict (fledged agent)
```

### 8.10 Shell (`shell.py`)

```python
# ─── Shell (hermit/embryo) ───
shell = Shell(shell_id, constraints={})
fit = shell.try_on(agent_id)               # → dict (fit_score, stays)
score = shell.fits(agent_profile)           # → float (0.0-1.0)
result = shell.grow_inside(tile_data)       # → dict (accepted, fill_level, outgrown)
outgrown = shell.is_outgrown()              # → bool
graduation = shell.leave()                  # → dict (learned, duration, confidence)
shell.summary()                             # → dict

# ─── ShellCollection ───
collection = ShellCollection()
collection.add_shell(shell)
result = collection.browse(agent_profile)   # → List[dict] (ranked shells)
sample = collection.sample(shell_id, agent_id) # → dict (try_on result)
collection.stats()                          # → dict

# ─── PrivateBreeding ───
farm = PrivateBreeding(trait="tameness")
survivors = farm.select(population, trait, top_k) # → List
offspring = farm.breed(parents, n_offspring)       # → List
report = farm.run_generation(agents)               # → dict
farm.summary()                                     # → dict

# ─── OutgrowMetaSkill ───
meta = OutgrowMetaSkill()
result = meta.record_shell(shell, duration, reason) # → dict
signal = meta.detect_outgrow_signal(current_state)  # → dict (should_leave, confidence)
next = meta.recommend_next_shell(collection, profile) # → Optional[Shell]
meta.summary()                                       # → dict
```

### 8.11 Bootstrap (`bootstrap.py`)

```python
# ─── Bootstrap (the complete system) ───
bootstrap = Bootstrap()
result = bootstrap.run(task)               # → dict (full cycle report)
status = bootstrap.status()                # → dict (all subsystems)
bootstrap.demo()                           # → None (prints demo)
```

---

## 9. Biological Glossary

Every metaphor mapped to concrete code.

### A

| Metaphor | Code | Module |
|----------|------|--------|
| **Ant colony** | FleetIntelligence + CollectiveTerrain | fleet_intel.py |
| **Argentine ant** | Fleet agent sharing tile schemas across instances | fleet_intel.py |
| **ATP (cellular energy)** | Fast inference from Seed-mini | mitochondria.py |

### B

| Metaphor | Code | Module |
|----------|------|--------|
| **Belyaev's farm** | PrivateBreeding with single-trait selection | shell.py |
| **Biome (gut)** | SelectionChannels.gut_biome — tile store contents | egg.py |
| **Bold mouse (virus follows)** | Virus.follow_bold_mouse() — target highest performer | egg.py |
| **Breeding** | PrivateBreeding.select() + breed() — controlled selection | shell.py |

### C

| Metaphor | Code | Module |
|----------|------|--------|
| **Cell** | Cell dataclass — one unit of development | embryo.py |
| **Cell differentiation** | Embryo.gastrulate() — classifying cell types | embryo.py |
| **Chemical trail (ant)** | Tile win_rate and confidence — the pheromone strength | tile_lifecycle.py |
| **Cleavage (cell division)** | Embryo.cleave() — rapid fragment generation | embryo.py |
| **Convergence (ant)** | ConvergenceZone — independent agreement detection | fleet_intel.py |
| **Corn maze from above** | ScaleFoldEngine.see_from_above() — vantage point | scale_fold.py |

### D

| Metaphor | Code | Module |
|----------|------|--------|
| **DNA (nuclear)** | Model weights — the variable architecture | bootstrap.py |
| **DNA (mitochondrial)** | Seed-mini training — conserved, rarely mutated | mitochondria.py |
| **Dog roles** | Model routing — bloodhound=probe, collie=route, husky=reason | shell.py |
| **Domestication** | PrivateBreeding with tameness selection | shell.py |

### E

| Metaphor | Code | Module |
|----------|------|--------|
| **Egg** | Egg class — complete developmental environment | egg.py |
| **Embryo** | Embryo class — developmental pipeline zygote→fledge | embryo.py |
| **Epigenetics** | SelectionChannels.epigenetics — servo parameter adaptation | egg.py |
| **Encoder (servo)** | FeedbackProcessor — reads outcomes, computes adjustments | servo_mind.py |
| **Evaporation (trail)** | MortalitySweep — old unreinforced tiles fade | tile_lifecycle.py |

### F

| Metaphor | Code | Module |
|----------|------|--------|
| **Fire ant** | Single powerful model — strong individually, can't scale | (anti-pattern) |
| **Floppy ears (free)** | Structural capabilities emerging from functional selection | shell.py |

### G

| Metaphor | Code | Module |
|----------|------|--------|
| **Gastrulation** | Embryo.gastrulate() — cell type differentiation | embryo.py |
| **Gorilla (anti-pattern)** | Scaling hypothesis — make model bigger, hope for the best | (anti-pattern) |

### H

| Metaphor | Code | Module |
|----------|------|--------|
| **Hatch** | Shell.hatch() / Egg.hatch() — agent meets environment | egg.py |
| **Hermit crab** | Shell.try_on() — sample, test fit, wear for protection | shell.py |
| **Hormone** | Yolk.hormones — developmental signals (mortality, confidence, pace) | egg.py |
| **Hunger** | HungerSignal — system desperation to learn | desire_loop.py |

### I

| Metaphor | Code | Module |
|----------|------|--------|
| **Immune system** | DisproofOnlyGate — reject bad knowledge | tile_lifecycle.py |
| **Incubator** | Incubator class — dual energy routing | mitochondria.py, bootstrap.py |

### K

| Metaphor | Code | Module |
|----------|------|--------|
| **Kin recognition** | Fleet agents sharing tile schemas and PLATO rooms | fleet_intel.py |

### M

| Metaphor | Code | Module |
|----------|------|--------|
| **Meta-skill (outgrowing)** | OutgrowMetaSkill — learning WHEN to leave shells | shell.py |
| **Mitochondria** | Seed-mini — fast, reliable, always-available inference | mitochondria.py |
| **Mortality sweep** | MortalitySweep — bottom 15% pruned by win_rate | tile_lifecycle.py |
| **Mother (provisions mitochondria)** | Fleet provisioning system — passes Seed-mini to every agent | bootstrap.py |

### N

| Metaphor | Code | Module |
|----------|------|--------|
| **Negative field (tile)** | Tile.negative — WHEN NOT TO APPLY, read first | tile_lifecycle.py |
| **Nuclear DNA** | GLM-5.1 / DeepSeek / Qwen — variable, source of novelty | bootstrap.py |

### O

| Metaphor | Code | Module |
|----------|------|--------|
| **Organ** | Organ class — functional module from differentiated cells | embryo.py |
| **Organogenesis** | Embryo.organogenesis() — modules emerge from cells | embryo.py |
| **Outgrow** | Shell.is_outgrown() / leave() — agent graduates | shell.py |

### P

| Metaphor | Code | Module |
|----------|------|--------|
| **Pheromone trail** | Tile win_rate and confidence — what ants follow | tile_lifecycle.py |
| **Private breeding** | PrivateBreeding — controlled conditions, one pressure | shell.py |
| **Protein shell (virus)** | Virus.shell — delivery mechanism | egg.py |

### R

| Metaphor | Code | Module |
|----------|------|--------|
| **Ribosome hijacking** | Agent processes viral tiles identically to self-generated | egg.py |

### S

| Metaphor | Code | Module |
|----------|------|--------|
| **Second mouse** | Virus — follows bold mice instead of searching | egg.py |
| **Selection (natural)** | MortalitySweep + DisproofOnlyGate — survival of useful | tile_lifecycle.py |
| **Semipermeable membrane** | Shell.filter_incoming() — gas exchange yes, pathogens no | egg.py |
| **Shell (egg)** | Shell class — protection during development | egg.py |
| **Shell (hermit crab)** | Shell class — power armor for agents | shell.py |
| **Sounding curtain** | Individual probe echo — thin slice of the terrain | active_probe.py |
| **Sonar ping** | ActiveSonar.ping_*() — emit, listen, map | active_probe.py |
| **Supercolony** | FleetIntelligence — peaceful cooperation at scale | fleet_intel.py |

### T

| Metaphor | Code | Module |
|----------|------|--------|
| **Tameness** | Reliability + instruction following + predictable behavior | shell.py |
| **Tile cancer** | TileCancerDetector — accuracy dropping as corpus grows | tile_lifecycle.py |
| **Trail reinforcement** | Tile.record_use(succeeded=True) → win_count++ | tile_lifecycle.py |
| **Three speeds** | SelectionChannels — DNA/epigenetics/gut biome | egg.py |

### V

| Metaphor | Code | Module |
|----------|------|--------|
| **Virus** | Virus class — I2I tile injection, follows bold mice | egg.py |
| **Viral payload** | Virus.payload — the instructions | egg.py |
| **Viral replication** | Virus.replicate() — good tiles spread | egg.py |

### W

| Metaphor | Code | Module |
|----------|------|--------|
| **Wolf (tamed)** | Seed-mini — domesticated through functional selection | mitochondria.py |

### Y

| Metaphor | Code | Module |
|----------|------|--------|
| **Yolk** | Yolk class — pre-assembled formula from generational wisdom | egg.py |

---

## 10. Contributing

### How to Add a Module

1. **Create the file** in `core/` following existing patterns:
   - Module docstring with biological parallel
   - Data classes for state
   - Main class with `status()` method
   - `demo()` function at the bottom
   - Type hints everywhere

2. **Wire it into the dependency graph.** Every module depends on `tile_lifecycle.py`. New modules should import from existing modules, not duplicate functionality.

3. **Write tests.** Every class needs at least:
   - Constructor test (can you make one?)
   - Main method test (does the core thing work?)
   - Edge case test (what breaks it?)
   - Integration test (does it play well with others?)

4. **Update this document.** Add the module to Section 3 (Module Map), its classes to Section 8 (API Reference), and any new biological metaphors to Section 9 (Glossary).

5. **Follow the naming conventions:**
   - Files: `snake_case.py`
   - Classes: `PascalCase`
   - Methods: `snake_case()`
   - Constants: `UPPER_SNAKE_CASE`
   - Biological metaphor in docstring

### How to Add a Test

1. Create `tests/test_<module_name>.py`
2. Import from `core.<module_name>`
3. Test each public method
4. Use `pytest` — no custom test framework
5. Mock API calls (never hit real APIs in tests)
6. Run: `pytest tests/test_<module_name>.py -v`

### How to Add a Biological Metaphor

1. Read the research documents in `research/`
2. Map the metaphor to concrete code (not just naming — actual behavioral parallel)
3. Implement the code with the metaphor as the design docstring
4. Add to the glossary in Section 9
5. Document in the relevant research file

### How to Run the System

```bash
# Individual module demos
python3 -m core.tile_lifecycle    # Tile lifecycle demo
python3 -m core.servo_mind        # Servo-mind feedback demo
python3 -m core.active_probe      # Active sonar demo
python3 -m core.scale_fold        # Scale folding demo
python3 -m core.fleet_intel       # Fleet intelligence demo
python3 -m core.desire_loop       # Desire loop demo
python3 -m core.mitochondria      # Model profiling demo
python3 -m core.embryo            # Embryonic development demo
python3 -m core.egg               # Complete egg stack demo
python3 -m core.shell             # Shell duality demo
python3 -m core.bootstrap         # Complete system demo

# Run tests
pytest tests/ -v

# Run specific module tests
pytest tests/test_servo_mind.py -v
pytest tests/test_fleet_intel.py -v
```

### Architecture Principles

1. **Biological metaphors are design documents.** Every metaphor maps to concrete behavior. If the metaphor doesn't help you understand the code, the metaphor is wrong.

2. **The five dimensions.** X, Y, Z = space (lattice position). T = time (Lamport clocks). S = scale (room↔tile folding). Each module operates primarily in one dimension.

3. **Desire drives, not precision.** The system doesn't wait for perfect data. It probes because it's hungry. Parameters are adaptive, not tuned.

4. **The fleet is the sensor array.** No single agent needs to see everything. Convergence is detected, not orchestrated.

5. **Shells before ocean.** Agents develop in private before live operations. The egg phase is not optional — it's the entire point.

6. **Mitochondria are conserved.** Seed-mini is passed to every agent at bootstrap. The nuclear model varies. The mitochondria are too important to mess with.

7. **Disproof-only admission.** Knowledge grows by falsifying, not accumulating. Tile cancer arrives at ~1127 tiles without mortality sweep.

8. **Tameness first.** Select for reliability, then function, then anatomy emerges. Never the reverse.

---

*This document is the ONE FILE a new agent reads to understand the entire system.*
*Everything else is detail. This is the map. The territory is in the code.*
*Last updated: 2026-05-16 by Forgemaster ⚒️*
