# GUARD — Generic Unified Assurance Requirement Descriptor

**Version:** 1.0.0-ship  
**Target:** FLUX 43-opcode stack VM  
**Intended Use:** Safety-critical systems (avionics, medical, nuclear, industrial control)  
**Compliance Targets:** DO-178C / DO-333, IEC 61508, ISO 26262, IEC 62304

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Design Principles](#2-design-principles)
3. [Language Overview](#3-language-overview)
4. [Complete Grammar](#4-complete-grammar)
5. [Semantics](#5-semantics)
6. [Compilation to FLUX Bytecode](#6-compilation-to-flux-bytecode)
7. [Proof Certificates](#7-proof-certificates)
8. [Error Messages](#8-error-messages)
9. [Comparison with Related Work](#9-comparison-with-related-work)
10. [Toolchain & Shipping Checklist](#10-toolchain--shipping-checklist)

---

## 1. Introduction

GUARD is a domain-specific language for specifying safety constraints that must hold over the lifetime of a physical system. It is designed for **safety engineers** — professionals who understand failure modes, hazard analysis, and regulatory standards, but who do not write C++ or model-checking scripts.

A GUARD module looks like a requirements document with structure:

```guard
invariant ThrottleMustNotExceedMax
  critical
  ensure throttle_command ≤ 100 %
  on_violation halt;
```

This text has **unambiguous formal semantics**, compiles to deterministic FLUX bytecode, and carries a **machine-checkable proof certificate** that the bytecode correctly implements the requirement.

### Why GUARD exists

Existing tools force a choice:

- **SCADE/Lustre** is powerful but requires control-engineering expertise and a qualified code generator.
- **Alloy** finds bugs but does not produce real-time executable constraints.
- **Datalog** reasons about facts, not continuous physics.
- **Hand-written C** is error-prone and its correctness cannot be mechanically verified without heroic effort.

GUARD bridges the gap: *natural-language readability* + *formal verification* + *real-time execution* + *independent proof certificates*.

---

## 2. Design Principles

### P1 — Readability over terseness
A safety engineer should read a GUARD file without training. Verbose is fine. Cryptic is not.

### P2 — Units are semantic, not cosmetic
`100` is meaningless. `100 %` or `340 kt` or `2.5 g` is meaningful. The compiler checks dimensional consistency. Adding knots to degrees is a type error.

### P3 — Temporal logic is explicit
Requirements talk about time: "for 3 seconds", "within 500 ms", "since takeoff". GUARD makes these first-class operators, not library functions.

### P4 — One source of truth
The `.guard` file is the requirement. It compiles to bytecode *and* to a proof certificate. There is no separate Word document, no separate Simulink model.

### P5 — Trust the proof, not the compiler
The compiler can be buggy. The proof certificate cannot lie (if the verifier is correct). The verifier is < 1,000 lines of Rust.

### P6 — Graceful degradation
Not every property can be fully verified automatically. GUARD distinguishes:
- **Proved** — SMT solver found a proof.
- **Bounded** — BMC checked up to N steps; no counterexample found.
- **Runtime** — No static proof; bytecode enforces the constraint at runtime.

---

## 3. Language Overview

A GUARD module has seven sections:

| Section | Purpose | Example |
|---------|---------|---------|
| `module` | Identity, version, target system | `module ThrottleLimit version "1.0.0"` |
| `import` | Reuse other modules | `import AtmosphereModel.density` |
| `dimension` | Define physical units | `dimension Knots is real from 0 kt to 500 kt` |
| `domain` | Define discrete/enumerable sets | `domain Zone = { Red, Orange, Yellow }` |
| `state` | Observable system variables | `state altitude has real in [0 ft .. 45000 ft]` |
| `invariant` | Hard constraints that must hold | `ensure altitude ≤ Alt_max` |
| `derive` | Logical consequences (proof obligations) | `conclude V_stall_current = ...` |
| `proof` | Verification tactics and certificate config | `tactic k_induction 5` |

### Temporal Operators

| Operator | Meaning | Use Case |
|----------|---------|----------|
| `always P` | P holds at every future step | Limit never exceeded |
| `eventually P` | P holds at some future step | Liveness (alarm must sound) |
| `next P` | P holds at the immediate next step | One-step lookahead |
| `P until Q` | P holds continuously until Q becomes true | Armed until fired |
| `P since Q` | P has held continuously since Q was true | Monitoring since fault |
| `for T P` | P holds continuously for duration T | Rate-limit cooldown |
| `after T P` | P holds after duration T has elapsed | Startup delay |
| `old x` | Value of x at previous time step | Detect changes |
| `rate_of x` | Derivative of x (per sample period) | Rate limiting |
| `delta x` | `x - old x` | Discrete change detection |

### N-ary Constraints

GUARD provides syntactic sugar for common n-ary constraints, lowered to FLUX bytecode loops:

- `all_distinct(x, y, z)` — No two values are equal.
- `all_equal(x, y, z)` — All values are equal.
- `monotone(x ascending)` — Values never decrease over time.
- `table T[i] must_be v` — Lookup-table constraint.
- `forall p in arr : P(p)` — Universal quantification over arrays.
- `exists p in arr : P(p)` — Existential quantification over arrays.

---

## 4. Complete Grammar

See [`GRAMMAR.ebnf`](GRAMMAR.ebnf) for the formal EBNF specification. Key excerpts:

```ebnf
invariant_decl ::=
  "invariant" identifier [ priority ] [ "when" expr ]
  "ensure" expr
  [ "on_violation" violation_action ]
  ";" ;

derive_decl ::=
  "derive" identifier "from" premise_list
  [ "when" expr ]
  "conclude" expr
  [ "proof_obligation" expr ]
  ";" ;

expr ::=
  logical_expr ;

logical_expr ::=
  temporal_expr
  | logical_expr "implies" temporal_expr
  | logical_expr "and" temporal_expr
  | logical_expr "or" temporal_expr
  | "not" temporal_expr ;

temporal_expr ::=
  comparison_expr
  | "always" comparison_expr
  | "eventually" comparison_expr
  | "next" comparison_expr
  | comparison_expr "until" comparison_expr
  | "for" quantity comparison_expr ;
```

---

## 5. Semantics

### 5.1 Trace Semantics

A GUARD module denotes a set of **traces** — infinite sequences of states `σ₀, σ₁, σ₂, ...` where each `σᵢ` is a valuation of all declared state variables.

An invariant is **satisfied** on a trace iff the constraint expression evaluates to `true` at every time step where the `when` guard is active.

A derived rule is **valid** iff it is a logical consequence of its premises in all reachable traces.

### 5.2 Unit Semantics

Every expression has a **unit signature** (a rational power-product of base dimensions: length, mass, time, temperature, angle, current, amount).

Rules:
- Addition/subtraction: operands must have identical signatures.
- Multiplication: signatures multiply (exponents add).
- Division: signatures divide (exponents subtract).
- Comparison: operands must have identical signatures.
- `rate_of`: signature is dividend signature divided by time.

Normalization: all quantities are converted to SI base units before bytecode emission, then scaled to fixed-point or `f64` representation as configured.

### 5.3 Temporal Semantics

GUARD uses **discrete-time linear temporal logic** (LTL) with bounded-duration operators.

- `always P` ≡ `∀k ≥ 0 . P(σₖ)`
- `eventually P` ≡ `∃k ≥ 0 . P(σₖ)`
- `next P` ≡ `P(σ₁)`
- `P until Q` ≡ `∃k ≥ 0 . Q(σₖ) ∧ (∀j < k . P(σⱼ))`
- `for T P` where T = n × sample_period ≡ `∀k ∈ [t, t+n] . P(σₖ)`
- `old x` ≡ `σₜ₋₁(x)` if t > 0, else `initial(x)`
- `rate_of x` ≡ `(σₜ(x) − σₜ₋₁(x)) / sample_period`

### 5.4 Formal Verification Conditions

For each invariant `I`, the compiler generates two verification conditions:

1. **Initiation**: `InitialState ⇒ I(σ₀)`
2. **Preservation**: `I(σₜ) ∧ Transition(σₜ, σₜ₊₁) ⇒ I(σₜ₊₁)`

If both are proved, `I` is an **inductive invariant** and holds in all reachable states.

For derived rules `D: P₁, ..., Pₙ conclude C`, the compiler generates:

- **Entailment**: `P₁ ∧ ... ∧ Pₙ ⇒ C`

Temporal properties are handled by:
- **K-induction** for unbounded `always` properties.
- **Bounded model checking (BMC)** for `eventually` and finite-horizon properties.
- **Differential invariants** for continuous-rate constraints.

---

## 6. Compilation to FLUX Bytecode

GUARD compiles to the **FLUX 43-opcode stack VM**. The compilation pipeline:

```
GUARD Source
     │
     ▼
┌─────────────┐
│   Parser    │  → AST
└─────────────┘
     │
     ▼
┌─────────────┐
│ Typechecker │  → Typed AST + unit-normalized expressions
└─────────────┘
     │
     ▼
┌─────────────┐
│  Lowering   │  → Desugar temporal ops, expand quantifiers,
│   Passes    │    inline derived rules, allocate memory slots
└─────────────┘
     │
     ▼
┌─────────────┐
│   Prover    │  → SMT-LIB VCs + proof obligations
└─────────────┘
     │
     ▼
┌─────────────┐
│   Emitter   │  → FLUX bytecode (.flux) + proof certificate (.guardcert)
└─────────────┘
```

### Memory Model

The FLUX VM has 256 memory slots (indexed 0–255), allocated as:

| Slot Range | Purpose |
|------------|---------|
| 0–31 | Constants (pre-loaded at boot) |
| 32–127 | State variables (updated by host every cycle) |
| 128–223 | Temporal history buffers (circular queues) |
| 224–255 | Scratch / intermediate results |

### Example Mapping

See [`BYTECODE.md`](BYTECODE.md) for the complete mapping of Example (a) — Throttle Limit — to FLUX bytecode offsets, hex dump, and runtime behavior.

---

## 7. Proof Certificates

Every compiled module produces a **proof certificate** (`.guardcert`) alongside the bytecode. The certificate is a JSON artifact containing:

- Source and bytecode hashes (tamper detection).
- One proof block per `proof { ... }` declaration.
- Per-obligation verification conditions in SMT-LIB format.
- Solver results (`sat` / `unsat` / `unknown`).
- Counterexamples for failed proofs.
- A Merkle root over all obligation traces.

See [`CERTIFICATES.md`](CERTIFICATES.md) for the complete format, Merkle construction, trusted computing base, and verification workflow.

---

## 8. Error Messages

GUARD error messages are designed for **safety engineers**, not compiler hackers. Every message includes:

1. **What went wrong** in plain English.
2. **Where** in the source (with a snippet).
3. **The safety impact** of the error.
4. **Concrete suggestions** for fixing it.

See [`ERRORS.md`](ERRORS.md) for the complete catalog covering parse errors, unit mismatches, proof failures, runtime violations, and certificate regressions.

---

## 9. Comparison with Related Work

See [`COMPARISON.md`](COMPARISON.md) for a detailed comparison with **SCADE/Lustre**, **Alloy**, and **Datalog**, covering audience, execution model, temporal expressiveness, proof style, and interoperability.

---

## 10. Toolchain & Shipping Checklist

### Compiler (`guardc`)

- [x] Parser (PEG-based, error-recovering)
- [x] Typechecker with dimensional analysis
- [x] Lowering passes (temporal expansion, quantifier elimination)
- [x] FLUX bytecode emitter
- [x] SMT-LIB VC generator (Z3 / cvc5 / Bitwuzla)
- [x] Proof certificate emitter
- [ ] IDE integration (VS Code extension)
- [ ] LSP server (go-to-definition, hover units)
- [ ] Requirements traceability matrix exporter (DO-178C)

### Runtime

- [x] FLUX 43-opcode VM (Rust, no-std capable)
- [x] Deterministic execution (bounded stack, no heap)
- [x] Host binding API (C / Rust)
- [x] Execution trace capture for NVM black-box
- [ ] WCET analyzer for FLUX bytecode
- [ ] SIL 4 qualified VM

### Verification

- [x] Native certificate format
- [x] Merkle root computation
- [x] Independent verifier CLI
- [ ] DO-333 formal methods supplement compliance
- [ ] Tool qualification kit (TQL)

### Documentation

- [x] Language specification (this document)
- [x] Grammar (EBNF)
- [x] Bytecode mapping guide
- [x] Certificate format
- [x] Error catalog
- [x] Comparison whitepaper
- [ ] Safety engineer tutorial (1-day course)
- [ ] Formal semantics paper (Coq mechanization)

---

## Examples

Three concrete examples of increasing complexity are provided in the `examples/` directory:

| File | Complexity | Concepts Demonstrated |
|------|------------|----------------------|
| [`examples/throttle.guard`](examples/throttle.guard) | Simple | State, domain, binary invariant, derived rule |
| [`examples/zone-access.guard`](examples/zone-access.guard) | Medium | Enums, arrays, records, lookup tables, quantifiers, existentials |
| [`examples/flight-envelope.guard`](examples/flight-envelope.guard) | Complex | Physical units, configuration constants, temporal rate limits, conditional authority reduction, differential invariants |

---

## License & Governance

GUARD is developed as part of the FLUX ecosystem. The language specification is versioned independently of the compiler. Changes to the grammar require a minor version bump; changes to bytecode encoding require a major version bump.

**Status: READY TO SHIP — v1.0.0**
