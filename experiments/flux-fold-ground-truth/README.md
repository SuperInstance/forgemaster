# FLUX-Fold Ground Truth

**Ground truth test suite for permutational folding on cyclotomic fields.**

Brutally honest evaluation of whether the overcomplete basis approach to
nearest-lattice-point is actually useful, or just mathematically interesting
but practically irrelevant.

## Structure

```
test_snap_correctness.py    — 100K random points: does snap return valid lattice points?
test_consensus_calibration.py — Is low fold-order consensus a calibrated uncertainty signal?
test_eisenstein_comparison.py — Head-to-head: cyclotomic folding vs standard Eisenstein snap
test_babai_comparison.py      — Comparison against Babai's nearest plane, LLL reduction, round-off
run_all.sh                    — Composite runner (aggregates results into results.json)
```

## Tests Overview

### 1. Snap Correctness (test_snap_correctness.py)
- **Valid lattice point**: Is the snapped point actually in Z[ζₙ]?
- **Idempotence**: Does snapping a snapped point give the same result?
- **Snap distance distribution**: What's the distance to nearest lattice point?
- **Optimality oracle**: Does the 3x3 neighborhood search find the TRUE closest point?
  (Brute-force over φ(n)-dim hypercube — slow but authoritative)
- **Fold order variation**: How many fold orders agree per point?
- **Nearest vs SOME lattice point**: Are we finding the nearest, or just any lattice point?

### 2. Consensus Calibration (test_consensus_calibration.py)
- **Consensus-error correlation**: Is low consensus correlated with high error?
- **Residual vs consensus**: Is consensus better than naive residual magnitude?
- **Calibration curve**: For consensus level k/N, prob of error in top 10%?
- **Edge cases**: near-lattice, near-boundary, known bad regions

### 3. Eisenstein Comparison (test_eisenstein_comparison.py)
- **Head-to-head**: Overcomplete vs Eisenstein on identical points
- **Best-case analysis**: Where does overcomplete actually beat Eisenstein?
- **Empirical covering radius**: Worst-case snap distance for both approaches
- **Worst-point improvement**: Does cyclotomic help where Eisenstein fails most?

### 4. Babai Comparison (test_babai_comparison.py)
- **Babai nearest plane**: Standard algorithm on raw basis pairs
- **LLL-reduced Babai**: Babai after lattice reduction
- **Round-off algorithm**: Simplest coefficient rounding
- **Failure modes**: Finding cases where Babai gives >2x optimal
- **Speed comparison**: ms/point for each algorithm

## Key Questions

### The "SO WHAT" Test
1. **1.5× tighter covering radius**: Does this improve ANY downstream task?
   - For constraint checking: yes, tighter bound = fewer false positives
   - For lattice cryptography: 1.5× tighter = ~1 bit less security needed
   - For nearest neighbor: unclear — depends on metric

2. **Consensus as uncertainty**: Is it calibrated?
   - If k/24 = 90% means top 10% error only 10% of the time → YES
   - If correlation is weak → NO, just a curiosity

3. **FLUX encoding**: Do 16-byte programs help anyone?
   - On constraint verification: program size irrelevant, quality of bound matters
   - On edge devices: small programs matter a lot
   - On server: irrelevant

### Known Bugs / Caveats
1. **3×3 neighborhood search**: May miss true nearest point. The brute-force tests reveal this.
2. **Overcomplete basis**: More basis vectors doesn't automatically mean tighter snap —
   the 3×3 search per pair vs. exhaustive across all pairs can give different results.
3. **Permutational folding**: The sequential projection loses information — 
   later projections depend on earlier rounding decisions.

## Running

```bash
# Full suite (~10 minutes, includes brute-force optimality checks for φ≤4)
./run_all.sh

# Quick mode (~30 seconds)
./run_all.sh --quick
```

## Output

All results are written to JSON files:
- `results_snap.json` — Snap correctness results
- `results_consensus.json` — Consensus calibration results  
- `results_eisenstein.json` — Eisenstein comparison results
- `results_babai.json` — Babai/algorithm comparison results
- `results.json` — Unified compilation
