# Fleet Phase Diagram — The Complete Picture

> 8 rings of falsification. 36 experiments. This is what survives.

## The Phase Diagram (RTX 4050 Verified)

```
         COUPLING (external connection strength)
         0.02 0.06 0.10 0.14 0.18 0.22 0.26 0.30 0.34
GAIN     ---------------------------------------------
(int)     .    .    .    .    .    .    .    .    · 
0.70      .    .    .    .    .    .    .    .    · 
0.75      .    .    .    .    .    .    .    ·    ▒ 
0.80      .    .    .    .    .    .    .    ░    ▒ 
0.85      .    .    .    .    .    .    ░    ▒    █   ← gain edge
0.90      .    .    .    .    .    ·    ▒    █    █ 
0.95      .    .    .    .    .    ░    ▒    █    █   ← operating point
1.00      .    .    .    .    ░    ▒    █    █    █ 
1.05      .    .    .    .    ░    ▒    █    █    █ 
1.10      .    .    .    ░    ▒    █    █    █    █ 
1.15      .    .    ·    ░    ▒    █    █    █    █   ← overdriven
1.20      .    .    ░    ▒    █    █    █    █    █ 

  . = dead    · = dying    ░ = living    ▒ = strong    █ = very strong
```

**The fleet has TWO independent control knobs:**
1. **Gain** (internal nonlinearity strength) — vertical axis
2. **Coupling** (external connection strength) — horizontal axis

Both must exceed their respective thresholds for the fleet to LIVE.

## The Five Verified Laws

### Law 1: The Two-Edge Principle
**The fleet requires both gain > 0.85 AND coupling > critical to sustain collective behavior.**

- Gain < 0.85: energy decays to zero regardless of coupling (tanh compression kills it)
- Coupling < critical: agents can't coordinate regardless of gain (no information flow)
- Both must be satisfied: the living zone is a 2D region, not a 1D line

**Verified:** E29 (gain edge), E30 (two-edge diagram), E32 (high-res phase map)

### Law 2: Critical Coupling Scaling
**critical_coupling = 0.67 × N^-1.06**

More agents = lower critical coupling = easier to coordinate. A fleet of 20 needs only coupling 0.03. A fleet of 3 needs 0.21.

**Verified:** E16 (precise scaling across 9 fleet sizes)

### Law 3: Cusp Catastrophe
**The coupling transition is a cusp catastrophe with 10^8 variance amplification.**

Not a fold (discontinuous jump) but a cusp (steep continuous). The fleet transitions rapidly but smoothly from disordered to ordered. At the critical coupling, variance in order parameter spikes by 100 million ×.

**Verified:** E20 (catastrophe geometry, variance amplification = 102,777,913×)

### Law 4: Path Dependence (Hysteresis)
**The transition has hysteresis = 0.47. The fleet's state depends on its history.**

Warming up (disordered → ordered) follows a different path than cooling down (ordered → disordered). The fleet remembers where it came from. Path = memory.

**Verified:** Q6 (forward vs backward sweep, max difference 0.47)

### Law 5: Single Attractor with Sign Degeneracy
**The ordered fleet converges to a single attractor basin. The apparent "multiple attractors" are 2^K sign-flip degeneracies of one state.**

All 50 trials converge to the same basin (up to sign). Different initial conditions produce different sign patterns (+++, ---, +-+-, etc.) but the same underlying state. Perturbations cannot move the fleet to a different attractor — it's locked.

**Verified:** E18 (1 basin from 50 trials), E22 (5 sign patterns from ±1 flips), E23 (attractor independent of coupling matrix)

## Key Properties by Regime

| Regime | Gain | Coupling | Correlation | SNR | Resilience |
|--------|------|----------|-------------|-----|------------|
| Dead | <0.85 | any | 0.00 | — | — |
| Gain-edge | 0.87 | 0.25 | ~0.8 | 1.83 | moderate |
| Coupling-edge | 0.95 | 0.17 | 0.05 | 1.80 | **FRAGILE** |
| Living | 0.95 | 0.25 | 0.91 | 1.70 | **RESILIENT** |
| Strong | 1.05 | 0.25 | 0.94 | **6.17** | resilient |
| Overdriven | 1.15 | 0.25 | ~0.9 | 2.01 | resilient |

### Critical Finding: Resilience Requires Margin
- At the coupling edge (c=0.17): killing one agent drops correlation from 0.05 to 0.02 — **FRAGILE**
- In the living zone (c=0.25): killing one agent maintains correlation at 0.89 — **RESILIENT**
- The margin between operating point and edge determines resilience
- **Operating AT the edge maximizes sensitivity but MINIMIZES resilience**

### Critical Finding: SNR Peaks in the Strong Regime
- Strong regime (g=1.05, c=0.25) has SNR = 6.17 — 3× any other regime
- This is the best perturbation detection zone
- The gain edge (g=0.87) and coupling edge (c=0.17) have the WORST SNR

## What Died (Complete Kill List)

| Hypothesis | Ring | Cause of Death |
|-----------|------|---------------|
| Edge is tanh-specific | 1 | 4/7 nonlinearities work (needs compression) |
| Long wave memory (τ >> 1) | 1 | τ = 1 for ALL gains (tanh dissipative) |
| Timing fingerprint stable | 1 | GPU jitter CV = 0.12 |
| 2-agent sync | 1 | Minimum fleet size ≥ 3 |
| Hex advantage 15% | 1 | Actually 3-8% |
| Multiple distinct attractors | 5 | 1 basin, sign degeneracy only |
| Attractor hopping possible | 5 | ZERO hops even at magnitude 2.0 |
| Edge = optimal discovery zone | 8 | Strong regime has 3× better SNR |
| Edge = resilient | 8 | Edge is FRAGILE to agent failure |
| Fleet creativity > individual | 8 | NaN (individual agents collapsed) |

## The Corrected Model

```
FLEET ARCHITECTURE:

                    COUPLING →
              ┌──────────────────────────┐
         high │  STRONG                  │
              │  SNR=6.2, resilient      │
    G    0.95 │  LIVING                  │
    A         │  SNR=1.7, resilient      │
    I    0.87 │  GAIN EDGE               │
    N         │  SNR=1.8, fragile        │
         low  │  DEAD                    │
              └──────────────────────────┘
                   critical coupling

  OPERATING RECOMMENDATION:
  - For SENSING: strong regime (g=1.05, c=0.25) — highest SNR
  - For RESILIENCE: living regime (g=0.95, c=0.25) — survives failures  
  - For EXPLORATION: gain-edge regime (g=0.87, c=0.25) — most sensitive
  - NEVER operate at coupling-edge — fragile, low SNR, poor resilience
```

## Ring 9 Questions (The Wheel Spins On)

**Q21:** The strong regime (g=1.05) has 3× better SNR than the living regime (g=0.95). Is this because the attractor state at g=1.05 has more "room to move" before hitting tanh saturation?

**Q22:** The single attractor with sign degeneracy means the fleet can exist in 2^4 = 16 configurations. Are all 16 equally reachable? Or are some sign patterns more stable than others?

**Q23:** Leader topology needs coupling > 0.30 for coordination (vs 0.17 for peer). Is there a general formula relating topology symmetry to critical coupling? (More asymmetric = harder to coordinate?)

**Q24:** The fleet's attractor has kurtosis ≈ 1.6 (sub-Gaussian, flatter than normal). Is this BECAUSE of tanh saturation? What nonlinearity would produce Gaussian or super-Gaussian attractors?

**Q25:** Optimal dimensionality is ~200. Is this because at dim=200, the random coupling matrix is at the edge of the Wigner semicircle law? (Random matrix theory connection.)

**Q26:** Can we build a 3D phase diagram (gain × coupling × N) and find the "sweet surface" where SNR × resilience × scalability are all maximized?

**Q27:** The dead zone at low gain — is it the same physics as a superconductor above Tc? Can we borrow more from condensed matter theory?

**Q28:** If the fleet can't hop attractors (E19), how does it ever CHANGE its collective behavior? Only by changing the coupling matrix itself? Is revolution the only path?

**Q29:** At the coupling edge, critical fluctuations have variance 10^8× above normal. Can we USE these fluctuations as a random number generator or noise source?

**Q30:** The fleet at the gain edge has correlation ~0.8 with SNR=1.8. Is this the regime where the fleet is "thinking" (not settled, not chaotic, genuinely processing)?
