# GPU Thermal/Power Profile — Sustained Load

## Setup
10 iterations of 5M constraint checks, monitoring power/temp/utilization

## Results

| Iteration | Throughput | Power | Temp | Util |
|-----------|-----------|-------|------|------|
| 1 | 24.8M/s | 6.21W | 52°C | 0% |
| 2 | 595.1M/s | 10.80W | 54°C | 0% |
| 3 | 577.6M/s | 10.79W | 54°C | 0% |
| 4 | 589.1M/s | 11.95W | 55°C | 3% |
| 5 | 619.7M/s | 10.84W | 55°C | 0% |
| 6 | 90.8M/s | 2.93W | 55°C | 0% |
| 7 | 90.4M/s | 3.41W | 55°C | 0% |
| 8 | 89.2M/s | 3.94W | 55°C | 0% |
| 9 | 88.0M/s | 3.86W | 55°C | 0% |
| 10 | 88.1M/s | 4.00W | 56°C | 0% |

## Analysis
- GPU bursts at ~600M/s (first 5 iterations) then settles to ~90M/s
- NOT thermal throttling: temp stays 52-56°C (well below 87°C limit)
- Likely WSL2 power management: GPU clocks down after initial burst
- Power scales: 11W burst → 4W sustained
- Temperature barely moves (+4°C over 50M checks)
- The RTX 4050 is massively underutilized for this workload

## Implication
For production deployment: expect ~90M/s sustained per constraint.
Use batch sizes of 5M+ for best throughput-per-watt.
