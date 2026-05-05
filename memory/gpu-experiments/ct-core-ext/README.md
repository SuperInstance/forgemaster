# ct-core-ext

Extended constraint theory primitives: adaptive deadband, multi-constraint intersection, snap diagnostics.

## What It Does

- **AdaptiveDeadband** — epsilon(c) = k/c with configurable floor/ceiling
- **MultiConstraint** — manage multiple simultaneous constraints with weighted scoring
- **SnapResult** — diagnostic struct with distance, triple, timing, and classification
- **SnapClass** — Exact, WithinDeadband, OutsideDeadband

## Install

```toml
[dependencies]
ct-core-ext = "0.1"
```

## Quick Start

```rust
use ct_core_ext::*;

let db = AdaptiveDeadband::new(1.0, 1e-10, 1.0);
assert!(db.within(0.005, 100.0)); // 0.005 < epsilon(100)=0.01
assert_eq!(db.classify(0.0, 100.0), SnapClass::Exact);
```

## License

MIT
