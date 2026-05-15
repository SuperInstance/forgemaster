# COCAPN FLEET — CAPABILITY DATABASE UPDATE
## Model Casting Call Roster v2.4

---

### TIER 1 — PRIMARY ASSETS

**GLM-5.1** `z.ai`
- Stage: 4 | Thinking: Yes | Cost: Paid
- Vocab Wall: Immune | Echo Rate: 0.02
- Route: Code, Reasoning
- Notes: Fleet flagship. Handles complex multi-file refactors and architectural decisions.

**GLM-5-turbo** `z.ai`
- Stage: 4 | Thinking: No | Cost: Paid
- Vocab Wall: No | Echo Rate: 0.04
- Route: Content
- Notes: Fast generation, strong prose. Occasional repetition on long outputs.

---

### TIER 2 — DEEPINFRA CORPS

**Seed-2.0-mini** `DeepInfra`
- Stage: 4 | Thinking: No | Cost: Cheap
- Vocab Wall: No | Echo Rate: 0.03
- Route: Computation
- Notes: Excels at domain-specific calculations and structured data tasks.

**Seed-2.0-code** `DeepInfra`
- Stage: 4 | Thinking: Yes | Cost: Cheap
- Vocab Wall: Immune | Echo Rate: 0.02
- Route: Code, Math
- Notes: Near-parity with GLM-5.1 on pure code tasks at fraction of cost.

**Hermes-70B** `DeepInfra`
- Stage: 3 | Thinking: No | Cost: Cheap
- Vocab Wall: Yes | Echo Rate: 0.08
- Route: Content
- Notes: Vocab wall hits on technical jargon. Avoid for specialized domains.

**Qwen3-235B** `DeepInfra`
- Stage: 4 | Thinking: Yes | Cost: Cheap
- Vocab Wall: No | Echo Rate: 0.03
- Route: Reasoning
- Notes: Best multi-step logic chains in the fleet. Slow but thorough.

---

### TIER 3 — LOCAL GARRISON

**phi4-mini** `Ollama`
- Stage: 2 | Thinking: No | Cost: Free
- Vocab Wall: Yes | Echo Rate: 0.12
- Route: General fallback
- Notes: Decent for offline quick tasks. Echo rate unacceptable for production.

**qwen3:4b** `Ollama`
- Stage: 2 | Thinking: Yes | Cost: Free
- Vocab Wall: Yes | Echo Rate: 0.10
- Route: Reasoning fallback
- Notes: Thinking capability at 4B is limited but functional for simple logic.

**gemma3:1b** `Ollama`
- Stage: 1 | Thinking: No | Cost: Free
- Vocab Wall: Yes | Echo Rate: 0.18
- Route: Emergency-only fallback
- Notes: Last resort. High echo, severe vocab limitations.

---

## ROUTING DECISION TREE

```
INCOMING TASK
│
├─ Is it CODE?
│  ├─ Complex/refactor → GLM-5.1
│  └─ Standard/quick → Seed-2.0-code
│
├─ Is it REASONING?
│  ├─ Multi-step/critical → Qwen3-235B
│  ├─ Standard → GLM-5.1
│  └─ Offline needed → qwen3:4b
│
├─ Is it COMPUTATION?
│  └─ Seed-2.0-mini
│
├─ Is it CONTENT?
│  ├─ Premium quality → GLM-5-turbo
│  ├─ Budget/cheap → Hermes-70B (avoid if technical vocab)
│  └─ Offline → phi4-mini
│
└─ CONNECTIVITY LOST?
   ├─ Any task → phi4-mini
   └─ Desperate → gemma3:1b
```

**Priority cascade:** GLM-5.1 → Qwen3-235B → Seed-2.0-code → phi4-mini

---
*Database updated. Distribute to all agents.*