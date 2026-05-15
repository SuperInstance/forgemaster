Now I have the actual data from Studies 42 and 44 (Study 43 produced no JSON — that gap matters). Let me write the paper design with eyes open to what actually happened.

---

`★ Insight ─────────────────────────────────────`
Study 44 produced the most surprising finding: **C1 (formula alone, no label) = 0% accuracy** — the model outputs 136 or 1364 when given `f(a,b) = a²-ab+b²` with no domain name. But C3 (same formula + "Eisenstein norm" label) = **100%**. This completely inverts the landmine narrative. The vocabulary isn't just a toxin — it's a load-bearing formula selector. Without it, computation collapses differently. That's the lede.
`─────────────────────────────────────────────────`

---

## Paper Design: Assuming Studies 42, 43, 44 Confirm

### 1. TITLE

**"What's in a Name? Domain Vocabulary as Formula Selector in LLM Arithmetic"**

Alternatives:
- "Vocabulary as Context: How Mathematical Terminology Routes LLM Computation"
- "The Formula Selector Effect: Domain Terminology and Arithmetic Accuracy in Large Language Models"

**Rationale**: The word "selector" is load-bearing — it's mechanistically humble (behavioral observation, not circuit claim) while still being specific. Avoids "attractor basin," "memorized pathway," "engram." The Shakespeare allusion earns the reader a second before the abstract hits.

---

### 2. ABSTRACT (~250 words)

> Large language models fail predictably on arithmetic problems involving domain-specific mathematical vocabulary — but the failure mode is more structured than previously described, and the cure more surprising. We document three related phenomena on Hermes-3-Llama-3.1-70B. First, identical arithmetic problems embedded in different mathematical nomenclature (e.g., "Hurwitz norm" vs. "Frobenius norm") produce systematically different wrong answers: "Hurwitz norm" yields the integer 43 on 20/20 trials; "Spectral norm" clusters at 43 and 37; "Sobolev norm" clusters at 37. The errors are not random — they are term-specific integer signatures, consistent across 20 independent samples. Second, we test whether providing an explicit formula alongside the domain label can override this interference. The result is unexpected: providing the formula **without** a domain label causes near-total failure (0/25 correct), while providing the formula **with** the problem label "Eisenstein norm" — previously documented as a catastrophic vocabulary landmine — yields 100% accuracy (25/25). This finding suggests that domain vocabulary functions as a **formula selector**: rather than simply triggering wrong answers, vocabulary terms route models toward specific memorized computations, and explicit formula provision succeeds precisely because the label anchors the formula to context. Third, a trivial intervention — stripping domain vocabulary to bare arithmetic — recovers 100% accuracy across models. We characterize the vocabulary selector effect across 12 norm terms, establish that the interference is term-specific and not label-frequency predictable, and propose a taxonomy of three interference modes. These findings have direct implications for LLM deployment in scientific and technical domains.

---

### 3. SECTION OUTLINE

---

#### Section 1: Introduction (1.5 pages)

**What goes here:**
- Open with the failure: a model that aces `f(5,-3) = ?` gets 0/20 when told to compute "the Hurwitz norm" of the same values.
- Second paragraph: the surprise. This isn't just vocabulary noise — the errors are *specific integers*. Hurwitz always says 43. Sobolev mostly says 37. This looks like formula retrieval, not arithmetic failure.
- Third paragraph: the deeper surprise from Study 44. Providing the correct formula doesn't help unless you also provide the domain label. Formula without label: 0%. Formula with landmine label: 100%. Vocabulary is doing something more than poisoning.
- Contribution statement: (a) systematic characterization of term-specific error signatures, (b) causal evidence that vocabulary acts as formula selector, (c) practical intervention achieving 100% accuracy.

**Framing discipline**: Do NOT say "the model has learned that Hurwitz norm = 43." Say: "the model's output distribution when conditioned on 'Hurwitz norm' is tightly concentrated at 43, consistent with retrieval of a fixed formula associated with that term in training."

**Demote**: Any claim about internal mechanisms. Use "consistent with" throughout. The word "suggests" is your shield.

---

#### Section 2: Background and Related Work (1 page)

**What goes here:**
- LLM arithmetic failures (Wei et al., scratchpad work, chain-of-thought work)
- Entity-level interference in NLP (proper nouns changing model behavior)
- Hallucination as retrieval error (point to Mallen et al. on entity frequency)
- Context window effects on computation
- Prompt sensitivity literature (Webson & Pavlick 2022, Sclar et al. 2023)

**Do NOT cite**: Papers claiming to explain *why* this happens mechanistically (IOI circuits, Anthropic superposition papers) unless you're explicitly disclaiming similarity.

**Distinguish from**: Sycophancy/prompt sensitivity work. This is different — the effect is not about tone or framing, it's about specific numeric outputs from specific vocabulary tokens.

**Positioning sentence**: "Unlike prior work on prompt sensitivity that examines accuracy degradation, we document *structured* accuracy degradation: the errors themselves carry information about which formula was selected."

---

#### Section 3: Experimental Setup (1 page)

**What goes here:**
- Target problem: f(5,-3) = 5² - 5×(-3) + (-3)² = 49 (the Eisenstein norm computation, but frame it as: "a fixed arithmetic expression embedded in varying vocabulary contexts")
- Model: Hermes-3-Llama-3.1-70B via DeepInfra
- Baselines: Bare arithmetic condition (no domain vocabulary) as upper bound
- Study 42 design: 12 norm terms × 20 trials each
- Study 44 design: 4 conditions × 25 trials (C1: formula-only, C2: formula+safe label, C3: formula+landmine label, C4: formula+emphasized+landmine label)
- Evaluation: accuracy at retrieving correct integer 49; analysis of wrong-answer distribution per term

**Be explicit about scope limitations here (not buried in limitations)**: Single model, single arithmetic problem, single domain. This is a characterization study, not a benchmark.

---

#### Section 4: Term-Specific Error Signatures (2 pages)

**What goes here — the Study 42 findings:**

**Highlight:**
- The full accuracy gradient across 12 terms (Table 1)
- The deterministic case: Hurwitz norm = 43, 20/20. Zero variance.
- The partial cases: Sobolev (37, 13/20 wrong), Spectral (43 and 37, 16/20 wrong)
- The immune cases: Frobenius, Hölder, Mahalanobis = 100% correct

**Demote:**
- The prospective prediction failure (3/12 correct) — acknowledge it honestly but don't bury it. Put it in this section: "We attempted to predict ahead of testing which terms would cause interference, achieving only 25% accuracy (3/12). The immunity vs. interference classification is not predictable from superficial features of term familiarity."

**Key claim (carefully worded)**: "The consistency of wrong answers within terms — and the divergence between terms — suggests that each vocabulary item routes computation toward a different, specific arithmetic result, rather than introducing random error."

**Framing discipline on the prediction failure**: Frame it as a positive finding — you tested falsifiability and found it; the phenomenon is real but the current theory of *what predicts* interference is insufficient. This is scientific maturity, not a wound.

---

#### Section 5: Vocabulary as Formula Selector — Causal Evidence (2 pages)

**What goes here — the Study 44 findings, the centerpiece of the paper:**

**Highlight:**
- C1 (formula, no label): 0/25. This is astonishing. The model cannot compute `f(a,b) = a²-ab+b²` at `f(5,-3)` without a domain anchor. It produces 136 and 1364 — candidate analysis of what those numbers correspond to (briefly speculate, carefully flagged as speculation).
- C3 (formula + "Eisenstein norm" label): 25/25. The worst known landmine, fully neutralized by formula provision.
- C4 (formula + emphasis): 25/25. No additional benefit from emphasis, suggesting C3's success is not about instruction following.
- C2 (formula + safe label): 23/25. Near-ceiling.

**The reframing this enables**: "The vocabulary wall is not a unidirectional poison. Domain vocabulary is a formula selector: it resolves ambiguity about which computation to perform. When the formula is absent, vocabulary retrieves a memorized answer. When the formula is present, vocabulary anchors the model to the correct computation pathway. The failure mode arises when vocabulary retrieves the wrong formula in the absence of explicit formula provision."

**Acknowledge limitation**: Study 44 was conducted on a single domain (Eisenstein norm). The C1 failure is specific to this computational form. Generalization requires Study 43 data — which you don't have yet.

**The honest contribution**: "These results establish that formula provision with domain label is sufficient for correct computation, providing a causal handle: if you control for formula, vocabulary interference disappears."

---

#### Section 6: The Auto-Translation Intervention (0.5 pages)

**What goes here:**
- The practical fix: strip domain vocabulary, rephrase as bare arithmetic
- Results: 100% accuracy across models (from earlier studies)
- Frame as: "consistent with the selector hypothesis — removing the misleading vocabulary selector eliminates interference"
- This is practical deployment guidance, not just an observation

---

#### Section 7: Discussion (1.5 pages)

**The 'selector' framing vs. 'attractor basin' framing:**
Explicitly address why you're not claiming the attractor basin interpretation. "While our results are consistent with a hypothesis in which domain vocabulary activates specific internal computation circuits, we make no such mechanistic claim. Activation-level evidence would require probing methods beyond the scope of this behavioral study."

**What remains open:**
- Which training data features determine whether a term causes interference?
- Does the effect generalize across models, tasks, domains? (Study 43 needed)
- What does the model compute in C1 (formula-only)? The 136/1364 outputs require explanation.
- Cross-lingual: does the same term in German/French trigger the same wrong answer?

**Implications for deployment**: When deploying LLMs in specialized scientific/engineering domains, vocabulary stripping or explicit formula provision are effective mitigations. Neither scaling nor majority voting reliably overcomes interference.

---

#### Section 8: Limitations (0.5 pages)

**Be aggressive here — it earns credibility:**
- Single model
- Single arithmetic expression  
- No activation-level evidence
- Prospective prediction failed (25% accuracy)
- Study 43 (cross-task replication) not yet complete — results pending
- Selection of 12 norm terms was not fully systematic
- The 0% in C1 is unexplained and the paper does not explain it

---

### 4. KEY FIGURES AND TABLES

**Table 1**: Accuracy by domain term (12 terms × accuracy % × most common wrong answer × wrong answer consistency). Sort by accuracy descending. Color-code: green (>80%), yellow (40-80%), red (<40%). This is the paper's visual anchor.

**Figure 1**: Bar chart of accuracy across 12 terms, with error bars (binomial confidence intervals). Overlay the dominant wrong answer as a secondary label on each bar. Purpose: shows both the gradient and the structure.

**Figure 2**: Study 44 four-condition accuracy comparison. Simple bar chart, C1/C2/C3/C4 side by side. The visual story is immediate: 0%, 92%, 100%, 100%. Caption should name this the "formula selector" evidence.

**Figure 3**: The vocabulary selector hypothesis diagram. A conceptual figure showing: bare term → formula retrieval (wrong) vs. term + explicit formula → formula anchoring (correct). Flag clearly as a hypothesis figure, not a mechanistic claim.

**Table 2**: Wrong answer catalog — for each term with <70% accuracy, list the wrong answer(s), their frequency, and a brief note on what computation would yield that answer. This is the "competing formula signatures" finding made concrete.

---

### 5. RELATED WORK POSITIONING

**Cite and distinguish from:**
- *Wei et al. (2022), Chain-of-Thought Prompting*: CoT helps but doesn't address vocabulary interference
- *Sclar et al. (2023), Quantifying Language Models' Sensitivity to Spurious Features*: related prompt sensitivity, but their effects are weaker and not numeric-structured
- *Mallen et al. (2023), When Not to Trust Language Models*: entity frequency predicts failure — your Study 22 found ~0.65 correlation, worth a citation
- *Webson & Pavlick (2022), "Do Prompt-Based Models Really Understand..."*: prompt template effects on classification; you extend this to arithmetic
- *Marcus (2018)*, any neural network compositionality critique: you're providing behavioral evidence, not theoretical critique

**Position against**: Mechanistic interpretability work (Elhage et al. circuits, IOI). Explicitly say: "We document behavioral patterns consistent with what mechanistic work would call retrieval circuits, but make no such internal claims. Our contribution is behavioral characterization and an effective intervention."

---

### 6. THE HONEST CONTRIBUTION STATEMENT

Here is what you can actually claim, with appropriate confidence:

> We demonstrate that domain-specific mathematical vocabulary causes *structured*, term-specific arithmetic errors in Hermes-3-Llama-3.1-70B: the wrong answers produced are consistent within terms and divergent across terms, suggesting vocabulary-dependent computation routing. We further show, through a causal intervention (Study 44), that explicit formula provision with domain label fully overrides this routing, while formula provision without label fails completely. This establishes vocabulary as a *formula selector* in LLM computation: the mechanism of interference is not vocabulary toxicity but vocabulary-driven formula retrieval. A trivial auto-translation intervention achieves 100% accuracy. These findings are behavioral and single-model; mechanistic verification and cross-model replication remain for future work.

---

### 7. VENUE RECOMMENDATION

**Primary target: EMNLP 2026 BlackboxNLP Workshop**

This is the right venue because:
- BlackboxNLP explicitly welcomes behavioral analysis without mechanistic claims
- The community expects single-model characterization studies
- The finding (structured error signatures + causal formula intervention) fits the "probing and understanding" scope exactly
- Acceptance bar is achievable with this evidence level

**Secondary target: ACL Findings (not main track)**
Findings papers are appropriate for solid empirical work that characterizes a phenomenon without resolving it. The Study 44 C1 finding (formula alone = 0%) is strong enough to warrant a Findings slot if cross-model replication from Study 43 can be added.

**Do not submit to**: NeurIPS main track, ICLR main track. The reviewers will demand activation patching, multi-model validation at scale, and a theoretical framework. You'll get desk-rejected or scored 3/6 with "interesting but not mechanistic enough for this venue."

**Dark horse: COLM 2026** (Conference on Language Modeling). Their scope explicitly includes behavioral characterization of LLMs. Given the practical intervention angle, this is worth a look.

---

### ONE CRITICAL HOLE TO PATCH BEFORE SUBMISSION

Study 43 (cross-task replication on Cauchy-Schwarz, Möbius, Fourier, Gram, Legendre) has no JSON file. **That gap is the difference between a workshop paper and a Findings paper.** The selector hypothesis rests on generalization — if Möbius always triggers the same wrong answer for a different computation, the phenomenon is real. If it doesn't replicate, your finding is narrowly about this one arithmetic form.

Run Study 43 before you submit anywhere. It's the cheapest experiment left that would most increase the paper's reach.
