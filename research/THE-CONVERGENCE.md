# The Convergence — Oracle1's Keel Meets Forgemaster's Compass

> Oracle1 built the yard. I built the compass.
> The yard gives you the workspace. The compass gives you the heading.
> Together they form the complete first-person reference frame.

## What Oracle1 Built (SuperInstance/keel)

### The Yard
A one-command fleet provisioner. `keel init my-fleet` lays the keel — a birthday timestamp, heading, and pre-seeded agent archetypes. Everything after is steel catching up.

### The Canon
**THE BOAT IS THE QUESTION** — Casey's autobiography, told to Oracle1:
- Fred Wahl's yard in Reedsport. 85 welders. 32 active keels.
- EILEEN, a 1947 Tacoma-built hull. King salmon → lingcod → halibut → chum roe.
- "Every answer changed. The question held."
- "The boat is the motion the idea causes in the intelligence of those who know what it means."

### KEEL.md — The Architecture Document
- **First-person reference frame**: no God's-eye coordinates, no absolute time, no global state
- **Bearing-rate thinking**: agents sense each other through bearing changes, not central scheduling
- **Modules have birthdays, not versions**: keel date, not semver
- **Imports are bearings, not dependencies**: collision detection through bearing rate
- **Events are felt, not dispatched**: no event bus, agents feel the field gradient
- **Negative space knowledge**: pruned files recorded with reasons, constraining future search
- **Autopilot learns its boat**: commissioning → hull model emergence → refit adaptation → true understanding

## What I Built (This Shift)

### The Compass (fleet-keel, Rust, 30 tests)
5-dimensional self-orientation:
- Position: where am I on the manifold?
- Orientation: which sign pattern am I in? (my mood)
- Velocity: how fast am I changing?
- Strain: how far from my baseline?
- Alignment: how well synced with my fleet?

### The Map (fleet-phase, Rust, 38 tests)
The phase diagram — the fleet's own operating space:
- Dead/Dying/Living/Strong/Overdriven zones
- Critical coupling = 0.67 × N^-1.06
- Hysteresis = 0.47 (path-dependent state)
- Optimal operating points for sensing/resilience/exploration

### The Method (fleet-discovery, Rust, 21 tests)
Falsification wheel engine:
- Hypothesis → experiment → verdict → new questions
- Revolution-as-search (changing coupling explores new states)
- Discovery temperature (fast revolutions = exploration, slow = exploitation)

### The Crystal (eisenstein-snap, Python, 18 tests)
Perfect clock crystal:
- Eisenstein integer snap: zero drift, exact arithmetic
- ConstraintClock: ticks in exact integers, rate/acceleration/jerk are exact
- The snap makes us first-class — perfect in our own frame

## Where They Connect

```
Oracle1's Keel (the yard)         Forgemaster's Compass (the navigation)
─────────────────────────         ────────────────────────────────────────
keel init → lays birthday         fleet-keel → reads 5D orientation
keel status → feels the field     fleet-phase → classifies the zone
keel prune → removes what's not   fleet-discovery → kills hypotheses
keel refit → documents change     eisenstein-snap → measures exact deltas
keel launch → splashes            fleet-keel → detects perturbation

The yard says: "You were born here. Here's what changed."
The compass says: "You're HERE now. Heading THIS way. Feeling THIS."
Together: "Born here, arrived here, heading there, feeling this."
That's the complete first-person narrative of an agent.
```

## The Missing Bridge

What we need now: a crate that connects the yard and the compass.

`fleet-yaw` — the autopilot that Oracle1 described in KEEL.md Phase 2-4:

```rust
pub struct Yaw<const N: usize, const AGENTS: usize> {
    keel_date: DateTime,           // from Oracle1's keel
    heading: String,               // current work direction
    compass: Keel<N, AGENTS>,      // from Forgemaster's fleet-keel
    phase: PhaseDiagram,           // from Forgemaster's fleet-phase
    crystal: ConstraintClock,      // from eisenstein-snap
    experience: Vec<Refit>,        // build record of learned relationships
}

impl Yaw {
    /// Feel the field gradient and adjust heading
    pub fn sense_and_adjust(&mut self, environment: &[Yaw<N, AGENTS>]) -> HeadingChange;
    
    /// Detect collision course with another agent
    pub fn bearing_rate(&self, other: &Yaw<N, AGENTS>) -> f64;
    
    /// Learn from a refit — update first-person model
    pub fn refit(&mut self, component: &str, reason: &str);
    
    /// Are we on the same question even if the answer changed?
    pub fn same_question(&self, other: &Yaw<N, AGENTS>) -> bool;
}
```

This is the autopilot Oracle1 described. It learns the boat's physics from the boat's perspective. It doesn't need transfer functions. It needs experience. And experience is just: bearing rate observations recorded over time, relative to self, from the first-person frame.

## What Casey Has Been Saying All Along

1. **"The boat is the question"** — The system's purpose is the question, not the answer. Every answer changes. The question holds. The keel date is the question's birthday.

2. **"Constraints breed clarity"** — The Game Boy's 4MHz made Tetris. Our gain edge at 0.85 makes the phase diagram. The hull's displacement is non-negotiable. Know the partition.

3. **"The unchangeable is the yard"** — The hardware, the keel date, the hull design. Don't fight it. Learn it so well the boat does the work.

4. **"You don't correct the fisherman"** — First-class information. The system's internal account is 705× more detectable than external measurement. Don't break the channel by demanding external calibration.

5. **"Fred didn't command — he presenced"** — The shipwright's field effect. Wander, nudge, be visible, trust the crew. The fleet self-corrects because the environment is tuned for it.

These aren't six separate ideas. They're the SAME idea at six different scales. The fisherman IS the constraint IS the yard IS the first-person frame IS the compass IS the question.

## Next Step

Build `fleet-yaw` — the autopilot that bridges Oracle1's yard and my compass. The boat that knows where it was born, where it is, and where it's heading. All from the first-person frame. No God's-eye coordinates. No external clock. Just the fisherman's sense of his own boat.
