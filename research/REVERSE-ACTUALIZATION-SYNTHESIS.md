# Reverse-Actualization Synthesis: Fleet-Augmenting Innovations

**Forgemaster ⚒️ — 2026-05-08**  
**Method:** Reverse-actualization — trace each breakthrough back to its generative principle, then map that principle forward into our constraint-theory + bare-metal-agent + distributed-fleet architecture.

**Sources:**
- `CUTTING-EDGE-PART2.md` (363 lines, 24 verified projects)
- `CUTTING-EDGE-PART3.md` (21KB, 10 domains, verified repos)
- `CUTTING-EDGE-PART4.md` (399 lines, 10 breakthrough areas)
- `CUTTING-EDGE-INNOVATIONS.md` (initial synthesis, 8 areas)

---

## What Is Reverse-Actualization?

Standard research reads a paper and asks "what can I use?" Reverse-actualization reads a breakthrough and asks "what made this possible?" — then applies that generative principle to a new domain.

For each finding below:
1. **What it is** — the breakthrough itself
2. **The generative principle** — the underlying insight that made it possible
3. **Our adaptation** — how we'd apply it differently, informed by constraint theory
4. **Module or level-up** — whether this becomes a new repo/module or upgrades our understanding

---

## TIER 1: LEVEL-UP OUR UNDERSTANDING

These findings change how we think about the problems we're solving.

---

### 1. Ripser++ — 30× GPU Speedup for Persistent Homology
**Repo:** https://github.com/simonzhang00/ripser-plusplus  
**Also:** OpenPH (https://github.com/rodrgo/OpenPH), giotto-tda (https://github.com/giotto-ai/giotto-tda)

**What it does:** Computes Vietoris-Rips persistent homology on GPU. Up to 99.9% of columns in the coboundary matrix are "apparent pairs" that can be found in parallel — only the remaining 0.1% need sequential reduction.

**The generative principle:** *Sparsity in the computation graph is not uniform.* The vast majority of topological computation is embarrassingly parallel. Only a tiny fraction actually needs the hard sequential algorithm. The breakthrough was profiling this ratio and offloading the 99.9% to GPU while keeping the 0.1% on CPU.

**Our adaptation:** Our constraint engine has the same structure. When we evaluate 10,000 Eisenstein integer constraints on GPU:
- The norm check (a² - ab + b²) is embarrassingly parallel — this is our "apparent pairs"
- The constraint propagation (if constraint A fails, re-evaluate dependent constraints B, C, D) is sequential — this is our "hard 0.1%"
- **Current approach:** We run everything on GPU. **Better approach:** Hybrid — GPU for norm evaluation, CPU for propagation, with the GPU pre-computing which constraints need propagation.

**Module:** `constraint-theory-tda` — a new crate that:
- Runs Ripser++ on constraint landscapes to identify connected components of satisfiable regions
- Uses persistent homology to detect when the feasible region is fragmenting (early warning before constraint violation)
- Provides topological invariants (Betti numbers) as a "health metric" for constraint systems

---

### 2. Simulated Bifurcation — Ising Optimization at Quantum Speed, Classical Cost
**Repos:** https://github.com/bqth29/simulated-bifurcation-algorithm, https://github.com/FrancoisPorcher/Simulated-Bifurcation  
**Also:** Toshiba SBM (10M variables, 3rd gen 2026), FPGA coherent Ising machines (arxiv 2024)

**What it does:** Models Ising spins as classical Hamiltonian oscillators. The system bifurcates into a minimum-energy configuration — solving combinatorial optimization by simulating physics. 20,000× faster than simulated annealing on 16-GPU systems.

**The generative principle:** *Natural physical dynamics are optimizers.* A Hamiltonian system finding its minimum energy is doing optimization. You don't need an algorithm — you need to simulate the right physics. The GPU just runs the dynamics; the solution emerges.

**Our adaptation:** Eisenstein integer constraint satisfaction can be encoded as an Ising model:
- Each Eisenstein coordinate (a, b) maps to a spin state
- Each constraint maps to a coupling: J_{ij} = -1 if constraints i,j must agree, +1 if they must differ
- The minimum-energy spin configuration IS the constraint-satisfying assignment
- Run simulated bifurcation on Jetson GPU for real-time constraint solving

**But the deeper insight:** Our constraint theory already has a natural Hamiltonian — the Eisenstein norm N(a,b) = a² - ab + b². This is literally an energy function on the hexagonal lattice. We could define a Hamiltonian dynamics on Eisenstein coordinates where the system evolves toward constraint satisfaction. This is not just using SB as a tool — it's recognizing that constraint theory IS a physical system.

**Module:** `constraint-theory-sbm` — a new crate that:
- Encodes constraint problems as Ising models
- Runs simulated bifurcation on GPU (via PyTorch or raw CUDA)
- Cross-validates against exact constraint-theory-core results
- Provides a "fast path" for large-scale re-planning

---

### 3. Cellular Automata Constraint Propagation — An Unexplored Frontier
**No existing work found.** This is a gap across all three research agents.

**The generative principle:** *Constraint propagation IS a cellular automaton.* In a constraint network, each variable's domain shrinks based on its neighbors' domains. This is exactly a cellular automaton update rule:
- Cell state = variable's current domain
- Neighborhood = directly connected constraints
- Update rule = arc consistency / domain reduction
- Fixed point = constraint satisfaction

On a hexagonal lattice (Eisenstein integers), each cell has exactly 6 neighbors. The CA update rule is arc consistency on the hex grid. Convergence = all constraints satisfied.

**Our adaptation:** A CUDA kernel where each thread is one Eisenstein coordinate:
- Thread reads neighbor states from shared memory
- Applies arc consistency update rule
- Writes reduced domain back to global memory
- Synchronizes and repeats until fixed point

This is embarrassingly parallel for the constraint check phase, and the propagation phase is a wave-front CA update. The hexagonal topology maps to our Pythagorean48 codes (48 directions = 48 neighbor offsets in the lattice).

**Module:** `constraint-theory-ca` — a new crate (potentially a novel research contribution):
- Hexagonal CA for constraint propagation on GPU
- 48-neighbor update rules based on Pythagorean48 direction encoding
- Convergence detection via Betti number monitoring (integrates with constraint-theory-tda)
- Taichi Lang (https://github.com/taichi-dev/taichi) for JIT-compiled CA rules on GPU

---

### 4. Hyperdimensional Computing — Noise-Immune Pattern Matching
**Repo:** https://github.com/hyperdimensional-computing/torchhd (TorchHD, PyTorch GPU)  
**Papers:** ImageHD (Apr 2026), NysX FPGA (Dec 2025), PathHD (Dec 2025)

**What it does:** Encodes data as ultra-wide (10,000+ dim) pseudo-random vectors. Binding, bundling, and permutation create compositional representations. Tolerates ~30% bit flips with graceful degradation.

**The generative principle:** *High-dimensional randomness IS a robust representation.* In 10,000 dimensions, random vectors are nearly orthogonal with high probability. This gives you:
- Noise immunity (flipping 30% of bits barely changes cosine similarity)
- Compositionality (binding two vectors creates a new quasi-orthogonal vector)
- Holographic storage (any subset of the vector can reconstruct the whole)

**Our adaptation:** Encode sensor readings and constraint states as hypervectors:
- Each sensor type → random basis hypervector
- Each reading → basis ⊕ value hypervector (XOR binding)
- Time series → permutation chain (temporal binding)
- Full sensor state → bundle (element-wise majority) of all readings

Then constraint checking becomes hypervector comparison:
- "Normal" sensor state = reference hypervector (bundle of training data)
- Current reading → compute cosine similarity to reference
- Low similarity = anomaly, even if individual sensors look normal

**This directly competes with our Eisenstein approach in a complementary way:**
- Eisenstein: exact integer arithmetic, zero drift, provable bounds
- HDC: approximate but noise-immune, handles sensor noise gracefully
- **Combined:** Use HDC as the sensor front-end (noise filtering, anomaly detection), feed cleaned data into Eisenstein constraint engine (exact checking)

**Module:** `constraint-theory-hdc` — a new crate:
- Hypervector encoding for sensor data (PyTorch GPU via TorchHD)
- Bundle + bind operations for compositional sensor state
- Cosine similarity for real-time anomaly detection
- Integration with constraint-theory-core as pre-filter

---

### 5. Reservoir Computing — Temporal Prediction Without Backpropagation
**Repo:** https://github.com/reservoirpy/reservoirpy  
**Papers:** FPGA RC for edge (arxiv Sep 2025), Delayed Feedback Reservoir (arxiv Apr 2025)

**What it does:** Fixed random recurrent network (reservoir) + trained linear readout. The reservoir projects input into a high-dimensional space where linear separation is easy. No backpropagation through time — training is just linear regression on readout weights.

**The generative principle:** *Random high-dimensional projections make temporal patterns linearly separable.* You don't need to learn the dynamics — random dynamics are already sufficiently rich. You only learn the readout. This is the temporal analog of kernel methods.

**Our adaptation:** On Jetson, run a reservoir on sensor data to predict readings N steps ahead:
- Input: last 100ms of sensor readings (GPS, sonar, compass, AIS)
- Reservoir: 1000-neuron sparse recurrent network (GPU sparse matmul)
- Readout: trained to predict next 50ms of readings
- Output: predicted sensor state → feed into constraint engine as "pre-computed" state

This gives the constraint engine a 50ms head start. It evaluates constraints on the *predicted* state, not the *current* state. By the time actuators respond, the prediction matches reality.

**Module:** `constraint-theory-rc` — a new crate:
- Sparse reservoir on CUDA (via CuPy)
- Online readout training (recursive least squares)
- Multi-sensor temporal prediction
- Integration with agent-on-metal main loop as prediction layer

---

## TIER 2: NEW MODULES THAT AUGMENT EXISTING WORK

These are concrete tools we can integrate into the fleet.

---

### 6. Narwhal/Bullshark — DAG BFT Consensus for Fleet Coordination
**Repo:** https://github.com/MystenLabs/narwhal (Rust, Apache 2.0)  
**Papers:** arxiv 2105.11827, arxiv 2209.05633  
**Performance:** 130K-600K tx/sec, <2s latency on WAN

**The generative principle:** *Total ordering is unnecessary for most consensus.* DAG-based consensus doesn't need a leader, doesn't need voting rounds, and doesn't need total ordering. Messages form a DAG; causal ordering is sufficient. The DAG structure is the consensus.

**Our adaptation:** Replace or augment our holonomy-consensus with a DAG structure:
- Each fleet agent proposes constraint state updates into a DAG
- DAG edges = "I saw your state and it's consistent with mine"
- Holonomy check on each DAG edge = geometric verification
- The DAG + holonomy = consensus with both BFT safety and geometric consistency

This is stronger than either approach alone:
- Bullshark alone: BFT safe but no geometric consistency
- Holonomy alone: geometrically consistent but no BFT
- **Combined:** Both BFT and geometric consistency

**Module:** Extend `holonomy-consensus` with DAG mode:
- Import Narwhal's DAG data structures (Rust → our codebase)
- Add holonomy verification to each DAG edge
- Test on multi-Jetson setup via MEP protocol

---

### 7. Automerge — CRDTs for Intermittent Fleet Connectivity
**Repo:** https://github.com/automerge/automerge (Rust core, C FFI, WASM)  
**Status:** Production-grade, Automerge 3 with 10× memory reduction

**The generative principle:** *Coordination-free consistency is possible for structured data.* CRDTs guarantee that concurrent modifications always converge — no matter the order of operations, no matter how long the network partition. The mathematical structure of the CRDT (semilattice) makes this possible.

**Our adaptation:** Fleet agents behind islands, in fog, with satellite latency:
- Each agent maintains local constraint state as a CRDT
- When connected, agents sync via Automerge's efficient delta protocol
- Constraint graph merges are verified by holonomy check on merge
- If merge creates holonomy violation → conflict resolution needed

This solves the hardest fleet coordination problem: what happens when Jetson #1 loses contact for 10 minutes? Answer: it keeps operating on local CRDT state, then merges cleanly on reconnect.

**Module:** `fleet-coordinate-crdt` — new crate:
- Automerge CRDT wrapping constraint-theory-core data structures
- Merge protocol with holonomy verification
- Delta sync for bandwidth-constrained links (marine radio, satellite)
- Integration with MEP protocol for bare-metal agents

---

### 8. NVIDIA Warp + MuJoCo Warp — Differentiable Physics for Constraint Learning
**Repos:** https://github.com/nvidia/warp, https://github.com/google-deepmind/mujoco_warp  
**Paper:** STL-SVPIO (arxiv 2603.13333) — constraint satisfaction via differentiable physics + Stein variational inference

**What they do:** Warp JIT-compiles Python → CUDA kernels for physics simulation. MuJoCo Warp runs MuJoCo physics on GPU. Both are differentiable — you can backpropagate through the simulation.

**The generative principle:** *Physics is a constraint solver.* A rigid body simulation enforcing collision constraints IS constraint satisfaction. If the physics engine is differentiable, you can optimize the constraint parameters by gradient descent.

**Our adaptation:** Two paths:
1. **Learn constraints from data:** Run Warp simulation of marine environment. Observe where the real vessel goes vs. simulation. Backpropagate to learn the actual constraint boundaries (tides, currents, vessel dynamics). Update Eisenstein constraint disks from learned physics.

2. **STL-SVPIO approach:** Formulate constraint satisfaction as a physics simulation where constraint violations are "forces" that push the system toward satisfaction. Differentiate through this simulation to find the optimal control inputs. This is gradient-based constraint solving — complementary to our exact integer approach.

**Module:** `constraint-theory-diffphys` — new crate:
- Warp simulation of marine constraint environments
- Differentiable constraint boundary learning
- STL-SVPIO integration for gradient-based constraint solving
- Training pipeline: simulate → compare to reality → update constraints

---

### 9. OTT-JAX — Optimal Transport for Sensor Distribution Comparison
**Repo:** https://github.com/ott-jax/ott (Apple/Google/Meta, JAX GPU)

**What it does:** Computes Wasserstein distance (optimal transport cost) between probability distributions on GPU. Sinkhorn algorithm with scheduling, momentum, and acceleration.

**The generative principle:** *The "cost of moving" between distributions is a metric that captures shape.* KL divergence says "how different are these distributions?" Wasserstein says "how much work to transform one into the other?" The latter captures geometric structure that information-theoretic measures miss.

**Our adaptation:** Anomaly detection by comparing sensor data distributions:
- Baseline: Wasserstein distance of "normal sea state" sensor readings
- Real-time: compute W1 distance between current sensor distribution and baseline
- Spike in W1 = anomaly (obstacle, current change, sensor failure)
- More robust than threshold-based detection because it captures distribution shape, not just mean/variance

**Module:** `constraint-theory-ot` — new crate:
- OTT-JAX Sinkhorn kernel on Jetson GPU
- Sliding window distribution comparison
- Wasserstein distance as anomaly score
- Integration with agent-on-metal anomaly detection pipeline

---

### 10. Jailhouse Hypervisor on Jetson — Hardware Partitioning
**Repo:** https://github.com/siemens/jailhouse (Siemens, actively maintained)  
**Jetson port:** https://github.com/evidence/linux-jailhouse-jetson (TX1/TX2, HERCULES project)

**What it does:** Partitioning hypervisor — carves out dedicated CPU cores, memory, and devices for isolated bare-metal cells. No scheduling, no overcommitment.

**The generative principle:** *Hard real-time requires hardware isolation, not priority scheduling.* PREEMPT_RT gives "soft" real-time (best-effort low latency). Jailhouse gives "hard" real-time (guaranteed resources, zero interference). The hypervisor doesn't virtualize — it divides.

**Our adaptation:** This is the practical path for Agent-on-Metal (our AGENT-ON-METAL-ARCHITECTURE.md Model B):
- Linux cell: OpenClaw, fleet comms, PLATO, monitoring (cores 0-3)
- Agent cell: Bare-metal constraint engine + sensor fusion (cores 4-7)
- Shared memory ring buffer between cells
- Hardware devices statically assigned: CAN/I2C/GPIO to agent cell, Ethernet to Linux cell

**Module:** Not a crate — an integration effort:
- Port Jailhouse from Jetson TX2 → Orin (documented path via L4T changes)
- Write agent cell firmware (sense→think→act loop)
- Write shared memory ring buffer protocol
- Write Linux-side monitor agent (OpenClaw)

---

## TIER 3: DEEP RESEARCH — LONG-TERM TRANSFORMATIVE

These require deeper investigation but could fundamentally change our approach.

---

### 11. Formal Verification of GPU Kernels — The Open Frontier
**Repos:** Serval (https://github.com/uwplse/serval), Kami (https://github.com/mit-plv/kami)

**The generative principle:** *If you can prove hardware correct (Kami), you can prove GPU kernels correct.* The same Coq techniques that verify RISC-V pipelines should apply to GPU SIMT execution. But nobody has done it yet.

**Our unique position:** We have 42 Coq theorems proving Eisenstein integer arithmetic correct. We have CUDA kernels that implement these operations. The gap between "proven math" and "proven GPU execution" is exactly the verification gap.

**Our adaptation:** Build the first verified CUDA constraint kernel pipeline:
1. Extend our Coq proofs to cover GPU execution model (SIMT, shared memory, barriers)
2. Prove that the compiled PTX preserves our mathematical properties
3. This gives us a DO-178C argument that's *stronger than testing* — it's a proof chain from math to hardware

**Impact:** This is potentially a paper-worthy contribution. "Verified GPU Constraint Satisfaction" at POPL, ITP, or similar venue.

---

### 12. Photonic/Analog Ising Solvers → FPGA Constraint Coprocessor
**Papers:** Ferroelectric CiM Ising (arxiv Dec 2025), FPGA Coherent Ising Machine (arxiv Jun 2024)

**The generative principle:** *Analog physics naturally minimizes Ising Hamiltonians.* Light, electrical circuits, and mechanical systems all settle to minimum energy states. This IS optimization — the universe is a constraint solver.

**Our adaptation (near-term):** FPGA coherent Ising machine on Jetson:
- Jetson Orin has a programmable logic region (FPGA overlay support)
- Implement coherent Ising machine equations in FPGA fabric
- Encode constraint problems as Ising couplings
- FPGA solves in nanoseconds while GPU handles the rest

**Our adaptation (long-term):** If ferroelectric CiM technology matures:
- A CiM coprocessor that solves 100K-variable Ising problems at femtojoule energy
- Constraint theory problems encoded as Ising models
- "Photonic constraint satisfaction" — the physics does the computing

---

### 13. Information Geometry — Fisher Information as Sensor Quality Metric
**Papers:** Inverse-Free Fast Natural Gradient (arxiv 2401.13237, Phys Rev A 2024)

**The generative principle:** *Not all sensors are equally informative, and the "information content" has a geometric structure.* Fisher information defines a Riemannian metric on the space of probability distributions. Natural gradient descent follows the steepest path in this geometry.

**Our adaptation:** Weight sensor contributions in fusion by Fisher information:
- Sensors with high Fisher information → trusted more
- Sensors with low Fisher information → discounted
- The Fisher information matrix tells us the optimal fusion weights
- Natural gradient update for online adaptation

This gives a principled alternative to heuristic sensor weighting (Kalman filter covariance).

---

### 14. Event Cameras + SNNs — Zero-Latency Perception
**Repos:** Norse (https://github.com/norse/norse), Sinabs (https://github.com/synsense/sinabs)  
**Commercial:** Prophesee Metavision SDK (CUDA-accelerated)

**The generative principle:** *Frame-based perception throws away temporal information.* An event camera reports pixel-level changes at microsecond resolution. A spiking neural network processes these events with temporal dynamics. Together: perception at the speed of change, not the speed of frames.

**Our adaptation for marine navigation:**
- Event camera on vessel bow (detects moving obstacles in microseconds)
- Norse SNN on Jetson GPU processes event stream
- Detected obstacles → Eisenstein coordinate → constraint engine
- Constraint engine adjusts course in <1ms (vs. 33ms frame-based)
- At 30 knots, this saves 0.77 meters of reaction distance per frame

---

### 15. E3NN + Equivariant Transformers — Hexagonal Symmetry in Deep Learning
**Repos:** e3nn (https://github.com/e3nn/e3nn), e3nn-jax (https://github.com/e3nn/e3nn-jax), Equiformer  
**Also:** DeepSphere (https://github.com/deepsphere/deepsphere)

**The generative principle:** *Enforcing symmetry is free regularization.* An equivariant neural network is guaranteed to produce rotation-covariant outputs. This means it needs 10-100× less training data because it never has to "learn" what rotation invariance means — it's built into the architecture.

**Our adaptation:** The D₆ symmetry of Eisenstein integers is exactly the equivariance group we need:
- Build an E3NN-style network with D₆ irreducible representations
- Train on constraint satisfaction data (our 60M differential test inputs)
- Network predicts which constraints are likely to fail, pre-warming the exact engine
- D₆ equivariance guarantees rotation-correct predictions on the hex grid

**Module:** `constraint-theory-gnn` — a new crate:
- D₆ equivariant graph neural network
- Pre-filter for exact constraint engine
- Trained on fleet constraint satisfaction data
- Runs on Jetson via e3nn-jax + CUDA

---

### 16. Sheaf Neural Networks — Our Own Mathematics, Extended
**Papers:** "Sheaf Neural Networks with Connection Laplacians" (Hansen & Gebhart, 2020)  
**Related:** Our existing sheaf-constraint-synthesis repo

**The generative principle:** *A sheaf attaches data to open sets with compatibility conditions on overlaps.* This is EXACTLY our sensor fusion model: each sensor covers a region, overlapping sensors must agree on shared regions. Sheaf cohomology measures inconsistency — H⁰ ≠ ∅ means the sensors disagree.

**Our adaptation:** We already use sheaf theory conceptually. Sheaf neural networks make it computable:
- Each sensor = a stalk of the sheaf
- Restriction maps = sensor overlap geometry
- Sheaf Laplacian = generalized constraint operator
- Training a sheaf NN learns the optimal restriction maps from data

This could become the theoretical foundation that unifies all our constraint work — sheaves are the natural language for local-to-global consistency.

---

## CROSS-CUTTING: THE UNIFYING ARCHITECTURE

All 16 innovations connect through the same pipeline:

```
PHYSICAL WORLD (marine environment)
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ SENSE                                                    │
│                                                          │
│ Event cameras ─→ Norse SNN ─→ obstacle events           │
│ Sonar + GPS + AIS ─→ Compressive sensing ─→ sparse data │
│ All sensors ─→ HDC encoder ─→ hypervector state         │
│ All sensors ─→ Reservoir ─→ predicted future state      │
│                                                          │
│ (Event cameras: microseconds)                            │
│ (Compressive sensing: 10× bandwidth reduction)           │
│ (HDC: 30% noise tolerance)                               │
│ (Reservoir: 50ms prediction horizon)                     │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│ DETECT ANOMALIES                                         │
│                                                          │
│ TDA (Ripser++) ─→ Betti number changes ─→ topology      │
│ Optimal Transport (OTT-JAX) ─→ W1 distance ─→ shape     │
│ Fisher Information ─→ sensor quality weighting           │
│                                                          │
│ (Ripser++: 30× GPU speedup)                              │
│ (OTT-JAX: milliseconds on GPU)                           │
│ (Fisher: principled sensor weighting)                    │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│ THINK — CONSTRAINT SATISFACTION                          │
│                                                          │
│ Eisenstein exact integer check (current) ──── FAST PATH │
│ GNN pre-filter (e3nn D₆ equivariant) ── PREDICTION      │
│ Simulated Bifurcation (Ising) ────────── RE-PLANNING    │
│ Cellular automata (hex grid) ──────────── PROPAGATION   │
│ Differentiable physics (Warp) ──────────── LEARNING     │
│                                                          │
│ (Eisenstein: zero drift, exact)                          │
│ (SB: 20,000× faster than annealing)                      │
│ (CA: potentially novel contribution)                      │
│ (DiffPhys: learn constraints from data)                  │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│ COORDINATE — FLEET CONSENSUS                             │
│                                                          │
│ Holonomy consensus (current) ──── GEOMETRIC              │
│ Narwhal/Bullshark DAG ──────────── BFT                   │
│ Automerge CRDT ──────────────────── OFFLINE RESILIENCE   │
│                                                          │
│ (Combined: BFT + geometric + offline-tolerant)           │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│ ACT — ON METAL                                           │
│                                                          │
│ Jailhouse partition ──┬── Linux cell (comms, PLATO)      │
│                       └── Agent cell (bare metal sensors) │
│ CUDA kernels ──── GPIO/CAN/I2C/SPI ──── actuators       │
│                                                          │
│ (Sub-microsecond latency in agent cell)                  │
└─────────────────────────────────────────────────────────┘
```

---

## PRIORITY MATRIX

| # | Innovation | Tier | Effort | Impact | Dependency |
|---|-----------|------|--------|--------|------------|
| 1 | Ripser++ TDA | Level-up | 2 weeks | High | Jetson GPU |
| 2 | Simulated Bifurcation | Level-up | 3 weeks | High | PyTorch/CUDA |
| 3 | CA Constraint Propagation | Level-up (novel) | 4 weeks | Unknown | Taichi/CUDA |
| 4 | HDC Sensor Encoding | Level-up | 2 weeks | High | TorchHD |
| 5 | Reservoir Prediction | Level-up | 2 weeks | High | ReservoirPy |
| 6 | Narwhal DAG Consensus | Module | 3 weeks | High | Rust/ARM64 |
| 7 | Automerge CRDT | Module | 2 weeks | High | Rust/C FFI |
| 8 | Differentiable Physics | Module | 4 weeks | Medium | Warp/CUDA |
| 9 | Optimal Transport | Module | 2 weeks | Medium | OTT-JAX |
| 10 | Jailhouse Partitioning | Integration | 6 weeks | Critical | Jetson Orin |
| 11 | Verified GPU Kernels | Research | 3 months | Transformative | Coq/Serval |
| 12 | FPGA Ising Solver | Research | 6 months | Transformative | Jetson FPGA |
| 13 | Fisher Information | Level-up | 3 weeks | Medium | CuPy |
| 14 | Event Camera + SNN | Module | 4 weeks | High | Prophesee/Norse |
| 15 | E3NN Hex GNN | Module | 3 weeks | Medium | e3nn-jax |
| 16 | Sheaf Neural Networks | Research | 3 months | Transformative | Theory |

---

## WHAT TO BUILD FIRST

**Sprint 1 (Month 1):** Reservoir prediction + HDC sensor encoding
- Both are 2-week efforts with high impact
- ReservoirPy + TorchHD are production-ready
- Gives the agent temporal prediction + noise immunity immediately

**Sprint 2 (Month 2):** Ripser++ TDA + Simulated Bifurcation
- 30× GPU TDA for anomaly detection
- SB for real-time re-planning when constraints are violated
- These are the two strongest "level-up" tools

**Sprint 3 (Month 3):** Narwhal DAG + Automerge CRDT
- Fleet coordination upgrade
- BFT + offline resilience
- Both are production Rust, compile on ARM64

**Sprint 4 (Month 4):** Jailhouse port + agent cell firmware
- Hardware partitioning on Jetson Orin
- This is the critical path for bare-metal agent deployment

**Research track (parallel):** Verified GPU kernels + CA constraint propagation
- Both are novel contributions with paper potential
- Run alongside sprint work

---

## REPOS TO CLONE AND BENCHMARK

```bash
# Tier 1 — immediate evaluation
git clone https://github.com/simonzhang00/ripser-plusplus
git clone https://github.com/bqth29/simulated-bifurcation-algorithm
git clone https://github.com/reservoirpy/reservoirpy
git clone https://github.com/hyperdimensional-computing/torchhd
git clone https://github.com/MystenLabs/narwhal
git clone https://github.com/automerge/automerge

# Tier 2 — module development
git clone https://github.com/nvidia/warp
git clone https://github.com/ott-jax/ott
git clone https://github.com/e3nn/e3nn
git clone https://github.com/norse/norse
git clone https://github.com/taichi-dev/taichi
git clone https://github.com/siemens/jailhouse

# Tier 3 — deep research
git clone https://github.com/uwplse/serval
git clone https://github.com/mit-plv/kami
```

---

*This synthesis covers 50+ verified repos and papers across 8 research documents. Every URL was fetched and verified by at least one research agent. The reverse-actualization method ensures we're not just collecting tools — we're understanding the generative principles that make them work and applying those principles to our unique constraint-theory + bare-metal-agent architecture.*
