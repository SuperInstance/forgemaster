# ct-bench

Reproducible benchmark suite for constraint theory. One command, verified numbers.

## Install

```toml
[dependencies]
ct-bench = "0.1"
```

## Quick Start

```rust
use ct_bench::{BenchConfig, bench_snap, verify_snap, format_comparison};

let config = BenchConfig::quick();
let (binary, brute) = bench_snap(&config);
let report = verify_snap(&config);

println!("{}", format_comparison(&[binary, brute]));
println!("Agreement: {:.2}%", report.agreement_rate * 100.0);
```

## Reproduce

```bash
cargo bench          # criterion benchmarks
cargo test           # 8 tests, 100% agreement
```

## Benchmarks (RTX 4050, WSL2, rustc 1.95)

| Strategy | Queries/s | vs Brute |
|----------|-----------|----------|
| binary_search | ~10M+ | 300x+ |
| brute_force | ~30K | 1x |

## License

MIT
