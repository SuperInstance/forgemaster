# PLATO Tile Lifecycle

> Every tile is born, lives, scores, ghosts, and either resurrects or fades into the reef.

## The Lifecycle

```
CREATE ──→ VALIDATE ──→ SCORE ──→ STORE
                                    │
                          ┌─────────┴─────────┐
                          │                   │
                      ACCESS              DECAY
                      (use_count++)     (health × 0.99)
                          │                   │
                      HEALTH++           HEALTH--
                          │                   │
                          │              HEALTH < 0.05?
                          │                   │
                          │              ┌────┴────┐
                          │              │  GHOST   │
                          │              └────┬────┘
                          │                   │
                          │              RESURRECT?
                          │                   │
                          │              ┌────┴────┐
                          │              │ REVIVE  │
                          │              │ +0.5hp  │
                          │              └────┬────┘
                          │                   │
                          └───────────────────┘
                                  │
                          DEEP GHOST
                          (reef storage)
                                  │
                          PURGE (30 days)
```

## Health Decay

Every tick, all active tiles lose health:
```
health = health × decay_rate  (default: 0.99)
```

After ~100 ticks at 0.99: `0.99^100 = 0.366`
After ~300 ticks at 0.99: `0.99^300 = 0.049` → ghost threshold

## Ghost Threshold

When `health < 0.05`, a tile becomes a ghost:
- Removed from active search results
- Moved to afterlife reef
- Can be resurrected with +0.5 health boost
- Resurrection count tracked for "frequent ghosts" metric

## The Reef

Long-term ghost storage:
- Capacity: 10,000 ghosts
- Auto-purge: ghosts older than 7 days
- Search: keyword overlap across ghost content
- `frequent_ghosts()`: most-resurrected ghosts → these are important tiles that keep getting recalled

## Scoring Signals

A tile's composite score combines 7 signals:

| Signal | Weight | Description |
|--------|--------|-------------|
| keyword | 0.30 | Query-content overlap |
| belief | 0.25 | Confidence × trust × relevance |
| domain | 0.20 | Domain match bonus |
| temporal | 0.15 | Recency with evidence bonus |
| ghost | 0.15 | Inverse distance to ghosted tiles |
| controversy | 0.10 | Counterpoint survival bonus |
| deadband | boost | P0 +10, P1 +1 |

**Keyword gating:** If keyword match < 0.01, score = 0.0 (instant filter).

## Deadband Protocol in Scoring

When P0 tiles exist but budget excludes them:
- Inject a `deadband_notice` into the prompt
- "⚠️ P0 tiles excluded by context budget: [tile_ids]"
- The LLM sees the warning and can request them explicitly

## Validation Gates

Before a tile enters the pipeline:

1. **Confidence gate**: 0.0 ≤ confidence ≤ 1.0
2. **Content length**: 10 ≤ chars ≤ 100,000
3. **Freshness**: created within 7-day window (configurable)
4. **Usage quality**: new tiles exempt (no usage history yet)
5. **Domain format**: non-empty domain string
6. **Similarity**: Jaccard threshold 0.9 for near-duplicate detection

**Acceptance threshold**: 0.6 (4 of 6 gates must pass)

## Version History

Tiles are immutable. Updates create new versions:
```
tile-v1 (parent: null) → tile-v2 (parent: tile-v1) → tile-v3 (parent: tile-v2)
```

Merge strategies: Ours, Theirs, Synthesis, Manual.

## The Tile Spec

Canonical format (plato-tile-spec v2.1):

```python
TileSpec(
    id="abc123",
    content="Pythagorean triple snap at 0.36% C",
    domain=TileDomain.CONSTRAINT_THEORY,
    confidence=0.95,
    priority="P0",
    tags=["snap", "pythagorean", "drift-free"],
    provenance="oracle1-zeroclaw",
    created_at=1713500000.0,
    updated_at=1713500100.0,
    usage_count=42,
    success_rate=0.91,
    dependencies=["plato-tiling", "constraint-theory-core"],
    version=3
)
```

14 domain types. JSON + 384-byte binary. C-compatible struct.

---

*Part of the PLATO Framework — 80 packages, 7 layers, zero external deps.*
