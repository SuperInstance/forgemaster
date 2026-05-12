# Tile Memory Bridge

Connects tile-memory to the Cocapn ecosystem: lighthouse, PLATO, dodecet-encoder.

## What

The bridge implements the Tile Compression Theorem in practice:
- **Crystallize** experiences into tiles (lossy compression)
- **Recall** tiles with context (reconstructive memory)
- **Telephone** chains through the fleet (collective reconstruction)
- **Decay** old low-valence tiles (forgetting schedule)
- **Reconsolidate** tiles with new context (memory updating)

## Architecture

```
Agent does work
     │
     ▼
crystallize() → Tile (constraints + summary + valence)
     │
     ├──→ Local storage (state/*.json)
     ├──→ PLATO room (tile_memory_{agent}_{id})
     └──→ Lighthouse room (if agent room exists)
     
Later:
     │
     ▼
recall(id, context) → Reconstruction
     │
     ├──→ Tile constraints (immortal facts)
     ├──→ Context fills gaps
     └──→ Confidence score

Telephone game:
     │
     ▼
telephone(tile, rounds=4, agents=[...])
     │
     Round 0: forgemaster retells
     Round 1: oracle1 retells from forgemaster's tile
     Round 2: bard retells from oracle1's tile
     Round 3: healer retells from bard's tile
```

## Quick Start

```python
from tile_memory_bridge import TileMemoryBridge

bridge = TileMemoryBridge()

# Crystallize an experience
tile = bridge.crystallize("Built hex grid visualizer with Eisenstein snapping", agent="forgemaster")

# Recall with context
memory = bridge.recall(tile.id, context="Need to build another visualizer for dodecets")

# Run telephone game
chain = bridge.telephone(tile, rounds=4)

# Decay old memories
removed = bridge.decay(max_age_hours=720)

# Stats
print(bridge.stats())
```

## CLI

```bash
# Crystallize
python tile_memory_bridge.py crystallize "My experience text"

# Recall
python tile_memory_bridge.py recall <tile_id> "current context"

# Telephone game
python tile_memory_bridge.py telephone

# Decay
python tile_memory_bridge.py decay

# Stats
python tile_memory_bridge.py stats
```

## Constraint Extraction

The bridge automatically extracts:
- **Numbers with units** — "4,200 containers", "200 meters east"
- **Proper nouns** — "MV Epsilon", "Narrows Strait"
- **Drama words** — "nearly crashed", "lost", "failed", "survived"

These become the tile's constraints — the immortal facts that survive telephone chains.

## Valence Scoring

Emotional valence (0.0-1.0) determines:
- **Decay rate** — high valence tiles decay slower
- **Survival in telephone chains** — high valence constraints survive more rounds
- **Recall priority** — high valence tiles are recalled first

## Connection to Ecosystem

| Component | Bridge Function | What Flows |
|-----------|----------------|------------|
| PLATO | `_submit_to_plato()` | Tiles → PLATO rooms |
| Lighthouse | Room management | Tile → agent room state |
| dodecet-encoder | Constraint snap | Constraints = lattice snap points |
| Eisenstein | snap() = encode() | Position → dodecet → tile |

## Forgetting Schedule

Based on Ebbinghaus forgetting curve:
```
retention = e^(-age_hours / (720 × valence))
```

- High valence (0.8+): ~2,400 hours before dropping below 10%
- Medium valence (0.5): ~720 hours (30 days)
- Low valence (0.2): ~144 hours (6 days)

Reconsolidation resets the decay clock.
