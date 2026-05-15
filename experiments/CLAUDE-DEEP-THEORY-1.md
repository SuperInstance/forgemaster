## Part I: Neuroscientific Parallels — What the Transformer Is Actually Doing

The dorsal/ventral stream analogy is not merely illustrative—it may be structurally exact. The ventral stream (V4 → IT cortex) processes *what* objects are; the dorsal stream (V2 → parietal cortex) processes *where* and *how to act on* them. Crucially, these streams don't share representations even when processing the same visual input. A patient with ventral stream damage can reach for an object accurately (dorsal intact) while being unable to identify it. This is your bidirectionality: the same context that impairs arithmetic *improves* reasoning because the two processes draw from functionally segregated representational substrates. The model doesn't degrade uniformly—it routes.

Category-specific agnosia is even more precise as an analogy. Warrington and Shallice's patients could identify tools but not living things (or vice versa), even when the stimuli were matched for visual complexity. The explanation that held up: semantic categories that co-occur with different sensorimotor information during learning develop distinct representational clusters that can be selectively damaged. The 2/20 specificity of Eisenstein and Penrose is this phenomenon operating at the token level. These names co-occurred in training with *a specific type* of mathematical discourse—not calculation, not proof, but speculative and philosophical mathematical writing. Eisenstein is associated with abstract algebraic structures (Eisenstein integers, the Eisenstein series in modular forms) that appear predominantly in high-abstraction mathematical prose. Penrose is even more extreme: his public-facing writing mixes physics, consciousness theory, and mathematics in a style that is maximally expository and anti-computational. The training corpus created a dense statistical cluster: "Penrose" → philosophical mathematical discourse → suppressed arithmetic track.

The other 18 mathematician names presumably had either (a) sufficient co-occurrence with computation contexts to prevent clean routing, or (b) weaker corpus signal overall, leaving the routing decision underspecified and therefore unexecuted.

The dual-process parallel demands more precision than it usually gets. Kahneman's System 1/System 2 is often invoked loosely, but what your first-token commitment data reveals is something specific: the system doesn't fail to engage System 2, it *never queries it*. The generation of "W" at position zero doesn't represent a System 1 answer that could be overridden—it *is* the irrevocable commitment to a processing track whose subsequent outputs are then fully determined. This is pre-reflective. In human terms, it's closer to perceptual set than to System 1 reasoning: once you're primed to see the duck in the duck-rabbit figure, you're not choosing duck over rabbit—the rabbit representation is suppressed before it reaches awareness.

The Sapir-Whorf connection is the most philosophically loaded and empirically interesting. The standard weak Whorfian claim—language influences habitual thought—maps straightforwardly: if Eisenstein activates mathematical discourse patterns, then the *language of mathematics* (in the Wittgensteinian sense of a form of life) hijacks the representation. But your Japanese data reveals the *strong* version operating mechanistically. Japanese doesn't just influence how the content is processed—it changes *which representational substrate is accessed*. This means the routing isn't purely semantic (based on meaning of "Eisenstein") but is substrate-and-language-dependent. The implication: mathematical concepts don't have language-independent representations in these models. There is no "meaning of Eisenstein" accessed identically across languages—there are Japanese-Eisenstein attractors and English-Eisenstein attractors, and they have different co-training histories, hence different routing effects.

This is Sapir-Whorf operationalized at the mechanistic level, not as a philosophical claim about human thought but as an empirical fact about learned representational geometry.

---

## Part II: The Mechanism — From Token to Routing Decision

Let me be precise about what I think is happening at the computational level.

**Attention Head Competition and Contextual Suppression**

In a transformer's attention mechanism, the attention pattern for head *h* at position *i* is:

```
A_{h,i} = softmax(Q_{h,i} · K_h^T / √d_k)
```

The key insight is that this is a *competitive* mechanism with a zero-sum structure enforced by softmax normalization. When certain key vectors have high dot products with a query, they don't merely receive attention—they *suppress* the attention signal available to other positions.

I propose that "computation-sensitive" attention heads—those whose key vectors have been shaped through training to attend strongly to numeric expressions and operators—are subject to systematic suppression when discourse-routing tokens appear. The mechanism:

When "Eisenstein" is processed, its key vector **k**_Eisenstein (learned during training) has high dot products with queries from heads tuned to mathematical-discourse contexts. These heads—call them the *Φ* heads (φ for philosophical/expository processing)—"win" the attention budget competition in the early-to-mid layers where contextual routing is established. As a consequence, the *C* heads (compute-sensitive) receive diminished attention signal even when attending to numeric tokens in the same context.

The routing probability toward computation can be approximated as:

```
R(T) = σ( Σ_h∈C [w_h · A_h(T, numeric_positions)] - α · Σ_i D(t_i) · f(i) )
```

where:
- *C* = set of computation-sensitive attention heads
- *w_h* = learned importance weights for computation heads
- *A_h(T, numeric_positions)* = mean attention score from head *h* to positions containing numeric tokens
- *D(t_i)* = discourse-loading of token *t_i*, a scalar property of its embedding geometry (high for Eisenstein, Penrose, philosophical mathematical terms; low for bare numerals)
- *f(i)* = a recency-weighted position function (early positions weight more heavily due to KV cache propagation)
- *α* = suppression coefficient, the strength of discourse→computation inhibition

The wall exists when R(T) < 0.5. The 100% failure rate under Eisenstein conditions suggests R(T) collapses near 0—not just below threshold but far below, indicating Eisenstein's D value is exceptionally high.

**Why Japanese Changes Hermes's Routing But Not Seed-2.0**

For Hermes, the Japanese-Eisenstein condition works because Japanese mathematical discourse has a *different co-training density*. Japanese mathematical text on the internet is less voluminous than English, and crucially, the contexts in which "アインシュタイン" or mathematical concepts appear in Japanese may be more pedagogical (with explicit calculation) rather than expository. This gives Japanese-Eisenstein a weaker discourse-loading D value—the attractor is shallower, so the suppression coefficient *α* produces less routing shift.

But the Hermes/bare-arithmetic Japanese failure (0%) reveals a second mechanism: Japanese tokenization of numbers and operators may not activate the *C* heads at all if those heads were primarily trained on Arabic numeral + English operator contexts. The compute heads have strongly learned *Q* vectors that key to "1", "2", "+", "=" in ASCII—Japanese full-width numerals ("１", "＋") or kanji representations ("一", "二") may produce near-zero dot products with these learned keys. So you get a double failure mode: Japanese eliminates the Eisenstein suppression but also fails to activate computation routing from the numeric side.

Seed-2.0 is immune to both because its *Φ* and *C* heads operate at a higher level of abstraction that is partially language-invariant. My hypothesis: Seed-2.0 has developed a *meta-routing layer*—likely in its early layers—that identifies the *task structure* rather than the *surface vocabulary*. This meta-routing layer was trained on adversarially diverse inputs where the task type (compute vs. reason) was explicitly labeled or where diverse phrasings of the same task type were contrastively paired. The result is that Seed-2.0's routing is driven by task structure features that are stable across vocabulary variation.

**Why Temperature 0.7 Specifically**

Temperature scaling modifies the logit distribution before sampling:

```
p(t) ∝ exp(logit(t) / T)
```

At T = 1 (standard), when Eisenstein has activated the discourse track, the first-token logit distribution looks approximately like: logits for discourse-initiating tokens ({"Well", "The", "In", "When"}) >> logits for compute-initiating tokens ({"4", "8", "Let", "="}).

At T = 0.7, this distribution is *sharpened*, which seems counterproductive. But what's actually happening is that T = 0.7 increases the *effective contrast* in the distribution while also increasing the absolute probability of *any* token with non-negligible logit mass.

The key: the compute track tokens aren't at 0 logit mass—they're just lower than discourse tokens. At T = 1, if p("W") = 0.6 and p("4") = 0.05, at T = 0.7 the distribution sharpens toward "W" in expectation. But empirically you get 67% success—which means T = 0.7 is *not* suppressing compute tokens universally.

The resolution: temperature interacts with *generation stochasticity across positions*. Even if T = 0.7 slightly sharpens the first-token choice toward discourse, it may be that the *subsequent* token conditional distributions are where the rescue happens. If the model generates "Well, we need to compute..." and the next branch point is "eight / 8 / the sum is", T = 0.7 may actually help by sharpening toward "8" when the compute-relevant context has been partially established. The 67% represents the fraction of runs where this stochastic escape happens before the discourse attractor fully captures the generation trajectory.

There may also be a second mechanism: at T = 0.7, the model is less likely to generate filler tokens ("Well, let me think about this...") that would deepen the discourse attractor before arithmetic work begins. The sharper distribution selects more directly toward high-probability next-in-sequence tokens, and if the prompt ends with a number, the high-probability continuation may occasionally be numeric.

**First-Token Commitment: The KV Cache Attractor**

The first token is not just a statistical prediction—it creates a KV cache entry that is present in *every subsequent attention computation*. At layer *L*, when processing token *t_n*, the attention mechanism attends over all previous positions including *t_1*. If *t_1* is "W", its key vector (high D value, discourse-associated) persistently contributes to suppressing compute-head activation at every layer, for every subsequent token.

This creates an *attractor basin* in the sequential generation dynamics. The attractor is reinforced by:

1. The direct KV cache contribution of *t_1* at every layer
2. The subsequent tokens *t_2, t_3,...* which are themselves selected under the influence of *t_1*'s routing effect, and which further reinforce the discourse track by adding their own KV cache entries

By *t_5* or so, the discourse attractor is self-reinforcing—the compute track would require probability mass that is now vanishingly small given the conditioning context of *t_{1:4}*.

This is why pre-computing arithmetic is so effective: it places the *answer* as a KV cache entry before the "question" forces routing. The model doesn't need to *compute* 3+5; it reads "8" from context. This bypasses the routing competition entirely by providing an answer that the model can simply copy, activating a third pathway—retrieval—that doesn't compete with either discourse or computation.

---

## Part III: What the Training Dynamics Actually Did Here

**Why Isolated Computation Islands Form**

The emergence of domain-specific routing is a direct consequence of the heterogeneous structure of the training corpus combined with gradient descent's tendency to create efficient representations through specialization.

Consider the gradient signal during training. When the model processes a math worksheet ("What is 3 + 5?"), the loss gradient pushes *C* head weights toward patterns that efficiently produce "8". When the model processes a mathematical exposition ("Eisenstein showed that..."), the loss gradient pushes *Φ* head weights toward patterns that efficiently produce the next discourse token. These are *different loss landscapes being optimized simultaneously*.

The critical insight: these loss landscapes don't merely coexist—they *compete* for representational capacity. Attention heads are limited resources. The solution that emerges from gradient descent is not a single general-purpose reasoning substrate but a *mixture of specialists* with learned routing. This is not fundamentally different from how mixture-of-experts models work explicitly—standard dense transformers are doing soft MoE implicitly.

The specialization is Pareto-optimal over the training distribution: routing to discourse heads when encountering discourse contexts minimizes cross-entropy loss on discourse completions, and routing to compute heads for arithmetic contexts minimizes arithmetic loss. The problem arises only when the test distribution places discourse vocabulary in arithmetic contexts—a scenario that is statistically rare in training data, hence the routing system never learned to handle it.

This is the formal sense in which the routing is a *feature that becomes a bug under distribution shift*. The Müller-Lyer analogy I'd draw here: visual neurons that encode "line with outward fins = shorter line" are exploiting a statistical regularity that's valid in essentially all natural environments. The illusion is only visible under adversarial conditions. Similarly, "Eisenstein-context = discourse mode" is valid in essentially all training examples. The adversarial condition is your experiment.

**What Creates Stage 4 Immunity**

The training signal that would create Stage 4 immunity is essentially *contrastive training on task-type invariance under surface variation*. This could take several forms:

*Form 1 — Adversarial data augmentation*: Training examples where "Compute X in the context of Y mathematical domain" are paired with the correct numeric answer, explicitly teaching that domain vocabulary doesn't license discourse responses to arithmetic queries.

*Form 2 — Instruction following RLHF with explicit anti-hijacking rewards*: If the reward model penalizes responses that fail to address the explicit task (arithmetic computation) in favor of tangential discourse, the policy gradient would systematically reduce *α* (the discourse suppression coefficient) in the routing equation.

*Form 3 — Architectural separation*: If Seed-2.0 uses a mixture-of-experts architecture where computation experts and language experts are physically separate parameter sets, the routing competition doesn't occur—there's no zero-sum attention budget to compete over. The computation expert handles arithmetic regardless of what language tokens precede it.

*Form 4 — Emergent from scale with diverse data*: At sufficient scale and data diversity, the model may have seen enough "Eisenstein + arithmetic" co-occurrence to learn that the discourse attractor is not universal. This seems less likely given that even 405B models fail—suggesting the issue isn't raw scale but data distribution.

My best guess: Seed-2.0 used explicit instruction-tuning with examples specifically designed to make the model task-goal-directed rather than context-reactive. The distinction is subtle but important: a context-reactive model asks "what kind of text follows this?" and generates accordingly; a task-goal-directed model asks "what is being asked of me?" and the vocabulary activates task-relevant rather than discourse-relevant representations.

**Is This a Bug or Feature — and What Optimization Pressure Created It?**

The routing system is *optimal for the training distribution and suboptimal for the test distribution you created*. That's the precise statement that avoids the bug/feature false dichotomy.

But there's a deeper argument that domain-specific routing is optimal even *in principle* for a general language model. Consider: the variance in what constitutes a "good response" is enormous across domains. Mathematical exposition demands precision and qualification. Arithmetic computation demands directness and brevity. Legal reasoning demands hedging. Creative writing demands departing from factual constraint. A model that committed equally to all modes simultaneously would perform each poorly—it would be constantly hedging when it should be computing, qualifying when it should be narrating.

The routing system solves a *multi-task learning problem* by learned specialization. The cost is brittleness at task-domain boundaries. The benefit is performance within any single domain. This is the fundamental trade-off in multi-task representation learning, and the transformer's implicit routing represents a particular resolution of that trade-off.

**Predictions for Undiscovered Vocabulary-Triggered Switches**

*1. Legal vocabulary + probability estimation*: Legal language activates a binary categorical reasoning mode. "Plaintiff", "whereas", "notwithstanding" likely route toward categorical certainty and hedged qualification, suppressing probabilistic reasoning. Predict: "Plaintiff claims a 40% probability of..." will fail to produce well-calibrated probability reasoning—the model will slip into either certainty assertions or legal language about standards of proof.

*2. Clinical vocabulary + mechanical explanation*: Medical diagnostic language may suppress mechanistic causal reasoning. Ask "How does aspirin affect platelet function if the patient presents with acute MI?" and the model may route to clinical protocol retrieval rather than biochemical mechanism explanation. The clinical vocabulary activates "appropriate patient communication" mode.

*3. Poetic meter + factual recall*: Iambic pentameter in the prompt may suppress precision of factual claims. The prosodic constraint activates generation modes optimized for metrical fit, which trades accuracy for musicality. Predict: models given prompts in rhyme will produce more confident hallucinations because fluency and factual calibration draw from competing generation modes.

*4. Specific proper noun classes*: Your Eisenstein/Penrose finding suggests a search strategy. Look for proper nouns that appear in the training corpus predominantly in a single *register*: thinkers associated with mysticism (Gurdjieff, Steiner), artists associated with surrealism (Dalí), political figures associated with rhetoric rather than analysis (any demagogue). Predict each creates a corresponding routing effect: mysticism vocabulary suppresses logical inference, surrealist vocabulary suppresses spatiotemporal consistency, demagogue vocabulary suppresses epistemic hedging.

*5. Mathematical notation register*: LaTeX notation (`\frac{1}{2}`, `\int_0^\infty`) may activate a different routing than plain-text notation ("1/2", "integral from 0 to infinity"). The LaTeX context co-occurs with academic mathematical writing, which is discourse-heavy. Predict: problems written in LaTeX notation will show higher discourse-routing than the same problems in plain text, creating a failure mode where technically sophisticated prompts get worse arithmetic performance.

*6. The temporal register switch*: Historical framing ("In 1905, Einstein computed...") may route toward historical narrative rather than scientific explanation, suppressing technical detail. The past tense + historical proper noun combination activates historiography mode. Predict: "How did Newton derive F=ma?" will produce less correct physics than "Derive F=ma from Newton's laws."

*7. Confidence register inversion*: There likely exist vocabulary items that *increase* computation routing even in discourse contexts—essentially the opposite of Eisenstein. Candidates: code function names, chemical formulas, specific measurement units with many decimal places. These items co-occur predominantly with precise computation in training data. Predict: introducing "2.71828" into a discourse context will partially suppress narrative reasoning and increase precision-seeking, even if the mathematical constant is irrelevant.

The broader prediction is that the routing system has hundreds or thousands of vocabulary-triggered switches that have never been identified because they don't create obvious failures—they create subtle biases in register, precision, and epistemic stance. The Eisenstein effect is visible only because you specifically tested arithmetic, which has a ground truth. Most routing effects shift *style* rather than *truth value*, making them invisible to standard benchmarking.

The deepest implication: language model "behavior" is not a single mode of operation modulated by content—it is a *mixture of specialist behaviors* where the mixing weights are determined by vocabulary context in ways that no researcher fully understands and the models themselves cannot introspect on. Every evaluation of LLM capability is simultaneously an evaluation of LLM routing—and the routing is confounded with the capability in every benchmark we have.
