# FLUX Assembly Programs

Constraint-theory algorithms implemented in FLUX ISA v3 assembly.

## Programs

| Program | Description | Input | Output | ~Bytes |
|---------|-------------|-------|--------|--------|
| `eisenstein_snap.flux` | Snap (x,y) to nearest Eisenstein integer lattice point | F0=a, F1=b (floats) | R8=x', R9=y' (snapped) | ~52 |
| `constraint_check.flux` | Hard constraint enforcement (FLUX-C style) | R0=val, R1=min, R2=max | R8=1 (ok) or PANIC | ~40 |
| `bloom_filter.flux` | Bloom filter membership test (3 hashes, 256-bit bitmap) | R0=value, R6=bitmap ptr | R8=1 (present) / 0 (absent) | ~88 |
| `intent_align.flux` | 9D intent vector cosine similarity | Two 9×int32 vectors in memory | R8=alignment (0–1000) | ~160 |
| `agent_coordinate.flux` | Multi-agent A2A consensus protocol | R0=action, R1/R2=agent IDs | R8=1 (consensus) / 0 (denied) | ~60 |
| `temporal_snap.flux` | Snap timestamp to nearest beat grid | R0=ticks, R1=period | R8=snapped, R9=drift | ~44 |

## Assembly Syntax

Programs use the FLUX ISA v3 mnemonic syntax:

```asm
; Comments start with ;
IMov    R8, R0             ; Move R0 → R8
IAdd    R2, R0, R1         ; R2 = R0 + R1
FRound  F2, F0, F0         ; F2 = round(F0)
Load32  R8, R6, 0          ; Load 32-bit from memory[R6+0]
Jump    label              ; Branch to label
Halt                      ; Stop execution
```

### Register Conventions

| Register | Name | Purpose |
|----------|------|---------|
| R0–R7 | GP | General-purpose, caller-saved |
| R8 | RV | Return value |
| R9, R10 | A0, A1 | Function arguments |
| R11 | SP | Stack pointer |
| R12 | FP | Frame pointer |
| R13 | FL | Flags |
| F0–F7 | FP | Float general-purpose |
| F8 | FV | Float return value |

### Instruction Formats

| Format | Size | Example |
|--------|------|---------|
| A (nullary) | 1 byte | `Halt`, `Panic`, `Nop` |
| B (2 reg) | 3 bytes | `IMov Rd, Rs`, `Push Rd, Rs` |
| C (3 reg) | 4 bytes | `IAdd Rd, Ra, Rb`, `BXor Rd, Ra, Rb` |
| D (reg + imm16) | 4 bytes | `IInc Rd, imm16`, `IDec Rd, imm16` |
| E (reg + base + off16) | 5 bytes | `Load32 Rd, Rb, off16` |
| G (variable) | 2+N bytes | `Jump offset`, `ATell agent, reg` |

## How to Assemble/Run

### Using flux-vm (Rust reference implementation)

```bash
# Install the FLUX toolchain
cargo install flux-vm

# Assemble a program
flux-asm programs/eisenstein_snap.flux -o eisenstein_snap.fbx

# Run the bytecode
flux-run eisenstein_snap.fbx
```

### Manual Assembly

Each instruction maps directly to bytes per the FLUX ISA v3 encoding:

```asm
; IMov R8, R0 = opcode 0x20, Rd=8, Rs=0 → bytes: [20 08 00]
; IAdd R2, R0, R1 = opcode 0x21, Rd=2, Ra=0, Rb=1 → bytes: [21 02 00 01]
; Halt = opcode 0x00 → byte: [00]
```

Refer to `flux-research/specs/flux-isa-v3.md` for the full opcode table.

## Algorithm Notes

### Eisenstein Snap
The Eisenstein integers form a triangular lattice. Valid lattice points satisfy `(a - b) mod 3 ∈ {0, 1}`. After rounding, if the remainder is 2, we adjust `b += 1` to reach the nearest valid point.

### Bloom Filter
Three hash functions provide probabilistic membership testing with no false negatives:
- `h1(v) = v ^ (v << 5)`
- `h2(v) = v ^ (v >> 3)`
- `h3(v) = (v << 7) ^ (v >> 5)`

Each hash indexes into a 256-bit bitmap. All three bits must be set for a "probably present" result.

### Intent Alignment
Cosine similarity between 9D vectors using fixed-point arithmetic (scale factor 1000). Uses `FSqrt` via float conversion for the norm calculation, then integer division for the final score.

### Temporal Snap
Rounds a timestamp to the nearest beat grid point using integer division with rounding. Drift is the absolute distance from the original timestamp.

## Spec Reference

FLUX ISA v3: `flux-research/specs/flux-isa-v3.md`
