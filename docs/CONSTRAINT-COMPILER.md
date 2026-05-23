# The Constraint-Aware Compiler

## The Core Idea

Traditional compilers optimize code. Forgemaster optimizes **assemblies** — and
treats the assembly process itself as a constraint satisfaction problem.

## How Traditional Systems Work

```
User Request → Glue Components Together → Hope It Works → Debug in Production
```

Components are treated as black boxes. Integration is ad-hoc. Guarantees are
theoretical, not enforced.

## How Forgemaster Works

```
User Request → Scan Ecosystem → Assemble Under Constraints → Verify Guarantees → Ship
```

Every step is a constraint check:

### 1. Component Declaration

Each module in the ecosystem declares its constraint profile:

```yaml
# constraint-theory-py
guarantees:
  precision: "IEEE 754 double"
  latency: "<1ms per constraint evaluation"
  memory: "<10MB working set"
  correctness: "83/83 tests passing"
```

### 2. Assembly as Constraint

When forgemaster assembles a pipeline, it treats the combination as a constraint
problem. It's not "does each piece work?" but "do they work **together**, under
the user's specific constraints?"

```
User wants: 4-voice counterpoint, <100ms latency, <50MB memory

Components selected:
  counterpoint-engine: guarantees SAT-solvable in <10ms for 4 voices ✓
  flux-tensor-midi: guarantees <5ms tensor encoding ✓
  constraint-synth: guarantees <50ms rendering at 44.1kHz ✓

Combined constraint check:
  10ms + 5ms + 50ms = 65ms < 100ms ✓
  10MB + 5MB + 20MB = 35MB < 50MB ✓
  
Result: ASSEMBLED with proof
```

### 3. Proof-Carrying Assembly

The assembled result carries its constraint proof. This isn't documentation —
it's a machine-verifiable certificate that the assembly meets its guarantees.

## The Paradigm Shift

| Traditional | Forgemaster |
|-------------|-------------|
| Components are black boxes | Components declare constraint profiles |
| Integration is hope-based | Integration is constraint-checked |
| "Works on my machine" | Guarantees travel with the code |
| Runtime surprises | Assembly-time verification |
| Manual optimization | Target-specific constraint optimization |

## What This Means for You

When forgemaster assembles something for you, you get:

1. **A pipeline that works** — not theoretically, but verified under your constraints
2. **Portable guarantees** — the proof travels with the assembled artifact
3. **Target optimization** — adjusted for your specific hardware/API budget
4. **Composability** — any assembled pipeline is itself a component that can be re-assembled

## Implementation

The compiler lives across several modules:

- `forgemaster/` — Core compiler logic (assembler, optimizer, verifier)
- `constraint-theory-py/` — Python constraint theory library (83 tests)
- `flux-vm/` — Virtual machine for constraint execution
- `flux-compiler/` — Compiles constraint programs to flux-isa
- `flux-verify-api/` — Verification API for proof checking
