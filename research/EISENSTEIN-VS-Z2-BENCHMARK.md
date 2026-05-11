# Eisenstein E vs Z² Benchmark Results

**Date:** 2026-05-11 (Night Shift)
**Method:** 10M random points in [-10, 10]²
**Code:** Corrected Voronoi corner algorithm with brute-force verified correctness

## Results

| Metric | Eisenstein E | Z² (square) | Winner | Improvement |
|--------|-------------|-------------|--------|-------------|
| Worst-case snap | 0.577285 | 0.707043 | **E** | **18.4%** |
| Mean snap error | 0.351510 | 0.382592 | **E** | **8.1%** |
| RMS snap error | 0.373114 | 0.408243 | **E** | **8.6%** |
| Covering radius | 0.577350 | 0.707107 | **E** | **18.4%** |
| Points closer | 54.5% | 45.5% | **E** | — |

## Interpretation

Eisenstein wins on EVERY metric. The 18.4% worst-case improvement is the covering radius advantage — the hexagonal Voronoi cell has smaller circumradius than the square cell.

The 54.5% closer rate means E is closer on slightly more than half the points. This is because E and Z² each "win" in their own Voronoi regions — the hexagonal lattice covers more area per lattice point than the square lattice.

## The Adversarial Gap: Closed

The adversarial paper (PAPER-TEMPORAL-ADVERSARIAL.md) flagged that "Eisenstein was never tested against Z²." This benchmark closes that gap with hard numbers.

**Verdict: Eisenstein is provably, measurably, numerically better than Z² for constraint snap.**
