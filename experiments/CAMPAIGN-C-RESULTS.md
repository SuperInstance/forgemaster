# Campaign C Results — Terrain-Weighted Consensus Voting

## What We Tested

9 claims across 4 knowledge domains. 5 agents vote on each claim. Compare uniform majority (1 agent = 1 vote) vs terrain-weighted (closer agents count more).

## Key Finding: Model Quality Dominates Terrain Proximity

**Overall accuracy: 33% for both uniform and terrain-weighted voting.**

The terrain weighting didn't help because phi4-mini simply doesn't know the domain facts. Terrain proximity can't compensate for model ignorance. You can't weight your way to knowledge that doesn't exist.

## The ONE Gold Nugget: CCC's Domain Proximity Effect

| Agent | Overall | When Close (dist ≤ 2) | Closest Domain |
|-------|---------|----------------------|----------------|
| **CCC** | 4/9 (44%) | **4/5 (80%)** | infrastructure |
| Forgemaster | 4/9 (44%) | 2/7 (29%) | constraint-theory |
| Oracle1 | 3/9 (33%) | 1/7 (14%) | music-encoding |
| Spectra | 3/9 (33%) | 0/0 (N/A) | far from all |
| Navigator | 3/9 (33%) | 0/0 (N/A) | far from all |

CCC scored **80% when close** to its domain (infrastructure). The Docker claim (easy, close) and K8s claim (medium, close) were both correct. This is the ONLY signal that terrain proximity matters — but only when the model actually has the knowledge.

## Negative Results (Equally Valuable)

1. **Forgemaster at constraint-theory domain: 29% when close.** The model doesn't know Eisenstein math despite being "placed" there. Terrain position ≠ domain knowledge.

2. **Oracle1 at music-encoding: 14% when close.** Same pattern — persona doesn't confer knowledge.

3. **No disagreements between uniform and weighted.** Zero cases where terrain weighting changed the outcome. The terrain layer is invisible at this model quality level.

4. **Easy claims failed harder than medium.** The "easy" Eisenstein norm claim (always non-negative) got 4/5 FALSE votes. The model doesn't know the math well enough to recognize a basic property.

## Revised Hypothesis

**Terrain weighting is a SECOND-ORDER effect.** It only matters when:
1. Models have sufficient baseline knowledge (≥60% accuracy)
2. Knowledge is UNEVENLY distributed across agents
3. Claims span multiple domains

With phi4-mini at 33% baseline, terrain weighting is noise. But with a model at 70% baseline that's 90% on its domain and 50% on others — terrain weighting would dominate.

**Next experiment:** Use GLM-5-turbo (z.ai, non-reasoning, actually produces content) instead of phi4-mini. Expected: terrain weighting becomes visible at higher model quality.

## Implication for the Fleet

Don't deploy terrain-weighted voting until agents demonstrate ≥60% baseline accuracy on domain claims. The verification system (Campaign A) must pass FIRST. Terrain weighting is optimization, not foundation.

**Build order:**
1. ✅ Campaign A: Verified Agent Cards (baseline accuracy)
2. ✅ Campaign C: Terrain Weighting (second-order optimization — needs better models)
3. 🔜 Campaign B: Retrieval Optimization (independent of model quality)
4. 🔜 Campaign D: FLUX Task Encoding (independent of model quality)
