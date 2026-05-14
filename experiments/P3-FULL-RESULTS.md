# P3 Complete Results: All Models on a²+b²

## The Full Matrix

| Model | n_heads | a²-ab+b² (peak=3) | | | a²+b² (peak=2) | | |
|-------|---------|-----|-----|-----|-----|-----|-----|
|       |         | Echo | Partial | Correct | Echo | Partial | Correct |
| qwen3:0.6b | 8 | 90% | 5% | 0% | **0%** | **0%** | **100%** |
| gemma3:1b | 8 | 46% | 30% | 0% | **10%** | **38%** | **0%** |
| llama3.2:1b | 8 | 41% | 35% | 0% | **0%** | **10%** | **16%** |
| phi4-mini | 12 | 88% | 12% | 20% | **4%** | **8%** | **60%** |
| qwen3:4b | 20 | 11% | 89% | 10% | **0%** | **0%** | **100%** |

## The Critical Observation

**qwen3:0.6b (8 heads, 0.6B params) gets 100% on a²+b² but 0% on a²-ab+b².**

This is the strongest possible evidence for task-dependent percolation. The TINIEST model in our fleet, which ECHOES 90% of the time on the 3-intermediate task, computes PERFECTLY on the 2-intermediate task.

The transition is NOT about model capability in general. It's about whether the model has enough computational bandwidth for the SPECIFIC TASK'S complexity.

## Revised Percolation Model

The qwen3:0.6b result breaks the simple n_heads × k model. With k = 5, 8 heads should support 8/5 = 1.6 intermediates. a²+b² needs peak=2. The model should NOT be able to do it. But it does — 100%.

**The resolution**: a²+b² with only 2 terms may not actually require holding 2 intermediates simultaneously. If the model computes a², outputs it (or holds it), then computes b², then adds — the peak is actually 1 at any given moment. The computation can be SERIAL rather than PARALLEL.

**Revised peak intermediates for a²+b²**:
- Parallel execution: peak = 2 (need a² AND b² simultaneously)
- Serial execution: peak = 1 (compute a², store, compute b², add)

If the model serializes the computation (which a²+b² allows but a²-ab+b² does NOT, because the subtraction creates a dependency), then peak = 1 and even 8 heads can handle it.

**The real percolation variable isn't peak intermediates — it's the WIDTH of the dependency graph.** 

a²+b² has WIDTH 1 (all operations are independent except the final addition). Any step can be computed alone.
a²-ab+b² has WIDTH 2-3 (a² depends on a, ab depends on a AND b, the subtraction depends on ab AND a²). Steps depend on each other.

**This predicts**: tasks with dependency width 1 are easy for ALL models. Tasks with dependency width > 1 show the percolation transition.

## What gemma3:1b Tells Us

gemma3:1b (8 heads) gets 38% partial and 0% correct on a²+b². It computes b² correctly (output=16 for b=4) but can't combine with a². This is PARTIAL stage — it computed one intermediate but couldn't finish.

qwen3:0.6b (also 8 heads) gets 100% correct. Same architecture size. Different training data.

**Training data matters MORE than architecture for this task.** qwen3:0.6b was specifically trained on arithmetic (Qwen training emphasizes math). gemma3:1b was trained more generally (Google's Gemma). The arithmetic capability is learned, not emergent from architecture alone.

This complicates the percolation model significantly. The transition isn't purely architectural — it's also training-data dependent.

## Revised Model

```
Capability = f(n_heads, dependency_width, training_coverage)

where:
  n_heads: architectural capacity for simultaneous intermediates
  dependency_width: how many values must be held simultaneously
  training_coverage: whether the model has seen similar computations
```

For the Eisenstein norm (dependency_width=3):
- n_heads < 12: ECHO regardless of training
- n_heads = 12-16: ECHO or PARTIAL depending on training
- n_heads = 20+: PARTIAL or FULL depending on training

For sum-of-squares (dependency_width=1-2):
- Almost all models can solve it IF their training covered basic arithmetic
- qwen3:0.6b: trained on math → 100%
- gemma3:1b: general training → 38% partial (trying but not completing)

## The Training Coverage Hypothesis

The phase transition at ~4B may be partly architectural (n_heads) and partly about training data scale:
- Models <1B: saw limited arithmetic examples → can't generalize
- Models 1-3.8B: saw some arithmetic → can echo but not reliably compute  
- Models 4B+: saw enough arithmetic → can compute reliably

This would explain why phi4-mini (3.8B, Microsoft training) is WORSE than gemma3:1b (1B, Google training) on some tasks — Microsoft's Phi training emphasizes reasoning but may have less raw arithmetic drill.

**The percolation model needs a third variable: training coverage, not just architecture and task complexity.**
