# Fleet Dependency Graph — Updated 2026-04-19

## New Crates This Session

| Crate | Tests | Layer | Connects To |
|-------|-------|-------|-------------|
| plato-tile-pipeline | 14 | Facade | validate, score, store, search, rank → all tile lifecycle |
| plato-tile-api | 15 | API | same as pipeline, wire-compatible with port 8847 |
| plato-papers | — | Docs | citable research output |

## Running Totals

- **74 PLATO crates** (72 Rust + 1 C + 1 Python)
- **~1,698 tests**
- **7 architectural layers**
- **Fleet tile count:** ~11,000+

## The "Playset" Layer (NEW)

`plato-tile-pipeline` and `plato-tile-api` sit ABOVE the 7-layer stack.
They are the pre-assembled playset — one call does everything.
The 72 individual crates are the raw Legos underneath.

```
                    ┌─────────────────────┐
                    │   plato-cli (HN)    │  ← Download, run, see it work
                    ├─────────────────────┤
                    │ plato-tile-pipeline │  ← One-call: process(tiles, query)
                    │ plato-tile-api      │  ← Wire-compatible with port 8847
                    ├─────────────────────┤
                    │  72 Legos below     │  ← Snap together as needed
                    └─────────────────────┘
```
