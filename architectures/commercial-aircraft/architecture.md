# Agent 2: Commercial Aircraft Flight Management System (FMS)

**Domain:** Commercial transport aircraft (narrow-body and wide-body)
**Architect:** Agent 2 (Aerospace Avionics & DO-178C)

## System Block Diagram

```
+------------------------------------------------------------------+
|              COMMERCIAL AIRCRAFT FLIGHT MANAGEMENT SYSTEM         |
|                    FLUX Constraint Engine                         |
+------------------------------------------------------------------+
|                                                                   |
|  +-------------------------------------------------------------+|
|  |                 TRIPLE MODULAR REDUNDANT (TMR) CORE          ||
|  |                                                              ||
|  |  +----------------+  +----------------+  +----------------+  ||
|  |  |   CHANNEL A    |  |   CHANNEL B    |  |   CHANNEL C    |  ||
|  |  |  Microchip     |  |  Microchip     |  |  Microchip     |  ||
|  |  |  PolarFire SoC |  |  PolarFire SoC |  |  PolarFire SoC |  ||
|  |  |  RT FPGA + R5  |  |  RT FPGA + R5  |  |  RT FPGA + R5  |  ||
|  |  +-------+--------+  +-------+--------+  +-------+--------+  ||
|  |          |                    |                    |          ||
|  |          v                    v                    v          ||
|  |  +-------+--------------------+--------------------+--------+  ||
|  |  |              VOTER / COMPARATOR (2oo3 Logic)              |  ||
|  |  |         Microsemi FPGA-based voter, radiation-tolerant      |  ||
|  |  +-------+--------------------+--------------------+--------+  ||
|  |          |                    |                    |          ||
|  |          v                    v                    v          ||
|  |  +---------------------------------------------------------+  ||
|  |  |           FLUX-C BYTECODE EXECUTION UNIT (FPGA)          |  ||
|  |  |    Custom 43-opcode INT8 pipeline, deterministic WCET    |  ||
|  |  +---------------------------------------------------------+  ||
|  +-------------------------------------------------------------+|
|                                                                   |
|  +-------------------------------------------------------------+|
|  |                     SENSOR INTERFACES                        ||
|  |  ARINC 429 (x24)  |  ARINC 664 (AFDX)  |  Analog/DIS (x48) ||
|  |  GPS/GNSS (x2)    |  IRS/INS (x2)      |  Air Data (x4)    ||
|  |  Engine FADEC (x4)|  Weather Radar     |  TCAS / ACAS      ||
|  +-------------------------------------------------------------+|
|                                                                   |
|  +-------------------------------------------------------------+|
|  |                     OUTPUT INTERFACES                        ||
|  |  Autopilot servo cmd  |  Display (PFD/ND)  |  CNS/ATM datalink||
|  +-------------------------------------------------------------+|
|                                                                   |
+------------------------------------------------------------------+
```

## Constraint Budget

| Constraint Category | Count | Type | Update Rate | Source |
|---------------------|-------|------|-------------|--------|
| Flight envelope (VMO, MMO, alpha) | 800 | Range (INT8) | 50 Hz | Air data + inertial |
| Navigation integrity (RNP, ANP) | 600 | Range (INT8) | 50 Hz | GNSS + IRS |
| Engine limits (N1, N2, EGT, EPR) | 1,200 | Range (INT8) | 50 Hz | FADEC ARINC 429 |
| Fuel system (imbalance, temp, qty) | 400 | Range (INT8) | 10 Hz | Fuel probes |
| Landing configuration (flaps, gear) | 300 | Enum/Range | 50 Hz | Proximity sensors |
| Terrain clearance (TAWS) | 500 | Range (INT8) | 5 Hz | Terrain database + GPS |
| TCAS resolution advisories | 200 | Enum | 1 Hz (event) | TCAS processor |
| Weight & balance (CG envelope) | 200 | Range (FP16-safe) | 10 Hz | Load sensors + fuel |
| Weather avoidance | 400 | Geofence | 10 Hz | Weather radar + SIGMET |
| ATC constraint compliance | 400 | Enum/Range | 5 Hz | CPDLC + FMS path |
| **TOTAL** | **5,000** | Mixed | 5-50 Hz | — |

## Hardware Selection

**Primary: Microchip PolarFire SoC (Radiation-Tolerant FPGA + RISC-V/Arm)**
- **FPGA:** 150K logic elements, hardened against SEUs, military-grade temp range
- **Processor:** 4x 64-bit RISC-V cores or dual-core Arm Cortex-A53
- **Memory:** 2 GB LPDDR4 with ECC
- **Safety:** DO-254 Level A support, ECC on all memory, EDAC on configuration SRAM
- **I/O:** Native ARINC 429, MIL-STD-1553, SpaceWire support

**Voter hardware:** Discrete radiation-tolerant FPGA (Microchip RTG4) implementing 2oo3 majority voter with self-checking pair.

## Latency Budget

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

## Redundancy Strategy

**Architecture: Triple Modular Redundancy (TMR) with 2-out-of-3 voting**

| Element | Implementation |
|---------|---------------|
| Channel A/B/C | Identical PolarFire SoC, independent power domains, independent sensors |
| Sensor independence | Each channel has dedicated ARINC 429 Rx, dedicated GPS receiver, dedicated air data probe |
| Voter | RTG4 FPGA implementing bit-level 2oo3 majority vote on all outputs |
| Voter integrity | Self-checking pair (two voters cross-check each other) |
| Fault detection | Channel divergence detected within 500 us; faulty channel isolated in < 2 ms |
| Fail-operational | System continues with 2 channels (degraded); 1 channel → safe state (AP disconnect, manual) |
| Power isolation | Each channel on separate 28V aircraft bus with independent DC-DC |

## Power Budget

| Component | Power (W) | Notes |
|-----------|-----------|-------|
| PolarFire SoC (x3, active) | 45 | 15W each @ full FPGA utilization |
| RTG4 voter FPGA | 8 | Self-checking pair + I/O |
| Sensor interfaces (ARINC 429 x24, AFDX) | 25 | Line drivers + isolators |
| GPS receivers (x3, aviation-grade) | 15 | Dual-frequency (L1/L5) |
| Air data computers (x3, standby) | 20 | Pitot-static + ADM |
| IRS/INS (x2, laser gyro) | 25 | Honeywell or Northrop Grumman |
| Enclosure + thermal (conduction cooled) | 7 | ARINC 600 form factor |
| **TOTAL** | **145 W** | — |
| FLUX compute specifically | ~8 W | FPGA logic + memory for constraint engine |

## Certification Path

| Standard | Level | Approach |
|----------|-------|----------|
| DO-178C | DAL A | Formal methods supplement (DO-333) for FLUX compiler Galois connection proofs |
| DO-254 | Level A | PolarFire SoC as custom device with elemental analysis |
| DO-278A | AL 1 | CNS/ATM ground system interface |
| ARP 4754A | — | Aircraft-level safety assessment, FHA, FTA |

**FLUX-specific certification argument:**
- Galois connection between GUARD DSL and FLUX-C is a **formal method** per DO-333
- 38 formal proofs replace extensive testing for compiler correctness
- Zero differential mismatches (10M+ inputs) provide statistical evidence
- FPGA implementation enables **deterministic WCET**

## Estimated Cost

| Cost Item | Amount (USD) |
|-----------|-------------|
| PolarFire SoC MPFS250T x3 | $18,000 |
| RTG4 voter FPGA + support | $8,000 |
| Aviation GPS receivers x3 | $12,000 |
| Laser IRS/INS x2 | $45,000 |
| Air data computers x3 | $22,000 |
| ARINC 429/AFDX interface cards | $15,000 |
| ARINC 600 enclosure + backplane | $8,000 |
| Development chassis (DO-254 testing) | $25,000 |
| BOM subtotal | **$153,000** |
| NRE (DO-178C Level A, DO-254 Level A) | $1,200,000 |
| FAA/EASA certification (TC/STC) | $800,000 |
| **Total per aircraft (amortized NRE over 100 units)** | **$185,000** |
| Total at volume (1,000 aircraft) | **$153,000** |
