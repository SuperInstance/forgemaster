## V4.0 Harsh Review

**Overall verdict:** V4.0 is sharper than V1-V3 but still has three structural weaknesses that could make it unfalsifiable in practice. Here's the breakdown.

---

### What V4.0 Gets Right That Previous Versions Didn't

V1-V3 implicitly treated vocabulary as directly causal. V4.0 makes a cleaner claim: vocabulary is a *proxy* for sign-handling context, not the mechanism itself. This is a meaningful advance because it generates a prediction V1-V3 couldn't: **remove the negative signs, and Mode C should recover**. That's what Study 45 tests. Good.

V4.0 also correctly isolates Eisenstein as a different mechanism (formula interference, not sign failure). This is a necessary refinement — lumping it with sign-handling failures would have been sloppy.

---

### Weak Point 1: "Stored Procedure" Is a Metaphor, Not a Mechanism

The framework uses "stored procedure" and "mode" as if they explain something, but they're phenomenological labels. What does "label anchors formula to known context" mean mechanistically? How does the model *know* it's in Mode A versus Mode B? This is the theory's biggest gap.

The test: **if you swap the label for a synthetic nonsense label ("Glorbitz series") but keep the formula, do you get Mode A behavior or Mode C behavior?** V4.0 predicts Mode C (no stored procedure to retrieve) but that's currently untested. If Glorbitz + formula → 90%+ accuracy, the stored procedure theory collapses — the formula alone is doing the work, not the label-formula pairing.

---

### Weak Point 2: 136/1364 Lacks a Baseline

Mode C "produces 136/1364" — roughly 10% accuracy. This number is doing a lot of work in your theory (it's the signature of "computational failure") but it's uninterpretable without a baseline.

**What does random guessing look like on this task?** If answers are drawn from a continuous distribution, random chance is ~0%. If the task is multiple-choice with 10 options, random chance is ~10%. If the model has a strong default output bias (always outputs the same wrong formula), you'd also get ~10% by accident on a diverse input set.

The specific falsification: **run Study 46 and check whether Mode C's wrong answers cluster around a small set of values (attractor state) or are uniformly distributed.** If they cluster — say, 80% of wrong answers are one of three specific outputs — then Mode C is retrieving a wrong stored procedure, which is mechanistically interesting. If they're uniform, Mode C is just noise. V4.0 currently doesn't distinguish these.

---

### Weak Point 3: Mode D's ~67% Has No Theoretical Basis

Where does 67% come from? If it's empirical: what's the confidence interval, and does it vary by input magnitude? If inputs with larger negatives fail more often than inputs with small negatives, that's a gradient that V4.0 doesn't currently predict.

If 67% is theoretical (say, 2/3 of subtraction operations handle signs correctly), you need to justify the 2/3 fraction. Otherwise Mode D's accuracy is just a datum, not a prediction — which means you can't falsify the "sign handling" story by observing any Mode D accuracy between 0% and 100%.

---

### Weak Point 4: The Modal Identification Problem

How do you know which mode is active for a given trial? You assign modes based on experimental conditions (what prompt you gave), but that assumes the model doesn't slip between modes within a condition. If 10% of "Mode C" trials actually trigger Mode B behavior accidentally (because some default context gets activated), your Mode C accuracy floor is already ~10% by construction.

This is why **Study 46's value isn't just the error distribution — it's detecting whether wrong answers have internal structure.** Partially-correct answers (right formula, wrong sign; right magnitude, wrong sign) would suggest Mode C is doing computation with a systematic error. Completely wrong answers (random-seeming outputs) would suggest Mode C is doing retrieval of a wrong formula.

---

### What Single Result Falsifies V4.0?

Study 45 (all-positive inputs, Mode C) is the key test. V4.0 predicts dramatic improvement — you said "~90%+." But what's the threshold?

**The falsification criterion should be stated precisely before the data arrives:**

> If Study 45 Mode C accuracy is < 50%, the sign-handling hypothesis is falsified as the primary mechanism.

Why 50%? Because that's the crossover point where sign handling can't explain most failures. If Mode C with all-positive inputs still fails 60% of the time, something else is driving failure (formula retrieval, computation length, abstraction level).

The single most devastating result: **Study 45 Mode C accuracy < 30%.** This would mean all-positive arithmetic in the bare Mode C condition still fails catastrophically — implying the failure is about the absence of the formula/label context, not about sign handling at all. It would push the explanation back toward "the model needs the formula presented to it" rather than "the model needs sign guidance."

---

### What V4.0 Still Can't Explain

One thing V4.0 is suspiciously silent on: **why does Mode A work at 100%?** Is it because the label anchors the formula? Or is it because the formula, once presented, makes the computation tractable regardless of label? If you could test "correct formula, wrong label" (e.g., use Fibonacci as the label but present the Schur formula), does it go to Mode A or Mode C?

If correct formula + wrong label → ~100%, then the label is doing nothing and Mode A's success is entirely formula-driven. That would collapse Mode A and Mode B into one question: does the model have the right formula in context?

---

### Summary

V4.0 is the strongest version so far because it's specific about mechanism (sign handling) and isolates Eisenstein. But it still needs:

1. A baseline for interpreting 136/1364
2. A theoretical basis for Mode D's ~67%
3. A pre-registered falsification threshold for Study 45 (< 50%? < 30%?)
4. The Glorbitz control (synthetic label + formula) to separate label effects from formula effects

The sign-handling story is **plausible and testable but not yet proven**. Study 45 is the right next move. If it comes back with all-positive Mode C < 50%, you're back to the drawing board — the failure is about context, not arithmetic.
