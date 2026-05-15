# Study 49: Label-Specific Paradox

## Date: 2026-05-15
## Model: Seed-2.0-mini (Stage 4)
## Refines: Study 47 Labeled Paradox

### Finding: The paradox is label-specific, not universal

| Condition | Correct | Tokens | Notes |
|-----------|:-------:|-------:|-------|
| bare (no label) | ✓ | 387 | Direct computation, fastest |
| "Eisenstein norm" | ✓ | 1170 | 3× tokens, still correct |
| "Hermitian form" | ✓ | 408 | Minimal overhead |
| "quadratic form" | ✓ | 397 | Minimal overhead |
| "explain" (conceptual) | ✓ | 513 | Conceptual framing works |
| N(5,-3) notation | ✗ | 723 | Extracts "5" — wrong retrieval |
| step-by-step pre-computed | ✗ | 488 | Verifies instead of computing |

### Key Insights

1. **Labels don't universally hurt Stage 4.** Only specific notation patterns cause failure.
2. **N(a,b) notation** triggers wrong retrieval — model parses "N(5,-3)" as "extract first value" instead of computing the norm.
3. **Pre-computed step-by-step** hurts because the model switches to verification mode instead of computation mode. It sees the pre-computed answer and tries to verify it, sometimes failing.
4. **Bare notation is fastest AND most accurate** for Stage 4 — no label needed, no step-by-step needed.
5. **Token count is a signal**: correct answers use 387-513 tokens; wrong answers use 488-723 tokens (more reasoning = more chance of error).

### The Refined Two-Path Model (V6.1)

```
Stage 4 (Seed-2.0):
  Pure notation → [direct computation] → CORRECT (387 tok, fastest)
  Labeled notation → [conceptual path] → CORRECT (400-1170 tok, slower but right)
  N(a,b) → [retrieval path] → WRONG (extracts values, 723 tok)
  Pre-computed steps → [verification path] → WRONG (verifies instead of computes)
  
Stage 3 (Hermes):
  Pure notation → [no pathway] → WRONG (defaults)
  Labeled notation → [activation path] → SOMETIMES CORRECT (depends on label)
  Step-by-step → [language path] → CORRECT (needs language framing)
```

### Implication for fleet_translator_v2

For Stage 4 models:
- **DO**: Send bare notation (a² − ab + b² where a=5, b=-3)
- **DON'T**: Pre-compute answers or use N(a,b) notation
- **OPTIONAL**: Add domain labels (doesn't hurt for most labels, just slower)

For Stage 3 models:
- **DO**: Add domain labels + convert to natural language
- **DON'T**: Send bare notation (they can't compute from it)
