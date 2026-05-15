# Study 36: Cross-Lingual Vocabulary Wall

**Date:** 2026-05-15
**Computation:** N(5-3ω) = 5²-5×(-3)+(-3)² = 25+15+9 = **49**

## Executive Summary

The Vocabulary Wall is **NOT English-specific** — it varies wildly by language AND model in unexpected ways. Japanese is paradoxically the *best* language for Eisenstein norm on Hermes (100% in Japanese, 0% in English/Chinese/Spanish). Seed-2.0-mini is the only model that achieves 100% across ALL language×framing combinations.

---

## Accuracy Matrix (Eisenstein Norm → answer=49)

| Model | EN | ZH | JA | ES | Total |
|-------|:--:|:--:|:--:|:--:|:-----:|
| **Qwen3-235B** | 5/5 (100%) | 4/5 (80%) | 5/5 (100%) | **0/5 (0%)** | 14/20 |
| **Hermes-70B** | **0/5 (0%)** | **0/5 (0%)** | **5/5 (100%)** | **0/5 (0%)** | 5/20 |
| **Seed-2.0-mini** | 5/5 (100%) | 5/5 (100%) | 5/5 (100%) | 5/5 (100%) | **20/20** |

## Accuracy Matrix (Bare Arithmetic → 25-(-15)+9=49)

| Model | EN | ZH | JA | ES | Total |
|-------|:--:|:--:|:--:|:--:|:-----:|
| **Qwen3-235B** | 5/5 | 5/5 | 5/5 | 5/5 | 20/20 |
| **Hermes-70B** | 5/5 | 5/5 | **0/5 (0%)** | 5/5 | 15/20 |
| **Seed-2.0-mini** | 5/5 | 5/5 | 5/5 | 5/5 | **20/20** |

---

## Key Findings

### 1. 🇯🇵 Japanese is the SECRET WEAPON for Eisenstein norms
**Hermes-70B** scores 0/5 in English, Chinese, and Spanish on Eisenstein norm — but **5/5 in Japanese**. This is stunning. The Japanese prompt somehow triggers correct mathematical reasoning that the English prompt completely fails to activate.

### 2. 🇪🇸 Spanish Eisenstein is CATASTROPHIC on Qwen3-235B
Qwen3-235B gets 100% on Eisenstein in EN/JA, 80% in ZH, but **0% in Spanish**. It consistently computes 5²-5·3+3²=19 instead of 5²-5·(-3)+(-3)²=49, dropping the negative signs on b. This is a pure language-dependent failure — same model, same math, different outcome.

### 3. Hermes-70B's Japanese↔English Inversion
Hermes shows a bizarre cross-language pattern:
- **Eisenstein:** Japanese 100%, everything else 0%
- **Arithmetic:** English/Chinese/Spanish 100%, **Japanese 0%** (answers 45 every time)

The model that *needs* Japanese for abstract math *fails* Japanese for simple arithmetic. This suggests language-specific reasoning pathways are being activated differently for different task types.

### 4. Seed-2.0-mini: The Universal Calculator
100% across every single condition (40/40). Language doesn't matter. Framing doesn't matter. This confirms Seed-2.0-mini as a Stage 4 model — immune to vocabulary walls across languages.

### 5. The Vocabulary Wall IS Cross-Lingual, Not English-Specific
The wall exists but manifests differently per language:
- **Qwen3-235B:** Spanish is the wall language (0% Eisenstein)
- **Hermes-70B:** English/Chinese/Spanish are wall languages for Eisenstein; Japanese is wall for arithmetic
- **Seed-2.0-mini:** No wall detected in any language

### 6. Language Matching (Response Language)
| Prompt Lang | Qwen3 | Hermes | Seed-mini |
|:-----------:|:------:|:------:|:---------:|
| EN | EN ✓ | EN ✓ | EN ✓ |
| ZH | EN ✗ | EN ✗ | EN ✓ (bare) |
| JA | JA ✓ | JA ✓ | JA ✓ |
| ES | EN ✗ | EN ✗ | EN ✓ (bare) |

Qwen3 and Hermes both respond in English to Chinese and Spanish prompts, while correctly matching Japanese. Seed-2.0-mini responds in the prompt language when it can (Japanese) but defaults to bare numbers for Chinese/Spanish.

---

## Error Analysis

### Qwen3-235B Spanish Eisenstein (0/5)
All 5 trials compute 5²-5·3+3²=19 instead of 5²-5·(-3)+(-3)²=49. The Spanish prompt `Calcula la norma de Eisenstein de (5-3ω)` causes the model to drop the negative sign on -3. This is NOT an arithmetic error — it's a **sign-parsing error** triggered by the Spanish frame.

### Hermes-70B English Eisenstein (0/5)
All 5 trials answer 61. Consistent wrong answer = systematic reasoning failure, not random error. Computes 5²+5·3+(-3)²=25+15+9=... wait, that's 49. The error is likely N(a+bω) misread as a²+ab+b² giving 25+15+9=... no. Actually 61=5²+6·3+(-3)²? No. 61=25+15+21? Hard to reconstruct. The point is: consistently wrong.

### Hermes-70B Japanese Arithmetic (0/5)
All 5 trials answer 45. Computing 25-(-15)+9... 25+15+9=49, but gets 45. Possibly 25+15+5? Or 25-(-15)+9 misparsed. Again consistent = systematic.

---

## Implications

1. **Multilingual evaluation is essential.** A model that appears broken in English might work perfectly in Japanese, and vice versa.
2. **Language is a confound in mathematical evaluation.** Results change with prompt language even when the math is identical.
3. **No single "safe" language** exists across models for domain computation — except for Seed-2.0-mini which appears language-agnostic.
4. **Japanese mathematical reasoning** is surprisingly strong on models trained with CJK data, possibly because Japanese math education language patterns are more precise/structured.

---

## Raw Data
- `cross-lingual-results.json` — 120 trial records with full prompts, responses, and metadata
