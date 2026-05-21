# Constraint Library Validation

**Validating 248 real-world engineering constraints across 10 safety-critical industries for internal consistency, INT8 deployability, and cross-domain compatibility.**

## Hypothesis

A constraint library sourced from real engineering standards (ISO 26262, DO-178C, IEC 61508, etc.) should be:
1. Internally consistent (every constraint is parseable and physically plausible)
2. Deployable on edge hardware (INT8 quantization compatible)
3. Cross-domain safe (same-unit constraints across industries don't produce dangerous disjoint ranges)

## Key Results

| Metric | Value |
|--------|-------|
| Total constraints parsed | 248 |
| Valid (internally consistent) | **247 (99.6%)** |
| INT8-compatible | **211 (85.1%)** |
| Cross-industry conflicts | 66 (all disjoint ranges, not contradictions) |
| Industries failing any check | 1 (Nuclear: 1 invalid constraint) |

### Per-Industry Scores

All 10 industries pass validation. Nuclear has one soft failure (23/24 valid). INT8 compatibility ranges from 68% (Robotics, ISO 10218 — wide voltage ranges) to 96% (Automotive, ISO 26262).

### The 66 "Conflicts"

All 66 cross-industry conflicts are **disjoint ranges** — e.g., automotive tire pressure [1.8, 3.5] bar vs. avionics propellant tank [10.0, 25.0] bar. These aren't errors; they reflect that different industries genuinely operate in different physical regimes. The validator correctly flags them for any system attempting to unify constraints across domains.

## Why This Matters for Engineers

**85.1% INT8 compatibility** means you can deploy the vast majority of safety constraints on microcontrollers without floating-point units. The 37 constraints that don't fit INT8 need special handling (wider types, scaling, or lookup tables).

**99.6% validity** means the automated extraction pipeline from standards documents is reliable. The single failure in Nuclear (IEC 61513) is a data quality issue to fix upstream, not a systemic problem.

**Cross-industry mapping** — the 66 disjoint ranges are a roadmap for where unified constraint systems need domain-switching logic. You can't use one set of thresholds for both automotive and aerospace temperature ranges.

## How to Reproduce

```bash
cd experiments/constraint-library-validation
python3 experiment.py
```

Requires constraint YAML files in `../../constraints/` directory. Outputs `RESULTS.md` and `results.json`.

## Files

- `experiment.py` — Parses, validates, INT8-checks, and cross-compares all constraints
- `RESULTS.md` — Full per-industry breakdown and conflict details
- `results.json` — Machine-readable results with all 66 conflict details

## Cross-References

- **laman-rigidity** — Rigidity theory determines minimum constraint count for determinism
- **collect-select-compile** — The COLLECT→SELECT→COMPILE pattern applied to constraint filtering
- **pythagorean48-encoding** — Zero-drift encoding for constraint parameter representation
