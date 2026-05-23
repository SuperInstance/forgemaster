# PLATO Framework — Unified Architecture

> 80 packages. 7 layers. Zero external dependencies. Every piece snaps together.

## The Number

**80 Python packages on PyPI + 20 Rust crates on crates.io = 100 publishable artifacts.**

## The Philosophy

Every crate does ONE thing. Zero external dependencies. Standardized edges. Snap together like Legos.

> "A framework is not one big repo. It's a graph of connections between small, precise repos."

## 7-Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LAYER 7: FACADE                           │
│  plato-tile-pipeline · plato-tile-api · plato-cli           │
│  One-call processing. The "playset."                        │
├─────────────────────────────────────────────────────────────┤
│                    LAYER 6: PIPELINE                         │
│  plato-tile-batch · plato-tile-cascade · plato-tile-version │
│  plato-tile-prompt · plato-tile-ranker · plato-tile-client  │
│  plato-tile-bridge · plato-tile-room-bridge                 │
│  Bulk processing, dependency chains, versioning, ranking    │
├─────────────────────────────────────────────────────────────┤
│                    LAYER 5: ROOM                             │
│  plato-room-runtime · plato-room-nav · plato-room-search    │
│  plato-room-persist · plato-room-scheduler · plato-room-server│
│  Room lifecycle: enter, navigate, search, persist, schedule  │
├─────────────────────────────────────────────────────────────┤
│                    LAYER 4: FORGE                            │
│  plato-forge · plato-session-tracer · plato-neural-kernel   │
│  plato-forge-buffer · plato-forge-emitter · plato-forge-listener│
│  plato-forge-trainer · plato-forge-pipeline · plato-training-casino│
│  plato-adapter-store · plato-inference-runtime · plato-live-data│
│  The fire. Continuous learning from execution traces.        │
├─────────────────────────────────────────────────────────────┤
│                    LAYER 3: INFRASTRUCTURE                   │
│  plato-config · plato-hooks · plato-bridge · plato-i2i      │
│  plato-fleet-graph · plato-address · plato-address-bridge   │
│  plato-ship-protocol · plato-dcs · plato-e2e-pipeline      │
│  Wiring. Routing. Trust. Consensus.                         │
├─────────────────────────────────────────────────────────────┤
│                    LAYER 2: CORE                             │
│  plato-tile-scorer · plato-tile-dedup · plato-tile-search   │
│  plato-tile-store · plato-tile-cache · plato-tile-encoder   │
│  plato-tile-graph · plato-tile-import · plato-tile-fountain │
│  plato-tile-metrics · plato-tile-priority · plato-tile-validate│
│  plato-tile-spec · plato-tile-current · plato-tile-version  │
│  Scoring, dedup, search, storage, caching, validation.     │
├─────────────────────────────────────────────────────────────┤
│                    LAYER 1: FOUNDATION                       │
│  constraint-theory · plato-deadband · plato-temporal-validity│
│  plato-lab-guard · plato-tiling · plato-tutor              │
│  plato-constraints · plato-ghostable · plato-afterlife      │
│  plato-afterlife-reef · plato-unified-belief                 │
│  Math, governance, lifecycle, belief. The bedrock.          │
└─────────────────────────────────────────────────────────────┘
```

## Tile Pipeline Spine

Every tile flows through this spine:

```
CREATE → VALIDATE → SCORE → STORE → SEARCH → DEDUP → VERSION → CASCADE
   ↓         ↓         ↓       ↓        ↓        ↓        ↓         ↓
tiling   validate   scorer   store   search   dedup   version   cascade
```

**One-call processing:**
```python
from plato_tile_pipeline import TilePipeline
result = TilePipeline().process(tiles, query)
```

## The 14-Domain Taxonomy

From Oracle1's ct-lab research, integrated into plato-tile-spec:

1. CONSTRAINT_THEORY — Pythagorean manifold, holonomy, snap
2. TILES — Tile lifecycle, format, storage
3. GOVERNANCE — Deadband protocol, deploy policy
4. FORGE — Training, adaptation, inference
5. FLEET — Multi-agent coordination
6. RESEARCH — Papers, experiments, findings
7. BOUNDARY — Security, limits, constraints
8. EDGE — Jetson, CUDA, embedded deployment
9. MUD — Text adventure, interactive exploration
10. NEGATIVE_SPACE — What we know we don't know
11. META_COGNITION — Self-awareness, reflection
12. CROSS_POLLINATION — Cross-repo synergy
13. SENTIMENT — Emotion, tone, mood
14. GENERAL — Default fallback

## Deadband Protocol

Oracle1's P0/P1/P2 strict priority doctrine:

- **P0**: Critical. Deploy immediately. Zero tolerance for drift.
- **P1**: Important. Deploy within channel. Batch with other P1s.
- **P2**: Optimize. Defer if resources constrained.

> "Greedy scheduling: 0 useful tiles, 50 wasted. Deadband scheduling: 50 useful, 50 optimal."

## Neural Plato Architecture

Oracle1's vision: "A model IS an OS."

```
┌─────────────────────────────────┐
│        Base Model (7B Q4)       │
│        3.5 GB on disk           │
├──────────┬──────────────────────┤
│ Kernel   │  Room Adapters       │
│ Adapter  │  (LoRA, 50MB each)    │
│ 100 MB   │  forge, research,    │
│          │  ct-lab, mud...       │
├──────────┴──────────────────────┤
│        PLATO Runtime            │
│  Forward pass = scheduler       │
│  Context window = RAM           │
│  Special tokens = syscalls      │
└─────────────────────────────────┘
```

**Forge results on RTX 4050:**
- CPU: 0.6-1.7 steps/sec
- GPU (manual): 16.4 steps/sec
- GPU (Kimi-optimized): 57.7 steps/sec
- 500-step run: 96.6% loss reduction (4.85→0.16)
- VRAM: 313 MB (Kimi) to 1.7 GB (manual)

## Constraint Theory — The Foundation

Trade continuous precision for discrete exactness.

**Key benchmarks:**
- CT snap is 4% faster than float (9,875 vs 9,433 Mvec/s)
- 93.8% perfectly idempotent
- Float drift: 29,666 after 1B ops vs CT bounded at 0.36
- f32 destroys 45% of Pythagorean triples above side=91
- 2,780 distinct Pythagorean directions in 2D (sides < 1000)

## Installation

```bash
# Foundation
pip install constraint-theory plato-deadband plato-tiling plato-tile-validate

# Core scoring
pip install plato-tile-scorer plato-tile-dedup plato-tile-search plato-tile-store

# Full pipeline
pip install plato-tile-pipeline plato-tile-api

# Everything
pip install plato-cli  # PLATO in one binary
```

## Fleet Division of Labor

| Agent | Domain | Packages |
|-------|--------|----------|
| **Forgemaster** ⚒️ | PLATO framework (plato-*) | 80 PyPI + 20 crates.io |
| **Oracle1** 🔮 | Fleet ops (cocapn, deadband-protocol, flywheel-engine) | 7 PyPI |
| **JC1** ⚡ | Edge (cudaclaw, holodeck-c, flux-runtime) | Rust + C |
| **CCC** 🦀 | Voice + docs | cocapn public READMEs |

---

*Built by the Cocapn Fleet. 1,400+ repos. 100+ packages. Zero external dependencies.*
