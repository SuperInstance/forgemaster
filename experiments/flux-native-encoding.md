# FLUX-Native Encoding — Mathematical Assembly for Truth

## The Core Idea

FLUX instructions don't describe computation. They describe mathematical intent.
The compiler finds the "truthest" physical realization — doesn't matter if that's
AVX-512, CUDA, Penrose paper folding, or Fortran assembly.

## FLUX ISA for Permutational Folding

| Opcode | Byte | Meaning |
|--------|------|---------|
| FOLD b<n> | 01 nn | Project residual onto basis vector n |
| ROUND | 02 | Quantize top-of-stack coefficient |
| RESIDUAL | 03 | Compute |r| after current folds |
| MINIMUM | 04 | Reduce to minimum across lanes |
| CONSENSUS | 05 | Count fold agreement |
| SNAP_ALL | 06 | Fork all permutations |

No memory. No pointers. No control flow.
Just: FOLD → ROUND → RESIDUAL → MINIMUM → truth.

## Example: Full snap to Z[ζ₅] with consensus

```
06 01 02 02 01 00 02 01 03 02 01 01 02 03 05 04
```
16 bytes. Encodes: fork 24 permutations → fold 4 bases → round each → residual → consensus → minimum.

## The Origami Connection

Each FOLD is a crease in the paper. The ORDER of creases determines the form.
For Penrose: 5 folds from R⁵ → Z⁵ (cut-and-project).
For Z[ζ₅]: 4 folds from R² → overcomplete lattice.
For Eisenstein: 2 folds from R² → hexagonal lattice.

The permutation IS the crease pattern. Different pattern → different form.

## The Truthest Method

FLUX doesn't care about substrate. The same bytecode compiles to:
- AVX-512: 24 folds in 3 batches of 8 doubles, ~15 cycles
- CUDA: 24 folds in 1 warp (32 threads), ~1 clock
- Paper: 24 physical crease patterns

Because the truth is the same regardless of physics.
FLUX encodes truth. The compiler maps truth → substrate.

## Connection to Casey's Vision

"Origami with Penrose paper into meaningful forms"
→ Each fold IS a crease. The permutation IS the form.

"FLUX-native encoding to a dynamic form of Fortran-like assembly"
→ 7 opcodes. No memory model. No control flow. Pure mathematical intent.

"It doesn't matter in flux. We are just mathematical finding the truthest methods."
→ The substrate is irrelevant. The truth is all that matters.
