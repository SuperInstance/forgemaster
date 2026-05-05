# CPU Scalar Benchmark — AMD Ryzen AI 9 HX 370

## Results
- Python scalar: 43.2M/s
- C scalar (single-thread, -O3 -march=native): 5.19B/s
- CPU cores: 24 (12C/24T, Zen 5)
- Projected 12T: 62.32B/s (if linear scaling)

## Comparison
| Target | Throughput | Safe-TOPS/W |
|--------|-----------|-------------|
| C scalar 1T | 5.19B/s | ~347M (at 15W) |
| C scalar 12T (projected) | 62.3B/s | ~4.15B (at 15W) |
| CUDA RTX 4050 burst | 620M/s | 63M (at 11W) |
| CUDA RTX 4050 sustained | 90M/s | ~23M (at 4W) |

## Key Insight
CPU scalar is MORE efficient than GPU for single-constraint checks.
GPU advantage: parallel constraint composition (run 5 constraints simultaneously).
For production: CPU for simple checks, GPU for complex multi-constraint programs.
