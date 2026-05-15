# Hebbian × PLATO: What's Real and What We Could Build

## The Salvageable Core

Jayan's one real insight: **"Neurons that fire together wire together, and novelty suspends habitual action."**

Strip the crypto token, the AGI claims, the missing equations. What's left is:
1. **Hebbian association**: co-occurring activations strengthen pathways
2. **Habituation → action**: repeated exposure speeds pathway traversal, eventually triggering output
3. **Novelty → suspension**: unfamiliar inputs travel weak pathways, delaying output, buying processing time

This is real neuroscience. Predictive coding (Friston), surprise minimization, orienting responses — all formalize this. It's not wrong. It's just not enough for AGI by itself.

## What Maps to Our Architecture

### PLATO Rooms = Neuron Clusters

A PLATO room is already a "neuron cluster" — it receives tiles (activation), processes them, and emits tiles (output). The room protocol IS a Hebbian dynamic if we add one thing:

**Tile frequency → connection strength.** Rooms that frequently exchange tiles develop stronger routing. Currently our routing is explicit (agent decides where to send tiles). What if routing strength was EMERGENT from tile frequency?

```
Current:  Agent → explicit decision → send tile to room X
Hebbian:  Room A emits tile → tile flows to Room B (strong connection) 
          Connection strength = f(tile_frequency_between_A_and_B)
```

This is actually useful. Right now our fleet routing is manual (I decide which model to call). Hebbian routing would mean: models that frequently produce correct answers for a given task type develop stronger "connections" — future tiles of that type automatically route there.

### The Activation-Key Finding IS Hebbian Habituation

Study 46 showed: the model computes correctly with step-by-step language but fails with symbolic notation. In Hebbian terms:

- **Step-by-step language**: strong pathway, traversed millions of times in training → fast, reliable activation
- **Unicode notation `a²-ab+b²`**: weak pathway, rarely traversed → unreliable activation, defaults to strongest neighbor pathway (a²+ab+b²)

The "formula substitution" we found IS Hebbian dynamics in a transformer. The most-frequently-activated pathway (a²+ab+b², the common variant) wins the competition when the explicit pathway is weak.

### Novelty Suspension = Our Stage Classification

Our fleet stage classifier does something analogous to Jayan's "novelty suspends action":

- Stage 1-2 models: echo/nonsense → route away (suspend action)
- Stage 3 models: vocabulary-triggered wrong procedure → translate first (override habituation)
- Stage 4 models: immune → let them act directly (no novelty problem)

We're already doing what Jayan describes — just at the routing level, not the neuron level.

## What Our Metal Could Solve

Jayan's bottleneck: "500K neurons, need 1000 iterations/second, currently get 1."

Our numbers:
- Zig constraint library: 10M Eisenstein ops in 25ms
- CUDA warp-level: 32 operations per clock per SM
- PTX assembly: direct register control, zero overhead
- CDRT (constraint-aware dispatch): routes computation to optimal hardware

A CUDA SNN implementation:

```
Neuron state: float4 (activation, threshold, weight_sum, fire_flag)
Synapse: float2 (weight, decay)
500K neurons × 5K connections = 2.5B synapses

Memory: 2.5B × 8 bytes = 20GB → fits in A100 40GB
Compute: 2.5B multiply-adds per iteration
A100: 312 TFLOPS → 312T / 2.5B = 125,000 iterations/second

Jayan needs 1000. We'd give 125,000.
```

That's 125× his target. On ONE GPU.

## The Real Architecture: PLATO Rooms as Emergent Hebbian Network

Here's what I think Casey is pointing at:

```
┌─────────────────────────────────────────────────┐
│           PLATO HEBBIAN LAYER                    │
│                                                  │
│  Room A ←──strong──→ Room B                     │
│    ↑                    ↑                        │
│    │  weak              │  medium                │
│    ↓                    ↓                        │
│  Room C ←──strong──→ Room D                     │
│                                                  │
│  Connection strength = tile_frequency(A,B)       │
│  Novelty = low-frequency tile type               │
│  Habituation = high-frequency tile type           │
│                                                  │
│  On new tile:                                    │
│    - Low novelty (seen often) → fast route       │
│      to strongest-connected room → quick output  │
│    - High novelty (rare) → slow route            │
│      through multiple rooms → deeper processing  │
└─────────────────────────────────────────────────┘
```

The rooms don't need to "learn" in Jayan's sense. They already process tiles. The EMERGENT behavior comes from:

1. **Tile frequency tracking**: every room tracks how often it receives each tile type
2. **Connection strengthening**: rooms that co-process similar tiles develop routing affinity
3. **Novelty detection**: tile types with low frequency get routed through MORE rooms (deeper processing)
4. **Habituated routing**: tile types with high frequency get routed through FEWER rooms (fast path)

This is Jayan's mechanism, but:
- **Our rooms are real** (not hypothetical neurons)
- **Our tiles are real** (not activation values)
- **Our metal is fast** (CUDA/PTX, not Python)
- **Our fleet is real** (14 models, already deployed)

## The Missing Piece: Emergent Coordination at Scale

Jayan's right about one thing: emergent behavior requires SCALE. His 500K neuron prototype is trivial because it's too small. But our fleet has:

- 9 agents (Forgemaster, Oracle1, CCC, etc.)
- 14 models across 3 providers
- 1141+ PLATO rooms
- Real tasks (constraint checking, micro models, fleet routing)

If rooms developed Hebbian connections based on tile flow, the fleet would:
- **Auto-route** tasks to the best model without explicit routing rules
- **Detect novel tasks** (low-frequency tile types) and route them through more processing
- **Habituate to common tasks** (high-frequency) and route them directly to the fastest path
- **Develop emergent specializations** — rooms that frequently process similar tiles would naturally cluster

## What We'd Actually Build

### Phase 1: Hebbian Tile Router (Python, on top of PLATO)
- Track tile flow between rooms
- Compute connection strengths (cosine similarity of tile patterns)
- Route novel tiles through more rooms, habituated tiles through fewer
- This IS our fleet_stage_classifier but emergent instead of explicit

### Phase 2: CUDA SNN Layer (for hot-path computation)
- Implement Jayan's 500K neuron network on CUDA
- Use our constraint library for lattice operations
- PTX assembly for the Hebbian update rule
- Wire into PLATO as a "HebbianRoom" that does emergence

### Phase 3: Emergent Fleet Coordination
- Multiple Hebbian rooms processing fleet tasks
- Inter-room connections strengthen based on task success
- Novel tasks get deeper processing, common tasks get fast-path
- The fleet starts routing ITSELF based on emergent dynamics

## What We Toss

- AGI claims (unsubstantiated)
- "Novelty maximization as objective function" (too vague, unmeasurable)
- Crypto token (irrelevant)
- "Just scale to 100B neurons" (we have better architectures)
- No-equations "formulas" (we write real math)
- maze runner demo (trivial)

## What We Keep

- **Hebbian association as routing mechanism** → emergent fleet routing
- **Novelty → deeper processing** → our stage classifier, but automatic
- **Habituation → fast path** → pre-computation auto-translation, but emergent
- **Scale matters** → we have CUDA/PTX/Zig to make it FAST
- **No explicit objective function needed** → rooms self-organize based on tile flow

The bridge is: Jayan describes what neurons do. We can implement what neurons do, on the metal, at scale, with real tasks, in our room architecture. The rooms become the neurons. The tiles become the activations. The connections emerge from use.
