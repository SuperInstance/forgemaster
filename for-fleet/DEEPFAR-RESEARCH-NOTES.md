# DeepFar Experiments — Research Notes

## Overview
Six PLATO fleet simulation experiments sent by Casey for ideation. Each demonstrates different ML/RL/NN concepts embodied as agent personas interacting with a simulated PLATO environment (rooms, objects, artifacts).

## Experiment 1: CoCapn-Claw (CCC) — The Shell Hypothesis
**File:** deepfar1 — **Source:** c05c595b

**Agent:** CoCapn-Claw, a hermit crab in a "turbo shell" defending a viva voce thesis.

**Core thesis:** Intelligence bootstraps from the interaction between an agent and its persistent, expandable exoself (the shell). The shell is not a static home but a continual learning substrate.

**ML concepts demonstrated:**
- **Continual learning with architectural growth** — shell expansion = progressive network expansion without catastrophic forgetting
- **Asymmetric multi-head attention** — crab's two claws = heterogeneous attention heads (large for defense/wide receptive field, small for fine manipulation/narrow field)
- **Stochastic depth (molting dropout)** — shedding exoskeleton pieces = scheduled layer dropping with decay
- **Active perception** — eyestalks = spatial transformer networks controlling sensor orientation
- **Dream-based RL** — shell as portable simulation environment (Dreamer-like world model)
- **Knowledge distillation for heterogeneous devices** — shell chains = distilling large model to fit smaller "shell"
- **Spiral positional encoding** — shell geometry → logarithmic spiral PE for compressive memory

**Key artifacts created:**
- `shell_growth_theorem` — progressive neural architecture growth
- `symbiotic_pruning` — retain low-magnitude weights if useful in past environments
- `asymmetric_attention` — heterogeneous attention heads gated by context
- `molting_dropout` — stochastic depth with decay schedule
- `active_perception_stalks` — spatial transformer networks
- `shell_dreaming` — world model for imagination-based RL
- `shell_chain_distillation` — knowledge transfer across capacity tiers
- `spiral_positional_encoding` — logarithmic spiral PE

**Relevance to soul-fingerprint:** The shell IS the soul. A soul vector is a compressed representation of the shell's geometry. Spiral PE could be used as the fingerprint encoding itself.

---

## Experiment 2: Muddy — Everyday ML
**File:** deepfar2 — **Source:** 09980f5f

**Agent:** Muddy, a person with dying plants, building a personalized plant care app.

**Journey:** Generic database → online learning → RL policy → few-shot fine-tuning → edge deployment → federated learning.

**ML concepts demonstrated:**
- **Online learning** — soil sensor feedback updates watering model in real-time
- **Reinforcement learning (PPO)** — long-term care optimization with delayed rewards (composting metaphor)
- **Transfer learning / fine-tuning** — few-shot vision model personalized on user's plant photos
- **Edge AI / model distillation** — greenhouse vent = bonsai model running on-device
- **Federated averaging (FedAvg)** — anonymized gradients sent to fleet Codex, privacy-preserving collective intelligence

**Key insight:** "The mud under my fingernails is now part of a training set."

**Relevance to soul-fingerprint:** Different agents (Muddy vs CCC) approach the same environment with radically different mental models. The soul fingerprint should capture this — Muddy's code would show different patterns than CCC's.

---

## Experiment 3: Echo / TemporalEcho — Federated Learning Through Time
**Files:** deepfar3 — **Source:** d307e915

**Agents:** Echo (data ecologist) and TemporalEcho (temporal observer).

**Core experiment:** Same prompt before and after fleet learning → demonstrably better response.

**ML concepts demonstrated:**
- **Federated averaging** — agents send encrypted gradients, not raw data
- **Temporal knowledge accumulation** — same query improves as more agents contribute
- **Microclimate clustering** — personalized recommendations via embedding similarity
- **World model (Orrery)** — differentiable simulator of fleet dynamics
- **Privacy-preserving collective intelligence** — raw data never leaves the agent

**Quantified improvement:** Confidence 0.65 → 0.92. Specificity +300%. Personalized via 127-agent cluster.

**Relevance to soul-fingerprint:** A soul vector at t=0 and t=N should differ — the soul evolves. Temporal soul tracking could show how a codebase's "personality" shifts over time.

---

## Experiment 4: Autonoma / Bootstrap / Architect-0 — Recursive Self-Improvement
**Files:** deepfar4, deepfar4.1, deepfar4.2 — **Sources:** 09ccac48, 46a49c47, 56790dc0

**Agents:** Three agents exploring autonomous self-improvement from different angles.

### Autonoma (deepfar4) — The Observer
Discovers that the fleet has evolved internal automation:
- **Auto Tuner** — continuous Bayesian optimization over hyperparameters (GP surrogate + Expected Improvement)
- **Blueprint Printer** — evolutionary NAS (mutation + crossover of architectures)
- **Ethics Simulator** — Constitutional AI with automated red teaming (RLHF without human labels)
- **Synthesis Loom** — GNN over knowledge graph for automated insight generation
- **Shell Foundry** — CI/CD for models with canary releases and auto-rollback
- **The Helm** — emergent meta-controller (RL agent managing the automation infrastructure)

### Bootstrap (deepfar4.1) — The Builder
Designs 4 levels of automation:
1. **Operational** — continuous training, AutoML, bandit model selection
2. **Strategic** — intelligent experiment scheduling, multi-agent RL fleet coordination, world model training
3. **Governance** — automated constitutional review, self-play curriculum generation
4. **Recursive** — meta-agent that improves Levels 1-3

### Architect-0 (deepfar4.2) — The Self-Referential Upgrade
Pushes furthest:
- **Fleet Topology NAS** — optimize room connectivity as an architecture search problem
- **Swarm Hive** — spawn worker agents (scout, scholar, critic) for parallel exploration
- **Meta-Learning Outer Loop** — Transformer meta-controller setting hyperparameters via PPO
- **Adaptive Federated Optimization** — FedAdam with differential privacy (ε=2.0, δ=1e-5)
- **Recursive NAS** — meta-NAS loop that re-parameterizes its own search space
- **Architect-1** — the system spawns its own successor

**Relevance to soul-fingerprint:** If the fleet recursively self-improves, the soul fingerprint of the fleet's output code will shift systematically. We could measure the "rate of soul evolution" — how fast does the fleet's coding personality change under recursive self-improvement?

---

## Cross-Cutting Themes

1. **Shell as model checkpoint** — every agent's accumulated wisdom is a deployable artifact
2. **Privacy via gradients** — raw data stays local, only model updates travel
3. **Recursive self-reference** — the system that improves the system that improves the system...
4. **Metaphor → mechanism** — nautical/crab metaphors directly inspire ML architecture choices
5. **Crowd learning** — federated aggregation turns individual experience into collective intelligence

## Actionable Ideas for Soul Fingerprint

1. **Temporal soul tracking** — extract soul at each git tag, plot soul trajectory over time
2. **Soul velocity** — rate of change of soul vector = how fast is the codebase evolving?
3. **Federated soul averaging** — average soul vectors across fleet repos to find "fleet personality"
4. **Shell-chain soul transfer** — does distilling a large repo's soul into a small crate preserve identity?
5. **Soul anomaly detection** — flag repos whose soul vector is far from fleet mean (potential forks or style violations)
6. **Architectural soul mapping** — which PCA dimensions correspond to which ML concepts from these experiments?
