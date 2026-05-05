## Agent 5: Maritime (IEC 62923 / IMO MSC)

**Agent Perspective:** Marine automation and DP (Dynamic Positioning) systems engineer for offshore supply vessels and cruise ships. Constraints cover navigation, propulsion, cargo, and hull integrity.

### Domain Overview

Maritime constraints must satisfy IEC 62923 (bridge equipment), SOLAS (Safety of Life at Sea), and IMO performance standards. DP systems operate at 1--10 Hz update; navigation at 1 Hz; engine control at 10--50 Hz. INT8 quantization must handle ocean-scale distances (NM) and precision mooring (cm).

### Constraint Definitions

#### 1. Ship's Heading -- Gyro
```
constraint heading_gyro {
  min: 0 degrees,
  max: 359 degrees,
  update: 10Hz
}
```
- **Safety Rationale:** Navigation, collision avoidance (COLREGS), traffic separation scheme compliance. ±0.5° accuracy for narrow channels.
- **INT8 Mapping:** `offset = 0, scale = 1.4118 deg/bit` → q=0 at 0°, q=255 wraps to 359°. Circular wrap logic.
- **Failure Mode:** Gyrocompass settling error after power-on; magnetic compass backup + GPS course-made-good cross-check.

#### 2. Ship's Speed -- Through Water (STW)
```
constraint speed_through_water {
  min: 0 knots,
  max: 35 knots,
  update: 1Hz
}
```
- **Safety Rationale:** Log speed for collision risk assessment. DP station-keeping uses STW for current compensation.
- **INT8 Mapping:** `offset = 0, scale = 0.1373 kn/bit` → q=0 at 0, q=73 at 10, q=182 at 25, q=255 at 35.
- **Failure Mode:** Paddle wheel fouled by fishing net; electromagnetic log or Doppler velocity log (DVL) backup.

#### 3. Ship's Speed -- Over Ground (SOG)
```
constraint speed_over_ground {
  min: 0 knots,
  max: 35 knots,
  update: 1Hz
}
```
- **Safety Rationale:** ETA, tide/current vector (SOG-STW). Minimum SOG for steerage way: typically 3--5 kn.
- **INT8 Mapping:** Same as STW.
- **Failure Mode:** GNSS multipath in fjords; DGNSS or RTK required for precision.

#### 4. Depth Below Keel -- Echo Sounder
```
constraint depth_below_keel {
  min: 0 m,
  max: 120 m,
  update: 5Hz
}
```
- **Safety Rationale:** Under-keel clearance (UKC). Shallow water: 10% draft margin. Deep water: no constraint. Dual-frequency for soft/hard bottom.
- **INT8 Mapping:** `offset = 0, scale = 0.4706 m/bit` → q=0 at 0, q=43 at 20, q=128 at 60, q=255 at 120. Nonlinear: <20 m uses 0.1 m/bit.
- **Failure Mode:** Sound velocity profile error in stratified water; SVP sensor or database lookup required.

#### 5. Roll Angle
```
constraint ship_roll {
  min: -30 degrees,
  max: +30 degrees,
  update: 10Hz
}
```
- **Safety Rationale:** Cargo lashing limits, passenger comfort, green water on deck. Container ship: parametric roll in head seas.
- **INT8 Mapping:** `offset = -30, scale = 0.2353 deg/bit` → q=0 at -30°, q=127 at 0°, q=255 at +30°.
- **Failure Mode:** Damaged stability (flooding) shifts GM; FLUX must recompute righting arm from loading computer.

#### 6. Pitch Angle
```
constraint ship_pitch {
  min: -8 degrees,
  max: +8 degrees,
  update: 10Hz
}
```
- **Safety Rationale:** Bow immersion (slamming) and propeller emergence. Trim by stern preferred for speed; by bow for fuel efficiency.
- **INT8 Mapping:** `offset = -8, scale = 0.0627 deg/bit` → q=0 at -8°, q=127 at 0°, q=255 at +8°.
- **Failure Mode:** Draft sensor offset from ballast transfer; cross-check with load cells and sounding tubes.

#### 7. Heave (Vertical Motion)
```
constraint heave {
  min: -6 m,
  max: +6 m,
  update: 10Hz
}
```
- **Safety Rationale:** Crane operations, helicopter landing, ROV launch. >3 m heave: operations suspended.
- **INT8 Mapping:** `offset = -6, scale = 0.0471 m/bit` → q=0 at -6, q=127 at 0, q=255 at +6.
- **Failure Mode:** MRU (Motion Reference Unit) gyro drift; GPS-RTK height rate cross-check.

#### 8. Cargo Tank Level -- Oil
```
constraint cargo_tank_level_oil {
  min: 0 %,
  max: 98 %,
  update: 1Hz
}
```
- **Safety Rationale:** 98% fill limit for thermal expansion (ullage). >98%: overflow, environmental release. Loading computer integration.
- **INT8 Mapping:** `offset = 0, scale = 0.3843 %/bit` → q=0 at 0%, q=128 at 49%, q=255 at 98%.
- **Failure Mode:** Radar level gauge echo loss from foam; temperature-compensated volume vs. sounding cross-check.

#### 9. Cargo Tank Pressure -- Inert Gas
```
constraint cargo_tank_pressure_ig {
  min: 50 mmWG,
  max: 2500 mmWG,
  update: 1Hz
}
```
- **Safety Rationale:** Inert gas (IG) prevents explosive atmosphere. 50 mmWG minimum: air ingress. 2500 max: tank structural limit.
- **INT8 Mapping:** `offset = 0, scale = 9.8039 mmWG/bit` → q=5 at 50, q=128 at 1250, q=255 at 2500.
- **Failure Mode:** IG blower failure; FLUX triggers nitrogen backup + cargo discharge halt.

#### 10. Main Engine RPM
```
constraint main_engine_rpm {
  min: 0 rpm,
  max: 120 rpm,
  update: 10Hz
}
```
- **Safety Rationale:** Slow-speed diesel: 120 rpm max. Overspeed: crankshaft / bearing failure. Dead slow ahead: 15 rpm.
- **INT8 Mapping:** `offset = 0, scale = 0.4706 rpm/bit` → q=0 at 0, q=32 at 15, q=128 at 60, q=255 at 120.
- **Failure Mode:** Governor failure; overspeed trip bolt + independent FLUX limit.

#### 11. Main Engine -- Cylinder Exhaust Temperature
```
constraint me_exhaust_temp {
  min: 200 °C,
  max: 520 °C,
  update: 1Hz
}
```
- **Safety Rationale:** Individual cylinder monitoring for combustion balance. >520°C: scavenge fire risk, turbocharger damage.
- **INT8 Mapping:** `offset = 200, scale = 1.2549 °C/bit` → q=0 at 200°C, q=80 at 300, q=175 at 420, q=255 at 520.
- **Failure Mode:** Fuel injector needle stuck open; FLUX detects single-cylinder deviation >40°C from mean.

#### 12. Propeller Shaft Torque
```
constraint propeller_torque {
  min: 0 kNm,
  max: 8000 kNm,
  update: 10Hz
}
```
- **Safety Rationale:** Shaft limit. Ice class: torque spikes from propeller-ice interaction. >100%: overload alarm.
- **INT8 Mapping:** `offset = 0, scale = 31.3725 kNm/bit` → q=0 at 0, q=80 at 2500, q=160 at 5000, q=255 at 8000.
- **Failure Mode:** Shaft fatigue crack; torsional vibration monitor (TVM) detects natural frequency shift.

#### 13. Propeller Pitch (CPP)
```
constraint propeller_pitch {
  min: -100 %,
  max: +100 %,
  update: 10Hz
}
```
- **Safety Rationale:** Controllable Pitch Propeller: +100% = full ahead, -100% = full astern, 0 = feather. Pitch-rpm envelope prevents cavitation.
- **INT8 Mapping:** `offset = -100, scale = 0.7843 %/bit` → q=0 at -100%, q=127 at 0%, q=255 at +100%.
- **Failure Mode:** Hydraulic pitch servo failure; mechanical locking at last pitch + backup pump.

#### 14. Rudder Angle
```
constraint rudder_angle {
  min: -35 degrees,
  max: +35 degrees,
  update: 10Hz
}
```
- **Safety Rationale:** COLREGS maneuverability. >35°: structural stop, but emergency may require. Rate of turn vs. ordered angle check.
- **INT8 Mapping:** `offset = -35, scale = 0.2745 deg/bit` → q=0 at -35°, q=127 at 0°, q=255 at +35°.
- **Failure Mode:** Steering gear hydraulic leak; dual-ram independent system + FLUX differential pressure check.

#### 15. DP Position -- North
```
constraint dp_position_north {
  min: -10 m,
  max: +10 m,
  update: 1Hz
}
```
- **Safety Rationale:** Dynamic Positioning Class 3: redundancy in all active components. 1 m accuracy for drilling. 10 m for supply vessel offloading.
- **INT8 Mapping:** `offset = -10, scale = 0.0784 m/bit` → q=0 at -10, q=127 at 0, q=255 at +10.
- **Failure Mode:** GNSS denial (jamming); acoustic positioning + inertial + taut-wire backup.

#### 16. DP Position -- East
```
constraint dp_position_east {
  min: -10 m,
  max: +10 m,
  update: 1Hz
}
```
- **Safety Rationale:** Same as North. Combined position error = sqrt(N²+E²). Must be within operational watch circle.
- **INT8 Mapping:** Same as North.
- **Failure Mode:** Acoustic beacon shift (subsea landslide); multiple seabed transponder network.

#### 17. DP Thruster -- Azimuth Angle
```
constraint thruster_azimuth {
  min: 0 degrees,
  max: 359 degrees,
  update: 10Hz
}
```
- **Safety Rationale:** Thruster allocation for station-keeping. Azimuth must match computed demand; misalignment wastes power / causes drift.
- **INT8 Mapping:** `offset = 0, scale = 1.4118 deg/bit` → q=0 at 0°, q=180 at 255° (wrap), circular logic.
- **Failure Mode:** Thruster gear tooth crack; vibration + position encoder cross-check.

#### 18. DP Thruster -- RPM
```
constraint thruster_rpm {
  min: 0 rpm,
  max: 900 rpm,
  update: 10Hz
}
```
- **Safety Rationale:** Electric or diesel-driven thrusters. Power load on generators; blackout prevention via load shedding.
- **INT8 Mapping:** `offset = 0, scale = 3.5294 rpm/bit` → q=0 at 0, q=71 at 250, q=142 at 500, q=255 at 900.
- **Failure Mode:** Thruster motor bearing seizure; current signature + vibration FLUX checks.

#### 19. Ballast Tank Level
```
constraint ballast_level {
  min: 0 %,
  max: 100 %,
  update: 1Hz
}
```
- **Safety Rationale:** Draft, trim, heel, GM stability. Loading computer calculates required ballast. Free surface effect reduces GM.
- **INT8 Mapping:** `offset = 0, scale = 0.3922 %/bit` → q=0 at 0%, q=128 at 50%, q=255 at 100%.
- **Failure Mode:** Level sensor in tank with entrained air; multiple sensors + sounding pipe backup.

#### 20. Bilge Level -- Engine Room
```
constraint bilge_level {
  min: 0 mm,
  max: 500 mm,
  update: 1Hz
}
```
- **Safety Rationale:** Flooding detection. >200 mm: bilge pump auto-start. >400 mm: high-level alarm + investigate.
- **INT8 Mapping:** `offset = 0, scale = 1.9608 mm/bit` → q=0 at 0, q=102 at 200, q=204 at 400, q=255 at 500.
- **Failure Mode:** Oil/water interface layer; capacitance probe must distinguish water from lube oil.

#### 21. Generator Load -- Total
```
constraint generator_load {
  min: 0 %,
  max: 100 %,
  update: 1Hz
}
```
- **Safety Rationale:** Blackout prevention. >85%: add generator. >100%: load shedding per priority table. DP vessels: N+1 redundancy.
- **INT8 Mapping:** `offset = 0, scale = 0.3922 %/bit` → q=0 at 0%, q=128 at 50%, q=217 at 85%, q=255 at 100%.
- **Failure Mode:** Paralleling sync failure; reverse power trip + FLUX checks active/reactive power balance.

#### 22. Hull Stress -- Still Water Bending Moment
```
constraint hull_bending {
  min: -100 %,
  max: +100 %,
  update: 0.1Hz
}
```
- **Safety Rationale:** Sagging/hogging moment vs. allowable. 100% = design limit. Container stacking weight + ballast + fuel.
- **INT8 Mapping:** `offset = -100, scale = 0.7843 %/bit` → q=0 at -100%, q=127 at 0%, q=255 at +100%.
- **Failure Mode:** Hull girder crack from fatigue; strain gauge monitoring + crack detection ultrasonic.

#### 23. Fire Detection -- Optical Density
```
constraint smoke_density {
  min: 0 %/m,
  max: 20 %/m,
  update: 1Hz
}
```
- **Safety Rationale:** IMO A.824: obscuration threshold 12.5%/m for detector. Engine room: CO2 flooding at confirmed fire.
- **INT8 Mapping:** `offset = 0, scale = 0.0784 %/m/bit` → q=0 at 0, q=159 at 12.5, q=255 at 20.
- **Failure Mode:** Dust contamination; auto-compensation drift + manual sensitivity test required.

#### 24. Anchor Chain Tension
```
constraint anchor_tension {
  min: 0 kN,
  max: 5000 kN,
  update: 1Hz
}
```
- **Safety Rationale:** Anchor drag in storm. >80% of holding power: alarm. >100%: anchor dragging, possible grounding.
- **INT8 Mapping:** `offset = 0, scale = 19.6078 kN/bit` → q=0 at 0, q=102 at 2000, q=204 at 4000, q=255 at 5000.
- **Failure Mode:** Chain wear link diameter reduction; periodic NDT + FLUX trend of tension vs. scope.

#### 25. LNG Bunker Tank Temperature
```
constraint lng_tank_temp {
  min: -165 °C,
  max: -150 °C,
  update: 0.1Hz
}
```
- **Safety Rationale:** LNG at -162°C, 1 bar. > -150°C: BOG (boil-off gas) exceeds reliquefaction capacity. Tank structural limit: warm LNG causes thermal stress.
- **INT8 Mapping:** `offset = -165, scale = 0.0588 °C/bit` → q=0 at -165°C, q=128 at -157.5°C, q=255 at -150°C.
- **Failure Mode:** Tank insulation vacuum loss; FLUX must trigger pressure relief + BOG compressor max speed.

### Agent 5 Summary
- **Total Constraints:** 25
- **Highest Update Rate:** 10 Hz (multiple)
- **Key Challenge:** DP system sensor fusion (GNSS + acoustics + inertial) in harsh offshore environment with GNSS jamming
- **IMO Compliance:** COLREGS, SOLAS, MARPOL environmental constraints integrated

---