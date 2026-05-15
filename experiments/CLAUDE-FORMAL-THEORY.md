`★ Insight ─────────────────────────────────────`
Three structural choices made in this formalization that would draw reviewer scrutiny:

1. **The sigmoid routing equation** uses linear combination inside σ — this is mathematically convenient but assumes additive independence between C-head pull and discourse push. Real attention heads interact multiplicatively through softmax normalization, which is non-linear. A more rigorous formulation would use the full softmax competition term.

2. **β > α > γ ordering** is the core falsifiable claim — it asserts that symbolic substitution is harder for LLMs than formula recall. This is counterintuitive given that retrieval failure (F) is often cited as the main failure mode in mathematical LLM research. Experiment 1 directly tests this.

3. **The τ* = 0.7 specificity argument** (§4.3) is the most mechanistically tight section — it derives the optimum from three independent constraints. This derivation is the most publishable contribution, as it makes a specific quantitative prediction that no prior work (temperature vs. wall) has addressed.
`─────────────────────────────────────────────────`

The document is at `experiments/ARXIV-THEORY-DRAFT.md` — approximately 3,100 words of formal theory across 8 sections.

Key structural decisions:

**What's rigorous:** The routing equation R(T) is fully specified with each term defined independently. The wall activation condition (Theorem 2.1) is a proper derivation from the equation. Stage definitions use numerical bounds from the experimental corpus, not verbal descriptions. All six predictions include explicit falsification conditions, not just directional claims.

**Where epistemic humility is flagged:** §8 explicitly distinguishes behavioral inference from mechanistic measurement — we don't directly observe A_h, W_h, or D(t) inside the model. The "KV cache attractor" and "attention head competition" are mechanistic interpretations consistent with behavior, but not yet confirmed by activation patching.

**The three most novel formal contributions:**
1. The language-conditioned D^(ℓ)(t) extension (§5) — formalizes why no single language is universally safe
2. The τ* = 0.7 derivation from three independent constraints (§4.3) — makes a quantitative temperature prediction
3. The consensus criterion as the stage 4/5 diagnostic (§6.1, Def 6.5) — because majority vote behavior depends on whether immunity is stochastic resistance or structural independence

The six experiments you're running now directly test P1 (coefficient ordering), P3 (first-token commitment), and P4 (temperature optimum).
