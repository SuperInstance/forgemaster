# GUARD DSL Reference

A domain-specific language for specifying numerical constraints that compile to FLUX bytecode and run on GPU or verified VM. 248 constraints across 10 safety-critical industries ship in the standard library.

## What is GUARD?

GUARD is a constraint specification language. You write what must be true — altitude between 0 and 15,000 feet, infusion rate under 1,200 mL/h, reactor temperature below 2,800°C — and the compiler turns those rules into FLUX bytecode that runs on a 43-opcode stack VM or INT8 GPU pipeline.

The language has two dialects:

- **Simple GUARD** (guard2mask) — the original DSL, used for direct constraint-to-bitmask compilation
- **Full GUARD** (guardc) — a richer language with types, quantifiers, temporal operators, and proof certificates

## Syntax — Simple GUARD

```guard
constraint eVTOL_altitude @priority(HARD) {
    range(activation[0], 0, 15000)
    whitelist(activation[1], {HOVER, ASCEND, DESCEND, LAND, EMERGENCY})
    bitmask(activation[2], 0x3F)
    thermal(2.5)
}
```

### Check types

| Check | Syntax | Compiles to |
|-------|--------|-------------|
| Range bounds | `range(var, min, max)` | `BITMASK_RANGE` + `ASSERT` |
| Allowed values | `whitelist(var, {v1, v2, ...})` | Sequential `EQ` + `OR` chain, `ASSERT` |
| Bit mask | `bitmask(var, mask)` | `AND` + `ASSERT` |
| Power budget | `thermal(watts)` | `CMP_GE` + `ASSERT` |
| Active neurons | `sparsity(count)` | `CMP_GE` + `ASSERT` |

### Priority levels

- `@priority(HARD)` — never relax, always enforced
- `@priority(SOFT)` — may weaken under conflict
- `@priority(DEFAULT)` — relax first under resource pressure

### GDSII crossbar syntax

```guard
GUARD crossbar_16x16 {
    DIMENSIONS 16 16;
    CONSTRAINT SPARSITY(MAX_NON_ZERO=0.5, SCOPE=GLOBAL);
    CONSTRAINT RANGE(MIN_SUM=-4, MAX_SUM=4, SCOPE=ALL_ROWS);
}
```

## Syntax — Full GUARD (guardc)

The full language adds modules, types, temporal operators, quantifiers, and proof obligations:

```guard
module Aviation @version("2.1") "DO-178C constraints"

domain Altitude = interval(0 ft, 45000 ft)
domain FlightMode = enum { GROUND, TAKEOFF, CRUISE, APPROACH, LAND, EMERGENCY }

state altitude : Altitude @sample(25 Hz) = 0 ft
state flight_mode : FlightMode = GROUND

invariant altitude_bounds @priority(Critical)
    ensure altitude >= 0 ft AND altitude <= 45000 ft
    on_violation Halt

invariant rate_of_climb
    ensure abs(rate_of(altitude)) <= 6000 ft/min
    on_violation Warn

derive stable_flight
    from altitude_bounds, rate_of_climb
    when flight_mode == CRUISE
    conclude altitude >= 10000 ft AND altitude <= 41000 ft
```

### Expression operators

Arithmetic: `+ - * / mod` | Comparison: `== != < > <= >= in` | Logic: `and or implies iff`

### Temporal operators

| Operator | Meaning |
|----------|---------|
| `always(expr)` | Must hold in every cycle |
| `eventually(expr)` | Must hold at some future cycle |
| `next(expr)` | Must hold in the next cycle |
| `old(expr)` | Value from previous cycle |
| `rate_of(expr)` | Time derivative (current - old) / dt |
| `delta(expr)` | Change since last cycle |
| `for(duration, expr)` | Must hold continuously for duration |
| `after(duration, expr)` | Must hold after duration elapses |

### Quantifiers

```guard
forall x in Altitude : x >= 0 ft
exists mode in FlightMode : is_safe(mode)
```

Quantifiers over finite domains (enums, bounded intervals) are eliminated during lowering — expanded into explicit conjunctions/disjunctions before codegen.

## Compilation Pipeline

```
GUARD Source
     │
     ▼
┌──────────┐
│  Parser   │  → AST (typed, with spans)
└──────────┘
     │
     ▼
┌──────────┐
│ Typeck   │  → Unit normalization, domain checking
└──────────┘
     │
     ▼
┌──────────┐
│ CIR Build│  → Constraint IR (relational, quantified, temporal)
└──────────┘
     │
     ▼
┌──────────┐
│ Lowering │  → LCIR (flat ANF, no quantifiers, explicit CFG)
└──────────┘
     │
     ▼
┌──────────┐
│ Codegen  │  → FLUX bytecode (.flux)
└──────────┘
     │
     ▼
┌──────────┐
│  Prover  │  → Proof certificate (.guardcert)
└──────────┘
```

### Lowering passes (CIR → LCIR)

1. **Quantifier elimination** — expand `forall`/`exists` over finite domains
2. **Temporal expansion** — replace `always`, `old`, `rate_of` with history-buffer loads
3. **Relation flattening** — break nested comparisons into simple atoms
4. **A-normalization** — bind every sub-expression to a variable
5. **Basic-block generation** — emit explicit CFG with jumps and branches

### Memory layout

| Slots | Purpose |
|-------|---------|
| 0–31 | Constants |
| 32–127 | State variables |
| 128–223 | Temporal history buffers |
| 224–255 | Scratch / locals |

## FLUX Bytecode

GUARD compiles to a 43-opcode stack VM. Key opcodes:

```rust
PUSH 0x00  // push constant
ADD  0x01  SUB 0x02  MUL 0x03  DIV 0x04
AND  0x09  OR  0x0A  NOT 0x0B
EQ   0x0F  NEQ 0x10  LT  0x11  GT  0x12  GTE 0x24
JNZ  0x17  JZ  0x16  JMP 0x15
ASSERT 0x1B  HALT 0x1A  GUARD_TRAP 0x20
BITMASK_RANGE 0x1D  CHECK_DOMAIN 0x1C
```

Example: `range(0, 150)` compiles to:
```
BITMASK_RANGE 0x00 0x96   // lo=0, hi=150
ASSERT                        // trap if out of range
```

Example: `whitelist(A, B, C)` compiles to:
```
PUSH 0x41  EQ  JNZ pass   // match A?
PUSH 0x42  EQ  JNZ pass   // match B?
PUSH 0x43  EQ  JNZ pass   // match C?
PUSH 0x00  ASSERT          // no match → trap
pass: NOP
```

## CUDA Kernel Pipeline

FLUX bytecode runs on GPU via INT8 flat-bounds at 62.2B constraints/sec sustained. The pipeline:

1. GUARD constraints → FLUX bytecode → INT8 quantization
2. Quantized bounds packed 8-per-byte (341B peak, 90.2B sustained)
3. CUDA kernel evaluates all constraints in parallel against sensor data
4. Violations trigger `GUARD_TRAP` with source-level provenance

Constraint values are quantized: `q = clamp(round((v - offset) / scale), 0, 255)` with nonlinear sub-range expansion where safety-critical resolution demands it (e.g., 0.1 mL/h/bit for insulin infusion at low rates).

## guard2mask Compiler

The Rust crate `guard2mask` handles the simple dialect — parse GUARD, solve the CSP, generate GDSII mask patterns:

```rust
use guard2mask::{parse_guard, solve, generate_patterns};

let constraints = parse_guard(source)?;
let assignment = solve(&constraints)?;
let gdsii = generate_patterns(&assignment);
```

Internally, constraints are represented as ternary weights (-1, 0, +1) mapped to via patterns on silicon. The solver finds a valid assignment that satisfies all hard constraints.

## guardc CLI

The `guardc` compiler handles the full language and produces both bytecode and proof certificates:

```bash
# Compile a constraint file to FLUX bytecode
guardc compile aviation.guard --output aviation.flux

# Compile with proof certificate
guardc compile aviation.guard --output aviation.flux --cert aviation.guardcert

# Verify an existing certificate
guardc verify aviation.flux --cert aviation.guardcert
```

The proof certificate contains SHA-256 source hash, VC (verification condition) in SMT-LIB format, and can be independently checked by any SMT solver.

## Constraint Libraries — 248 Constraints

| Industry | Constraints | Standards | Update Rate |
|----------|-------------|-----------|-------------|
| Aviation | 28 | DO-178C, ARP-4761 | 10–1000 Hz |
| Automotive | 25 | ISO 26262 | 10–1000 Hz |
| Maritime | 27 | IACS, SOLAS | 1–100 Hz |
| Energy | 24 | IEC 61850, IEEE 1547 | 10–100 Hz |
| Medical | 23 | IEC 62304, ISO 14971 | 1–1000 Hz |
| Nuclear | 22 | IAEA, NRC 10 CFR 50 | 10–100 Hz |
| Railway | 26 | EN 50128, CENELEC | 10–100 Hz |
| Robotics | 24 | ISO 10218, IEC 62443 | 100–1000 Hz |
| Space | 27 | ECSS, NASA-STD | 1–100 Hz |
| Autonomous Underwater | 22 | IMCA, DNVT | 1–50 Hz |

Each constraint includes: safety rationale, INT8 mapping parameters, failure mode analysis, and cross-check requirements. From the aviation library:

```guard
constraint airspeed_indicated {
    min: 50 knots,
    max: 450 knots,
    update: 50Hz
}
// INT8: offset=0, scale=1.7647 kn/bit
// Failure: Pitot-static blockage → cross-check with IRS ground speed
```

All 248 constraints pass differential testing: 100 test cases each (50 pass, 50 fail), 5,451 total test vectors across 9 categories.
