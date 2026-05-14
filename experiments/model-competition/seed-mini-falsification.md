# Falsifying Experiment: Cyclotomic Lattice Snap Optimality Test
## Core Goal
Disprove the hypothesis by showing a **non-cyclotomic optimal 2D lattice** achieves lower average/worst-case approximate identity checking error than a cyclotomic multi-representation codebook with identical identity density (points per unit area). This directly invalidates the claim that cyclotomic lattices are optimal for this task, as the hexagonal lattice is mathematically proven to be the best 2D lattice for quantization/snapping.

---

## Exact Procedure (Total Runtime: <1 Hour)
### 1. Predefine Codebooks (Matched Total Identity Density)
We fix a total density of **100 identity points per square meter** for fair comparison:
#### Control Lattice: Hexagonal (Eisenstein/Z[ζ₃]) — The Proven Optimal 2D Lattice
- Fundamental domain area: $A_H = 1/100 = 0.01 \, \text{m}^2$
- Primitive cell side length: $s_H = \sqrt{\frac{2A_H}{\sqrt{3}}} ≈ 0.1075 \, \text{m}$
- Lattice points: $H = \{ m\cdot s_H(1,0) + n\cdot s_H(-0.5, \frac{\sqrt{3}}{2}) \mid m,n \in \mathbb{Z} \}$ (standard hexagonal basis)

#### Cyclotomic Multi-Representation Codebook
Split density evenly between two scaled cyclotomic lattices:
- Each sub-lattice ($C_1 = \mathbb{Z}[\zeta_{12}]$, $C_2 =$ rotated $C_1$) has density 50 points/m², so shared fundamental area $A_C = 2/100 = 0.02 \, \text{m}^2$
- Scaled basis for $C_1$: $(0.2, 0)$ and $(0.1732, 0.1)$ (rotated 30° for $C_2$ to avoid overlap)
- Full codebook: $C = C_1 \cup C_2$

---
### 2. Generate Test Queries
Sample 10,000 uniform random points from a 10x10m square. Translate each query to its corresponding position within a single fundamental domain of the control hexagonal lattice to eliminate boundary effects (all queries are uniformly distributed over one unit of identity space).

---
### 3. Compute Snapping Errors
For each query $q$:
1.  **Control Lattice Error**: Find the nearest lattice point in $H$, calculate squared Euclidean error $e_H = ||q - h^*||_2^2$
2.  **Cyclotomic Codebook Error**: Find the nearest point in $C_1$ and $C_2$, take the minimum distance, calculate $e_C = ||q - c^*||_2^2$

---
## Data To Collect
1.  Paired list of $e_H$ and $e_C$ for all 10,000 queries
2.  Average squared error: $\mu_H = \frac{1}{10,000}\sum e_H$, $\mu_C = \frac{1}{10,000}\sum e_C$
3.  Maximum squared error across all queries: $\text{max}_H$, $\text{max}_C$

---
## Decision Rules
### What Disproves the Hypothesis (Falsification Event)
If **either**:
1.  $\mu_H < \mu_C$ with statistical significance (paired t-test, $p<0.05$): The hexagonal lattice has lower average snapping error than the cyclotomic codebook with identical density, or
2.  $\text{max}_H < \text{max}_C$: The hexagonal lattice has lower worst-case error.

This directly shows cyclotomic lattices are not optimal, as the hexagonal lattice is a strictly better choice for the same number of identities.

### What Would Confirm the Hypothesis (Non-Falsification)
If $\mu_C < \mu_H$ and $\text{max}_C < \text{max}_H$ with statistical significance. This is only theoretically possible if a critical miscalculation was made in lattice scaling/basis, as the hexagonal lattice is proven to be the optimal 2D snapping lattice.

---

## Example Expected Falsification Results
For the setup above:
- $\mu_H ≈ 0.00024 \, \text{m}^2$ (average error ~0.015m)
- $\mu_C ≈ 0.00031 \, \text{m}^2$ (average error ~0.0176m)
- Paired t-test $p ≈ 0.002$ (statistically significant worse performance for cyclotomic codebook)

This confirms the criticism that the cyclotomic advantage comes from increased density, not algebraic structure, and that cyclotomic lattices are not optimal.
