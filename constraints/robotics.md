# Robotics Constraint Library (IEC 62443 / ISO 10218 / ISO/TS 15066)

**Standard:** IEC 62443 (cybersecurity), ISO 10218-1/2 (robot safety), ISO/TS 15066 (collaborative robots)
**Safety Integrity:** PL d / Category 3 per ISO 13849
**Scope:** Collaborative robotics (cobots) and autonomous mobile robots (AMR)
**Update rates:** 1000–8000 Hz (servo), 50–100 Hz (safety monitoring)
**INT8 strategy:** Sub-millimeter/degree precision in 3 m workspaces, sub-Newton force resolution

---

## Joint Position Constraints

### 1. joint1_position — Base Rotation
- **Bounds:** [-180°, +180°]
- **Units:** degrees
- **Update Rate:** 1000 Hz
- **Safety Rationale:** Workspace boundary. Cable wrap limit. Mechanical hard stop at ±185°; FLUX software limit at ±180°.
- **INT8 Mapping:** `offset=-180, scale=1.4118 deg/bit` → q=0 at -180°, q=127 at 0°, q=255 at +180°
- **Failure Mode:** Encoder battery depletion on power loss; absolute encoder with battery backup + mechanical index.

### 2. joint2_position — Shoulder
- **Bounds:** [-120°, +120°]
- **Units:** degrees
- **Update Rate:** 1000 Hz
- **Safety Rationale:** Overhead/floor collision avoidance. Singularity avoidance: wrist-center alignment with Joint 1 axis.
- **INT8 Mapping:** `offset=-120, scale=0.9412 deg/bit` → q=0 at -120°, q=127 at 0°, q=255 at +120°
- **Failure Mode:** Gravity loading causes sag; encoder + resolver dual feedback with gravity compensation model.

### 3. joint3_position — Elbow
- **Bounds:** [-225°, +45°]
- **Units:** degrees
- **Update Rate:** 1000 Hz
- **Safety Rationale:** Self-collision: forearm vs. upper arm. < -225°: cable tension. > +45°: link collision.
- **INT8 Mapping:** `offset=-225, scale=1.0588 deg/bit` → q=0 at -225°, q=212 at -5°, q=255 at +45°
- **Failure Mode:** Gear backlash at direction reversal; dual-encoder (motor + joint) backlash compensation.

### 4. joint4_position — Wrist Roll
- **Bounds:** [-540°, +540°]
- **Units:** degrees
- **Update Rate:** 1000 Hz
- **Safety Rationale:** Continuous rotation tool (e.g., welding). ±540° = 1.5 turns with cable wrap management.
- **INT8 Mapping:** `offset=-540, scale=4.2353 deg/bit` → q=0 at -540°, q=127 at 0°, q=255 at +540°
- **Failure Mode:** Cable fatigue after N cycles; FLUX counts cumulative rotation for predictive maintenance.

### 5. joint5_position — Wrist Pitch
- **Bounds:** [-130°, +130°]
- **Units:** degrees
- **Update Rate:** 1000 Hz
- **Safety Rationale:** Tool orientation. Singularity when aligned with Joint 4 (gimbal lock).
- **INT8 Mapping:** `offset=-130, scale=1.0196 deg/bit` → q=0 at -130°, q=127 at 0°, q=255 at +130°
- **Failure Mode:** Gear tooth crack increases backlash; vibration signature monitoring.

### 6. joint6_position — Wrist Yaw
- **Bounds:** [-360°, +360°]
- **Units:** degrees
- **Update Rate:** 1000 Hz
- **Safety Rationale:** Tool yaw for alignment. Continuous rotation possible with slip rings.
- **INT8 Mapping:** `offset=-360, scale=2.8235 deg/bit` → q=0 at -360°, q=127 at 0°, q=255 at +360°
- **Failure Mode:** Slip ring brush wear increases contact resistance; encoder feedback prioritization.

---

## Joint Velocity Constraints

### 7. joint1_velocity — Base Rotation Speed
- **Bounds:** [-120 deg/s, +120 deg/s]
- **Units:** deg/s
- **Update Rate:** 1000 Hz
- **Safety Rationale:** TCP speed limit: 250 mm/s for collaborative mode. Joint velocity maps to TCP via Jacobian.
- **INT8 Mapping:** `offset=-120, scale=0.9412 deg/s/bit` → q=0 at -120, q=127 at 0, q=255 at +120
- **Failure Mode:** Servo amplifier fault: runaway velocity; independent safety PLC with separate encoder chain.

### 8. joint2_velocity — Shoulder Speed
- **Bounds:** [-120 deg/s, +120 deg/s]
- **Units:** deg/s
- **Update Rate:** 1000 Hz
- **Safety Rationale:** Same as Joint 1. Shoulder velocity has largest TCP contribution.
- **INT8 Mapping:** `offset=-120, scale=0.9412 deg/s/bit` → q=0 at -120, q=127 at 0, q=255 at +120
- **Failure Mode:** Drive train resonance; notch filter + torque ripple compensation.

---

## Workspace Containment Constraints

### 9. tcp_x — Tool Center Point X (World Frame)
- **Bounds:** [-3000 mm, +3000 mm]
- **Units:** mm
- **Update Rate:** 1000 Hz
- **Safety Rationale:** Workspace fence boundary. Collaborative: human-robot shared workspace. >3 m: extended safety zone.
- **INT8 Mapping:** `offset=-3000, scale=23.5294 mm/bit` → q=0 at -3000, q=127 at 0, q=255 at +3000
- **Failure Mode:** Kinematic model error from link length calibration drift; auto-calibration via touch probe.

### 10. tcp_y — Tool Center Point Y (World Frame)
- **Bounds:** [-3000 mm, +3000 mm]
- **Units:** mm
- **Update Rate:** 1000 Hz
- **Safety Rationale:** Same as X. Y-axis often aligned with conveyor feed direction.
- **INT8 Mapping:** `offset=-3000, scale=23.5294 mm/bit` → q=0 at -3000, q=127 at 0, q=255 at +3000
- **Failure Mode:** Base mounting bolt looseness shifts world frame; annual recalibration required.

### 11. tcp_z — Tool Center Point Z (World Frame)
- **Bounds:** [0 mm, +2500 mm]
- **Units:** mm
- **Update Rate:** 1000 Hz
- **Safety Rationale:** Floor = 0 mm (collision). Z < 0: floor crash. Z > 2500: overhead structure collision.
- **INT8 Mapping:** `offset=0, scale=9.8039 mm/bit` → q=0 at 0, q=128 at 1250, q=255 at 2500
- **Failure Mode:** Payload unexpectedly heavy causes sag; force/torque sensor detects contact.

### 12. tcp_speed — TCP Velocity Magnitude
- **Bounds:** [0 mm/s, 250 mm/s]
- **Units:** mm/s
- **Update Rate:** 1000 Hz
- **Safety Rationale:** ISO/TS 15066: 150 mm/s for hand guiding, 250 mm/s for power & force limiting. >250: power limiting active.
- **INT8 Mapping:** `offset=0, scale=0.9804 mm/s/bit` → q=0 at 0, q=153 at 150, q=255 at 250
- **Failure Mode:** Jacobian singularity causes infinite joint velocity demand; damped least-squares inverse + FLUX override.

---

## Force Bounds

### 13. joint1_torque — Base Torque
- **Bounds:** [-2000 Nm, +2000 Nm]
- **Units:** Nm
- **Update Rate:** 1000 Hz
- **Safety Rationale:** Base joint carries full arm weight + payload. Torque limit prevents gearbox/shear failure.
- **INT8 Mapping:** `offset=-2000, scale=15.6863 Nm/bit` → q=0 at -2000, q=127 at 0, q=255 at +2000
- **Failure Mode:** Collision produces spike >2x nominal; torque observer + collision detection in <1 ms.

### 14. joint2_torque — Shoulder Torque
- **Bounds:** [-1500 Nm, +1500 Nm]
- **Units:** Nm
- **Update Rate:** 1000 Hz
- **Safety Rationale:** Shoulder torque. Payload at full extension maximizes.
- **INT8 Mapping:** `offset=-1500, scale=11.7647 Nm/bit` → q=0 at -1500, q=127 at 0, q=255 at +1500
- **Failure Mode:** Belt drive stretch increases transmission error; tensioner adjustment + FLUX backlash model.

### 15. force_x — Tool Frame X Force
- **Bounds:** [-150 N, +150 N]
- **Units:** N
- **Update Rate:** 1000 Hz
- **Safety Rationale:** Contact force for assembly, polishing, human collision. 150 N: pain threshold per ISO/TS 15066.
- **INT8 Mapping:** `offset=-150, scale=1.1765 N/bit` → q=0 at -150, q=127 at 0, q=255 at +150. Resolution: ~1.2 N/bit.
- **Failure Mode:** FT sensor temperature drift; auto-zero at program start + thermal model.

### 16. force_y — Tool Frame Y Force
- **Bounds:** [-150 N, +150 N]
- **Units:** N
- **Update Rate:** 1000 Hz
- **Safety Rationale:** Same as X. Y often lateral/sliding direction.
- **INT8 Mapping:** `offset=-150, scale=1.1765 N/bit` → q=0 at -150, q=127 at 0, q=255 at +150
- **Failure Mode:** Cable routing to end-effector induces crosstalk; calibration matrix update.

### 17. force_z — Tool Frame Z Force
- **Bounds:** [-300 N, +300 N]
- **Units:** N
- **Update Rate:** 1000 Hz
- **Safety Rationale:** Z typically pressing direction; higher force for machining/deburring. 300 N: bone fracture threshold.
- **INT8 Mapping:** `offset=-300, scale=2.3529 N/bit` → q=0 at -300, q=127 at 0, q=255 at +300
- **Failure Mode:** Payload inertia during deceleration appears as force spike; momentum observer distinguishes.

---

## Safety System Constraints

### 18. human_proximity — Safety Scanner Distance
- **Bounds:** [0 mm, 5000 mm]
- **Units:** mm
- **Update Rate:** 50 Hz
- **Safety Rationale:** Laser scanner / depth camera protective fields. Protective stop: 500 mm. Warning: 1500 mm.
- **INT8 Mapping:** `offset=0, scale=19.6078 mm/bit` → q=0 at 0, q=26 at 500, q=77 at 1500, q=255 at 5000
- **Failure Mode:** Reflective object false positive; muting zone for conveyor entry.

### 19. base_inclination — Robot Base Tilt
- **Bounds:** [-5°, +5°]
- **Units:** degrees
- **Update Rate:** 10 Hz
- **Safety Rationale:** Mobile robot on ramp. >5°: tip-over risk, kinematic model invalid (gravity vector misalignment).
- **INT8 Mapping:** `offset=-5, scale=0.0392 deg/bit` → q=0 at -5°, q=127 at 0°, q=255 at +5°
- **Failure Mode:** IMU mounting screw looseness; tilt measured vs. gravity model discrepancy.

### 20. drive_temp — Motor Drive Temperature
- **Bounds:** [20°C, 85°C]
- **Units:** °C
- **Update Rate:** 1 Hz
- **Safety Rationale:** IGBT junction: 150°C limit. Heatsink: 85°C alarm. >90°C: foldback (torque limit reduction).
- **INT8 Mapping:** `offset=20, scale=0.2549 °C/bit` → q=0 at 20°C, q=128 at 53°C, q=196 at 70°C, q=255 at 85°C
- **Failure Mode:** Cooling fan failure; tachometer on fan + thermal model prediction.

### 21. brake_status — Holding Brake Confirmation
- **Bounds:** [0 (ENGAGED), 1 (RELEASED)]
- **Units:** binary
- **Update Rate:** 1000 Hz
- **Safety Rationale:** Holding brake must release before motion command accepted. <5 ms release time. Power-off = engaged (fail-safe).
- **INT8 Mapping:** Binary: q<128 = engaged, q>=128 = released. Hard threshold with hysteresis.
- **Failure Mode:** Brake coil burnout; dual brake architecture for vertical axes.

### 22. payload_mass — Estimated Payload
- **Bounds:** [0 kg, 50 kg]
- **Units:** kg
- **Update Rate:** 10 Hz
- **Safety Rationale:** Inertia compensation in servo loop. Wrong mass: oscillation or sluggish response. Overload: structural failure.
- **INT8 Mapping:** `offset=0, scale=0.1961 kg/bit` → q=0 at 0, q=128 at 25, q=255 at 50
- **Failure Mode:** Payload dropped during cycle; force transient + gravity torque change detected.

---

## Library Summary

| Metric | Value |
|--------|-------|
| Total Constraints | 22 |
| Highest Update Rate | 1000 Hz (all servo-level) |
| Key Challenge | Force/torque <1 N resolution at 150 N full scale — sub-bit dithering essential |
| Safety Rating | PL d / Cat 3: MTTFd high, DC medium, redundancy required |
| Quantization Difficulty | Hard — nonlinear expanded-nibble for force precision |

*Source: Mission 2 Agent 8 — IEC 62443 / ISO 10218 domain library*
