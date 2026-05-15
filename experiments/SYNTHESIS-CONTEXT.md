# Experimental Context for High-Level Synthesis

## All Findings (R1-R32 + F1-F6 + Round 1-6 new)

### Bedrock Findings (Tier 1, replicated)
- R1: 8B beats 70B on math (training_coverage > parameter_count)
- R2: MoE models perform at active parameter level
- R3: Extraction method is first-class variable (0% vs 100% depending on prompt)
- R5: Temperature=0.0 is perfect but fragile for specific formulas
- R6: Coefficient familiarity > dependency width
- R20: Training coverage dominates architecture

### New Findings from This Session
- F1: Seed-mini has NO depth cliff through depth 10 (model-specific, not universal)
- F2: Qwen3.5 family has an INVERTED scale curve: 0.8B=47% > 2B=47% > 4B=0% > 9B=0% > 27B=0%
- F3: Step-3.5-Flash needs max_tokens=100+ (token budget = first-class variable)
- F4: Cache-aware pricing: $0.05/1K queries
- F5: Seed-mini temperature-invariant (T=0.0-2.0 all correct)
- F6: Seed-mini magnitude-invariant (no cliff through magnitude 10,000)
- F7: Addition depth cliff (llama-8b): 100%→80%→60%→20%→0% at depths 1-6
- F8: Multiplication 60pp worse than addition at same depth
- F9: Nesting demand separate from depth (0% across all models)
- F10: Temperature has zero effect on llama-8b broad accuracy
- F11: Seed-mini 91% on hard probes, only fails on unfamiliar coefficients
- F12: llama-scout (17B MoE) 0% on arithmetic, gpt-oss-20b 0-2%

### Qwen3.5 Scale Paradox (CRITICAL)
The entire Qwen3.5 family above 2B is arithmetic-blind:
- 0.8B: 47% (answers in reasoning_content, direct computation)
- 2B: 47% (same pattern)
- 4B: 0% (thinking process chains, gives wrong numbers)
- 9B: 0% (thinking process chains, gives wrong numbers)
- 27B: 0% (thinking process chains, gives wrong numbers)

The 4B+ models all emit "Thinking Process: ..." and then give wrong answers.
The 0.8B model just computes and gives the answer.
This is the strongest evidence yet that thinking hurts small/mid models.

### Spreader-Tool Architecture Implications
Logging camp cutter/buncher/delimber control system:
- Primary reasoner: Seed-2.0-mini (91% on hard probes, $0.05/1K queries)
- Fast safety layer: MiMo-V2.5 (366ms, cached queries for repeated checks)
- NOT recommended: Step-Flash (needs careful token budgeting), Qwen3.5 family (unreliable)

### Capability Formula (provisional)
capability = training_coverage × coefficient_familiarity × f(depth, model) × g(magnitude) × h(extraction)

Where:
- training_coverage: model-specific, NOT parameter-count-dependent
- coefficient_familiarity: a²-ab+b²=25% but a²+2ab+b²=100%
- f(depth, model): cliff at depth 5-6 for llama-8b, no cliff for Seed-mini
- g(magnitude): cliff at magnitude>100 for llama-8b, no cliff for Seed-mini
- h(extraction): system prompt + max_tokens + reasoning_content handling

### The Qwen Paradox Mechanism
Hypothesis: Qwen3.5-4B+ models have a "thinking mode" that was trained to output chain-of-thought.
This chain-of-thought:
1. Burns through the token budget before reaching the answer
2. Introduces arithmetic errors during the chain (echo, partial computation)
3. The final "answer" is often wrong because the chain accumulated errors

The 0.8B model has NO thinking mode — it just computes directly.
This is a genuine architectural difference, not just scale.

### Cache-Aware Architecture
DeepInfra cached-input rate: $0.02/1M tokens (vs $0.15/1M uncached for Seed-mini)
Strategy: Use FIXED system prompt across all queries → gets cached after first call
Result: 605 queries for $0.0325 ($0.05/1K)
This makes Seed-mini one of the cheapest viable reasoning models.

### Key Open Questions
1. WHY does the Qwen3.5 scale inversion happen? Is it thinking-mode or something else?
2. What makes Seed-mini so good? Training data? Architecture? Both?
3. Can we find a model that matches Seed-mini at faster speed?
4. What is the minimal viable model for safety-critical spreader-tool operations?
5. Does the capability formula predict accuracy on completely novel domains?
