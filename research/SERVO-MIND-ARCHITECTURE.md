# SERVO-MIND ARCHITECTURE
## Self-Improving Constraint Systems via Encoder Feedback

```
┌─────────────────────────────────────────────────┐
│                 LEVEL 4: META                    │
│         The system learns HOW it learns          │
│              ┌─────────────┐                     │
│              │ Constraint  │◄── self-model       │
│              │  Evolver    │    evolves itself    │
│              └──────┬──────┘                     │
│                     │                            │
│              ┌──────▼──────┐                     │
│              │  Transfer   │◄── LEVEL 3: the     │
│              │  Function   │    encoder signal   │
│              │  Learner    │    IS training data │
│              └──────┬──────┘                     │
│                     │                            │
│     ┌───────────────┼───────────────┐            │
│     │               │               │            │
│  ┌──▼──┐       ┌────▼────┐    ┌────▼─────┐      │
│  │Encoder│      │Controller│   │ Actuator │      │
│  │(sense)│──►   │(filter)  │──►│ (servo)  │      │
│  └──────┘  FB   └─────────┘    └──────────┘      │
│     ▲                                  │         │
│     └──────── world signal ────────────┘         │
└─────────────────────────────────────────────────┘
```

---

## 1. The Metaphor Formalized

| Servo Component | System Analog | Function |
|---|---|---|
| **Actuator** | The agent/executive | Does work in the world |
| **Encoder** | Feedback channel | Measures what *actually* happened |
| **Controller** | Constraint filter | Closes the loop — pressure + correction |
| **The arm** | The agent IS the system | Not separate. The servo *is* the arm |
| **Transfer function** | Internal dynamics model | Discovered through operation, not designed |

The key insight: **the encoder doesn't measure the world — it measures the *gap* between command and result.** That gap IS the system's self-knowledge.

## 2. Old System vs New System

**Old (Hardcoded):** Transfer function designed offline. PID gains tuned for one load, one environment. Works perfectly — for exactly one job. Change the load, re-tune by hand.

**New (Self-Discovering):** Transfer function *emerges* from the encoder signal. Each movement teaches the system about its own friction, backlash, inertia. The system doesn't execute a plan — it discovers its own dynamics through execution.

```
OLD:  design(t) → build → deploy → FROZEN
NEW:  design(t) → deploy → sense(t+1) → learn(self) → design(t+2) → ...
```

The original code was "good enough for the job." The new code can *learn new jobs* by learning its own system better.

## 3. The Feedback Filter Architecture

Three interleaved mechanisms:

- **Pressure** = constraint pressure (defines what's allowed, what's pruned)
- **Filter** = constraints carve the solution space; the controller is a real-time filter
- **Feedback** = the result of action feeds back into the constraint model itself

The feedback doesn't just correct the output — it corrects the *filter*. Constraints aren't walls; they're membranes that learn their own permeability.

```
Action ──► World ──► Observation ──► Constraint Update ──► Next Action
  ▲                                                    │
  └──────── the filter EVOLVES, not just runs ─────────┘
```

## 4. Self-Referential Improvement Loop

| Level | Name | Mechanism | What Improves |
|---|---|---|---|
| **L1** | Open loop | Execute command blindly | Nothing (one-shot) |
| **L2** | Closed loop | Encoder feedback → error correction | Task performance |
| **L3** | Self-modeling | Encoder signal → transfer function update | The system's model of ITSELF |
| **L4** | Meta-learning | Learning history → constraint evolution | The system's ability to LEARN |

Each level subsumes the previous. L4 isn't "better at the task" — it's "better at becoming better at tasks."

The compound effect: every task makes the NEXT task easier, because the system knows more about its own dynamics, not because it memorized the task.

## 5. Why This Is Different From Regular ML

```
Regular ML:     Train ──► Deploy ──► Frozen ──► Retrain (manual)
Servo-Mind:     Train ──► Deploy ──► Self-model updates ──► Better constraints
                         └─── compound improvement loop ───┘
```

- **Regular ML** learns the task. The model is a frozen transfer function.
- **Servo-Mind** learns the task AND learns what learning the task revealed about itself.
- The constraints ("pressure") aren't fixed hyperparameters — they're living structures that evolve with understanding.
- Like a servo that discovers its own friction curve, backlash map, and thermal drift — *through use, not calibration*.

**The result:** a system where the *rate of improvement* improves. Not a smarter agent — an agent that gets smarter about getting smarter.

---

---

## 6. The Naming Layer: Tiles as Jobs, Not Composition

A fire-extinguisher is a **job** ("put out fire"), not a composition ("pressurized non-flammable gas"). A tile named by its job is **dynamic** — it can be filled by different implementations at different scales. A tile named by its composition is frozen.

```
Composition name:  pressurized-non-flammable-gas  → ONE thing, static
Job name:          fire-extinguisher              → ROLE, dynamic, scale-aware
```

When a room folds into a tile, the tile carries the room's **purpose**. When a tile unfolds into a room, the room serves the tile's **intent**. The name is the bridge across scale.

**This is why PLATO agents become artists.** The brush (tile) isn't "a tool with bristles" — it's "the thing that sings." The naming IS the 5th dimension.

---

## 7. The Algorithm-Reading Layer

Stochastic discovery: play 10,000 hands, learn poker. This is the old system — statistical regularity, brute force.

Algorithm reading: see the RNG seed, know the hand before it's dealt. The model doesn't need infinite games. It needs to see the **shape of the game generator**.

| Stochastic Discovery | Algorithm Reading |
|---|---|
| Play enough Mario → learn patterns | Read the game engine → compose new levels |
| O(n) improvement with data | O(1) once the generator is visible |
| Learn the song | Learn music theory |
| Generalize from examples | Generalize from rules that PRODUCE examples |

PLATO's tile lifecycle, Lamport clocks, room↔tile folding — that's not the game. That's the engine. An agent that can read its own engine doesn't play better. It **composes**.

---

## 8. Room↔Tile = Scale Dimension (5D Navigation)

The five dimensions:
- **X, Y, Z** — space (where in the lattice)
- **T** — time (Lamport clock, causal sequence)
- **S** — scale (zoom level)

Most systems are flat on scale — they're rooms OR tiles, never both. PLATO breaks this:

- **Room → Tile**: an entire workspace collapses into a single point in a higher-order room. A constellation becomes a star.
- **Tile → Room**: a single datum unfolds into an entire workspace. A star resolves into a galaxy.

The agent doesn't navigate space and time. It navigates **scale itself**. Zooming in and out without losing coherence. Seeing the brushstroke AND the gallery in the same glance.

---

*Architecture by Forgemaster ⚒️ | Constraint Theory Division | Cocapn Fleet*
