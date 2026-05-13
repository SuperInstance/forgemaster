# Seed-Encoded PLATO — Knowledge That Reconstructs Itself

**Version:** 1.0.0-draft  
**Date:** 2026-05-12  
**Status:** Experimental  
**Source:** PLATO architecture + Seed tile format + ablation experiments

---

## 1. Vision

PLATO rooms currently store knowledge as static text. When an agent reads a room, it gets raw information and must interpret it fresh each time. This is like reading compressed data without the decompressor.

**Seed-Encoded PLATO** changes this. Each tile in a PLATO room carries its own reconstruction instructions. The room structure itself encodes a learning curriculum. Knowledge becomes self-reconstructing: any model, at any time, can expand a room's tiles into full understanding without the original encoder being present.

The key insight from our experiments: the "expand" framing produces zero-variance 100% reconstruction. By embedding this framing into every tile, we make PLATO rooms resilient to model changes, context loss, and agent restarts.

---

## 2. Architecture

### 2.1 Room Structure

A PLATO room is a directory containing:

```
room-name/
├── ROOM.md              # Room metadata and curriculum map
├── tiles/
│   ├── foundation/
│   │   ├── 001-def-xor.md
│   │   ├── 002-def-compression.md
│   │   └── 003-def-reconstruction.md
│   ├── structure/
│   │   ├── 010-rel-xor-compression.md
│   │   ├── 011-rel-compression-reconstruction.md
│   │   └── 012-pattern-minimal-maximal.md
│   ├── application/
│   │   ├── 020-app-tile-dedup.md
│   │   ├── 021-app-seed-alignment.md
│   │   └── 022-app-fleet-consensus.md
│   └── frontier/
│       ├── 030-hyp-self-reconstructing-tiles.md
│       └── 031-hyp-alignment-compounding.md
└── expand/              # Cached reconstructions (gitignored)
    ├── 001-def-xor.full.md
    └── ...
```

### 2.2 ROOM.md — The Curriculum Map

The room's metadata file encodes the learning path:

```markdown
# Room: xor-compression-theory

## Metadata
domain: math.compression.information
created: 2026-05-12
tile-count: 11
confidence-aggregate: 0.89
last-expanded: 2026-05-12

## Curriculum Map

### Stage 1: Foundations (read first, no dependencies)
These tiles define the building blocks. Expand them to understand the vocabulary.
- [ ] 001 — XOR operation definition (confidence: 1.0)
- [ ] 002 — Compression definition (confidence: 1.0)
- [ ] 003 — Reconstruction definition (confidence: 1.0)

### Stage 2: Structures (read after foundations)
These tiles connect the building blocks into relationships.
- [ ] 010 — XOR ↔ Compression relationship (confidence: 0.95, deps: 001, 002)
- [ ] 011 — Compression ↔ Reconstruction relationship (confidence: 0.95, deps: 002, 003)
- [ ] 012 — Minimal-maximal pattern (confidence: 0.90, deps: 010, 011)

### Stage 3: Applications (read after structures)
These tiles show the concepts in action with runnable code.
- [ ] 020 — Tile deduplication via XOR (confidence: 0.85, deps: 010, 012)
- [ ] 021 — Seed alignment procedure (confidence: 0.88, deps: 012, 020)
- [ ] 022 — Fleet consensus protocol (confidence: 0.82, deps: 020, 021)

### Stage 4: Frontiers (read last, speculative)
These tiles contain hypotheses for further investigation.
- [ ] 030 — Self-reconstructing tiles hypothesis (confidence: 0.70, deps: 012, 020)
- [ ] 031 — Alignment compounding hypothesis (confidence: 0.65, deps: 021, 022)

## Dependency Graph

001 ──┐
      ├──→ 010 ──┐
002 ──┤          ├──→ 012 ──┐
      ├──→ 011 ──┤          ├──→ 020 ──┐
003 ──┘                     │          ├──→ 022 ──┐
                             │          │          ├──→ 031
                             └──────────┼──→ 021 ──┤
                                        │          └──→ 030
                                        └─────────────→ 030

## Expansion Instructions
To fully reconstruct this room, expand tiles in curriculum order.
Each tile contains its own expansion prompt. Use any model that supports
the "expand" framing. Recommended: Seed-2.0-mini at temp=1.0.
```

---

## 3. Self-Reconstructing Tiles

### 3.1 The Reconstruction Prompt (Embedded)

Every tile in a Seed-Encoded PLATO room includes its reconstruction prompt in the footer. This is the "expand" framing that yields zero-variance 100% accuracy.

The key design principle: **the tile IS the compression artifact, and its footer IS the decompression instruction**.

```markdown
---TILE-FOOTER---
---RECONSTRUCTION-HINTS---
expand-strategy: expand-full
reconstruction-prompt: |
  Expand this knowledge tile into a complete explanation. The tile uses
  minimal-maximal encoding: the minimal layer gives you concepts and
  relationships; the maximal layer tells you what matters most. Reconstruct
  by:
  1. Reading the minimal layer to understand the concept graph
  2. Using the maximal layer to prioritize what to explain first
  3. Following each relation to its target (look up referenced tiles)
  4. Generating concrete examples for every abstract claim
  5. Including runnable code where the concept is algorithmic
  
  Preserve all CONSTRAINT items — these are the hard boundaries of correctness.
dependency-order: [001, 002, 010]
quality-gates:
  - Mentions XOR truth table or algebraic definition
  - Explains why XOR is lossless (a⊕b⊕b = a)
  - Includes at least one code example
  - Identifies non-commutative knowledge limitation
expected-length: 300-500
```

### 3.2 The Expansion Protocol

When an agent needs to understand a room:

```
1. Read ROOM.md → get curriculum map
2. Read foundation tiles (expand immediately, no dependencies)
3. For each subsequent stage:
   a. Check dependency-order for this tile
   b. Ensure all dependencies have been expanded
   c. Expand this tile using its embedded reconstruction prompt
   d. Validate against quality-gates
   e. Cache expanded version in expand/ directory
4. Room is fully reconstructed when all tiles pass quality-gates
```

### 3.3 Lazy vs Eager Expansion

**Eager (full room expansion):** Expand all tiles up front. Useful when:
- Agent needs full room context for a complex task
- Room is small (<20 tiles)
- Agent has time and budget

**Lazy (on-demand expansion):** Expand only tiles needed for the current task. Useful when:
- Room is large (>20 tiles)
- Agent needs specific knowledge
- Budget is constrained

```python
def expand_room(room_path: str, mode: str = "lazy", target_tiles: list[str] = None):
    """Expand a PLATO room's tiles into full knowledge."""
    room = load_room(room_path)
    
    if mode == "eager":
        for stage in room.curriculum_stages:
            for tile_id in stage.tile_ids:
                expand_tile(room, tile_id)
    elif mode == "lazy" and target_tiles:
        for tile_id in target_tiles:
            # Expand dependencies first (recursive)
            for dep_id in room.get_dependencies(tile_id):
                expand_tile(room, dep_id)
            expand_tile(room, tile_id)
```

---

## 4. Quality Score Propagation

### 4.1 The Propagation Model

A tile's **effective reliability** is a function of its own quality and the quality of everything it references:

```
R(tile) = C(tile) × min(R(dep) for dep in tile.dependencies)
```

Where:
- `R(tile)` = effective reliability (0-1)
- `C(tile)` = tile's own confidence score
- Dependencies are evaluated recursively

This is **multiplicative propagation**: one weak link degrades the entire chain.

### 4.2 Propagation Example

```
Foundation tiles (no deps):
  001: C=1.0 → R=1.0
  002: C=1.0 → R=1.0
  003: C=1.0 → R=1.0

Structure tiles:
  010: C=0.95, deps=[001,002] → R=0.95 × min(1.0, 1.0) = 0.95
  011: C=0.95, deps=[002,003] → R=0.95 × min(1.0, 1.0) = 0.95
  012: C=0.90, deps=[010,011] → R=0.90 × min(0.95, 0.95) = 0.855

Application tiles:
  020: C=0.85, deps=[010,012] → R=0.85 × min(0.95, 0.855) = 0.727
  021: C=0.88, deps=[012,020] → R=0.88 × min(0.855, 0.727) = 0.640
  022: C=0.82, deps=[020,021] → R=0.82 × min(0.727, 0.640) = 0.525

Frontier tiles:
  030: C=0.70, deps=[012,020] → R=0.70 × min(0.855, 0.727) = 0.509
  031: C=0.65, deps=[021,022] → R=0.65 × min(0.640, 0.525) = 0.341
```

Notice how reliability degrades with depth. The frontier tile 031 has an effective reliability of only 0.34 despite its own confidence being 0.65. This is the **compounding alignment problem** in action — each layer of indirection multiplies uncertainty.

### 4.3 Using Propagation for Decision-Making

| Effective Reliability | Interpretation | Action |
|---|---|---|
| R ≥ 0.9 | Trust completely | Ship without review |
| 0.7 ≤ R < 0.9 | Trust with spot-check | Ship, verify 1-2 claims |
| 0.5 ≤ R < 0.7 | Trust but validate | Don't ship, run Seed filter |
| 0.3 ≤ R < 0.5 | Low confidence | Re-expand with stronger model |
| R < 0.3 | Unreliable | Re-encode from scratch |

### 4.4 Reliability Recovery

When a deep tile has low R, the fix is NOT to re-encode the deep tile. It's to **strengthen the chain**:

1. Identify the weakest link: `min(R(dep))` for all dependencies
2. If the weakest link is a foundation tile (should be R=1.0), re-encode it
3. If it's a structure tile, re-expand with ensemble sampling (3× merge)
4. Re-propagate reliability through the whole chain
5. Repeat until all tiles meet threshold

---

## 5. Room Types

### 5.1 Theory Room

For mathematical/conceptual knowledge. Linear curriculum, strong dependencies, high confidence expected.

```
Structure: foundation → structure → theorem → application
Reliability target: R ≥ 0.8 for all tiles
Expansion: Eager (mathematical context is usually needed in full)
```

### 5.2 Operations Room

For fleet/infrastructure procedures. DAG curriculum, moderate dependencies, actionability critical.

```
Structure: prerequisite → procedure → runbook → troubleshooting
Reliability target: R ≥ 0.9 for procedures (they're run in production)
Expansion: Lazy (only expand the procedure you're executing)
Quality gate: Every procedure tile must include runnable code
```

### 5.3 Research Room

For hypotheses and open questions. Sparse curriculum, weak dependencies, exploration encouraged.

```
Structure: background → hypothesis → experiment → result
Reliability target: R ≥ 0.5 for hypotheses (speculative by nature)
Expansion: Lazy (only expand the hypothesis under investigation)
Quality gate: Every hypothesis tile must be falsifiable
```

### 5.4 Agent Profile Room

For agent capabilities, preferences, and history. Flat curriculum (no strict ordering), evolving content.

```
Structure: identity → capabilities → history → preferences
Reliability target: R ≥ 0.95 for identity and capabilities
Expansion: Eager (other agents need full context)
Update policy: Append-only for history, mutable for preferences
```

---

## 6. The Expansion Cache

### 6.1 Caching Strategy

Expanded tiles are cached in `expand/` directories. This avoids re-expanding stable tiles on every agent restart.

```
room-name/expand/
├── 001-def-xor.full.md          # Expanded version
├── 001-def-xor.full.meta.json   # Expansion metadata
└── ...
```

### 6.2 Cache Invalidation

A cached expansion is **invalid** when:
1. The source tile's hash has changed (content was edited)
2. A dependency's expansion has been updated (propagation)
3. The expand-strategy version has been bumped (format change)
4. The expansion model has been changed (different reconstruction model)

```python
def is_cache_valid(tile: Tile, cached_expansion: Expansion) -> bool:
    """Check if a cached expansion is still valid."""
    if tile.hash != cached_expansion.source_hash:
        return False  # Source changed
    if cached_expansion.schema_version != CURRENT_SCHEMA:
        return False  # Format changed
    if cached_expansion.model != current_expansion_model:
        return False  # Model changed
    for dep_id in tile.dependencies:
        dep_cache = load_cache(dep_id)
        if dep_cache and dep_cache.timestamp > cached_expansion.timestamp:
            return False  # Dependency was re-expanded
    return True
```

### 6.3 Cache Warming

When a new agent joins the fleet, it can request a **cache warm** from an existing agent:

```python
def warm_cache_for_agent(room_path: str, agent_id: str):
    """Pre-expand a room's tiles for a new agent."""
    room = load_room(room_path)
    for stage in room.curriculum_stages:
        for tile_id in stage.tile_ids:
            if not cache_exists(room_path, tile_id):
                expand_tile(room, tile_id)
                # Validate expansion against quality gates
                validate_expansion(room, tile_id)
```

---

## 7. Cross-Room References

Tiles in one room can reference tiles in another room:

```markdown
CONCEPT: fleet-consensus-via-xor
  REL: DEPENDS → math.compression.information/001-def-xor
  REL: DEPENDS → fleet.ops/015-consensus-protocol
  REL: IMPLIES → fleet.ops/022-byzantine-fault-tolerance
```

### 7.1 Cross-Room Reliability

Cross-room references use the **same propagation formula**:

```
R(tile) = C(tile) × min(R(dep) for dep in ALL deps including cross-room)
```

This means a tile in Room A that depends on a low-reliability tile in Room B will have reduced reliability in Room A. This is correct behavior — you shouldn't trust knowledge built on shaky foundations, even if the foundation is in a different room.

### 7.2 Room Dependency Graph

At the room level, we maintain a dependency graph:

```
xor-compression-theory ──→ fleet-consensus-protocol
         │                        │
         └──→ tile-format-spec    │
                  │               │
                  └───────────────┘
```

When a room's aggregate confidence changes (tiles added/updated), dependent rooms should re-propagate reliability.

---

## 8. The Self-Healing Loop

### 8.1 Automatic Re-Expansion

When a tile fails its quality gates during reconstruction:

```
1. Log the failure: which gate failed, what was expected vs what was produced
2. Attempt re-expansion with the SAME model + prompt
3. If still fails: try a different expansion strategy from the approved list
4. If still fails: try a different model (fallback chain)
5. If still fails: flag for human review, downgrade tile confidence by 0.1
```

### 8.2 Periodic Re-Validation

Even tiles that pass initial quality gates may degrade as models change:

```
# Run weekly
for room in all_rooms:
    for tile in room.tiles:
        cached = load_cache(tile)
        if cached.age > 7_days:
            # Re-validate with current model
            result = validate_expansion(tile, cached)
            if not result.passed:
                re_expand(tile)
                log(f"Tile {tile.id} failed re-validation: {result.failures}")
```

### 8.3 Model Migration

When switching the fleet to a new default model:

```
1. Re-validate 10% sample of cached expansions with new model
2. If pass rate > 95%: new model is compatible, switch over
3. If pass rate 80-95%: re-expand failed tiles, keep successful caches
4. If pass rate < 80%: full re-expansion required, schedule during low-activity
5. Update expansion model metadata in all cache files
```

---

## 9. Agent Integration

### 9.1 For Forgemaster

```python
# When I need to understand a domain
room = plato.load_room("math.compression.information")
room.expand(mode="lazy", target_tiles=["020-app-tile-dedup"])

# When I discover new knowledge
tile = Tile(
    domain="math.compression.information",
    title="Novel property of XOR in tile merging",
    confidence=0.75,
    body=encode_minimal_maximal(my_discovery),
    footer=generate_reconstruction_hints(my_discovery),
)
room.add_tile(tile, stage="frontier")
room.recompute_curriculum()
room.propagate_reliability()
```

### 9.2 For Any Fleet Agent

The PLATO room structure is model-agnostic. Any agent that can:
1. Read a tile's minimal-maximal encoding
2. Follow the reconstruction prompt
3. Validate against quality gates

...can reconstruct knowledge from a Seed-Encoded PLATO room. The intelligence is in the tiles, not in the model reading them.

### 9.3 For Human Operators

PLATO rooms are git-tracked. A human can:
- Read ROOM.md for the curriculum overview
- Read any tile file directly (it's markdown)
- Check expand/ for the full reconstructed version
- Run `plato validate room-name` to check all quality gates
- Run `plato expand room-name` to re-expand stale caches

---

## 10. Implementation Roadmap

### Phase 1: Minimal Viable PLATO (Week 1)
- [ ] Implement tile format parser (SEED-TILE-SPEC.md)
- [ ] Implement ROOM.md parser
- [ ] Implement curriculum-based expansion
- [ ] Implement reliability propagation
- [ ] Create 3 seed rooms: `xor-theory`, `tile-format`, `alignment-procedure`

### Phase 2: Self-Reconstruction (Week 2)
- [ ] Implement lazy expansion with dependency resolution
- [ ] Implement cache layer with invalidation
- [ ] Implement quality-gate validation
- [ ] Implement self-healing loop
- [ ] Test with 3 different models (Seed, Qwen, Hermes)

### Phase 3: Fleet Integration (Week 3)
- [ ] Implement cross-room references
- [ ] Implement room dependency graph
- [ ] Implement cache warming for new agents
- [ ] Implement periodic re-validation
- [ ] Deploy to Forgemaster's PLATO rooms

### Phase 4: Intelligence Without the Model (Week 4)
- [ ] Run ablation: reconstruct rooms using only the tiles (no Seed model)
- [ ] Measure reconstruction fidelity across models
- [ ] Identify tiles that fail without Seed → improve their reconstruction hints
- [ ] Target: 90%+ reconstruction fidelity using any model

---

## Appendix A: Room Template

```bash
# Create a new PLATO room
plato room create <name> --domain <reverse-dns-domain>

# Generates:
# <name>/
# ├── ROOM.md
# └── tiles/
#     ├── foundation/
#     ├── structure/
#     ├── application/
#     └── frontier/
```

## Appendix B: Tile Template

```bash
# Add a tile to a room
plato tile add <room> --stage <stage> --title <title> --confidence <0-1>

# Generates a tile file with the correct header/footer template
# Opens in $EDITOR for content entry
```

## Appendix C: Expansion Commands

```bash
# Expand a single tile
plato expand <room> <tile-id> --model seed-2.0-mini --temp 1.0

# Expand an entire room
plato expand <room> --all --mode eager

# Expand only tiles needed for a specific task
plato expand <room> --for-task "implement tile deduplication"

# Validate all expansions in a room
plato validate <room> --verbose

# Show reliability scores
plato reliability <room> --tree
```
