# Zeitgeist Protocol ⚒️

FLUX transference specification and reference implementation.

The **Zeitgeist** is a composite CRDT semilattice capturing five dimensions of agent alignment:
- **Precision** — Deadband funnel convergence
- **Confidence** — Certainty via bloom filter + parity
- **Trajectory** — Trend via Hurst exponent
- **Consensus** — Cycle coherence with CRDT version vector
- **Temporal** — Beat grid rhythm coherence

## Merge Laws (Proven)

All three CRDT semilattice laws proven with 100-iteration randomized property tests:

| Law | Property |
|-----|----------|
| Commutative | `merge(a, b) == merge(b, a)` |
| Associative | `merge(merge(a, b), c) == merge(a, merge(b, c))` |
| Idempotent | `merge(a, a) == a` |

## Structure

```
zeitgeist-protocol/
├── docs/PROTOCOL.md          # Wire format specification
├── src/                      # Rust reference implementation
│   ├── lib.rs                # Public API
│   ├── packet.rs             # FLUX packet encode/decode
│   ├── zeitgeist.rs          # Composite CRDT
│   ├── precision.rs          # Deadband funnel
│   ├── confidence.rs         # Bloom + parity
│   ├── trajectory.rs         # Hurst exponent
│   ├── consensus.rs          # Holonomy + CRDT version vector
│   ├── temporal.rs           # Beat grid
│   └── merge.rs              # Merge law tests
├── python/                   # Python bindings
│   ├── zeitgeist.py
│   └── test_zeitgeist.py
├── ts/                       # TypeScript bindings
│   ├── zeitgeist.ts
│   └── test_zeitgeist.ts
└── Cargo.toml
```

## Run Tests

```bash
# Rust (reference)
cargo test

# Python
cd python && python3 -m pytest test_zeitgeist.py -v

# TypeScript
cd ts && npx tsx test_zeitgeist.ts
```

## Wire Format

See [`docs/PROTOCOL.md`](docs/PROTOCOL.md) for the full binary wire format specification.

Each FLUX packet carries an arbitrary payload + a CBOR-encoded Zeitgeist, with XOR parity integrity checking.
