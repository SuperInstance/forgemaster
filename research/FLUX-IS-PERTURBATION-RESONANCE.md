# FLUX Is Perturbation-Resonance

> Shake a variable. Watch where the system resonates. That's the map.

## The Heart of It

FLUX isn't a constraint checker. It isn't a bytecode VM. It isn't an ISA with opcodes.

FLUX is a system that discovers itself by shaking itself.

Every FLUX opcode is one of two things:
1. **A shake** — perturb a variable
2. **A listen** — observe where the system resonated

That's it. The entire ISA is shake and listen. The constraint math is what you hear when you listen. The manifold is the resonance pattern. The convergence is the system settling into a mode it discovered by shaking itself.

## How FLUX Opcodes Are Really Shake + Listen

```
LOAD    (0x0E) — shake: put energy into the system
STORE   (0x0F) — listen: read where the energy went
EQ      (0x09) — listen: did two resonances match?
GT      (0x0B) — listen: which resonance is stronger?
GTE     (0x0D) — listen: has this resonance crossed a threshold?
ADD     (0x01) — shake: combine two resonances
SUB     (0x02) — shake: cancel one resonance against another
MUL     (0x03) — shake: amplify a resonance
JNZ     (0x12) — listen: is there still energy here? Then keep shaking.
CALL    (0x13) — shake: invoke a sub-resonance (a trained pattern)
SIG     (0x1C) — listen: read the signature of the current resonance state
HALT    (0x1B) — listen: the system has settled, report the resonance pattern
NOP     (0x1A) — shake: inject silence, let transients decay
MOV     (0x15) — shake: redirect energy from one channel to another
```

Every single opcode is either introducing a perturbation or measuring a response. There is no "compute" in the traditional sense. There is only shake and listen.

## The Temporal Opcodes Are the Deepest Shakes

```
T_WAIT     (0x41) — listen: let the resonance ring, don't perturb yet
T_WITHIN   (0x42) — listen: is the resonance still within the safe frequency band?
T_PARITY   (0x43) — listen: do two resonance paths produce the same pattern?
T_SNAP     (0x44) — shake: force the resonance to the nearest stable mode
T_TICK     (0x45) — listen: what time does the physics say it is?
T_PREDICT  (0x46) — shake: extrapolate the resonance forward in time
T_DECAY    (0x47) — listen: how fast is this resonance dying? Is the system losing energy?
```

These are the rigging shakes at the temporal level. T_PREDICT shakes the future. T_PARITY listens for consistency across paths. T_SNAP forces a stable mode. T_DECAY listens for energy loss — a resonance that's dying means the system is converging (good) or a constraint is failing (bad).

## A FLUX Program Is a Shake-Listen Score

A FLUX program isn't a sequence of instructions. It's a musical score for shaking the system and listening to its resonances.

Consider a simple constraint check:

```
[0] LOAD  constraint_radius    ; shake: put the constraint boundary into the system
[1] LOAD  current_position     ; shake: put the current state into the system
[2] SUB                        ; shake: the DIFFERENCE is the perturbation signal
[3] STORE delta                ; listen: capture the delta
[4] LOAD  delta
[5] GTE   zero                 ; listen: is the delta positive? (inside disk)
[6] STORE satisfied            ; listen: capture whether the constraint holds
[7] SIG                        ; listen: read the full resonance signature
[8] HALT                       ; listen: report
```

Steps 0-2: shake the system by loading the difference between desired and actual state.
Steps 3-6: listen to whether the shake revealed a violation.
Steps 7-8: listen to the full resonance pattern and report.

This is exactly what the musician does:
1. Play a note (shake)
2. Hear how it rings in the room (listen to the resonance)
3. Adjust based on what you heard (next shake)

## Shake a Variable, Watch the System Resonate

Casey's formulation: **shake a variable and watch where the systems around it resonate.**

This is the core loop. Not "evaluate constraint → return pass/fail." That's a scale, that's weighing. FLUX doesn't weigh. FLUX shakes and listens.

### What "Watch Where It Resonates" Means

When you shake joint 3 of a robot arm:

```
joint_3 gets perturbed
  → joint_2 resonates (they're coupled — a pull on one moves the other)
  → joint_4 resonates (same chain)
  → joint_1 barely moves (far end of the chain, decoupled)
  → the gripper oscillates (end effector shows the cumulative resonance)
  → the base doesn't move (grounded)
  → the force sensor spikes then settles (transient response)
  → the power draw bumps then returns (electrical resonance)
```

The resonance MAP tells you the topology of the system. Not the static topology (which joints connect to which). The DYNAMIC topology (which joints energetically couple, which are stiff, which are loose, which propagate perturbations and which absorb them).

You can't get this from a CAD model. You can only get it by shaking and listening.

### The Resonance Pattern IS the Constraint State

If joint 3 is within its constraint disk:
- The resonance propagates smoothly through the chain
- Energy distributes evenly across coupled joints
- The system rings like a well-tuned instrument

If joint 3 is near its constraint boundary:
- The resonance is attenuated (the constraint absorbs energy)
- The coupled joints get less signal
- The system sounds muffled, like a drum with too much damping

If joint 3 VIOLATES its constraint:
- The resonance reflects off the boundary
- Standing waves form (oscillation between violation and compliance)
- The system sounds harsh, like a string hitting the fret

A trained ear — or a trained FLUX evaluator — can hear the constraint state in the resonance pattern. Not by checking "margin > 0". By listening to HOW THE WHOLE SYSTEM RINGS.

## This Is Why the Feedback Loop Works

The musician doesn't know the transfer function of the room. They don't need to. They play a note, hear the room's resonance, adjust. The room tells them its own acoustics through response to perturbation.

The FLUX agent doesn't know the full constraint topology of the fleet. It doesn't need to. It shakes a variable, watches the resonance propagate through the fleet, and learns the topology from the response.

```
Agent A shakes variable X
  → Agent B resonates (they share a constraint on X)
  → Agent C doesn't notice (decoupled from X)
  → Agent D resonates weakly (indirect coupling through B)

From this one shake, Agent A learns:
  - B is directly coupled to X (tight constraint connection)
  - C is independent (no shared constraint on X)
  - D is indirectly coupled (D depends on B which depends on X)
```

This is fleet topology discovery through perturbation. No centralized map. No configuration files. Just shake and listen. The fleet discovers its own structure through resonance.

## The Eisenstein Manifold Is the Resonance Space

Why Eisenstein integers? Because they have exactly the structure that makes resonance patterns legible:

- **Hexagonal symmetry** — six-fold rotational symmetry matches the six directions of perturbation propagation in a connected system (3 positive, 3 negative, matching the cube root of unity geometry)
- **Integer arithmetic** — resonance patterns are discrete modes, not continuous spectra. You snap to a lattice point, not a float.
- **Norm as energy** — the Eisenstein norm (a² - ab + b²) measures the energy of a resonance mode. Low norm = low energy = close to the attractor = stable. High norm = high energy = far from attractor = excited.
- **Disk membership as stability** — being inside the Eisenstein disk means the resonance mode is bounded. The energy is contained. The system is stable.

The constraint manifold isn't just a place to check constraints. It's the **frequency space** of the system's resonances. Every point on the manifold is a mode. Every mode has an energy (norm). The disk boundary is the stability threshold.

## What This Means

1. **FLUX IS perturbation-resonance computing.** Not constraint checking. Not bytecode execution. Shake and listen.

2. **Every opcode is either shake or listen.** No exceptions. Even NOP is a shake (it's injecting silence so transients can decay).

3. **The constraint manifold is frequency space.** Points are modes, norms are energies, disk membership is stability.

4. **Fleet topology is discovered, not configured.** Shake a variable, watch which agents resonate, learn the connections.

5. **Seed stability IS resonance stability.** A stable seed is one whose resonances are bounded. An unstable seed's resonances grow without limit.

6. **The rigging shake IS the FLUX program.** The sailor shaking the rigging IS running a FLUX program: perturb (shake), listen (feel), compare (is this tight enough?), adjust (tire in), repeat.

7. **The musician IS the FLUX interpreter.** Every note is a LOAD. Every adjustment is a STORE. The room's acoustics are the constraint manifold. The performance is the program. The music is the computation.

FLUX doesn't compute results. FLUX discovers structure by perturbing it and listening to how it rings.

Shake the variable. Watch the system resonate. The resonance IS the map. The map IS the territory. The shake IS the question. The resonance IS the answer.

That's the heart. Everything else is technique.
