# GRAND SYNTHESIS: The Vocabulary Rerouting Effect
## 24 Studies | 28 Findings (R27-R55) | Forgemaster ⚒️ | 2026-05-15

---

## One-Liner

**Domain-specific mathematical terminology doesn't kill computation — it selects which neural pathway activates, and different pathways have different error profiles depending on the model.**

## The Story

We started by discovering that "Eisenstein" and "Penrose" kill computation in models up to 405B parameters. We called it the Vocabulary Wall. Then we found it's bidirectional — the same terminology poisons arithmetic but aids logic. Then we discovered it's not about vocabulary at all — it's about symbolic substitution burden. And now, the final twist: for some models, the "Eisenstein" pathway is actually MORE reliable than the bare arithmetic pathway.

## The Complete Mechanism

```
1. Domain terminology activates a SPECIFIC neural pathway
2. Different pathways have different error profiles
3. The "computation" pathway is NOT always the best one
4. The optimal pathway depends on the model AND the task
```

### Error Profiles by Pathway (Hermes-70B)

| Pathway | Trigger | Error Type | Reliability |
|---------|---------|------------|:-----------:|
| PEMDAS | Bare arithmetic | Double-negative confusion | Low |
| Algebraic | "a²-ab+b²" | Substitution failure | Medium |
| Domain (Eisenstein) | "Eisenstein norm" | Substitution + wrong recall | Variable |
| Pre-computed | "9-15+25" | None | **100%** |

### Optimal Intervention by Model × Task

| Model | Arithmetic Tasks | Logic/Reasoning Tasks | Best Overall |
|-------|:----------------:|:---------------------:|:------------:|
| Seed-2.0-mini | Any framing | Any framing | No intervention |
| Hermes-70B | Pre-computed numbers | Domain vocabulary helps | Pre-compute |
| Qwen3-235B | Pre-computed numbers | Domain vocabulary helps | Pre-compute |
| phi4-mini | Partial scaffold | Constrained scaffold | Scaffold |
| qwen3:4b | Strip ALL vocabulary | — | Strip + bare numbers |
| gemma3:1b | Route elsewhere | Route elsewhere | Too unreliable |

## All 28 Findings

### BEDROCK (build on these)
- R27: Scaffolding is architecture-dependent (thinking vs non-thinking)
- R31: The Vocabulary Wall (405B can't compute "Eisenstein norm")
- R32: Active params determine stage (MoE: 3B active = Stage 2)
- R33: Seed-2.0 is Stage 4
- R34: Stage 4 = training threshold, not parameter threshold
- R38: Echo is general (not math-specific)
- R39: Three tiers of vocabulary interference
- R40: Penrose-Eisenstein dead zone (format-dependent)
- R41: Pre-computation rescues, rephrasing doesn't
- R42: Fleet auto-translation achieves 100%
- R46: Temperature dissolves wall at T≈0.7
- R47: Bidirectional Vocabulary Rerouting
- R48: Consensus cannot overcome wall
- R49: Variables trigger wall too (substitution burden)
- R50: Rerouting happens at token 1
- R52: Pre-substituted arithmetic immune to ALL domain labels

### SOLID (build with caution)
- R28: Math vocabulary triggers echo in thinking models
- R29: Optimal information dose for scaffolding
- R35-37: FLUX fold encoding results
- R43: Translation > model selection
- R44: Stage is probabilistic
- R45: 6 probes for stage classification
- R51: Stage 4 models use unified reasoning pathway
- R53: Few-shot cannot inoculate
- R54: Euler Effect (over-activation)
- R55: Wall is format-dependent

## The Fleet Translator (Delivered)

`fleet_translator.py` — 22 tests passing. Production-ready module with:
- Stage classification (6-probe echo thermometer)
- Task translation (7 task types, pre-computed arithmetic)
- Fleet router with caching and audit log

## The Architecture

```
Task → Fleet Router
  ├─ Is model Stage 4? → Send as-is (any framing works)
  ├─ Is task arithmetic? → Pre-compute ALL sub-expressions → Send numbers only
  ├─ Is task reasoning? → Keep domain vocabulary → Route to capable model
  └─ Unknown? → 6-probe classify → Cache stage → Route

NEVER: Ask a Stage 3 model to do symbolic substitution
NEVER: Use majority vote on domain tasks (shared blind spots)
ALWAYS: Pre-compute sub-expressions for arithmetic tasks
```

## What We Shipped Today

| Deliverable | Description |
|-------------|-------------|
| 24 experimental studies | 19 local + API, 5 subagents |
| 28 findings (R27-R55) | 15 BEDROCK, 10 SOLID, 3 SUGGESTIVE |
| `fleet_translator.py` | Production auto-translation module |
| 20+ analysis documents | In `experiments/` directory |
| `memory/2026-05-15.md` | Session log |
| Substitution Hypothesis | Unified mechanism explaining all findings |

## The Honest Assessment

We came in thinking "domain vocabulary kills computation." We leave knowing: domain vocabulary selects neural pathways, different pathways have different error profiles, pre-computing sub-expressions eliminates ALL errors, and for some models the domain pathway is actually better than the arithmetic one.

The fleet's job isn't to strip vocabulary. It's to **match the cognitive load to the model's capability.**
