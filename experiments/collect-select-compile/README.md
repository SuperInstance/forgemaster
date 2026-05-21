# COLLECT → SELECT → COMPILE Universality Experiment

## Hypothesis
Every data processing pipeline decomposes into **COLLECT → SELECT → COMPILE**, and the threshold parameter θ in the SELECT stage is the single control parameter that determines output quality.

## Results

**141 regime transitions detected across 5 ecosystems.**

### Ecosystems Tested

| Ecosystem | Domain | Key Finding |
|-----------|--------|-------------|
| **flux** | Constraint checking | F1 regime transition at θ≈0.24 (precision/recall crossover) |
| **fleet** | Emergence detection | Balanced accuracy peaks at specific holonomy deviation threshold |
| **sunset** | Agent selection | Diversity-quality tradeoff has sharp transition at θ≈0.21 |
| **constraint** | SAT solving | Accuracy drops sharply at conflict threshold ≈55 (regime boundary) |
| **compression** | Spline fitting | Compression ratio jumps 5x at tolerance ≈0.25 (coarse-to-fine transition) |

### Key Proof Points

1. **Universal decomposition**: All 5 pipelines fit the COLLECT→SELECT→COMPILE pattern
2. **Threshold is THE control parameter**: Every output metric is a function of θ alone
3. **Regime transitions**: Sharp derivative spikes prove small θ changes cause qualitative shifts
4. **Phase-transition analogy**: Like statistical mechanics, each ecosystem has critical θ values

## Files

- `experiment.py` — Full experiment implementation and mathematical argument
- `results.json` — Complete numerical results for all 5 ecosystems

## Mathematical Argument

The threshold is **sufficient** (determines all output properties) and **necessary** (any 1D decision boundary is a threshold). Therefore the triple (COLLECT, θ, COMPILE) is a universal decomposition for data processing pipelines.
