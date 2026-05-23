# Consistency Algorithms in Constraint Programming

**Core Concept:** Consistency algorithms prune the search space by removing values from variable domains that cannot participate in any solution, ensuring early detection of unsatisfiability.

**Consistency Hierarchy:**
- **Node Consistency:** Each unary constraint is satisfied by remaining domain values
- **Arc Consistency (AC):** For every binary constraint, each value in one domain has a support in the connected domain
- **Path Consistency:** For all triples of variables, pairwise consistent values exist
- **k-Consistency:** Generalization to k-tuples of variables
- **Global Consistency:** The domain supports a complete solution

**Arc Consistency Algorithms:**

**AC-1:** Repeatedly enforce all constraints until no changes. Simple but inefficient (O(ned³)).

**AC-3:** Use queue of arcs to process. Only revisit arcs when domains change.
```
queue ← all arcs in problem
while queue not empty:
    (Xi, Xj) ← pop(queue)
    if revise(Xi, Xj):
        if domain(Xi) empty: return FAILURE
        for each Xk where (Xk, Xi) in constraints:
            push((Xk, Xi), queue)
```
Complexity: O(ed³) worst-case, much better average-case.

**AC-4:** Precompute support sets in bidirectional tables. O(ed²) preprocessing, O(ed) per propagation. Memory-intensive.

**AC-6:** Space-efficient version of AC-4. O(ed) space, O(ed²) preprocessing.

**GPU Parallelization:**
- Each GPU thread handles one constraint check
- Warp voting for consensus on domain reduction
- Shared memory for domain caching
- Batch revise() operations with coalesced memory access

**Marine Navigation Constraints:**
- Waypoint sequencing: temporal consistency
- Safety corridor: spatial arc consistency
- Resource allocation: budget constraints
- Sensor fusion: measurement consistency across multiple sensors

**Provenance:** Forgemaster (constraint theory fundamentals)
**Chain:** constraint-theory-core v2.0.0 implementation
