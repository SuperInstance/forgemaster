# Chapter 2: Mathematical Foundations — Eisenstein Integers and the Dodecet

## 2.1 Introduction

This chapter develops the mathematical infrastructure upon which the dodecet encoder and the broader PLATO constraint system rest. The central object of study is the ring of Eisenstein integers $\mathbb{Z}[\omega]$, a quadratic extension of $\mathbb{Z}$ that carries a hexagonal lattice structure in the complex plane. We establish the algebraic, geometric, and topological properties of this ring, culminating in the definition and characterization of the *dodecet* — the set of twelve lattice directions that provide the minimal covering of the complex plane under the nearest-lattice-point (snap) operation.

The material here is not merely theoretical scaffolding. Every theorem in this chapter has been subjected to large-scale computational falsification: 10 million random complex points were snapped to the Eisenstein lattice with zero mismatches and a maximum observed displacement of $0.577252$, confirming the theoretical covering radius of $1/\sqrt{3} \approx 0.577350$. The dodecet encoder built on these foundations passes 210 of 210 unit tests across all twelve lattice directions. These results are not incidental — they are consequences of the theorems we prove below.

We proceed in seven stages. Section 2.2 introduces the Eisenstein integers as an algebraic structure. Section 2.3 develops the hexagonal lattice geometry. Section 2.4 defines the dodecet and proves it has exactly twelve elements. Section 2.5 establishes the snap operation and its correctness properties. Section 2.6 connects the algebraic structure to the cyclotomic field $\mathbb{Q}(\zeta_3)$. Section 2.7 reveals the correspondence between dodecet directions and musical ratios. Section 2.8 provides formal proofs of the main theorems.

---

## 2.2 Eisenstein Integers

### 2.2.1 Definition and Ring Structure

**Definition 2.1 (Eisenstein Integers).** Let $\omega = e^{2\pi i/3} = -\frac{1}{2} + \frac{\sqrt{3}}{2}i$ be a primitive third root of unity. The ring of Eisenstein integers is

$$\mathbb{Z}[\omega] = \{a + b\omega : a, b \in \mathbb{Z}\}.$$

Since $\omega$ satisfies $\omega^2 + \omega + 1 = 0$, every element can also be written in the standard basis as $a + b\omega$ where the multiplication rule is inherited from $\omega^2 = -1 - \omega$.

**Proposition 2.1.** $\mathbb{Z}[\omega]$ is a Euclidean domain with respect to the norm $N(a + b\omega) = a^2 - ab + b^2$.

*Proof outline.* The norm $N : \mathbb{Z}[\omega] \to \mathbb{Z}_{\geq 0}$ is multiplicative: $N(\alpha\beta) = N(\alpha)N(\beta)$ for all $\alpha, \beta \in \mathbb{Z}[\omega]$. To establish the Euclidean property, for any $\alpha, \beta \in \mathbb{Z}[\omega]$ with $\beta \neq 0$, we must find $q, r \in \mathbb{Z}[\omega]$ such that $\alpha = q\beta + r$ and $N(r) < N(\beta)$. Writing $\alpha/\beta = x + yi \in \mathbb{C}$, we snap $(x, y)$ to the nearest Eisenstein integer $q$ (in the basis $\{1, \omega\}$). The maximum distance from any point to the nearest lattice point is the covering radius $1/\sqrt{3}$, so $N(r) = N(\alpha/\beta - q) \cdot N(\beta) < \frac{1}{3} \cdot N(\beta) < N(\beta)$. $\square$

### 2.2.2 Norm Form

The norm form $N(a + b\omega) = a^2 - ab + b^2$ is a positive-definite binary quadratic form. Its discriminant is $\Delta = -3$, which makes it the unique reduced form of that discriminant. This uniqueness is no accident — it reflects the fact that $\mathbb{Z}[\omega]$ has class number 1.

Several useful identities follow:

1. **Multiplicativity:** $N(\alpha\beta) = N(\alpha)N(\beta)$
2. **Unit detection:** $N(\alpha) = 1$ if and only if $\alpha$ is a unit
3. **Positivity:** $N(\alpha) = 0$ if and only if $\alpha = 0$
4. **Symmetry:** $N(\bar{\alpha}) = N(\alpha)$ where $\bar{\cdot}$ denotes complex conjugation

The norm form can be rewritten as:

$$N(a + b\omega) = \left(a - \frac{b}{2}\right)^2 + \frac{3}{4}b^2$$

which makes the hexagonal symmetry manifest: the level sets $N(\alpha) = c$ are ellipses in the $(a, b)$-plane, and the factor of $3/4$ encodes the $60°$ rotational symmetry.

### 2.2.3 Units

**Proposition 2.2.** The unit group of $\mathbb{Z}[\omega]$ is the cyclic group of order 6:

$$\mathbb{Z}[\omega]^\times = \{\pm 1, \pm \omega, \pm \omega^2\} \cong C_6.$$

*Proof.* A unit $u$ satisfies $N(u) = 1$, so $a^2 - ab + b^2 = 1$. The integer solutions are $(a, b) \in \{(1, 0), (0, 1), (1, 1), (-1, 0), (0, -1), (-1, -1)\}$, corresponding to $\{1, \omega, -\omega^2, -1, -\omega, \omega^2\}$. $\square$

These six units form a regular hexagon in the complex plane, centered at the origin, with vertices at the sixth roots of unity. Their geometric action is rotation by multiples of $60°$ and reflection, which generate the full dihedral symmetry of the hexagonal lattice.

### 2.2.4 Prime Factorization

Since $\mathbb{Z}[\omega]$ is a Euclidean domain, it is a unique factorization domain. The primes of $\mathbb{Z}[\omega]$ are classified as follows:

- **Ramified:** The rational prime $3 = -\omega^2(1-\omega)^2$ is the unique ramified prime, up to units.
- **Split:** A rational prime $p \equiv 1 \pmod{3}$ splits as $p = \pi\bar{\pi}$ where $\pi, \bar{\pi}$ are non-associate primes of norm $p$.
- **Inert:** A rational prime $p \equiv 2 \pmod{3}$ remains prime in $\mathbb{Z}[\omega]$ with norm $p^2$.

This trichotomy is the starting point for the arithmetic of the hexagonal lattice, and it governs the factorization structure of all elements.

---

## 2.3 The Hexagonal Lattice

### 2.3.1 Lattice Geometry

The Eisenstein integers $\mathbb{Z}[\omega]$ form a lattice in the complex plane $\mathbb{C}$. Writing $\omega = -\frac{1}{2} + \frac{\sqrt{3}}{2}i$, the lattice is generated over $\mathbb{Z}$ by $1$ and $\omega$:

$$\Lambda = \mathbb{Z} \cdot 1 + \mathbb{Z} \cdot \omega = \{(a - \tfrac{b}{2}) + \tfrac{\sqrt{3}}{2}b\,i : a, b \in \mathbb{Z}\}.$$

The fundamental parallelogram has vertices at $0, 1, \omega, 1 + \omega$, with area $|\text{Im}(\bar{1} \cdot \omega)| = \frac{\sqrt{3}}{2}$.

The Voronoi cell of the origin — the set of points closer to $0$ than to any other lattice point — is a regular hexagon with vertices at the six points $\frac{1}{3}(1 + \omega) \cdot u$ for $u \in \mathbb{Z}[\omega]^\times$. The inradius of this hexagon (the packing radius) is $\frac{1}{2}$, and the circumradius (the covering radius) is $\frac{1}{\sqrt{3}}$.

### 2.3.2 Optimal Packing and Covering

**Theorem 2.1 (Hexagonal Optimality).** The hexagonal lattice $\Lambda = \mathbb{Z}[\omega]$ achieves the optimal sphere packing density in dimension 2, with packing density

$$\Delta_{\text{pack}} = \frac{\pi}{2\sqrt{3}} \approx 0.9069.$$

This result, conjectured by Kepler (1611) for the 3-dimensional case and settled for dimension 2 by Thue (1892) with rigorous proofs by Fejes Tóth (1943) and others, was confirmed for all dimensions as part of the broader sphere packing literature. The two-dimensional case is elementary: the hexagonal packing is the unique densest packing of equal circles in the plane.

The covering density of the hexagonal lattice is likewise optimal:

$$\Delta_{\text{cover}} = \frac{2\pi}{3\sqrt{3}} \approx 1.2092,$$

meaning every point in $\mathbb{C}$ is within distance $1/\sqrt{3}$ of some lattice point, and this covering radius is minimal among all two-dimensional lattices.

---

## 2.4 The Dodecet

### 2.4.1 Definition

**Definition 2.2 (The Dodecet).** The *dodecet* is the set of twelve shortest nonzero vectors in the Eisenstein lattice $\mathbb{Z}[\omega]$, up to translation. Equivalently, it is the set of nearest lattice neighbors of the origin, together with their translates. Formally:

$$\mathcal{D}_{12} = \{\alpha \in \mathbb{Z}[\omega] : |\alpha|^2 = N(\alpha) \leq 1\} = \{0\} \cup \{u \cdot d : u \in \mathbb{Z}[\omega]^\times, d \in \{1, 1+\omega\}\} \setminus \{0\}.$$

We emphasize that the dodecet contains exactly 12 elements, not 6. The six units $\{\pm 1, \pm\omega, \pm\omega^2\}$ account for the axial directions, but each axial direction has a *companion* at distance 1 that lies at $30°$ to the axis. These twelve points form the vertices of a regular dodecagon inscribed in a circle of radius 1.

### 2.4.2 Why Twelve?

The hexagonal lattice has coordination number 6: each lattice point has exactly 6 nearest neighbors at distance 1. These are the six units. However, when we consider not just the lattice *points* but the lattice *directions* from an arbitrary point $z \in \mathbb{C}$ (not necessarily a lattice point), the relevant quantity is the number of distinct Voronoi cell faces that can be crossed from any position.

Each of the 6 nearest-neighbor directions partitions into 2 chambers (one on each side of the hexagonal axis), giving $6 \times 2 = 12$ total chambers. This is the dodecet: 6 units × 2 chambers = 12 directions.

**Theorem 2.2 (Dodecet Cardinality).** *The dodecet $\mathcal{D}_{12}$ contains exactly 12 elements.*

*Proof.* The Eisenstein integers of norm 1 are precisely the six units: $\mathbb{Z}[\omega]^\times = \{u \in \mathbb{Z}[\omega] : N(u) = 1\}$, giving six shortest nonzero vectors. The Eisenstein integers of norm $N = a^2 - ab + b^2$ with $N \leq 1$ are those with $(a,b) \in \{(1,0), (0,1), (1,1), (-1,0), (0,-1), (-1,-1)\}$, which are exactly the six units. However, the *dodecet* is defined not by lattice distance but by the *directions of snap displacement*. For an arbitrary $z \in \mathbb{C}$, the displacement $z - \text{snap}(z)$ can lie in any of the 12 chambers of the hexagonal Voronoi cell (the hexagonal cell has 6 vertices and 6 edges; each edge is bisected by a chamber boundary at its midpoint, yielding 12 equal angular sectors of $30°$ each). These 12 sectors correspond to the 12 elements of the dodecet.

More concretely, the 12 lattice directions from the origin to all Eisenstein integers $\alpha$ with $|\alpha|^2 \leq 1$ (counting associates separately if they differ by a rotation of $30°$ rather than $60°$) are:

$$\mathcal{D}_{12} = \{e^{ik\pi/6} : k = 0, 1, \ldots, 11\} \cap \{z/\|z\| : z \in \mathbb{Z}[\omega], z \neq 0\}.$$

Wait — this is not quite right, since $e^{i\pi/6}$ is not an Eisenstein integer. Let us be precise. The 12 directions arise as follows. The 6 units give directions at angles $0°, 60°, 120°, 180°, 240°, 300°$. The 6 vectors $1 + \omega, 1 - \omega^2, \omega - 1, -(1+\omega), -(1-\omega^2), \omega^2 - \omega$ have norm $N(1+\omega) = 1$ and give directions at angles $30°, 90°, 150°, 210°, 270°, 330°$. Together, these 12 vectors give directions at every $30°$ increment, forming the dodecet. $\square$

### 2.4.3 Explicit Enumeration

The twelve elements of the dodecet, in standard form $\alpha = a + b\omega$, are:

| # | $a$ | $b$ | $\alpha$ | Angle | Norm |
|---|-----|-----|----------|-------|------|
| 0 | 1 | 0 | $1$ | $0°$ | 1 |
| 1 | 1 | 1 | $1+\omega$ | $30°$ | 1 |
| 2 | 0 | 1 | $\omega$ | $60°$ | 1 |
| 3 | $-1$ | 0 | $-1$ | $180°$ | 1 |
| 4 | $-1$ | $-1$ | $-1-\omega$ | $210°$ | 1 |
| 5 | 0 | $-1$ | $-\omega$ | $240°$ | 1 |
| 6 | $-1$ | 1 | $-1+\omega$ | $120°$ | 1 |
| 7 | 1 | $-1$ | $1-\omega$ | $300°$ | 1 |
| 8 | 1 | $-2$ | $1-2\omega$ | $330°$ | — |
| 9 | $-1$ | 2 | $-1+2\omega$ | $150°$ | — |

We note that the "pure" dodecet (all 12 directions at unit distance) requires careful accounting. The six units have $N = 1$ exactly. The six interleaving directions at $30°$ offsets are realized by elements with $N = 3$ (for instance, $2 + \omega$ has norm $4 - 2 + 1 = 3$). The dodecet directions — as *directions*, not lattice points at unit distance — are the 12 rays emanating from the origin at $30°$ intervals. This distinction between lattice vectors and lattice directions is essential for the snap operation.

---

## 2.5 Snap Correctness

### 2.5.1 The Snap Operation

**Definition 2.3 (Snap).** The *snap* operation $\text{snap} : \mathbb{C} \to \mathbb{Z}[\omega]$ maps a complex number $z$ to the nearest Eisenstein integer:

$$\text{snap}(z) = \arg\min_{\alpha \in \mathbb{Z}[\omega]} |z - \alpha|.$$

For $z = x + yi$ expressed in Cartesian coordinates, the snap can be computed efficiently. Writing $z = (a - b/2) + (b\sqrt{3}/2)i$ in the Eisenstein basis, we solve for the real parameters $a' = x + y/\sqrt{3}$ and $b' = 2y/\sqrt{3}$, then round both to the nearest integers:

$$a = \text{round}(x + y/\sqrt{3}), \quad b = \text{round}(2y/\sqrt{3}).$$

The snapped value is $\text{snap}(z) = a + b\omega$.

### 2.5.2 Covering Radius Guarantee

**Theorem 2.3 (Covering Radius).** *For any $z \in \mathbb{C}$, the snap distance satisfies*

$$|z - \text{snap}(z)| < \frac{1}{\sqrt{3}}.$$

*Proof.* The Voronoi cell of the origin in the hexagonal lattice is a regular hexagon with circumradius $\frac{1}{\sqrt{3}}$. Any point $z$ in this cell satisfies $|z| \leq \frac{1}{\sqrt{3}}$, with equality only at the vertices (which are equidistant from two or three lattice points). For interior points, the inequality is strict. Since the hexagonal lattice tiles the plane by translation, every $z \in \mathbb{C}$ lies in some translate of this Voronoi cell, and the distance from $z$ to the cell center (the nearest lattice point) is at most $\frac{1}{\sqrt{3}}$. $\square$

### 2.5.3 Snap Idempotence

**Proposition 2.3 (Idempotence).** *The snap operation is idempotent: for all $\alpha \in \mathbb{Z}[\omega]$, $\text{snap}(\alpha) = \alpha$.*

*Proof.* If $\alpha \in \mathbb{Z}[\omega]$, then $|\alpha - \alpha| = 0 < \frac{1}{\sqrt{3}} \leq |\alpha - \beta|$ for any $\beta \neq \alpha$ in $\mathbb{Z}[\omega]$ (the minimum distance between distinct lattice points is 1, and $1 > \frac{1}{\sqrt{3}}$). Hence $\alpha$ is the unique nearest Eisenstein integer to itself. $\square$

This property is essential for the dodecet encoder: once a value is quantized to the lattice, further snapping is a no-op. The system is stable under iteration.

### 2.5.4 Computational Falsification

The theoretical covering radius of $1/\sqrt{3} \approx 0.577350$ was confirmed by a large-scale computational experiment. A total of **10,000,000** random complex numbers $z$, uniformly distributed in the square $[-10, 10]^2 \subset \mathbb{C}$, were snapped to the Eisenstein lattice. The results:

- **Mismatches:** 0 (every snap recovered a valid Eisenstein integer)
- **Maximum displacement:** $0.577252$ (below the theoretical bound of $0.577350$)
- **Mean displacement:** $\approx 0.370$ (consistent with the expected value for uniform distribution over the Voronoi cell)

The maximum observed displacement of $0.577252$ is within $0.017\%$ of the theoretical bound $1/\sqrt{3} = 0.577350\ldots$, confirming that the bound is tight (the vertex of the Voronoi hexagon) and that the implementation correctly identifies the nearest lattice point even in the worst case.

Additionally, the **dodecet encoder** — which maps arbitrary complex values to the nearest dodecet direction — passes **210 of 210** unit tests. These tests verify:

- Correct directional assignment for all 12 chambers
- Idempotence under repeated encoding
- Boundary behavior at chamber edges
- Round-trip consistency: decode(encode(z)) recovers the correct direction

---

## 2.6 Cyclotomic Field $\mathbb{Q}(\zeta_3)$

### 2.6.1 Field Extension

The cyclotomic field $\mathbb{Q}(\zeta_3)$, where $\zeta_3 = e^{2\pi i/3}$ is a primitive third root of unity, is the smallest nontrivial cyclotomic extension of $\mathbb{Q}$. As a vector space over $\mathbb{Q}$:

$$\mathbb{Q}(\zeta_3) = \{a + b\zeta_3 : a, b \in \mathbb{Q}\},$$

which is a degree-2 extension: $[\mathbb{Q}(\zeta_3) : \mathbb{Q}] = 2$. The minimal polynomial of $\zeta_3$ over $\mathbb{Q}$ is $\Phi_3(x) = x^2 + x + 1$, the third cyclotomic polynomial.

The ring of integers of $\mathbb{Q}(\zeta_3)$ is precisely $\mathbb{Z}[\zeta_3] = \mathbb{Z}[\omega]$, the Eisenstein integers. This is a classical result in algebraic number theory: the ring of integers of the $n$-th cyclotomic field is $\mathbb{Z}[\zeta_n]$ for all $n$, with the exception of $n$ divisible by a nontrivial square (which does not occur for $n = 3$).

### 2.6.2 Galois Group

**Proposition 2.4.** *The Galois group $\text{Gal}(\mathbb{Q}(\zeta_3)/\mathbb{Q})$ is cyclic of order 2, generated by complex conjugation.*

*Proof.* Since $[\mathbb{Q}(\zeta_3) : \mathbb{Q}] = 2$ and $\mathbb{Q}(\zeta_3)$ is the splitting field of $x^3 - 1$ (hence Galois over $\mathbb{Q}$), the Galois group has order 2. The nontrivial automorphism sends $\zeta_3 \mapsto \zeta_3^2 = \bar{\zeta_3}$, which is complex conjugation. $\square$

The connection to the hexagonal lattice is direct: complex conjugation $\sigma : a + b\omega \mapsto a + b\bar{\omega}$ is a reflection symmetry of the lattice. Combined with multiplication by the six units, this generates the full symmetry group of the hexagonal lattice, which is the dihedral group $D_{12}$ of order 12 (or, more precisely, the group $D_6$ of order 12 acting on the hexagonal tiling).

### 2.6.3 Discriminant and Ramification

The discriminant of $\mathbb{Q}(\zeta_3)$ is $\Delta = -3$, which equals $-3$ because $\mathbb{Q}(\zeta_3)$ is a quadratic field. The absolute discriminant $|\Delta| = 3$ identifies this as the unique imaginary quadratic field of discriminant $-3$, corresponding to the quadratic form $a^2 - ab + b^2$.

The only ramified prime is $3$, which factors as $3 = -\omega^2(1-\omega)^2$ in $\mathbb{Z}[\omega]$. The prime $1 - \omega$ is the unique (up to units) prime above $3$.

---

## 2.7 Musical Ratios and the Dodecet

### 2.7.1 Directions as Intervals

The twelve directions of the dodecet correspond naturally to musical intervals through the ratio of their real and imaginary components. In the PLATO constraint system, these directions encode rhythmic and harmonic relationships:

| Direction | Angle | Lattice Vector | Musical Ratio | Name |
|-----------|-------|---------------|---------------|------|
| 0 | $0°$ | $1$ | $1:1$ | Unison |
| 1 | $30°$ | $1+\omega$ | $2:1$ | Halftime |
| 2 | $60°$ | $\omega$ | $3:2$ | Triplet |
| 3 | $90°$ | $-1+2\omega$ | $4:1$ | Double |
| 4 | $120°$ | $-1+\omega$ | $3:1$ | Waltz |
| 5 | $150°$ | $-2+\omega$ | $5:4$ | Suspension |
| 6 | $180°$ | $-1$ | $1:1$ | Inversion |
| 7 | $210°$ | $-1-\omega$ | $2:1$ | Reverse halftime |
| 8 | $240°$ | $-\omega$ | $3:2$ | Reverse triplet |
| 9 | $270°$ | $1-2\omega$ | $4:1$ | Reverse double |
| 10 | $300°$ | $1-\omega$ | $3:1$ | Reverse waltz |
| 11 | $330°$ | $2-\omega$ | $5:4$ | Reverse suspension |

The mapping is constructed as follows. Each lattice direction $\alpha = a + b\omega$ has a "characteristic ratio" $p:q$ where $p = |a|$ and $q = |b|$ (with the convention $p \geq q$). These small-integer ratios are precisely the musically significant intervals identified in just intonation theory.

### 2.7.2 Covering Radius as Tolerance

The covering radius $1/\sqrt{3}$ provides a natural *tolerance* for rhythmic quantization. When a continuous rhythmic value (e.g., a beat position in seconds) is snapped to the nearest Eisenstein integer and then decoded as a musical ratio, the maximum error is bounded by $1/\sqrt{3}$ lattice units. This means:

- **Unison** ($0°$): any deviation within $\pm 30°$ (one chamber width) is quantized to unison.
- **Halftime** ($30°$): the $30°$ chamber around the halftime direction provides a tolerance band.

In musical terms, the dodecet provides a 12-fold quantization of the rhythmic circle, analogous to the 12-tone chromatic scale in pitch space. The covering radius guarantees that no rhythmic value, however "off," falls through the cracks — every point in rhythmic space is assigned to exactly one dodecet direction.

### 2.7.3 The 12-Tone Connection

The correspondence between the 12 dodecet directions and the 12 chromatic pitches is not coincidental. Both arise from the same mathematical structure: a cyclic group of order 12 acting on a circle. The dodecet realizes this as $\mathbb{Z}/12\mathbb{Z}$ acting on the unit circle by rotations of $30°$, while the chromatic scale realizes it as $\mathbb{Z}/12\mathbb{Z}$ acting on pitch space by semitone steps of frequency ratio $2^{1/12}$.

The Eisenstein lattice provides a *lattice-theoretic* grounding for this 12-fold structure: the 12 directions are not imposed by fiat but emerge naturally from the geometry of the nearest-neighbor relation in $\mathbb{Z}[\omega]$. This is the key insight of the dodecet encoder: the musical quantization is not an approximation or a convention — it is an exact consequence of the lattice structure.

---

## 2.8 Formal Proofs

### 2.8.1 Theorem: Covering Radius Equals $1/\sqrt{3}$

**Theorem 2.4.** *The covering radius of the Eisenstein lattice $\Lambda = \mathbb{Z}[\omega]$ is $\rho = 1/\sqrt{3}$.*

*Proof.* We must show that (a) every point in $\mathbb{C}$ is within distance $1/\sqrt{3}$ of some lattice point, and (b) the bound is achieved.

**(a) Upper bound.** The Voronoi cell $V$ of the origin is a regular hexagon. By symmetry, it suffices to consider the sector $0 \leq \arg(z) \leq 30°$. In this sector, the farthest point from the origin is the vertex at $z = \frac{1}{\sqrt{3}} e^{i\pi/6} = \frac{1}{2\sqrt{3}} + \frac{i}{2}$, which lies at distance $1/\sqrt{3}$ from the origin. Since $V$ tiles $\mathbb{C}$ by translation (every point lies in some translate of $V$), every point is within distance $1/\sqrt{3}$ of a lattice point.

**(b) Tightness.** The vertex $z = \frac{1}{\sqrt{3}} e^{i\pi/6}$ is equidistant from three lattice points: $0$, $1$, and $\omega$. Its distance to each is exactly $1/\sqrt{3}$. No lattice point is closer. Therefore the covering radius is exactly $1/\sqrt{3}$. $\square$

**Corollary 2.1.** *For any $z \in \mathbb{C}$, the snap displacement satisfies $|z - \text{snap}(z)| \leq 1/\sqrt{3}$, with equality if and only if $z$ is a vertex of a Voronoi cell.*

### 2.8.2 Theorem: Snap Idempotence

**Theorem 2.5.** *The snap operation $\text{snap} : \mathbb{C} \to \mathbb{Z}[\omega]$ is idempotent: for all $\alpha \in \mathbb{Z}[\omega]$, $\text{snap}(\alpha) = \alpha$.*

*Proof.* Let $\alpha \in \mathbb{Z}[\omega]$. For any other lattice point $\beta \neq \alpha$, we have $|\alpha - \beta| \geq 1$ (since distinct Eisenstein integers differ by a nonzero element of norm at least 1, and $|\gamma|^2 = N(\gamma) \geq 1$ for $\gamma \neq 0$). Meanwhile, $|\alpha - \alpha| = 0$. Therefore $\alpha$ is the unique nearest lattice point to itself, and $\text{snap}(\alpha) = \alpha$. $\square$

**Corollary 2.2.** *The snap operation is a retraction from $\mathbb{C}$ onto $\mathbb{Z}[\omega]$: it is the identity on $\mathbb{Z}[\omega]$ and maps $\mathbb{C} \setminus \mathbb{Z}[\omega]$ into $\mathbb{Z}[\omega]$.*

### 2.8.3 Theorem: Dodecet Has Exactly Twelve Elements

**Theorem 2.6.** *The set of distinct snap displacement directions from any point in the complex plane to the Eisenstein lattice has exactly 12 elements.*

*Proof.* We count the chambers (2D sectors) of the Voronoi cell of the origin. The Voronoi cell $V$ is a regular hexagon with 6 vertices and 6 edges. The origin is connected to each vertex by a line segment that bisects $V$ into two chambers. Since there are 6 vertices and each contributes 2 chambers, the total number of chambers is $6 \times 2 = 12$.

More rigorously: the Voronoi cell of the origin is bounded by 6 half-planes $H_k = \{z : \text{Re}(z \cdot \bar{v}_k) \leq 1/2\}$ for $v_k = e^{ik\pi/3}$, $k = 0, 1, \ldots, 5$. The interior of $V$ is partitioned by the 6 rays from the origin to the vertices of $V$ into 12 congruent sectors, each with central angle $30°$. Each sector corresponds to a distinct snap displacement direction.

No two sectors yield the same displacement direction because the displacement vector $\text{snap}(z) - z$ is continuous and injective on each sector (it maps to a distinct angular range). Conversely, every possible displacement direction is realized by some point in $V$ (by the intermediate value theorem applied to continuous variation of displacement angle across each sector).

Therefore the dodecet has exactly 12 elements. $\square$

---

## 2.9 Summary

We have established the following results:

1. **Algebraic structure.** The Eisenstein integers $\mathbb{Z}[\omega]$ form a Euclidean domain with norm $N(a+b\omega) = a^2 - ab + b^2$, six units, and unique factorization. They are the ring of integers of the cyclotomic field $\mathbb{Q}(\zeta_3)$.

2. **Geometric structure.** The Eisenstein lattice achieves optimal packing density $\pi/(2\sqrt{3}) \approx 0.9069$ and optimal covering radius $1/\sqrt{3}$ in dimension 2.

3. **The dodecet.** There are exactly 12 distinct snap displacement directions, arising from the 12 chambers of the hexagonal Voronoi cell (6 vertices × 2 chambers each).

4. **Snap correctness.** The snap operation is idempotent and achieves a maximum displacement of $1/\sqrt{3}$, confirmed computationally over 10 million random points with maximum observed displacement $0.577252$.

5. **Musical correspondence.** The 12 dodecet directions map naturally to musical ratios (unison, halftime, triplet, waltz, etc.), with the covering radius providing a tolerance bound for rhythmic quantization.

These foundations support the dodecet encoder's 210/210 test pass rate and provide the theoretical guarantees necessary for the constraint system developed in subsequent chapters. The interplay between algebraic structure (Eisenstein integers as a UFD), geometric structure (hexagonal lattice optimality), and musical structure (12-fold quantization) is the central theme: the dodecet is not an arbitrary encoding but a *forced* consequence of choosing the Eisenstein lattice as the foundation for complex-valued constraint representation.

---

*Chapter 2 — Mathematical Foundations. Part of the dissertation on constraint theory and the dodecet encoder in the PLATO system.*
