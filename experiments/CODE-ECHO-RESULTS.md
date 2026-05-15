# Study 11: Code Generation Echo Analysis

**Date:** 2026-05-15
**Models:** qwen3:4b, phi4-mini, gemma3:1b (all via ollama, localhost:11434)
**Trials:** 3 per condition per task
**Total runs:** 90 (3 models × 5 tasks × 2 conditions × 3 trials)

## Hypothesis

Does the echo/stage model hold for code generation tasks? Specifically:
- **ECHO EFFECT:** Scaffolded prompts (with code structure) should produce better results than bare baseline prompts
- **STAGE DEPENDENCE:** Smaller/weaker models should show stronger scaffold benefits

## Tasks

1. Reverse a linked list
2. Recursive factorial
3. Binary search
4. String palindrome check
5. Fizzbuzz

## Conditions

- **BASELINE:** "Write a function in Python that [task]. Reply ONLY with code, no explanation."
- **SCAFFOLDED:** "Complete this code:\n```python\ndef [name]([params]):\n    # [step 1]\n    # [step 2]\n```\nReply ONLY with the completed code."

## Results

### By Model

| Model | Condition | CORRECT | EMPTY | Total |
|-------|-----------|---------|-------|-------|
| **qwen3:4b** | baseline | 7 (47%) | 8 (53%) | 15 |
| **qwen3:4b** | scaffold | 8 (53%) | 7 (47%) | 15 |
| **qwen3:4b** | **TOTAL** | **15 (50%)** | **15 (50%)** | **30** |
| **phi4-mini** | baseline | 15 (100%) | 0 | 15 |
| **phi4-mini** | scaffold | 15 (100%) | 0 | 15 |
| **phi4-mini** | **TOTAL** | **30 (100%)** | **0** | **30** |
| **gemma3:1b** | baseline | 15 (100%) | 0 | 15 |
| **gemma3:1b** | scaffold | 15 (100%) | 0 | 15 |
| **gemma3:1b** | **TOTAL** | **30 (100%)** | **0** | **30** |

### Key Finding: No Echo Effect for Code

**The echo/stage model does NOT hold for code generation tasks.**

1. **phi4-mini and gemma3:1b:** Both achieve 100% correct across ALL conditions. Baseline = Scaffolded. The scaffold adds zero value — these models are already at ceiling performance for basic code tasks.

2. **gemma3:1b (1B params!)** achieves 100% on all 5 tasks, including linked list reversal and binary search. This is remarkable for a 1B model and suggests code generation is fundamentally different from the reasoning tasks where echo effects were observed.

3. **qwen3:4b** has a unique failure mode: 50% empty responses. This is NOT a code generation failure — it's a **thinking mode artifact**. The model's internal reasoning tokens consume the output budget, leaving nothing. Among responses that DID produce output, 100% were correct (15/15).

### Scaffold Effect on qwen3:4b Empty Rate

| Condition | Empty Responses |
|-----------|----------------|
| Baseline | 8/15 (53%) |
| Scaffold | 7/15 (47%) |

Marginal improvement (1 fewer empty response), not statistically significant at 15 trials. The scaffold did NOT meaningfully rescue the empty-response problem.

## Why Code is Different from Reasoning

The echo/stage model was developed for reasoning tasks where models benefit from structural scaffolding. Code is different:

1. **Well-defined syntax** — Python has strict, unambiguous structure. Models trained on code have clear patterns to follow.
2. **High training signal** — Code is overrepresented in training data (GitHub, StackOverflow). Even 1B models see millions of function implementations.
3. **Compositional** — Code tasks decompose into known patterns (loop, compare, return). No deep reasoning required for these canonical problems.
4. **Deterministic correctness** — Unlike "explain X" or "analyze Y," code either works or it doesn't. No ambiguity in evaluation.

## The qwen3:4b Thinking Mode Problem

The 50% empty rate for qwen3:4b is a significant practical concern:

- **Root cause:** qwen3:4b outputs `<think reasoning>` tokens that aren't visible in the API response, but they consume the `num_predict` budget (set to 512 tokens).
- **When thinking is long, the actual code response gets truncated to zero.**
- **This is a configuration issue, not a capability issue.** Every non-empty qwen3:4b response was perfectly correct.

**Fix:** For qwen3:4b code generation, increase `num_predict` significantly (2048+) or use the `/no_think` prompt suffix to disable thinking mode.

## Classification Breakdown

| Classification | Count | % |
|---------------|-------|---|
| CORRECT | 75 | 83% |
| EMPTY_RESPONSE | 15 | 17% |
| SYNTAX_ERROR | 0 | 0% |
| SYNTAX_OK_LOGIC_WRONG | 0 | 0% |
| ECHO_PROMPT | 0 | 0% |

**Zero ECHO_PROMPT classifications across all 90 runs.** No model copied the scaffold without adding logic. This confirms scaffolding doesn't create echo traps for code tasks.

## Conclusions

1. **No echo effect for basic code generation.** The scaffold/baseline distinction is irrelevant for simple coding tasks on models that can already solve them.

2. **1B models are sufficient for canonical code problems.** gemma3:1b (1B) matches phi4-mini (~3B) on all 5 tasks. For standard algorithms, model scale doesn't matter below ~4B.

3. **The bottleneck is output delivery, not capability.** qwen3:4b's failure mode is thinking mode eating the output budget, not inability to generate correct code.

4. **Code generation is qualitatively different from reasoning.** The echo/stage model applies to tasks where structural priming helps organize thought. For code, the structure is already implicit in the language syntax.

5. **Practical implication:** For code tasks, use the simplest prompt format. Complex scaffolding adds latency without improving results. Reserve scaffolding for tasks where reasoning depth matters, not syntax.

## Files

- `code-echo-results.json` — Full results (90 entries with responses and classifications)
- `code_echo_study.py` — Experiment runner script
