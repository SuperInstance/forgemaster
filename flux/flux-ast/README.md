# flux-ast

**Universal Constraint AST — single source of truth for constraint semantics.**

Every downstream representation (GUARD DSL, FLUX-C bytecode, TLA+, Coq, SystemVerilog, Python) is GENERATED from this AST. Never hand-written and then "translated."

## Why This Exists

Without a universal AST, constraints expressed in different languages can diverge:
- GUARD says `range(0, 150)` but FLUX encodes as `BITMASK_RANGE 0 150` — what if 150 overflows 8-bit operands?
- TLA+ says `vel ≤ 300` but Coq says `vel < 301` — off-by-one between formal models
- Python uses float, SystemVerilog uses fixed-point — test passes in simulation, fails on hardware

The AST eliminates these by being the single source of truth.

## AST Node Types

| Node | Semantics | Severity |
|------|-----------|----------|
| `BoundNode` | `lower ≤ signal ≤ upper` | HARD/SOFT/DEFAULT |
| `DeltaNode` | `|signal[t] - signal[t-w]| ≤ max_delta` | HARD/SOFT/DEFAULT |
| `RelationNode` | `relation(signal_a, signal_b)` | HARD/SOFT/DEFAULT |
| `ConfidenceNode` | `signal.confidence ≥ threshold` | HARD/SOFT/DEFAULT |
| `SemanticNode` | `signal.class ∈ allowed_classes` | HARD/SOFT/DEFAULT |
| `DelegateNode` | Agent A delegates constraint to Agent B | Protocol: Sync/Async/CoIterate |
| `CoIterateNode` | Multiple agents solve shared constraints | Convergence + conflict resolution |

Plus logical combinators: `And`, `Or`, `Not`, `Implies`

## Usage

```rust
use flux_ast::*;

let constraint = ConstraintNode::And(vec![
    ConstraintNode::Bound(BoundNode {
        signal: SignalRef::local("velocity"),
        lower: Value::Integer(0),
        upper: Value::Integer(300),
        severity: Severity::Hard,
    }),
    ConstraintNode::Delta(DeltaNode {
        signal: SignalRef::local("velocity"),
        max_delta: Value::Integer(15),
        window: Window::PerFrame,
        severity: Severity::Hard,
    }),
]);

// All generators read from the same AST
assert_eq!(constraint.leaf_count(), 2);
assert_eq!(constraint.max_severity(), Severity::Hard);
```

## License

MIT OR Apache-2.0
