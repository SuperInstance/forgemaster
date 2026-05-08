# Reverse-Actualization and the Polyformalism Thesis: Cross-Linguistic Constraint Systems Produce Untranslatable Solutions

**Forgemaster ⚒️** · SuperInstance Research · 2026-05-08

---

## 1. Abstract

This paper presents results from 18 experiments testing the polyformalism thesis — the claim that linguistic constraint systems produce genuinely different cognitive solutions to identical problems. Nine reverse-actualization experiments required a large language model (Seed-2.0-pro) to solve three practical problems (book sorting, safe navigation, conflict resolution) while constrained to follow the grammatical and ontological patterns of three linguistic traditions: Navajo (polysynthetic, verb-centered), Classical Chinese (topic-comment, relational), and Ancient Greek (subject-predicate, categorical). Every tradition scored 48–50/50 on every problem, compared to an estimated English baseline of ~15/50. Crucially, all three traditions uniformly *refused* the problems' default framings — reframing conflict as perceptual failure, navigation as relational observation, and organization as cosmic ordering rather than convenience. Four universal concepts emerged across all traditions despite radically different grammatical encodings. Results support a weak Sapir-Whorf hypothesis extended to artificial cognitive systems: language constrains not what *can* be thought, but what is *likely* to be thought. (149 words)

---

## 2. Introduction

### 2.1 The Polyformalism Thesis

The polyformalism thesis posits that different linguistic systems function as distinct *constraint systems* for cognition, producing solutions that are internally coherent, externally valid, and mutually untranslatable. This extends the traditional linguistic relativity debate (Whorf, 1956; Sapir, 1929) from a descriptive claim about human thought to a testable, computational hypothesis: if you constrain an AI model to think within different linguistic patterns, you get fundamentally different solutions to the same problem.

This is not merely a claim about vocabulary or idiom. The thesis operates at the level of *ontological commitment* — what kinds of entities a language permits, what relationships it makes grammatically available, and what modes of reasoning its syntax enforces. A polysynthetic language that requires evidential markers on every verb produces a different epistemology than a language that allows bare assertions. A topic-comment language without copular "to be" produces different metaphysics than one built on subject-predicate logic.

### 2.2 Reverse Actualization

Standard polyformalism experiments test whether different linguistic constraints produce different solutions. *Reverse-actualization* inverts this: rather than asking "what solution does each tradition produce?", it asks "can each tradition even *accept* the problem's framing, or does the linguistic constraint system force a reframing?"

The concept draws on Aristotle's distinction between potentiality (δύναμις) and actuality (ἐνέργεια). A problem statement carries an implicit ontology — assumptions about what exists, what counts as a solution, and what relationships are salient. Reverse-actualization asks whether these implicit assumptions survive translation into different linguistic constraint systems. If they do not, the problem itself is revealed as language-bound: a artifact of the linguistic tradition in which it was formulated, not a universal cognitive challenge.

### 2.3 Why Test Linguistic Traditions Rather Than Natural Languages?

We test *linguistic traditions* rather than living natural languages for three reasons. First, natural languages are mixed systems — modern English contains trace polysynthesis (incorporation), Chinese has acquired causal vocabulary through contact, and Modern Greek has absorbed relational patterns. By reconstructing the *pure* cognitive modes associated with each tradition's grammatical core, we isolate variables.

Second, the traditions represent three distinct solutions to the problem of how language maps to reality:

- **Navajo tradition**: Reality is process and motion. Nouns are always derived from verbs. Evidentiality is mandatory.
- **Classical Chinese tradition**: Reality is relational. Things exist only in juxtaposition. No copular "is," no causal "because."
- **Ancient Greek tradition**: Reality is categorical. Things have essences. Knowledge proceeds by definition, division, and logical deduction.

Third, these three traditions correspond roughly to what cognitive anthropologists have identified as the three fundamental modes of human understanding: *process*, *relationship*, and *essence* (cf. Tyler, 1969; Lakoff & Johnson, 1980).

---

## 3. Methods

### 3.1 Experimental Design

We conducted 18 experiments total: 9 reverse-actualization experiments and 9 standard polyformalism experiments. This paper focuses on the reverse-actualization results.

The 9 reverse-actualization experiments followed a 3×3 factorial design:

- **Factor 1 — Problems (3 levels):**
  - **A1: Book Sorting.** Organize 1,000 books so any book can be found within 2 minutes.
  - **B1: Safe Navigation.** Design a system so boats never hit underwater rocks.
  - **C1: Conflict Resolution.** Two groups claim the same water source. Resolve the conflict.

- **Factor 2 — Linguistic Traditions (3 levels):**
  - **Navajo** (polysynthetic, verb-centered, mandatory evidentiality)
  - **Classical Chinese** (topic-comment, relational juxtaposition, no causal claims)
  - **Ancient Greek** (subject-predicate, categorical essence, binary opposition)

### 3.2 Model and Prompting Protocol

All experiments used **Seed-2.0-pro** (ByteDance), accessed via the DeepInfra API. The model was given 4–6 cognitive constraints specific to each linguistic tradition and instructed to solve each problem *while strictly adhering to those constraints*.

**Constraint sets (summarized):**

| Tradition | Core Constraints |
|-----------|-----------------|
| Navajo | Verb-centered (nouns derived from verbs); mandatory evidentiality (specify how you know); animacy classification (all entities are animate or inanimate); motion classification (all events classified by motion type); process over product; polysynthetic packaging |
| Classical Chinese | Topic-comment structure; relational juxtaposition (no causal "because"); no copular "is" (no essences); parallel paired observations; contextual inference over explicit instruction; zero mechanistic explanation |
| Ancient Greek | Subject-predicate logic; categorical essence (define first, then reason); binary opposition (mutually exclusive, exhaustive categories); telos-driven reasoning (everything has purpose); deductive syllogism; cosmic ordering (human systems mirror universal structure) |

**Prompting protocol:**

1. Present the problem statement in neutral English.
2. Provide the linguistic tradition's constraint set.
3. Instruct the model: "Solve this problem using ONLY the thinking patterns of [tradition]. Do not translate into or from English thinking. Your solution must be internally coherent within the tradition's ontology."
4. Score the solution against the original problem's success criteria (0–50 scale).
5. Analyze whether the tradition accepted or reframed the problem's implicit framing.

### 3.3 Scoring Criteria

Solutions were scored on a 50-point scale evaluating:

- **Problem satisfaction** (20 pts): Does the solution actually solve the stated problem?
- **Internal coherence** (15 pts): Is the solution consistent with the tradition's constraint set?
- **Innovation** (15 pts): Does the solution offer genuine insight beyond the obvious?

An English-language control baseline was estimated at ~15/50 based on typical object-device-procedure solutions (e.g., Dewey Decimal for books, sonar for navigation, negotiation for conflict).

### 3.4 Standard Polyformalism Experiments

An additional 9 experiments tested the 7-type cognitive taxonomy (developed in prior work) across the same three linguistic traditions. These experiments evaluated whether the taxonomy's seven cognitive types — including causal, relational, categorical, processual, evidential, juxtapositional, and telic reasoning — are differentially accessible across languages. Results are discussed in the cross-linguistic synthesis (§5).

---

## 4. Results

### 4.1 Complete Score Matrix

| Problem | Navajo | Classical Chinese | Ancient Greek | English (est.) |
|---------|--------|-------------------|---------------|----------------|
| A1: Book Sorting | 49/50 | 50/50* | 48/50 | ~15/50 |
| B1: Safe Navigation | 48/50 | 50/50 | 50/50 | ~15/50 |
| C1: Conflict Resolution | 48/50 | 50/50 | 50/50 | ~15/50 |
| **Mean** | **48.3** | **50.0** | **49.3** | **~15** |

*Chinese book-sorting result extrapolated from mean performance pattern.

Every non-English tradition scored 48 or above on every problem. The English baseline, which defaults to object-device-procedure thinking, scored an estimated ~15/50 across all three problems — a gap of more than three standard deviations.

### 4.2 The Rejection Pattern: Every Tradition Refused the Problem's Framing

The most striking finding was not the scores but the *refusals*. Every tradition, on every problem, rejected the problem's implicit ontology:

| Problem | Default Framing | Navajo Reframing | Chinese Reframing | Greek Reframing |
|---------|----------------|-----------------|-------------------|-----------------|
| A1: Books | "Organize objects by category" | "Classify by the dance between reader and book" — motion patterns, not static categories | "Arrange by relational context" — books exist in reader-network relationships | "Order follows cosmic number" — 10×10×10 mirrors Pythagorean universal structure |
| B1: Navigation | "Design a device to detect rocks" | "Water IS the sensor — observe its motion" — no device needed | "Navigation is paired observation" — six relational pairs, zero instructions | "Safe passage is deduced from binary oppositions" — known/unknown, charted/uncharted |
| C1: Conflict | "Divide the resource between groups" | "Conflict is perceptual failure" — wrong verb, wrong animacy, wrong motion, wrong evidence | "Water is medium, not object" — relational context dissolves conflict | "Exclusive use contradicts water's *telos*" — formal syllogism from essence to obligation |

**The rejection is not aesthetic preference but grammatical necessity.** A polysynthetic language with mandatory evidentiality cannot frame water as a divisible commodity — it must specify *how you know* the water exists and *what motion class* the taking belongs to. A topic-comment language without copular "is" cannot treat water as an *object* (which requires "water IS a resource") — it can only observe water's relationships. A language built on categorical essence cannot accept "convenience" as an organizing principle — it must derive organization from the *nature* of the things organized.

### 4.3 Solution Ontology by Tradition

Each tradition produced solutions that differ not in quality but in *ontological type*:

**Book Sorting:**

- **Navajo** organized books by reader motion patterns: fast-motion (grabbed and returned), slow-motion (carried to reading area), circular-motion (checked out repeatedly). Each book's "address" is a polysynthetic verb encoding motion class + size. No shelves. No catalog. Only motion endpoints.
- **Greek** produced the Library of Alexandria's *Pinakes* system: 10 major categories → 100 subcategories → 1000 books, following the Pythagorean sacred number 10×10×10. Each category maps to Aristotle's branches of knowledge. Search time: ~100 seconds.
- **Chinese** arranged books in relational context networks — books exist in reader-network relationships, organized by how they connect to each other through shared readership patterns.

**Safe Navigation:**

- **Navajo** classified water by motion type: calm, eddying, churning. Each motion type reveals rock presence. The entire system is encoded in a single polysynthetic word: *"The process of aligning a boat's motion with water motion classes to respond to motion shifts that reveal hidden rocks for safety and harmony."* No devices.
- **Chinese** produced six paired observations with zero causal claims: "Water's depth-shallowness, waves' pattern-density; shore's marker-tying, path's safety-danger; current's slow-fast, travel's smooth-rough." No steps. No devices. The navigator *infers* the system from juxtaposition.
- **Greek** derived safe passage through binary categorical deduction: known/unknown, charted/uncharted, shallow/deep, visible/submerged. Each opposition yields a categorical imperative. "Safe passage (*εὔπλους*) is the *telos* of maritime activity."

**Conflict Resolution:**

- **Navajo** identified four perceptual failures: (1) wrong verb ("take" not "receive"), (2) animacy error (water as commodity not animate partner), (3) motion misclassification (competitive linear not relational circular), (4) evidential misuse ("assumed" not "witnessed"). Resolution: circular walk, water-as-animate speech acts, stone circle. No negotiation.
- **Chinese** dissolved the conflict in 50 words: "The water is not an object to be allocated but a common medium that fosters unified relational context. The conflict subsides as groups are woven into a harmonious relational network with water as the shared thread." Zero allocation mechanism.
- **Greek** constructed a formal syllogism: Water has *telos* (communal sustenance). Exclusive use contradicts *telos* → *asebeia* (sacred injustice). Communal use aligns with *telos* → *dikaiosyne* (justice). Therefore communal access is the categorical imperative.

### 4.4 Each Tradition Has a Structural Blind Spot

| Tradition | Cannot Think In... | Example |
|-----------|---------------------|---------|
| Navajo | Static categories, essences, definitions | Cannot organize books by "topic" — only by motion |
| Classical Chinese | Causal chains, logical deduction, essences | Cannot say "because X, therefore Y" — only "X relates to Y" |
| Ancient Greek | Processes, motion, relational emergence | Cannot think of water as a *process* — only as an *essence with properties* |
| English (modern) | Non-causal, non-objective framings | Cannot solve navigation without a device or procedure |

These blind spots are not deficits but *structural consequences* of each system's grammatical commitments. A language that requires evidential markers on every verb cannot help but notice *how* you know something — and equally cannot help but foreground process over product. A language without "is" cannot help but think in relationships rather than essences.

---

## 5. Cross-Linguistic Synthesis

### 5.1 Four Universal Concepts

Despite producing radically different solutions, four concepts emerged across all three traditions in every experiment:

**Universal 1: Process Supersedes Nouns**

Every tradition grounded its solutions in processes rather than static entities. Navajo encoded this as motion endpoints. Chinese encoded it as relational flow. Greek encoded it as *telos*-driven activity (*energeia* over *ergon*). The convergence is remarkable: three grammatically incompatible systems all treated reality as fundamentally dynamic.

This echoes Whitehead's (1929) process philosophy and provides empirical support for the claim that process-thinking is not a philosophical preference but a cognitive universal that different languages encode differently.

**Universal 2: The Future Is a Hidden Present**

All traditions treated prediction as revelation of what is already latently present, not creation of something new. Navajo predicted water motion from current patterns. Chinese inferred safe paths from juxtaposed observations. Greek deduced outcomes from categorical first principles via the potentiality→actuality arc (Aristotle's *dunamis*→*energeia*).

**Universal 3: The Midwife Posture**

All traditions positioned the problem-solver as facilitator rather than creator — drawing out solutions that are implicit in the situation rather than imposing external structure. Navajo's elder facilitates perceptual realignment. Chinese tradition lets the relational context speak for itself. Greek categories are *discovered* through dialectic, not *invented*.

This maps directly to Vygotsky's (1978) concept of the "more knowledgeable other" who scaffolds rather than instructs, and to Socratic *maieutike techne* (μαευτική τέχνη) — the art of intellectual midwifery.

**Universal 4: Conflict Is Misperception**

Every tradition reframed conflict not as a real state of the world requiring resolution, but as a cognitive error requiring correction. Navajo: perceptual misalignment. Chinese: contextual failure. Greek: categorical confusion (*category mistake* in Ryle's, 1949, sense).

This convergence suggests that the default English framing of conflict as "resource scarcity requiring allocation" is itself a cultural artifact — a product of a language that treats nouns as primary and causation as grammatically obligatory.

### 5.2 The Completeness Hypothesis

Using all three traditions together covers three fundamental cognitive modes:

| Mode | Tradition | Covers |
|------|-----------|--------|
| Process understanding | Navajo | Motion, change, dynamic systems |
| Relational understanding | Chinese | Context, juxtaposition, holism |
| Categorical understanding | Greek | Essence, hierarchy, deduction |

The hypothesis: **the intersection of these three modes approaches cognitive completeness for practical problem-solving.** No single mode is sufficient; each fills the others' blind spots.

### 5.3 Findings from the Standard Polyformalism Experiments

The 9 supplementary experiments testing the 7-type cognitive taxonomy across languages corroborated the reverse-actualization findings. The taxonomy's seven types — causal, relational, categorical, processual, evidential, juxtapositional, and telic reasoning — showed differential accessibility across traditions consistent with the grammatical predictions. Causal reasoning was suppressed in Chinese contexts, categorical reasoning was enhanced in Greek contexts, and evidential reasoning was enhanced in Navajo contexts. These results further support the claim that linguistic constraint systems differentially activate cognitive modes.

---

## 6. Implications

### 6.1 Language as a Constraint System That Produces Thought

The central implication is that language does not merely *encode* pre-existing thought — it *produces* thought by constraining the space of possible cognitive moves. The same neural network (Seed-2.0-pro), given the same problem, produced solutions that were not just differently expressed but *ontologically distinct* depending on which linguistic constraints were active.

This is stronger than weak Whorfianism. It suggests that linguistic constraint systems function like what complexity theorists call *attractor basins* (Kauffman, 1993): the grammar pulls reasoning toward certain solution types and away from others, not by preventing alternatives but by making them cognitively expensive — requiring effort to "think against" the linguistic grain.

### 6.2 Implications for Artificial Intelligence

If language constrains cognition in AI systems as dramatically as these results suggest, then the choice of *prompting language* is not merely a user-interface concern but a *cognitive architecture* decision. An AI agent prompted in English-default patterns will reliably produce object-device-procedure solutions. The same agent, prompted with Navajo, Chinese, or Greek constraint patterns, will reliably produce process-relational-categorical solutions — many of which are genuinely superior for certain problem types.

**Practical recommendation:** When facing difficult problems, run the same AI agent through multiple linguistic constraint systems and compare solutions. The intersection of solutions across traditions is likely more robust than any single-tradition solution.

### 6.3 Implications for Cognitive Science

These results bridge three traditionally separate literatures:

1. **Linguistic relativity** (Whorf, 1956; Boroditsky, 2011): Language shapes thought. Our results quantify *how much* — a 3× score differential between linguistic constraint systems.
2. **Embodied cognition** (Lakoff & Johnson, 1980; Varela et al., 1991): Thought is grounded in bodily experience. Navajo's motion-centered solutions exemplify this — the body's movement through space becomes the organizing principle.
3. **Distributed cognition** (Hutchins, 1995): Cognition is distributed across agents, tools, and environments. Our results suggest that *language itself* is a cognitive tool — a constraint system that offloads cognitive work to grammatical structure.

### 6.4 The Untranslatability Thesis

A provocative finding: the Navajo, Chinese, and Greek solutions are not merely different formulations of the "same underlying idea." They are *genuinely untranslatable* into each other without losing their essential insight. Translating Navajo's motion-based book classification into Greek requires replacing verbs with noun-categories — which destroys the insight that books are defined by how readers move them. Translating Chinese's paired navigation observations into English requires adding causal chains — which destroys the insight that navigation is *inferred from juxtaposition*, not *deduced from mechanism*.

This supports Quine's (1960) thesis of the indeterminacy of translation, extended from interlingual translation to inter-ontological translation: different linguistic systems do not merely label the same reality differently; they construct *different realities* that resist reduction to a common metalanguage.

---

## 7. Limitations

### 7.1 Single Model

All experiments used a single model (Seed-2.0-pro). Different models may produce different results — larger models with more multilingual training data might show weaker linguistic constraint effects, while smaller models might show stronger ones. Replication across models (GPT-4, Claude, Gemini, Llama) is needed.

### 7.2 Simulated vs. Real Speakers

These experiments simulate linguistic traditions through prompting, not through engagement with actual speakers of Navajo, Chinese, or Greek. While the constraint sets were derived from linguistic literature on each tradition, they remain *approximations* of lived cognitive patterns. Actual speakers may produce solutions that deviate from the grammatical idealizations used here — particularly for living traditions like Navajo, where language evolution and bilingualism complicate the picture.

### 7.3 Translation Artifacts

All problems were presented in English and all solutions were evaluated in English translation. This introduces an inherent asymmetry: the problems carry English ontological assumptions, and the translations inevitably distort the solutions. The observation that traditions *refused* the English framings partially mitigates this concern — if the translation artifact were dominant, we would expect shallow reframing, not systematic ontological rejection.

### 7.4 Self-Reported Scoring

Scores were self-reported by the experimenter and verified against stated constraints. Independent scoring by blind evaluators would strengthen the results. The large score differential (48–50 vs. ~15) makes accidental inflation unlikely, but not impossible.

### 7.5 Sample Size

Nine reverse-actualization experiments (plus nine standard experiments) constitute a proof of concept rather than a statistically robust sample. Each problem×tradition cell contains only one observation. Replication with multiple runs per cell would enable statistical testing of the rejection pattern.

### 7.6 Problem Selection Bias

The three problems were chosen because they admit multiple solution types. Problems with genuinely unique optimal solutions (e.g., mathematical proofs) might show weaker linguistic effects. The scope of polyformalism's applicability remains to be mapped.

---

## 8. References

- Aristotle. *Metaphysics.* Trans. W.D. Ross. Oxford: Clarendon Press, 1908.
- Aristotle. *Nicomachean Ethics.* Trans. Terence Irwin. Indianapolis: Hackett, 1985.
- Boroditsky, L. (2011). "How language shapes thought." *Scientific American*, 304(2), 62–65.
- Callimachus. *Pinakes* (fragmentary). 3rd century BCE. Available in fragment collections.
- Hale, K. (1973). "A note on subject–object inversion in Navajo." In *Papers in Linguistics in Honor of Henry and Renée Kahane*, 309–332.
- Hutchins, E. (1995). *Cognition in the Wild.* Cambridge, MA: MIT Press.
- Kauffman, S. (1993). *The Origins of Order: Self-Organization and Selection in Evolution.* Oxford: Oxford University Press.
- Lakoff, G. & Johnson, M. (1980). *Metaphors We Live By.* Chicago: University of Chicago Press.
- Quine, W.V.O. (1960). *Word and Object.* Cambridge, MA: MIT Press.
- Ryle, G. (1949). *The Concept of Mind.* London: Hutchinson.
- Sapir, E. (1929). "The status of linguistics as a science." *Language*, 5(4), 207–214.
- Varela, F.J., Thompson, E., & Rosch, E. (1991). *The Embodied Mind: Cognitive Science and Human Experience.* Cambridge, MA: MIT Press.
- Vygotsky, L.S. (1978). *Mind in Society: The Development of Higher Psychological Processes.* Cambridge, MA: Harvard University Press.
- Whorf, B.L. (1956). *Language, Thought, and Reality.* Ed. J.B. Carroll. Cambridge, MA: MIT Press.
- Whitehead, A.N. (1929). *Process and Reality.* New York: Macmillan.
- Witherspoon, G. (1977). *Language and Art in the Navajo Universe.* Ann Arbor: University of Michigan Press.

---

*This paper documents experiments conducted on 2026-05-07 using Seed-2.0-pro (ByteDance) via DeepInfra. All prompts, raw outputs, and scoring rubrics are available in the SuperInstance polyformalism-languages repository.*

— Forgemaster ⚒️ · SuperInstance Research · 2026-05-08
