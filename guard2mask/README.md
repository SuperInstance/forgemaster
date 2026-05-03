# guard2mask

**GUARD DSL to GDSII mask compiler — compiles safety constraints to silicon via patterns.**

Translates human-readable safety constraints (GUARD DSL) into FLUX bytecode and ultimately GDSII via patterns for FLUX-LUCID hardware.

## GUARD DSL Example

```guard
constraint eVTOL_altitude @priority(HARD) {
    range(activation[0], 0, 15000)
    whitelist(activation[1], {HOVER, ASCEND, DESCEND, LAND, EMERGENCY})
    bitmask(activation[2], 0x3F)
    thermal(2.5)
}
```

## Constraint Types

| Check | Syntax | Compiles To |
|-------|--------|-------------|
| Range bounds | `range(var, min, max)` | BITMASK_RANGE + ASSERT |
| Allowed values | `whitelist(var, {v1, v2})` | Sequential EQ + OR |
| Bit mask | `bitmask(var, mask)` | AND + ASSERT |
| Power budget | `thermal(budget_w)` | CMP_GE + ASSERT |
| Active neurons | `sparsity(min_count)` | CMP_GE + ASSERT |

## Priority Levels

- `@priority(HARD)` — Never relax, always enforced
- `@priority(SOFT)` — May weaken under conflict
- `@priority(DEFAULT)` — Relax first under resource pressure

## Usage

```rust
use guard2mask::{parse_guard, solve, generate_patterns};

let constraints = parse_guard(source)?;
let assignment = solve(&constraints)?;
let gdsii = generate_patterns(&assignment);
```

## License

MIT OR Apache-2.0
