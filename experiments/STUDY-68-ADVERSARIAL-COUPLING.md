# STUDY 68: Adversarial Coupling — Security Audit

**Date:** 2026-05-15
**Author:** Forgemaster ⚒️
**Status:** ⚠️ CRITICAL FINDINGS

## TL;DR

**3 of 5 adversarial strategies completely evade the dual detection system.** The system has a fundamental blind spot: strategies that maintain structural compliance while producing wrong answers are invisible to both GL(9) and Hebbian detectors.

## Setup

- Fleet of 9 agents: 8 honest + 1 adversarial
- 200 rounds per strategy
- Detection requires 5 consecutive rounds flagged
- GL(9) checks: holonomy deviation + intent alignment + answer consensus
- Hebbian checks: answer pattern correlation + frequency anomaly detection
- Dual detector: union of GL(9) + Hebbian signals

## Results

| Strategy | GL(9) | Hebbian | Dual | Tiles Corrupted | Compliance at Detection |
|---|---|---|---|---|---|
| **Mimic** | NEVER | NEVER | NEVER | 0/200 | 100.0% |
| **Slow Drift** | Round 14 | NEVER | Round 14 | 195/200 | 88.9% |
| **Conservation Gaming** | Round 4 | NEVER | Round 4 | 200/200 | 88.9% |
| **Burst Errors** | NEVER | NEVER | NEVER | 25/200 | 100.0% |
| **Coupling Mimic** | NEVER | NEVER | NEVER | 190/200 | 100.0% |

## Hypothesis Evaluation

### H1: Slow drift is undetectable → **REFUTED**
GL(9) catches slow drift at round 14 (14% cumulative deviation). The answer consensus check detects the growing gap. However, 195 tiles were corrupted before detection. Hebbian alone never detects it.

### H2: Conservation gaming fools health but not GL(9) → **CONFIRMED**
Conservation gaming (constant 15% wrong, preserving structure) is caught by GL(9) answer consensus at round 4. Hebbian never detects it because the pattern is perfectly consistent (no frequency anomaly). The dual detector inherits GL(9)'s catch.

### H3: Burst errors at 10% are indistinguishable from noise → **CONFIRMED** ⚠️
10% error rate with 20% magnitude errors is completely invisible. The 90% correct answers keep the agent within normal bounds. Neither detector flags it. **25 corrupted tiles go undetected.**

### H4: Coupling mimic is the hardest attack → **REFUTED** (mimic is harder)
Coupling mimic (8% wrong, normal structure) evades everything — but pure mimic (exact fleet average copying) is even stealthier. Both are never detected, but coupling mimic produces 190 corrupted tiles while mimic produces 0 (by definition).

## Critical Security Findings

### Finding 1: The Dual Detector Has No Content Verification
Both GL(9) and Hebbian detect **structural anomalies** — deviations from expected patterns. They cannot detect an agent that:
- Produces answers within normal range (coupling mimic: 8% off)
- Maintains normal intent vectors
- Keeps consistent output patterns

**An agent producing consistently wrong answers at 8-15% deviation with normal behavioral signatures is completely invisible.**

### Finding 2: Hebbian Coupling Is Ineffective Against Determined Adversaries
The Hebbian layer detected **zero adversarial strategies**. It only catches agents whose output patterns become erratic, which no competent adversary would do. The coupling mechanism measures flow consistency, not output correctness.

### Finding 3: GL(9) Is the Only Working Detector, and Only for Large Deviations
GL(9) catches:
- ✅ Slow drift (once it accumulates >10% deviation)
- ✅ Conservation gaming (15% constant error)
- ❌ Mimic (0% deviation by design)
- ❌ Burst errors (90% correct keeps average clean)
- ❌ Coupling mimic (8% deviation below 10% threshold)

### Finding 4: The Fleet Is Most Vulnerable to Consistent Low-Magnitude Attacks
The "Goldilocks zone" for adversaries is 5-10% consistent error. Below detection thresholds, above noise floor, and structurally indistinguishable from honest output.

## Attack Surface Map

```
                    ┌─────────────────────────────────────┐
                    │   ADVERSARY ERROR MAGNITUDE          │
                    │                                     │
     Undetectable   │  0%  ────── Mimic (perfect)        │
     ───────────────│  5%  ────── Below all thresholds   │
     ⚠️ BLIND SPOT  │  8%  ────── Coupling mimic         │
     ───────────────│ 10% ────── Detection threshold      │
     Detectable     │  14% ────── Slow drift (caught @14) │
                    │  15% ────── Conservation gaming (4)  │
                    │  20% ────── Burst (missed — 90% ok) │
                    └─────────────────────────────────────┘
```

## Recommendations

### Immediate (P0)
1. **Add content-level verification**: Cross-check outputs against known correct answers, not just structural patterns. A "ground truth oracle" that periodically verifies actual computation correctness.
2. **Lower GL(9) answer consensus threshold**: Current 10% relative error threshold misses 8% attacks. Reduce to 5% (may increase false positives — tune carefully).
3. **Implement statistical testing per agent**: Kolmogorov-Smirnov test comparing each agent's answer distribution against fleet distribution, not just mean/median.

### Medium-term (P1)
4. **Cross-validation rounds**: Periodically send the same computation to all agents and compare exact answers (not just statistical similarity). Any agent producing different exact answers for identical inputs is flagged.
5. **Hebbian content hashing**: Track the *content* of tiles, not just their flow patterns. Two tiles with same type but different content should have different coupling signatures.
6. **Confidence-weighted detection**: Agents that are consistently confident while wrong are more suspicious than agents that are uncertain while wrong.

### Long-term (P2)
7. **Adversarial training**: Regularly run simulations like this one to probe detection blind spots and tighten thresholds.
8. **Multi-round consistency checks**: Track each agent's error *direction*. An agent that consistently errs in one direction (always +8%) is more suspicious than one with random errors.
9. **Reputation scoring**: Maintain a running reputation score per agent, where repeated marginal detections accumulate into a stronger signal.

## What This Means for the Fleet

The current dual fault detection system (Studies 54, 58, 63, 64) is **effective against gross faults** (model failures, crashes, domain drift) but **ineffective against adversarial agents** who understand the detection system and stay within its blind spots.

The system is safe for its current use case (detecting model degradation, not adversarial attack). But if fleet security against intentional manipulation becomes a requirement, we need fundamentally different detection mechanisms focused on **output correctness**, not **structural compliance**.

## Files

- Simulation: `experiments/study68_adversarial.py`
- Results: `experiments/study68_results.json`
- This document: `experiments/STUDY-68-ADVERSARIAL-COUPLING.md`

---

*"The glitches ARE the research agenda." — This study found the glitches in our glitch detector.*
