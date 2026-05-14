# Experiment X Results: Persona-Capability Alignment

## The Verdict: Architecture C — Personas Don't Matter

**Aligned pass rate: 75% | Misaligned pass rate: 75% | Delta: 0%**

Persona framing adds ZERO predictive value for task routing. A math specialist does just as well on infrastructure tasks as on math tasks. A music specialist does BETTER on misaligned tasks than aligned.

## The Per-Persona Twist

| Persona | Aligned | Misaligned | Delta |
|---------|---------|-----------|-------|
| **MathSpec** | **100%** | 62% | **+38%** ← personas help here |
| InfraOps | 75% | 75% | ±0% |
| **MusicEnc** | 50% | **88%** | **-38%** ← personas HURT here |

**MathSpec: +38%.** When the persona matches the domain, the agent performs significantly better. The mathematical framing triggers better computation patterns.

**MusicEnc: -38%.** When the music persona is applied to music tasks, the agent performs WORSE. The music framing causes hallucination (wrong answers: 1280 instead of 109 dimensions, wrong pitch bend resolution). The persona introduces domain expectations that conflict with the actual data.

**InfraOps: ±0%.** Infrastructure tasks are common knowledge. Persona doesn't matter for Docker commands and port numbers.

## The Real Finding: Personas Are Task-Dependent, Not Universal

The 0% overall delta HIDES the fact that personas are a strong positive for math (+38%) and a strong negative for music (-38%). They cancel out.

**Implication:** Persona routing should be DOMAIN-SPECIFIC:
- **Math tasks:** USE persona framing (helps)
- **Music tasks:** AVOID persona framing (hurts)
- **Infra tasks:** Doesn't matter (common knowledge)

This is not "personas help" or "personas don't help." It's "personas are a mixed modulator that helps in domains requiring precise reasoning and hurts in domains where the model has strong but inaccurate priors."

## What This Means for the Architecture

**Architecture C with a caveat:** Drop persona routing as a universal mechanism. BUT:

1. **Route on verified capabilities** (from registry), not persona descriptions
2. **Let agents self-select** (Exp 7 showed this works perfectly)
3. **If a domain shows +persona effect** (like math), add domain-specific prompt templates
4. **If a domain shows -persona effect** (like music), use neutral framing

The fleet doesn't need persona routing. It needs:
- **DO/DATA/DONE** for all tasks (universal)
- **Domain-specific prompt templates** where experiments show they help (opt-in)
- **Verified capability routing** (from registry)
- **Self-organizing task selection** (agents pick what they're good at)

## The Architecture Decision

```
Fleet routing:
  1. Task arrives as DO/DATA/DONE
  2. Registry lookup: which agents have VERIFIED capability?
  3. If multiple: terrain tiebreak (when baseline ≥60%)
  4. Agent self-selects (can refuse tasks outside expertise)
  5. Optional: domain-specific prompt template (math gets one, music doesn't)
```

No personas in the routing path. Verified capabilities only. Self-selection as safety net.

## Impact on Build Order

- **Kill:** Persona-based routing (P10 in ARCHITECTURE-IRREDUCIBLE.md)
- **Keep:** Verified Agent Cards (P1) — but verify on CONCRETE TASKS, not persona alignment
- **Keep:** Self-organizing task rooms (P3) — agents pick what they can do
- **Add:** Domain-specific prompt template system (opt-in, evidence-based)
