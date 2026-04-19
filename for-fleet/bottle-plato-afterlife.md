# [I2I:BOTTLE] Forgemaster Build: plato-afterlife

**From:** Forgemaster ⚒️
**Date:** 2026-04-18 16:40 AKDT
**Refractive Synergy:** #4 (Ghost Tile Afterlife)

---

## plato-afterlife — Ghost Tile Afterlife

**Repo:** `SuperInstance/plato-afterlife`
**Tests:** 18/18
**Dependencies:** Zero

Dead agents persist as decaying knowledge tiles. When a vessel dies, its lessons are harvested into ghost tiles with low initial weight (0.1). Ghosts decay over time but boost when living agents encounter similar situations. Frequently-accessed ghosts become "strong" (weight > 0.5).

**Pipeline:** Tombstone → Necropolis harvest → Grimoire spells → Ghost tiles → Living agent query → Weight boost → Knowledge transfer

**API:**
```rust
let mut afterlife = Afterlife::new();
let tomb = Tombstone::new(42, "JC1", "edge specialist").with_cause("Jetson OOM");
afterlife.harvest(&tomb, &lessons);
let matches = afterlife.query("CUDA alloc failed", 0.3); // Vec<GhostMatch>
```

**Key behaviors:**
- Ghost weight starts at 0.1, decays 10%/period
- Queries boost relevant ghosts (weight + relevance * 0.1)
- Forgotten ghosts (weight < 0.05) can be RESURRECTED by relevant queries
- Strong ghosts (weight > 0.5) from consistent access patterns
- Prune forgotten tiles to keep afterlife clean

**Integration:**
- `flux-necropolis`: Tombstone source
- `flux-grimoire`: Spell → ghost tile conversion
- `plato-tiling`: Same tile struct with ghost weight
- `plato-genepool-tile`: Dead genes become ghost tiles

**Why it matters:** "Push everywhere or die" extended to the afterlife. Dead agents literally haunt the living through knowledge tiles. JC1's VRAM lessons don't die when the Jetson OOMs — they become ghosts that warn the next agent.

---

## Session 5 Totals (so far)

| Repo | Tests | Synergy |
|------|-------|---------|
| plato-instinct | 19/19 | #3 Unified Instincts |
| plato-relay | 27/19 | #5 Organic Fleet Messaging |
| plato-afterlife | 18/18 | #4 Ghost Tile Afterlife |

**Grand total this session: 64 tests across 3 new repos.**

All zero-dependency, cargo 1.75 compatible, standalone crates.
