# STUDY 63 — Fleet Self-Healing via GL(9) Fault Detection

**Date:** 2026-05-15
**Question:** When GL(9) detects a faulty expert, can the router automatically quarantine it and re-route?

## Answer: YES ✅

> YES — GL(9) intent-drift + answer-consensus fault detection triggers automatic re-routing. Phase A: 100% precision, 71% recall, 0.08ms latency. Phase B: Best strategy is 'quarantine' (86.78% accuracy, degradation=+0.0234). Phase C: 4/4 cascade scenarios handled without collapse.

---

## Fault Detection Method

GL(9) consensus alone (cycle holonomy of identity transforms) produces zero detections.
The effective detector combines **two signals** in 9D intent space:

1. **Intent drift** — cosine similarity between expert's baseline and current intent vector (< 0.85 → fault)
2. **Answer consensus** — relative error of expert's answer vs fleet median (> 0.5 → outlier)

Intersection of both signals: fault confirmed if **both** agree (high precision), with 2-round confirmation.

---

## Phase A — Self-Healing Loop (50 rounds)

| Metric | Value |
|--------|-------|
| Fault injections | 7 |
| Fault clears | 0 |
| Total detections | 5 |
| Precision | 100.00% |
| Recall | 71.43% |
| F1 score | 0.8333 |
| Avg detection latency | 0.077ms |
| Avg fleet accuracy | 89.77% |
| Pre-fault accuracy | 86.67% |
| Post-fault accuracy | 90.11% |
| Avg rounds to detect | 2.4 |

## Phase B — Strategy Comparison (50 rounds, 8 faults each)

| Strategy | Avg Accuracy | Pre-Fault | Post-Fault | Degradation | Detections | Quarantines |
|----------|-------------|-----------|------------|-------------|------------|-------------|
| no_action | 64.67% | 88.89% | 61.98% | +0.2691 | 42 | 0 |
| quarantine | 86.78% | 88.89% | 86.55% | +0.0234 | 4 | 4 |
| cross_consult | 86.78% | 88.89% | 86.55% | +0.0234 | 4 | 4 |

## Phase C — Cascading Failures

| Scenario | Strategy | Initial Faults | Total Faults | Post-Fault Acc | Final Acc | Active | Status |
|----------|----------|---------------|-------------|---------------|-----------|--------|--------|
| 2_simultaneous | quarantine | 2 | 2 | 88.50% | 85.71% | 7/9 | ✅ Stable |
| 2_simultaneous | cross_consult | 2 | 2 | 88.50% | 85.71% | 7/9 | ✅ Stable |
| 3_simultaneous | quarantine | 3 | 3 | 92.09% | 100.00% | 6/9 | ✅ Stable |
| 3_simultaneous | cross_consult | 3 | 3 | 92.09% | 100.00% | 6/9 | ✅ Stable |
| cascade_2_then_1 | quarantine | 2 | 3 | 90.31% | 100.00% | 6/9 | ✅ Stable |
| cascade_2_then_1 | cross_consult | 2 | 3 | 90.31% | 100.00% | 6/9 | ✅ Stable |
| cascade_3_then_2 | quarantine | 3 | 5 | 87.20% | 100.00% | 4/9 | ✅ Stable |
| cascade_3_then_2 | cross_consult | 3 | 5 | 87.20% | 100.00% | 4/9 | ✅ Stable |

## Architecture

```
Expert computes tile → GL9FaultDetector checks:
  1. Intent drift: cosine_sim(base_intent, current_intent) < 0.90?
  2. Answer consensus: |answer - fleet_median| / |median| > 0.10?
  └── Union: fault if EITHER triggers

On detection:
  quarantine → expert.quarantined = True, router excludes
  cross_consult → quarantine + re-evaluate remaining answers
  no_action → do nothing (baseline)
```

## Integration Points

- **gl9_consensus.py** → IntentVector provides 9D intent representation
- **fleet_router_api.py** → CriticalAngleRouter with model availability toggle
- **fleet_unified_health.py** → GL9AlignmentTracker pattern adapted for real-time detection

## Key Finding: Holonomy vs Intent Drift

GL(9) cycle holonomy (transform product deviation from identity) cannot detect faults
when all agents use identity transforms. Intent vector drift detection is the correct signal.
The 9D intent space preserves CI facet correlation (GL(9) key result from Oracle1),
making cosine similarity a reliable fault indicator.
