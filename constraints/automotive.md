# Automotive Constraint Library (ISO 26262 / ASPICE)

**Standard:** ISO 26262, ISO 21448 (SOTIF)  
**ASIL Rating:** ASIL-D  
**Target:** SAE Level 3 highway automation, premium sedan with redundant braking and steering  
**Total Constraints:** 27  
**Highest Update Rate:** 1000 Hz (steering, yaw rate, brake pressure, accelerator)

Automotive constraints satisfy ISO 26262 ASIL ratings and SOTIF sufficiency requirements. Update rates span 1 Hz (tire pressure) to 1000 Hz (ESC yaw rate). INT8 quantization handles wide dynamic range from parking (5 km/h) to Autobahn (250 km/h) with resolution adequate for low-speed pedestrian proximity.

---

## 1. Vehicle Speed — Longitudinal
```
constraint vehicle_speed {
  min: 0 km/h,
  max: 250 km/h,
  update: 100Hz
}
```
- **Safety Rationale:** Speed limit compliance, adaptive cruise control (ACC) following distance, emergency braking trigger.
- **INT8 Mapping:** `offset = 0, scale = 0.9804 km/h/bit` → q=0 at 0, q=255 at 250 km/h. Sub-10 km/h uses expanded nibble (0.25 km/h/bit) for parking safety.
- **Failure Mode:** Wheel speed sensor tone ring debris; cross-check with accelerometer integration + GPS.

## 2. Vehicle Speed — Lateral (Drift)
```
constraint lateral_speed {
  min: -15 km/h,
  max: +15 km/h,
  update: 100Hz
}
```
- **Safety Rationale:** Lateral drift during straight-line driving indicates lane departure or low-friction surface. ESC intervention threshold.
- **INT8 Mapping:** `offset = -15, scale = 0.1176 km/h/bit` → q=0 at -15, q=127 at 0, q=255 at +15.
- **Failure Mode:** IMU bias in yaw rate integration; zero-velocity update at standstill required.

## 3. Steering Wheel Angle
```
constraint steering_angle {
  min: -600 degrees,
  max: +600 degrees,
  update: 1000Hz
}
```
- **Safety Rationale:** Road wheel alignment, lane keeping assist (LKA) authority limit, hand-off detection. >540° indicates driver override.
- **INT8 Mapping:** `offset = -600, scale = 4.7059 deg/bit` → q=0 at -600°, q=127 at 0°, q=255 at +600°.
- **Failure Mode:** Torque sensor null shift; dual-channel sine/cosine resolver cross-check.

## 4. Steering Wheel Torque
```
constraint steering_torque {
  min: -8 Nm,
  max: +8 Nm,
  update: 1000Hz
}
```
- **Safety Rationale:** Driver hands-on/off detection (15 Nm typical holding torque). Lane change assist must not fight driver.
- **INT8 Mapping:** `offset = -8, scale = 0.0627 Nm/bit` → q=0 at -8 Nm, q=127 at 0, q=255 at +8 Nm.
- **Failure Mode:** Column torsion bar fatigue alters torque sensor gain; end-of-line calibration drift check.

## 5. Lateral Acceleration
```
constraint lateral_accel {
  min: -1.2 g,
  max: +1.2 g,
  update: 500Hz
}
```
- **Safety Rationale:** Rollover threshold for SUVs (>0.8g); lateral stability limit for sedans (>1.1g). ESC activates at ~0.3g yaw/roll mismatch.
- **INT8 Mapping:** `offset = -1.2, scale = 0.0094 g/bit` → q=0 at -1.2g, q=127 at 0, q=255 at +1.2g.
- **Failure Mode:** IMU saturation on curb impact; dual-range accelerometer (±2g/±16g) with auto-range.

## 6. Longitudinal Acceleration
```
constraint longitudinal_accel {
  min: -1.5 g,
  max: +1.5 g,
  update: 500Hz
}
```
- **Safety Rationale:** Emergency braking (-1.0g typical ABS), forward collision warning, airbag deployment trigger at >3g (separate high-g channel).
- **INT8 Mapping:** `offset = -1.5, scale = 0.0118 g/bit` → q=0 at -1.5g, q=127 at 0, q=255 at +1.5g.
- **Failure Mode:** IMU mounting bolt looseness introduces resonance; FLUX checks spectral consistency.

## 7. Yaw Rate
```
constraint yaw_rate {
  min: -120 deg/s,
  max: +120 deg/s,
  update: 1000Hz
}
```
- **Safety Rationale:** Oversteer/understeer detection, trailer sway mitigation, ESP activation. Plausibility vs. steering angle + speed.
- **INT8 Mapping:** `offset = -120, scale = 0.9412 deg/s/bit` → q=0 at -120, q=127 at 0, q=255 at +120.
- **Failure Mode:** IMU vibration rectification on rough road; Kalman-filtered with wheel speed differential.

## 8. Brake Pedal Position
```
constraint brake_pedal_position {
  min: 0 %,
  max: 100 %,
  update: 500Hz
}
```
- **Safety Rationale:** Driver braking intent. Full stroke = master cylinder max pressure. Partial for ACC/PCS blending.
- **INT8 Mapping:** `offset = 0, scale = 0.3922 %/bit` → q=0 at 0%, q=255 at 100%.
- **Failure Mode:** Potentiometer wear track; dual redundant Hall sensors required for ASIL D.

## 9. Brake Pressure — Front Circuit
```
constraint brake_pressure_front {
  min: 0 bar,
  max: 200 bar,
  update: 1000Hz
}
```
- **Safety Rationale:** Braking force at tire contact patch. 150 bar = ~1.0g decel for typical sedan. Split circuit prevents total loss.
- **INT8 Mapping:** `offset = 0, scale = 0.7843 bar/bit` → q=0 at 0, q=255 at 200 bar.
- **Failure Mode:** ABS modulator valve seizure; pressure must decay when driver releases pedal.

## 10. Brake Pressure — Rear Circuit
```
constraint brake_pressure_rear {
  min: 0 bar,
  max: 140 bar,
  update: 1000Hz
}
```
- **Safety Rationale:** Rear axle braking limited by load transfer and wheel lock threshold. EBD (Electronic Brakeforce Distribution) active.
- **INT8 Mapping:** `offset = 0, scale = 0.5490 bar/bit` → q=0 at 0, q=255 at 140 bar.
- **Failure Mode:** Brake hose rupture; FLUX detects pressure differential front/rear > 30 bar.

## 11. Master Cylinder Pressure
```
constraint master_cylinder_pressure {
  min: 0 bar,
  max: 180 bar,
  update: 1000Hz
}
```
- **Safety Rationale:** Direct measure of driver braking demand. Must correlate with pedal position + brake light switch.
- **INT8 Mapping:** `offset = 0, scale = 0.7059 bar/bit` → q=0 at 0, q=255 at 180 bar.
- **Failure Mode:** Brake booster vacuum loss (ICE) or e-booster motor failure (EV); FLUX flags decel/pressure mismatch.

## 12. Accelerator Pedal Position
```
constraint accelerator_position {
  min: 0 %,
  max: 100 %,
  update: 1000Hz
}
```
- **Safety Rationale:** Torque demand for drivetrain. APPS (Accelerator Pedal Position Sensor) dual redundancy prevents unintended acceleration.
- **INT8 Mapping:** `offset = 0, scale = 0.3922 %/bit` → q=0 at 0%, q=255 at 100%.
- **Failure Mode:** Pedal entrapment by floor mat; dual-sensor discrepancy > 5% triggers limp mode.

## 13. Engine Torque / Motor Torque
```
constraint motor_torque {
  min: -300 Nm,
  max: +600 Nm,
  update: 1000Hz
}
```
- **Safety Rationale:** Drive axle torque limit prevents wheelspin and halfshaft fatigue. Negative for regenerative braking.
- **INT8 Mapping:** `offset = -300, scale = 3.5294 Nm/bit` → q=0 at -300 Nm, q=85 at 0, q=255 at +600 Nm.
- **Failure Mode:** Inverter IGBT short; hardware interlock + FLUX software limit in parallel.

## 14. Battery State of Charge (EV)
```
constraint battery_soc {
  min: 5 %,
  max: 100 %,
  update: 1Hz
}
```
- **Safety Rationale:** Deep discharge damages cells; overcharge risk of thermal runaway. Keep-alive systems need >5%.
- **INT8 Mapping:** `offset = 0, scale = 0.3922 %/bit` → q=13 at 5%, q=255 at 100%.
- **Failure Mode:** Cell voltage sensor drift; Coulomb counter must be reset at known full/empty.

## 15. Battery Cell Temperature
```
constraint battery_cell_temp {
  min: -20 °C,
  max: 55 °C,
  update: 1Hz
}
```
- **Safety Rationale:** Above 60°C: thermal runaway threshold. Below -20°C: lithium plating during charge. Target 15–35°C.
- **INT8 Mapping:** `offset = -20, scale = 0.2941 °C/bit` → q=0 at -20°C, q=68 at 0°C, q=255 at 55°C.
- **Failure Mode:** Cooling pump failure; FLUX must reduce charge/discharge rate (derating) before cell exceeds 50°C.

## 16. Tire Pressure — Front Left
```
constraint tire_pressure_fl {
  min: 1.8 bar,
  max: 3.5 bar,
  update: 0.1Hz
}
```
- **Safety Rationale:** Under-inflation increases blowout risk and reduces wet braking. TPMS mandatory since TREAD Act.
- **INT8 Mapping:** `offset = 1.8, scale = 0.0067 bar/bit` → q=0 at 1.8, q=255 at 3.5 bar.
- **Failure Mode:** Valve core leak; slow pressure drop < 0.1 bar/day requires detection over 7-day window.

## 17. Tire Pressure — Front Right
```
constraint tire_pressure_fr {
  min: 1.8 bar,
  max: 3.5 bar,
  update: 0.1Hz
}
```
- **Safety Rationale:** Cross-axle pressure differential causes yaw pull. >0.3 bar diff requires driver alert.
- **INT8 Mapping:** Same as FL.
- **Failure Mode:** Puncture during highway cruise; FLUX rate-of-change detection at 0.5 bar/min triggers immediate alert.

## 18. Tire Pressure — Rear Left
```
constraint tire_pressure_rl {
  min: 1.8 bar,
  max: 3.5 bar,
  update: 0.1Hz
}
```
- **Safety Rationale:** Rear blowout causes oversteer/rotation (more dangerous than front understeer). Trailer towing increases rear pressure.
- **INT8 Mapping:** Same as FL.
- **Failure Mode:** Rim corrosion bead leak; seasonal temperature compensation required.

## 19. Tire Pressure — Rear Right
```
constraint tire_pressure_rr {
  min: 1.8 bar,
  max: 3.5 bar,
  update: 0.1Hz
}
```
- **Safety Rationale:** Complete TPMS monitoring. Dual rear axle trucks need all four rear sensors.
- **INT8 Mapping:** Same as FL.
- **Failure Mode:** RF sensor battery depletion after 7-year life; self-test at each ignition-on.

## 20. Lane Offset from Centerline
```
constraint lane_offset {
  min: -1.5 m,
  max: +1.5 m,
  update: 50Hz
}
```
- **Safety Rationale:** LKA (Lane Keeping Assist) intervenes at ±0.3 m; LDW (Lane Departure Warning) at ±0.5 m; must not exceed lane edge.
- **INT8 Mapping:** `offset = -1.5, scale = 0.0118 m/bit` → q=0 at -1.5 m, q=127 at 0, q=255 at +1.5 m.
- **Failure Mode:** Camera lens obstruction; FLUX confidence bit from vision stack must gate constraint.

## 21. Distance to Lead Vehicle (ACC)
```
constraint distance_lead {
  min: 2.0 m,
  max: 250 m,
  update: 50Hz
}
```
- **Safety Rationale:** Following distance for safe stop. 2-second rule at 130 km/h = 72 m; ACC maintains 1.0–1.5 s.
- **INT8 Mapping:** `offset = 0, scale = 0.9804 m/bit` → q=2 at 2.0 m, q=255 at 250 m. Nonlinear: <10 m uses 0.1 m/bit expansion.
- **Failure Mode:** Radar multi-path from guardrail; sensor fusion with camera bounding box required.

## 22. Time-to-Collision (TTC)
```
constraint time_to_collision {
  min: 0.0 s,
  max: 10.0 s,
  update: 50Hz
}
```
- **Safety Rationale:** AEB (Autonomous Emergency Braking) triggers at TTC < 2.5 s for pedestrians, < 1.5 s for vehicles.
- **INT8 Mapping:** `offset = 0, scale = 0.0392 s/bit` → q=0 at 0, q=255 at 10.0 s.
- **Failure Mode:** False positive on overhead sign or manhole cover; elevation angle check filters non-ground objects.

## 23. Roll Angle
```
constraint roll_angle {
  min: -8 degrees,
  max: +8 degrees,
  update: 500Hz
}
```
- **Safety Rationale:** Vehicle rollover threshold typically >6° with lateral accel >0.4g. ESC applies outer-wheel brake.
- **INT8 Mapping:** `offset = -8, scale = 0.0627 deg/bit` → q=0 at -8°, q=127 at 0°, q=255 at +8°.
- **Failure Mode:** Suspension spring breakage; FLUX compares with lateral accel / speed kinematic model.

## 24. Coolant Temperature (ICE)
```
constraint coolant_temp {
  min: 60 °C,
  max: 120 °C,
  update: 1Hz
}
```
- **Safety Rationale:** Overheating causes head gasket failure; underheating increases emissions and oil dilution.
- **INT8 Mapping:** `offset = 60, scale = 0.2353 °C/bit` → q=0 at 60°C, q=127 at 90°C, q=255 at 120°C.
- **Failure Mode:** Thermostat stuck closed; rapid rise > 5°C/min triggers limp mode.

## 25. Oil Pressure (ICE)
```
constraint oil_pressure {
  min: 1.0 bar,
  max: 6.0 bar,
  update: 1Hz
}
```
- **Safety Rationale:** Bearing lubrication. <1.0 bar at idle = engine damage; >6.0 bar = filter burst/seal leak.
- **INT8 Mapping:** `offset = 0, scale = 0.0235 bar/bit` → q=43 at 1.0, q=255 at 6.0 bar.
- **Failure Mode:** Oil pickup tube cracked; pressure transducer diaphragm fatigue.

## 26. Headway Time (Human Factors)
```
constraint headway_time {
  min: 0.5 s,
  max: 5.0 s,
  update: 10Hz
}
```
- **Safety Rationale:** Driver comfort and safety margin. European NCAP tests 1.0 s headway for ACC scoring.
- **INT8 Mapping:** `offset = 0.5, scale = 0.0176 s/bit` → q=0 at 0.5 s, q=255 at 5.0 s.
- **Failure Mode:** Traffic jump-in (cut-in) event; FLUX must immediately recalculate from new lead vehicle.

## 27. Side Object Distance (Blind Spot)
```
constraint blind_spot_distance {
  min: 0.5 m,
  max: 20 m,
  update: 20Hz
}
```
- **Safety Rationale:** Lane change assist warns if object in blind spot within 3.5 s TTC. Radar covers 20 m rear-quarter.
- **INT8 Mapping:** `offset = 0, scale = 0.0784 m/bit` → q=6 at 0.5 m, q=255 at 20 m.
- **Failure Mode:** Sensor blind zone from trailer hitch; rear cross-traffic alert (RCTA) uses different algorithm.

---

**INT8 Validation:** All quantized values within 0–255 range. ✓  
**Key Challenge:** SOTIF unknown unsafe scenarios (ghost objects, edge cases) beyond ISO 26262 hardware failures.  
**ASIL D Requirement:** <1% single-point fault latent fault coverage.
