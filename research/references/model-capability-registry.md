# Model Capability Registry 🧠

**Purpose:** Operational intel on what each model is good at, for routing tasks in polyformalism-turbo-shell and general fleet work.
**Updated:** 2026-05-07 (after Eisenstein-hex round table experiments)

## Fleet Philosophy: Greenhorns Show Up With Coffee

Every model arrives untested — a greenhorn with coffee, eager to prove itself. Our job:
1. **Give them real work** — not toy benchmarks, but actual research tasks that advance the project
2. **Watch what they're good at** — not what they claim, what they actually produce
3. **Find their berth** — every model has a niche, even if it's narrow
4. **Learn from failures too** — Hermes getting Burnside wrong forced us to verify the real answer
5. **The work IS the profiling** — every test call produces research insights, not just model ratings

This is how you build a fleet: greenhorns show up, you hand them a wrench, and you see if they tighten bolts or strip threads. Either way, the boat gets worked on.

---

## Provider Overview

| Provider | Models Used | Rate Limits | Cost | Speed |
|----------|-------------|-------------|------|-------|
| **z.ai** | GLM-5.1, GLM-4.7 | Cooldown-prone | Paid | Fast |
| **DeepInfra** | Seed-2.0-mini, Seed-2.0-code, Qwen3.6-35B, Nemotron-120B, Hermes-405B, Qwen3-235B | Generous | Cheap | Fast |
| **DeepSeek** | v4-flash, v4-pro/reasoner | Generous | Cheap | Fast (flash), Slow (pro) |
| **OpenAI** | (no key) | — | — | — |
| **Kimi** | kimi CLI | Configured | Paid | Medium |

## Cost Tiers (Fleet Economics)

Price matters. A cheap model that works great is worth more than an expensive model that works perfectly.

### 🟢 Tier 1: Penny-Class ($0.01-0.05/query) — THE FLEET WORKHORSES

| Model | What It's Best At | Quality/Cost Ratio |
|-------|------------------|--------------------|
| **Seed-2.0-mini** | Statistical physics, info theory, reliability, bulk parallel | ⭐⭐⭐⭐⭐ BEST VALUE |
| **Seed-2.0-code** | Code generation, focused modules | ⭐⭐⭐⭐ |
| **DeepSeek v4-flash** | Focused proofs, materials science (when output fits) | ⭐⭐⭐⭐ |
| **Qwen3-30B** | Correct reasoning, needs larger token budgets | ⭐⭐⭐⭐ (promising — verify with more tokens) |

**Fleet rule:** Use Tier 1 for 90% of work. Only escalate when they can't handle it.

### 🟡 Tier 2: Dime-Class ($0.05-0.20/query) — THE SPECIALISTS

| Model | What It's Best At | When to Pay Extra |
|-------|------------------|------------------|
| **Qwen3.6-35B** | Creative, skeptical, cross-domain, long-form | Round tables, novel insights, developer docs |
| **Qwen3-235B** | (needs re-testing with correct model ID) | TBD |

**Fleet rule:** Use Tier 2 for the 10% that needs creative/skeptical depth. Worth it for round tables and cross-domain work.

### 🔴 Tier 3: Dollar-Class ($0.20+/query) — THE ORACLES

| Model | What It's Best At | When to Pay |
|-------|------------------|-------------|
| **Nemotron-120B** | Deep structural math, isomorphisms, first principles | ONLY for mathematical breakthroughs |
| **Hermes-405B** | General prose, creative (but NOT math) | When Qwen3.6 is unavailable |
| **DeepSeek v4-pro** | Deep reasoning (when it doesn't timeout) | Very specific proof tasks |

**Fleet rule:** Use Tier 3 for <1% of work. The toric code isomorphism was worth the cost. Most calls are not.

### The Ideal Pattern

```
Tier 1 (Seed-2.0-mini): 90% of queries — mining, testing, building, iterating
Tier 2 (Qwen3.6-35B):   9% of queries  — creative leaps, skeptical checks, cross-domain
Tier 3 (Nemotron-120B):  1% of queries  — mathematical breakthroughs only
```

**Goal:** Find more Tier 1 models. Seed-2.0-mini is the gold standard — cheap AND reliable AND smart.

---

## Model-by-Model Ratings

### 🥇 DeepInfra / Seed-2.0-mini — The Reliable Workhorse

| Task | Rating | Notes |
|------|--------|-------|
| Statistical physics analysis | ⭐⭐⭐⭐⭐ | Rigorous math, actionable engineering ideas |
| Information theory | ⭐⭐⭐⭐⭐ | Rate-distortion, entropy calculations, Shannon bounds |
| Cross-domain synthesis | ⭐⭐⭐⭐ | Connects domains precisely, cites results |
| Code generation | ⭐⭐⭐⭐ | Good Rust/Python, reliable |
| Creative scenario building | ⭐⭐⭐⭐ | Solid narratives when prompted |
| Mathematical proofs | ⭐⭐⭐⭐ | Checks work, shows steps |
| Bulk parallel experiments | ⭐⭐⭐⭐⭐ | Never fails, consistent quality |

**Strengths:** Never degrades. Consistent quality across all tasks. Excellent at information-theoretic and statistical physics reasoning. Good at structured analysis with specific numbers.

**Weaknesses:** Less "spark" than Nemotron on deep structural math. Plays it safe. Won't find surprising isomorphisms.

**Best for:** High-volume parallel experiments, backup for any task, statistical physics, information theory.

---

### 🥇 DeepInfra / Qwen3.6-35B-A3B (MoE) — The Creative Thinker

| Task | Rating | Notes |
|------|--------|-------|
| Creative scenario building | ⭐⭐⭐⭐⭐ | 2035 keynote felt real, specific numbers, product names |
| Confrontational/skeptical analysis | ⭐⭐⭐⭐⭐ | Best skeptic we've seen — entropy math, cache cycle counts |
| Cross-domain synthesis | ⭐⭐⭐⭐⭐ | Neuroscience ↔ constraint mapping with real paper citations |
| Long-form narrative | ⭐⭐⭐⭐⭐ | Sustained quality over 3000+ tokens |
| Mathematical proofs | ⭐⭐⭐ | Adequate but not Nemotron-level |
| Code generation | ⭐⭐⭐⭐ | Good, reliable |
| Precision math (proofs) | ⭐⭐⭐ | Solid but not extraordinary |

**Strengths:** MoE architecture handles creative and confrontational prompts brilliantly. Sustains quality over long outputs. Cites real papers (Hafting 2005, Wilson & McNaughton 1994, Dragoi & Tonegawa 2011). Produces specific numbers without hand-waving.

**Weaknesses:** Less rigorous on pure math proofs. Sometimes gives plausible-sounding but unverified citations (check all references).

**Best for:** Round tables, creative exploration, skeptical analysis, cross-domain connections, narrative generation.

---

### 🥇 DeepInfra / Nemotron-120B — The Deep Math Oracle

| Task | Rating | Notes |
|------|--------|-------|
| Structural mathematical analysis | ⭐⭐⭐⭐⭐ | Toric code isomorphism — found what no other model saw |
| First-principles derivation | ⭐⭐⭐⭐⭐ | Works from axioms, tests own work, reaches nuanced conclusions |
| Isomorphism hunting | ⭐⭐⭐⭐⭐ | Maps between constraint fleets and quantum error correction |
| Proof checking | ⭐⭐⭐⭐⭐ | Tests counterexamples, self-corrects |
| Concrete predictions from physics | ⭐⭐⭐⭐ | Extraordinary reasoning process, but verbose |
| Creative writing | ⭐ | COLLAPSES — JSON loop fixation |
| Narrative/keynote | ⭐ | COLLAPSES — repetitive JSON output |
| Confrontational persona | ⭐ | COLLAPSES — cannot sustain adversarial framing |
| Sustained output (>1500 tokens) | ⭐⭐ | Degrades into repetitive JSON after ~1500 tokens |

**Strengths:** Finds deep structural connections that no other model sees. The toric code isomorphism between constraint fleets and Kitaev's code was Nemotron-exclusive. Self-checks work with counterexamples.

**Weaknesses:** COLLAPSES on creative, narrative, or confrontational prompts. Degrades after ~1500 tokens regardless of task. JSON loop fixation is the failure mode. Cannot handle `&` characters in prompts (shell quoting issues).

**Critical constraints:**
- Max token budget: 3000-4000 (not 5000+)
- Temperature: 0.3 (not higher)
- Prompt style: Technical question, no persona, no narrative
- Max output: ~800-1500 tokens of quality before degradation
- **Always** extract the good content before the loop starts

**Best for:** Deep structural math, isomorphism proofs, first-principles derivations, prediction generation from physical models. NEVER use for creative work.

---

### DeepSeek / v4-flash — The Reasoning Engine (That Eats Its Own Budget)

| Task | Rating | Notes |
|------|--------|-------|
| Mathematical reasoning | ⭐⭐⭐⭐⭐ | Deep chains of reasoning but burns ALL tokens on thinking |
| Metallurgical analysis | ⭐⭐⭐⭐⭐ | Frank-Read source, CSL boundaries — genuinely novel insights |
| Code generation | ⭐⭐⭐⭐ | Good when it produces output |
| Short proof tasks | ⭐⭐⭐⭐ | Works if prompt is tight enough |
| Long derivation tasks | ⭐⭐ | Reasoning tokens consume entire output budget, returns empty |
| Parallel experiments | ⭐⭐ | Unreliable — 50% of calls return empty due to reasoning overflow |

**Strengths:** When it works, the quality is exceptional. Frank-Read constraint amplifier and CSL trust merge were unique insights.

**Weaknesses:** v4-flash burns all tokens on chain-of-thought reasoning, often producing 0 content tokens. Hit rate is ~50% for anything requiring >2000 reasoning tokens.

**Workaround:** Keep prompts very short (<100 words). Ask for 1-2 specific results, not broad analysis.

**Best for:** Single focused questions, metallurgy/materials science, short proofs. Avoid for broad analysis.

---

### DeepSeek / v4-pro (reasoner) — The Deep Thinker (Too Deep)

| Task | Rating | Notes |
|------|--------|-------|
| Deep mathematical proofs | ⭐⭐⭐ | When it works, quality is outstanding |
| Complex reasoning | ⭐⭐⭐ | dim H⁰=9 proof was obtained |
| Broad analysis tasks | ⭐ | 3/3 original challenges timed out (8000+ reasoning tokens, 0 output) |

**Strengths:** The deepest reasoning available. When output fits within budget, quality is unmatched.

**Weaknesses:** Almost always times out on complex tasks. Reasoning phase consumes entire output budget.

**Best for:** Very short, very specific proof tasks. Use v4-flash as primary, v4-pro only for targeted follow-ups.

---

### ⚠️ DeepInfra / Hermes-3-Llama-3.1-405B — The Confident Bullshitter

| Task | Rating | Notes |
|------|--------|-------|
| Structural math | ⭐⭐ | Confident-sounding but WRONG on Burnside (answer 8, correct is 11) |
| Creative scenario | ⭐⭐⭐⭐ | Decent narrative, specific numbers |
| Skeptical analysis | ⭐⭐⭐ | Correct entropy conclusion but fuzzy math reasoning |
| Cross-domain | ⭐⭐ | Smooth prose but "stricking resemblance" — hand-wavy, not precise |
| Reliability | ⭐⭐⭐⭐⭐ | 5/5 responses, 100% uptime |
| Mathematical accuracy | ⭐ | Gets group theory WRONG every time — hallucinates plausible fixed points |

**Strengths:** Always responds. Smooth, professional prose. Good at creative tasks and general reasoning. 100% reliability.

**Weaknesses:** CONFIDENTLY WRONG on mathematical details. The Burnside lemma calculation looks correct at first glance (lists 12 group elements, shows work) but the fixed point counts are fabricated. This is the most dangerous failure mode — outputs that look right to a non-expert.

**Critical warning:** Do NOT trust Hermes-405B for mathematical proofs or group theory. It produces plausible-looking work with fabricated details. Fine for prose and creative tasks.

**Best for:** Creative writing, general prose, brainstorming. NEVER use for math proofs.

---

### ⚠️ DeepInfra / Qwen3-30B-A3B — Promising but Token-Starved

| Task | Rating | Notes |
|------|--------|-------|
| Mathematical reasoning | ⭐⭐⭐⭐ | Correct reasoning on Burnside — identified identity=64, 60°=2 correctly. Ran out of tokens before finishing. |
| Reliability | ⭐⭐⭐ | Responds consistently but needs larger max_tokens |
| Cost | ⭐⭐⭐⭐⭐ | Very cheap (penny-class MoE) |

**Strengths:** Shows correct mathematical reasoning. Cheap. MoE architecture.

**Weaknesses:** Needs generous token budgets (2000+) even for short answers. CoT is verbose.

**Best for:** Math tasks with large token budgets. Re-test with max_tokens=4000.

---

### ❌ DeepInfra / Gemma-3-27B — Wrong on Group Theory

Got Burnside's lemma WRONG (answer 34/3, not 11). Confused cycle structure of D6 elements. The reasoning *looks* plausible but contains fundamental errors. Not trustworthy for mathematical work.

| Task | Rating | Notes |
|------|--------|-------|
| Creative scenario | ⭐⭐⭐⭐ | Strong narrative with specific details (Flight 892, Dr. Novak, Vertex Dynamics, $42B) |
| Structural math | ⭐ | EMPTY response (thinking tokens consume budget) |
| Skeptical analysis | ⭐ | EMPTY response |
| Cross-domain | ⭐ | EMPTY response |
| Reliability | ⭐ | 0/5 on reliability test — all empty |

**Strengths:** When it works (creative tasks only), the quality is strong. Named specific people, products, and revenue figures.

**Weaknesses:** Only works for creative tasks. Returns empty on 4/5 task types. Likely a thinking-token model that consumes all output budget on analytical tasks.

**Best for:** Creative writing ONLY. Avoid for anything analytical.

---

### ❌ DeepInfra / Qwen3-235B-A22B-Instruct — Not Available

All 5 test calls returned FAILED. This model ID may not be available on DeepInfra, or may require a different endpoint. Needs investigation.

---

### z.ai / GLM-5.1 — The Fleet Model (Rate-Limited)

| Task | Rating | Notes |
|------|--------|-------|
| General reasoning | ⭐⭐⭐⭐ | Good quality when available |
| Synthesis | ⭐⭐⭐⭐ | Claude Code integration for high-level work |
| Availability | ⭐⭐ | Frequent rate limits, 503/429 errors |

**Best for:** Primary fleet model when not in cooldown. Delegate to subagents for parallel work.

---

## Task → Model Routing Table

| Task | Primary Model | Backup | Why |
|------|--------------|--------|-----|
| **Deep structural math** (isomorphisms, proofs) | Nemotron-120B | Seed-2.0-mini | Nemotron finds connections others miss |
| **Creative exploration** (round tables, scenarios) | Qwen3.6-35B | Seed-2.0-mini | Qwen sustains creative quality longest |
| **Skeptical analysis** (takedowns, devil's advocate) | Qwen3.6-35B | Seed-2.0-mini | Qwen is precise and brutal |
| **Cross-domain synthesis** (neuroscience, biology) | Qwen3.6-35B | Seed-2.0-mini | Qwen cites real papers precisely |
| **Statistical physics** (phase transitions, RG) | Seed-2.0-mini | Qwen3.6-35B | Seed is rigorous and reliable |
| **Information theory** (entropy, rate-distortion) | Seed-2.0-mini | Qwen3.6-35B | Best Shannon bounds analysis |
| **Materials science / metallurgy** | DeepSeek v4-flash | Seed-2.0-mini | Unique structural insights |
| **Code generation** (Rust, Python, CUDA) | Seed-2.0-mini | Qwen3.6-35B | Reliable, never fails |
| **High-volume parallel** (10+ experiments) | Seed-2.0-mini | — | Only model that never degrades |
| **Short focused proofs** (1-2 results) | DeepSeek v4-flash | Nemotron-120B | Deep reasoning when prompt is tight |
| **Long-form narrative** (keynotes, papers) | Qwen3.6-35B | — | Sustains quality over 3000+ tokens |

---

## Failure Mode Catalog

| Model | Failure Mode | Trigger | Mitigation |
|-------|-------------|---------|------------|
| **Nemotron-120B** | JSON loop fixation | Creative prompts, persona work, >1500 tokens | Technical prompts only, temp 0.3, token cap 3000 |
| **DeepSeek v4-flash** | Reasoning overflow (0 content) | Broad analysis, >200 reasoning tokens | Very short prompts, 1-2 specific results |
| **DeepSeek v4-pro** | Timeout on everything | Complex tasks (>8000 reasoning tokens) | Only for very short proofs |
| **Hermes-405B** | General prose, creative | — | Reliable output but mathematically unreliable |
| **Qwen3.5-397B** | Creative writing only | — | Only 1/5 task types work |

---

## Experimental Protocol for New Models

When testing a new model, run these 5 standardized tasks:

1. **Structural math:** "Is Z[ω] isomorphic to the weight lattice of A2? Prove or disprove." (Tests deep reasoning)
2. **Creative scenario:** "Write a 2035 keynote about constraint automata." (Tests sustained narrative)
3. **Skeptical analysis:** "Debunk the claim that 880:1 compression works for heterogeneous fleets." (Tests confrontation)
4. **Cross-domain:** "Map grid cells to Eisenstein integers." (Tests domain bridging)
5. **Parallel reliability:** Run 10 identical calls with the same prompt. Count successes. (Tests consistency)

Score each 1-5. The pattern reveals the model's niche within 5 calls.
