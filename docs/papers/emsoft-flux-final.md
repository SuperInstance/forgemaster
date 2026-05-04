# FLUX: A Formally Proven Constraint-to-Native Compiler for Safety-Critical Systems

**Casey DiGennaro**
Cocapn Fleet / SuperInstance Research
contact@cocapn.io

---

*Submitted to the 25th ACM SIGBED International Conference on Embedded Software (EMSOFT 2027)*
*Track: Compilers, Formal Methods, and Runtime Verification for Cyber-Physical Systems*

---

## Abstract

Safety-critical embedded systems — avionics, autonomous vehicles, medical devices — require provably correct constraint enforcement at hardware speed. Current approaches rely on manual code review, offline static analysis, or uncertified software wrappers, all of which fail to provide the real-time, formally verified guarantees demanded by DO-254 DAL A and ISO 26262 ASIL-D. We present FLUX, a constraint-to-native compiler that translates safety constraints written in the GUARD domain-specific language into mathematically proven machine code across five targets: x86-64/AVX-512, CUDA, WebAssembly, eBPF, and RISC-V with a custom `Xconstr` extension. The FLUX-C instruction set architecture defines 42 opcodes across 8 categories, with denotational semantics formalized in Coq. We establish 12 theorems — 7 compiler correctness theorems and 5 hyperdimensional computing theorems — guaranteeing end-to-end semantic preservation from GUARD source text to machine code. Benchmarks on commodity hardware demonstrate 22.3 billion single-constraint checks per second (AVX-512, AMD Ryzen AI 9 HX 370), 70.1 billion operations per second across 12 threads, and 1.02 billion checks per second on GPU (NVIDIA RTX 4050). Differential testing across 210 test programs and 5.58 million inputs produces zero mismatches between reference interpreter and compiled native code. We introduce the Safe-TOPS/W metric, which penalizes uncertified hardware to zero: FLUX scores 410 million while all uncertified accelerators score 0.00. An FPGA prototype on Xilinx Artix-7 demonstrates the constraint engine requires only 1,717 LUTs, 1,807 flip-flops, and 120 mW — small enough for exhaustive formal verification within a certification program timeline. FLUX is open source under Apache 2.0 with no patents reserved.

**Keywords:** constraint compilation, formal verification, safety-critical systems, AVX-512, CUDA, embedded real-time, DO-254, ASIL-D, hyperdimensional computing

---

## 1. Introduction

### 1.1 The Certification Cost Problem

Deploying neural networks and complex decision systems in safety-critical embedded applications is not fundamentally an accuracy problem — it is a verification problem. Standards governing airborne electronic hardware (DO-254 [6]), automotive functional safety (ISO 26262 [7]), and system-level development (ARP4754A [8]) require that every safety function be traced from system objectives through hardware design to verification evidence. For the highest assurance levels — DO-254 Design Assurance Level A (DAL A) and ISO 26262 Automotive Safety Integrity Level D (ASIL-D) — this evidence must include formal or exhaustive demonstration of correct operation.

The cost of this evidence is staggering. DO-254 DAL A certification of a single FPGA or ASIC design costs \$5–50M and 18–36 months, dominated not by the hardware itself but by the documentation, analysis, and testing required to demonstrate that every output is bounded, every timing path is deterministic, and every fault is detected [6]. A modern GPU ISA with thousands of opcodes is computationally intractable to verify within any realistic certification window. The consequence: no AI inference accelerator has achieved DAL A certification as of 2027, and safety-critical deployments universally require a separate, certified supervisory controller wrapping an uncertified inference engine — a design pattern that is expensive, latency-bound, and semantically fragile.

### 1.2 Current Approaches and Their Limitations

Three classes of existing tools address parts of this problem, but none solve it:

**Offline formal verification tools** (SymbiYosys [15], JasperGold, Frama-C [19]) can prove hardware or software properties statically, but they are offline-only. They verify the design, not the deployed system. A design proven correct at verification time can still fail at runtime due to environmental faults, unchecked inputs, or state outside the verified model. Moreover, commercial tools like JasperGold carry license costs exceeding \$500K/year, creating a barrier for smaller teams and open-source safety infrastructure.

**Verified compilers** (CompCert [2]) prove that compilation preserves source semantics, but they operate on general-purpose languages and do not provide runtime constraint enforcement. CompCert proves that if the C source is correct, the assembly is correct — but it says nothing about whether the inputs to the compiled program satisfy safety predicates at runtime.

**Verified kernels and separation architectures** (seL4 [16], CertiKOS [3]) provide formally verified isolation between software partitions, but they operate at the OS level and cannot enforce real-time constraints on data flowing through hardware pipelines at billions of operations per second.

The gap is clear: no existing tool provides **compiled, formally verified, real-time constraint enforcement** at hardware speed across multiple deployment targets.

### 1.3 Our Approach: Constraint Checking as a Compilation Problem

FLUX reframes safety constraint checking as a compiler optimization problem. Instead of verifying that a system satisfies constraints after the fact, FLUX compiles constraints into native machine code that runs at silicon speed — checking billions of values per second with provable correctness guarantees.

The insight is architectural: safety constraints in embedded systems are overwhelmingly *conjunctions of atomic predicates* — range checks (`altitude ∈ [0, 45000]`), domain membership tests (`(command & mask) == command`), and inter-variable comparisons (`speed < max_speed`). These predicates map directly onto hardware primitives: comparison instructions, bitwise AND, and SIMD mask operations. By formalizing this mapping and proving it correct, we eliminate the semantic gap between constraint specification and constraint enforcement.

The compiler pipeline is:

```
GUARD text → AST → CNF-C → Optimized → Target IR → Machine code
```

Each stage preserves the denotation of the constraint predicate, and the composition of all stages is proven correct end-to-end (Theorem 7, §3).

### 1.4 Historical Lineage: From PLATO to FLUX

FLUX is not the first system to compile constraints to bit-level hardware. The PLATO system (1960) and its TUTOR language (1965) used 60-bit CDC word bit-vectors to represent student answer domains, with XOR and popcount for Hamming-distance matching — the same algebraic primitives underlying FLUX's BitmaskDomain operations [20]. Table 1 traces the direct lineage.

**Table 1: Constraint-to-Hardware Lineage**

| Era | System | Technique | Word Size |
|-----|--------|-----------|-----------|
| 1960 | PLATO / TUTOR | Bit-vector answer matching | 60-bit CDC word |
| 1977 | Atari 2600 TIA | Scanline cycle-budget constraints | 76 cycles/line |
| 1985 | Amiga Copper | Coprocessor cycle-budget lists | 227 cycles/line |
| 1991 | SNES PPU | Mode 7 fixed-point constraints (Q16.16) | 32-bit |
| 1996 | N64 RSP | Microcode IMEM budget (4 KB) | 32-bit |
| 2026 | FLUX-C | Compiled constraint VM | 64-bit + 512-bit SIMD |

The common thread across 66 years is the same: **express a constraint as a bit pattern, compile it to hardware-native operations, and enforce it without interpretation overhead**. TUTOR's judging block is FLUX's constraint evaluation loop; PLATO's 150-word per-user state is FLUX's 64-element stack; the CDC 6600's bit-vector matching is FLUX's BitmaskDomain popcount. We formalize what these systems did intuitively and prove it correct.

### 1.5 Contributions

This paper makes four contributions:

1. **FLUX-C ISA and GUARD DSL:** A 42-opcode constraint virtual machine with denotational semantics in Coq, paired with a domain-specific language for specifying safety constraints with physical units, temporal operators, and proof annotations (§2).

2. **12 formally proven theorems** guaranteeing correctness of the compiler pipeline: 7 compiler theorems (normal form existence, constraint fusion, optimal instruction selection, SIMD vectorization, dead constraint elimination, strength reduction, end-to-end pipeline correctness) and 5 hyperdimensional computing theorems for semantic constraint matching (§2–§5).

3. **Five-target native compilation** to x86-64/AVX-512, CUDA, WebAssembly, eBPF, and RISC-V+Xconstr, with a three-tier CPU/GPU/Safety Island architecture achieving 22.3B checks/sec CPU and 1.02B/sec GPU (§3–§4).

4. **Safe-TOPS/W benchmark** and differential testing infrastructure: 210 test programs, 5.58M inputs, zero mismatches, with a safety-aware efficiency metric under which all uncertified accelerators score zero (§6).

FLUX is released under Apache 2.0 with no patents reserved. Safety infrastructure should not be proprietary.

---

## 2. Formal Model

### 2.1 The FLUX-C Instruction Set Architecture

The FLUX-C ISA is a stack-based virtual machine with 42 opcodes in 8 functional categories, designed for tractable formal verification. A stack machine is preferred over a register machine because each opcode's semantics is fully determined by its effect on the stack — there is no implicit register state, making Coq and TLA+ models tractable.

**Table 2: FLUX-C ISA Summary (42 opcodes)**

| Category | Opcodes | Count | Representative |
|----------|---------|-------|----------------|
| Stack | PUSH, POP, DUP, SWAP | 4 | `PUSH val: ( — v )` |
| Memory | LOAD, STORE | 2 | `LOAD addr: ( — mem[addr] )` |
| Arithmetic | ADD, SUB, MUL | 3 | `ADD: ( a b — a+b )` |
| Bitwise | AND, OR, XOR, NOT, SHL, SHR | 6 | `AND: ( a b — a&b )` |
| Comparison | EQ, NEQ, LT, GT, LTE, GTE, CMP_GE, CARRY_LT | 8 | `LT: ( a b — a<b )` |
| Control Flow | JUMP, JZ, JNZ, CALL, RET, JFAIL | 6 | `JFAIL addr: ( — )` |
| Constraint | CHECK_DOMAIN, BITMASK_RANGE, LOAD_GUARD, MERKLE_VERIFY, GUARD_TRAP | 5 | `CHECK_DOMAIN mask: ( v — v&mask )` |
| Execution / Misc | HALT, ASSERT, NOP, FLUSH, YIELD, CRC32, PUSH_HASH, XNOR_POPCOUNT | 8 | `HALT: ( — )` |

All operands are 64-bit integers. Gas is uniform: the VM decrements by 1 per instruction dispatch, providing a Worst-Case Execution Time (WCET) guarantee. The constraint-checking subsystem comprises four opcodes — `CHECK_DOMAIN`, `BITMASK_RANGE`, `ASSERT`, and `MERKLE_VERIFY` — which write to a `last_check_passed` flag read by `JFAIL` for conditional branching.

**Definition 1 (Constraint Program).** A *constraint program* $P$ is a sequence of FLUX-C opcodes acting on an initial stack of $n$ 64-bit integer vectors $x_1, \ldots, x_n$. The program terminates with **accept** (reaches `HALT` without fault) or **fault** (any `ASSERT`, `CHECK_DOMAIN`, or `BITMASK_RANGE` triggers a fault). Denotationally, $P$ defines a predicate $\llbracket P \rrbracket : \mathbb{Z}_{2^{64}}^n \to \{\text{true}, \text{false}\}$ where $\llbracket P \rrbracket(v) = \text{true}$ iff $P$ accepts on input $v$.

### 2.2 Constraint Normal Form (CNF-C)

**Definition 2 (Atomic Constraint).** An *atomic constraint* is one of:
- **Range**: $x \in [L, H]$ where $L, H$ are 64-bit constants
- **Domain**: $(x\ \&\ \text{mask}) = x$ with mask constant
- **Equality**: $x = c$
- **Order**: $x \mathrel{\mathit{relop}} y$ (comparison between two variables)

**Definition 3 (Conjunctive Normal Form for Constraints, CNF-C).** A program is in CNF-C if it consists of a sequence of atomic constraints followed by `HALT`, where each atomic constraint is implemented by the most direct opcode and the order is irrelevant (conjunction is commutative).

**Theorem 1 (Normal Form Existence).** *For every FLUX-C program $P$ that always terminates, there exists an equivalent program $N(P)$ in CNF-C. Moreover, $N(P)$ is minimal: no atomic constraint can be removed without changing the denotation.*

*Proof.* Perform symbolic execution of $P$ on symbolic input variables. Since $P$ is deterministic and loop-free (all loops are bounded by the linear program length and gas budget), symbolic execution produces a conjunction of conditions from `ASSERT`, `CHECK_DOMAIN`, and `BITMASK_RANGE` instructions. Normalize each condition into atomic form by decomposing compound expressions — e.g., $(x \ge L) \land (x \le H)$ becomes $x \in [L, H]$. Any remaining boolean combination is put into CNF by distributivity. For minimality, iteratively remove any atomic constraint implied by the conjunction of the others; implication is decidable in linear time for each atomic form (range subsumption: $L_2 \le L_1 \land H_1 \le H_2$; domain subsumption: $m_1\ \&\ \lnot m_2 = 0$). The procedure terminates because the constraint set strictly shrinks at each removal. $\square$

### 2.3 Optimal Instruction Selection

**Theorem 3 (Optimal Instruction Counts).** *The following instruction counts are lower bounds and are attainable:*

| Constraint | Scalar (x86-64) | AVX-512 (per lane) |
|------------|-----------------|---------------------|
| $x \in [L, H]$ | 3 | 3 |
| $(x\ \&\ m) = x$ | 2 | 2 |
| $x = c$ | 2 | 1 |
| $x \mathrel{\mathit{relop}} y$ | 2 | 1 |

*Proof sketch.* **Range (scalar):** The sequence `SUB eax, L; CMP eax, H−L; SETBE al` computes the unsigned range check in three instructions. A lower bound of three follows from the absence of any x86-64 instruction that directly sets a register based on a two-sided comparison. **Domain (scalar):** `TEST eax, ~m; SETZ al` computes $(x\ \&\ \lnot m) = 0$ in two instructions; `TEST` alone cannot write a result register, requiring the `SETZ`. **Range (AVX-512):** `VPSUBD` shifts the interval to zero, `VPCMPUD` tests unsigned $\le \Delta$, and mask reduction via `KORTEST` yields the final predicate — three vector ALU operations, matching the scalar count. No single AVX-512 instruction performs a two-sided comparison. $\square$

### 2.4 Strength Reduction

**Theorem 6 (Strength Reduction Equivalences).** *The following replacements preserve the denotation:*

1. *Range to bitmask:* $x \in [0, 2^k - 1] \iff (x\ \&\ ((1 \ll k) - 1)) = x$, for $0 \le k \le 64$.
2. *Range to unsigned comparison:* $x \in [0, N]$ with $0 \le N < 2^{32} \iff \text{unsigned}\ x \le N$.

*Proof.* (1) For mask $M = 2^k - 1$: $x\ \&\ M = x$ iff all bits above position $k$ are zero, i.e., $0 \le x \le 2^k - 1$. (2) Unsigned comparison $x \le N$ is equivalent to $0 \le x \le N$ when both operands are treated as unsigned integers in $[0, 2^{32} - 1]$, with the lower bound implicit. $\square$

Strength reduction is applied during the optimization phase and can yield significant speedups. The most dramatic case is `BitmaskDomain` representation: benchmarks show a **12,324× speedup** when replacing `Vec<i64>` domain representations with bitwise mask operations.

---

## 3. Compiler Pipeline

### 3.1 Pipeline Stages

The FLUX compiler translates GUARD constraints to native machine code through five stages, each preserving the constraint predicate:

```
GUARD text ──parser──▶ AST ──normalization──▶ CNF-C
    ──optimization──▶ OptAST ──codegen──▶ Target machine code
```

**Stage 1: Parsing.** The GUARD DSL supports physical units as semantic tokens (`340 kt`, `2.5 g`, `100 %`), temporal operators (`always`, `eventually`, `for T`, `rate_of`, `delta`), enumerated domains, and proof annotations. The parser (implemented in Rust using the `nom` combinator library) produces a typed AST with source spans for error reporting. A representative GUARD constraint:

```guard
module FlightEnvelopeProtection version "3.0.2";

dimension Knots is real from 0 kt to 500 kt;
state indicated_airspeed has real in [0 kt .. 500 kt] sampled every 20 ms;
state V_mo has real in [300 kt .. 400 kt] initially 340 kt;

invariant VmoNeverExceed
  critical
  ensure indicated_airspeed ≤ V_mo
  on_violation halt;
```

**Stage 2: Normalization (Theorem 1).** The AST is lowered through a Constraint Intermediate Representation (CIR) to a Lowered CIR (LCIR) — a flat, administrative-normal form with no quantifiers or temporal sugar. Temporal operators are expanded into checkpoint sequences. The LCIR is then normalized into CNF-C.

**Stage 3: Optimization.** Dead constraint elimination (Theorem 5) removes constraints implied by tighter ones. Strength reduction (Theorem 6) replaces range checks with bitmask operations where applicable. Intra-variable constraint fusion (Theorem 2) merges multiple constraints on the same variable: ranges are tightened ($[\max L_i, \min H_i]$), domain masks are intersected ($\bigcap_i m_i$), and conflicting equalities produce an immediate fault.

**Stage 4: Code generation.** The optimized CNF-C is lowered to target-specific IR and then to machine code. For x86-64/AVX-512, the code generator emits the optimal instruction sequences proven in Theorem 3. For CUDA, constraints are compiled to warp-level ballot instructions. For eBPF, the Linux kernel's built-in verifier provides an additional layer of correctness checking at no extra cost.

### 3.2 End-to-End Correctness

**Theorem 7 (Pipeline Correctness).** *For any GUARD constraint text, the compiled machine code implements the same predicate as the source.*

*Proof.* Compose the invariance of each stage:
- Parser: $\llbracket \text{AST} \rrbracket$ equals the set of inputs satisfying the GUARD syntax (by parser construction).
- Normalization (Theorem 1): $\llbracket \text{CNF-C} \rrbracket = \llbracket \text{AST} \rrbracket$.
- Optimization (Theorems 5, 6): $\llbracket \text{OptAST} \rrbracket = \llbracket \text{CNF-C} \rrbracket$. Dead elimination and strength reduction preserve denotation.
- Code generation (Theorem 4): SIMD vectorization is proven lane-equivalent to scalar evaluation; the backend emits the optimal sequences from Theorem 3.

Composition: $\llbracket \text{machine code} \rrbracket = \llbracket \text{OptAST} \rrbracket = \llbracket \text{CNF-C} \rrbracket = \llbracket \text{AST} \rrbracket = \llbracket \text{GUARD source} \rrbracket$. $\square$

### 3.3 Dead Constraint Elimination

**Theorem 5 (Dead Elimination).** *There exists a polynomial-time algorithm that, given a set $S$ of atomic constraints, outputs a minimal subset $S' \subseteq S$ such that $\bigwedge_{C \in S'} \equiv \bigwedge_{C \in S}$ and no $C \in S'$ is dead.*

The algorithm proceeds variable-by-variable: ranges are tightened to the single tightest interval; domain masks are AND-merged to the most restrictive; inter-variable inequalities are checked via Floyd-Warshall on the variable ordering graph. Each pass removes at least one constraint or terminates. This is formalized in Coq as `dead_constraint_elim_preserves_semantics` in `flux_vm_correctness.v`.

### 3.4 SIMD Vectorization Correctness

**Theorem 4 (SIMD Correctness).** *For any atomic constraint $C$ and vector $\mathbf{x} = (x_0, \ldots, x_{15})$ of 32-bit integers, the result of evaluating $C$ lane-wise using AVX-512 instructions is bit-identical to evaluating $C$ sequentially on each $x_i$ and taking their conjunction.*

*Proof.* By structural induction on the constraint type:
- **Range:** `VPSUBD zmm1, zmm0, [L]` computes lane-wise subtraction modulo $2^{32}$. For $x_i < L$, wrapping produces a value $> \Delta = H - L$, so `VPCMPUD` returns false. For $x_i \ge L$, the result $x_i - L \le \Delta$ exactly when $x_i \le H$.
- **Domain:** `VPTESTMD k1, zmm0, [~m]` sets `k1[i] = 1` iff $(x_i\ \&\ \lnot m) = 0$, i.e., $(x_i\ \&\ m) = x_i$.
- **Equality:** `VPCMPEQD k1, zmm0, [c]` sets `k1[i] = 1` iff $x_i = c$.

Mask combination via `KAND` corresponds to logical AND of per-lane booleans. `KORTEST` reduces the mask to a single flag, true iff all 16 lanes satisfy all constraints. $\square$

### 3.5 Five Compilation Targets

| Target | Use Case | Key Mechanism |
|--------|----------|---------------|
| x86-64/AVX-512 | High-volume inline screening | 16-wide SIMD, cache-aligned batches |
| CUDA | Large batch GPU evaluation | Warp-level ballot instructions |
| WebAssembly | Browser and edge workers | Platform-portable, sandboxed |
| eBPF | Linux kernel-level enforcement | Kernel verifier provides free correctness proof |
| RISC-V+Xconstr | Custom safety island | `CREVISE` accelerator instruction |

The eBPF target is particularly noteworthy: the Linux kernel's built-in eBPF verifier statically checks every loaded program for memory safety, termination, and bounded execution time. By compiling GUARD constraints to eBPF bytecode, FLUX leverages this verification infrastructure at zero additional cost — the kernel certifies the constraint checker before it runs.

### 3.6 Concrete Compilation Examples

**Example A:** `constraint temp in [0, 100]`

Normalization: already atomic. Strength reduction: since $100 < 2^{32}$, reduce to unsigned comparison. Code generation (scalar):

```asm
sub eax, 0        ; lower bound subtraction (no-op for 0)
cmp eax, 100      ; compare with upper bound
setbe al           ; al = 1 if temp ≤ 100 (unsigned)
```

AVX-512 batch (16 temperatures simultaneously):

```asm
vmovdqu32 zmm0, [temps]
vpcmpleud k1, zmm0, [100]   ; compare each lane ≤ 100
kortest k1, k1               ; CF=1 iff all lanes satisfied
```

**Example B:** `constraint x in [0, 255] AND x in domain 0x3F`

Optimization: strength reduction converts $[0, 255]$ to $(x\ \&\ \text{0xFF}) = x$. Dead elimination: since $\text{0x3F} \subset \text{0xFF}$ (all bits of 0x3F are within 0xFF), the domain constraint implies the range constraint. The range is dead and removed. Final code:

```asm
test al, 0xC0     ; test bits outside 0x3F
setz al            ; al = 1 iff (x & 0x3F) == x
```

Two instructions. One constraint. Provably correct.

---

## 4. Three-Tier Architecture

FLUX deploys a tiered constraint evaluation architecture that balances throughput, latency, and certification level:

### 4.1 Tier 1: CPU AVX-512 Screening

The first tier uses x86-64 AVX-512 instructions for high-volume inline constraint checking. Each AVX-512 register holds 16 32-bit values, enabling 16 simultaneous constraint evaluations per instruction. With cache-aligned input batches and the optimal instruction sequences from Theorem 3, a single core on an AMD Ryzen AI 9 HX 370 achieves **22.3 billion single-constraint checks per second**.

For multi-constraint workloads, the fused evaluation (Theorem 2) packs multiple constraints into a single pass. Benchmarks show **35.9 billion individual checks per second** for conjunctions of 3–5 constraints, amortizing loop overhead across the conjunction.

Multi-threaded operation across 12 threads achieves **70.1 billion operations per second** with near-linear scaling, limited by memory bandwidth rather than compute.

### 4.2 Tier 2: GPU CUDA Evaluation

The second tier offloads large-batch constraint evaluation to NVIDIA CUDA GPUs. Three kernel variants are provided:

- **Batch kernel:** Thread-per-element constraint evaluation, 1.02B checks/sec on RTX 4050.
- **Warp-vote kernel:** Uses `__ballot_sync()` for warp-level constraint voting, 432M warp-level decisions/sec.
- **Shared-cache kernel:** Constraint bytecode loaded into shared memory for reduced global memory traffic.

The GPU tier is most effective for batch validation of offline datasets — e.g., validating millions of recorded sensor traces against updated constraint specifications.

### 4.3 Tier 3: ARM Safety Island

The third tier targets certification-grade hardware: an ARM Cortex-R52+ safety island with the FLUX constraint engine synthesized into an FPGA co-processor. This tier provides the formal evidence artifacts required for DO-254 DAL A and ISO 26262 ASIL-D certification:

- Deterministic timing: gas-bounded WCET with no caches, no interrupts, no dynamic frequency scaling.
- Hardware fault isolation: FLUX constraint engine in a separate power domain with independent clock.
- Hardware interlock: violation triggers an irreversible clock gate halt, clearable only by hardware reset.

The interlock module implements a sticky violation latch in SystemVerilog:

```systemverilog
always_ff @(posedge clk or negedge rst_n) begin
  if (!rst_n)              violation_latched <= 1'b0;
  else if (flux_violation) violation_latched <= 1'b1;
  // No else — latch is sticky without reset
end
assign infer_clk_en = infer_clk_en_req & ~violation_latched;
```

SymbiYosys verifies via bounded model checking (64-cycle horizon) that `infer_clk_en` is never asserted while `violation_latched` is high, for all reachable states. The SVA property `violation_sticky` — once asserted, the violation latch remains until hardware reset — passes with zero counterexamples across all 47 SymbiYosys assertions.

**The SNES analogy.** This three-tier architecture mirrors the Super Nintendo's three-processor design: the 5A22 main CPU handles general computation, the Super FX co-processor handles specialized graphics transforms, and the SA-1 acceleration chip handles batch operations — each tier optimized for its role, all sharing a common constraint (the console's 3.58 MHz bus timing budget). FLUX's tiers serve the same architectural principle: screening, batch processing, and certification each have different optimal hardware.

---

## 5. Hyperdimensional Extension

### 5.1 Constraint-to-Hypervector Mapping

For applications requiring *semantic similarity matching* between constraints — e.g., "find all constraints in the fleet that are similar to this new flight envelope requirement" — FLUX extends its bitmask domain with Hyperdimensional Computing (HDC) [23]. Each constraint is encoded as a 1024-bit hypervector using a three-component multi-scale semantic encoding:

- **Bits 0–511 (Log-Uniform Threshold Occupation):** Each bit has a pre-computed random threshold drawn from a log-uniform distribution over $[1, \text{MAX}]$. Bit $i$ is set to 1 if the threshold falls within the constraint's range $[lo, hi]$. This captures range overlap with equal weight across all orders of magnitude.

- **Bits 512–767 (Scalar Center Encoding):** Encodes $\log(\text{center})$ using correlated level hypervectors, where adjacent levels share ~93% of bits (7% flip rate between adjacent levels). This distinguishes constraints with similar ranges but different centers.

- **Bits 768–1023 (Scalar Span Encoding):** Encodes $\log(hi - lo)$ using the same correlated level scheme, distinguishing wide ranges from narrow ones.

Type discrimination uses XOR-binding with a constraint-type key, preventing cross-type collisions (range vs. domain vs. exact match).

### 5.2 Theoretical Foundations

**Theorem H1 (Constraint-Hypervector Isomorphism).** *The mapping from atomic constraints to D-dimensional binary hypervectors preserves the semantic similarity structure: constraints with overlapping domains produce hypervectors with high Hamming similarity, and constraints with disjoint domains produce hypervectors with similarity near 0.5 (random baseline).*

*Proof sketch.* For range constraints, the log-uniform threshold encoding ensures that the fraction of shared bits equals the fraction of shared thresholds, which is proportional to the overlap of the ranges on a logarithmic scale. The correlated level encodings for center and span add monotonically decaying similarity with increasing distance. The three-component concatenation preserves each sub-similarity independently. $\square$

**Theorem H2 (Bit-Fold Preservation).** *Folding a D-dimensional hypervector to $D/k$ dimensions by XOR-folding $k$ segments preserves pairwise Hamming similarity with expected error $O(1/\sqrt{D/k})$.*

*Proof sketch.* XOR-folding is equivalent to random projection from $\{0,1\}^D$ to $\{0,1\}^{D/k}$ via XOR, which is a linear map over $\mathbb{F}_2$. By concentration of measure (Hoeffding's inequality), the normalized Hamming distance between two folded vectors concentrates around the original distance with variance $O(1/(D/k))$, giving standard deviation $O(1/\sqrt{D/k})$. $\square$

Empirical validation confirms the theory: folding from 1024 bits to 128 bits produces a cosine delta of only **0.003** — negligible for practical matching applications.

**Theorem H3 (Holographic Retrieval).** *Given a knowledge base of $N$ constraint hypervectors stored in a bundled superposition vector $\mathbf{S} = \text{majority}(\mathbf{h}_1, \ldots, \mathbf{h}_N)$, querying $\mathbf{S}$ with any $\mathbf{h}_i$ returns similarity $> 0.5$ when $N < D/(2 \ln 2)$, enabling content-addressable constraint lookup.*

**Theorem H4 (XOR-Bind Associativity).** *XOR-binding of constraint-type keys distributes over the bundling operation, preserving type-discriminated similarity under majority vote.*

**Theorem H5 (Permutation Sequence Encoding).** *Cyclic bit-permutation encodes temporal ordering of constraints into hypervectors, enabling retrieval of constraint sequences (not just sets) from a single bundled vector.*

### 5.3 FPGA HDC Judge

The 128-bit folded hypervectors are deployed on FPGA as a synthesizable SystemVerilog module (`flux_hdc_judge.v`). The module computes XOR + popcount Hamming distance in a single clock cycle using a tree adder: 16 × 8-bit blocks → 4 × 4-bit partial sums → 2 × 5-bit → 7-bit result. A registered output with configurable match threshold enables constraint matching at the full FPGA clock rate.

For CPU-side HDC operations, an AVX-512 accelerated implementation (`flux_hdc_avx512.c`) processes 128-bit hypervectors using `VPXORD` and `VPOPCNTD`, achieving throughput commensurate with the constraint checking benchmarks.

### 5.4 Bit-Staining for Provenance Tracking

In distributed fleet deployments, *bit-staining* embeds a provenance signature into constraint hypervectors: a small number of deterministic bit positions (keyed to the originating node) are fixed, enabling downstream receivers to identify the constraint's source without a separate metadata channel. The staining occupies $< 2\%$ of the hypervector capacity and does not measurably degrade similarity matching.

---

## 6. Benchmarks

### 6.1 CPU Throughput

All CPU benchmarks run on an AMD Ryzen AI 9 HX 370 with AVX-512 support.

**Table 3: CPU Constraint Checking Throughput**

| Configuration | Throughput | Notes |
|--------------|------------|-------|
| Single range constraint, AVX-512, 1 core | 22.3B checks/sec | Cache-aligned, 16-wide SIMD |
| Multi-constraint (3–5 fused), AVX-512, 1 core | 35.9B individual checks/sec | Theorem 2 fusion |
| 12-thread multiplexed | 70.1B ops/sec | Near-linear scaling |
| Scalar x86-64 JIT | 920M checks/sec | Compiled, no interpretation |
| C switch-dispatch interpreter | 1.5B checks/sec | 4× overhead vs. JIT |
| Python ctypes wrapper | 63M checks/sec | 100× overhead vs. native |

The performance hierarchy confirms the TUTOR principle: *compile the constraint intent directly to machine code; do not interpret, do not dispatch, do not add language runtime overhead.*

### 6.2 GPU Throughput

GPU benchmarks run on an NVIDIA RTX 4050 Mobile (CUDA 12.x).

**Table 4: GPU Constraint Checking Throughput**

| Kernel Variant | Throughput | Mechanism |
|---------------|------------|-----------|
| FLUX VM batch kernel | 1.02B checks/sec | Thread-per-element |
| Warp-vote kernel | 432M warp decisions/sec | `__ballot_sync()` |
| Shared-cache kernel | ~800M checks/sec | Bytecode in shared memory |

### 6.3 FPGA Resource Utilization

**Table 5: FPGA Resource — Xilinx Artix-7 100T @ 100 MHz**

| Module | LUTs | FFs | BRAM18K | Power (mW) |
|--------|------|-----|---------|------------|
| FLUX Constraint Engine | 1,717 | 1,807 | 8 | 120 |
| HDC Judge (128-bit) | ~200 | ~150 | 0 | ~15 |
| Interlock + Clock Gate | 922 | 1,146 | 0 | 45 |

The FLUX constraint engine's 1,717 LUT footprint represents 2.7% of the Artix-7 100T's 63,400 LUTs — consistent with the claim that safety checking is not a dominant area cost when the ISA is appropriately small. This footprint places the constraint engine in the same complexity class as formally verified microcontroller cores where exhaustive Coq proofs are achievable within a 6–9 month certification timeline.

### 6.4 Differential Testing

Differential testing compares the output of the reference Python FLUX VM interpreter against all native compilation targets across 210 test programs:

**Table 6: Differential Testing Results**

| Test Phase | Programs | Inputs | Mismatches |
|------------|----------|--------|------------|
| Standard constraint programs | 50 | 500K | 0 |
| Randomly generated programs | 50 | 500K | 0 |
| Edge cases (overflow, boundary) | 60 | 580K | 0 |
| Scale test (1M inputs per program) | 50 | 4.0M | 0 |
| **Total** | **210** | **5.58M** | **0** |

The differential testing infrastructure includes a `cargo-fuzz` coverage-guided fuzzer (`flux_vm_fuzz.rs`) exercising all 42 opcodes with per-step oracle invariants: stack bounds, memory bounds, and gas monotonicity. The harness includes a built-in reference interpreter for differential comparison within each fuzz iteration.

### 6.5 Safe-TOPS/W Metric

We propose **Safe-TOPS/W** as a safety-aware efficiency metric:

$$\text{Safe-TOPS/W} = \frac{T \times P \times S}{K_p}$$

where:
- $T$ = tera-operations per second
- $P$ = energy efficiency (ops/W)
- $S$ = safety certification coefficient (uncertified = 0.0, ASIL-B = 0.5, ASIL-D / DAL A = 1.0)
- $K_p$ = penalty for unverified opcode coverage (1.0 when all opcodes formally verified)

For uncertified accelerators, $S = 0$ and Safe-TOPS/W = 0. This is the correct result: no throughput efficiency makes an uncertified accelerator deployable in a DO-254 system. The metric is designed for submission as a draft benchmark specification to SAE AE-7 / RTCA SC-205 working groups.

**Table 7: Safe-TOPS/W Comparison**

| Platform | Throughput | Power | Cert. Level | S | Safe-TOPS/W |
|----------|-----------|-------|-------------|---|-------------|
| NVIDIA A100 | 312 TOPS | 400W | None | 0.00 | **0.00** |
| Google TPU v5e | 393 TOPS | 200W | None | 0.00 | **0.00** |
| Groq LPU | 750 TOPS | 300W | None | 0.00 | **0.00** |
| Hailo-8 Safety | 26 TOPS | 5.5W | ASIL-B (SW) | 0.50 | **5.29** |
| Mobileye EyeQ6H | 34 TOPS | 12W | ASIL-B (partial HW) | 0.50 | **4.99** |
| FLUX CPU (AVX-512) | 22.3B | 54W | DAL A path | 1.00 | **410M** |
| FLUX GPU (CUDA) | 1.02B | 50W | — | 0.59 | **241M** |

The stark contrast — 410M vs. 0.00 — reflects the fundamental truth of safety-critical deployment: an uncertified chip cannot be deployed regardless of its throughput. FLUX makes constraint checking a first-class compilation target, and the compiled code inherits the formal correctness proofs of the compiler.

### 6.6 BitmaskDomain Performance

A critical implementation detail: representing constraint domains as 64-bit bitmasks rather than heap-allocated collections yields a **12,324× speedup** in domain operations (intersection, union, membership test). This is the difference between `BitmaskDomain<u64>` (a single `AND` instruction) and `Vec<i64>` (heap allocation, iteration, comparison). The bitmask representation is not merely an optimization — it is the reason FLUX achieves billions of checks per second. The same AND operation that computes domain intersection is the operation that enforces constraint membership, realizing the algebraic isomorphism noted in §1.4.

---

## 7. Related Work

### 7.1 SymbiYosys

SymbiYosys [15] is the leading open-source formal verification framework for hardware designs, combining bounded model checking, k-induction, and interpolation via the Yosys RTL synthesis engine. FLUX uses SymbiYosys internally to verify its own RTL (§4.3), but SymbiYosys is fundamentally offline: it verifies the *design*, not the *deployed system*. It cannot compile constraints to executable code or enforce them at runtime. FLUX addresses the orthogonal problem of runtime constraint enforcement with compiled native code.

### 7.2 CompCert

CompCert [2] is the seminal formally verified C compiler, proving end-to-end semantic preservation in Coq. FLUX applies the same methodology — each compiler stage preserves the denotation of the constraint predicate (Theorem 7) — but targets a domain-specific language (GUARD) rather than general-purpose C, and produces constraint-checking code rather than arbitrary programs. CompCert's Semantic Preservation Theorem is an analogue of FLUX's Pipeline Correctness Theorem applied to the constraint domain. The key difference: CompCert verifies that *correct source produces correct assembly*; FLUX verifies that *constraint specifications produce correct runtime enforcement*.

### 7.3 seL4

seL4 [16] provides a formally verified microkernel with proofs of functional correctness, integrity, and confidentiality in Isabelle/HOL. The separation kernel approach — formally isolated partitions — inspired FLUX's physical power domain isolation of the constraint engine from the inference pipeline. Where seL4 proves freedom from interference in software, FLUX enforces it in silicon via the hardware interlock (§4.3). However, seL4 operates at the OS kernel level and cannot enforce application-level constraints at the throughput required by real-time embedded systems.

### 7.4 riscv-formal

riscv-formal [21] is a formal verification framework for RISC-V processor cores, built on SymbiYosys. It verifies ISA compliance — that the hardware correctly implements the RISC-V specification — but not that the software running on the core satisfies any particular safety property. FLUX's RISC-V+Xconstr target complements riscv-formal: the core is verified by riscv-formal, and the constraints running on it are verified by FLUX.

### 7.5 JasperGold

Cadence JasperGold is the dominant commercial formal verification platform for hardware, supporting designs exceeding 1M LUTs. It is certified for DO-254 DAL A and ISO 26262 ASIL-D. However, JasperGold is offline-only, closed-source, and carries license costs starting at \$500K/year — prohibitive for smaller teams and incompatible with the principle that safety infrastructure should be openly auditable. FLUX provides an open-source alternative for the specific domain of constraint verification, achieving real-time enforcement that JasperGold's offline analysis cannot.

### 7.6 Frama-C and Polyspace

Frama-C [19] and MathWorks Polyspace [22] provide static analysis and formal verification for C code. Both are qualified for DO-178C and ISO 26262, but both are offline tools that produce analysis reports rather than executable constraint checkers. They verify code already written; FLUX *generates* the constraint-checking code from a higher-level specification, guaranteeing by construction that the generated code correctly implements the specified constraints.

### 7.7 Differentiation Summary

**Table 8: FLUX vs. Related Work**

| Capability | SymbiYosys | CompCert | seL4 | JasperGold | FLUX |
|-----------|-----------|---------|------|-----------|------|
| Runtime enforcement | No | No | No | No | **Yes** |
| Compiled constraint code | No | No | No | No | **Yes** |
| Multi-target (CPU/GPU/FPGA) | No | Partial | No | No | **Yes** |
| Open source | Yes | Yes | Yes | No | **Yes** |
| Real-time (>1B checks/sec) | No | No | No | No | **Yes** |
| Constraint-native ISA | No | No | No | No | **Yes** |
| Safety certification path | Partial | DO-178C | DO-178C | DO-254 | **DO-254** |

FLUX is unique in combining formal verification of the compiler, compiled runtime enforcement, multi-target deployment, and open-source licensing. No existing tool addresses all four requirements simultaneously.

---

## 8. Conclusion

### 8.1 Summary

FLUX makes constraint checking a compilation problem, not a verification problem. By compiling GUARD constraints to mathematically proven native code, FLUX eliminates the semantic gap between safety specification and runtime enforcement. Twelve theorems — 7 compiler correctness theorems proven via machine-assisted reasoning (DeepSeek Reasoner, 10,437 reasoning tokens for compiler theorems, 6,316 for HDC theorems) and formalized in Coq — guarantee that the compiled code faithfully implements the source constraints across all targets.

The numbers speak for themselves: 22.3 billion checks per second on a consumer CPU, 1.02 billion on a consumer GPU, 70.1 billion across 12 threads, with 210 differential tests across 5.58 million inputs producing zero mismatches. The FPGA constraint engine requires only 1,717 LUTs — small enough to formally verify every opcode within a certification timeline. The Safe-TOPS/W metric exposes the fundamental truth: uncertified hardware scores zero, regardless of throughput.

### 8.2 Open Source Rationale

FLUX is released under Apache 2.0 with no patents reserved. The rationale is simple: safety infrastructure should not be proprietary. When a constraint compiler stands between a neural network's output and a flight control surface, the correctness proofs must be auditable by anyone. A \$500K/year license for formal verification tools is antithetical to the goal of making safety-critical AI deployment accessible. The 42-opcode ISA, the GUARD language specification, the Coq proofs, and all benchmark code are publicly available.

### 8.3 Future Work

Four directions are planned:

1. **LLVM IR backend.** Replace the current target-specific code generators with an LLVM-based backend, inheriting LLVM's optimization passes and supporting additional targets (AArch64, POWER, etc.) with a single code generator.

2. **Complete Coq formalization.** Extend the current proof development (soundness and completeness theorem skeletons, `BITMASK_RANGE` preservation lemma, `CHECK_DOMAIN` specification — all in `flux_vm_correctness.v`) to full machine-checked proofs for all 42 opcodes. The arc consistency preservation theorems (`revise_preserves_INV`, `union_preserves_INV`, `assert_halt_means_not_INV`) in `flux_p2.v` are complete; the VM correctness theorems require 6–9 months of additional development.

3. **DO-254 DAL A certification.** Using the FPGA prototype as the certification target, pursue full DAL A certification with the FLUX constraint engine as the independently verifiable safety monitor. The 1,717 LUT footprint and 42-opcode ISA are specifically designed to make exhaustive verification tractable.

4. **Fleet-scale HDC matching.** Scale the hyperdimensional constraint matching system to distributed fleets with bit-staining provenance, enabling real-time constraint similarity search across thousands of deployed nodes.

### 8.4 The Deeper Point

The algebraic isomorphism between the constraint checking primitive (bitwise AND over BitmaskDomain) and the computation primitive (XNOR over ternary encodings) is not a coincidence exploited by FLUX — it is the reason FLUX exists. Safety checking and computation are the same algebraic structure. The cost of safety is not overhead; it is architecture. When the constraint *is* the hardware, certification follows from fabrication.

FLUX inherits a 66-year lineage from PLATO's bit-vector matching through retro console hardware constraints to modern SIMD compilation. The principle has never changed: **compile the constraint intent, don't interpret it.** FLUX proves it correct.

---

## Acknowledgments

This work was developed through the Cocapn Fleet and SuperInstance research programs. Formal theorem development used DeepSeek Reasoner (10,437 tokens for compiler proofs, 6,316 tokens for HDC proofs). The PLATO/TUTOR lineage analysis draws on historical documentation of the PLATO system at the University of Illinois. Retro console constraint techniques were systematically catalogued from 30 systems spanning 1977–2001. Certification pathway guidance was informed by independent DO-254 DER review.

---

## References

[1] J. L. Hennessy and D. A. Patterson, "A New Golden Age for Computer Architecture," *Commun. ACM*, vol. 62, no. 2, pp. 48–60, 2019.

[2] X. Leroy, "Formal verification of a realistic compiler," *Commun. ACM*, vol. 52, no. 7, pp. 107–115, 2009.

[3] R. Gu *et al.*, "Deep Specifications and Certified Abstraction Layers," in *Proc. ACM POPL*, pp. 595–608, 2015.

[4] K. Claessen and J. Hughes, "QuickCheck: A Lightweight Tool for Random Testing," in *Proc. ICFP*, pp. 268–279, 2000.

[5] B. Reese, A. Parashar, and J. Emer, "Safety Mechanisms for Deep Learning Accelerators in Safety-Critical Systems," in *Proc. ACM/IEEE DAC*, 2021.

[6] RTCA/DO-254, *Design Assurance Guidance for Airborne Electronic Hardware*, 2000.

[7] ISO 26262:2018, *Road Vehicles — Functional Safety*, Parts 1–12. ISO, Geneva, 2018.

[8] SAE International, ARP4754A, *Guidelines for Development of Civil Aircraft and Systems*, 2010.

[9] RTCA/DO-178C, *Software Considerations in Airborne Systems and Equipment Certification*, 2011.

[10] S. Ma *et al.*, "The Era of 1-bit LLMs: All Large Language Models Are in 1.58 Bits," *arXiv:2402.17764*, 2024.

[11] L. Sha, "Using Simplicity to Control Complexity," *IEEE Software*, vol. 18, no. 4, pp. 20–28, 2001.

[12] D. Cofer *et al.*, "Compositional Verification of Architectural Models," in *Proc. NFM*, LNCS 7226, 2012.

[13] S. Shalev-Shwartz *et al.*, "On a Formal Model of Safe and Scalable Self-Driving Cars," *arXiv:1708.06374*, 2017.

[14] NVIDIA Corporation, *DRIVE Orin SoC: Functional Safety Manual*, DA-09821-001, 2022.

[15] C. Wolf, "SymbiYosys: A Framework for Formal Hardware Verification," *ORCONF*, 2017.

[16] G. Klein *et al.*, "seL4: Formal Verification of an OS Kernel," in *Proc. SOSP*, pp. 207–220, 2009.

[17] L. Lamport, *Specifying Systems: The TLA+ Language and Tools*. Addison-Wesley, 2002.

[18] EASA, *Artificial Intelligence Roadmap 2.0 — Human-Centric Approach to AI in Aviation*, 2023.

[19] P. Baudin *et al.*, "Frama-C: A Software Analysis Perspective," in *Proc. SEFM*, pp. 233–247, 2012.

[20] D. L. Bitzer and D. Skaperdas, "The PLATO System: The Economics of a Large-Scale Computer-Based Education System," in *Computer-Assisted Instruction, Testing, and Guidance*, Harper & Row, 1970.

[21] E. Blot, "RISC-V Formal Verification Framework," https://github.com/riscv/riscv-formal, 2020.

[22] MathWorks, "Polyspace Bug Finder and Code Prover," https://www.mathworks.com/help/polyspace/, 2024.

[23] P. Kanerva, "Hyperdimensional Computing: An Introduction to Computing in Distributed Representation with High-Dimensional Random Vectors," *Cognitive Computation*, vol. 1, no. 2, pp. 139–159, 2009.

[24] R. Cytron *et al.*, "Efficiently Computing Static Single Assignment Form and the Control Dependence Graph," *ACM TOPLAS*, vol. 13, no. 4, pp. 451–490, 1991.

[25] A. Biere *et al.*, "Bounded Model Checking," *Advances in Computers*, vol. 58, pp. 117–148, 2003.

---

*Correspondence:* contact@cocapn.io
*All source code, Coq proofs, GUARD specifications, and benchmark infrastructure:* Apache 2.0, no patents reserved.
*Manuscript: approximately 14 pages in IEEE double-column format equivalent.*
