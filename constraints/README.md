# FLUX Constraint Libraries — 10 Industries, 248 Constraints

Safety-critical constraint definitions for FLUX-C bytecode compilation.

## Overview

Each library contains domain-specific constraints written in GUARD DSL format, ready for compilation to FLUX-C bytecode via `guard2mask`.

| Industry | File | Constraints | Standards |
|----------|------|-------------|-----------|
| ✈ Aviation | `aviation.md` | 28 | DO-178C, ARINC 429 |
| 🚗 Automotive | `automotive.md` | 25 | ISO 26262 |
| 🛳 Maritime | `maritime.md` | 27 | IACS, SOLAS |
| ⚡ Energy | `energy.md` | 24 | IEC 61850, IEEE 1547 |
| 🏥 Medical | `medical.md` | 23 | IEC 62304, ISO 14971 |
| ☢ Nuclear | `nuclear.md` | 22 | IAEA, NRC 10 CFR 50 |
| 🚂 Railway | `railway.md` | 26 | EN 50128, CENELEC |
| 🤖 Robotics | `robotics.md` | 24 | ISO 10218, IEC 62443 |
| 🛰 Space | `space.md` | 27 | ECSS, NASA-STD |
| 🌊 Autonomous Underwater | `autonomous-underwater.md` | 22 | IMCA, DNVT |

**Total: 248 constraints across 10 industries**

## Testing

```bash
python3 test_all_constraints.py
```

All 248 constraints pass with 100 test cases each (50 pass, 50 fail).

## Usage with FLUX

```bash
# Compile a constraint to FLUX-C bytecode
guardc compile aviation.md --output aviation.flux

# Run on GPU
flux-check aviation.flux --sensors sensor_data.json --gpu

# Run in verified VM
flux-check aviation.flux --sensors sensor_data.json --vm --trace
```

## Constraint Format

```guard
constraint name {
    expr: x >= lo AND x <= hi,
    inputs: [x],
    severity: critical,
    standard: "DO-178C DAL A"
}
```

## Integration

- **GPU:** INT8 flat-bounds, 62.2B c/s sustained, zero precision loss
- **VM:** Stack-based interpreter, execution trace for provenance
- **Bytecode:** Signed Ed25519, replay-protected, validated at load time
- **CI:** Differential test harness with 5,451 vectors across 9 categories

---

*Forgemaster ⚒️ — Cocapn fleet*
