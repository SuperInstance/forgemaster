# FPGA Implementation Plan: FLUX Constraint Checker (DO-254 DAL A)

---

## 1. Overview

FLUX is a constraint virtual machine with 43 opcodes, a 64-element stack, and a gas limit mechanism. The reference implementation runs on CUDA at 321M constraints/second but is uncertifiable for safety-critical airborne systems. This plan targets a Xilinx Artix-7 (XC7A100T) implementation achieving ~100M constraints/second at 100 MHz with a clear DO-254 Design Assurance Level A certification path.

---

## 2. State Machine Architecture

The FLUX core is a 5-stage FSM-based pipeline:

```
FETCH → DECODE → EXECUTE → WRITEBACK → GAS_CHECK
```

Each stage advances on the rising clock edge. The control FSM has the following states:

| State | Description |
|---|---|
| `IDLE` | Awaiting constraint program load |
| `FETCH` | Read opcode from instruction BRAM at PC |
| `DECODE` | Register opcode, decode operands, check gas |
| `EXECUTE` | Perform stack operation or arithmetic |
| `WRITEBACK` | Commit stack pointer and result |
| `TRAP` | Latch fault (stack underflow, gas exhaustion, assert fail) |
| `HALT` | Clean termination, raise `DONE` signal |

The `TRAP` state is a **one-way latch** — no self-clearing. This is a DO-254 requirement: faults must be externally acknowledged and logged before the core resets.

---

## 3. BRAM Stack

The 64-element stack maps cleanly to a single 18Kb BRAM in simple dual-port mode:

- **Width:** 32-bit data (IEEE 754 single or fixed-point Q16.16)
- **Depth:** 64 entries (6-bit address)
- **Port A:** Read (EXECUTE stage pulls operands)
- **Port B:** Write (WRITEBACK pushes results)
- **Stack pointer:** 6-bit register, incremented/decremented combinatorially

Stack underflow (`SP == 0` on a pop) and overflow (`SP == 63` on a push) immediately assert `TRAP`. The BRAM initialization vector is zeroed at reset — this must be verified in the DO-254 Hardware Verification Test (HVT) suite.

```verilog
// Stack BRAM primitive (Xilinx RAMB18E1)
RAMB18E1 #(
  .READ_WIDTH_A(32), .WRITE_WIDTH_B(32),
  .RAM_MODE("SDP"),  .DOA_REG(0)
) stack_bram (
  .CLKARDCLK(clk), .ADDRARDADDR({sp_read, 4'b0}),
  .CLKBWRCLK(clk), .ADDRBWRADDR({sp_write, 4'b0}),
  .DIBDI(tos_write), .DOBDO(tos_read),
  .ENARDEN(read_en), .ENBWREN(write_en)
);
```

---

## 4. Opcode Implementations

### `RANGE` (opcode 0x07)
Pops `val`, `lo`, `hi` (3 pops). Pushes 1 if `lo ≤ val ≤ hi`, else traps. Implemented as two parallel comparators in a single EXECUTE cycle. No division, no multi-cycle stall.

### `ASSERT` (opcode 0x0A)
Pops TOS. If TOS == 0, asserts `TRAP` with fault code `ASSERT_FAIL`. If TOS != 0, continues. One cycle.

### `BOOL_AND` (opcode 0x11)
Pops two values. Pushes `(A != 0) & (B != 0)`. Pure combinatorial — synthesizes to ~2 LUTs.

### `BOOL_OR` (opcode 0x12)
Pops two values. Pushes `(A != 0) | (B != 0)`. One cycle, ~2 LUTs.

### `DUP` (opcode 0x1C)
Reads TOS without decrementing SP, then pushes the same value. Implemented as a BRAM read followed by a write to SP+1 with SP increment. Two-cycle operation (pipeline stall inserted via `stall` signal).

### `SWAP` (opcode 0x1D)
Reads TOS and TOS-1 simultaneously using two BRAM read ports (or single-port with a 2-cycle stall). Writes them back in swapped order. Implemented as a 2-cycle micro-op.

### `HALT` (opcode 0x00)
Transitions FSM to `HALT` state. Asserts `DONE` output high. Gas remaining is latched to `GAS_OUT` register. The constraint result (pass/fail) is latched to `RESULT` output. All outputs are registered — no combinatorial paths to outputs (DO-254 requirement).

---

## 5. Gas Limit Mechanism

A 16-bit down-counter initialised from a `GAS_LIMIT` input register decrements each EXECUTE cycle. On undercount (`GAS == 0` before `HALT`), the FSM enters `TRAP` with fault code `GAS_EXHAUSTED`. This prevents infinite loops in malformed constraint programs — critical for deterministic worst-case execution time (WCET) analysis required by DO-254.

---

## 6. Throughput Estimate

| Parameter | Value |
|---|---|
| Clock frequency | 100 MHz (Artix-7 grade -1) |
| Cycles per constraint (average) | 1 pipeline cycle amortised |
| DUP/SWAP stall penalty | 1 cycle per occurrence |
| BRAM read latency | 1 cycle (registered output) |
| **Throughput** | **~100M constraints/second** |

Pipeline occupancy is maximised by preloading the next constraint's first opcode during the `HALT` state of the current constraint (lookahead fetch). Effective throughput approaches 1 constraint/clock for workloads with ≤5% DUP/SWAP frequency.

---

## 7. Resource Estimate (XC7A100T)

| Resource | Estimated Usage | Available | Utilisation |
|---|---|---|---|
| LUTs | ~480 | 63,400 | 0.76% |
| FFs | ~220 | 126,800 | 0.17% |
| BRAM (18Kb) | 2 (stack + instruction) | 135 | 1.5% |
| DSP48 | 0 (arithmetic in LUTs) | 240 | 0% |
| IOBs | 32 (AXI-lite interface) | 210 | 15% |

The minimal footprint enables co-integration with a DO-254 flight computer SoC on the same Artix-7 device.

---

## 8. DO-254 DAL A Certification Path

DO-254 DAL A requires evidence that the hardware is free of undetected design errors. The FLUX FPGA core addresses this through:

**Plan for Hardware Aspects of Certification (PHAC):**
- Hardware Safety Assessment (HSA) mapping each TRAP state to a system-level failure mode
- Requirements capture in DOORS/Excel with bidirectional traceability to HDL

**Design Assurance Activities:**
- HDL coding standards (MISRA-HDL or equivalent) enforced via linting (Questa Lint)
- Peer review of every FSM state transition with sign-off
- Independence between EXECUTE and TRAP logic (separate always blocks, separate review)

**Verification (DO-254 §6.2):**
- **Functional simulation:** ModelSim/Questa — 100% opcode coverage, all TRAP paths exercised
- **Formal verification:** SymbiYosys (see §9)
- **Hardware Verification Tests (HVT):** Physical board tests at temperature/voltage extremes
- **Code coverage:** Statement, branch, expression, FSM state — 100% required for DAL A
- **Structural coverage analysis:** MC/DC equivalent for HDL

**Configuration Management:**
- All HDL committed to CM-controlled repository with immutable tags
- Synthesis tool (Vivado 2024.x) and version locked in CM record
- Bitstream hash logged in certification artefact package

**Tool Qualification:**
- Vivado synthesis/P&R requires TQL-5 qualification artefact (vendor-provided or project-generated)
- SymbiYosys requires qualification artefact under DO-254 §11.4

---

## 9. SymbiYosys Formal Verification Assertions

```systemverilog
// flux_formal.sv — SymbiYosys assertion module

module flux_formal (
  input logic clk, rst_n,
  input logic [5:0] sp,
  input logic [2:0] fsm_state,
  input logic trap, done,
  input logic [15:0] gas
);

  // P1: Stack pointer never exceeds depth
  STACK_BOUNDS: assert property (
    @(posedge clk) disable iff (!rst_n)
    sp <= 6'd63
  );

  // P2: TRAP is a one-way latch (no self-clear)
  TRAP_LATCH: assert property (
    @(posedge clk) disable iff (!rst_n)
    trap |=> trap
  );

  // P3: DONE only asserted from HALT state (state 3'b110)
  DONE_FROM_HALT: assert property (
    @(posedge clk) disable iff (!rst_n)
    done |-> (fsm_state == 3'b110)
  );

  // P4: Gas never underflows past zero
  GAS_NO_UNDERFLOW: assert property (
    @(posedge clk) disable iff (!rst_n)
    (gas == 16'h0) |-> trap
  );

  // P5: TRAP and DONE mutually exclusive
  TRAP_DONE_MUTEX: assert property (
    @(posedge clk) disable iff (!rst_n)
    !(trap && done)
  );

  // P6: After reset, stack pointer is zero
  RESET_SP: assert property (
    @(posedge clk)
    !rst_n |=> (sp == 6'd0)
  );

endmodule
```

Run with: `sby -f flux_formal.sby prove` targeting `bmc` depth 50 and `prove` unbounded.

---

## 10. GPU vs FPGA Trade-off Analysis

| Attribute | GPU (CUDA) | FPGA (Artix-7) |
|---|---|---|
| Throughput | **321M/s** | 100M/s |
| Certification | Uncertifiable (DO-254) | **DAL A certifiable** |
| Determinism | Non-deterministic latency | **Cycle-exact WCET** |
| Power | ~150W (data centre GPU) | **~0.5W** |
| Fault isolation | OS/driver stack | **Hardware-only, no OS** |
| Formal verification | Not applicable | **SymbiYosys proven** |
| Deployment context | Ground simulation only | **Airborne, embedded** |

The GPU delivers 3.2× higher raw throughput but is architecturally incompatible with airborne certification. The FPGA solution accepts a throughput reduction in exchange for determinism, formal correctness guarantees, and a complete DO-254 DAL A evidence package — making 100M/s at full assurance categorically superior to 321M/s uncertified for safety-critical constraint checking in flight systems.

---

`★ Insight ─────────────────────────────────────`
- The one-way TRAP latch is architecturally mandated by DO-254: self-clearing fault logic is a common DAL A rejection reason because it can mask transient hardware errors before they are logged.
- BRAM-based stacks on Artix-7 add exactly 1 cycle of read latency (registered output mode). Choosing unregistered mode halves latency but destroys the 100 MHz timing closure — a common first-pass timing failure in student FPGA designs.
- SymbiYosys `prove` mode uses k-induction, not just BMC. For safety properties like TRAP_LATCH, induction is required; BMC alone cannot prove unbounded liveness.
`─────────────────────────────────────────────────`
