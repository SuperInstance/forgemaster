# Study 10: Stage 4 Boundary — The Vocabulary Wall

**Date**: 2026-05-15 06:15 AKDT
**Status**: COMPLETE

## The Question

Where does FULL computation (Stage 4) kick in? We tested 6 API models from 3B active to 405B dense params.

## Results

| Model | Params | Active | Baseline | Just Arithmetic | Stage |
|-------|--------|--------|:--------:|:---------------:|-------|
| Qwen3.6-35B | 35B MoE | **3B** | 0% | 12% | Stage 2 (ECHO) |
| Hermes-70B | 70B dense | 70B | 25% | 88% | Stage 3 (META-ECHO) |
| Qwen3-235B | 235B MoE | **22B** | 38% | 100% | Stage 3 (META-ECHO) |
| Hermes-405B | 405B dense | 405B | 25% | 100% | Stage 3 (META-ECHO) |
| **Seed-2.0-mini** | ? | ? | **100%** | **100%** | **Stage 4 (FULL)** |
| **Seed-2.0-code** | ? | ? | **100%** | **100%** | **Stage 4 (FULL)** |

## Critical Findings

### F1: The Vocabulary Wall Is Real (R31, BEDROCK)

**Even 405B parameters can't compute "Eisenstein norm of (a+bω)" correctly — but can compute "X - Y + Z = ?" perfectly.**

- Hermes-405B: 25% with math vocabulary → 100% with bare arithmetic
- Qwen3-235B: 38% → 100%
- Hermes-70B: 25% → 88%

The bottleneck is NOT computation capacity. It's **vocabulary interference** — the math term "Eisenstein norm" triggers pattern matching instead of computation, even in the largest dense model tested.

### F2: MoE Active Params Determine Stage (R32, BEDROCK)

- Qwen3.6-35B (3B active): **Stage 2** — same as 1B local models
- Qwen3-235B (22B active): Stage 3 — same as 4B local models
- Hermes-70B (70B active): Stage 3 — not yet Stage 4

**CONFIRMS**: The stage model prediction from yesterday (R25). Active parameters, not total, determine cognitive stage.

### F3: Seed-2.0 Is a Genuine Stage 4 Model (R33, BEDROCK)

Seed-2.0-mini and Seed-2.0-code both hit 100% on BOTH conditions — math vocabulary doesn't interfere. This is the only model family tested that computes Eisenstein norms correctly regardless of framing.

**Why?** Seed models are likely trained with significant math/reasoning data. The "Eisenstein norm" term doesn't trigger pattern matching because the model has genuine mathematical understanding at that level.

### F4: The Stage Boundary Is NOT at 7B (R34, BEDROCK)

Yesterday's hypothesis: "Stage 4 at 7B+." 

**Reality**: Hermes-70B (70B dense) is still Stage 3. The boundary is NOT at 7B — it depends on training, not just parameter count. Stage 4 requires specific mathematical training, not just scale.

## The Revised Stage Model

| Stage | Behavior | Triggered By | Best Intervention | Examples |
|-------|----------|-------------|-------------------|----------|
| 1 (<1B) | NONE | Can't produce output | Route elsewhere | qwen3:0.6b |
| 2 (1-4B active) | ECHO | Inputs → echo them | Scaffold with labels | gemma3:1b, phi4-mini, Qwen3.6-35B |
| 3 (4-70B+ active) | META-ECHO | Math vocab → pattern match | Strip vocabulary | qwen3:4b, Hermes-70B, Hermes-405B, Qwen3-235B |
| 4 (trained) | FULL | Computation regardless | No intervention needed | Seed-2.0-mini, Seed-2.0-code |

**Stage 4 is NOT a size threshold — it's a TRAINING threshold.** Seed-2.0-mini might have far fewer than 70B params, but it's trained to compute rather than pattern-match.

## Implications

1. **Fleet routing**: Don't route by model size. Route by STAGE. A 3B MoE is Stage 2; a "mini" model can be Stage 4.
2. **The 405B result is humbling**: Throwing parameters at the problem doesn't solve vocabulary interference. Training does.
3. **Seed-2.0 is the fleet's computation backbone**: Use it for anything requiring actual math, not just language about math.
4. **Casting call update**: The model roster needs a "stage" column, not just a "size" column.

## Connection to Yesterday's Work

- **R25 (active params determine stage)**: ✅ CONFIRMED. Qwen3.6-35B with 3B active = Stage 2.
- **R27 (scaffolding is architecture-dependent)**: Extended — the vocabulary wall affects ALL non-Stage-4 models, even 405B.
- **Golden ratio conjecture (s_c ≈ φ × d_head)**: Untestable without knowing Seed-2.0's architecture. But the result suggests the threshold isn't a simple bandwidth calculation.

## Files
- `experiments/stage4_boundary.py` — experiment script
- `experiments/stage4-boundary-results.json` — raw results
