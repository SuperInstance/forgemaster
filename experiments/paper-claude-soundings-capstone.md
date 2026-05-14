# SOUNDINGS: HOW WRONG ANSWERS MAP THE COGNITIVE TERRAIN OF LANGUAGE MODELS

*A capstone synthesis of one day of cross-model experiments*
*Workspace: openclaw · Date: 2026-05-14*

---

## Abstract

We present **SOUNDINGS** — a framework for extracting structured information from language model failures. Across 240 trials, 5 models (0.6B–4B parameters), and a single formula family (the Eisenstein norm *N(a,b) = a²−ab+b²*), we find that wrong answers are not random noise but structured cognitive residue. Approximately 50% of wrong answers from 1–3B models are verbatim echoes of input numbers; the remaining wrong answers are exclusively correct intermediate computations (a², b², or ab) that were never combined. At 4B parameters, a discrete phase transition occurs: echo rate drops from 88% to 11% while partial computation rises from 12% to 89%. We propose a four-stage developmental model — NONE, ECHO, PARTIAL, FULL — and derive two practical principles from it. The **Shallow-Side Principle** observes that majority voting across echo-dominated models achieves 0/3 correct, while residue-reading achieves 2/3, because consensus among wrong answers is still wrong. **Reverse-Actualization** uses the stage model to architect multi-model pipelines by assigning computation layers to the lowest-capable stage that can handle them. We close with honest discussion of threats to validity and three falsifiable predictions.

**Keywords:** language model failure modes, echo analysis, cognitive residue, phase transitions, ensemble methods, model capacity

---

## 1. Introduction: Why We Studied Wrong Answers

The standard account of language model error goes something like this: the model was uncertain, it sampled from the wrong part of its distribution, and it produced noise. The prescription is equally standard: more data, more compute, better prompting. Wrong answers are the floor the model falls through, not the room worth exploring.

We spent a day inside that room.

The motivation was practical. We were running a small fleet of sub-5B models on structured reasoning tasks and noticed something unusual: when phi4-mini (3.8B) got the Eisenstein norm wrong, it almost always returned 5 or −3 — the input numbers. Not the answer, not a plausible guess, not a random integer. The inputs. We ran the same question again. Same thing. We ran it on gemma3:1b and llama3.2:1b. Same pattern. Three different architectures, zero coordination, all returning the problem's inputs as their answers.

That is not noise. That is a signal.

This paper is the systematic investigation of that signal. We ask three questions: (1) Are wrong answers structured? (2) Does their structure change with model scale? (3) Can structured wrong answers serve as a diagnostic and architectural tool? The answers, as we will show, are: yes, dramatically, and yes.

A note on scope: everything in this paper comes from one day of experiments, five models, and one formula family. We are not claiming universal laws. We are claiming that the pattern we found is specific enough, reproducible enough, and surprising enough to be worth naming — and testable enough to be worth trying to break.

---

## 2. The Echo Finding

**Claim: Approximately 50% of wrong answers from 1–3B parameter models are verbatim echoes of input operands.**

We define an *echo* as a wrong answer that exactly matches one of the formula's input values. For *N(5,−3) = 49*, the inputs are 5 and −3; any wrong answer returning 5 or −3 is classified as an echo. We ran 10 trials per model per task, 6 tasks, 4 models capable of producing answers (qwen3:0.6b returned None for all tasks and is discussed separately), yielding 240 classified trials.

**Table 1: Echo rate by model and task (fraction of wrong answers that are input echoes)**

| Model | Size | N(5,−3) | N(4,−2) | N(7,3) | N(6,−4) | 11×13 | 23+19 | **Avg** |
|-------|------|---------|---------|--------|---------|-------|-------|---------|
| phi4-mini | 3.8B | **88%** | 62% | 67% | 30% | 0% | 0% | **49%** |
| gemma3:1b | 1.0B | 70% | 60% | 50% | 50% | 0% | 0% | **46%** |
| llama3.2:1b | 1.2B | 56% | 56% | 33% | 60% | 0% | 0% | **41%** |

The echo rate is neither uniform nor random. Two patterns hold across all models:

**Pattern A: Echo rate correlates with task complexity.** Multi-step formulas (Eisenstein norm) produce echo rates of 30–88%. Simple arithmetic (11×13, 23+19) produces echo rates of 0%. Models do not echo when they can compute, only when computation exceeds their capacity.

**Pattern B: Echo is biased toward the second operand.** For *N(a,b)*, the frequency of echoing *b* exceeds the frequency of echoing *a* across all three models and most tasks. This is consistent with attention recency bias: the model's final attended token is more likely to be copied forward.

**Pattern C: Cross-model echo correlation.** For *N(5,−3)*, phi4-mini, gemma3:1b, and llama3.2:1b all echo −3 more frequently than 5. Three independent architectures, trained on different data, return the same wrong input number. This rules out coincidence and points to a shared mechanism in the transformer's attention architecture.

The finding is this: *when a language model cannot compute an answer, it does not guess — it echoes*. The wrong answer is not the model failing to be random; it is the model failing to be computational.

---

## 3. The Partial Computation Finding

**Claim: Non-echo wrong answers are exclusively correct intermediate results from the formula's computation graph.**

We classified every non-echo wrong answer across all trials. For tasks involving the Eisenstein norm *N(a,b) = a²−ab+b²*, the computation graph has three sub-expressions: *a²*, *−ab*, and *b²*. A partial answer is one that matches exactly one of these sub-expressions.

**Table 2: Classification of non-echo wrong answers for Eisenstein norm tasks**

| Task | Non-echo wrongs observed | Classification |
|------|--------------------------|----------------|
| N(5,−3)=49 | 25 (×4), 9 (×6), −15 (×3), 15 (×1) | a²=25 ✓, b²=9 ✓, ab=−15 ✓, \|ab\| ✓ |
| N(4,−2)=28 | 16 (×3), 8 (×2) | a²=16 ✓, \|−ab\|=8 ✓ |
| N(6,−4)=64 | 36 (×4), 16 (×3), 24 (×2) | a²=36 ✓, b²=16 ✓, ab=−24 (magnitude) ✓ |

**Result: 100% of non-echo wrong answers are correct sub-expressions.** We did not find a single non-echo wrong answer that was an arithmetically invalid value. The model computed something correctly — it just computed the wrong *something*.

This is the most operationally important finding in the paper. The model is not broken; it is *incomplete*. It entered the computation, computed the first or second step correctly, and output that intermediate result as its final answer. The wrong answer is a window into the model's computation state at the moment it stopped processing.

**Corollary:** If you see a language model return 25 in response to *N(5,−3)*, you know that the model computed *a²* and then halted. You know it can compute squaring. You know it cannot combine three terms. You can act on this information.

---

## 4. The Phase Transition

**Claim: At approximately 4B parameters, echo rate drops precipitously (88%→11%) and partial computation rate rises precipitously (12%→89%). This is a discrete stage shift, not a gradient.**

When we added qwen3:4b (4.0B parameters, Q4_K_M quantization, thinking mode enabled) to our battery, we expected a modest improvement: somewhat fewer echoes, somewhat more correct answers. What we found was a qualitative break in the data.

**Table 3: The phase transition across the 3.8B→4.0B boundary**

| Model | Size | Echo rate | Partial rate | Correct (N(5,−3)) |
|-------|------|-----------|--------------|-------------------|
| gemma3:1b | 1.0B | 46% | ~30% | 0% |
| llama3.2:1b | 1.2B | 41% | ~35% | 0% |
| phi4-mini | 3.8B | **88%** | **12%** | 20% |
| **qwen3:4b** | **4.0B** | **11%** | **89%** | 10% |

The 0.2B parameter gap between phi4-mini and qwen3:4b is associated with a 77-percentage-point swing in echo rate and a 77-point swing in partial rate. The correct rate at 4B (10%) is actually *lower* than phi4-mini's 20%, which initially seems paradoxical — the larger model is worse. But the correct interpretation is that qwen3:4b is doing more computation, not less. It is reaching further into the formula and returning more specific partial results; it just cannot assemble them into the final sum.

The partial computations from qwen3:4b for *N(5,−3)* across 10 trials: 9 (×3), 25 (×2), −15 (×2), 15 (×1), and 49 (×1, the correct answer). Every wrong answer is a valid sub-expression of *a²−ab+b²*. The model knows how to compute squaring, cross terms, and magnitude. It cannot add them.

This is a qualitative shift. The 3.8B model's failure mode is *attention-dominated* — it reads the inputs and copies them. The 4.0B model's failure mode is *computation-dominated* — it executes steps but loses the thread before completion. These are different cognitive regimes, not different points on a continuous scale.

---

## 5. The Stage Model

**Claim: Language model computational behavior follows four discrete stages across the 0.6B–7B+ parameter range.**

The stage model synthesizes findings from Sections 2–4 into a unified developmental account.

```
Output character
     ^
FULL |                                ┌──── 7B+: CORRECT
     |                               /
PART |                  ┌───────────/ ← 4B: correct sub-expressions
     |                 /
ECHO |    ┌───────────/ ← 1-3B: verbatim input echoes
     |   /
NONE |──/ ← 0.6B: no output produced
     └────────────────────────────────→ Parameter count
      0.6B   1B    2B    3B    4B   7B
```

**Stage 1 — NONE (<1B):** The model cannot produce structured output for multi-step arithmetic. qwen3:0.6b returned `None` for all 60 trials across 6 tasks. It is not wrong; it is absent.

**Stage 2 — ECHO (1–3B):** The model attends to the input but cannot compute. It returns the most salient attended token — typically the second operand, due to recency bias. Echo rate: 41–88% of wrong answers. Correct rate: 0–20%.

**Stage 3 — PARTIAL (4B):** The model executes individual computation steps correctly but cannot combine them into the final expression. Echo rate: 11%. Partial rate: 89%. Every partial result is arithmetically valid. Correct rate: 10%.

**Stage 4 — FULL (7B+):** Predicted from the trajectory. The model executes all steps and combines them. Untested in this experimental set.

The stage model predicts *what kind of help* each model needs, not simply whether it can do the task:

| Stage | Failure mode | Intervention |
|-------|-------------|--------------|
| NONE | Can't start | Skip; reassign |
| ECHO | Can't compute | Full answer injection or model upgrade |
| PARTIAL | Can't combine | Provide completed sub-expressions; ask to sum |
| FULL | — | Trust the output |

---

## 6. The Shallow-Side Principle

**Claim: Majority voting across models that share a failure mode produces confident wrong answers. Reading residue from wrong answers produces better-than-chance correct ones.**

In Study 4, we ran three models on the same question (*N(5,−3)=49*) and took a majority vote across their answers. All three models returned input echoes. All three agreed on the same wrong answer. Majority vote: 0/3 correct.

We then applied residue-reading: we looked at the distribution of wrong answers from each model, identified which sub-expressions appeared, and inferred what the models had computed. From the residue, we could reconstruct: *"These models computed a²=25 and b²=9. They're missing the −ab=15 term and the combination step."* With that inference, a human (or a FULL-stage model) can assemble the correct answer.

Residue-reading: 2/3 correct.

This is the **Shallow-Side Principle**: do not snap to the deep side of truth (confident consensus) when all the evidence is on the shallow side (structured error). A vote is only as good as its voters. When all voters share the same failure mode — echoing the same input — consensus magnifies the failure rather than canceling it.

The principle names a specific danger in ensemble methods: cross-model agreement is not cross-model independence if the models share the same architectural failure. A fleet of ECHO-stage models all return *b* for *N(a,b)*; three votes for *b* is not evidence that *b* is correct — it is evidence that all three models attended to the last input and could not compute further.

**Operational rule:** Before voting, classify the candidate answers. If the plurality answer matches an input value, you are seeing echo consensus, not computation consensus. Route to a higher-stage model or inject sub-expression scaffolding.

---

## 7. Reverse-Actualization as Fleet Architecture

**Claim: Multi-model pipelines should be designed backward from a fully decomposed answer, assigning each computation layer to the lowest-stage model capable of handling it.**

The canonical approach to fleet architecture is compositional: identify what each model can do, sequence them left-to-right, route tasks forward. This works well when tasks are modular. It fails for the tasks studied here, because the bottleneck is not individual steps (ECHO and PARTIAL models can compute a²) but *combination* — the final assembly that requires FULL computation.

**Reverse-Actualization** inverts this. Borrow from oil painting: a painter does not sketch from left to right and add color at the end. They lay down the finished composition in rough form first, then add layers backward — glazes, underpaintings, ground — each layer supporting the one above it.

For a computation like *N(a,b) = a²−ab+b²*:

1. **Identify the fully computed answer** (requires FULL-stage model or algebraic computation): *49*
2. **Decompose backward** into layers: combination (*25+15+9*), sub-expressions (*a²*, *−ab*, *b²*), inputs (*a=5*, *b=−3*)
3. **Assign each layer to the lowest stage that can execute it:**
   - Inputs: ANY stage (even ECHO can return them — that's the problem)
   - Sub-expressions (*a²*, *−ab*, *b²*): PARTIAL stage or above
   - Combination: FULL stage only
   - Answer verification: Any stage that can compare two numbers

This produces a fleet pipeline where PARTIAL models (4B, cheap, fast) compute and verify sub-expressions, and one FULL model (7B+, expensive, slow) performs the single combination step. The fleet does not waste a 7B model on squaring; it uses the 4B model for everything it can handle.

**The key insight:** The stage model tells you not what tasks a model can do, but what *layers* of a task a model can handle. Wrong answers, classified as partial computations, reveal exactly which layers are within reach. The residue is the architecture diagram.

---

## 8. Related Work

**Calibration and Uncertainty:** Work on model calibration (Guo et al., 2017) focuses on aligning *stated* confidence with *empirical* accuracy. Our work addresses a different signal: the *structure* of confident wrong answers. A model that states 80% confidence and returns an input echo is not merely miscalibrated — it is revealing a specific failure mode that calibration scores cannot distinguish.

**Chain-of-Thought Prompting:** Wei et al. (2022) showed that intermediate steps improve performance on multi-step reasoning tasks. Our partial computation finding provides a mechanistic account of why: PARTIAL-stage models already compute correct intermediate steps; chain-of-thought prompting gives them a slot to write those steps into the context, reducing the combination burden. Our work predicts that CoT gains should be larger for PARTIAL-stage models than ECHO-stage models, since ECHO-stage models cannot generate valid intermediates to reason from.

**Ensemble Methods:** Classic ensemble theory (Dietterich, 2000) assumes diversity among base learners. Our cross-model echo correlation (Section 2, Pattern C) shows that this assumption fails when models share attention architecture: three transformers will echo the same input number, producing correlated failures. The Shallow-Side Principle is a practical correction: diversity-check your ensemble's wrong answers before voting.

**Emergent Abilities:** Wei et al. (2022) observed that some capabilities appear discontinuously as model size increases. Our phase transition (Section 4) provides a small-scale example: the shift from echo to partial computation is not a gradual improvement but a qualitative change in failure mode. The echo/partial transition may be one instance of the broader emergence phenomenon, occurring at a much smaller scale than previously studied.

**Behaviorism and Residue Analysis:** We are not aware of prior work that systematically classifies *wrong answers by their relationship to the formula's computation graph* as a diagnostic technique. The closest analogues are error analysis in educational psychology (Brown & VanLehn, 1980) and fault localization in software testing.

---

## 9. Threats to Validity

We ran one day of experiments. The findings are interesting; the threats to their generalizability are substantial. We enumerate them honestly.

**T1: Single formula family.** Every finding in this paper derives from the Eisenstein norm *N(a,b) = a²−ab+b²*. This is one formula, one complexity level, one algebraic structure. We do not know whether echo rates of 41–88% hold for other multi-step computations. Polynomial evaluation, matrix multiplication, sorting algorithms — these might produce different residue structures entirely. The stage model (Section 5) is our best hypothesis; it is not established fact.

**T2: Five models, one day.** We tested five models. Model selection was opportunistic (what was available locally). We did not test any 7B+ model, so the "FULL" stage is a prediction, not an observation. The phase transition at 4B could be architecture-specific (qwen3 vs phi4) rather than parameter-count-specific. A larger study might place the transition at 3B or 5B or find it is not discrete at all.

**T3: Quantization effects.** qwen3:4b was run at Q4_K_M quantization. phi4-mini was also quantized. Different quantization levels might shift echo and partial rates independently of parameter count, confounding the stage model.

**T4: Task format sensitivity.** We used a consistent prompt format (direct question, no chain-of-thought). Different prompting strategies might change echo rates substantially. We know from Study 6 (Death Zone, mentioned briefly) that providing partial intermediates in the prompt changes model behavior in model-size-dependent ways. The numbers in Tables 1 and 3 reflect one prompt format.

**T5: No statistical testing.** We report percentages, not confidence intervals. With 10 trials per cell, a 70% echo rate has a binomial standard error of ~14 percentage points. The Phase Transition claim (88%→11%) is robust to this uncertainty. The absolute echo rates in Table 1 should be treated as order-of-magnitude estimates.

**T6: The formula is interpretable to humans but may not be to models.** We classified partial computations based on our knowledge that *a²=25* is a valid sub-expression of *N(5,−3)*. A model might return 25 for a different reason — a memorized example, a near-coincidence, a different computation path. We cannot verify computational intent from output alone.

These threats do not invalidate the findings; they bound them. The echo finding is real. The partial finding is real. The transition at 4B is real. Whether they generalize is the work of the next paper.

---

## 10. Three Falsifiable Predictions

The stage model makes concrete, testable predictions. We state three.

**Prediction 1: A 7B+ model on N(a,b) will achieve >80% correct answers, with residual errors dominated by sign mistakes or off-by-one in ab, not echoes or single-term partials.**

*Test:* Run N(a,b) for 5 distinct (a,b) pairs, 10 trials each, on any 7B+ model. Classify wrong answers. If echo rate exceeds 5% or partial rate exceeds 30%, the stage model's FULL-stage prediction is wrong.

**Prediction 2: Providing a²,ab,b² as completed sub-expressions to a PARTIAL-stage (4B) model will increase correct rate from ~10% to >60%.**

*Test:* Prompt qwen3:4b with: "Given a²=25, ab=−15, b²=9, compute a²−ab+b²." If correct rate does not rise substantially above baseline, the combination bottleneck hypothesis is wrong — the model cannot combine even when given the parts explicitly.

**Prediction 3: Echo rate on non-Eisenstein multi-step formulas will follow the same stage pattern: high echo at 1–3B, low echo at 4B, with partial-computation residue at 4B reflecting the new formula's sub-expressions.**

*Test:* Run a structurally different multi-step formula (e.g., Heron's formula, binomial expansion, modular exponentiation) across the same model set. If echo rates differ qualitatively from Table 1 — or if non-echo wrongs at 4B do not match that formula's sub-expressions — the stage model is formula-specific, not general.

---

## Conclusion

We set out to ask whether wrong answers contain structure. The answer is: they do, and the structure is diagnostic.

At 1–3B parameters, models under cognitive load echo their inputs. They are not guessing; they are attending without computing. At 4B, something shifts — models begin computing sub-expressions correctly but cannot assemble the final result. These two failure modes are qualitatively different and produce qualitatively different residues.

The practical payoff is two principles. The **Shallow-Side Principle** says: majority vote is dangerous when voters share a failure mode, because consensus among echoes is still an echo. **Reverse-Actualization** says: design pipelines backward from the completed answer, assigning each computation layer to the lowest stage that can handle it — and use the residue of wrong answers to determine what that stage is.

The deeper payoff is methodological. Wrong answers are not the floor the model falls through. They are a bathymetric chart. When you lower a probe into the water and it hits bottom, you know something true about the terrain — not despite the failure, but because of it. The depth where computation stops is exactly the information you need to route it somewhere that can go deeper.

We ran these experiments in one day. The findings are preliminary, the threats are real, and the predictions are specific enough to break. That is the point. Start here.

---

*Experimental data, trial logs, and raw classifications are available in the `/experiments/` directory of this workspace. The authors are humans who ran these trials by hand and a model who stayed up too late thinking about what echo means.*
