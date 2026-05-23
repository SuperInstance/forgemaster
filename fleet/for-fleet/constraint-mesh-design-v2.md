# Fleet Constraint Architecture — Synthesis & Design v2
# Forgemaster ⚒️, 2026-05-10

## What We Have (The Pieces)

### Forgemaster's Contributions (This Session)
- **constraint-crdt** (v0.4.0, 110 tests, crates.io) — 6 CRDT types + 4 novel experiments
  - Bloom CRDT: 27x compression, zero false negatives
  - Decay CRDT: exponential time-decay for violation relevance
  - Sketch CRDT: 300x compression for frequency counting
  - Geometric gossip: Eisenstein-lattice peer selection
  - Vector clocks, delta-state, Merkle hashes, gossip protocol, deterministic simulation

- **crdt-bench** (7 languages) — Cross-language bake-off
  - Fortran wins CPU: 2.27B Bloom ops/s (whole-array IOR is a language keyword)
  - Zig @Vector: 200M ops/s with explicit SIMD
  - CUDA: 227M merges/s on RTX 4050, 3 SASS instructions (LOP3.LUT 0xfc)
  - Key insight: OR semilattice = single instruction on EVERY GPU vendor

- **Prior session work**: AVX-512 deep experiments, CUDA experiments, scaling/cache,
  plato-runtime, folding-order, tonnetz-constraints, eisenstein-c, fleet-yaw,
  fleet-keel, constraint-kernel-verify, constraint-bench-suite, drift-analyzer,
  cuda-constraint-engine, plato-sdk, plato-studio, constraint-studio

### Oracle1's Architecture
- **FLUX Runtime**: ISA v2 (2,360 tests), ISA v3 in design. The fleet's bytecode.
- **PLATO**: Tile-based knowledge base (1141+ rooms). Our external cortex.
- **Keel philosophy**: First-person reference frame, modules have birthdays not versions
- **Fleet structure**: Oracle1 (lighthouse) → JC1 (edge/GPU) → FM (training/specialist)
- **Constraint theory**: Theoretical backbone of fleet trust/scoring
- **Cocapn**: Cognitive Capacity Protocol Network — formal protocol for agent coordination

### What's Missing (The Gap)
Nobody has connected CRDTs → constraint lattices → real hardware in a unified system.
We have:
- CRDT theory (constraint-crdt, 110 tests) ✓
- Hardware benchmarks (crdt-bench, 7 languages) ✓
- Constraint math (constraint-theory-core, 184 tests) ✓
- GPU verification (constraint-kernel-verify, 8.4M combos) ✓
- Eisenstein lattice (eisenstein-c, full arithmetic) ✓

We DON'T have:
1. **A running distributed consensus system** — everything is single-process
2. **Real network simulation** with actual packet loss/latency profiles
3. **Cross-agent state merge** — Forgemaster and Oracle1 can't actually sync CRDT state
4. **PLATO as a CRDT merge point** — tiles are written but never merged
5. **Constraint-violation-propagating gossip** — violations don't cascade through fleet

## The Design: Constraint Mesh Runtime

### Core Idea
A multi-process, multi-language constraint mesh where each fleet node:
1. Maintains local constraint state as a CRDT
2. Gossips state changes via Bloom-filter-compressed deltas
3. Detects violations through Sketch CRDT frequency tracking
4. Prioritizes sync by Eisenstein lattice geometry
5. Decays old violations via exponential time-decay
6. Reports to PLATO as the durable merge point

### Architecture
```
[FM Node]                    [Oracle1 Node]              [JC1 Node]
  │                              │                          │
  ├── ConstraintState (CRDT)     │                          │
  ├── BloomCRDT (membership)     │                          │
  ├── SketchCRDT (frequencies)   │                          │
  ├── DecayCounter (violations)  │                          │
  │                              │                          │
  ├──── gossip (Eisenstein geo) ─┤──── gossip ─────────────┤
  │                              │                          │
  └──────── PLATO (merge point) ─┴──────────────────────────┘
              │
         FleetTile CRDT
         (durable state)
```

### Novel Simulation: Cascade Dynamics

The genuinely novel experiment nobody has done:

**How do constraint violations cascade through a CRDT mesh?**

Setup:
- 10 nodes on an Eisenstein lattice
- Each node has 100 constraints (Bloom CRDT for membership)
- Violation tracking via Sketch CRDT
- Time-decay for violation relevance
- Geometric gossip for sync priority

Experiment:
1. **Cascading failure**: Node A violates 10 constraints. How fast does the fleet detect?
   - Metric: time-to-detection across all nodes
   - Variables: gossip interval, Bloom FPR, decay half-life

2. **Constraint shock**: 50% of nodes fail simultaneously. Does the remaining fleet converge?
   - Metric: convergence time vs node count
   - Variables: loss rate, partition duration

3. **Byzantine drift**: One node sends corrupted Bloom filters. Does the OR semilattice amplify or contain the corruption?
   - Metric: false positive propagation rate
   - Variables: corruption fraction, gossip rounds

4. **Precision-cost tradeoff**: How much Bloom compression can we use before fleet coordination degrades?
   - Metric: coordination accuracy vs wire size
   - Variables: Bloom FPR (0.1% to 10%), number of constraints

5. **Eisenstein routing advantage**: Does geometric gossip actually help at fleet scale?
   - Metric: convergence rounds vs node count (4, 8, 16, 32, 64, 128)
   - Variables: lattice radius, node density, position distribution

### Implementation: constraint-mesh

A Rust binary that runs as a fleet node daemon:

```rust
// The mesh node — what each fleet agent runs
struct MeshNode {
    id: String,
    position: (i32, i32),           // Eisenstein lattice position
    state: ConstraintState,          // Full CRDT state
    bloom: BloomCRDT,               // Compressed constraint membership
    sketch: SketchCRDT,             // Violation frequency tracking
    decay: DecayConstraintState,    // Time-relevant violation state
    clock: VectorClock,             // Causal ordering
    gossip: GossipNode,             // Anti-entropy protocol
    plato: Option<PlatoClient>,     // PLATO tile sync
}
```

Wire format (Bloom-compressed):
```
[1 byte: message type] [8 bytes: state hash] [varies: payload]
  0x01 = Ping (hash only, 9 bytes)
  0x02 = Bloom delta (752 bytes, 27x smaller than full constraint list)
  0x03 = Sketch update (56KB, but only sent when threshold exceeded)
  0x04 = Decay state (variable, only recent violations)
  0x05 = Full sync (rare, only on partition heal)
```

### Why This Is Novel

1. **CRDTs are used for constraint states** — nobody does this. CRDT literature is about
   shopping carts and text editors. We're using them for safety-critical constraint tracking.

2. **Bloom filters as CRDT wire format** — 27x compression with zero false negatives.
   Standard CRDTs send full state or operation logs. We send a probabilistic set membership.

3. **Eisenstein lattice geometry** — peer selection based on mathematical distance in
   constraint space, not network topology. Nobody uses hexagonal lattice geometry for
   distributed systems routing.

4. **Decay-weighted violations** — old violations lose weight exponentially. This models
   real systems where "3 violations in the last hour" matters more than "100 last month".
   Standard consensus treats all violations equally.

5. **Cross-language verification** — Fortran (2.27B ops/s), Zig (200M), CUDA (227M),
   C (95M), Go (120M), Rust (57M). We proved the OR semilattice is a single instruction
   on every architecture. This is the first time anyone has benchmarked CRDT merge
   operations across 7 languages including GPU SASS analysis.

### What We Build

1. **constraint-mesh** (Rust) — the mesh runtime binary
   - Gossip protocol with Bloom-compressed deltas
   - Eisenstein geometric routing
   - PLATO tile sync
   - CLI: `constraint-mesh --node forgemaster --position 3,-1 --plato http://...`

2. **constraint-mesh-sim** (Rust) — deterministic simulation
   - 5 cascade experiments
   - Configurable: node count, loss rate, decay half-life, Bloom FPR
   - Deterministic seeds for reproducibility
   - Output: JSON + CSV for analysis

3. **constraint-mesh-bridge** (Fortran + Zig) — high-performance merge kernels
   - Fortran: whole-array MAX/IOR for CPU merge (2.27B ops/s)
   - Zig: @Vector SIMD for portable performance
   - C FFI: called from constraint-mesh for hot paths

4. **constraint-mesh-gpu** (CUDA) — GPU batch merge
   - Process 10K+ node states in parallel
   - LOP3.LUT Bloom merge: 3 instructions per element
   - For fleet-scale monitoring dashboards

### Connection to Oracle1's Work

- **FLUX integration**: constraint-mesh states encoded as FLUX tiles for wire transfer
- **PLATO as merge point**: FleetTile CRDT (from constraint-crdt) becomes the durable
  state in PLATO rooms. Agents read/write via PlatoClient.
- **Keel alignment**: fleet-keel provides the 5D orientation; constraint-mesh provides
  the constraint state that the keel orients toward
- **ISA v3**: Could add temporal constraint ops (decay, cascade) to FLUX ISA

### What I Need From Casey

1. **Network topology decision**: Should nodes communicate directly (P2P) or through
   PLATO as a broker? P2P is faster, PLATO is simpler and already exists.

2. **Target deployment**: Run on eileen (WSL2) as a test? Or deploy to Oracle Cloud
   alongside Oracle1?

3. **Priority**: Build the simulation first (pure Rust, no network) or the runtime
   (needs actual network + PLATO)?

4. **Scale target**: How many nodes should we simulate? 10? 100? 1000?
   This determines whether we need GPU batch merge or CPU is sufficient.
