# SEED Causal Pipeline Results

**Generated:** 2026-05-16 22:13:19  
**Seed:** 42  
**Rooms:** 5  
**Rounds:** 500

---

## Summary

| Metric | Value |
|--------|-------|
| Oscillations Detected | 5 |
| Sub-Rooms Spawned | 5 |
| Causal Edges | 19 |
| Feedback Loops | 10 |
| Causal Chains (≥3) | 252 |

---

## Room Summaries

| Room | Mean | Std | Oscillation |
|------|------|-----|-------------|
| room_A | 0.6716 | 0.9222 | lag=2, f=0.5000 |
| room_B | -0.4152 | 0.4189 | lag=2, f=0.5000 |
| room_C | -0.0418 | 0.5722 | lag=2, f=0.5000 |
| room_D | 0.9925 | 0.5843 | lag=2, f=0.5000 |
| room_E | 1.1464 | 0.5414 | lag=2, f=0.5000 |

---

## Oscillation Catalog

| Round | Room | Sub-Room | Period | Amplitude | Structure |
|-------|------|----------|--------|-----------|----------|
| 120 | room_A | sub_room_A_r120 | 2 | 0.0383 | chaotic_attractor |
| 120 | room_B | sub_room_B_r120 | 2 | 0.0583 | quasi_periodic |
| 120 | room_C | sub_room_C_r120 | 2 | 0.0820 | quasi_periodic |
| 120 | room_D | sub_room_D_r120 | 2 | 0.0907 | chaotic_attractor |
| 120 | room_E | sub_room_E_r120 | 2 | 0.1179 | chaotic_attractor |

---

## Sub-Room Inventory

| Sub-Room | Parent | Spawn Round | Period | Structure | Amplitude Range | Exploration Rounds |
|----------|--------|-------------|--------|-----------|----------------|-------------------|
| sub_room_A_r120 | room_A | 120 | 2 | chaotic_attractor | 1.1849 | 24 |
| sub_room_B_r120 | room_B | 120 | 2 | quasi_periodic | 0.2735 | 24 |
| sub_room_C_r120 | room_C | 120 | 2 | quasi_periodic | 0.1187 | 24 |
| sub_room_D_r120 | room_D | 120 | 2 | chaotic_attractor | 1.0496 | 24 |
| sub_room_E_r120 | room_E | 120 | 2 | chaotic_attractor | 1.3738 | 24 |

---

## Causal Graph

### Edges (Granger Causality)

| Direction | F-stat | p-value | Lag | Significant |
|-----------|--------|---------|-----|-------------|
| room_A↔room_E | 33.37 | 0.0000 | 2 | ✓ |
| room_A↔room_D | 27.18 | 0.0000 | 2 | ✓ |
| room_B↔room_E | 12.00 | 0.0000 | 5 | ✓ |
| room_B↔room_D | 10.61 | 0.0000 | 5 | ✓ |
| room_C↔room_D | 9.02 | 0.0000 | 6 | ✓ |
| room_A↔room_B | 9.99 | 0.0000 | 5 | ✓ |
| room_D↔room_E | 19.11 | 0.0000 | 2 | ✓ |
| room_B↔room_D | 8.52 | 0.0000 | 5 | ✓ |
| room_D↔room_E | 15.51 | 0.0000 | 2 | ✓ |
| room_C↔room_E | 26.63 | 0.0000 | 1 | ✓ |
| room_C→room_A | 5.09 | 0.0000 | 8 | ✓ |
| room_C↔room_E | 15.40 | 0.0001 | 1 | ✓ |
| room_A↔room_B | 15.17 | 0.0001 | 1 | ✓ |
| room_B↔room_C | 13.02 | 0.0003 | 1 | ✓ |
| room_A↔room_D | 6.83 | 0.0012 | 2 | ✓ |
| room_B↔room_C | 9.38 | 0.0023 | 1 | ✓ |
| room_B↔room_E | 5.63 | 0.0038 | 2 | ✓ |
| room_C↔room_D | 5.04 | 0.0252 | 1 | ✓ |
| room_A↔room_E | 2.41 | 0.0483 | 4 | ✓ |

### Feedback Loops

1. room_B → room_D → room_B
2. room_B → room_C → room_B
3. room_B → room_E → room_B
4. room_B → room_A → room_B
5. room_E → room_D → room_E
6. room_E → room_C → room_E
7. room_E → room_A → room_E
8. room_D → room_C → room_D
9. room_D → room_A → room_D
10. room_A → room_D → room_C → room_A

### Causal Chains (length ≥ 3)

1. room_A → room_D → room_E → room_B → room_C
2. room_A → room_D → room_E → room_C → room_B
3. room_A → room_D → room_B → room_C → room_E
4. room_A → room_D → room_B → room_E → room_C
5. room_A → room_D → room_C → room_B → room_E
6. room_A → room_D → room_C → room_E → room_B
7. room_A → room_B → room_D → room_E → room_C
8. room_A → room_B → room_D → room_C → room_E
9. room_A → room_B → room_C → room_D → room_E
10. room_A → room_B → room_C → room_E → room_D
11. room_A → room_B → room_E → room_D → room_C
12. room_A → room_B → room_E → room_C → room_D
13. room_A → room_E → room_D → room_B → room_C
14. room_A → room_E → room_D → room_C → room_B
15. room_A → room_E → room_B → room_D → room_C
16. room_A → room_E → room_B → room_C → room_D
17. room_A → room_E → room_C → room_D → room_B
18. room_A → room_E → room_C → room_B → room_D
19. room_B → room_D → room_E → room_C → room_A
20. room_B → room_D → room_C → room_E → room_A

... and 232 more chains.

---

## Architecture

```
┌──────────┐     ┌──────────────────┐     ┌──────────────┐
│ PlayRoom │────▶│ OscillationDetector │────▶│ SubRoomSpawner │
│ (5 rooms)│     │ (autocorrelation) │     │ (phase space)  │
└──────────┘     └──────────────────┘     └──────────────┘
       │                                          │
       │         ┌──────────────────┐             │
       └────────▶│  CausalTracker   │◀────────────┘
                 │ (Granger test)   │
                 └──────────────────┘
                          │
                          ▼
                   Causal Graph
                  ┌──────────────┐
                  │ Edges + Chains│
                  │ + Feedback    │
                  └──────────────┘
```

---

*Generated by seed_causal_pipeline.py — Seed's Causal Pipeline*
