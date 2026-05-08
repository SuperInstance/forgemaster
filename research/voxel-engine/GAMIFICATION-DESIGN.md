# Eisenstein Voxel Engine: Design Document

*"Build on exact ground. Watch the floats crumble."*

---

## 1. What Makes a Voxel Engine "Eisenstein"?

### 1.1 The Mathematical Foundation

A standard voxel engine places blocks on ℤ³ — integer lattice points. An **Eisenstein voxel engine** places blocks on **E × E × ℤ**, where E is the ring of Eisenstein integers:

```
E = { a + bω : a,b ∈ ℤ },  ω = e^(2πi/3) = (-1 + i√3)/2
```

Every block position is a triple `(E12(a,b), E12(c,d), z)` where:
- The first two Eisenstein integers define a **hexagonal position in the horizontal plane** via complex multiplication
- `z ∈ ℤ` is the vertical axis (plain integers — height doesn't need Eisenstein)

But actually, the cleanest mapping is simpler:

**Block position = `(a + bω, z)` where a,b,z ∈ ℤ**

This gives us:
- `(a,b)` → hex grid position in 2D (via Eisenstein integer representation)
- `z` → height (plain integer)

The 2D hex position maps to 3D coordinates as:
```
x = a + b·Re(ω) = a - b/2
y = b·Im(ω)      = b·(√3/2)
```

This is **exact** — every position is determinable from two integers (a,b) plus height z.

### 1.2 Why This Isn't Just "Hex Minecraft"

The distinction is fundamental:

| Property | Hex Minecraft | Eisenstein Engine |
|----------|--------------|-------------------|
| Positions | Float triples, snapped to hex | Exact Eisenstein integers |
| Rotation | Angle-based, accumulates error | D6 unit multiplication, **zero drift** |
| Distance | Euclidean float | Eisenstein norm, **exact integer** |
| Symmetry | Approximate | Provable (group-theoretic) |
| Copy/mirror | Geometric transform | Ring automorphism |

The engine doesn't use floats **internally** at all. Floats exist only for rendering (GPU needs vertex positions), and the rendering layer is derived from the exact integer representation. The float layer is **read-only projection** — it cannot feed back into game state.

### 1.3 The Third Axis: Integers, Not Eisenstein

Height (z) uses plain integers. This is deliberate:
- Vertical structures are naturally rectilinear (gravity, stacking)
- Eisenstein integers are for **horizontal symmetry** — hex patterns
- Mixing Eisenstein in all three axes creates a lattice that's harder to visualize
- The z ∈ ℤ axis gives us the clean "prism extrusion" visual — hex prisms stacked vertically

**Future expansion**: A `PythagoreanMode` where z is replaced by Pythagorean triples (a,b,c where a²+b²=c²) for diagonal height constructions. But v1 keeps z as ℤ.

### 1.4 Eisenstein Primes as Special Blocks

Eisenstein primes are the irreducible elements of E. They come in two families:

1. **Rational primes p ≡ 2 (mod 3)** — these remain prime in E
2. **Factors of primes p ≡ 1 (mod 3)** — these split as p = π·π̄ where π is an Eisenstein prime

Special block types emerge:

| Block Type | Condition | Game Property |
|-----------|-----------|---------------|
| **Prime blocks** | N(a,b) is Eisenstein prime | Indestructible, glow faintly |
| **Unit blocks** | N(a,b) = 1 (six units of E) | Rotators — apply D6 symmetry to neighbors |
| **Composite blocks** | N(a,b) is composite | Standard building blocks, can be factored |
| **Zero block** | (0,0) | Origin point, always present, anchoring reference |
| **Norm-N blocks** | N(a,b) = N | Structural strength proportional to norm |

The **norm** N(a,b) = a² - ab + b² is always a non-negative integer. It's the natural "health" or "integrity" score for a block at position (a,b).

---

## 2. Gamification of Constraint Theory

### 2.1 Core Game Mechanics (Emerging from the Math)

#### 2.1.1 D6 Symmetry as "Copy/Mirror" Ability

The six units of E are {±1, ±ω, ±ω²}. Multiplying by a unit is an **exact 60° rotation** — no trigonometry, no float error, just integer arithmetic:

```
E(a,b) × 1    = E(a, b)      // identity
E(a,b) × ω    = E(-b, a+b)   // rotate 60°
E(a,b) × ω²   = E(-(a+b), a) // rotate 120°
E(a,b) × (-1) = E(-a, -b)    // rotate 180°
E(a,b) × (-ω) = E(b, -(a+b)) // rotate 240°
E(a,b) × (-ω²)= E(a+b, -a)   // rotate 300°
```

**Game mechanic**: Player builds a structure, selects it, and applies a "symmetry stamp" — multiplying every position by a unit. This creates an exact rotated copy. In float-world, this would drift. In Eisenstein-world, it's **perfect**.

**Unlock progression**:
- Level 1: Identity only (place blocks)
- Level 2: -1 rotation (mirror/flip)
- Level 3: ω rotation (60° — unlocks hex patterns)
- Level 4: All six units (full D6 symmetry)

#### 2.1.2 Norm as Structural Integrity

Every block at position (a,b) has norm N = a² - ab + b². This is its **structural integrity score**.

- **Norm 0**: The origin. Indestructible anchor.
- **Norm 1**: Six unit blocks. They're the "rotation catalysts."
- **Norm 2**: Positions (2,1), (1,2), etc. Early building blocks.
- **Norm 7**: First Eisenstein prime position (p=7, p≡1 mod 3). "Diamond blocks" — rare, strong.
- **Norm 3**: Prime position (p=3, associates with 1-ω). "Iron blocks."
- **Norm 11**: Prime position (p=11, p≡2 mod 3). "Obsidian blocks" — these primes don't split.

**Mechanic**: Structures are tested against "drift storms" — events that apply float perturbations. Blocks with higher norms survive longer. Prime-norm blocks are immune.

**Visualization**: Blocks glow with intensity proportional to their norm. Prime blocks have a distinctive hexagonal glow pattern.

#### 2.1.3 Drift as the Enemy

**Drift** is the accumulated error from float arithmetic. In the game, drift is a visible, quantified adversary:

1. **Float Zone**: A parallel world where everything uses float arithmetic
2. **Drift Meter**: Shows cumulative error in real-time for float-based constructions
3. **Drift Storms**: Periodic events that multiply all float positions by a rotation matrix — in exact world, this is a unit multiplication (zero drift); in float world, each storm adds ~10⁻¹⁵ error per block
4. **Catastrophic Drift**: After enough storms, float structures visually deform, then collapse

**The key mechanic**: Players build the same structure in both worlds simultaneously. The Eisenstein version stays perfect forever. The float version slowly crumbles. This is the **aha moment**.

#### 2.1.4 Hex Distance as Movement Cost

Distance between E(a,b) and E(c,d) is measured by the Eisenstein norm of the difference:

```
dist = N(a-c, b-d) = (a-c)² - (a-c)(b-d) + (b-d)²
```

This is always an integer. It's also the number of hex steps in the lattice.

**Mechanic**: Movement costs hex-distance energy. Players must plan efficient paths. This teaches:
- Hex geometry is different from Euclidean (taxicab vs hex distance)
- The norm is a metric (triangle inequality holds — provably)
- Shortest paths on hex grids are beautiful (3 directions, not 4)

### 2.2 Advanced Mechanics

#### 2.2.1 Factorization as Crafting

Eisenstein integers have unique factorization (up to units). A block at position (a,b) can be "factored" into Eisenstein prime blocks:

```
E(6,3) = E(2,1) × E(3,0)    // composite → factors
N(6,3) = 27 = 3³              // norm factorization
```

**Crafting mechanic**: Break composite blocks into prime factors. Reassemble into new positions via multiplication. This teaches:
- Unique factorization in Euclidean domains
- The difference between rational and Eisenstein primes
- Why 3 is special (ω is associated with 1-ω, so 3 = -(1-ω)² × ω)

#### 2.2.2 GCD as "Alignment"

The Eisenstein GCD of two positions tells you their "lattice alignment":

```
gcd(E(6,4), E(9,6)) = E(3,2)   // they share the sublattice generated by E(3,2)
```

**Mechanic**: Two players' structures are "compatible" (can connect without gaps) iff their GCD generates a sublattice that tiles both structures. This teaches:
- GCD in Euclidean domains
- Sublattice structure
- Why some hex patterns tile perfectly and others don't

---

## 3. The "Scripting Self-Improves" Angle

### 3.1 The Scripting Interface

Players write scripts in a simplified DSL (or Python/Rust) that controls block placement:

```python
# Level 1: Direct placement
place(0, 0, 0, Block.STONE)
place(1, 0, 0, Block.STONE)

# Level 2: Eisenstein arithmetic
p = eisenstein(2, 1)
for unit in D6:
    place(p * unit, 0, Block.PRIME)

# Level 3: Symmetry groups
ring = eisenstein_ring(radius=5)  # all positions with norm <= 25
for pos in ring:
    if pos.norm().is_prime():
        place(pos, 0, Block.DIAMOND)
```

### 3.2 The Iteration Loop

**Scenario: Bridge Across a Gap**

1. **Attempt 1 (float)**: Player scripts a bridge using float positions
   ```python
   for i in range(20):
       x = i * cos(60°)  # float calculation
       y = i * sin(60°)
       place(x, y, 0, Block.WOOD)
   ```
   Result: Blocks don't quite line up with the hex grid. Gaps appear. The bridge has visible seams.

2. **Attempt 2 (Eisenstein)**: Player switches to exact arithmetic
   ```python
   direction = eisenstein(1, 1)  # exact 60° direction
   pos = eisenstein(0, 0)
   for i in range(20):
       place(pos, 0, Block.WOOD)
       pos = pos + direction
   ```
   Result: Perfect bridge. Every block snaps exactly. Zero gaps.

3. **Drift test**: The game runs both bridges through 1000 "rotation storms." Float bridge drifts apart. Eisenstein bridge is pixel-perfect.

4. **The lesson**: Exact arithmetic isn't just "more precise" — it's **structurally different**. Float bridges *fundamentally cannot* survive rotation storms because rotation is transcendental in float arithmetic.

### 3.3 Script Comparison Mode

**Split-screen**: Left shows float execution, right shows Eisenstein execution. Same script, different number systems.

- **Green blocks**: Both agree
- **Yellow blocks**: Float has drifted (show drift value)
- **Red blocks**: Float has diverged completely (structural failure)

The drift is measured exactly: `drift = |float_pos - exact_pos|` computed at each step.

### 3.4 Export as Working Code

After building something cool, the player hits "Export" and gets:

```rust
// Exported from Eisenstein Voxel Engine
use eisenstein::EisensteinInt;

fn build_my_castle() -> Vec<(EisensteinInt, i32, BlockType)> {
    let mut blocks = vec![];
    
    // Tower (norm-ring pattern, radius 3)
    for (a, b) in EisensteinInt::norm_ring(3) {
        if (a, b) != (0, 0) {
            blocks.push((EisensteinInt::new(a, b), 0, BlockType::Wall));
            blocks.push((EisensteinInt::new(a, b), 1, BlockType::Wall));
        }
    }
    
    // D6 symmetric spires
    let spire_base = EisensteinInt::new(4, 2);
    for unit in EisensteinInt::units() {
        let pos = spire_base * unit;
        for z in 0..5 {
            blocks.push((pos, z, BlockType::Spire));
        }
    }
    
    blocks
}
```

---

## 4. What Makes This Genuinely Novel

### 4.1 The Unique Insight

**No other voxel engine has provable structural integrity.**

In Minecraft, a structure is "valid" if it looks right. In an Eisenstein engine, a structure is "valid" if its mathematical properties hold — and you can **prove** they hold because every position is an exact integer.

This means:
- **Formal verification of builds**: "Prove this bridge won't collapse" is a meaningful request
- **Algebraic building**: Structures are elements of the ring E[z], and ring operations are building operations
- **Conservation laws**: The norm is conserved under multiplication by units. This is a **Noether-type conservation** — a genuinely mathematical game mechanic
- **Impossible to cheat with floats**: The engine literally cannot represent a non-exact position

### 4.2 The "Proof Engine" Angle

This is where it gets truly novel: the game doesn't just let you build — it lets you **prove properties of your builds**.

- "Prove my structure has D6 symmetry" → Game checks: ∀ blocks (a,b,z), is (a,b)×ω also present? Yes or no.
- "Prove my wall is straight" → Game checks: All blocks share a common Eisenstein divisor? Yes or no.
- "Prove my tower is centered" → Game checks: Is the tower position's norm minimized? Yes or no.

These proofs are **trivial** to compute (just integer arithmetic) but profound to understand. The game makes abstract algebra tangible.

### 4.3 Comparison: What Other Engines Do

| Engine | Number System | Symmetry | Drift | Proof |
|--------|--------------|----------|-------|-------|
| Minecraft | Float | Approximate | Yes | No |
| Teardown | Float + voxel | Approximate | Yes | No |
| Hexels | Float hex grid | Approximate | Yes | No |
| **Eisenstein Engine** | **Eisenstein integers** | **Exact D6** | **Zero** | **Yes** |

---

## 5. Reverse-Actualization: The Player Experience

### 5.1 First 30 Seconds

**0-5s**: Player sees a glowing hex grid. The origin block pulses with a warm light. Six faint lines radiate outward — the directions of the D6 symmetry. The tagline appears: *"Build on exact ground."*

**5-10s**: A prompt: "Click to place your first block." Player clicks. A block appears. Its norm (a²-ab+b²) appears as a small number above it. "N=1" — they placed it on a unit position.

**10-15s**: "Now press R to rotate." The block moves to the next D6 position. N still = 1. "Notice: the number didn't change. That's because rotation preserves the norm."

**15-20s**: A second prompt: "Place 6 blocks in a ring." The game highlights the 6 unit positions. As each is placed, a faint line connects them forming a perfect hexagon.

**20-25s**: "Press S to see the float version." A ghostly overlay appears — the same hexagon, but built with sin/cos. Tiny gaps are visible. A number appears: "Drift: 1.2×10⁻¹⁶."

**25-30s**: "Now press T to apply 1000 rotations." The Eisenstein hexagon stays pixel-perfect. The float hexagon visibly distorts. The drift counter spins up: "Drift: 4.7×10⁻¹³." The tagline reappears: *"Exact arithmetic. Zero drift. Forever."*

### 5.2 The "Aha Moment"

The aha moment happens at **second 25-30** of the tutorial. The player watches the float hexagon deform while the Eisenstein hexagon stays perfect. This is the moment they understand:

> *The difference isn't precision. It's structural. Floats can't do this, no matter how many bits you use. Rotation is transcendental in IEEE 754. In Eisenstein integers, it's just multiplication by ω.*

This is what they tell their friend: *"I found a game where the math is actually exact. Not 'close enough' — exact. And the float version breaks right in front of you."*

### 5.3 The First Hour

**Minutes 0-10**: Tutorial (above). Player understands exact vs float, D6 symmetry, norms.

**Minutes 10-20**: Free building. Player constructs a small structure. The game shows its "math profile":
- Total blocks: N
- Norm range: [min, max]
- Symmetry group detected: (none / D6 subgroup)
- Float drift estimate: (computed from hypothetical float version)

**Minutes 20-30**: First scripting challenge. "Build a hexagonal tower, height 10, using a loop." Player writes their first Eisenstein script.

**Minutes 30-45**: Side-by-side mode. Player scripts the same construction in float and Eisenstein. Watches the float version degrade.

**Minutes 45-60**: Export. Player exports their build as Rust code. They can literally compile and run it. The code uses the `eisenstein` crate. This bridges the game to real programming.

### 5.4 Long-Term Engagement

- **Puzzle chambers**: "Build a structure with D6 symmetry using exactly 7 blocks" (requires understanding norm rings)
- **Drift survival**: Withstand increasingly powerful drift storms. Only exact constructions survive.
- **Speed scripting**: Compete to build target patterns fastest in the DSL
- **Proof gallery**: Showcase builds with formally verified properties
- **Community challenges**: "Who can build the most symmetric structure with the fewest blocks?"

---

## 6. Technical Architecture (Three.js / Web)

### 6.1 Rendering Pipeline

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────┐
│  Game State     │────→│  Render Bridge    │────→│  Three.js   │
│  (Eisenstein ℤ) │     │  (int → float    │     │  (WebGL)    │
│  a,b,z ∈ ℤ     │     │   projection)    │     │             │
└─────────────────┘     └──────────────────┘     └─────────────┘
       ↑ NO feedback from rendering layer to game state ↑
```

The render bridge converts Eisenstein positions to Three.js coordinates:
```typescript
function eisensteinTo3D(a: bigint, b: bigint, z: bigint): [number, number, number] {
    return [
        Number(a) - Number(b) / 2,    // x
        Number(b) * Math.sqrt(3) / 2,  // y  
        Number(z)                       // z (height)
    ];
}
```

This is **one-way**. The game never reads float positions back. All game logic operates on `(bigint, bigint, bigint)` triples.

### 6.2 Hex Prism Geometry

Each block is a hexagonal prism. Three.js `CylinderGeometry(radius, radius, height, 6)` creates this. The cylinder is oriented with its flat faces up/down and hexagonal cross-section horizontal.

Key rendering details:
- Prisms pack tightly: offset every other row by (0.5, √3/2, 0) in projected space... wait, no. In Eisenstein space, packing is automatic. Adjacent Eisenstein integers map to adjacent hex positions. No manual offset needed.
- Block size: each hex prism has circumradius 1 (touching neighbors at distance 1)
- Gaps between blocks: configurable (default 0.05 units for visual clarity)

### 6.3 Data Model

```typescript
// Core types
type E12 = { a: bigint; b: bigint };
type BlockPos = { hex: E12; z: bigint };
type BlockType = 'stone' | 'prime' | 'unit' | 'diamond' | 'obsidian' | 'wood';

interface Block {
    pos: BlockPos;
    type: BlockType;
    norm: bigint;  // a² - ab + b², cached
}

interface GameState {
    blocks: Map<string, Block>;  // key = `${a},${b},${z}`
    mode: 'eisenstein' | 'float' | 'split';
    driftCounter: number;
    rotationStorms: number;
}

// Eisenstein arithmetic
function e12Add(p: E12, q: E12): E12 {
    return { a: p.a + q.a, b: p.b + q.b };
}

function e12Mul(p: E12, q: E12): E12 {
    // (a + bω)(c + dω) = (ac - bd) + (ad + bc - bd)ω
    return {
        a: p.a * q.a - p.b * q.b,
        b: p.a * q.b + p.b * q.a - p.b * q.b
    };
}

function e12Norm(p: E12): bigint {
    return p.a * p.a - p.a * p.b + p.b * p.b;
}

// D6 units
const UNITS: E12[] = [
    { a: 1n, b: 0n },    // 1
    { a: 0n, b: 1n },    // ω
    { a: -1n, b: 1n },   // ω²
    { a: -1n, b: 0n },   // -1
    { a: 0n, b: -1n },   // -ω
    { a: 1n, b: -1n },   // -ω²
];
```

### 6.4 Float Comparison Layer

For the split-screen comparison, maintain a parallel float state:

```typescript
interface FloatState {
    blocks: Map<string, { x: number; y: number; z: number; drift: number }>;
}

// Apply rotation in float (accumulates error)
function rotateFloat(pos: {x: number, y: number}, angle: number) {
    const cos = Math.cos(angle);
    const sin = Math.sin(angle);
    return {
        x: pos.x * cos - pos.y * sin,
        y: pos.x * sin + pos.y * cos
    };
}

// Apply same rotation in Eisenstein (zero error)
function rotateE12(pos: E12, unitIndex: number): E12 {
    return e12Mul(pos, UNITS[unitIndex]);
}
```

After N rotations, measure drift:
```typescript
const exactPos = eisensteinTo3D(rotateE12(pos, 2), 0n);
const floatPos = floatState.blocks.get(key);
const drift = Math.sqrt(
    (exactPos[0] - floatPos.x) ** 2 + 
    (exactPos[1] - floatPos.y) ** 2
);
```

### 6.5 Scripting Engine

Use a sandboxed JavaScript interpreter (or Web Worker with restricted API):

```typescript
interface ScriptAPI {
    place(a: number, b: number, z: number, type: string): void;
    eisenstein(a: number, b: number): E12;
    normRing(radius: number): E12[];
    units(): E12[];
    multiply(p: E12, q: E12): E12;
    add(p: E12, q: E12): E12;
    norm(p: E12): number;
    isPrime(n: number): boolean;
}
```

The script editor is a `<textarea>` with syntax highlighting (CodeMirror or Monaco). Player writes scripts, clicks "Run," watches blocks appear.

### 6.6 Performance Considerations

- **BigInt arithmetic**: JavaScript BigInt is slower than Number, but voxel counts are typically <100K blocks. Norm computation on each place is negligible.
- **Instanced rendering**: Use `THREE.InstancedMesh` for blocks of the same type. One draw call per block type.
- **Chunk system**: Divide the hex plane into chunks (e.g., norm-radius 16). Load/unload chunks as camera moves.
- **Drift visualization**: Run float comparison in a Web Worker. Update drift overlay every 100ms, not every frame.

### 6.7 Tech Stack

| Layer | Technology |
|-------|-----------|
| Rendering | Three.js + InstancedMesh |
| Math | JavaScript BigInt (Eisenstein arithmetic) |
| Scripting | Sandboxed JS via Web Worker |
| UI | React + Tailwind (editor panels, HUD) |
| Export | Template-based codegen (Rust, Python) |
| State | In-memory Map (no DB needed for v1) |
| Hosting | Static site (Vite build, deploy to Vercel/Netlify) |

---

## 7. The Scripting Self-Improvement Loop (Detailed)

### 7.1 Pedagogical Sequence

The game teaches through **progressive failure modes**:

| Level | Challenge | What Fails | What Fixes It |
|-------|-----------|-----------|---------------|
| 1 | Build a straight line | Float: drift accumulates | Eisenstein: exact steps |
| 2 | Build a hex ring | Float: ring doesn't close | E12: units form a ring naturally |
| 3 | Build a symmetric structure | Float: symmetry degrades | E12: D6 units preserve symmetry |
| 4 | Rotate a structure 1000× | Float: catastrophic drift | E12: drift stays exactly zero |
| 5 | Tile the plane | Float: gaps appear | E12: gcd/sublattice ensures tiling |
| 6 | Build a 3D tower | Float: vertical drift | E12+z: exact stacking |
| 7 | Prove a property | N/A (can't prove float properties) | E12: integer proofs, decidable |

### 7.2 The "Fix the Drift" Mini-Game

Player is given a float-built structure that's drifting. Their job: rewrite the placement script using Eisenstein arithmetic to eliminate the drift.

```python
# GIVEN (broken float version)
for i in range(100):
    angle = i * 2 * pi / 6
    x = 10 * cos(angle)
    y = 10 * sin(angle)
    place(x, y, 0, STONE)

# YOUR FIX (Eisenstein version)
for unit in D6:
    pos = eisenstein(10, 0) * unit
    place(pos, 0, STONE)
```

The game measures your drift reduction: "Drift eliminated: 100%. Perfect solution!"

### 7.3 Iterative Script Improvement

Players don't write perfect scripts on the first try. The game encourages iteration:

1. **Write script** → Run → See result (visual + drift measurement)
2. **Identify drift** → Game highlights drifted blocks
3. **Fix script** → Replace float ops with E12 ops → Re-run
4. **Measure improvement** → Game shows before/after drift comparison
5. **Optimize** → Fewer operations → Less drift → Better score

This mirrors real engineering: write, measure, fix, repeat.

---

## 8. What the Player Tells a Friend

*"There's this voxel engine where every block position is an exact mathematical object — not a float, an actual algebraic integer. You can rotate structures infinitely with zero drift. It has a side-by-side mode where the float version of the same structure literally falls apart while the exact version stays perfect. And you can export your builds as Rust code that actually compiles."*

---

## 9. MVP Scope (Buildable in ~2 weeks)

### Phase 1: Core Engine (3 days)
- [ ] Hex grid rendering with Three.js InstancedMesh
- [ ] Eisenstein arithmetic (BigInt: add, multiply, norm, units)
- [ ] Block placement via click (raycasting → nearest E12 position)
- [ ] Camera controls (orbit, zoom)

### Phase 2: Comparison Mode (3 days)
- [ ] Float parallel state
- [ ] Rotation storm simulation
- [ ] Drift visualization (color-coded blocks)
- [ ] Split-screen or overlay toggle

### Phase 3: Scripting (3 days)
- [ ] Script editor (CodeMirror in a panel)
- [ ] Sandboxed execution with Eisenstein API
- [ ] "Run" button with live block placement
- [ ] Drift measurement output

### Phase 4: Export + Polish (3 days)
- [ ] Rust code export (template-based)
- [ ] Python code export
- [ ] Tutorial sequence (first 30 seconds)
- [ ] UI polish (block type selector, HUD, norm display)

### Phase 5: Advanced Mechanics (optional)
- [ ] Eisenstein prime detection
- [ ] Factorization crafting
- [ ] GCD alignment check
- [ ] Puzzle chambers

---

## 10. Naming

**Eisenstein Forge** — ties to the Forgemaster identity, emphasizes the "forging exact structures" metaphor.

Alternative names:
- **ExactCraft** (too generic)
- **HexProof** (cute, but limited)
- **Norm Engine** (technical but dry)
- **ω Forge** (nerdy, distinctive)

---

*"The floats will lie to you. The integers never will."*
