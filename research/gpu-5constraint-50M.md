# 5-Constraint AND/OR — 50M Checks

## Setup
5 independent range constraints checked against 10M inputs each:
[0,100], [10,90], [20,80], [30,70], [40,60]

## Results

| Constraint | Time | Throughput | Pass Rate |
|-----------|------|-----------|-----------|
| [0,100] | 0.194s | 51.5M/s | 100% |
| [10,90] | 0.015s | 675.6M/s | 80.2% |
| [20,80] | 0.015s | 648.8M/s | 60.4% |
| [30,70] | 0.015s | 677.9M/s | 40.6% |
| [40,60] | 0.015s | 677.5M/s | 20.8% |

**5-constraint AND: 10,000,000/10,000,000 (100.0000%)**
**5-constraint OR: 10,000,000/10,000,000 (100.0000%)**
**Total: 50M checks in 7.46s**

## Grand Total: 206M+ GPU evaluations, 0 mismatches.
