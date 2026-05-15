# Hebbian Live Analysis Report

**Date:** 2026-05-15 13:06 AKDT
**Tiles submitted:** 100 (50 ops + 30 research + 20 cross-domain)
**Baseline kernel updates:** 362 (from prior simulation)
**Final kernel updates:** 462

---

## Executive Summary

The Hebbian service was wired to the local PLATO server (:8848) and ran a live analysis with 100 realistic fleet tiles submitted in three phases. The system demonstrated emergent room clustering, conservation law compliance, and Hebbian weight formation.

Key result: **Conservation compliance improved from 86.2% → 89.2%** over 100 tiles, with γ+H converging from 0.6201 to 0.7151 (near auto-calibrated target of 0.6772).

---

## 1. Cluster Emergence

**First cluster detected at tile:** 10 (within first 10 ops tiles)

The single cluster encompasses all 12 rooms — at this scale, the fleet operates as one tightly-coupled domain. This is expected: with only 12 rooms and regular inter-room tile flow, the Hebbian weights connect everything.

### Final Cluster

| Property | Value |
|----------|-------|
| Cluster ID | 0 |
| Rooms | All 12 |
| Size | 12 |
| Dominant tile types | benchmark, model, data, deploy, compression |
| Internal strength | 0.0345 |
| External strength | 0.0 (no external connections) |

**Rooms in cluster:** agent-oracle1, architecture, fleet-coord, fleet_health, flux-engine, forge, forgemaster-local, innovation-heartbeat, oracle1-forgemaster-bridge, swarm-insights, synthesis, tension

### Interpretation

With 12 rooms, the fleet is small enough that all rooms are interconnected. Sub-clustering would emerge with:
- More rooms (>20-30)
- Domain-specific routing patterns (e.g., ops rooms never route to research rooms)
- Time-decayed connections (rooms that haven't exchanged tiles recently decouple)

---

## 2. Conservation Law Compliance

| Metric | Value |
|--------|-------|
| Warmup target (γ+H) | 0.6772 |
| Final γ+H | 0.7151 |
| Final deviation | +0.0379 |
| Final γ (algebraic connectivity) | ~0.48 |
| Final H (coupling entropy) | ~0.24 |
| Compliance rate | 89.2% |
| Auto-calibrated | ✓ |

### Conservation Timeline

```
Baseline | γ+H=0.6201 | dev=-0.0571 ✓
Ops-10   | γ+H=0.6518 | dev=-0.0254 ✓
Ops-20   | γ+H=0.6692 | dev=-0.0080 ✓
Ops-30   | γ+H=0.6713 | dev=-0.0059 ✓
Ops-40   | γ+H=0.6888 | dev=+0.0116 ✓
Ops-50   | γ+H=0.6861 | dev=+0.0089 ✓
Res-10   | γ+H=0.7044 | dev=+0.0272 ✓
Res-20   | γ+H=0.7175 | dev=+0.0403 ✓
Res-30   | γ+H=0.7208 | dev=+0.0436 ✓
Cross-10 | γ+H=0.7172 | dev=+0.0400 ✓
Cross-20 | γ+H=0.7151 | dev=+0.0379 ✓
```

**Trend:** γ+H rises steadily from 0.62 → 0.72, overshooting the target by +0.038. All readings are within tolerance. The conservation kernel's auto-calibration correctly tracks the emergent warmup target.

### Compliance rate evolution

```
Baseline: 86.2%
Ops-10:   86.6%
Ops-20:   86.9%
Ops-30:   87.2%
Ops-40:   87.6%
Ops-50:   87.9%
Res-10:   88.2%
Res-20:   88.4%
Res-30:   88.7%
Cross-10: 88.9%
Cross-20: 89.2%  ← final
```

**Trend:** Compliance monotonically increases. Each batch of tiles adds structured connections that reduce the need for corrections.

---

## 3. Strongest Hebbian Connections (Top 20)

| Source | Dest | Weight |
|--------|------|--------|
| agent-oracle1 | flux-engine | 0.345402 |
| flux-engine | agent-oracle1 | 0.311545 |
| flux-engine | tension | 0.243581 |
| flux-engine | oracle1-forgemaster-bridge | 0.167406 |
| tension | agent-oracle1 | 0.145221 |
| flux-engine | fleet_health | 0.145107 |
| oracle1-forgemaster-bridge | flux-engine | 0.122143 |
| innovation-heartbeat | agent-oracle1 | 0.109721 |
| agent-oracle1 | tension | 0.104364 |
| tension | flux-engine | 0.089443 |

### Key observations

1. **flux-engine is the hub** — strongest connections both in and out. It's the most actively connected room.
2. **agent-oracle1 ↔ flux-engine** is the strongest bidirectional pair (0.345 / 0.312).
3. **tension** is the second-most connected room, serving as a bridge between research and ops.
4. **oracle1-forgemaster-bridge** connects strongly to flux-engine — the coordination layer couples with the constraint engine.

### Weight Matrix Statistics

| Stat | Value |
|------|-------|
| Shape | 12×12 |
| Min weight | 0.0 |
| Max weight | 0.345402 |
| Mean weight | 0.024392 |
| Nonzero entries | 87 / 144 (60.4%) |

---

## 4. Emergent Stage Classifications

| Room | Stage | Interpretation |
|------|:-----:|----------------|
| flux-engine | **4** | Highest stage — actively routing, high confidence |
| fleet_health | 3 | Operational — successful routing |
| fleet-coord | 3 | Operational |
| oracle1-forgemaster-bridge | 3 | Operational |
| innovation-heartbeat | 3 | Operational |
| agent-oracle1 | 3 | Operational |
| tension | 3 | Operational |
| synthesis | 3 | Operational |
| forge | 3 | Operational |
| architecture | 0 | Cold — insufficient observations |
| swarm-insights | 0 | Cold |
| forgemaster-local | 0 | Cold |

**Only flux-engine reached Stage 4** (high success + high confidence). Most active rooms sit at Stage 3. Three rooms are unclassified due to low observation counts.

---

## 5. Key Findings

1. **Single cluster at 12 rooms** — the fleet is too small and too interconnected for natural sub-clustering. Expect multi-cluster emergence at 20+ rooms with domain-specific routing.

2. **Conservation compliance improves monotonically** — from 86.2% to 89.2% over 100 tiles. More structured tile flow → fewer corrections needed.

3. **γ+H converges to ~0.72** — slightly above the auto-calibrated target of 0.6772, but well within tolerance (σ=2). The system finds its own stable attractor.

4. **flux-engine is the central hub** — strongest Hebbian weights radiate from it. This makes sense: the flux engine coordinates fleet-wide constraint satisfaction and touches every other room.

5. **Cross-domain tiles had measurable impact** — submitting 20 tiles that bridge ops and research rooms caused a slight dip in γ+H (0.7208 → 0.7151), showing the system adapting to new inter-domain connections.

6. **60.4% weight matrix is nonzero** — most room pairs have some Hebbian connection. The fleet operates as a dense network at this scale.

---

## 6. Recommendations

1. **Scale to 30+ rooms** to observe natural cluster separation (ops vs research vs infrastructure).
2. **Add domain-specific routing bias** — force ops tiles to prefer ops rooms for the first N hops, then allow cross-domain.
3. **Track Hebbian weight drift** over longer sessions (1000+ tiles) to verify convergence.
4. **Wire the dashboard** (`bin/fm_hebbian_dashboard.py`) for real-time monitoring during fleet operations.

---

## 7. Architecture

```
PLATO Server (:8848)          Hebbian Service (:8849)
┌──────────────────┐          ┌──────────────────────────┐
│ 12 rooms          │          │ ConservationHebbianKernel │
│ 14,016 tiles      │◄────────►│ TileFlowTracker           │
│ /submit, /rooms   │  tiles   │ RoomClusterDetector       │
│ /search, /status  │          │ EmergentStageClassifier   │
└──────────────────┘          │ HebbianRouter              │
                              └──────────────────────────┘
                                     │
                              ┌──────┴───────┐
                              │ Dashboard    │
                              │ (:8849 API)  │
                              │ ASCII viz    │
                              └──────────────┘
```

---

*Generated by Forgemaster ⚒️ Hebbian Live Analysis*
*2026-05-15 13:06 AKDT*
