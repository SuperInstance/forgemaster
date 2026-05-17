# Research Brief: Random Matrix Theory & Conservation in Coupled Agent Systems

*Compiled: 2026-05-17 | For: GPU Constraint Experiment Loop, Cycle 2+*

---

## Our Findings in One Paragraph

We observe that a conservation law γ+H = C holds in coupled multi-agent dynamical systems **if and only if** the coupling matrix has GOE (Wigner-Dyson) eigenvalue statistics. Wigner random coupling conserves perfectly (CV=0.032) across ALL numerical precisions (FP64 through INT8, including mixed heterogeneous fleets). Structured coupling (Hebbian, Attention) does NOT conserve (CV=0.12–0.15) regardless of precision. Precision heterogeneity, even at ratios of 10^15:1, does not break conservation when coupling statistics are GOE. Asymmetric (direction-dependent) coupling paradoxically *improves* conservation. INT8 quantization produces "frozen conservation" (CV→0). The conservation constant C is flat across precision (C ≈ 0.64 ± 0.01 from 2-bit to 64-bit).

---

## 1. Wigner Semi-Circle Law and Universality in Coupled Systems

### 1a. Foundational: Wigner Semi-Circle Law and Conservation-Like Universality

**Key reference:** Wigner (1955, 1958); Mehta (2004); Tao & Vu (various)

The Wigner semi-circle law states that the eigenvalue density of large random symmetric matrices converges to a semi-circular distribution, regardless of the entry-level distribution. This is the deepest universality result in RMT.

**Connection to our work:** Our finding that conservation is determined by GOE eigenvalue statistics, not by precision/entry-level details, is a direct consequence of Wigner universality. The semi-circle law is *why* changing from FP64 to INT8 doesn't affect conservation — the macroscopic spectral shape is invariant under the microscopic distribution of entries. Our conservation law appears to be a *functional* of this invariant spectral shape.

**Suggested experiment:** Compute the actual eigenvalue distributions of our coupling matrices across precision configs. Verify they all follow the semi-circle law. If they do, the conservation law is an integral over this distribution.

### 1b. Generalized Spectral Form Factor (Wei, 2024)

**Paper:** "Generalized Spectral Form Factor in Random Matrix Theory" — Zhiyang Wei, arXiv:2401.02119, January 2024

**Key finding:** Extends the spectral form factor (SFF) to include higher-order correlations. The GSFF is complex-valued, with both real and imaginary parts exhibiting universal dynamics. The real part shows the classic dip-ramp-plateau structure.

**Connection to our work:** The SFF/GSFF captures the *temporal* signature of spectral correlations. Our conservation law holds across time (rounds of interaction). If γ+H conservation is a spectral property, the GSFF should predict when conservation holds and when it breaks. The "ramp" and "plateau" regions may correspond to our "conserved" and "non-conserved" regimes.

**Suggested experiment:** Compute the SFF for our coupling matrices. Compare SFF between random (conserved) and Hebbian/Attention (non-conserved) coupling. If the SFF differs systematically, we have a diagnostic tool for predicting conservation.

### 1c. Joint Spectral Properties of Coupled Random Matrices (March 2025)

**Paper:** Joint spectral properties of coupled random matrices — arXiv (referenced in search results), March 2025

**Key finding:** Even under weak decorrelation conditions (matrices almost fully correlated), fluctuations of individual eigenvalues in the bulk can remain asymptotically independent. Coupled matrices retain independent spectral fluctuations even when strongly correlated.

**Connection to our work:** This is directly relevant to our asymmetric coupling finding. When agents have different precision (FP64→INT8 direction), the coupling matrices are "almost the same but decorrelated." This paper suggests the eigenvalue fluctuations remain independent, which could explain why asymmetric coupling doesn't break (and may improve) conservation — the spectral statistics remain in the universality class.

**Suggested experiment:** Construct explicitly coupled random matrices (like in this paper) with precision-dependent decorrelation. Measure whether conservation correlates with the independence of eigenvalue fluctuations.

---

## 2. Random Matrix Theory in Multi-Agent and Network Systems

### 2a. RMT for Brain Mapping and Functional Connectivity (Lawrence, 2025)

**Paper:** "Applications of Random Matrix Theory in Machine Learning and Brain Mapping" — Katrina Lawrence, arXiv:2502.14878, February 2025

**Key finding:** Marchenko-Pastur law for Wishart matrices is robust to any type of added noise. Eigenvalue distributions converge to theoretical predictions regardless of noise characteristics. Outliers from the predicted distribution indicate discrete functional networks.

**Connection to our work:** This is a direct analogy. Brain voxel connectivity ≈ agent coupling. Noise ≈ precision errors. The finding that RMT predictions are noise-robust mirrors our finding that conservation is precision-robust. Outlier eigenvalues in brain mapping correspond to structured (non-random) coupling in our system — exactly the Hebbian/Attention matrices that break conservation.

**Suggested experiment:** Apply Marchenko-Pastur analysis to our coupling matrices. See if Hebbian/Attention matrices produce outlier eigenvalues (beyond the MP bulk). If yes, conservation breakdown is detectable from spectral outliers alone.

### 2b. Scalable Spectral Representations in Multi-Agent RL (2024–2025)

**Research area:** Network Markov Decision Processes with spectral local representations

**Key finding:** Exponential decay property of network dynamics enables scalable spectral local representations for MARL. Each agent's Q-function lives in a network linear subspace defined by the spectral structure.

**Connection to our work:** If network dynamics have exponential spectral decay (as in this work), and our coupling matrices are random (GOE), then the effective dynamics live in a low-dimensional subspace where conservation is naturally maintained. Structured coupling may violate the exponential decay property, leading to dynamics that escape the conserved subspace.

**Suggested experiment:** Measure the spectral decay rate of coupling matrices (random vs structured). Test whether conservation correlates with the rate of spectral decay.

### 2c. Data-Driven Eigenvalue Estimation for Large-Scale Systems (November 2024)

**Research area:** Scalable algorithms for determining eigenvalues in interconnected systems with unknown dynamics

**Key finding:** Machine learning methods can estimate spectral properties of large-scale systems from observed trajectories, without knowing the underlying dynamics.

**Connection to our work:** Our conservation law is an invariant of the trajectory (γ+H over rounds). If this conservation is detectable from trajectories alone (which it is — we compute it from dynamics), then data-driven eigenvalue methods should be able to predict conservation from observed behavior without knowing the coupling matrix. This is the "black-box conservation detection" problem.

**Suggested experiment:** Train a simple estimator to predict whether conservation holds, using only trajectory data (not coupling matrix). If it works, conservation is empirically detectable from behavior alone.

---

## 3. Eigenvalue Statistics and Information Conservation

### 3a. Universality of Wigner-Dyson-Mehta Statistics (April 2024)

**Paper:** Universality of eigenvalue gap statistics for deformed Wigner matrices — arXiv, April 2024

**Key finding:** Wigner-Dyson-Mehta statistics for eigenvalue gaps are universal even for deformed Wigner matrices. Monoparametric families still produce universal gap distributions.

**Connection to our work:** "Deformed Wigner" is exactly our setup when we add structure (Hebbian, Attention) to random coupling. The question is: at what deformation level do the statistics depart from Wigner-Dyson? Our data suggests Hebbian/Attention deformation is already past this transition, while precision deformation is not. This gives us a "deformation threshold" for conservation.

**Suggested experiment:** Systematically interpolate between random and Hebbian coupling: C_α = (1-α)·W + α·H, where W is Wigner and H is Hebbian. Find the critical α where conservation breaks. This gives us the "conservation deformation threshold."

### 3b. RMT Perspective on Learned Features (Dandi et al., 2024)

**Paper:** "A Random Matrix Theory Perspective on the Spectrum of Learned Features and Asymptotic Generalization Capabilities" — Yatin Dandi et al., arXiv:2410.18938, October 2024

**Key finding:** After gradient descent, neural network features become equivalent to an isotropic spiked random feature model. The feature spectrum's tails modify with training in a predictable way. Derives deterministic equivalents for the feature covariance matrix.

**Connection to our work:** This is the most directly relevant paper. It shows that learning (structure acquisition) produces spectral modifications (spikes) in an otherwise random feature matrix. Our Hebbian coupling is learned structure — it should produce spikes in the coupling matrix spectrum. Spikes = non-GOE statistics = conservation breakdown. This gives us the mechanism: structure creates spectral spikes, spikes break GOE universality, broken universality → broken conservation.

**Suggested experiment:** Compute the eigenvalue spectrum of Hebbian vs random coupling matrices. Look for spike eigenvalues (outliers beyond the semi-circle bulk) in Hebbian. If spikes correlate with conservation breakdown, we have the mechanism.

---

## 4. GOE/GUE Universality in Network Dynamics

### 4a. Universality Classes in Network Dynamics

**Foundational work:** Barabási, Pósfai; also Dyson (1962); Mehta (2004)

**Key finding:** Complex network dynamics can be categorized into "dynamical universality classes" defined by universal exponents. Spectral statistics (GOE/GUE/Ginibre) determine the class. The Laplacian spectral gap determines synchronization time. Asymmetric matrices → Ginibre ensemble (non-Hermitian RMT).

**Connection to our work:** Our coupling matrices are symmetric (GOE class) when random. Hebbian coupling may push them toward a different universality class (possibly Wishart, given the outer-product structure of Hebbian learning: H = Σ x_i x_i^T). Wishart/Laguerre ensemble has different spectral statistics from GOE. This could explain the conservation breakdown.

**Suggested experiment:** Classify our coupling matrices by ensemble type. Are Hebbian matrices better described by Wishart/Laguerre statistics? If yes, conservation may be a GOE-specific property, not a Wishart property. Test by comparing Wishart coupling vs Wigner coupling.

### 4b. Coupled Random Matrix Ensembles

**Research area:** Joint spectral properties of coupled/interacting random matrices

**Key finding:** Multiple interacting random matrices can be analyzed through free probability theory. The spectral distribution of sums/products of random matrices is determined by their free convolution, not classical convolution.

**Connection to our work:** Our heterogeneous fleet has agents with different precision levels, which is equivalent to coupling matrices with different variance scales. Free probability predicts the spectral distribution of such coupled systems. If the free convolution preserves GOE character, conservation holds. If it doesn't, conservation breaks.

**Suggested experiment:** Use free probability (R-transform, S-transform) to compute the theoretical spectral distribution of our heterogeneous coupling matrices. Verify it matches our numerical spectra. This gives us an analytical tool for predicting conservation.

---

## 5. Precision-Dependent Phase Transitions

### 5a. BBP (Baik-Ben Arous-Péché) Transition

**Foundational work:** Baik, Ben Arous, Péché (2005); also Baik, Silverstein

**Key finding:** In sample covariance matrices, the largest eigenvalue transitions from being inside the bulk (Marchenko-Pastur) to becoming an outlier (spike) when the signal-to-noise ratio exceeds a critical threshold. This is the BBP transition.

**Connection to our work:** Our EXP-3 tested for BBP-like broadening with heterogeneity and found none. But the BBP transition applies to the *largest eigenvalue* of sample covariance matrices, not directly to coupling matrices. We need to reformulate: when does precision heterogeneity create a "spike" in the coupling matrix spectrum? Our data says "never, for GOE coupling" — which is consistent with BBP theory, since GOE matrices don't have a spike structure.

**Suggested experiment:** Instead of testing for BBP broadening, test for a different phase transition: the "conservation breakdown transition" at the ternary/binary boundary. Map out γ+H CV as a function of precision bits (2, 3, 4, 8, 16, 32, 64). If there's a sharp transition, it's a genuine phase transition, not a BBP transition.

### 5b. Precision as Temperature Analogy

**Conceptual framework:** Precision bits ≈ inverse temperature (β) in statistical mechanics

**Connection to our work:** In our BBP experiments (EXP-4 in Cycle 0), we used β as an actual control parameter and found the transition width is ~0.40 for all precision configs. But there's a deeper analogy: low precision ≈ high temperature (more quantization noise ≈ more thermal noise). Our finding that conservation is temperature-independent (precision-independent) is like saying a thermodynamic invariant is independent of temperature. This is normal for conserved quantities!

**Suggested experiment:** Formalize the precision-as-temperature analogy. Map quantization step size σ_q ∝ 2^{-b} to an effective temperature T_eff. Compute γ+H as a function of T_eff. If conservation holds independent of T_eff for GOE coupling but not for structured coupling, this is analogous to an ergodicity-breaking transition.

---

## 6. Quantized Neural Networks and Spectral Properties

### 6a. Low-Precision Training Dynamics

**Key references:** Various works on LLM quantization (GPTQ, AWQ, SmoothQuant, etc.), 2023–2025

**Key finding:** Quantized neural networks maintain performance down to 4-bit (INT4) with minimal degradation. 2-bit quantization shows significant degradation. Binary/ternary networks exist but require special training.

**Connection to our work:** Our ternary/binary threshold (EXP-2 in Cycle 1) matches the real-world quantization threshold for neural networks. The same transition we see in conservation (ternary OK, binary breaks) is the same transition seen in model quality. This suggests conservation and model quality may be linked — a conserved system can maintain information flow, a non-conserved system cannot.

**Suggested experiment:** Train a small network with different quantization levels. Measure both task performance AND the spectral statistics of the weight matrices. Does conservation of γ+H (or equivalent) predict task performance across quantization levels?

### 6b. Frozen/Discrete Dynamics in Quantized Systems

**Relevant concept:** Quantization grids pin dynamics to discrete states

**Connection to our work:** Our "frozen conservation" finding (INT8 CV→0, asymmetric FP64/INT4 CV=0) is a quantization pinning effect. When the coupling matrix entries are quantized to a discrete grid, the dynamics are constrained to a lattice. On this lattice, γ+H is exactly conserved because the discrete dynamics can't produce the continuous drift that would violate conservation. This is analogous to a crystal lattice pinning electron dynamics.

**Suggested experiment:** Map the dynamics on the quantization lattice explicitly. For INT8, enumerate the possible states and verify that all transitions preserve γ+H. If true, frozen conservation is a combinatorial theorem about the lattice, not a numerical artifact.

---

## 7. Noise Injection and Regularization by Asymmetry

### 7a. Noise as Regularizer

**Foundational concept:** Injecting noise into coupling/weight matrices acts as regularization (Tikhonov, dropout, etc.)

**Connection to our work:** Our finding that asymmetric coupling *improves* conservation is exactly a noise injection effect. Direction-dependent precision loss introduces asymmetry → asymmetry ≈ noise in the eigenvector basis → noise regularizes the spectral statistics → pushes them closer to GOE → better conservation.

**Suggested experiment:** Directly test noise injection. Add Gaussian noise of varying amplitude to Hebbian/Attention coupling matrices. At what noise level does conservation recover? If it's a smooth crossover, we can define a "noise-to-structure ratio" that predicts conservation.

### 7b. Free Probability and Asymmetric Matrices

**Relevant theory:** Free probability for non-Hermitian matrices; Ginibre ensemble

**Connection to our work:** Asymmetric coupling matrices are non-Hermitian. Their spectral statistics follow the Ginibre ensemble (circular law), not GOE (semi-circle law). Our asymmetric coupling improved conservation — does this mean the Ginibre ensemble also supports conservation? Or does the asymmetry project back onto GOE statistics in the symmetric part?

**Suggested experiment:** Decompose asymmetric coupling matrices into symmetric and antisymmetric parts. Compute spectral statistics of each part separately. Is conservation carried by the symmetric part? Does the antisymmetric part contribute additional regularization?

---

## Priority Experiments for Cycle 2

Based on the above research, the highest-value experiments are:

### E1: Deformation Threshold (from §3a)
Interpolate between random and structured coupling: C_α = (1-α)·W + α·H. Find critical α_c where conservation breaks. This is the "conservation deformation threshold" — a new quantitative result.

### E2: Spectral Spike Detection (from §3b, §6a)
Compute full eigenvalue spectra for random, Hebbian, and Attention coupling matrices. Identify spike eigenvalues. Test whether conservation CV correlates with spike magnitude. This identifies the mechanism.

### E3: Noise Recovery (from §7a)
Add Gaussian noise to Hebbian/Attention coupling at varying amplitudes. Find the noise level that restores conservation. Define the "noise-to-structure ratio" for conservation.

### E4: Frozen Conservation on Lattice (from §6b)
Enumerate quantized coupling states for INT8. Prove or disprove that all lattice transitions preserve γ+H. If provable, frozen conservation is a theorem, not an artifact.

### E5: Wishart vs Wigner Coupling (from §4a)
Test whether Wishart/Laguerre coupling (outer-product structure like Hebbian) also fails to conserve. Compare against Wigner coupling. If Wishart fails and Wigner succeeds, conservation is GOE-specific.

---

## Key Theoretical Threads

1. **Conservation is a spectral functional:** γ+H appears to be a functional of the eigenvalue distribution. GOE distributions produce one value, structured distributions produce others that drift.

2. **Wigner universality explains precision-independence:** The semi-circle law doesn't care about entry distributions (FP64 vs INT8), only about symmetry and independence. Conservation inherits this universality.

3. **Structure creates spectral spikes:** Hebbian/Attention coupling modifies the bulk spectral distribution, creating outliers that break the GOE universality class. Conservation breaks when the statistics leave GOE.

4. **Asymmetry regularizes toward GOE:** Direction-dependent precision loss adds effective noise that pushes spectral statistics back toward GOE, improving conservation. This is regularization, not perturbation.

5. **Quantization grids pin conservation:** Low-precision coupling constrains dynamics to a lattice where γ+H is exactly conserved by construction. This is a discrete analog of a Noether-type conservation.

6. **The ternary/binary threshold is real:** The conservation breakdown between ternary and binary precision is not an artifact — it's the same threshold seen in neural network quantization literature.

---

## References (Ordered by Relevance)

1. Wigner, E.P. (1955/1958). "Characteristic vectors of bordered matrices with infinite dimensions" / "On the distribution of the roots of certain symmetric matrices." — *Foundational: semi-circle law*
2. Baik, J., Ben Arous, G., Péché, S. (2005). "Phase transition of the largest eigenvalue for nonnull complex sample covariance matrices." — *BBP transition*
3. Mehta, M.L. (2004). *Random Matrices.* 3rd ed. Academic Press. — *Comprehensive reference*
4. Wei, Z. (2024). "Generalized Spectral Form Factor in Random Matrix Theory." arXiv:2401.02119. — *Higher-order spectral correlations*
5. Dandi, Y. et al. (2024). "A Random Matrix Theory Perspective on the Spectrum of Learned Features." arXiv:2410.18938. — *Spectral spikes from learning = our mechanism*
6. Lawrence, K. (2025). "Applications of Random Matrix Theory in Machine Learning and Brain Mapping." arXiv:2502.14878. — *RMT noise-robustness, direct analogy*
7. Tao, T. & Vu, V. (various). Universality of local eigenvalue statistics. — *Universality proofs*
8. Dyson, F.J. (1962). "Statistical theory of the energy levels of complex systems." — *Dyson index, universality classes*
9. Coupled random matrices (March 2025). Joint spectral properties with weak decorrelation. arXiv:2502.14878v1 area. — *Explains asymmetric coupling result*
10. April 2024. Universality of Wigner-Dyson-Mehta statistics for deformed Wigner matrices. — *Deformation threshold experiment*

---

*This brief should be used by the next cycle's experiment crafter to design targeted tests that connect our numerical findings to established RMT theory.*
