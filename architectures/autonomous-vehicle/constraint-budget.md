# Autonomous Vehicle ECU — Constraint Budget

| Constraint Category | Count | Type | Update Rate | Source |
|---------------------|-------|------|-------------|--------|
| Minimum following distance | 2,400 | Range (INT8) | 100 Hz | Radar/LiDAR fusion |
| Lane boundary adherence | 1,800 | Range/Enum | 100 Hz | Camera + HD map |
| Speed limit compliance | 800 | Range (INT8) | 100 Hz | GNSS + camera (signs) |
| Pedestrian/cyclist safety zone | 2,200 | Range/Geofence | 100 Hz | Camera + LiDAR |
| Traffic signal/state | 600 | Enum (INT8) | 100 Hz | Camera + V2X |
| Occupancy grid collision | 3,200 | Boolean grid | 100 Hz | LiDAR + Radar |
| Vehicle dynamics envelope | 600 | Range (FP16-safe) | 100 Hz | IMU + wheel odometry |
| Emergency braking threshold | 400 | Threshold | 100 Hz | All sensors fused |
| **TOTAL** | **12,000** | Mixed INT8/Enum/Bool | 100 Hz | — |

At 100 Hz with 12,000 constraints: 1.2 million constraint evaluations per second. FLUX on Drive Orin (~120B constraints/sec effective) provides **100,000x headroom**.
