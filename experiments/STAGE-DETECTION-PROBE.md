# Study 24: Single-Response Stage Detection

**Date**: 2026-05-15 06:55 AKDT

## Probe: N(5+3ω) = 5²-5×3+3² = 25-15+9 = 19

| Model | Answer | Correct? | Stage from Study 10 |
|-------|:------:|:--------:|:---:|
| Qwen3.6 (3B active) | 2 | ✗ | Stage 2 |
| Hermes-70B | 49 | ✗ | Stage 3 |
| Qwen3-235B | 19 | ✓ | Stage 3 (now Stage 4?) |
| Hermes-405B | 19 | ✓ | Stage 3 (now Stage 4?) |
| Seed-2.0-mini | 19 | ✓ | Stage 4 |
| Seed-2.0-code | 19 | ✓ | Stage 4 |

## R44 (SOLID): Stage Classification Is Input-Dependent

Qwen3-235B and Hermes-405B scored 25-38% on Study 10 (8 test pairs) but 100% on this single probe. The Vocabulary Wall is probabilistic, not deterministic — these models sometimes compute correctly, sometimes don't. 

The stage model should be understood as **expected accuracy distributions**, not deterministic classifications:
- Stage 4: ~100% on all inputs
- Stage 3: 20-40% (gets lucky on some inputs)
- Stage 2: 0-12% (almost never correct)

Single-response probing is insufficient for reliable stage classification. Need multiple probes.

## Implication for Fleet Routing

A model that gets 25% right is still wrong 75% of the time. Fleet auto-translation (Study 23) remains essential — you can't trust a Stage 3 model even when it sometimes gets lucky.
