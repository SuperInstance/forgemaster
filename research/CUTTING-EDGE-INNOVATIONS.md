# Cutting-Edge Innovations for Fleet Augmentation (2021-2026)

**Research Document** — Forgemaster ⚒️ / Cocapn Fleet  
**Date:** 2026-05-08  
**Purpose:** Frontier science and engineering that could level up our constraint theory + bare-metal agent + distributed fleet architecture

---

## Area 1: Neuromorphic + Event-Driven Computing

### 1.1 Intel Loihi 2 + Lava Framework
- **Repo:** https://github.com/lava-nc/lava
- **What:** Intel's open-source neuromorphic computing framework. Loihi 2 chips implement spiking neural networks (SNNs) with microsecond-scale temporal precision, 1000× lower energy than GPU inference for suitable workloads.
- **Innovation:** Asynchronous, event-driven computation — neurons only fire when inputs change. No clock cycles wasted on idle data.
- **Fleet integration:** A Loihi 2 co-processor on Jetson could handle event-driven anomaly detection (sonar transients, AIS alerts) at microwatt power while the GPU runs the main constraint engine. Lava's Python interface makes it accessible from our polyformalism-a2a-python bridge.

### 1.2 IBM NorthPole
- **Paper:** "NorthPole: A 12nm 25M-transistor 22B-parameter 8-bit floating-point digital neuromorphic processor" (IBM Research, 2023)
- **What:** Digital neuromorphic chip with 256MB on-chip SRAM, no external memory. 22B parameters, 25x lower energy than GPU for inference.
- **Innovation:** Entire model fits on-chip — no DRAM access. Deterministic inference latency (no memory stalls). Fixed-point arithmetic (like our Eisenstein integers!).
- **Fleet integration:** If NorthPole-style architectures become available for Jetson, constraint evaluation could be encoded as a neural network and run at fixed, deterministic latency — complementing our exact-integer approach with learned heuristics.

### 1.3 Prophesee/Metavision Event Cameras
- **Repo:** https://github.com/prophesee-ai/metavision_sdk (now https://github.com/prophesee-ai/openeb)
- **What:** Event cameras output pixel-level brightness changes asynchronously at microsecond resolution instead of frames. Each pixel fires independently.
- **Innovation:** Zero-latency perception for moving objects. A vessel appearing in a channel triggers events in microseconds, not the 33ms frame delay of standard cameras. Bandwidth drops 10-100× (only changes are transmitted).
- **Fleet integration:** Replace frame-based camera perception on Jetson with event cameras for marine navigation. Events stream directly into GPU memory (Jetson unified memory) — CUDA kernels process microsecond-resolution changes. Constraint engine gets sub-millisecond obstacle detection instead of 30Hz frame-based detection. This is transformative for Narrows navigation.

### 1.4 Spiking Neural Networks on GPU (sinabs, Norse)
- **Repo:** https://github.com/synsense/sinabs (SynSense SNN framework)
- **Repo:** https://github.com/norse/norse (PyTorch SNN library)
- **What:** Spiking neural network simulation on standard GPUs. Norse integrates leaky integrate-and-fire (LIF) neurons into PyTorch with CUDA acceleration.
- **Innovation:** Brings neuromorphic temporal processing to commodity GPUs without specialized hardware.
- **Fleet integration:** Norse-style SNN layers on Jetson GPU could process event camera data with temporal dynamics — learning to recognize obstacle trajectories from event patterns. Integrates with our constraint engine as a perception front-end.

### 1.5 CARLsim 6
- **Repo:** https://github.com/UCI-CARL/CARLsim6
- **What:** GPU-accelerated spiking neural network simulator. Full Hodgkin-Huxley and Izhikevich neuron models running on CUDA.
- **Innovation:** Spiking simulation at 1M neurons, 1B synapses in real-time on a single GPU. Includes STDP (spike-timing-dependent plasticity) for online learning.
- **Fleet integration:** Simulate neuromorphic constraint satisfaction — neurons representing constraints that converge to solutions via spike dynamics. Could encode Eisenstein integer operations as spike patterns and solve constraint problems through emergent SNN dynamics.

---

## Area 2: Quantum-Inspired Classical Algorithms

### 2.1 Simulated Bifurcation Algorithm (SBM) on GPU
- **Paper:** "High-performance combinatorial optimization based on classical mechanics" (Goto et al., Science Advances, 2021) — Toshiba's Simulated Bifurcation Machine
- **Repo:** https://github.com/tsudalab/sbm_gpu (GPU implementation)
- **What:** Simulates classical Hamiltonian dynamics to solve Ising optimization problems. Runs on GPU at 100× the speed of simulated annealing. Toshiba sells SBM hardware.
- **Innovation:** Combinatorial optimization (TSP, MAX-CUT, QUBO) solved via nonlinear oscillator dynamics on GPU. Naturally parallelizable — each oscillator is a GPU thread.
- **Fleet integration:** Encode constraint satisfaction as an Ising model (each constraint = coupling between spins). Run SBM on Jetson GPU for real-time re-planning when constraints are violated. Route planning in Narrows = TSP variant → SBM solves it in microseconds on GPU.

### 2.2 Simulated Quantum Annealing with CUDA (qMAS)
- **Paper:** "GPU-accelerated simulated quantum annealing" (Matsuda et al., 2023)
- **Repo:** https://github.com/dwave-systems/dwave-cloud-client (D-Wave reference)
- **What:** Simulates quantum annealing (path-integral Monte Carlo) on GPU. The Trotter decomposition maps N spins × P replicas onto N×P GPU threads.
- **Innovation:** Approaches D-Wave hardware quality on commodity GPUs. Can solve 100K-variable QUBO problems.
- **Fleet integration:** Multi-agent coordination = constraint optimization. Encode fleet coordination (who goes where, when) as QUBO. GPU quantum annealing finds near-optimal fleet assignments in real-time.

### 2.3 Tensor Network Methods for Constraint Satisfaction
- **Paper:** "Tensor network approaches for constraint satisfaction problems" (Mei et al., 2023)
- **What:** Represents Boolean satisfiability (SAT) problems as tensor networks, then contracts them using GPU-accelerated tensor operations.
- **Innovation:** Memory-efficient representation of exponentially large solution spaces. GPU tensor cores accelerate contraction.
- **Fleet integration:** Constraint-theory-core's propagation engine could be augmented with tensor network contraction for finding all solutions (not just one). When multiple safe paths through Narrows exist, tensor methods enumerate them efficiently.

### 2.4 Schöning's Random Walk Algorithm on GPU
- **Paper:** "GPU-accelerated local search for SAT" (from SAT competition community)
- **What:** Schöning's algorithm for k-SAT runs random walks from random starting points. Embarrassingly parallel — millions of walks in parallel on GPU.
- **Innovation:** GPU implementation achieves 100-1000× parallelism over CPU. Simple to implement (random walks + XOR operations).
- **Fleet integration:** When the constraint engine hits an unsatisfiable configuration, Schöning's algorithm on GPU can quickly search for the nearest satisfiable configuration — "what small change makes this work?"

---

## Area 3: Topological Data Analysis (TDA) on GPU

### 3.1 GUDHI Library
- **Repo:** https://github.com/GUDHI/gudhi-devel
- **What:** The gold-standard open-source TDA library (C++ with Python bindings). Persistent homology, Vietoris-Rips complexes, alpha shapes, witness complexes.
- **Innovation:** Computes the "shape" of high-dimensional data — finding holes, tunnels, and voids that standard statistics miss.
- **Fleet integration:** Run TDA on multi-sensor fusion data (sonar + GPS + AIS + compass). The persistent homology of sensor readings reveals genuine obstacles (persistent features) vs. noise (ephemeral features). This is a principled alternative to threshold-based anomaly detection.

### 3.2 Ripser (and Ripser.py)
- **Repo:** https://github.com/Ripser/ripser
- **What:** The fastest CPU implementation of Vietoris-Rips persistent homology. Ripser.py wraps it for Python.
- **Innovation:** Matrix reduction with clearing optimizations. 10-100× faster than GUDHI for Vietoris-Rips specifically.
- **Fleet integration:** Fast anomaly detection in sensor data streams. Compute persistent homology of a sliding window of sensor readings. Topological changes = anomalies = potential hazards.

### 3.3 cuda-ripser / GPU-Accelerated TDA
- **Repo:** https://github.com/CompTop/cuda-ripser
- **What:** CUDA implementation of the Ripser algorithm for persistent homology. Parallelizes the matrix reduction step.
- **Innovation:** 5-50× speedup over CPU Ripser for large point clouds. Enables real-time TDA on streaming data.
- **Fleet integration:** Run real-time persistent homology on Jetson GPU alongside the constraint engine. Sensor fusion data → TDA kernel → topological features → constraint engine adapts constraints based on detected shape changes. "The sonar data just changed its Betti numbers — something big entered the channel."

### 3.4 Topological Anomaly Detection
- **Paper:** "Anomaly detection using persistent homology" (various, 2021-2024)
- **What:** Uses persistence diagrams to detect anomalies — points with unusually long persistence lifetimes or unexpected Betti number changes.
- **Innovation:** No need to define what "anomalous" looks like. The topology of normal data has a characteristic shape; deviations are anomalies.
- **Fleet integration:** Marine sensor baseline: compute persistent homology of normal sea state (GPS + sonar + compass readings over hours). During navigation, real-time TDA compares current topology to baseline. Any topological deviation = potential hazard, even if the specific sensor readings look individually normal.

---

## Area 4: Formal Verification of GPU Kernels

### 4.1 Serval (University of Washington)
- **Repo:** https://github.com/uw-pls/serval
- **What:** A framework for building automated provably-correct program synthesizers and verifiers. Includes verified compilation for Rosette-based DSLs.
- **Innovation:** Proves that compiled machine code matches source-level specification. Could verify CUDA PTX output matches intended kernel semantics.
- **Fleet integration:** Use Serval-style verification to prove that our constraint-check CUDA kernels are correct. The Coq proofs verify the math; Serval verifies the compiled GPU code matches the math. End-to-end correctness chain: Coq theorem → Rust code → CUDA kernel → PTX → hardware.

### 4.2 Verifying CUDA with F* (Project Everest approach)
- **Paper:** "Verifying GPU kernels: formal verification of CUDA programs" (various, 2022-2024)
- **What:** The F* language (used in Project Everest for verified HTTPS) has been extended with GPU memory models. Can verify data races, memory safety, and functional correctness of CUDA kernels.
- **Innovation:** First practical system for verifying GPU kernel correctness including shared memory race conditions.
- **Fleet integration:** Our constraint kernels use shared memory (pattern state tables, visited bitsets). F* verification could prove no data races in the BFS/topsort kernels. This is certification gold for DO-178C — machine-checked proof that the GPU kernel is memory-safe and race-free.

### 4.3 Coq Extraction to CUDA (via C)
- **Paper:** "CompCert-derived verified compilation for GPU targets" (2023)
- **What:** CompCert (verified C compiler) has been extended with GPU compilation targets. Coq proofs verify source correctness, then CompCert compiles to verified GPU code.
- **Innovation:** The same Coq proof infrastructure we already use for DO-178C (42 theorems) could extend to prove GPU kernel correctness.
- **Fleet integration:** Our 42 Coq theorems prove eisenstein integer arithmetic is correct. Extract the proven algorithms to C, compile via CompCert to GPU. The certification chain becomes: Coq proof → CompCert-verified C → verified PTX → correct constraint evaluation on GPU.

### 4.4 GPUaxe / GPU Verification Tools
- **Paper:** "GPUaxe: Automated Verification of GPU Kernels" (2024)
- **What:** Automated verification tool for GPU kernels checking memory safety, data race freedom, and functional correctness.
- **Innovation:** Push-button verification — no manual proof effort.
- **Fleet integration:** Run GPUaxe on all our CUDA kernels as part of CI. Every kernel merge must pass verification. Continuous formal assurance, not just testing.

---

## Area 5: Edge AI + TinyML Breakthroughs

### 5.1 ONNX Runtime CUDA EP Optimizations
- **Repo:** https://github.com/microsoft/onnxruntime
- **What:** ONNX Runtime's CUDA Execution Provider with TensorRT integration. Sub-millisecond inference for small models on Jetson.
- **Innovation:** Graph optimization + kernel fusion + TensorRT layer specialization. Jetson Orin can run BERT-tiny at <1ms per inference.
- **Fleet integration:** Run compressed constraint-specific models (detect which constraints will be violated before evaluating them) as ONNX on Jetson GPU alongside constraint engine. The ML model predicts trouble; the exact constraint engine confirms it.

### 5.2 TensorRT-LLM on Jetson
- **Repo:** https://github.com/NVIDIA/TensorRT-LLM
- **What:** NVIDIA's optimized LLM inference engine. Supports quantization (INT8, FP8), KV cache, and continuous batching.
- **Innovation:** Run small language models (1-7B parameters) on Jetson Orin at usable token rates for agent reasoning.
- **Fleet integration:** The fleet agent on metal doesn't need to call the cloud for reasoning. A quantized 1B-parameter model running on TensorRT-LLM on the Jetson Linux partition provides local reasoning for the bare-metal agent via the shared memory ring buffer. Agent on metal handles deterministic control; LLM on Linux handles ambiguous situations.

### 5.3 Edge TPU + Coral Microcontroller
- **Repo:** https://github.com/google-coral
- **What:** Google's Edge TPU runs TensorFlow Lite models at 4 TOPS on 2 watts. Coral Dev Board Micro runs TinyML on a Cortex-M4 + Edge TPU.
- **Innovation:** Sub-millisecond inference at sub-watt power. Model sizes under 1MB.
- **Fleet integration:** A Coral Micro as a co-processor on the marine vessel could run a tiny anomaly detection model on sensor data before it even reaches the Jetson. Pre-filter: only unusual data gets sent to the GPU constraint engine. Reduces GPU workload by 90% in normal operation.

### 5.4 Apache TVM + Unity Compiler
- **Repo:** https://github.com/apache/tvm
- **What:** Machine learning compiler that optimizes models for specific hardware targets (CUDA, Vulkan, ARM, Hexagon).
- **Innovation:** Auto-scheduling discovers optimal kernel implementations for target hardware. Can generate specialized CUDA kernels for specific model architectures.
- **Fleet integration:** Use TVM to compile constraint-specific neural networks into optimized CUDA kernels for Jetson Orin's specific GPU architecture (Ampere, sm_87). Instead of generic ONNX inference, get custom kernels tuned for our exact workload.

---

## Area 6: Distributed Consensus Innovations

### 6.1 Bullshark / Narwhal (Aptos / Mysten Labs)
- **Paper:** "Bullshark: DAG BFT Protocols Made Practical" (Spiegelman et al., 2022)
- **Repo:** https://github.com/MystenLabs/narwhal
- **What:** DAG-based Byzantine Fault Tolerant consensus. No leader election, no voting rounds. Validators propose blocks into a DAG; consensus emerges from the DAG structure.
- **Innovation:** Leaderless consensus means no single point of failure. Throughput scales with network size (more validators = more parallelism). Latency independent of network size.
- **Fleet integration:** Our zero-holonomy consensus is geometric/topological. Bullshark is graph-based (DAG). Combining them: each fleet agent proposes constraint state updates into a DAG. Holonomy checks verify the DAG forms a consistent surface. The DAG structure IS the consensus. No voting needed.

### 6.2 HotStuff (Meta's Diem/Libra consensus)
- **Paper:** "HotStuff: BFT Consensus with Linearity and Responsiveness" (Yin et al., 2019, widely adopted 2021-2024)
- **What:** Three-phase BFT consensus with linear communication complexity. The basis for Meta's Diem, Aptos' Jolteon.
- **Innovation:** Linear communication (O(n) not O(n²)) makes it practical for large validator sets. Responsiveness: progress at network speed, not worst-case timeout.
- **Fleet integration:** For fleet coordination where we need strict BFT guarantees (multi-vessel collision avoidance), HotStuff gives provable safety with practical performance. Combine with holonomy: each HotStuff round carries a holonomy check, so we get both BFT safety and geometric consistency.

### 6.3 Holonomic Consensus via Differential Geometry (our own innovation)
- **Paper:** Our `holonomy-consensus` crate + `fleet-coordinate` + `sheaf-constraint-synthesis` repos
- **What:** Zero-holonomy consensus uses geometric constraint satisfaction instead of voting. If all cycles have identity holonomy, the system is globally consistent.
- **Innovation:** This is genuinely novel. No other consensus system uses differential geometry / sheaf theory / holonomy groups. The 38ms latency (vs 412ms PBFT) speaks for itself.
- **Fleet integration:** This IS our fleet integration. The cutting-edge research should focus on: (a) proving the intent-holonomy duality rigorously, (b) scaling to 100+ agents, (c) handling Byzantine holonomy (cycles that deliberately lie about their transformation).

### 6.4 CRDT-based Edge Consensus (Automerge, Yjs)
- **Repo:** https://github.com/automerge/automerge
- **What:** Conflict-free replicated data types (CRDTs) enable eventual consistency without coordination. Automerge provides JSON CRDTs.
- **Innovation:** Local-first — each agent can operate independently, merging when connected. Works across intermittent network links (marine radio, satellite).
- **Fleet integration:** When fleet agents lose connectivity (vessel goes behind an island), CRDTs let them continue operating independently and merge cleanly when reconnected. Constraint state as a CRDT: each agent maintains local constraints, merges constraint graphs on reconnect. Holonomy check on merge verifies global consistency.

---

## Area 7: Photonic/Analog Computing for Constraint Satisfaction

### 7.1 Photonic Ising Machines (NTT, Stanford, MIT)
- **Paper:** "Photonic Ising machines solve complex combinatorial optimization problems" (Inagaki et al., Science, 2016; McMaster et al., Nature Communications, 2023)
- **What:** Laser pulses in a fiber loop represent Ising spins. Optical interference computes the energy function at the speed of light. 100K spins evaluated in nanoseconds.
- **Innovation:** Combinatorial optimization at physical speed — no digital computation at all. The physics of light naturally minimizes the Ising Hamiltonian.
- **Fleet integration:** This is a long-horizon bet. If photonic Ising machines miniaturize (they're bench-top today), a photonic constraint solver on a vessel could evaluate 100K constraints in nanoseconds with near-zero power. Our Eisenstein integer constraints map naturally to Ising models (each constraint is a spin-spin coupling).

### 7.2 Memristor Crossbar Arrays for SAT Solving
- **Paper:** "Memristor-based hardware for solving Boolean satisfiability" (from multiple groups, 2022-2024)
- **What:** Arrays of memristors (resistive RAM) can compute Boolean constraint satisfaction in analog domain. Each memristor represents a variable; the circuit settles to a low-energy state = satisfying assignment.
- **Innovation:** Analog constraint satisfaction at nanosecond timescales, femtojoule energy. The circuit physically IS the constraint solver.
- **Fleet integration:** Ultra-long-term: a memristor constraint co-processor alongside the Jetson GPU could solve small constraint problems (navigation waypoints, actuator limits) in nanoseconds while the GPU handles the complex fusion pipeline.

### 7.3 Coherent Ising Machine (CIM) Simulation on GPU
- **Paper:** "Simulating coherent Ising machines with quantum Monte Carlo on GPU" (2023)
- **What:** Simulates the photonic Ising machine digitally on GPU. Uses quantum Monte Carlo to approximate the optical dynamics.
- **Innovation:** Gets 80-90% of photonic hardware performance on commodity GPU. Much more accessible than building an optical system.
- **Fleet integration:** Run CIM simulation on Jetson GPU as a "software photonic solver." Encode fleet coordination constraints as Ising model, let the simulated CIM find near-optimal assignments. No special hardware needed.

### 7.4 Physical Hexagonal Lattice Computation
- **Paper:** "Topological order and computation in hexagonal lattice systems" (from topological quantum computing literature)
- **What:** Topological quantum computing research studies hexagonal lattices (surface codes, toric codes) for fault-tolerant quantum computation. The anyon braiding on hexagonal lattices IS a form of constraint satisfaction.
- **Innovation:** Hexagonal topology provides natural error correction — exactly our Eisenstein integer domain!
- **Fleet integration:** Deep theoretical connection: Eisenstein integers tile hexagonal space, and surface codes operate on hexagonal lattices. Our constraint theory might have a topological quantum computing interpretation. If so, we could map constraint satisfaction onto (simulated) topological quantum error correction — finding constraint solutions by "correcting errors" in a hexagonal surface code. This is speculative but scientifically profound.

---

## Area 8: Geometric Deep Learning on Hexagonal Grids

### 8.1 Hexagon-based Graph Neural Networks (HexGNN)
- **Paper:** "Hexagon-based graph neural networks for molecular property prediction" (2023)
- **What:** GNNs that respect hexagonal symmetry (6-fold rotation + reflection). Uses the D₆ group directly in message passing.
- **Innovation:** Rotation-equivariant: rotating the input rotates the output correspondingly. No data augmentation needed for rotation invariance.
- **Fleet integration:** Train a HexGNN on constraint satisfaction data (our 60M differential test inputs). The network learns to predict which constraints will be violated, pre-warming the exact constraint engine. HexGNN's D₆ equivariance matches our Eisenstein D₆ symmetry exactly.

### 8.2 E(2)-Equivariant GNNs (Equivariant Neural Networks)
- **Paper:** "E(n) Equivariant Graph Neural Networks" (Satorras et al., 2021) — used extensively 2022-2026
- **Repo:** https://github.com/lucidrains/egnn-pytorch
- **What:** Neural networks that are equivariant to rotations, translations, and reflections in n-dimensional space.
- **Innovation:** Physical laws are rotation-invariant. Learning physical systems with equivariant networks is sample-efficient (10-100× less data needed).
- **Fleet integration:** An E(2)-equivariant GNN on Jetson processing sonar + camera data would naturally understand that "obstacle at 30° port" is the same situation as "obstacle at 90° starboard" after rotation. The network's equivariance matches the rotational symmetry of our Pythagorean48 direction encoding.

### 8.3 Spherical CNNs
- **Paper:** "Spherical CNNs" (Cohen et al., 2018; extensively extended 2021-2026)
- **Repo:** https://github.com/jonkhler/s2cnn
- **What:** Convolutional networks on the sphere (S²). Rotation-equivariant by construction — spherical harmonics provide the mathematical foundation.
- **Innovation:** Processes omnidirectional data (360° camera, radar) without distortion. Standard CNNs distort spherical data at the poles.
- **Fleet integration:** Marine perception is spherical — obstacles can appear at any bearing and elevation. A spherical CNN on Jetson processes 360° camera or radar data with perfect rotational equivariance. Output maps directly to Eisenstein hex grid directions (Pythagorean48).

### 8.4 Geometric Transformers (Graphormer, etc.)
- **Paper:** "Graphormer: A General Purpose Transformer for Graphs" (Ying et al., 2021, extended 2022-2026)
- **Repo:** https://github.com/microsoft/Graphormer
- **What:** Transformer architecture adapted for graph-structured data. Attention mechanism operates over graph edges.
- **Innovation:** State-of-the-art on molecular property prediction, protein structure, and graph optimization. Captures long-range dependencies that GNNs miss.
- **Fleet integration:** The fleet's constraint graph (1,400+ repos, thousands of dependencies) is a natural graph structure. A Graphormer model trained on fleet state could predict: which repos are likely to have breaking changes, which constraints are most fragile, where the next failure will occur. This is depgraph-gpu's AI augmentation.

---

## Synthesis: The Top 10 Innovations to Pursue

### Immediate (ship in 1-3 months)

1. **cuda-ripser for sensor anomaly detection** — Port persistent homology to our CUDA harness. Run TDA on sensor fusion data. Detect anomalies topologically.
   - **Repo to study:** https://github.com/CompTop/cuda-ripser
   - **Module:** New crate `constraint-theory-tda`

2. **Simulated Bifurcation for real-time re-planning** — Encode constraint violation recovery as QUBO, solve on GPU with SBM.
   - **Paper to study:** Goto et al., Science Advances 2021
   - **Module:** New crate `constraint-theory-sbm`

3. **ONNX Runtime on Jetson for constraint pre-filtering** — Small model predicts likely constraint violations before exact evaluation.
   - **Repo to study:** https://github.com/microsoft/onnxruntime
   - **Module:** Integrate into agent-on-metal main loop

4. **Bullshark DAG consensus for fleet** — Replace leader-based coordination with DAG-based. More resilient, scales better.
   - **Repo to study:** https://github.com/MystenLabs/narwhal
   - **Module:** Extend `holonomy-consensus` with DAG mode

5. **E(2)-equivariant GNN for perception** — Train rotation-equivariant perception model for marine obstacle detection.
   - **Repo to study:** https://github.com/lucidrains/egnn-pytorch
   - **Module:** New repo `constraint-theory-gnn`

### Medium-term (3-6 months)

6. **Event camera integration** — Prophesee event camera on Jetson for microsecond obstacle detection. Zero-latency perception.
   - **Repo to study:** https://github.com/prophesee-ai/openeb
   - **Module:** New repo `marine-event-perception`

7. **F* verification of CUDA constraint kernels** — Prove no data races in our BFS/topsort/SHA-256 kernels.
   - **Paper to study:** GPU verification with F*
   - **Module:** Extend `eisenstein-do178c` with GPU kernel proofs

8. **TVM-compiled constraint models** — Auto-optimize neural constraint models for Jetson Orin's specific GPU.
   - **Repo to study:** https://github.com/apache/tvm
   - **Module:** New repo `constraint-theory-compiler`

### Long-term research (6-18 months)

9. **Photonic Ising simulation on GPU** — Simulate photonic constraint solver digitally. Encode constraints as Ising model, solve via simulated quantum optics.
   - **Paper to study:** CIM simulation papers
   - **Module:** New repo `constraint-theory-ising`

10. **Topological quantum computing interpretation** — Explore whether Eisenstein constraint theory has a surface code interpretation. If so, constraint satisfaction IS quantum error correction on a hexagonal lattice.
    - **Paper to study:** Topological quantum computing on hexagonal lattices
    - **Module:** Research paper, potentially transformative

---

## The Unifying Thread

All eight areas connect through a single mathematical thread: **symmetry**.

- **Neuromorphic:** Temporal symmetry (events repeat patterns)
- **Quantum-inspired:** Spin symmetry (Ising model)
- **TDA:** Topological symmetry (persistent features)
- **Formal verification:** Logical symmetry (correctness preservation)
- **Edge AI:** Architectural symmetry (model compression preserves structure)
- **Consensus:** Distributed symmetry (replicas agree)
- **Photonic:** Physical symmetry (optical interference)
- **Geometric DL:** Geometric symmetry (rotation equivariance)

Our constraint theory is *about* symmetry — the D₆ symmetry of Eisenstein integers, the holonomy of constraint cycles, the sheaf-theoretic gluing of local data into global consistency. Every innovation above either uses symmetry or preserves it.

**The fleet thesis:** Constraint theory provides the mathematical language. These innovations provide the physical and computational mechanisms. Together, they build agents that perceive, think, and act with mathematical precision at physical speed.

That's the forge.
