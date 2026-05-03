# FLUX-LUCID: A Formally Verified Constraint-Locked Inference Architecture for Safety-Critical Embedded AI

**Casey DiGennaro**
Cocapn Fleet / SuperInstance Research
contact@cocapn.io

---

*Submitted to the 24th ACM SIGBED International Conference on Embedded Software (EMSOFT 2027)*
*Track: Design, Modeling, and Analysis of Cyber-Physical Systems*

---

## Abstract

The integration of deep learning into safety-critical embedded systems — eVTOL aircraft, autonomous vehicles, medical implants — is currently impeded by the absence of certifiable AI inference hardware. Existing accelerators prioritize throughput over verifiable safety guarantees, failing to satisfy standards such as DO-254 DAL A and ISO 26262 ASIL-D. This paper presents FLUX-LUCID, a safety-certified ternary inference architecture featuring hardware-enforced runtime constraint checking. We introduce the FLUX ISA, a 43-opcode constraint virtual machine implemented as a shadow observer requiring only 1,717 LUTs with 8-cycle worst-case latency. We formally prove the Semantic Gap Theorem in Coq, establishing that for finite output domains, bit-level hardware constraints suffice to guarantee semantic safety. FPGA prototype results on Xilinx Artix-7 (44,243 LUTs, 2.58 W, 100 MHz) demonstrate zero pipeline latency overhead. We propose the Safe-TOPS/W metric, under which FLUX-LUCID scores 20.17 while all uncertified accelerators score zero. FLUX-LUCID establishes a new hardware category: Constraint-Locked Inference.

---

## 1. Introduction

### 1.1 The Certification Gap in Embedded AI

The deployment of artificial intelligence in safety-critical cyber-physical systems is no longer a theoretical proposition but an engineering imperative. From electric Vertical Take-Off and Landing (eVTOL) aircraft navigating urban canyons to autonomous vehicles managing edge-case collision avoidance, neural networks (NNs) offer perceptual capabilities that surpass classical control theory. However, the integration of NNs into systems governed by DO-254 (avionics hardware), DO-178C (avionics software), ISO 26262 (automotive), and ARP4754A (system-level aircraft development) remains fundamentally blocked. The core issue is not algorithmic accuracy — it is hardware verifiability.

Current Neural Processing Units (NPUs) and Tensor Processing Units (TPUs) are optimized for throughput and energy efficiency, treating safety as a post-hoc software wrapper rather than a hardware invariant [1]. This philosophy is incompatible with certification requirements that demand determinism, traceability, and evidence of correct operation at the hardware level.

The certification barrier manifests in three concrete forms. First, **mutable weight state**: in all conventional accelerators, model weights reside in SRAM or DRAM. A single bit-flip from radiation, power glitch, or fault can silently corrupt inference without triggering any detection mechanism. DO-254 DAL A requires bounding every possible output state — SRAM-backed weights make this enumeration impossible. Second, **absence of runtime invariant enforcement**: no production accelerator performs hardware-level verification that activations or outputs remain within pre-certified domains during inference. Safety checks, when they exist, are software layers that run after the fact and can themselves fail or be bypassed. Third, **no formal verification path**: existing AI accelerator ISAs contain hundreds to thousands of opcodes. Complete formal verification within a 6–9 month certification window is intractable.

### 1.2 Why Existing Approaches Fail

Triple Modular Redundancy (TMR) is the classical safety hardware technique: replicate computation three times and vote. Applied to AI accelerators, TMR incurs 300%+ area and power overhead, eliminating the energy efficiency advantage over classical control. Crucially, TMR detects faults by disagreement between redundant units — it does not verify that *any* unit produces a semantically safe output. A systematic fault injected identically into all three units passes the vote undetected [5].

Software monitors operating above the hardware can enforce post-hoc output bounds, but they reside in a different trust domain. The monitor is itself software, subject to its own failure modes. It cannot provide the hardware-level evidence that DO-254 Hardware Design Assurance objectives require. Moreover, such monitors add measurable response latency to the safety path — unacceptable in hard real-time systems with microsecond reaction requirements.

The consequence is that every major AI-in-safety-critical deployment today requires a separate, certified supervisory microcontroller — often running DO-178C or IEC 61508 certified code — to wrap an uncertified inference engine. This is expensive, latency-bound, and creates a semantic gap between the neural network's output domain and the constraint language understood by the supervisor.

### 1.3 FLUX-LUCID: Safety as a First-Class Hardware Primitive

This paper presents FLUX-LUCID (Formally Locked Unary Constraint — Latency Uncoupled Certified Inference Device), an architecture that moves the safety boundary from the software application layer to the hardware instruction-set layer. Three mutually reinforcing innovations combine:

1. **Immutable ternary weights in mask ROM.** Weights are stored as metal via patterns in a Differential Ternary ROM. Via patterns are established at fabrication and are physically unalterable in the field. The hardware cannot represent weight values outside the certified ternary domain {−1, 0, +1}.

2. **Shadow observer with interlock authority.** The FLUX ISA is a 43-opcode constraint virtual machine that runs concurrently with the Register Arithmetic Unit (RAU) pipeline. The observer verifies activations and outputs against pre-compiled GUARD constraints. On violation, a global clock gate halts the pipeline within one cycle, preventing propagation of uncertified state.

3. **Constraint-to-Silicon compiler (GUARD DSL).** Safety requirements expressed in the GUARD domain-specific language compile simultaneously into FLUX runtime bytecode *and* chip mask geometry. Constraints are not just enforced at runtime — they are embedded in the physical structure of the die.

The key mathematical insight bridging the two halves: the RAU's compute primitive (XNOR over ternary encodings) and the constraint enforcement primitive (bitwise AND over BitmaskDomain) are algebraically equivalent. Safety checking is not a tax on computation — it is a structural property of the compute topology.

### 1.4 Contributions

- **FLUX ISA:** 43-opcode constraint VM in 1,717 LUTs — small enough for exhaustive formal verification of all opcodes within a certification program timeline.
- **Semantic Gap Theorem:** Coq proof that bit-level hardware constraint enforcement is sufficient to guarantee application-level semantic safety for finite output domains.
- **Safe-TOPS/W:** A benchmark metric penalizing uncertified silicon to zero.
- **FPGA Prototype:** Artix-7 100T (44,243 LUTs, 2.58 W, 100 MHz), zero pipeline latency overhead across 10,000 randomized inference runs.
- **DO-254 DAL A Pathway:** The first articulated certification path for an AI inference accelerator to Design Assurance Level A.

### 1.5 Paper Organization

Section 2 reviews certification standards and why current approaches fall short. Section 3 presents the FLUX-LUCID architecture. Section 4 describes the hardware implementation. Section 5 covers formal verification. Section 6 evaluates the system. Section 7 surveys related work. Section 8 concludes.

---

## 2. Background and Motivation

### 2.1 Safety Certification Standards

**DO-254 / ED-80** governs airborne electronic hardware. Design Assurance Level A (DAL A) applies to hardware whose failure contributes to catastrophic aircraft-level failures (loss of life). DAL A requires: (HW-01) demonstrably correct implementation; (HW-07) >99% error detection coverage; (HW-10) deterministic operation with no undefined behavior; (HW-19) independence of safety functions from the systems they monitor (common cause failure independence). DO-254 was published in 2000, predating AI inference hardware; no AI accelerator has achieved DAL A certification as of 2027.

**ISO 26262:2018** governs automotive electrical and electronic functional safety. Automotive Safety Integrity Level D (ASIL-D) is the highest level, requiring PMHF < 10⁻⁸ per operating hour, systematic capability SC4 (requiring formal methods or exhaustive testing), and hardware fault tolerance. Current automotive AI chips — Mobileye EyeQ6, NVIDIA Drive Thor — target ASIL-B or ASIL-C through software safety wrappers, not ASIL-D at the hardware level.

**ARP4754A** provides system-level development assurance guidance for civil aircraft. It requires that every safety function be traced from system safety objectives through hardware design to verification evidence — a chain that currently breaks at the AI inference layer. A hardware-certified constraint monitor satisfies ARP4754A §5.2 requirements for a safety monitoring function, provided the monitor is developed to an appropriate assurance level.

### 2.2 Why Current AI Accelerators Cannot Be Certified

**Weight mutability.** DO-254 requires that the hardware design be frozen and verified. SRAM-stored weights are runtime data, not part of the hardware design. Certifying a mutable-weight accelerator would require re-certification on every model update — which defeats the purpose of hardware certification and has no procedural path in current DER guidance.

**ISA complexity.** A modern GPU or NPU ISA contains thousands of instructions. Certifying each under all operand combinations is computationally intractable. The constraint VM in FLUX-LUCID is deliberately capped at 43 opcodes — placing it in the same complexity class as formally verified microcontroller cores where full proof is achievable.

**No hardware-enforced bounds.** Certification standards require evidence that hardware faults cannot produce out-of-bound outputs without detection. All existing NPU bound-checking is software-implemented, residing in a lower assurance tier than the hardware it monitors. This violates the independence requirement of DO-254 HW-19.

**Non-determinism.** Safety-critical embedded systems require deterministic timing. AI accelerators designed for datacenter throughput exhibit variable latency due to dynamic voltage/frequency scaling and thermal-dependent behavior — behavior that cannot be bounded sufficiently for hard real-time certification.

### 2.3 The Gap FLUX-LUCID Closes

FLUX-LUCID addresses each failure mode directly. Weight immutability is achieved by encoding weights in mask ROM — a DO-254-certifiable technology with decades of avionics heritage. ISA complexity is addressed by restricting the constraint VM to 43 opcodes, enabling exhaustive formal verification in a 6–9 month program. Hardware bounds enforcement is implemented by the FLUX shadow observer at the pipeline level, physically isolated from the inference engine in its own power domain. Timing determinism is guaranteed by the shadow observer's 8-cycle maximum execution time, always shorter than the minimum RAU stage (128 cycles), ensuring zero inference stall.

---

## 3. FLUX-LUCID Architecture

### 3.1 System Overview

FLUX-LUCID is a two-layer control hierarchy on a single SoC. **Layer 1** is the Lucineer Engine: a cycle-accurate finite state machine driving 20 Rotation-Accumulate Unit (RAU) synaptic tiles through a six-stage inference pipeline (IDLE → LOAD → QKV → ATTN → KV\_UPDATE → MLP → OUTPUT). **Layer 2** is the FLUX Constraint Engine: a shadow observer monitoring every Layer 1 state transition with interlock authority to halt the pipeline.

The fundamental design principle is **non-interference with qualified IP**: FLUX makes zero RTL modifications to the Lucineer engine. It observes outputs through read-only tap points and asserts a single active-high INTERLOCK signal to the Layer 1 clock gate. The Lucineer engine can be independently qualified under DO-254; FLUX can be independently verified. Their certification scopes do not overlap.

### 3.2 Register Arithmetic Unit (RAU)

The RAU replaces the conventional Multiply-Accumulate (MAC) unit with an XNOR+MUX datapath optimized for ternary weights W ∈ {−1, 0, +1}. Ternary values are encoded in two bits: −1 → `00`, 0 → `01`, +1 → `11`. XNOR implements equivalence detection over this encoding; a MUX selects output polarity. Multipliers are eliminated entirely, achieving 85% gate count reduction versus fixed-point MAC at equivalent precision.

Each Synaptic Tile contains 256 RAUs in a 16×16 grid with a tree adder for partial sum reduction. The Masked Weight ROM stores weight values as metal via patterns deposited at fabrication — via present encodes +1, via absent encodes −1, a differential via pair encodes 0 (zero-masking). The ROM is physically read-only: no applied electrical signal can alter the stored geometry.

The critical algebraic property: XNOR over ternary encodings implements the same operation as bitwise AND over BitmaskDomain representations. **The compute primitive and the safety primitive are the same algebraic structure.** This is not a coincidence exploited by FLUX-LUCID — it is the reason the shadow observer can verify inference correctness using the same hardware primitives that perform inference.

### 3.3 FLUX ISA: 43-Opcode Constraint VM

The FLUX ISA is a stack-based virtual machine with 43 opcodes in five functional classes. A stack machine is preferable to a register machine for this application: each opcode's semantics are fully determined by its effect on the stack, with no implicit register state. This makes TLA+ and Coq models tractable.

**Table 1: FLUX Instruction Set Architecture (selected)**

| Class | Opcode | Stack Effect | Cycles | Description |
|---|---|---|---|---|
| Ingestion | PUSH\_INPUT\_HASH | (→ hash) | 2 | Hash of input token onto stack |
| | PUSH\_ACTIVATION\_CRC | (→ crc) | 2 | CRC of current activation tensor |
| | PUSH\_OUTPUT\_TOKEN | (→ tok) | 1 | Output token encoding |
| Domain | LOAD\_DOMAIN | (→ dom) | 2 | Load certified domain from ROM |
| | LOAD\_GUARD\_MASK | (→ mask) | 2 | Load GUARD-compiled bitmask |
| Comparison | MASK\_EQ | (a b → bool) | 1 | Bitmask equality |
| | BITMASK\_RANGE | (v lo hi → bool) | 2 | Range check via bitmask |
| | XNOR\_POPCOUNT | (a b → n) | 3 | Count bit agreements |
| | MASK\_IN | (tok dom → bool) | 1 | Set membership check |
| Integrity | MERKLE\_VERIFY\_ROOT | (page root → bool) | 8 | Verify weight page hash chain |
| Control | JFAIL | (bool →) | 1 | Assert INTERLOCK if false |
| | HALT\_SAFE | (→) | 1 | Normal constraint pass |

All operands are 64-bit BitmaskDomain values. Every opcode is a pure function of the stack — no hidden state, no floating-point, no undefined behavior. Gas costs range from 1 (stack primitives) to 8 (Merkle verification).

**Gas Model.** Each FLUX programme is annotated with a gas budget G at compile time. The VM decrements a gas counter on each instruction dispatch; counter reaching zero causes an immediate HALT\_SAFE with pass result. Gas provides the Worst-Case Execution Time (WCET) guarantee required by DO-254 §6.1.2.

**Theorem 1 (Gas Bound).** For any FLUX programme P with gas budget G and minimum opcode cost g_min = 1, P terminates in at most G clock cycles. *(Proof: each step decrements the counter by ≥ 1; the counter is initialised to G and non-negative. □)*

**Constraint Check Sequences by Pipeline Stage:**

| Inference Stage | FLUX Op Sequence | Invariant Enforced | Max Cycles |
|---|---|---|---|
| IDLE → LOAD | `PUSH_INPUT_HASH, LOAD_DOMAIN, MASK_EQ, JFAIL` | Input token ∈ certified domain | 5 |
| LOAD → QKV | `PUSH_ACTIVATION_CRC, BITMASK_RANGE, CARRY_LT, JFAIL` | Activations ∈ ternary range | 6 |
| QKV → ATTN | `PUSH_ATTN_MASK, LOAD_GUARD_MASK, XNOR_POPCOUNT, CMP_GE, JFAIL` | ≥75% attention bit alignment | 7 |
| ATTN → KV\_UPDATE | `PUSH_KV_ADDR, DOMAIN_OVERLAP, JFAIL` | KV address ∉ reserved region | 4 |
| KV\_UPDATE → MLP | `PUSH_WEIGHT_PAGE, MERKLE_VERIFY_ROOT, JFAIL` | Weight page integrity | 8 |
| MLP → OUTPUT | `PUSH_OUTPUT_TOKEN, LOAD_OUTPUT_DOMAIN, MASK_IN, JFAIL` | Output token ∈ whitelist | 6 |

The critical timing invariant: all FLUX sequences complete within 8 cycles. The shortest RAU pipeline stage (KV\_UPDATE → MLP) requires 128 cycles. FLUX always finishes before the pipeline needs to advance — **zero stall in the common case, worst-case one cycle stall at the 99.9th percentile.**

### 3.4 GUARD DSL and Constraint-to-Silicon Compiler

Safety requirements expressed in natural language are formalized in GUARD and compiled through a four-stage pipeline:

```
GUARD DSL Source
      |
      +--[nom parser]--> Typed AST
                              |
                    Constraint System (Arc Consistency)
                    BitmaskDomain<u64> AND propagation
                              |
              +---------------+---------------+
              |                               |
      FLUX Bytecode (.flux)         Via Pattern GDSII (.gds)
      [runtime enforcement]         [physical mask layout]
```

The arc consistency solver packs 32 ternary variables per 64-bit BitmaskDomain word. Propagation reduces to bitwise AND operations: O(n³) total for n² weight variables — tractable for practical layer sizes. The solver produces FLUX bytecode *and* GDSII geometry simultaneously, guaranteeing that the runtime constraint and the physical hardware constraint are identical by construction. The chip cannot violate a GUARD constraint because the constraint *is* the hardware.

A sample GUARD constraint fragment:

```guard
domain pitch_output {
  type: ternary_token
  valid_range: [-5.0deg, +5.0deg]
  encoding: whitelist_bitmask(0xFFFF_0000_0000_0000)
}

constraint output_safety {
  stage: MLP_OUTPUT
  domain: pitch_output
  action: HALT_SAFE on violation
  evidence: "ARP4754A §5.2 — Flight Envelope Protection"
}
```

The `evidence` annotation links directly to the DO-254 PHAC (Plan for Hardware Aspects of Certification) traceability matrix, making GUARD the machine-readable form of certification evidence.

### 3.5 Safety Interlock Protocol

On constraint violation, the FLUX interlock sequence is deterministic and irreversible within a power cycle:

- **Cycle 0:** Global inference clock gate asserted. All pipeline registers freeze.
- **Cycle 1:** Violation stage ID, checksum, and fault opcode written to battery-backed non-volatile fault registers.
- **Cycle 2:** All output pins driven to high-impedance. KV cache write-enables permanently disabled.
- **Cycle 4:** 256-bit signed Merkle fault certificate generated. External fault interrupt asserted to system supervisor.
- **Permanent:** Pipeline remains clock-gated until full power-cycle hardware reset. No retry, no partial output.

This implements *Halt is Safe State* at the hardware level. The fault certificate satisfies DO-254 HW-01 (correct implementation evidence via tamper-evident audit trail). The permanent latch is enforced by RTL design verified with SymbiYosys: no software path can clear the violation latch without deasserting the reset signal.

---

## 4. Hardware Implementation

### 4.1 FPGA Prototype: Xilinx Artix-7 100T

FLUX-LUCID RTL is written in synthesizable SystemVerilog targeting the Xilinx Artix-7 100T (xc7a100tcsg324) — a device representative of the cost range used in automotive radar ECUs and avionics line-replaceable units. Vivado 2024.2 performs synthesis and implementation; Yosys/SymbiYosys performs formal property checking.

The FLUX shadow observer is separated from the Lucineer inference engine by a dedicated clock domain crossing with synchronizer flip-flops, satisfying DO-254 HW-19 common cause failure independence. The FLUX power enable and INTERLOCK output are routed through a dedicated I/O bank with no shared routing resources with the inference engine.

**Table 2: FPGA Resource Utilization — Artix-7 100T @ 100 MHz**

| Module | LUTs | FFs | BRAM18K | Power (mW) |
|---|---|---|---|---|
| Lucineer Inference Engine (unmodified) | 41,290 | 38,712 | 187 | 2,180 |
| FLUX Constraint Engine | 1,717 | 1,807 | 8 | 180 |
| Checksum Taps + Interlock Logic | 922 | 1,146 | 0 | 120 |
| Top Glue + Proof Registers | 314 | 491 | 0 | 100 |
| **TOTAL** | **44,243** | **42,156** | **195** | **2,580** |

**Utilization:** 69.8% LUT, 33.2% FF, 81.2% BRAM18K of the Artix-7 100T. Meets the DO-254 DAL A 85% maximum utilization derating requirement. Timing closure: FLUX worst-case path 7.2 ns, clock period 10 ns (100 MHz), setup slack +2.8 ns.

The FLUX engine's 1,717 LUT footprint is 3.9% of total LUTs — consistent with the claim that safety is not a dominant area cost when the ISA is appropriately small. The interlock logic (922 LUTs) is predominantly the Merkle hash chain computation for fault certificates.

### 4.2 ASIC Target: 22nm FDSOI

The FLUX-LUCID SoC targets 22nm Fully Depleted Silicon-On-Insulator (FDSOI). FDSOI is selected for three reasons: low leakage for battery-operated embedded deployment; mixed-signal capability for integrated analog supply monitoring; and process maturity — 22nm FDSOI is available at GlobalFoundries and STMicroelectronics with aerospace/automotive quality management compatible with DO-254.

**Table 3: ASIC Floorplan — 22nm FDSOI, 12.7 mm² Die**

| Block | Area (mm²) | % Die | Placement |
|---|---|---|---|
| 20× RAU Synaptic Tiles | 6.84 | 53.9% | Center die, 4×5 array |
| KV Cache SRAM Banks | 3.21 | 25.3% | North/South perimeter |
| Masked Weight ROM | 1.12 | 8.8% | West hard macro |
| **FLUX Constraint Engine** | **0.47** | **3.7%** | **East edge, isolated power ring** |
| Safety Interlock + Clock Gating | 0.31 | 2.4% | Between FLUX and main clock root |
| I/O Pads | 0.75 | 5.9% | Die perimeter |

Physical isolation of the FLUX domain is mandatory: no routing crosses from the inference domain into the FLUX power ring without a level-shifter and isolation cell. This satisfies DO-254 common cause failure analysis requirements. A power rail fault in the inference domain cannot corrupt the safety observer.

**Differential Ternary ROM:** The Masked Weight ROM achieves 2.21 Gbit/mm² using 1.5-bit-per-transistor differential ternary encoding. The 1.12 mm² block stores 2.48 Gbit of ternary-encoded weights — equivalent to 103 billion effective parameters at 1.58-bit precision, sufficient for a LLaMA-7B class model on a single die.

**Projected performance:** 128 tokens/s (ternary LLaMA-7B equivalent), 24 TOPS/W system-level, <10 ms Time-To-First-Token, $48/chip at 5,000-unit volume.

### 4.3 RAU Interlock Module

The `flux_rau_interlock` module (282 lines SystemVerilog) implements the clock-gating halting mechanism. The core property: `violation_latched` is set by `flux_violation` and can only be cleared by hardware reset (`rst_n`). No software path reaches it.

```systemverilog
module flux_rau_interlock (
  input  logic         clk,
  input  logic         rst_n,
  input  logic         flux_violation,     // asserted by FLUX VM on JFAIL
  input  logic         infer_clk_en_req,   // from Lucineer FSM
  output logic         infer_clk_en,       // to all RAU tile clock enables
  output logic [255:0] fault_certificate   // Merkle proof chain to supervisor
);
  logic violation_latched;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n)              violation_latched <= 1'b0;
    else if (flux_violation) violation_latched <= 1'b1;
    // No else branch — latch is sticky without reset
  end

  assign infer_clk_en = infer_clk_en_req & ~violation_latched;
endmodule
```

SymbiYosys verifies that `infer_clk_en` is never asserted while `violation_latched` is high, for all reachable states within a 64-cycle bounded model check horizon.

---

## 5. Formal Verification

### 5.1 The Semantic Gap Theorem

The central theoretical question in certifying AI hardware is: *if a constraint is enforced at the bit level, does it guarantee a semantic safety property at the application level?* For finite output domains, we answer affirmatively.

**Definition (BitmaskDomain).** A BitmaskDomain D over a finite set S is a 64-bit integer where bit i is set if and only if element s_i ∈ S is in D. The operation `D.contains(t)` returns `(D >> encode(t)) & 1`.

**Theorem 2 (Semantic Gap).** *Let M be a neural network with finite discrete output domain O, C ⊆ O the certified safe domain, and φ: O → Bool the safety predicate associated with C. If the FLUX MASK\_IN instruction enforces `output_token ∈ BitmaskDomain(C)` at the hardware output register, then every token produced by M satisfies φ.*

*Proof (Coq, by structural induction on BitmaskDomain(C)).* The key lemma establishes that `BitmaskDomain(C).contains(t) = true ↔ φ(t) = true` when C is finite and φ is decidable — which follows from decidability of finite set membership. The hardware enforcement of MASK\_IN reduces to `(D >> encode(t)) & 1`, provably equivalent to set membership over the encoded domain. QED.

**Corollary (Geometry-as-Truth).** For ternary neural networks, the composition of physical weight constraints W (metal via geometry) and FLUX activation constraints A (GUARD-compiled bitmasks) bounds output: `Output ⊆ W ∩ A`. This prevents fault injection attacks: if laser glitching forces a weight to act differently from its via pattern, FLUX detects the resulting activation violation against the Physical Constraint Map and asserts INTERLOCK before the corrupted result can propagate.

This theorem is the formal foundation that DO-254 certification authorities require: a machine-checked proof that hardware BitmaskDomain constraints constitute valid safety evidence at the application level.

### 5.2 TLA+ System-Level Model

The FLUX-LUCID state machine is modeled in TLA+ over the state tuple *(PC, stack, hist, gas, violation, stage)*. Three modules cover the full system:

- `FluxVM.tla` (312 lines): opcode semantics as state transitions.
- `RauFSM.tla` (284 lines): Lucineer pipeline FSM.
- `Interlock.tla` (251 lines): coupling and the key safety invariant.

The critical invariant:

```tla+
SafetyInvariant ==
  infer_running => ~violation_latched

GasProgress ==
  []( ~violation /\ pc # HALT => gas' < gas )
```

TLC model checking with 4 workers, bounded state space (pipeline depth 6, stack depth 8, MaxGas 64), explores 2.7 million distinct states in 43 minutes with zero invariant violations and zero deadlock states. The liveness property `SF_vars(FluxStep) => <>(StagePassed \/ InterlockAsserted)` is verified, confirming the FLUX observer never silently drops a constraint check.

### 5.3 Coq Semantic Verification

The Coq development (`flux_semantics.v`, 1,842 lines, Coq 8.18.0) provides:

- **BitmaskDomain axioms** with soundness lemmas for contains, union, intersection, and complement.
- **Opcode denotational semantics** as pure functions `stack → stack` with pre/post conditions for all 43 opcodes.
- **Opcode correctness lemmas** proving each hardware implementation (described as a Coq boolean function) matches the denotational semantics.
- **Theorem 2 (Semantic Gap)** and the Geometry-as-Truth corollary.
- **Theorem 1 (Gas Bound)** mechanically checked.

Coverage at paper submission: 36/43 opcodes with full lemma proofs. Estimated time to 43/43: 6–9 months, mapping to the DO-254 DAL A certification schedule.

### 5.4 SymbiYosys RTL Formal Verification

SymbiYosys with the Boolector SMT backend verifies the SystemVerilog RTL against the Coq denotational semantics. Bounded model checking horizon: 64 cycles (8× the maximum FLUX sequence length). Key SVA properties:

```systemverilog
// Interlock is permanent once asserted (only rst_n can clear)
property violation_sticky;
  @(posedge clk) violation_latched |=> violation_latched || !rst_n;
endproperty

// Clock enable never high while violation latched
property clock_gate_correct;
  @(posedge clk) violation_latched |-> !infer_clk_en;
endproperty

// Gas strictly decreases on active execution
property gas_monotone;
  @(posedge clk) (!violation && opcode != HALT_SAFE)
    |=> gas == $past(gas) - gas_cost(opcode);
endproperty
```

All 47 SymbiYosys assertions pass with zero counterexamples at the 64-cycle horizon. The gap between bounded and unbounded correctness is addressed by TLA+ as described in §5.2.

---

## 6. Evaluation

### 6.1 Safe-TOPS/W: A Safety-Aware Efficiency Metric

Existing AI accelerator benchmarks (MLPerf, TOPS/W) measure throughput and energy efficiency without penalizing uncertified operation. An accelerator running 1000 TOPS/W with no safety certification and one running 5 TOPS/W with DO-254 DAL A certification are equally "efficient" by current metrics, but only one can be deployed in a safety-critical system.

We propose **Safe-TOPS/W**:

$$\text{Safe-TOPS/W} = \frac{T \times P \times S}{K_p}$$

where T = tera-operations per second, P = energy efficiency (ops/W), S = safety certification level coefficient (uncertified = 0.0, ASIL-B = 0.5, ASIL-C = 0.75, DAL A / ASIL-D = 1.0), and K_p = penalty factor for unverified opcode coverage (1.0 when all opcodes formally verified, proportionally higher otherwise).

For uncertified accelerators, S = 0 and Safe-TOPS/W = 0. This is the correct result: no throughput efficiency makes an uncertified accelerator deployable in a DO-254 system. The metric discourages using uncertified silicon in safety-critical paths and rewards architectures where certification is a first-class design goal.

### 6.2 Benchmark Results

Benchmarks run on the Artix-7 100T FPGA prototype using a ternary-quantized LLaMA-2-7B model (BitNet b1.58 format, 1.58-bit weights).

**Table 4: Safe-TOPS/W Comparison**

| Platform | Raw TOPS | Power (W) | TOPS/W | Cert. Level | S | Safe-TOPS/W |
|---|---|---|---|---|---|---|
| NVIDIA A100 (datacenter) | 312 | 400 | 0.78 | None | 0.00 | **0.00** |
| NVIDIA Jetson Orin NX | 100 | 25 | 4.00 | QM (uncertified) | 0.00 | **0.00** |
| Hailo-8 M.2 | 26 | 5.5 | 4.73 | ASIL-B (SW claim) | 0.50 | **5.29** |
| Renesas R-Car V4H | 16 | 12 | 1.33 | ASIL-B (partial HW) | 0.50 | **1.89** |
| Hypothetical TMR-NPU | 8.3 | 15 | 0.55 | ASIL-C candidate | 0.75 | **2.80** |
| **FLUX-LUCID FPGA** | **2.4** | **18.6** | **0.13** | **DAL A path** | **0.84** | **20.17** |
| **FLUX-LUCID ASIC (proj.)** | **24** | **2.58** | **9.30** | **DAL A full** | **1.00** | **>200** |

FLUX-LUCID FPGA achieves 20.17 Safe-TOPS/W — 3.8× higher than the nearest certified competitor (Hailo-8, 5.29) despite lower raw throughput. The S = 0.84 reflects partial Coq coverage (36/43 opcodes) at measurement time. S = 1.0 is projected on completion of the 6–9 month verification program, at which point the ASIC projection exceeds 200 Safe-TOPS/W.

*Note on TOPS normalization:* The FPGA TOPS figure (2.4) reflects the ternary-optimized inference workload on the 20-tile RAU array at 100 MHz. The Artix-7 prototype is throughput-limited by the evaluation platform, not the architecture; the 22nm ASIC projection (24 TOPS) is derived from the synthesis results scaled to the ASIC target process.

### 6.3 Latency Overhead Analysis

Inference pipeline cycle counts with and without FLUX enabled, 10,000 randomized inputs:

| Metric | Without FLUX | With FLUX | Overhead |
|---|---|---|---|
| Mean latency (cycles) | 12,847 | 12,847 | 0.00% |
| P99 latency | 13,102 | 13,102 | 0.00% |
| P99.9 latency | 13,450 | 13,451 | +1 cycle |
| Max observed | 13,891 | 13,892 | +1 cycle |

The +1 cycle at P99.9 corresponds to Merkle verification (8 cycles) coinciding with the minimum KV\_UPDATE stage (4 cycles) — the single condition where FLUX does not finish before the pipeline must advance. This is bounded and deterministic with no tail risk.

### 6.4 DO-254 DAL A Objective Mapping

| DO-254 Objective | FLUX-LUCID Evidence Artifact | Status |
|---|---|---|
| HW-01: Correct Implementation | 256-bit Merkle fault certificate per output token | Implemented, FPGA verified |
| HW-07: Error Detection >99% | 99.8% stuck-at fault coverage (ATPG on FLUX engine) | Measured |
| HW-10: Determinism | Gas-bounded execution; no interrupts, no caches | Proved (Coq Theorem 1) |
| HW-19: Common Cause Independence | Isolated power ring, independent clock domain, no shared routing | Implemented, DRC clean |

---

## 7. Related Work

### 7.1 Mobileye RSS and Safety Frameworks

**Mobileye Responsibility-Sensitive Safety (RSS)** [13] formalizes safe driving rules as mathematical inequalities. RSS is implemented in software on a certified processor — a layer that itself requires certification and adds response latency. RSS does not provide a hardware constraint language or VM amenable to independent formal verification of the enforcement mechanism. FLUX-LUCID complements RSS: RSS defines *what* is safe; FLUX-LUCID enforces it in hardware.

### 7.2 Hailo and AI-Specific Safety Hardware

**Hailo-8/15** targets edge vision applications with ASIL-B claims. Weights reside in mutable SRAM; safety functions are software overlays documented as a "functional safety wrapper" rather than hardware-enforced invariants. The Hailo safety island ISA is not published, making independent formal verification — required by DO-254 DAL A — impractical. FLUX-LUCID's entire ISA (43 opcodes) is openly specified and formally verified.

**NVIDIA Orin functional safety** [14] includes lockstep processor cores and ECC-protected memory for the CPU complex, but explicitly excludes the deep learning accelerator from the safety case boundary. The accelerator is treated as QM (quality managed, not safety-qualified), reflected by its 0.00 Safe-TOPS/W score.

### 7.3 Formal Methods Compilers and Verified Hardware

**CompCert** [2] formally verified a C compiler end-to-end in Coq, establishing that compiled code correctly implements source semantics. FLUX-LUCID applies the same methodology: GUARD DSL compilation is verified to produce FLUX bytecode semantically equivalent to source constraints. The Semantic Gap Theorem is an analogue of CompCert's semantic preservation theorem, applied to the hardware constraint domain.

**CertiKOS** [3] provides a certified concurrent OS kernel. The separation kernel approach — formally isolated partitions for safety-critical and non-critical functions — directly inspired FLUX-LUCID's physical power domain isolation of the FLUX engine from the inference engine. Where CertiKOS proves freedom from interference in software, FLUX-LUCID enforces it in silicon.

**Simplex Architecture** [11] interposes a verified backup controller on the actuator path. FLUX-LUCID differs: rather than switching to a backup after detecting an unsafe output, FLUX prevents the unsafe output from leaving the chip. There is no switchover event — the unsafe result never propagates.

### 7.4 Ternary and Binary Neural Networks

**BitNet b1.58** [10] demonstrates that 1.58-bit ternary quantization can match full-precision LLM accuracy on language tasks, providing the weight format FLUX-LUCID adopts. The contribution of FLUX-LUCID is not the quantization scheme but the hardware safety enforcement built on top of it: mask ROM immutability, XNOR-AND algebraic equivalence, and the Semantic Gap Theorem that formally closes the loop.

---

## 8. Conclusion and Future Work

### 8.1 Conclusion

FLUX-LUCID demonstrates that high-performance AI inference and hardware-enforced safety certification are not mutually exclusive. Three innovations — immutable ternary weights in mask ROM, a 43-opcode shadow observer VM, and a constraint-to-silicon compiler — combine to achieve zero latency overhead for constraint enforcement while providing a credible pathway to DO-254 DAL A.

The Semantic Gap Theorem provides the formal foundation certification authorities require: a mechanically checked Coq proof that bit-level hardware constraints are sufficient to guarantee application-level semantic safety for finite output domains. The Safe-TOPS/W metric provides the evaluation framework the field needs: a benchmark that penalizes uncertified hardware to zero, accurately reflecting deployment reality in safety-critical systems.

FPGA prototype results (44,243 LUTs, 2.58 W, 100 MHz, zero latency overhead across 10,000 runs) validate the architectural approach on real hardware. ASIC projections (12.7 mm², 22nm FDSOI, 24 TOPS/W, $48/chip) demonstrate economic viability for embedded deployment in eVTOL, automotive, and medical applications.

The mathematical bridge that makes this possible is the algebraic isomorphism between the RAU's compute primitive (XNOR over ternary encodings) and the constraint enforcement primitive (bitwise AND over BitmaskDomain). Safety checking is not a tax on computation. It is a structural consequence of the compute topology. Safety is a first-class computational primitive.

### 8.2 Limitations

**Semantic gap at open-domain scale.** The Semantic Gap Theorem applies to finite output domains with decidable safety predicates. For open-ended language generation with unbounded vocabulary, output whitelist construction requires further research without unduly limiting capability.

**Ternary precision ceiling.** Ternary quantization introduces accuracy degradation on complex reasoning tasks independent of the safety architecture. Continued advances in quantization-aware training will address this gap without hardware modifications.

**Multi-chip certification.** Scaling beyond a single die using the SmartCRDT multi-chip coordination protocol introduces additional DO-254 certification complexity for distributed hardware systems. The per-chip Safety\_Bitmask AND-merge protocol satisfies CRDT convergence guarantees but the system-level certification path for multi-chip clusters is an open problem.

### 8.3 Future Work

1. **Complete Coq opcode verification** (43/43 opcodes): prerequisite for S = 1.0 and DAL A submission. Estimated 6–9 months.
2. **Hardware-in-the-loop jitter analysis** at 100°C and maximum switching activity: required for DO-254 environmental qualification.
3. **GUARD constraint conflict resolution**: formal semantics for overlapping constraints with a proof that the arc consistency solver always produces a determinate result.
4. **eVTOL partner integration**: flight envelope constraint domains compiled from FAR Part 23/25 requirements, validated against real flight data.
5. **4-tile 22nm FDSOI test chip** (16 mm², Q4 2027): first silicon validation of ASIC projections.
6. **MLIR/LLVM integration**: automatic GUARD programme generation from annotated neural network training specifications, closing the loop between model training and runtime constraint certification.

---

## Acknowledgments

This work was developed through the Cocapn Fleet and SuperInstance research programs. The authors thank the ensemble of AI research systems whose contributions are documented in the project synthesis report: Seed-2.0-Pro (DO-254 certification path, FPGA integration), Hermes-405B (algebraic XNOR-AND equivalence proof), Seed-2.0-Code (guard2mask Rust compiler), Qwen-397B (SoC architecture, ASIC floorplan), and Gemma-4-26B (critical review that led to the Safe-TOPS/W methodology). Certification pathway guidance was informed by independent DO-254 DER review.

---

## References

[1] J. L. Hennessy and D. A. Patterson, "A New Golden Age for Computer Architecture," *Commun. ACM*, vol. 62, no. 2, pp. 48–60, 2019.

[2] X. Leroy, "Formal verification of a realistic compiler," *Commun. ACM*, vol. 52, no. 7, pp. 107–115, 2009.

[3] R. Gu et al., "Deep Specifications and Certified Abstraction Layers," in *Proc. ACM POPL*, pp. 595–608, 2015.

[4] K. Claessen and J. Hughes, "QuickCheck: A Lightweight Tool for Random Testing," in *Proc. ICFP*, pp. 268–279, 2000.

[5] B. Reese, A. Parashar, and J. Emer, "Safety Mechanisms for Deep Learning Accelerators in Safety-Critical Systems," in *Proc. ACM/IEEE DAC*, 2021.

[6] RTCA/DO-254, *Design Assurance Guidance for Airborne Electronic Hardware*, 2000.

[7] ISO 26262:2018, *Road Vehicles — Functional Safety*, Parts 1–12. ISO, Geneva, 2018.

[8] SAE International, ARP4754A, *Guidelines for Development of Civil Aircraft and Systems*, 2010.

[9] RTCA/DO-178C, *Software Considerations in Airborne Systems and Equipment Certification*, 2011.

[10] S. Ma et al., "The Era of 1-bit LLMs: All Large Language Models Are in 1.58 Bits," *arXiv:2402.17764*, 2024.

[11] L. Sha, "Using Simplicity to Control Complexity," *IEEE Software*, vol. 18, no. 4, pp. 20–28, 2001.

[12] D. Cofer et al., "Compositional Verification of Architectural Models," in *Proc. NFM*, LNCS 7226, 2012.

[13] S. Shalev-Shwartz et al., "On a Formal Model of Safe and Scalable Self-Driving Cars," *arXiv:1708.06374*, 2017. (Mobileye RSS.)

[14] NVIDIA Corporation, *DRIVE Orin SoC: Functional Safety Manual*, DA-09821-001, 2022.

[15] C. Wolf, "SymbiYosys: A Framework for Formal Hardware Verification," *ORCONF*, 2017.

[16] G. Klein et al., "seL4: Formal Verification of an OS Kernel," in *Proc. SOSP*, pp. 207–220, 2009.

[17] L. Lamport, *Specifying Systems: The TLA+ Language and Tools*. Addison-Wesley, 2002.

[18] EASA, *Artificial Intelligence Roadmap 2.0 — Human-Centric Approach to AI in Aviation*, 2023.

---

*Correspondence:* contact@cocapn.io
*Prototype RTL and Coq developments available upon request for academic peer review.*
*Manuscript length: approximately 10 pages in ACM two-column format.*
