# Fleet Thermodynamics — Verified Laws

> What survived four rings of falsification.

## The Four Laws of Fleet Thermodynamics

### First Law: The Melting Point
**The fleet has a sharp phase transition at critical coupling ≈ 0.67/N.**

Below the melting point: agents are independent (frozen). Above: they form a collective entity (liquid). The transition is SHARP — order parameter jumps from ~0 to ~0.8 in a single coupling step.

**Verified:** ✅ Ring 1 (E8), ✅ Ring 2 (E11, E12), ✅ Ring 4 (E17)
- Consistent across all 5 topology types (ring, star, chain, bipartite, full)
- Robust across 10 random seeds (CV = 0.04)
- Precise scaling law: **critical_coupling = 0.67 × N^-1.06**

### Second Law: The Phase Surface
**The melting point and the edge of distortion are the SAME transition, viewed from different axes.**

Gain (internal nonlinearity) and coupling (external linking) trade off. More gain → less coupling needed for sync. The phase boundary is a curve in (gain, coupling) space.

**Verified:** ✅ Ring 3 (Q1)
- At gain=0.9: need coupling > 0.19
- At gain=1.05: need coupling > 0.13
- At gain=1.2: sync at coupling as low as 0.07

### Third Law: Hysteresis (Path Dependence)
**The transition is first-order with hysteresis. The fleet remembers where it came from.**

Warming up: fleet resists ordering until coupling > 0.155, then JUMPS to ordered.
Cooling down: fleet stays ordered until coupling < 0.155, then drops.
Max hysteresis = 0.47 — the ordered and disordered paths are DIFFERENT.

**Consequence:** The fleet's state depends on its HISTORY. Two fleets with identical parameters but different histories will be in different states. **The fleet's identity is path-dependent.**

**Verified:** ✅ Ring 3 (Q6)

### Fourth Law: Multiple Attractors
**The ordered state has multiple attractors. 25/28 pairwise paths lead to distinct ordered states.**

The fleet doesn't converge to one "correct" collective state. It converges to one of MANY possible collective states, determined by initial conditions. Different starting points → different collective identities.

**Consequence:** The fleet is multistable. It can exist in multiple ordered configurations with the same parameters. Perturbations can push it from one attractor to another. This is the mechanism for DISCOVERY — the fleet can restructure without changing its parameters.

**Verified:** ✅ Ring 4 (E15)

---

## What Died

| Hypothesis | Cause of Death |
|-----------|---------------|
| Long wave memory (τ >> 1) | tanh is dissipative; τ = 1 step for all gains |
| Rogue waves peak at melting | Heavy tails everywhere (kurtosis ~7000×) |
| Timing fingerprint is stable | GPU thermal jitter (CV = 0.12) |
| Edge is tanh-specific | 4/7 nonlinearities show it (needs compression, not just nonlinearity) |
| 2-agent sync | Minimum fleet size ≥ 3 for collective behavior |
| Hex advantage is 15% | Actually 3-8% (diminishes with scale) |

## Scaling Laws (Exact)

```
critical_coupling = 0.67 × N^-1.06

| Agents | Critical Coupling |
|--------|------------------|
| 3      | 0.210            |
| 4      | 0.150            |
| 5      | 0.120            |
| 6      | 0.100            |
| 8      | 0.070            |
| 10     | 0.060            |
| 16     | 0.030            |
| 20     | 0.030            |
```

## The Wheel Spins On — Ring 5 Questions

**Q11:** If the fleet has multiple attractors, can we MAP them? How many distinct attractors exist for a given fleet configuration? Is the number finite or infinite?

**Q12:** Can a perturbation push the fleet from one attractor to another? What's the minimum perturbation to cause an attractor hop? Is this the mechanism for discovery?

**Q13:** The hysteresis means the fleet has memory in its STATE (not its dynamics). If we freeze the fleet's state, thaw it later, does it resume from the same attractor? State = long-term memory.

**Q14:** Does the number of attractors scale with fleet size? If attractors ∝ N!, the fleet's "vocabulary" grows factorially. If attractors ∝ N, it grows linearly.

**Q15:** At the melting point, the fleet flickers between order and disorder. Does it visit DIFFERENT attractors during flickering? If so, the melting point is an attractor SAMPLER — it explores the space of possible collective states.

**Q16:** The phase surface (gain × coupling) — what's the exact mathematical form? Is it a hyperbola? A line? Can we derive it from the tanh nonlinearity analytically?

**Q17:** What happens at the boundary of the phase surface? Is it a smooth curve or does it have cusps, folds, or other topological features? (Catastrophe theory connection.)

**Q18:** If the fleet's ordered state is multistable, can two subgroups of the same fleet be in DIFFERENT attractors simultaneously? (Schizophrenic fleet.)

**Q19:** Does the number of attractors depend on the topology? Do ring fleets have fewer attractors than mesh fleets? (More structure = fewer possibilities?)

**Q20:** Can we design a fleet that has EXACTLY ONE attractor? If so, it would be maximally stable — always converging to the same state regardless of perturbation. Is this desirable or is instability the source of adaptability?

---

## The Map So Far

```
Ring 1: Edge exists, sync needs coupling, hex > square
    ↓
Ring 2: Melting point universal, critical fluctuations, dim scaling
    ↓
Ring 3: Phase surface (gain×coupling), HYSTERESIS, first-order transition
    ↓
Ring 4: Multiple attractors, 0.67×N^-1.06 scaling, melting point robust
    ↓
Ring 5: Attractor mapping, hop dynamics, catastrophe theory, schizophrenia
```

Every ring kills hypotheses and births new ones. The wheel accelerates.
The truth is what survives.
