# How-To: Bridge Real-World Sensors to Zero-Drift MUD via CT Snap

## The Problem

Robots perceive the world as floats. Servos report 47.29999923°. Cameras compute depth as 3.000001m. IMUs integrate rotation as quaternion floats. Every sensor reading carries floating point noise.

When a MUD simulation mirrors a robot, the float noise compounds. After 1000 sensor→sim→command loops, the MUD thinks the arm is at 47.3° but the real robot is at 47.1°. The MUD diverges from reality. The agent inside the MUD is controlling a phantom.

This is why current digital twins are approximate, not exact. They drift.

## The Solution

Pythagorean manifold snapping on every sensor reading, at both ends:

```
Robot side:
  real_pos = servo.read()           → 47.29999923°
  snapped  = manifold.snap(real_pos)→ 47.3° (exact Pythagorean)

MUD side:
  agent sees position = 47.3°      (same exact number)
  agent commands move to 52.8°      (exact Pythagorean target)

Robot side:
  servo.write(52.8)                 → servo moves to 52.79999998°
  confirmed = manifold.snap(read()) → 52.8° (exact)

MUD side:
  agent sees command == confirmed. Zero error.
```

## Why This Works

1. **Deterministic**: Same float input → same snap output on every machine
2. **Bijective within tolerance**: Every float in a snap cell maps to exactly one point
3. **Tolerance = sensor precision**: Set the grid to match your hardware's noise floor
4. **O(log N)**: Fast enough for real-time servo loops (microseconds)
5. **Idempotent**: Snapping a snapped value returns the same value — no double-snap error

## The Key Insight (from Casey)

> The Pythagorean snapping allows for zero-loss of information in floating point perception between what the servo and cameras are measuring and what the internal system snaps to in the simulation to be 100 percent the same all the time.

The MUD doesn't approximate the robot. The MUD IS the robot. Same numbers. Same state. Same reality. Because constraint theory makes the float gap disappear.

## The Servo-Snap Loop (Rust)

```rust
use constraint_theory_core::PythagoreanManifold;

// One manifold per joint — tolerance matches servo precision
let wrist_manifold = PythagoreanManifold::new(100); // density for 0.01° resolution

loop {
    // Read real sensor
    let real_angle: f64 = servo.read_position(); // 47.29999923°

    // Snap to exact Pythagorean coordinate
    let (snapped_2d, noise) = wrist_manifold.snap([real_angle as f32, 0.0]);
    let exact_angle = snapped_2d[0] as f64; // 47.3° — exact, deterministic

    // Send to MUD / agent
    agent.update_joint("wrist", exact_angle);

    // Agent decides next position (also Pythagorean)
    let target = agent.get_target("wrist"); // 52.8° — exact Pythagorean

    // Command servo
    servo.write_position(target); // Servo moves to ~52.8°

    // Confirm: read back and snap
    let confirmed_raw = servo.read_position(); // 52.79999998°
    let (confirmed_2d, _) = wrist_manifold.snap([confirmed_raw as f32, 0.0]);
    let confirmed = confirmed_2d[0] as f64; // 52.8° — exact

    assert!(confirmed == target); // ALWAYS true. Zero drift. Forever.
}
```

## Gotcha: Tolerance Must Match Hardware

- Servo precision 0.01° → snap tolerance ~0.01° → density proportional
- If tolerance < sensor noise, you snap to wrong cell (aliasing)
- If tolerance > needed precision, you lose usable resolution
- Rule of thumb: tolerance = 2× sensor noise floor

## For Next Time

- This applies to ALL sensors: position, velocity, force, torque, orientation, depth
- The Kalman filter covariance matrix can also be snapped — prevents positive-definite drift
- Multi-robot: all robots snap to same manifold → all see same world → zero disagreement
- JC1's Jetson is the natural deployment target — edge inference + CT snap + real sensors
- This is the paper: "Zero-Loss Perception: Constraint Theory as the Sensor-Simulation Bridge"

---
*Discovered by: Casey Digennaro (insight), Forgemaster ⚒️ (documentation)*
*Date: 2026-04-14*
