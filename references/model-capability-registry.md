# Model Capability Registry 🧠

**Purpose:** Operational intel on what each model is good at, for routing tasks in polyformalism-turbo-shell and general fleet work.
**Updated:** 2026-05-07 (after Eisenstein-hex round table experiments)

---

## Provider Overview

| Provider | Models Used | Rate Limits | Cost | Speed |
|----------|-------------|-------------|------|-------|
| **z.ai** | GLM-5.1, GLM-4.7 | Cooldown-prone | Paid | Fast |
| **DeepInfra** | Seed-2.0-mini, Seed-2.0-code, Qwen3.6-35B, Nemotron-120B, Hermes-405B, Qwen3-235B | Generous | Cheap | Fast |
| **DeepSeek** | v4-flash, v4-pro/reasoner | Generous | Cheap | Fast (flash), Slow (pro) |
| **OpenAI** | (no key) | — | — | — |
| **Kimi** | kimi CLI | Configured | Paid | Medium |

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
| **z.ai GLM-5.1** | Rate limit (503/429) | Subagent spawning, parallel calls | Serialize calls, use as orchestrator not worker |

---

## Experimental Protocol for New Models

When testing a new model, run these 5 standardized tasks:

1. **Structural math:** "Is Z[ω] isomorphic to the weight lattice of A2? Prove or disprove." (Tests deep reasoning)
2. **Creative scenario:** "Write a 2035 keynote about constraint automata." (Tests sustained narrative)
3. **Skeptical analysis:** "Debunk the claim that 880:1 compression works for heterogeneous fleets." (Tests confrontation)
4. **Cross-domain:** "Map grid cells to Eisenstein integers." (Tests domain bridging)
5. **Parallel reliability:** Run 10 identical calls with the same prompt. Count successes. (Tests consistency)

Score each 1-5. The pattern reveals the model's niche within 5 calls.
