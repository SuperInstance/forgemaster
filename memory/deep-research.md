# Deep Research: Making Constraint Theory Maximal

> Research synthesis — 2026-04-26
> Cross-referencing: number theory, GPU architecture, learned indexes, 
> algebraic geometry, topological physics, computational geometry

## Executive Summary

Five synergistic directions can make our system orders of magnitude better:

1. **K-ary GPU search** — 3-8x immediate GPU speedup (from 2.6B to 10-20B qps)
2. **Berggren ternary tree** — Algebraic structure we're completely ignoring
3. **Stern-Brocot snap** — Provably optimal rational approximation
4. **CDF-learned snap** — Neural network replaces binary search (O(1) prediction)
5. **Holonomy as Berry phase** — Theoretical foundation connecting to quantum topology

---

## 1. GPU Kernel Rewrite: K-ary + Cache + Merge Path

### Current Bottleneck Analysis

Our kernel does 16 binary search iterations (log2(41216) ≈ 15.3), each accessing
a different random location in the triple array. This is BAD for GPU because:
- 16 random memory accesses per thread = 16 cache misses per query
- Thread divergence: different threads are at different search depths
- No spatial locality between concurrent queries

### Fix 1: K-ary Search (immediate 3-8x)

A 2025 paper (Henneberg, "Bigger Is Not Better") shows optimized K-ary search
on GPU outperforms ALL sophisticated GPU index structures by up to 3.8x.

K-ary search: instead of splitting in half (2-way), split into K equal parts.
- Depth: log_K(N) instead of log_2(N)
- 16-ary search on 41K triples: depth = log_16(41216) ≈ 3.4 → only 4 levels!
- Each level: load 15 comparison values (1 already known) → 15 memory accesses
- Total: 4 × 15 = 60 memory accesses vs 16 for binary

WAIT — that's MORE accesses. The trick is that on GPU, we can load all K values
with a SINGLE coalesced memory read if they're contiguous. Binary search reads
from random locations (bad coalescing). K-ary reads from contiguous blocks (good).

**Implementation**: 
- Reorder the angle array into a K-ary tree layout (B-tree like)
- Each level is a contiguous block of values
- One coalesced read per level instead of K random reads
- 4 coalesced reads vs 16 random reads = ~4x fewer cache misses

### Fix 2: `__ldg()` Read-Only Cache

Our triple array is READ-ONLY during snap. On modern GPUs (sm_89), the `__ldg()`
intrinsic routes reads through the texture cache pipeline without needing texture
objects. This gives us free L1/Tex cache hits with zero code change beyond
replacing `angles[i]` with `__ldg(&angles[i])`.

Expected impact: 1.5-2x for warm cache, minimal for cold.

### Fix 3: Merge Path for Sorted Queries

When queries are sorted (common in batch workloads), we can use moderngpu's
merge path algorithm: O(A + B) instead of O(A log B). For 1M sorted queries on
41K triples, this is ~1M operations instead of ~15M.

**Key insight**: merge path restructures the search as a parallel merge.
Threads cooperatively advance two pointers (one in queries, one in triples),
similar to merge step of mergesort but in parallel across thread blocks.

### Fix 4: Warp-Cooperative Search

Instead of 1 thread = 1 query, use 32 threads = 1 query:
- Load a tile of the angle array into shared memory (e.g., 1024 values)
- All 32 threads cooperatively search within the tile
- Warp shuffle (`__shfl_sync`) for inter-thread communication
- No shared memory bank conflicts if we pad correctly

Expected impact: 2-4x for small arrays, 1-2x for large (shared mem limited).

### Projected GPU Performance

| Technique | Expected qps | Improvement |
|-----------|-------------|-------------|
| Current (binary, global) | 2.6B | 1x |
| + `__ldg()` cache | 3.9B | 1.5x |
| + K-ary tree layout | 7.8B | 3x |
| + Warp-cooperative | 13B | 5x |
| + Merge path (sorted) | 20B+ | 8x |

---

## 2. Berggren Ternary Tree: The Algebraic Structure We're Ignoring

### Discovery

All primitive Pythagorean triples form a TREE rooted at (3,4,5). Three 3×3
matrices (Berggren, 1934) generate every child triple:

```
A = [ 1 -2  2]    B = [ 1  2  2]    C = [-1  2  2]
    [ 2 -1  2]        [ 2  1  2]        [-2  1  2]
    [ 2 -2  3]        [ 2  2  3]        [-2  2  3]
```

Applying A, B, or C to (3,4,5)^T produces three children. Repeating produces
ALL primitive triples exactly once. The inverse matrices navigate back to root.

### Why This Matters for Constraint Theory

1. **Hierarchical snap**: Snap to the nearest node in the Berggren tree, then
   descend to the leaf. This gives multi-resolution: coarse snap first, refine.
   O(tree_depth) ≈ O(log N) but with STRUCTURE — each level corresponds to a
   specific resolution of the manifold.

2. **Progressive refinement**: Start with just the root (3,4,5), then add
   children, then grandchildren. The manifold gets denser at each level.
   This is PERFECT for PLATO — rooms start sparse, get denser over time.

3. **Local operations**: The Berggren matrices are LOCAL — applying a matrix
   to a triple produces a nearby triple. This means snap refinement is a
   local operation (don't need to re-search the whole array).

4. **Algebraic snap**: The group law on rational points (complex multiplication
   of (a/c + ib/c)) gives us an ALGEBRAIC snap function — snap by multiplying
   query point by the inverse of the nearest group element.

5. **Holonomy through group theory**: The fundamental group of the circle (S1)
   is Z (the integers). Holonomy measures how many times a walk wraps around
   the circle. The Berggren tree gives us a DISCRETE version of this —
   counting tree levels crossed during a walk.

### Implementation Plan

New crate: `ct-berggren`
- Generate triples via tree traversal instead of Euclid's formula
- Each triple stores its tree path (sequence of A/B/C choices)
- Snap = find nearest triple by tree path comparison (prefix matching)
- Multi-resolution: snap to depth D first, then refine to depth D+k

---

## 3. Stern-Brocot Snap: Provably Optimal Rational Approximation

### The Connection

The Stern-Brocot tree enumerates ALL positive rationals exactly once.
The Farey sequence F_n contains all rationals in [0,1] with denominator ≤ n.

Our snap problem: given angle θ, find the rational tan(θ) = a/b with
hypotenuse c = sqrt(a²+b²) ≤ max_c that minimizes |θ - arctan(a/b)|.

This IS a best rational approximation problem with denominator constraint!

### Stern-Brocot Algorithm

Given real number x and max denominator N:
1. Start with bounds L = 0/1, R = 1/0
2. Compute mediant M = (L.num + R.num) / (L.den + R.den)
3. If M.den > N, stop — return the closer of L, R
4. If M < x, set L = M; else set R = M
5. Go to 2

This is O(log N) and finds the BEST rational approximation with denom ≤ N.

### Why This Beats Binary Search

Binary search on sorted angles finds the nearest EXISTING triple.
Stern-Brocot finds the nearest POSSIBLE triple (even if we haven't generated it).

For our application, we generate ALL triples up to max_c, so both methods find
the same answer. BUT the Stern-Brocot approach has a key advantage:

- It can generate the nearest triple ON THE FLY without storing all triples
- Memory: O(log N) instead of O(N)
- This enables snapping at max_c = 10^9 or higher without storing billions of triples

### Implementation Plan

New crate: `ct-sternbrocot`
- On-the-fly triple generation via Stern-Brocot tree traversal
- O(log max_c) time, O(log max_c) memory
- Provably optimal (finds the best rational approximation)
- GPU kernel: each thread runs independent Stern-Brocot walk

---

## 4. CDF-Learned Snap: Neural Network Replaces Binary Search

### The Idea

The Kraska et al. (2018) "Case for Learned Index Structures" showed that a
neural network can learn the cumulative distribution function (CDF) of sorted
data, mapping key → predicted position. For our case:

- Input: angle θ ∈ [0, 2π)
- Output: predicted index i in the sorted triple array
- Error: |predicted_i - actual_i| ≤ ε (bounded by training)
- Correction: binary search in [predicted_i - ε, predicted_i + ε]

If ε is small (say 64), the correction is only 6 comparisons (log2(128)).
Total: O(1) neural forward pass + O(log ε) correction = effectively O(1).

### Why This Works Perfectly for Pythagorean Triples

The angle distribution is SMOOTH and PREDICTABLE:
- Uniform distribution (proven: angles of primitive triples are uniform in (0, π/4))
- The CDF is nearly linear: CDF(θ) ≈ θ / (2π) × N_triples
- A simple 2-layer network with ~100 parameters can learn this perfectly

### GPU Implementation with Tensor Cores

1. **Training** (one-time, ~10 minutes on GPU):
   - Generate 1M (angle, index) pairs
   - Train a small MLP: angle → predicted_index
   - Measure max error ε across validation set

2. **Inference** (per query):
   - Normalize angle to [0, 1]
   - Feed through MLP (FP16 on Tensor Cores)
   - Binary search in ±ε window
   - Total: ~100 FLOPs for MLP + ~6 comparisons for correction

3. **Batching**:
   - Reshape 1M queries into matrix multiply: [1M, 1] × [1, hidden]
   - Tensor Core MM: massive throughput
   - Estimated: 10-50 BILLION qps on RTX 4050

### LITune Optimization (2025)

The LITune framework uses Deep RL to automatically tune:
- Network architecture (width, depth, activation)
- Error window size (tradeoff: larger window = less training, more correction)
- Quantization level (FP16 vs INT8 vs INT4)
- Reported: 98% runtime reduction, 17x throughput increase

---

## 5. Holonomy as Berry Phase: Theoretical Foundation

### The Formal Connection

Our holonomy measurement (displacement after a random walk on the triple array)
is the CLASSICAL ANALOG of the Berry phase:

- Berry phase: geometric phase acquired by a quantum state transported around
  a closed path in parameter space
- Our holonomy: angular displacement after a closed walk on the Pythagorean
  manifold (a closed path in the space of Pythagorean triples)
- Both depend only on the GEOMETRY of the path, not the dynamics
- Both are TOPOLOGICAL INVARIANTS (modulo 2π for Berry, modulo TAU for us)

### Implications

1. **Topological protection**: In topological physics, Berry phase provides
   robustness against perturbations. Our bounded holonomy (0.213 rad) means
   the manifold is "topologically protected" — walks can't drift arbitrarily.

2. **Discrete quantum walk connection**: A 2024 paper shows discrete quantum
   walks on lattices have topological invariants determined by holonomy.
   Our random walk IS a discrete quantum walk (classical version) on the
   Pythagorean lattice. The holonomy bound is a topological invariant.

3. **Holonomic quantum computation**: HQC uses geometric phases for robust
   quantum gates. Our constraint theory provides a CLASSICAL analog:
   constraint satisfaction IS holonomic computation (satisfying constraints
   = following the manifold's geometry).

4. **Berry curvature of the triple manifold**: The Berry curvature is the
   local holonomy density. For the Pythagorean manifold (circle S1), the
   Berry curvature is constant = 1/(2π) (the uniform distribution).
   This explains WHY the angles are uniformly distributed — the manifold
   has constant curvature!

### New Research Direction

Define "constraint-theoretic Berry phase" formally:
- Parameter space = the space of constraint configurations
- Connection = the snap function (parallel transport on the manifold)
- Curvature = the holonomy density (how much snap drifts per unit path length)
- Chern number = integral of curvature over the manifold = winding number

This connects constraint theory to:
- Topological insulators (Chern insulators)
- Quantum Hall effect
- Anyon braiding in topological quantum computing
- Gauge theory (the snap function IS a gauge choice)

---

## Synergy Map

```
                    BERGGREN TREE
                   /      |       \
                  /       |        \
           TREE ORDER   GROUP LAW   MULTI-RES
                |         |            |
           K-ARY LAYOUT  ALGEBRAIC   PROGRESSIVE
                |       SNAP           |
           COALESCED    STERN-        REFINEMENT
           GPU READS   BROCOT            |
                |       SNAP             |
            __ldg()   ON-THE-FLY      LEARNED
           CACHE HIT  GENERATION      INDEX
                |         |            |
           MERGE PATH  NO STORAGE    TENSOR CORE
                |      REQUIRED      INFERENCE
                |         |            |
                +----+----+----+-------+
                     |
                 GPU SNAP
                 (10-50B qps)
                     |
              BERRY PHASE
              HOLOMONY
              TOPOLOGY
```

---

## Implementation Priority

### Phase 1 (TODAY): K-ary GPU kernel + `__ldg()`
- Rewrite snap kernel with 16-ary search
- Add `__ldg()` for read-only cache
- Target: 5-8B qps on RTX 4050

### Phase 2 (TODAY): Stern-Brocot crate
- `ct-sternbrocot` — on-the-fly optimal snap
- O(log N) time, O(log N) memory
- Works for max_c = 10^12 (impossible with array-based approach)

### Phase 3 (THIS WEEK): Berggren tree crate
- `ct-berggren` — tree-based triple generation
- Hierarchical snap, multi-resolution
- Group law for algebraic snap

### Phase 4 (THIS WEEK): Learned snap
- Train small MLP on GPU
- Ship as `ct-learned-snap` with pre-trained weights
- Tensor Core inference for 10-50B qps

### Phase 5 (NEXT WEEK): Berry phase paper
- Formal connection: holonomy = Berry phase
- Topological invariants for constraint manifolds
- Submit to arXiv

---

## Key References

1. Henneberg (2025) — "Bigger Is Not Better: The Fastest Static GPU Index Is Also Lightweight!" — arXiv:2506.01576
2. Kraska et al. (2018) — "The Case for Learned Index Structures" — SIGMOD
3. Berggren (1934) — Pythagorean ternary tree matrices
4. Stern-Brocot tree / Farey sequences — optimal rational approximation
5. Landau-Ramanujan constant K ≈ 0.764 — density of sums of two squares
6. Lehmer (1900) — N/(2π) asymptotic for primitive Pythagorean triples
7. moderngpu — Merge Path algorithm for sorted search
8. NVIDIA cuVS (2024) — GPU vector search with CAGRA graph index
9. LITune (2025) — Deep RL for learned index tuning
10. Berry (1984) — Geometric phase in quantum mechanics
