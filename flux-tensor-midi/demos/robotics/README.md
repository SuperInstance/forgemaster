# Robotics Demo: 6-DOF Arm as a Band

A working demonstration of FLUX-Tensor-MIDI's musical coordination model applied to robot kinematics. Each joint of a 6-DOF arm is a `RoomMusician` with its own tempo, role, and Eisenstein lattice snap grid.

## Concept

```
Joint 1 (base)     - slow (30 BPM)  - Halftime role
Joint 2 (shoulder) - slow (40 BPM)  - Triplet role  (drives rhythm)
Joint 3 (elbow)    - medium (60 BPM)- Root role     (main motion)
Joint 4 (wrist_pitch) - med (80 BPM)- Compound role
Joint 5 (wrist_yaw)   - med (80 BPM)- Doubletime role
Joint 6 (gripper)  - fast (120 BPM) - Waltz role    (fastest)
```

All joints are added to a `Band("robot_arm")` that listens to every member. Motion is coordinated as a **chord**: all joints arrive at their target within 1 beat of each other.

## Features

- **Pick-and-place cycle**: 9 phases (HOME → APPROACH → LOWER → GRASP → LIFT → MOVE → LOWER → RELEASE → RETURN)
- **Each joint** emits a 9-channel `FluxVector` (angle, error, velocity, progress, ready-flag)
- **Side-channel nods**: elbow nods to gripper when in position ("elbow in position, your turn gripper")
- **Harmony analysis**: Jaccard overlap of joint timing profiles, consonance/correlation at phase boundaries
- **Timeline export**: Full 80-beat timeline saved as JSON
- **VMS export**: Pick-and-place motion as a Video Music Score

## Run

```bash
cd demos/robotics/
python3 demo_robotics.py
```

## Output

- `pick_and_place_timeline.json` — full timeline with joint angles and end-effector positions
- `pick_and_place.vms` — VMS score of the motion
- Console output showing beat-by-beat end-effector position, harmony analysis, and arrival times

## Harmony Results

The demo computes:
- **Arrival spread**: All joints reach target within 0 beats (perfect chord for RETURN phase)
- **Jaccard overlap**: Pairwise timing profile similarity (e.g., base ↔ shoulder = 1.0, base ↔ gripper = 0.25)
- **Phase harmony**: Consonance ranges from 0.39 (HOME, all at zero) to 0.67 (extended pose)
- **Mean band coherence**: 0.915

## Technical Notes

- Uses simple planar forward kinematics (DH parameter-based)
- Each joint's angle is cubic-eased (smoothstep) for natural motion
- The band's mean coherence reflects how well all joints' state vectors align
