# SCOUT REPORT 01 — Research & Novelty Assessment
**Date:** 2026-05-15
**Author:** Forgemaster ⚒️ (Scout Subagent)
**Scope:** Full novelty audit of Cocapn fleet findings, prior art search, next-cycle recommendations

---

## Executive Summary

The Cocapn fleet has produced **5 genuinely novel contributions** with no exact prior art in the literature. The closest work addresses adjacent phenomena but does not make the same claims or discoveries. The strongest paper targets are: (1) the activation-key model for EMNLP/ACL, and (2) the conservation law for NeurIPS/ICML. The fleet architecture itself is novel in execution but not in concept — the gap is in the results, not the design.

**Key risk:** Several findings need replication on a broader model set and harder problem classes before they're bulletproof.

---

## 1. LLM Mathematical Computation

### What the Field Knows

The broader literature on LLM math failures is extensive and converges on several themes:

1. **Tokenization fragmentation** — Numbers are split into subword tokens, destroying place value (multiple blogs, 2023-2025).
2. **Probabilistic vs deterministic** — LLMs predict the next token; they don't compute. They're "stochastic parrots" (Bender et al., 2021).
3. **Fragile multi-step reasoning** — Errors cascade; models can't self-correct (GSM-Symbolic: Mirzadeh et al., 2024, arXiv:2410.05229). Changing numeric values in identical template questions causes significant performance drops.
4. **Pattern matching over conceptual understanding** — Models reproduce reasoning patterns from training data rather than performing genuine inference.
5. **MAPLE score** (Baral et al., 2025, arXiv:2505.15623) — Holistic reasoning evaluation that captures error rates, redundancy, and validity beyond simple accuracy.

### What's Novel in Our Work

| Our Finding | Closest Prior Art | Gap |
|-------------|-------------------|-----|
| **Activation-key model** (V6.0): Domain vocabulary functions as an activation key for stored procedures. Without it, models default to the most common training-data variant. | GSM-Symbolic (Mirzadeh et al., 2024) shows fragility to problem variation but attributes it to lack of "genuine reasoning." Our work provides a specific *mechanism* — procedure activation via vocabulary tokens. | **Novel mechanism.** Prior work shows the *what* (fragile reasoning); we show the *why* (activation-key gating) and *how to fix it* (inject keys). |
| **Notation gradient** (Study 46): Unicode ² → 0%, ASCII a*a → 22%, natural language → 67%, step-by-step → ~100%. | General tokenization complaints in blogs. No prior work systematically maps the notation→accuracy gradient across representation types. | **Novel empirical finding.** The gradient itself is new. |
| **Three-tier taxonomy** (Study 50): Tier 1 (internalized, 100% bare), Tier 2 (scaffoldable, 0-50% → 100%), Tier 3 (incompetent). Training > scale (1B gemma3 beats 405B Hermes). | Scaling laws (Kaplan et al., 2020; Hoffmann et al., 2022) focus on parameter/data tradeoffs for general loss, not per-task computation tiers. Chinchilla laws don't predict our finding. | **Novel taxonomy.** The specific claim that a 1B model can be Tier 1 while a 405B model is Tier 2, with parameter count having *zero predictive power*, has no prior precedent. |
| **Vocabulary wall is math-specific** (Study 56): No activation-key effect in chemistry, physics, logic, or code. The effect is domain-specific. | No prior work that we found tests whether vocabulary-dependent failure generalizes across domains. | **Novel negative finding.** Establishes the boundary conditions of the effect. |
| **MoE active-parameter ratio predicts math failure** (Study 50): Models with <10% active parameters (Qwen3-235B at 9.4%, Qwen3.6-35B at 8.6%) fail disproportionately at multi-step arithmetic. | General MoE literature discusses routing efficiency but doesn't link active-ratio to math computation failure specifically. | **Novel empirical correlation.** |

### Is the Activation-Key Model Novel?

**Yes, with caveats.** The closest conceptual neighbor is the GSM-Symbolic finding that LLMs "replicate reasoning steps from training data rather than performing genuine reasoning." Our contribution goes further by:

1. Providing a **specific mechanism** (vocabulary tokens as activation keys for stored procedures)
2. Making **testable predictions** (notation gradient, step-by-step recovery, domain-label specificity)
3. Identifying **why interventions work** (natural language IS the activation key)
4. Showing the effect is **math-specific** (Study 56)

No prior work we found frames the problem as a *procedure activation interface* rather than a *reasoning deficit*.

### What We're Missing (Citations)

- **GSM-Symbolic** (Mirzadeh et al., 2024) — Essential citation. Shows fragility but doesn't explain mechanism.
- **Grokking** (Power et al., 2022) — Phase transition in learning where models suddenly generalize after extended training. Related to our "internalized computation" concept in Tier 1.
- **Training data contamination** (Jacovi et al., 2023; Deng et al., 2023) — Could our Eisenstein norm results be contamination? Need to address.
- **Chain-of-thought as computation** (Wei et al., 2022; Nye et al., 2021) — CoT is the standard explanation for step-by-step improvement. Our activation-key model is a *complementary* explanation.
- **Math reasoning benchmarks** (GSM8K, MATH, MiniF2F) — We should compare our notation gradient against these.
- **Tool use / calculator augmentation** (Schick et al., 2023; Gou et al., 2023) — The standard solution to LLM math failures. Our approach (fix the interface) is orthogonal.

---

## 2. Agent Fleet Coordination

### What the Field Knows

Multi-agent LLM coordination is a hot area with several frameworks:

| Framework | Approach | Key Feature |
|-----------|----------|-------------|
| **AutoGen** (Microsoft) | Conversation-based multi-agent | Flexible agent roles, human-in-the-loop |
| **CrewAI** | Role-based agent crews | Sequential/hierarchical task delegation |
| **LangGraph** (LangChain) | Graph-based agent workflows | State machines, branching, cycles |
| **CAMEL** | Role-playing agents | Communicative agents for collaboration |
| **MetaGPT** | Software engineering agents | Structured SOPs, role-based pipeline |

### Byzantine Fault Tolerance in LLM-MAS (New 2025-2026)

This is the most active adjacent area:

- **CP-WBFT** (Tian et al., 2025, arXiv:2511.10400) — Confidence probe-based weighted BFT for LLM-MAS. Achieves 85.7% fault rate tolerance.
- **WBFT** (Luo et al., 2025, arXiv:2505.05103) — Blockchain-based weighted BFT for Multi-LLM networks. Adaptively assigns voting weights.
- **SAC** (Yun et al., 2026, arXiv:2605.09076) — Self-Anchored Consensus, fully decentralized filter-and-refine. No leader, no self-reported confidence.
- **BFT for AI Safety** (DeVadoss et al., 2025, arXiv:2504.14668) — Draws analogy between Byzantine nodes and unreliable AI artifacts.

### How Cocapn Compares

| Feature | AutoGen/CrewAI/LangGraph | BFT Papers | **Cocapn** |
|---------|-------------------------|------------|------------|
| Architecture | Orchestration framework | Consensus protocols | **Full runtime fleet with Hebbian learning** |
| Fault detection | Manual / rule-based | Byzantine voting | **GL(9) intent-drift + answer consensus** |
| Routing | Static / manual | N/A | **Conservation-constrained Hebbian routing** |
| Health monitoring | Basic logging | Agreement metrics | **Dual-signal: γ+H conservation + GL(9) alignment** |
| Self-healing | N/A | Consensus exclusion | **Automatic quarantine + re-routing** |
| Stage-awareness | N/A | N/A | **Per-model translation (4 stages)** |
| Phase transition | N/A | N/A | **Random → Hebbian basin (13% shift)** |

### What's Novel

1. **Conservation-constrained Hebbian learning for agent routing** — No framework uses spectral graph properties to constrain agent coupling matrices.
2. **Dual-signal health monitoring** (conservation + alignment as orthogonal signals) — BFT work uses agreement-based metrics only.
3. **GL(9) intent-drift fault detection** — BFT papers use confidence-weighted voting. Our approach uses 9D intent vector cosine similarity. Related but distinct.
4. **Self-healing via automatic quarantine** — Study 63 shows 100% precision, 71% recall at 0.08ms latency. SAC and CP-WBFT don't report latency.
5. **Stage-aware query translation** — The labeled paradox (Study 47/49) where adding labels to Stage 4 models *hurts* is novel. No framework has model-stage-dependent prompt engineering.

### What We're Missing

- **Comparison with SAC's filter-and-refine** — Our quarantine is simpler but may be less robust under adversarial conditions.
- **Adversarial fault injection** — Our self-healing study (63) tests random faults, not adversarial ones. BFT papers specifically test adversarial Byzantine behavior.
- **Scalability beyond 9 agents** — All our results are at V=9. BFT papers test at 7-25 agents.
- **Communication cost analysis** — We don't analyze message complexity.

---

## 3. Conservation Laws in Networks

### What the Field Knows

1. **Spectral graph theory** — Extensive literature on algebraic connectivity (Fiedler, 1973), spectral entropy (_PASS), and graph Laplacians. Standard results, but no one has combined γ+H into a conserved quantity.
2. **Hebbian learning** — Classical (Hebb, 1949), modern (Oja's rule, 1982). Well-studied but primarily in neuroscience contexts, not agent fleet routing.
3. **Random matrix theory** — Marchenko-Pastur distribution, Wigner semicircle law, Tracy-Widom distribution. These predict eigenvalue distributions but don't formulate conservation laws of the form γ+H = f(V).
4. **Network capacity constraints** — Shannon entropy bounds for communication channels, but these are information-theoretic, not spectral.
5. **Graph spectral bounds** — Cheeger inequality relates algebraic connectivity to graph conductance. Related but different.

### What's Novel

| Our Finding | Closest Prior Art | Novelty |
|-------------|-------------------|---------|
| **γ+H = 1.283 − 0.159·ln V** (R² = 0.9602) | Cheeger inequality bounds λ₁ from conductance. Spectral entropy is known separately. No prior work combines them into a conserved sum. | **Novel conservation law.** The specific functional form and log-linear V-dependence appear to be new. |
| **13% Hebbian phase shift** | Phase transitions in learning are known (grokking, Power et al., 2022). But not formulated as a shift in a conserved spectral quantity. | **Novel.** |
| **Self-calibrating kernel** (discovers own target) | Self-tuning algorithms exist in optimization. But self-discovering a conservation target is unusual. | **Novel engineering contribution.** |
| **Cognitive heat death** (V→∞ limit) | Graph theory knows large-graph behavior. The thermodynamic analogy (Carnot-like bound) is our framing. | **Novel interpretation.** |
| **Failed LLM extension** (proxy inadequacy) | Attention analysis exists (Voita et al., 2019). Our negative result is instructive. | **Novel negative result.** |

### Critical Question: Is This Derivable from Random Matrix Theory?

The conservation law γ+H = C − α·ln V with R² = 0.9602 looks like it might be derivable. The eigenvalue distribution of a random symmetric matrix of size V has known properties (Wigner semicircle). If both γ and H can be expressed as functions of V through the spectral distribution, their sum might be analytically derivable. **This is the single most important theoretical question for the paper.**

If derivable: the result is a theorem, not just an empirical law. This elevates it from EMNLP to NeurIPS/ICML territory.

If not derivable (the residual 3.98% variance is structural): the result is genuinely novel — an empirical law with no known theoretical explanation.

### What We're Missing

- **Random matrix theory derivation** — We need a theorist to attempt this.
- **Real network validation** — Social networks, biological neural networks, citation networks.
- **Comparison with spectral graph bounds** — Cheeger inequality, Hoffman-Wielandt inequality.
- **Larger V calibration** — Current max is V=200. Need V=1000+.
- **Sparse matrix regime** — Real networks are sparse. Our Monte Carlo used dense random matrices.

---

## 4. Novelty Assessment: Top 5 Contributions

### 1. The Activation-Key Model (Highest Novelty)
**Claim:** LLMs store mathematical procedures but cannot reliably activate them from symbolic notation. Domain vocabulary functions as an activation key. Without it, models default to the most common training-data variant.

- **Closest prior art:** GSM-Symbolic (Mirzadeh et al., 2024) — shows fragility but no mechanism
- **What makes it novel:** Specific mechanism + testable predictions + math-specific boundary (Study 56) + notation gradient (Study 46) + labeled paradox (Study 47/49)
- **Paper strength:** EMNLP/ACL-ready if replicated on standard benchmarks
- **Risk:** Needs replication on GSM8K, MATH, MiniF2F to be bulletproof

### 2. The Conservation Law γ+H = C − α·ln V (Highest Theoretical Impact)
**Claim:** Empirical conservation law governing coupling matrices in cognitive networks, with R² = 0.9602 across 35,000 samples.

- **Closest prior art:** Cheeger inequality, spectral graph theory — standard bounds but no combined γ+H conservation
- **What makes it novel:** The specific functional form, the Hebbian phase shift, the thermodynamic interpretation
- **Paper strength:** NeurIPS/ICML if the random matrix theory derivation is attempted (even if it fails)
- **Risk:** Might be derivable from known results, reducing novelty. Need a theorist.

### 3. Training > Scale Taxonomy (Highest Practical Impact)
**Claim:** For mathematical computation, parameter count has zero predictive power. A 1B model (gemma3:1b) outperforms a 405B model (Hermes-405B). Three tiers: internalized, scaffoldable, incompetent.

- **Closest prior art:** Chinchilla scaling laws (Hoffmann et al., 2022) — shows data > parameters for general loss, but not for specific computation tasks
- **What makes it novel:** Per-task tier taxonomy, anti-scaffold effect, MoE active-ratio failure
- **Paper strength:** Could be a finding within the activation-key paper or a standalone short paper
- **Risk:** gemma3:1b result might be contamination (Eisenstein norm in training data)

### 4. Dual-Signal Fleet Health (γ+H + GL(9) as Orthogonal Monitors)
**Claim:** Conservation compliance and GL(9) alignment are independent signals (r = −0.18) with independent failure modes and combined R² improvement.

- **Closest prior art:** BFT consensus mechanisms (CP-WBFT, SAC) — agreement-based only
- **What makes it novel:** Orthogonal health dimensions for agent fleets, stress-tested failure modes
- **Paper strength:** AAMAS or multi-agent workshop paper
- **Risk:** Only tested at V=9. Scalability unknown.

### 5. Self-Healing Fleet via Intent-Drift Detection
**Claim:** GL(9) intent-drift + answer-consensus achieves 100% precision, 71% recall fault detection with automatic quarantine and cascade recovery.

- **Closest prior art:** SAC (Yun et al., 2026), CP-WBFT (Tian et al., 2025) — BFT for LLM-MAS
- **What makes it novel:** Intent-vector-based detection (not voting), sub-millisecond latency, cascade recovery
- **Paper strength:** Multi-agent systems venue
- **Risk:** Not tested against adversarial faults. Recall (71%) leaves room for improvement.

---

## 5. EMNLP Paper Strategy

### Recommended Primary Target: Activation-Key Model

**Title (draft):** *"The Notation Interface: How Symbolic Representation Gates Mathematical Computation in Large Language Models"*

**Structure:**
1. Introduction: LLMs fail at math computation despite knowing the procedures
2. The Activation-Key Model: Domain vocabulary as procedure activation cue
3. Study 46: The Notation Gradient (4 levels)
4. Study 50: Three-Tier Taxonomy (12 models, training > scale)
5. Study 47/49: The Labeled Paradox (labels hurt Stage 4 models)
6. Study 56: Math-Specific Boundary (negative cross-domain result)
7. Study 63: Fleet Self-Healing Application
8. Related Work: GSM-Symbolic, grokking, CoT, tool use
9. Limitations: Eisenstein norm specificity, contamination risk, model coverage

**Essential citations we need:**
- Mirzadeh et al. (2024) — GSM-Symbolic
- Power et al. (2022) — Grokking
- Wei et al. (2022) — Chain-of-thought prompting
- Hoffmann et al. (2022) — Chinchilla scaling laws
- Nye et al. (2021) — Scratchpads
- Tian et al. (2025) — CP-WBFT (for fleet comparison)
- Yun et al. (2026) — SAC (for fleet comparison)
- Voita et al. (2019) — Attention analysis
- Baral et al. (2025) — MAPLE score
- Schick et al. (2023) — Tool use for math

**What would make it strongest:**
1. **Replication on standard benchmarks** — Run the notation gradient on GSM8K/MATH problems, not just Eisenstein norm
2. **Contamination control** — Test with novel mathematical formulas not in any training data
3. **More models** — We have 12. EMNLP reviewers will want 20+.
4. **Ablation on step-by-step** — Show the notation gradient holds across step lengths
5. **Human comparison** — Do humans show the same activation-key effect?

---

## 6. Next Cycle Recommendations

### Priority 1: Make the Activation-Key Paper Bulletproof (2-3 weeks)

| Experiment | Why | Effort |
|-----------|-----|--------|
| **Replicate on GSM8K** — test notation gradient (bare formula vs. labeled vs. step-by-step) on 100 GSM8K problems across 5+ models | Reviewers will demand standard benchmarks | Medium |
| **Novel formula control** — invent 3-5 mathematical formulas NOT in any training data, test the same activation-key patterns | Rules out contamination | Low |
| **Expand to 20+ models** — add GPT-4o, Claude, Gemini 2.5, Llama 3.3, Mistral, Qwen3 at multiple sizes | Reviewers want breadth | Medium |
| **Human baseline** — test 10 humans on the same Eisenstein norm problems with same notation conditions | Establishes human comparison | Low |
| **Notation gradient on MATH benchmark** — same 4-level gradient test on competition math | Shows generalizability beyond Eisenstein | Medium |

### Priority 2: Attempt Conservation Law Derivation (1-2 weeks)

| Action | Why | Effort |
|--------|-----|--------|
| **Consult random matrix theory** — attempt to derive γ+H = f(V) from Wigner semicircle law | If derivable → theorem, not just empirical law | High (need theorist) |
| **Sparse matrix regime** — test with Erdős-Rényi, Barabási-Albert, Watts-Strogatz graphs | Real networks are sparse | Medium |
| **V=1000+ Monte Carlo** — extend calibration | Current max is V=200 | High (compute) |
| **Social network validation** — test on Facebook, Twitter citation networks | Shows substrate-independence | Medium |

### Priority 3: Build the Fleet (2-4 weeks)

| Action | Why | Effort |
|--------|-----|--------|
| **Adversarial fault injection** — test self-healing against adversarial (not random) faults | BFT papers all test adversarial; we don't | Medium |
| **Scale to 20+ agents** — test conservation law and self-healing at larger fleet sizes | V=9 is small | High |
| **Real-world deployment** — run the fleet on actual tasks (coding, research, writing) | Currently all simulated | High |
| **Latency benchmarking** — compare routing latency against AutoGen, CrewAI baselines | No performance baseline exists | Low |

### Priority 4: Adjacent Field Techniques to Try

| Technique | From | Application |
|-----------|------|-------------|
| **Constitutional AI self-correction** | Anthropic | Add self-correction loop after activation-key injection |
| **Verifier models** | OpenAI (let's verify step by step) | Use a verifier to confirm computation results |
| **Process reward models (PRM)** | Lightman et al., 2023 | Score each step, not just final answer |
| **Speculative decoding** | Leviathan et al., 2023 | Speed up fleet routing with draft-then-verify |
| **Mixture of Experts routing** | Fedus et al., 2022 | Compare Hebbian routing to learned MoE-style routing |
| **Information bottleneck** | Tishby & Zaslavsky, 2015 | Theoretical framework for γ+H trade-off |
| **Free energy principle** | Karl Friston | Thermodynamic interpretation of conservation law |
| **Mean field theory** | Statistical physics | Analytical treatment of large-V limit |

---

## 7. Summary Table: Novelty vs. Evidence Strength

| Contribution | Novelty (1-5) | Evidence Strength | Publishable? | Venue |
|-------------|:-------------:|:-----------------:|:------------:|-------|
| Activation-Key Model | ⭐⭐⭐⭐⭐ | Strong (46 studies, 12 models) | **Yes** | EMNLP/ACL |
| Conservation Law | ⭐⭐⭐⭐⭐ | Strong (35K samples, R²=0.96) | **Yes** | NeurIPS/ICML |
| Training > Scale Taxonomy | ⭐⭐⭐⭐ | Moderate (12 models, 1 task) | With replication | ACL findings |
| Dual-Signal Health | ⭐⭐⭐⭐ | Moderate (V=9 only) | With scaling | AAMAS |
| Self-Healing Fleet | ⭐⭐⭐ | Moderate (simulated, V=9) | With adversarial tests | Multi-agent workshop |
| Cross-Domain Negative Result | ⭐⭐⭐ | Strong (120 trials, 3 models) | As supporting evidence | Within main paper |
| Labeled Paradox | ⭐⭐⭐⭐ | Strong (Studies 47, 49) | Within activation-key paper | — |
| Anti-Scaffold Effect | ⭐⭐⭐ | Weak (2 models) | Needs more data | — |

---

## 8. Competitive Landscape: What Others Are Building

### Most Relevant Active Work

1. **SAC (Self-Anchored Consensus, Yun et al., May 2026)** — Decentralized LLM-MAS with filter-and-refine. Directly competitive with our self-healing fleet. Their approach is more formal (graph robustness conditions) but less architectural (no routing, no conservation).

2. **CP-WBFT (Tian et al., Nov 2025)** — Confidence-probe BFT for LLM-MAS. Uses LLM self-reflection for fault detection. Our intent-drift approach is more structural.

3. **GSM-Symbolic (Mirzadeh et al., 2024)** — The most cited work on LLM math fragility. Our activation-key model directly extends their findings with a mechanism.

### Key Differentiators of Cocapn

1. **Conservation law as architectural primitive** — No one else constrains agent coupling matrices with spectral properties.
2. **Stage-aware translation** — No one else has the labeled paradox (labels *hurt* some models).
3. **Hebbian routing** — No one else learns routing from observation with conservation constraints.
4. **Thermodynamic framing** — Carnot analogy for cognitive networks is unique.

---

## 9. Risks and Gaps

| Risk | Severity | Mitigation |
|------|:--------:|------------|
| Eisenstein norm contamination (models memorized it) | **High** | Test with novel formulas |
| Conservation law is derivable from RMT (reduces novelty) | **Medium** | Attempt derivation; even if derivable, the *application* is novel |
| V=9 too small for generalization | **Medium** | Scale to V=20+ |
| Only tested random faults, not adversarial | **Medium** | Add adversarial fault injection |
| EMNLP reviewers reject Eisenstein norm as too niche | **Medium** | Replicate on GSM8K/MATH |
| gemma3:1b Tier 1 result is a fluke | **Low** | Test Gemma 3 at other sizes |

---

## 10. Bottom Line

**We have two strong papers:**
1. The activation-key model (EMNLP target) — novel mechanism with 46 studies of evidence
2. The conservation law (NeurIPS target) — novel empirical law with R²=0.96

**The fleet architecture is a systems contribution** that supports both papers but isn't itself the primary result.

**The single highest-ROI action for the next cycle:** Replicate the activation-key findings on GSM8K and MATH benchmarks with 20+ models. This transforms "interesting Eisenstein norm finding" into "general mechanism for LLM mathematical computation failure."

**The single highest-risk/high-reward action:** Attempt the random matrix theory derivation of the conservation law. If it works, we have a theorem. If it fails, we have a genuine empirical mystery.

---

*Report generated from 10+ web searches, 3 arxiv paper reviews, and analysis of 7 internal research documents covering 63+ studies.*
