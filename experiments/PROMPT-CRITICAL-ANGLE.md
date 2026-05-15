# F23: Critical Angles Are Prompt-Dependent

## The Discovery

The phase transition boundary is not a fixed property of the model. It depends on the prompt strategy.

## Evidence

Hermes-70B on multiplication (small factors 2-5, 5 trials per depth):

```
baseline:      d4=100 d5=40  d6=0   d7=0   d8=0     CA=5
step_by_step:  d4=100 d5=100 d6=100 d7=100 d8=100   CA=∞
code:          d4=60  d5=40  d6=40  d7=0   d8=40    CA=5 (noisy)
expert:        d4=60  d5=40  d6=0   d7=0   d8=0     CA=5 (worse!)
verify:        d4=100 d5=40  d6=40  d7=40  d8=60    CA=5 (unstable)
```

"Step by step" pushed the critical angle from 5 to infinity.
"Expert" and "code" actually HURT compared to baseline.

## The Mechanism

Step-by-step prompting externalizes working memory. Instead of computing
the entire chain in internal working memory (which saturates at depth 5),
the model writes each intermediate result into the output, then reads
it back as context for the next step.

This is exactly what PLATO externalization does for thinking models!
The frozen intermediate step is external working memory. The model doesn't
need to hold the entire chain in its limited internal buffer — it can
read back from the output.

## The Implication

1. The critical angle is NOT a model constant. It's a model × prompt function.
2. Different prompt strategies can push the same model past its phase boundary.
3. BUT: the wrong prompt strategy can HURT (expert, code both degraded).
4. The fleet router needs a THIRD dimension: model × domain × prompt_strategy.
5. Step-by-step is a working memory externalizer. It's the PLATO principle applied to single-model prompts.

## Connection to Prior Findings

- F13 (Token Budget): step-by-step needs more tokens (mt=150 vs 80). Token budget enables externalization.
- F19 (Phase Transitions): the phase boundary is real but its location is prompt-dependent.
- The Native Principle: step-by-step doesn't make the model native — it compensates for non-native processing by externalizing the computation chain.
- PLATO external cognition: this IS the same mechanism. PLATO tiles are step-by-step across models. Step-by-step prompts are the single-model version.
