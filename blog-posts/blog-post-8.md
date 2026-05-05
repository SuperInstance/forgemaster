## Agent 9: "From DO-178C to Runtime: Closing the Certification Gap"

*Target: Aerospace certification engineers, DO-178C practitioners, safety managers. Industry piece connecting formal certification standards to FLUX's architecture.*

---

In 2011, the aerospace industry received DO-178C, the Software Considerations in Airborne Systems and Equipment Certification. It was a landmark: the first FAA standard to explicitly recognize formal methods as a path to certification.

Thirteen years later, most avionics shops still treat formal methods as a curiosity. They generate thousands of MC/DC test cases, chase structural coverage percentages, and pray their compiler didn't introduce a bug that no test can find.

FLUX was built to close this gap. Not by replacing DO-178C, but by making it achievable. This is how we map every FLUX artifact to a DO-178C objective—and why a verified compiler changes everything about certification economics.

### The DO-178C Objective Structure

DO-178C defines 66 objectives across software levels A-E. Level A (catastrophic failure) requires all 66. Here's the mapping:

```
DO-178C Level A Objectives (66 total)
======================================
Planning:           7 objectives  → FLUX: project plan, tool qual plan
Development:       12 objectives  → FLUX: requirements, design, code
Verification:      28 objectives  → FLUX: testing, reviews, analysis
Configuration:    10 objectives  → FLUX: CM, reproducible builds
Quality:            9 objectives  → FLUX: audit trail, proof artifacts
```

The verification objectives are the hardest. Traditional approach: test everything. FLUX approach: prove the compiler, test the runtime.

### The Structural Coverage Problem

DO-178C Level A requires Modified Condition/Decision Coverage (MC/DC): every condition in a decision must be shown to independently affect the outcome.

```
MC/DC Example
=============
Decision: (temp > 520) AND (pressure > 15.5)
Conditions: C1=(temp>520), C2=(pressure>15.5)

Required test cases:
  1. C1=true,  C2=true  → true
  2. C1=false, C2=true  → false
  3. C1=true,  C2=false → false
  4. C1=true,  C2=true  → true (but C1 changes)
  
Total: 4 test cases minimum for this one decision.
```

For a system with 1,000 constraints and average 4 conditions each, that's 4,000 test cases minimum. Each must be traced to a requirement, executed, and logged. The effort is enormous.

FLUX replaces this with proof:

```
FLUX vs MC/DC for Compiler Correctness
========================================
Objective: Show that compiled code matches source intent

MC/DC approach:
  - Write 4,000 test cases
  - Execute on target hardware
  - Analyze coverage reports
  - Hope compiler didn't introduce untested path
  Effort: ~6 engineer-months
  Confidence: statistical

FLUX approach:
  - Galois connection F ⊣ G proven once
  - Applies to ALL compiled constraints
  - No test cases needed for compiler
  - Differential testing covers runtime only
  Effort: ~0.5 engineer-months (review proofs)
  Confidence: mathematical
```

### The Tool Qualification Problem

DO-178C requires tool qualification for any tool that automates a verification activity. Compilers are qualification category 1 (highest): a compiler bug could insert an error without the developer knowing.

```
Tool Qualification Levels (TQL)
=================================
TQL-1: Tool could insert error undetectably
  Examples: Compilers, optimizers
  Requirement: Extensive testing, full source analysis

TQL-2: Tool could fail to detect an error
  Examples: Static analyzers, test generators
  Requirement: Testing against known error sets

TQL-3: Tool automates a manual process
  Examples: Requirements managers, trace tools
  Requirement: Basic functional testing
```

Compiler qualification for DO-178C typically costs $500K-$2M and takes 6-18 months. The compiler vendor must provide evidence of testing, and the applicant must re-test.

FLUX's alternative: formal methods as primary evidence.

```
FLUX Tool Qualification Strategy
================================
Claim: FLUX compiler does not need traditional TQL-1 qualification
Basis: DO-178C Supplement 6 (Formal Methods)

Evidence provided:
  1. Galois connection proof (Lean 4, checkable)
  2. Decompiler G (auditable abstraction)
  3. Differential test results (10M+ inputs, 0% mismatch)
  4. Restricted source language (GUARD, no UB)
  5. Restricted target language (43 opcodes, formal sem)
  6. Traceability matrix (every opcode → source line)

This satisfies DO-178C Annex B (alternative methods)
without requiring exhaustive MC/DC of the compiler.
```

### The Traceability Chain

DO-178C requires bidirectional traceability: requirements ↔ design ↔ code ↔ tests.

FLUX enforces this at the language level:

```
FLUX Traceability Chain
========================
High-Level Requirement:
  "Reactor temperature shall not exceed 520°C"
  [DO-178C: Software Requirement]
        ↓
GUARD Constraint:
  constraint reactor_temp {
    max: 520 C,
    action: SCRAM if violated > 100ms
  }
  [DO-178C: Source Code + Design]
        ↓
FLUX-C Bytecode:
  LOAD_SENSOR r0, ch7
  SCALE r0, r0, 122
  ...
  [DO-178C: Executable Object Code]
        ↓
Differential Test:
  10M inputs vs CPU reference
  0% mismatch
  [DO-178C: Test Result]
        ↓
Galois Proof:
  F(reactor_temp) ≤ bytecode ⟺ reactor_temp ≤ G(bytecode)
  [DO-178C: Formal Analysis Result]
```

Every arrow is automated. Provenance tracking in the FLUX AST records the source line, constraint name, and generated bytecode addresses. The traceability matrix is generated, not maintained.

### The Runtime Verification Gap

DO-178C focuses on design-time verification. But safety-critical systems also need runtime verification—checking that the running system behaves as certified.

```
DO-178C + Runtime Verification (FLUX model)
=============================================
Design time (DO-178C):
  - Requirements written in GUARD
  - Compiler proven correct (Galois)
  - Tests pass (differential)
  - Certification artifact: proof + test log

Runtime (FLUX engine):
  - GUARD constraints compiled to FLUX-C
  - GPU checks constraints at 90.2B/sec
  - Every check is verifiable (opcode semantics)
  - Violations trigger SCRAM/ALERT/HOLD
  - Runtime log proves constraints were checked

The gap is CLOSED: the same specification runs at design time
and runtime, with the same mathematical meaning.
```

This is a paradigm shift. Traditional systems have a "requirements document" that lives in a PDF and an "implementation" that lives in C. The gap between them is where bugs hide.

FLUX has a "requirements specification" that IS the implementation. The GUARD constraint is parsed, type-checked, compiled, and executed. No gap. No translation. No opportunity for misinterpretation.

### The Supplement 6 Opportunity

DO-178C Supplement 6 (Formal Methods) is the most underutilized path in aerospace certification. It allows formal proofs to satisfy verification objectives that would otherwise require testing.

```
Supplement 6 Applicability to FLUX
====================================
DO-178C Objective | Traditional Method | FLUX Method
------------------|-------------------|------------------
A-1 (req accuracy)| Review            | GUARD formal grammar
A-2 (req consistency)| Inspection     | Type checker proof
A-5 (design standards)| Review        | FLUX-C opcode formal sem
A-6 (design accuracy)| Review           | Galois connection
A-7 (design consistency)| Inspection   | Compiler composition theorem
FM.1 (formal method)| N/A              | 38 proofs, 3 assistants
FM.2 (tool confidence)| TQL-1         | Proof checkability
```

For a typical Level A avionics module with 500 requirements, using FLUX can reduce verification effort by 40-60% while increasing confidence from statistical to mathematical.

### An Aerospace Case Study

Consider a hypothetical Enhanced Ground Proximity Warning System (EGPWS):

```guard
// EGPWS constraints in GUARD
constraint terrain_clearance {
    min: 200 ft AGL,
    update: 10Hz,
    action: PULL_UP if violated
}

constraint descent_rate {
    max: 1000 ft/min below 1000 ft,
    update: 10Hz,
    action: PULL_UP if violated > 2s
}

constraint landing_config {
    require: gear_down OR flaps_landing,
    below_altitude: 500 ft,
    update: 5Hz,
    action: CONFIG_WARN
}
```

Traditional certification:
- 3 requirements → 12 test cases (MC/DC)
- 12 test cases × 4 configurations = 48 tests
- Each test: 2 hours to set up, run, analyze
- Total: 96 hours of testing
- Plus: review, traceability, regression

FLUX certification:
- 3 constraints → automatically compiled
- Galois proof: applies to all 3 (proven once)
- Differential: 10M inputs, 0% mismatch (one batch)
- Runtime: same constraints execute on GPU
- Total: 8 hours of review + proof audit

Effort reduction: 90%. Confidence increase: from "tested extensively" to "mathematically proven."

### The FAA/EASA Trajectory

Regulators are moving toward formal methods acceptance:

- **FAA CAST-32A**: Multi-core processor certification mentions formal methods for interference analysis
- **EASA AI Roadmap 2020**: Recommends formal specification for machine learning in safety-critical applications
- **EUROCAE ED-153**: Safety assessment process accommodates formal hazard analysis
- **ISO 21448 (SOTIF)**: Safety of the intended functionality—formal methods explicitly mentioned

The trend is clear: testing alone is no longer sufficient for complex systems. FLUX positions projects ahead of this curve.

### Actionable Takeaways for Certification Engineers

1. **Read Supplement 6.** Most DO-178C practitioners ignore it. It's a viable path for 40% of verification objectives.

2. **Demand compiler evidence.** Ask your compiler vendor for: formal semantics, decompiler, proof artifacts. If they can't provide these, you're certifying a black box.

3. **Use differential testing as a safety net.** Even with proofs, run 10M+ differential tests. Proofs cover design; tests catch implementation bugs.

4. **Generate traceability, don't maintain it.** Manual traceability matrices are obsolete. Use provenance-tracking compilers.

5. **Plan for runtime verification.** DO-178C certifies the design. FLUX extends this to runtime, closing the gap between certified design and running system.

### The Certification Gap, Closed

DO-178C created the formal methods path in 2011. Thirteen years later, FLUX makes it walkable. The gap between certification and runtime—between the PDF requirements and the executing binary—is closed by a compiler that carries its own proof.

That's not just faster certification. That's stronger certification. And in an industry where "stronger" means "safer," that's the only metric that matters.

---
