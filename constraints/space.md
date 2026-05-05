## Agent 7: Space (ECSS / NASA-STD-8719.24)

**Agent Perspective:** Spacecraft GNC (Guidance, Navigation, and Control) engineer for LEO satellite bus and lunar lander. Constraints cover attitude, thermal, power, propulsion, and communication. Class B (high reliability, non-human-rated) and Class A (human-rated) mixed.

### Domain Overview

Space constraints must satisfy ECSS standards and NASA technical standards. Vacuum, radiation, thermal extremes (-150°C to +150°C), and communication delays drive unique constraints. Update rates: 1--10 Hz for thermal/power, 10--100 Hz for attitude, 0.1--1 Hz for orbit/comm. INT8 quantization must handle orbital mechanics (km-scale) and precision pointing (arcsecond-scale).

### Constraint Definitions

#### 1. Attitude -- Roll (LEO Pointing)
```
constraint attitude_roll {
  min: -2 degrees,
  max: +2 degrees,
  update: 100Hz
}
```
- **Safety Rationale:** Earth-pointing antenna / solar array alignment. >2°: communication loss, insufficient power generation.
- **INT8 Mapping:** `offset = -2, scale = 0.0157 deg/bit` → q=0 at -2°, q=127 at 0°, q=255 at +2°. High resolution: ~0.016°/bit.
- **Failure Mode:** Reaction wheel bearing degradation; torque noise couples into pointing error. EKF divergence.

#### 2. Attitude -- Pitch (LEO Pointing)
```
constraint attitude_pitch {
  min: -2 degrees,
  max: +2 degrees,
  update: 100Hz
}
```
- **Safety Rationale:** Same as roll. Cross-coupling between axes via Euler kinematics; small-angle approximation valid.
- **INT8 Mapping:** Same as roll.
- **Failure Mode:** CMG (Control Moment Gyro) singularity; FLUX must flag gimbal angle rate limit approaching singular configuration.

#### 3. Attitude -- Yaw (LEO Pointing)
```
constraint attitude_yaw {
  min: -5 degrees,
  max: +5 degrees,
  update: 100Hz
}
```
- **Safety Rationale:** Yaw less constrained for nadir-pointing (symmetry). >5°: solar array illumination angle degrades.
- **INT8 Mapping:** `offset = -5, scale = 0.0392 deg/bit` → q=0 at -5°, q=127 at 0°, q=255 at +5°.
- **Failure Mode:** Magnetorquer saturation in high-beta orbit; momentum dumping via RCS thrusters.

#### 4. Angular Rate -- X Axis
```
constraint angular_rate_x {
  min: -1 deg/s,
  max: +1 deg/s,
  update: 100Hz
}
```
- **Safety Rationale:** Rate damping after slew maneuver. >1°/s: flexible appendage excitation (solar array modal).
- **INT8 Mapping:** `offset = -1, scale = 0.0078 deg/s/bit` → q=0 at -1, q=127 at 0, q=255 at +1.
- **Failure Mode:** Rate gyro bias shift from radiation (Co-60, protons); auto-calibration at known inertial hold.

#### 5. Angular Rate -- Y Axis
```
constraint angular_rate_y {
  min: -1 deg/s,
  max: +1 deg/s,
  update: 100Hz
}
```
- **Safety Rationale:** Same as X. Cross-axis coupling through products of inertia.
- **INT8 Mapping:** Same as X.
- **Failure Mode:** IMU coning motion in elliptical orbit; vibration isolation + digital filtering.

#### 6. Angular Rate -- Z Axis
```
constraint angular_rate_z {
  min: -3 deg/s,
  max: +3 deg/s,
  update: 100Hz
}
```
- **Safety Rationale:** Z-axis usually aligned with orbit normal; higher rate tolerance for slew about orbit axis.
- **INT8 Mapping:** `offset = -3, scale = 0.0235 deg/s/bit` → q=0 at -3, q=127 at 0, q=255 at +3.
- **Failure Mode:** Reaction wheel speed saturation; desaturation via magnetic torque bars.

#### 7. Solar Array Wing Temperature
```
constraint solar_array_temp {
  min: -150 °C,
  max: +120 °C,
  update: 1Hz
}
```
- **Safety Rationale:** Cell efficiency: -0.5%/°C above 25°C. >120°C: adhesive degradation, cell cracking. >150°C: solder melt.
- **INT8 Mapping:** `offset = -150, scale = 1.0588 °C/bit` → q=0 at -150°C, q=142 at 0°C, q=255 at 120°C.
- **Failure Mode:** Eclipse exit thermal shock; passive radiator + active heater control.

#### 8. Battery Temperature
```
constraint battery_temp_space {
  min: -10 °C,
  max: +40 °C,
  update: 1Hz
}
```
- **Safety Rationale:** Li-ion: charge prohibited below 0°C (plating). Discharge to -10°C limited C-rate. >40°C: cycle life degradation.
- **INT8 Mapping:** `offset = -10, scale = 0.1961 °C/bit` → q=0 at -10°C, q=51 at 0°C, q=128 at 25°C, q=255 at 40°C.
- **Failure Mode:** Heater thermostat stuck-on during eclipse; FLUX must detect temp rise + disable heater.

#### 9. Battery State of Charge
```
constraint battery_soc_space {
  min: 20 %,
  max: 100 %,
  update: 0.1Hz
}
```
- **Safety Rationale:** Eclipse operation: battery must survive longest eclipse (72 min for LEO). 20% minimum for emergency safe mode.
- **INT8 Mapping:** `offset = 0, scale = 0.3922 %/bit` → q=51 at 20%, q=128 at 50%, q=255 at 100%.
- **Failure Mode:** Cell imbalance in series string; bypass diode + cell-level monitoring.

#### 10. Battery Depth of Discharge (Cycle)
```
constraint battery_dod {
  min: 0 %,
  max: 80 %,
  update: 0.1Hz
}
```
- **Safety Rationale:** DOD >80% reduces cycle life (typically 3000 cycles at 25% DOD vs. 500 at 80%). Mission lifetime constraint.
- **INT8 Mapping:** `offset = 0, scale = 0.3137 %/bit` → q=0 at 0%, q=128 at 40%, q=204 at 64%, q=255 at 80%.
- **Failure Mode:** Solar array degradation (UV darkening, micrometeoroids); FLUX must reduce load via power management.

#### 11. Bus Voltage -- Primary 28V
```
constraint bus_voltage_28v {
  min: 24 V,
  max: 36 V,
  update: 10Hz
}
```
- **Safety Rationale:** 28V ±4V per MIL-STD-704. <24V: payload brownout, memory corruption. >36V: converter overvoltage stress.
- **INT8 Mapping:** `offset = 24, scale = 0.0471 V/bit` → q=0 at 24V, q=85 at 28V, q=128 at 30V, q=255 at 36V.
- **Failure Mode:** Solar array string short; battery disconnect protects bus.

#### 12. Bus Voltage -- Secondary 5V
```
constraint bus_voltage_5v {
  min: 4.75 V,
  max: 5.25 V,
  update: 100Hz
}
```
- **Safety Rationale:** Digital logic, FPGA, processor core. <4.75V: timing violations, SEU susceptibility. >5.25: latch-up risk.
- **INT8 Mapping:** `offset = 4.75, scale = 0.0020 V/bit` → q=0 at 4.75V, q=127 at 5.00V, q=255 at 5.25V.
- **Failure Mode:** DC-DC converter oscillation; LC filter + FLUX ripple detection.

#### 13. Power Generation -- Solar Array
```
constraint solar_power {
  min: 0 W,
  max: 5000 W,
  update: 1Hz
}
```
- **Safety Rationale:** Must exceed load + battery charge. End-of-life (EOL) power: BOL × degradation factor (typically 0.75).
- **INT8 Mapping:** `offset = 0, scale = 19.6078 W/bit` → q=0 at 0, q=51 at 1000, q=128 at 2500, q=255 at 5000.
- **Failure Mode:** Solar array drive motor failure (array stuck); FLUX computes alternative attitude for power generation.

#### 14. Propellant Tank Pressure -- MON
```
constraint propellant_pressure_mon {
  min: 10 bar,
  max: 25 bar,
  update: 1Hz
}
```
- **Safety Rationale:** Mixed Oxides of Nitrogen (MON-3) oxidizer. Blowdown architecture: pressure drives propellant to engine. Tank structural: 35 bar.
- **INT8 Mapping:** `offset = 10, scale = 0.0588 bar/bit` → q=0 at 10, q=85 at 15, q=170 at 20, q=255 at 25.
- **Failure Mode:** Propellant isolation valve pyro failure; dual-seat valve + FLUX pressure decay check post-command.

#### 15. Propellant Tank Pressure -- MMH
```
constraint propellant_pressure_mmh {
  min: 10 bar,
  max: 25 bar,
  update: 1Hz
}
```
- **Safety Rationale:** Monomethylhydrazine fuel. Paired with MON. Pressure differential between oxidizer/fuel must be <2 bar for injector health.
- **INT8 Mapping:** Same as MON.
- **Failure Mode:** Diaphragm tank bellows rupture; FLUX monitors fuel/oxidizer pressure difference.

#### 16. Thruster Valve -- On-Time (Pulse)
```
constraint thruster_pulse {
  min: 4 ms,
  max: 5000 ms,
  update: 100Hz
}
```
- **Safety Rationale:** Minimum impulse bit (MIB): 4 ms. Max: steady-state burn. Valve cycle life: ~1M cycles.
- **INT8 Mapping:** `offset = 0, scale = 19.6078 ms/bit` → q=1 at 4, q=51 at 1000, q=128 at 2500, q=255 at 5000. Nonlinear: <100 ms uses 0.5 ms/bit.
- **Failure Mode:** Valve seat erosion increases MIB; FLUX compensates via longer pulse calibration.

#### 17. Communication Link Margin
```
constraint link_margin {
  min: 3 dB,
  max: 30 dB,
  update: 0.1Hz
}
```
- **Safety Rationale:** 3 dB = minimum acceptable (rain margin, pointing error). <0 dB: link drop, command loss.
- **INT8 Mapping:** `offset = 0, scale = 0.1176 dB/bit` → q=26 at 3, q=85 at 10, q=170 at 20, q=255 at 30.
- **Failure Mode:** High-gain antenna pointing error from attitude drift; switch to omni + low rate.

#### 18. Ground Track Error
```
constraint ground_track_error {
  min: 0 km,
  max: 50 km,
  update: 0.1Hz
}
```
- **Safety Rationale:** Orbital station-keeping: ±25 km box. Beyond: ground station handoff failure, collision risk.
- **INT8 Mapping:** `offset = 0, scale = 0.1961 km/bit` → q=0 at 0, q=51 at 10, q=128 at 25, q=255 at 50.
- **Failure Mode:** Drag model error during solar maximum; GPS navigation solution + onboard orbit propagator.

#### 19. Reaction Wheel Speed
```
constraint rw_speed {
  min: -6000 rpm,
  max: +6000 rpm,
  update: 100Hz
}
```
- **Safety Rationale:** Momentum storage. Saturation at 6000 rpm = no control authority. Must desaturate before mission-critical maneuver.
- **INT8 Mapping:** `offset = -6000, scale = 47.0588 rpm/bit` → q=0 at -6000, q=127 at 0, q=255 at +6000.
- **Failure Mode:** Bearing lubricant depletion; acoustic emission sensor + FLUX vibration trend.

#### 20. Star Tracker -- Identification Confidence
```
constraint star_id_confidence {
  min: 80 %,
  max: 100 %,
  update: 1Hz
}
```
- **Safety Rationale:** Lost-in-space mode: must identify >3 stars with >80% confidence. <80%: attitude unknown, safe mode.
- **INT8 Mapping:** `offset = 80, scale = 0.0784 %/bit` → q=0 at 80%, q=128 at 90%, q=255 at 100%.
- **Failure Mode:** Earth/Moon in FOV causes false star detection; rejection algorithm + secondary star tracker.

#### 21. Radiation Dose -- Total Ionizing
```
constraint tid_dose {
  min: 0 krad,
  max: 100 krad,
  update: 0.01Hz
}
```
- **Safety Rationale:** Component qualification: 100 krad typical for LEO 5-year mission. >50 krad: performance degradation.
- **INT8 Mapping:** `offset = 0, scale = 0.3922 krad/bit` → q=0 at 0, q=128 at 50, q=255 at 100.
- **Failure Mode:** Solar particle event (SPE); radiation-hardened components + shielding design margin.

#### 22. Orbit Altitude (Perigee)
```
constraint altitude_perigee {
  min: 400 km,
  max: 2000 km,
  update: 0.1Hz
}
```
- **Safety Rationale:** <200 km: rapid decay. 400 km: ISS orbit, atmospheric drag manageable. >2000 km: Van Allen belt radiation.
- **INT8 Mapping:** `offset = 400, scale = 6.2745 km/bit` → q=0 at 400, q=64 at 800, q=128 at 1200, q=255 at 2000.
- **Failure Mode:** Orbit insertion underburn; propellant reserve for deorbit or orbit raise.

#### 23. Pointing Knowledge Error
```
constraint pointing_knowledge {
  min: 0 arcsec,
  max: 60 arcsec,
  update: 10Hz
}
```
- **Safety Rationale:** High-resolution imaging: 1 arcsec = 5 m ground sample distance at 1000 km. >60 arcsec: image blur unusable.
- **INT8 Mapping:** `offset = 0, scale = 0.2353 arcsec/bit` → q=0 at 0, q=4 at 1, q=85 at 20, q=255 at 60.
- **Failure Mode:** Thermal distortion of optical bench; active focus adjustment + post-processing.

### Agent 7 Summary
- **Total Constraints:** 23
- **Highest Update Rate:** 100 Hz (attitude, rates, bus, thruster)
- **Key Challenge:** Radiation-induced sensor degradation over mission lifetime; FLUX must accommodate graceful degradation
- **ECSS Class A/B:** Class A (human) requires 0.999 reliability at 95% confidence; Class B (robotic) 0.99

---