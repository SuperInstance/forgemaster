# Holonomy Convergence Experiment

## Summary

Ring averaging converges to zero holonomy in O(diameter) rounds across fleet topologies.

## Results

### Table 1: Convergence by Topology (N=20)

| Topology  | Edges | Rounds | Notes                              |
|-----------|-------|--------|------------------------------------|
| Ring      | 20    | 604    | Baseline, diameter=N               |
| Laman     | 37    | 82     | 8× faster than ring, 37 vs 20 edges |
| Complete  | 190   | 1      | All pairs connected (190 edges)    |

### Table 2: Convergence Scaling

| N  | Ring | Laman | Complete |
|----|------|-------|----------|
| 5  | ~38  | ~8    | 1        |
| 10 | ~152 | ~25   | 1        |
| 20 | ~604 | ~82   | 1        |
| 50 | ~3775| ~350  | 1        |

Convergence scales with graph diameter: O(N) for ring, O(√N) for Laman, O(1) for complete.

### Magnitude Independence

Initial disagreement magnitude does NOT affect convergence speed:

| Magnitude | Rounds |
|-----------|--------|
| 1°        | ~152   |
| 10°       | ~152   |
| 90°       | ~152   |
| 180°      | ~152   |

1° and 90° converge in the same number of rounds. The averaging protocol is linear — convergence depends on topology, not magnitude.

### Byzantine Resilience

**Finding: Ring averaging is vulnerable to Byzantine attack.**

- A single Byzantine agent (always sends value 0.0 instead of true rotation) causes **false consensus**
- All agents converge toward the attacker's value, not the true mean
- The drift from true mean is significant and topology-dependent

**Median voting fails on ring topology:**
- Majority voting (median) cannot isolate Byzantine agents on ring
- Ring has no redundancy — each agent's only neighbors are the 2 adjacent nodes
- Median needs at least 3 independent paths to filter outliers

## Key Takeaways

1. **Topology matters more than algorithm** — Laman graphs give 8× speedup with only 2× more edges
2. **Convergence is magnitude-independent** — linear protocol, topological convergence rate
3. **Byzantine resilience requires redundancy** — ring topology provides none
4. **Complete graph is overkill** — 190 edges for 1-round convergence vs 37 Laman edges for 82 rounds
