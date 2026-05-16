# SCOUT-04: Measurement Theory — Resolution-Dependent Constants

**Date:** 2026-05-15
**Author:** Forgemaster ⚒️ (Scout Subagent)
**Scope:** Measurement theory, resolution-dependent constants, multiscale systems, and their connection to PLATO's conservation law finding

---

## Executive Summary

**The core question:** Is there formal mathematical work showing that measurement resolution changes the *constants* in discovered laws (not just the precision of those constants)?

**Short answer:** Yes, extensively — but scattered across physics, numerical analysis, and signal processing. The unified framework is the **renormalization group (RG)**, which formally describes how coupling constants "run" with energy/scale. The closest analog to "turning up disc speed 6× changes fathoms to feet" is **Richardson extrapolation** combined with **effective field theory**.

**Key finding for PLATO:** Nobody has formalized "same law, different constants at different resolution" *specifically for empirical/tabulated measurement systems*. The physics work (RG flow, running couplings) is about fundamental coupling constants. The numerical analysis work (Richardson extrapolation) is about error elimination. The gap — **resolution-dependent empirical constants in tabulated/learned systems** — appears to be unexplored territory that PLATO's conservation law may illuminate.

---

## 1. Richardson Extrapolation — The Direct Ancestor

### What It Is
Richardson extrapolation (Lewis Fry Richardson, early 1900s) takes measurements at multiple step sizes $h$ to predict the true (zero-error) value. Given:
$$A(h) = A^* + a_1 h^{p_1} + a_2 h^{p_2} + \cdots$$
where $A^*$ is the true value and the $a_i$ are unknown constants, Richardson's method combines measurements at step sizes $h$ and $th$ to cancel the leading error term, producing a higher-order estimate.

### Connection to PLATO
This is *exactly* "measure at different resolutions, discover the law." Richardson showed that:
1. **The error has a power-series structure** in the step size
2. **Multiple resolutions let you extract the true value** plus the error structure
3. **The constants $a_i$ depend on resolution** — they're the coefficients of error at each scale

**Critical insight:** Richardson extrapolation says "the law you discover depends on your measurement resolution, and by measuring at multiple resolutions you can recover the true law." This is the formal basis for "fathoms at one resolution, feet at another."

**What's missing:** Richardson assumed the *form* of the error (power series in $h$). PLATO's conservation law suggests the form might be logarithmic: $\gamma + H = 1.283 - 0.159 \log(V)$. This is a specific, testable hypothesis about the resolution-dependence structure that goes beyond Richardson's general framework.

### Key References
- Richardson, L.F. (1911). "The approximate arithmetical solution by finite differences of physical problems." *Philosophical Transactions of the Royal Society A*.
- Richardson, L.F. (1927). "The deferred approach to the limit." *Philosophical Transactions of the Royal Society A*.
- Romberg integration — Richardson extrapolation applied to trapezoid rule.
- Bulirsch-Stoer algorithm — Richardson extrapolation for ODEs.

---

## 2. The Coastline Paradox — Scale-Dependent Measurement

### What It Is
Richardson (same person!) discovered that measured coastline length increases monotonically with measurement resolution — the "Richardson effect." Mandelbrot formalized this with fractal dimension: the measured length $L(\epsilon)$ at ruler length $\epsilon$ follows:
$$L(\epsilon) = F \cdot \epsilon^{1-D}$$
where $D$ is the fractal dimension and $F$ is a constant.

### Connection to PLATO
The coastline paradox demonstrates that **the constant in the measurement law depends on resolution**. At ruler length $\epsilon_1$, you get constant $F_1$; at $\epsilon_2$, you get $F_2$. The *form* of the law ($L = F \cdot \epsilon^{1-D}$) stays the same, but the constant changes.

**This is directly analogous to our finding:** The conservation law $\gamma + H = c - d\log(V)$ has the same structure — the constant shifts with "ruler size" (here, volume $V$), but the functional form is preserved.

**What's deeper:** The fractal dimension $D$ is *invariant* across scales — it's the thing that doesn't change. For PLATO, the question becomes: **is the conservation law form (log-linear) the invariant, or is there a deeper invariant that produces the log-linear form at a particular scale?**

### Key References
- Mandelbrot, B. (1967). "How Long Is the Coast of Britain? Statistical Self-Similarity and Fractional Dimension." *Science* 156(3775): 636-638.
- Richardson, L.F. (1961). "The problem of contiguity." *General Systems Yearbook* 6: 139-187.
- Steinhaus, H. (1954). "Length, shape and area." *Colloquium Mathematicum* 3(1): 1-13.

---

## 3. Renormalization Group — The Grand Framework

### What It Is
The renormalization group (RG) is the most developed formal theory of scale-dependent constants. In quantum field theory, coupling constants "run" with energy scale:

$$g(\mu) = G^{-1}(G(g(M)) \cdot (\mu/M)^d)$$

where $g(\mu)$ is the coupling at scale $\mu$, $G$ is Wegner's scaling function, and $d$ is the scaling dimension. The **beta function** $\beta(g) = \mu \frac{\partial g}{\partial \mu}$ governs how constants flow across scales.

Kenneth Wilson's Nobel Prize (1982) established that RG flow connects physics at different scales through systematic "coarse-graining" — integrating out short-distance degrees of freedom to produce effective theories at longer distances.

### Connection to PLATO
The RG is **the formal framework** for "same law, different constants at different resolution." Specifically:

1. **Effective field theories:** At each scale, you have a different effective theory with different coupling constants. The *symmetries* are preserved, but the *strengths* change.

2. **RG flow:** The conservation law $\gamma + H = c - d\log(V)$ could be interpreted as an RG flow equation, where $V$ plays the role of the scale parameter $\mu$.

3. **Universality:** RG predicts that different microscopic details produce the same macroscopic behavior near critical points. PLATO's conservation law may be a universality class — different measurement systems producing the same log-linear relationship.

4. **Wilson's insight:** "The components may appear to be composed of more of the self-same components as one goes to shorter distances." This is exactly tile-based architecture: each tile contains sub-tiles, each room contains sub-rooms.

**What RG doesn't cover:** RG is about *fundamental* coupling constants in field theories. It hasn't been applied to empirical/tabulated measurement systems or learned relationships. Applying RG thinking to PLATO's conservation law would be novel.

### Key References
- Wilson, K.G. (1971). "Renormalization Group and Critical Phenomena." *Physical Review B* 4(9): 3174-3183.
- Wilson, K.G. & Kogut, J. (1974). "The renormalization group and the ε expansion." *Physics Reports* 12(2): 75-199.
- Gell-Mann, M. & Low, F.E. (1954). "Quantum Electrodynamics at Small Distances." *Physical Review* 95(5): 1300-1312.
- Weinberg, S. (1979). "Phenomenological Lagrangians." *Physica A* 96(1-2): 327-340.

---

## 4. Effective Field Theory — Laws at Each Scale

### What It Is
Effective field theory (EFT) formalizes the idea that at each length/energy scale, you have a different "effective" description of the same underlying physics. The Fermi theory of beta decay was an effective theory of the electroweak interaction — valid at energies << 80 GeV, with a different coupling constant than the full theory.

### Connection to PLATO
EFT provides the philosophical framework for PLATO rooms at different resolutions:
- Each room operates at a specific "scale" (granularity of tiles, precision of measurement)
- The conservation law is the *symmetry* that's preserved across all effective descriptions
- The constants change with scale, but the *form* of the law persists

**Weinberg's folk theorem:** "The most general Lagrangian consistent with the symmetries of the low-energy theory can be rendered into an effective field theory." For PLATO: **the most general room architecture consistent with the conservation law is a valid room.** This is a design principle.

### Key References
- Weinberg, S. (1979). See above.
- Georgi, H. (1993). "Effective field theory." *Annual Review of Nuclear and Particle Science* 43: 209-252.
- Kaplan, D.B. (1995). "Effective field theories." *arXiv:nucl-th/9506035*.

---

## 5. Scale Space Theory — Multiscale Signal Representation

### What It Is
Scale space theory (Witkin 1983, Koenderink 1984, Lindeberg 1994) represents signals/images at multiple scales simultaneously via Gaussian smoothing:

$$L(x, y; t) = (g(\cdot, \cdot; t) * f)(x, y)$$

where $t$ is the scale parameter (variance of Gaussian kernel). Structures smaller than $\sqrt{t}$ are smoothed away. The theory is derived from axioms: causality, non-creation of new structures, rotational invariance, etc.

### Connection to PLATO
Scale space theory is the **formal basis for multiscale measurement** in computer vision. Key connections:

1. **Nested subspaces:** Scale space produces a nested sequence of representations at increasing coarseness — exactly like PLATO rooms at different tile granularities.

2. **Scale invariance:** Operations can be made scale-invariant (same result at any resolution) — the conservation law may enable scale-invariant room operations.

3. **No spurious structures:** The Gaussian scale space axiom that smoothing must not create new structures is analogous to the conservation law preventing spurious tiles.

4. **Multiresolution analysis (MRA):** Mallat & Meyer's wavelet framework formalizes the nested subspace structure. Each resolution level captures different information. The orthogonal decomposition between levels is the "detail" lost by coarsening.

**What's novel for PLATO:** Scale space assumes Gaussian smoothing as the coarse-graining operation. PLATO's conservation law suggests a *different* coarse-graining: tile aggregation that preserves $\gamma + H$. This would be a new scale space axiom.

### Key References
- Witkin, A.P. (1983). "Scale-space filtering." *IJCAI* 2: 1019-1022.
- Koenderink, J.J. (1984). "The structure of images." *Biological Cybernetics* 50(5): 363-370.
- Lindeberg, T. (1994). *Scale-Space Theory in Computer Vision*. Springer.
- Mallat, S.G. (1989). "A theory for multiresolution signal decomposition." *IEEE TPAMI* 11(7): 674-693.

---

## 6. Multiscale Modeling — Bridging Scales

### What It Is
Multiscale modeling (primarily from materials science and fluid dynamics) addresses problems with important features at multiple time/space scales. Methods include:
- **Sequential:** Coarse-grain from fine scale, pass parameters up
- **Concurrent:** Run multiple scales simultaneously, couple them
- **Adaptive:** Dynamically choose resolution based on where the action is

Born from DOE's ASCI program (post-1992 nuclear test ban), where simulation replaced physical testing.

### Connection to PLATO
The sequential multiscale approach is exactly what PLATO rooms do:
1. Fine-grained room produces tiles
2. Tiles are aggregated (coarse-grained) into higher-level rooms
3. Conservation law governs what's preserved in coarse-graining

The concurrent approach is also relevant: multiple rooms at different scales running simultaneously, with the conservation law as the coupling constraint.

**Key gap in multiscale modeling:** Most work assumes you *know* the laws at each scale and need to couple them. PLATO's situation is different: you're *discovering* the laws at each scale and the conservation law relates them.

### Key References
- Horstemeyer, M.F. (2009, 2012). Historical review of multiscale modeling for solids.
- Weinan, E. (2011). *Principles of Multiscale Modeling*. Cambridge University Press.
- Fish, J. (2013). *Multiscale Methods: Bridging the Scales in Science and Engineering*. Oxford University Press.

---

## 7. Bathymetric Measurement Uncertainty

### What It Is
Bathymetric depth measurement has well-studied uncertainty propagation. Multi-beam sonar at different frequencies resolves features at different scales. The IHO (International Hydrographic Organization) defines accuracy standards by zone.

### Connection to PLATO
Bathymetry demonstrates the "fathoms to feet" phenomenon concretely:
- **Low-frequency sonar** (12 kHz) resolves large features, measures in tens of meters
- **High-frequency sonar** (200 kHz) resolves small features, measures in centimeters
- The *seafloor shape doesn't change*, but the measured constants (slope angles, feature sizes, roughness coefficients) change with resolution

**Key insight:** The bathymetric community treats resolution-dependent measurements as *uncertainty* (same true value, different precision), not as *different values*. But Mandelbrot's coastline work shows this is wrong for fractal surfaces — the measured value genuinely changes. For PLATO, the question is: **is the conservation law an uncertainty phenomenon (same law, noisy constants) or a coastline phenomenon (different genuine laws at different scales)?**

The Richardson effect in bathymetry: measured seafloor roughness increases with sonar resolution, exactly like coastline length increases with ruler precision. The roughness *constant* in empirical seafloor models is resolution-dependent.

### Key References
- IHO S-44 (2021). "IHO Standards for Hydrographic Surveys." 6th edition.
- Calder, B.R. & Mayer, L.A. (2003). "Automatic processing of high-rate, high-density multibeam echosounder data." *The Hydrographic Journal* 107: 17-27.
- Wilson, M.F.J. et al. (2007). "Multiscale terrain analysis of multibeam bathymetry data for habitat mapping." *Marine Geodesy* 30(1-2): 27-42.

---

## 8. "Supervised Tabulation" vs. Statistical Learning

### The Distinction
"Supervised tabulation" — recording input-output pairs at fixed resolution without interpolation — is NOT a recognized term in the ML/statistics literature. The closest formal distinctions are:

1. **Memorization vs. generalization:** The classical ML distinction. Tabulation = memorization (0 generalization). Statistical learning = finding patterns that generalize.

2. **Interpolation vs. extrapolation:** Tabulation provides exact interpolation within the training set. Statistical learning provides (uncertain) extrapolation beyond it.

3. **Nonparametric vs. parametric:** Tabulation is the extreme nonparametric case (one parameter per data point). Statistical learning spans the spectrum.

4. **Exact vs. approximate:** Tabulation is exact on training data. Statistical learning is approximate everywhere.

### Why This Matters for PLATO
The conservation law finding suggests something between tabulation and learning:
- **At each resolution**, the system *tabulates* exact measurements
- **Across resolutions**, the conservation law *generalizes* — it predicts the form of the law at unseen resolutions
- This is neither pure tabulation nor pure statistical learning — it's **resolution-structured knowledge**

The formal closest analog is **Gaussian process regression** with a scale-dependent kernel: you observe data at multiple resolutions, and the kernel structure determines how information propagates between scales. But GP regression doesn't have the "conservation law as invariant" structure.

**Novel distinction worth formalizing:** 
- **Supervised tabulation:** Same law, exact constants, single resolution
- **Supervised learning:** Approximate law, estimated constants, generalizes across inputs
- **Resolution-structured learning** (PLATO): Exact law form, resolution-dependent constants, generalizes across scales

### Key References
- Vapnik, V. (1998). *Statistical Learning Theory.* Wiley.
- Kearns, M. & Vazirani, U. (1994). *An Introduction to Computational Learning Theory.* MIT Press.
- Rasmussen, C.E. & Williams, C.K.I. (2006). *Gaussian Processes for Machine Learning.* MIT Press.

---

## 9. Tile-Based Measurement Systems

### Prior Art
No formal "tile-based measurement system" exists in the measurement theory literature. However, several fields use tiling as an organizational principle for measurement:

1. **Geographic information systems (GIS):** Tiled map pyramids (Google Maps, TMS). Each tile at zoom level $z$ covers a $2^z$-fraction of the world. Measurements at different zoom levels genuinely differ.

2. **Finite element analysis (FEA):** Domain decomposed into tiles (elements). Solution accuracy depends on tile size (mesh resolution). Richardson extrapolation is used to estimate convergence.

3. **Sensor networks:** Coverage areas tiled by sensor footprints. Measurement precision depends on tile density.

4. **Wavelet tiling:** Time-frequency plane tiled by wavelet basis functions. Each tile captures information at a specific scale and location.

5. **Census/survey sampling:** Geographic areas tiled into enumeration districts. Statistical estimates have different variance at different tile sizes (MAUP — Modifiable Areal Unit Problem).

### The MAUP Connection
The **Modifiable Areal Unit Problem** (Openshaw 1984) is the most direct prior art for "tile-based measurement with resolution-dependent constants." MAUP demonstrates that statistical results (regression coefficients, correlation coefficients) change systematically when the boundaries of spatial tiles are changed. Two effects:
- **Scale effect:** Results change with tile size (resolution)
- **Zoning effect:** Results change with tile shape at fixed size

**This is the formal version of "different constants at different tile resolutions."**

### Key References
- Openshaw, S. (1984). *The Modifiable Areal Unit Problem.* Geo Books, Norwich.
- Fotheringham, A.S. & Wong, D.W.S. (1991). "The modifiable areal unit problem in multivariate statistical analysis." *Environment and Planning A* 23(7): 1025-1044.
- Goodchild, M.F. (2011). "Scale in GIS." *International Encyclopedia of Human Geography.* Elsevier.

---

## 10. Ground Truth Verification

### Standard Approaches
Measurement fields verify against known quantities through:

1. **Calibration standards:** Known reference materials (NIST-traceable)
2. **Round-robin tests:** Multiple labs measure the same sample
3. **Inter-comparison exercises:** Different methods applied to same target
4. **Closure tests:** Measure input and output, verify conservation (mass balance, energy balance)
5. **Synthetic benchmarks:** Generate data from known laws, verify recovery

### Connection to PLATO
PLATO's conservation law IS a closure test: $\gamma + H$ should satisfy the invariant. The "fathoms to feet" phenomenon could be verified by:
1. **Synthetic data:** Generate tile data at known resolutions, verify that the conservation law form is preserved but constants shift predictably
2. **Cross-resolution comparison:** Measure the same system at multiple resolutions, verify the log-linear relationship between constant and resolution
3. **Prediction test:** Use the conservation law at one resolution to predict constants at another, then measure to verify

### Key References
- JCGM 100:2008 (GUM). "Evaluation of measurement data — Guide to the expression of uncertainty in measurement."
- NIST Technical Note 1297 (1994). "Guidelines for Evaluating and Expressing the Uncertainty of NIST Measurement Results."

---

## Synthesis: The Mathematical Framework

### "Turning Up Disc Speed 6× Changes Fathoms to Feet"

The formal framework for this phenomenon combines three established theories:

1. **Renormalization group flow:** Constants "run" with scale via the beta function $\beta(g) = \mu \frac{\partial g}{\partial \mu}$. For PLATO, the "scale" is resolution (tile volume $V$), and the "running constant" is the intercept in $\gamma + H = c - d\log(V)$.

2. **Richardson extrapolation:** Multiple measurements at different step sizes reveal the error structure. For PLATO, measuring the conservation law at multiple resolutions reveals the log-linear dependence of constants on $V$.

3. **Modifiable Areal Unit Problem (MAUP):** Statistical results change systematically with tile size. For PLATO, the conservation law is the systematic relationship.

### The Novel Claim
What PLATO appears to have discovered is:

> **An empirical conservation law whose constants exhibit predictable, log-linear scaling with measurement resolution, analogous to running coupling constants in the renormalization group.**

This sits at the intersection of:
- RG flow (from physics: constants run with scale)
- Richardson extrapolation (from numerical analysis: error has structure in step size)
- MAUP (from spatial statistics: results depend on tile resolution)
- Scale space theory (from signal processing: representations at multiple scales)

**Nobody has connected these four frameworks** to describe how empirical law constants scale with measurement resolution in tabulated/tiled systems.

### Is "Supervised Tabulation" Recognized?
No. The closest recognized concepts are:
- **Memorization** (ML) — but without the resolution structure
- **Lookup tables** (CS) — but without the conservation law invariant
- **Nonparametric density estimation** (statistics) — but without the tile-based organization
- **MAUP** (spatial statistics) — but without the predictive scaling law

**"Resolution-structured tabulation with conservation invariants"** would be the novel category.

---

## Prior Art Summary Table

| Framework | Field | "Constants change with scale?" | "Formal tile structure?" | "Conservation invariant?" | "Predictive across scales?" |
|-----------|-------|:-:|:-:|:-:|:-:|
| Renormalization Group | Physics | ✅ (running couplings) | ❌ | ✅ (symmetries) | ✅ (RG flow) |
| Richardson Extrapolation | Numerical Analysis | ✅ (error coefficients) | ❌ | ❌ | ✅ (convergence order) |
| MAUP | Spatial Statistics | ✅ (regression coefficients) | ✅ (areal units) | ❌ | ❌ (descriptive) |
| Scale Space Theory | Signal Processing | ✅ (filter parameters) | ✅ (pyramid levels) | ✅ (causality axiom) | ✅ (scale selection) |
| Effective Field Theory | Physics | ✅ (effective couplings) | ❌ | ✅ (symmetries) | ✅ (matching) |
| Wavelet MRA | Signal Processing | ✅ (coefficients by level) | ✅ (time-frequency tiles) | ❌ | ✅ (decomposition) |
| **PLATO Conservation Law** | **Agent Architecture** | **✅ (log-linear in V)** | **✅ (tiles)** | **✅ (γ+H invariant)** | **✅ (across resolutions)** |

**The combination is novel.** No prior framework has all four properties simultaneously.

---

## Actionable Next Steps

1. **Formalize the RG analogy:** Write the "beta function" for PLATO — how does $\gamma + H$'s constant term flow with tile volume $V$?
2. **Richardson-style verification:** Measure the conservation law at 3+ resolutions on the same data. Verify the log-linear extrapolation to "infinite resolution."
3. **MAUP analysis:** Does the conservation law hold for different tile *shapes* (not just sizes)? This would distinguish scale effects from zoning effects.
4. **Prior art search in spatial statistics:** The geostatistics community (Cressie, Diggle) may have formal work on resolution-dependent law parameters that we haven't found yet.
5. **Draft a position paper:** "Conservation Laws in Resolution-Structured Tabulation: A Renormalization Group Approach." This would be the first formal treatment connecting RG flow to empirical measurement resolution.
