# constraint-theory-metrics

Benchmarking and analysis tools for Pythagorean manifold operations.

## What It Does

- **DistributionAnalysis** — angular distribution metrics (CV, uniformity test, histogram)
- **CorrectnessReport** — verify snap strategies against brute-force ground truth
- **BenchmarkResult** — measure snap query throughput (qps)
- Pretty-print helpers for comparison tables and histograms

## Install

```toml
[dependencies]
constraint-theory-metrics = "0.1"
```

## Quick Start

```rust
use constraint_theory_metrics::*;

let angles: Vec<f64> = vec![/* ... */];
let analysis = DistributionAnalysis::from_angles(&angles, 18);
println!("CV: {:.3}, uniform: {}", analysis.cv, analysis.is_uniform);
```

## License

MIT
