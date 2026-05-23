# Aviation Constraint Library (DO-178C / ARP-4761)

**Standard:** DO-178C, ARP-4761  
**Development Assurance Level:** DAL A (catastrophic failure condition)  
**Target:** Transport-category aircraft (Boeing/Airbus class)  
**Total Constraints:** 28  
**Highest Update Rate:** 1000 Hz (AOA, windshear)

Aviation constraints satisfy DO-178C software assurance and ARP-4761 safety assessment. Update rates range from 10 Hz (cabin environmental) to 1000 Hz (primary flight control surfaces). INT8 quantization preserves resolution at low airspeeds while accommodating cruise-flight dynamic range.

---

## 1. Airspeed — Indicated (KIAS)
```
constraint airspeed_indicated {
  min: 50 knots,
  max: 450 knots,
  update: 50Hz
}
```
- **Safety Rationale:** Stall below minimum; structural damage / flutter above maximum. KIAS is pilot-reference critical.
- **INT8 Mapping:** `offset = 0, scale = 1.7647 kn/bit` → q=29 at 50 kn, q=255 at 450 kn. Nonlinear: CAS<100 kn uses expanded lower nibble (sub-bit interpolation reserved for flaps-extended regime).
- **Failure Mode:** Pitot-static blockage → false low reading; FLUX must cross-check with IRS ground speed + ADC diagnostic flag.

## 2. Airspeed — True (KTAS)
```
constraint airspeed_true {
  min: 55 knots,
  max: 520 knots,
  update: 50Hz
}
```
- **Safety Rationale:** Navigation, fuel burn, and performance calculations depend on KTAS. Deviations cause range errors and altitude-clearance violations.
- **INT8 Mapping:** `offset = 0, scale = 2.0392 kn/bit` → q=27 at 55 kn, q=255 at 520 kn.
- **Failure Mode:** ADC temperature probe failure causes density altitude error; must be bounded against IRS-derived TAS.

## 3. Altitude — Pressure (hPa)
```
constraint altitude_pressure {
  min: 200 hPa (~39,000 ft),
  max: 1050 hPa (sea level),
  update: 25Hz
}
```
- **Safety Rationale:** Reduced vertical separation minima (RVSM) require ±50 ft accuracy. Pressure altitude drives TCAS and transponder reporting.
- **INT8 Mapping:** `offset = 200, scale = 3.3333 hPa/bit` → q=0 at 200 hPa, q=255 at 1050 hPa. Inverted sense: lower q = higher altitude.
- **Failure Mode:** Static port icing → altimeter reads high; cross-check with GPS altitude and radar altimeter below 2500 ft.

## 4. Altitude — Radar (AGL)
```
constraint altitude_radar {
  min: 0 ft,
  max: 2500 ft,
  update: 100Hz
}
```
- **Safety Rationale:** Ground proximity warning (EGPWS) primary input. Decision height for CAT III approaches.
- **INT8 Mapping:** `offset = 0, scale = 9.8039 ft/bit` → q=0 at 0 ft, q=255 at 2500 ft. Nonlinear below 100 ft: 1 ft/bit resolution (nibble expansion).
- **Failure Mode:** Terrain database mismatch; FLUX must validate against GPS position + terrain model.

## 5. Pitch Angle
```
constraint attitude_pitch {
  min: -25 degrees,
  max: +30 degrees,
  update: 500Hz
}
```
- **Safety Rationale:** Excessive pitch leads to stall (nose-high) or terrain impact (nose-low). AFCS envelope protection.
- **INT8 Mapping:** `offset = -25, scale = 0.2157 deg/bit` → q=0 at -25°, q=255 at +30°. Midpoint q=116 at 0°.
- **Failure Mode:** IRS gyro drift; dual-channel voting with third monitor channel required per ARINC 704.

## 6. Roll Angle
```
constraint attitude_roll {
  min: -67 degrees,
  max: +67 degrees,
  update: 500Hz
}
```
- **Safety Rationale:** Bank angle limit prevents spiral instability and structural load factor exceedance (2.5g limit at 67°).
- **INT8 Mapping:** `offset = -67, scale = 0.5255 deg/bit` → q=0 at -67°, q=255 at +67°. Midpoint q=127 at 0°.
- **Failure Mode:** ADIRU failure producing constant roll offset; compare with standby attitude indicator.

## 7. Heading — True
```
constraint heading_true {
  min: 0 degrees,
  max: 359 degrees,
  update: 25Hz
}
```
- **Safety Rationale:** Navigation integrity, airspace boundary compliance, approach course tracking.
- **INT8 Mapping:** `offset = 0, scale = 1.4118 deg/bit` → q=0 at 0°, q=255 wraps to 359°. Circular domain: wraparound logic in FLUX `constraint` block.
- **Failure Mode:** Magnetic variation database error; true heading from IRS preferred for oceanic / polar ops.

## 8. Angle of Attack (AOA)
```
constraint angle_of_attack {
  min: -2 degrees,
  max: +18 degrees,
  update: 1000Hz
}
```
- **Safety Rationale:** Stall warning and stick shaker trigger. Critical for envelope protection; 1° accuracy required near stall.
- **INT8 Mapping:** `offset = -2, scale = 0.0784 deg/bit` → q=0 at -2°, q=255 at +18°. High resolution: ~0.08°/bit.
- **Failure Mode:** Vane icing or sensor mounting damage; triple-vote with synthetic AOA from inertial + air data.

## 9. Engine N1 (Fan Speed)
```
constraint engine_n1 {
  min: 18 %,
  max: 105 %,
  update: 100Hz
}
```
- **Safety Rationale:** Primary thrust control parameter. Overspeed causes turbine blade liberation (uncontained failure).
- **INT8 Mapping:** `offset = 0, scale = 0.4118 %/bit` → q=44 at 18%, q=255 at 105%.
- **Failure Mode:** FADEC sensor fault or fuel control stuck-open; independent N1/N2/N3 (turbofan) cross-check.

## 10. Engine N2 (Core Speed)
```
constraint engine_n2 {
  min: 55 %,
  max: 102 %,
  update: 100Hz
}
```
- **Safety Rationale:** Core overspeed damages high-pressure compressor/turbine. Surge margin monitored via N2/N1 ratio.
- **INT8 Mapping:** `offset = 0, scale = 0.4000 %/bit` → q=138 at 55%, q=255 at 102%.
- **Failure Mode:** Shaft shear or sensor gear failure; N2-N1 coherence check at steady-state.

## 11. Engine EGT (Exhaust Gas Temperature)
```
constraint engine_egt {
  min: 200 °C,
  max: 950 °C,
  update: 50Hz
}
```
- **Safety Rationale:** Overtemp degrades turbine blade creep life; redline exceeded = mandatory inspection. Takeoff EGT margin defines payload/range capability.
- **INT8 Mapping:** `offset = 200, scale = 2.9412 °C/bit` → q=0 at 200°C, q=255 at 950°C.
- **Failure Mode:** Thermocouple open-circuit reads low (false safe); detect via impedance monitoring.

## 12. Fuel Flow per Engine
```
constraint fuel_flow {
  min: 150 kg/h,
  max: 12,000 kg/h,
  update: 10Hz
}
```
- **Safety Rationale:** Fuel imbalance, leak detection, and range verification. Sudden increase may indicate leak; sudden decrease may indicate flameout.
- **INT8 Mapping:** `offset = 0, scale = 47.0588 kg/h/bit` → q=3 at 150 kg/h, q=255 at 12,000 kg/h.
- **Failure Mode:** Flow meter turbine jam; compare with FADEC-computed flow from N1/EPR + bleed demand.

## 13. Hydraulic Pressure — System A
```
constraint hydraulic_pressure_a {
  min: 2200 psi,
  max: 3500 psi,
  update: 100Hz
}
```
- **Safety Rationale:** Primary flight controls (ailerons, elevator, rudder) require 2800 psi nominal. Below 2200 psi: degraded authority; above 3500 psi: seal blowout risk.
- **INT8 Mapping:** `offset = 2200, scale = 5.0980 psi/bit` → q=0 at 2200 psi, q=255 at 3500 psi.
- **Failure Mode:** Engine-driven pump failure; electric pump auto-start monitored via FLUX pressure-rate check.

## 14. Hydraulic Pressure — System B
```
constraint hydraulic_pressure_b {
  min: 2200 psi,
  max: 3500 psi,
  update: 100Hz
}
```
- **Safety Rationale:** Redundant hydraulic system for flight controls and landing gear. Loss of both = manual reversion (catastrophic if not managed).
- **INT8 Mapping:** Same as System A.
- **Failure Mode:** RAT (Ram Air Turbine) deployment required on dual failure; FLUX triggers at combined pressure < 2400 psi.

## 15. Cabin Pressure Differential
```
constraint cabin_delta_p {
  min: 0 psi,
  max: 9.1 psi,
  update: 10Hz
}
```
- **Safety Rationale:** Structural limit of pressure vessel. Excessive differential causes fuselage rupture; negative differential risks inward collapse.
- **INT8 Mapping:** `offset = 0, scale = 0.0357 psi/bit` → q=0 at 0 psi, q=255 at 9.1 psi.
- **Failure Mode:** Outflow valve actuator runaway; cabin rate-of-change must also be constrained.

## 16. Cabin Altitude Rate
```
constraint cabin_altitude_rate {
  min: -2000 ft/min,
  max: +2000 ft/min,
  update: 25Hz
}
```
- **Safety Rationale:** Rapid decompression causes hypoxia and barotrauma; rapid compression causes sinus/ear injury. Passenger comfort + physiological limits.
- **INT8 Mapping:** `offset = -2000, scale = 15.6863 ft/min/bit` → q=0 at -2000, q=127 at 0, q=255 at +2000.
- **Failure Mode:** Outflow valve hardover; FLUX rate-limit check + master warning trigger.

## 17. Flap Position
```
constraint flap_position {
  min: 0 degrees,
  max: 40 degrees,
  update: 25Hz
}
```
- **Safety Rationale:** Exceeding placard speed with flaps extended causes structural damage. Asymmetric flap = loss of lateral control.
- **INT8 Mapping:** `offset = 0, scale = 0.1569 deg/bit` → q=0 at 0°, q=255 at 40°. Discrete detent verification: 0, 5, 10, 15, 25, 40.
- **Failure Mode:** Torque tube shear; skew detection via dual position sensors per wing.

## 18. Landing Gear — Oleo Strut Extension
```
constraint oleo_extension {
  min: 0 %,
  max: 100 %,
  update: 50Hz
}
```
- **Safety Rationale:** Gear not fully extended/locked causes landing collapse. Air/ground sensing from strut compression drives system logic.
- **INT8 Mapping:** `offset = 0, scale = 0.3922 %/bit` → q=0 at 0%, q=255 at 100%.
- **Failure Mode:** Proximity sensor target separation; FLUX cross-check with WOW (Weight-on-Wheels) + gear door position.

## 19. Brake Temperature
```
constraint brake_temperature {
  min: 0 °C,
  max: 650 °C,
  update: 1Hz
}
```
- **Safety Rationale:** Rejected takeoff (RTO) energy absorption. Fuse plug melt releases tire pressure to prevent explosion.
- **INT8 Mapping:** `offset = 0, scale = 2.5490 °C/bit` → q=0 at 0°C, q=255 at 650°C.
- **Failure Mode:** Brake on with retracted gear; inhibit FLUX high-temp alert when WOW = false.

## 20. Navigation Position — Cross-Track Error
```
constraint cross_track_error {
  min: -4.0 NM,
  max: +4.0 NM,
  update: 5Hz
}
```
- **Safety Rationale:** RNP (Required Navigation Performance) containment. RNP 0.3 requires 95% probability within 0.3 NM; FLUX monitors 4σ boundary.
- **INT8 Mapping:** `offset = -4.0, scale = 0.0314 NM/bit` → q=0 at -4 NM, q=127 at 0, q=255 at +4 NM.
- **Failure Mode:** GNSS signal spoofing; FLUX must validate against IRS + ground-based navaid.

## 21. Autopilot — Vertical Speed Command
```
constraint autopilot_vs {
  min: -6000 ft/min,
  max: +4000 ft/min,
  update: 25Hz
}
```
- **Safety Rationale:** Excessive descent rate below 10,000 ft violates noise abatement and terrain clearance; excessive climb rate risks stall.
- **INT8 Mapping:** `offset = -6000, scale = 37.2549 ft/min/bit` → q=0 at -6000, q=161 at 0, q=255 at +4000.
- **Failure Mode:** MCP (Mode Control Panel) bug error or AFCS servo runaway; pilot authority must always override.

## 22. Windshear — Rate of Change of AOA
```
constraint windshear_aoa_rate {
  min: -5 deg/s,
  max: +8 deg/s,
  update: 1000Hz
}
```
- **Safety Rationale:** AOA rate is primary windshear predictor. Exceedance triggers predictive windshear warning (PWS) or reactive recovery.
- **INT8 Mapping:** `offset = -5, scale = 0.0510 deg/s/bit` → q=0 at -5°/s, q=98 at 0, q=255 at +8°/s.
- **Failure Mode:** AOA vane inertial overshoot during turbulence; apply 50 ms median filter before FLUX check.

## 23. Tire Pressure — Main Gear
```
constraint tire_pressure_main {
  min: 180 psi,
  max: 235 psi,
  update: 0.1Hz
}
```
- **Safety Rationale:** Under-inflation causes blowout on high-speed turnoff; over-inflation reduces contact patch and increases hydroplaning risk.
- **INT8 Mapping:** `offset = 180, scale = 0.2157 psi/bit` → q=0 at 180 psi, q=255 at 235 psi.
- **Failure Mode:** Valve stem leak; tire pressure monitoring system (TPMS) wireless link dropout.

## 24. Oxygen Pressure — Flight Crew
```
constraint oxy_pressure_crew {
  min: 1200 psi,
  max: 1850 psi,
  update: 0.1Hz
}
```
- **Safety Rationale:** Minimum pressure for emergency descent from FL 450. Crew must have 22 minutes at 10,000 ft equivalent.
- **INT8 Mapping:** `offset = 1200, scale = 2.5490 psi/bit` → q=0 at 1200 psi, q=255 at 1850 psi.
- **Failure Mode:** Regulator diaphragm rupture; FLUX flags pressure decay rate > 5 psi/day.

## 25. Slat Position
```
constraint slat_position {
  min: 0 degrees,
  max: 27 degrees,
  update: 25Hz
}
```
- **Safety Rationale:** Slats extend high-lift regime forward of flaps. Asymmetric slat = uncontrolled roll moment near stall.
- **INT8 Mapping:** `offset = 0, scale = 0.1059 deg/bit` → q=0 at 0°, q=255 at 27°.
- **Failure Mode:** Slat track dolly failure; dual track position monitoring per panel.

## 26. Rudder Trim
```
constraint rudder_trim {
  min: -20 degrees,
  max: +20 degrees,
  update: 10Hz
}
```
- **Safety Rationale:** Excessive trim with engine-out asymmetric thrust causes sideslip and structural load. Must be within AFCS authority for recovery.
- **INT8 Mapping:** `offset = -20, scale = 0.1569 deg/bit` → q=0 at -20°, q=127 at 0°, q=255 at +20°.
- **Failure Mode:** Trim actuator runaway; rate-limit check + pilot alert.

## 27. GPWS — Sink Rate
```
constraint gpws_sink_rate {
  min: 0 ft/min,
  max: 2500 ft/min,
  update: 100Hz
}
```
- **Safety Rationale:** "SINK RATE, PULL UP" warning threshold. Terrain closure rate must be within envelope for altitude.
- **INT8 Mapping:** `offset = 0, scale = 9.8039 ft/min/bit` → q=0 at 0, q=255 at 2500.
- **Failure Mode:** Barometric altitude rate noisy in turbulence; use inertial-derived vertical speed fused with radar altimeter.

## 28. TCAS — Intruder Range Rate
```
constraint tcas_range_rate {
  min: -5000 ft/min,
  max: +5000 ft/min,
  update: 1Hz
}
```
- **Safety Rationale:** Closing rate determines RA (Resolution Advisory) strength. High closing rate at short range triggers "CLIMB, CLIMB NOW".
- **INT8 Mapping:** `offset = -5000, scale = 39.2157 ft/min/bit` → q=0 at -5000, q=127 at 0, q=255 at +5000.
- **Failure Mode:** Transponder garble or multipath; FLUX must validate via Mode S lockout + multiple interrogations.

---

**INT8 Validation:** All quantized values within 0–255 range. ✓  
**Key Challenge:** Cross-sensor fusion (ADC + IRS + GPS) to reject single-sensor failures without nuisance trips.  
**DAL A Integrity Requirement:** 1e-9 catastrophic failure probability per flight hour.
