# ct-holonomy

Holonomy measurement on the Pythagorean manifold — angular deficit, Berry phase analogy.

## What It Does

- `holonomy_walk(start, steps, max_c)` — single random walk with per-step deficit
- `holonomy_batch(walks, steps, max_c)` — statistical analysis (mean, std, median)
- `berry_phase_fraction(walks, steps, max_c)` — deficit as fraction of 2π
- `angular_distance(a, b)` — circular distance on [0, 2π)

## The Physics

Holonomy measures the angular deficit accumulated during parallel transport
around a closed loop on a curved manifold. On the Pythagorean triple manifold,
this is the classical analog of the Berry phase from quantum mechanics.

## Install

```toml
[dependencies]
ct-holonomy = "0.1"
```

## License

MIT
