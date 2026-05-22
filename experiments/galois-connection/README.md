# Galois Connection Verification

## ⚠️ STATUS: BUG — REGEX CRASH IN PHASE 3

The experiment runs Phases 1-2 successfully but crashes in Phase 3 on a regex edge case
in the test generator. The hypothesis (zero false negatives in GUARD→FLUX-C compilation)
is sound but the implementation needs debugging.

**Do not re-run without fixing the regex bug in experiment.py.**

## Hypothesis
There exists a Galois connection between GUARD (abstract spec) and FLUX-C (compiled code)
such that compilation is sound: never misses violations.

## What Works
- Phase 1: Abstraction function α (GUARD → FLUX-C)
- Phase 2: Concretization function γ (FLUX-C → GUARD)

## What's Broken
- Phase 3: Regex-based test input generator crashes on edge cases
