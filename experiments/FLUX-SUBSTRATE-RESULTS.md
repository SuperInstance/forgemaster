# Flux Substrate Translation Experiment — Results

## Overview

- **Total chains tested:** 48
- **Valid chains:** 26
- **Errors:** 8
- **Overall survival rate:** 65.4%

## 1. Translation Mode Comparison

| Mode | Total | Correct | Rate |
|------|-------|---------|------|
| DIRECT | 17 | 12 | 70.6% |
| ANTI_TRANSLATED | 9 | 5 | 55.6% |

**Best mode:** DIRECT

**Anti-translation vs Direct:** Anti=55.6%, Direct=70.6%, Δ=-15.0%
Anti-translation does NOT help signal survival.

## 2. Survival by Difficulty

| Difficulty | Total | Correct | Rate |
|------------|-------|---------|------|
| easy | 14 | 10 | 71.4% |
| hard | 12 | 7 | 58.3% |

## 3. Signal Decay (1-hop vs 2-hop)

- **1-hop survival:** 69.2%
- **2-hop survival:** 61.5%
- **Signal decay:** 7.7% (lost in second translation)

## 4. Substrate Distance (1-hop model pairs)

| Source → Target | Total | Correct | Rate |
|-----------------|-------|---------|------|
| seed-mini→hermes-70b | 2 | 2 | 100.0% |
| hermes-70b→seed-mini | 4 | 4 | 100.0% |
| qwen-35b→hermes-70b  | 1 | 1 | 100.0% |
| seed-mini→qwen-35b   | 2 | 1 | 50.0% |
| hermes-70b→qwen-35b  | 4 | 1 | 25.0% |

**Key question:** Does Seed→Hermes survive better than Hermes→Qwen?

## 5. Per-Function Survival

| Function | Difficulty | Total | Correct | Rate |
|----------|------------|-------|---------|------|
| sort | easy | 14 | 10 | 71.4% |
| moving_average | hard | 12 | 7 | 58.3% |

## 6. Detailed Results (1-hop, all modes)

| Chain | Function | Mode | Correct | Details |
|-------|----------|------|---------|---------|
| seed-mini → hermes-70b | sort | DIRECT | ✓ | All tiles pass |
| seed-mini → qwen-35b | sort | DIRECT | ✓ | All tiles pass |
| hermes-70b → seed-mini | sort | DIRECT | ✓ | All tiles pass |
| hermes-70b → qwen-35b | sort | DIRECT | ✗ | Could not extract function |
| qwen-35b → seed-mini | sort | DIRECT | ✗ | Original incorrect: Could not extract function |
| qwen-35b → hermes-70b | sort | DIRECT | ✓ | All tiles pass |
| hermes-70b → seed-mini | sort | ANTI_TRANSLATED | ✓ | All tiles pass |
| hermes-70b → qwen-35b | sort | ANTI_TRANSLATED | ✗ | Could not extract function |
| qwen-35b → seed-mini | sort | ANTI_TRANSLATED | ✗ | Original incorrect: Could not extract function |
| qwen-35b → hermes-70b | sort | ANTI_TRANSLATED | ✗ | Original incorrect: Could not extract function |
| seed-mini → hermes-70b | moving_average | DIRECT | ✓ | All tiles pass |
| seed-mini → qwen-35b | moving_average | DIRECT | ✗ | Could not extract function |
| hermes-70b → seed-mini | moving_average | DIRECT | ✓ | All tiles pass |
| hermes-70b → qwen-35b | moving_average | DIRECT | ✓ | All tiles pass |
| qwen-35b → seed-mini | moving_average | DIRECT | ✗ | Original incorrect: Could not extract function |
| qwen-35b → hermes-70b | moving_average | DIRECT | ✗ | Original incorrect: Could not extract function |
| hermes-70b → seed-mini | moving_average | ANTI_TRANSLATED | ✓ | All tiles pass |
| hermes-70b → qwen-35b | moving_average | ANTI_TRANSLATED | ✗ | Could not extract function |
| qwen-35b → seed-mini | moving_average | ANTI_TRANSLATED | ✗ | Original incorrect: Could not extract function |
| qwen-35b → hermes-70b | moving_average | ANTI_TRANSLATED | ✗ | Original incorrect: Could not extract function |

## 7. Key Findings

   1. **Overall survival rate:** 65.4% — Moderate signal transmission across substrates.
   2. **Best translation mode:** DIRECT
   3. **Anti-translation does NOT help** — direct code transfer works better by 15.0%. The opposite-vocabulary approach loses signal.
   4. **Signal decay:** 7.7% lost per hop. After 2 translations, signal is well-preserved.
   5. **Difficulty gradient:** Easy=71.4%, Hard=58.3%. Signal loss is consistent across difficulties.
   6. **Substrate distance:** Best pair=seed-mini→hermes-70b (100.0%), Worst pair=hermes-70b→qwen-35b (25.0%)

## 8. Conclusion

The Flux thesis is **not strongly supported** by this experiment. Direct code transfer
outperforms opposite-vocabulary explanations, suggesting that code is already a universal
substrate across models, and that natural-language rephrasing (in any vocabulary) adds noise.

Signal decay is low — tiles survive multi-hop translation well. The PLATO tile protocol
should work across heterogeneous model fleets.
