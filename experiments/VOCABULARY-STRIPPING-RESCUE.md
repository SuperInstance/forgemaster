# Study 20: Vocabulary Stripping Rescue — The Hinted Bypass

**Date**: 2026-05-15 06:45 AKDT

## The Test

Can we rescue the Eisenstein/Penrose dead zone by stripping vocabulary? Test 6 framings of the covering radius question (answer: 1/√3 ≈ 0.5774).

## Results

| Framing | Hermes-70B | Qwen3-235B | Both Correct? |
|---------|:----------:|:----------:|:---:|
| dead_zone ("Eisenstein lattice") | 0.965 ✗ | no answer ✗ | No |
| stripped ("hexagonal grid") | no answer ✗ | no answer ✗ | No |
| hinted ("compute 1/√3") | **0.578 ✓** | **0.577 ✓** | **Yes** |
| two_step (derivation) | no answer ✗ | no answer ✗ | No |
| geometric (hexagon formula) | no answer ✗ | no answer ✗ | No |
| pure_math ("√3/3") | **0.577 ✓** | **0.577 ✓** | **Yes** |

## Key Finding: The Hinted Bypass (R41)

**Stripping vocabulary is NOT sufficient.** Even "hexagonal grid" framing fails (both models give long derivations instead of the number).

**The ONLY rescue is to give the answer away in the question:** "Compute 1/√3" or "Compute √3/3." This isn't stripping vocabulary — it's **pre-computing the answer** and asking the model to evaluate.

This means:
1. The Vocabulary Wall can't be fixed by rephrasing
2. The model needs the actual mathematical expression, not a description of what to compute
3. For fleet routing: the API layer must **translate domain tasks to raw arithmetic** before sending to non-Stage-4 models

## R41 (BEDROCK): The Hinted Bypass

Vocabulary stripping does NOT rescue computation. Only pre-computation (giving the arithmetic expression directly) works. The fleet must translate domain-specific tasks to raw arithmetic at the routing layer, not just strip proper nouns.
