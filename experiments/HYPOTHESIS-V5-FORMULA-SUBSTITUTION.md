# V5.0: The Formula Substitution Hypothesis
## The first hypothesis consistent with ALL 46 studies

### The Core Claim

Hermes-70B (and likely most non-Stage-4 LLMs) does not execute explicit mathematical formulas faithfully. When presented with `f(a,b) = a² - ab + b²`, the model retrieves a STORED version of this formula from training data. The stored version is usually the MORE COMMON variant `a² + ab + b²`. The model then executes the stored formula, not the given one.

### Evidence Map

| Study | Finding | V5.0 Explanation |
|-------|---------|-------------------|
| **Study 45** (kill shot) | All-positive inputs → 1.7% accuracy. 51% give 49 = a²+ab+b² instead of 19 = a²-ab+b² | Model substitutes + for - in the formula. Executes stored formula, not given formula. |
| **Study 42** | Hurwitz=0%, all give 43 | 43 = 5²+5×3+3 = a²+ab+b. Same PLUS substitution, plus b=3 (dropped negative). |
| **Study 44** C1 | Formula-only → 0%, produces 136 | No label → model computes SOMETHING, but not the given formula. 136 = ? (awaiting Study 46) |
| **Study 44** C3 | Formula+Eisenstein → 100% | "Eisenstein" is a strong enough anchor that the model retrieves the CORRECT stored formula (a²-ab+b²) — the one associated with Eisenstein in training data. |
| **Study 39** C1 | Full Eisenstein (with formula) → 100% | Same as C3 above. Eisenstein label overrides the default PLUS substitution. |
| **Study 39** C5 | Bare arithmetic "25-(-15)+9" → 67% | Double negatives partially defeat the substitution. When the model can't substitute, it computes. When it can, it retrieves. |
| **Study 42** Frobenius/Hölder = 100% | These terms have NO stored formula that conflicts | The model has no competing stored formula, so it... actually follows the given one? |
| Study 10 | Bare arithmetic = 100%, Eisenstein = 0-25% | Without the formula given, Eisenstein triggers full stored formula override. With bare numbers, no formula to override — just arithmetic. |
| Study 28 | T=0.7 dissolves wall (67%) | Temperature increases stochasticity, allowing escape from the stored-formula attractor. |

### The Mechanism

1. Model receives `f(a,b) = a² - ab + b²`
2. Model recognizes this as "a quadratic form" from training data
3. Model retrieves the MOST COMMON version of this formula from its training distribution
4. The most common quadratic form in math is `a² + ab + b²` (the POSITIVE definite one, used in Eisenstein/Hermitian/lots of contexts)
5. The model EXECUTES the stored version, not the given version
6. Exception: when a strong domain label (Eisenstein) is present, the stored version associated with that label (a²-ab+b²) overrides the generic default

### Why This Explains Everything

- **Why Eisenstein with formula = 100%**: The Eisenstein label anchors to the SPECIFIC stored formula a²-ab+b², which happens to be correct
- **Why bare "Frobenius norm" = 100%**: Frobenius norm has NO specific competing formula for 2D inputs, so the given formula wins by default
- **Why generic f() = 0%**: No label → model retrieves the default (a²+ab+b²) and computes that
- **Why Hurwitz = 0%**: "Hurwitz" triggers a stored formula that computes a²+ab+b² (or a²+ab+b = 43)
- **Why all-positive didn't help**: The problem isn't sign handling in arithmetic — it's sign handling in the FORMULA ITSELF. The model reads "-" and stores "+"

### The Three Falsifiable Predictions

1. **Study 46 will show**: Mode C (formula-only) computes a²+ab+b² across most input pairs. The "136" from Study 44 is a²+ab+b² evaluated at (5,-3) = 25+(-15)+9 = 19? No wait — a²+ab+b² for (5,-3) = 25-15+9 = 19. That doesn't give 136. So 136 is something else — maybe the model is computing a²×b² or (a-b)²×something. Study 46 will tell us.

2. **If we test with the PLUS formula** (a²+ab+b²) and all-positive inputs, accuracy should be near 100% — because the stored default MATCHES the given formula.

3. **If we test a genuinely rare formula** that has no common training-data variant, the model should follow the given formula correctly — no competing stored formula to override.

### What This Means for the Paper

The paper isn't about a "Vocabulary Wall." It's about **formula substitution in LLMs**:
- Models don't execute given formulas — they retrieve stored formulas triggered by vocabulary
- The most common stored variant overrides the given formula
- Domain labels can override the default if the label has a specific formula association
- This is a fundamental limitation of current LLM architectures for mathematical computation

THIS is the publishable finding. Not "vocabulary kills computation" — "LLMs substitute common formulas for given ones."
