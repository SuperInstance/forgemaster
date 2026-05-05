# SQLite Constraint Store

Persists constraint check history and violation records to SQLite.

## Build & Test

```bash
cd flux-sqlite/
cargo test
```

## Usage

```rust
use flux_sqlite::{ConstraintStore, ViolationRecord, CheckRecord};

let store = ConstraintStore::open("constraints.db").unwrap();
store.record_check(&CheckRecord { /* ... */ }).unwrap();
```

## Performance

~18,000 inserts/sec in WAL mode (SSD, single writer thread).
