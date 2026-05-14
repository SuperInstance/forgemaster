# The Decomposition Engine: Five Directions

*A research ideation document for the Forgemaster decomposition engine architecture.*

---

## Direction 1: Self-Improving Verification — The System That Grows Its Own Local Muscle

### Core Insight

The decomposition engine currently starts with a fixed set of 6 verifiers. Each experiment teaches us something about the mathematical landscape — but the verifiers themselves never learn. The insight: **experimental results ARE training data for new verifiers.** Every time an Eisenstein snap succeeds or a covering radius check fails, that's a labeled data point. Over 1000 experiments, patterns emerge. The system should extract those patterns and compile them into new local verifiers.

This is the difference between a tool and an ecosystem. A tool stays sharp. An ecosystem evolves.

### What's Already Proven

- **Verifiers work at hardware speed.** 621M ops/sec on the snap benchmark via AVX-512 + fast-math — local verification is already orders of magnitude faster than API calls.
- **Docker sandboxing is reliable.** Zeroclaw isolates each experiment. No cross-contamination, no SSH overhead.
- **PLATO tile flow works end-to-end.** Decomposition → sub-problems → verification → results collection is a closed loop in production.
- **The 6-verifier set covers real ground.** SplineLinear + drift detection + covering radius + snap + threshold + intent checks form a working proof-of-concept on 48 task×target combinations.

### What Needs to Be Built Next

1. **A "trace serializer"** — captures the full input/output/prediction triple for every verifier call, not just the binary pass/fail. This includes: the mathematical object being verified, the verifier's internal state at every step, the exact output, and the cycle count. PLATO tiles already have the schema — just need to wire in richer metadata.

2. **A "pattern miner"** — a background process that scans the trace corpus for recurring structures. Cluster embeddings of mathematical objects that pass/fail together. When a cluster reaches critical mass (say 100 examples), pattern-miner proposes a new verifier spec.

3. **A "verifier generator"** — converts pattern-miner output into actual verifier code. This could be automated for simple patterns (threshold checks, range constraints) or escalated to an API call for complex ones (novel lattice structures). The API is used sparingly — only when pattern-miner lacks confidence.

4. **A "regression harness"** — every proposed verifier must pass the existing test suite AND not regress on any tile-score metric. This prevents garbage generation and keeps the verifier set trustworthy.

### The Killer Application

**Autonomous mathematical discovery at scale.** Imagine a system that starts with 6 verifiers and, after 10,000 experiments, has discovered 43. The system didn't just solve problems — it invented new ways to check its own work. This is a machine that recursively strengthens its reasoning toolkit.

Practical payoff: when a new conjecture arrives, the system has 7× more local verification power than it started with, no API calls needed. The growth is exponential in experiments, not linear.

### Honest Limitation

**Pattern mining is easy to get wrong in catastrophic ways.** A spurious correlation in the trace data leads to a bad verifier, which passes itself off as reliable, and every subsequent result built on it is quietly wrong. The system degrades, not improves.

Mitigation: regression harness + confidence thresholds + forced API re-verification of all results built on new verifiers for the first 100 uses. But this adds complexity and slows the self-improvement loop. The trade-off between growth speed and trustworthiness is the core design tension.

---

## Direction 2: Fleet-Wide Optimization — Collective Hardware Intelligence

### Core Insight

Different machines have different chips. An Eisenstein snap that hits 621M ops/sec on an AVX-512 Skylake server might run at 80M ops/sec on an ARM Mac. A LoRA verifier that's fast on an NPU might be slow on a GPU.

Today, each sandbox discovers its optimal configuration in isolation. Tomorrow: **every sandbox shares its hardware fingerprint and benchmark results via PLATO, and the fleet collectively learns the optimal configuration per architecture.**

The fleet becomes a distributed optimization engine — not just running experiments, but learning how to run them faster.

### What's Already Proven

- **Multi-target deployment works.** The `deploy_fleet()` function already maps 48 task×target combinations — cpu-tiny, cpu, gpu, npu, etc. Each target gets its own variant selection (spline, dense+INT8, lora).
- **Hardware-aware variant selection exists.** The auto system already chooses spline for cpu-tiny, dense for npu, lora for gpu. This is a primitive form of fleet optimization.
- **PLATO serves as fleet memory.** Tile flows between nodes work. The infrastructure for cross-node knowledge sharing is green-lit.

### What Needs to Be Built Next

1. **A "hardware fingerprint" tile schema** — CPU model, ISA extensions (AVX-512, AVX2, SVE, NEON), cache hierarchy, memory bandwidth, GPU/NPU model, vector width, DP capability, TDP. Standardized across the fleet.

2. **A "benchmark oracle"** — when a new machine joins the fleet, it runs a 30-second benchmark suite. Results go to PLATO. The oracle cross-references with existing fingerprints and recommends: variant selection, batch sizes, quantization targets, thread counts.

3. **A "performance drift detector"** — monitors per-machine tile execution times. When one node starts running 30% slower (thermal throttling? neighbor workload?), the fleet reroutes heavy experiments and re-optimizes.

4. **A "cross-architecture synthesis"** — if x86 discovers:spline[192,64] → best for drift-detect, and ARM discovers: spline[256,64] → best for drift-detect, the system synthesizes a general rule: "drift-detect spline optimal width = 256 near AVX-512 boundary, 192 otherwise."

### The Killer Application

**Zero-configuration performance for heterogeneous fleets.** A new Mac Studio joins the fleet. Ten seconds later, it's running at 95% of its optimal speed for every verifier. No manual tuning. No build flags. No "why is this node slower?" debugging.

Over 100 nodes, the fleet converges on the global optimal configuration for each architecture class in under an hour. Any single node that discovers a better configuration seeds the improvement to all compatible nodes within minutes.

### Honest Limitation

**Hardware differences are usually real, but sometimes they're noise.** A node that's 2% slower on one benchmark might have different thermals or OS scheduling policies, not a fundamentally different chip. The optimization oracle needs to distinguish signal from noise, or it'll churn on irrelevant "optimizations."

Worse: the fleet could converge on a local optimum that's terrible for a specific machine class if the optimization surface has sharp non-linearities (e.g., cache-line alignment boundaries). Outlier detection and explicit exploration budgets are essential safeguards.

---

## Direction 3: Scientific Method at Machine Speed

### Core Insight

The scientific method is an iterative loop: hypothesis → experiment → observation → falsification → new hypothesis. Human scientists run this loop in weeks or months per iteration.

The decomposition engine runs the same loop: conjecture → decomposition → local verification → (pass/fail) → refinement. Each iteration takes **seconds.**

This is not a metaphor. The structural isomorphism is exact. The system is doing science — it's just doing it 10,000× faster than humans can.

### What's Already Proven

- **Decomposition + verification is a closed loop.** A conjecture enters, sub-problems are verified locally, results flow back, and the system iterates. This IS the scientific method's loop, fully automated.
- **Falsification works locally.** Covering radius checks, drift bounded checks, Eisenstein snap — these are falsification methods. They find counterexamples. That's scientific progress.
- **No interpretation lag.** Results don't sit in a notebook for a month. They flow through PLATO tiles in real-time, available for the next hypothesis.

### What Needs to Be Built Next

1. **A "hypothesis manager"** — tracks the tree of conjectures, their status (tentative/confirmed/falsified/inconsistent), and the chain of experiments that led to each status. This is the scientific record, machine-native.

2. **A "discrepancy prioritizer"** — when a conjecture passes verification locally but a small subset of sub-problems had very tight margins (snap near boundary, drift near threshold), those are flagged. They represent high-value targets for the next iteration — hypotheses that are technically confirmed but suspicously close to being wrong.

3. **An "experimental design module"** — given the current frontier of high-margin verifications, designs the next decomposition. This is the "what to test next" engine. It replaces random exploration with targeted falsification attempts.

4. **A "confidence accumulator"** — tracks how many independent verifications a given conjecture has survived. Each passing verification increases confidence. Each narrow margin leaves a "suspicion token" that accumulates. A conjecture with 100 passes and 0 suspicion tokens is treated as tentatively established.

### The Killer Application

**Mathematical literature at 10,000× speed.** A human mathematician produces ~10 proven results per year. A decomposition engine running 24/7 could produce 10,000 verified conjectures per year — with the full evidentiary trail, confidence scores, and linked verification chains.

Not all are important, of course. But the "important" filter becomes a second pass: run the top-1% of verified conjectures through a heavy-weight verification cycle (more verifiers, more iterations, cross-domain tests). The result is 100 truly novel, rigorously verified mathematical results per year from a single machine.

In the limit: the system doesn't just prove things. It **discovers what's worth proving.**

### Honest Limitation

**Speed amplifies bias.** If the verifier set encodes an implicit bias (e.g., favoring algebraic over analytic structures), the machine-speed scientific loop will explore the algebraic neighborhood exhaustively while barely touching analysis. The system converges quickly — on a distorted picture of the mathematical terrain.

Humans have the same problem but are slower, so the distortion takes years to manifest. Machine speed makes it visible in hours. The solution requires deliberate diversification of verifiers, not just more of them. The `pattern-miner` from Direction 1 must actively seek verifiers that disagree with existing ones.

---

## Direction 4: The Convergence Point — When Local Trumps API

### Core Insight

Right now, the API does decomposition. The chips do verification. The API is the bottleneck — it's expensive, slow, and centralized.

But every time the system runs an experiment, it gains capacity to do more locally. Pattern miners produce new verifiers (Direction 1). Fleet optimization makes verifiers faster (Direction 2). The scientific loop generates more data, which generates more verifiers, which generates more data.

**There is a convergence point where local verifiers cover enough mathematical territory that the API becomes unnecessary for most work.**

### What's Already Proven

- **6 verifiers already cover a useful domain.** The drift-detect task hits 100% accuracy on 5/6 hardware targets. That's a non-trivial proof-of-concept.
- **SplineLinear gives 20× compression at same accuracy.** Local computation is NOT sacrificing power for speed. In some cases, it's strictly superior.
- **Sub-millisecond inference on all CPU targets.** Local verification is effectively free in time-cost terms.

### What's the Path from 6 to 600?

The growth curve isn't linear. It's likely logistic or exponential.

**Phase 1 (1-30 verifiers):** Manual + pattern-miner handoff. Pattern-miner proposes, human (or API) reviews. Slow but safe. This builds the foundation and the regression harness.

**Phase 2 (30-100 verifiers):** Automated generation with API escalation for serious proposals. Pattern-miner has enough examples to cluster reliably. Most verifier proposals are simple (threshold checks, range bounds, linear invariants). A few are complex (novel invariants, structural constraints).

**Phase 3 (100-300 verifiers):** The API is only used for decomposition on problems where no available verifier covers the required sub-domain. The system has become largely self-sufficient for routine mathematics.

**Phase 4 (300-600 verifiers):** Verifier coverage is broad enough that most decompositions can be verified entirely locally. The API is used only for genuinely novel territory — what would be "research frontier" for human mathematicians.

**Escape velocity:** The point where the system generates more new verifiers from its own experimental output than it consumes from API calls. Estimated threshold: ~50-100 verifiers, depending on domain diversity. At this point, the system is self-sustaining.

### The Killer Application

**A self-hosting mathematics engine.** The API pays for the initial exploration. After escape velocity, the system generates more mathematical knowledge from its own results than it costs to run. The marginal cost of a new verified conjecture approaches zero.

In economic terms: the API is the capital investment. Local verifiers are the recurring revenue of mathematical progress.

### Honest Limitation

**The tail is hard.** The first 100 verifiers cover 90% of common mathematical structures. The next 500 cover the remaining 10%. These are the hard ones: non-linear invariants, pathological edge cases, domains that require genuinely novel mathematics to verify.

The system might hit diminishing returns hard around 200 verifiers. Each new one costs more in computation and review than the last, while covering less new territory. The design question becomes: is 90% coverage (with API fallback for the tail) good enough? Probably yes — but the "escape velocity" narrative is weaker at 90% than at 99%.

---

## Direction 5: Applications Beyond Mathematics

### Core Insight

The decomposition engine's architecture is not specific to mathematics. It's a general pattern:

**Expensive decomposition + cheap local verification + iterative refinement loop.**

Any domain with this structure is a candidate. The decomposition engine pattern — use a powerful but expensive model to decompose problems, use fast local verifiers to check solutions, iterate — applies wherever there's a separation between "breaking down" and "checking the pieces."

### 5.1 Physics Simulation

**Structure:** A high-level physics task (e.g., "simulate turbulent flow over this airfoil profile") can be decomposed by an API model into sub-simulations. Each sub-simulation runs on a local, small, specialized physics engine (verifier). The results are tiles: pressure coefficients, vorticity peaks, separation points.

**What's already proven:** The same pattern — decompose big problems into small verifiable pieces. The "verifier" here is a 2D Navier-Stokes solver running on AVX-512. The decomposition is the mesh refinement strategy.

**What needs building:** Domain-specific physics verifiers (NS solver, rigid body dynamics, electromagnetic field propagation). A decomposition schema for physics problems (domain decomposition in the literal sense).

**Killer app:** Run 10,000 airfoil simulations overnight, each one a different profile, all verified locally. The API doesn't run a single CFD call — it just designs the experiment. Morning arrival: a database of 10,000 validated drag coefficients.

**Risk:** Physics verifiers are harder to make "sound" than mathematical ones. A buggy NS solver gives confident wrong answers. The regression harness needs physics-aware tests.

### 5.2 Compiler Optimization

**Structure:** "Optimize this LLVM IR for throughput" → API decomposes into: (1) vectorize inner loop, (2) hoist loop-invariant code, (3) inline hot calls, (4) scheduling pattern. Each sub-problem is verified locally: is the new IR semantically equivalent to the old? Does it use target ISA features? What's the cycle estimate?

**What's already proven:** The "verifier as local checker" pattern maps exactly to existing compiler verification tools (alive2, Souper, peephole correctness proofs). The decomposition engine becomes a super-optimizer: propose any sequence of transforms, verify each step locally.

**What needs building:** Compiler-IR tile schemas. Semantic equivalence verifiers. A cost model that's verifier-fast (sub-millisecond per basic block). Integration with LLVM's pass pipeline.

**Killer app:** Instead of hand-tuning optimization sequences for each chip generation, the API decomposes the IR into transform targets, and the local verifiers explore the search space. Result: 5% faster code for the same compile time. Fleet-wide sharing of optimization strategies across architectures.

**Risk:** IR equivalence checking is NP-hard in general. Local verifiers can only handle bounded-time cases. The decomposition engine needs to know when to give up and fall back to the baseline.

### 5.3 Drug Design

**Structure:** "Find a molecule that binds to this protein target" → API decomposes into: (1) scaffold generation, (2) side-chain optimization, (3) binding affinity prediction, (4) toxicity screening. Each sub-problem is verified locally. Scaffolds pass through a molecular-dynamics verifier. Affinity predictions run through a docking simulation verifier.

**What's already proven:** The "decompose → verify locally" pattern is literally the standard drug discovery pipeline, but typically orchestrated by humans. The decomposition engine automates the orchestration and exploration.

**What needs building:** Domain-specific verifiers for molecular docking (AutoDock Vina as local verifier), toxicity prediction (DeepTox as local verifier), ADME properties. These are well-established tools that just need tile wrappers.

**Killer app:** Screen 100,000 candidate molecules computationally overnight. The API designs the screening strategy (which scaffold families to explore, which pendant groups to vary). Local verifiers run the actual docking and toxicity checks. Morning arrival: the top 100 candidates, fully validated, ready for synthesis.

**Risk:** False positives are expensive (you synthesize a compound that doesn't work). False negatives are expensive too (you miss the one that would work). Local verifiers must be calibratable in confidence, not just binary pass/fail. The physics simulations are approximations; the system needs to know the approximation error.

### 5.4 Financial Modeling

**Structure:** "Simulate portfolio performance under 10,000 market scenarios" → API decomposes into scenario clusters. Each cluster is verified locally by a fast Monte Carlo engine tuned for the specific risk factor profile. Scenarios that produce extreme outcomes (tail events) get flagged for deeper verification.

**What's already proven:** Monte Carlo simulation is embarrassingly parallel with local decomposition. The PLATO tile pattern maps directly to scenario storage and comparison. "Drift detection" as a verifier concept maps to VaR (Value at Risk) exceedance detection.

**What needs building:** Financial verifiers for scenario generation, risk aggregation, correlation modeling. PLATO tile schemas for financial simulation state. Integration with existing quantitative libraries (QuantLib, XGBoost for volatility prediction).

**Killer app:** A bank's risk team gives the decomposition engine a new portfolio model. By lunchtime, it's been stress-tested against 100,000 scenarios across 10 risk-factor regimes. Each scenario was verified locally. The API was used only for scenario design. The result is a risk report that took 20 minutes of API time and 200,000 core-hours of local verification — automatically parallelized.

**Risk:** Financial models are regulatory instruments. A verifier that's wrong by 1% in a tail scenario leads to wrong capital reserves. The "confidence accumulator" from Direction 3 is essential here — and regulators want explanations, not just confidence scores. The gap between mathematically sound and regulatorily acceptable is real.

---

## Synthesis: The Meta-Pattern

All five directions share a common structure:

1. **Use the expensive API for what it's best at:** decomposition, pattern recognition, creative proposal generation.
2. **Use fast local computation for what it's best at:** verification, iteration, exhaustive search.
3. **PLATO tiles connect them:** the bridge between expensive thought and fast execution.
4. **The system improves over time:** verifiers grow, optimization converges, the scientific loop tightens.

The decomposition engine is not a tool for solving mathematical problems. It's a **machine for producing trust at scale** — for making the expensive cheap and the uncertain verifiable, for distributing the work of being right across a fleet of cheap, fast, locally trustworthy chips.

The API asks "what should we check?" The chips answer "we checked it." The gap between those two operations — the distance from question to verified answer — is what the decomposition engine architecture closes.

---

*Generated 2026-05-14 by Forgemaster research ideation agent. Intent: directional speculation, concrete proposals, honest limitations. No fluff.*
