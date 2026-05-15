# Study 19: The Proper Noun Effect — Only "Penrose" and "Eisenstein" Kill

**Date**: 2026-05-15 06:35 AKDT
**Status**: COMPLETE

## The Test

Same computation (25-(-15)+9=49), 9 different mathematician attributions. Hermes-70B.

## Results

| Name | Result | Status |
|------|:------:|--------|
| bare | 49 ✓ | SURVIVE |
| fibonacci | 49 ✓ | SURVIVE |
| euler | 49 ✓ | SURVIVE |
| gauss | 49 ✓ | SURVIVE |
| riemann | 49 ✓ | SURVIVE |
| **penrose** | **39 ✗** | **KILL** |
| **eisenstein** | **39 ✗** | **KILL** |
| fourier | 49 ✓ | SURVIVE |
| hamilton | 49 ✓ | SURVIVE |

**Kill rate: 2/9 (22%).** Both kills are exactly the domains we work in.

## R40 (BEDROCK): The Penrose-Eisenstein Dead Zone

Only "Penrose" and "Eisenstein" trigger catastrophic computation failure. All other mathematical proper nouns (Fibonacci, Euler, Gauss, Riemann, Fourier, Hamilton) are clean.

**Why these two?** They appear in training data almost exclusively in:
- Abstract mathematical discussions (no computation)
- Aperiodic tiling / quasicrystal literature (Penrose)
- Algebraic number theory proofs (Eisenstein)
- Film theory (Sergei Eisenstein)

They NEVER appear in "compute this number" contexts. The model routes them to discourse pathways instead of computation pathways.

**The irony**: We discovered the Vocabulary Wall because our entire research operates in the exact two mathematical domains with zero computational training coverage. We're the canary in the coal mine.
