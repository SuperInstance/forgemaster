# Universal Constraint AST — Design Specification

## Design Principle

The Universal Constraint AST is the single source of truth for all constraint semantics.
Every downstream representation (GUARD, FLUX, TLA+, Coq, SV, Python) is GENERATED from the AST,
never hand-written and then "translated." This eliminates the leaky abstraction where
a constraint written in one language behaves differently when expressed in another.

The AST captures **intent**, not **syntax**.

## AST Node Types

### 1. BoundNode — Output Range Constraint
```rust
struct BoundNode {
    signal: SignalRef,        // what we're constraining
    lower: Value,             // minimum allowed value
    upper: Value,             // maximum allowed value
    unit: Option<Unit>,       // km/h, deg, m/s²
    severity: Severity,       // HARD | SOFT | DEFAULT
}
```
Semantics: `lower ≤ signal ≤ upper` at all times.
Independent of: language syntax, fixed-point encoding, comparison opcodes.

### 2. DeltaNode — Temporal Rate-of-Change Constraint
```rust
struct DeltaNode {
    signal: SignalRef,
    max_delta: Value,         // maximum change per frame
    window: Window,           // per_frame | sliding(n) | cumulative
    unit: Option<Unit>,
    severity: Severity,
}
```
Semantics: `|signal[t] - signal[t-1]| ≤ max_delta` over window.
Requires: history buffer (maps to HIST_PUSH + HIST_DELTA in FLUX-C).

### 3. RelationNode — Inter-Signal Dependency
```rust
struct RelationNode {
    signal_a: SignalRef,
    signal_b: SignalRef,
    relation: Relation,       // mutually_exclusive | increases_with | decreases_with | proportional(factor)
    severity: Severity,
}
```
Semantics: `relation(signal_a, signal_b)` holds at all times.
This is where most "leaky abstraction" bugs live — cross-signal constraints
are hard to express consistently across formal and executable languages.

### 4. ConfidenceNode — Minimum Confidence Requirement
```rust
struct ConfidenceNode {
    signal: SignalRef,        // the detection/classification output
    threshold: f64,           // minimum confidence [0.0, 1.0]
    scope: ConfidenceScope,   // safety_critical | path_planning | all
    severity: Severity,
}
```
Semantics: `signal.confidence ≥ threshold` before acting on signal.

### 5. SemanticNode — Class-Membership Constraint
```rust
struct SemanticNode {
    signal: SignalRef,
    allowed_classes: Vec<ClassLabel>,
    mask: Option<u64>,        // bitmask for FLUX-C efficiency
    severity: Severity,
}
```
Semantics: `signal.class ∈ allowed_classes`.

### 6. DelegateNode — Cross-Agent Constraint Delegation
```rust
struct DelegateNode {
    source_agent: AgentId,
    target_agent: AgentId,
    constraint: Box<ConstraintNode>,  // the constraint being delegated
    protocol: DelegateProtocol,       // sync | async | co_iterate
}
```
Semantics: `source_agent` delegates enforcement of `constraint` to `target_agent`.
This is Casey's key insight — delegation is a SEMANTIC operation, not a syntax feature.

### 7. CoIterateNode — Collaborative Constraint Solving
```rust
struct CoIterateNode {
    agents: Vec<AgentId>,
    constraints: Vec<ConstraintNode>,
    convergence: ConvergenceCriteria,  // max_iterations | tolerance | timeout
    conflict_resolution: ResolutionPolicy,  // priority | voting | arbiter
}
```
Semantics: Multiple agents collaboratively satisfy a shared constraint set.
The AST captures WHAT must be satisfied and HOW agents coordinate, independent
of whether coordination happens via Matrix messages, shared PLATO tiles, or
FLUX-X inter-agent opcodes.

## ConstraintNode — Recursive AST Root
```rust
enum ConstraintNode {
    Bound(BoundNode),
    Delta(DeltaNode),
    Relation(RelationNode),
    Confidence(ConfidenceNode),
    Semantic(SemanticNode),
    Delegate(DelegateNode),
    CoIterate(CoIterateNode),
    And(Vec<ConstraintNode>),     // conjunction
    Or(Vec<ConstraintNode>),      // disjunction
    Not(Box<ConstraintNode>),     // negation
    Implies(Box<ConstraintNode>, Box<ConstraintNode>),  // implication
}
```

## Code Generation (All FROM AST, never TO AST)

### GUARD DSL Generator
```rust
fn to_guard(node: &ConstraintNode) -> String {
    match node {
        ConstraintNode::Bound(b) => format!("bound {} in [{}, {}] {};", b.signal, b.lower, b.upper, b.unit.unwrap_or_default()),
        ConstraintNode::Delta(d) => format!("temporal delta {} <= {} per {};", d.signal, d.max_delta, d.window),
        ConstraintNode::Delegate(del) => format!("delegate {} -> {} [{}] {{ {} }}", del.source_agent, del.target_agent, del.protocol, to_guard(&del.constraint)),
        // ...
    }
}
```

### FLUX-C Bytecode Generator
```rust
fn to_flux_c(node: &ConstraintNode) -> Vec<u8> {
    match node {
        ConstraintNode::Bound(b) => vec![
            PUSH, encode(b.lower), BITMASK_RANGE, encode(b.lower), encode(b.upper), ASSERT
        ],
        ConstraintNode::Delta(d) => vec![
            HIST_PUSH, HIST_DELTA, encode(d.window), PUSH, encode(d.max_delta), LTE, ASSERT
        ],
        // DelegateNode maps to FLUX-X CONSTRAINT_CHECK, not FLUX-C
        // This is where the two-ISA split matters
    }
}
```

### TLA+ Formula Generator
```rust
fn to_tla(node: &ConstraintNode) -> String {
    match node {
        ConstraintNode::Bound(b) => format!("{}Bound == {} <= {} /\\ {} <= {}", b.signal, b.lower, b.signal, b.signal, b.upper),
        ConstraintNode::Delta(d) => format!("{}Delta == {}[t] - {}[t-1] <= {}", b.signal, b.signal, b.signal, d.max_delta),
        // Temporal operators map naturally to TLA+ □ (always)
    }
}
```

### Coq Proposition Generator
```rust
fn to_coq(node: &ConstraintNode) -> String {
    match node {
        ConstraintNode::Bound(b) => format!("Theorem {}_bound : forall t, {} <= signal {} t <= {}.", b.signal, b.lower, b.signal, b.upper),
        // Proof obligations generated from AST structure
    }
}
```

### SystemVerilog Assertion Generator
```rust
fn to_sva(node: &ConstraintNode) -> String {
    match node {
        ConstraintNode::Bound(b) => format!("assert property (@(posedge clk) {} >= {} && {} <= {});", b.signal, b.lower, b.signal, b.upper),
        // Directly synthesizable — no translation ambiguity
    }
}
```

## Why This Matters for Certification

**DO-254 DAL A** requires traceability from requirements to implementation.
With the Universal AST:

1. Requirement → AST node (human-reviewed, language-independent)
2. AST node → FLUX-C bytecode (machine-generated, deterministic)
3. AST node → TLA+ property (machine-generated, model-checkable)
4. AST node → Coq theorem (machine-generated, proof-carrying)
5. AST node → SV assertion (machine-generated, synthesizable)

Every representation is a projection of the SAME semantic intent.
No human translation errors. No "works in Python but fails in Verilog" bugs.
The certification auditor reviews the AST, not 5 different language artifacts.

## The Leaky Abstraction This Kills

Without Universal AST:
- GUARD says `range(0, 150)` but FLUX encodes as `BITMASK_RANGE 0 150`
  → What if 150 overflows the 8-bit operand? GUARD author doesn't know.
- TLA+ says `vel ≤ 300` but Coq says `vel < 301`
  → Off-by-one between formal models. Proof is valid for wrong property.
- Python test uses float comparison, SV uses fixed-point
  → Test passes in simulation, fails on hardware.

With Universal AST:
- The BoundNode says exactly `(0, 150)` with type `Q16.16`
- Every generator receives the same node with the same type
- Overflow is caught at AST validation time, before any code generation
- All representations agree by construction

## Delegate and CoIterate as First-Class AST Nodes

This is Casey's key insight. `delegate` and `co_iterate` are not syntax sugar —
they're SEMANTIC OPERATIONS on the same level as `bound` and `delta`.

When FLUX-X needs to check a constraint on another agent's output:
- The DelegateNode captures WHO delegates to WHOM with WHAT protocol
- The FLUX-X generator emits CONSTRAINT_CHECK (bridge call)
- The TLA+ generator emits an inter-process temporal property
- The Coq generator emits a distributed system lemma

The SAME semantic operation, expressed correctly in each target domain,
because the AST is the single source of truth.

## Implementation Priority

1. **ConstraintNode enum in Rust** (flux-ast crate)
2. **GUARD parser → AST** (extend guard2mask)
3. **AST → FLUX-C bytecode** (extend guard2mask compiler)
4. **AST → TLA+** (new generator)
5. **AST → Coq** (new generator)
6. **AST → SystemVerilog assertions** (new generator)
7. **AST validation pass** (type checking, overflow detection, gas estimation)

This becomes `flux-ast` on crates.io — the universal constraint compiler's intermediate representation.
