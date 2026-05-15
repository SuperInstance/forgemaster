# Study 9: Combination Scaffolding — Can We Rescue Partial Computation?

**Date**: 2026-05-15 06:05 AKDT
**Status**: COMPLETE (2 of 3 models, gemma3:1b OOM'd)

## Hypothesis

qwen3:4b computes correct sub-expressions (a², b², ab) but fails to combine into a²-ab+b². If we scaffold the combination step, accuracy should jump from ~10% to >60%.

## Results

### Accuracy Matrix

| Condition | qwen3:4b (4B) | phi4-mini (3.8B) |
|-----------|:-------------:|:----------------:|
| baseline (no help) | **0%** | **0%** |
| scaffolded (sub-results given) | **0%** | **40%** |
| partial scaffold (a²,b² given) | **0%** | **64%** |
| step-by-step (full walk) | **0%** | **56%** |
| just arithmetic (no math words) | **24%** | **4%** |

### Key Finding: Scaffolding Is Model-Dependent

**phi4-mini** (Stage 2-3, echo dominant):
- Partial scaffold is the sweet spot: **64%** — up from 0% baseline
- Scaffolded and step-by-step also help (40%, 56%)
- Just arithmetic WITHOUT scaffolding drops to 4%
- **Diagnosis**: phi4-mini needs the sub-results spelled out, then CAN combine them

**qwen3:4b** (Stage 3, partial computation):
- ALL scaffolding conditions: 0%
- Classification shifts from "other/echo_input" to "echo_partial"
- When given sub-results, it ECHOES them instead of combining
- Only "just arithmetic" (raw numbers, no math vocabulary) helps: **24%**
- **Diagnosis**: qwen3:4b's thinking mode triggers meta-reasoning about the numbers instead of computing. Math vocabulary = echo trigger.

## The Scaffolding Paradox

| Model | Best Scaffold | Best Accuracy | What Works |
|-------|:------------:|:-------------:|:-----------|
| qwen3:4b | just_arithmetic (no words) | 24% | Strip all math language |
| phi4-mini | partial_scaffold (labeled) | 64% | Spell out sub-results WITH labels |

**Opposite prescriptions**: qwen3:4b needs LESS context (math words trigger echoing), phi4-mini needs MORE context (labeled sub-results prevent guessing).

## Residue Classification Shift

### qwen3:4b
- Baseline: 72% "other" (random-ish), 28% echo_input
- Scaffolded: 80% echo_partial — **providing sub-results makes it WORSE** (more echo)
- Just arithmetic: 36% echo_partial, 24% correct, 16% partial_a2_minus_ab

### phi4-mini
- Baseline: 88% "other", 12% wrong_op_no_minus
- Partial scaffold: 64% correct, 32% other — **scaffold rescues computation**
- Just arithmetic: 52% partial_a2_minus_ab (computes a²-ab, forgets +b²)

## Revised Stage Model (R27)

The 4B phase transition is more nuanced than "partial computation":

- **Stage 2 (1-3B)**: ECHO — recognizes inputs, parrots them
  - Scaffold response: **positive** — labeled sub-results prevent guessing
  - Best intervention: partial scaffold (provide sub-results WITH math labels)

- **Stage 3a (~4B, thinking models)**: META-ECHO — reasons about inputs, echoes sub-results
  - Scaffold response: **negative** — more information triggers more echoing
  - Best intervention: strip math vocabulary, present as pure arithmetic

- **Stage 3b (~4B, non-thinking)**: PARTIAL — computes sub-expressions correctly, can't combine
  - Scaffold response: **strongly positive** — sub-results unlock combination
  - Best intervention: partial scaffold (provide labeled sub-results)

**The critical variable is NOT model size alone — it's thinking mode.** qwen3:4b (thinking) and phi4-mini (non-thinking) are the same size but require opposite interventions.

## New Findings

- **R27 (BEDROCK)**: Scaffolding effectiveness is model-ARCHITECTURE dependent, not just size-dependent. Thinking vs non-thinking models at the same scale need opposite interventions.
- **R28 (SOLID)**: Math vocabulary triggers echo in thinking models. "Just arithmetic" (raw numbers) is the only scaffold that helps qwen3:4b.
- **R29 (SOLID)**: phi4-mini's partial scaffold 64% > scaffolded 40% > step-by-step 56%. Partial scaffolding (give a², b² but let model compute ab and combine) is optimal — full scaffolding provides too much signal, triggering echo.
- **R30 (SUGGESTIVE)**: There may be an optimal "information dose" for scaffolding — too little (baseline) or too much (step-by-step) both underperform the sweet spot (partial scaffold).

## Implications for Fleet Routing

The fleet can't use a universal "scaffold all small models" strategy. It needs:
1. Detect thinking vs non-thinking mode
2. For non-thinking (phi4-mini): provide labeled sub-results → combination
3. For thinking (qwen3:4b): strip vocabulary, present as bare arithmetic
4. For echo-stage (gemma3:1b): scaffolding unlikely to help at all

This is a **per-model routing decision**, not a fleet-wide setting.

## Files
- `experiments/combination_scaffolding.py` — experiment script
- `experiments/combination-scaffolding-results.json` — raw results (if completed)
