## Agent 6: Smart Grid Protection Relay

**Domain:** Digital protective relay for transmission grid (110kV-765kV)
**Architect:** Agent 6 (Power Systems & IEC 61850)

### System Block Diagram

```
+------------------------------------------------------------------+
|              SMART GRID PROTECTION RELAY (Transmission Class)       |
|                    FLUX Constraint Engine                         |
+------------------------------------------------------------------+
|                                                                   |
|  +-------------------------------------------------------------+|
|  |                 DUAL INDEPENDENT ARCHITECTURE                ||
|  |                                                              ||
|  |  +------------------------+  +------------------------+      ||
|  |  |     RELAY A (Primary)  |  |     RELAY B (Backup)   |      ||
|  |  |  Xilinx Zynq UltraScale+|  |  Xilinx Zynq UltraScale+|      ||
|  |  |  + FPGA (real-time)    |  |  + FPGA (real-time)    |      ||
|  |  |  + A53 (IEC 61850)     |  |  + A53 (IEC 61850)     |      ||
|  |  |  + FLUX-C Engine       |  |  + FLUX-C Engine       |      ||
|  |  +-----------+------------+  +-----------+------------+      ||
|  |              |                          |                      ||
|  |              v                          v                      ||
|  |  +---------------------------------------------------------+ ||
|  |  |           IEC 61850-8-1 GOOSE / MMS COMMUNICATION       | ||
|  |  |           Time-sync (IEEE 1588 PTP / IRIG-B)              | ||
|  |  +---------------------------------------------------------+ ||
|  +-------------------------------------------------------------+|
|                                                                   |
|  +-------------------------------------------------------------+|
|  |              ANALOG FRONT-END (High-Speed ADC)               ||
|  |  CT / VT inputs (x9: 3-phase voltage + current, neutral)      ||
|  |  Rogowski coils (x3)  |  Optical CT (x3)  |  Resistive VT  ||
|  |  Sampling: 256 samples/cycle @ 60 Hz = 15.36 kS/s            ||
|  |  (oversampled to 100 kS/s for harmonic analysis)            ||
|  +-------------------------------------------------------------+|
|                                                                   |
|  +-------------------------------------------------------------+|
|  |              TRIP OUTPUT (Solid-State + Electromechanical)   ||
|  |  High-speed trip (thyristor) < 2 ms                          ||
|  |  Lockout relay (electromechanical) < 50 ms                   ||
|  +-------------------------------------------------------------+|
|                                                                   |
+------------------------------------------------------------------+
```

### Constraint Budget

| Constraint Category | Count | Type | Update Rate | Source |
|---------------------|-------|------|-------------|--------|
| Overcurrent (instantaneous) | 6,000 | Threshold (INT8) | 100 kHz | Per-sample CT |
| Overcurrent (time-inverse) | 6,000 | Range/Timer (INT8) | 100 kHz | IEC 60255 curves |
| Differential protection (87) | 3,000 | Range (INT8) | 100 kHz | Restrained differential |
| Distance protection (21) | 4,000 | Geofence/Range | 100 kHz | Impedance plane zones |
| Directional overcurrent (67) | 3,000 | Enum/Range | 100 kHz | Phase comparison |
| Voltage restraint (27/59) | 4,000 | Range (INT8) | 100 kHz | Undervolt / overvolt |
| Frequency protection (81) | 6,000 | Range (INT8) | 100 kHz | ROCOF, UF/OF |
| Harmonic restraint (2nd, 5th) | 4,000 | Range (INT8) | 100 kHz | FFT per cycle |
| Power swing blocking | 4,000 | Range (INT8) | 100 kHz | Rate of impedance change |
| Synchronism check (25) | 2,000 | Range (INT8) | 100 kHz | Slip frequency, angle |
| Breaker failure (50BF) | 2,000 | Timer/Boolean | 100 kHz | Current + time |
| FLISR (fault isolation) | 4,000 | Boolean/Enum | 100 kHz | Sectionalizer logic |
| **TOTAL** | **48,000** | Mostly INT8 | 100 kHz | — |

At 100 kHz with 48,000 constraints: 4.8 billion evaluations/sec. Zynq UltraScale+ FPGA fabric at 200 MHz with parallel FLUX-C execution units sustains ~5B constraints/sec. **1x headroom** — this is a tight but feasible design with pipelined and parallel execution lanes.

### Hardware Selection

**Primary: Xilinx Zynq UltraScale+ ZU19EG (Dual independent relays)**
- **FPGA:** 1,143K logic cells, 6,840 DSP slices for FFT/filter banks
- **Processor:** Quad-core Cortex-A53 for IEC 61850 communication, HMI, logging
- **ADC interface:** TI ADS54J60 16-bit 1 GSPS ADC, 9 channels via JESD204B
- **I/O:** 256 digital I/O, Gigabit Ethernet (IEC 61850 GOOSE/MMS)
- **Time sync:** Hardware IEEE 1588 PTP with < 1 us accuracy

**Justification:**
1. **Throughput necessity:** 4.8B constraints/sec at 100 kHz is the highest evaluation rate of all 10 architectures. Only FPGA with massively parallel execution lanes can meet this. GPU cannot guarantee <50 us latency end-to-end due to kernel launch overhead and non-determinism.
2. **Determinism:** Protection relay requires < 4 ms total operate time (IEEE C37.90). FPGA provides cycle-accurate timing. Each sample is processed in fixed pipeline stages.
3. **Signal processing integration:** Zynq's DSP slices implement FFT, IIR/FIR filters, and phasor estimation on the same die as FLUX constraint engine. Eliminates inter-chip latency.
4. **Dual independent:** Relay A and B are fully separate (no shared power, no shared ADC, no shared trip path). Primary failure does not impair backup — meets N-1 reliability for transmission grid.

**ADC selection:** TI ADS54J60 (16-bit, 1 GSPS) with anti-aliasing and isolation amplifiers. 9 channels (3-phase V, 3-phase I, neutral V, neutral I, zero-sequence). Oversampled to 100 kHz effective with digital decimation.

### Latency Budget Breakdown

| Stage | Time | Cumulative | Notes |
|-------|------|------------|-------|
| CT/VT signal conditioning | 10 us | 10 us | Anti-aliasing + isolation amp |
| ADC sampling + digital filtering | 20 us | 30 us | CIC + FIR decimation to 100 kHz |
| Phasor estimation (DFT/FFT) | 15 us | 45 us | 1-cycle DFT on FPGA DSP slices |
| FLUX constraint execution (48K @ 100kHz) | 30 us | 75 us | Parallel FPGA lanes, 200 MHz |
| Protection logic + timer management | 8 us | 83 us | Boolean combinations, definite time |
| GOOSE message generation | 10 us | 93 us | IEC 61850-8-1 Ethernet frame |
| Trip output (solid-state) | 5 us | 98 us | Thyristor / IGBT gate drive |
| Breaker mechanical operation | 30-100 ms | — | SF6 / vacuum breaker |
| **TOTAL (relay operate time)** | **~42 us** | — | Meets IEEE C37.90 < 4 ms (includes breaker) |
| **TOTAL (to fault isolation)** | **< 50 ms** | — | Meets grid stability requirements |

The 42 us relay compute time is dominated by FLUX constraint execution (30 us). Pipelined design with 16 parallel lanes each handling 3,000 constraints provides throughput. For time-critical elements (instantaneous overcurrent), dedicated hardware comparators bypass FLUX entirely, achieving <5 us.

### Redundancy Strategy

**Architecture: Dual independent with no shared elements**

| Element | Implementation |
|---------|---------------|
| Relay A | Primary protection, Zynq UltraScale+ with dedicated CT/VT set |
| Relay B | Backup protection, identical hardware, separate CT/VT set |
| CT/VT | Separate current transformers and voltage transformers for A and B (physical separation) |
| Trip path | Separate trip coils on breaker (dual trip coil breaker) |
| Communication | Independent GOOSE messages; subscribing IEDs vote on A and B outputs |
| Time sync | Independent PTP grandmasters; IRIG-B backup |
| Power | Independent 125V DC station batteries for A and B |
| Test | Independent test switches; online testing of B while A protects |

**Rationale:** NERC CIP and utility practice mandate independent primary and backup protection. Any single failure (relay, CT, VT, trip coil, battery, communication) leaves the other system fully functional. "Independent" means no shared components — not even a common chassis ground.

### Power Budget

| Component | Power (W) | Notes |
|-----------|-----------|-------|
| Zynq UltraScale+ (x2, active) | 20 | 10W each @ 200 MHz FPGA + 1 GHz A53 |
| High-speed ADC (x18, 9 per relay) | 18 | 1W each, JESD204B |
| Analog front-end (isolation, filters) | 8 | 4W per relay |
| Ethernet PHY + magnetics (x4) | 4 | GOOSE + MMS + debug |
| Optocoupler trip outputs (x8) | 2 | Gate drive for thyristors |
| Electromechanical lockout relays | 3 | Coil holding current |
| GPS/PTP time sync modules (x2) | 2 | Grandmaster + slave |
| DC-DC conversion (125V -> 5V/3.3V) | 5 | Isolated, redundant |
| Enclosure + natural convection | 2 | Substation environment |
| **TOTAL** | **64 W** | — |
| FLUX compute specifically | ~8 W | FPGA fabric for 48K constraint lanes |

### Certification Path

| Standard | Level | Approach |
|----------|-------|----------|
| IEC 61508 | SIL 3 | Systematic capability SC3, HFT=1 (dual independent) |
| IEC 61850 | — | Communication protocol compliance (GOOSE, SV, MMS) |
| IEEE C37.90 | — | Standard for relays and relay systems (surge, oscillatory, fast transient) |
| IEEE 1547 | — | Interconnection and interoperability (DER, inverter-based resources) |
| NERC CIP-002/003 | — | Cybersecurity for critical cyber assets |
| UL 508 | — | Industrial control equipment safety |

**FLUX-specific certification argument:**
- **Deterministic execution at 100 kHz:** Each sample processed in fixed FPGA cycles. Supports complete test coverage via simulation of all fault types (AG, BG, CG, AB, BC, CA, ABC, 3-phase ground, etc.).
- **Formal equivalence:** GUARD DSL protection rules map directly to IEC 60255 curve equations. Galois connection ensures compiled FPGA logic matches source equations exactly.
- **No dynamic allocation:** All constraints pre-allocated, all memory pre-mapped. Supports IEC 61508 SIL 3 static analysis requirements.
- **Traceability:** Each protection element (constraint) has unique identifier linking to single-line diagram, relay setting sheet, and protection study report.

### Estimated Cost

| Cost Item | Amount (USD) |
|-----------|-------------|
| Zynq UltraScale+ ZU19EG x2 | $8,000 |
| TI ADS54J60 ADC x18 | $5,400 |
| CT/VT isolation amplifiers x36 | $2,800 |
| Anti-aliasing filter networks x18 | $1,200 |
| Ethernet PHY + magnetics x4 | $400 |
| Optocoupler trip outputs x8 | $600 |
| Lockout relays (electromechanical) x4 | $1,200 |
| PTP/GPS time sync modules x2 | $1,600 |
| Substation-rated enclosure (IP54) | $2,000 |
| Redundant DC-DC power supplies x4 | $1,800 |
| BOM subtotal | **$25,000** |
| NRE (IEC 61508 SIL 3, IEEE C37.90 testing) | $120,000 |
| Type testing (dIEC, EMC, environmental) | $45,000 |
| **Total per relay pair (amortized NRE over 20 units)** | **$14,500** |
| Total at volume (200 substations, production line) | **$9,000** |

---