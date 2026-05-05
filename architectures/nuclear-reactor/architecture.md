## Agent 3: Nuclear Reactor Safety System

**Domain:** Pressurized Water Reactor (PWR) safety instrumentation and control
**Architect:** Agent 3 (Nuclear I&C Systems, IEC 61508/62340)

### System Block Diagram

```
+------------------------------------------------------------------+
|              NUCLEAR REACTOR SAFETY SYSTEM (Reactor Protection)   |
|                    FLUX Constraint Engine                         |
+------------------------------------------------------------------+
|                                                                   |
|  +-------------------------------------------------------------+|
|  |                    2-out-of-3 (2oo3) ARCHITECTURE            ||
|  |                                                              ||
|  |  +----------------+  +----------------+  +----------------+ ||
|  |  |   CHANNEL A    |  |   CHANNEL B    |  |   CHANNEL C    | ||
|  |  |  Microchip     |  |  Microchip     |  |  Microchip     | ||
|  |  |  PolarFire RT  |  |  PolarFire RT  |  |  PolarFire RT  | ||
|  |  |  FPGA (150K LE)|  |  FPGA (150K LE)|  |  FPGA (150K LE)| ||
|  |  |  No processor  |  |  No processor  |  |  No processor  | ||
|  |  |  Pure FPGA     |  |  Pure FPGA     |  |  Pure FPGA     | ||
|  |  +-------+--------+  +-------+--------+  +-------+--------+ ||
|  |          |                    |                    |         ||
|  |          v                    v                    v         ||
|  |  +---------------------------------------------------------+||
|  |  |           2oo3 COINCIDENCE LOGIC (Actuation Voting)     |||
|  |  |    Hardware-only voter, no software, no processor       |||
|  |  +---------------------------------------------------------+||
|  +-------------------------------------------------------------+|
|                                                                   |
|  +-------------------------------------------------------------+|
|  |                     SENSOR INPUTS (Class 1E)                 ||
|  |  Neutron flux (x4)  |  Core temp (x8)  |  Primary pressure  ||
|  |  (fission chambers)  |  (RTD/Thermocouple)  |  (dP transmitters)||
|  |  Flow rate (x4)     |  Rod position (x16)|  Containment pressure||
|  |  (venturi/ultrasonic)|  (LVDT/RVDT)      |  (strain gauges)   ||
|  +-------------------------------------------------------------+|
|                                                                   |
|  +-------------------------------------------------------------+|
|  |                     SAFETY ACTUATION OUTPUTS                 ||
|  |  Reactor Trip (scram)  |  Safety Injection (SI)  |  Aux Feed ||
|  |  (control rod drop)    |  (pump start)          |  (pump/turb)||
|  |  Containment Iso.      |  Main Steam Iso.        |  Feedwater iso||
|  +-------------------------------------------------------------+|
|                                                                   |
|  +-------------------------------------------------------------+|
|  |                     FAIL-SAFE DESIGN                         ||
|  |  De-energize to trip: loss of power = safe state (rods in)  ||
|  |  Independent test facility: periodic online testing         ||
|  +-------------------------------------------------------------+|
|                                                                   |
+------------------------------------------------------------------+
```

### Constraint Budget

| Constraint Category | Count | Type | Update Rate | Source |
|---------------------|-------|------|-------------|--------|
| Neutron flux (power level) | 400 | Range (INT8) | 10 Hz | Ex-core fission chambers |
| Core coolant temperature | 320 | Range (INT8) | 10 Hz | RTD (Pt100) |
| Primary loop pressure | 160 | Range (INT8) | 10 Hz | Differential pressure |
| Core coolant flow rate | 160 | Range (INT8) | 10 Hz | Venturi + ultrasonic |
| Control rod position | 320 | Range (INT8) | 10 Hz | LVDT/RVDT |
| Containment pressure | 80 | Range (INT8) | 10 Hz | Strain gauge |
| Steam generator level | 240 | Range (INT8) | 10 Hz | Differential pressure |
| Feedwater flow / temp | 160 | Range (INT8) | 10 Hz | Venturi + RTD |
| Turbine / generator params | 160 | Range (INT8) | 10 Hz | Various |
| Safety system availability | 400 | Boolean | 10 Hz | Self-test + status |
| **TOTAL** | **2,400** | Mixed INT8/Boolean | 10 Hz | — |

Worst-case: 2,400 constraints x 10 Hz = 24,000 evaluations/sec. PolarFire RT at 50 MHz executes FLUX-C pipeline at ~2M constraints/sec (83x headroom). Conservative design leaves margin for expanded sensor coverage during plant modifications.

### Hardware Selection

**Primary: Microchip PolarFire RT (Radiation-Tolerant FPGA, no processor)**
- **FPGA:** 150K logic elements, flash-based configuration (SEU-immune)
- **Processor:** None — pure hardware implementation for safety actuation
- **I/O:** 3.3V/5V TTL, isolated via optocouplers to meet Class 1E separation
- **Temperature:** -55C to +125C (military-grade)
- **Qualification:** QML Class V (radiation tolerant)

**Justification:**
1. **No processor = no common-cause software faults:** Nuclear safety systems traditionally avoid software on the actuation path. FLUX-C executes as a hardware state machine with no OS, no scheduler, no interrupts.
2. **Flash-based immunity:** Unlike SRAM FPGAs requiring scrubbing, flash FPGAs hold configuration permanently. SEU cross-section is effectively zero for configuration bits.
3. **Deterministic execution:** Fixed 10 Hz cycle, fixed latency per constraint, fully synchronous design. WCET = BCET (best-case = worst-case).
4. **Separation:** PolarFire's non-volatile nature allows power-cycling for test without configuration loss — critical for online testing requirements in nuclear plants.

**Voter:** Discrete analog/digital 2oo3 coincidence logic (hardware only, no programmable devices). Traditional relay ladder or discrete solid-state logic satisfies regulatory preference for non-programmable final actuation voting.

### Latency Budget Breakdown

| Stage | Time | Cumulative | Notes |
|-------|------|------------|-------|
| Sensor acquisition (analog -> digital) | 20 ms | 20 ms | Isolated ADC, 16-bit, anti-aliasing filter |
| Input conditioning (linearization, cold junction) | 10 ms | 30 ms | FPGA lookup tables + polynomial |
| FLUX constraint execution (2.4K @ 10Hz) | 1.2 ms | 31.2 ms | Pure FPGA state machine |
| 2oo3 coincidence logic | 5 ms | 36.2 ms | Hardware relay/solid-state voter |
| Actuation driver (breaker control) | 10 ms | 46.2 ms | SCR firing or relay coil |
| Control rod drop (physical) | 1.5-4.0 s | — | Gravity-driven rod insertion |
| **TOTAL (compute + voting)** | **~85 ms** | — | Meets IEEE 279 < 200 ms requirement |
| **TOTAL (to safe state)** | **< 4.5 s** | — | Meets 10 CFR 50.62 ECCS requirement |

Nuclear reactor dynamics are slow (thermal time constants: seconds to minutes). 85 ms compute latency is negligible compared to physical plant response. The safety requirement is **fail-safe reliability**, not speed — making FPGA's determinism more valuable than GPU's throughput.

### Redundancy Strategy

**Architecture: 2-out-of-3 voting with channel independence**

| Element | Implementation |
|---------|---------------|
| Channel A/B/C | Independent PolarFire RT FPGA on independent 125V DC bus |
| Sensor separation | Each channel has dedicated sensor trains (4x neutron detectors per channel) |
| Physical separation | Channels in separate fire zones, seismic isolation, electromagnetic shielding |
| 2oo3 voter | Hardware coincidence logic: any 2 channels demanding trip -> actuate |
| Testability | Each channel has independent test switch; online testing possible with channel in "test" mode (voter blocks test channel) |
| Fail-safe | De-energize to trip: power loss to any channel causes "trip" state from that channel, 2oo3 logic still functional with 2 remaining |
| Diversity | Diverse sensor types (fission chambers + SPNDs) for neutron flux; no common sensor design |

**Rationale:** Nuclear Regulatory Commission (NRC) requires defense-in-depth. 2oo3 is the industry standard for reactor protection. De-energize-to-trip ensures power failure is safe. Channel independence prevents common-cause failures (fire, flood, software bug).

### Power Budget

| Component | Power (W) | Notes |
|-----------|-----------|-------|
| PolarFire RT FPGA (x3) | 9 | 3W each @ 50 MHz, mostly static |
| Sensor excitation + ADC (x3 trains) | 12 | 4W per channel, isolated supplies |
| Optocoupler isolation banks | 3 | 72 channels, high-speed digital isolators |
| 2oo3 coincidence logic (discrete) | 2 | Solid-state relays + logic |
| Actuation drivers (SCR, relay coils) | 0 | Sourced from plant 125V DC, not safety system |
| Enclosure + passive cooling | 2 | Conduction to cabinet, no fans |
| **TOTAL** | **28 W** | — |
| FLUX compute specifically | ~2 W | FPGA fabric for constraint pipeline |

Extremely low power is critical for battery-backed operation during station blackout (SBO) events. 28W can be sustained for hours on Class 1E 125V DC batteries.

### Certification Path

| Standard | Level | Approach |
|----------|-------|----------|
| IEC 61508 | SIL 3 | Systematic capability SC3, HFT=1 (2oo3) |
| IEC 62340 | — | Nuclear power plant instrumentation and control |
| IEEE 603 | — | Standard criteria for safety systems for nuclear power plants |
| 10 CFR 50 Appendix B | — | NRC quality assurance criteria |
| RG 1.153 | — | NRC guide for safety system software |

**FLUX-specific certification argument:**
- **No software on the safety path:** FLUX-C executes as FPGA hardware logic, not as software running on a processor. This avoids RG 1.153 software concerns entirely for the actuation path.
- **Formal equivalence:** Galois connection proof demonstrates that GUARD DSL constraints are semantically preserved in hardware logic. Safety analysts can review GUARD source (human-readable) while trusting FPGA implementation (machine-verified).
- **Bounded complexity:** 43 opcodes implemented as 43 distinct hardware modules. Complete test coverage achievable via exhaustive simulation.
- **Determinism:** No cache, no pipeline hazards, no interrupts. Each 100 ms cycle executes identically. Supports online comparison testing against reference software model.

### Estimated Cost

| Cost Item | Amount (USD) |
|-----------|-------------|
| PolarFire RT FPGA x3 | $9,000 |
| QML-qualified ADC modules x3 | $18,000 |
| Fission chamber detectors x12 | $35,000 |
| RTD/temperature transmitters x24 | $8,000 |
| Pressure/flow transmitters x12 | $12,000 |
| LVDT/RVDT rod position sensors x16 | $14,000 |
| Class 1E enclosure + isolation | $15,000 |
| Redundant 125V DC power supplies x3 | $6,000 |
| Actuation relays / SCR drivers | $4,000 |
| BOM subtotal | **$121,000** |
| NRE (IEC 61508 SIL 3, NRC licensing) | $450,000 |
| Environmental/ seismic qualification | $180,000 |
| **Total per reactor (amortized NRE over 5 units)** | **$95,000** |
| Total at fleet deployment (20 reactors) | **$75,000** |

---