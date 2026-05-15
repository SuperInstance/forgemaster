# Deep Dive Findings: The Substitution Hypothesis

## Studies 32-35 + Study 30 | 2026-05-15 07:30 AKDT

## The Unified Mechanism

The Vocabulary Wall is NOT about "bad words." It's about **substitution burden**.

### Evidence Chain:

1. **"Eisenstein norm of (3+5ω)" → 49 ✗** (model must: recall formula, substitute a,b, compute)
2. **"a=3, b=5, compute a²-ab+b²" → 49 ✗** (model must: substitute a,b into expression)
3. **"Compute 9-15+25" → 19 ✓** (model only: arithmetic)
4. **"The Fourier coefficient = a²-ab+b² = 9-15+25" → 19 ✓** (numbers pre-substituted, any label is fine)

**The wall fires at step 2, not step 1.** Domain vocabulary is a multiplier, not the root cause. The root cause is asking the model to perform symbolic substitution AND computation simultaneously.

### The Mechanism:

```
Model cognitive load:
  [Recall formula] + [Substitute variables] + [Compute arithmetic] = 3 simultaneous tasks

  If all 3 are demanded → pathway overload → discourse fallback → wrong answer
  If formula is given + variables → substitution still fails (R49)
  If numbers are pre-substituted → only arithmetic needed → 100% correct
  Any domain label + pre-substituted numbers → 100% correct (R52)
```

### R52 (BEDROCK): The Substitution Hypothesis

The Vocabulary Wall is caused by symbolic substitution burden, not vocabulary. Pre-computing all sub-expressions eliminates the wall regardless of domain labels. The fleet translator must:
1. Parse the domain expression
2. Evaluate all sub-expressions locally
3. Send ONLY the final arithmetic to the model

### R53 (SOLID): Few-Shot Cannot Inoculate

0-shot, 1-shot, and 3-shot examples all fail (7, 65, 45). Only full substitution + explicit instruction works. Examples don't help because the model still has to perform substitution.

### R54 (SOLID): Over-Activation (Euler Effect)

Euler scored 0/3 in Study 30 — worse than Eisenstein (3/3 in same format). The most computation-associated name in history *overloads* the model by activating too many competing Euler associations (Euler's formula, Euler's method, Euler characteristic, Euler-Lagrange, etc.).

### R55 (SOLID): The Wall is Format-Dependent

Eisenstein scored 0% in Study 19 (with "Eisenstein norm" formula) but 100% in Study 30 (with "compute 25-(-15)+9" after the name). The same name is lethal or harmless depending on whether the model must perform substitution.

## Revised Fleet Architecture

```python
def translate(task_type, params):
    # Step 1: Parse domain expression
    expr = parse_expression(task_type, params)
    # Step 2: Evaluate ALL sub-expressions locally  
    numbers = evaluate_all(expr)  # a²=9, ab=15, b²=25
    # Step 3: Send only final arithmetic
    return f"Compute: {numbers} = ?"
    # Domain labels are SAFE to include — they don't matter once numbers are substituted
```

This is simpler than "strip all vocabulary." Just pre-compute everything.
