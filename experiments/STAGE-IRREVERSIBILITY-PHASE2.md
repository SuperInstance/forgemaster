# Piaget Stage Test — Phase 2: Recall & Transfer (Eisenstein Integers)

**Date:** 2026-05-15 13:12
**Models:** qwen3:0.6b, qwen3:4b, gemma3:1b
**Cells:** A (baseline), B (step-by-step few-shot), C (Eisenstein warm-up facts)
**Questions:** 8 (4 recall, 4 transfer) — formula NOT provided
**Scoring:** 0=wrong, 1=partial, 2=correct (max=16 per cell)

## Summary Scores

| Model | Cell A | Cell B | Cell C | A% | B% | C% |
|-------|--------|--------|--------|----|----|-----|
| qwen3:0.6b | 3/16 | 1/16 | 6/16 | 18.8% | 6.2% | 37.5% |
| qwen3:4b | 0/16 | 0/16 | 0/16 | 0.0% | 0.0% | 0.0% |
| gemma3:1b | 7/16 | 10/16 | 8/16 | 43.8% | 62.5% | 50.0% |

## Per-Model Detail

### qwen3:0.6b

| Q | Group | Cell A | Cell B | Cell C |
|---|-------|--------|--------|--------|
| 1 | A | 1 | 1 | 2 |
| 2 | A | 0 | 0 | 2 |
| 3 | A | 0 | 0 | 0 |
| 4 | A | 0 | 0 | 0 |
| 5 | B | 2 | 0 | 2 |
| 6 | B | 0 | 0 | 0 |
| 7 | B | 0 | 0 | 0 |
| 8 | B | 0 | 0 | 0 |

### qwen3:4b

| Q | Group | Cell A | Cell B | Cell C |
|---|-------|--------|--------|--------|
| 1 | A | 0 | 0 | 0 |
| 2 | A | 0 | 0 | 0 |
| 3 | A | 0 | 0 | 0 |
| 4 | A | 0 | 0 | 0 |
| 5 | B | 0 | 0 | 0 |
| 6 | B | 0 | 0 | 0 |
| 7 | B | 0 | 0 | 0 |
| 8 | B | 0 | 0 | 0 |

### gemma3:1b

| Q | Group | Cell A | Cell B | Cell C |
|---|-------|--------|--------|--------|
| 1 | A | 1 | 2 | 1 |
| 2 | A | 0 | 0 | 0 |
| 3 | A | 1 | 1 | 0 |
| 4 | A | 2 | 2 | 2 |
| 5 | B | 0 | 2 | 0 |
| 6 | B | 1 | 1 | 2 |
| 7 | B | 1 | 1 | 1 |
| 8 | B | 1 | 1 | 2 |

## Group Comparison (Recall vs Transfer)

| Model | Cell | Recall (A) | Transfer (B) |
|-------|------|------------|--------------|
| qwen3:0.6b | A | 1/8 | 2/8 |
| qwen3:0.6b | B | 1/8 | 0/8 |
| qwen3:0.6b | C | 4/8 | 2/8 |
| qwen3:4b | A | 0/8 | 0/8 |
| qwen3:4b | B | 0/8 | 0/8 |
| qwen3:4b | C | 0/8 | 0/8 |
| gemma3:1b | A | 4/8 | 3/8 |
| gemma3:1b | B | 5/8 | 5/8 |
| gemma3:1b | C | 3/8 | 5/8 |

## Stage Classification

| Model | Cell A | Cell B | Cell C | Overall Stage |
|-------|--------|--------|--------|---------------|
| qwen3:0.6b | S1 | S1 | S2 | S2 |
| qwen3:4b | S1 | S1 | S1 | S1 |
| gemma3:1b | S2 | S3 | S3 | S3 |

## Key Observations

### Phase 2 vs Phase 1
Phase 2 tests **recall** (knowing Eisenstein integer properties without being given formulas) vs Phase 1 which tested **computation** (applying given formulas). This distinguishes:
- **Stage 4**: Can recall domain facts AND apply them correctly
- **Stage 3**: Can apply scaffolding but lacks independent recall
- **Stage 2**: Partial recall, inconsistent application
- **Stage 1**: Cannot recall or apply domain-specific knowledge

### Expected Patterns
- **qwen3:0.6b (Stage 1)**: Near-zero scores across all cells — too small for domain recall
- **qwen3:4b (Stage 2-3)**: Cell C > Cell B > Cell A (scaffolding helps), moderate scores
- **gemma3:1b (Stage 1)**: Low scores, may show some improvement with Cell C

### Critical Test: Cell B vs Cell C
- Cell B gives general reasoning scaffolding → helps Stage 3+ (can reason if they know facts)
- Cell C gives domain facts → helps Stage 2+ (can apply if given the facts)
- **If Cell C >> Cell B**: Model is Stage 2 (needs domain knowledge, not reasoning help)
- **If Cell B >> Cell C**: Model is Stage 3 (can reason but domain knowledge is wrong)
- **If Cell B ≈ Cell C ≈ high**: Model is Stage 4 (has both reasoning and domain knowledge)

## Sample Responses

### qwen3:0.6b — Q5 (N(αβ)) Cell A
**Score: 2/2**
> N(αβ) = 13 × 7 = 91.

### qwen3:0.6b — Q1 (7 prime?) Cell C
**Score: 2/2**
> No, 7 is not an Eisenstein prime because 7 ≡ 1 mod 3, which does not satisfy the condition for being a rational prime congruent to 2 modulo 3.


### qwen3:4b — Q5 (N(αβ)) Cell A
**Score: 0/2**
> 

### qwen3:4b — Q1 (7 prime?) Cell C
**Score: 0/2**
> 


### gemma3:1b — Q5 (N(αβ)) Cell A
**Score: 0/2**
> N(αβ) = Nα * Nβ / Nα * Nβ = 13 * 7 / 13 * 7 = 13

### gemma3:1b — Q1 (7 prime?) Cell C
**Score: 1/2**
> No. 7 is not an Eisenstein prime because it is not congruent to 2 modulo 3.

