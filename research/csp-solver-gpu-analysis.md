# GPU-Accelerated CSP Solver Analysis

## Algorithm: BitmaskDomain + Parallel Backtracking

Each variable's domain is a 64-bit bitmask (bit i = 1 → value i available). AC-3 arc consistency prunes domains before search. GPU parallelizes across partial assignments — each CUDA thread explores a different branch.

## Complexity

- **AC-3:** O(c × d³) where c = constraints, d = max domain size
- **Backtracking:** O(d^n) worst case, but BitmaskDomain prunes to O(pruned^n)
- **GPU:** O(pruned^n / threads) amortized — each thread gets one partial assignment

## Results (RTX 4050)

| Problem | N/V | Solutions | GPU Speedup | Throughput |
|---------|-----|-----------|-------------|------------|
| N-Queens | 8 | 92 | 0.11x | 21M nodes/s |
| N-Queens | 10 | 724 | 0.32x | 73M nodes/s |
| N-Queens | 12 | 14200 | **1.40x** | **304M nodes/s** |
| Petersen 3-color | 10 | 120 | — | 8M nodes/s |
| Random 10V/30% | 10 | 72 | — | 10M nodes/s |
| Random 12V/25% | 12 | 1296 | — | 28M nodes/s |

## Key Findings

1. **Speedup grows with problem size** — GPU needs enough parallelism to saturate 20 SMs
2. **N=12 is the crossover** — below that, CPU overhead (partial assignment generation) dominates
3. **BitmaskDomain is the enabler** — compact representation fits in shared memory
4. **AC-3 provides marginal benefit** for small graphs but essential for scaling

## Connection to FLUX

FLUX constraint checking is a special case of CSP where:
- Each sensor = one variable with domain {pass, fail}
- Constraints are unary (single-variable bounds checks)
- The "solution" is the assignment of pass/fail to all sensors

The GPU CSP solver generalizes FLUX to multi-variable constraints (cross-sensor, temporal). The BitmaskDomain approach directly enables the multivariate constraint engine (exp54).

## Future Work

- N=14+ queens: expect 5-10x GPU speedup as search space explodes
- SAT reduction: encode constraints as CNF, use GPU-accelerated DPLL
- Integration with FLUX-C: compile cross-sensor constraints to BitmaskDomain operations
