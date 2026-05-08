# Eisenstein Developer Tools Plan

## 5 Tools — Weekend-Buildable, Real Utility

---

### Tool 1: `eisenstein-bench` (P0 — Ship with HN)
**CLI benchmark suite for hex lattice operations**

- **Problem:** Developers need to see the drift for themselves before believing the claim
- **Stack:** Rust binary, depends on eisenstein crate + criterion
- **Repo:** `SuperInstance/eisenstein-bench`

**Key Features:**
- `eisenstein-bench drift` — Run N rotations, compare E12 vs float, print drift stats
- `eisenstein-bench disk` — Benchmark HexDisk iteration at various radii
- `eisenstein-bench snap` — Benchmark angle snapping throughput
- `eisenstein-bench norm` — Benchmark norm computation vs float hypot
- `eisenstein-bench full` — Run all benchmarks, print summary table

**API:**
```bash
eisenstein-bench drift --rotations 100000
eisenstein-bench disk --radius 1000
eisenstein-bench full --json > results.json
```

**Size:** ~800 lines Rust
**Why P0:** The HN post claims "zero drift after 10K rotations". This tool PROVES it on the reader's machine.

---

### Tool 2: `eisenstein-fuzz` (P0 — Ship with HN)
**Property-based fuzzing harness for the eisenstein crate**

- **Problem:** "Zero drift" is a strong claim. Fuzzing finds counterexamples.
- **Stack:** Rust binary, cargo-fuzz + arbitrary
- **Repo:** `SuperInstance/eisenstein-fuzz`

**Key Features:**
- Fuzz: rotation identity (6 rotations = identity for all E12 values)
- Fuzz: norm is always non-negative integer
- Fuzz: multiplication distributes over addition
- Fuzz: D6 neighbors have norm within ±2 of parent
- Fuzz: disk iteration covers exactly the right points
- Fuzz: conjugate is involution (conj(conj(x)) = x)
- Fuzz: angle snap lands on valid E12 direction
- Fuzz: overflow behavior at i32 boundaries

**API:**
```bash
cargo fuzz run rotation_identity
cargo fuzz run norm_nonneg -- -max_total_time=300
cargo fuzz run all -- -runs=1000000
```

**Size:** ~600 lines Rust
**Why P0:** "Zero drift" needs proof. Fuzzing is how Rust devs trust claims.

---

### Tool 3: `eisenstein-wasm` (P1 — Next Week)
**WebAssembly build of eisenstein for JS/TS consumers**

- **Problem:** Browser demos currently reimplement E12 in JS. Should use the real crate.
- **Stack:** Rust → wasm-pack → npm package
- **Repo:** `SuperInstance/eisenstein-wasm`

**Key Features:**
- `E12.new(a, b)` — construct
- `e12.norm()`, `e12.rot()`, `e12.add(other)`, `e12.mul(other)`
- `E12.snap_from_angle(theta)` — angle snapping
- `HexDisk.radius(n)` — iterator exposed as JS generator
- `E12.neighbors()` — D6 neighbor list
- TypeScript type definitions included
- ~20KB gzipped wasm output

**API (JS):**
```js
import { E12, HexDisk } from '@superinstance/eisenstein-wasm';

const z = new E12(3, 1);
console.log(z.norm()); // 7
console.log(z.rot().toString()); // "E12(-1, 4)"

for (const pt of HexDisk.radius(5)) {
  console.log(pt.a, pt.b, pt.norm());
}
```

**Size:** ~400 lines Rust + ~200 lines JS wrapper + .d.ts
**Why P1:** Makes the browser demos use the real crate, not reimplementation. Enables other JS devs.

---

### Tool 4: `hexgrid-gen` (P1 — Next Week)
**CLI code generator for hex grid constants**

- **Problem:** Game devs need precomputed lookup tables for hex operations.
- **Stack:** Rust binary, no deps
- **Repo:** `SuperInstance/hexgrid-gen`

**Key Features:**
- Generate neighbor offset tables for any hex radius
- Generate coordinate→index mapping for compact hex storage
- Output in Rust, Python, JS, C, or JSON
- Generate D6 rotation lookup tables
- Generate distance tables (hex Manhattan distance)
- Verify all outputs with property checks

**API:**
```bash
# Generate neighbor table for radius 50 in Rust
hexgrid-gen neighbors --radius 50 --lang rust > neighbors.rs

# Generate full coordinate table as JSON
hexgrid-gen disk --radius 100 --lang json > disk100.json

# Generate C header for embedded
hexgrid-gen table --radius 20 --lang c > hexgrid.h

# Verify correctness
hexgrid-gen verify --radius 200
```

**Size:** ~1200 lines Rust
**Why P1:** Game devs (Civ, Factorio-like) need this immediately. Precomputed tables = zero runtime cost.

---

### Tool 5: `eisenstein-verify` (P2 — Nice to Have)
**Formal verification helper — generates proof obligations for SMT solvers**

- **Problem:** "Exact arithmetic" is a claim that benefits from machine-checked proofs.
- **Stack:** Rust binary, outputs SMT-LIB2 format (for Z3, CVC5)
- **Repo:** `SuperInstance/eisenstein-verify`

**Key Features:**
- Generate SMT-LIB2 for rotation identity: ∀a,b: rot^6(a,b) = (a,b)
- Generate SMT-LIB2 for norm non-negativity: ∀a,b: a²-ab+b² ≥ 0
- Generate SMT-LIB2 for ring axioms (associativity, distributivity)
- Generate SMT-LIB2 for D6 closure
- Run Z3/CVC5 on generated obligations
- Print pass/fail for each axiom with counterexample if found

**API:**
```bash
# Generate all proof obligations
eisenstein-verify generate --all > proofs.smt2

# Generate specific axiom
eisenstein-verify generate --rotation-identity > rot.smt2

# Generate and verify with Z3
eisenstein-verify verify --solver z3 --timeout 60

# Verify specific axiom
eisenstein-verify verify --norm-nonneg --solver cvc5
```

**Size:** ~1000 lines Rust
**Why P2:** Nice for academic credibility. Not blocking for HN launch.

---

## Execution Plan

| # | Tool | Priority | ETA | Agent |
|---|------|----------|-----|-------|
| 1 | eisenstein-bench | P0 | 30 min | Spawn subagent |
| 2 | eisenstein-fuzz | P0 | 30 min | Spawn subagent |
| 3 | eisenstein-wasm | P1 | 45 min | Spawn subagent |
| 4 | hexgrid-gen | P1 | 45 min | Spawn subagent |
| 5 | eisenstein-verify | P2 | 60 min | Spawn subagent |

**Ship P0 tools before HN post goes live.** P1 within a week. P2 when someone asks for it.

## HN Post Update

Add to the HN post after tools ship:
```
Dev tools: [benchmark suite](https://github.com/SuperInstance/eisenstein-bench) (prove the drift claim on your machine), [fuzz harness](https://github.com/SuperInstance/eisenstein-fuzz) (find counterexamples if they exist)
```
