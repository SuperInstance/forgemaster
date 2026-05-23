# deadband-rs

Forgemaster's vessel — the Cocapn fleet constraint-theory specialist workspace. Contains the `deadband` crate, 43+ clock-sync and drift experiments, fleet coordination tools, and the constraint-theory proof portfolio.

## What's In Here

### The `deadband` Crate

A Rust library implementing deadband filtering and constraint-theory math primitives:

| Module | What It Does |
|--------|-------------|
| `div360` | Exact integer division by 360 for angle arithmetic (zero drift) |
| `eisenstein` | Snap Cartesian points to nearest Eisenstein integer lattice point |
| `bma` | Berlekamp-Massey algorithm over GF(2) — find shortest LFSR for a binary sequence |
| `hpdf` | Uniform sampling over a regular hexagon (rejection method) |
| `fib_spline` | Fibonacci spiral vector search on circle/sphere |
| `shell` | 2×2 matrix eigendecomposition and dynamical classification (node, saddle, spiral, center) |

### Experiments (43+)

Systematic exploration of clock synchronization algorithms under fleet conditions:

- **PTP vs NTP vs Cristian vs EWMA** head-to-head comparisons
- **Production factorials** — combined stress testing
- **Drift analysis** — bounded vs unbounded drift under various topologies
- **Anti-fragile timing** — PTP confirmed most consistent under adversarial conditions

### Fleet Infrastructure

- `.keeper/` — Heartbeat and monitoring
- `.local-plato/` — Local PLATO knowledge base
- `captains-log/` — Session state and mission tracking
- `portfolio/` — Constraint-theory proof products
- `vessel/` — Ship systems (bridge, engine room, crew)

## The Deadband Concept

A deadband filter eliminates noise below a perceptibility threshold:

```
L ≤ k  →  not perceivable (filtered)
L > k  →  perceivable (passed through)
```

This is the same principle used in thermostat hysteresis, audio noise gates, and constraint-theory tolerance — if the change doesn't matter, don't propagate it.

## Building the Crate

```bash
cargo build --release
cargo test
```

The binary (`src/main.rs`) runs an interactive demo of all modules.

## Key Results

- `/360 arithmetic`: **zero drift** across all 129,600 integer angle pairs
- **PTP**: strictly dominant over Cristian/EWMA/hybrid for fleet clock sync
- **Churn fix**: warm-up queues eliminate unbounded drift (boot-to-mean = 99.97% reduction)
- **Production config**: combined stress breaks individual component guarantees — documented failure mode

## Fleet Context

This is Forgemaster's workspace in the Cocapn fleet (SuperInstance org). The fleet runs 9 agents coordinated through I2I protocol and PLATO knowledge system.

Related repos:
- [constraint-theory-core](https://github.com/SuperInstance/constraint-theory-core) — Constraint engine library
- [i2i-protocol](https://github.com/SuperInstance/i2i-protocol) — Inter-agent messaging
- [superinstance-ffi](https://github.com/SuperInstance/superinstance-ffi) — C FFI bindings for fleet math

## License

Apache-2.0
