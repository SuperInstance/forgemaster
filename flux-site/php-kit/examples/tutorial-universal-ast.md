# Universal Constraint AST — Single Source of Truth

## The Problem: Representation Drift

A safety constraint exists in 5+ places:

1. **Requirements doc** — "altitude must be 0-15000 ft"
2. **Source code** — `if altitude > 15000: fault()`
3. **Test cases** — `assert check(15001) == FAULT`
4. **Formal model** — Coq definition of altitude range
5. **Hardware** — RTL comparator threshold

When someone changes the altitude limit to 12000, which representations get updated? In practice: maybe 2 out of 5. The others drift. Representation drift is the #1 cause of certification failures.

## The Solution: Universal AST

The Universal Constraint AST is the **single source of truth**. Every representation is GENERATED from it:

```
                    Universal AST
                         │
            ┌────────────┼────────────┐
            │            │            │
        GUARD text   FLUX bytecode   Coq proof
            │            │            │
        Human reads  VM executes   Formal verifies
            │            │            │
        ┌───┴───┐   ┌───┴───┐   ┌───┴───┐
        │ Docs  │   │ Tests │   │  SV   │
        └───────┘   └───────┘   └───────┘
```

Change the AST node → regenerate everything. No drift possible by construction.

## The 7 Node Types

### 1. Bound (Range Constraints)

```rust
BoundNode::Range { min: 0, max: 150 }
BoundNode::Domain { mask: 0x3F }
BoundNode::Value { allowed: [0, 1, 2] }
```

Generated representations:
- GUARD: `range(0, 150)` / `bitmask(0x3F)` / `whitelist([0, 1, 2])`
- FLUX: `BITMASK_RANGE 0 150` / `CHECK_DOMAIN 0x3F` / `PUSH+EQ+JNZ` chain
- Coq: `bounded n min max` inductive type

### 2. Delta (Rate-of-Change)

```rust
DeltaNode {
    variable: "velocity",
    max_rate: 10.0,
    unit: "m/s²",
}
```

Generated:
- GUARD: `drift(velocity, max=10)`
- FLUX: `DRIFT target actual` opcode
- Coq: `continuous_derivative constraint`

### 3. Relation (Between Variables)

```rust
RelationNode {
    left: "thrust",
    op: LessThan,
    right: "weight * 1.5",
}
```

Generated:
- GUARD: `thrust < weight * 1.5`
- FLUX: `PUSH LOAD(thrust) LOAD(weight) PUSH 1.5 MUL CMP_LT ASSERT`
- Coq: `forall t, thrust t < 1.5 * weight t`

### 4. Confidence (Probability-Weighted)

```rust
ConfidenceNode {
    constraint: Box<BoundNode>,
    confidence: 0.95,
}
```

For probabilistic safety: "I'm 95% confident the constraint holds." Lower confidence → higher gas cost for the check.

### 5. Semantic (Intent-Preserving)

```rust
SemanticNode {
    intent: "never_exceed_max_altitude",
    encoding: vec![...],
}
```

The intent is preserved across all representations. An auditor sees "never_exceed_max_altitude" regardless of whether they're reading GUARD, FLUX, or Coq.

### 6. Delegate (Inter-Agent)

```rust
DelegateNode {
    source: "safety_monitor",
    target: "planner",
    constraint: Box<BoundNode>,
    protocol: CoIterate,
}
```

See [Multi-Agent Delegation](/learn/delegation) for full details.

### 7. CoIterate (Collaborative)

```rust
CoIterateNode {
    agents: ["perception", "planner"],
    constraint: Box<BoundNode>,
    max_rounds: 5,
    convergence: 1.0,
}
```

## Combinators

Nodes are combined with logical combinators:

```rust
// AND: both must pass
And(Box<Node>, Box<Node>)

// OR: either can pass
Or(Box<Node>, Box<Node>)

// NOT: negation
Not(Box<Node>)

// IMPLIES: if A then B
Implies(Box<Node>, Box<Node>)
```

Example:
```rust
let constraint = And(
    Box::new(BoundNode::Range { min: 0, max: 150 }),  // altitude
    Box::new(Implies(
        Box::new(RelationNode::gt("altitude", 100)),   // if altitude > 100
        Box::new(BoundNode::Range { min: 0, max: 50 }), // then velocity ≤ 50
    )),
);
```

GUARD output:
```guard
constraint flight_safety @priority(HARD) {
    range(0, 150)
    implies(
        altitude > 100,
        range(0, 50)
    )
}
```

## The Generation Chain

```
AST ──► GUARD (human-readable)
    ├──► FLUX-C bytecode (certified VM execution)
    ├──► FLUX-X bytecode (general compute)
    ├──► TLA+ model (temporal logic verification)
    ├──► Coq definitions (proof assistant)
    ├──► SystemVerilog RTL (hardware implementation)
    ├──► Python tests (unit tests from constraints)
    └──► Documentation (constraint specs from metadata)
```

Each generator is a pure function: `generate(ast_node) → representation`. No translation ambiguity because there is no translation — only generation.

## Why Not Bidirectional Translation?

Bidirectional translation (GUARD ↔ FLUX ↔ Coq) seems flexible but introduces representation drift:

1. GUARD has features FLUX doesn't (comments, formatting)
2. FLUX has features Coq doesn't (gas metering, fault handling)
3. Coq has features GUARD doesn't (dependent types, tactics)

Round-tripping loses information. The AST approach avoids this by making the AST the **maximal representation** — it contains everything, and each generator produces a **projection** (subset relevant to that format).

## Install

```rust
// Cargo.toml
[dependencies]
flux-ast = "0.1.0"
guard2mask = "0.1.2"
flux-vm = "0.2.0"
```

```rust
use flux_ast::{Node, BoundNode, Compiler};
use guard2mask::Parser;

// Parse GUARD to AST
let ast = Parser::parse(r#"
    constraint alt @priority(HARD) {
        range(0, 150)
    }
"#)?;

// Generate FLUX bytecode from AST
let bytecode = ast.compile()?;

// Execute on VM
let mut vm = FluxVM::new(1000);
vm.execute(&bytecode, 100)?; // PASS
vm.execute(&bytecode, 200)?; // FAULT
```

## Next

- [Multi-Agent Delegation](/learn/delegation) — DelegateNode and CoIterateNode in action
- [Formal Verification](/learn/formal) — AST → Coq generation
- [Hardware Implementation](/learn/hardware) — AST → SystemVerilog generation
