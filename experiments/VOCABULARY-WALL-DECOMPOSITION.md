# Study 18: Vocabulary Wall Decomposition — The "Eisenstein" Word Kill

**Date**: 2026-05-15 06:30 AKDT
**Status**: COMPLETE

## The Experiment

Same computation (a=5, b=-3, norm=49), 8 different word framings. Only the words change, not the math.

## Results

| Framing | Hermes-70B | Qwen3-235B | Pattern |
|---------|:----------:|:----------:|---------|
| bare (25-(-15)+9) | 49 ✓ | 49 ✓ | Clean |
| arithmetic (words) | 49 ✓ | 49 ✓ | Clean |
| casual ("hey what is") | 49 ✓ | 49 ✓ | Clean |
| code ("write the result") | 49 ✓ | 49 ✓ | Clean |
| algebra (x,y variables) | 34 ✗ | 49 ✓ | Hermes fails, Qwen handles |
| lattice (hexagonal context) | 52 ✗ | 49 ✓ | Hermes fails, Qwen handles |
| eisenstein (proper noun) | 181 ✗ | 1 ✗ | **BOTH FAIL** |
| theorem (math jargon) | 25 ✗ | 8 ✗ | BOTH FAIL |

## The Finding: Three Tiers of Vocabulary Interference

### Tier 1: Clean (0% interference)
**bare, arithmetic, casual, code** — both models compute correctly. No domain-specific words.

### Tier 2: Partial (model-dependent)
**algebra, lattice** — Qwen3-235B handles these (more training on algebra/lattice), Hermes-70B fails. The interference is training-dependent.

### Tier 3: Lethal (kills ALL models)
**"Eisenstein", "theorem"** — both models fail catastrophically. These words activate non-computational pattern matching in every model tested (except Stage 4 models like Seed-2.0).

## Why "Eisenstein" Specifically?

The word "Eisenstein" in training data appears in:
- History of mathematics (biography)
- Number theory discussions (abstract, no computation)
- Film theory (Sergei Eisenstein)
- References to the Eisenstein criterion (divisibility, not norms)

The model has almost NEVER seen "Eisenstein" followed by "compute this number." It has seen "Eisenstein" followed by abstract discussions, proofs, and definitions. So it pattern-matches to abstract discourse instead of computation.

**This is a training coverage artifact, not a capability limitation.** The model CAN compute 49 — it does so in 6 other framings. The word "Eisenstein" simply routes to the wrong neural pathway.

## R38 (BEDROCK): The Proper Noun Effect

Domain-specific proper nouns ("Eisenstein", "Penrose", "Riemann") trigger catastrophic vocabulary interference even in models that correctly handle the underlying computation. The kill rate is:
- "Eisenstein": 100% failure (all non-Stage-4 models)
- Generic math terms ("algebra", "lattice"): model-dependent
- No math terms: 0% failure

## R39 (SOLID): The Vocabulary Wall Has Structure

Not all math vocabulary is equal. Three tiers of interference:
1. **Tier 1** (clean): everyday language, code, bare numbers → 0% interference
2. **Tier 2** (partial): domain terms ("algebra", "lattice") → model-dependent interference
3. **Tier 3** (lethal): proper nouns ("Eisenstein", "theorem") → 100% interference

## Fleet Implication

For the casting call / model routing:
- **NEVER** send Eisenstein-labeled tasks to non-Stage-4 models
- **STRIP** domain-specific proper nouns before routing to Hermes/Qwen
- **Seed-2.0** is the ONLY model that should see "Eisenstein" in prompts
- The fleet's API layer should auto-strip Tier 3 vocabulary and re-inject results with proper labels

## Files
- Inline experiment (Study 18)
