# Energy / Grid Constraint Library (IEC 61850 / IEEE 1547)

**Standard:** IEC 61850 (substation communication), IEEE 1547 (DER interconnection), NERC CIP (cybersecurity)
**Safety Integrity:** Protection relay class, transmission grid (400 kV) and distributed generation
**Scope:** Substation automation, generator control, wide-area monitoring
**Update rates:** 1–4 kHz (protection sampled values), 1–10 Hz (SCADA)
**INT8 strategy:** 400 kV to millivolt precision for synchrophasor angles; 3.9 mHz/bit frequency resolution

---

## Voltage Constraints

### 1. bus_voltage_a — Phase A RMS
- **Bounds:** [360 kV, 420 kV]
- **Units:** kV
- **Update Rate:** 50 Hz
- **Safety Rationale:** 400 kV nominal, ±5% (380–420 kV). >420: insulation stress, corona. <360: load shedding, voltage collapse.
- **INT8 Mapping:** `offset=360000, scale=235.2941 V/bit` → q=0 at 360 kV, q=128 at 390 kV, q=170 at 400 kV, q=255 at 420 kV
- **Failure Mode:** VT fuse blow; dual VT + FLUX checks phase balance + sequence components.

### 2. bus_voltage_b — Phase B RMS
- **Bounds:** [360 kV, 420 kV]
- **Units:** kV
- **Update Rate:** 50 Hz
- **Safety Rationale:** Phase balance indicator. Unbalance >2%: single-phase fault or load imbalance.
- **INT8 Mapping:** Same as Phase A.
- **Failure Mode:** Broken conductor; negative-sequence voltage relay + FLUX unbalance calculation.

### 3. bus_voltage_c — Phase C RMS
- **Bounds:** [360 kV, 420 kV]
- **Units:** kV
- **Update Rate:** 50 Hz
- **Safety Rationale:** Three-phase symmetry required for rotating machines.
- **INT8 Mapping:** Same as Phase A.
- **Failure Mode:** Capacitor bank blown fuse on one phase; voltage rise on remaining phases.

---

## Frequency Constraints

### 4. system_frequency — Grid Frequency
- **Bounds:** [49.5 Hz, 50.5 Hz]
- **Units:** Hz
- **Update Rate:** 50 Hz
- **Safety Rationale:** 50 Hz nominal (EU). 49.5: under-frequency load shedding (UFLS) Stage 1. 50.5: over-frequency generation shedding. 47.5 Hz: blackout.
- **INT8 Mapping:** `offset=49.5, scale=0.0039 Hz/bit` → q=0 at 49.5, q=128 at 50.0, q=255 at 50.5. Resolution: 3.9 mHz/bit.
- **Failure Mode:** PMU clock sync loss (GPS); holdover oscillator + FLUX frequency rate validation.

### 5. rocof — Frequency Rate of Change
- **Bounds:** [-2.0 Hz/s, +2.0 Hz/s]
- **Units:** Hz/s
- **Update Rate:** 50 Hz
- **Safety Rationale:** >0.5 Hz/s: imminent instability. ROCOF relay trips on loss of infeed (e.g., HVDC pole trip, generator loss).
- **INT8 Mapping:** `offset=-2.0, scale=0.0157 Hz/s/bit` → q=0 at -2.0, q=127 at 0, q=255 at +2.0
- **Failure Mode:** Load switching transient; 100 ms filter + FLUX must distinguish from genuine generation loss.

---

## Current Constraints

### 6. line_current_a — Phase A
- **Bounds:** [0 A, 4000 A]
- **Units:** A
- **Update Rate:** 1000 Hz
- **Safety Rationale:** 400 kV line: 2000 A nominal, thermal limit ~3000 A. >4000 A: conductor annealing, sag to ground clearance.
- **INT8 Mapping:** `offset=0, scale=15.6863 A/bit` → q=0 at 0, q=128 at 2000, q=191 at 3000, q=255 at 4000
- **Failure Mode:** CT saturation during fault; air-core CT or optical CT for high dynamic range.

### 7. line_current_b — Phase B
- **Bounds:** [0 A, 4000 A]
- **Units:** A
- **Update Rate:** 1000 Hz
- **Safety Rationale:** Three-phase balance for transmission efficiency.
- **INT8 Mapping:** Same as Phase A.
- **Failure Mode:** High-impedance fault (tree contact); sensitive ground relay + FLUX zero-sequence detection.

### 8. line_current_c — Phase C
- **Bounds:** [0 A, 4000 A]
- **Units:** A
- **Update Rate:** 1000 Hz
- **Safety Rationale:** Phase comparison for line differential protection.
- **INT8 Mapping:** Same as Phase A.
- **Failure Mode:** CT ratio mismatch; line differential must compensate per tap settings.

---

## Power Quality Constraints

### 9. power_factor
- **Bounds:** [0.85 lag, 1.0]
- **Units:** dimensionless
- **Update Rate:** 1 Hz
- **Safety Rationale:** Low PF: increased reactive power flow, voltage drop, equipment overload. >0.95 lag preferred.
- **INT8 Mapping:** `offset=0.85, scale=0.000588/bit` → q=0 at 0.85, q=128 at 0.925, q=255 at 1.0
- **Failure Mode:** Capacitor bank out of service; automatic switching + FLUX voltage support request.

### 10. active_power_gen — Generator Active Power
- **Bounds:** [0 MW, 1000 MW]
- **Units:** MW
- **Update Rate:** 1 Hz
- **Safety Rationale:** Generator output vs. spinning reserve. >1000 MW: turbine limit. Sudden drop: grid frequency event.
- **INT8 Mapping:** `offset=0, scale=3.9216 MW/bit` → q=0 at 0, q=128 at 500, q=255 at 1000
- **Failure Mode:** Generator trip; droop response + secondary frequency control.

### 11. reactive_power_gen — Generator Reactive Power
- **Bounds:** [-500 MVAr, +500 MVAr]
- **Units:** MVAr
- **Update Rate:** 1 Hz
- **Safety Rationale:** Over-excited (+): voltage support. Under-excited (-): stability limit (SSSL).
- **INT8 Mapping:** `offset=-500, scale=3.9216 MVAr/bit` → q=0 at -500, q=127 at 0, q=255 at +500
- **Failure Mode:** AVR failure to minimum excitation limiter (MEL); loss of synchronism.

---

## Load Balancing Constraints

### 12. transformer_oil_temp — Transformer Oil Temperature
- **Bounds:** [20°C, 105°C]
- **Units:** °C
- **Update Rate:** 1 Hz
- **Safety Rationale:** IEC 60076-7 loading guide. 105°C: alarm. 115°C: trip. Insulation aging doubles every 6°C above 98°C.
- **INT8 Mapping:** `offset=20, scale=0.3333 °C/bit` → q=0 at 20°C, q=60 at 40°C, q=128 at 63°C, q=255 at 105°C
- **Failure Mode:** Cooling fan/pump failure; FLUX activates backup fans + load reduction request.

### 13. transformer_hot_spot — Winding Hot Spot
- **Bounds:** [20°C, 140°C]
- **Units:** °C
- **Update Rate:** 1 Hz
- **Safety Rationale:** Hot spot >98°C: cellulose insulation degradation. 140°C: emergency load limit. Fiber-optic sensor direct measurement.
- **INT8 Mapping:** `offset=20, scale=0.4706 °C/bit` → q=0 at 20°C, q=85 at 60°C, q=170 at 100°C, q=255 at 140°C
- **Failure Mode:** Hysteresis in thermal model; direct measurement preferred for critical transformers.

### 14. sf6_pressure — GIS Switchgear SF6 Pressure
- **Bounds:** [5.0 bar(abs), 7.5 bar(abs)]
- **Units:** bar(abs)
- **Update Rate:** 1 Hz
- **Safety Rationale:** SF6 insulation strength depends on density. <5.0: alarm, lockout operation. Leak = environmental (GWP 23,500).
- **INT8 Mapping:** `offset=5.0, scale=0.0098 bar/bit` → q=0 at 5.0, q=128 at 6.25, q=255 at 7.5
- **Failure Mode:** Seal degradation; FLUX trends pressure vs. temperature compensated density.

### 15. breaker_operating_time — Circuit Breaker Timing
- **Bounds:** [20 ms, 80 ms]
- **Units:** ms
- **Update Rate:** 0.01 Hz
- **Safety Rationale:** Opening time: 20–60 ms (SF6), 40–80 ms (air). Slower: fault clearing exceeds equipment rating.
- **INT8 Mapping:** `offset=0, scale=0.3137 ms/bit` → q=64 at 20, q=128 at 40, q=255 at 80
- **Failure Mode:** Mechanism spring fatigue; FLUX trends operating time + flags >10% increase.

### 16. synchrophasor_angle_diff — Wide-Area Angle Difference
- **Bounds:** [-30°, +30°]
- **Units:** degrees
- **Update Rate:** 50 Hz
- **Safety Rationale:** PMU wide-area angle difference across grid. >20°: stress, >30°: separation risk.
- **INT8 Mapping:** `offset=-30, scale=0.2353 deg/bit` → q=0 at -30°, q=127 at 0°, q=255 at +30°
- **Failure Mode:** GPS timing error (spoofing); common-view GPS + atomic clock holdover.

---

## DER / Inverter Constraints

### 17. inverter_dc_link — DER Inverter DC Bus
- **Bounds:** [600 V, 1000 V]
- **Units:** V
- **Update Rate:** 1000 Hz
- **Safety Rationale:** Solar PV string / battery DC bus. 800 V nominal. >1000: IGBT overvoltage. <600: MPPT lost.
- **INT8 Mapping:** `offset=600, scale=1.5686 V/bit` → q=0 at 600, q=128 at 800, q=255 at 1000
- **Failure Mode:** Cloud transient causes rapid rise; chopper + DC crowbar protection.

### 18. der_frequency_ride_through — DER Frequency Ride-Through
- **Bounds:** [47.0 Hz, 52.0 Hz]
- **Units:** Hz
- **Update Rate:** 50 Hz
- **Safety Rationale:** IEEE 1547-2018: must ride through 47–52 Hz for specified durations. Trip outside: contributes to cascade.
- **INT8 Mapping:** `offset=47.0, scale=0.0196 Hz/bit` → q=0 at 47.0, q=153 at 50.0, q=255 at 52.0
- **Failure Mode:** Inverter anti-islanding false trip; FLUX checks vector shift + ROCOF consistency.

### 19. der_voltage_ride_through — DER Low Voltage Ride-Through
- **Bounds:** [0.0 pu, 1.2 pu]
- **Units:** per-unit
- **Update Rate:** 50 Hz
- **Safety Rationale:** LVRT: must stay connected 0–0.5 s at 0 pu, 2 s at 0.5 pu. Supports grid during fault.
- **INT8 Mapping:** `offset=0, scale=0.0047 pu/bit` → q=0 at 0, q=85 at 0.4, q=213 at 1.0, q=255 at 1.2
- **Failure Mode:** Inverter current limit saturation during voltage dip; reactive current injection priority.

---

## Station Auxiliaries

### 20. substation_battery — DC Station Supply
- **Bounds:** [105 V, 130 V]
- **Units:** V (DC)
- **Update Rate:** 1 Hz
- **Safety Rationale:** 110V nominal for protection relays, breaker trip coils, SCADA. <105: trip coil under-voltage. >130: overcharge.
- **INT8 Mapping:** `offset=105, scale=0.0980 V/bit` → q=0 at 105V, q=128 at 117.5V, q=255 at 130V
- **Failure Mode:** Charger failure; FLUX monitors battery discharge rate during AC loss.

### 21. thd_voltage — Voltage Harmonic Distortion
- **Bounds:** [0%, 8%]
- **Units:** %
- **Update Rate:** 1 Hz
- **Safety Rationale:** IEC 61000: THD <5% normal, <8% acceptable. High THD: transformer overheating, capacitor resonance.
- **INT8 Mapping:** `offset=0, scale=0.0314 %/bit` → q=0 at 0%, q=128 at 4%, q=159 at 5%, q=255 at 8%
- **Failure Mode:** PWM drive harmonics; passive/active filter + FLUX selective harmonic monitoring.

### 22. ltc_position — Load Tap Changer Position
- **Bounds:** [0, 33]
- **Units:** steps
- **Update Rate:** 1 Hz
- **Safety Rationale:** 33 steps = ±10% voltage adjustment. Step 16 = nominal. Excessive operations: mechanical wear, oil degradation.
- **INT8 Mapping:** `offset=0, scale=0.1294 steps/bit` → q=0 at 0, q=124 at 16, q=255 at 33. Discrete: FLUX rounds to nearest integer.
- **Failure Mode:** Tap stuck between positions (arc, fire); voltage ratio check detects non-integer effective ratio.

### 23. line_sag — Transmission Line Sag
- **Bounds:** [0 m, 15 m]
- **Units:** m
- **Update Rate:** 0.1 Hz
- **Safety Rationale:** Dynamic thermal rating (DLR): sag increases with current. >15 m: ground clearance violation.
- **INT8 Mapping:** `offset=0, scale=0.0588 m/bit` → q=0 at 0, q=85 at 5, q=170 at 10, q=255 at 15
- **Failure Mode:** High wind + high current; FLUX computes real-time ampacity from sag measurement.

---

## Library Summary

| Metric | Value |
|--------|-------|
| Total Constraints | 23 |
| Highest Update Rate | 1000 Hz (line current, inverter DC link) |
| Key Challenge | 3.9 mHz/bit at 50 Hz — rounding to wrong side of 50.0 triggers false trip |
| Protocol | IEC 61850 GOOSE: 3 ms end-to-end; sampled values: 4 kHz |
| Quantization Difficulty | Easy — direct affine for most; medium for ride-through curves |

*Source: Mission 2 Agent 9 — IEC 61850 / IEEE 1547 domain library*
