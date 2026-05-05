# Agent 1: Autonomous Vehicle ECU

**Domain:** SAE Level 4/5 autonomous driving — urban and highway
**Architect:** Agent 1 (Automotive Safety-Critical Systems)

## System Block Diagram

```
+------------------------------------------------------------------+
|                     AUTONOMOUS VEHICLE ECU                        |
|                     FLUX Constraint Engine                        |
+------------------------------------------------------------------+
|                                                                   |
|  +-------------+     +-------------+     +------------------+   |
|  |  SENSOR     |     |   SENSOR    |     |    SENSOR        |   |
|  |  FUSION     |---->|  FUSION     |---->|   FUSION         |   |
|  |  FRONT      |     |   REAR      |     |    PERIPHERAL    |   |
|  |  (Camera,   |     |   (Radar,   |     |    (LiDAR,       |   |
|  |   Radar,    |     |   Camera,   |     |    Ultrasonic,   |   |
|  |   LiDAR)    |     |   Ultrasonic|     |    GNSS, IMU)    |   |
|  +------+------+     +------+------+     +---------+--------+   |
|         |                    |                      |            |
|         v                    v                      v            |
|  +------+--------------------+----------------------+--------+ |
|  |              SENSOR PREPROCESSING LAYER                     | |
|  |         (CUDA-based: object detection, tracking, SLAM)      | |
|  +------+--------------------+----------------------+--------+ |
|         |                    |                      |            |
|         v                    v                      v            |
|  +------+--------------------+----------------------+--------+ |
|  |              FLUX CONSTRAINT ENGINE (Drive Orin)            | |
|  |  +-----------------------------------------------------+  | |
|  |  |  GUARD DSL Compiler -> FLUX-C Bytecode (43 opcodes) |  | |
|  |  |  GPU Kernel Scheduler  |  Constraint Batch Queue       |  |
|  |  |  INT8 x8 Packed Execution  |  90.2B checks/sec         |  |
|  |  +-----------------------------------------------------+  | |
|  +------+--------------------+----------------------+--------+ |
|         |                    |                      |            |
|         v                    v                      v            |
|  +------+--------------------+----------------------+--------+ |
|  |              SAFETY MONITOR (Lockstep Cortex-R52)           | |
|  |         Watchdog | Cross-check | Fail-safe fallback        | |
|  +------+--------------------+----------------------+--------+ |
|         |                    |                      |            |
|         v                    v                      v            |
|  +------+--------------------+----------------------+--------+ |
|  |              VEHICLE ACTUATION                            | |
|  |    Braking ECU    |    Steering ECU    |    Throttle ECU   | |
|  +-------------------------------------------------------------+
|                                                                   |
|  [REDUNDANT CHANNEL B: Identical hardware, hot standby]          |
|                                                                   |
+------------------------------------------------------------------+
```

## Constraint Budget

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

At 100 Hz with 12,000 constraints: 1.2 million constraint evaluations per second. FLUX on Drive Orin (256 CUDA cores @ 1.7 GHz, ~120B constraints/sec effective) provides **100,000x headroom**.

## Hardware Selection

**Primary: NVIDIA Drive Orin (Jetson AGX Orin automotive variant)**
- **GPU:** 2048 CUDA cores, 64 Tensor cores, INT8 x8 packing supported
- **CPU:** 12-core Arm Cortex-A78AE (functional safety capable)
- **Memory:** 32 GB LPDDR5 (204 GB/s bandwidth, exceeds FLUX 187 GB/s need)
- **TDP:** 60W (configurable 15W-60W)
- **Safety:** ISO 26262 ASIL-D capable hardware, lockstep cluster

**Secondary (Channel B):** Identical Drive Orin module, hot standby.
**Safety monitor:** Infineon Aurix TC397 (tri-core lockstep) for cross-check and watchdog.

## Latency Budget

| Stage | Time | Cumulative | Notes |
|-------|------|------------|-------|
| Sensor capture (Camera/Radar/LiDAR) | 5-15 ms | 15 ms | Rolling shutter + sync |
| Preprocessing (object detection) | 8-12 ms | 27 ms | CUDA-accelerated YOLO/BEVFusion |
| Sensor fusion & state estimation | 3-5 ms | 32 ms | Kalman/EKF on GPU |
| FLUX constraint compilation (amortized) | 0.01 ms | 32 ms | Bytecode cached |
| FLUX constraint execution (12K @ 100Hz) | 0.05 ms | 32 ms | GPU kernel launch + 12K INT8 evals |
| Safety monitor cross-check | 0.5 ms | 32.5 ms | Lockstep Cortex-R52 comparison |
| Actuator command generation | 0.8 ms | 33.3 ms | Brake/steer/throttle CAN-FD |
| Actuator physical response | 50-100 ms | — | Hydraulic brake lag dominates |
| **TOTAL (compute path)** | **~4.2 ms** | — | Well within 100ms end-to-end requirement |
| **TOTAL (physical response)** | **~100 ms** | — | Meets ISO 26262 ASIL-D braking latency |

## Redundancy Strategy

**Architecture: Dual hot standby with cross-check**

| Element | Implementation |
|---------|---------------|
| Channel A | Drive Orin primary — executes full perception + planning + FLUX |
| Channel B | Drive Orin secondary — mirrored execution, synchronized state |
| Cross-check | Infineon Aurix TC397 compares actuator commands from A and B every 500 us |
| Voting | If A and B diverge > 5%, TC397 commands safe state (max braking, lane keep) |
| Fail-safe | Loss of either channel triggers degraded mode (min risk maneuver, pull over) |
| Watchdog | 1 ms hardware watchdog on each Orin; missed heartbeat → channel disable |

## Power Budget

| Component | Power (W) | Notes |
|-----------|-----------|-------|
| Drive Orin (Channel A) | 35 | Active compute, 100% duty |
| Drive Orin (Channel B) | 20 | Hot standby, reduced clock |
| Infineon Aurix TC397 | 3 | Safety monitor, always on |
| Sensor front-ends (Camera x8, Radar x4, LiDAR x1) | 45 | Includes PHYs, serializers |
| Network switch (10GbE TSN) | 8 | Time-sensitive networking |
| Cooling (active, sealed) | 12 | IP67 automotive enclosure |
| DC-DC conversion loss (10%) | 12 | 48V -> 12V -> 5V/3.3V |
| **TOTAL** | **135 W** | — |
| FLUX compute specifically | ~42 W | 2x Orin GPU partitions @ ~21W each |

## Certification Path

| Standard | Level | Approach |
|----------|-------|----------|
| ISO 26262 | ASIL-D (highest) | 1oo2 dual-channel decomposition with diagnostic coverage > 99% |
| UL 4600 | — | Safety case argumentation for ML-based perception |
| SAE J3016 | Level 4/5 | Operational design domain (ODD) constraint enforcement via FLUX |
| UN R157/R79 | — | ALKS / steering regulation compliance via GUARD DSL rules |

**FLUX-specific certification argument:**
- Galois connection proof (38 formal proofs) provides **semantic preservation** argument
- Zero differential mismatches across 10M+ inputs provide **empirical equivalence** evidence
- 43-opcode ISA is **bounded complexity**, enabling complete test coverage (MC/DC achievable)
- Deterministic execution time supports **WCET analysis**

## Estimated Cost

| Cost Item | Amount (USD) |
|-----------|-------------|
| Drive Orin module x2 | $3,000 |
| Infineon Aurix TC397 + support | $400 |
| 8x automotive camera modules | $1,200 |
| 4x 77GHz radar modules | $2,000 |
| 1x 128-beam LiDAR | $2,500 |
| TSN Ethernet switch + cabling | $600 |
| IP67 enclosure + thermal solution | $1,200 |
| PCB (12-layer, high-speed) x2 | $800 |
| BOM subtotal | **$11,700** |
| NRE (GUARD DSL rule development, ASIL-D process) | $250,000 |
| Certification testing (TUV/Exida) | $180,000 |
| **Total per vehicle (amortized NRE over 10K units)** | **$8,500** |
| Total at volume (100K units, ASIC transition) | **$3,200** |
