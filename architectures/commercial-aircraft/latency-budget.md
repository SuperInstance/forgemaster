# Commercial Aircraft FMS — Latency Budget

| Stage | Time | Cumulative | Notes |
|-------|------|------------|-------|
| Sensor acquisition (ARINC 429/AFDX) | 2-10 ms | 10 ms | Protocol + bus latency |
| Input validation & filtering | 1 ms | 11 ms | CRC, range, rate-of-change checks |
| State estimation (Kalman) | 3 ms | 14 ms | Triple-channel independent computation |
| FLUX constraint compilation | 0 ms | 14 ms | Bytecode pre-loaded, no runtime compile |
| FLUX constraint execution (5K @ 50Hz) | 0.1 ms | 14.1 ms | FPGA pipeline, fully unrolled |
| 2oo3 voter comparison | 0.5 ms | 14.6 ms | Bitwise comparison of outputs |
| Output generation (ARINC 429/AFDX) | 2 ms | 16.6 ms | Format + queue |
| Actuator servo loop | 20-50 ms | — | Hydraulic flight control surfaces |
| **TOTAL (compute path)** | **~12 ms** | — | Meets DO-178C 100 ms control loop requirement |
| **TOTAL (with actuation)** | **~50 ms** | — | Well within aircraft dynamics time constants |
