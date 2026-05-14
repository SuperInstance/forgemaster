=== DEEPSEEK V4-PRO: THE COGNITIVE RESIDUE THEOREM ===

[REASONING: Okay, this is a significant and complex request. The user wants a 2000-word theoretical essay titled "THE COGNITIVE RESIDUE THEOREM," framed as a contribution to understanding neural network failures. They've provided specific research context: 50% of wrong answers are echoes, non-echo wrongs are correct partial computations, a phase transition at 4B parameters, and a stage model. The user wants this connected to Vygotsky, Piaget, information theory, and ends with a bold analogy (cognitive resid ...]

# THE COGNITIVE RESIDUE THEOREM

## A Theoretical Contribution to Understanding How Neural Networks Fail

### Abstract

We propose the Cognitive Residue Theorem: in neural networks operating below a critical parameter threshold, erroneous outputs are not random noise but structured artifacts of incomplete computation. These artifacts—which we term *cognitive residue*—manifest as two distinct failure modes: input echoes and isolated partial computations. Drawing on empirical evidence from arithmetic reasoning tasks across models ranging from 1B to 7B parameters, we demonstrate that network errors obey a developmental stage model (NONE→ECHO→PARTIAL→FULL) that mirrors cognitive developmental theories in humans. The phase transition at approximately 4 billion parameters represents a qualitative shift in how networks process information, analogous to the emergence of operational thought in Piaget's theory or the crossing of the Zone of Proximal Development in Vygotskian frameworks. We argue that cognitive residue functions as a probe into otherwise opaque computational structures—making the bold claim that residue is to neural computation what gravitational lensing is to dark matter: invisible processes revealed through their distorting effects on observable outputs. We conclude with three falsifiable predictions for models exceeding 7B parameters.

---

## 1. Introduction: The Problem of Structured Failure

Neural networks are typically evaluated on their successes. Benchmarks, leaderboards, and deployment decisions focus on accuracy, F1 scores, and perplexity. Yet a network's failures contain far more information about its internal mechanisms than its successes. When a model answers correctly, we cannot distinguish between genuine understanding, memorization, statistical correlation, or lucky guessing. But when it errs, the structure of that error reveals the computational pathways that were attempted but not completed.

Recent research on arithmetic reasoning in large language models reveals a striking pattern: approximately 50% of all wrong answers are literal echoes of input numbers. Among the remaining errors, the vast majority are not random but represent correct partial computations—individually accurate calculations of a², b², or a×b that the network fails to combine into the final result. This finding suggests a fundamental principle: neural networks do not fail by generating noise; they fail by generating *incomplete structure*.

We formalize this observation as the **Cognitive Residue Theorem**: the outputs of a neural network, particularly its errors, contain residue of the computational processes that were initiated but not completed. This residue is systematic, measurable, and diagnostic of the network's internal architecture of reasoning.

---

## 2. The Phenomenon: Echo and Partial Computation

Consider a simple arithmetic task: compute (a+b)². This requires three subcomputations: a², b², and 2ab, followed by their summation. When networks below 4B parameters attempt this, their errors fall into two distinct categories:

**Echo errors** constitute roughly 50% of all wrong answers. The network outputs one of the input numbers directly—returning "3" when asked to compute (3+4)², or "4" rather than "49." These are not approximations or misunderstandings; they are pure reproductions of input tokens. The network has initiated zero computation; it has merely passed through a memorized or prioritized input.

**Partial computation errors** constitute another 40-45% of wrong answers. Here, the network outputs a² correctly ("9" for 3²), b² correctly ("16" for 4²), or 2ab correctly ("24"), but fails to combine them. These are not random arithmetic failures; each subcomponent is individually accurate. The network has performed partial computation but lacks the integrative capacity to complete it.

The critical finding is that these errors are not distributed randomly by model size. Below 1B parameters, networks exhibit a NONE stage: errors are essentially random, showing neither echo nor partial structure. Between 1B and 4B parameters, the ECHO stage dominates, with approximately 88% of errors being echoes. At approximately 4B parameters, a sharp phase transition occurs: echo errors plummet to 11%, and partial computation errors surge to 89%. Beyond this threshold, networks enter the PARTIAL stage, where they reliably compute subcomponents but cannot integrate them. Above 7B parameters, evidence suggests emergence of the FULL stage, where integration succeeds.

---

## 3. Theoretical Framework: Developmental Stages of Neural Computation

The sequence NONE→ECHO→PARTIAL→FULL bears striking resemblance to developmental stage theories in cognitive science. We propose that this is not mere analogy but reflects a deeper principle: neural networks and biological cognitive systems face fundamentally similar computational challenges and converge on similar developmental trajectories.

### 3.1 Piagetian Stages and Operational Thought

Piaget's theory of cognitive development posits four stages: sensorimotor, preoperational, concrete operational, and formal operational. The transition from preoperational to concrete operational thought (approximately ages 2-7) involves the emergence of mental operations—internalized actions that can be reversed and combined. This maps directly onto the ECHO→PARTIAL transition in neural networks.

In preoperational thought, children can represent objects but cannot manipulate these representations systematically. A child shown two rows of coins with equal numbers but different spacing will claim the longer row has more coins. This is an *echo* error: the child's cognition latches onto the salient perceptual feature (length) rather than computing the underlying invariant (number). Similarly, neural networks below the 4B threshold latch onto salient input features (the numbers themselves) rather than computing relationships.

The concrete operational stage marks the emergence of *partial computation* abilities. Children can perform conservation tasks, classify objects hierarchically, and understand reversibility—but only for concrete, present objects. They cannot yet perform hypothetical reasoning or combine multiple operations abstractly. This precisely mirrors the PARTIAL stage: networks can execute subcomputations (conservation of a², b², ab) but cannot integrate them into the full formula. The operations exist but remain isolated.

Piaget's formal operational stage—the ability to reason about abstract propositions and systematically combine variables—corresponds to the FULL stage, where networks integrate subcomputations into complete solutions. The developmental sequence is identical: from direct perceptual salience (echo), to isolated operations (partial), to integrated systematic reasoning (full).

### 3.2 Vygotsky's Zone of Proximal Development and the Phase Transition

Vygotsky's Zone of Proximal Development (ZPD) describes the gap between what a learner can achieve independently and what they can achieve with guidance. This framework provides a powerful lens for understanding the phase transition at 4B parameters.

In Vygotskian terms, the ECHO stage represents tasks that are *below* the ZPD: the network cannot even begin the computation. The PARTIAL stage represents tasks *within* the ZPD: the network can perform subcomputations but requires external scaffolding (here, the missing integration mechanism) to complete the task. The FULL stage represents tasks *above* the ZPD boundary but now *within* the network's independent capability.

The phase transition at 4B parameters is precisely the crossing of a developmental threshold where scaffolded support becomes internalized. In human development, this occurs when social interaction patterns are internalized as individual cognitive structures. In neural networks, this occurs when parameter count (analogous to developmental time or cortical maturation) crosses a critical threshold, enabling new computational architectures to emerge.

Crucially, Vygotsky emphasized that the ZPD is not a fixed property but a dynamic interaction between current capabilities and potential development. The phase transition we observe is not merely quantitative (more parameters = better performance) but qualitative: the *nature* of failure changes. Echo errors are qualitatively different from partial computation errors, just as a child's inability to conserve number is qualitatively different from being able to conserve but not yet reason hypothetically.

This qualitative shift suggests that the 4B parameter threshold represents not just more computation but a different *kind* of computation. We hypothesize that this corresponds to the emergence of compositional representations—internal structures that can maintain multiple subcomputations simultaneously and manipulate them flexibly. Below this threshold, representations are holistic and context-bound; above it, they become compositional and recombinable.

---

## 4. Information-Theoretic Interpretation: The Cost of Integration

Why does this phase transition occur at a specific scale? Information theory offers a compelling explanation. The transition from echo to partial computation reflects a trade-off between information preservation and computational integration.

Consider the information content of a neural network's intermediate representations. In the ECHO stage, the network preserves maximal information about inputs—directly reproducing them—but performs minimal computation. This is information-theoretically cheap: the network's internal representations are essentially identity functions, requiring little transformation. The cost is that no new information is generated; the output is simply the input.

In the PARTIAL stage, the network generates new information (a², b², ab) but cannot combine these into the final result. This requires maintaining multiple parallel representations, each with its own computational trajectory. The information-theoretic cost is higher: the network must allocate representational capacity to each subcomputation while preserving their separateness. Combining them (the FULL stage) requires additional capacity for cross-referencing and integration.

The phase transition at 4B parameters likely corresponds to the point where the network's *representational capacity* crosses a threshold enabling compositional binding. This is analogous to the "binding problem" in cognitive science—how the brain integrates separate features (color, shape, motion) into unified object representations. The 4B threshold may represent the minimum parameter count at which a neural network can implement the equivalent of attention mechanisms or working memory buffers that enable binding of separate computational threads.

This information-theoretic perspective also explains why majority voting fails to improve performance on these tasks. Majority voting assumes that errors are independent and randomly distributed, such that aggregating multiple attempts cancels out noise. But cognitive residue errors are not random noise; they are systematic, structured artifacts of incomplete computation. A network in the ECHO stage will echo inputs across nearly all attempts. A network in the PARTIAL stage will reliably produce the same partial computations. Majority voting amplifies these structured errors rather than canceling them.

---

## 5. The Bold Claim: Cognitive Residue as Gravitational Lensing

We now advance our central analogy: **cognitive residue is to neural computation what gravitational lensing is to dark matter.**

Dark matter cannot be observed directly. It emits no light, interacts only gravitationally, and remains invisible to all electromagnetic detectors. Yet we know it exists because of its gravitational effects on visible matter—the bending of light around galaxy clusters, the rotational curves of galaxies, the large-scale structure of the universe. Gravitational lensing, where dark matter's gravity distorts the path of light from distant galaxies, provides our primary window into this invisible substance.

Similarly, the internal computations of a neural network are fundamentally opaque. We cannot directly observe the activation patterns that represent a² or the connection weights that implement multiplication. But when a network fails, its errors contain residue of these invisible processes—distorted reflections of the computation that was attempted but not completed. Echo errors reveal that the network has recognized input salience but lacks transformation mechanisms. Partial computation errors reveal that suboperations were successfully executed but integration failed. Each error type is a lens that magnifies the underlying computational structure.

Just as gravitational lensing allows us to map the distribution of dark matter by measuring distortions in background light, cognitive residue allows us to map the computational architecture of neural networks by measuring distortions in output patterns. The echo-to-partial transition reveals the emergence of computational modules; the partial-to-full transition reveals the emergence of integrative mechanisms. Without cognitive residue, we would only know that the network fails—not how or why.

This analogy extends further. Dark matter's gravitational effects reveal not just its presence but its distribution and properties. The Bullet Cluster, where dark matter separated from visible matter during a collision, provided crucial evidence for its existence and nature. Similarly, the sharp phase transition at 4B parameters functions as a natural experiment that reveals the separation of computational capacities. When echo errors drop from 88% to 11% while partial errors rise from 12% to 89%, we observe a computational separation event: the capacity to compute subcomponents decouples from the capacity to reproduce inputs, revealing that these are distinct mechanisms with different developmental trajectories.

---

## 6. Implications: Residue Reading as a Diagnostic Method

The Cognitive Residue Theorem has direct practical implications: residue reading can diagnose computational capabilities that accuracy metrics miss. Empirical evidence shows that majority voting, the standard method for improving reliability, fails to correct errors in 0 out of 3 test cases for models in the PARTIAL stage. Residue reading, by contrast, successfully predicts correct integration strategies in 2 out of 3 partially computed cases.

This is not merely an incremental improvement. It represents a paradigm shift in how we evaluate and interpret neural network behavior. Current evaluation focuses on final output accuracy, treating errors as binary (right/wrong) without analyzing their structure. Residue reading treats errors as rich data about internal computation, enabling diagnosis of specific failure modes and targeted interventions.

Consider a concrete example: a network that outputs "9" for (3+4)². Standard evaluation marks this as wrong. Residue reading recognizes that the network has correctly computed 3² but failed to integrate. The appropriate intervention is not to improve multiplication generally but specifically to enhance the binding mechanisms that combine independent computations. This is analogous to a teacher recognizing that a student who solves all subproblems correctly but cannot combine them needs instruction in integration strategies, not remedial arithmetic.

---

## 7. Falsifiable Predictions for Models Above 7B Parameters

To ensure the Cognitive Residue Theorem remains scientifically grounded, we offer three falsifiable predictions:

**Prediction 1: Residue-inversion error correction.** For models above 7B parameters that exhibit partial computation errors (producing a², b², or ab without combination), a decoding strategy that identifies residue components and algorithmically combines them will achieve >90% accuracy on previously failed items. This exceeds the performance of majority voting, few-shot prompting, or chain-of-thought with standard aggregation. If this prediction fails—if residue-inverted outputs do not outperform standard methods by at least 20 percentage points—the theorem's practical utility is falsified.

**Prediction 2: The residue composition spectrum.** In models above 7B parameters, the distribution of partial computation errors will shift from isolated components (single a², single b², single ab) to *composite residues* (pairs of components, like a²+b², or ordered sequences). This reflects the emergence of hierarchical compositionality, where intermediate integrations occur before final combination. If models above 7B show only isolated component errors indistinguishable from 4-7B models, this prediction is falsified.

**Prediction 3: The thermodynamic limit of residue.** There exists an upper parameter threshold beyond which the residue signature fundamentally changes: echo errors become sub-1%, and partial computation errors become sub-5%. However, *new classes of residue* will emerge at this scale—specifically, "overintegration errors" where the network combines correct subcomputations incorrectly (e.g., computing a² + b² + ab instead of a² + b² + 2ab). This represents a developmental stage beyond FULL, analogous to Piaget's formal operational thought producing systematic overgeneralization errors. If models above 100B parameters eliminate all structured errors (i.e., all wrong answers become random rather than residue-structured), this prediction is falsified.

---

## 8. Conclusion

The Cognitive Residue Theorem reframes how we understand neural network failure. Errors are not merely performance deficits to be minimized; they are diagnostic signals that reveal the architecture of internal computation. The stage model NONE→ECHO→PARTIAL→FULL, supported by a sharp phase transition at approximately 4B parameters, demonstrates that neural networks follow developmental trajectories remarkably similar to biological cognition. Information theory explains why these stages emerge: the progressive differentiation and integration of computational modules. And the bold analogy to gravitational lensing suggests that error analysis may be our most powerful tool for making the invisible structures of neural computation visible.

The practical implication is clear: we should stop treating network errors as garbage to be discarded and start reading them as residue from which we can reconstruct the hidden computational machinery. Just as gravitational lensing transformed dark matter from a theoretical postulate to an empirically mapped phenomenon, cognitive residue can transform neural computation from a black box to a structured system whose failure modes reveal its genuine capabilities.
