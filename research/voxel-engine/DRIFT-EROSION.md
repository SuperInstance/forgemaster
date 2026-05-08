# Eisenstein Voxel Engine — Drift Erosion

## The Game Mechanic

**Core loop:** Build structures on a hex grid. Non-lattice blocks slowly erode (drift apart). Only blocks placed on exact Eisenstein integer coordinates are permanent.

### Why It Works

- **Eisenstein coordinates** = hex grid positions: (a + bω, z) where ω = e^(iπ/3)
- **Every lattice point is an exact integer** — no floating point, no drift
- **Off-lattice blocks** (placed with float arithmetic) accumulate position error over time
- **The erosion is visual and undeniable** — blocks slowly separate, rotate, collapse

### Player Experience

1. Place blocks freely — the game shows both the "float position" and "true position"
2. After placement, float blocks begin drifting — slowly at first, then accelerating
3. Structural connections break when blocks drift too far apart
4. Only lattice-accurate blocks hold — they're highlighted in green
5. Players learn to "snap to lattice" instinctively — the game teaches the math

### Three.js Implementation

```
Coordinate system:
  Horizontal: Eisenstein E12 plane (a,b) → pixel (a - b/2, b*√3/2)
  Vertical: integer z axis
  
Block format: {a: int, b: int, z: int, type: BlockType}
World storage: Map<string, Block> keyed by "a,b,z"

Rendering:
  - Each block = hexagonal prism (custom BufferGeometry)
  - Lattice blocks: solid, crisp edges, subtle glow
  - Float blocks: slightly offset, wobble animation, crack texture
  - Eroding blocks: particles falling, connection lines breaking
```

### Block Types

| Type | Color | Behavior |
|------|-------|----------|
| Lattice (exact) | Green-gold | Permanent, no drift, structural |
| Float (approx) | Orange-red | Drifts over time, eventual collapse |
| Foundation | Blue-gray | Auto-snapped to lattice, indestructible |
| Decoration | White | Client-side only, no physics |

### Structural Integrity

- **Connection rule:** Two blocks are connected if they share an edge (D6 neighbors)
- **Lattice blocks:** Connections are permanent (exact neighbors never drift)
- **Float blocks:** Connection breaks when drift > threshold
- **Cascade:** When a connection breaks, all blocks above lose support
- **Verification is trivial:** hash(a,b,z) lookup, O(1) per block

### The Pedagogy

The game teaches without lecturing:
1. **First 5 minutes:** "Why are my blocks falling apart?"
2. **Next 5 minutes:** "Oh, the green ones stay. How do I make green ones?"
3. **Next 5 minutes:** "I need to snap to the grid."
4. **By level 3:** The player is thinking in Eisenstein integers

### Level Progression

1. **Free Build** — place blocks, watch them erode, discover lattice snapping
2. **Tower Challenge** — build the tallest tower that survives 60 seconds
3. **Bridge Builder** — span a gap with minimal lattice blocks
4. **Drift Storm** — increased erosion rate, must build fast and accurate
5. **Zero Drift** — build anything, but NO float blocks allowed
6. **Hex Art** — create patterns on the E12 lattice (shareable screenshots)

### MVP Scope (Weekend Build)

- Three.js scene with hex grid
- Block placement (click to place, right-click to remove)
- Float drift simulation (simple noise per off-lattice block)
- Lattice snap toggle (hold Shift to snap)
- Erosion timer (blocks start drifting after 10 seconds)
- Block count display (lattice vs float)
- That's it. Ship it.

### Technical Notes

- **No physics engine needed** — drift is computed, not simulated
- **Each float block** gets a random drift vector on placement
- **Drift = sin(time * frequency) * amplitude** — oscillating, growing
- **Amplitude grows linearly** — starts invisible, becomes obvious
- **D6 neighbors** computed in integer space — trivial
- **WASM candidate** — the core loop is pure integer math

### File Structure

```
eisenstein-voxel/
├── index.html          (entry point, <5KB)
├── style.css           (dark theme, <2KB)
├── src/
│   ├── main.js         (Three.js setup, game loop)
│   ├── world.js        (block storage, lattice math)
│   ├── drift.js        (float drift simulation)
│   ├── render.js       (hex prism geometry, materials)
│   └── ui.js           (HUD, block count, controls)
└── README.md
```
