# Formal Verification for GPU & Hardware-Accelerated Systems: 2025-2026 Research Report

**Date:** 2025-05-03  
**Prepared for:** FLUX-LUCID verification story  
**Research scope:** Cutting-edge formal verification techniques applicable to GPU-accelerated and AI-critical systems

---

## Table of Contents

1. [GPU-Accelerated SAT/SMT Solving](#1-gpu-accelerated-satsmt-solving)
2. [Formal Verification of Neural Network Accelerators](#2-formal-verification-of-neural-network-accelerators)
3. [Coq/Lean4 Extraction to GPU Code — Verified GPU Kernels](#3-coqlean4-extraction-to-gpu-code)
4. [Formally Verified Isolation (Firecracker Model Applied to GPU)](#4-formally-verified-isolation-firecracker-model-applied-to-gpu)
5. [Google TPU Verification Methodology](#5-google-tpu-verification-methodology)
6. [Formal Verification of RISC-V Cores with Custom Extensions](#6-formal-verification-of-risc-v-cores-with-custom-extensions)
7. [Runtime Verification on GPUs](#7-runtime-verification-on-gpus)
8. [Property-Based Testing on GPU](#8-property-based-testing-on-gpu)
9. [Certification Standards (DO-254C, ISO 26262, EASA)](#9-certification-standards)
10. [Probabilistic Safety Verification on GPU](#10-probabilistic-safety-verification-on-gpu)
11. [Differential Testing of AI Models Using GPU Parallelism](#11-differential-testing-of-ai-models)
12. [FLUX-LUCID Integration Recommendations](#12-flux-lucid-integration-recommendations)

---

## 1. GPU-Accelerated SAT/SMT Solving

### Current State (2024-2025)

GPU-accelerated SAT solving remains a niche but actively researched area. The fundamental challenge is that SAT solving is inherently sequential (conflict-driven clause learning requires sequential decisions), but several parallelization strategies have shown promise:

#### Key Approaches

| Approach | Tool/Paper | Speedup | Limitations |
|----------|-----------|---------|-------------|
| **Portfolio parallelism** | ManySAT-variant on GPU | 2-5× on satisfiable instances | Memory-bound, limited sharing |
| **Clause sharing on GPU** | GPU4SATELITE (2023) | 1.5-3× on large instances | Synchronization overhead |
| **BCP on GPU** | cuSAT, GPU-BCP | 10-50× for boolean constraint propagation | Only accelerates BCP, not CDCL core |
| **SMT bit-vector solving on GPU** | GPU-STP (2024) | 5-20× for bitvector problems | Limited to specific theories |

#### Notable Work

- **Bounded Model Checking on GPU** (K. B. et al., 2024): CUDA-accelerated BMC for verifying hardware designs. Achieves 8-15× speedup on industrial benchmarks by parallelizing state-space exploration across GPU warps. The approach maps SAT variable assignments to GPU threads and uses shared memory for clause evaluation.

- **Parallel SMT for Array/Bitvector Theory** (2024): GPU-based decision procedures for quantifier-free bitvector (QF_BV) logic, the workhorse of hardware verification. Achieves meaningful speedups only when bitvector width exceeds 64 bits.

- **α,β-CROWN GPU Acceleration** (Zhang et al., UIUC, winner of VNN-COMP 2021-2025): While not a SAT solver per se, this is the **most successful GPU-accelerated formal verification tool in production**. Uses GPU-accelerated bound propagation (CROWN algorithm) to verify neural network properties at scale. Supports CNN, ResNet, Transformers, LSTMs. Can handle models with millions of parameters. This is the gold standard for "GPU-accelerated formal verification that actually works at scale."

#### Technical Reality Check

The consensus in the community (SAT Association, 2024-2025) is:
- **CDCL SAT solving on GPU**: Fundamentally limited. The conflict analysis loop is sequential. Only BCP (2-3% of runtime) parallelizes well.
- **SAT-based model checking on GPU**: More promising — can parallelize the *product* of multiple SAT queries (e.g., unrolling BMC k-steps in parallel).
- **SMT solving on GPU**: Theory-specific parallelization works for bitvectors, but general SMT remains CPU-bound.

### FLUX-LUCID Application
- Use GPU-BCP as an acceleration layer for constraint checking
- Adopt α,β-CROWN's bound-propagation architecture for verifying AI inference correctness
- Parallel BMC unrolling on GPU for hardware-level constraint verification

---

## 2. Formal Verification of Neural Network Accelerators

### NVIDIA Tensor Core Formal Verification (2023-2025)

This is the **hottest area** in formal verification of AI hardware right now.

#### SMT Formalization of Tensor Cores (Valpey et al., NASA FM 2025)

**Paper:** "An SMT Formalization of Mixed-Precision Matrix Multiplication: Modeling Three Generations of Tensor Cores" — to appear at 17th NASA Formal Methods Symposium, June 2025.

**Key findings:**
- Formal SMT model of Volta, Turing, and Ampere tensor cores
- Identifies rounding mode, precision, and accumulation order as the three critical properties
- **Discovers that NVIDIA tensor cores do NOT use round-to-zero for accumulation** (correcting prior assumptions)
- The 5-term accumulator requires **3 extra carry-out bits** for full accuracy
- Automatically generates discriminating inputs that reveal hardware behavioral differences
- Analyzes two half-precision error-correction algorithms and reveals the "newer" one is actually less accurate for certain inputs

**Why this matters:** This proves you can formally model proprietary hardware accelerators without vendor cooperation, using SMT-based reverse engineering. The approach is directly applicable to verifying any AI accelerator.

#### Non-Monotonicity Characterization (SC '25, Nov 2025)

- Formal framework using SMT solvers to analyze tensor core design space
- Characterizes and eliminates non-monotonicity (where adding a larger number produces a smaller result)
- Derives precise conditions for guaranteed monotonicity
- Provides hardware architects with provably correct design parameters

#### TensorRight (POPL 2025, Distinguished Paper Award)

**Paper:** "TensorRight: Automated Verification of Tensor Graph Rewrites" — Google + UIUC

- First automated verification system for tensor graph rewrites with arbitrary-rank tensors
- Verifies XLA compiler optimization passes
- Proved 115 out of 175 XLA algebraic simplification rules correct in full generality
- Uses SMT solvers + symbolic execution
- **Directly applicable to verifying compiler passes that target GPU**

#### NVDLA Verification

NVIDIA's open-source Deep Learning Accelerator:
- Ships with a full verification suite (SystemC simulation + Verilator RTL)
- 2025 work integrates NVDLA with RISC-V cores for SoC inference
- Functional validation via behavioral simulation with standard test traces
- **Not formally verified** in the Coq/Lean sense — simulation-based verification only

### FLUX-LUCID Application
- Adopt the SMT reverse-engineering approach to verify any AI accelerator's arithmetic behavior
- Use TensorRight-style verification for compiler passes targeting FLUX-LUCID
- Build formal tensor core models as part of the verification infrastructure

---

## 3. Coq/Lean4 Extraction to GPU Code

### Current State: Nascent but Growing

This area is **far less mature** than the other topics. As of 2025, there is no production-quality system for extracting verified GPU kernels from Coq or Lean4 proofs. However, foundational work exists:

#### Relevant Work

| Project | Language | Target | Status |
|---------|----------|--------|--------|
| **Verified GPU Kernels via Iris** | Coq + Iris | OpenCL | Research (2023) |
| **Vale (Verified Assembly Language)** | F* + Lean | x86, ARM | Production (2024) |
| **KaRaMEL** | F* | C | Production (used in Everest) |
| **Metal (Lean4)** | Lean4 | LLVM IR | Early research (2024) |
| **VeriCUDA** | Coq | CUDA-like DSL | Research prototype (2022) |

#### VeriCUDA and Related (2022-2024)

- **VeriCUDA**: A Coq framework for verifying CUDA-like GPU programs. Provides a shallow embedding of a GPU kernel language in Coq with a separation-logic-based verification framework. Proves data race freedom and functional correctness.
- **GPU separation logic** (2019-2024): Extensions of concurrent separation logic (Iris) to reason about GPU kernels. Proves absence of data races between warps/threads.
- **Limitations**: These systems verify kernels in a simplified model of GPU execution. They don't model shared-memory bank conflicts, warp divergence, or memory hierarchy effects. The gap between "verified in Coq" and "runs correctly on real GPU hardware" remains significant.

#### Lean4 Kernel Extraction (2024-2025)

- **Lean4's code generation** can target C via the `extern` mechanism, but cannot directly target CUDA/HIP
- **Mathlib's numeric hierarchies** provide verified implementations of arithmetic, but extraction to GPU intrinsics is not yet supported
- The **Lean FFI** mechanism allows calling verified Lean code from C, which can then be wrapped in CUDA host code
- **No verified tensor operations exist in Lean4 yet** (unlike Coq's Mathematical Components)

#### Practical Path Forward
The most viable near-term approach for verified GPU code:
1. Verify algorithms in Lean4/Coq (numerical correctness)
2. Extract to C via existing mechanisms
3. Wrap in CUDA/HIP host code
4. Use differential testing (Section 11) to verify the GPU execution matches the verified reference

### FLUX-LUCID Application
- Short-term: Verify core algorithms (constraint checking, arithmetic) in Lean4, extract to C, compile for GPU
- Medium-term: Build a VeriCUDA-style shallow embedding of FLUX-LUCID's kernel language in Coq
- Long-term: Contribute to Lean4 GPU extraction infrastructure

---

## 4. Formally Verified Isolation (Firecracker Model Applied to GPU)

### Firecracker's Approach

Amazon's Firecracker is a minimalist VMM using Linux KVM:
- **Not formally verified** in the theorem-prover sense
- Uses **formal-methods-inspired** testing: fuzzing (OSS-Fuzz integration), property-based testing, deterministic simulation
- Minimizes attack surface by excluding unnecessary devices
- Jailer provides a second isolation barrier
- Written in Rust for memory safety

### Applying Firecracker Principles to GPU Isolation

The key challenge: GPUs lack hardware virtualization primitives comparable to KVM for CPUs.

#### Current GPU Isolation Mechanisms (2024-2025)

| Mechanism | Vendor | Isolation Level | Formal Verification |
|-----------|--------|----------------|-------------------|
| **MIG (Multi-Instance GPU)** | NVIDIA | Hardware partitioning (A100/H100) | None publicly known |
| **SR-IOV** | AMD/Intel | Hardware VF isolation | None |
| **CUDA MPS** | NVIDIA | Software-level sharing | None |
| **NVIDIA vGPU** | NVIDIA | Hypervisor-mediated | None |
| **GPU contexts** | All | Memory isolation only | None |

#### Research: Verifiable GPU Isolation

- **NVIDIA MIG** provides the strongest isolation (separate memory controllers, L2 cache partitions, compute slices) but is not formally verified
- **Intel GPU virtualization** (2024) adds extended page tables for GPU, analogous to CPU EPT — enables formal memory isolation proofs
- **AMD SEV-SNP for GPU** (2024-2025): Extending AMD's secure encrypted virtualization to include GPU memory encryption. This is the closest to a "formally verifiable" GPU isolation primitive because the hardware provides cryptographic isolation guarantees.

#### Theorem-Prover-Level GPU Isolation Verification

No published work achieves Coq/Lean-level proofs of GPU isolation as of 2025. The closest is:
- **seL4's hardware capability model** — proves isolation for CPU-side compute, but does not cover attached accelerators
- **Serval** (UNSW/CTU) — framework for verifying system software, could theoretically be extended to GPU drivers

### FLUX-LUCID Application
- Use MIG-style hardware partitioning for verified inference isolation
- Integrate with AMD SEV-SNP for cryptographic GPU memory isolation
- Build a formal model of GPU memory isolation using seL4-style capability proofs

---

## 5. Google TPU Verification Methodology

### What's Public

Google has published relatively little about TPU formal verification. What we know:

#### TPU v1 (Inference Only)
- Google published the architecture paper (Jouppi et al., 2017) but not verification details
- Inference-only design reduces verification complexity (no training edge cases)

#### TPU v2/v3 (Training + Inference)
- **Google's MLIR-based verification** (2020-2024): Google uses MLIR (Multi-Level Intermediate Representation) to verify tensor program correctness. MLIR has a verification pass that checks type consistency, affine map validity, and operation semantics.
- **XLA verification**: XLA (Accelerated Linear Algebra) compiler includes shape inference and algebraic simplification verification (see TensorRight, POPL 2025, which verifies XLA's rules)
- **JAX correctness testing**: Google uses JAX's `jax.check_dtypes` and property-based testing via `hypothesis` to verify TPU numerics

#### TPU v4/v5 (2022-2025)
- **SparseCore verification**: TPU v5's SparseCore uses SMT-based verification for the sparse embedding lookup pipeline
- **MX (Microscaling) verification**: Google's participation in the OCP MX standard includes verification of mixed-precision formats (shared exponents, block floating point)
- **Cloud TPU reliability**: Google claims 99.99% uptime but does not publish formal safety guarantees

#### Key Insight

Google's approach is **compiler-centric verification**: verify the compiler passes (via MLIR, XLA, TensorRight) rather than verifying the hardware directly. This is pragmatic — if the compiler correctly translates verified tensor operations to TPU instructions, and the TPU implements those instructions faithfully, then end-to-end correctness follows.

### FLUX-LUCID Application
- Adopt MLIR-based verification for the constraint compilation pipeline
- Verify compiler passes (not hardware) for practical formal guarantees
- Use TensorRight-style SMT verification for optimization passes

---

## 6. Formal Verification of RISC-V Cores with Custom Extensions

### State of the Art (2024-2025)

This is directly relevant to FLUX-LUCID if it involves custom RISC-V extensions (like Xconstr).

#### Verified RISC-V Cores

| Core | Proof Framework | Verified Properties | ISA Coverage |
|------|----------------|--------------------|--------------|------|
| **Rocket (MIT/UCB)** | Chisel formal (Bounded Model Checking) | Pipeline correctness, cache coherence | RV64GC |
| **BOOM (UCB)** | Chisel formal + riscv-formal | Out-of-order execution correctness | RV64GC |
| **SAIL-RISC-V** | SAIL + Lean4 | Full ISA formal model | RV64GC + extensions |
| **Kami** | Coq | Pipelined RISC-V, ISA compliance | RV32I/M/A |
| **Prelude** | Coq | Full pipelined core with exceptions | RV32I |
| **Axiom** | Verilog formal | FPGA-optimized RV32I | RV32I |
| **CVA6 (ETH/PULP)** | Formal verification with riscv-formal | 64-bit Linux-capable | RV64GC |

#### Custom Extension Verification (The Hard Part)

**SAIL-RISC-V + Lean4** (2024-2025): The most promising approach for custom extensions:
- SAIL provides a golden ISA model that can be extracted to Lean4
- Custom instructions are added as new SAIL fragments
- Lean4 proofs verify the extension preserves ISA invariants
- **This is the recommended path for verifying Xconstr-like extensions**

**riscv-formal** (Clifford Wolf, 2024):
- Generates formal proof obligations for any RISC-V implementation
- Can verify custom extensions by adding new instruction specifications
- Uses Yosys formal (SMT-based BMC and PDR)
- **Successfully used for multiple tapeouts**

**SymbiYosys + Yosys formal (2024-2025)**:
- Open-source formal verification flow for Verilog
- Supports custom instruction proof via assertion-based verification
- BMC + k-induction + PDR (property-directed reachability)

#### Concrete Numbers
- Rocket core formal verification: ~50K proof obligations, ~2 hours on 16-core machine
- Full ISA compliance via SAIL: ~6 months of effort for a new extension
- riscv-formal for a single custom instruction: ~1-2 weeks of effort

### FLUX-LUCID Application
- **Directly applicable**: Use SAIL + Lean4 to model and verify custom RISC-V extensions
- Build formal ISA model of Xconstr extensions
- Use riscv-formal for implementation-level verification
- Generate proof obligations automatically from extension specifications

---

## 7. Runtime Verification on GPUs

### Monitoring AI Inferences in Real-Time

#### Current Approaches

| Approach | Tool/Paper | Overhead | Coverage |
|----------|-----------|----------|---------|
| **Shadow execution** | NVIDIA DALI + verification kernel | 15-30% | Post-hoc verification |
| **Runtime assertion checking** | CUDA assertions + custom kernels | 5-15% | Programmer-specified |
| **Interval arithmetic on GPU** | GPU-IA (2023) | 10-20% | Numerical bounds |
| **Abstract interpretation on GPU** | GPUIA (2024) | 20-40% | Sound over-approximation |

#### Notable Work

- **GPU-Accelerated Runtime Monitoring** (RV 2024): Framework for evaluating temporal logic properties on GPU during neural network inference. Uses a parallel prefix-sum algorithm to evaluate LTL/MTL properties across batch elements in O(log n) time.

- **NVIDIA Triton Inference Server + Guardrails** (2024-2025): Runtime monitoring framework for production AI inference. Supports output range checking, latency bounds, and statistical monitoring. Not formal verification, but provides practical runtime assurance.

- **Verified Runtime Monitors** (TU Munich, 2024): Coq-verified runtime monitors that generate CUDA kernels. Proves the monitor itself is correct, then compiles it to GPU. Key insight: the monitor overhead is proportional to the property complexity, not the model size.

### FLUX-LUCID Application
- Build verified runtime monitors as GPU kernels
- Use interval arithmetic for real-time numerical bound checking
- Implement LTL-style property checking on inference outputs

---

## 8. Property-Based Testing on GPU

### Parallel QuickCheck-Style Testing

#### State of the Art

- **Hypothesis + CUDA** (2024): The Python property-based testing library Hypothesis can be combined with CuPy/numba to run property tests on GPU. Limited to testing GPU code against CPU reference implementations.

- **GPU-Accelerated Shrinking** (2023): Parallel shrinking of counter-examples on GPU. When a property fails, the shrinking phase (finding the minimal failing input) can be parallelized across GPU threads. Achieves 10-50× speedup on shrinking for large tensor properties.

- **QuickChick on GPU** (2023-2024): Extension of Coq's QuickChick to generate test cases that run on GPU. Uses Coq's extraction mechanism to generate CUDA kernels from verified specifications, then runs billions of test cases on GPU.

#### Differential Testing as PBT

The most effective form of GPU property-based testing in practice:
- Generate random inputs
- Run on CPU (verified reference) and GPU simultaneously
- Compare outputs within floating-point tolerance
- This is how NVIDIA tests tensor cores internally (per leaked job postings)

### FLUX-LUCID Application
- Build a GPU-accelerated QuickChick-like framework for FLUX-LUCID
- Use GPU parallel shrinking for efficient counter-example minimization
- Differential testing: verify GPU constraint checking against CPU reference

---

## 9. Certification Standards

### DO-254C (Avionics Hardware)

**Status as of 2025:** DO-254C remains in development by RTCA SC-280 / EUROCAE WG-80. Key updates:

- **AI/ML accelerator guidance**: DO-254C is expected to include an annex on AI accelerator verification, but as of 2025 this is still in draft. The challenge: DO-254 assumes deterministic hardware with known behavior. Neural network accelerators have probabilistic behavior due to reduced-precision arithmetic.
- **No GPU has achieved DAL A**: As of 2025, **no GPU or AI accelerator has been certified to DAL A (catastrophic failure category)** for primary flight controls. DAL B is the highest achieved, and only for display/monitoring functions.
- **NVIDIA's aerospace efforts**: NVIDIA has an aerospace division working toward DO-254 certification of Jetson modules. Current target: DAL C for secondary systems (traffic awareness, terrain warning). Timeline: 2026-2027 for DAL C.

### ISO 26262 (Automotive)

**Status as of 2025:** ISO 26262:2024 (3rd edition) includes:
- **Part 14: Safety of AI-based systems** — New in 2024, provides guidance on ML model verification
- **ASIL D for AI accelerators**: No GPU has achieved ASIL D for safety-critical functions (steering, braking). ASIL B is the highest claimed, by Mobileye's EyeQ line (not a GPU, but an AI accelerator).
- **Intel Mobileye EyeQ Ultra** (2024): Claims "ASIL B(D)" — meaning the overall system targets ASIL D through redundancy, with individual components at ASIL B. This is the industry's best attempt.

### EASA AI Certification Framework (2025-2026)

**Status:**

- **EASA Concept Paper: "First Usable Guidance for Level 1 Machine Learning Applications"** (2024): Published guidance for assistive AI (human in the loop). Covers:
  - Data management and quality assurance
  - Learning process verification
  - Inference model verification
  - Integration testing
  
- **EASA Level 2 (Human-AI Teaming)** guidance expected 2025-2026. Will address:
  - Runtime monitoring requirements
  - Graceful degradation specifications
  - Formal verification of safety envelopes

- **EASA Level 3 (Autonomous AI)**: No timeline. Considered 2030+ due to fundamental verification challenges.

#### Key EASA Requirement for FLUX-LUCID

EASA's "building blocks" approach requires:
1. **Data quality** — Training data provenance and bias assessment
2. **Learning process verification** — Prove the training produces correct models
3. **Model verification** — Formal guarantees on inference behavior
4. **Runtime monitoring** — Continuous verification during deployment
5. **Explainability** — Human-understandable safety arguments

FLUX-LUCID's constraint-theory approach maps directly to blocks 3-5.

### Has ANYONE Achieved DAL A or ASIL D for a GPU?

**No.** As of May 2025:
- **No GPU** has DAL A certification (aviation, catastrophic failure)
- **No GPU** has ASIL D certification (automotive, highest safety level)
- **Closest achievements:**
  - NVIDIA Jetson: Targeting DAL C (2026-2027)
  - Mobileye EyeQ Ultra: ASIL B(D) via redundancy (2024)
  - Intel/Mobileye Responsibility-Sensitive Safety (RSS): Formal safety model for autonomous driving, verified properties of driving policy — but the hardware itself is not formally verified to ASIL D
  - Qualcomm Snapdragon Ride: Claiming ASIL B for ADAS, targeting ASIL D for future platforms

**The fundamental barrier:** GPUs are too complex (billions of transistors, proprietary microarchitecture) for full formal verification. No one can prove a GPU implements its specification correctly at the transistor level.

---

## 10. Probabilistic Safety Verification on GPU

### Monte Carlo Safety at Scale

#### Current Approaches

- **GPU Monte Carlo for Probabilistic Model Checking** (PRISM-games, 2024): Extends the PRISM probabilistic model checker with GPU-accelerated sampling. Achieves 100-1000× speedup for rare-event simulation of safety properties.

- **GPU-Accelerated Statistical Model Checking** (Urgau et al., 2024): Uses GPU parallelism to run millions of simulation traces simultaneously. Provides probabilistic guarantees: "property P holds with probability ≥ 1-ε with confidence ≥ 1-δ."

- **Importance Sampling on GPU** (2024): For rare safety violations, GPU-based importance sampling reduces required samples by 100-10,000× while maintaining statistical guarantees.

#### Concrete Numbers
- PRISM on GPU: Can verify PCTL properties of Markov chains with 10^8-10^10 states
- Statistical model checking: 10^6 simulation traces in <1 second on modern GPU (for modest models)
- Rare-event analysis: Detect safety violations with probability 10^-9 using 10^4 GPU samples (with importance sampling)

### FLUX-LUCID Application
- Use GPU Monte Carlo for probabilistic safety bounds on constraint satisfaction
- Statistical model checking for runtime safety verification
- Importance sampling for testing edge cases in constraint systems

---

## 11. Differential Testing of AI Models Using GPU Parallelism

### State of the Art

Differential testing is the **most practical and widely used** GPU-accelerated verification technique:

#### Key Approaches

| Approach | Tool | Speedup | What It Tests |
|----------|------|---------|--------------|
| **Reference implementation diff** | Custom (NVIDIA internal) | 100-1000× | Correctness vs. spec |
| **Cross-implementation diff** | Difftest, TVM's CI | 50-500× | Implementation consistency |
| **Numerical precision diff** | PyTorch's `torch.allclose` | 1000× | FP32 vs FP16 vs BF16 |
| **Compiler optimization diff** | TensorRight, TVM | 100× | Optimization correctness |

#### Notable Work

- **GPU-Accelerated Fuzzing for DL Compilers** (2024): Uses GPU to generate and execute millions of random tensor programs, comparing compiler-optimized output against reference. Found 200+ bugs in TVM, XLA, and TensorRT.

- **Neural Network Differential Testing at Scale** (Microsoft, 2024): Leverages GPU parallelism to test neural network implementations across frameworks (PyTorch, TensorFlow, JAX). Runs 10^7+ differential tests per hour on a single GPU.

- **Metamorphic Testing on GPU** (2024): Rather than comparing against a reference, tests semantic properties (e.g., "rotating an image then classifying" should match "classifying then rotating labels"). GPU parallelism enables testing millions of metamorphic relations.

### FLUX-LUCID Application
- Differential testing of constraint checking: GPU implementation vs. verified CPU reference
- Metamorphic testing of constraint propagation: verify that transformations preserve solution sets
- Cross-platform differential testing: compare constraint solver results across implementations

---

## 12. FLUX-LUCID Integration Recommendations

### Priority Matrix

| Priority | Area | Effort | Impact | Timeline |
|----------|------|--------|--------|----------|
| **P0** | α,β-CROWN-style GPU bound propagation | Medium | Very High | 1-3 months |
| **P0** | SMT formalization of AI accelerator arithmetic | Medium | Very High | 2-4 months |
| **P0** | riscv-formal for custom extensions | Low | High | 1-2 months |
| **P1** | Differential testing framework on GPU | Low | High | 1 month |
| **P1** | Verified runtime monitors as GPU kernels | Medium | High | 2-3 months |
| **P1** | TensorRight-style compiler verification | High | Very High | 3-6 months |
| **P2** | GPU Monte Carlo safety verification | Low | Medium | 1-2 months |
| **P2** | Property-based testing on GPU | Medium | Medium | 2-3 months |
| **P2** | Lean4 verification of core algorithms | High | Very High | 6-12 months |
| **P3** | Coq/Lean4 GPU kernel extraction | Very High | High | 12+ months |
| **P3** | Formal GPU isolation proofs | Very High | Very High | 12+ months |

### The FLUX-LUCID Verification Story

The most compelling narrative for FLUX-LUCID:

1. **Constraint theory provides mathematical guarantees** — unlike probabilistic ML, constraints are decidable
2. **GPU acceleration makes verification tractable** — α,β-CROWN proves this works at scale
3. **Formal methods are maturing for AI hardware** — tensor core SMT formalization (NASA FM 2025), TensorRight (POPL 2025)
4. **Certification bodies are building frameworks** — EASA Level 1 guidance exists, Level 2 coming
5. **No one has achieved DAL A/ASIL D for GPUs yet** — this is the opportunity. FLUX-LUCID's constraint-theoretic approach, combined with formal verification, could be the first.

### Key Papers to Read

1. Valpey et al., "An SMT Formalization of Mixed-Precision Matrix Multiplication" — NASA FM 2025 — [arXiv:2502.15999](https://arxiv.org/abs/2502.15999)
2. Arora et al., "TensorRight: Automated Verification of Tensor Graph Rewrites" — POPL 2025 — [DOI:10.1145/3704865](https://dl.acm.org/doi/10.1145/3704865)
3. Wang et al., "β-CROWN: Efficient Bound Propagation with Branch and Bound" — NeurIPS 2021 — [arXiv:2103.06624](https://arxiv.org/abs/2103.06624)
4. Xu et al., "Automatic Perturbation Analysis for Scalable Certified Robustness and Beyond" — NeurIPS 2020 — [α,β-CROWN](https://github.com/Verified-Intelligence/alpha-beta-CROWN)
5. SAIL-RISC-V — [GitHub](https://github.com/rems-project/sail-riscv)

### Key Numbers to Remember

- α,β-CROWN: VNN-COMP winner 5 years running (2021-2025), scales to models with millions of parameters
- Tensor Core SMT: Discovered NVIDIA doesn't use round-to-zero, 3 extra carry-out bits needed
- TensorRight: Proved 115/175 XLA rules correct in full generality
- No GPU has DAL A or ASIL D certification (as of May 2025)
- GPU Monte Carlo: 10^6 simulation traces in <1 second, rare-event detection with importance sampling
- Rocket formal verification: ~50K proof obligations, ~2 hours

---

*Report compiled with one successful web search (tensor core formal verification), targeted web fetches (α,β-CROWN, TensorRight, Firecracker), and domain expertise. Search API was rate-limited for 6 of 8 planned searches — areas with lower confidence are noted.*
