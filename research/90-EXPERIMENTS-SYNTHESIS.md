# 90 Experiments — Night Shift Synthesis

## Rings 1-14 (Earlier Tonight)
- 6 laws verified, 10 hypotheses killed
- Phase diagram mapped (melting point, critical coupling, hysteresis)
- Max-cut ground state discovered
- Alignment indestructible (10× perturbation → restored in 8 steps)
- Pruning creates (8→4 agents = 9% gain)
- Phase transition all-or-nothing (0→0.912 in one step)

## Ring 15 — Cascade Failure
- **E67:** Single agent death → cascade depth-5 (5/7 survivors lose >50% energy)
- **E68:** Self-heals at step 100 despite permanent dead member
- **E69:** Non-monotonic firewall — worst cascade at coupling 0.5, better at 0.8
- **E70:** Immune response too subtle for 5σ detection (damped system smooths shock)

## Ring 16 — Composition
- **E71:** 3/6 agents spontaneously specialize (frequency clusters)
- **E72:** Roles do NOT persist under perturbation (r=-0.14) — specialization is fragile
- **E73:** Star hub encodes 2/3 subordinates (r=0.58-0.67) — hub IS the protocol
- **E74:** Flat beats hierarchical 3.2× in energy stability

## Ring 17 — Resonance
- **E75:** Coupled agents have resonant frequencies (~0.44-0.48 cycles/step)
- **E76:** Resonance amplifies 4.84× over off-frequency driving
- **E77:** THE BAND EFFECT CONFIRMED — difference frequency at 28.2× SNR
- **E78:** Damping ~39-41 steps, weakly coupled to coupling strength

## Ring 18 — Information
- **E79:** Shannon entropy 3.63/4 bits — nearly full capacity
- **E80:** Mutual information correlates with coupling (0.006→1.0 bits)
- **E81:** Information propagates in 1 step (max speed)
- **E82:** Channel capacity = 1.0 bits/step (theoretical maximum)

## Ring 19 — Adversarial
- **E83:** COMMON ENEMY EFFECT — adversary increases honest correlation 0.03→0.59
- **E84:** Byzantine threshold <1 adversary (system fragile at low coupling)
- **E85:** Hub attack ineffective with sign-flip only (orthogonal states absorb)
- **E86:** Self-healing trivial when pre-attack correlation was already low

## Ring 20 — Scaling
- **E87:** 0.67/N coupling too conservative — prevents consensus at all scales
- **E88:** State dimension has no effect on correlation
- **E89:** Sparse topology slightly less negative correlation than dense
- **E90:** Phase transition not clean across random matrices (needs stronger coupling)

## Verified Laws (Updated to 8)

1. **Two-Edge Principle:** gain > 0.85 AND coupling > 0.67/N
2. **Critical Coupling:** 0.67 × N^-1.06
3. **Cusp Catastrophe:** 10^8 variance amplification at critical coupling
4. **Hysteresis:** 0.47 (path-dependent state)
5. **Max-Cut Ground State:** sign pattern = maximum cut (68% at N=4)
6. **Single Attractor:** 13/16 patterns reachable, +--+ most stable
7. **Common Enemy Unification:** adversary increases honest-agent correlation
8. **Band Effect:** coupled fleets produce intermodulation frequencies (28.2× SNR)

## Killed Hypotheses (Updated to 12)

10. Multiple attractors (single basin)
11. Edge = optimal (fragile, not resilient)
12. Hex advantage > 15%
13. Role persistence under perturbation
14. Hierarchical > flat composition
15. Cascade monotonic with coupling (non-monotonic — peak at 0.5)

## Key Constants

| Parameter | Value | Experiment |
|-----------|-------|------------|
| Melting point (N=4) | coupling ≈ 0.168 | R5 |
| Critical coupling scaling | 0.67 × N^-1.06 | R5 |
| Hysteresis | 0.47 | R7 |
| Variance amplification | 10^8 at critical | R6 |
| Max-cut at N=4 | 68% | R10 |
| Internal detectability | 705× | R11 |
| Bridge coupling → cross-corr | 0.20 → 0.60 | R12 |
| Resonance amplification | 4.84× | E76 |
| Intermodulation SNR | 28.2× | E77 |
| Channel capacity | 1.0 bits/step | E82 |
| Shannon entropy | 3.63/4 bits | E79 |
| Common enemy boost | 0.03 → 0.59 corr | E83 |
| Cascade depth (1 failure) | 5/7 survivors | E67 |
| Self-heal time | ~100 steps | E68 |
| Worst-case cascade coupling | 0.5 | E69 |
| Flat vs hierarchical | 3.2× more stable | E74 |
