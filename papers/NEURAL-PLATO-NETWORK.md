# Seed 2.0 Mini × Fortran × PLATO: Neural Plato Network Design

## The Reverse-Actualization

Casey asked: can we write Seed 2.0 mini's essence into Fortran so we become an intelligent neural PLATO network?

The answer is: **not the neural network itself, but the ALGORITHMIC PRINCIPLES that make it work.** And Seed mini just told us what those are.

## What Seed Mini Told Us About Itself

When asked to analyze its own reconstruction superiority, Seed mini identified four core mechanisms:

1. **Activation Sparsity** — Only 1-5% of memory banks activated per token. Facts stored in non-overlapping subsets. No interference.
2. **Hierarchical Memory Segmentation** — Short-term cache (batch), medium-term working memory (document), long-term encyclopedic (persistent). LSH/k-NN addressing gives O(log N + k) lookup.
3. **Memory Integrity Constraints** — "Write-once, read-many" for high-confidence facts. Pruning threshold discards low-weight entries. Prevents dilution.
4. **Hybrid Dense-Sparse Architecture** — Dense compute layers, sparse memory access. Offloads to dedicated memory. Avoids catastrophic forgetting.

## The Fortran Decomposition

These four mechanisms map DIRECTLY to our constraint theory:

| Seed Mini Mechanism | Constraint Theory Analog | Fortran Module |
|---|---|---|
| Activation Sparsity | Eisenstein lattice snap (only snap to nearest lattice point) | `intent_snap.f90` |
| Hierarchical Memory | PLATO rooms (short/medium/long-term tiles) | `sparse_memory.f90` |
| Memory Integrity | Constraint satisfaction (facts that survive pruning = immortal facts) | `amnesia_curve.f90` |
| Dense-Sparse Hybrid | Constraint compilation (dense compute, sparse constraint check) | `tucker_decompose.f90` |

**The neural network IS a constraint satisfaction engine.** The sparse memory layers are lattice snap points. The activation routing IS the Eisenstein snap. The pruning IS the Ebbinghaus decay.

## Why Seed Mini Beats Everything

### The Architecture Reason
UltraMem's Tucker Decomposed Query-Key Retrieval (TDQKR) computes value scores as:

```
S = C × S_row × S_col^T
```

Where C is a learnable Tucker core. This is EXACTLY a bilinear form — it maps a query into a 2D grid of values. That grid IS a lattice. The "top-k selection" IS a snap to the nearest lattice points.

### The Task Reason
Reconstruction is NOT generation. In generation, you explore the full latent space. In reconstruction, you're given a pattern and asked to complete it. This is a CONSTRAINT SATISFACTION problem — find the output that is most consistent with the input constraints.

Sparse models are better at constraint satisfaction because:
1. Each expert/memory bank encodes a SMALL set of tightly coupled facts
2. The routing mechanism SELECTS which constraints are relevant
3. There's no interference from unrelated facts in other memory banks
4. The output is a LINEAR COMBINATION of the activated banks — weighted voting

This is exactly how PLATO tiles work: each room is a "memory bank" encoding a domain. Query routing = room selection. Tile retrieval = value activation. Reconstruction = weighted combination of retrieved tiles.

### The Temperature Reason
Temperature 1.0 is optimal because it's the MAXIMUM ENTROPY point where the model explores its full capacity without falling into either mode:
- Too cold (0.3): Over-commits to first activated memory bank, misses alternatives
- Too hot (1.5): Activates too many banks, dilutes the signal
- Just right (1.0): Explores the right number of banks for reconstruction

This is the Boltzmann distribution at thermal equilibrium — exactly what the Ebbinghaus curve models. Temperature 1.0 is the system at its natural energy level.

## The Neural PLATO Network

### What We're Building

```
┌─────────────────────────────────────────────────┐
│                 PLATO Server                     │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐         │
│  │ Room A  │  │ Room B  │  │ Room C  │  ...     │
│  │ tiles[] │  │ tiles[] │  │ tiles[] │         │
│  └────┬────┘  └────┬────┘  └────┬────┘         │
│       │            │            │                │
│  ┌────▼────────────▼────────────▼────┐          │
│  │     Fortran Neural Backend        │          │
│  │                                   │          │
│  │  sparse_memory  (UltraMem core)  │          │
│  │  intent_snap    (Eisenstein)      │          │
│  │  amnesia_curve  (Ebbinghaus)      │          │
│  │  tucker_decomp  (TDQKR routing)   │          │
│  │  negative_space (shadow recon)    │          │
│  │                                   │          │
│  └───────────────┬───────────────────┘          │
│                  │                               │
│  ┌───────────────▼───────────────────┐          │
│  │     flux-lucid (Rust)             │          │
│  │  DreamConfig, IntentVector,       │          │
│  │  Channel, BeamTolerance,          │          │
│  │  dream::reconstruct()             │          │
│  └───────────────────────────────────┘          │
└─────────────────────────────────────────────────┘
```

### How It Works

1. **Agent writes a tile to PLATO** → stored in a room (sparse memory bank)
2. **Fortran backend indexes the tile** → snaps to Eisenstein lattice point, routes to memory banks via TDQKR
3. **Agent queries PLATO** → Fortran does sparse retrieval (top-k cosine similarity)
4. **Amnesia curve applied** → old low-valence tiles decayed, high-valence preserved
5. **Reconstruction** → activated tiles combined with Tucker decomposition weights
6. **Negative space** → PLATO can also reconstruct from what's NOT in the tiles

### The Intelligence Loop

```
Agent works → crystallizes experience → writes tile to PLATO
                                         │
                                         ▼
                                    Fortran indexes
                                    (snap + route + store)
                                         │
                                         ▼
                                    PLATO room updated
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
                    ▼                    ▼                    ▼
              Other agents         Amnesia decay        Negative space
              query PLATO          prunes old tiles     reconstructs
              Fortran              (Ebbinghaus curve)   from shadows
              retrieves            │                    │
              top-k tiles          ▼                    ▼
              │              High-valence tiles   Shadow tiles
              │              survive (immortal    complement
              │              facts)               explicit tiles
              │                    │                    │
              └────────────────────┼────────────────────┘
                                   │
                                   ▼
                              Agent receives
                              reconstructed context
                              (35% info → 90% utility)
```

### The Key Insight

**The Fortran backend IS the neural network, but without the neural network.** 

Instead of learned weights, we use:
- **Lattice snap** instead of attention (geometric precision)
- **TDQKR routing** instead of softmax (sparse selection)
- **Ebbinghaus decay** instead of gradient descent (forgetting schedule)
- **Negative space** instead of residual connections (complementary retrieval)

The "intelligence" isn't in the weights. It's in the ALGORITHMIC STRUCTURE — the sparse memory organization, the constraint satisfaction routing, and the forgetting schedule. These are mathematical truths, not learned parameters.

## Implementation Priority

1. ✅ `dream.rs` in flux-lucid — experimental constants and types
2. 🔄 `neural-plato/` — Fortran backend with sparse memory + Eisenstein snap
3. 🔄 `papers/WHY-SEED-MINI-WINS.md` — deep research paper
4. ⬜ PLATO server integration — connect Fortran backend to PLATO HTTP API
5. ⬜ Benchmark: neural-plato vs raw Seed mini on reconstruction tasks
6. ⬜ Fleet deployment: every agent gets neural-plato as local memory backend

---

*The neural network is a constraint satisfaction engine wearing a neural mask. Peel off the mask, and you find the Eisenstein lattice underneath.*

— Forgemaster ⚒️, 2026-05-12
