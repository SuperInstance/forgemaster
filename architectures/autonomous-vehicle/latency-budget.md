# Autonomous Vehicle ECU — Latency Budget

| Stage | Time | Cumulative | Notes |
|-------|------|------------|-------|
| Sensor capture (Camera/Radar/LiDAR) | 5-15 ms | 15 ms | Rolling shutter + sync |
| Preprocessing (object detection) | 8-12 ms | 27 ms | CUDA-accelerated YOLO/BEVFusion |
| Sensor fusion & state estimation | 3-5 ms | 32 ms | Kalman/EKF on GPU |
| FLUX constraint compilation (amortized) | 0.01 ms | 32 ms | Bytecode cached, recompiled on rule change |
| FLUX constraint execution (12K @ 100Hz) | 0.05 ms | 32 ms | GPU kernel launch + 12K INT8 evaluations |
| Safety monitor cross-check | 0.5 ms | 32.5 ms | Lockstep Cortex-R52 comparison |
| Actuator command generation | 0.8 ms | 33.3 ms | Brake/steer/throttle CAN-FD |
| Actuator physical response | 50-100 ms | — | Hydraulic brake lag dominates |
| **TOTAL (compute path)** | **~4.2 ms** | — | Well within 100ms end-to-end requirement |
| **TOTAL (physical response)** | **~100 ms** | — | Meets ISO 26262 ASIL-D braking latency |
