## Agent 9: Underwater Pipeline Inspection AUV

**Domain:** Autonomous underwater vehicle for subsea pipeline survey
**Architect:** Agent 9 (Subsea Systems & Limited Bandwidth Operations)

### System Block Diagram

```
+------------------------------------------------------------------+
|              UNDERWATER PIPELINE INSPECTION AUV                   |
|                    FLUX Constraint Engine                         |
+------------------------------------------------------------------+
|                                                                   |
|  +-------------------------------------------------------------+|
|  |                    PRIMARY CONTROL UNIT                      ||
|  |                                                              ||
|  |   NVIDIA Jetson Orin Nano (8GB) — sealed, oil-filled       ||
|  |   + FLUX constraint engine                                   ||
|  |   + SLAM + pipeline tracking + visual inspection           ||
|  +-------------------------------------------------------------+|
|                                                                   |
|  +-------------------------------------------------------------+|
|  |                    BACKUP NAVIGATION UNIT                    ||
|  |   Xilinx Artix-7 FPGA (cold standby, wake-on-fault)          ||
|  |   + Basic depth/altitude hold                               ||
|  |   + Emergency surfacing sequence                            ||
|  +-------------------------------------------------------------+|
|                                                                   |
|  +-------------------------------------------------------------+|
|  |                    SENSOR SUITE                              ||
|  |   DVL (Doppler velocity log)     |   Multibeam sonar        ||
|  |   INS/DVL fusion                 |   (bathymetry, obstacle) ||
|  |   Pressure sensor (depth)        |   Sidescan sonar         ||
|  |   Camera x2 (LED strobe, HD)     |   (pipeline tracking)   ||
|  |   Magnetometer (heading)         |   CTD (conductivity,    ||
|  |   Acoustic modem ( communication)|   temp, depth)           ||
|  +-------------------------------------------------------------+|
|                                                                   |
|  +-------------------------------------------------------------+|
|  |                    ACTUATION                                 ||
|  |   Thrusters x8 (vectored)      |   Buoyancy pump           ||
|  |   (surge, sway, heave, yaw)    |   (trim/emergency)        ||
|  |   Control surfaces x4          |   Drop weight (emergency) ||
|  +-------------------------------------------------------------+|
|                                                                   |
+------------------------------------------------------------------+
```

### Constraint Budget

| Constraint Category | Count | Type | Update Rate | Source |
|---------------------|-------|------|-------------|--------|
| Depth ceiling (surface) / floor | 200 | Range (INT8) | 20 Hz | Pressure sensor |
| Altitude above seabed | 160 | Range (INT8) | 20 Hz | Multibeam / DVL |
| Pipeline tracking deviation | 200 | Range (INT8) | 20 Hz | Sidescan + camera |
| Obstacle / collision avoidance | 300 | Range/Geofence | 20 Hz | Multibeam sonar |
| Speed envelope (surge, sway, heave) | 180 | Range (INT8) | 20 Hz | DVL + INS |
| Heading / yaw stability | 120 | Range (INT8) | 20 Hz | Magnetometer + INS |
| Vehicle attitude (pitch, roll) | 120 | Range (INT8) | 20 Hz | INS |
| Battery / energy reserves | 160 | Range (INT8) | 1 Hz | Battery management |
| Communication timeout (dead reckoning) | 120 | Timer/Boolean | 1 Hz | Acoustic modem |
| Mission abort / emergency surface | 120 | Boolean | 20 Hz | Combined health |
| Pressure vessel integrity | 120 | Boolean | 1 Hz | Leak detection |
| **TOTAL** | **1,800** | Mixed | 1-20 Hz | — |

At 20 Hz with 1,800 constraints: 36,000 evaluations/sec. Jetson Orin Nano (~50B constraints/sec) provides **1,400,000x headroom**. Extreme margin supports simultaneous visual inspection processing (neural network) and acoustic modem data encoding.

### Hardware Selection

**Primary: NVIDIA Jetson Orin Nano (8 GB) — subsea-rated enclosure**
- **GPU:** 1024 CUDA cores, INT8 x8 packing
- **CPU:** 6-core Cortex-A78AE
- **Memory:** 8 GB LPDDR5
- **TDP:** 7W-15W (critical for battery operation)
- **Enclosure:** Oil-filled, pressure-compensated, 3000m depth rated

**Justification:**
1. **Power efficiency:** Orin Nano at 7W provides 50B+ constraints/sec. For 36K evaluations/sec, utilization is 0.00007%. Remaining power budget goes to sonar processing and thrusters.
2. **AI perception:** Pipeline inspection requires visual crack detection, anode depletion analysis, and marine growth assessment — all CUDA-accelerated neural networks.
3. **Size:** 45mm x 69mm module fits in small-diameter AUV hulls (150mm-200mm typical).
4. **Long-term supply:** 10-year availability commitment from NVIDIA, critical for subsea systems with 15-20 year operational life.

**Backup: Xilinx Artix-7 FPGA (cold standby)**
- Pure hardware emergency sequence: depth hold -> surface -> beacon activation
- Battery-backed, wake-on-primary-fault
- No software, no OS — operates even if Orin is flooded/corrupted

### Latency Budget Breakdown

| Stage | Time | Cumulative | Notes |
|-------|------|------------|-------|
| Sonar ping + receive (multibeam) | 50 ms | 50 ms | 200-400 kHz, 50m range |
| DVL bottom track | 25 ms | 75 ms | 300 kHz, 4-beam Janus |
| INS/DVL integration | 5 ms | 80 ms | Kalman filter, 20 Hz output |
| FLUX constraint execution (1.8K @ 20Hz) | 0.03 ms | 80 ms | GPU kernel |
| SLAM / pipeline tracking | 20 ms | 100 ms | Visual + sonar fusion |
| Control law (PID + allocation) | 2 ms | 102 ms | 8-thruster allocation matrix |
| Thruster command (ESC) | 5 ms | 107 ms | BLDC motor controllers |
| Propeller thrust build-up | 50-100 ms | — | Inertia + flow development |
| **TOTAL (control loop)** | **~45 ms** | — | Well within 50 ms requirement |
| **TOTAL (obstacle avoidance)** | **< 200 ms** | — | Meets AUV dynamics for 2 kt speed |

Underwater vehicle dynamics are slow (high inertia, viscous damping). 45 ms control latency is acceptable. The critical timing is emergency surfacing: backup FPGA must activate drop weight within 500 ms of leak detection or communication loss.

### Redundancy Strategy

**Architecture: Dual cold standby with emergency-only backup**

| Element | Implementation |
|---------|---------------|
| Primary | Jetson Orin Nano — full navigation + FLUX + inspection + communication |
| Backup | Artix-7 FPGA — emergency depth hold, emergency surfacing, acoustic beacon |
| Activation | FPGA monitors Orin heartbeat (100 ms timeout) and leak detector (binary) |
| Emergency sequence | 1) Kill thrusters, 2) Activate buoyancy pump, 3) Drop emergency weight, 4) Activate pinger |
| Communication | Acoustic modem (9.6 kbps) — intermittent, not real-time. AUV operates autonomously. |
| Surface recovery | Iridium backup on surface, USBL beacon for subsurface tracking |
| Power | Li-ion battery (2 kWh typical), Orin + sensors + thrusters. Backup has separate LiPo. |

**Rationale:** AUVs operate beyond real-time communication (acoustic modem: kbps, seconds latency). Full autonomy is mandatory. Backup must be completely independent of primary (different hardware, different power, different software) because flooding or power loss are real risks at depth. Cold standby acceptable because emergency sequences are pre-programmed, not computed.

### Power Budget

| Component | Power (W) | Notes |
|-----------|-----------|-------|
| Jetson Orin Nano | 10 | Navigation + FLUX + vision |
| Artix-7 FPGA (standby) | 0.5 | Watchdog + leak monitor only |
| DVL (Teledyne WorkHorse) | 8 | 300 kHz, bottom track |
| Multibeam sonar | 12 | 200-400 kHz, 128 beams |
| Sidescan sonar | 6 | 100/400 kHz dual frequency |
| Camera x2 + LED strobe x2 | 8 | Synchronized, short pulse |
| INS (MEMS or FOG grade) | 3 | Subsea INS, pressure rated |
| Acoustic modem | 3 | 9.6 kbps, 10W transmit |
| Thrusters x8 (average cruise) | 40 | 5W each at 2 kt cruise |
| Buoyancy pump | 2 | Occasional trim adjustments |
| Pressure vessel heaters | 5 | Prevent condensation in hull |
| **TOTAL (average cruise)** | **97.5 W** | — |
| **TOTAL (peak, inspection hover)** | **~140 W** | All sensors + thrusters active |
| FLUX compute specifically | ~3 W | Orin Nano GPU, very low utilization |

2 kWh battery at 97.5W average = 20.5 hours endurance. Reducing FLUX power to 3W (vs 10W module) is achieved by aggressive clock gating and CPU-idle during GPU constraint execution.

### Certification Path

| Standard | Level | Approach |
|----------|-------|----------|
| IMCA AODC 046 | — | Guidance on AUV safety |
| DNV-ST-F101 | — | Submarine pipeline systems |
| IMCA R 004 | — | Remotely operated vehicles |
| ISO 13628-8 | —| Subsea production systems — ROV interfaces |
| Class society rules | — | DNV/Lloyd's/BV AUV classification (as applicable) |

**FLUX-specific certification argument:**
- **Autonomous operation without comms:** FLUX constraints execute entirely on-board with no ground dependency. GUARD DSL rules are compiled before dive; no runtime compilation needed.
- **Predictive safety:** "Will AUV hit seabed in 30 seconds at current speed?" — FLUX evaluates future trajectories, enabling proactive avoidance rather than reactive depth ceiling.
- **Resource-aware constraints:** Battery, mission time, and data storage are constraints in GUARD DSL. System can autonomously decide to abort mission if energy reserve drops below safe-return threshold.
- **Formal equivalence:** Compiled rules are proven equivalent to source. No risk of compiler bugs causing rule corruption during autonomous operation.

### Estimated Cost

| Cost Item | Amount (USD) |
|-----------|-------------|
| Jetson Orin Nano (subsea-rated) | $2,500 |
| Artix-7 FPGA + support | $800 |
| DVL (Teledyne Explorer) | $18,000 |
| Multibeam sonar (Kongsberg / R2Sonic) | $35,000 |
| Sidescan sonar (EdgeTech) | $12,000 |
| Subsea cameras x2 + LED strobes | $8,000 |
| INS (subsea MEMS or FOG) | $10,000 |
| Acoustic modem (EvoLogics / Teledyne) | $8,000 |
| Thrusters x8 (subsea brushless) | $6,000 |
| Pressure vessel (titanium, 3000m) | $15,000 |
| Buoyancy + trim system | $4,000 |
| Li-ion battery pack (2 kWh, pressure) | $8,000 |
| Emergency drop weight + release | $2,000 |
| BOM subtotal | **$129,300** |
| NRE (AUV design, pressure testing, IMCA compliance) | $220,000 |
| Sea trials + pipeline validation | $180,000 |
| **Total per AUV (amortized NRE over 15 units)** | **$29,000** |
| Total at fleet volume (50 AUVs) | **$22,000** |

---