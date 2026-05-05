## Agent 4: Surgical Robot Controller

**Domain:** Minimally invasive robotic surgery (MIRS) — da Vinci-class system
**Architect:** Agent 4 (Medical Robotics & Real-Time Control)

### System Block Diagram

```
+------------------------------------------------------------------+
|              SURGICAL ROBOT CONTROLLER (Master-Slave Teleop)      |
|                    FLUX Constraint Engine                         |
+------------------------------------------------------------------+
|                                                                   |
|  +-------------------------------------------------------------+|
|  |                    MASTER CONSOLE (Surgeon Side)               ||
|  |  +----------------+  +----------------+  +----------------+||
|  |  |  Hand Controllers  |  Foot Pedals    |  Head/Clutch    | ||
|  |  |  (6-DOF, force FB) |  (camera, energy)|  (positioning) | ||
|  |  +--------+---------+  +--------+------+  +--------+------+||
|  |           |                     |                    |      ||
|  |           v                     v                    v      ||
|  |  +---------------------------------------------------------+||
|  |  |    NVIDIA Jetson AGX Orin  | 64GB, GPU + CPU + FPGA    |||
|  |  |    FLUX Constraint Engine  |  Safety Controller         |||
|  |  +---------------------------------------------------------+||
|  +-------------------------------------------------------------+|
|                              |                                    |
|                    Fiber / EtherCAT (isolated)                    |
|                              |                                    |
|  +-------------------------------------------------------------+|
|  |                    PATIENT SIDE CART (Slave)                 ||
|  |  +----------------+  +----------------+  +----------------+ ||
|  |  |  Arm 1 (Left)  |  |  Arm 2 (Right) |  |  Arm 3 (Camera)| ||
|  |  |  6-DOF + 1 tool|  |  6-DOF + 1 tool|  |  6-DOF + endo | ||
|  |  |  Force sensors |  |  Force sensors |  |  Vision sensors| ||
|  |  +--------+-------+  +--------+-------+  +--------+-------+ ||
|  |           |                     |                    |      ||
|  |           v                     v                    v      ||
|  |  +---------------------------------------------------------+||
|  |  |    Real-Time Safety FPGA (Xilinx Zynq UltraScale+)      |||
|  |  |    1 kHz constraint check |  HW emergency stop logic     |||
|  |  +---------------------------------------------------------+||
|  |  +---------------------------------------------------------+||
|  |  |    MOTOR DRIVES (x18 servo loops, 20 kHz PWM)           |||
|  |  +---------------------------------------------------------+||
|  +-------------------------------------------------------------+|
|                                                                   |
+------------------------------------------------------------------+
```

### Constraint Budget

| Constraint Category | Count | Type | Update Rate | Source |
|---------------------|-------|------|-------------|--------|
| Joint position limits (x18 joints) | 540 | Range (INT8) | 1 kHz | Motor encoders |
| Joint velocity limits (x18) | 540 | Range (INT8) | 1 kHz | Differentiated position |
| Joint torque/force limits (x18) | 540 | Range (FP16-safe) | 1 kHz | Strain gauges |
| Tool-tip force limits (x3 tools) | 120 | Range (FP16-safe) | 1 kHz | Force/torque sensor |
| Workspace boundaries | 360 | Geofence (INT8) | 1 kHz | Forward kinematics |
| Patient collision avoidance | 600 | Range/Boolean | 1 kHz | Stereoscopic vision + proximity |
| Energy device safety (cautery, US) | 180 | Enum/Range | 1 kHz | Pedal + tissue impedance |
| Sterile field violation | 120 | Boolean | 1 kHz | Vision-based zone detection |
| Master-slave tracking error | 600 | Range (INT8) | 1 kHz | Position comparison |
| Emergency stop response | 600 | Boolean | 1 kHz | HW + SW e-stop chain |
| Grasping force (tissue damage) | 240 | Range (FP16-safe) | 1 kHz | Tool jaw force sensing |
| Instrument life / calibration | 360 | Enum | 100 Hz | Usage counter + self-test |
| **TOTAL active (1 kHz)** | **5,280** | Mixed | 1 kHz | — |
| **TOTAL periodic** | **~6,000** | — | — | — |

At 1 kHz with ~5,000 active constraints: 5 million evaluations/sec. Jetson Orin GPU (~150B constraints/sec peak) provides **30,000x headroom**. FPGA safety coprocessor runs a critical subset (workspace, force limits, e-stop) at hard real-time with <10 us latency.

### Hardware Selection

**Primary: NVIDIA Jetson AGX Orin (master console + constraint engine)**
- **GPU:** 2048 CUDA cores, INT8 x8 packing, ~150B constraints/sec effective
- **CPU:** 12-core Cortex-A78AE, 64 GB LPDDR5
- **Safety co-processor:** Xilinx Zynq UltraScale+ (patient side, hard real-time)
- **FPGA role:** 1 kHz servo loop + emergency stop logic (no dependency on GPU/OS)

**Justification:**
1. **Throughput headroom:** 5M evaluations/sec vs 150B/sec = 0.003% GPU utilization. Leaves enormous margin for vision-based constraints (tissue tracking, bleeding detection at 30 Hz video rates adding ~2,000 more constraints).
2. **Medical-grade compute:** Jetson Orin supports 24/7 operation, passive cooling options, and long-term supply commitment from NVIDIA (critical for 15-year medical device lifecycle).
3. **Dual-domain architecture:** GPU handles complex constraints (vision, kinematics, tissue modeling); FPGA handles life-safety hard real-time (force limits, e-stop, workspace boundaries). This separation satisfies IEC 62304 software class C while ensuring <1 ms emergency stop.
4. **Isolation:** Master (Orin) and slave (FPGA) connected via fiber-optic EtherCAT, providing 5kV galvanic isolation required for patient leakage current limits (IEC 60601-1).

**Safety-critical FPGA: Xilinx Zynq UltraScale+ ZU7EV**
- Dual-core Cortex-A53 (non-safety, runs Linux for UI)
- Programmable logic: 504K cells, dedicated DSP slices for kinematics
- Safety logic: Pure FPGA fabric, no processor involvement for e-stop path
- I/O: 18 servo motor drives, 18 encoder channels, analog force inputs

### Latency Budget Breakdown

| Stage | Time | Cumulative | Notes |
|-------|------|------------|-------|
| Master hand controller acquisition | 0.3 ms | 0.3 ms | 6-DOF magnetic/optical encoders |
| Command transmission (fiber) | 0.05 ms | 0.35 ms | <1 km fiber, negligible propagation |
| FPGA safety check (critical subset) | 0.01 ms | 0.36 ms | Force limits, workspace, e-stop |
| FLUX constraint execution (5K @ 1kHz) | 0.03 ms | 0.39 ms | GPU kernel on Orin |
| Kinematics + trajectory generation | 0.2 ms | 0.59 ms | Inverse kinematics, Jacobian |
| Motor command generation | 0.05 ms | 0.64 ms | EtherCAT distributed clock |
| Motor drive response (current loop) | 0.05 ms | 0.69 ms | 20 kHz PWM, sub-cycle update |
| Mechanical response (arm + tool) | 2-5 ms | — | Harmonic drive + cable compliance |
| **TOTAL (control loop)** | **~0.38 ms** | — | Meets 1 kHz update requirement |
| **TOTAL (surgeon perception)** | **< 5 ms** | — | Imperceptible teleoperation delay |

The critical path for safety is the FPGA loop: master input -> fiber -> FPGA force check -> e-stop logic. This path is **< 100 us** independent of the GPU constraint engine. The GPU adds "soft safety" (vision, tissue modeling) with 0.4 ms latency. Dual-path architecture ensures no single point of failure can bypass force limits.

### Redundancy Strategy

**Architecture: Dual cross-check with independent safety paths**

| Element | Implementation |
|---------|---------------|
| Primary control | Jetson Orin (GPU) — full constraint set, vision, kinematics |
| Safety monitor | Zynq UltraScale+ FPGA — critical constraints only, HW e-stop |
| Cross-check | Orin and FPGA independently compute force limit compliance; disagreement → pause |
| Emergency stop | Triple-redundant e-stop chain: pedal -> FPGA -> motor drive disable |
| Degraded mode | Loss of GPU → FPGA maintains position hold + basic force limits |
| Loss of FPGA → | System halts (Orin cannot drive motors without FPGA safety gate) |
| Power | Dual medical-grade isolated supplies (IEC 60601-1), battery backup for e-stop |

**Rationale:** IEC 62304 Class C (life-supporting) requires risk mitigation to ALARP. Dual cross-check between GPU (complex, high throughput) and FPGA (simple, deterministic) captures both systematic software faults and complex environmental faults. FPGA as "safety gate" ensures no software error can command unsafe motion.

### Power Budget

| Component | Power (W) | Notes |
|-----------|-----------|-------|
| Jetson AGX Orin (master console) | 35 | Full compute, vision processing |
| Xilinx Zynq UltraScale+ (patient side) | 8 | FPGA + light CPU duties |
| Motor drives x18 | 18 | 1W each, standby + control |
| Hand controller force feedback x2 | 6 | Haptic motors |
| Stereoscopic vision system | 12 | Dual 4K endoscopes + processing |
| EtherCAT network + fiber transceivers | 4 | Isolated communication |
| Medical-grade power supplies (x2, isolated) | 8 | IEC 60601-1, leakage < 100 uA |
| Cooling (active, low noise) | 10 | < 35 dB for OR environment |
| Patient cart mechanics + brakes | 5 | Holding brakes, counterbalance |
| **TOTAL** | **106 W** | — |
| FLUX compute (GPU) | ~18 W | Constraint kernel + vision |
| FLUX compute (FPGA critical) | ~2 W | Hard real-time subset |

### Certification Path

| Standard | Level | Approach |
|----------|-------|----------|
| IEC 62304 | Class C (life-supporting) | Full software lifecycle, independent verification |
| ISO 13485 | — | Medical device quality management |
| IEC 60601-1 | — | Basic safety & essential performance, isolation, leakage |
| IEC 60601-1-2 | — | Electromagnetic compatibility (EMC) |
| ISO 13482 | — | Personal care robot safety (force/pressure limits) |
| FDA 21 CFR 820 | — | Quality system regulation (US market) |
| MDR 2017/745 | — | Medical Device Regulation (EU market) |

**FLUX-specific certification argument:**
- **Deterministic execution** supports IEC 62304 Class C software unit verification — each constraint has fixed execution path, no dynamic memory.
- **Formal equivalence** (Galois connection) allows safety case to argue that compiled bytecode is provably equivalent to reviewed GUARD DSL source. Reduces testing burden for compiler validation.
- **Separation of concerns:** GUARD DSL for medical constraints is reviewable by clinical experts without GPU/FPGA expertise. Compiler correctness is proven mathematically, not tested empirically.
- **Traceability:** Each GUARD constraint maps to a single hazard in the ISO 14971 risk management file. FLUX-C opcode execution provides deterministic trace for incident analysis.

### Estimated Cost

| Cost Item | Amount (USD) |
|-----------|-------------|
| Jetson AGX Orin (64GB) | $1,500 |
| Xilinx Zynq UltraScale+ ZU7EV | $2,500 |
| Hand controllers x2 (6-DOF force feedback) | $4,000 |
| Patient cart arms x3 (6-DOF + tool) | $25,000 |
| Motor drives x18 (medical grade) | $9,000 |
| Force/torque sensors x3 | $3,500 |
| Endoscopic vision system (4K stereo) | $8,000 |
| Fiber-optic EtherCAT isolators | $1,200 |
| Medical-grade PSU x2 | $2,000 |
| Sterile draping + instrument interface | $6,000 |
| BOM subtotal | **$62,700** |
| NRE (IEC 62304 Class C, FDA 510(k)/PMA) | $350,000 |
| Clinical trials (safety/efficacy) | $850,000 |
| **Total per system (amortized NRE over 100 units)** | **$22,000** |
| Total at volume (1,000 systems, production line) | **$15,000** |

---