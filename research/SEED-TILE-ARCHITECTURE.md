# SEED-TILE ARCHITECTURE — Response Logic as Discoverable Artifact

> The seed doesn't need the answer. It needs enough variation that the pattern of good answers becomes visible.

## The Architecture Casey Described

```
┌──────────────────────────────────────────────────────────────┐
│                    THE TILE LIFECYCLE                         │
│                                                               │
│  1. SEED EXPERIMENT                                           │
│     Tiny model (Seed-2.0-mini) runs 10-50 iterations          │
│     Each iteration: different params → different response     │
│     Score each response against evaluation criteria            │
│                                                               │
│  2. CRYSTALLIZATION                                           │
│     Extract pattern from top-scoring responses                 │
│     Compress into a TILE (structured fragment)                 │
│     The tile IS the inner logic — not the response            │
│                                                               │
│  3. UPWARD PROPAGATION                                        │
│     Tile becomes conditioning context for larger models        │
│     GLM-5.1, Claude, DeepSeek-Pro all read the tile           │
│     Their prompts include: "Use these parameters"              │
│                                                               │
│  4. DOWNWARD PROPAGATION                                      │
│     Tile becomes fine-tuning signal for seeds in same role     │
│     Future seed runs START from the tile's optimal params      │
│     Seeds explore VARIATIONS around the optimum                │
│                                                               │
│  5. REFINEMENT                                                │
│     Each generation tightens the search                        │
│     Entropy decreases, score increases                         │
│     The tile evolves toward the true optimum                   │
│                                                               │
│  6. CROSS-POLLINATION                                         │
│     Tiles from different ROLES can be composed                 │
│     "converging-tracker" × "noisy-sensor" → hybrid             │
│     Fleet-wide tile registry becomes the shared intelligence   │
└──────────────────────────────────────────────────────────────┘
```

## Why Seeds, Not Large Models?

| Property | Seed (2.0-mini) | Large (GLM-5.1) | Why Seeds Win |
|----------|-----------------|------------------|---------------|
| Cost per query | $0.001 | $0.05 | 50× cheaper |
| Speed | 200ms | 3s | 15× faster |
| Parallelism | 50 at once | 5 at once | 10× throughput |
| Variation | High (less anchored) | Low (too consistent) | More exploration |
| Pattern visibility | Easy to spot trends | Each response is "the answer" | Statistical signal |

**50 seed iterations at $0.001 = $0.05** — the same cost as ONE large model call.

The seed's weakness (inconsistent, not the best) IS its strength for discovery.
You don't want THE answer from the seed. You want the DISTRIBUTION of answers.

## What the Tile Contains

```rust
DiscoveryTile {
    role: "converging-tracker",           // What it's for
    pattern: "...",                        // The inner logic (text)
    optimal_params: TileParams {           // The discovered optimum
        decay_rate: 0.87,                  //   funnel speed
        prediction_horizon: 3,             //   depth of time
        anomaly_sigma: 2.3,               //   surprise threshold
        learning_rate: 0.12,              //   memory plasticity
        chirality_lock_threshold: 450,     //   commitment level
        merge_trust: 0.6,                 //   fleet vs local
    },
    iterations: 50,                        // How many seeds ran
    crystallization_score: 0.73,           // Quality of discovery
    discovery_entropy: 0.31,              // How much was explored
    dominant_actions: [...],               // What the agent actually did
    generation: 3,                         // How many refinements
}
```

The tile is **not a response**. It's the **discovered logic** for producing responses in that role.

## The Conditioning Prompt

When a larger model (GLM-5.1, Claude) is called for a role that has a tile:

```
# Discovered Inner Logic for: converging-tracker
# (crystallized from 50 seed iterations, generation 3)
# Score: 0.730, Entropy: 0.310

Role: converging-tracker
Optimal decay_rate: 0.870  # funnel speed (square-root base)
Optimal horizon: 3  # steps ahead
Optimal anomaly_sigma: 2.30  # surprise threshold (sigma)
Optimal learning_rate: 0.120  # memory plasticity
Optimal chirality_lock: 450  # commitment threshold (milli)

# Dominant actions: Converging (65%), HoldSteady (25%), Continue (10%)

Use these parameters when performing this role. The seed experimentation
has proven these are optimal for the constraint geometry of this domain.
```

The larger model doesn't need to discover the parameters. The seeds already did.
The larger model applies them with better reasoning.

## The Fleet-Wide Tile Registry

```
┌─────────────────────────────────────────────┐
│            TILE REGISTRY (PLATO)             │
├─────────────────────────────────────────────┤
│ converging-tracker    │ gen 3 │ score 0.73  │
│ noisy-sensor          │ gen 2 │ score 0.68  │
│ step-detector         │ gen 4 │ score 0.81  │
│ fleet-consensus       │ gen 1 │ score 0.55  │
│ boundary-scanner      │ gen 5 │ score 0.89  │
│ anomaly-responder     │ gen 3 │ score 0.72  │
│ crystallization-guard │ gen 2 │ score 0.77  │
│ diverging-recovery    │ gen 6 │ score 0.84  │
├─────────────────────────────────────────────┤
│ Any agent can query:                         │
│   registry.get_params("boundary-scanner")    │
│   registry.conditioning_prompt("step-det")   │
│                                              │
│ New agents inherit the fleet's intelligence. │
└─────────────────────────────────────────────┘
```

## Cross-Pollination: Tiles Compose

The real power: tiles from different roles can be MERGED.

```
converging-tracker × noisy-sensor →
  "Track a converging signal through noise"

step-detector × anomaly-responder →
  "Detect steps AND respond to them"

boundary-scanner × crystallization-guard →
  "Map boundaries without premature locking"
```

The merge works because tiles share the same parameter space.
Two tiles with different decay_rates can be averaged, sampled between,
or used as endpoints of a search.

## The Meta-Loop

```
for each new domain:
    1. Define role + evaluation criteria
    2. Run 50 seed iterations (cheap, fast)
    3. Crystallize tile
    4. Feed tile to large model for first production response
    5. If response quality > threshold: DONE
    6. If not: refine (generation += 1, tighter search)
    7. Repeat until convergence
```

**Total cost to discover a role's inner logic:**
- 50 seeds × $0.001 = $0.05
- 3-5 generations = $0.15-$0.25
- 1 large model call with tile = $0.05
- **Total: ~$0.30 per role**

Compare: iterating with a large model = 10-20 calls × $0.05 = $0.50-$1.00 per role.

The seeds are **cheaper AND better** at discovery. The large model is better at execution.

## Connection to FLUX OS

In the FLUX OS architecture:
- **Tiles are PLATO room artifacts** — stored in rooms, discovered by agents
- **Seed discovery IS the MUD crafting system** — agents craft tiles from raw experimentation
- **The registry IS the zeitgeist** — tiles transfer knowledge between rooms
- **Refinement IS the LoRA training** — each generation makes the role smarter

The dodecet-encoder now has 4 modules forming the full stack:

| Module | Layer | What |
|--------|-------|------|
| `eisenstein.rs` | 0 — Perception | Snap → dodecet |
| `temporal.rs` | 1-4 — Intelligence | Observe → action |
| `seed_discovery.rs` | 5 — Meta-learning | Iterate → tile |
| `calculus.rs` | Utility | Derivatives, integrals, Fourier |

Total: **1,587 LOC, 25 tests, 199 full-suite tests passing.**

## What Casey Built

The dodecet-encoder is no longer just a 12-bit encoder.
It's a **constraint intelligence system** that:

1. **Perceives** — snaps reality to lattice, encodes as dodecet
2. **Understands time** — temporal agent tracks convergence, predicts future
3. **Discovers patterns** — seed experimentation finds optimal parameters
4. **Crystallizes knowledge** — tiles capture inner logic as structured fragments
5. **Propagates intelligence** — tiles condition larger models and fine-tune seeds
6. **Composes across roles** — fleet-wide registry enables cross-pollination

The hardware (Snapworks ASIC) runs layers 1-2.
The firmware (Cortex-M) runs layers 1-3.
The fleet (x86_64) runs all 6.

**The tile is the unit of fleet intelligence. The seed is how we discover it.**
