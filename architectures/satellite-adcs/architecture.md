## Agent 5: Satellite Attitude Control System (ADCS)

**Domain:** LEO satellite attitude determination and control
**Architect:** Agent 5 (Space Systems & Radiation Effects)

### System Block Diagram

```
+------------------------------------------------------------------+
|              SATELLITE ATTITUDE DETERMINATION & CONTROL (ADCS)    |
|                    FLUX Constraint Engine                         |
+------------------------------------------------------------------+
|                                                                   |
|  +-------------------------------------------------------------+|
|  |                 PRIMARY PROCESSING UNIT                      ||
|  |                                                              ||
|  |   Xilinx XQR Zynq UltraScale+ MPSoC (Radiation-Tolerant)   ||
|  |   +------------------+  +------------------+               |||
|  |   |  Processing Sys  |  |  Programmable    |               |||
|  |   |  (Quad A53)      |  |  Logic (FPGA)    |               |||
|  |   |  - Flight SW     |  |  - FLUX-C Engine |               |||
|  |   |  - Kalman filter |  |  - Sensor fusion |               |||
|  |   |  - Command/exec  |  |  - Actuator ctrl |               |||
|  |   +--------+---------+  +--------+---------+               |||
|  |            |                     |                         |||
|  |            v                     v                         |||
|  |   +--------+---------+  +--------+---------+               |||
|  |   |  DDR4 w/ ECC     |  |  BRAM / UltraRAM |               |||
|  |   |  (4 GB)          |  |  (on-chip)       |               |||
|  |   +------------------+  +------------------+               |||
|  +-------------------------------------------------------------+|
|                                                                   |
|  +-------------------------------------------------------------+|
|  |                 COLD STANDBY UNIT (Identical)                 ||
|  |   Powered off; watchdog can power-on in < 5 seconds         ||
|  +-------------------------------------------------------------+|
|                                                                   |
|  +-------------------------------------------------------------+|
|  |                     SENSOR INTERFACES                         ||
|  |   Star tracker x2   |   IMU (MEMS/FOG) x2   |   Sun sensor x4||
|  |   Magnetometer x3   |   Earth sensor x2      |   GPS receiver ||
|  |   (coarse/fine)     |   (horizon crossing)   |   (position)   ||
|  +-------------------------------------------------------------+|
|                                                                   |
|  +-------------------------------------------------------------+|
|  |                     ACTUATOR INTERFACES                       ||
|  |   Reaction wheels x4    |   Magnetic torquers x3            ||
|  |   (momentum storage)    |   (momentum dump)                  ||
|  |   Thrusters x8 (cold gas)|  (emergency/control)              ||
|  +-------------------------------------------------------------+|
|                                                                   |
+------------------------------------------------------------------+
```

### Constraint Budget

| Constraint Category | Count | Type | Update Rate | Source |
|---------------------|-------|------|-------------|--------|
| Attitude error (roll, pitch, yaw) | 360 | Range (INT8) | 20 Hz | Star tracker + Kalman |
| Angular rate limits | 180 | Range (INT8) | 20 Hz | IMU |
| Momentum wheel saturation | 240 | Range (INT8) | 20 Hz | RW tachometers |
| Power generation (solar pointing) | 120 | Range (INT8) | 10 Hz | Sun sensor + power |
| Thermal limits (electronics) | 80 | Range (INT8) | 1 Hz | Temperature sensors |
| Communication pointing (antenna) | 120 | Range (INT8) | 10 Hz | Earth sensor + GPS |
| Momentum dumping schedule | 60 | Enum/Range | 1 Hz | B-dot algorithm |
| Thruster firing constraints | 40 | Enum | Event | Operational sequence |
| Earth limb avoidance (optics) | 80 | Geofence | 10 Hz | Ephemeris + attitude |
| Safe mode entry conditions | 120 | Boolean | 1 Hz | Combined health |
| **TOTAL** | **1,400** | Mixed | 1-20 Hz | — |

At 20 Hz with 1,400 constraints: 28,000 evaluations/sec. XQR Zynq UltraScale+ FPGA fabric at 100 MHz executes FLUX-C at ~5M constraints/sec (178x headroom). Power-limited operation targets minimum clock for margin, not maximum throughput.

### Hardware Selection

**Primary: Xilinx XQR Zynq UltraScale+ MPSoC (Radiation-Tolerant)**
- **Processing system:** Quad-core Arm Cortex-A53 (ECC-protected caches)
- **FPGA:** ~600K system logic cells, UltraRAM, DSP slices
- **Memory:** 4 GB DDR4 with ECC, 256 MB QSPI flash (TMR for configuration)
- **Radiation tolerance:** TID > 100 krad(Si), SEL > 60 MeV-cm2/mg
- **I/O:** SpaceWire, MIL-STD-1553, LVDS for payload interfaces
- **Power:** 5-15W depending on utilization

**Justification:**
1. **Radiation hardness:** XQR-qualified devices are fully characterized for LEO (500-1200 km) radiation environment. SEU rates are characterized; EDAC + scrubbing maintains reliability.
2. **Integrated MPSoC:** FPGA for real-time control + ARM for flight software eliminates need for separate processor, saving power, mass, and board area.
3. **Space heritage:** Zynq UltraScale+ has extensive flight history (NASA, ESA missions), reducing qualification risk.
4. **Power scalability:** ADCS typically operates at low duty cycle; Zynq can clock-gate unused regions. FLUX constraint engine occupies small FPGA footprint, leaving most fabric for payload processing.

**Cold standby:** Identical XQR Zynq module, powered off except watchdog timer. Primary failure detection -> power-on standby -> switchover in < 5 seconds (acceptable for attitude control, not time-critical like rendezvous).

### Latency Budget Breakdown

| Stage | Time | Cumulative | Notes |
|-------|------|------------|-------|
| Star tracker image capture | 100-200 ms | 200 ms | CCD integration + readout |
| IMU data acquisition | 1 ms | 201 ms | SPI/I2C at 1 kHz, decimated to 20 Hz |
| Sensor fusion (EKF) | 5 ms | 206 ms | Quaternion Kalman filter on A53 |
| FLUX constraint execution (1.4K @ 20Hz) | 0.3 ms | 206.3 ms | FPGA fabric |
| Control law (PID + momentum management) | 2 ms | 208.3 ms | FPGA or A53 |
| Actuator command (reaction wheel) | 1 ms | 209.3 ms | CAN / SpaceWire to RW drive |
| Wheel torque response | 10-50 ms | — | Motor + momentum transfer |
| **TOTAL (compute path)** | **~8.5 ms** | — | Dominated by star tracker |
| **TOTAL (with star tracker)** | **~210 ms** | — | Fine pointing loop (arcsecond) |

Note: Coarse pointing (sun sensor + IMU) runs at 1 Hz with 500 ms latency; fine pointing (star tracker) at 0.2 Hz with 200 ms. FLUX constraints execute on both loops. 8.5 ms compute latency is negligible compared to sensor latency.

### Redundancy Strategy

**Architecture: Cold standby with watchdog and graceful degradation**

| Element | Implementation |
|---------|---------------|
| Primary | XQR Zynq UltraScale+ — full ADCS + FLUX + payload interface |
| Standby | Identical XQR Zynq — powered off, watchdog-monitored |
| Watchdog | External rad-tolerant watchdog (CML Microcircuits CMX994) on primary; triggers standby boot if primary misses 3 heartbeats |
| Sensor redundancy | 2x star trackers (cross-check), 2x IMU (voting), 3x magnetometer (2oo3), 4x sun sensors (any 2) |
| Actuator redundancy | 4x reaction wheels in pyramid config (any 3 sufficient), 3x magnetorquers (any 2 sufficient), 8x thrusters (any 4 for control) |
| Safe mode | Loss of ADCS -> sun-pointing safe mode (solar power priority), autonomous recovery |
| Ground intervention | Uplink command can force standby takeover, safe mode, or constraint rule update |

**Rationale:** Satellites cannot be repaired. Cold standby avoids power waste (critical for solar-battery budget) while providing recovery from primary failures. Sensor and actuator over-provisioning (more than minimum needed) allows continued operation after any single failure — standard practice for LEO missions.

### Power Budget

| Component | Power (W) | Notes |
|-----------|-----------|-------|
| XQR Zynq UltraScale+ (active) | 8 | 800 MHz A53 + 50 MHz FPGA fabric |
| XQR Zynq UltraScale+ (standby, off) | 0.2 | Watchdog only |
| Star tracker x2 | 3 | 1.5W each, CCD + processor |
| IMU x2 | 1 | 0.5W each, MEMS-based |
| Magnetometer x3 | 0.3 | 0.1W each, fluxgate |
| Sun sensor x4 | 0.4 | Photodiode-based, very low power |
| Earth sensor x2 | 1 | Thermopile-based |
| GPS receiver | 1.5 | Space-qualified L1 receiver |
| Reaction wheel drive x4 | 4 | Highly variable (0-10W each), average |
| Magnetic torquer x3 | 1.5 | PWM coil drivers |
| Thruster valve drivers x8 | 0.5 | Cold gas, only fired occasionally |
| **TOTAL (average)** | **~12 W** | — |
| **TOTAL (peak, momentum dump)** | **~35 W** | All RWs + thrusters active |
| FLUX compute specifically | ~1.5 W | FPGA fabric portion |

12W average is critical for a 12U CubeSat with 20W solar panel capacity. FLUX's extremely low FPGA power (<2W) leaves budget for payload and communications.

### Certification Path

| Standard | Level | Approach |
|----------|-------|----------|
| ECSS-Q-ST-80C | — | Space product assurance — component selection |
| NASA-STD-8719.13B | — | Software safety requirements for NASA projects |
| MIL-STD-883 | — | Test methods and procedures for microelectronics |
| AIAA S-120-2006 | — | Space system cybersecurity |
| Launch provider | — | SpaceX/NASA/ESA mission-specific requirements |

**FLUX-specific certification argument:**
- **Small attack surface:** 43-opcode ISA with no OS dependencies, no network stack, no file system. Satisfies NASA-STD-8719.13B software safety for autonomous spacecraft.
- **Formal correctness:** Galois connection proof eliminates need for extensive ground-based validation of compiled rules. Upload constraint updates with mathematical guarantee of semantic preservation.
- **Deterministic scheduling:** Fixed 20 Hz control loop with fixed FLUX execution time. Supports worst-case execution time (WCET) analysis for real-time schedulability.
- **In-orbit updatability:** GUARD DSL source can be uplinked and recompiled on orbit. Formal equivalence ensures uploaded rules match ground-validated source.

### Estimated Cost

| Cost Item | Amount (USD) |
|-----------|-------------|
| XQR Zynq UltraScale+ x2 | $18,000 |
| Space-qualified star trackers x2 | $28,000 |
| IMU (navigation-grade MEMS) x2 | $6,000 |
| Magnetometers (space-grade) x3 | $4,500 |
| Sun sensors x4 | $2,000 |
| Earth horizon sensors x2 | $5,000 |
| GPS receiver (space-qualified) | $8,000 |
| Reaction wheels (miniature) x4 | $16,000 |
| Magnetic torquers x3 | $1,500 |
| Cold gas thruster system x8 | $4,000 |
| PCB (space-qualified materials) x2 | $5,000 |
| Enclosure (thermal control, conduction) | $3,000 |
| BOM subtotal | **$101,000** |
| NRE (ADCS design, radiation analysis, launch integration) | $250,000 |
| Environmental test (thermal vacuum, vibration, TVAC) | $120,000 |
| **Total per satellite (amortized NRE over 5 units)** | **$67,000** |
| Total at constellation (50 satellites) | **$55,000** |


---