# GPU Experiments — 2026-04-25

## Running
- **Claude Code**: CUDA kernel for parallel snap (session: neat-claw)
- **Kimi**: constraint-theory-core v2.0 implementation (session: quick-bison)

## Completed

### CPU Benchmark (cpu_benchmark.rs)
- Generates Pythagorean triples up to max_c
- Brute-force O(n) snap queries
- Holonomy measurement (closed-loop displacement)
- Results: 831K qps (max_c=100), 27K qps (max_c=10000)

### KD-Tree Benchmark (kd_benchmark.rs)
- Custom 2D KD-tree for nearest-neighbor snap
- Compares brute-force vs KD-tree across 8 resolutions
- Results: 3.1x speedup at 3186 triples, ZERO distance delta
- At max_c=50K: 24K qps (KD) vs 8.3K qps (brute)
- Theoretical: 9600x advantage at max_c=1M

### v2.0 Design (DESIGN.md) — by Claude Code
Five components:
1. **AdaptiveTolerance**: epsilon(c) = k/c for sparse boundary regions
2. **ManifoldResolution**: configurable + auto-refinement (AMR-style)
3. **HolonomyMeter**: closed-loop displacement API with survey()
4. **SnapReport**: per-snap diagnostics (distance, time, resolution, tolerance)
5. **ConstraintSurface trait**: multi-manifold support with ConflictStrategy

## Key Insight
The KD-tree speedup is only 3x because points on a unit circle wrap around — 
a proper angular KD-tree or ball tree would exploit this better. But the 
principle is proven: O(log n) makes constraint theory practical at any resolution.
