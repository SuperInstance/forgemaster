# Constraint Library Validation Results

**Date:** 2026-05-21  
**Scope:** 10 industries, target 248 constraints  
**Source:** `/home/phoenix/.openclaw/workspace/constraints`

---

## Summary

| Metric | Count | Percentage |
|--------|-------|-----------|
| Total constraints parsed | 248 | — |
| Valid (internally consistent) | 247 | 99.6% |
| INT8-compatible | 211 | 85.1% |
| Cross-industry conflicts | 66 | — |

## Per-Industry Breakdown

| Industry | Standard | Total | Valid | INT8-Compat | Status |
|----------|----------|-------|-------|-------------|--------|
| Automotive | ISO 26262 | 27 | 27 | 26 | ✅ |
| Aerospace | DO-178C | 28 | 28 | 20 | ✅ |
| Avionics | DO-254 | 23 | 23 | 19 | ✅ |
| Medical | IEC 62304 | 28 | 28 | 27 | ✅ |
| Energy | IEC 61511 | 23 | 23 | 20 | ✅ |
| Marine | DNV | 25 | 25 | 22 | ✅ |
| Nuclear | IEC 61513 | 24 | 23 | 21 | ⚠️ |
| Rail | EN 50128 | 24 | 24 | 21 | ✅ |
| Robotics | ISO 10218 | 22 | 22 | 15 | ✅ |
| Industrial | IEC 61508 | 24 | 24 | 20 | ✅ |

## Cross-Industry Conflicts

- **Automotive/Tire Pressure — Front Left** vs **Avionics/Propellant Tank Pressure -- MON**: Ranges are disjoint — no overlap between industries
  - A: [1.8, 3.5] bar,
  - B: [10.0, 25.0] bar,
- **Automotive/Tire Pressure — Front Left** vs **Avionics/Propellant Tank Pressure -- MMH**: Ranges are disjoint — no overlap between industries
  - A: [1.8, 3.5] bar,
  - B: [10.0, 25.0] bar,
- **Automotive/Tire Pressure — Front Right** vs **Avionics/Propellant Tank Pressure -- MON**: Ranges are disjoint — no overlap between industries
  - A: [1.8, 3.5] bar,
  - B: [10.0, 25.0] bar,
- **Automotive/Tire Pressure — Front Right** vs **Avionics/Propellant Tank Pressure -- MMH**: Ranges are disjoint — no overlap between industries
  - A: [1.8, 3.5] bar,
  - B: [10.0, 25.0] bar,
- **Automotive/Tire Pressure — Rear Left** vs **Avionics/Propellant Tank Pressure -- MON**: Ranges are disjoint — no overlap between industries
  - A: [1.8, 3.5] bar,
  - B: [10.0, 25.0] bar,
- **Automotive/Tire Pressure — Rear Left** vs **Avionics/Propellant Tank Pressure -- MMH**: Ranges are disjoint — no overlap between industries
  - A: [1.8, 3.5] bar,
  - B: [10.0, 25.0] bar,
- **Automotive/Tire Pressure — Rear Right** vs **Avionics/Propellant Tank Pressure -- MON**: Ranges are disjoint — no overlap between industries
  - A: [1.8, 3.5] bar,
  - B: [10.0, 25.0] bar,
- **Automotive/Tire Pressure — Rear Right** vs **Avionics/Propellant Tank Pressure -- MMH**: Ranges are disjoint — no overlap between industries
  - A: [1.8, 3.5] bar,
  - B: [10.0, 25.0] bar,
- **Automotive/Oil Pressure (ICE)** vs **Avionics/Propellant Tank Pressure -- MON**: Ranges are disjoint — no overlap between industries
  - A: [1.0, 6.0] bar,
  - B: [10.0, 25.0] bar,
- **Automotive/Oil Pressure (ICE)** vs **Avionics/Propellant Tank Pressure -- MMH**: Ranges are disjoint — no overlap between industries
  - A: [1.0, 6.0] bar,
  - B: [10.0, 25.0] bar,
- **Avionics/Propellant Tank Pressure -- MON** vs **Rail/Brake Cylinder Pressure -- Car 1**: Ranges are disjoint — no overlap between industries
  - A: [10.0, 25.0] bar,
  - B: [0.0, 4.5] bar,
- **Avionics/Propellant Tank Pressure -- MMH** vs **Rail/Brake Cylinder Pressure -- Car 1**: Ranges are disjoint — no overlap between industries
  - A: [10.0, 25.0] bar,
  - B: [0.0, 4.5] bar,
- **Automotive/Battery Cell Temperature** vs **Aerospace/Engine EGT (Exhaust Gas Temperature)**: Ranges are disjoint — no overlap between industries
  - A: [-20.0, 55.0] °C,
  - B: [200.0, 950.0] °C,
- **Automotive/Battery Cell Temperature** vs **Marine/Main Engine -- Cylinder Exhaust Temperature**: Ranges are disjoint — no overlap between industries
  - A: [-20.0, 55.0] °C,
  - B: [200.0, 520.0] °C,
- **Automotive/Battery Cell Temperature** vs **Marine/LNG Bunker Tank Temperature**: Ranges are disjoint — no overlap between industries
  - A: [-20.0, 55.0] °C,
  - B: [-165.0, -150.0] °C,
- **Automotive/Coolant Temperature (ICE)** vs **Aerospace/Engine EGT (Exhaust Gas Temperature)**: Ranges are disjoint — no overlap between industries
  - A: [60.0, 120.0] °C,
  - B: [200.0, 950.0] °C,
- **Automotive/Coolant Temperature (ICE)** vs **Avionics/Battery Temperature**: Ranges are disjoint — no overlap between industries
  - A: [60.0, 120.0] °C,
  - B: [-10.0, 40.0] °C,
- **Automotive/Coolant Temperature (ICE)** vs **Marine/Main Engine -- Cylinder Exhaust Temperature**: Ranges are disjoint — no overlap between industries
  - A: [60.0, 120.0] °C,
  - B: [200.0, 520.0] °C,
- **Automotive/Coolant Temperature (ICE)** vs **Marine/LNG Bunker Tank Temperature**: Ranges are disjoint — no overlap between industries
  - A: [60.0, 120.0] °C,
  - B: [-165.0, -150.0] °C,
- **Automotive/Coolant Temperature (ICE)** vs **Industrial/Battery Temperature**: Ranges are disjoint — no overlap between industries
  - A: [60.0, 120.0] °C,
  - B: [0.0, 45.0] °C,
- **Automotive/Coolant Temperature (ICE)** vs **Industrial/Internal Temperature -- Electronics**: Ranges are disjoint — no overlap between industries
  - A: [60.0, 120.0] °C,
  - B: [-10.0, 50.0] °C,
- **Aerospace/Engine EGT (Exhaust Gas Temperature)** vs **Avionics/Solar Array Wing Temperature**: Ranges are disjoint — no overlap between industries
  - A: [200.0, 950.0] °C,
  - B: [-150.0, 120.0] °C,
- **Aerospace/Engine EGT (Exhaust Gas Temperature)** vs **Avionics/Battery Temperature**: Ranges are disjoint — no overlap between industries
  - A: [200.0, 950.0] °C,
  - B: [-10.0, 40.0] °C,
- **Aerospace/Engine EGT (Exhaust Gas Temperature)** vs **Marine/LNG Bunker Tank Temperature**: Ranges are disjoint — no overlap between industries
  - A: [200.0, 950.0] °C,
  - B: [-165.0, -150.0] °C,
- **Aerospace/Engine EGT (Exhaust Gas Temperature)** vs **Rail/Axle Bearing Temperature**: Ranges are disjoint — no overlap between industries
  - A: [200.0, 950.0] °C,
  - B: [20.0, 150.0] °C,
- **Aerospace/Engine EGT (Exhaust Gas Temperature)** vs **Industrial/Battery Temperature**: Ranges are disjoint — no overlap between industries
  - A: [200.0, 950.0] °C,
  - B: [0.0, 45.0] °C,
- **Aerospace/Engine EGT (Exhaust Gas Temperature)** vs **Industrial/Internal Temperature -- Electronics**: Ranges are disjoint — no overlap between industries
  - A: [200.0, 950.0] °C,
  - B: [-10.0, 50.0] °C,
- **Aerospace/Brake Temperature** vs **Marine/LNG Bunker Tank Temperature**: Ranges are disjoint — no overlap between industries
  - A: [0.0, 650.0] °C,
  - B: [-165.0, -150.0] °C,
- **Avionics/Solar Array Wing Temperature** vs **Marine/Main Engine -- Cylinder Exhaust Temperature**: Ranges are disjoint — no overlap between industries
  - A: [-150.0, 120.0] °C,
  - B: [200.0, 520.0] °C,
- **Avionics/Battery Temperature** vs **Marine/Main Engine -- Cylinder Exhaust Temperature**: Ranges are disjoint — no overlap between industries
  - A: [-10.0, 40.0] °C,
  - B: [200.0, 520.0] °C,
- **Avionics/Battery Temperature** vs **Marine/LNG Bunker Tank Temperature**: Ranges are disjoint — no overlap between industries
  - A: [-10.0, 40.0] °C,
  - B: [-165.0, -150.0] °C,
- **Marine/Main Engine -- Cylinder Exhaust Temperature** vs **Rail/Axle Bearing Temperature**: Ranges are disjoint — no overlap between industries
  - A: [200.0, 520.0] °C,
  - B: [20.0, 150.0] °C,
- **Marine/Main Engine -- Cylinder Exhaust Temperature** vs **Industrial/Battery Temperature**: Ranges are disjoint — no overlap between industries
  - A: [200.0, 520.0] °C,
  - B: [0.0, 45.0] °C,
- **Marine/Main Engine -- Cylinder Exhaust Temperature** vs **Industrial/Internal Temperature -- Electronics**: Ranges are disjoint — no overlap between industries
  - A: [200.0, 520.0] °C,
  - B: [-10.0, 50.0] °C,
- **Marine/LNG Bunker Tank Temperature** vs **Rail/Traction Motor Temperature**: Ranges are disjoint — no overlap between industries
  - A: [-165.0, -150.0] °C,
  - B: [20.0, 220.0] °C,
- **Marine/LNG Bunker Tank Temperature** vs **Rail/Axle Bearing Temperature**: Ranges are disjoint — no overlap between industries
  - A: [-165.0, -150.0] °C,
  - B: [20.0, 150.0] °C,
- **Marine/LNG Bunker Tank Temperature** vs **Industrial/Battery Temperature**: Ranges are disjoint — no overlap between industries
  - A: [-165.0, -150.0] °C,
  - B: [0.0, 45.0] °C,
- **Marine/LNG Bunker Tank Temperature** vs **Industrial/Internal Temperature -- Electronics**: Ranges are disjoint — no overlap between industries
  - A: [-165.0, -150.0] °C,
  - B: [-10.0, 50.0] °C,
- **Automotive/Lane Offset from Centerline** vs **Industrial/DVL Altitude Above Bottom**: Ranges are disjoint — no overlap between industries
  - A: [-1.5, 1.5] m,
  - B: [2.0, 120.0] m,
- **Aerospace/Airspeed — Indicated (KIAS)** vs **Marine/Ship's Speed -- Through Water (STW)**: Ranges are disjoint — no overlap between industries
  - A: [50.0, 450.0] knots,
  - B: [0.0, 35.0] knots,
- **Aerospace/Airspeed — Indicated (KIAS)** vs **Marine/Ship's Speed -- Over Ground (SOG)**: Ranges are disjoint — no overlap between industries
  - A: [50.0, 450.0] knots,
  - B: [0.0, 35.0] knots,
- **Aerospace/Airspeed — True (KTAS)** vs **Marine/Ship's Speed -- Through Water (STW)**: Ranges are disjoint — no overlap between industries
  - A: [55.0, 520.0] knots,
  - B: [0.0, 35.0] knots,
- **Aerospace/Airspeed — True (KTAS)** vs **Marine/Ship's Speed -- Over Ground (SOG)**: Ranges are disjoint — no overlap between industries
  - A: [55.0, 520.0] knots,
  - B: [0.0, 35.0] knots,
- **Avionics/Bus Voltage -- Primary 28V** vs **Industrial/Battery Pack Voltage**: Ranges are disjoint — no overlap between industries
  - A: [24.0, 36.0] V,
  - B: [180.0, 260.0] V,
- **Avionics/Bus Voltage -- Secondary 5V** vs **Industrial/Battery Pack Voltage**: Ranges are disjoint — no overlap between industries
  - A: [4.75, 5.25] V,
  - B: [180.0, 260.0] V,
- **Medical/SpO2 (Oxygen Saturation)** vs **Energy/thd_voltage — Voltage Harmonic Distortion**: Ranges are disjoint — no overlap between industries
  - A: [70.0, 100.0] %
  - B: [0.0, 8.0] %
- **Medical/FIO2 (Fraction Inspired Oxygen)** vs **Energy/thd_voltage — Voltage Harmonic Distortion**: Ranges are disjoint — no overlap between industries
  - A: [21.0, 100.0] %
  - B: [0.0, 8.0] %
- **Energy/thd_voltage — Voltage Harmonic Distortion** vs **Nuclear/Pressurizer Level**: Ranges are disjoint — no overlap between industries
  - A: [0.0, 8.0] %
  - B: [15.0, 85.0] %
- **Energy/thd_voltage — Voltage Harmonic Distortion** vs **Nuclear/Steam Generator Level — Narrow Range**: Ranges are disjoint — no overlap between industries
  - A: [0.0, 8.0] %
  - B: [20.0, 80.0] %
- **Medical/Temperature — Core** vs **Nuclear/Reactor Coolant Temperature — Hot Leg**: Ranges are disjoint — no overlap between industries
  - A: [25.0, 45.0] °C
  - B: [250.0, 350.0] °C
- **Medical/Temperature — Core** vs **Nuclear/Reactor Coolant Temperature — Cold Leg**: Ranges are disjoint — no overlap between industries
  - A: [25.0, 45.0] °C
  - B: [250.0, 330.0] °C
- **Medical/Temperature — Skin** vs **Nuclear/Reactor Coolant Temperature — Hot Leg**: Ranges are disjoint — no overlap between industries
  - A: [20.0, 42.0] °C
  - B: [250.0, 350.0] °C
- **Medical/Temperature — Skin** vs **Nuclear/Reactor Coolant Temperature — Cold Leg**: Ranges are disjoint — no overlap between industries
  - A: [20.0, 42.0] °C
  - B: [250.0, 330.0] °C
- **Energy/transformer_oil_temp — Transformer Oil Temperature** vs **Nuclear/Reactor Coolant Temperature — Hot Leg**: Ranges are disjoint — no overlap between industries
  - A: [20.0, 105.0] °C
  - B: [250.0, 350.0] °C
- **Energy/transformer_oil_temp — Transformer Oil Temperature** vs **Nuclear/Reactor Coolant Temperature — Cold Leg**: Ranges are disjoint — no overlap between industries
  - A: [20.0, 105.0] °C
  - B: [250.0, 330.0] °C
- **Energy/transformer_hot_spot — Winding Hot Spot** vs **Nuclear/Reactor Coolant Temperature — Hot Leg**: Ranges are disjoint — no overlap between industries
  - A: [20.0, 140.0] °C
  - B: [250.0, 350.0] °C
- **Energy/transformer_hot_spot — Winding Hot Spot** vs **Nuclear/Reactor Coolant Temperature — Cold Leg**: Ranges are disjoint — no overlap between industries
  - A: [20.0, 140.0] °C
  - B: [250.0, 330.0] °C
- **Nuclear/Reactor Coolant Temperature — Hot Leg** vs **Robotics/drive_temp — Motor Drive Temperature**: Ranges are disjoint — no overlap between industries
  - A: [250.0, 350.0] °C
  - B: [20.0, 85.0] °C
- **Nuclear/Reactor Coolant Temperature — Cold Leg** vs **Robotics/drive_temp — Motor Drive Temperature**: Ranges are disjoint — no overlap between industries
  - A: [250.0, 330.0] °C
  - B: [20.0, 85.0] °C
- **Medical/Pacemaker Pulse Amplitude** vs **Energy/inverter_dc_link — DER Inverter DC Bus**: Ranges are disjoint — no overlap between industries
  - A: [0.0, 10.0] V
  - B: [600.0, 1000.0] V
- **Medical/Pacemaker Pulse Amplitude** vs **Energy/substation_battery — DC Station Supply**: Ranges are disjoint — no overlap between industries
  - A: [0.0, 10.0] V
  - B: [105.0, 130.0] V
- **Medical/Pacemaker Pulse Width** vs **Energy/breaker_operating_time — Circuit Breaker Timing**: Ranges are disjoint — no overlap between industries
  - A: [0.1, 2.0] ms
  - B: [20.0, 80.0] ms
- **Energy/bus_voltage_a — Phase A RMS** vs **Nuclear/Emergency Diesel Generator (EDG) Voltage**: Ranges are disjoint — no overlap between industries
  - A: [360.0, 420.0] kV
  - B: [3.6, 4.4] kV
- **Energy/bus_voltage_b — Phase B RMS** vs **Nuclear/Emergency Diesel Generator (EDG) Voltage**: Ranges are disjoint — no overlap between industries
  - A: [360.0, 420.0] kV
  - B: [3.6, 4.4] kV
- **Energy/bus_voltage_c — Phase C RMS** vs **Nuclear/Emergency Diesel Generator (EDG) Voltage**: Ranges are disjoint — no overlap between industries
  - A: [360.0, 420.0] kV
  - B: [3.6, 4.4] kV
- **Marine/Bilge Level -- Engine Room** vs **Rail/Wheel Diameter (Calibrated)**: Ranges are disjoint — no overlap between industries
  - A: [0.0, 500.0] mm,
  - B: [800.0, 920.0] mm,

## Validation Criteria

1. **Internal consistency:** Lower bound < upper bound, parseable values
2. **Physical plausibility:** No negative Kelvin, reasonable magnitudes
3. **INT8 saturation:** Range fits in 8-bit encoding after scaling
4. **Cross-industry compatibility:** No disjoint ranges for same-unit constraints

---

*Generated by `experiment.py` — Forgemaster ⚒️ Constraint Validation Suite*
