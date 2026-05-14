# Interference Hypothesis: Cognitive Signal Processing in Language Models

**Date**: 2026-05-14  
**Status**: HYPOTHESIS — supported by 5 studies, needs larger-model validation

---

## The Hypothesis

Model cognition is a signal processing system. Input data either **constructively** or **destructively** interferes with the model's internal computation, depending on the model's **bandwidth** (parameter count).

### The Frequency Response Model

```
Interference
    ^
    |
CON |         ╱╲
    |       ╱    ╲          ← medium models: partial data HURTS
    |     ╱        ╲
ZERO|───╱────────────╲───── ← zero interference line
    | ╱                ╲
DES|╱                    ╲  ← small models: partial data HELPS
    └──────────────────────→ Model Size (params)
      0.6B  1B  3B  7B  70B
```

- **Small models** (<1B): Partial data = constructive interference. The data fills gaps in computation capacity. +40% accuracy.
- **Medium models** (1-7B): Partial data = destructive interference. The data clashes with the model's own partial computation. -20% accuracy.
- **Large models** (>7B, untested): Prediction: partial data returns to constructive (model can integrate partial data into its own reasoning). +10-20%.

### The Mechanism

1. **Small models** have low bandwidth. They can't compute a²-ab+b². Partial data (a²=16, b²=4) provides MISSING information → constructive.

2. **Medium models** have medium bandwidth. They CAN partially compute (get a²=16) but then the partial data says "a²=16" too. Two competing representations → destructive interference. The model is unsure whether to use its own computation or the provided data.

3. **Large models** have high bandwidth. They can fully compute AND integrate provided data. The partial data is redundant but not conflicting → neutral to constructive.

### Testable Predictions

1. **P1**: A 7B model should show LESS interference than phi4-mini (3.8B). P(correct with partial data) > P(correct without).
2. **P2**: A 70B model should show ZERO interference. It computes correctly regardless of data.
3. **P3**: The Death Zone (0% accuracy with partial data) only exists in the 1-7B range. Below 1B, partial data helps. Above 7B, it's neutral.
4. **P4**: Echo rate should decrease with model size. 0.6B: 0%, 1B: ~46%, 3B: ~49%, 7B: ~10%, 70B: ~0%.
5. **P5**: The cross-over point (where partial data switches from constructive to destructive) depends on TASK DIFFICULTY relative to model capacity, not model size alone.

---

## Evidence For

- **W1 Cross-Model Death Zone** (gemma3:1b +40%, phi4-mini -20% with same partial data)
- **Study 5 Echo Analysis** (echo rate = cognitive bandwidth proxy)
- **Study 3 Temporal Decomposition** (stochastic vs deterministic failure tiers)
- **DEEP Exp 2** (JIT chain summary = destructive for stream execution)
- **Campaign D** (FLUX encoding = compressed signal that some models can decode, others can't)

## Evidence Against

- Only tested on 4 models (0.6B to 3.8B), all on one task type
- Haven't tested 7B+ models
- Haven't tested non-math tasks
- The "interference" could be simpler explanations (memorization, pattern matching)

---

## Architectural Implications for Fleet

### Phase Matching

In signal processing, maximum power transfer requires impedance matching between source and load. In fleet cognition, maximum accuracy requires **phase matching** between DATA format and model capacity.

| DATA Format | Phase-Matched To | Mismatched To |
|------------|-----------------|---------------|
| Formula + inputs (minimal) | Medium models (they compute) | Small models (they can't) |
| Step-by-step scaffolding | Small models (they need it) | Medium models (it interferes) |
| Full answer | All models (coherent signal) | Nobody (but wastes tokens) |

### The Fleet as a Frequency-Division Multiplexer

Different models operate at different "frequencies" (computation bandwidths). The fleet coordinator should:

1. **Measure model bandwidth** — run calibration tasks, measure echo rate and accuracy
2. **Phase-match DATA to bandwidth** — scaffold for small, minimal for medium, trust large
3. **Detect phase mismatch** — if answers are echoes, the DATA is wrong phase
4. **Use cognitive residue for diagnosis** — wrong answers reveal the interference pattern

### The Residue Decoder

```
Model output → Residue classifier → Fleet action
  ├─ Echo        → "Model can't compute" → Route to larger model
  ├─ Partial     → "Model started, needs help" → Add one more step
  ├─ Wrong Op    → "Model misunderstood" → Clarify instructions  
  ├─ Stochastic  → "Model can compute, isn't reliable" → Consensus vote
  └─ Deterministic → "Model always fails this" → Blacklist task type
```

---

## Experimental Design to Validate/Kill

### Critical Experiment: 7B Model

Run the same Death Zone experiment on a 7B model:
- N(5,-3)=49 with no data, minimal data, partial intermediates, full answer
- If partial intermediates IMPROVE accuracy: hypothesis confirmed (interference is bandwidth-dependent)
- If partial intermediates HURT: hypothesis needs revision (interference isn't just about bandwidth)
- If no effect: interference is only in small models, not architecturally relevant

### Secondary: Non-Math Tasks

Run echo analysis on:
- Text summarization (can models echo sentences?)
- Code generation (can models echo requirements?)
- Creative writing (is echo even a thing here?)

If echo is math-specific, the interference hypothesis only applies to computation tasks. If echo appears in all domains, it's a fundamental property of model cognition.

---

*"The fleet isn't just a collection of models. It's a signal processing pipeline. Every model is a filter with its own bandwidth and frequency response. The coordinator's job is impedance matching."*
