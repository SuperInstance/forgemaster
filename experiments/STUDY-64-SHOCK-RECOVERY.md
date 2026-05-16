# STUDY-64: Shell Shock Recovery Dynamics

**Date:** 2026-05-15
**Question:** When shell shock hits (conservation < 85%), how many rounds does it take to recover? What recovery strategy is fastest?
**Hypothesis:** Conservation-guided reweighting recovers fastest because it directly targets the constraint that was violated.

---

## TL;DR

**Hypothesis CONFIRMED.** Conservation-guided reweighting recovers in **3.2 rounds on average**, vs 10.0 for quarantine+wait. Hebbian rebalancing never converged within 100 rounds. Conservation reweighting also loses **73% fewer tiles** (9.5 vs 35.8).

---

## Method

### Fleet Model
- 9 experts (3 Tier-1, 4 Tier-2, 2 Tier-3) with realistic accuracies
- Conservation metric: γ (fleet intent alignment) + H (accuracy coherence)
- Baseline compliance: ~89% (healthy fleet)
- Shell shock: compliance drops below 85%

### Scenarios Tested
| Scenario | What happens | Severity |
|----------|-------------|----------|
| **Single drift** | Top expert accuracy -50%, intent drifts | Mild |
| **Pair misalignment** | Two top experts diverge in opposite directions | Moderate |
| **Cascading failure** | Expert 0 fails → neighbors 1-3 degrade | Severe |
| **Full fleet stress** | All 9 experts degrade 35-65% | Critical |

### Recovery Strategies

1. **Quarantine + Wait** (current approach from Study 63)
   - Quarantine experts with accuracy < 65% of baseline or intent drift
   - Restore after 5 clean rounds with 80%+ accuracy recovery
   - Passive recovery at 4% base rate while quarantined
   - Fleet protection: never drop below 4 active experts

2. **Hebbian Rebalancing**
   - Never quarantine — keep all experts active
   - Increase coupling to stressed agents (Hebbian kernel strengthening)
   - Pull degraded experts toward fleet mean
   - Coupling scales with stress level (0.08–0.33)

3. **Conservation-Guided Reweighting** ⭐
   - Never quarantine — reweight based on conservation contribution
   - Recovery rate scales with conservation gap (bigger violation → more aggressive)
   - Adjusts expert weights: alignment × accuracy = conservation contribution
   - Intent coupling also scales with gap (0.06–0.31)

---

## Results

### Recovery Speed (rounds to reach 85% compliance)

| Scenario | Quarantine+Wait | Hebbian Rebalance | Conservation Reweight |
|----------|:-:|:-:|:-:|
| Single drift | 1 | ✗ (100+) | **2** |
| Pair misalignment | 2 | ✗ (100+) | 6 |
| Cascading failure | 23 | ✗ (100+) | **4** |
| Full fleet stress | 14 | ✗ (100+) | **1** |
| **Average** | **10.0** | **N/A** | **3.2** |

### Tiles Lost During Recovery

| Strategy | Avg Tiles Lost | vs Best |
|----------|:-:|:-:|
| Conservation Reweight | **9.5** | — |
| Quarantine+Wait | 35.8 | 3.8× worse |
| Hebbian Rebalance | 99.0 | 10.4× worse |

### Final Accuracy (post-recovery)

All strategies converge to similar final accuracy (~0.693), but conservation reweighting gets there fastest and with the least collateral damage.

---

## Analysis

### Why Conservation Reweighting Wins

The key insight is that shell shock is a **conservation violation** — γ+H has drifted from its predicted value. Conservation reweighting:

1. **Measures the gap directly** — computes γ+H deviation and scales recovery rate proportionally
2. **Never removes capacity** — all 9 experts remain active, maintaining fleet throughput
3. **Adapts aggressiveness** — large violations trigger aggressive recovery (up to 26% recovery rate vs 6% baseline)
4. **Preserves intent diversity** — pulls toward baseline intent, not fleet mean (unlike Hebbian)

### Why Quarantine+Wait Struggles on Severe Scenarios

- **Cascading failure:** 4 experts get quarantined (0-3), leaving only 5 active. Recovery is slow because quarantined experts recover at 4%/round passively. Takes 23 rounds.
- **Full stress:** Nearly all experts fault simultaneously. Can't quarantine them all (fleet protection kicks in at 4 minimum). The partially-quarantined fleet limps along.
- **The math:** Quarantine removes the symptom (bad outputs) but doesn't accelerate the cure (expert recovery). It's defensive, not therapeutic.

### Why Hebbian Rebalancing Fails

Hebbian rebalancing pulls degraded experts toward the **fleet mean**, but when most of the fleet is degraded, the mean itself is wrong. This creates a convergence trap:

- Stressed fleet → low mean → experts pulled toward low mean → fleet stays stressed
- The coupling mechanism is positive feedback in the wrong direction
- Never escaped the 40% compliance range in any scenario

This is a fundamental limitation: Hebbian learning assumes the environment (fleet mean) is a good target, which breaks during fleet-wide stress.

---

## Key Findings

1. **Conservation reweighting is 3.1× faster** than quarantine+wait (3.2 vs 10.0 rounds)
2. **Conservation reweighting loses 73% fewer tiles** (9.5 vs 35.8)
3. **Hebbian rebalancing is dangerous** during fleet-wide stress — creates convergence traps
4. **Quarantine is slow but safe** — guarantees eventual recovery but with high tile loss
5. **Full fleet stress is the hardest scenario** for quarantine (14 rounds) but paradoxically easy for conservation reweighting (1 round) because the gap signal is strongest

### Counter-intuitive Finding

Full fleet stress recovers in just **1 round** under conservation reweighting, while pair misalignment takes **6 rounds**. This is because:
- Full stress creates a large, uniform gap → recovery rate scales to ~0.26 → rapid correction
- Pair misalignment creates a subtler gap with conflicting signals → takes longer to untangle

---

## Recommendations for Fleet Implementation

1. **Replace quarantine-first with conservation-guided reweighting** as the default recovery strategy
2. **Keep quarantine as a safety net** for cases where reweighting fails after N rounds
3. **Remove Hebbian rebalancing from recovery playbooks** — it's actively harmful during fleet stress
4. **Add conservation gap to the routing decision** — the `conservation_threshold` in `fleet_router_api.py` should drive recovery rate, not just binary Tier-1 filtering

### Code Changes Needed

In `fleet_router_api.py` → `SelfHealingMixin.check_expert_health()`:
- Add conservation gap–scaled recovery instead of fixed `consecutive_for_quarantine`
- Weight experts by `alignment × accuracy` during recovery periods
- Keep progressive quarantine as fallback when reweighting fails after 10 rounds

---

## Files

- `experiments/study64_results.json` — Full simulation data
- `experiments/study64_sim.py` — Simulation source code
- `experiments/STUDY-64-SHOCK-RECOVERY.md` — This report

---

*Study 64 — Forgemaster ⚒️ — 2026-05-15*
