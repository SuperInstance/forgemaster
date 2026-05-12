# Zeitgeist Protocol — FLUX Transference Specification

## Overview

The Zeitgeist Protocol defines a binary wire format for transmitting **FLUX packets** — structured messages carrying both arbitrary payloads and a **Zeitgeist**: a composite CRDT semilattice capturing five dimensions of agent alignment state.

## FLUX Packet Wire Format

```
┌──────────────────────────────────────────┐
│ Magic:    0xFLUX (4 bytes)              │  bytes 0-3
│ Version:  u16 (big-endian)              │  bytes 4-5
│ Flags:    u8 (compression, encryption)   │  byte 6
│ Source:   RoomId (u32, big-endian)       │  bytes 7-10
│ Target:   RoomId (u32, big-endian)       │  bytes 11-14
│ Timestamp: f64 (big-endian, UNIX epoch)  │  bytes 15-22
│ Payload Len: u32 (big-endian)            │  bytes 23-26
│ Zeitgeist Len: u32 (big-endian)          │  bytes 27-30
│ Payload:  [u8; Payload Len]             │  bytes 31..31+PL
│ Zeitgeist: [u8; Zeitgeist Len] (CBOR)   │  variable
│ Parity:   u8 (XOR of all preceding)     │  last byte
└──────────────────────────────────────────┘
```

### Magic
`0x46 0x4C 0x55 0x58` ("FLUX" in ASCII)

### Flags
| Bit | Meaning |
|-----|---------|
| 0x01 | Payload is compressed (zlib) |
| 0x02 | Payload is encrypted (AES-256-GCM) |

### Parity
XOR of all bytes preceding the parity byte. Single-byte integrity check.

## Zeitgeist Binary Format (CBOR)

The Zeitgeist is encoded as a CBOR map with integer keys:

```
{
  1: {                    // Precision — Deadband funnel state
    1: deadband: float64,     // Current deadband width (>0, <covering_radius)
    2: funnel_pos: float64,   // Position in funnel (0=wide, 1=snap)
    3: snap_imminent: bool    // Within closing threshold
  }
  2: {                    // Confidence — Certainty state
    1: bloom: bytes[32],      // Bloom filter hash
    2: parity: uint8,         // Bitwise parity
    3: certainty: float64     // 0.0-1.0
  }
  3: {                    // Trajectory — Trend state
    1: hurst: float64,        // H estimate (0-1)
    2: trend: uint8,          // 0=stable, 1=rising, 2=falling, 3=chaotic
    3: velocity: float64      // Rate of change
  }
  4: {                    // Consensus — Cycle coherence
    1: holonomy: float64,     // Cycle integral (0=coherent)
    2: peer_agreement: float64, // Fraction of agreeing peers (0-1)
    3: crdt_version: map<u64,u64>  // State vector clock
  }
  5: {                    // Temporal — Rhythm state
    1: beat_pos: float64,     // Position in beat grid (0-1)
    2: phase: uint8,          // 0=idle, 1=approaching, 2=snap, 3=hold
    3: rhythm_coherence: float64 // How well rhythm matches grid (0-1)
  }
}
```

## Merge Semantics (CRDT Semilattice)

Each Zeitgeist dimension uses a **semilattice merge** — the merge operation is:

1. **Commutative**: `merge(a, b) == merge(b, a)`
2. **Associative**: `merge(merge(a, b), c) == merge(a, merge(b, c))`
3. **Idempotent**: `merge(a, a) == a`

### Per-Field Merge Rules

| Dimension | Field | Merge Rule | Rationale |
|-----------|-------|-----------|-----------|
| Precision | deadband | `min(a, b)` | Tighter bound wins |
| Precision | funnel_pos | `max(a, b)` | Further along = more certain |
| Precision | snap_imminent | `a OR b` | Either can trigger snap |
| Confidence | bloom | `a OR b` (bitwise) | Union of evidence |
| Confidence | parity | `a OR b` (bitwise) | Union of parity bits |
| Confidence | certainty | `max(a, b)` | Higher certainty wins |
| Trajectory | hurst | `min(a, b)` | Conservative estimate |
| Trajectory | trend | `a if a==b else Chaotic` | Disagreement = chaos |
| Trajectory | velocity | `max(a, b)` | Most urgent signal |
| Consensus | holonomy | `min(a, b)` | Most coherent wins |
| Consensus | peer_agreement | `max(a, b)` | Best agreement wins |
| Consensus | crdt_version | `pointwise max` | Standard PVV merge |
| Temporal | beat_pos | `max(a, b)` | Latest position |
| Temporal | phase | `max(a, b)` | Most advanced phase |
| Temporal | rhythm_coherence | `max(a, b)` | Best coherence wins |

## Alignment Constraints

A valid Zeitgeist must satisfy:

- `precision.deadband > 0` and `< covering_radius`
- `confidence.certainty ∈ [0, 1]`
- `trajectory.hurst ∈ [0, 1]`
- `consensus.peer_agreement ∈ [0, 1]`
- `temporal.beat_pos ∈ [0, 1]`
- `temporal.rhythm_coherence ∈ [0, 1]`

Violations produce an `AlignmentReport` listing all failed constraints.

## Reference Implementation

Rust: `src/` — `cargo test` runs 100-iteration property tests proving all three merge laws.

### Binding Status

- ✅ Rust (reference)
- ✅ Python (`python/zeitgeist.py`)
- ✅ TypeScript (`ts/zeitgeist.ts`)
