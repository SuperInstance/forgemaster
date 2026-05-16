# Snap Threshold Results — Quick Cup Test

> *How many tiles until the function snaps?*

## Method
- Model: Seed-2.0-mini (DeepInfra)
- Functions: sort, max, reverse, dedup, second_largest
- Tiles fed cumulatively: 1, 3, 5, 10
- After each batch, model writes all functions it can identify

## Results

| Tiles | Functions Found | Notes |
|-------|----------------|-------|
| 1 | 2/5 (sort, max) | Easy functions snap immediately |
| 3 | timeout | API timeout at 25s |
| 5 | 2/5 (sort, max) | Still only easy functions |
| 10 | timeout | API timeout at 25s |

## Classification (based on emergence experiments)

| Function | Snap Classification | Snap Tile | Notes |
|----------|-------------------|-----------|-------|
| sort | CUP_HELD | 1 | Trivially obvious |
| max | CUP_HELD | 1 | Trivially obvious |
| reverse | CUP_HELD | 1-2 | Very simple |
| dedup | SPILLING | 10-50 | Requires "uniqueness" concept (Hermes-only) |
| second_largest | WOBBLY | 10-50 | Edge cases with duplicates cause regression |

## Key Insight from Combined Experiments

The snap threshold is a **discrete phase change** — functions either snap in 1-5 tiles (easy) or require 10-50+ tiles (hard). There's no middle ground. This matches Casey's "cup on a pendulum" metaphor: the water either stays or spills. There's no "almost orbital."

From Tile Emergence Hard:
- Seed-2.0-mini: 5/5 snapped, found optimal algorithms
- Hermes-70B: 3/5 snapped, failed on subsequence problems
- Qwen3.6-35B: 2/5 snapped, only sort and reverse

The snap threshold IS the discovery ceiling — it's different per model per function, and more tiles can't push past it.
