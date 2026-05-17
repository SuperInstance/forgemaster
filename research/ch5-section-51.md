# Chapter 5: Analysis

## 5.1 Introduction

This chapter presents the empirical analysis of three primary experiments and a series of supplementary studies designed to test the central claims of this dissertation. The spine claim—that approximate identity checking achieves its theoretical optimum when the domain's equivalence structure is represented as ideal structure in a cyclotomic integer ring—rests on two empirical pillars: (a) the conservation law governing multi-agent coupling dynamics holds on live operational systems, and (b) the observed coupling structure is consistent with the spectral properties predicted by the Z[ζ₁₂] lattice framework.

Three hypotheses, derived from the theoretical framework in Chapter 3 and the experimental design in Chapter 4, structure the analysis:

- **H1:** The conserved quantity γ + H, combining the algebraic connectivity (spectral gap) and normalized spectral entropy of the fleet coupling matrix, remains approximately constant during live multi-agent interaction, consistent with the theoretical prediction γ + H = 1.283 − 0.159·ln(*V*).

- **H2:** The coupling matrix of live LLM fleets converges to rank-1 structure (γ → 0), reflecting semantic uniformity arising from shared training data—a signature consistent with the cyclotomic lattice's projection onto a dominant subspace.

- **H3:** Attention-weighted coupling, rather than Hebbian accumulation, is the generative mechanism producing the conservation law's characteristic decreasing slope, establishing selective routing as the architectural prerequisite for lattice-consistent dynamics.

The chapter is organized in three movements. Sections 5.2–5.4 present the three primary experiments in sequence, each building on the previous: E1 establishes the conservation law on live systems, E2 reveals its scaling behavior and the γ → 0 collapse, and E3 identifies the causal mechanism. Sections 5.5 and 5.6 present two enabling-condition analyses—the Vocabulary Wall and the Stage Model—that explain *when* and *why* the conservation law is observable, establishing preconditions for fleet participation. Section 5.7 synthesizes these findings into a unified account of the conservation law as a Noether-type symmetry of the cyclotomic snap, and Section 5.8 summarizes the hypothesis dispositions and effect sizes that carry forward to the discussion in Chapter 6.

All analyses were conducted using Python 3.11 with NumPy 1.26, SciPy 1.12, and NetworkX 3.2. An α level of .05 was adopted for all inferential tests unless otherwise noted. Bonferroni corrections were applied where multiple comparisons were conducted. Effect sizes (Cohen's *d*, Pearson's *r*, and R²) are reported following American Psychological Association (APA, 7th edition) guidelines.
