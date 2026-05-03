# GUARD — Generic Unified Assurance Requirement Descriptor

> A constraint specification DSL for safety-critical systems. Designed by safety engineers, for safety engineers. Compiles to FLUX bytecode. Ships with proof certificates.

---

## What is this?

GUARD is a domain-specific language that lets safety engineers write formal safety requirements in a syntax that looks like a requirements document — not a programming language. It compiles to deterministic FLUX bytecode for a 43-opcode stack VM, and every compilation produces an independently verifiable proof certificate.

## Directory Layout

```
guard-dsl/
├── SPEC.md                     # Complete language specification
├── GRAMMAR.ebnf                # Formal EBNF grammar
├── BYTECODE.md                 # GUARD → FLUX bytecode mapping guide
├── CERTIFICATES.md             # Proof certificate format & verification
├── ERRORS.md                   # Human-centered error message catalog
├── COMPARISON.md               # Comparison with SCADE/Lustre, Alloy, Datalog
├── README.md                   # This file
└── examples/
    ├── throttle.guard          # (a) Simple: throttle limit
    ├── zone-access.guard       # (b) Medium: radiation bunker interlock
    └── flight-envelope.guard   # (c) Complex: fly-by-wire envelope protection
```

## Quick Start

### Read the spec
```bash
cat guard-dsl/SPEC.md
```

### Inspect an example
```bash
cat guard-dsl/examples/throttle.guard
```

### See the bytecode mapping
```bash
cat guard-dsl/BYTECODE.md
```

## Design Highlights

| Feature | GUARD Approach |
|---------|---------------|
| **Syntax** | Reads like a requirements doc (`ensure x ≤ MAX`) |
| **Units** | Mandatory dimensional analysis (knots + degrees = error) |
| **Temporal** | First-class (`always`, `for 3 s`, `rate_of`, `since`) |
| **Proof** | SMT-based VCs with Merkle-ized certificates |
| **Runtime** | 43-opcode FLUX VM, deterministic, no-std capable |
| **Errors** | Safety-impact explanations, not compiler jargon |

## Status

**v1.0.0-ship** — Specification complete. Ready for compiler implementation.

## Integration with FLUX Ecosystem

GUARD compiles to the existing FLUX ISA (see `../flux-isa/` and `../flux-isa-std/`). Proof certificates integrate with the FLUX provenance system (see `../flux-verify-api/src/provenance/`).
