# Study 55 (P2): Router Accuracy Over Time — Degradation & Conservation Prediction

**Date:** 2025-05-15  
**Method:** Pure simulation using `fleet_router_api.py` classes (no live API calls)  
**Rounds:** 400 total (100 baseline + 200 degradation + 100 recovery)

## Executive Summary

The fleet router's self-healing system is a **double-edged sword**: it successfully detects degraded models but can trigger **fleet collapse** when degradation is systematic. Conservation metrics in their current form are **not reliable early-warning signals** for routing accuracy.

| Phase | Accuracy | Conservation | Active Models | Quarantined |
|-------|----------|-------------|---------------|-------------|
| A (Baseline) | 70.0% | 0.954 | 11 | 0 |
| B (Degradation) | 39.0% | 0.804 (end) | 4 | 7 |
| C (Recovery) | 17.0% | 0.931 (end) | 4 | 7 |

---

## Phase A — Baseline Routing Accuracy

**100 requests, no drift applied.**

- **Overall accuracy: 70.0%** (70/100)
- Average conservation compliance: 0.954
- Average alignment score: 0.997

### Tier Distribution
- Tier 1: 9 requests (9%)
- Tier 2: 91 requests (91%)

### Key Observation
The router heavily favors **Tier 2 models** — specifically `llama3.2:1b` received 81/100 requests. This is because the auto-selection logic iterates through `PREFERRED_ORDER`, and when conservation compliance ≥ 0.85, it allows Tier 2. The first Tier 1 model (`Seed-2.0-mini`) gets picked, but then subsequent calls cycle through the list based on internal state.

**Baseline accuracy is only 70%** because `llama3.2:1b` (Tier 2) has ~62% base accuracy — the router's load-balancing concentrates traffic on lower-accuracy models.

---

## Phase B — Simulated Degradation

**200 requests with drift applied:**
- Tier 1 models: -2% accuracy per 20 requests
- Tier 2 models: -5% accuracy per 20 requests

### Window-by-Window Results

| Window | Rounds | Accuracy | Conservation | Quarantined |
|--------|--------|----------|-------------|-------------|
| 1 | 100-119 | 75.0% | 0.944 | 5 |
| 2 | 120-139 | 60.0% | 0.922 | 7 |
| 3 | 140-159 | 30.0% | 0.901 | 7 |
| 4 | 160-179 | 55.0% | 0.884 | 7 |
| 5 | 180-199 | 50.0% | 0.865 | 7 |
| 6 | 200-219 | 45.0% | 0.842 | 7 |
| 7 | 220-239 | 10.0% | 0.826 | 7 |
| 8 | 240-259 | 15.0% | 0.804 | 7 |
| 9 | 260-279 | 25.0% | 0.779 | 7 |
| 10 | 280-299 | 25.0% | 0.762 | 7 |

### Degradation Trajectory
Accuracy dropped from **75% → 10%** over 140 rounds (a 65pp drop). Conservation dropped from 0.944 → 0.762.

### Self-Healing Behavior
- **7 models quarantined** during Phase B (all Tier 1 and most Tier 2)
- Progressive quarantine: 5 rounds → 10 rounds → **permanent**
- After 2-3 quarantine cycles, most models received **permanent bans**
- Only 4 models remained active (at the `min_active_experts` floor)

### Critical Finding: Fleet Collapse
The self-healing system entered a **death spiral**:
1. Models degrade → quarantine triggers
2. Quarantined models auto-restore after rounds elapsed
3. Models immediately re-offend (still degraded) → re-quarantined
4. Progressive penalty escalates → permanent quarantine
5. Fleet shrinks below usable size → only Tier 3 models remain

**The system has no mechanism for gradual degradation accommodation.** It treats all faults equally — a model that's 5% degraded gets the same quarantine as one that's 50% degraded.

---

## Phase C — Recovery

**100 requests with drift stopped, models slowly recovering (+0.2%/round).**

### Results
- Recovery accuracy: **17.0%** — WORSE than degradation phase
- 7 models permanently quarantined, never restored
- Only 4 models remain: `llama3.2:1b`, `phi4-mini`, and 2 Tier 3 models

### Why Recovery Failed
1. **Permanent quarantine is irreversible** — `progressive_rounds = [5, 10, 0]` where `0` means permanent
2. Models that were restored immediately re-offended because their accuracy was still low
3. The 3rd offense triggers permanent quarantine — no path back
4. The remaining active models (`llama3.2:1b` at ~50% accuracy, Tier 3 models at <15%) can't carry the fleet

### Recovery Window Analysis
| Window | Rounds | Accuracy | Conservation | Active | Quarantined |
|--------|--------|----------|-------------|--------|-------------|
| 1 | 300-319 | 15.0% | 0.772 | 4 | 7 |
| 2 | 320-339 | 15.0% | 0.814 | 4 | 7 |
| 3 | 340-359 | 10.0% | 0.853 | 4 | 7 |
| 4 | 360-379 | 20.0% | 0.894 | 4 | 7 |
| 5 | 380-399 | 25.0% | 0.931 | 4 | 7 |

Conservation recovered (0.772 → 0.931) but accuracy didn't, because the quarantined models couldn't participate.

---

## Phase D — Conservation as Early Warning Predictor

### Hypothesis
Conservation compliance drops BEFORE routing accuracy, providing an early warning signal.

### Results

| Metric | Phase A | Phase B | Phase C |
|--------|---------|---------|---------|
| Correlation (conservation ↔ accuracy) | r = 0.071 | r = -0.069 | r = 0.081 |
| Lead correlation (cons[t] → acc[t+10]) | r = -0.087 | r = -0.112 | r = 0.056 |

**Conservation compliance did NOT reliably precede accuracy drops.** The correlation is near-zero across all phases. Conservation stayed above 0.85 well into the degradation phase.

### Why Conservation Fails as Predictor
1. **Conservation is computed from Tier 1 model accuracies** — these degrade slowly (-2%/20 requests)
2. **Routing targets Tier 2 models** — these degrade fast (-5%/20 requests)
3. The signal (Tier 1 health) doesn't match the decision (Tier 2 routing)
4. Conservation is too smooth — it doesn't capture the step-function behavior of quarantine events

---

## Key Findings

### 1. Baseline Routing Has a Load-Balancing Bug
The router concentrates 81% of traffic on `llama3.2:1b` (Tier 2, 62% accuracy) instead of distributing across Tier 1 models (94-97% accuracy). This depresses baseline accuracy to 70%.

**Recommendation:** Fix `find_best()` to properly rotate through Tier 1 models before falling to Tier 2.

### 2. Self-Healing Causes Fleet Collapse Under Systematic Degradation
When multiple models degrade simultaneously (e.g., provider outage), the quarantine system:
- Bans models too aggressively (2 consecutive detections → quarantine)
- Escalates to permanent bans too quickly
- Has no "degraded but usable" state
- Can't recover without manual intervention

**Recommendation:** 
- Add a "degraded" tier between healthy and quarantined (reduce traffic, don't eliminate)
- Make progressive quarantine slower: `[10, 20, 30, 50]` instead of `[5, 10, 0]`
- Add manual "acknowledge degradation" endpoint that resets quarantine counters

### 3. Conservation Metrics Don't Predict Routing Accuracy
The conservation signal (Tier 1 health) is disconnected from routing decisions (often Tier 2). This makes it useless as an early warning.

**Recommendation:**
- Track conservation per-tier, not just Tier 1
- Use the tier that's actually being routed as the conservation baseline
- Add a "routing tier accuracy" metric that tracks the accuracy of whichever tier the router selects

### 4. Permanent Quarantine is Too Aggressive
Models that receive 3 quarantine offenses are permanently banned with no recovery path. Under systematic degradation, this quickly kills the fleet.

**Recommendation:**
- Replace `0` (permanent) with a very long timeout (e.g., 100 rounds)
- Add a "grace" mechanism where models can partially restore after a long clean period
- Never permanent-ban Tier 1 models (they're too valuable)

### 5. Recovery Requires Manual Intervention
After fleet collapse, accuracy stays at 17% indefinitely. No automated mechanism restores permanently-quarantined models, even when they've recovered.

**Recommendation:**
- Add a `POST /fleet/healing/reset-permanent` endpoint
- Periodically test quarantined models with a "health probe" computation
- Auto-lift permanent quarantine if a model passes 5 consecutive health probes

---

## Appendix: Simulation Parameters

- **Seed:** 42 (reproducible)
- **Models:** 11 (3 Tier 1, 5 Tier 2, 3 Tier 3)
- **Drift rates:** Tier 1 = -0.1%/round, Tier 2 = -0.25%/round
- **Recovery rate:** +0.2%/round (capped at base accuracy)
- **Quarantine config:** `min_active=4`, `consecutive=2`, `clean_restore=3`, `progressive=[5,10,0]`
- **Conservation sim:** Based on Tier 1 accuracy average + noise
- **Health check sim:** Noisy intent vectors + answer drift proportional to accuracy loss
