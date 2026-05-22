# deadband-python

Deadband perceptual quantization for sensor data. Uses Eisenstein integers, Fibonacci spline search, and human perceptual models to decide when a signal change actually matters.

## Install

```bash
pip install deadband-python
```

## Quick Start

```python
from deadband_python import div360_sub, deadband_perceivable, eisenstein_snap

# Is a 0.3° change perceptible at threshold 0.5°?
print(deadband_perceivable(0.3, 0.5))   # False — below threshold

# Is a 0.7° change perceptible?
print(deadband_perceivable(0.7, 0.5))   # True — above threshold

# Snap coordinates to Eisenstein lattice
x, y = eisenstein_snap(3.7, 2.1, scale=1.0)
print(f"Snapped: ({x}, {y})")           # (4.0, 2.0)
```

## What it does

Deadband filtering answers one question: **did the signal change enough to matter?**

This library provides the math for that decision:

- **`div360_add/sub/mul`** — Modular arithmetic on Z/360Z (angle deadband)
- **`deadband_perceivable`** — Human-perceptual threshold check
- **`deadband_min_bits`** — Minimum bit depth for deadband representation
- **`eisenstein_snap`** — Snap to Eisenstein integer lattice (hexagonal quantization)
- **`fib_spline_search`** — Fibonacci-scaled spline search for nearest threshold
- **`bma_detect`** — Backward moving average change detection
- **`shell_decompose`** — Concentric shell decomposition (number-theoretic structure)
- **`hpdf_sample/dither`** — Hierarchical perceptual distance function sampling and dithering

## C Extension

A C extension (`_deadband_c`) is compiled at build time when possible. If unavailable, pure-Python fallbacks are used automatically. Check `_C_EXT` to see which backend is active:

```python
from deadband_python import _C_EXT
print("C extension" if _C_EXT else "Pure Python")
```

## License

MIT
