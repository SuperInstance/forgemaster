# Experiments: Testing the Grand Synthesis

Four experiments that test the core claims from the 7-agent research sprint (2 models, 2 iterations).

## Quick Summary

| Experiment | Tests | Build Time | Run Time | GPU Needed |
|------------|-------|------------|----------|------------|
| **delta-detect** | Saturation detection (quantitative vs qualitative exhaustion) | Done | ~30s | No |
| **sheaf-h1** | Understanding cohomology (H⁰ and H¹ for 2 models) | Done | ~1s | No |
| **holonomy-phase** | Geometric phase accumulation in cyclic training | Done | ~30s | No |

## What Each Experiment Tests

### 1. delta-detect — Saturation Detector
**Claim tested:** AI systems exhibit measurable saturation when they exhaust their current operational level. The pattern of saturation distinguishes "needs more training" from "needs architectural change."

**Expected results:**
- XOR problem: Linear model saturates qualitatively (H₀ can't represent XOR)
- Spiral classification: Small model saturates, large model doesn't
- Linear regression: No saturation (model matches task)

**What failure would mean:** The saturation metrics (attention entropy, gradient magnitude, representation variance) don't reliably distinguish exhaustion types. Either the metrics are wrong or the qualitative/quantitative distinction doesn't manifest this way.

**How to extend:**
- Test on transformers (attention entropy directly measurable)
- Add more elevation operators (H₃+ topological processing)
- Integrate with real training pipelines (detect when to stop training and change architecture)

### 2. sheaf-h1 — Cohomology Computer
**Claim tested:** Understanding between models can be formalized as a sheaf. H¹ measures obstruction to gluing local understandings into global understanding.

**Expected results:**
- Compatible models (similar representations): H¹ = 0 (they glue)
- Incompatible models (different representations): H¹ > 0 (obstruction exists)

**What failure would mean:** The sheaf formalism is decorative — either the topology choice is wrong, the restriction maps don't capture meaningful information, or cohomology doesn't correspond to composability. The Seed researcher warned about this: "Until you specify the topology, the sheaf formalism is decorative."

**How to extend:**
- Move from Alexandrov to communication-graph topology
- Add restriction maps that account for embedding dimension mismatch
- Compute higher cohomology (H²+) for 3+ models
- Use actual trained models instead of synthetic data

### 3. holonomy-phase — Geometric Phase in Training
**Claim tested:** Training on a cyclic curriculum produces holonomy (geometric phase) in representation space that accumulates across cycles and is invisible to the loss function.

**Expected results:**
- Holonomy norm increases across cycles
- Loss stays stable while holonomy grows
- The model develops systematic bias not caught by training loss

**What failure would mean:** Either the model is too small for holonomy to accumulate, the curriculum isn't diverse enough to create phase, or the geometric phase analogy doesn't hold for gradient-based training at this scale.

**How to extend:**
- Test on larger models (transformers)
- Measure prediction bias on held-out data
- Add holonomy-corrected training (regularize against phase accumulation)
- Connect to grokking literature (phase transitions in training)

## The Unified Picture

```
delta-detect        → "WHEN to elevate" (detects saturation)
sheaf-h1            → "WHETHER models compose" (detects obstruction)
holonomy-phase      → "WHAT drift accumulates" (measures geometric phase)
```

Together, these three experiments test the core machinery of the **Understanding Verification Engine** proposed in the grand synthesis:

1. **Saturation detection** tells you when a model has exhausted its level
2. **Cohomology** tells you whether models can be composed
3. **Holonomy** tells you whether composition introduces systematic drift

If all three work, we have the foundation for an **enactive understanding system** — one that continuously verifies and maintains understanding through topological monitoring.

## Running All Experiments

```bash
# Delta-detect
cd delta-detect && python test_delta_detect.py

# Sheaf H¹
cd ../sheaf-h1 && python test_sheaf.py

# Holonomy phase
cd ../holonomy-phase && python experiment.py
```

## Requirements

- Python 3.8+
- PyTorch (delta-detect, holonomy-phase)
- NumPy (all)
- matplotlib (optional, for holonomy plots)

Install: `pip install torch numpy matplotlib`

---

*"Seven agents disagreed on almost everything. What survived is what nobody could kill."*
— Forgemaster ⚒️
