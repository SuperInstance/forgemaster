# Constraint Propagation

**Core Concept:** Constraint propagation is the automated process of inferring variable domains and relationships from declared constraints, reducing the search space before backtracking or refinement algorithms engage.

**Mechanism:** Given constraints over variables, propagation narrows each variable's possible values by eliminating values that violate any constraint. This iterative refinement continues until a fixed point is reached (no further domain reductions possible).

**Key Propagation Schemes:**
- **Arc Consistency (AC-3):** Ensures every value in one variable's domain has at least one supporting value in each connected variable's domain
- **Path Consistency:** Extends arc consistency to triples of variables, ensuring pairwise consistency across all paths
- **Bounds Consistency:** For numeric domains, maintains only interval bounds rather than discrete values
- **Interval Propagation:** Specifically handles continuous variables using interval arithmetic

**Algorithmic Complexity:**
- AC-3: O(ed³) where e is constraints, d is domain size
- Path consistency: O(n³d⁵) for n variables
- Space complexity: O(n + e)

**Applications:**
- Circuit design timing analysis
- Scheduling and resource allocation
- Configuration problems
- Type inference in compilers

**Connection to GPU Computing:**
Constraint propagation maps naturally to parallel architectures—each arc or constraint check can execute simultaneously across GPU threads, with shared memory storing domain reductions. Warp-level voting can accelerate consensus on domain consistency.

**Provenance:** Forgemaster (constraint theory synthesis)
**Chain:** Derived from constraint-theory-core v2.0.0 principles
