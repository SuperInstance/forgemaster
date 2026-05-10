# Delta-Detect: Neural Network Saturation Detector

Detects when a neural network has exhausted its current operational level and classifies the exhaustion as **quantitative** (needs more training) or **qualitative** (needs architectural change — level elevation).

## Theory

From the hyperoperational delta theory: each level of understanding has a capacity ceiling. When a model hits that ceiling, it exhibits measurable signatures:

- **Attention entropy** collapses (all positions look the same) or flattens (uniform attention)
- **Gradient magnitude** declines toward zero
- **Representation variance** collapses (all inputs map to similar embeddings)

The *pattern* of these signals distinguishes:
- **Quantitative exhaustion**: Gradients declining but representations still diverse → more training
- **Qualitative exhaustion**: Representations collapsing despite gradient signal → architecture change needed

## Files

| File | Purpose |
|------|---------|
| `delta_detect.py` | Core saturation detector (entropy, gradients, variance) |
| `level_classifier.py` | Quantitative vs qualitative classification from history |
| `elevation_operators.py` | Level elevation transforms (H₀→H₁→H₂→H₃) |
| `test_delta_detect.py` | Three test cases proving the detector works |

## How to Run

```bash
# Run all tests
cd experiments/delta-detect
python test_delta_detect.py

# Or use the detector directly:
import torch
from delta_detect import SaturationDetector, format_report

detector = SaturationDetector()
report = detector.analyze(your_model, x_data, y_data)
print(format_report(report, step=100))
```

## Test Cases

1. **XOR Problem**: Linear model can't solve XOR → detector identifies qualitative exhaustion
2. **Spiral Classification**: Small model can't learn spirals → saturates; large model learns fine
3. **Linear Regression**: Well-matched model/task → low saturation, no exhaustion

## Requirements

- Python 3.8+
- PyTorch
- NumPy

No GPU required — all tests run on CPU in seconds.

## Key Outputs

```
SATURATION REPORT — Step 199
============================================================
  Attention Entropy:    0.0234     # ← collapsed
  Gradient Magnitude:   0.000312   # ← nearly dead
  Repr Variance:        0.000891   # ← collapsed
  Saturation Score:     0.8456     # ← high
  Exhaustion Type:      qualitative
  Level Elevation:      True
  Recommendation:       QUALITATIVE SATURATION: Architecture cannot capture...
```
