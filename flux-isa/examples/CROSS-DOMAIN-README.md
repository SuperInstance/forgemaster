# FLUX-ISA Cross-Domain Programs

Five demonstration programs showing how FLUX-DEEP opcodes bridge mathematical
domains through shared bytecode execution on a single stack machine.

## Architecture

FLUX-ISA defines **58 opcodes** across six groups:

| Range   | Group               | Count | Purpose                                  |
|---------|---------------------|-------|------------------------------------------|
| 0x01-0x65 | Core              | 43    | Arithmetic, constraints, flow, memory, logic, compare, INT8 |
| 0x80-0x87 | Galois Adjunctions| 8     | Verified mathematical adjunctions (XorInvert, Clamp, Bloom, FloorQ, CeilQ, Align, Holonomy) |
| 0x88-0x8F | Cross-Domain      | 8     | Tdqkr, Amnesia, Shadow, Phase, Couple, Federate, Bearing, Depth |
| 0x90-0x95 | Projection        | 6     | Cut-and-project between high-D and low-D (Penrose tiling space) |

The **cross-domain principle**: every domain uses every other domain's best math
through shared bytecode. No domain is isolated.

---

## Program 1: Penrose → Eisenstein

**What it does:** Pushes a 5D point (constructed from golden ratio powers),
checks if the dimension guarantees aperiodicity via `NASTY`, projects down to
2D Penrose tiling space via `PROJECT`, then snaps the projected coordinates to
an Eisenstein (hexagonal) lattice using `FLOORQ` with step = φ.

**Math involved:**
- 5D → 2D cut-and-project using golden ratio projection matrix
- Floor adjunction: `floor(v/φ)·φ` snaps to nearest lattice point
- Aperiodicity check via Greenfeld-Tao threshold

**Domains crossed:** Projection → Galois adjunctions → Constraint validation

**Expected output:**
- Two values snapped to the φ-spaced Eisenstein lattice
- Validation passes (values in range)

---

## Program 2: Mandelbrot meets Memory

**What it does:** Computes 3 iterations of z² + c (unrolled), checks if the
orbit survived (didn't escape |z| < 2), applies Ebbinghaus forgetting curve
via `AMNESIA` to the orbit memory, checks phase transition via `PHASE` to
determine if the memory persists, then projects survivors to Penrose floor
via `PROJECT` + `SNAPHIGH`.

**Math involved:**
- Mandelbrot iteration: z_{n+1} = z_n² + c
- Ebbinghaus decay: V(t) = V₀ · e^(-t/τ)
- Phase transition: memory strength > threshold → coherent
- Golden ratio snap for survivors

**Domains crossed:** Complex iteration → Temporal decay → Phase transition → Projection → Lattice snap

**Expected output:**
- Phase transition flag (0 or 1)
- Projected coordinates snapped to golden ratio lattice

---

## Program 3: Baton Shuffle

**What it does:** Takes a tile value (42), splits it into 3 shards via
arithmetic division and golden ratio decomposition, applies "telephone drift"
(amnesia decay with different ages per shard), computes the negative space
via `SHADOW`, couples the shadow with the original via `COUPLE`, then
projects and reconstructs to demonstrate information preservation through
the cut-and-project roundtrip.

**Math involved:**
- Arithmetic splitting: 42/3 = 14, 14+φ², 14·(1/φ)
- Ebbinghaus decay with varying ages: e^(-age/τ)
- Negative space: 1 - Σ(shadow_components)
- Critical coupling: (a·b)/√(a²+b²)
- Project + Reconstruct roundtrip

**Domains crossed:** Arithmetic → Amnesia drift → Shadow reconstruction → Coupling → Projection/Reconstruction

**Expected output:**
- Coupling strength between shadow and original
- Reconstructed values from the project-reconstruct roundtrip

---

## Program 4: Golden Pipeline

**What it does:** Constructs a 5D golden ratio vector [φ, 2φ, 3φ, 4φ, 5φ],
projects it to 2D via `PROJECT`, scores the projected value using `TDQKR`
(query-key retrieval score = x²), clamps the score to [0, 100] via `CLAMP`,
then checks holonomy consistency of the remaining values.

**Math involved:**
- Golden ratio rotation: multiply each dimension by φ
- Cut-and-project from 5D to 2D Penrose space
- TDQKR scoring: top-k query-key retrieval (simplified as x²)
- Clamp as reflective subcategory (idempotent truncation)
- Holonomy: product of cycle signs (consistency check)

**Domains crossed:** Golden rotation → Projection → TDQKR scoring → Galois clamp → Holonomy

**Expected output:**
- Clamped TDQKR score (bounded to [0, 100])
- Holonomy product (should be ±1.0)

---

## Program 5: Priority Fleet

**What it does:** Two agent states (priority + load) enter `COUPLE` for
critical coupling strength, `FEDERATE` for consensus voting, `SHADOW` for
negative space computation, `BEARING` for fleet heading, and `ALIGN` for
target alignment check.

**Math involved:**
- Critical coupling: (a·b)/√(a²+b²)
- Federation: majority vote among agents
- Shadow: 1 - Σ(components) = negative space
- Bearing: snap angle to 30° dodecet (12 directions)
- Alignment: |actual - intent| ≤ tolerance

**Domains crossed:** Coupling → Federation → Shadow → Bearing → Alignment

**Expected output:**
- Coupling strengths for both load and priority
- Federation consensus (1.0 = unanimous)
- Shadow (negative space)
- Bearing direction (0-11)
- Alignment flag (1.0 = on target)

---

## Running

```bash
cd flux-isa
python examples/cross_domain_demo.py
```

All programs are self-contained — no external dependencies beyond the
`pyflux` compatibility layer in this repo.

## Opcode Cross-Reference

Each program demonstrates specific opcode combinations:

| Program | Opcodes Used |
|---------|-------------|
| 1 | LOAD, POP, NASTY, PROJECT, FLOORQ, SWAP, VALIDATE, HALT |
| 2 | LOAD, LT, AMNESIA, PHASE, AND, PROJECT, POP, SNAPHIGH, HALT |
| 3 | LOAD, DIV, MUL, ADD, AMNESIA, SHADOW, COUPLE, PROJECT, RECONSTRUCT, HALT |
| 4 | LOAD, MUL, PROJECT, SWAP, TDQKR, CLAMP, HOLONOMY, HALT |
| 5 | LOAD, COUPLE, SWAP, FEDERATE, SHADOW, BEARING, ALIGN, HALT |
