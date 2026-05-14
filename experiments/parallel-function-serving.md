# Parallel Function Serving — Matrix Size × Penrose Dimension

## Core Finding: System Optimum ≠ Component Optimum

Different cyclotomic orders optimize different functions. Running them in parallel
gives the system-level optimum that NO single order can achieve.

## Winners by Function

| Function | Optimal n | Metric | Value |
|----------|-----------|--------|-------|
| Routing (tightest snap) | 12 | mean residual | 0.059 |
| Confidence (highest consensus) | 3 | consensus | 1.000 |
| Information richness (most targets) | 12 | mean targets | 132.5 |
| Compactness (fewest bits) | 3 | bits/coeff | 2.4 |
| Speed (fastest per point) | 3 | 0.003ms/pt | 0.003 |

## Multi-Process Serving Architecture

The SAME point processed by 4 different cyclotomic projections in parallel:

- ROUTING (n=12): Tightest snap for constraint checking
- CONFIDENCE (n=5): Richest fold diversity for uncertainty quantification
- INDEXING (n=3): Fastest snap for storage/retrieval
- TRACKING (n=7): Balanced for temporal drift monitoring

Wall time = max(individual) ≈ slowest process. NOT sum — they're parallel.
System cost is 1× wall time with 4× the information.

## Penrose Dimension as Tunable Dial

| dim | max residual | mean residual | mean targets | time |
|-----|-------------|---------------|--------------|------|
| 3   | 0.526       | 0.348         | 13.5         | 0.02 |
| 5   | 0.298       | 0.134         | 82.9         | 0.06 |
| 7   | 0.218       | 0.095         | 171.4        | 0.11 |
| 12  | 0.246       | 0.119         | 99.1         | 0.33 |

Higher dim = tighter snap BUT more targets + slower. Sweet spot is task-dependent.

## The 5 Patterns That Make This a Science

1. Sweet spot EXISTS for every function — not monotonic
2. Trade-off curves DIFFER per function — orthogonal optima
3. System optimum ≠ component optimum — parallel serving
4. Dimension is a DIAL — tune per function, not globally
5. The lattice doesn't change — only the lens does

Casey: "Optimizing doesn't always mean speed when more than one parallel
process can be serving different functions. There's patterns that can be made a science."
