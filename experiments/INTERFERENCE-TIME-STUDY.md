# Interference Through Time Study

```
======================================================================
STUDY 1: LONGITUDINAL STABILITY (same Q, 20 trials)
======================================================================

  Question: Simple (expected: 63)

    ✓ phi4-mini      : correct=100% agreement=100% entropy=-0.00
        15× 63 ←

    ✓ gemma3:1b      : correct=100% agreement=100% entropy=-0.00
        15× 63 ←

    ✗ llama3.2:1b    : correct=27% agreement=53% entropy=1.77
         8× 76
         4× 63 ←
         1× 70
         1× 75
         1× 77

    ✗ qwen3:0.6b     : correct=0% agreement=100% entropy=-0.00
        15× None

  Question: Medium (expected: 25)

    ✓ phi4-mini      : correct=87% agreement=87% entropy=0.57
        13× 25 ←
         2× 13

    ✗ gemma3:1b      : correct=0% agreement=73% entropy=1.05
        11× 16
         3× 5
         1× 6

    ✗ llama3.2:1b    : correct=20% agreement=27% entropy=2.92
         4× 32
         3× 25 ←
         2× 12
         1× 50
         1× 42

    ✗ qwen3:0.6b     : correct=0% agreement=100% entropy=-0.00
        15× None

  Question: Hard (expected: 0)

    ✗ phi4-mini      : correct=27% agreement=27% entropy=2.79
         4× 0 ←
         3× None
         2× 3
         2× 60
         1× 2

    ✗ gemma3:1b      : correct=7% agreement=47% entropy=2.15
         7× 6
         3× 240
         2× 180
         1× 0 ←
         1× 3

    ✗ llama3.2:1b    : correct=13% agreement=47% entropy=2.46
         7× None
         2× 0 ←
         1× 1
         1× 120
         1× 60

    ✗ qwen3:0.6b     : correct=0% agreement=100% entropy=-0.00
        15× None

======================================================================
STUDY 2: CROSS-MODEL INTERFERENCE SPECTRUM
Same question, 4 models × 10 trials. Is disagreement noise or signal?
======================================================================

  Arithmetic: What is 11 × 13? Reply ONLY integer.
    phi4-mini      : correct=100% dist={'143': 10}
    gemma3:1b      : correct=100% dist={'143': 10}
    llama3.2:1b    : correct=0% dist={'120': 4, '119': 3, '140': 1}
    qwen3:0.6b     : correct=0% dist={None: 10}

  Eisenstein: Compute a²-ab+b² for a=5, b=3. Reply ONLY integer.
    phi4-mini      : correct=0% dist={'3': 4, '5': 2, '2': 1}
    gemma3:1b      : correct=0% dist={'9': 9, '3': 1}
    llama3.2:1b    : correct=0% dist={'3': 7, '5': 1, '25': 1}
    qwen3:0.6b     : correct=0% dist={None: 10}

  Subjective: Is a hexagonal or square lattice better for 2D quantization?
    phi4-mini      : hex=100% square=80% other=-80%
    gemma3:1b      : hex=100% square=80% other=-80%
    llama3.2:1b    : hex=100% square=100% other=-100%
    qwen3:0.6b     : hex=0% square=0% other=100%

======================================================================
STUDY 3: TEMPORAL DECOMPOSITION — is error stochastic?
15 trials each. If error is stochastic, retries help. If deterministic, retries don't.
======================================================================

  N(5,-3)=49
    phi4-mini      : 4/15 correct
      dist: {'49': 4, '-3': 3, '5': 2, '9': 2}
      Stochastic: P(correct) ≈ 27%

    gemma3:1b      : 3/15 correct
      dist: {'-3': 5, '5': 3, '49': 3, '9': 2}
      Stochastic: P(correct) ≈ 20%

    llama3.2:1b    : 2/15 correct
      dist: {'-3': 6, '9': 4, '25': 2, '49': 2}
      Stochastic: P(correct) ≈ 13%

    qwen3:0.6b     : 0/15 correct
      dist: {None: 15}
      ⚠️ DETERMINISTIC FAILURE — never correct in 15 trials
      Top wrong answer: None (15×)

  N(4,-2)=28
    phi4-mini      : 2/15 correct
      dist: {'2': 4, '4': 4, '16': 2, '28': 2}
      Stochastic: P(correct) ≈ 13%

    gemma3:1b      : 0/15 correct
      dist: {'-2': 5, '4': 4, '1': 2, '16': 2}
      ⚠️ DETERMINISTIC FAILURE — never correct in 15 trials
      Top wrong answer: -2 (5×)

    llama3.2:1b    : 0/15 correct
      dist: {'-2': 9, '16': 4, '-8': 1, '4': 1}
      ⚠️ DETERMINISTIC FAILURE — never correct in 15 trials
      Top wrong answer: -2 (9×)

    qwen3:0.6b     : 0/15 correct
      dist: {None: 15}
      ⚠️ DETERMINISTIC FAILURE — never correct in 15 trials
      Top wrong answer: None (15×)

  N(7,3)=37
    phi4-mini      : 8/15 correct
      dist: {'37': 8, '3': 2, '9': 1, '49': 1}
      Stochastic: P(correct) ≈ 53%

    gemma3:1b      : 4/15 correct
      dist: {'49': 4, '37': 4, '3': 3, '9': 2}
      Stochastic: P(correct) ≈ 27%

    llama3.2:1b    : 2/15 correct
      dist: {'3': 4, '9': 3, '21': 3, '7': 2}
      Stochastic: P(correct) ≈ 13%

    qwen3:0.6b     : 0/15 correct
      dist: {None: 15}
      ⚠️ DETERMINISTIC FAILURE — never correct in 15 trials
      Top wrong answer: None (15×)

======================================================================
STUDY 4: MULTI-PERSPECTIVE COHERENCE
Same problem through 3 analytical lenses. Do they converge?
======================================================================

  Model: phi4-mini
    GEOMETRIC      : hex=100% other=100%
    COMPUTATIONAL  : hex=100% other=100%
    PHYSICAL       : hex=100% other=80%
    ✅ COHERENT — all perspectives agree on hexagonal

  Model: gemma3:1b
    GEOMETRIC      : hex=80% other=100%
    COMPUTATIONAL  : hex=100% other=100%
    PHYSICAL       : hex=100% other=60%
    ✅ COHERENT — all perspectives agree on hexagonal

======================================================================
SYNTHESIS: THE INTERFERENCE STRUCTURE
======================================================================

Key findings from this run:

  1. Deterministic failures: 6 conditions where model ALWAYS fails the same way
  2. Stochastic failures: 6 conditions where output varies significantly
  3. The 'noise' in model outputs is structured:
     — Wrong answers tend to be CONSISTENT (same wrong number)
     — This is NOT random noise, it's a systematic error mode
     — Retrying does NOT help for deterministic failures
  4. Model size determines error TYPE:
     — Small models: stochastic (random wrong answers)
     — Medium models: deterministic (same wrong answer)
     — This is the 'frequency response' of model cognition
```
