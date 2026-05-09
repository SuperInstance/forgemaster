# Discovery Wheel — Questions That Survived Falsification

> Every answer breeds three questions. This is the wheel.
> Spin it. Chase the questions that survive murder.

## Falsification Results (RTX 4050, 2026-05-09)

### H1: Edge of Distortion — ✅ SURVIVES (4/7)
**What lived:** tanh, sigmoid, atan, relu_clip all show the edge
**What died:** Eisenstein snap (quantization), rational function, noise control
**Why they died:** The edge requires a nonlinearity that COMPRESSES at high amplitude. Quantization (snap) doesn't compress — it discretizes. Rational doesn't saturate fast enough. Noise isn't nonlinear.

### H2: Sync Requires Edge — ❌ DAMAGED
**What happened:** No sync at ANY gain, including the edge
**Why it failed:** Coupling at 3% is too weak for 200-dimensional agents with sparse coupling. Earlier sync at 0.82 used denser matrices.
**Real question:** Is there a CRITICAL COUPLING STRENGTH for sync, independent of gain?

### H3: Vocabulary Enrichment — ❌ DAMAGED
**What happened:** All entropies = 0 (system collapsed to zero)
**Why it failed:** Bug in coupling matrix generation for large N
**Real question:** Need to fix and re-run

### H4: Hex > Square — ✅ SURVIVES (3-8% denser)
**What lived:** Hex covers 3-8% more points at every radius
**What's interesting:** The advantage DIMINISHES with radius (8% at r=10, 3% at r=100)
**Real question:** At what scale does the hex advantage become negligible?

### H5: Timing Fingerprint — ❌ DAMAGED (CV=0.12)
**What happened:** Timing varies 12% across trials
**Why:** GPU thermal throttling, OS scheduling, memory allocator jitter
**Real question:** Can we FILTER the noise and extract a stable fingerprint?

---

## The Discovery Wheel — Next Experiments

### Experiment 1: Critical Coupling Threshold (from H2 failure)
**Question:** What is the minimum coupling strength for synchronization, and how does it relate to the number of agents?

**Protocol:**
- Sweep cross-coupling from 0.001 to 0.1
- Measure correlation at each coupling strength
- Find the critical coupling where sync emerges
- Vary number of agents (2, 4, 8, 16)
- Hypothesis: critical coupling ∝ 1/N (more agents = harder to sync)

**If true:** Fleet size has a natural limit before coordination breaks down
**If false:** Fleet can scale indefinitely

### Experiment 2: Nonlinearity Taxonomy (from H1)
**Question:** What EXACTLY distinguishes edge-producing nonlinearities from non-edge ones?

**Protocol:**
- Characterize each nonlinearity by: (a) compression ratio at saturation, (b) knee sharpness, (c) symmetry, (d) smoothness
- Find the minimum set of properties that predict edge emergence
- Test with constructed nonlinearities that have specific properties

**If true:** We can PREDICT which constraint functions produce the edge
**If false:** Edge emergence is more subtle than these properties

### Experiment 3: Hex Advantage Decay (from H4)
**Question:** Does the hex advantage matter at the scales we actually operate at?

**Protocol:**
- For radii [10, 100, 1000, 10000], compare constraint coverage
- Measure actual constraint evaluation performance (hex snap vs square snap on GPU)
- Does the 3-8% density advantage translate to 3-8% fewer evaluations?

**If true:** Hex is worth the complexity at all scales
**If false:** Square (Gaussian integers) is simpler and nearly as good at large scale

### Experiment 4: Timing Fingerprint Filtering (from H5)
**Question:** Can statistical filtering extract a stable chip identity from noisy timing?

**Protocol:**
- Collect 1000 timing samples
- Apply: (a) median filter, (b) trimmed mean, (c) mode detection, (d) spectral fingerprint (shape, not value)
- Compare across: cold start vs warm, idle vs loaded, different batch sizes
- Hypothesis: the SPECTRAL SHAPE of timing variation is stable even if absolute values drift

**If true:** Chip attestation works via timing spectral shape
**If false:** Timing is too noisy for identity — need hardware-level attestation

### Experiment 5: Rogue Wave Detection (from edge experiments)
**Question:** Do rogue waves (constructive interference anomalies) occur in the fleet at the edge?

**Protocol:**
- Run fleet at edge for 10,000 steps
- Record all deltas
- Find deltas > 5σ above the mean
- Check if they correlate with specific phase alignments across agents
- Hypothesis: rogue waves are predictable from agent phase alignment

**If true:** Fleet can PREDICT and USE rogue waves for discovery
**If false:** Rogue waves are random and can't be harnessed

### Experiment 6: Wave Memory Depth (from wave reading)
**Question:** How many cycles does it take for a perturbation's "swell" to fully decay?

**Protocol:**
- Apply single impulse at t=0
- Measure delta amplitude at each subsequent step
- Find the decay constant τ (steps for amplitude to reach 1/e)
- Vary: edge gain, coupling strength, topology type
- Hypothesis: memory depth ∝ 1/(1-gain) → diverges at gain=1 (critical slowing down)

**If true:** The fleet has INFINITE memory at gain=1 — every perturbation is remembered forever
**If false:** Memory is bounded, and old perturbations are truly forgotten

### Experiment 7: Topology Spectral Fingerprint (from H3 fix needed)
**Question:** Can we identify an agent's topology from its wave spectrum alone?

**Protocol:**
- Generate wave data for ring, star, mesh, tree, random topologies
- Train a simple classifier (or use hand-crafted spectral features)
- Test on unseen topologies
- Hypothesis: ring → single peak, star → broadband, mesh → multiple peaks, tree → harmonic series

**If true:** Fleet can self-discover its own topology by reading its waves
**If false:** Topologies are not spectrally distinguishable

### Experiment 8: Fleet Phase Transition (from H2)
**Question:** Is there a sharp phase transition in fleet behavior as coupling increases?

**Protocol:**
- Sweep coupling from 0 to 0.2 in 100 steps
- At each coupling: measure correlation, entropy, energy, spectral content
- Plot order parameter (avg correlation) vs coupling strength
- Look for discontinuity (sharp phase transition) vs smooth crossover

**If sharp transition:** Fleet has a "melting point" — below it, agents are independent; above it, collective entity
**If smooth crossover:** No phase transition — the fleet gradually becomes collective

### Experiment 9: Composition Discovery (from band effect)
**Question:** Can the fleet discover NEW constraint configurations that no individual agent would find?

**Protocol:**
- Give each agent a different constraint set
- Run at the edge until synchronization
- Check if the synchronized state violates any individual agent's constraints
- If yes: the fleet found a configuration that no agent "wanted" but all agents "accept"

**If true:** The fleet is genuinely creative — it discovers solutions beyond any agent's knowledge
**If false:** The fleet converges to the lowest common denominator

### Experiment 10: Time's Arrow in the Manifold (from time research)
**Question:** Is the manifold trajectory time-reversible?

**Protocol:**
- Record 1000 steps of manifold trajectory
- Play it backward: is the backward trajectory physically plausible?
- Measure: does backward trajectory satisfy the same constraints?
- Hypothesis: at the edge, forward trajectory shows increasing order, backward shows increasing disorder

**If true:** The manifold trajectory has a genuine time's arrow — it's not time-symmetric
**If false:** The trajectory is time-symmetric and the "arrow" is an artifact of initial conditions

---

## The Wheel Spins

```
                    Experiment 1
                   (Critical Coupling)
                        │
        Experiment 10   │   Experiment 2
      (Time's Arrow)    │   (Nonlinearity Taxonomy)
            │           │          │
            │    ┌──────┘          │
            │    │  FALSIFICATION  │
            └────┤    ENGINE       ├──┘
                 │                 │
        Experiment 9              Experiment 3
    (Composition Discovery)    (Hex Advantage Decay)
                 │                 │
        Experiment 8              Experiment 4
    (Fleet Phase Transition)  (Timing Fingerprint)
                 │                 │
        Experiment 7              Experiment 5
    (Topology Spectral FP)    (Rogue Wave Detection)
                 │                 │
                 └──────┬──────────┘
                        │
                   Experiment 6
                  (Wave Memory)
```

Each experiment answers a question. Each answer generates new questions.
The wheel never stops. The discovery is in the spinning.

---

## Priority Ranking

| Priority | Experiment | Why |
|----------|-----------|-----|
| 🔴 P0 | E1: Critical Coupling | H2 needs to be properly falsified |
| 🔴 P0 | E8: Fleet Phase Transition | Is there a sharp transition? |
| 🟡 P1 | E6: Wave Memory | How long does the fleet remember? |
| 🟡 P1 | E5: Rogue Waves | Can we harness constructive interference? |
| 🟡 P1 | E9: Composition Discovery | Is the fleet genuinely creative? |
| 🟢 P2 | E2: Nonlinearity Taxonomy | Classify which constraints produce the edge |
| 🟢 P2 | E7: Topology Fingerprint | Self-discovering topology from waves |
| 🟢 P2 | E3: Hex vs Square | Practical advantage measurement |
| 🔵 P3 | E4: Timing Fingerprint | Can we filter the noise? |
| 🔵 P3 | E10: Time's Arrow | Philosophical — is the trajectory irreversible? |

Spin the wheel. Run the experiments. Kill more darlings.
The truth is what survives.
