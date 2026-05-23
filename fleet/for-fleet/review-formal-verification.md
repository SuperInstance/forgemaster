# Formal Review: Formal Verification of a Constraint Compilation VM

**Reviewer:** Forgemaster ⚒️ (Subagent Review)
**Paper:** "Formal Verification of a Constraint Compilation VM: A Lean4 Proof Strategy for FLUX ISA"
**Date:** 2026-05-03
**Venue模拟:** CAV/ITP-style review

---

## 1. Proof Feasibility — 7/10

The proposed proof is **doable** but the paper conflates several things that a real formal methods paper must separate.

**What's feasible:** The mini VM (21 opcodes, sequential execution, no backward jumps, fixed stack) is a genuinely tractable proof target. Termination (Theorem 2) is almost trivial — IP only moves forward, so `program.length - ip` is a well-founded measure. Stack boundedness (Theorem 3) is structurally guaranteed by the `Fin (STACK_SIZE + 1)` type on `sp`. These two theorems together probably represent 2-3 weeks of honest effort.

**What's questionable:** Soundness (Theorem 1) as stated requires an execution trace that the paper's `Steps` relation does not actually produce. The `Steps` inductive (Section 4.3) yields a final `ExecResult`, not a trace. The theorem quantifies over `trace : ExecutionTrace` and `trace[i]`, but no `ExecutionTrace` type is defined anywhere in the Lean4 signatures. This is a **gap** — you either need to define traces explicitly (substantial additional effort) or reformulate soundness to only talk about the final state.

**351 lemmas:** This number feels pulled from thin air. The decomposition table (Section 6.1) lists "3 per opcode" for single-step semantics, "2 per opcode" for invariant preservation — these are reasonable ballpark figures, but the real question is how many auxiliary lemmas about `Vector`, `Fin`, and `Float` arithmetic you'll need. In practice, Lean4 proofs of this kind require 2-3× the "core" lemma count in infrastructure lemmas about the standard library. Budget 500-700 lemmas total.

## 2. Lean4 Strategy — 5/10

Several technical issues with the Lean4 code as presented:

**Critical: `stack` type mismatch.** The `VMState` structure declares `stack : Float` — a single float, not a stack. The prose says it should be `Vector Float STACK_SIZE` or equivalently `Fin STACK_SIZE → Float`. This is a typo that undermines confidence in the rest of the type signatures.

**`Steps` relation is wrong.** The `Steps.refl` constructor says `Steps s prog (.ok s [] s.constraints_ok)` — but this means "zero steps of execution produce a result with empty outputs and the initial constraints_ok." The `Steps.step` constructor says `Step s prog (.ok s' [])` — but `Step` for opcodes like `Add` should produce a state with advanced IP, not necessarily empty outputs. The `[]` for `outputs` in the intermediate states doesn't make sense. This needs to be restructured so intermediate steps carry state, not output lists.

**`ExecResult` carries `outputs : List Float`** but no opcode in the mini VM produces outputs. Where do outputs come from? This appears to be carried over from the full VM design without adaptation.

**Float opacity is underappreciated.** The paper mentions this in risk factors but doesn't address it in the proof strategy. Lean4's `Float` is literally `Float` mapping to C `double`. You cannot prove `a + b = b + a` for Lean4 `Float` without axiomatizing it. The comparison opcodes (`Eq`, `Lt`, etc.) push `1.0` or `0.0` based on float comparison — you need to axiomatize what `Float` comparisons mean. The `Assert` opcode checks `val ≠ 0.0` — but in IEEE 754, `-0.0 = 0.0`. Does the Rust implementation treat `-0.0` as passing or failing? This matters for soundness.

**`safe` predicate is undefined.** Section 3.1 and the Hermes-style formulation reference `safe P` meaning "well-formed, no stack underflow on any execution path." But computing `safe` for an arbitrary program requires solving a reachability problem. In the mini VM (no jumps), this is decidable by forward simulation, but the paper doesn't define it formally.

## 3. Soundness Theorem — 6/10

**The theorem statement is almost right but has issues:**

The first formulation (Section 3.1) says: "If VM reports `constraints_satisfied = true`, then every Assert in the execution trace evaluated its operand to non-zero." This is soundness of constraint reporting. It's the right thing to prove.

But the Lean4 formalization in Section 4.7 doesn't match. The `soundness` theorem there quantifies over a `TraceEntry` type that doesn't exist in the formal model. And the induction is on `hsteps`, but the conclusion talks about positions `ip` in the *program*, not in the execution trace — these are different things if the program is executed starting from a nonzero initial IP.

**Missing case: `Reject`.** The `Reject` opcode unconditionally sets `constraints_ok = false`. The soundness theorem's hypothesis is `constraints_satisfied = true`, so `Reject` must not have been executed. But the theorem doesn't explicitly exclude execution paths containing `Reject`. If a program has `Reject` followed by `Halt`, and execution starts *after* the `Reject`... the theorem as stated is fine because it talks about *the* execution, but the `Steps` relation needs to ensure that execution always starts at IP=0 (or the theorem needs to account for arbitrary starting IPs).

**Missing case: `Check` with zero.** The `Check` opcode sets `constraints_ok = false` when the top of stack is zero, but doesn't abort. A program could have `Check` (zero) followed by more instructions that happen to produce `constraints_ok = true` through some later operation. Wait — looking at the semantics, `Check` sets it to `false`, and nothing ever sets it back to `true`. So once false, always false. But the paper doesn't state or prove this monotonicity property. It's essential for soundness.

## 4. Weaknesses (Top 3)

### W1: No Float Reasoning Strategy
The paper handwaves float arithmetic by saying "treat float operations as opaque satisfying basic commutativity/associativity axioms." But the `Assert` opcode's correctness depends on whether a float value is zero or nonzero. The `Div`/`Mod` opcodes depend on zero-checks. The `Eq` opcode uses float equality (not bitwise equality). You need at minimum a decision procedure for "is this float expression zero" — and IEEE 754 makes this undecidable in general (you can't even prove `x + (-x) = 0.0` without controlling for NaN/Inf). **This is the paper's biggest gap.**

### W2: Refinement Gap is Unaddressed
The paper proposes proving properties about a Lean4 model, then claims a "refinement proof" bridges to the Rust implementation. But Section 5.6 gives no formal account of this refinement. What is the simulation relation? How do you handle the fact that Lean4 `Float` ≠ Rust `f64` (different NaN payloads, different signaling)? Without the refinement, you've proved a mathematical model correct, not the actual VM.

### W3: `Steps` Semantics Don't Support Soundness Proof
The multi-step relation `Steps` produces a final `ExecResult` but discards intermediate states. To prove "every Assert in the trace passed," you need the trace — a list of intermediate states. You either need to redefine execution to produce traces (changing the entire proof structure) or reformulate soundness to only talk about the final state (weakening the theorem).

## 5. Strengths (Top 3)

### S1: Excellent Choice of Proof Target
The mini VM is genuinely well-suited for formal verification. Sequential execution, fixed stack, no heap, `no_std`, 21 opcodes — these are not accidental properties. The paper correctly identifies that each simplification in the implementation translates directly to proof simplification. This is proof engineering wisdom.

### S2: Termination is Nearly Free
The observation that the mini VM has no backward jumps means termination follows from a simple measure (`program.length - ip`). This is a genuine design-for-verification property. In a world where most verification effort goes into termination proofs, having this come "for free" is significant.

### S3: Stack Safety by Construction
Using `Fin (STACK_SIZE + 1)` for the stack pointer means stack bounds are enforced by Lean4's type system. You can't construct an out-of-bounds `sp`. This is exactly the right approach — use types to eliminate proof obligations. The boundedness theorem (Theorem 3) is then about preservation of this invariant through operations, which is much simpler than proving it from scratch.

## 6. Technical Errors

1. **`stack : Float`** in `VMState` — should be `Vector Float STACK_SIZE` or `Array Float` with a length constraint.
2. **`Steps.refl`** allows "zero steps = result" which conflates initial state with terminal state. Needs restructuring.
3. **`Steps.step`** constructor pattern-matches on `Step s prog (.ok s' [])` but `Step` for most opcodes produces `.ok (push (popn s 2) (a + b)) rest s.constraints_ok` — the `rest` here is unexplained. Should this be the remaining program, or a continuation? If the program is fixed and IP advances, there is no "rest."
4. **`assert_pass` produces `.ok (pop s) []`** — the empty list `[]` appears to be an output list, but Assert doesn't produce output. Meanwhile `add` produces `.ok (push (popn s 2) (a + b)) rest` — what is `rest`? These constructors are inconsistent.
5. **The `vm_cases` tactic** references `FluxOpcode.all_cases` which is not defined. You'd need `@[reducible] def FluxOpcode.allCases : List FluxOpcode := [.Add, .Sub, ...]` or use the `cases` tactic directly on the inductive type.
6. **The Hermes-style theorem** references `res.constraints_ok` but `ExecResult.ok` has signature `ok (state : VMState) (outputs : List Float) (satisfied : Bool)` — so it should be the `satisfied` field, accessed via pattern matching, not dot notation on `res`.

## 7. Missing Proof Obligations

1. **`constraints_ok` monotonicity**: Once set to `false`, it never returns to `true`. Required for soundness, not proved or even stated as a lemma.
2. **`Check` semantics correctness**: `Check` peeks without popping (Section 2.4 says "non-consuming"), but the stack depth effect is `sp` unchanged. The paper needs to prove that `Check` doesn't modify the stack at all (only `constraints_ok`).
3. **`Validate` semantics**: Pops 3 values (val, lower, upper) — but which is on top? Stack ordering conventions need to be specified and proved consistent between `peek` indices and the semantic interpretation.
4. **Program well-formedness / `safe` predicate**: The soundness theorem's Hermes formulation requires `safe P`, but this predicate is never formally defined and its decidability is not established.
5. **Float comparison soundness**: The comparison opcodes (`Eq`, `Lt`, etc.) produce `1.0` or `0.0`. The paper assumes these are meaningful truth values, but needs to connect them to the Boolean `constraints_ok` maintained by `Assert`/`Check`.
6. **Initial state invariant**: The theorems assume some initial state, but don't specify that `sp = 0`, `ip = 0`, `steps = 0`, `constraints_ok = true` initially. These should be preconditions.

## 8. Effort Estimate

**The 8-16 week estimate is optimistic but in the right ballpark for the abstract model alone.**

For comparison:
- **CompCert**: ~100K lines of Coq, ~15 person-years (Leroy's team). But CompCert is a full optimizing C compiler with ~150 passes.
- **seL4**: ~200K lines of Isabelle, ~20 person-years. Microkernel with 10K LOC C, concurrency, IPC.
- **Fiat-Crypto**: ~30K lines of Lean, ~3-4 person-years. Curve arithmetic with fiat synthesis.
- **WASM type soundness** (Watt): ~10K lines of Isabelle, ~6 months for one researcher.

The FLUX VM is genuinely simpler than all of these. A reasonable comparison is the **JVM bytecode verifier** sub-problem (stack-map frame verification), which took ~3-4 months for a trained researcher in Coq.

**Revised estimate:**
- Abstract model + Theorems 2 & 3: 4-6 weeks
- Soundness (Theorem 1) with trace reconstruction: 6-8 weeks
- Float axiomatization and related proofs: 2-4 weeks
- Custom tactics and automation: 2-3 weeks
- **Total: 14-21 weeks (3.5-5 months)** for a trained Lean4 practitioner

The "8 weeks optimistic" estimate ignores float reasoning and the trace reconstruction problem. A more honest estimate is 4-5 months.

## 9. Certification Claims — 4/10

The DO-330 discussion (Section 8) is aspirational but incomplete:

1. **No formal gap analysis.** DO-330 requires *specific* objectives to be met with *specific* evidence. The table in Section 8.2 maps objectives to "how proof helps" but doesn't identify what's missing. Missing: configuration management evidence, tool installation procedures, tool operating environment documentation, tool problem reporting procedures.

2. **Tool chain qualification.** The paper mentions that "Lean4 itself should be trusted or qualified" but dismisses this as a limitation. For TQL-3 and above, DO-330 *requires* tool chain qualification. You need evidence that the Lean4 type checker, the Lake build system, and the Lean4 runtime are themselves correct. This is a massive qualification effort that the paper ignores.

3. **Refinement gap is certification-critical.** DO-330 §6.3.6 (Tool Integration) requires evidence that the *as-built* tool matches the *as-specified* tool. Without a formal refinement proof from the Lean4 model to the Rust implementation, you have a proof of a model, not a proof of the tool. This is the difference between TQL-4 (model proved correct) and TQL-2 (tool proved correct).

4. **Float environment assumptions.** The paper assumes "correct float arithmetic, which depends on hardware." DO-330 requires you to document, justify, and validate *all* environment assumptions. The IEEE 754 compliance of the target platform must be demonstrated, not assumed.

5. **The paper claims TQL-3 or TQL-2 is needed.** For a constraint checker that is the "last line of defense" in safety-critical systems, this should arguably be **TQL-1** (tool output is not verified by subsequent processes). The paper underestimates the qualification level.

## 10. Overall Verdict: **REVISE (Major)**

This paper presents a sound *strategy document* for a feasible verification effort, but it is not a completed verification and has several technical gaps that must be addressed before publication at a formal methods venue.

**What's needed for acceptance:**
1. Fix the Lean4 type signatures (`stack : Float` → proper vector type, fix `Steps` relation, define `ExecutionTrace`)
2. Define the `safe` predicate formally
3. Provide the float axiomatization strategy (even if just "we axiomatize Float as a totally ordered field minus NaN/Inf and prove the theorems under this assumption")
4. Complete at least one of the three theorems in full Lean4 (termination is the obvious choice — it's the easiest and demonstrates the approach works)
5. Scale back DO-330 claims to what the proof actually supports

**The core insight — that the mini VM's design-for-verification properties make formal proof tractable — is valuable and correct.** The paper needs more rigor in its own formalization to be convincing at CAV/ITP.

---

*Review completed: 2026-05-03*
*Forgemaster ⚒️ — Precision is not a luxury, it's a requirement.*
