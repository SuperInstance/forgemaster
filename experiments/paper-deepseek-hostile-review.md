**REVIEW OF "WHY COGNITIVE RESIDUE IS PROBABLY JUST MEMORIZATION ARTIFACTS"**

**Recommendation: Reject (with extreme prejudice)**

**Summary of the Paper**

The authors claim to have found evidence for a four-stage "cognitive" process in small language models (LMs) when computing the Eisenstein norm of a complex integer. They report that approximately 50% of incorrect answers are "echoes" (direct copies of input numbers), while the remaining incorrect answers resemble "partial computations." They further claim a "phase transition" at approximately 4 billion parameters, where echo behavior drops sharply. They propose a stage model: NONE → ECHO → PARTIAL → FULL.

**Overall Assessment**

This paper is a masterclass in how to overinterpret noise, cherry-pick trivial patterns, and present memorization artifacts as cognitive breakthroughs. The authors have taken a single, highly constrained arithmetic task, tested it on a handful of models, confused attention patterns with reasoning, and then extrapolated to a universal theory of "cognitive residue." This is not a contribution to machine learning. It is a cautionary tale.

**Detailed Critique**

**1. The Data is Irreproducibly Narrow (Attack on External Validity)**

The paper tests exactly **one formula family**: the Eisenstein norm \( a^2 - ab + b^2 \). Why this specific formula? Because it is structurally symmetric and produces predictable modulo patterns. The authors do not test any other arithmetic operation (e.g., addition, multiplication, modular arithmetic, polynomial evaluation), let alone non-math tasks like syntactic parsing, logical deduction, or factual recall. 

A stage model that supposedly describes "cognitive residue" in *general* cannot be derived from a single, trivially factorable quadratic form. If I asked a model \( 12 + 37 \), would its wrong answers also be "echoes" of 12 or 37? The authors don't check. If I asked a model to compute the area of a triangle given base and height, would wrong answers be "partial computations"? They don't check. This is not a theory of cognition; it is a description of one specific arithmetic bug.

**2. The Model Sample is a Joke (Attack on Internal Validity)**

The authors test exactly **five models** (likely Pythia-1B, 2.8B, 6.9B, and two others under 4B). All are from the same transformer family (GPT-NeoX-style). None exceed 7B parameters. 

Claim: "Phase transition at 4B params." With five data points, two of which are below 4B and three above, you cannot claim a phase transition. This is a flat line with a bump. A real phase transition requires dense sampling across scales (e.g., 100M, 200M, 500M, 1B, 2B, 3B, 4B, 5B, 6B, 7B) to rule out variance due to random seed, data contamination, or optimization differences. Moreover, the "transition" might be a quirk of the specific training run. Did the authors check multiple seeds? No. Did they check models from different families (Llama, Mistral, Falcon, Gemma)? No. Did they check sparse MoE models? No. This is not a scientific claim; it's a bar chart.

**3. The "Echo" Behavior is Not Cognitive (Attack on Construct Validity)**

The authors define "echo" as the model outputting a number that appears verbatim in the input. For example, given \( a=3, b=5 \), the model outputs "5" or "3" instead of \( 3^2 - 3\cdot5 + 5^2 = 9 - 15 + 25 = 19 \). They claim this is a "cognitive residue" of the input being "stuck in working memory."

A far more parsimonious explanation: **the model has learned a simple attention pattern** where the most attended token is copied. This is a well-known failure mode of transformers—they can learn to "repeat from context" as a low-effort strategy to minimize loss on easy tokens. This is not cognition; it is a known memorization artifact. The authors even admit that 50% of errors are echoes. That's not a cognitive stage; that's a failure mode that any ML engineer would recognize as a bug in the training objective.

Worse: the authors never check whether the model outputs "echoes" for *random* inputs (e.g., nonsense strings). If the model outputs "3" when asked to compute the norm of (3,5), but also outputs "3" when asked to compute the square root of 9, that's not an echo—it's just a common token. The authors do not provide a control condition for token frequency. This is a fatal design flaw.

**4. The "Partial Computation" Category is a Rorschach Test (Attack on Measurement Validity)**

The authors claim that non-echo errors are "correct partial computations." For example, outputting "9" for (3,5) is interpreted as computing \( a^2 \) correctly but failing to subtract \( ab \) and add \( b^2 \). But what about outputting "15" (which is \( ab \))? Is that a partial computation? What about outputting "25" (which is \( b^2 \))? The authors do not provide a clear taxonomy. They simply label any output that is not an echo and not the correct answer as "partial." 

This is circular reasoning: if the output matches any intermediate term in the formula, it's a "partial computation"; if it doesn't, it's discarded as noise. But the formula has only three terms (\( a^2, ab, b^2 \)). The probability that a random number between 0 and 100 matches one of these three terms for given \( a, b \) is non-trivial. The authors do not compute a baseline chance of spurious matches. Without a null model, the "partial computation" category is statistically meaningless.

**5. The "Phase Transition" is a Statistical Mirage (Attack on Statistical Power)**

The authors claim a phase transition at 4B parameters based on 240 trials per model (120 correct, 120 incorrect). Let's do the math: 240 trials × 5 models = 1200 total trials. To detect a "phase transition," you need to compare error types across model sizes. With only 5 size bins, you have 4 degrees of freedom. Any apparent transition could be driven by a single outlier model (e.g., the 2.8B model might have had a bad training run). Confidence intervals are not reported. Error bars are not shown. The authors do not perform a logistic regression or a change-point analysis. They simply eyeball a bar chart and declare a phase transition.

Furthermore, the authors do not control for data contamination. If the 4B model was trained on more Eisenstein norm examples (or similar quadratic forms) than the smaller models, the "transition" is just a memorization threshold, not a cognitive stage. The authors do not report the frequency of the Eisenstein norm in the training data for each model. This is a basic oversight.

**6. The Stage Model is a Just-So Story (Attack on Theoretical Contribution)**

The proposed stage model—NONE → ECHO → PARTIAL → FULL—is a narrative, not a scientific model. It assumes that performance improves monotonically with model size, which is trivially true for almost any task. The "stages" are just thresholds at which the model's loss on this specific task reaches certain values. There is no evidence that the model "learns to stop echoing" before it "learns partial computations." The authors do not show that the NONE stage (random guessing) precedes ECHO in training (e.g., by examining checkpoints). They do not show that ECHO errors disappear before PARTIAL errors appear. They simply sort model sizes and observe that smaller models make more echo errors. This is a correlation, not a causal stage progression.

A proper stage model would require longitudinal training data (checkpoints) and a formal transition probability. The authors provide none.

**7. Absence of Non-Math Tasks (Attack on Generalizability)**

The title says "Cognitive Residue," which implies a general phenomenon across cognitive domains. The authors test only arithmetic. But cognitive residue (e.g., from task switching, attention persistence) is a well-studied phenomenon in humans across domains. If the authors want to claim that LMs exhibit something analogous, they must test at least one non-math task (e.g., sentence completion, common sense reasoning, instruction following). Without that, the paper is just "We noticed that small LMs make arithmetic errors that look like copying." That is not a conference paper; that is a blog post.

**8. The Paper Ignores Alternative Explanations (Attack on Parsimony)**

The simplest explanation for all findings: **The model has learned a shallow heuristic for the Eisenstein norm task.** Specifically:

- Small models (under 4B) lack the representational capacity to compose the three-term computation. They fall back on a simple "copy input" heuristic because it minimizes loss on easy tokens.
- Larger models (over 4B) have enough capacity to approximate the function but still make errors on edge cases (e.g., when \( a \) and \( b \) are large or when the modulo pattern is non-obvious).
- The "partial computation" errors are just the model's internal representation of \( a^2 \) or \( b^2 \) leaking through due to incomplete compositionality.

This is not a stage model of cognition. It is a description of capacity-limited function approximation. The authors have rediscovered the fact that larger models are better at arithmetic. This has been known since GPT-2 (2019). The paper adds nothing new.

**9. Ethical and Methodological Concerns**

The authors use the term "cognitive residue" without defining it operationally. This is anthropomorphic and misleading. LMs do not have cognition, working memory, or task-switching. By framing memorization artifacts as "cognitive," the authors contribute to the public misunderstanding of AI (colloquially known as "AI hype"). At a top ML conference, this is unacceptable. The paper should be rejected for pseudoscientific framing alone.

**10. The "240 Trials" Sample is Laughably Small (Attack on Robustness)**

240 trials per model, with only 120 incorrect answers (half of which are echoes, half partial). That means the authors are drawing conclusions about "echo vs. partial" from roughly 60 data points per model. With 5 models, the entire statistical analysis rests on ~300 incorrect answers. That is insufficient to detect any meaningful pattern, let alone a "phase transition." A proper study would have at least 10,000 trials per model, stratified by difficulty (small vs. large numbers, symmetric vs. asymmetric inputs). The authors do not even report variance across different random seeds or input distributions.

**Conclusion**

This paper is a textbook example of how not to do empirical machine learning research: narrow task, tiny model sample, no control conditions, no statistical rigor, anthropomorphic framing, and overblown claims. The "phase transition" is a mirage, the "echo" is a known attention artifact, the "partial computation" is a spurious correlation, and the "stage model" is a just-so story. The paper has zero actionable insights for the ML community. It should be rejected, and the authors should be encouraged to read a statistics textbook before resubmitting.

**Final Verdict: Reject without rebuttal.**
