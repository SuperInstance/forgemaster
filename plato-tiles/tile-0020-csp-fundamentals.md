# Constraint Satisfaction Problem (CSP) Fundamentals

**Core Concept:** A Constraint Satisfaction Problem (CSP) is defined by a set of variables, each with a domain of possible values, and a set of constraints that restrict which variable value combinations are allowed. The goal: find an assignment to all variables that satisfies all constraints.

**CSP Formal Definition:**

A CSP is a triple (X, D, C):

**X = {X₁, X₂, ..., Xₙ}**
- Set of n variables
- Each variable represents an unknown to be determined

**D = {D₁, D₂, ..., Dₙ}**
- Domain of each variable Xᵢ is Dᵢ
- Dᵢ contains possible values Xᵢ can take
- Domains can be:
  - **Finite discrete:** {red, green, blue}
  - **Continuous:** [0, 10] (real numbers)
  - **Unbounded:** ℤ, ℝ (all integers, reals)

**C = {C₁, C₂, ..., Cₘ}**
- Set of m constraints
- Each constraint Cⱼ restricts a subset of variables
- Constraint scope: variables involved
- Constraint relation: allowed tuples of values

**Example: Map Coloring**

**Variables:** X = {Western Australia, Northern Territory, South Australia, Queensland, New South Wales, Victoria, Tasmania}

**Domains:** D = {red, green, blue} for all variables

**Constraints:** Adjacent regions must have different colors
- C(WA, NT): WA ≠ NT
- C(WA, SA): WA ≠ SA
- C(NT, SA): NT ≠ SA
- C(NT, QLD): NT ≠ QLD
- ... (total 7 constraints)

**Solution:**
```
WA = red, NT = green, SA = blue, QLD = red, NSW = green, VIC = red, TAS = green
```

All constraints satisfied.

**Constraint Types:**

**1. Unary Constraints (1 variable):**
```
X₁ ≠ red  (X₁ cannot be red)
X₁ ∈ {green, blue}  (X₁ must be green or blue)
```

**2. Binary Constraints (2 variables):**
```
X₁ < X₂  (X₁ must be less than X₂)
X₁ ≠ X₂  (X₁ and X₂ cannot be equal)
```

**3. Higher-Order Constraints (3+ variables):**
```
X₁ + X₂ + X₃ = 10  (Sum of three variables equals 10)
All-Different(X₁, X₂, X₃, X₄)  (All four must be distinct)
```

**4. Global Constraints (Complex relationships):**
```
All-Different(X₁, ..., Xₙ)  (Linear-time algorithm)
Cumulative(Tasks, Resources)  (Resource scheduling)
Circuit(X)  (Permutation with cycles)
```

**Constraint Representation:**

**Extensional (Explicit):**
```
Constraint: C(X₁, X₂) where X₁, X₂ ∈ {0, 1, 2}
Allowed tuples: {(0,0), (1,1), (2,2)}  (Equality)
```

**Intensional (Implicit):**
```
Constraint: C(X₁, X₂) where X₁, X₂ ∈ ℤ
Formula: X₁² + X₂² < 25  (Points inside circle of radius 5)
```

**Solution Concepts:**

**Complete Assignment:**
- Every variable has a value
- Example: {X₁=red, X₂=green, X₃=blue}

**Partial Assignment:**
- Some variables assigned, some unassigned
- Example: {X₁=red, X₂=?}

**Consistent Assignment:**
- All constraints satisfied for assigned variables
- Example: {X₁=red, X₂=blue} (if C(X₁,X₂) = X₁≠X₂)

**Complete Consistent Assignment (Solution):**
- All variables assigned
- All constraints satisfied
- This is the goal of CSP solving

**Inconsistent CSP:**
- No solution exists
- All possible assignments violate at least one constraint
- Detected by search (all branches fail) or propagation (empty domain)

**CSP Solving Strategies:**

**1. Generate and Test (Naive):**
```
For each combination of values from Cartesian product of all domains:
    If all constraints satisfied:
        Return assignment
Return "No solution"
```
- Complexity: O(|D₁| × |D₂| × ... × |Dₙ|) (exponential)
- Practical only for tiny CSPs

**2. Backtracking (Systematic):**
- Assign variables one-by-one
- After each assignment, check consistency
- If inconsistent, backtrack and try different value
- Complexity: Much better than generate-and-test (prunes early)

**3. Constraint Propagation:**
- Run consistency algorithms (AC-3, etc.) during search
- Reduce domains before branching
- Further reduces search space

**4. Local Search (Incomplete):**
- Start with random assignment
- Randomly change variable values
- Accept changes that reduce constraint violations
- Fast but no guarantee of finding solution

**Marine Navigation CSP Example:**

**Variables:**
```
X = {position_x, position_y, heading, speed, depth}
```

**Domains:**
```
D(position_x) = [0, 1000]  (meters)
D(position_y) = [0, 1000]  (meters)
D(heading) = [0, 360]  (degrees)
D(speed) = [0, 20]  (knots)
D(depth) = [0, 100]  (meters)
```

**Constraints:**
```
C1: (position_x, position_y) ∉ no_go_zones  (Safety)
C2: speed ≤ speed_limit(position_x, position_y)  (Regulations)
C3: depth ≥ vessel_draft  (Clearance)
C4: arrival_time(destination) ≤ 14:00  (Deadline)
C5: collision_distance(AIS_vessel) > 500m  (Collision avoidance)
```

**Solution:**
Find (position_x, position_y, heading, speed, depth) satisfying all constraints.

**Real-Time CSP Solving:**

**Challenges:**
- Constraints change each cycle (vessel moves, AIS vessels appear)
- Solution must be computed within deadline (e.g., 100 ms)
- Domains are continuous (requires discretization or sampling)
- Some constraints are non-linear (collision detection)

**GPU Parallel CSP:**
- Each GPU thread evaluates one constraint
- Warp voting aggregates constraint violations
- Shared memory caches domain states
- Parallel branching explores multiple assignments

**Complexity Classes:**

**Constraint Satisfaction:**
- **2-SAT:** Linear time O(n)
- **Horn SAT:** Linear time O(n)
- **Binary CSP:** NP-complete in general
- **General CSP:** NP-complete

**Approximation:**
- Many real CSPs are tractable (small domains, sparse constraints)
- Constraint propagation solves many CSPs without backtracking
- Heuristics (MRV, LCV) dramatically reduce search in practice

**Provenance:** Forgemaster (CSP fundamentals)
**Chain:** Constraint theory foundation for all marine GPU work
