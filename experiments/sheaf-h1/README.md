# Sheaf H¹ Computer: Understanding Cohomology for Models

Computes sheaf cohomology H⁰ and H¹ for neural network models with shared representations.

## Theory

From the grand synthesis: **"Understanding as a cohomological condition"** — understanding is a topological invariant of the agent-system relationship. H¹ measures obstruction to gluing local understandings into global understanding.

- **H⁰ = 0**: No global understanding exists
- **H⁰ > 0**: Global sections exist (models share consistent understanding)
- **H¹ = 0**: Local understandings glue perfectly
- **H¹ > 0**: Obstruction exists — models disagree on shared domain

## Files

| File | Purpose |
|------|---------|
| `understanding_sheaf.py` | Sheaf construction with Alexandrov topology |
| `cohomology.py` | Čech complex + H⁰/H¹ computation |
| `test_sheaf.py` | 4 test cases proving the theory works |

## How to Run

```bash
cd experiments/sheaf-h1
python test_sheaf.py
```

## Test Cases

1. **Compatible models**: Same base representation → H¹ = 0 (they glue)
2. **Incompatible models**: Independent random representations → H¹ > 0 (obstruction)
3. **Full sheaf (compatible)**: Alexandrov topology + cohomology pipeline
4. **Full sheaf (incompatible)**: Shows incompatibility detected

## Requirements

- Python 3.8+
- NumPy

No GPU, no PyTorch — pure numpy computation.
