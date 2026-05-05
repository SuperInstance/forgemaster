## Agent 8: Industrial Robot Cell Safety System

**Domain:** Collaborative robot (cobot) and industrial robot workcell
**Architect:** Agent 8 (Industrial Automation & Functional Safety)

### System Block Diagram

```
+------------------------------------------------------------------+
|              INDUSTRIAL ROBOT CELL SAFETY SYSTEM                    |
|                    FLUX Constraint Engine                         |
+------------------------------------------------------------------+
|                                                                   |
|  +-------------------------------------------------------------+|
|  |                    SAFETY-RELATED CONTROL                    ||
|  |                                                              ||
|  |  +------------------+  +------------------+  +-------------+||
|  |  |  NVIDIA Jetson   |  |  Safety PLC      |  |  Light curtain||
|  |  |  Orin Nano (8GB) |  |  (Siemens S7-1500|  |  + pressure ||
|  |  |  FLUX + vision   |  |   F-CPU)         |  |  mat + scanner||
|  |  |  + AI perception |  |  ISO 13849 Cat 3 |  |               ||
|  |  +--------+---------+  +--------+---------+  +------+------+||
|  |           |                     |                     |      ||
|  |           v                     v                     v      ||
|  |  +---------------------------------------------------------+||
|  |  |           SAFETY GATE / CONTACTOR CONTROL               |||
|  |  |    Dual-channel Cat 3 |  PL d |  Safe Torque Off (STO)   |||
|  |  +---------------------------------------------------------+||
|  +-------------------------------------------------------------+|
|                                                                   |
|  +-------------------------------------------------------------+|
|  |                    ROBOT & CELL INTERFACES                   ||
|  |  Robot controller (KUKA/Fanab/ABB) — STO input               ||
|  |  Servo drives (Safe Torque Off / Safe Stop 1 / Safe Stop 2)  ||
|  |  End effector (force/torque sensor, gripper status)          ||
|  |  Cell perimeter (safety scanner, light curtain, mat)           ||
|  +-------------------------------------------------------------+|
|                                                                   |
+------------------------------------------------------------------+
```

### Constraint Budget

| Constraint Category | Count | Type | Update Rate | Source |
|---------------------|-------|------|-------------|--------|
| Joint position soft limits | 360 | Range (INT8) | 500 Hz | Encoder (motor-side + load-side) |
| Joint velocity limits (safe reduced) | 360 | Range (INT8) | 500 Hz | Differentiated position |
| Cartesian workspace boundary | 480 | Geofence (INT8) | 500 Hz | Forward kinematics |
| Speed separation monitoring (SSM) | 400 | Range (INT8) | 500 Hz | Safety laser scanner |
| Power/force limiting (PFL) | 240 | Range (FP16-safe) | 500 Hz | Force/torque sensor |
| Operator proximity / intrusion | 320 | Boolean/Enum | 500 Hz | Light curtain + mat + scanner |
| Tool / payload mass verification | 120 | Range (INT8) | 100 Hz | Motor current + model |
| Collision detection (momentum observer) | 240 | Range (INT8) | 500 Hz | Disturbance observer |
| Safe Stop 1 / Safe Stop 2 timing | 160 | Timer/Boolean | 500 Hz | STO/SS1 path monitoring |
| Gripper force / object integrity | 120 | Range (FP16-safe) | 500 Hz | Finger force sensors |
| Hand guiding mode constraints | 200 | Range (INT8) | 500 Hz | Enabling switch + force |
| Energy isolation verification | 160 | Boolean | 100 Hz | Contactors + feedback |
| **TOTAL active (500 Hz)** | **3,200** | Mixed | 500 Hz | — |
| **TOTAL with periodic** | **3,280** | — | — | — |

At 500 Hz with 3,200 constraints: 1.6 million evaluations/sec. Jetson Orin Nano (1024 CUDA cores, ~50B constraints/sec) provides **30,000x headroom**. Safety PLC (Siemens F-CPU) handles STO path independently at 1 ms cycle.

### Hardware Selection

**Primary: NVIDIA Jetson Orin Nano (8 GB)**
- **GPU:** 1024 CUDA cores, INT8 x8 packing
- **CPU:** 6-core Cortex-A78AE
- **Memory:** 8 GB LPDDR5
- **TDP:** 7W-15W configurable
- **Safety co-processor:** Integrated safety islands (lockstep capable)

**Safety PLC: Siemens SIMATIC S7-1500F (Fail-safe CPU)**
- **Category:** ISO 13849 Cat 3, PL d
- **Response time:** < 1 ms for STO output
- **I/O:** F-DI (fail-safe digital input), F-DQ (fail-safe digital output), F-AI

**Justification:**
1. **Separation of safety functions:** FLUX on Orin Nano handles "soft safety" (workspace optimization, predictive collision avoidance, production efficiency). Safety PLC handles "hard safety" (STO, light curtains, e-stops) per ISO 13849 Cat 3.
2. **Orin Nano cost:** At ~$500, lowest-cost FLUX deployment platform. Enables FLUX in every robot cell, not just high-end installations.
3. **Collaborative robot requirements:** ISO/TS 15066 requires power/force limiting and speed separation. FLUX constraints enforce these dynamically based on detected human proximity.
4. **Vision integration:** Orin Nano GPU runs person detection (YOLO) at 30 Hz, providing inputs to SSM constraints (human position -> allowed robot speed mapping).

### Latency Budget Breakdown

| Stage | Time | Cumulative | Notes |
|-------|------|------------|-------|
| Encoder acquisition (BiSS-C / EnDat 2.2) | 0.1 ms | 0.1 ms | 26-bit absolute, serial |
| Force/torque sensor (EtherCAT) | 0.2 ms | 0.3 ms | ATI Nano series |
| Safety scanner (SICK microScan) | 0.5 ms | 0.8 ms | PROFIsafe over PROFINET |
| FLUX constraint execution (3.2K @ 500Hz) | 0.02 ms | 0.82 ms | GPU kernel |
| Safety PLC cycle (Cat 3) | 1.0 ms | 1.82 ms | F-CPU scans I/O + logic |
| STO signal to servo drive | 0.5 ms | 2.32 ms | Safe pulse test + contactors |
| Servo drive STO response | 1.0 ms | 3.32 ms | IGBT gate disable |
| Mechanical stop (brake + friction) | 50-200 ms | — | Robot arm inertia |
| **TOTAL (STO path)** | **~3.3 ms** | — | Meets ISO 13849 < 500 ms stop requirement |
| **TOTAL (Safe Stop 1)** | **< 200 ms** | — | Controlled stop then STO |

The critical safety path (light curtain -> PLC -> STO -> drive) is < 5 ms and does not depend on FLUX. FLUX provides predictive safety: "will the robot enter restricted zone in 500 ms?" — enabling proactive speed reduction rather than reactive stopping. This improves productivity while maintaining safety.

### Redundancy Strategy

**Architecture: Dual channel (Category 3) with diverse technology**

| Element | Implementation |
|---------|---------------|
| Channel 1 (safety) | Siemens F-CPU — hardwired safety, contactor-based STO, ISO 13849 Cat 3 |
| Channel 2 (FLUX) | Jetson Orin Nano — predictive constraints, vision-based, "soft safety" |
| Interaction | FLUX can request speed reduction; F-CPU can override with STO. F-CPU always wins. |
| Sensor diversity | Encoders (motor + load side), force sensor, vision, light curtain, pressure mat — diverse technologies |
| STO path | Dual contactors in series, both must close for motion. Either opens -> STO. |
| Fail-safe | Any detected fault -> STO. Manual reset required. |
| Test mode | Maintenance key switch bypasses FLUX, keeps F-CPU active. |

**Rationale:** ISO 13849 Category 3 requires "no single fault leads to loss of safety function" and "single faults are detected." Dual-channel architecture with F-CPU as primary and FLUX as secondary satisfies this. FLUX failures are detected by F-CPU (expected speed commands vs actual) and result in STO.

### Power Budget

| Component | Power (W) | Notes |
|-----------|-----------|-------|
| Jetson Orin Nano | 12 | Full compute, vision + FLUX |
| Siemens S7-1500F F-CPU | 8 | Safety PLC + I/O modules |
| Safety I/O (F-DI x16, F-DQ x8) | 5 | Fail-safe digital modules |
| Servo drives (x6 axes, standby) | 15 | Holding current, control power |
| Safety scanner (SICK microScan3) | 4 | 270° scanning, PROFIsafe |
| Light curtain (Type 4) | 3 | Receiver + emitter pair |
| Force/torque sensor + amplifier | 2 | ATI Nano25, strain gauge |
| Vision camera (industrial, IP65) | 4 | Person detection |
| Enclosure + DIN rail + cooling | 5 | Cabinet, passive convection |
| DC power supply (24V industrial) | 3 | Efficiency losses |
| **TOTAL** | **61 W** | — |
| FLUX compute specifically | ~5 W | Orin Nano GPU portion |

### Certification Path

| Standard | Level | Approach |
|----------|-------|----------|
| ISO 13849 | PL d | Category 3, MTTFd high, DCavg medium |
| IEC 62061 | SIL 2 | Safety-related control systems for machinery |
| ISO/TS 15066 | — | Collaborative robots safety requirements |
| IEC 60204-1 | — | Electrical equipment of machines |
| ANSI/RIA R15.06 | — | Industrial robot safety (US) |
| CE Machinery Directive 2006/42/EC | — | EU market access |

**FLUX-specific certification argument:**
- **Category 3 with software:** ISO 13849 allows software in Cat 3 if properly designed (SIL 2 equivalent). FLUX's deterministic execution and formal equivalence support this claim.
- **Predictive safety evidence:** FLUX constraint "predictive workspace violation" can be validated against recorded human trajectories. Zero false negatives = safety requirement; false positives = productivity cost.
- **Modular constraints:** Each GUARD DSL constraint maps to a single hazard in the ISO 12100 risk assessment. Easy traceability for certifying body review.

### Estimated Cost

| Cost Item | Amount (USD) |
|-----------|-------------|
| Jetson Orin Nano 8GB | $500 |
| Siemens S7-1500F F-CPU | $2,800 |
| F-DI / F-DQ modules x4 | $1,200 |
| Safety scanner (SICK) | $2,500 |
| Light curtain (Type 4, 2m) | $1,800 |
| Force/torque sensor (ATI Nano25) | $3,500 |
| Industrial camera (IP65) | $800 |
| Servo STO modules (x6) | $1,200 |
| Safety contactors (x4, redundant) | $400 |
| Enclosure + DIN rail + PSU | $1,200 |
| Cabling + connectors | $600 |
| BOM subtotal | **$16,500** |
| NRE (ISO 13849 PL d validation, risk assessment) | $55,000 |
| Type testing (TUV, IFA) | $35,000 |
| **Total per cell (amortized NRE over 20 cells)** | **$11,000** |
| Total at volume (200 cells, robot OEM line) | **$7,500** |

---