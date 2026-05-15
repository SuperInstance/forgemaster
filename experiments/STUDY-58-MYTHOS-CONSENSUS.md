# STUDY 58: MythosTile Consensus — GL(9) vs Hebbian Fault Detection

**Date:** 2026-05-15T15:08:10
**Status:** Complete

## Question

When experts disagree, do GL(9) consensus checking and Hebbian anomaly detection identify the same faulty experts?

## Experimental Design

- **50 scenarios**: 25 healthy (all experts agree) + 25 faulty (1-2 experts anomalous)
- **5-9 experts** per scenario
- **5 fault types**: confidence_drop, content_scramble, domain_drift, confidence_spike, silent_expert
- **5 scenarios per fault type** (even coverage)

## Key Findings

### Agreement Rate: 60.0%

⚠️ **MODERATE AGREEMENT** — Detectors partially overlap but each misses some faults.
**Recommendation: Use BOTH detectors** (union for recall, intersection for precision).

## Per-Fault-Type Detection

| Fault Type | GL(9) Catch | Hebbian Catch | Both | Neither |
|------------|-------------|---------------|------|---------|
| confidence_drop | 5/5 | 2/5 | 2/5 | 0/5 |
| confidence_spike | 0/5 | 0/5 | 0/5 | 5/5 |
| content_scramble | 0/5 | 0/5 | 0/5 | 5/5 |
| domain_drift | 0/5 | 0/5 | 0/5 | 5/5 |
| silent_expert | 5/5 | 3/5 | 3/5 | 0/5 |

## Detection Metrics

| Detector | Precision | Recall | F1 | TP | FP | FN |
|----------|-----------|--------|-----|----|----|----|
| GL(9) alone | 0.424 | 0.424 | 0.424 | 14 | 19 | 19 |
| Hebbian alone | 0.333 | 0.151 | 0.208 | 5 | 10 | 28 |
| **Combined (union)** | 0.326 | 0.424 | 0.368 | 14 | 29 | 19 |
| Combined (intersection) | 1.000 | 0.151 | 0.263 | 5 | 0 | 28 |

## False Positive Analysis (Healthy Scenarios)

- GL(9) false positives: 0/25
- Hebbian false positives: 6/25

## Disagreement Analysis

- Total disagreements: 20
- Disagreement rate: 40.0%
- GL(9)-only catches by fault type: {'confidence_drop': 3, 'silent_expert': 2}
  - **Interpretation:** GL(9) catches intent divergence — experts whose holonomy transform deviates from identity
- Hebbian-only catches by fault type: {'content_scramble': 2, 'domain_drift': 1, 'confidence_spike': 1}
  - **Interpretation:** Hebbian catches frequency anomalies — experts whose behavior patterns are statistically unusual

## Detection Modes (Complementary Analysis)

### GL(9) Mode: Intent Divergence Detection
- Operates on 9D intent vectors (CI facets)
- Detects when an expert's transform deviates from identity in holonomy cycles
- Strength: catches subtle semantic drift, domain mismatch
- Weakness: may miss obvious statistical anomalies

### Hebbian Mode: Frequency/Pattern Anomaly Detection
- Operates on observable statistics (confidence, content diversity, frequency)
- Detects when an expert's behavior is statistically unusual
- Strength: catches confidence drops, silent experts, content scrambles
- Weakness: may miss subtle intent divergence

## Recommendation

**Use BOTH detectors (union).** No single detector achieves sufficient F1 alone.

---
*Study 58 — generated 2026-05-15T15:08:10*