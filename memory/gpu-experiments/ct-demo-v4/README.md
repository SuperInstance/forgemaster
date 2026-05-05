# constraint-theory-demo

Self-validating constraint theory demo — proves Pythagorean manifold snap is exact, drift-free, and consistent.

## What It Does

1. **Generates** all primitive Pythagorean triples up to `max_c`, mirrored across 8 octants
2. **Verifies** 100% binary-search / brute-force agreement over 100K random queries
3. **Checks** all triples satisfy x² + y² = c² (zero violations)
4. **Measures** holonomy (bounded accumulated phase error)
5. **Proves** zero floating-point drift

## Run

```
cargo run --release
```

Exit code 0 = all checks passed, 1 = failure detected.

## Sample Output

```
RESULT: ALL CHECKS PASSED ✓
Consistency:  100000/100000  |  Violations: 0/8296
Holonomy: 0.2133 rad  |  Drift: 0.0e0
Throughput: 162297 qps  |  Triples: 8296
```

## Key Results

- **100% agreement** binary search vs brute force
- **Zero drift** — exact integer arithmetic
- **162K qps** at max_c=10,000
- **Bounded holonomy** — circle topology ensures stability

## License

MIT
