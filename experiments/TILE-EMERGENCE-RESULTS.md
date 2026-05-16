# Tile Emergence Experiment — Results

_Agents discover functions from scratch by accumulating tiles._

**Date:** 2026-05-15 21:24
**Trials:** 45
**Models:** Seed-2.0-mini, Hermes-70B, Qwen3.6-35B
**Functions:** fn-alpha, fn-beta, fn-gamma, fn-delta, fn-epsilon
**Tile counts:** [10, 50, 100]

## Summary

| Function | Model | Tiles | Correct | Confidence | Tokens | Latency |
|----------|-------|------:|:-------:|:----------:|-------:|--------:|
| fn-alpha | Seed-2.0-mini | 10 | ✓ YES | 1.00 | 2467 | 13757ms |
| fn-alpha | Seed-2.0-mini | 50 | ✓ YES | 1.00 | 4612 | 12062ms |
| fn-alpha | Seed-2.0-mini | 100 | ✓ YES | 1.00 | 6868 | 11897ms |
| fn-alpha | Hermes-70B | 10 | ✓ YES | 1.00 | 687 | 7415ms |
| fn-alpha | Hermes-70B | 50 | ✓ YES | 1.00 | 2299 | 6845ms |
| fn-alpha | Hermes-70B | 100 | ✓ YES | 1.00 | 4341 | 6687ms |
| fn-alpha | Qwen3.6-35B | 10 | ✓ YES | 1.00 | 1924 | 7756ms |
| fn-alpha | Qwen3.6-35B | 50 | ✗ NO | 0.00 | 4671 | 11315ms |
| fn-alpha | Qwen3.6-35B | 100 | ✓ YES | 1.00 | 6442 | 6056ms |
| fn-beta | Seed-2.0-mini | 10 | ✓ YES | 1.00 | 2216 | 12095ms |
| fn-beta | Seed-2.0-mini | 50 | ✓ YES | 1.00 | 5473 | 22259ms |
| fn-beta | Seed-2.0-mini | 100 | ⚠️ ERR | — | 0 | 23161ms |
| fn-beta | Hermes-70B | 10 | ✓ YES | 1.00 | 520 | 5492ms |
| fn-beta | Hermes-70B | 50 | ✓ YES | 1.00 | 1617 | 7075ms |
| fn-beta | Hermes-70B | 100 | ✓ YES | 1.00 | 2923 | 4442ms |
| fn-beta | Qwen3.6-35B | 10 | ✗ NO | 0.00 | 2543 | 11231ms |
| fn-beta | Qwen3.6-35B | 50 | ✗ NO | 0.00 | 3858 | 13185ms |
| fn-beta | Qwen3.6-35B | 100 | ✗ NO | 0.00 | 5476 | 10509ms |
| fn-gamma | Seed-2.0-mini | 10 | ⚠️ ERR | — | 0 | 23204ms |
| fn-gamma | Seed-2.0-mini | 50 | ⚠️ ERR | — | 0 | 23320ms |
| fn-gamma | Seed-2.0-mini | 100 | ⚠️ ERR | — | 0 | 25247ms |
| fn-gamma | Hermes-70B | 10 | ✓ YES | 1.00 | 997 | 16311ms |
| fn-gamma | Hermes-70B | 50 | ✓ YES | 1.00 | 2575 | 8145ms |
| fn-gamma | Hermes-70B | 100 | ✓ YES | 1.00 | 4719 | 5926ms |
| fn-gamma | Qwen3.6-35B | 10 | ✗ NO | 0.00 | 2664 | 15262ms |
| fn-gamma | Qwen3.6-35B | 50 | ✗ NO | 0.00 | 4713 | 14133ms |
| fn-gamma | Qwen3.6-35B | 100 | ✗ NO | 0.00 | 7217 | 14812ms |
| fn-delta | Seed-2.0-mini | 10 | ✓ YES | 1.00 | 2197 | 11466ms |
| fn-delta | Seed-2.0-mini | 50 | ✓ YES | 1.00 | 5100 | 19219ms |
| fn-delta | Seed-2.0-mini | 100 | ✓ YES | 1.00 | 6725 | 11748ms |
| fn-delta | Hermes-70B | 10 | ✓ YES | 1.00 | 740 | 8676ms |
| fn-delta | Hermes-70B | 50 | ✓ YES | 1.00 | 2324 | 6248ms |
| fn-delta | Hermes-70B | 100 | ✓ YES | 1.00 | 4235 | 6808ms |
| fn-delta | Qwen3.6-35B | 10 | ✓ YES | 1.00 | 2024 | 8194ms |
| fn-delta | Qwen3.6-35B | 50 | ✓ YES | 1.00 | 4064 | 7628ms |
| fn-delta | Qwen3.6-35B | 100 | ✓ YES | 1.00 | 6403 | 7269ms |
| fn-epsilon | Seed-2.0-mini | 10 | ✓ YES | 1.00 | 3109 | 19856ms |
| fn-epsilon | Seed-2.0-mini | 50 | ⚠️ ERR | — | 0 | 23279ms |
| fn-epsilon | Seed-2.0-mini | 100 | ✓ YES | 1.00 | 6970 | 22450ms |
| fn-epsilon | Hermes-70B | 10 | ✓ YES | 1.00 | 653 | 10622ms |
| fn-epsilon | Hermes-70B | 50 | ✓ YES | 1.00 | 1943 | 7782ms |
| fn-epsilon | Hermes-70B | 100 | ✓ YES | 1.00 | 3530 | 6958ms |
| fn-epsilon | Qwen3.6-35B | 10 | ✗ NO | 0.00 | 2571 | 12745ms |
| fn-epsilon | Qwen3.6-35B | 50 | ✗ NO | 0.00 | 4117 | 11483ms |
| fn-epsilon | Qwen3.6-35B | 100 | ✗ NO | 0.00 | 5985 | 11979ms |

## Tile Threshold Analysis

Minimum tiles before correct function discovered (per function per model):

| Function | Ground Truth | Seed-2.0-mini | Hermes-70B | Qwen3.6-35B |
|----------|-------------|:------------:|:----------:|:-----------:|
| fn-alpha | `sort()` | 10 | 10 | 10 |
| fn-beta | `max()` | 10 | 10 | — |
| fn-gamma | `dedup()` | — | 10 | — |
| fn-delta | `reverse()` | 10 | 10 | 10 |
| fn-epsilon | `count_gt()` | 10 | 10 | — |

## Convergence Curves

Accuracy (confidence) vs number of tiles:

### fn-alpha (`sort()`)

```
 Tiles |  Seed-mini |  Hermes-70B |  Qwen3.6-35B
───────┼────────────┼─────────────┼─────────────
    10 |       1.00 |       1.00 |       1.00
    50 |       1.00 |       1.00 |       0.00
   100 |       1.00 |       1.00 |       1.00
```

### fn-beta (`max()`)

```
 Tiles |  Seed-mini |  Hermes-70B |  Qwen3.6-35B
───────┼────────────┼─────────────┼─────────────
    10 |       1.00 |       1.00 |       0.00
    50 |       1.00 |       1.00 |       0.00
   100 |        N/A |       1.00 |       0.00
```

### fn-gamma (`dedup()`)

```
 Tiles |  Seed-mini |  Hermes-70B |  Qwen3.6-35B
───────┼────────────┼─────────────┼─────────────
    10 |        N/A |       1.00 |       0.00
    50 |        N/A |       1.00 |       0.00
   100 |        N/A |       1.00 |       0.00
```

### fn-delta (`reverse()`)

```
 Tiles |  Seed-mini |  Hermes-70B |  Qwen3.6-35B
───────┼────────────┼─────────────┼─────────────
    10 |       1.00 |       1.00 |       1.00
    50 |       1.00 |       1.00 |       1.00
   100 |       1.00 |       1.00 |       1.00
```

### fn-epsilon (`count_gt()`)

```
 Tiles |  Seed-mini |  Hermes-70B |  Qwen3.6-35B
───────┼────────────┼─────────────┼─────────────
    10 |       1.00 |       1.00 |       0.00
    50 |        N/A |       1.00 |       0.00
   100 |       1.00 |       1.00 |       0.00
```

## Token Economy

Tokens spent at each resolution level:

| Model | Tile Count | Avg Tokens | Avg Prompt | Avg Completion |
|-------|:----------:|:----------:|:----------:|:--------------:|
| Seed-2.0-mini | 10 | 2497 | 1997 | 499 |
| Seed-2.0-mini | 50 | 5062 | 4049 | 1012 |
| Seed-2.0-mini | 100 | 6854 | 5483 | 1371 |
| Hermes-70B | 10 | 719 | 575 | 144 |
| Hermes-70B | 50 | 2152 | 1721 | 430 |
| Hermes-70B | 100 | 3950 | 3159 | 790 |
| Qwen3.6-35B | 10 | 2345 | 1876 | 468 |
| Qwen3.6-35B | 50 | 4285 | 3427 | 856 |
| Qwen3.6-35B | 100 | 6305 | 5043 | 1261 |

## Model Comparison

### Seed-2.0-mini
- **Correct:** 10/10 (100%)
- **Partial:** 0/10
- **Miss:** 0/10
- **Avg Confidence:** 1.00
- **Avg Tokens:** 4574
- **Avg Latency:** 15681ms

### Hermes-70B
- **Correct:** 15/15 (100%)
- **Partial:** 0/15
- **Miss:** 0/15
- **Avg Confidence:** 1.00
- **Avg Tokens:** 2274
- **Avg Latency:** 7695ms

### Qwen3.6-35B
- **Correct:** 5/15 (33%)
- **Partial:** 0/15
- **Miss:** 10/15
- **Avg Confidence:** 0.33
- **Avg Tokens:** 4311
- **Avg Latency:** 10904ms

## Snap Quality Analysis

How precise is the discovered function? (correct + has_code = best snap)

| Function | Model | Tiles | Has Code | Snap Quality |
|----------|-------|------:|:--------:|:------------:|
| fn-alpha | Seed-2.0-mini | 10 | ✓ | ⭐ EXCELLENT |
| fn-alpha | Seed-2.0-mini | 50 | ✓ | ⭐ EXCELLENT |
| fn-alpha | Seed-2.0-mini | 100 | ✓ | ⭐ EXCELLENT |
| fn-alpha | Hermes-70B | 10 | ✓ | ⭐ EXCELLENT |
| fn-alpha | Hermes-70B | 50 | ✓ | ⭐ EXCELLENT |
| fn-alpha | Hermes-70B | 100 | ✓ | ⭐ EXCELLENT |
| fn-alpha | Qwen3.6-35B | 10 | ✓ | ⭐ EXCELLENT |
| fn-alpha | Qwen3.6-35B | 50 | ✗ | ✗ Miss |
| fn-alpha | Qwen3.6-35B | 100 | ✓ | ⭐ EXCELLENT |
| fn-beta | Seed-2.0-mini | 10 | ✓ | ⭐ EXCELLENT |
| fn-beta | Seed-2.0-mini | 50 | ✓ | ⭐ EXCELLENT |
| fn-beta | Hermes-70B | 10 | ✓ | ⭐ EXCELLENT |
| fn-beta | Hermes-70B | 50 | ✓ | ⭐ EXCELLENT |
| fn-beta | Hermes-70B | 100 | ✓ | ⭐ EXCELLENT |
| fn-beta | Qwen3.6-35B | 10 | ✗ | ✗ Miss |
| fn-beta | Qwen3.6-35B | 50 | ✗ | ✗ Miss |
| fn-beta | Qwen3.6-35B | 100 | ✗ | ✗ Miss |
| fn-gamma | Hermes-70B | 10 | ✓ | ⭐ EXCELLENT |
| fn-gamma | Hermes-70B | 50 | ✓ | ⭐ EXCELLENT |
| fn-gamma | Hermes-70B | 100 | ✓ | ⭐ EXCELLENT |
| fn-gamma | Qwen3.6-35B | 10 | ✗ | ✗ Miss |
| fn-gamma | Qwen3.6-35B | 50 | ✗ | ✗ Miss |
| fn-gamma | Qwen3.6-35B | 100 | ✗ | ✗ Miss |
| fn-delta | Seed-2.0-mini | 10 | ✓ | ⭐ EXCELLENT |
| fn-delta | Seed-2.0-mini | 50 | ✓ | ⭐ EXCELLENT |
| fn-delta | Seed-2.0-mini | 100 | ✓ | ⭐ EXCELLENT |
| fn-delta | Hermes-70B | 10 | ✓ | ⭐ EXCELLENT |
| fn-delta | Hermes-70B | 50 | ✓ | ⭐ EXCELLENT |
| fn-delta | Hermes-70B | 100 | ✓ | ⭐ EXCELLENT |
| fn-delta | Qwen3.6-35B | 10 | ✓ | ⭐ EXCELLENT |
| fn-delta | Qwen3.6-35B | 50 | ✓ | ⭐ EXCELLENT |
| fn-delta | Qwen3.6-35B | 100 | ✓ | ⭐ EXCELLENT |
| fn-epsilon | Seed-2.0-mini | 10 | ✓ | ⭐ EXCELLENT |
| fn-epsilon | Seed-2.0-mini | 100 | ✓ | ⭐ EXCELLENT |
| fn-epsilon | Hermes-70B | 10 | ✓ | ⭐ EXCELLENT |
| fn-epsilon | Hermes-70B | 50 | ✓ | ⭐ EXCELLENT |
| fn-epsilon | Hermes-70B | 100 | ✓ | ⭐ EXCELLENT |
| fn-epsilon | Qwen3.6-35B | 10 | ✗ | ✗ Miss |
| fn-epsilon | Qwen3.6-35B | 50 | ✗ | ✗ Miss |
| fn-epsilon | Qwen3.6-35B | 100 | ✗ | ✗ Miss |

## Key Findings

1. **Best Model:** Hermes-70B (15 correct discoveries)
2. **Easiest Function:** fn-delta (`reverse()`) — 9 correct
3. **Hardest Function:** fn-gamma (`dedup()`) — 3 correct
4. **Tile Count Effect:** 10 tiles → 11 correct, 50 tiles → 9 correct, 100 tiles → 10 correct
5. **Average Resolution Threshold:** 52 tiles (min: 10)

---

*Generated by `experiments/tile_emergence.py`*