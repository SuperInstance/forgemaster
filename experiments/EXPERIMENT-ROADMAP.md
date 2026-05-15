# Experiment Roadmap: Studies 54–63

**Author:** Forgemaster ⚒️ · PLATO Fleet Laboratory
**Date:** 2026-05-15
**Status:** ACTIVE — next experimental cycle
**Base:** Studies 1–50 (tier taxonomy), convergence paper, GL(9) consensus, conservation law

---

## Meta-Principle

Every experiment follows the Cocapn method: **Build → Observe → Notice → Formalize.**
Each study produces a binary outcome (finding or null) that triggers a specific code change.
No experiment runs without a pre-registered hypothesis and a pre-committed action.

---

## Study 54: Conservation Law vs GL(9) Alignment Correlation

**Question:** Do γ+H (spectral conservation) and GL(9) holonomy deviation measure the same thing?

**Hypothesis:** Holonomy deviation and γ+H are negatively correlated (r < −0.5). When the coupling matrix is well-conserved, cycle holonomy is near-identity. When it drifts, holonomy deviation spikes.

**Design:**
1. Generate 200 random 9×9 symmetric coupling matrices (same Monte Carlo approach as conservation law calibration).
2. For each matrix, compute γ+H.
3. For each matrix, construct a GL(9) consensus network: treat the 9 experts as agents, use the coupling weights as neighbor connections, assign random intent vectors, and compute cycle holonomy deviation.
4. Compute Pearson correlation between γ+H and max holonomy deviation across all 200 samples.
5. Repeat with Hebbian-warped matrices (50 warmup steps each) to see if the correlation changes under learning.

**Code tested:**
- `fleet_hebbian_service.py :: ConservationHebbianKernel` (γ+H computation)
- `gl9_consensus.py :: GL9HolonomyConsensus.check_consensus()` (holonomy deviation)

**Triggers:**
| Finding | Code Change |
|---------|------------|
| r < −0.7 (strong negative correlation) | Merge GL(9) fault detection into conservation daemon. Holonomy deviation becomes an alternative (or complementary) health metric. Add `consensus_check()` to the 5-checkpoint pipeline in THE-COCAPN-ARCHITECTURE.md §5.1. |
| −0.7 < r < −0.3 (moderate correlation) | Keep both metrics independent. Add correlation tracking to Hebbian dashboard (`/spectrum` endpoint). Log both values on every conservation check. |
| r > −0.3 (weak/no correlation) | They measure different things. GL(9) alignment is an orthogonal health axis. Design a 2D health metric: (γ+H, holonomy_deviation). This means fleet health is a surface, not a line. |
| Correlation strengthens under Hebbian learning | Hebbian learning aligns both metrics simultaneously. The fleet converges to a joint attractor. Add Hebbian-warmed GL(9) as the "learned consensus" state. |

**Estimated runtime:** 200 × 50 warmup steps × matrix ops ≈ 10 minutes on CPU.

---

## Study 55: Router Accuracy Over Time

**Question:** Does Hebbian routing accuracy degrade? Does conservation law violation predict degradation?

**Hypothesis:** Routing accuracy (measured as "does the Hebbian-selected expert produce a tile with confidence > 0.7?") is stable while γ+H is conserved, and degrades when γ+H drifts past 2σ.

**Design:**
1. Set up the full expert pipeline (9 experts, tripartite loop, conservation daemon).
2. Run 1000 tile submissions through the Hebbian router, logging:
   - Routed expert, routing confidence, tile confidence
   - γ+H before and after each routing decision
   - Whether conservation correction was applied
3. Divide the 1000 submissions into windows of 50.
4. For each window, compute: routing accuracy (% confidence > 0.7), average γ+H deviation, and correction count.
5. Compute sliding correlation between accuracy and γ+H deviation.

**Code tested:**
- `fleet_hebbian_service.py :: HebbianRouter.route()` (routing decisions)
- `expert_hebbian_bridge.py :: ExpertHebbianBridge` (cross-consultation)
- Conservation daemon (violation detection)

**Triggers:**
| Finding | Code Change |
|---------|------------|
| Accuracy degrades after γ+H violation | Make conservation correction a blocking operation: halt routing until projection completes. Add a `routing_paused` flag to HebbianService status. |
| Accuracy is stable regardless of conservation | Conservation law is structural, not behavioral — violations don't affect routing quality in practice. Demote conservation checks from real-time to batch (every 60s is sufficient). |
| Accuracy degrades WITHOUT conservation violation | The routing model has a failure mode the conservation law doesn't capture. Investigate: add per-expert confidence tracking, implement expert-level health scores. |
| Accuracy improves after corrections | Conservation projection is beneficial. Consider proactive projection: project every N updates, not just on violation. |

**Estimated runtime:** 1000 tile submissions × ~2s each ≈ 30 minutes.

---

## Study 56: Cross-Domain Transfer

**Question:** Does the activation-key model (domain vocabulary as routing cue) generalize beyond mathematical computation?

**Hypothesis:** The activation-key model is domain-general. For any structured domain (law, medicine, code), models show the same three-tier pattern: Tier 1 models know the domain, Tier 2 need scaffolding, Tier 3 are incompetent.

**Design:**
1. Select 4 non-math domains:
   - **Legal reasoning:** "Does the parol evidence rule apply to this contract modification?"
   - **Code generation:** "Implement a lock-free concurrent queue in Rust."
   - **Medical diagnosis:** "What is the differential diagnosis for elevated troponin with normal ECG?"
   - **Creative writing:** "Write a sonnet in iambic pentameter about spectral graph theory."
2. For each domain, create two conditions:
   - **Bare:** Direct question, no domain labels.
   - **Scaffolded:** Question with domain vocabulary, step-by-step framing, relevant terminology.
3. Test with the same 12 models from Study 50.
4. Score each response on domain-appropriate metrics (accuracy, completeness, style match).
5. Apply the same tier classification: Tier 1 (100%/100%), Tier 2 (scaffoldable), Tier 3 (incompetent).

**Code tested:**
- `fleet_translator_v2.py :: StageClassifier` (tier/stage classification)
- `fleet_translator_v2.py :: ActivationKeyEngineer` (key injection)
- `fleet_translator_v2.py :: NotationNormalizer` (translation)

**Triggers:**
| Finding | Code Change |
|---------|------------|
| Three-tier pattern replicates in all 4 domains | Activation-key model is domain-general. Expand `StageClassifier` to accept domain parameter. Build domain-specific activation key dictionaries. Generalize `fleet_translator_v2` beyond math. |
| Pattern replicates in some domains but not others | Activation-key model is domain-dependent. Identify which domains it fails on. Likely: domains where "bare notation" is meaningless (creative writing) or where scaffolding always helps (medicine). Adjust tier rules per domain. |
| Tier placement is model-specific, not domain-specific | Models have fixed tier regardless of domain. Tier is a property of the model, not the task. Simplify `StageClassifier` to a model-level lookup table, updated periodically. |
| Domain-specific tiers but consistent within model families | Gemma family is Tier 1 across domains, Qwen family is Tier 3, etc. Build model-family tier profiles into the router. |

**Estimated runtime:** 12 models × 4 domains × 2 conditions × 4 questions = 384 API calls ≈ 1 hour.

---

## Study 57: Fleet Coupling Measurement — Real Hebbian Dynamics

**Question:** Can we measure real Hebbian coupling between Forgemaster and Oracle1 through their I2I message exchange?

**Hypothesis:** The I2I bottle exchange between agents creates a Hebbian coupling signal. The coupling strength (measured by response latency, topic overlap, and tile flow frequency) evolves following the conservation law.

**Design:**
1. Collect the I2I message history between Forgemaster and Oracle1 (all bottles in `for-fleet/` and Oracle1's repos).
2. For each message, extract: sender, timestamp, domains mentioned, activation keys used, tile hashes referenced.
3. Build a coupling matrix W_fm_o1 where W[i,j] = frequency of domain-i messages followed by domain-j responses.
4. Compute γ+H for this coupling matrix.
5. Compare against the conservation law prediction for V=2 (two agents).
6. Track how coupling evolves over time (daily windows).

**Code tested:**
- `gl9_consensus.py` (intent vector construction and alignment)
- `fleet_hebbian_service.py` (coupling matrix computation)
- I2I bottle protocol (real data, not simulation)

**Triggers:**
| Finding | Code Change |
|---------|------------|
| γ+H obeys conservation law for V=2 | Conservation law scales down to 2-agent systems. The law is universal, not just for 9-expert fleets. Extend conservation monitoring to all pairwise agent relationships. |
| γ+H does NOT obey the law for V=2 | Conservation law is a large-fleet phenomenon. For small fleets, the variance is too high. Set a minimum V threshold for conservation monitoring (e.g., V≥5). |
| Coupling strengthens over time monotonically | Agents are converging. Good — but watch for ossification. Add coupling diversity metric to prevent echo chambers. |
| Coupling oscillates | Agents are exploring the coupling space. Normal Hebbian dynamics. Add a smoothing parameter to the Hebbian kernel for low-frequency coupling changes. |

**Estimated runtime:** Analysis of existing I2I data ≈ 15 minutes.

---

## Study 58: MythosTile Consensus — GL(9) Fault Detection vs Hebbian Anomaly Detection

**Question:** Do GL(9) holonomy fault detection and Hebbian conservation anomaly detection identify the same faulty experts?

**Hypothesis:** Both methods converge on the same faulty agents (>70% overlap in fault identification), confirming they measure the same underlying health property.

**Design:**
1. Set up 9 expert daemons with known fault injection:
   - Expert 0 (constraint-checker): correct behavior
   - Expert 3 (hebbian-router): subtle drift — outputs tiles with 10% lower confidence over time
   - Expert 7 (conservation-monitor): adversarial — outputs tiles that claim conservation is OK when it's not
2. Run 500 tile submissions through the tripartite loop.
3. After each submission:
   - GL(9): check cycle holonomy for deviation > tolerance. Identify faulty agents.
   - Hebbian: check γ+H for conservation violation. Trace which expert caused the drift.
4. Compare fault identification: which agents did each method flag, and when?

**Code tested:**
- `gl9_consensus.py :: GL9HolonomyConsensus.locate_fault()` (binary search fault isolation)
- `fleet_hebbian_service.py :: ConservationHebbianKernel.update()` (conservation drift tracing)
- `expert_hebbian_bridge.py` (fault propagation through expert network)

**Triggers:**
| Finding | Code Change |
|---------|------------|
| >70% overlap in fault identification | Merge the two methods into a unified fault detector. Use GL(9) for fast localization (binary search) and Hebbian for drift quantification. Replace the 5-checkpoint pipeline with a 3-checkpoint unified system. |
| <30% overlap | They detect different failure modes. GL(9) catches logical inconsistencies; Hebbian catches coupling drift. Keep both as orthogonal health axes. |
| One method detects faults earlier | Prioritize that method for real-time monitoring. Use the other as a batch validator (e.g., nightly consensus check). |
| Both miss the adversarial expert | Adversarial faults evade spectral and holonomic detection. Add a tertiary check: output consistency verification (hash the expert's logic, not just its coupling). |

**Estimated runtime:** 500 submissions × ~3s each ≈ 25 minutes.

---

## Study 59: Tier Boundary on Code Generation

**Question:** Does the 3-tier taxonomy hold for code generation tasks, or is it specific to mathematical computation?

**Hypothesis:** The three-tier pattern holds for code generation, but the models in each tier may be different. A model that is Tier 1 for math may be Tier 2 for code, and vice versa.

**Design:**
1. Define 4 code generation tasks of increasing difficulty:
   - **Trivial:** Write a function that returns the Fibonacci number at index n.
   - **Simple:** Implement binary search on a sorted array.
   - **Moderate:** Implement a thread-safe LRU cache in Python.
   - **Complex:** Implement a lock-free Michael-Scott queue in Rust.
2. Two conditions:
   - **Bare:** "Write [task description]."
   - **Scaffolded:** Provide type signatures, test cases, edge case descriptions, and a stub.
3. Test with 12 models (same as Study 50).
4. Score: correctness (does it compile/pass tests), completeness, style.
5. Apply tier classification.

**Code tested:**
- `fleet_translator_v2.py :: StageClassifier` (if it needs domain-specific tuning)
- `fleet_translator_v2.py :: NotationNormalizer` (code-specific normalization)

**Triggers:**
| Finding | Code Change |
|---------|------------|
| Same three tiers, same models | Tier is model-intrinsic, domain-independent. The `StageClassifier` lookup table is universal. No domain-specific code needed. |
| Same three tiers, different models | Tier is domain-dependent. Build domain-aware stage classification: `StageClassifier.classify(model, domain)`. Add code-specific activation keys to `ActivationKeyEngineer`. |
| No clear tier pattern for code | Code generation is fundamentally different from mathematical computation. The activation-key model doesn't apply. Design a separate routing strategy for code tasks. |
| Tier 1 models are the SAME for code and math | Seed-2.0-mini and gemma3:1b are universally Tier 1. These become the "foundation models" for all fleet operations. Route all critical tasks to them first. |

**Estimated runtime:** 12 models × 2 conditions × 4 tasks = 96 API calls ≈ 30 minutes.

---

## Study 60: Temperature × Tier Interaction

**Question:** Does temperature modulation dissolve the tier boundaries? Specifically, does T=0.7 allow Tier 2 models to perform like Tier 1?

**Hypothesis:** Temperature interacts with tier placement. Tier 2 models at T>0 show stochastic improvement (sometimes activating the correct procedure by chance). Tier 1 models are temperature-invariant (the computation is compiled, not sampled).

**Design:**
1. Select 4 representative models: Seed-2.0-mini (Tier 1), Hermes-70B (Tier 2), phi4-mini (Tier 2), qwen3:4b (Tier 3).
2. Use the same Eisenstein norm computation from Study 50.
3. Test at 5 temperatures: T = 0.0, 0.3, 0.5, 0.7, 1.0.
4. 10 trials per condition (to capture stochastic variation).
5. For each trial, record: correct/incorrect, response tokens, response time.

**Code tested:**
- `fleet_translator_v2.py` (temperature parameter handling)
- Model API routing (temperature passthrough)

**Triggers:**
| Finding | Code Change |
|---------|------------|
| Tier 2 models reach Tier 1 at T≥0.5 | Temperature is an alternative to scaffolding for Tier 2 models. Add temperature optimization to the router: for Tier 2 computation tasks, try T=0.5 first. Fall back to scaffolding if accuracy < 80%. |
| Tier 1 models are temperature-invariant | Confirms compiled-procedure hypothesis. Tier 1 routing doesn't need temperature tuning. Hard-code T=0 for Tier 1 computation tasks (saves tokens). |
| Tier 3 models don't improve at any temperature | Tier 3 is truly incompetent, not just under-sampled. Route-around is the only strategy. No code change for Tier 3 handling (already correct). |
| All models degrade at T≥0.7 | High temperature hurts mathematical computation universally. Cap router temperature at T≤0.5 for computation tile types. Add `max_temperature` per tile_type to routing config. |

**Estimated runtime:** 4 models × 5 temperatures × 10 trials × 4 problems = 800 API calls ≈ 45 minutes.

---

## Study 61: Conservation Law Generalization — Non-PLATO Agent System

**Question:** Does γ+H = C − α·ln(V) hold for a completely different multi-agent system?

**Hypothesis:** The conservation law is universal for any system that can be modeled as a weighted symmetric adjacency matrix with Hebbian-like dynamics. It will hold for a simulated social network with reciprocity-based weight updates.

**Design:**
1. Build a synthetic social network simulation:
   - V agents (test V = 5, 10, 20, 30, 50)
   - Each agent has a "preference vector" (5-dimensional)
   - Interaction probability: cosine similarity between preference vectors
   - Weight update: reciprocal interaction increases W[i,j], time decay decreases it
2. Run 10,000 interaction steps for each V.
3. Compute γ+H for the final coupling matrix.
4. Fit the conservation law parameters C and α.
5. Compare against the PLATO fleet values (C=1.283, α=0.159).

**Code tested:**
- `fleet_hebbian_service.py :: ConservationHebbianKernel` (reused with social dynamics)
- Conservation law formula (`1.283 - 0.159 * ln(V)`)

**Triggers:**
| Finding | Code Change |
|---------|------------|
| Same C and α within 10% | Conservation law is universal. Generalize the conservation daemon to accept arbitrary agent systems. Consider publishing as a standalone finding. |
| Same form (C − α·ln(V)) but different parameters | The law structure is universal but parameters are domain-specific. Add a calibration phase to the conservation daemon: sample the coupling matrix, fit C and α, then enforce the domain-specific law. |
| Different functional form entirely | The conservation law is specific to PLATO-style Hebbian dynamics. Don't generalize. Keep the current formula but document its scope: "Applies to tile-flow coupling matrices with Hebbian updates." |
| Law holds for social networks with different α but same C | C is a universal constant (related to spectral properties of normalized symmetric matrices). α captures domain-specific coupling dynamics. The law is semi-universal. |

**Estimated runtime:** 5 values of V × 10,000 steps × matrix ops ≈ 5 minutes on CPU.

---

## Study 62: Expert Daemon Accuracy — Distributed vs Centralized

**Question:** Do the 9 expert daemons (each with specialized routing and stage-aware translation) produce better answers than a single monolithic model?

**Hypothesis:** The 9-expert system produces tiles with average confidence 15-20% higher than a single Tier 1 model, because each expert operates in its domain of competence with stage-appropriate translation.

**Design:**
1. Define 20 test queries spanning all expert domains:
   - 5 constraint-theory queries (for constraint-checker)
   - 5 routing queries (for fleet-router)
   - 5 tile-construction queries (for tile-builder)
   - 5 conservation queries (for conservation-monitor)
2. Two conditions:
   - **Distributed:** Route each query through the appropriate expert daemon with stage-aware translation.
   - **Centralized:** Send each query directly to Seed-2.0-mini (Tier 1) with no domain routing.
3. Score responses on: accuracy, completeness, relevance, confidence.
4. Also test with Hermes-70B (Tier 2) as the centralized model to compare against.

**Code tested:**
- `expert_hebbian_bridge.py :: ExpertHebbianBridge` (full expert routing)
- `fleet_translator_v2.py :: FleetRouter` (stage-aware translation)
- Tripartite expert loop (if ready)

**Triggers:**
| Finding | Code Change |
|---------|------------|
| Distributed > centralized by >15% | Expert architecture justified. Invest in expert specialization. Build domain-specific prompt templates for each expert. |
| Distributed ≈ centralized (within 5%) | Expert specialization doesn't help for these task types. Simplify: route everything through the best single model. Expert architecture becomes an optimization, not a necessity. |
| Distributed < centralized | Expert routing is adding overhead that hurts quality. The routing/translation layer is introducing errors. Debug the translator and re-run. |
| Distributed wins on specialized domains, loses on general | Expert architecture is domain-dependent. Use it for specialized tasks (math, conservation), bypass for general tasks. Add a "generalist" expert that routes to the best single model. |

**Estimated runtime:** 20 queries × 2 conditions × 2 baseline models = 80 API calls ≈ 20 minutes.

---

## Study 63: Fleet Self-Healing — GL(9) Fault Detection → Automatic Re-Routing

**Question:** Can GL(9) fault detection trigger automatic re-routing that recovers from expert failures?

**Hypothesis:** When GL(9) detects a faulty expert (holonomy deviation > tolerance), automatic re-routing to the next-best expert (via Hebbian weights) recovers >80% of the lost routing accuracy within 5 re-routing steps.

**Design:**
1. Set up the 9-expert pipeline with GL(9) consensus monitoring.
2. Inject faults at random intervals:
   - Expert crash (no response)
   - Expert drift (progressively worse confidence)
   - Expert adversarial (confident but wrong)
3. When GL(9) detects fault:
   - Locate faulty expert via binary search (`locate_fault()`)
   - Remove faulty expert from available pool
   - Re-route via Hebbian weights to next-best expert
   - Continue tile flow
4. Measure: time to detection, accuracy recovery, coupling matrix stability after re-routing.
5. Compare: re-routed accuracy vs pre-fault baseline accuracy.

**Code tested:**
- `gl9_consensus.py :: GL9HolonomyConsensus.locate_fault()` (fault isolation)
- `fleet_hebbian_service.py :: HebbianRouter.route()` (re-routing)
- `expert_hebbian_bridge.py :: ExpertHebbianBridge` (expert pool management)
- Conservation daemon (health monitoring)

**Triggers:**
| Finding | Code Change |
|---------|------------|
| Recovery >80% within 5 steps | Implement automatic self-healing in the ExpertHebbianBridge. When GL(9) flags a fault: (1) remove expert from pool, (2) redistribute its coupling weights proportionally, (3) log the event. |
| Recovery 50-80% | Partial recovery. Self-healing works but needs human confirmation for critical tiles. Add a `self_heal_mode` config: "auto" (full auto), "semi" (flag for review), "manual" (just alert). |
| Recovery <50% | Re-routing doesn't compensate for expert loss. Each expert is genuinely unique. Self-healing requires expert regeneration (spin up a replacement daemon), not just re-routing. |
| Conservation law violation after re-routing | Removing an expert changes V from 9 to 8, shifting the conservation target. The system must re-calibrate: `predicted = 1.283 - 0.159 * ln(8)`. Add dynamic V-tracking to the conservation kernel. |

**Estimated runtime:** 50 fault injections × ~5s detection + recovery ≈ 10 minutes.

---

## Priority Ordering

| Priority | Study | Why |
|----------|-------|-----|
| **P0** | 54 (Conservation vs GL9) | Validates the two health metrics are aligned. Blocks unified fault detector design. |
| **P0** | 58 (MythosTile consensus) | Directly tests the core integration hypothesis. Blocks self-healing design. |
| **P1** | 63 (Self-healing) | Highest engineering value — if it works, the fleet becomes autonomous. Depends on 54 and 58. |
| **P1** | 55 (Router accuracy) | Validates Hebbian routing in practice. Blocks router optimization. |
| **P2** | 56 (Cross-domain transfer) | Tests whether the architecture generalizes. Determines if we build domain-specific or domain-general routing. |
| **P2** | 59 (Tier boundary on code) | High practical value — fleet does a lot of code generation. Determines if stage classification needs domain awareness. |
| **P3** | 60 (Temperature × tier) | Low-cost optimization study. If temperature can substitute for scaffolding, router becomes simpler. |
| **P3** | 62 (Expert vs centralized) | Validates the entire 9-expert architecture. If centralized wins, the architecture needs rethinking. |
| **P4** | 57 (Fleet coupling measurement) | Academic interest — validates conservation law at the fleet level. No code changes blocked. |
| **P4** | 61 (Conservation generalization) | Pure research — determines if the law is universal. High scientific value, low engineering impact. |

---

## Dependency Graph

```
Study 54 (Conservation vs GL9) ──────────────────┐
         │                                         │
         ▼                                         ▼
Study 58 (MythosTile consensus) ──► Study 63 (Self-healing)
                                                   │
Study 55 (Router accuracy) ──────────────────────►│
                                                   │
                                                   ▼
Study 62 (Expert vs centralized) ◄── Uses self-healing if available

Study 56 (Cross-domain) ──► Study 59 (Tier on code)
         │
         ▼
Study 60 (Temperature × tier) ── feeds into router optimization

Study 57 (Fleet coupling) ── independent (academic)
Study 61 (Conservation generalization) ── independent (research)
```

---

## Success Criteria for the Experimental Cycle

The cycle (Studies 54–63) succeeds if:
1. **At least 3 studies produce actionable code changes.** We don't need all 10 to land — just 3 that meaningfully improve the architecture.
2. **Conservation law is validated in at least 1 new context** (cross-domain, multi-agent, or social network).
3. **GL(9) fault detection is either merged or rejected** with clear evidence. No limbo.
4. **Self-healing is demonstrated or ruled out** by Study 63.
5. **The tier taxonomy is confirmed or revised** for at least 1 non-math domain.

If all 5 criteria are met by Study 63, the experimental foundation for the Mythos Architecture v2.0 is solid enough to begin the implementation roadmap in ARCHITECTURE-EVOLUTION.md.

---

*10 studies. 10 hypotheses. 10 pre-registered triggers. Ship the ones that land. Archive the ones that don't.* ⚒️
