## Agent 6: Railway (EN 50128 / EN 50129)

**Agent Perspective:** Railway signaling and control systems engineer for ETCS/ERTMS and CBTC metro systems. SIL 4 rated. Target: high-speed passenger rail (300 km/h) and urban metro.

### Domain Overview

Railway constraints must satisfy CENELEC standards EN 50128 (software), EN 50129 (hardware), and EN 50159 (communication). Train protection update rates: 50--500 Hz for ATP; 1 Hz for interlocking. Braking curves are kinematic: position + speed + gradient + adhesion. INT8 must encode braking distance with meter precision at 300 km/h.

### Constraint Definitions

#### 1. Train Speed -- Maximum Permitted
```
constraint train_speed_max {
  min: 0 km/h,
  max: 320 km/h,
  update: 100Hz
}
```
- **Safety Rationale:** ETCS braking curve: emergency brake intervention if speed exceeds permitted + margin. TGV/ICE/CRH: 300--320 km/h.
- **INT8 Mapping:** `offset = 0, scale = 1.2549 km/h/bit` → q=0 at 0, q=80 at 100, q=160 at 200, q=255 at 320.
- **Failure Mode:** Wheel slide during braking causes speed sensor under-read; radar + accelerometer cross-check.

#### 2. Train Speed -- Current
```
constraint train_speed_current {
  min: 0 km/h,
  max: 320 km/h,
  update: 100Hz
}
```
- **Safety Rationale:** Continuous speed monitoring for ATP. Braking model: current speed must allow stop before danger point.
- **INT8 Mapping:** Same as max speed.
- **Failure Mode:** Doppler radar false low due to ground clutter; odometer + radar sensor fusion.

#### 3. Distance to Danger Point (Moving Block)
```
constraint distance_danger {
  min: 0 m,
  max: 5000 m,
  update: 50Hz
}
```
- **Safety Rationale:** Moving block / CBTC: train must maintain safe separation from preceding train. Braking distance + margin.
- **INT8 Mapping:** `offset = 0, scale = 19.6078 m/bit` → q=0 at 0, q=13 at 250, q=51 at 1000, q=255 at 5000.
- **Failure Mode:** Communication loss to wayside; train must apply service brake + transition to fixed block.

#### 4. Braking Curve Deceleration
```
constraint braking_decel {
  min: 0 m/s²,
  max: 2.5 m/s²,
  update: 50Hz
}
```
- **Safety Rationale:** Service brake: 1.0 m/s². Emergency: 2.5 m/s². Low adhesion (leaves, ice): 0.3 m/s² achievable. Model must adapt.
- **INT8 Mapping:** `offset = 0, scale = 0.0098 m/s²/bit` → q=0 at 0, q=102 at 1.0, q=255 at 2.5.
- **Failure Mode:** Brake pad coefficient degradation; wheel-mounted temperature + WSP (Wheel Slide Protection) monitors.

#### 5. Braking Distance to Stop
```
constraint braking_distance {
  min: 0 m,
  max: 4000 m,
  update: 50Hz
}
```
- **Safety Rationale:** From 300 km/h: ~3800 m braking distance. ATP must compute real-time vs. available distance.
- **INT8 Mapping:** `offset = 0, scale = 15.6863 m/bit` → q=0 at 0, q=16 at 250, q=64 at 1000, q=255 at 4000.
- **Failure Mode:** Gradient error from track database; inclinometer + GNSS/INS real-time update.

#### 6. Position Uncertainty (Train Odometry)
```
constraint position_uncertainty {
  min: 0 m,
  max: 50 m,
  update: 10Hz
}
```
- **Safety Rationale:** CBTC: train reports position + uncertainty. Wayside allocates block based on worst-case position. >20 m: degraded mode.
- **INT8 Mapping:** `offset = 0, scale = 0.1961 m/bit` → q=0 at 0, q=51 at 10, q=102 at 20, q=255 at 50.
- **Failure Mode:** Wheel diameter calibration drift; balise (transponder) passage resets position + uncertainty.

#### 7. Track Gradient
```
constraint track_gradient {
  min: -40 ‰,
  max: +40 ‰,
  update: 1Hz
}
```
- **Safety Rationale:** 40‰ = 4% grade. Downhill extends braking distance; uphill shortens. ETCS profile from track database.
- **INT8 Mapping:** `offset = -40, scale = 0.3137 ‰/bit` → q=0 at -40‰, q=127 at 0‰, q=255 at +40‰.
- **Failure Mode:** Database error at construction modification; balise-linked gradient update required.

#### 8. Curve Cant Deficiency
```
constraint cant_deficiency {
  min: 0 mm,
  max: 150 mm,
  update: 1Hz
}
```
- **Safety Rationale:** Uncompensated lateral acceleration in curves. >150 mm: risk of derailment, passenger discomfort (1.5 m/s² lateral).
- **INT8 Mapping:** `offset = 0, scale = 0.5882 mm/bit` → q=0 at 0, q=85 at 50, q=170 at 100, q=255 at 150.
- **Failure Mode:** Cant measurement error from track geometry car; real-time accelerometer validation.

#### 9. Signal Aspect -- Approach
```
constraint signal_aspect {
  min: 0 (STOP),
  max: 4 (PROCEED),
  update: 5Hz
}
```
- **Safety Rationale:** 0=STOP, 1=CAUTION, 2=CLEAR, 3=PROCEED, 4=CALL-ON. ATP must enforce braking to respect aspect.
- **INT8 Mapping:** Discrete values: q=0, 64, 128, 192, 255. FLUX checks validity: only these 5 codes permitted.
- **Failure Mode:** Lamp filament failure; LED signals have partial degradation detection. Track circuit failure: most restrictive aspect.

#### 10. Door Status -- All Closed & Locked
```
constraint door_closed_locked {
  min: 0 (OPEN),
  max: 1 (CLOSED),
  update: 25Hz
}
```
- **Safety Rationale:** Train must not move with doors open. Individual door lock microswitches in series + door loop circuit.
- **INT8 Mapping:** Binary: q<128 = open/unlocked, q>=128 = closed/locked. Hysteresis: close >180, open <80.
- **Failure Mode:** Door edge seal ice prevents full close; heater activation + FLUX re-check before movement enable.

#### 11. Platform Screen Door Alignment
```
constraint psd_alignment {
  min: 0 mm,
  max: 200 mm,
  update: 10Hz
}
```
- **Safety Rationale:** PSD must align with train door ±200 mm. >500 mm: PSD remains closed, train doors blocked.
- **INT8 Mapping:** `offset = 0, scale = 0.7843 mm/bit` → q=0 at 0, q=64 at 50, q=128 at 100, q=255 at 200.
- **Failure Mode:** Train stop position overshoot; reverse within 1 m or skip stop protocol.

#### 12. Traction Motor Current
```
constraint traction_current {
  min: 0 A,
  max: 2000 A,
  update: 100Hz
}
```
- **Safety Rationale:** Overcurrent: motor winding insulation damage, fire. Current limit curve vs. speed (constant power region).
- **INT8 Mapping:** `offset = 0, scale = 7.8431 A/bit` → q=0 at 0, q=64 at 500, q=128 at 1000, q=255 at 2000.
- **Failure Mode:** Traction inverter IGBT shoot-through; fast fuse + FLUX current rate-limit check.

#### 13. Traction Motor Temperature
```
constraint traction_motor_temp {
  min: 20 °C,
  max: 220 °C,
  update: 1Hz
}
```
- **Safety Rationale:** Insulation class H: 180°C limit. >200°C: immediate power reduction. Bearing temperature separate.
- **INT8 Mapping:** `offset = 20, scale = 0.7843 °C/bit` → q=0 at 20°C, q=128 at 120°C, q=204 at 180°C, q=255 at 220°C.
- **Failure Mode:** Cooling blower failure in tunnel; FLUX derates motor torque to thermal model limit.

#### 14. Pantograph -- Contact Force
```
constraint pantograph_force {
  min: 50 N,
  max: 120 N,
  update: 100Hz
}
```
- **Safety Rationale:** <50 N: contact loss, arcing, wire damage. >120 N: wire uplift, fatigue, detachment. High speed: aerodynamic effects.
- **INT8 Mapping:** `offset = 50, scale = 0.2745 N/bit` → q=0 at 50, q=64 at 68, q=128 at 85, q=255 at 120.
- **Failure Mode:** Pantograph head carbon strip wear reduces compliance; FLUX force trend predicts end-of-life.

#### 15. Overhead Line Voltage (Catenary)
```
constraint catenary_voltage {
  min: 19 kV,
  max: 31 kV,
  update: 100Hz
}
```
- **Safety Rationale:** 25 kV AC nominal. 17.5 kV min for equipment. >29 kV: regenerative braking overvoltage; >31: traction lockout.
- **INT8 Mapping:** `offset = 19000, scale = 47.0588 V/bit` → q=0 at 19 kV, q=128 at 25 kV, q=255 at 31 kV.
- **Failure Mode:** Substation fault; train must coast + pantograph lower if >32 kV.

#### 16. Axle Bearing Temperature
```
constraint axle_bearing_temp {
  min: 20 °C,
  max: 150 °C,
  update: 1Hz
}
```
- **Safety Rationale:** Hot bearing / journal failure: derailment risk. >90°C: alarm. >120°C: stop train.
- **INT8 Mapping:** `offset = 20, scale = 0.5098 °C/bit` → q=0 at 20°C, q=64 at 53°C, q=137 at 90°C, q=255 at 150°C.
- **Failure Mode:** Grease degradation; trend analysis (delta vs. ambient) more reliable than absolute.

#### 17. Wheel Diameter (Calibrated)
```
constraint wheel_diameter {
  min: 800 mm,
  max: 920 mm,
  update: 0.01Hz
}
```
- **Safety Rationale:** New wheel: 920 mm. Wear limit: 820 mm. Diameter affects speed/odometry accuracy; FLAX uses wheelset average.
- **INT8 Mapping:** `offset = 800, scale = 0.4706 mm/bit` → q=0 at 800, q=128 at 860, q=255 at 920.
- **Failure Mode:** Lathe turning without database update; FLUX must auto-calibrate via balise passage timing.

#### 18. Brake Cylinder Pressure -- Car 1
```
constraint brake_cyl_pressure {
  min: 0 bar,
  max: 4.5 bar,
  update: 100Hz
}
```
- **Safety Rationale:** Air brake or EP brake. 3.5 bar = full service brake. 4.5 bar = emergency. Graduated release vs. direct release.
- **INT8 Mapping:** `offset = 0, scale = 0.0176 bar/bit` → q=0 at 0, q=128 at 2.25, q=199 at 3.5, q=255 at 4.5.
- **Failure Mode:** Brake pipe leak; FLUX monitors pressure decay rate during brake application.

#### 19. Interlocking -- Route Set Consistency
```
constraint route_consistency {
  min: 0 (INVALID),
  max: 1 (VALID),
  update: 5Hz
}
```
- **Safety Rationale:** No conflicting routes. Points, signals, track circuits must form consistent state per interlocking table.
- **INT8 Mapping:** Binary encoded: q=0 = invalid/conflict, q=255 = valid. No intermediate values permitted.
- **Failure Mode:** Relay contact weld; solid-state interlocking (SSI) with dual-comparator architecture.

#### 20. ATP Brake Demand
```
constraint atp_brake_demand {
  min: 0 %,
  max: 100 %,
  update: 50Hz
}
```
- **Safety Rationale:** ATP service brake demand from braking curve. 100% = emergency brake. Modulated service: 10--90%.
- **INT8 Mapping:** `offset = 0, scale = 0.3922 %/bit` → q=0 at 0%, q=128 at 50%, q=255 at 100%.
- **Failure Mode:** Brake controller receives demand but pneumatic valve fails; feedback loop required.

#### 21. Axle Load -- Bogie 1
```
constraint axle_load_bogie1 {
  min: 0 t,
  max: 25 t,
  update: 1Hz
}
```
- **Safety Rationale:** Prevent overloading, uneven distribution. Freight: 22.5 t/axle standard. Passenger: 17 t/axle.
- **INT8 Mapping:** `offset = 0, scale = 0.0980 t/bit` → q=0 at 0, q=102 at 10, q=230 at 22.5, q=255 at 25.
- **Failure Mode:** Air spring pressure sensor drift; wheel load measurement from strain gauges at trackside.

#### 22. GSM-R / LTE-R Radio Signal Strength
```
constraint radio_rssi {
  min: -100 dBm,
  max: -40 dBm,
  update: 1Hz
}
```
- **Safety Rationale:** ETCS Level 2/3 requires continuous radio. < -95 dBm: communication loss → transition to Level 1/0.
- **INT8 Mapping:** `offset = -100, scale = 0.2353 dBm/bit` → q=0 at -100, q=21 at -95, q=128 at -70, q=255 at -40.
- **Failure Mode:** Tunnel shadowing; leaky feeder cable + trackside radio heads.

#### 23. Cabin Air Pressure (High-Speed Tunnel)
```
constraint cabin_pressure_tunnel {
  min: 950 hPa,
  max: 1050 hPa,
  update: 10Hz
}
```
- **Safety Rationale:** Tunnel entry/exit pressure transients: 2--4 kPa/s. Passenger comfort: eardrum pressure <1 kPa/s rate.
- **INT8 Mapping:** `offset = 950, scale = 0.3922 hPa/bit` → q=0 at 950, q=128 at 1000, q=255 at 1050.
- **Failure Mode:** Pressure seal failure; FLUX controls HVAC damper to modulate rate.

#### 24. Tilt Angle (Active Tilt Train)
```
constraint active_tilt {
  min: 0 degrees,
  max: 8 degrees,
  update: 50Hz
}
```
- **Safety Rationale:** Pendolino/ICE-T: active tilt compensates curve lateral accel. >8°: risk of striking platform / infrastructure.
- **INT8 Mapping:** `offset = 0, scale = 0.0314 deg/bit` → q=0 at 0°, q=80 at 2.5°, q=160 at 5°, q=255 at 8°.
- **Failure Mode:** Tilt actuator hydraulic leak; train must run at reduced speed with tilt disabled.

### Agent 6 Summary
- **Total Constraints:** 24
- **Highest Update Rate:** 100 Hz (speed, traction current, pantograph force)
- **Key Challenge:** Braking curve computation with real-time adhesion estimation and position uncertainty propagation
- **SIL 4 Requirement:** <1e-9 dangerous failure probability per hour; formal methods (B-method, SCADE) mandated

---