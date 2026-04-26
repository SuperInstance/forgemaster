# pythagorean-treemap

Squarified treemap visualization of Pythagorean triple angular density.

## What It Does

- **Density analysis** — bins triple angles into N angular segments, computes density
- **Squarified treemap** — space-filling layout with aspect ratios near 1:1
- **ASCII rendering** — 2D text visualization of the density treemap
- **Full-circle generation** — all 8 octants for uniform distribution (CV < 0.3)

## Install

```toml
[dependencies]
pythagorean-treemap = "0.1"
```

## Quick Start

```rust
use pythagorean_treemap::*;

let triples = generate_triples(1000);
let bins = analyze_density(&triples, 18);
let tree = build_treemap(&bins, Rect::new(0.0, 0.0, 1.0, 1.0));
println!("{}", render_ascii(&tree, 40, 20));
```

## License

MIT
