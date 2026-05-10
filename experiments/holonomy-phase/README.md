# Holonomy Phase Experiment: Geometric Phase in Neural Training

Trains a small model on a cyclic curriculum (A→B→C→A) and measures whether representation vectors accumulate holonomy (geometric phase) across cycles.

## Theory

From the grand synthesis: **Holonomy = classical geometric phase.** When a model is trained on a cycle of tasks, its internal representations undergo a closed loop in representation space. If they don't return to the starting point, the deficit is holonomy — a systematic bias invisible to the loss function.

This is analogous to the **Hannay angle** in classical mechanics: a system carried around a loop in parameter space picks up a geometric phase.

## What This Tests

1. **Holonomy accumulates**: Representation drift grows across cycles
2. **Systematic direction**: Drift isn't random — it has a consistent direction
3. **Invisible to loss**: The loss function stays low while holonomy grows
4. **Creates bias**: The model develops systematic prediction errors on the "same" task

## Files

| File | Purpose |
|------|---------|
| `experiment.py` | Full cyclic curriculum experiment |
| `holonomy.py` | Holonomy/phase shift computation utilities |
| `README.md` | This file |

## How to Run

```bash
cd experiments/holonomy-phase
python experiment.py
```

**Runtime**: ~30 seconds on CPU. No GPU needed.

## Expected Results (if theory is correct)

```
Cycle 1: ||holonomy|| = 0.234567, angle = 12.34°
Cycle 2: ||holonomy|| = 0.345678, angle = 18.45°
Cycle 3: ||holonomy|| = 0.456789, angle = 24.56°
...

★ CONFIRMED: Holonomy accumulates while loss stays stable!
  This is systematic bias invisible to the loss function.
```

## What Failure Would Mean

If holonomy doesn't accumulate:
- The model's representations are path-independent
- Cyclic training doesn't create systematic bias
- The geometric phase analogy doesn't hold for this scale of model
- Try larger models or more diverse curricula

## Extensions

1. **Larger models**: Test on transformers, CNNs
2. **More complex curricula**: 5+ phases, varying difficulty
3. **Holonomy correction**: Add regularization to minimize holonomy
4. **Connection to grokking**: Does holonomy predict sudden generalization?
5. **Multi-model**: Compute holonomy between models in a fleet
