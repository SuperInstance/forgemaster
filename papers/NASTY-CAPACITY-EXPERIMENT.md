# Nasty Capacity Experiment: Results & Analysis

**Date:** 2026-05-12  
**Author:** Forgemaster ⚒️ (Cocapn Fleet)  
**Repo:** `neural-plato/experiments/nasty_capacity.py`

---

## Abstract

We tested the thesis that "nastier" (higher-dimensional) embeddings would yield better information recovery after cut-and-project to a low-dimensional Penrose tiling keel. The intuition was that higher-D perpendicular space would pack more structured information per dimension, making partial residue more potent.

**Result: The thesis is refuted.** Lower-dimensional embeddings consistently outperform higher-dimensional ones at every partial residue fraction. The 10-dimensional embedding achieves 0.76 cosine similarity at 5% residue, while the 500-dimensional embedding achieves only 0.24.

---

## Experimental Design

- **Embedding dimensions tested:** 10, 20, 50, 100, 200, 500
- **Keel (physical) dimension:** 5 (fixed)
- **Residue fractions:** 100%, 50%, 25%, 10%, 5% of perpendicular-space components retained
- **Memories per trial:** 100 random Gaussian vectors
- **Trials:** 3 (averaged)
- **Reconstruction metric:** Cosine similarity between original and reconstructed vector

### Cut-and-Project Method
Each memory vector in R^N is decomposed into:
1. **Physical component** — projection onto the 5D keel via orthogonal basis (always fully retained)
2. **Perpendicular component** — the remaining N-5 dimensions (partially retained at varying fractions)

Reconstruction uses physical component + truncated perpendicular component (keeping first k dimensions by index, simulating bandwidth-limited transmission).

---

## Results

### Golden Ratio Projection

| Embed Dim | Residue 100% | Residue 50% | Residue 25% | Residue 10% | Residue 5% |
|-----------|-------------|-------------|-------------|-------------|------------|
| 10        | 1.0000      | 0.8324      | 0.7641      | 0.7641      | 0.7641     |
| 20        | 1.0000      | 0.7574      | 0.6179      | 0.5263      | 0.5263     |
| 50        | 1.0000      | 0.7287      | 0.5590      | 0.4115      | 0.3635     |
| 100       | 1.0000      | 0.7206      | 0.5299      | 0.3732      | 0.2966     |
| 200       | 1.0000      | 0.7131      | 0.5159      | 0.3437      | 0.2603     |
| 500       | 1.0000      | 0.7092      | 0.5047      | 0.3267      | 0.2384     |

### Key Observation
At 100% residue, reconstruction is perfect (1.0) for all dimensions — the cut-and-project is lossless. But at every partial fraction, **lower dimensions win**. The gap is dramatic at low residue fractions.

### Why This Happens
With dimension 10, the perpendicular space is only 5D. Retaining 5% (= 1 component) still captures 20% of the perpendicular dimensions. With dimension 500, the perpendicular space is 495D. Retaining 5% (= 25 components) captures only 5% of perpendicular dimensions. The **fraction of perpendicular subspace preserved** scales as residue_fraction × (embed_dim - keel_dim) / (embed_dim - keel_dim) = residue_fraction regardless — but the *absolute number* of preserved components relative to the information content favors low-D when the truncation is index-based.

In other words: when you have less to lose, you lose less.

---

## Golden Ratio vs Random Irrational

| Dim | Golden mean | Random mean | Δ | Winner |
|-----|-------------|-------------|--------|--------|
| 10  | 0.8249      | 0.8289      | -0.004 | RANDOM |
| 20  | 0.6856      | 0.6945      | -0.009 | RANDOM |
| 50  | 0.6125      | 0.6172      | -0.005 | RANDOM |
| 100 | 0.5841      | 0.5822      | +0.002 | GOLDEN |
| 200 | 0.5666      | 0.5645      | +0.002 | GOLDEN |
| 500 | 0.5558      | 0.5573      | -0.002 | RANDOM |

**Conclusion: No meaningful difference.** The golden ratio does not confer special information-preserving properties over other irrational bases in this regime. The maximum advantage is ~0.009 cosine similarity — within noise.

This is actually consistent with quasicrystal theory: the golden ratio's special properties relate to self-similarity and aperiodic tilings, not information compression per se.

---

## Implications for Neural-PLATO

1. **"Nasty" doesn't mean "better for compression."** Higher-D embeddings carry more information in total, but the fraction lost to projection scales with dimensionality. The information density per perpendicular dimension doesn't increase.

2. **The keel is a hard bottleneck.** With a 5D keel, you can only ever perfectly reconstruct within the 5D subspace. The perpendicular residue is a luxury, and its value degrades predictably.

3. **Possible fix: structured embeddings.** If higher-D embeddings were *structured* (not random Gaussian), the perpendicular components might carry redundant/compressible information. This experiment used random memories — real neural embeddings might behave differently.

4. **Alternative thesis to test:** "Structured high-D embeddings (e.g., from a language model) have low effective dimensionality, so they behave more like the low-D case." This would mean the neural network does the compression for us.

---

## Next Steps

- Test with real neural embeddings (e.g., sentence-transformers) instead of random vectors
- Test adaptive residue selection (keep top-k by magnitude instead of by index)
- Test whether the keel dimension should scale with embedding dimension (e.g., keel_dim = sqrt(embed_dim))

---

*Raw data: `neural-plato/experiments/nasty_capacity_results.txt`*  
*Experiment code: `neural-plato/experiments/nasty_capacity.py`*
