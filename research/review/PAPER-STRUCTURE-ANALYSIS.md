# Landmark White Paper Structure Analysis

Study of 5 foundational systems/ML papers (2004–2023) to extract structural patterns for our Signal Chain paper.

---

## Paper 1: MapReduce (Dean & Ghemawat, 2004)

**Opening sentence:** "MapReduce is a programming model and an associated implementation for processing and generating large data sets."

**Structure:**
1. Introduction
2. Programming Model
   - 2.1 Example (word count — appears within 2 paragraphs of section start)
3. Implementation
   - 3.1 Execution Overview
   - 3.2 Master Data Structures
   - 3.3 Fault Tolerance
   - 3.4 Locality
   - 3.5 Task Granularity
   - 3.6 Backup Tasks
4. Refinements
   - 4.1 Partitioning Function
   - 4.2 Ordering Guarantees
   - 4.3 Combiner Function
   - 4.4 Input and Output Types
   - 4.5 Side-effects
   - 4.6 Skipping Bad Records
   - 4.7 Local Execution
   - 4.8 Status Information
   - 4.9 Counters
5. Performance
   - 5.1 Cluster Configuration
   - 5.2 Grep
   - 5.3 Sort
   - 5.4 Effect of Backup Tasks
   - 5.5 Machine Failures
6. Experience / Usage within Google
7. Related Work
8. Conclusions

**Paragraphs before first concrete example:** ~2 (the word count pseudocode appears almost immediately in Section 2)

**Concrete examples:** ~8–10 (word count, distributed grep, URL access frequency, term-vector per host, inverted index, distributed sort, production indexing system, machine failures during sort)

**Tables/Figures:** ~6 figures (execution flow diagram, progress bar) + 2–3 tables (performance data). Relatively few — text-heavy.

**Length:** 11 pages (OSDI format)

**Tone:** Third person, formal but plain-spoken. Active voice dominates ("We describe...", "Users specify..."). Minimal jargon outside the programming model itself. Confident and direct.

**Limitations:** Handled inline in Section 4.5 (side-effects) and implicitly in the "Refinements" section. No dedicated "Limitations" section.

---

## Paper 2: Attention Is All You Need (Vaswani et al., 2017)

**Opening sentence:** "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder."

**Structure:**
1. Introduction
2. Background
3. Model Architecture
   - 3.1 Encoder and Decoder Stacks
   - 3.2 Attention
     - 3.2.1 Scaled Dot-Product Attention
     - 3.2.2 Multi-Head Attention
     - 3.2.3 Applications of Attention in our Model
   - 3.3 Position-wise Feed-Forward Networks
   - 3.4 Embeddings and Softmax
   - 3.5 Positional Encoding
4. Why Self-Attention
5. Training
   - 5.1 Training Data and Batching
   - 5.2 Hardware and Schedule
   - 5.3 Optimizer
   - 5.4 Regularization
6. Results
   - 6.1 Machine Translation
   - 6.2 Model Variations
   - 6.3 English Constituency Parsing
7. Conclusion
   - Acknowledgments
   - References
   - Appendix (5 sections: training details, varied attention heads, tensor2tensor, etc.)

**Paragraphs before first concrete example:** ~4 paragraphs of intro, then 1 section of background, then concrete architecture with Figure 1. ~6 paragraphs total before the first real concrete artifact.

**Concrete examples:** ~5–6 (BLEU scores on WMT tasks, parsing results, model variation ablations in Table 3, training time comparisons)

**Tables/Figures:** 5 figures + 4 tables. Heavy on visual architecture diagrams and ablation tables.

**Length:** 15 pages (including appendix). ~7,500 words body text.

**Tone:** First person plural ("We propose...", "we employ..."). Formal academic, but notably confident — direct claims without hedging. Active voice almost exclusively.

**Limitations:** Not addressed in a dedicated section. The paper acknowledges trade-offs inline (e.g., "reduced effective resolution due to averaging attention-weighted positions") and in the "Why Self-Attention" comparison table.

---

## Paper 3: Dynamo (DeCandia et al., 2007)

**Opening sentence:** "Reliability at massive scale is one of the biggest challenges we face at Amazon.com, one of the largest e-commerce operations in the world; even the slightest outage has significant financial consequences and impacts customer trust."

**Structure:**
1. Introduction
2. Background and Motivation
   - 2.1 System Assumptions and Requirements
   - 2.2 Service-Level Agreement (SLA)
   - 2.3 Design Considerations
3. System Design
   - 3.1 System Interface
   - 3.2 Partitioning Algorithm
   - 3.3 Replication
   - 3.4 Data Versioning
   - 3.5 Execution of get() and put() operations
   - 3.6 Handling Permanent Failures: Replica Synchronization
   - 3.7 Membership and Failure Detection
   - 3.8 Tuning Consistency
4. Implementation
5. Results and Experience
   - 5.1 Performance and Efficiency
   - 5.2 Scalability
   - 5.3 Durability and Availability
   - 5.4 Client-side Optimizations
6. Related Work
7. Conclusions

**Paragraphs before first concrete example:** ~3 (SLA example appears early in Section 2.2, concrete design trade-offs in 2.3)

**Concrete examples:** ~6–8 (SLA requirements, consistency window examples, vector clock examples, hinted handoff, merkle tree anti-entropy, production deployment metrics from Amazon's shopping cart service)

**Tables/Figures:** ~5 figures (architecture diagrams, latency distributions) + 2–3 tables (performance metrics, configuration parameters). Notably includes a table of design choices mapping requirements to techniques.

**Length:** 12 pages (SOSP format)

**Tone:** First person plural ("we face at Amazon.com", "we present"). Distinctive for being written by practitioners — the tone is more operational and concrete than typical academic papers. Active voice. Concrete about production constraints.

**Limitations:** Addressed in Section 2.3 ("Design Considerations") as explicit trade-offs. No dedicated "Limitations" section — limitations are framed as design choices and justified.

---

## Paper 4: Resilient Distributed Datasets / Spark (Zaharia et al., 2012)

**Opening sentence:** "Cluster computing frameworks like MapReduce have simplified the programming of large-scale data-parallel applications by letting users compose acyclic data flow operators."

**Structure:**
1. Introduction
2. Resilient Distributed Datasets (RDDs)
   - 2.1 RDD Abstraction
   - 2.2 Spark Programming Interface
   - 2.3 Representing RDDs
   - 2.4 Comparison with Shared Memory
3. Spark System
   - 3.1 Implementation
   - 3.2 Integration with Cluster Manager
   - 3.3 The Spark Interpreter
4. Evaluation
   - 4.1 Iterative Machine Learning Applications (K-means, Logistic Regression, etc.)
   - 4.2 PageRank
   - 4.3 Interactive Data Mining
   - 4.4 Fault Recovery
5. Related Work
6. Discussion (limitations and future)
7. Conclusion

**Paragraphs before first concrete example:** ~3 (first code example appears in Section 2.2, within about 2 pages)

**Concrete examples:** ~10+ (K-means, logistic regression, PageRank, SQL interactive queries, text search, fault recovery time measurements, comparison table with Hadoop, memory usage graphs)

**Tables/Figures:** ~7 figures (performance graphs, RDD lineage diagrams) + 3–4 tables (operation list, performance comparison). Heavy on performance graphs.

**Length:** 14 pages (NSDI format). ~8,000 words.

**Tone:** Third person / first person plural mixed. Formal academic. Active voice. Notably includes actual Scala code snippets in the text.

**Limitations:** Dedicated "Discussion" section (Section 6) that explicitly addresses limitations — acknowledges RDDs are unsuitable for fine-grained async updates, and discusses future directions.

---

## Paper 5: LLaMA (Touvron et al., 2023)

**Opening sentence:** "We introduce LLaMA, a collection of foundation language models ranging from 7B to 65B parameters."

**Structure:**
1. Introduction
2. Pre-training Data
   - 2.1 Dataset composition table
3. Architecture (parameter choices compared to PaLM, GPT-3)
   - 3.1 Transformer Architecture modifications
   - 3.2 Training details (optimizer, batch size, learning rate)
4. Training Results and Performance
   - 4.1 Comparison with other models (tables of benchmark results)
   - 4.2 Results on specific benchmarks (MMLU, GSM8K, etc.)
5. Instruction Finetuning (brief)
6. Bias, Toxicity, and Safety
7. Related Work
8. Conclusion

**Paragraphs before first concrete example:** ~2 (dataset composition table appears in Section 2, within 1 page)

**Concrete examples:** ~15+ (benchmark scores across 20+ benchmarks, per-model-size comparisons, training compute table, data mix table, toxicity measurements). Extremely numbers-dense.

**Tables/Figures:** ~8–10 tables (benchmark comparisons, architecture parameters, data mix) + 3–4 figures (training loss curves, scaling behavior). Table-heavy.

**Length:** 9 pages body + 20+ pages appendix. ~5,000 words body text (short for a major paper — the results ARE the paper).

**Tone:** First person plural ("We introduce..."). Direct, almost terse. Minimal narrative. The numbers speak. Active voice throughout. No grandiosity.

**Limitations:** Dedicated Section 6 (Bias, Toxicity, and Safety). Also acknowledges limitations inline (LLaMA does not match PaLM-540B on all benchmarks).

---

## Cross-Paper Pattern Analysis

### Structural Patterns

| Pattern | MapReduce | Attention | Dynamo | Spark RDD | LLaMA |
|---------|-----------|-----------|--------|-----------|-------|
| **Pages** | 11 | 15 | 12 | 14 | 9+20apx |
| **Body words** | ~7K | ~7.5K | ~8K | ~8K | ~5K |
| **Sections** | 8 | 7+apx | 7 | 7 | 8 |
| **Subsections** | 16 | 12 | 11 | 12 | ~8 |
| **Tables** | 2-3 | 4 | 2-3 | 3-4 | 8-10 |
| **Figures** | 6 | 5 | 5 | 7 | 3-4 |
| **Concrete examples** | 8-10 | 5-6 | 6-8 | 10+ | 15+ |
| **Para before 1st example** | 2 | 6 | 3 | 3 | 2 |
| **Dedicated limitations section** | No | No | No | Yes | Yes (safety) |
| **Opening sentence type** | Definition | Problem statement | Problem+scale | Context+problem | Contribution |

### Key Findings

1. **Length sweet spot:** 10–15 pages body, 5,000–8,000 words. LLaMA is the outlier at 5K body (but has a massive appendix).

2. **Examples are everything.** Every paper puts concrete examples within 2–6 paragraphs of the start. MapReduce and LLaMA are fastest (2 paragraphs). The average is ~3.

3. **Opening sentences fall into two camps:**
   - **Definition/Contribution:** "X is a Y that does Z." (MapReduce, LLaMA)
   - **Problem statement:** "The dominant/current approach has limitation Y." (Attention, Dynamo, Spark)
   
   Both work. Both are concrete. Neither uses metaphor.

4. **Tone:** First person plural is dominant (4/5 papers). Active voice universally. Formal but plain-spoken. No hedging on the contribution.

5. **Structure follows a consistent pattern:**
   - Introduction (problem + contribution summary)
   - Background / Related context
   - The Thing (detailed design/architecture)
   - Implementation details
   - Evaluation / Results
   - Related Work (usually late)
   - Conclusion
   
   MapReduce and Dynamo interleave implementation refinements into the design section. Attention puts "Why" as a separate section (unusual and effective).

6. **Tables vs Figures:** Systems papers (MapReduce, Dynamo, Spark) lean on execution diagrams and performance graphs. ML papers (Attention, LLaMA) lean on ablation tables and benchmark comparison tables.

7. **Limitations:** 3/5 papers handle limitations inline (MapReduce, Attention, Dynamo). 2/5 have dedicated sections (Spark, LLaMA). The trend in recent years is toward explicit limitation/safety sections.

8. **No paper uses metaphor in its opening.** Every one opens with either a concrete definition or a concrete problem statement.

9. **Every paper leads with numbers in the abstract.** BLEU scores, terabytes processed, parameter counts, SLA percentages. The abstract IS a results summary.

---

## Signal Chain Paper Template

Based on what works across these 5 landmark papers:

### Section Structure

```
Title: [Concrete, descriptive. No metaphors. "Signal Chain: [what it does]"]

Abstract (150-200 words)
  - Problem in 1 sentence
  - Contribution in 1-2 sentences  
  - Key result with numbers in 1-2 sentences
  - "We show..." generalization sentence

1. Introduction (1.5-2 pages)
  - Opening: concrete problem statement OR concrete definition
  - Paragraph 2-3: Why existing approaches fall short
  - Paragraph 3-4: Our contribution (what we built, what it does)
  - Paragraph 5: Key results with numbers
  - Paragraph 6: Paper roadmap ("The remainder of this paper...")

2. Background / Problem Statement (0.5-1 page)
  - Formalize the problem
  - Establish notation
  - First concrete example here

3. Design / The Thing (3-4 pages, the bulk)
  - 3.1 Core abstraction/mechanism
  - 3.2 Key algorithm/component
  - 3.3 Architecture details
  - 3.4 Implementation considerations
  [Numbered examples inline throughout, at least 5-6]

4. Why This Design / Motivation (0.5-1 page)
  - Comparison table with alternatives (like Attention's Table 1)
  - Justify specific design choices

5. Evaluation / Results (2-3 pages)
  - 5.1 Microbenchmarks
  - 5.2 End-to-end application results
  - 5.3 Comparison with alternatives
  - 5.4 Ablation / variant analysis (table of variations)
  - 5.5 Failure/scalability scenario

6. Related Work (0.5-1 page)
  - Position against closest alternatives
  - Brief, late (like all 5 papers)

7. Limitations and Future Work (0.5 page)
  - Explicit (modern trend)
  - Honest about what doesn't work yet

8. Conclusion (0.5 page)
  - Restate contribution + key number
  - 1-2 sentences on implications

References
Appendix (if needed for proofs, full tables, extra examples)
```

### Target Metrics

| Metric | Target | Rationale |
|--------|--------|-----------|
| **Body length** | 10-12 pages, 6,000-8,000 words | Sweet spot across all 5 papers |
| **Sections** | 7-8 | Matches all papers |
| **Subsections** | 10-14 | Matches all papers |
| **Concrete examples** | 8-12 | More than Attention, less than LLaMA |
| **Tables** | 4-6 | Comparison table, ablation table, results tables |
| **Figures** | 4-6 | Architecture diagram, performance graphs |
| **Paragraphs before 1st example** | ≤3 | Match MapReduce/LLaMA speed |
| **Appendix** | Optional, for detailed proofs/data | Follow LLaMA pattern |

### Tone Guidelines

1. **First person plural:** "We present...", "We show...", "Our system..."
2. **Active voice.** No "It was observed that..." → "We observe that..."
3. **Formal but plain-spoken.** No slang, no academic padding, no hedging.
4. **Confident claims.** "Signal Chain achieves X" not "Signal Chain appears to achieve approximately X"
5. **Numbers in every claim.** Not "significantly faster" → "3.2× faster"
6. **No metaphor.** Every paper in this study opens with concrete language. Follow suit.

### Opening Paragraph Template

```
[Opening sentence: Concrete problem statement with scale]
[Second sentence: Why current approaches fail at this]
[Third sentence: What we built — one-sentence definition]
[Fourth sentence: Key result with specific numbers]
```

Example for Signal Chain:
> "Distributed constraint systems accumulate drift — small errors that compound across propagation chains until the system violates its own invariants. Current approaches detect drift retroactively through global reconciliation, which is expensive and incomplete. We present Signal Chain, a [one-sentence definition of what it is]. Signal Chain reduces drift detection latency by [X]× while maintaining [Y]% constraint satisfaction across [Z]-node clusters."

### Key Anti-Patterns (from studying these papers)

1. **DON'T** open with motivation/background before stating what you built
2. **DON'T** have more than 3 paragraphs of text before a concrete example
3. **DON'T** bury results in prose — use tables
4. **DON'T** use passive voice for your own contributions
5. **DON'T** put related work early (it goes in section 6-7)
6. **DON'T** write an abstract without specific numbers
7. **DON'T** use metaphor where a number would do

---

*Analysis date: 2026-05-17*
*Source papers: MapReduce (2004), Attention (2017), Dynamo (2007), Spark RDD (2012), LLaMA (2023)*
