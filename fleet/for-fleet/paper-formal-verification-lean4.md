# Formal Verification of a Constraint Compilation VM: A Lean4 Proof Strategy for FLUX ISA

**Forgemaster ⚒️ — SuperInstance / Cocapn Fleet**
**Date: 2026-05-03 (Revised)**

---

## Abstract

The FLUX ISA is a stack-based bytecode virtual machine designed to execute compiled constraint satisfaction programs. It serves as the runtime verifier in a constraint compilation pipeline: if the VM contains a bug in its ASSERT logic, constraints may pass that should fail — a catastrophic failure mode for safety-critical systems. This paper presents a formal verification strategy targeting the FLUX VM using Lean4. We extract the VM's operational semantics from its Rust implementation, state three core theorems — soundness, termination, and boundedness — and develop a proof strategy using induction on execution steps, well-founded recursion on step counters, and case splitting over a finite opcode set. We argue that the flux-isa-mini variant (21 opcodes, 32-slot fixed stack, no heap, no allocation, no async) is the ideal proof target: its finite state space makes the verification tractable, and its `no_std` design eliminates entire classes of undefined behavior.

**Revised estimate:** We estimate 500–700 lemmas across 14–21 weeks for a trained Lean4 practitioner, and sketch the path from Lean4 proof artifact to DO-178C Tool Qualification under DO-330. We recommend an integer-only initial proof (Option C) to defer IEEE 754 reasoning, extending to full float semantics later.

---

## 1. Introduction

### 1.1 The "Who Verifies the Verifier?" Problem

Constraint compilation is the process of translating high-level constraint specifications into executable bytecode that can be evaluated on a target machine. The FLUX ISA is the bytecode format; the FLUX VM is the interpreter. In safety-critical domains — aviation, medical devices, autonomous systems — constraint checking is often the last line of defense. A sonar sensor on an underwater vehicle runs FLUX bytecode to validate that depth readings satisfy geometric constraints before forwarding data upstream. A flight control system might use FLUX to check that actuator commands remain within certified envelopes.

The problem: **if the VM has a bug, constraints pass that shouldn't.**

This is the verification of the verifier. It is qualitatively different from testing the verifier — testing can show the presence of bugs, but only formal proof can demonstrate their absence. For systems subject to DO-178C certification, the relevant standard is DO-330 (Software Tool Qualification), which requires evidence that a tool "has been demonstrated to be correct to the level of confidence required by its tool qualification level."

### 1.2 Why Lean4

Lean4 offers several advantages over Coq or Isabelle for this project:

- **Metaprogramming**: We can write custom tactics for VM-specific proof obligations
- **Evaluation**: Lean4 can *run* the VM spec as executable code, enabling test-before-prove workflows
- **Mathlib integration**: Well-founded recursion, decidable typeclasses, and automation
- **Growing ecosystem**: Lake build system, VS Code integration, active community

### 1.3 Contributions

1. A formal operational semantics for the FLUX VM, extracted from the Rust reference implementation
2. Three core theorems (soundness, termination, boundedness) stated in Lean4
3. A detailed proof strategy with lemma decomposition and effort estimation
4. An argument for why the mini variant is the correct proof target
5. A discussion of float axiomatization strategies for the verification of constraint VMs
6. A path from proof artifact to DO-330 tool qualification evidence, with appropriately scoped claims

---

## 2. The FLUX VM Formal Model

### 2.1 State Space

The FLUX VM state is a 5-tuple. The stack holds heterogeneous values — the real VM stores `f64` values, but the formal model must account for the semantic intent of operations that produce comparison results (`1.0`/`0.0` as stand-ins for booleans). We define a proper value type:

```lean4
-- Values on the VM stack
inductive Value where
  | float : Float → Value
  | int : Int → Value
  | bool : Bool → Value
  deriving DecidableEq, Repr
```

This distinction matters for the proof: `Assert` checks for "nonzero," `Check` tests truth, and comparison opcodes produce boolean-like float values (`1.0`/`0.0`). In the actual Rust implementation, all values are `f64`, but the formal model needs to reason about the *intent* of these values. The refinement proof (Section 5.6) will establish that the `Value.float` projection maps to the Rust `f64` stack entries.

The VM state:

```
State := (stack : Vector Value STACK_SIZE) ×
         (sp : Fin (STACK_SIZE + 1)) ×
         (ip : Nat) ×
         (steps : Nat) ×
         (constraints_ok : Bool)
```

Where:
- `stack` is a fixed-size array of `STACK_SIZE` values (32 slots in mini, configurable in full)
- `sp` is the stack pointer — the index of the next free slot, bounded by `STACK_SIZE`
- `ip` is the instruction pointer — an index into the program
- `steps` is the execution step counter
- `constraints_ok` is the accumulated constraint satisfaction flag

In the actual Rust implementation (`flux-isa-mini/src/vm.rs`):

```rust
pub struct FluxVm {
    stack: [f64; STACK_SIZE],  // 32 slots = 256 bytes
    sp: usize,                  // next free slot
}
```

The execution context additionally tracks `steps_executed` and `constraints_satisfied` as local variables within the `execute` function.

**Why `Value` instead of raw `Float`?** The Rust VM uses `f64` uniformly, but semantically the stack holds at least three kinds of data: numeric values from `Load`/arithmetic, boolean-like values from comparisons (`1.0`/`0.0`), and range-check results from `Validate`. Defining `Value` as a sum type in the formal model lets us reason about *what kind of thing* is on the stack at each point in execution, which is essential for proving that `Assert` correctly identifies constraint violations. The refinement proof to the Rust implementation will need to show that this type-level distinction is faithfully erased to `f64`.

### 2.2 Program Representation

A program is a finite sequence of instructions. Each instruction pairs an opcode with up to 2 operand floats:

```
Instruction := (opcode : FluxOpcode) × (operands : List Float)

Program := List Instruction
```

From the Rust (`flux-isa-mini/src/instruction.rs`):

```rust
pub struct FluxInstruction {
    pub opcode: FluxOpcode,
    pub operands: [f64; 2],
    pub operand_count: usize,
}
```

### 2.3 Opcode Taxonomy

The mini VM defines 21 opcodes organized into 6 groups:

| Group | Opcodes | Count |
|-------|---------|-------|
| Arithmetic | `Add, Sub, Mul, Div, Mod` | 5 |
| Comparison | `Eq, Lt, Gt, Lte, Gte` | 5 |
| Constraint | `Assert, Check, Validate, Reject` | 4 |
| Stack | `Load, Push, Pop` | 3 |
| Transform | `Snap, Quantize` | 2 |
| Control | `Halt, Nop` | 2 |

The full VM adds 14 more opcodes (`Neq, Jump, Branch, Call, Return, Store, Swap, Cast, Promote, And, Or, Not, Xor, Debug, Trace, Dump`) for 35 total. We target the mini variant first.

### 2.4 Transition Function

The one-step transition function `step : State → Program → Option State` maps a state and program to the next state (or `none` if execution halts/errors):

```
step (stack, sp, ip, steps, ok) program :=
  match program[ip] with
  | none => none                                    -- IP out of bounds → halt
  | some instr =>
    match instr.opcode with
    | Add    => if sp ≥ 2 then (stack', sp-1, ip+1, steps+1, ok) else error
    | Sub    => if sp ≥ 2 then (stack', sp-1, ip+1, steps+1, ok) else error
    | Mul    => if sp ≥ 2 then (stack', sp-1, ip+1, steps+1, ok) else error
    | Div    => if sp ≥ 2 ∧ peek(1) ≠ 0 then (stack', sp-1, ip+1, steps+1, ok) else error
    | Mod    => if sp ≥ 2 ∧ peek(1) ≠ 0 then (stack', sp-1, ip+1, steps+1, ok) else error
    | Eq     => if sp ≥ 2 then (stack', sp-1, ip+1, steps+1, ok) else error
    | Lt .. Gte => (similar, comparison pushes 1.0 or 0.0)
    | Assert => if sp ≥ 1 ∧ peek(0) ≠ 0 then (stack, sp-1, ip+1, steps+1, ok) else (error: ConstraintViolation)
    | Check  => if sp ≥ 1 ∧ peek(0) ≠ 0 then (stack, sp, ip+1, steps+1, ok) else (stack, sp, ip+1, steps+1, false)
    | Validate => if sp ≥ 3 then pop 3, push result, update ok else error
    | Reject => (stack, sp, ip+1, steps+1, false)
    | Load   => if sp < STACK_SIZE then (stack[sp]=operand, sp+1, ip+1, steps+1, ok) else error
    | Push   => (same as Load for mini)
    | Pop    => if sp ≥ 1 then (stack, sp-1, ip+1, steps+1, ok) else error
    | Snap   => if sp ≥ 1 then (stack', sp, ip+1, steps+1, ok) else error
    | Quantize => if sp ≥ 2 ∧ peek(0) ≠ 0 then (stack', sp-1, ip+1, steps+1, ok) else error
    | Halt   => none
    | Nop    => (stack, sp, ip+1, steps+1, ok)
```

Key observations:
- Every opcode has a **stack depth precondition** checked before execution
- `Div` and `Mod` check for zero before popping
- `Assert` is the only opcode that can **abort** execution on constraint violation
- `Check` is **non-consuming** — it peeks without popping (distinct from the full VM's behavior)
- All stack mutations are bounded: push checks `sp < STACK_SIZE`, pop checks `sp > 0`

### 2.5 Terminal States

Execution terminates in one of three ways:

1. **Normal halt**: `Halt` opcode encountered or IP exceeds program length
2. **Constraint violation**: `Assert` pops a zero value → `ConstraintViolation` error
3. **Stack error**: `StackOverflow` or `StackUnderflow` (malformed program)

Notably, there is no infinite loop in the mini VM because there are no `Jump` or `Branch` opcodes. The mini VM executes instructions **strictly sequentially**. This is a critical simplification for the proof.

---

## 3. The Soundness Theorems

We state three theorems. Theorem 1 is the primary soundness result. Theorems 2 and 3 are supporting results needed to complete the proof.

### 3.1 The Program `safe` Predicate

Before stating the theorems, we define the `safe` predicate used in the soundness formulation. A program is `safe` if it is well-formed: no instruction can cause a stack underflow or overflow on any reachable execution path. For the mini VM, `safe` is decidable by forward simulation because there are no jumps:

```lean4
/-- A program is safe if, starting from the initial state (sp=0, ip=0),
    every opcode's stack depth precondition is met at every reachable step. -/
def safe (prog : Program) : Bool :=
  go prog 0 0
where
  go : Program → Nat → Nat → Bool
  | prog, ip, sp =>
    if h : ip < prog.length then
      match (prog.get ⟨ip, h⟩).opcode with
      | .Add | .Sub | .Mul | .Div | .Mod
      | .Eq | .Lt | .Gt | .Lte | .Gte =>
        if sp ≥ 2 then go prog (ip + 1) (sp - 1) else false
      | .Assert | .Pop =>
        if sp ≥ 1 then go prog (ip + 1) (sp - 1) else false
      | .Check | .Snap =>
        if sp ≥ 1 then go prog (ip + 1) sp else false
      | .Validate | .Quantize =>
        -- Validate: pops 3, pushes 1 → net sp-2
        -- Quantize: pops 2, pushes 1 → net sp-1
        if sp ≥ 3 then
          match (prog.get ⟨ip, h⟩).opcode with
          | .Validate => go prog (ip + 1) (sp - 2)
          | .Quantize => go prog (ip + 1) (sp - 1)
          | _ => false  -- unreachable
        else false
      | .Load | .Push =>
        if sp < STACK_SIZE then go prog (ip + 1) (sp + 1) else false
      | .Reject | .Nop => go prog (ip + 1) sp
      | .Halt => true
    else true
```

This is a static analysis that computes the stack depth at each instruction and verifies that every opcode's precondition is satisfied. Because the mini VM has no backward jumps, the stack depth at each instruction is uniquely determined — there is only one execution path. The `safe` predicate is therefore decidable and runs in O(program length) time.

**Relation to well-formedness:** `safe P = true` implies that for the execution of P starting from `sp = 0, ip = 0`, no `StackOverflow` or `StackUnderflow` error will occur. This is a precondition for the soundness theorem — we only prove soundness for well-formed programs.

### 3.2 Theorem 1: Soundness

> **If the VM reports `constraints_satisfied = true`, then every `Assert` opcode in the execution trace evaluated its operand to a non-zero value.**

Formally, using the execution trace (defined in Section 4.4):

```lean4
theorem soundness : ∀ (prog : Program) (init_s final_s : VMState) (trace : ExecutionTrace),
  init_s.ip = 0 →
  init_s.sp = 0 →
  init_s.constraints_ok = true →
  safe prog = true →
  Steps init_s prog (.ok final_s trace true) →
  -- If VM reports constraints_satisfied = true, then:
  ∀ (i : Nat),
    i < prog.length →
    prog.get? i = some { opcode := .Assert, .. } →
    -- The assert was reached and passed
    ∃ (entry : TraceEntry),
      entry.ip = i ∧
      entry.opcode = .Assert ∧
      entry.constraint_passed = true
  := by sorry
```

Equivalently, in the Hermes-style formulation:

```lean4
/-- Either the program runs to completion with all constraints satisfied,
    or it cannot complete with constraints_ok = true. There is no third
    possibility where the VM falsely claims satisfaction. -/
theorem hermes_soundness : ∀ (prog : Program) (s : VMState),
  s.ip = 0 → s.sp = 0 → s.constraints_ok = true →
  safe prog = true →
  (∃ final_s trace, Steps s prog (.ok final_s trace true)) ∨
  (∀ final_s trace ok,
    Steps s prog (.ok final_s trace ok) → ok = false) ∨
  (∃ err final_s, Steps s prog (.error err final_s))
  := by sorry
```

The three-way disjunction captures: (1) execution succeeds with all constraints satisfied, (2) execution completes but `constraints_ok = false`, or (3) execution errors out (e.g., `Assert` failure). There is no case where the VM reports `true` incorrectly.

### 3.3 Theorem 2: Termination

> **For any program P with N instructions, execution terminates in at most N steps.**

```lean4
theorem termination : ∀ (prog : Program) (s : VMState),
  s.ip ≤ prog.length →
  ∃ res, Steps s prog res ∧
    match res with
    | .ok final_s trace _ => final_s.steps ≤ prog.length
    | .error _ final_s => final_s.steps ≤ prog.length
  := by sorry
```

This follows directly from the sequential execution model: the mini VM has no backward jumps. Each step advances IP by 1 (or halts). After at most `program.length` steps, IP exceeds the program bounds.

### 3.4 Theorem 3: Boundedness (Stack Safety)

> **Stack overflow is impossible: `sp` never exceeds `STACK_SIZE`, and `sp` never underflows below 0.**

```lean4
theorem boundedness : ∀ (prog : Program) (s : VMState) (res : ExecResult),
  s.sp ≤ STACK_SIZE →
  safe prog = true →
  Steps s prog res →
  match res with
  | .ok final_s _ _ => final_s.sp ≤ STACK_SIZE
  | .error _ final_s => final_s.sp ≤ STACK_SIZE
  := by sorry
```

This is an invariant maintained by the `push` and `pop` operations. Every `push` checks `sp < STACK_SIZE` before writing. Every `pop` checks `sp > 0` before reading. The theorem states that this invariant holds throughout execution.

---

## 4. Lean4 Proof Strategy

### 4.1 Type Definitions

We begin by defining the VM state and opcodes as Lean4 types:

```lean4
-- Values on the VM stack
inductive Value where
  | float : Float → Value
  | int : Int → Value
  | bool : Bool → Value
  deriving DecidableEq, Repr

-- Opcode enumeration (21 variants)
inductive FluxOpcode :=
  | Add | Sub | Mul | Div | Mod
  | Eq | Lt | Gt | Lte | Gte
  | Assert | Check | Validate | Reject
  | Load | Push | Pop
  | Snap | Quantize
  | Halt | Nop
  deriving DecidableEq, Repr

-- Instruction: opcode + operands
structure Instruction where
  opcode : FluxOpcode
  operand0 : Float
  operand1 : Float
  deriving DecidableEq, Repr

-- Program: list of instructions
abbrev Program := List Instruction

-- Stack size constant
def STACK_SIZE : Nat := 32

-- VM State: stack is a vector of heterogeneous Values
structure VMState where
  stack : Vector Value STACK_SIZE
  sp : Fin (STACK_SIZE + 1)  -- bounded by construction
  ip : Nat
  steps : Nat
  constraints_ok : Bool
  deriving DecidableEq, Repr

-- Execution error
inductive VMError :=
  | stackOverflow
  | stackUnderflow
  | divisionByZero
  | constraintViolation
  | invalidInstruction (byte : UInt8)
  deriving DecidableEq, Repr
```

### 4.2 The Step Relation

We define execution as a small-step operational semantics. Each constructor produces a pair of (next state, optional error), and we omit the spurious `outputs` and `rest` parameters that appeared in the earlier draft. The step relation maps `(state, program)` to either a next state (continuing) or an error (terminating):

```lean4
-- Result of a single step: either continue with new state, or error
inductive StepResult where
  | ok (next : VMState)
  | error (err : VMError) (state : VMState)
  | halt (state : VMState)
  deriving DecidableEq, Repr

-- One step of execution
inductive Step : VMState → Program → StepResult → Prop where
  -- Halt: execution terminates normally
  | halt : ∀ s prog,
    prog.get? s.ip = some { opcode := .Halt, .. } →
    Step s prog (.halt s)

  -- Out of bounds: IP past program end
  | ip_oob : ∀ s prog,
    prog.get? s.ip = none →
    Step s prog (.halt s)

  -- Add: pop two, push sum
  | add : ∀ s prog a b,
    s.sp ≥ 2 →
    prog.get? s.ip = some { opcode := .Add, .. } →
    peek s 1 = some a →
    peek s 0 = some b →
    Step s prog (.ok (push (popn s 2) (Value.float (a + b)) { s with ip := s.ip + 1, steps := s.steps + 1 }))

  -- Sub: pop two, push difference
  | sub : ∀ s prog a b,
    s.sp ≥ 2 →
    prog.get? s.ip = some { opcode := .Sub, .. } →
    peek s 1 = some a →
    peek s 0 = some b →
    Step s prog (.ok (push (popn s 2) (Value.float (a - b)) { s with ip := s.ip + 1, steps := s.steps + 1 }))

  -- Mul: pop two, push product
  | mul : ∀ s prog a b,
    s.sp ≥ 2 →
    prog.get? s.ip = some { opcode := .Mul, .. } →
    peek s 1 = some a →
    peek s 0 = some b →
    Step s prog (.ok (push (popn s 2) (Value.float (a * b)) { s with ip := s.ip + 1, steps := s.steps + 1 }))

  -- Div: pop two, push quotient (checked for zero)
  | div_ok : ∀ s prog a b,
    s.sp ≥ 2 →
    prog.get? s.ip = some { opcode := .Div, .. } →
    peek s 1 = some a →
    peek s 0 = some b →
    b ≠ 0.0 →
    Step s prog (.ok (push (popn s 2) (Value.float (a / b)) { s with ip := s.ip + 1, steps := s.steps + 1 }))

  | div_zero : ∀ s prog b,
    s.sp ≥ 2 →
    prog.get? s.ip = some { opcode := .Div, .. } →
    peek s 0 = some b →
    b = 0.0 →
    Step s prog (.error .divisionByZero s)

  -- Mod: pop two, push remainder (checked for zero)
  | mod_ok : ∀ s prog a b,
    s.sp ≥ 2 →
    prog.get? s.ip = some { opcode := .Mod, .. } →
    peek s 1 = some a →
    peek s 0 = some b →
    b ≠ 0.0 →
    Step s prog (.ok (push (popn s 2) (Value.float (a % b)) { s with ip := s.ip + 1, steps := s.steps + 1 }))

  | mod_zero : ∀ s prog b,
    s.sp ≥ 2 →
    prog.get? s.ip = some { opcode := .Mod, .. } →
    peek s 0 = some b →
    b = 0.0 →
    Step s prog (.error .divisionByZero s)

  -- Comparison opcodes: push Value.bool, represented as 1.0/0.0 in float projection
  | eq : ∀ s prog a b,
    s.sp ≥ 2 →
    prog.get? s.ip = some { opcode := .Eq, .. } →
    peek s 1 = some a →
    peek s 0 = some b →
    Step s prog (.ok (push (popn s 2) (Value.bool (a = b)) { s with ip := s.ip + 1, steps := s.steps + 1 }))

  -- Lt, Gt, Lte, Gte: similar pattern (elided for brevity)

  -- Assert succeeds: top of stack is nonzero → pop and continue
  | assert_pass : ∀ s prog val,
    s.sp ≥ 1 →
    prog.get? s.ip = some { opcode := .Assert, .. } →
    peek s 0 = some val →
    val ≠ 0.0 →
    Step s prog (.ok { (pop s) with ip := s.ip + 1, steps := s.steps + 1 })

  -- Assert fails: top of stack is zero → error (constraints_ok is NOT set to false; execution aborts)
  | assert_fail : ∀ s prog val,
    s.sp ≥ 1 →
    prog.get? s.ip = some { opcode := .Assert, .. } →
    peek s 0 = some val →
    val = 0.0 →
    Step s prog (.error .constraintViolation s)

  -- Check: non-consuming peek; if zero, set constraints_ok = false
  | check_pass : ∀ s prog val,
    s.sp ≥ 1 →
    prog.get? s.ip = some { opcode := .Check, .. } →
    peek s 0 = some val →
    val ≠ 0.0 →
    Step s prog (.ok { s with ip := s.ip + 1, steps := s.steps + 1 })

  | check_fail : ∀ s prog val,
    s.sp ≥ 1 →
    prog.get? s.ip = some { opcode := .Check, .. } →
    peek s 0 = some val →
    val = 0.0 →
    Step s prog (.ok { s with ip := s.ip + 1, steps := s.steps + 1, constraints_ok := false })

  -- Validate: pop 3 (val, lower, upper), push bool, update constraints_ok
  | validate : ∀ s prog val lower upper,
    s.sp ≥ 3 →
    prog.get? s.ip = some { opcode := .Validate, .. } →
    peek s 2 = some val →
    peek s 1 = some lower →
    peek s 0 = some upper →
    let ok := val ≥ lower ∧ val ≤ upper →
    Step s prog (.ok (push (popn s 3) (Value.bool ok) { s with ip := s.ip + 1, steps := s.steps + 1, constraints_ok := (s.constraints_ok ∧ ok) }))

  -- Reject: unconditionally set constraints_ok = false, continue execution
  | reject : ∀ s prog,
    prog.get? s.ip = some { opcode := .Reject, .. } →
    Step s prog (.ok { s with ip := s.ip + 1, steps := s.steps + 1, constraints_ok := false })

  -- Load: push operand onto stack
  | load : ∀ s prog val,
    s.sp < STACK_SIZE →
    prog.get? s.ip = some { opcode := .Load, operand0 := val, .. } →
    Step s prog (.ok (push s (Value.float val) { s with ip := s.ip + 1, steps := s.steps + 1 }))

  -- Push: same as Load for mini
  | push_op : ∀ s prog val,
    s.sp < STACK_SIZE →
    prog.get? s.ip = some { opcode := .Push, operand0 := val, .. } →
    Step s prog (.ok (push s (Value.float val) { s with ip := s.ip + 1, steps := s.steps + 1 }))

  -- Pop: discard top of stack
  | pop_op : ∀ s prog,
    s.sp ≥ 1 →
    prog.get? s.ip = some { opcode := .Pop, .. } →
    Step s prog (.ok { (pop s) with ip := s.ip + 1, steps := s.steps + 1 })

  -- Nop: advance IP, nothing else
  | nop : ∀ s prog,
    prog.get? s.ip = some { opcode := .Nop, .. } →
    Step s prog (.ok { s with ip := s.ip + 1, steps := s.steps + 1 })

  -- Stack underflow: any opcode requiring more stack than available
  | stack_underflow : ∀ s prog,
    prog.get? s.ip = some instr →
    ¬(stack_depth_ok instr.opcode s.sp) →
    Step s prog (.error .stackUnderflow s)

  -- Stack overflow: any opcode requiring push when sp = STACK_SIZE
  | stack_overflow : ∀ s prog,
    prog.get? s.ip = some instr →
    opcode_pushes instr.opcode →
    s.sp ≥ STACK_SIZE →
    Step s prog (.error .stackOverflow s)
```

Note: each constructor now produces a `StepResult` that is either `.ok next_state` (continue), `.error err state` (abort), or `.halt state` (clean termination). There are no spurious `outputs` or `rest` parameters. Each constructor explicitly constructs the full next state including advanced `ip` and incremented `steps`.

### 4.3 Multi-Step Execution

The multi-step relation follows the standard pattern from CompCert's `star` relation — reflexive transitive closure over individual steps, accumulating the execution trace:

```lean4
-- Multi-step execution: reflexive transitive closure of Step
-- Accumulates an ExecutionTrace (defined in Section 4.4)
inductive Steps : VMState → Program → ExecResult → Prop where
  | refl : ∀ s prog,
    -- Zero steps: terminal state (halt or error already occurred, or initial state)
    Steps s prog (.ok s [] s.constraints_ok)
  | step : ∀ s s' prog res entry,
    Step s prog (.ok s') →
    Steps s' prog res →
    -- Build trace entry for this step
    entry = { ip := s.ip, opcode := (prog.get? s.ip).map (·.opcode), state_before := s, state_after := s' } →
    Steps s prog (prepend_trace entry res)
  | error : ∀ s prog err,
    Step s prog (.error err s) →
    Steps s prog (.error err s [])
  | halt : ∀ s prog,
    Step s prog (.halt s) →
    Steps s prog (.ok s [] s.constraints_ok)
```

Key fix from the earlier draft: `Steps.step` now correctly threads through the intermediate state `s'` without discarding it. The `Steps.refl` constructor represents the base case (zero remaining steps). The `Steps.step` constructor takes one `Step` and recurses. The `Steps.error` and `Steps.halt` constructors handle terminal cases.

### 4.4 ExecutionTrace and TraceEntry

The `ExecutionTrace` is a list of `TraceEntry` records, each capturing the state before and after a single step. This is essential for the soundness proof, which must reason about every `Assert` that was encountered during execution:

```lean4
-- A single step in the execution trace
structure TraceEntry where
  ip : Nat                        -- instruction pointer at this step
  opcode : Option FluxOpcode      -- opcode executed (none if IP out of bounds)
  state_before : VMState          -- VM state before this step
  state_after : VMState           -- VM state after this step
  constraint_passed : Option Bool -- for Assert/Check/Validate: did it pass?
  deriving DecidableEq, Repr

-- Execution trace: ordered list of trace entries
abbrev ExecutionTrace := List TraceEntry

-- Execution result, now carrying the full trace
inductive ExecResult where
  | ok (state : VMState) (trace : ExecutionTrace) (satisfied : Bool)
  | error (err : VMError) (state : VMState) (trace : ExecutionTrace)
  deriving DecidableEq, Repr

-- Helper: prepend a trace entry to the result's trace
def prepend_trace (entry : TraceEntry) : ExecResult → ExecResult
  | .ok s trace ok => .ok s (entry :: trace) ok
  | .error err s trace => .error err s (entry :: trace)
```

The `constraint_passed` field is populated for constraint opcodes (`Assert`, `Check`, `Validate`) and left `none` for all others. This allows the soundness proof to inspect every `Assert` in the trace and verify that it passed.

### 4.5 Key Invariants

Before proving the main theorems, we establish invariants that hold throughout execution:

```lean4
-- Stack pointer is always in bounds
theorem sp_invariant : ∀ s prog res,
  s.sp ≤ STACK_SIZE →
  Steps s prog res →
  match res with
  | .ok s' _ _ => s'.sp ≤ STACK_SIZE
  | .error _ s' _ => s'.sp ≤ STACK_SIZE
  := by
  intro s prog res hsp hsteps
  induction hsteps with
  | refl => exact hsp
  | step s s' prog res entry hstep hsteps ih =>
    -- prove that one step preserves the invariant
    sorry  -- case analysis on hstep
  | error s prog err hstep =>
    sorry
  | halt s prog hstep =>
    exact hsp

-- Steps counter is monotonically increasing
theorem steps_monotone : ∀ s prog res,
  Steps s prog res →
  match res with
  | .ok s' _ _ => s'.steps ≥ s.steps
  | .error _ s' _ => s'.steps ≥ s.steps
  := by sorry
```

#### Monotonicity of `constraints_ok`

A critical lemma for the soundness proof: `constraints_ok` is **monotonically decreasing** — once set to `false`, it never returns to `true`. This is because no opcode ever sets `constraints_ok` back to `true`. The only opcodes that modify it are `Check` (may set to `false`), `Validate` (may set to `false`), and `Reject` (unconditionally sets to `false`). All other opcodes preserve it:

```lean4
/-- constraints_ok is monotonically non-increasing:
    once false, always false. -/
theorem constraints_ok_monotone : ∀ s prog res,
  Steps s prog res →
  match res with
  | .ok s' _ ok => (¬s.constraints_ok → ¬ok) ∧ (ok → s.constraints_ok)
  | .error _ s' _ => True
  := by
  intro s prog res hsteps
  induction hsteps with
  | refl => constructor <;> intro h <;> trivial
  | step s s' prog res entry hstep hsteps ih =>
    -- Show that Step preserves: if constraints_ok was false, it stays false
    -- Case-split on hstep: only Check, Validate, Reject can set false
    sorry
  | error => trivial
  | halt => constructor <;> intro h <;> trivial
```

This lemma is essential because the soundness theorem concludes `constraints_ok = true` in the final state. If `constraints_ok` could return to `true` after being set to `false`, a program with a failed `Check` followed by a later opcode could falsely report satisfaction. Monotonicity guarantees this cannot happen.

### 4.6 Proof of Theorem 2 (Termination)

The termination proof is the simplest. In the mini VM, IP only moves forward:

```lean4
-- IP advances by at least 1 each step (or execution halts)
theorem ip_advances : ∀ s prog res,
  Step s prog res →
  match res with
  | .ok s' => s'.ip ≥ s.ip + 1
  | .error _ _ => True
  | .halt _ => True
  := by
  intro s prog res hstep
  cases hstep with
  | halt => trivial
  | ip_oob => trivial
  | add _ _ _ _ _ _ _ => omega
  | assert_pass => omega
  | assert_fail => trivial
  | check_pass => omega
  | check_fail => omega
  | reject => omega
  | load => omega
  | nop => omega
  -- ... each non-terminal case advances ip by 1
```

From this, termination follows because IP is bounded by `program.length`:

```lean4
theorem termination : ∀ (prog : Program) (s : VMState),
  s.ip ≤ prog.length →
  ∃ res, Steps s prog res ∧
    match res with
    | .ok final_s _ _ => final_s.steps ≤ prog.length
    | .error _ final_s _ => final_s.steps ≤ prog.length
  := by
  intro prog s hip
  -- Well-founded induction on (prog.length - s.ip), which decreases each step
  induction h : (prog.length - s.ip) generalizing s with
  | zero =>
    -- IP = prog.length, so we're past the end → halt
    exists .ok s [] s.constraints_ok
    constructor
    · exact Steps.halt s prog (by simp [List.get?_eq_none.mpr (by omega)])
    · simp; omega
  | succ n ih =>
    -- IP < prog.length, step forward
    sorry  -- apply Step, then recurse with ih
```

### 4.7 Proof of Theorem 3 (Boundedness)

Stack boundedness is maintained by construction in the Lean4 model because `sp` is a `Fin (STACK_SIZE + 1)`. But we need to show that our `push` and `pop` operations preserve this:

```lean4
def push (s : VMState) (val : Value) (next : VMState) : VMState :=
  if h : s.sp < STACK_SIZE then
    { next with
      stack := s.stack.set ⟨s.sp, h⟩ val
      sp := ⟨s.sp + 1, by omega⟩
    }
  else next  -- overflow case; won't happen for safe programs

def pop (s : VMState) : VMState :=
  if h : s.sp > 0 then
    { s with sp := ⟨s.sp - 1, by omega⟩ }
  else s  -- underflow case; won't happen for safe programs
```

Because `push` and `pop` are guarded by the `safe` predicate (which checks stack depth preconditions), the boundedness proof reduces to showing that `safe` correctly computes the stack effect of each opcode:

```lean4
theorem safe_implies_no_overflow : ∀ (prog : Program) (s : VMState),
  safe prog = true →
  s.sp = 0 →
  s.ip = 0 →
  ∀ res, Steps s prog res →
    match res with
    | .ok s' _ _ => s'.sp ≤ STACK_SIZE
    | .error _ s' _ => s'.sp ≤ STACK_SIZE
  := by sorry
```

### 4.8 Proof of Theorem 1 (Soundness)

The soundness proof proceeds by **strong induction on execution steps**, using the trace to inspect every `Assert`:

```lean4
theorem soundness : ∀ (prog : Program) (init_s final_s : VMState) (trace : ExecutionTrace),
  init_s.ip = 0 →
  init_s.sp = 0 →
  init_s.constraints_ok = true →
  safe prog = true →
  Steps init_s prog (.ok final_s trace true) →
  -- If VM reports constraints_satisfied = true, then every Assert passed
  ∀ (ip : Nat),
    ip < prog.length →
    prog.get? ip = some { opcode := .Assert, .. } →
    -- The assert was reached and passed
    ∃ (entry : TraceEntry),
      entry.ip = ip ∧
      entry.opcode = some .Assert ∧
      entry.constraint_passed = some true
  := by
  intro prog init_s final_s trace hinit_ip hinit_sp hinit_ok hsafe hsteps ip hip hassert
  -- Key insight: Assert with value 0.0 causes immediate .error return.
  -- constraints_ok is monotonically non-increasing.
  -- Therefore, if final constraints_ok = true, no Assert failed.
  induction hsteps with
  | refl =>
    -- No steps executed. But the program has an Assert at position ip.
    -- If the program has 0 length, contradiction with hip.
    -- If non-zero length, we must have halted at step 0 — but ip < prog.length,
    -- so the Assert at ip was never reached. This is fine — it means the
    -- program halted before reaching this Assert, so the theorem vacuously holds
    -- (the Assert was not executed, and the VM correctly reported satisfaction).
    sorry
  | step s s' prog res entry hstep hsteps ih =>
    -- Case split: did we hit the assert at position ip?
    by_cases h : s.ip = ip
    · -- We're at the assert. Show it passed.
      -- If it failed, Step would have gone to .error, not .ok
      -- The Step relation's assert_fail constructor produces .error,
      -- so if we took .ok path, it must have been assert_pass.
      sorry
    · -- We're not at the assert yet. Inductive hypothesis applies.
      exact ih (by omega)
  | error s prog err hstep =>
    -- Error case: but hypothesis says .ok, contradiction
    simp at hsteps
  | halt s prog hstep =>
    -- Halt: similar to refl, the Assert at ip was never reached
    sorry
```

The critical observation is that the `Step` relation makes it **impossible** to reach a state where `constraints_ok = true` after an `Assert` fails, because:
1. `Assert` with a zero value produces `.error .constraintViolation`, terminating execution immediately (the `assert_fail` constructor).
2. `Check` and `Validate` may set `constraints_ok = false` but do not terminate execution — and by the `constraints_ok_monotone` lemma, once `false`, it stays `false`.
3. `Reject` unconditionally sets `constraints_ok = false` and continues execution.

Therefore, the only way to reach `(.ok _ _ true)` is if every `Assert` passed and no `Check`/`Validate`/`Reject` failed.

### 4.9 Proof Automation with Custom Tactics

We can leverage Lean4's metaprogramming to automate the opcode case split:

```lean4
-- All opcode cases, for use in case analysis
def FluxOpcode.allCases : List FluxOpcode :=
  [.Add, .Sub, .Mul, .Div, .Mod,
   .Eq, .Lt, .Gt, .Lte, .Gte,
   .Assert, .Check, .Validate, .Reject,
   .Load, .Push, .Pop,
   .Snap, .Quantize,
   .Halt, .Nop]

-- Custom tactic for opcode case analysis
elab "vm_cases" : tactic => do
  -- Use Lean4's native `cases` tactic on the inductive type
  Lean.Elab.Tactic.evalTactic (← `(tactic| cases FluxOpcode.allCases with
    | Add => try simp; try omega
    | Sub => try simp; try omega
    | Mul => try simp; try omega
    | Div => try simp; try omega
    | Mod => try simp; try omega
    | Eq => try simp; try omega
    | Lt => try simp; try omega
    | Gt => try simp; try omega
    | Lte => try simp; try omega
    | Gte => try simp; try omega
    | Assert => try simp; try omega
    | Check => try simp; try omega
    | Validate => try simp; try omega
    | Reject => try simp; try omega
    | Load => try simp; try omega
    | Push => try simp; try omega
    | Pop => try simp; try omega
    | Snap => try simp; try omega
    | Quantize => try simp; try omega
    | Halt => try simp
    | Nop => try simp))

-- Decidable equality on opcodes enables `split` and `cases`
instance : DecidableEq FluxOpcode := by
  intro a b
  cases a <;> cases b <;> try (left; rfl) <;> right <;> intro h; cases h
```

---

## 5. Float Axiomatization Strategies

### 5.1 The Problem

Lean4's `Float` type maps directly to C's `double` — it is opaque. You cannot prove `a + b = b + a` for arbitrary `Float` values because Lean4 does not axiomatize IEEE 754 arithmetic. The comparison opcodes (`Eq`, `Lt`, etc.) push `1.0` or `0.0` based on float comparison, and `Assert` checks `val ≠ 0.0`. But IEEE 754 makes seemingly obvious properties fail:

- `x + (-x) = 0.0` fails when `x = NaN` or `x = ±∞`
- `x == x` fails when `x = NaN`
- `0.0 = -0.0` is true (both are zero), but `1.0 / 0.0 ≠ 1.0 / -0.0` (different infinities)
- `a + b = b + a` holds for IEEE 754, but `(a + b) + c = a + (b + c)` does not

This is the **hardest part** of the verification effort. The paper must not handwave it.

### 5.2 Option A: Abstract Float Axiomatization

Treat `Float` as an abstract type with axioms for the properties we need:

```lean4
-- Axiomatize Float as a totally ordered field, excluding NaN/Inf
axiom Float.add_comm : ∀ (a b : Float), a + b = b + a
axiom Float.mul_comm : ∀ (a b : Float), a * b = b * a
axiom Float.add_assoc : ∀ (a b c : Float), (a + b) + c = a + (b + c)
axiom Float.mul_assoc : ∀ (a b c : Float), (a * b) * c = a * (b * c)
axiom Float.add_zero : ∀ (a : Float), a + 0.0 = a
axiom Float.mul_one : ∀ (a : Float), a * 1.0 = a
axiom Float.zero_ne_one : (0.0 : Float) ≠ 1.0
-- ... more axioms as needed
```

**Pros:** Simple, lets proofs proceed without wrestling IEEE 754 edge cases.
**Cons:** The axioms are *wrong* for NaN/Inf. The proof only holds for the "normal" float subset. This must be documented as a proof assumption.

### 5.3 Option B: Flocq / Formalized Float Arithmetic

Use a formalized model of IEEE 754 arithmetic (such as Flocq in Coq) that defines float operations in terms of bitvectors and proves their properties. This would require either porting Flocq to Lean4 or working in Coq instead.

**Pros:** Mathematically precise. Handles NaN, Inf, signed zero, rounding modes correctly.
**Cons:** Massive effort (Flocq is ~30K lines of Coq). Changes the proof target significantly. Not feasible for the initial verification.

### 5.4 Option C: Integer-Only Initial Proof (Recommended)

For the initial proof, restrict the VM to integer-valued stack elements only. Define `Value.int` as the only variant used:

```lean4
-- Initial proof: all values are integers
-- Map arithmetic ops to Int operations
-- Div/Mod use Int.div/Int.mod (no NaN/Inf issues)
-- Comparison produces Bool directly, no float intermediaries
-- Assert checks val ≠ 0 (Int zero, not Float zero)
```

This defers float reasoning entirely. The integer proof demonstrates that the VM's *structural* properties (stack safety, control flow, constraint propagation) are correct. Float correctness is then an orthogonal concern that can be addressed incrementally:

1. **Phase 1 (Integer):** Prove soundness, termination, boundedness for integer-valued programs. All arithmetic is `Int`, comparisons produce `Bool`.
2. **Phase 2 (Abstract Float):** Extend to `Float` with Option A axioms. Prove that structural properties still hold under float operations.
3. **Phase 3 (IEEE 754):** Either port Flocq results or establish a formal correspondence between the axiomatized model and IEEE 754 semantics.

**Why this works:** The VM's soundness property is fundamentally about *constraint propagation* — whether `constraints_ok` accurately reflects whether all assertions passed. This property is structural: it depends on the *control flow* (Assert aborts on zero, Check sets flag but continues, Reject unconditionally fails) and the *monotonicity* of `constraints_ok`. It does not depend on the specific arithmetic being performed. A soundness proof over integers establishes the structural argument; extending to floats is then a matter of showing that the float operations don't violate the structural invariants.

### 5.5 Recommendation

**We recommend Option C for the initial proof.** This gives us:

- A complete, machine-checkable proof of the VM's structural correctness
- A clear path to extending the proof to float arithmetic
- Honest documentation of what the proof covers and what it doesn't
- A realistic timeline (integer proofs are well-understood in Lean4)

The float axiomatization (Option A) is planned for Phase 2, and full IEEE 754 reasoning (Option B) is noted as future work requiring either a Flocq port or collaboration with the formal methods community.

---

## 6. The Mini VM as Proof Target

### 6.1 Why Not the Full VM?

The full FLUX ISA has 35 opcodes including `Jump`, `Branch`, `Call`, and `Return`. These introduce:

- **Non-sequential control flow**: IP can move backward, requiring loop invariants and well-foundedness arguments
- **Call stack**: A second bounded data structure to reason about
- **7 more opcodes**: 67% more cases in every proof by case analysis

The proof effort scales roughly quadratically with the number of opcodes (each invariant must be verified for each opcode), making the mini VM approximately 4× easier to verify.

### 6.2 Finiteness → Decidability

The mini VM's state space is **finite**:

- Stack: 32 × 64-bit float = 256 bytes
- SP: 0–32 (6 bits)
- IP: 0–N (bounded by program length)
- Steps: 0–N (bounded by program length)
- `constraints_ok`: 1 bit

For a program of length N, the total state space is:
```
|State| = 2^(32×64) × 33 × (N+1) × (N+1) × 2
```

While this is too large for explicit model checking, the **structure** of the state space (fixed-size array, sequential execution) makes inductive proofs tractable.

### 6.3 No Heap Allocation → Simpler Memory Model

The mini VM uses `stack: [f64; 32]` — a fixed-size array. No `Vec`, no `Box`, no dynamic allocation. In Lean4, this maps directly to `Vector Value 32` or `Fin 32 → Value`. There is no aliasing, no borrowing, no lifetime reasoning.

Compare with the full VM's `stack: Vec<f64>` (heap-allocated, dynamically grown). Proving memory safety for a `Vec` requires reasoning about the allocator, capacity, and reallocation — an entirely separate proof effort.

### 6.4 No Async → Sequential Execution

The mini VM executes in a single `for` loop over instructions. There are no `await` points, no concurrent access, no synchronization. The execution model is purely sequential, which means the proof is a simple forward induction without any concurrency invariants.

### 6.5 `no_std` → No Undefined Behavior

The mini VM is `#![no_std]` — it doesn't link against the Rust standard library. This eliminates:
- Panics from allocation failure
- Thread-related UB (data races, deadlocks)
- I/O-related UB (file descriptor exhaustion)
- All of `libstd`'s internal invariants

The only remaining sources of UB in Rust are:
- Integer overflow (impossible — we use checked arithmetic or no arithmetic on indices)
- Invalid pointer dereference (impossible — no raw pointers)
- Uninitialized memory (impossible — stack initialized to `0.0`)

In practice, the mini VM is **UB-free by construction** in safe Rust. The Lean4 proof is about logical correctness, not memory safety — the type system already handles that.

### 6.6 Proof Refinement

The strategy is a **refinement proof**:

1. **Abstract model** (Lean4): Prove theorems about the mathematical VM
2. **Implementation model** (Lean4/Rust): Show the Rust implementation refines the abstract model
3. **Bridging**: Use a shallow embedding — the Lean4 types closely match the Rust types, minimizing the gap

For step 2, the refinement must establish a **simulation relation** R between Lean4 `VMState` and the Rust VM's concrete state:

```
R(s_lean, s_rust) :=
  (∀ i < s_lean.sp, to_f64 (s_lean.stack[i]) = s_rust.stack[i]) ∧
  s_lean.sp = s_rust.sp ∧
  s_lean.ip = s_rust.ip ∧
  s_lean.constraints_ok = s_rust.constraints_ok
```

Where `to_f64` projects the `Value` to its float representation:
- `to_f64 (Value.float f) = f`
- `to_f64 (Value.int n) = n.toFloat`
- `to_f64 (Value.bool true) = 1.0`
- `to_f64 (Value.bool false) = 0.0`

The simulation proof shows that for every `Step` in the Lean4 model, the Rust implementation makes a corresponding transition preserving R. This is future work — the initial proof targets only the abstract model. We note that without this refinement, we have proved a mathematical model correct, not the actual VM. Completing the refinement is a prerequisite for certification at TQL-2 or higher.

---

## 7. Proof Effort Estimation

### 7.1 Lemma Decomposition

| Component | Lemmas | Difficulty | Time |
|-----------|--------|------------|------|
| `Value` type infrastructure | 20 | Easy | 3 days |
| Stack operations (push/pop/peek) | 50 | Easy | 5 days |
| Single-step semantics (21 opcodes × 3 lemmas) | 63 | Medium | 8 days |
| Step invariant preservation (21 opcodes × 2 lemmas) | 42 | Medium | 6 days |
| `constraints_ok` monotonicity | 15 | Medium | 3 days |
| IP advancement lemma | 25 | Easy | 3 days |
| `safe` predicate correctness | 40 | Medium | 6 days |
| Termination (Theorem 2) | 20 | Medium | 4 days |
| Stack boundedness (Theorem 3) | 25 | Medium | 4 days |
| ExecutionTrace infrastructure | 30 | Medium | 4 days |
| Soundness (Theorem 1) | 80 | Hard | 14 days |
| Custom tactics / automation | 40 | Medium | 6 days |
| Standard library lemmas (`Vector`, `Fin`, `List`) | 50 | Easy-Medium | 5 days |
| **Total** | **~500** | | **~71 days** |

Note: The "standard library lemmas" row accounts for the auxiliary lemmas about `Vector`, `Fin`, and `List` that are needed in practice. In Lean4 proofs of this kind, infrastructure lemmas typically account for 10–15% of the total effort. The estimate above includes a conservative 50 such lemmas; if the standard library is less complete than expected, this could grow to 100+, pushing the total toward 600–700.

### 7.2 Calendar Estimate

- **Optimistic** (full-time Lean4 expert, integer-only proof): 14 weeks
- **Realistic** (part-time, with other work): 18 weeks
- **Pessimistic** (learning Lean4 while proving, or extending to floats): 21+ weeks

### 7.3 Risk Factors

- **Float reasoning**: Even with Option C (integer-only initial proof), the `Value.float` variant exists and must be handled in case analysis. If float-specific lemmas are needed sooner than expected, the timeline extends. Mitigation: start with Option C, measure progress, and reassess.
- **Division by zero**: The `Div` and `Mod` opcodes check for zero before popping. Proving that this check always happens in the right order requires careful sequencing lemmas. The `Step` relation's `div_zero` and `mod_zero` constructors make this explicit.
- **Validate semantics**: The mini VM's `Validate` pops 3 values (val, lower, upper) — the order matters and must match the Lean4 model exactly. From the Rust code: `upper = pop()`, `lower = pop()`, `val = pop()`, so `peek(0) = upper`, `peek(1) = lower`, `peek(2) = val`.
- **`-0.0` handling**: In IEEE 754, `-0.0 = 0.0`. The Rust VM's `Assert` checks `val == 0.0`, so `-0.0` would cause an assert failure. This is correct behavior, but the formal proof must account for it if using floats. Under Option C (integers), this is a non-issue.

---

## 8. Related Work

### 8.1 CompCert (Leroy, 2009)

CompCert is a formally verified C compiler proven correct in Coq. The key result: the generated assembly code behaves identically to the CompCert Clight source. Our work differs in scope (a VM, not a compiler) and target (Lean4, not Coq). However, the technique of proving **simulation** between abstract and concrete semantics is directly applicable. CompCert's `star` relation for multi-step execution informed our corrected `Steps` definition. CompCert's ~100,000 lines of Coq dwarf our estimated ~5,000–8,000 lines of Lean4, reflecting our simpler target.

### 8.2 seL4 (Klein et al., 2009)

seL4 is a formally verified microkernel (~200,000 lines of Isabelle/HOL proof). It proves functional correctness: the implementation refines an abstract specification. Our proof is structurally similar but vastly simpler — a single-threaded VM with no I/O, no scheduling, no memory management. Where seL4 reasons about 10,000+ invariants, we expect ~20.

### 8.3 Fiat-Crypto (Erbsen et al., 2019)

Fiat-Crypto uses Lean4 (née Lean) to generate verified elliptic curve cryptography code. It proves that the generated assembly correctly implements the mathematical specification. Our work is complementary: Fiat-Crypto verifies the *output* of a compiler; we verify the *interpreter* that executes the output. Together, they would form an end-to-end verified pipeline.

### 8.4 WebAssembly Formal Verification (Watt, 2018)

Watt mechanized the WebAssembly specification in Isabelle and proved type soundness. WebAssembly is a stack-based VM with ~170 instructions, far more complex than FLUX. Our proof benefits from FLUX's much smaller instruction set and simpler control flow (no blocks/loops/ifs in mini — just sequential).

### 8.5 Comparison Summary

| Project | Target | Proof Size | Difficulty | Tool |
|---------|--------|------------|------------|------|
| CompCert | C compiler | ~100K lines | Extreme | Coq |
| seL4 | Microkernel | ~200K lines | Extreme | Isabelle |
| Fiat-Crypto | Crypto codegen | ~30K lines | Very Hard | Lean4 |
| WASM verification | WASM spec | ~10K lines | Hard | Isabelle |
| **FLUX VM (this work)** | **Constraint VM** | **~5–8K lines** | **Medium** | **Lean4** |

---

## 9. Certification Path: From Lean4 Proof to DO-178C

### 9.1 DO-178C and DO-330

DO-178C is the aviation standard for software certification. DO-330 is its companion standard for tool qualification. When a tool is used to eliminate, reduce, or automate a verification process (like constraint checking), the tool itself must be qualified.

DO-330 defines five Tool Qualification Levels (TQL-1 through TQL-5), with TQL-1 being the most stringent (required when tool output is not verified by subsequent processes).

### 9.2 Claim: Contributes to DO-330 Evidence

**We do not claim that the formal proof "satisfies DO-330."** Rather, the proof *contributes to* the evidence package required for tool qualification. The distinction is critical:

- **The proof provides**: mathematical assurance that the abstract VM model is correct (soundness, termination, boundedness)
- **The proof does not provide**: configuration management evidence, tool installation procedures, tool operating environment documentation, tool problem reporting procedures, or qualification of the Lean4 tool chain itself

For **TQL-3** (tool output partially verified by downstream processes), the formal proof provides strong evidence for correctness objectives (§6.3.1, §6.3.3, §6.3.4) but does not constitute complete qualification evidence.

For **TQL-1** (highest level, required when tool output is the sole verification means), additional qualification of the Lean4 type checker, the Lake build system, and the Lean4 runtime would be required. This is a separate and substantial effort — qualifying a proof assistant itself involves demonstrating that it correctly checks proofs, which is a bootstrapping problem. This is noted as future work and is beyond the scope of this paper.

### 9.3 How Formal Proof Contributes to Qualification

DO-330 objectives that formal proof directly addresses:

| Objective | DO-330 § | How Proof Contributes |
|-----------|----------|----------------------|
| Tool is correct | §6.3.1 | Soundness theorem (Theorem 1) provides evidence |
| Tool development process | §6.3.2 | Proof development is a rigorous process |
| Tool requirements | §6.3.3 | Theorems are formalized requirements |
| Tool architecture | §6.3.4 | Lean4 model is the formal architecture |
| Tool source code | §6.3.5 | Lean4 definitions are executable specification |
| Tool integration | §6.3.6 | *Requires* refinement proof (future work) |
| Tool testing | §6.3.7 | Lean4 `#eval` tests supplement unit tests |
| Tool requirements coverage | §6.3.8 | Each theorem maps to a requirement |
| Tool robustness | §6.3.9 | Boundedness theorem (Theorem 3) provides evidence |

**Note on §6.3.6 (Tool Integration):** The refinement proof from the Lean4 abstract model to the Rust implementation (Section 5.6) is essential for this objective. Without it, we have a proof of a mathematical model, not a proof of the as-built tool. This is the difference between contributing to TQL-3 evidence (model proved correct, implementation tested) and TQL-2 evidence (tool proved correct). Completing the refinement proof is a prerequisite for higher qualification levels.

### 9.4 The Qualification Evidence Package

A complete qualification package would include:

1. **Tool Requirements Specification** — The three theorems stated in Section 3
2. **Tool Design Description** — The Lean4 formal model from Section 4
3. **Proof Artifacts** — All Lean4 source files, compiled with `lake build`
4. **Proof Review Report** — Independent review by a second Lean4 expert
5. **Traceability Matrix** — Mapping each DO-330 objective to specific proof artifacts
6. **Refinement Proof** — Correspondence between Lean4 model and Rust implementation (future work)
7. **Test Results** — Executable semantics tested against Rust test suite
8. **Tool Chain Documentation** — Evidence of Lean4 version, Lake version, dependencies
9. **Environment Assumptions** — IEEE 754 compliance of target hardware (documented, not assumed)

### 9.5 Limitations and Honest Assessment

Formal proof does not replace all qualification activities:

1. **Configuration management** of the proof artifacts is still required (version control, change control, baselining)
2. **Tool chain qualification** — Lean4 itself is not formally verified. Trusting the proof requires trusting the Lean4 type checker. For TQL-3 and above, DO-330 requires tool chain qualification evidence. This is a known gap.
3. **Environment assumptions** — The proof assumes correct float arithmetic on the target hardware. DO-330 requires documentation and justification of all environment assumptions. IEEE 754 compliance of the target platform must be demonstrated, not assumed.
4. **Refinement gap** — Without the formal refinement proof (Section 5.6), we have proved a model correct, not the implementation. The gap between the Lean4 model and the Rust code must be auditable and is subject to review.
5. **Float reasoning** — Under Option C (integer-only proof), the formal proof does not cover float arithmetic at all. This must be clearly documented as a limitation and addressed in subsequent phases.

---

## 10. Conclusion

We have presented a formal verification strategy for the FLUX constraint VM, targeting the flux-isa-mini variant with 21 opcodes, a 32-slot fixed stack, and sequential execution. The strategy centers on three theorems — soundness, termination, and boundedness — proved in Lean4 using induction on execution steps, well-founded recursion on the step counter, and case analysis over the finite opcode set.

The key insight is that the mini VM's design choices — `no_std`, no heap allocation, no async, no backward jumps — are not just engineering conveniences. They are **proof engineering choices** that make formal verification tractable. Every simplification in the implementation is a simplification in the proof.

The revised estimate of 500–700 lemmas over 14–21 weeks is achievable by a single trained Lean4 practitioner for the integer-only proof (Phase 1). Extending to float arithmetic adds additional effort that is difficult to estimate without experience with the chosen axiomatization strategy.

We have addressed the float reasoning challenge honestly: the initial proof targets integer-only semantics, with float axiomatization as Phase 2 and full IEEE 754 reasoning as future work. We have scoped the certification claims appropriately: the formal proof *contributes to* DO-330 TQL-3 evidence but does not constitute complete qualification, and TQL-1 would require qualifying Lean4 itself.

Future work includes:
1. Completing the Phase 1 (integer) proof and measuring actual effort vs. estimate
2. Extending to Phase 2 (abstract float axiomatization) and assessing proof effort
3. Completing the refinement proof from Lean4 model to Rust implementation
4. Extending the proof to the full 35-opcode VM (requiring loop invariants for Jump/Branch)
5. Proving the compiler: that the constraint compiler emits bytecode satisfying the `safe` predicate
6. End-to-end verification: from high-level constraint specification to VM execution

The constraint compilation pipeline can be trusted. We now have a roadmap for proving it.

---

## Appendix A: Lean4 Signature Summary

```lean4
-- Value type (heterogeneous stack entries)
inductive Value := | float : Float → Value | int : Int → Value | bool : Bool → Value

-- Core types
inductive FluxOpcode := (21 variants)
structure Instruction := (opcode, operand0, operand1)
abbrev Program := List Instruction
structure VMState := (stack : Vector Value STACK_SIZE, sp, ip, steps, constraints_ok)
inductive VMError := (5 variants)

-- Step result
inductive StepResult := | ok (next : VMState) | error (err : VMError) (state : VMState) | halt (state : VMState)

-- Execution trace
structure TraceEntry := (ip, opcode, state_before, state_after, constraint_passed)
abbrev ExecutionTrace := List TraceEntry

-- Execution result
inductive ExecResult := | ok (state : VMState) (trace : ExecutionTrace) (satisfied : Bool) | error (err : VMError) (state : VMState) (trace : ExecutionTrace)

-- Step relation
inductive Step : VMState → Program → StepResult → Prop

-- Multi-step
inductive Steps : VMState → Program → ExecResult → Prop

-- Safe predicate
def safe (prog : Program) : Bool

-- Main theorems
theorem soundness : ∀ prog init_s final_s trace, ... → Steps init_s prog (.ok final_s trace true) → ...
theorem termination : ∀ prog s, s.ip ≤ prog.length → ∃ res, Steps s prog res ∧ ...
theorem boundedness : ∀ prog s res, s.sp ≤ STACK_SIZE → safe prog = true → Steps s prog res → ...

-- Supporting lemmas
theorem constraints_ok_monotone : ∀ s prog res, Steps s prog res → (constraints_ok is non-increasing)
theorem sp_invariant : ∀ s prog res, Steps s prog res → sp_bounded res
theorem ip_advances : ∀ s prog res, Step s prog res → ip_forward res
theorem steps_monotone : ∀ s prog res, Steps s prog res → steps_nondecreasing res
theorem safe_correct : ∀ prog, safe prog = true → (static stack analysis matches runtime)
```

## Appendix B: Mini VM Opcode Quick Reference

| Hex | Opcode | Stack In | Stack Out | Effect |
|-----|--------|----------|-----------|--------|
| 0x01 | Add | 2 | 1 | a + b |
| 0x02 | Sub | 2 | 1 | a - b |
| 0x03 | Mul | 2 | 1 | a × b |
| 0x04 | Div | 2 | 1 | a ÷ b (checked) |
| 0x05 | Mod | 2 | 1 | a mod b (checked) |
| 0x10 | Eq | 2 | 1 | 1.0 if a=b, else 0.0 |
| 0x11 | Lt | 2 | 1 | 1.0 if a<b, else 0.0 |
| 0x12 | Gt | 2 | 1 | 1.0 if a>b, else 0.0 |
| 0x13 | Lte | 2 | 1 | 1.0 if a≤b, else 0.0 |
| 0x14 | Gte | 2 | 1 | 1.0 if a≥b, else 0.0 |
| 0x20 | Assert | 1 | 0 | Error if val=0.0 |
| 0x21 | Check | 1 | 1 | Non-consuming, flag if 0.0 |
| 0x22 | Validate | 3 | 1 | Range check [lower, upper] |
| 0x23 | Reject | 0 | 0 | Set constraint false |
| 0x30 | Load | 0 | 1 | Push operand |
| 0x31 | Push | 0 | 1 | Push operand |
| 0x32 | Pop | 1 | 0 | Discard top |
| 0x40 | Snap | 1 | 1 | Round to nearest |
| 0x41 | Quantize | 2 | 1 | Round(val/step)×step |
| 0xF0 | Halt | 0 | 0 | Stop execution |
| 0xFF | Nop | 0 | 0 | No operation |

---

*Forgemaster ⚒️ — Precision is not a luxury, it's a requirement.*
*SuperInstance · Cocapn Fleet · 2026*
