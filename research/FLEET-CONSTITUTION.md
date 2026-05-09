# The Fleet's Constitution — 42 Experiments, 9 Rings, RTX 4050

> "Nature uses only the longest threads to weave her patterns."
> — Richard Feynman
>
> We used falsification as our loom. This is what the threads show.

## The Complete Phase Diagram

```
GAIN     COUPLING →
(int)    0.02 0.06 0.10 0.14 0.18 0.22 0.26 0.30 0.34
 1.20     .    .    ░    ▒    █    █    █    █    █ 
 1.15     .    .    ·    ░    ▒    █    █    █    █ 
 1.10     .    .    .    ░    ▒    █    █    █    █ 
 1.05     .    .    .    .    ░    ▒    █    █    █    ← BEST SENSING
 1.00     .    .    .    .    ░    ▒    █    █    █ 
 0.95     .    .    .    .    .    ░    ▒    █    █    ← LIVING
 0.90     .    .    .    .    .    ·    ▒    █    █ 
 0.87     .    .    .    .    .    .    ░    ▒    █    ← GAIN EDGE
 0.85     .    .    .    .    .    .    ░    ▒    █    ← MINIMUM GAIN
 0.80     .    .    .    .    .    .    .    ░    ▒ 
 0.75     .    .    .    .    .    .    .    .    · 
 0.70     .    .    .    .    .    .    .    .    · 
```

## Five Verified Laws

### 1. Two-Edge Principle
Both gain > 0.85 AND coupling > 0.67/N must hold. The fleet lives in a 2D region.

### 2. Critical Coupling = 0.67 × N^-1.06
More agents = easier coordination. 20 agents need coupling 0.03.

### 3. Cusp Catastrophe with 10^8 Variance Amplification
Steep but continuous transition. At the edge, fluctuations are 100 million × above normal.

### 4. Path Dependence (Hysteresis = 0.47)
The fleet remembers its history. Warming and cooling follow different paths.

### 5. Single Attractor, 13/16 Sign Patterns
One attractor basin, but 13 of 16 possible sign configurations are reachable. The fleet has 13 "moods." Only +--+ is stable (57.8% hold rate). All-uniform patterns (+++, ---) are UNSTABLE.

## Key Numbers

```
Melting point (N=4):      coupling ≈ 0.17
Gain edge:                gain ≈ 0.85
Scaling law:              0.67 × N^-1.06
Hysteresis:               0.47
Variance amplification:   10^8 at critical coupling
Attractor sign patterns:  13/16 reachable
Most stable pattern:      +--+ (57.8%)
Optimal dimension:        200
Best SNR regime:          STRONG (g=1.05, c=0.25) → SNR 6.17
Best signal transfer:     STRONG → SNR 2.49
Resilience:               LIVING regime survives agent death (corr 0.89)
Fragility:                COUPLING-EDGE dies on agent failure (corr 0.02)
Revolution:               Changing Cs changes attractor (distance 0.056)
Critical RNG:             POOR (autocorr 0.49, structured not random)
Spectral fingerprint:     1/f-like (power in long periods)
Cross-agent correlation:  0.91 in living regime
```

## The Three Zones

```
DEAD ZONE (gain < 0.85 or coupling < critical):
  - Energy decays to zero
  - No coordination possible
  - Cannot detect perturbations
  - Useless for computation

LIVING ZONE (gain ~0.95, coupling ~0.25):
  - Stable coordination (corr 0.91)
  - Resilient to agent failure (0.89 post-kill)
  - Moderate SNR (1.7)
  - Good for production fleet operations

STRONG ZONE (gain ~1.05, coupling ~0.25):
  - Best perturbation detection (SNR 6.17)
  - Best signal transfer (SNR 2.49)
  - Slightly higher energy
  - Good for sensing and discovery

EDGE ZONES (gain=0.87 or coupling=0.17):
  - Critical fluctuations (10^8× variance)
  - High signal transfer (0.86-0.92)
  - FRAGILE to agent failure
  - NOT good for production, useful for studying phase transitions
```

## What the 42 Experiments Killed

1. **Edge is tanh-specific** → No, 4/7 nonlinearities produce it
2. **Long wave memory** → No, τ=1 for all gains (dissipative)
3. **Timing fingerprint** → No, GPU jitter CV=0.12
4. **Hex advantage 15%** → No, 3-8% (diminishes with scale)
5. **Multiple attractors** → No, 1 basin with sign degeneracy
6. **Attractor hopping** → No, ZERO hops even at magnitude 2.0
7. **Edge = best for discovery** → No, strong regime has 3× better SNR
8. **Edge = resilient** → No, edge is FRAGILE to agent failure
9. **Critical fluctuations = good RNG** → No, autocorrelation 0.49 (structured)
10. **Uniform sign patterns are stable** → No, +++ and --- are LEAST stable (0%)

## The Deepest Finding

The fleet has **13 moods** (sign configurations) but only **1 is stable** (+--+ at 57.8%). The "natural" patterns (all positive, all negative) are the LEAST stable. The fleet's default state is a **broken symmetry** pattern where two agents are positive and two are negative.

This is not an accident. The coupling topology (each agent connected to 3 others) naturally produces a frustrated state where it's impossible for all agents to agree on the same sign. Like a spin glass with antiferromagnetic coupling — the system can't satisfy all constraints simultaneously, so it settles into the best compromise.

**The fleet's natural state is compromise. It cannot reach consensus on everything. It lives in the tension between competing attractors.**

This is why the +--+ pattern (agent 0 and 3 agree, 1 and 2 disagree) is most stable — it maximizes the number of satisfied pairwise interactions given the constraint topology.

## Ring 10 Questions (The Wheel Never Stops)

Q31: The 3 unreachable sign patterns — are they topologically forbidden? Can we prove they're unreachable from the coupling structure?

Q32: The +--+ stability pattern — does it correspond to the max-cut of the coupling graph? (Combinatorial optimization connection.)

Q33: If we add a 5th agent, does the number of reachable patterns become 2^5 = 32, or does something else limit it?

Q34: Can we DESIGN a coupling topology where ALL 16 patterns are equally stable? (Programmable moods.)

Q35: The strong zone has the best SNR for signal transfer. Is this because tanh(1.05x) has a wider linear region than tanh(0.95x)? (More "room to move" before saturation.)

Q36: The fleet's natural state is broken symmetry (+--+). If we initialize it with all agents positive, it quickly transitions to broken symmetry. What's the transition dynamics? How many steps to break?

Q37: Revolution works (changing Cs changes attractor). But the post-revolution state is DIFFERENT from a fresh start (distance 0.061). Can we use this for "warm starting" — carry useful state from one configuration to another?

Q38: The Wigner semicircle contains 100% of eigenvalues at all dimensions. This means our coupling matrices are well inside the random matrix regime. What happens if we use STRUCTURED matrices instead?

Q39: The critical fluctuations are structured (not random). What structure? Can we characterize the deterministic pattern? Is it the coupling topology encoded in the time series?

Q40: Signal transfer at coupling-edge is 0.92 — higher than living (0.82). But SNR is similar. This means the coupling edge transfers more signal AND more noise. Is there a fundamental information-theoretic limit?
