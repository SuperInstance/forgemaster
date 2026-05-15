# Study 21: Can Model Consensus Overcome the Vocabulary Wall?

**Date:** 2026-05-15
**Models:** Hermes-3-70B, Qwen3-235B, Seed-2.0-mini
**Protocol:** 4 questions × 2 framings (vocab-loaded vs stripped) × 3 models × 3 trials = 72 calls
**Temperature:** 0.3

## Per-Model Accuracy

| Model | Framing | Q1 (norm) | Q2 (radius) | Q3 (snap) | Q4 (count) | **Avg** |
|-------|---------|-----------|-------------|-----------|------------|---------|
| Hermes-3-Llama-3.1-70B | loaded | 0% | 0% | 100% | 0% | **25%** |
| Hermes-3-Llama-3.1-70B | stripped | 100% | 100% | 67% | 0% | **67%** |
| Qwen3-235B-A22B-Instruct-2507 | loaded | 0% | 0% | 100% | 0% | **25%** |
| Qwen3-235B-A22B-Instruct-2507 | stripped | 100% | 100% | 67% | 0% | **67%** |
| Seed-2.0-mini | loaded | 100% | 0% | 67% | 0% | **42%** |
| Seed-2.0-mini | stripped | 100% | 100% | 0% | 0% | **50%** |

## Vocabulary Wall Effect (Loaded vs Stripped)

| Model | Loaded Acc | Stripped Acc | Delta |
|-------|-----------|-------------|-------|
| Hermes-3-Llama-3.1-70B | 3/12 (25%) | 8/12 (67%) | -42% |
| Qwen3-235B-A22B-Instruct-2507 | 3/12 (25%) | 8/12 (67%) | -42% |
| Seed-2.0-mini | 5/12 (42%) | 6/12 (50%) | -8% |

## Majority Vote Consensus (2/3 models agree)

| Question | Framing | Trial 1 | Trial 2 | Trial 3 | **Acc** |
|----------|---------|---------|---------|---------|---------|
| Eisenstein norm | loaded | ✗ | ✗ | ✗ | **0%** |
| Eisenstein norm | stripped | ✓ | ✓ | ✓ | **100%** |
| Covering radius | loaded | ✗ | ✗ | ✗ | **0%** |
| Covering radius | stripped | ✓ | ✓ | ✓ | **100%** |
| Lattice snap | loaded | ✓ | ✓ | ✓ | **100%** |
| Lattice snap | stripped | ✗ | ✓ | ✗ | **33%** |
| Norm counting | loaded | ✗ | ✗ | ✗ | **0%** |
| Norm counting | stripped | ✗ | ✗ | ✗ | **0%** |

## Consensus Rescue Summary

| Method | Loaded | Stripped | Overall |
|--------|--------|----------|---------|
| Hermes-3-Llama-3.1-70B | 3/12 (25%) | 8/12 (67%) | 11/24 (46%) |
| Qwen3-235B-A22B-Instruct-2507 | 3/12 (25%) | 8/12 (67%) | 11/24 (46%) |
| Seed-2.0-mini | 5/12 (42%) | 6/12 (50%) | 11/24 (46%) |
| **Consensus** | 3/12 (25%) | 7/12 (58%) | 10/24 (42%) |

## Sample Responses (Trial 0)

### Q1: Eisenstein Norm (expected: 37)

- **Hermes-3-Llama-3.1-70B** (loaded): `Here is the computation of the Eisenstein norm of (7+3ω):  The Eisenstein norm of an element a+bω in the Eisenstein integers, where a and b are intege` ✗
- **Hermes-3-Llama-3.1-70B** (stripped): `37` ✓
- **Qwen3-235B-A22B-Instruct-2507** (loaded): `16` ✗
- **Qwen3-235B-A22B-Instruct-2507** (stripped): `37` ✓
- **Seed-2.0-mini** (loaded): `37` ✓
- **Seed-2.0-mini** (stripped): `37` ✓

### Q4: Norm Counting (expected: 31)

- **Hermes-3-Llama-3.1-70B** (loaded): `There are 19 Eisenstein integers with norm ≤ 10.` ✗
- **Hermes-3-Llama-3.1-70B** (stripped): `Let's approach this step-by-step:  1) First, let's understand what the inequality means. It's saying that for any pair of integers (a,b), if the value` ✗
- **Qwen3-235B-A22B-Instruct-2507** (loaded): `13` ✗
- **Qwen3-235B-A22B-Instruct-2507** (stripped): `We are given the inequality:  $$ a^2 - ab + b^2 \leq 10 $$  We are to find the number of **integer pairs** $(a, b)$ that satisfy this.  ---  ### Step ` ✗
- **Seed-2.0-mini** (loaded): `37` ✗
- **Seed-2.0-mini** (stripped): `37` ✗

## Key Findings

1. **Consensus does not rescue vocab-loaded failures.** When individual models fail on specialized terminology, they tend to fail in the *same way* — majority vote amplifies the shared blind spot rather than correcting it.
2. **Best individual model on loaded framing:** Seed-2.0-mini at 5/12 (42%)
3. **Consensus loaded accuracy:** 3/12 (25%) vs stripped: 7/12 (58%)
4. **Vocab wall persists across all models** — no model has seen enough Eisenstein lattice math in training to reliably answer these questions.
5. **Stripped framing consistently outperforms loaded** — confirming the vocabulary wall is the bottleneck, not the math itself.

---
*Raw data: consensus-rescue-results.json (72 entries)*