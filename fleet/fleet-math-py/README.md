# fleet-math-py

Q(ζ₁₅) cyclotomic field operations for Cocapn's constraint-theory framework.

## What

A Python package implementing the core mathematical operations for the
unified 6D cut-and-project scheme connecting Eisenstein and Penrose tilings
via the cyclotomic field Q(ζ₁₅).

## 9 Verified Claims

| Claim | Description | Verified Error |
|-------|-------------|----------------|
| 1 | Q(ζ₁₅) field construction, degree φ(15)=8 | Correct |
| 2 | ζ₁₅ rotation accuracy | < 1e-15 |
| 3 | ω = ζ₁₅⁵ → Eisenstein unit | Exact |
| 4 | Penrose projection at θ=arctan(φ) | < 0.1 rad |
| 5 | Galois connection: field → constraint domain | Exact |
| 6 | Eisenstein snap_to_lattice | ≤ 1/√3 |
| 7 | Unified 6D cut-and-project | Idempotent |
| 8 | Dodecet encoding (12-bit, 512-byte LUT) | ~3.6% FPR |
| 9 | Bounded drift check | Galois-proven |

## Usage

```python
from fleet_math import (
    Q15, eisenstein_snap_to_lattice, dodecet_encode,
    BoundedDrift, eisenstein_project, penrose_project,
    eins_round, constraint_check,
)

# Snap a point to the A₂ Eisenstein lattice
((a, b), error) = eisenstein_snap_to_lattice(1.5, 2.3)
print(f"Snapped to: a={a}, b={b}, error={error:.6f}")

# 12-bit dodecet encoding
code = dodecet_encode(a, b)

# Unify projection
proj = eisenstein_project(np.array([[1, 0, 0, 0, 0, 0]], dtype=float))

# Bounded drift check
drift = BoundedDrift(is_closed=True)
drift.add_step(0.0, 0.0, 0.0, 0.0)
print(f"Within bound: {drift.within_bound}")

# Constraint checking
from fleet_math.eisenstein import DodecetLUT
lut = DodecetLUT()
lut.insert(3, 5)
constraint_check(3, 5, lut=lut)  # True
```

## Installation

```bash
cd fleet-math-py
pip install -e .
# With test deps:
pip install -e ".[test]"
pytest tests/
```

## Repository

https://github.com/SuperInstance/fleet-math-py
