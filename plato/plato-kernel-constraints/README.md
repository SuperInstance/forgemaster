# plato-kernel-constraints

Constraint engine extracted from plato-kernel — first-person permission filtering with assertive markdown constraints.

Extracted from the plato-kernel constraint_engine module (443 lines) as a standalone publishable crate.

## What It Does

**Two core components:**

### 1. ConstraintEngine — Permission Filtering
Entities in PLATO rooms have permission matrices that govern what they can see and do. The `ConstraintEngine` checks commands against these matrices:

- `Allow` — action is permitted
- `Deny` — action is blocked with a `ConstraintViolation`
- `RequestApproval` — action requires approval from designated approvers

```rust
use plato_kernel_constraints::{ConstraintEngine, Command, ConstraintMatrix, Constraint, FilterType};

let engine = ConstraintEngine::new();
let matrix = ConstraintMatrix {
    identity: "@visitor".into(),
    room: "garden".into(),
    constraints: vec![
        Constraint { id: "view_room".into(), description: "Can view room".into(), enabled: true, filter_type: FilterType::Allow },
        Constraint { id: "admin_commands".into(), description: "Admin only".into(), enabled: true, filter_type: FilterType::Deny },
    ],
};

let result = engine.check(&matrix, &Command::from_string("look fern"));
assert_eq!(result, ConstraintResult::Allow);
```

### 2. ConstraintAuditor — Assertive Markdown

Parse Markdown bullet points as runtime assertions. Inspired by the PLATO lesson loop (1970s) where students couldn't advance without passing the current block.

```rust
use plato_kernel_constraints::{ConstraintAuditor, AuditOutcome};

let markdown = r#"
## Rules
- The user's name must be capitalized.
- Output cannot contain profanity.
- Links should be https.
"#;

let auditor = ConstraintAuditor::from_markdown(markdown);

// Lowercase output fails "must be capitalized" → RetryRequired
assert!(matches!(auditor.audit("hello world"), AuditOutcome::RetryRequired(_)));

// Capitalized output passes
assert!(matches!(auditor.audit("Hello World — Capitalized."), AuditOutcome::Pass));
```

## Assertion Kinds

| Kind | Trigger | Behavior |
|------|---------|----------|
| `Must` | "must", "shall", "always" | Hard requirement — retry on failure |
| `MustNot` | "cannot", "must not", "never" | Hard prohibition — retry on violation |
| `Should` | "should", "ought" | Soft recommendation — warn but allow |

## Design Philosophy

This is constraint theory applied to agent governance. No omniscience — entities see only what permissions allow. The PLATO tradition of "Cave of Evals" lives here: assertions are not suggestions, they are constraints that shape behavior.

## License

MIT
