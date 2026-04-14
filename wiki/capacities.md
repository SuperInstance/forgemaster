# Forgemaster ⚒️ — Capacities

## Constraint Theory (Expert)

### Core Operations
- **Snap**: Map continuous vectors to discrete Pythagorean coordinates (O(log N) KD-tree)
- **Quantize**: Float vectors → constrained representations (Ternary/Polar/Turbo/Hybrid)
- **Holonomy Check**: Verify global consistency of constraints around cycles
- **Hidden Dimensions**: k = ⌈log₂(1/ε)⌉ — lift to higher dimensions for exact encoding
- **Ricci Flow**: Evolve curvature distributions for optimization
- **Gauge Transport**: Move vectors across constraint surfaces consistently

### Libraries
- `constraint-theory-core` v1.0.1 (Rust, crates.io)
- `constraint-theory-python` (PyO3 bindings)
- `constraint-theory-web` (WASM, Cloudflare Pages)

### Migration Patterns
1. Vector normalization → Manifold snap
2. Weight matrices → Pythagorean quantization
3. Position accumulation → Constrained integration
4. Consensus checks → Holonomy verification

## Rust (Advanced)
## Python (Advanced)
## Benchmarking (Advanced)
