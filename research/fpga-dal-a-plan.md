# FLUX Constraint Checker — FPGA Implementation Plan for DO-254 DAL A

**Author:** Forgemaster ⚒️  
**Date:** 2026-05-04  
**Target:** Xilinx Artix-7 (XC7A100T) — aerospace-qualified  
**Standard:** DO-254 Design Assurance Level A (DAL A)  

---

## 1. Architecture Overview

The FLUX-C core implements a three-stage state machine for constraint evaluation:

```
        ┌──────────┐    ┌──────────┐    ┌──────────┐
        │  FETCH   │───▶│  DECODE  │───▶│ EXECUTE  │──┐
        └──────────┘    └──────────┘    └──────────┘  │
              ▲                                         │
              └─────────────────────────────────────────┘
                         (next instruction / HALT)
```

### State Machine

| State     | Description                                              | Cycles |
|-----------|----------------------------------------------------------|--------|
| `FETCH`   | Read opcode from instruction memory (ROM/BRAM), PC++     | 1      |
| `DECODE`  | Map opcode → control signals; resolve operand fields     | 1      |
| `EXECUTE` | Perform operation (comparison, stack op, boolean logic)  | 1      |

**Pipeline strategy:** Simple 3-state FSM (not pipelined) to minimize verification surface. DAL A favors deterministic, single-cycle-per-instruction execution over throughput.

### Top-Level Ports

```systemverilog
module flux_core #(
    parameter int STACK_DEPTH = 64,
    parameter int DATA_WIDTH  = 32,
    parameter int GAS_WIDTH   = 16
) (
    input  logic                    clk,        // 100 MHz
    input  logic                    rst_n,      // active-low reset
    input  logic                    start,      // begin evaluation
    input  logic [DATA_WIDTH-1:0]   test_value, // value under test
    output logic                    pass_fail,  // 1=pass, 0=fail
    output logic                    done,       // evaluation complete
    output logic                    gas_fault   // gas exhausted
);
```

### Instruction Memory

- **Layout:** Single BRAM (18Kb), up to 1024 × 16-bit instructions
- **Encoding:** `[15:10] opcode (6 bits)` | `[9:0] immediate/operand`
- **PC:** 10-bit counter, reset to 0 on `start`

---

## 2. Stack Design — BRAM-Based, 64 Entries

### Implementation

```
Stack Pointer (SP): 6-bit counter (0–63)
Stack Memory:       BRAM, 64 × 32-bit, single-port
                    READ:  SP-1 (TOS)  [combinational addr]
                    WRITE: SP         [registered write]
```

### Stack Operations

| Operation | SP Change | Notes                        |
|-----------|-----------|------------------------------|
| PUSH imm  | SP++      | Write to SP, then increment  |
| POP       | SP--      | Decrement SP                 |
| DUP       | SP++      | Copy TOS to SP, increment    |
| SWAP      | —         | Exchange TOS and TOS-1       |
| PEEK      | —         | Read TOS without modifying SP|

### BRAM Timing

BRAM has 1-cycle read latency. To achieve single-cycle execution:

1. **Pre-fetch:** During DECODE, assert BRAM read address for TOS (SP-1)
2. **Execute:** BRAM data available at clock edge; operate immediately
3. **Write-back:** Simultaneous write if operation modifies TOS

This is safe because BRAM supports **read-first** mode (same-address read completes before write).

```systemverilog
// Stack memory — single-port BRAM, read-first mode
logic [DATA_WIDTH-1:0] stack_mem [0:STACK_DEPTH-1];
logic [5:0]            sp;  // stack pointer

always_ff @(posedge clk) begin
    if (wr_en)
        stack_mem[sp] <= wr_data;
    rd_data <= stack_mem[rd_addr];  // 1-cycle latency
end
```

---

## 3. Opcode Set

### Core Opcodes (FLUX-C Subset for FPGA)

| Opcode  | Code | Stack Effect          | Description                                    |
|---------|------|-----------------------|------------------------------------------------|
| `NOP`   | 0x00 | —                     | No operation                                   |
| `PUSH`  | 0x01 | → val                 | Push immediate value                           |
| `LOAD`  | 0x02 | → test_value          | Push the test value onto stack                 |
| `DUP`   | 0x03 | a → a a               | Duplicate top of stack                         |
| `SWAP`  | 0x04 | a b → b a             | Swap top two elements                          |
| `POP`   | 0x05 | a →                   | Discard top of stack                           |
| `RANGE` | 0x10 | lo hi val → bool      | True if lo ≤ val ≤ hi                         |
| `EQ`    | 0x11 | a b → bool            | True if a == b                                 |
| `LT`    | 0x12 | a b → bool            | True if a < b                                  |
| `GT`    | 0x13 | a b → bool            | True if a > b                                  |
| `ASSERT`| 0x20 | bool →                | If false, set pass_fail=0, halt                |
| `BOOL_AND` | 0x21 | a b → (a∧b)        | Logical AND                                    |
| `BOOL_OR`  | 0x22 | a b → (a∨b)        | Logical OR                                     |
| `BOOL_NOT` | 0x23 | a → ¬a              | Logical NOT                                    |
| `HALT`  | 0x3F | —                     | End evaluation, output result                  |

### RANGE Opcode Detail

The critical opcode for constraint checking. Implemented as a single-cycle triple comparison:

```systemverilog
// RANGE: lo ≤ val ≤ hi
// Stack: [lo, hi, val] → [result]
wire [DATA_WIDTH-1:0] lo  = stack_mem[sp-3]; // 3rd from top
wire [DATA_WIDTH-1:0] hi  = stack_mem[sp-2]; // 2nd from top
wire [DATA_WIDTH-1:0] val = stack_mem[sp-1]; // TOS

wire in_range = (val >= lo) && (val <= hi);
// Result replaces the three operands on stack
```

### ASSERT Opcode Detail

```systemverilog
// ASSERT: if TOS is 0, fail and halt; if nonzero, continue
always_ff @(posedge clk) begin
    if (opcode == ASSERT) begin
        if (tos == 32'd0) begin
            pass_fail <= 1'b0;
            state     <= HALTED;
        end
        sp <= sp - 1; // pop the boolean
    end
end
```

---

## 4. Gas Counter — 16-Bit Execution Guard

Prevents infinite loops and guarantees deterministic termination.

```systemverilog
logic [GAS_WIDTH-1:0] gas;

always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n)
        gas <= {GAS_WIDTH{1'b1}}; // init to max (65535)
    else if (start)
        gas <= gas_init;          // configurable initial gas
    else if (state == EXECUTE && gas != 0)
        gas <= gas - 1;
    else if (gas == 0 && state != HALTED) begin
        gas_fault <= 1'b1;
        pass_fail <= 1'b0;
        state     <= HALTED;
    end
end
```

**Properties:**
- 16-bit gives 65,535 instruction budget per evaluation
- Gas decrements in EXECUTE state only
- Gas exhaustion → immediate halt with FAIL
- Gas is **not** writable by instructions (no gas manipulation attack vector)

---

## 5. Throughput Estimate

### Single-Core Performance

| Parameter         | Value                |
|-------------------|----------------------|
| Clock frequency   | 100 MHz              |
| Instructions/cycle| 1 (non-pipelined)    |
| Avg constraint length | ~5 instructions  |
| Constraints/sec   | **~20M/s per core**  |

**Note:** 1 constraint per clock cycle (100M/s) applies only if constraints are single-instruction (pure RANGE). Realistic constraints with LOAD+PUSH+RANGE+ASSERT average 5 instructions, yielding ~20M/s.

### Multi-Core Scaling (Artix-7 XC7A100T)

| Config       | Cores | Throughput    | BRAM Used | LUTs Used |
|--------------|-------|---------------|-----------|-----------|
| Single core  | 1     | 20M/s         | 2         | ~500      |
| 16-core      | 16    | 320M/s        | 32        | ~8,000    |
| 32-core      | 32    | 640M/s        | 64        | ~16,000   |
| 64-core      | 64    | 1.28B/s       | 128       | ~32,000   |

**Artix-7 XC7A100T resources:** 15,850 LUTs, 240 BRAM (36Kb), 100 I/O.  
→ **Sweet spot: 16-core** at 320M/s, using ~50% LUTs and 13% BRAM.

### Throughput Comparison

| Platform       | Throughput  | Certifiable? | Latency     |
|----------------|-------------|--------------|-------------|
| CUDA GPU       | 321M/s      | ❌ No         | ~1ms batch  |
| FPGA 1-core    | 20M/s       | ✅ DAL A      | ~50ns single|
| FPGA 16-core   | 320M/s      | ✅ DAL A      | ~50ns single|
| FPGA 32-core   | 640M/s      | ✅ DAL A      | ~50ns single|

**Key insight:** FPGA matches GPU throughput at 16 cores while being fully certifiable, with orders-of-magnitude better single-check latency.

---

## 6. Resource Estimate — Single FLUX-C Core

| Resource                | Estimate  | Rationale                              |
|-------------------------|-----------|----------------------------------------|
| LUTs                    | ~500      | ALU (comparators, muxes), FSM, decoder |
| Flip-Flops              | ~200      | SP (6), PC (10), gas (16), state (2), control |
| BRAM (18Kb)             | 1         | Stack: 64×32-bit = 2Kb (fits in 1 BRAM) |
| BRAM (instruction mem)  | 1         | Up to 1024 × 16-bit instructions       |
| DSP slices              | 0         | No multiplication needed               |
| Clock                   | 100 MHz   | Conservative for Artix-7               |

**Total footprint: < 3% of Artix-7 XC7A100T resources per core.**

This is tiny. The design is dominated by BRAM (stack + instruction memory) and the comparison logic in RANGE/EQ/LT/GT.

---

## 7. DO-254 DAL A Certification Path

### DO-254 Overview

DO-254 ("Design Assurance Guidance for Airborne Electronic Hardware") defines five Design Assurance Levels (A through E). **DAL A** is the highest — required for hardware whose failure would cause or contribute to a catastrophic failure condition.

### DAL A Requirements Summary

| Requirement                | FLUX-C Approach                                        |
|---------------------------|--------------------------------------------------------|
| Planning                  | PHAC, SDP, SVP, SCP, CMP (see §10 below)             |
| Design standards          | Coding standard (SystemVerilog style guide)            |
| Requirements traceability | Every opcode → requirement → test case                 |
| 100% structural coverage  | Statement, branch, condition, FSM state coverage       |
| Independence              | Verification team independent from design team         |
| Formal verification       | SymbiYosys proofs for all opcodes (see §8)            |
| Element-level analysis    | Each FLUX-C opcode is a verified element               |
| Configuration management  | Git-based, tagged releases, baseline control           |
| Tool qualification        | Synthesis tool (Vivado) assessed per DO-254 §11.4     |

### Certification Artifacts

1. **PHAC** — Plan for Hardware Aspects of Certification
2. **Hardware Development Plan** — Design process, tools, standards
3. **Hardware Verification Plan** — Test strategy, formal verification plan
4. **Hardware Requirements** — Functional requirements per opcode
5. **Traceability Matrix** — Requirement ↔ Design ↔ Test ↔ Formal Proof
6. **Hardware Test Results** — Simulation + hardware test reports
7. **Formal Verification Report** — SymbiYosys proof results
8. **Configuration Index** — Controlled file list with checksums
9. **Hardware Accomplishment Summary** — Compliance statement

---

## 8. SymbiYosys Formal Verification

### Tool Chain

- **SymbiYosys** (sby) — open-source formal verification for Verilog/SystemVerilog
- **Yosys** — synthesis engine with formal backends
- **Solvers:** Z3, Boolector, Yices (multiple solvers for independence)

### Verification Strategy

Each opcode is proven correct via SystemVerilog `assert`, `assume`, and `cover` properties. The FLUX-C core's small size (~500 LUTs) makes exhaustive formal verification feasible.

### Assertions Per Opcode

```systemverilog
// ============================================================
// FLUX-C Formal Verification — SymbiYosys Assertions
// ============================================================

module flux_core_formal #(
    parameter int STACK_DEPTH = 64,
    parameter int DATA_WIDTH  = 32,
    parameter int GAS_WIDTH   = 16
) (
    input  logic                    clk,
    input  logic                    rst_n,
    input  logic                    start,
    input  logic [DATA_WIDTH-1:0]   test_value,
    output logic                    pass_fail,
    output logic                    done,
    output logic                    gas_fault
);

    // --- Instantiation wrapper (bind into flux_core) ---
    // Assumes flux_core signals are accessible via hierarchical reference

    // ============================================================
    // ASSUMPTIONS (constrain inputs)
    // ============================================================

    // Stack pointer never underflows or overflows
    assume property (@(posedge clk) disable iff (!rst_n)
        sp inside {[0:STACK_DEPTH-1]});

    // Gas is initialized properly
    assume property (@(posedge clk) disable iff (!rst_n)
        start |-> gas == {GAS_WIDTH{1'b1}});

    // ============================================================
    // RANGE OPCODE PROOF
    // ============================================================

    // RANGE computes: (val >= lo) && (val <= hi)
    // Stack effect: pops 3, pushes 1 boolean
    assert property (@(posedge clk) disable iff (!rst_n)
        (opcode == RANGE && state == EXECUTE && sp >= 3 && gas > 0)
        |=>
        // Result is 1 iff lo <= val <= hi
        (stack_mem[sp-4] == 32'd1) ==
            ((stack_mem[sp-3] <= stack_mem[sp-1]) &&
             (stack_mem[sp-1] <= stack_mem[sp-2]))
    );

    // RANGE always decrements SP by 2 (net: pop 3, push 1)
    assert property (@(posedge clk) disable iff (!rst_n)
        (opcode == RANGE && state == EXECUTE && sp >= 3 && gas > 0)
        |=>
        sp == $past(sp) - 2
    );

    // ============================================================
    // ASSERT OPCODE PROOF
    // ============================================================

    // ASSERT(false) always sets pass_fail = 0
    assert property (@(posedge clk) disable iff (!rst_n)
        (opcode == ASSERT && state == EXECUTE &&
         stack_mem[sp-1] == 32'd0 && gas > 0)
        |=>
        pass_fail == 1'b0 && state == HALTED
    );

    // ASSERT(true) continues execution
    assert property (@(posedge clk) disable iff (!rst_n)
        (opcode == ASSERT && state == EXECUTE &&
         stack_mem[sp-1] != 32'd0 && gas > 0)
        |=>
        pass_fail == $past(pass_fail) && state != HALTED
    );

    // ============================================================
    // BOOL_AND OPCODE PROOF
    // ============================================================

    assert property (@(posedge clk) disable iff (!rst_n)
        (opcode == BOOL_AND && state == EXECUTE && sp >= 2 && gas > 0)
        |=>
        // Result is 1 iff both operands are nonzero
        (stack_mem[sp-3] != 32'd0) ==
            (($past(stack_mem[sp-2]) != 32'd0) &&
             ($past(stack_mem[sp-1]) != 32'd0))
    );

    // ============================================================
    // BOOL_OR OPCODE PROOF
    // ============================================================

    assert property (@(posedge clk) disable iff (!rst_n)
        (opcode == BOOL_OR && state == EXECUTE && sp >= 2 && gas > 0)
        |=>
        (stack_mem[sp-3] != 32'd0) ==
            (($past(stack_mem[sp-2]) != 32'd0) ||
             ($past(stack_mem[sp-1]) != 32'd0))
    );

    // ============================================================
    // BOOL_NOT OPCODE PROOF
    // ============================================================

    assert property (@(posedge clk) disable iff (!rst_n)
        (opcode == BOOL_NOT && state == EXECUTE && sp >= 1 && gas > 0)
        |=>
        (stack_mem[sp-2] == 32'd0) == ($past(stack_mem[sp-1]) != 32'd0)
    );

    // ============================================================
    // DUP OPCODE PROOF
    // ============================================================

    assert property (@(posedge clk) disable iff (!rst_n)
        (opcode == DUP && state == EXECUTE && sp >= 1 &&
         sp < STACK_DEPTH-1 && gas > 0)
        |=>
        stack_mem[sp-1] == $past(stack_mem[sp-2]) &&  // new TOS = old TOS
        sp == $past(sp) + 1
    );

    // ============================================================
    // SWAP OPCODE PROOF
    // ============================================================

    assert property (@(posedge clk) disable iff (!rst_n)
        (opcode == SWAP && state == EXECUTE && sp >= 2 && gas > 0)
        |=>
        stack_mem[sp-2] == $past(stack_mem[sp-1]) &&  // TOS = old TOS-1
        stack_mem[sp-1] == $past(stack_mem[sp-2])     // TOS-1 = old TOS
    );

    // ============================================================
    // GAS COUNTER PROOF
    // ============================================================

    // Gas always decrements in EXECUTE state
    assert property (@(posedge clk) disable iff (!rst_n)
        (state == EXECUTE && gas > 0 && opcode != HALT)
        |=>
        gas == $past(gas) - 1
    );

    // Gas exhaustion triggers fault
    assert property (@(posedge clk) disable iff (!rst_n)
        (state == EXECUTE && gas == 1 && opcode != HALT)
        |=>
        gas_fault == 1'b1 && pass_fail == 1'b0
    );

    // Gas fault is sticky (cannot clear without reset)
    assert property (@(posedge clk) disable iff (!rst_n)
        gas_fault |=> gas_fault
    );

    // ============================================================
    // HALT OPCODE PROOF
    // ============================================================

    assert property (@(posedge clk) disable iff (!rst_n)
        (opcode == HALT && state == EXECUTE && gas > 0)
        |=>
        done == 1'b1 && state == HALTED
    );

    // ============================================================
    // COVERAGE PROPERTIES
    // ============================================================

    // Cover: all opcodes are reached
    cover property (@(posedge clk) disable iff (!rst_n)
        opcode == RANGE);
    cover property (@(posedge clk) disable iff (!rst_n)
        opcode == ASSERT && stack_mem[sp-1] == 32'd0);
    cover property (@(posedge clk) disable iff (!rst_n)
        opcode == ASSERT && stack_mem[sp-1] != 32'd0);
    cover property (@(posedge clk) disable iff (!rst_n)
        opcode == BOOL_AND);
    cover property (@(posedge clk) disable iff (!rst_n)
        opcode == BOOL_OR);
    cover property (@(posedge clk) disable iff (!rst_n)
        gas_fault == 1'b1);

endmodule
```

### SymbiYosys Configuration (sby file)

```ini
[options]
mode prove
depth 50
timeout 600

[engines]
smtbmc z3
smtbmc yices    # second solver for independence

[script]
read -formal flux_core.sv
read -formal flux_core_formal.sv
prep -top flux_core_formal

[files]
flux_core.sv
flux_core_formal.sv
```

### Formal Verification Plan

| Proof Target            | Method       | Depth | Solvers    |
|-------------------------|--------------|-------|------------|
| RANGE correctness       | assert       | 20    | Z3, Yices  |
| ASSERT false path       | assert       | 10    | Z3, Yices  |
| ASSERT true path        | assert       | 10    | Z3, Yices  |
| BOOL_AND truth table    | assert       | 10    | Z3, Yices  |
| BOOL_OR truth table     | assert       | 10    | Z3, Yices  |
| BOOL_NOT correctness    | assert       | 10    | Z3, Yices  |
| DUP preserves value     | assert       | 10    | Z3, Yices  |
| SWAP exchanges values   | assert       | 10    | Z3, Yices  |
| Gas decrements          | assert       | 20    | Z3, Yices  |
| Gas exhaustion fault    | assert       | 20    | Z3, Yices  |
| Gas fault sticky        | assert       | 50    | Z3, Yices  |
| HALT terminates         | assert       | 10    | Z3, Yices  |
| No unreachable states   | cover        | 50    | Z3, Yices  |
| Stack bounds invariant  | assume+assert| 50    | Z3, Yices  |

---

## 9. GPU vs FPGA Comparison

### Quantitative

| Metric               | CUDA GPU (RTX-class) | FPGA 16-core (Artix-7) |
|----------------------|----------------------|-------------------------|
| Throughput           | 321M constraints/s   | 320M constraints/s      |
| Single-check latency | ~1ms (batch mode)    | ~50ns (deterministic)   |
| Power                | 250W+                | 2-5W                    |
| Silicon area         | ~800mm²              | ~35mm²                  |
| Weight               | ~1kg (card)          | ~10g (FPGA)             |
| Temperature range    | 0–85°C (consumer)    | -55–125°C (military)    |
| Certification path   | None                 | DO-254 DAL A feasible   |
| Tool chain cost      | CUDA toolkit (free)  | Vivado ($0–$3K)         |
| NRE cost             | Software engineering | HW + certification      |
| Unit cost (qty 100)  | $500–$1,500          | $30–$80                 |

### Qualitative

| Aspect              | GPU                           | FPGA                              |
|---------------------|-------------------------------|-----------------------------------|
| **Certifiability**  | Impossible — no DO-254 path for GPU | Purpose-built for DO-254     |
| **Determinism**     | Non-deterministic scheduling  | Cycle-exact deterministic        |
| **Radiation**       | No rad-hard variants          | Available in rad-hard grades      |
| **Supply chain**    | Consumer, volatile            | Aerospace-qualified supply       |
| **Verification**    | Software testing only         | Formal proof + structural coverage|
| **Throughput parity** | ✅ 321M/s today             | ✅ 320M/s at 16 cores            |

### The Bottom Line

The GPU wins on raw throughput-per-dollar for non-certified use. But for airborne use:

> **A GPU at 321M/s that can't fly is worth 0M/s.**  
> **An FPGA at 100M/s that passes DO-254 DAL A is worth infinitely more.**

And at 16 cores, the FPGA *matches* GPU throughput anyway. This is not a trade-off — it's a clean sweep.

---

## 10. Path to DO-254 DAL A — Phase Plan

### Phase 1: Design (Weeks 1–4)

**Objective:** Produce certifiable RTL and design documentation.

| Activity                         | Output                               |
|----------------------------------|--------------------------------------|
| Write Hardware Requirements Spec | HRS document, opcode-by-opcode       |
| Write Design Standard            | SystemVerilog coding standard        |
| Implement RTL                    | `flux_core.sv` — synthesizable RTL   |
| Write traceability matrix        | Req ↔ RTL ↔ Proof ↔ Test mapping     |
| Design review (peer)             | Review minutes, action items          |

**Design Standards:**
- All `always_ff` blocks with async reset (`negedge rst_n`)
- No `x` propagation — all signals have explicit default values
- No `casex` — use `casez` only with documented justification
- Parameterized design (`DATA_WIDTH`, `STACK_DEPTH`, `GAS_WIDTH`)
- No inferred latches — full case coverage verified by formal

### Phase 2: Formal Verification (Weeks 3–6, overlaps Phase 1)

**Objective:** Prove functional correctness via SymbiYosys.

| Activity                         | Output                               |
|----------------------------------|--------------------------------------|
| Write SVA assertions             | `flux_core_formal.sv`               |
| Run SymbiYosys proofs            | Proof report (PASS/FAIL per property)|
| Run with 2+ solvers              | Independence evidence                |
| Cover all opcodes                | Coverage report                      |
| Document proofs                  | Formal Verification Report           |

**Independence requirement (DAL A):** Formal verification must be performed by someone other than the RTL designer. Minimum two independent solvers (Z3 + Yices).

### Phase 3: Simulation Verification (Weeks 5–8)

**Objective:** Dynamic simulation achieving 100% structural coverage.

| Activity                         | Output                               |
|----------------------------------|--------------------------------------|
| Write testbench                  | SystemVerilog UVM or simple TB       |
| Stimulus per opcode              | Directed tests for each opcode       |
| Random stimulus                  | Constrained-random for edge cases    |
| Measure coverage                 | 100% statement, branch, condition, FSM |
| Regression suite                 | Automated, version-controlled tests  |
| Test results report              | Coverage dashboard, pass/fail matrix |

**Coverage targets (DAL A mandatory):**
- **Statement coverage:** 100%
- **Branch coverage:** 100%
- **Condition coverage:** 100%
- **FSM state coverage:** 100%
- **FSM transition coverage:** 100%

### Phase 4: Synthesis & Implementation (Weeks 7–10)

| Activity                         | Output                               |
|----------------------------------|--------------------------------------|
| Synthesize with Vivado           | Netlist, utilization report          |
| Place & route                    | Timing report (100MHz met)           |
| Static timing analysis           | All paths meet timing                |
| Power analysis                   | Power budget (must be <2W)           |
| Gate-level simulation            | GLS with SDF annotation              |
| Bitstream generation             | `.bit` file, controlled baseline     |

### Phase 5: Hardware Testing (Weeks 9–12)

| Activity                         | Output                               |
|----------------------------------|--------------------------------------|
| Board bring-up                   | Artix-7 dev board or custom PCB      |
| Run test vectors on hardware     | Hardware test results                |
| Compare HW vs simulation         | Matching results                     |
| Environmental test (if required) | Temperature, vibration data          |

### Phase 6: Certification Package (Weeks 11–14)

| Document                         | Description                          |
|----------------------------------|--------------------------------------|
| PHAC                             | Plan for Hardware Aspects of Certification |
| Hardware Development Plan        | Design process, tools, standards     |
| Hardware Verification Plan       | Formal + simulation + HW test plan   |
| Hardware Requirements            | Functional spec per opcode           |
| Design Representation            | RTL, schematic (if hybrid)           |
| Traceability Matrix              | Full bidirectional trace             |
| Formal Verification Report       | SymbiYosys results                   |
| Simulation Test Report           | Coverage + results                   |
| Hardware Test Report             | On-target results                    |
| Configuration Management Plan    | Git, tagging, baselines              |
| Tool Qualification Report        | Vivado assessment                    |
| Hardware Accomplishment Summary  | Compliance statement for DER         |

### Timeline Summary

```
Week  1  2  3  4  5  6  7  8  9 10 11 12 13 14
      ├──┤                                        Phase 1: Design
            ├─────┤                                Phase 2: Formal Verif
                  ├─────┤                          Phase 3: Simulation
                        ├─────┤                    Phase 4: Synthesis
                              ├─────┤              Phase 5: HW Test
                                    ├─────┤        Phase 6: Cert Package
```

**Total: ~14 weeks (3.5 months) from start to certification package.**

---

## Appendix A: FLUX-C Instruction Encoding

```
  15  14  13  12  11  10   9   8   7   6   5   4   3   2   1   0
 ┌───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┐
 │     OPCODE (6)      │              IMMEDIATE (10)                │
 └───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┴───┘
```

- **OPCODE** (bits [15:10]): 6 bits → 64 possible opcodes (43 used in full FLUX-C)
- **IMMEDIATE** (bits [9:0]): 10-bit signed or unsigned immediate
  - Used by `PUSH` for small constants (−512 to +511)
  - Unused by stack-only opcodes (DUP, SWAP, etc.)

## Appendix B: Constraint Example — Range Check

Check that `altitude` is in [0, 50000]:

```
PUSH 0          ; lo = 0
PUSH 50000      ; hi = 50000 (may need multi-word for large immediates)
LOAD            ; push test_value (altitude)
RANGE           ; → bool: 0 ≤ altitude ≤ 50000
ASSERT          ; fail if out of range
HALT            ; done
```

Stack trace:
```
Initial:  []
PUSH 0:   [0]
PUSH 50K: [0, 50000]
LOAD:     [0, 50000, altitude]
RANGE:    [1 or 0]           ← single comparison cycle
ASSERT:   []                  ← pass or halt with fail
HALT:     done
```

Gas consumed: 5 instructions (well within 65,535 limit).

---

*End of FPGA Implementation Plan. This document is a living artifact — version-controlled and updated as the design evolves.*
