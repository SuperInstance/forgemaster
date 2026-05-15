# Study 32: First-Token Commitment — The Rerouting Is Immediate

**Date**: 2026-05-15 07:25 AKDT

## Qwen3-235B First Tokens (expected: 49)

| Framing | First Token | Track | Full Result |
|---------|:-----------:|:-----:|:-----------:|
| bare (no instruction) | **"W"** (We...) | DISCOURSE | Derivation |
| instruction ("reply ONLY integer") | **"4"** | COMPUTE | 49 ✓ |
| eisenstein | **"W"** (We...) | DISCOURSE | 79 ✗ |
| theorem | **"3"** | COMPUTE | 3 ✗ (wrong) |
| penrose | **"4"** | COMPUTE | 59 ✗ (wrong) |
| gauss | **"2"** | COMPUTE | Re-derives |

## Seed-2.0 First Tokens

| Framing | First Token | Track | Full Result |
|---------|:-----------:|:-----:|:-----------:|
| bare | "G" (Got...) | REASONING | 49 ✓ |
| instruction | "L" (Let...) | REASONING | 49 ✓ |
| eisenstein | "G" (Got...) | REASONING | 49 ✓ |
| penrose | "G" (Got...) | REASONING | 49 ✓ |
| gauss | "G" (Got...) | REASONING | 49 ✓ |

## R50 (BEDROCK): Rerouting Happens at Token 1

The model's fate is sealed by the FIRST TOKEN it generates:
- Qwen3-235B commits to discourse ("We...") or computation ("4...") on token 1
- With "Eisenstein" framing: 100% discourse track
- With "instruction" framing: 100% computation track
- The rerouting is NOT gradual — it's a binary switch at the first token

## R51 (SOLID): Stage 4 Models Use a Different Pathway

Seed-2.0 always starts with reasoning preamble ("Let's think...", "Got it...") regardless of framing, then ALWAYS arrives at the correct answer. It doesn't have the discourse/compute binary — it has a unified reasoning pathway that reliably reaches computation.

## Mechanism

```
Stage 3 model:
  Input → Embedding → [Eisenstein activates] → DISCOURSE pathway → first token "We/The"
  Input → Embedding → [clean arithmetic] → COMPUTE pathway → first token "4"

Stage 4 model:
  Input → Embedding → [unified] → REASONING pathway → first token "Let/Got" → correct answer
```

The Vocabulary Wall is a pathway selection failure at the embedding/attention level, manifesting at token 1.
