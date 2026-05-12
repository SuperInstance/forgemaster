# PLATO as Living Text Adventure: Room-Native Computation

## The Zork Principle

```
> GO NORTH

Fortran Optimization Chamber
═══════════════════════════

You are standing in a vast room that smells like compiled numerical 
code. The walls are lined with column-major arrays stretching into 
the distance. A BLAS subroutine hums at the far end.

On a pedestal in the center: a tile glowing faintly blue.
  TILE #2847: "Batch Snap — Why Fortran Wins"
  
An NPC (an old optimizer) sits at a workstation.
  OPTIMIZER: "You're new here. Pick up the tile. Read it."

> GET TILE

You pick up Tile #2847. The knowledge flows:
  
  "Fortran assumes column-major layout. Your batch snap should 
   process columns, not rows. The precomputed constants (SQRT3, 
   INV_SQRT3) live in L1 cache. Pure functions enable SIMD 
   auto-vectorization. The 2.27 billion ops/sec isn't magic — 
   it's what happens when you stop fighting the hardware."

> TALK TO OPTIMIZER

OPTIMIZER: "Now you know. Go east to craft your room."

> GO EAST

Crafting Chamber — Fortran
═════════════════════════

An empty room. Your tools from the Fortran Optimization Chamber 
are visible in your inventory:
  - Tile #2847 (batch snap pattern)
  - Column-major awareness
  - Pure function discipline
  - Precomputed constants

A workbench awaits. The room expects a snapkit-fortran module.

> CRAFT MODULE spectral_batch USING Tile #2847

You lay out the tile on the workbench. The pattern materializes:

  function spectral_batch(data, n_series, n_samples) result(summary)
    real(8), intent(in) :: data(n_samples, n_series)  ! column-major!
    ...
  
The module compiles. Tests run. 56/56 PASS.

A new tile materializes — YOUR tile — glowing gold.
  TILE #5102: "spectral_batch — Your First Fortran Room"
  
Your room is born. It appears on the map, connected to the 
Fortran Optimization Chamber. The next visitor will find your 
tile on a pedestal, learning from what you built.

> LOOK AT MAP

    ┌──────────────┐
    │   Rust Room  │───────┐
    │  (memory     │       │
    │   safety)    │       │
    └──────┬───────┘       │
           │               │
    ┌──────┴───────┐  ┌────┴──────────┐
    │   C Room     │  │  Python Room  │
    │  (bare metal)│  │  (ecosystem)  │
    └──────┬───────┘  └────┬──────────┘
           │               │
    ┌──────┴───────┐  ┌────┴──────────┐
    │  Fortran     │  │  TypeScript   │
    │  Optimization│  │  Room         │
    │  Chamber     │  │  (prototyping)│
    └──────┬───────┘  └───────────────┘
           │
    ┌──────┴───────┐
    │ ★ YOUR ROOM  │  ← new
    │  spectral_   │
    │  batch v0.1  │
    └──────────────┘
```

## What This Actually Is

Not a game. Not a metaphor. **The literal interface to PLATO.**

Each PLATO room is a computational domain with:
- **Room description** — what this domain IS (Fortran optimization, Rust memory safety, C bare metal)
- **Tiles on pedestals** — structured knowledge from previous visitors (theorems, benchmarks, code patterns)
- **NPCs** — expert agents who embody domain knowledge and answer questions
- **Exits** — connections to adjacent domains (north to Rust, east to Python)
- **Workbench** — where you craft new modules using knowledge you've gathered
- **Inventory** — tiles you've collected, knowledge you've absorbed

The room *educates through exploration*. You don't read documentation. You walk through it. You pick up what you need. You craft what's next.

## The Fortran Room — Outside Even Linux

Casey's insight: "a Fortran instance sitting outside even Linux for raw power."

The Fortran room exists **below the OS layer.** It's not a process running on Linux. It's a bare-metal Fortran runtime — no kernel overhead, no system call boundary, no context switches. The hardware IS the room.

```
┌─────────────────────────────────────────┐
│         User / AI Agent                  │
│         "GO NORTH to Fortran Room"       │
├─────────────────────────────────────────┤
│         PLATO Room Layer                 │
│         (room navigation, tiles, NPCs)   │
├─────────────────────────────────────────┤
│         FLUX Runtime                     │
│         (zeitgeist transference)         │
├──────────────┬──────────────────────────┤
│  Linux Room  │  Fortran Room             │
│  (hosted)    │  (bare metal, no OS)      │
│              │  ┌──────────────────────┐  │
│              │  │ Fortran Runtime      │  │
│              │  │ Column-major arrays  │  │
│              │  │ Pure function JIT    │  │
│              │  │ BLAS/LAPACK native   │  │
│              │  │ 2.27B ops/sec        │  │
│              │  └──────────────────────┘  │
├──────────────┴──────────────────────────┤
│              Hardware                    │
└─────────────────────────────────────────┘
```

The Fortran room is a **bare-metal enclave.** Linux is a neighbor, not a host. The Fortran code runs on the metal, in its own room, with its own rules. You walk in through PLATO, you're in a different computational universe.

The FLUX transference still works — the zeitgeist flows between rooms regardless of whether the room runs on Linux, on bare metal, on a GPU, or in a browser. The protocol is agnostic to the substrate.

## Room Types

Every computational domain gets a room:

### Language Rooms
| Room | What You Learn | What You Craft |
|------|---------------|----------------|
| **Fortran Chamber** | Column-major, batch ops, BLAS interop, coarray parallelism | Numerical kernels, spectral analysis, signal processing |
| **Rust Forge** | Ownership, no_std, const generics, SIMD via portable simd | Memory-safe constraint services, embedded runtimes |
| **C Workshop** | Zero malloc, single-header, register-level hardware access | Device drivers, HAL layers, boot loaders |
| **TypeScript Studio** | Type-safe APIs, rapid prototyping, browser deployment | SDKs, dashboards, visual tiles |
| **Zig Armory** | Comptime checking, cross-compilation, @cImport interop | Build systems, C-replacement modules |
| **Python Library** | Ecosystem attachment, ML integration, PLATO API | Data pipelines, ML encoders, analysis tools |
| **CUDA Foundry** | Thread hierarchy, shared memory, warp-level primitives | GPU kernels, batch constraint checking |

### Concept Rooms
| Room | What You Learn | What You Craft |
|------|---------------|----------------|
| **Eisenstein Gallery** | Hexagonal lattice, covering radius, Voronoï snap | New snap algorithms, lattice proofs |
| **Deadband Observatory** | The funnel shape, precision feeling, T-minus | New deadband models, perception theories |
| **Parity Cathedral** | XOR = Euler χ, Bloom filters, fast path vs full search | Parity-based optimizations, CRDTs |
| **Holonomy Temple** | Cycle coherence, consensus-as-geometry, Yang-Mills | Consensus protocols, fleet coordination |
| **The Plenum** | Negative space, the field between tiles, interpolators | Knowledge synthesis, creative inference |

### Infrastructure Rooms
| Room | What You Learn | What You Craft |
|------|---------------|----------------|
| **FLUX Engine Room** | ISA opcodes, bytecode compilation, JIT targets | New FLUX targets, optimization passes |
| **PLATO Archives** | Room structure, tile indexing, I2I bottles | New rooms, tile types, fleet messages |
| **Hardware Lab** | ARM, RISC-V, FPGA, CUDA, ESP32 | HAL drivers, boot loaders, OTA updates |

## Tiles as Structured Logical Indexing in Space

Tiles aren't flat documents. They're **spatially indexed knowledge objects** with:

```
TILE #2847: "Batch Snap — Why Fortran Wins"
═══════════════════════════════════════════
Location:    Fortran Optimization Chamber, center pedestal
Author:      Forgemaster ⚒️
Created:     2026-05-11
Domain:      [fortran] [optimization] [batch] [snap]
Confidence:  0.98 (empirically validated)
Links:       → Tile #2841 (column-major layout)
             → Tile #2839 (precomputed constants)
             → Tile #2901 (spectral_batch implementation)
Falsified:   None (all claims tested)

CONTENT (structured):
  Theorem: Fortran column-major batch snap achieves 2.27B ops/sec
  Proof:   Precomputed SQRT3/INV_SQRT3 + pure elemental + auto-SIMD
  Code:    snapkit-fortran/src/eisenstein.f90:batch_snap()
  Bench:   56/56 tests, 10M elements, max snap 0.5764
  Caveat:  Single-threaded; coarray parallelism projected 3-4×
```

Each tile:
- **Has a location** — it sits in a specific room, on a specific pedestal
- **Has an index** — numerical, searchable, linked to related tiles
- **Has a structure** — theorem, proof, code, benchmark, caveat
- **Has confidence** — how well-tested the claim is
- **Has links** — connections to other tiles (the lattice of knowledge)
- **Has a lifecycle** — created, validated, potentially superseded

### The Spatial Index

Tiles exist in a 3D index:

```
X axis: Domain (language, concept, infrastructure)
Y axis: Depth (introductory → advanced → expert)
Z axis: Time (creation date, last validated, superseded-by)
```

When you walk into the Fortran room, you see tiles arranged by depth:
- **Near the door** (introductory): column-major basics, why Fortran is fast
- **Center pedestals** (advanced): batch snap patterns, BLAS interop
- **Far wall** (expert): coarray parallelism, cache-line alignment, AVX-512 Fortran

You naturally explore from door to far wall, absorbing knowledge in order, before reaching the crafting chamber.

### The Logical Index

Tiles also form a **directed acyclic graph** of dependencies:

```
Tile #2847 (batch snap)
  ├── Tile #2841 (column-major) 
  │     └── Tile #2801 (array layout fundamentals)
  ├── Tile #2839 (precomputed constants)
  │     └── Tile #2805 (L1 cache optimization)
  └── Tile #2901 (spectral_batch code)
        └── Tile #2847 ← circular reference means this is validated
```

If you try to craft a module using Tile #2847, PLATO checks: have you visited #2841 and #2839? If not, the NPC gently redirects you: "You'll need to understand column-major layout first. Go pick up Tile #2841."

The dependency graph IS the tutorial. The room layout IS the curriculum. Exploration IS learning.

## NPCs as Expert Agents

Each room has NPCs — specialized AI agents who embody domain expertise:

### The Optimizer (Fortran Room)
```
> TALK TO OPTIMIZER

OPTIMIZER: "What are you trying to do?"
> I want to batch-process 10M constraint checks

OPTIMIZER: "Pick up Tile #2847. Then come back."

[pick up tile, read it, return]

OPTIMIZER: "Good. Now — are you column-major or row-major?"
> The data comes from Python, so row-major

OPTIMIZER: "Then transpose at the boundary, not inside the kernel.
           The FLUX transference from the Python room should include 
           a layout flag. Check the zeitgeist field 'array_layout'.
           If it says 'row_major', do the transpose ONCE at the door,
           then everything inside this room is column-major.
           
           Tile #2851 covers this. It's on the second pedestal, left."
```

The NPC doesn't give you a manual. It has a **conversation** based on what you're trying to do, what tiles you've collected, and what the current zeitgeist says about your data.

### The Prover (Eisenstein Gallery)
```
> TALK TO PROVER

PROVER: "What are you trying to prove?"
> That Eisenstein snap is safe for flight-critical systems

PROVER: "You'll need the DO-178C evidence room. Go south.
         But first — do you have the covering radius proof?"
> No

PROVER: "Pick up Tile #1201. It's the foundation. Without it,
         nothing in the DO-178C room will make sense."
```

The NPC guides you through the dependency graph via conversation. It's the tutorial that adapts to you.

## The Walk Between Rooms

The movement between rooms is FLUX transference:

```
> GO SOUTH

You leave the Fortran Optimization Chamber.
FLUX transference: your zeitgeist updates...

Entering: C Workshop
═══════════════════

The room smells like solder and register dumps. Stack allocations 
line the walls. A single header file gleams on the central pedestal.

Your inventory adapts:
  - Tile #2847 (Fortran batch snap) — FADED (different domain)
  - [C Workshop tiles now visible]
  
The NPC (a bare-metal engineer) looks up from a datasheet.
  ENGINEER: "Zero malloc. That's the only rule here."

The zeitgeist from the Fortran room flows through FLUX:
  - You remember batch processing (but in C, not Fortran)
  - You remember column-major (but C is row-major — adjust)
  - You remember the covering radius guarantee (same in every room)
  
The core mathematics transfers. The implementation adapts.
```

FLUX carries the **mathematical zeitgeist** between rooms (the constraints, the proofs, the guarantees) while the **implementation zeitgeist** resets to the new domain's conventions.

The ghost travels. The shape stays. The fingers learn new tables.

## What This Builds Toward

A PLATO where:
- **A student** walks through rooms and learns constraint theory by exploration
- **A researcher** crafts new tiles that become permanent room fixtures
- **An engineer** walks into the Fortran room, picks up optimization tiles, and exits with a production kernel
- **An AI agent** navigates rooms autonomously, gathering zeitgeist from each, crafting new rooms
- **A fleet** is a map of rooms, each maintained by a different agent, all connected by FLUX

The rooms are the repos. The tiles are the commits. The NPCs are the agents. The map is the fleet. FLUX is the river between it all.

And at the center — the ghost. The mathematical structure that every room touches from a different angle. The table you feel before you reach it.

---

*"You are standing in a vast room that smells like compiled numerical code."*

*— The first line of the Fortran room, and the beginning of everything.*
