# ct-farey

Farey sequence — optimal rational enumeration for Pythagorean snap quality bounds.

## What It Does

- `farey(n)` — generate Farey sequence F_n (all reduced fractions ≤ n)
- `farey_neighbors(value, n)` — bracket a value in the Farey sequence
- `max_gap(n)` — worst-case gap in F_n (snap quality bound)
- `euler_totient(n)` — Euler's totient function
- `snap_quality_bound(max_c)` — provable worst-case angular error

## Install

```toml
[dependencies]
ct-farey = "0.1"
```

## License

MIT
