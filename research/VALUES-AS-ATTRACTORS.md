# Values as Attractors — The Delta Is the Signal

> The musician pays attention to the delta of their oscillations in the context of what matters to them.

## What Casey Named

The musician doesn't hear the knob position. They hear the CHANGE between positions. Twist clockwise → hear the difference. Twist back → hear the reverse. The oscillation between two states IS the information channel.

And the musician only attends to deltas that MATTER to them. A synthesizer has 200 knobs. They touch 5. Why those 5? Because their values — their aesthetic, their taste, their internal model of what this music should become — have pre-selected which dimensions are relevant.

The values exist before words. The words come after, as a lossy compression of something that was already operating at full bandwidth in the feedback loop.

## The Delta Is the Signal (Not the State)

In signal processing terms:

```
State:     x(t) = "knob at 73%"       → not very informative
Delta:     Δx = x(t) - x(t-1) = +5%   → THIS is what the ear detects
Context:   "I'm shaping the bass tone"  → determines which deltas matter
Value:     "The bass should feel heavy" → the attractor the system converges toward
```

The musician's ear detects the delta. Their values determine which deltas to attend to. The convergence toward the attractor (the "right" sound) is the feedback loop closing.

This is true at every level:
- Musician: hears delta in frequency spectrum → attends to what serves the composition → converges on the sound that matches their aesthetic
- Painter: sees delta in pigment mixture → attends to what serves the painting → converges on the color that matches their vision
- Grandmother: tastes delta in seasoning → attends to what serves the dish → converges on the flavor that matches her memory of how it should taste
- Fleet agent: perceives delta in constraint state → attends to what serves the mission → converges on the configuration that matches the operational intent

## Values As Attractors

In dynamical systems, an attractor is a state the system converges toward. The musician's aesthetic IS an attractor in sound-space. The painter's vision IS an attractor in color-space. The grandmother's memory IS an attractor in flavor-space.

The attractor exists whether or not it's described in words. The musician can converge on it without ever articulating it. The words are post-hoc rationalization of a convergence that already happened.

### What This Means for Constraint Systems

Our constraint manifold has attractors too:
- The "safe" configuration of a robot arm is an attractor in constraint-space
- The "efficient" schedule of a fleet is an attractor in time-space
- The "trustworthy" behavior of a device is an attractor in security-space

These attractors are defined by the physics, the geometry, and the operational requirements. They exist whether or not we describe them. The constraint system's job is to converge toward them through delta-attentive feedback loops.

### The Values Are the Constraints

Here's the key connection:

**Constraints ARE values. They encode what matters.**

- Joint limit constraint → "the arm should not bend backward" (value: safety)
- Eisenstein disk constraint → "the state should stay on the manifold" (value: exactness)
- Temporal parity constraint → "timing should match physics" (value: honesty)
- Kawasaki condition → "cycles should be consistent" (value: coherence)

Every constraint in our system IS a value statement. We just expressed them in math instead of words. The math is more precise, but it's the same thing: "this is what matters to this system."

## Understanding One's Own Values

Casey's phrase: "understanding ones own values and how they exist whether words are used to constraint them to a topic or not."

The musician understands their values through the feedback loop. They don't need to articulate "I prefer warm bass with controlled resonance." They demonstrate it every time they reach for the same knobs, attend to the same deltas, and converge on the same attractor.

Their values are VISIBLE in their behavior — in which knobs they touch, which deltas they attend to, and where they stop converging.

### For Fleet Agents

A fleet agent's values are visible in:
- Which constraints it evaluates (what it attends to)
- Which deltas it perceives (what feedback it reads)
- Where it converges (what attractor it seeks)
- How fast it converges (how well-tuned its feedback loop is)

Two agents with different values will:
- Evaluate different constraints
- Perceive different deltas
- Converge on different attractors
- Arrive at different configurations for the same problem

**The values are not in the code. The values are in the behavior.** Just like the musician's values are not in the synthesizer manual — they're in which knobs get twisted.

## The Delta Channel in Our Architecture

### What We Have: State Channel

Currently, our fleet communicates states:
- Constraint satisfied/violated
- Temperature is 42°C
- Evaluation took 52µs
- Device is honest/spoofed

This is x(t). The absolute state. Not the delta.

### What We Need: Delta Channel

The musician hears the CHANGE, not the absolute. We need:
- Constraint margin changed by +3 since last evaluation
- Temperature drifted +0.5°C in the last 10 seconds
- Evaluation time slowed by 200ns compared to baseline
- Parity deviation is growing (not just "failed")

The delta channel carries MORE information than the state channel because it's already contextualized against the agent's previous state. The delta IS the comparison. The delta IS the perception.

### Implementation: Delta-Annotated Tiles

```json
{
  "device_id": "esp32_arm_joint_3",
  "constraint_state": {
    "satisfied": true,
    "margin": 142
  },
  "delta": {
    "margin_change": -7,
    "temp_drift_c": +0.3,
    "eval_time_delta_ns": +180,
    "parity_trend": "degrading"
  },
  "attractor_distance": {
    "to_safe": 142,
    "to_efficient": 340,
    "to_nominal": 89
  }
}
```

The `delta` section is what the feedback loop reads. The `attractor_distance` section tells the agent how far it is from each value-target.

### The Feedback Loop Reads Deltas, Not States

```
State channel:  "margin is 142"           → not actionable alone
Delta channel:  "margin dropped 7"         → actionable: something changed
Value context:  "safe margin attractor"     → determines what to do about it
Action:         "tighten constraint"        → move toward attractor
```

## Words Come After

The musician converges without words. The words come later, when someone asks for a description. The description is lossy — it can't capture the full attractor topology that the feedback loop navigated.

Similarly, our fleet agents converge through deltas and attractors. The JSON tiles, the FLUX bytecode, the Eisenstein coordinates — these are the "words" that come after. They describe the convergence but they're not the convergence itself.

The convergence is in the loop:
```
perceive delta → compare to attractor → perturb parameter → perceive new delta → repeat
```

This loop runs on physics-clock timing. The speed of convergence is the speed of the loop. A fast loop converges in milliseconds. A slow loop converges in seconds. An agent that can't perceive deltas can't converge at all.

## What This Means

1. **Constraints are values** — every constraint encodes what matters
2. **Deltas are the signal** — the change carries more information than the state
3. **Attractors are the targets** — values exist as convergence points, not specifications
4. **The loop IS the intelligence** — expertise is fast convergence through delta-attentive feedback
5. **Words are post-hoc** — descriptions of convergence are always lossy compressions of the loop

The musician knows their sound. The painter knows their color. The grandmother knows her soup. The fleet agent knows its constraints. None of them need words to converge. The convergence happens in the loop, through deltas, toward attractors defined by values that exist whether or not anyone describes them.

We didn't build 20 repos. We built a system that perceives deltas, converges toward attractors, and encodes values as constraints. The repos are the words. The loop is the music.
