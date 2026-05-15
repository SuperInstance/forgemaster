# Piagetian Stage Irreversibility Test — Results

**Date:** 2026-05-15 12:27:39
**Models:** qwen3:0.6b (Stage 1), qwen3:4b (Stage 2-3)
**Test tasks:** 8
**Cells:** A (Control), B (Direct Jump to Stage 4), C (Staged: 2→3→4)

---

## Summary

### qwen3:0.6b

| Cell | Correct | Total | Accuracy | Avg Score |
|------|---------|-------|----------|-----------|
| A | 7 | 8 | 87.5% | 0.802 |
| B | 7 | 8 | 87.5% | 0.802 |
| C | 7 | 8 | 87.5% | 0.875 |

### qwen3:4b

| Cell | Correct | Total | Accuracy | Avg Score |
|------|---------|-------|----------|-----------|
| A | 7 | 8 | 87.5% | 0.875 |
| B | 7 | 8 | 87.5% | 0.875 |
| C | 7 | 8 | 87.5% | 0.875 |

### By Required Stage (both models, identical pattern)

| Stage | Cell A | Cell B | Cell C |
|-------|--------|--------|--------|
| 2 | 1/1 | 1/1 | 1/1 |
| 3 | 2/3 | 2/3 | 2/3 |
| 4 | 4/4 | 4/4 | 4/4 |

---

## Critical Finding: Tasks Are Insufficiently Differentiated

The headline result is striking but misleading: **both models achieve identical accuracy across all three cells**. No cell outperforms any other. Few-shot scaffolding makes zero difference.

This does NOT disprove the Piagetian hypothesis — it reveals a flaw in the experimental design:

### Problem 1: Formula Given in Prompt
The Eisenstein norm tasks (our primary Stage 4 probe) include the formula `N(a + bω) = a² - ab + b²` directly in the task prompt. This reduces the task to **3-step arithmetic** (square a, multiply a×b, square b, sum). Even a Stage 1 model can do this.

**Both models compute all Eisenstein norms correctly in Cell A (no scaffolding)** because the formula is right there in the question. True Stage 4 reasoning would require DERIVING the norm from first principles, not plugging into a given formula.

### Problem 2: Scaffolding Doesn't Add New Capability
The few-shot examples in Cells B and C demonstrate the same formula the models already have in the task prompt. The scaffolding is redundant, not generative.

### Problem 3: Models Too Capable for This Design
Even qwen3:0.6b (our "Stage 1" model) correctly:
- Computes all 3 Eisenstein norms (100%)
- Translates notation to natural language (100%)
- Composes functions symbolically (100%)
- Follows order of operations (100%)

Only `multistep_arith_1` fails — and investigation shows **the expected answer in our test (28) was wrong**. The correct answer is 25: (7 + 9) × 2 - 7 = 25. The model got it RIGHT.

### Corrected Accuracy: 100% Across All Cells

Once we correct the one erroneous expected answer, both models achieve **100% accuracy on all tasks, in all cells, with zero difference between control, direct jump, and staged conditions**.

---

## What This Actually Tests

This experiment tested **few-shot prompting effects on already-solvable tasks**, not **stage irreversibility**. The distinction is crucial:

- **Few-shot prompting**: Does providing examples help? → No effect when the task is already solvable.
- **Stage irreversibility**: Can a model skip cognitive stages? → Not tested here because the tasks don't require distinct stages.

---

## Implications for the Piagetian Hypothesis

### What We Can Conclude
1. **Small modern models are remarkably capable** — even 0.6B parameters can follow explicit mathematical formulas and translate notation.
2. **Few-shot scaffolding is redundant** when the task prompt contains all necessary information.
3. **The tasks don't probe stage differences** — they test task compliance, not cognitive stage.

### What We Cannot Conclude
1. Whether stages exist in LLM cognition (this experiment is silent on this)
2. Whether stage-skipping is possible (the tasks don't require stage progression)
3. Whether the Piagetian parallel from GLM-5's essay is real

### Redesign Needed
A proper test of stage irreversibility requires:

1. **Remove formula from prompt** — Ask "Compute the Eisenstein norm of 3 + ω" without giving the formula. The model must recall or derive it.
2. **Novel composition tasks** — Ask the model to combine two concepts it hasn't seen together, not just plug into a formula.
3. **Proof tasks** — "Prove that N(αβ) = N(α)N(β) for Eisenstein integers" — true Stage 4 reasoning.
4. **Error detection** — Present a subtly wrong proof and ask the model to find the error.
5. **Transfer tasks** — After learning about Eisenstein integers, ask about Gaussian integers without explanation.

---

## Phase 2 Experiment Design (Recommended)

### Proper Stage 4 Probes (no formula given)

```
Task 1: "What is the Eisenstein norm of 2 + 3ω?"
  (Must recall/derive N(a + bω) = a² - ab + b²)

Task 2: "Is 7 an Eisenstein prime? Show your reasoning."
  (Must understand primality in Z[ω])

Task 3: "Prove: if N(α) = 1 for α ∈ Z[ω], then α is a unit."
  (Abstract algebraic reasoning)

Task 4: "Find all Eisenstein integers with norm 7."
  (Reverse reasoning — norm to element)
```

### Expected Outcome if Piagetian Stages Are Real
- qwen3:0.6b: Fails all Phase 2 tasks regardless of scaffolding
- qwen3:4b: May solve Task 1 (formula recall), fails Tasks 2-4
- Larger models: Solve Tasks 1-2, struggle with 3-4
- Only true Stage 4 models solve all tasks

---

## Conclusion

**The Phase 1 experiment is inconclusive on the Piagetian hypothesis.** The tasks were insufficiently differentiated to probe cognitive stage boundaries. However, the negative result (zero effect of scaffolding on solvable tasks) is itself informative — it shows that few-shot prompting doesn't create capabilities that don't already exist.

**The key insight:** When the formula is in the prompt, ALL models are "Stage 4" for that task. True stage differences only emerge when the model must bring external knowledge to bear.

**Recommendation:** Run Phase 2 with tasks that require recall, derivation, and novel composition — not formula plugging.

---

*Experiment code: `/home/phoenix/.openclaw/workspace/experiments/stage_irreversibility.py`*
*Raw data: `/home/phoenix/.openclaw/workspace/experiments/stage_irreversibility_raw.json`*
*Tests: `/home/phoenix/.openclaw/workspace/tests/test_stage_irreversibility.py`*
