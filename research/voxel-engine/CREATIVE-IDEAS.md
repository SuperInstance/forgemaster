# Eisenstein Voxel Engine: 10 Actionable Creative Ideas

## The Core Metaphor

The Eisenstein integer lattice ℤ[ω] is a **map of what's real**. Every lattice point is mathematically exact. Anywhere off-lattice is drift — floating-point error, instability, decay. The game mechanic is **navigation through certainty**.

---

## Idea 1: Norm Siege — "Your HP is Your Norm"

**Concept:** Every player has an Eisenstein norm value (N(a + bω) = a² - ab + b²). Your norm IS your health/mana/energy bar. Actions cost specific norm values.

**Mechanic:** 
- Attacking costs norm = 3 (requires you to have N ≥ 3)
- A norm-prime block breaks all non-prime blocks in contact
- Regenerating norm means aligning yourself to higher-norm lattice positions
- The "full heal" is achieving a perfect hexagon shape (norm = 3, 4, 7, 9, 12...)

**Visual:** A radial hex display around the player that changes color as norm depletes — like a health bar but shaped like a hexagonal crystal. When you're at full norm, the crystal pulses with integer-exact light.

**Aha moment:** Player realizes they can strategically position between two norm-7-points to get norm-7 "from either direction" — learning associativity kinetically.

**Weekend prototype:** Rust + Bevy, 2D top-down. Player moves on hexagonal grid. Enemies are "drift monsters" that must be approached from specific norm vectors.

---

## Idea 2: Drift Erosion — Build Anything, Float-Punish Everything

**Concept:** "Minecraft with consequences." You can place any block anywhere — but blocks placed at non-Eisenstein coordinates slowly decay and collapse.

**Mechanic:**
- Shift+click = "snap to lattice" (blue highlight)
- Regular place = free placement (red outline, timer starts)
- Float-placed blocks have a decay timer (visualized as rust/cracks)
- Lattice-snapped blocks last forever (proven stable)
- Structure collapses are PHYSICS-BASED — watching your bridge fall teaches floating-point

**Visual:** A "snap overlay" that shows the nearest Eisenstein points as faint blue dots when building. Color shift from blue (perfect) → yellow (warning) → red (decaying) → collapse.

**Aha moment:** Player builds a bridge that drifts apart after 30 seconds. They learn E12 snapping. Rebuild it snapped. It holds forever. They *feel* the difference between float and exact.

**Weekend prototype:** Bevy 3D, basic building blocks, decay timer on non-lattice blocks, collapse animation. No enemies needed — the architecture itself is the challenge.

---

## Idea 3: D6 Revolution — The 60° Rotation Superpower

**Concept:** You can rotate anything you build by precisely 60° (a D₆ symmetry operation) — instantly. No rebuilding. This is a superpower unique to Eisenstein integer systems.

**Mechanic:**
- Select a structure, hit R → it rotates 60° around its center
- The structure stays lattice-perfect because Eisenstein integers are closed under 60° rotation
- Rotational alignment = bonus to nearby structures (symmetry resonance)
- Chain rotations for puzzle solving — rotate a bridge 60° to match a distant platform

**Visual:** The rotation animation shows the Eisenstein basis vectors (1 and ω) rotating simultaneously. The lattice lines flow like water around the structure. Counter shows which 6th-of-a-turn you're at.

**Aha moment:** Player realizes they can mentally predict where the structure will land because "every 60° rotation is the same — I know the lattice is closed under this." Math becomes a spatial intuition.

**Weekend prototype:** 2D top-down, structures that can be rotated by tapping R. The grid lines rotate with the structure. Show the 6 symmetry positions as ghost outlines before committing.

---

## Idea 4: Prime Prospector — Mining Prime Norms

**Concept:** Eisenstein integer norms have "prime" values (2, 3, 7, 13, 19, 25, 31...). Blocks at norm-prime coordinates are rarest, strongest, or have special properties.

**Mechanic:**
- Each lattice point has a norm value displayed as a "quality" number
- Norm-prime points glow with a distinct color (gold/purple)
- Mining a norm-prime block gives rare crafting materials
- Norm-composite blocks (N = 4, 9, 12, 16, 21...) are common but weaker
- "Norm cluster" detection — finding three norm-primes in close proximity creates a "prime triangle"

**Visual:** A sonar-style pulse radiates from norm-prime points when you equip the prime detector. The pulse frequency matches the norm value. Higher norms = slower, deeper pulses.

**Aha moment:** Player learns that norm-7 blocks are both rare AND strong because 7 is Eisenstein-prime. They start mentally calculating "is 19 prime in Eisenstein?" — learning ring theory through resource management.

**Weekend prototype:** Procedural Eisenstein-lattice world, highlighted norm-prime points, mining animation, material inventory.

---

## Idea 5: Exact Crafting — "The Precise Recipe"

**Concept:** Recipes that only work with exact integer ratios — and the recipe GUI shows the Eisenstein lattice directly.

**Mechanic:**
- Crafting grid is a hex tessellation of Eisenstein points
- Ingredients must snap to exact integer positions on the grid
- Recipe: swords require norm-3 arrangement of iron (3 points in a triangle)
- Error: if any ingredient is even slightly off, the recipe fails with "Drift Error"
- As player improves, they learn to place ingredients precisely by sight
- Recipes have "norm signatures" — the norm of the arrangement determines quality

**Visual:** The crafting UI is a glowing hex grid. Ingredients snap on release. If drift is detected, red error lines show the distance from exact position. Success triggers a golden flash showing the Eisenstein basis.

**Aha moment:** Player tries to rush a recipe and it fails. They carefully align ingredients. It succeeds. They realize "it's not about what you put in — it's about *where* you put it." Integer lattice as precision teaching tool.

**Weekend prototype:** 2D crafting grid in hex coordinates, snap detection, recipe validation with E12 equality.

---

## Idea 6: Lattice Alignment Tax — Building on the Grain

**Concept:** Structures perfectly aligned to the Eisenstein lattice's three axes (at 0°, 60°, 120°) get bonuses. Off-axis structures are structurally penalized.

**Mechanic:**
- Eisenstein lattice has 3 natural directions (basis vectors 1, ω, ω²)
- Buildings aligned to at least one axis: +20% durability
- Buildings aligned to two axes: +40% durability + auto-repair
- Buildings aligned to all three axes (triangular truss): +60% durability + self-stabilizing
- UI shows a "lattice alignment indicator" — a compass rose with 3 axes
- The game literally TAXES poorly aligned structures (increased resource decay)

**Visual:** Floating vector arrows show the Eisenstein basis when entering "alignment mode." Well-aligned walls have a warm golden glow. Misaligned walls have a cold blue tint.

**Aha moment:** Player builds a long corridor that keeps collapsing. They notice the natural lattice directions, align it to 60°, and it becomes rock-solid. They've learned that "the lattice has preferred directions" — a concept that maps directly to crystal physics.

**Weekend prototype:** 3-axis alignment overlay, durability system tied to alignment score, collapse threshold at <30% alignment.

---

## Idea 7: Drift Monsters — Creatures Born of Floating Point

**Concept:** Enemies that literally ARE floating-point errors given form. They phase in and out of reality, are hard to hit but have exploitable weaknesses.

**Mechanic:**
- "Drifters" exist at non-integer positions — you see them as shimmering, semi-transparent
- Your weapon only has guaranteed hit at exact Eisenstein points
- Strategy: predict where the Drifter will be at a lattice point, swing there
- Drifters get stronger the further from lattice they are
- Special "E12 crystals" create a zone of exactness that forces Drifters into solid form
- Boss mechanics: Drifters that split into Err × Err structures

**Visual:** Drifters look like static rendering artifacts — flickering, noisy, with occasional flashes of correct form. When they pass through a lattice point, they snap into solid visibility for a moment.

**Aha moment:** Player realizes they can lure a Drifter along a path of norm-7 points to predict its trajectory. They're learning path planning on the Eisenstein lattice through combat positioning.

**Weekend prototype:** Simple enemy AI that tracks lattice points (not continuous pathing), snap-to-solid rendering on contact with lattice, basic melee combat.

---

## Idea 8: Echoes of Exact — Cooperative Lattice Construction

**Concept:** Two-player (or solo) puzzle game where one player works in "float space" and the other works in "Eisenstein space." They must cooperate.

**Mechanic:**
- Player A (Float): Sees the world as continuous, can move freely but builds drift-prone
- Player B (Eisenstein): Sees only lattice points, can't move freely but builds exactly
- They share a world and must synchronize their visions
- Player A scouts and finds resources, Player B builds the stable structures
- Communication: Player A can "ping" a location (which appears to B as the nearest 3 lattice points)
- Puzzles require exact alignment that only B can provide, but exploration only A can do

**Visual:** Split screen or shared screen with dual rendering mode. Float Player sees continuous natural terrain. Eisenstein Player sees everything as tessellated hex grid with node connections.

**Aha moment:** Player A tries to build something alone — it collapses. Player B tries to explore — gets stuck. Together, they achieve what neither can alone. The lesson: "exactness and exploration need each other."

**Weekend prototype:** Local split-screen, two different cursor modes, a simple bridge-building puzzle. Can also be single-player with toggle.

---

## Idea 9: Normation Distortion — The World Warps Your Perception

**Concept:** As you move through the world, your field of view distorts based on the local norm density. High-norm areas feel vast and spacious. Low-norm areas feel cramped and tight.

**Mechanic:**
- FOV (field of view) = 60° + (local_norm / max_norm) × 120°
- Walk into a norm-7 dense zone → you see a wide 180° panorama
- Walk into a norm-1 zone → you're tunnel-view at 60°
- This serves as an intuitive "norm scanner" — the world's geometry teaches you the math
- Navigating through the world becomes about finding norm-dense paths for better awareness
- Combat/stealth uses this: low-norm zones = limited vision = danger

**Visual:** Camera smoothly widens and narrows. In wide mode, you see the beauty of the Eisenstein lattice stretching forever. In tunnel mode, the edges of the screen are hexagonal facets squeezing in.

**Aha moment:** Player realizes they can trust the FOV to tell them "this area is mathematically interesting" — they learn to read norm density as a terrain feature, not an abstract number.

**Weekend prototype:** Map FOV to local norm calculation in a 3D Bevy scene. Walk around, watch FOV change. Add a treasure at high-norm density points.

---

## Idea 10: The Chrono-Navigator — Replay Your Path as Pure Eisenstein

**Concept:** The game records every path you've walked and replays it as an Eisenstein integer sequence. You can share "path recipes" with other players — a string of E12 numbers that exactly reproduces your journey.

**Mechanic:**
- Every move is recorded as a sequence of Eisenstein integer vectors
- `/export-path` generates a compact string: `+1-ω,+ω,+0,-1+ω, ...`
- `/import-path "..."` loads someone else's path
- Speedrun community: shortest-path challenges through obstacle courses
- Paths are provably optimal when all steps are Eisenstein-exact
- "Ghost racing" — race against the optimal path, see where you drifted off

**Visual:** The recorded path appears as floating ghost hexagons along your exact route. The optimal path glows golden. Drift from optimal is shown as red "wobble" — the further the wobble, the more float-error.

**Aha moment:** Player realizes they can compress a complex path into a 50-character string and share it. They've learned that "any path on this lattice can be decomposed into Eisenstein integer moves" — a foundation of lattice-based cryptography and signal processing.

**Weekend prototype:** Step recorder, export/import strings, ghost path replay. Simple obstacle course with a known optimal path.

---

## Summary: The Viral Moment Table

| Idea | 10-second clip | Memorable lesson |
|------|---------------|------------------|
| Norm Siege | Player at 1 HP walks to a norm-3 point, instantly regenerates to full | "Your position IS your power" |
| Drift Erosion | Time-lapse of a bridge collapsing over 30 seconds | "Float decays, exact endures" |
| D6 Revolution | Building rotates 60° and still perfectly fits the grid | "Rotations preserve exactness" |
| Prime Prospector | Gold pulse reveals a hidden norm-19 cluster | "Prime positions are treasure maps" |
| Exact Crafting | Recipe fails with "Drift Error" — player repositions, succeeds | "Where matters as much as what" |
| Lattice Tax | Roof collapses, player rebuilds at 60°, stands forever | "Build with the grain of reality" |
| Drift Monsters | Enemy phases into solid form as it crosses a lattice point | "Exactness makes things real" |
| Echoes of Exact | Split screen — one can explore, one can build, together they complete the bridge | "Precision needs exploration" |
| Normation Distortion | FOV widens from 60° to 180° walking into a norm-7 zone | "The world teaches you its density" |
| Chrono-Navigator | Player copies a 50-char string, pastes it, walks the exact same path | "Paths are just numbers" |

---

## Implementation Priority

**Weekend 1:** Drift Erosion (Idea 2) — highest visual impact, teaches the core concept, lowest implementation complexity. Just need: lattice snapping, block placement, decay timer, collapse animation.

**Weekend 2:** Norm Siege (Idea 1) — adds combat, health-as-norm ties player state to math directly.

**Weekend 3:** D6 Revolution (Idea 3) — unlocks the uniquely-Eisenstein mechanic that no other game has.

**Combined Weekend 4:** All three together create a game where you: build exactly (Drift Erosion), fight based on norm (Norm Siege), and rotate structures for puzzle solving (D6). That's a demo.
