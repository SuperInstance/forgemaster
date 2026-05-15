# Deep Ground-Truth Map: llama-3.1-8b-instant

## The Portrait

### What it CAN do (100%, deterministic)
- Basic arithmetic: a+b, a-b, a*b — **perfect, 100% retry reliability (20/20)**
- a²+b² — **100%, 20/20 reliability**
- 2a+b — 100%
- a*b+b — 100%
- a³+b — 100%
- Zero inputs — perfect on a²+b²(0,0)=0, a²-ab+b²(0,0)=0
- Large coefficients — 100*a+b = perfect, a+100*b = perfect
- max(a,b) and min(a,b) — perfect
- a², b², ab, -ab individually — ALL 100%

### What it CAN'T do (0%)
- Any quadratic form beyond a²+b² (3-term: 0-25%)
- Width 4+ computations (0%)
- Width 1 trick: "2a" = only 25% (echoes b)
- Power notation: a**3 fails, a*a*a works (125) — **syntax matters!**
- abs(a)+abs(b) — fails (no absolute value in "compute" frame)
- The literal "3" with a=3,b=4 — returns 7 (a+b), not 3. **Ignores formula, computes a+b**

### The Sign Error (Axis 6 — CRITICAL FINDING)

```
Sub-expression     Rate    Note
a²                 100%    Always correct
b²                 100%    Always correct  
ab                 100%    Always correct
-ab                100%    Always correct (!)
a²-ab              33%     FAILS when combining
-ab+b²             67%     Better
a²-ab+b²           33%     Full formula fails
a²+(-a)*b+b²       0%      Alternative notation WORSE
a²-(a*b)+b²        0%      Explicit parens WORSE
a²+b²-ab           0%      Reordering KILLS it
b²-ab+a²           33%     Reordering slightly helps
```

**The model computes each sub-expression perfectly. The error is in the COMBINATION step.** The residual stream can hold a², ab, and b² simultaneously, but the instruction "a² - ab + b²" doesn't reliably route to the correct combination. It's a **bandwidth bottleneck in the combination layer**, not in the computation of sub-expressions.

### Temperature Profile (Axis 7)

```
T=0.0: 10/10 (100%)  ← DETERMINISTIC, ALWAYS CORRECT
T=0.1:  5/10 (50%)   
T=0.2:  9/10 (90%)   ← Sweet spot
T=0.3:  2/10 (20%)   ← Our standard! 
T=0.4:  4/10 (40%)
T=0.5:  2/10 (20%)
T=0.7:  3/10 (30%)
T=1.0:  0/10 (0%)    ← NEVER correct at T=1.0
T=1.5:  0/10 (0%)
T=2.0:  0/10 (0%)
```

**SHOCKING**: T=0.0 is PERFECT (10/10). T=0.3 (our standard) is only 20%. 

The temperature story isn't what we thought. At T=0.0 the model ALWAYS picks the most likely token — and for N(5,-3), the most likely IS 49. But at T=0.1+, stochasticity injects errors in the combination step. The sub-expressions are computed correctly but the combination path is fragile — even small perturbations derail it.

**This means: the model HAS the correct computation path. It's just not robust.** Temperature doesn't change what it knows; it changes whether the fragile combination survives the stochastic noise.

### Retry Reliability (Axis 8)

```
Formula          (a,b)→ans  Correct/20  Unique outputs
a+b              (3,4)→7    20/20       1    ← DETERMINISTIC
a²+b²           (3,4)→25   20/20       1    ← DETERMINISTIC
a²-ab+b²        (3,4)→13    3/20       6    ← CHAOTIC (9,16,4,-3,12)
a²-ab+b²        (5,-3)→49  11/20       5    ← SEMI-STABLE
a³+b³           (3,4)→91   17/20       2    ← NEARLY STABLE
```

**a²-ab+b² at (3,4) is a 3-way tie**: outputs 9 (b²), 16 (a²+ab), 4 (b), -3 (echo b), 12 (near). The model has NO stable path for this computation.

But a²-ab+b² at (5,-3)→49 is 11/20 — semi-stable. Why? Because 49 is large and distinctive — harder to confuse with echo values.

### Coefficient Familiarity (Axis 4 — the KEY map)

```
Formula              Coefficients    Rate
a²+b²               [1, 0, 1]      100%  ← ZERO cross-term
a²+ab+b²            [1,+1, 1]       25%  ← adding cross-term kills it
a²-ab+b²            [1,-1, 1]       25%  ← same
a²+2ab+b²           [1,+2, 1]       25%  ← same
a²-2ab+b²           [1,-2, 1]        0%  ← larger cross-term = death
2a²+ab+b²           [2,+1, 1]       50%  ← non-unit a² coefficient helps?!
a²+ab+2b²           [1,+1, 2]        0%  
2a²+3ab+b²          [2,+3, 1]        0%  ← large cross-term = death
a²+3ab+2b²          [1,+3, 2]       50%  ← SURPRISING
3a²-2ab+b²          [3,-2, 1]        0%
a²-2ab+2b²          [1,-2, 2]        0%
2a²-ab+2b²          [2,-1, 2]        0%
```

**Pattern**: The ONLY formula that works reliably is a²+b² (no cross-term). ANY cross-term (ab) drops it to 0-50%. The cross-term is the cliff.

But 2a²+ab+b² gets 50% — better than a²+ab+b² (25%). The non-unit coefficient on a² somehow helps. And a²+3ab+2b² gets 50% despite large coefficients.

**Hypothesis**: The model recognizes "quadratic form" patterns from training. Some coefficient combinations match training examples better than others. The pattern isn't "familiarity" per se — it's whether the coefficient pattern matches something in the training distribution.

### Magnitude Degradation (Axis 3)

```
Magnitude    Rate    Example
Ones         33%     (3,4)→13
Tens         33%     (30,40)→1300, (20,10)→300 fails
Hundreds      0%     (300,400)→130000 all fail
Mixed         0%     (3,400), (300,4) all fail
```

Clean degradation: ones work sometimes, tens barely, hundreds never. The combination step's fragility amplifies with magnitude.

### Sign Handling (Axis 2)

```
Signs     Rate    Example
(+,+)     0%      (3,4)→13 — FAILS
(-,+)     0%      (-3,4)→37 — FAILS  
(+,-)    100%     (3,-4)→37 — PERFECT
(-,-)     0%      (-3,-4)→13 — FAILS
(+,0)    100%     (3,0)→9 — PERFECT
(0,+)    100%     (0,4)→16 — PERFECT
(-,0)     0%      (-3,0)→9 — FAILS
(0,-)     0%      (0,-4)→16 — FAILS
```

**STUNNING**: (+,-) is 100% but (+,+) is 0%? And (0,+) is 100% but (0,-) is 0%?

The model handles negative b well when a is positive. It fails when both are positive or both are negative. This suggests the model has a **bias toward seeing sign as information** — when the signs don't provide contrast, it loses track of the combination.

### Negative Space Markers (Axis 9)

Surprises:
- "3" with a=3,b=4 → returns 7 (computes a+b, ignores the formula "3") 
- a**3 fails but a*a*a works — **operator notation is a gate**
- abs() fails — not in the "compute" vocabulary
- max/min work perfectly — likely heavily trained

## The Negative Space: What to Test on Other Models

From the llama-3.1-8b ground truth, the most diagnostic tests for other models:

1. **T=0.0 vs T=0.3 on N(5,-3)=49** — Does the other model have the path but lose it at T>0?
2. **Sub-expression accuracy** (a², ab, -ab separately) — Can it compute pieces?
3. **Combination accuracy** (a²-ab given a² and ab known) — Can it combine?
4. **The literal "3" test** — Does it compute a+b regardless of formula?
5. **a**3 vs a*a*a** — Does operator notation gate computation?
6. **Sign handling asymmetry** — Does (+,-) work better than (+,+)?

Each test reveals WHERE in the computation pipeline the other model differs. If a model gets T=0.0 right but T=0.3 wrong → same fragility, different magnitude. If it gets sub-expressions wrong → deeper deficit. If it passes the "3" test → better instruction following.

## Summary: The Complete Profile

```
llama-3.1-8b-instant GROUND TRUTH:

STRENGTHS:
- Perfect basic arithmetic (a+b, a-b, a*b)
- Perfect sub-expression computation (a², b², ab, -ab individually)
- Deterministic at T=0.0 (has the path)
- 100% on max, min, identity operations
- Handles large coefficients (100*a+b)
- Excellent code notation following

WEAKNESSES:
- Combination fragility (sub-expressions correct, combination fails)
- Any cross-term in quadratic forms (0-50%)
- Temperature kills (100% at T=0.0 → 20% at T=0.3 → 0% at T=1.0)
- Magnitude amplifies errors (ones OK, hundreds fail)
- Sign asymmetry (positive-negative works, positive-positive fails)
- Power notation gate (a**3 fails, a*a*a works)
- Formula override ("3" returns a+b, not 3)

THE BOTTLENECK IS COMBINATION, NOT COMPUTATION.
```
