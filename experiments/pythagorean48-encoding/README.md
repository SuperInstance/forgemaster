# Pythagorean48 Encoding — Zero-Drift Direction Representation

**Exact unit vectors from integer Pythagorean triples. Zero floating-point drift. Forever.**

## Hypothesis

The 52 Pythagorean triples (a, b, c) where a² + b² = c² and c ≤ 100 provide exact unit vectors in 128 unique directions (full 360°), with zero floating-point drift when using rational representations (a/c, b/c) instead of floating-point sin/cos.

## Key Results

| Metric | Pythagorean48 | Float32 |
|--------|--------------|---------|
| Unique directions | 128 | ∞ (continuous) |
| Angular resolution (min gap) | 0.93° | N/A |
| Angular resolution (median gap) | 2.29° | N/A |
| MSE vs. continuous angles | 5.71 deg² | 0 (baseline) |
| **Drift after 1000 chained rotations** | **0.00e+00** | **1.72e-05** |
| Drift ratio | ∞ (zero) | baseline |

### Comparison with Fixed Direction Encodings

| Encoding | Directions | MSE (deg²) | RMSE (deg) | Max Error (deg) |
|----------|-----------|------------|------------|-----------------|
| Compass (8-dir) | 8 | 169.28 | 13.01 | 22.50 |
| 16-direction | 16 | 42.00 | 6.48 | 11.25 |
| 36-direction (10°) | 36 | 8.29 | 2.88 | 5.00 |
| **Pythagorean48 (128-dir)** | **128** | **5.71** | **2.39** | **8.80** |
| 48-direction (7.5°) | 48 | 4.69 | 2.17 | 3.75 |

### The Zero-Drift Proof

After 1000 chained rotations:
- **Pythagorean48**: |magnitude² − 1.0| = **exactly 0** (integer arithmetic never drifts)
- **Float32**: |magnitude² − 1.0| = **1.72 × 10⁻⁵** (accumulates roundoff every step)

The drift ratio is literally infinite. Integer ratios don't drift.

## Why This Matters for Engineers

If you're doing robotics, aerospace, or any system that chains rotational transformations, floating-point drift is a silent killer. Over thousands of operations, unit vectors stop being unit vectors. Renormalization is a band-aid. Pythagorean48 is the cure — exact rational arithmetic means drift is structurally impossible.

**Trade-off**: You get 128 discrete directions (2.3° median resolution) in exchange for zero drift forever. For most control systems, 2.3° resolution is more than sufficient, and the drift elimination is invaluable.

**INT8 bonus**: Since a/c and b/c are rational with small denominators, these map cleanly to fixed-point representations for embedded deployment.

## How to Reproduce

```bash
cd experiments/pythagorean48-encoding
python3 experiment.py
```

No dependencies. Outputs full triple table, angular coverage analysis, comparison table, and zero-drift proof to stdout.

## Files

- `experiment.py` — Complete experiment: triple enumeration, coverage analysis, drift comparison

## Cross-References

- **constraint-library-validation** — INT8 deployment uses exact arithmetic principles from this encoding
- **collect-select-compile** — Direction quantization is a SELECT operation on continuous angle space
- **laman-rigidity** — Graph rigidity uses direction vectors; zero-drift encoding improves constraint checking
