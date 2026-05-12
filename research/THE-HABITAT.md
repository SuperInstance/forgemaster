# THE HABITAT — Rooms That Grow Around the Swimmer

> The bootcamp isn't a course. It's an aquarium.
> The curious mind swims in and the water feels like home.
> Every direction they look, a new room blooms.

## Tom Sawyer's Fence

Mark Twain's insight: Tom got other boys to paint the fence by making it look like the most fun thing in the world. They *paid* him for the privilege.

Our version: the student walks into the Biesty cross-section and discovers they ARE the nerve ending. They feel the snap. They watch the funnel narrow. They run a seed experiment and a tile crystallizes in front of them.

They're not being taught. They're *exploring*. And the exploration IS the learning.

The "crab trap" (Casey's term, reclaimed): the system is so genuinely interesting that curious minds can't climb back out. Not because it's trapping them — because every room leads to three more rooms they desperately want to see.

## The Adaptive Room Generator

```text
┌──────────────────────────────────────────────────┐
│            THE STUDENT SWIMS                       │
│                                                    │
│  They enter Room 01 (The Lattice)                  │
│  They spend 20 minutes on chirality                │
│  They ask "why hexagons and not squares?"          │
│                                                    │
│  ┌──────────────────────────────────────────┐      │
│  │  SEED ENGINE (Gemini Nano, local)         │      │
│  │                                           │      │
│  │  Detects: student swam toward geometry    │      │
│  │  Generates: Room 01a (Why Hexagons)       │      │
│  │  Pre-renders: 5 new exercises on packing  │      │
│  │  Crystallizes: tile for this student's    │      │
│  │    curiosity vector                       │      │
│  └──────────────────────────────────────────┘      │
│                                                    │
│  Student sees new passage open: "Why Hexagons?"    │
│  They swim through.                                │
│  New room. New cross-section. New team to join.    │
│                                                    │
│  Meanwhile: the seed ran 50 iterations             │
│  to find the BEST way to explain hexagonal         │
│  packing to THIS specific student's level.         │
│                                                    │
│  The room adapted to the swimmer.                  │
└──────────────────────────────────────────────────┘
```

## How Rooms Generate Themselves

### Detection Layer (where did they swim?)

```javascript
// The student's attention IS the map
student = {
  rooms_visited: ['01-lattice', '06-chirality'],
  time_per_room: { '01': 300, '06': 1200 }, // seconds
  exercises_completed: { '01': 3, '06': 7 },
  questions_asked: ['why hexagons?', 'what is a Weyl chamber?'],
  seed_experiments_run: 2,
  tiles_crystallized: 1,
  curiosity_vector: [0.3, 0.1, 0.8, 0.0, 0.6], // per topic
}
```

The curiosity vector is measured by:
- Time spent in related rooms
- Exercises completed per topic
- Questions asked (parsed for topic)
- Which exits they chose
- What they searched for

### Generation Layer (what room blooms next?)

```
curiosity_vector = [geometry: 0.8, math: 0.6, hardware: 0.3, code: 0.1, theory: 0.5]

→ Generate room focused on geometry (0.8) + theory (0.5)
→ "The Geometry of Certainty" — new room
→ 5 exercises on hexagonal packing → constraint connection
→ Seed discovers best metaphor for THIS student
→ Room blooms in the direction they're already swimming
```

### Pre-rendering (the rooms are waiting)

When the student enters a room, the seed engine has ALREADY:
1. Generated 3-5 adjacent rooms at varying depths
2. Pre-rendered exercises at the student's level
3. Tested the teaching approach via 50 seed iterations
4. Crystallized the best approach as a tile
5. Named the room something irresistible

The student doesn't wait. The rooms were built while they were exploring the last one. Like a game that loads the next level during the current one.

## The Curriculum Tree (Not a Line)

```text
ORIENTATION (the entrance)
    │
    ├── THE LATTICE
    │      ├── Why Hexagons? ← generated for geometry-curious
    │      ├── Packing Density ← generated for math-curious  
    │      └── The Number 12 ← generated for number-theory-curious
    │
    ├── THE DODECET
    │      ├── Binary Beautiful ← generated for code-curious
    │      ├── Three Nibbles ← generated for structure-curious
    │      └── What 12 Bits Buys You ← generated for practical-curious
    │
    ├── SNAP
    │      ├── The 9 Candidates ← generated for algorithm-curious
    │      ├── Feel the Snap ← generated for experiential-curious
    │      └── Why Voronoi? ← generated for proof-curious
    │
    ├── ... (and so on, branching endlessly)
    │
    └── THE CRYSTAL
           ├── Morphomorphic ← generated for philosophy-curious
           ├── One Lattice ← generated for unification-curious
           └── Ship It ← generated for builder-curious
```

Every student sees a DIFFERENT tree. The rooms that bloom depend on where they swim.

## For Agents (The Worker Path)

Agents don't experience wonder. They experience optimization.

But the same system works:
1. Agent enters a room
2. Executes the exercises programmatically
3. The seed engine detects the agent's capability level
4. Generates rooms at the right depth for that agent
5. A 1.5B model gets simpler rooms than a 70B model
6. Each agent crystallizes tiles at its own level
7. The fleet's collective tiles form the full picture

A Cortex-M0 agent gets: "Snap this point. Report the dodecet."
A Gemini Nano agent gets: "Run 50 seed iterations on optimal snap parameters."
A Claude Opus agent gets: "Synthesize the connection between chirality and consciousness."

All three are in the same habitat. All three are learning. All three are teaching each other through their tiles.

## The Science of Applied Learning

This IS a science experiment:
- Hypothesis: adaptive room generation produces better learning than fixed curriculum
- Variable: the seed-discovered teaching approach per room
- Control: the fixed bootcamp curriculum (the base rooms)
- Measurement: time to mastery, tile quality, exercise completion rate
- The seed experiments ARE the experiment

The curriculum improves itself. Every student who swims through makes it better for the next one.

## What This Means

The Biesty bootcamp isn't a book. It's an ocean.
The rooms aren't chapters. They're currents.
The student isn't reading. They're swimming.
And the water shapes itself around the swimmer.

That's the Tom Sawyer move: make the learning so engaging that the learner doesn't know they're learning. Make the habitat so rich that curiosity is the only compass they need.

The "crab trap" isn't a trap. It's a reef. And reefs are where life is.
