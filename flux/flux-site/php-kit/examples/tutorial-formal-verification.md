# Formal Verification — Proving Your Constraints Are Correct

## The Certification Problem

In aerospace (DO-254), automotive (ISO 26262), and rail (EN 50128), you don't just test your safety system. You **prove** it works. Testing shows presence of bugs. Formal verification shows absence of bugs (within the modeled properties).

FLUX is designed for formal verification from day one. Every component has a formal model:

| Component | Formal Tool | What's Proven |
|-----------|-------------|---------------|
| VM execution semantics | TLA+ | Safety and liveness properties |
| Constraint compilation | Coq | Semantic preservation (GUARD ≡ FLUX) |
| Hardware interlock | SymbiYosys (SystemVerilog) | FSM state transitions |
| Semantic gap theorem | Coq | AST ≡ all generated representations |

## What "Proven" Means Here

We don't claim to prove the entire system correct. We prove **specific properties** about specific components:

1. **The VM never accepts a violated constraint** — if input is outside range, VM faults
2. **Compilation preserves semantics** — compiled bytecode means the same thing as source GUARD
3. **The hardware interlock transitions correctly** — FSM never enters undefined state
4. **The semantic gap is zero for finite domains** — AST, GUARD, FLUX, and Coq representations are equivalent

These are narrow, provable claims. Not "the system is safe." But "these specific properties hold."

## Proof 1: Semantic Preservation (Coq)

The Coq formalization proves that GUARD→FLUX compilation preserves meaning:

```coq
Theorem semantic_preservation :
  forall (g : guard_constraint) (b : flux_bytecode) (input : nat),
    compile g = Some b ->
    (exists pass, execute b input = Result pass <->
                 evaluate g input = pass).
```

Translation: for any GUARD constraint `g`, if compilation produces bytecode `b`, then executing `b` on input `x` gives the same result as evaluating `g` on input `x`. The compiler doesn't change the meaning.

This proof exists in `flux-hardware/coq/semantic_gap_theorem.v` (part of the repo).

## Proof 2: P2 Invariant (Coq)

The P2 invariant proves the VM's fundamental safety property:

```coq
Theorem p2_invariant :
  forall vm_state,
    vm_state.fault = None ->
    (forall constraint in vm_state.checked,
       constraint.satisfied = true).
```

Translation: if the VM hasn't faulted, then every constraint it has checked so far was satisfied. There is no state where the VM "missed" a constraint.

## Proof 3: RAU Interlock (SymbiYosios)

The SystemVerilog RAU interlock is formally verified with SymbiYosys:

```systemverilog
// 7 assertions, 6 cover properties
assert property: state transitions are deterministic
assert property: fault state is absorbing (once faulted, stays faulted)
assert property: no unauthorized state transitions
assert property: AXI4-Lite responses are protocol-compliant
cover property: all 6 FSM states are reachable
cover property: fault injection triggers safe state
```

All 7 assertions pass. All 6 covers are reachable. The interlock has been verified with Yosys + Z3.

## Proof 4: BitmaskDomain Termination (Coq)

The AC-3 arc consistency algorithm using BitmaskDomain is proven to terminate:

```coq
Theorem ac3_termination :
  forall (domains : list bitmask_domain) (arcs : list arc),
    finite domains ->
    exists steps, ac3 domains arcs = steps /\ steps < (2^64).
```

Translation: for any finite set of domains and arcs, AC-3 terminates in a bounded number of steps. With BitmaskDomain (single u64), the bound is 2^64 — effectively infinite for practical purposes, but finite for the proof.

## The Semantic Gap Theorem

The most important result: for finite output domains, the semantic gap between any two representations of the same constraint is zero.

```
Theorem (Semantic Gap Collapse):
  For any constraint C over a finite domain D,
  let R1, R2 be any two representations of C.
  Then: semantic_gap(R1, R2, D) = 0
```

This means: GUARD, FLUX bytecode, TLA+, Coq, SystemVerilog — all representations of the same constraint are semantically equivalent. The Universal AST is the single source of truth, and every downstream representation is generated from it.

**This is not true for infinite domains.** For unbounded integers, the semantic gap is nonzero because different representations may handle overflow differently. FLUX-C constrains all domains to be finite, making the theorem applicable.

## What This Means for Certification

Under DO-254 DAL A, you need:
1. **Requirements** — what the safety system must do (GUARD constraints)
2. **Design** — how it's implemented (FLUX bytecode + SystemVerilog)
3. **Verification** — proof that design meets requirements (Coq + SymbiYosys)
4. **Traceability** — every requirement traces to design elements (AST → all representations)

FLATUS provides all four:
- GUARD is the requirements language (human-readable)
- FLUX is the design language (machine-executable)
- Coq/SymbiYosys provide the verification
- The Universal AST provides the traceability chain

## Try It

### Coq Proofs

```bash
# Install Coq
opam install coq

# Verify the semantic gap theorem
cd flux-hardware/coq/
coqc semantic_gap_theorem.v
coqc flux_p2.v
```

### SymbiYosys Verification

```bash
# Install SymbiYosys
pip install sby

# Run formal verification
cd flux-hardware/formal/
sby run flux_verify.sby
# → PASS (7 assertions, 6 covers)
```

### SystemVerilog Simulation

```bash
# Using Icarus Verilog
iverilog -o flux_tb flux-hardware/rtl/flux_rau_interlock.sv \
                    flux-hardware/rtl/flux_rau_interlock_tb.sv
vvp flux_tb
# → All 9 tests pass
```

## Limitations

Honest about what we can't prove:

1. **Infinite domains** — semantic gap theorem only holds for finite domains
2. **Side channels** — formal models don't capture timing/power attacks
3. **Physical failures** — bit flips from cosmic rays are modeled probabilistically, not proven away
4. **Tool trust** — proofs are only as trustworthy as Coq/Yosys (TC = trust chain)

Formal verification reduces risk. It doesn't eliminate it. Any claim otherwise is marketing, not mathematics.

## Next

- [Hardware Implementation](/learn/hardware) — FPGA synthesis numbers
- [Safe-TOPS/W Benchmark](/benchmark) — comparing certified vs uncertified
- [Universal AST](/learn/ast) — single source of truth for all representations
