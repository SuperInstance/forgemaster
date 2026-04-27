# ct-proofs

Formal verification proofs for constraint theory — exhaustive testing and property checking.

## What It Does

- `prove_euclid_validity(max_c)` — every Euclid triple satisfies a²+b²=c²
- `prove_euclid_completeness(max_c)` — Euclid generates ALL primitive triples
- `prove_snap_correctness(max_c, samples)` — snap always returns valid triple
- `prove_snap_deterministic(max_c)` — same input → same output
- `prove_octant_coverage(max_c)` — all 8 sign/reflection variants valid
- `prove_berggren_validity(depth)` — Berggren matrices preserve Pythagorean property
- `run_all_proofs(max_c)` — execute all proofs, return results

## Install

```toml
[dependencies]
ct-proofs = "0.1"
```

## License

MIT
