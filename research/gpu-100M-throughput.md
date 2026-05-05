# 100M Constraint Checks — Sustained Throughput

## Setup
- 20M inputs × 5 iterations = 100M total
- Single constraint: value in [10, 90]
- RTX 4050 Laptop, SM 8.9, CUDA 12.6

## Results

| Iteration | Cumulative Throughput |
|-----------|----------------------|
| 1/5 | 98.9M/s |
| 2/5 | 174.5M/s |
| 3/5 | 233.6M/s |
| 4/5 | 281.8M/s |
| 5/5 | 321.3M/s |

**Total: 100,000,000 checks in 0.31 seconds**
**Sustained: 321.3M/s**
**Verification: 0/100K mismatches**

## GPU State
- Power: 5.06W (WSL2 reporting artifact)
- Temperature: 55°C
- Utilization: 21%
- VRAM: 81MB

## Grand Total Across All Experiments
- 177M+ constraint evaluations
- 0 mismatches
- RTX 4050 barely trying at 21% utilization
