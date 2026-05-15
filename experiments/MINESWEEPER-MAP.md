# The Minesweeper Map — What Each Experiment Revealed and What It Cascades To

## The Board State After 44 Studies

### REVEALED TILES (things we KNOW)

| Tile | What We Know | What It Cascades To |
|------|-------------|-------------------|
| **Formula-without-label = 0%** (Study 44, C1) | Models NEED a domain anchor to compute. Generic `f(a,b)` is computationally meaningless to Hermes-70B. | → The model doesn't "compute arithmetic" — it "retrieves a procedure associated with a label." Math is lookup, not calculation. |
| **Formula + Eisenstein label = 100%** (Study 44, C3) | The "landmine" word actually HELPS when formula is present. | → Vocabulary isn't poison. It's a KEY. Without the key, the formula vault stays locked. |
| **Bare arithmetic (25-(-15)+9) = 67%** (Study 39, C5) | Sign handling is the REAL failure mode, not domain vocabulary. | → Double negatives are the actual landmine. The "Vocabulary Wall" was misnamed — it's partly a sign-handling wall that vocabulary accidentally helps with. |
| **Hurwitz norm = 0%** (Study 42) | A "safe" predicted term is the worst landmine. | → You CANNOT predict landmines from domain vocabulary alone. The training data topology is opaque. |
| **Frobenius/Hölder/Mahalanobis = 100%** (Study 42) | Some domain terms are perfectly safe. | → These terms lack competing formula associations in training data. The model has no "wrong procedure" to retrieve. |
| **Wrong answer = 43** (dominant error in Study 42) | 43 = 5² + 5×3 + 3 = a² + ab + b (treating b=3 not b=-3). Sign confusion, not formula swap. | → The primary error mode for most terms is sign handling. Only Eisenstein specifically triggers a DIFFERENT formula (a²+ab+b²=61). |
| **Seed-2.0 = 100% everywhere** (Studies 10, 13, 36, 38) | One model family is immune to all of this. | → Immunity is a TRAINING artifact, not an architecture artifact. What did ByteDance do differently? |
| **Context deprivation hurts** (Study 39) | Full Eisenstein framing (100%) > bare arithmetic (67%). | → Domain context provides computational scaffolding. Stripping it is counterproductive. |

### FLAGGED TILES (things we NOW KNOW ARE MINES — falsified theories)

| Mine | What Hit It | Cascade |
|------|------------|---------|
| "Vocabulary adds load" | Study 39: bare arithmetic worse than domain-framed | → It's not load, it's pathway selection |
| "Specificity predicts danger" | Study 40: r=+0.33, inverted | → Training data topology is the real variable, not term frequency |
| "First token locks in routing" | Study 41: all prefills = 100% with formula | → Routing is conditional on formula presence, not unconditional |
| "Landmines are predictable" | Study 42: 3/12 predictions correct | → We can't predict which terms are dangerous from outside |
| "Attractor basins" | Study 44: landmine label HELPS with formula | → It's not an attractor that captures trajectories, it's a lookup key |
| "Pre-computation always helps" | Study 39 C3: pre-done = 73% < full = 100% | → Models re-derive from scratch instead of trusting given values |

### ADJACENT TILES (what we can DEDUCE from revealed tiles)

**Deduction 1: The model has THREE computational modes, not two.**
- Mode A: "Label + formula" → executes formula correctly (100%)
- Mode B: "Label, no formula" → retrieves stored procedure associated with label (0-100% depending on label)
- Mode C: "No label, formula" → CANNOT compute (0%, produces garbage like 136)
- Mode D: "No label, no formula" → bare arithmetic, sign-handling dependent (~67%)

**Deduction 2: The sign-handling problem IS the computation problem.**
The dominant error across most terms (43) is b=-3 treated as b=3. This isn't domain vocabulary interference — it's a tokenization/arithmetic limitation. Domain vocabulary HELPS because it triggers Mode B (stored procedure), and the stored procedure for most terms happens to handle signs correctly.

**Deduction 3: The real "vocabulary wall" is extremely narrow.**
Only Eisenstein specifically triggers a COMPETING formula (a²+ab+b²=61 instead of a²-ab+b²=49). Most terms fail for the SAME reason (sign handling), not different reasons.

**Deduction 4: Seed-2.0's immunity = correct sign handling + no competing formulas.**
If Seed-2.0 handles negative signs correctly AND doesn't retrieve competing procedures, it's immune by definition. This is probably a training data artifact — ByteDance may have trained on more computational math (with explicit sign handling) vs expository math.

### UNREVEALED TILES (what we STILL need to flip)

| Unknown | Adjacent To | The Cascade Experiment |
|---------|------------|----------------------|
| **Does Mode C generalize?** Is formula-without-label always 0%? | Study 44 C1 (Eisenstein formula) | Test formula-only for Cauchy-Schwarz, Möbius, etc. If all 0% → models can't compute abstract functions at all. If some work → specific to this formula form. |
| **Is sign handling the universal bottleneck?** | Study 42 (43 = dominant error) | Test with ALL POSITIVE inputs (a=5, b=3, answer=19). If accuracy jumps to 95%+ → sign handling is THE problem, everything else is secondary. |
| **Does cross-task replication hold?** | Study 43 (running now) | If vocabulary selector effect appears in Möbius, Fourier, Gram → it's a general phenomenon. If Eisenstein-specific → we found a narrow curiosity. |
| **What does C1's 136/1364 mean?** | Study 44 C1 | 136 = ? 1364 = ? Reverse-engineer what the model computes when given abstract f(a,b) with no label. This tells us what Mode C actually does. |
| **Is Seed-2.0's sign handling different?** | Seed-2.0 = 100% on all tasks | Run Study 42 on Seed-2.0. If it gets 100% on Hurwitz too → sign handling is the differentiator. If it also fails on Hurwitz → different mechanism. |

### THE CASCADE EXPERIMENTS (tightest possible next moves)

**Experiment A: All-Positive Test (Study 45)**
IF sign handling is the primary failure mode → removing negatives should eliminate most errors.
- Same 12 terms from Study 42 but with a=5, b=3 (all positive)
- Answer: 5² - 5×3 + 3² = 25 - 15 + 9 = 19
- PREDICTION: If sign handling is THE problem → accuracy jumps from ~50% average to ~90%+
- CASCADE: If correct → "vocabulary wall" was never about vocabulary. It was about sign handling amplified by vocabulary-dependent lookup.

**Experiment B: Reverse-Engineer 136 (Study 46)**
What IS the model computing in Mode C (formula-only, no label)?
- f(5,-3) → 136 or 1364
- Try f(1,1), f(2,0), f(3,1), f(0,5) with no label
- Map the function the model IS computing
- PREDICTION: 136 = some consistent misparse of a²-ab+b² with unicode superscripts
- CASCADE: If we can reverse-engineer Mode C's function → we understand what "no label" does

**Experiment C: Seed-2.0 Landmine Test (Study 47)**
Does Seed-2.0 handle Hurwitz/Eisenstein/etc the same way?
- Run Study 42's 12 terms on Seed-2.0
- PREDICTION: Seed-2.0 gets 100% on all terms (it's Stage 4)
- FALSIFICATION: If Seed-2.0 also fails on Hurwitz → Hurwitz is a universal landmine, not model-specific
- CASCADE: If Seed-2.0 passes → sign handling IS the Stage 4 differentiator

---

## The Tightened Hypothesis

**V1.0 (dead):** "Vocabulary adds cognitive load" → FALSIFIED by Study 39
**V2.0 (dead):** "Attractor basins compete" → FALSIFIED by Study 44
**V3.0 (dead):** "Domain terms trigger competing formulas" → FALSIFIED by Study 42 (only Eisenstein does this)

**V4.0 (current, testable):**

> LLMs have three computational modes triggered by the presence/absence of (a) a domain label and (b) an explicit formula:
> - Mode A (label + formula): correct execution — the label anchors the formula to a known computation context
> - Mode B (label, no formula): stored procedure retrieval — the label triggers whatever formula the model associates with that term
> - Mode C (no label, formula): computational failure — the model cannot execute abstract function notation without a domain anchor
>
> The primary arithmetic failure mode across modes is negative sign handling. Domain vocabulary's apparent "toxicity" is an artifact: most domain terms happen to trigger stored procedures that handle signs correctly, while bare arithmetic exposes the underlying sign-handling deficit.
>
> A small number of domain terms (Eisenstein specifically) trigger genuinely competing stored formulas, but this is the exception, not the rule.

**Three falsifiable predictions of V4.0:**
1. All-positive inputs will show near-ceiling accuracy across ALL domain terms (Study 45)
2. Mode C (formula-only, no label) produces a consistent, reverse-engineerable wrong function (Study 46)
3. Seed-2.0's immunity extends to all domain terms including Hurwitz (Study 47)
