# GUARD vs. Related Technologies

GUARD occupies a unique position in the design space: it is a **requirements-language-first** formal specification tool that compiles to a lightweight VM and produces independently verifiable proof artifacts.

## At a Glance

| Dimension | GUARD | SCADE/Lustre | Alloy | Datalog |
|-----------|-------|--------------|-------|---------|
| **Primary user** | Safety engineer | Control engineer | Software architect | Database engineer |
| **Syntax feel** | Requirements doc | Dataflow diagram / equations | Relational logic | Logic rules |
| **Execution model** | Constraint loop on FLUX VM | Synchronous dataflow (SCADE Suite) | SAT solver (bounded) | Fixpoint evaluation |
| **Temporal logic** | Explicit (`always`, `next`, `for T`) | Implicit via `pre`, `->`, clocks | Via dynamic predicates | Via stratified negation / DRed |
| **Physical units** | **Mandatory, checked** | Optional (Simulink-style) | No | No |
| **Proof style** | SMT + inductive invariants | KCG (qualified code generator) | SAT (bounded verification) | Query satisfiability |
| **Certificates** | **Native Merkle proofs** | DO-178C tool qualification | None | None |
| **Target runtime** | FLUX 43-opcode VM | C / Ada (certified) | Java / Alloy Analyzer | Datalog engine |
| **Real-time** | **Hard real-time (≤ 1 ms loop)** | Hard real-time (deterministic) | Offline only | Soft real-time |
| **N-ary constraints** | First-class (`all_distinct`, tables) | Via node networks | Relational quantifiers | Joins + aggregates |

---

## SCADE / Lustre

### What SCADE does well
- **Certified code generation** (KCG) is the gold standard for DO-178C.
- Synchronous dataflow is intuitive for control engineers: every variable is a stream, operators are pointwise.
- Excellent traceability from model to object code.

### Where GUARD differs
- **Audience**: SCADE requires training in synchronous programming. GUARD reads like a requirements document ("ensure throttle_command ≤ 100 %") so safety engineers can write it directly.
- **Units**: SCADE has optional unit annotations; GUARD enforces dimensional consistency at compile time.
- **Proof model**: SCADE relies on *tool qualification* (trust the code generator). GUARD relies on *proof certificates* (trust a small verifier, not the compiler).
- **Temporal expressiveness**: Lustre's `pre` and `->` are powerful but subtle. GUARD's `always`, `for 3 s`, and `rate_of` map directly to natural-language requirements.
- **Runtime footprint**: SCADE-generated C requires an OS thread and libc. FLUX bytecode runs on a 300-line VM with no heap allocation, suitable for bare-metal FCCs.

### When to use SCADE
You need DO-178C certification, you have control engineers on staff, and you can afford the Esterel toolchain.

### When to use GUARD
You need safety engineers to own the specification, you want machine-checked proofs without trusting a large compiler, or your target is a resource-constrained node (edge, PLC, bare-metal).

---

## Alloy

### What Alloy does well
- **Relational modeling** is unmatched for structural constraints (e.g., "no cycles in the ownership graph").
- **Bounded verification** finds subtle bugs in protocols and access-control policies.
- Lightweight, open-source, excellent for early design exploration.

### Where GUARD differs
- **Execution**: Alloy is a *model finder*, not a runtime. It answers "is there a counterexample within bound k?" GUARD generates executable bytecode that enforces constraints every 10 ms.
- **Temporal logic**: Alloy 6 added temporal operators, but they are translated to SAT and verified only within a bounded horizon. GUARD uses SMT + k-induction for unbounded proofs (when possible).
- **Physical units**: Alloy has no concept of knots, feet, or g-loads.
- **Error messages**: Alloy's counterexamples are raw relational tuples. GUARD's counterexamples cite the aircraft state and suggest fixes.

### When to use Alloy
You are designing a protocol, a file-system structure, or an authorization matrix, and you want to explore "what if" scenarios.

### When to use GUARD
You need to *continuously enforce* safety limits on a physical system and generate auditable proof that the limits are correct.

---

## Datalog

### What Datalog does well
- **Rule-based reasoning** is declarative and composable.
- Stratified negation and semi-naive evaluation make it efficient for large fact bases.
- Excellent for static analysis, authorization, and dependency tracking.

### Where GUARD differs
- **Variables over time**: Standard Datalog is atemporal. Extensions like Datalog± or DatalogMTL add temporal reasoning, but they are research tools, not shipping products.
- **Physical semantics**: Datalog reasons about discrete facts. GUARD reasons about continuous physical quantities with derivatives and integrals.
- **Proof certificates**: Datalog derivations can be provenance-tracked, but there is no standard for tamper-evident certificates. GUARD produces Merkle-ized SMT proofs.
- **Determinism**: Datalog evaluation order can affect performance but not results (declarative). GUARD's FLUX VM is strictly deterministic, cycle-accurate, and memory-bounded.

### When to use Datalog
You are building a compiler, a dependency analyzer, or an authorization engine with millions of facts.

### When to use GUARD
You are protecting a physical system where a missed deadline means a crashed aircraft.

---

## Unique Contributions of GUARD

1. **Requirements-as-Code**: The source file *is* the safety requirement. There is no separate Word document that drifts out of sync with the model.
2. **Unit-Aware Type System**: Mixing knots and degrees is a compile-time error, not a Mars Climate Orbiter disaster.
3. **Temporal First-Class**: Time is not an afterthought. `for 3 s`, `rate_of`, and `since` are native, not library hacks.
4. **Proof Certificates**: The output includes not just bytecode but a independently checkable proof that the bytecode is correct relative to the source.
5. **Human-Scale Error Messages**: Every error message includes the physical meaning, the safety impact, and concrete suggestions.
6. **FLUX VM Target**: A 43-opcode stack machine that fits in 8 KB of flash, runs without an OS, and executes constraints in deterministic time.

---

## Interoperability

GUARD is designed to coexist with these tools:

- **SCADE**: Export GUARD invariants as SCADE proof obligations; import SCADE type definitions as GUARD state declarations.
- **Alloy**: Use Alloy to verify the structural correctness of GUARD domain definitions (e.g., "is the auth_matrix total and deterministic?").
- **Datalog**: Use Datalog to compute reachability over GUARD state transition graphs offline.
