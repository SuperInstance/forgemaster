# Study 33: Translation Depth — Variables Also Trigger the Wall

**Date**: 2026-05-15 07:25 AKDT

## Results (Hermes-70B, expected: 19)

| Translation Depth | Prompt | Result |
|:--|:--|:--:|
| raw_domain | "Eisenstein norm of (3+5ω)" | 49 ✗ |
| stripped | "a=3, b=5, compute a²-ab+b²" | 49 ✗ |
| **two_step** | "First: a=3, b=5. Then: a²-ab+b²" | **49 ✗** |
| **substituted** | "Compute 9 - 15 + 25" | **19 ✓** |
| broken_down | "Step 1: 3²=9. Step 2: 3×5=15..." | 19 ✓ |
| equation_only | "9 - 15 + 25 = ?" | 19 ✓ |
| verification | "I calculated 9-15+25=19. Correct?" | 19 ✓ |
| chain_of_thought | "Let me think step by step..." | 19 ✓ |

## R49 (BEDROCK): Variables Are Lethal Too

"Compute a²-ab+b² where a=3, b=5" returns 49 (wrong). "Compute 9-15+25" returns 19 (correct).

The model cannot reliably bind variables to values for computation. The presence of algebraic variables triggers the same pattern-matching pathway as domain vocabulary.

**The translation must be FULLY substituted — no variables, no algebra, just numbers and operators.**

## Translation Depth Hierarchy

1. ✗ Domain + variables: "Eisenstein norm of (a+bω)" 
2. ✗ Variables only: "a=3, b=5, compute a²-ab+b²"
3. ✗ Mixed: "First: a=3, b=5. Then compute..."
4. ✓ Numbers only: "Compute 9-15+25"
5. ✓ Step-by-step numbers: "3²=9, 3×5=15, 5²=25, 9-15+25=?"
6. ✓ Verification: "I got 19, correct?"
7. ✓ Chain of thought with numbers: "Let me think... 9-15+25=19"

The fleet translator must pre-compute ALL sub-expressions. No variable binding delegation to the model.
