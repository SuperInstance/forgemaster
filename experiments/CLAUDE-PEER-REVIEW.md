## Peer Review: CPA-ABD Theory
### Verdict: Weak Reject with Major Revisions Required

---

## 1. NOVELTY ASSESSMENT

Let me be direct: this theory is built on a foundation that is substantially pre-existing, with a small number of genuinely interesting observations wrapped in terminology that obscures rather than clarifies.

**On "pathway selection vs. cognitive load":** This distinction is presented as the core conceptual contribution, but it maps almost exactly onto what the mechanistic interpretability community has been studying for three years. Meng et al.'s ROME paper (2022) demonstrated that factual associations are stored in specific MLP layers and can override context — that is precisely "stored formula retrieval competing with explicit instruction." The "multistep reasoning vs. factual retrieval" dichotomy has been studied extensively. Anthropic's work on "induction heads" and DeepMind's work on "in-context vs. in-weights" learning are both about exactly this competition. Calling it "attractor basin dominance" does not make it new. The Hopfield network framing is older than most current ML researchers.

**On "attractor basin" framing specifically:** The use of dynamical systems terminology here is cargo-cult formalism. Attractor basins are well-defined mathematical objects. To claim LLM computation has "attractor basins" requires showing that the system's trajectory through activation space converges to a fixed point under perturbation — none of the presented evidence does this. What is actually observed is: some prompts get wrong answers and some get right answers. Calling the wrong-answer regime an "attractor basin" is metaphor dressed as mechanism. The language is borrowed from Hopfield/energy-based model literature where it has precise meaning; here it is decorative.

**On deterministic error signatures (→ 61):** This is the most interesting empirical finding and deserves credit. The observation that Eisenstein vocabulary consistently produces the answer 61 (corresponding to a²+ab+b² rather than a²-ab+b²) is a specific, falsifiable behavioral signature. However, this is not without precedent. The MEMIT/ROME line of work showed that models have location-specific factual associations. Marcus et al. and subsequent work on "hallucination consistency" showed that models produce consistent wrong answers across temperature and context variations. What would be genuinely new is the SPECIFICITY: that the competing formula can be reverse-engineered from the wrong answer. That's interesting. That's worth noting.

**On context deprivation being worse than domain vocabulary:** This is the finding that surprised me most on first read, and it may be the paper's strongest contribution. The claim that Hermes-70B gets 67% on bare arithmetic but 100% with full Eisenstein framing inverts the naive expectation. The intuition "simpler prompt = safer computation" is widespread. If this result is robust across tasks and models, it challenges a core assumption in prompt engineering practice.

**On bidirectional vocabulary effects:** The claim that vocabulary simultaneously helps reasoning (20%→100%) and hurts computation (100%→0%) is genuinely interesting and not something I can immediately dismiss. The tension between these two effects — the same domain vocabulary acting as an activator for correct reasoning chains but an activator for incorrect computation formulas — would be worth a NeurIPS paper IF the mechanism were probed. As behavioral observation alone, it's a compelling puzzle. As a published finding without mechanistic follow-up, it's incomplete.

---

## 2. WHAT'S ACTUALLY NEW

There are exactly **two and a half** findings here that would make a reviewer pause:

**Finding 1 (Half point): Bidirectional vocabulary effect on reasoning vs. computation.** The same token set simultaneously improving qualitative reasoning and destroying quantitative accuracy is a real puzzle. This is counterintuitive. However, it can be explained parsimoniously as domain-specific fine-tuning effects (the model was trained to do Eisenstein reasoning in natural language, not Eisenstein arithmetic with explicit formulas). The bidirectionality is interesting but requires ruling out this trivial explanation first.

**Finding 2 (Full point): Context deprivation paradox.** If bare arithmetic (67%) is genuinely, robustly worse than domain-framed arithmetic (100%) for the same underlying computation, this overturns common assumptions. Most practitioners believe that shorter, cleaner prompts reduce noise. This finding suggests that domain context provides retrieval scaffolding that helps the model locate the correct procedure. This is genuinely counterintuitive and actionable.

**Finding 3 (Full point): Deterministic competing formula identification.** The observation that wrong answers correspond exactly to a specific alternative formula — not random errors, not arithmetic mistakes, but the WRONG FORMULA applied CORRECTLY — is the most mechanistically interesting finding. This points toward the model being "captured" by a stored procedure. This is the finding that would generate follow-up work.

Everything else is either (a) known, (b) expected, or (c) presented with insufficient evidence to distinguish it from simpler explanations.

---

## 3. WHAT'S FLUFF OR REPACKAGING

**"Vocabulary Wall"** is prompt sensitivity. This has been documented extensively since at least 2021. The specific framing here adds nothing mechanistically new. Every LLM practitioner knows that certain vocabulary choices produce dramatic performance drops. The observation that Eisenstein-specific terms cause failures is an instance of a documented phenomenon.

**Training distribution topology explains performance.** Yes. This is the core thesis of dozens of papers from 2020-2024. Tokens at training-distribution peaks with high co-occurrence with specific outputs will bias model predictions toward those outputs. This is not CPA-ABD; this is basic generalization theory applied to LLMs. The paper appears to rediscover frequency effects.

**"Binary minefield" claim.** This is weakened by the authors' own data. A Pearson r of +0.33 between specificity and accuracy is a GRADIENT, not a binary. r=0.33 would be considered a weak-to-moderate continuous relationship in any statistics course. The paper cannot simultaneously claim the effect is binary AND present r=0.33 as supporting evidence. This is a logical contradiction. Either the effect is binary (and you need to explain why r≠1.0) or it's gradient (and the core theoretical claim is wrong).

**"The model isn't failing — it's succeeding at the wrong procedure."** This is a reframing, not a finding. It's rhetorically useful but empirically empty. Whether you say "the model failed to follow instructions" or "the model succeeded at retrieving the wrong formula," the behavioral prediction is identical. A theory that produces identical predictions under different framings is not a new theory; it's a new metaphor.

**Cross-lingual effects (Japanese helps, Spanish hurts).** This is tokenization + training distribution confounded with language effects. Without controlling for these separately, this finding cannot support the attractor basin theory. It's consistent with the theory but consistent with at least five other explanations (tokenization artifacts, language-specific training data composition, positional encoding interactions with script direction, etc.).

---

## 4. WEAKNESSES THAT WOULD SINK THIS AT NEURIPS

**Attack #1: Single primary task.** Eisenstein norm is an unusual choice for a primary task — it's low-frequency in training data, has a specific formula, and involves recognizable vocabulary. These properties make it maximally susceptible to the proposed mechanism, which means the study is testing the theory under conditions where it's most likely to be confirmed. Peer reviewers will ask: what happens with Cauchy-Schwarz? Gram matrices? Fourier transforms? The theory should generalize. If it doesn't, it's an observation about Eisenstein norms specifically, not a general theory of LLM computation.

**Attack #2: No mechanistic evidence.** Every finding is behavioral. There is no attention head probing, no activation patching, no logit lens analysis, no circuit identification. The attractor basin claim is completely unverifiable from behavioral data alone. A reviewer will write: "The authors propose a mechanistic theory (attractor basins, pathway selection) but provide only behavioral correlation. This is analogous to proposing a theory of water flow based on measuring downstream temperature without examining the pipes." The bar for mechanistic claims at top venues is now much higher post-Anthropic's interpretability work and the circuits paper series.

**Attack #3: Correlation ≠ selection.** The claim that vocabulary SELECTS pathways (as opposed to adding noise, shifting probability mass, interacting with positional encodings, or triggering retrieval modes) is not established by the evidence. Every finding is consistent with simpler explanations. The "competitive pathway selection" mechanism is the most complex explanation consistent with the data, and Occam's razor cuts against it.

**Attack #4: The binary claim contradicts the evidence.** As noted: r=0.33 is not a binary effect. The discrete minefield claim is the theory's most specific and falsifiable claim, and the authors' own data falsify it. This is not a minor point. If the effect is actually gradational (as r=0.33 suggests), the theoretical apparatus (attractor basins, landmines) is the wrong framework.

**Attack #5: Model heterogeneity without systematic analysis.** The claim that "only Seed-2.0 is immune across all conditions" is potentially very interesting — but it requires systematic investigation of what Seed-2.0 does differently (training data? fine-tuning procedure? architecture differences? RLHF? system prompt handling?). Without this analysis, the Seed-2.0 immunity is a fact in search of an explanation.

**Attack #6: Temperature 0.7 dissolves the wall.** This is the most damaging finding for the theory as stated. If the "vocabulary wall" can be dissolved by increasing temperature, then the effect is not a hard attractor basin (which would require energy well escape, not stochastic exploration). It's more consistent with the model having a sharp probability distribution that gets smoothed at higher temperature — essentially, the model has high confidence in the wrong formula, and temperature reduces that confidence. This is a much simpler explanation that requires no attractor basin apparatus.

---

## 5. REVOLUTIONARY OR FLUFF? FINAL VERDICT

**Overall assessment: 4/10 — Interesting observations, oversold theory.**

The theory is not fluff, but it is substantially overclaimed. There are 2-3 genuine findings buried in 33 claims. The mechanistic framework is unfalsifiable from the presented evidence and uses terminology more precisely defined in adjacent fields. The "attractor basin" framing adds conceptual weight without adding predictive power.

What this work DOES contain:
- Careful behavioral documentation of a real phenomenon
- The context-deprivation paradox (genuinely interesting)
- The deterministic competing formula observation (genuinely interesting)
- The bidirectionality observation (potentially interesting)

What this work DOES NOT contain:
- Mechanistic evidence for the proposed theory
- Adequate task diversity to support generalization
- A test that distinguishes CPA-ABD from simpler frequency/distribution explanations
- A well-defined formalization of "attractor basin" that connects to existing mathematical frameworks

**Confidence in verdict: 8/10.** The remaining uncertainty is on whether the context deprivation finding and deterministic error signature are as robust as claimed — if they are, they're worth publishing even without the theoretical apparatus.

---

## 6. WHAT WOULD MAKE THIS UNDENIABLE

Three experiments that would force top-venue acceptance:

**Experiment 1: Activation Patching / Logit Lens with Contrastive Conditions.** Run the same arithmetic with and without Eisenstein vocabulary. At each transformer layer, compare the logit distribution over the next token. If the vocabulary is triggering a stored formula, you should see the model's internal state diverge from the correct computation trajectory at a specific layer — and the point of divergence should correspond to where the Eisenstein-related representations are most active. If you can show that the model's residual stream "switches" from a computation-consistent trajectory to a formula-retrieval trajectory at a specific layer when Eisenstein tokens are present, you have mechanistic evidence. This would be the difference between a behavioral paper and a mechanistic interpretability paper.

**Experiment 2: Cross-Task Replication with Controlled Formula Conflict.** Design 5 additional tasks that replicate the structural conditions: known named procedures with specific vocabulary, where an alternative but similar formula exists in training data. Test whether the same vocabulary → wrong formula mechanism generalizes. If you can show that (a) the wrong formula is always the training-data-proximal alternative, and (b) performance matches the predicted pattern across all 5 tasks, the single-task weakness is eliminated. If the mechanism fails to generalize, you've correctly scoped your finding.

**Experiment 3: Causal Intervention via Retrieval-Augmented Control.** Insert the correct formula explicitly into the context in different forms: (a) formula only, (b) formula with domain vocabulary stripped, (c) formula with domain vocabulary present. If attractor basin dominance is real, condition (c) should still show degraded performance even with the explicit formula present — because the vocabulary would route computation away from the in-context formula toward the stored one. If condition (c) matches condition (a), the theory is falsified and you have a more parsimonious explanation (vocabulary activates a competing lookup that dominates unless the correct formula is exceptionally foregrounded). This is the critical test that distinguishes your theory from the simpler "vocabulary shifts attention away from the formula" explanation.

---

## BOTTOM LINE

You have interesting data. You have an overpowered theory. The reviewers will separate these two things and you will be penalized for the mismatch. The correct move is to shrink the theoretical claims to match the evidence you have — the context deprivation finding and the deterministic formula signature are genuinely publishable at a workshop or a solid conference. The "attractor basin" apparatus should be removed entirely until you have mechanistic evidence, and replaced with: "Our results suggest a stored-formula retrieval mechanism competing with explicit instruction following, consistent with predictions from [ROME/mechanistic interpretability literature]."

Alternatively, run Experiment 1 above. Six months of interpretability work on top of this behavioral foundation would produce a genuinely top-tier paper. Right now you have the behavioral component of what could be an important finding. Don't submit the half-built version.
