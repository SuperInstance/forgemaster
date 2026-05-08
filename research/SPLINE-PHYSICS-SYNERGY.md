# Synergy Map: Spline Anchoring + Physics + Constraints + OpenArm + FPGA

> The constraint stack runs from silicon to sea floor.

## The Full Stack (8 Layers)

```
Layer 8: Application
         ├── OpenArm (robot arm, constraint safety envelope)
         ├── SonarVision (underwater perception, beamformer)
         └── Insight Engine (self-iterating discovery)

Layer 7: Fleet Coordination
         ├── PLATO (knowledge system, tiles)
         ├── cocapn-schemas (cross-language contracts)
         └── fleet-proto (Rust shared types)

Layer 6: Constraint Math
         ├── Eisenstein integers (hex lattice workspace bounds)
         ├── Pythagorean triples (snap-to-manifold anchoring)
         ├── Spline snap (deadband-aware offset, publishable)
         └── Holonomy (angular deficit on constraint manifold)

Layer 5: GPU Acceleration
         ├── eisenstein.cuh (shared CUDA header)
         ├── guard2mask-gpu (5 CUDA kernels, AC-3 solver)
         ├── flux-vm-gpu (batch constraint VM, 3 opcodes)
         ├── depgraph-gpu (CSR graph, dependency analysis)
         └── marine-gpu-edge (beamformer, temporal smoothing)

Layer 4: VM / ISA
         ├── flux-vm (constraint bytecode VM)
         ├── guard2mask (GUARD DSL parser + solver)
         ├── Physics opcodes (PHY_ABSORB through PHY_REFRAC, 0xB0-0xB8)
         └── Eisenstein opcodes (EISEN_PACK, EISEN_NORM, EISEN_CHECK)

Layer 3: FPGA
         ├── flux_checker_top (DO-254 DAL A, TMR, 41 LUTs on iCE40)
         ├── flux_rau_interlock (AI→actuator safety gate)
         ├── hdc_judge (HDC safety arbitration, AXI4-Lite)
         └── iCE40UP5K ($50 board, 0.8% utilization for HDC judge)

Layer 2: Bare Metal
         ├── ESP32 (PLATO client, TWAI CAN, constraint check at 100Hz)
         ├── RP2040 (PLATO client, LED node)
         └── Jetson (Rust constraint service, aarch64)

Layer 1: Physics
         ├── UNESCO/Chen-Millero sound speed
         ├── Francois-Garrison absorption
         ├── Jerlov water type light attenuation
         ├── Thermocline model
         ├── Seabed model
         └── MarinePhysicsScope (9 models, dive chain 0-100m)
```

## The Synergy Points

### 1. Spline Snap → OpenArm Workspace
Spline snapping (deadband-aware offset) gives smooth constraint boundaries. Currently OpenArm uses hard joint limits (step function). Spline snap would:
- Create smooth workspace envelopes (no jerky rejection at boundary)
- Deadband-aware: small violations within tolerance are allowed, large ones blocked
- Snap trajectories to the nearest safe spline path

**Implementation**: `ConstraintSet.clamp_command()` calls `snap_to_spline()` instead of hard clamping.

### 2. Physics Opcodes → OpenArm Dynamics
The 9 physics opcodes (PHY_ABSORB through PHY_REFRAC) were built for underwater sonar. But the physics engine is generic:
- **PHY_ABSORB** → OpenArm: energy absorption in joint damping
- **PHY_REFRAC** → OpenArm: refraction = how control signals bend through the kinematic chain
- **MarinePhysicsScope** → OpenArm: `ArmPhysicsScope` with gravity, inertia, friction models

**Implementation**: The same FLUX VM that runs underwater physics can run arm dynamics. Just swap the physics model.

### 3. Beamformer → Multi-Arm Coordination
Delay-and-sum beamforming (32-element array, 128 beams) is essentially:
- Many parallel signals → combine into coherent picture
- Weighted sum with geometric delays

Multi-arm coordination is the SAME math:
- Many arm joint states → combine into fleet-wide constraint picture
- Weighted constraints with priority delays

**Implementation**: `beamformer_kernel` → `fleet_constraint_kernel`. Same CUDA code, different weights.

### 4. Eisenstein Workspace → Sonar Beam Steering
Eisenstein hex lattice gives 6-fold symmetric workspace bounds. Sonar beam steering has the same geometry:
- 32-element array → 128 beams in 360° → hexagonal beam pattern
- Eisenstein norm gives exact integer beam indices

**Implementation**: Map beam angles to Eisenstein lattice, use `eisenstein_disk_check` for beam selection.

### 5. Constraint Snap → FPGA Path
Spline snap (Pythagorean triple manifold) maps to hardware:
- `snap(theta, max_c)` → nearest triple → deterministic WCET
- On FPGA: lookup table in BRAM, O(1) snap
- Deadband check → simple comparator
- No floating point needed on the FPGA

**Implementation**: Pre-compute snap table for all angles, store in iCE40 BRAM (30 blocks available, we used 0).

### 6. Insight Engine → All Physics Models
The insight engine discovers patterns in Eisenstein experiments. The same frontier-driven loop can discover:
- Optimal constraint parameters for specific arm configurations
- Anomalous sonar readings (new underwater features)
- Phase transitions in multi-arm coordination
- Which spline snap tolerance gives the best safety/coverage tradeoff

**Implementation**: Each physics model publishes results as PLATO discovery tiles. Insight engine reads them all.

## Concrete Next Steps

| Step | What | Time |
|------|------|------|
| 1 | `ConstraintSet.clamp_command()` → use spline snap instead of hard clamp | 1 day |
| 2 | `ArmPhysicsScope` — reuse FLUX physics opcodes for arm dynamics | 2 days |
| 3 | `fleet_constraint_kernel` — repurpose beamformer CUDA for multi-arm | 2 days |
| 4 | Eisenstein beam steering — map sonar beams to hex lattice | 1 day |
| 5 | FPGA snap table — pre-compute Pythagorean snap into BRAM | 1 day |
| 6 | Insight engine reads ALL physics discovery tiles | 1 day |

## The Big Picture

```
Sonar sees the water → Beamformer (CUDA) → Physics opcodes (FLUX VM)
         ↓                                    ↓
   Eisenstein beams              Constraint snap (spline anchoring)
         ↓                                    ↓
   FPGA constraint gate ← ← ← ← Arm physics (gravity, inertia)
         ↓                                    ↓
   Actuator (OpenArm)              PLATO fleet logging
                                            ↓
                                    Insight engine discovers
                                    optimal parameters for BOTH
```

One constraint stack. Substrate-independent. Runs on GPU, FPGA, ESP32, or CPU. Same math everywhere.
