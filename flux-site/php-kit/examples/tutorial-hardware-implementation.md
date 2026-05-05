# Hardware Implementation — From Bytecode to Silicon

## The Promise: Constraints in Hardware

Software constraints run on general-purpose CPUs. They share memory, bus bandwidth, and cache with the AI model they're guarding. When the model goes wrong, it can corrupt the very guard that's supposed to catch it.

FLUX constraints can be implemented directly in hardware. The constraint VM becomes a **Runtime Assurance Unit (RAU)** — a dedicated circuit that checks AI outputs before they reach actuators, with zero software involvement.

## The Numbers

Synthesized on a Xilinx Artix-7 (XC7A100T):

| Metric | Value |
|--------|-------|
| LUTs | 44,243 (69% of device) |
| Flip-flops | 18,201 (28%) |
| BRAM | 12 (9%) |
| Clock | 100 MHz |
| Power | 2.58W |
| Latency | 0 cycles (combinational check) |
| Fault detection | 1 cycle |

### What "Zero Latency" Means

The constraint check happens **during the same clock cycle** as the AI output. The RAU sits between the AI accelerator and the actuator bus. Every output passes through the RAU's combinational logic. If the output violates a constraint, the RAU blocks it within one clock cycle.

There is no "check, then act." The check IS the action. The output either satisfies the constraint (passes through) or doesn't (blocked). No software involved.

## The RAU Interlock (flux_rau_interlock.sv)

The core hardware module is a 6-state finite state machine:

```
         ┌──────────┐
    ┌───►│   IDLE   │◄──────────────┐
    │    └────┬─────┘               │
    │         │ start               │
    │    ┌────▼─────┐               │
    │    │  FETCH   │               │
    │    └────┬─────┘               │
    │         │ instruction ready    │
    │    ┌────▼─────┐               │
    │    │  DECODE  │               │
    │    └────┬─────┘               │
    │         │                     │
    │    ┌────▼─────┐    fault      │
    │    │ EXECUTE  ├──────────────►│
    │    └────┬─────┘               │
    │    pass │                     │
    │    ┌────▼─────┐               │
    │    │  HALT    ├───────────────┘
    │    └──────────┘               │
    │         │                     │
    │    ┌────▼─────┐               │
    └────┤  FAULT   ├───────────────┘
         └──────────┘
```

States:
1. **IDLE** — waiting for constraint check request
2. **FETCH** — loading next bytecode instruction
3. **DECODE** — decoding opcode and operands
4. **EXECUTE** — running the instruction (ALU + stack)
5. **HALT** — constraint passed, output released
6. **FAULT** — constraint violated, output blocked

The fault state is **absorbing** — once entered, only a hardware reset can exit. This is the latching behavior required by DO-254.

## AXI4-Lite Register Interface

The RAU exposes its state via AXI4-Lite registers:

| Register | Offset | R/W | Purpose |
|----------|--------|-----|---------|
| STATUS | 0x00 | R | Current FSM state |
| CONTROL | 0x04 | W | Start check, reset fault |
| BYTECODE_BASE | 0x08 | R/W | Pointer to constraint bytecode |
| INPUT_VALUE | 0x0C | R/W | Value to check |
| RESULT | 0x10 | R | PASS/FAULT + fault code |
| GAS_REMAINING | 0x14 | R | Gas counter |
| CYCLE_COUNT | 0x18 | R | Execution cycle counter |

Integration with any SoC is straightforward: map the RAU registers into the processor's address space, write the bytecode pointer and input value, set CONTROL[start], poll STATUS until HALT or FAULT.

## From GUARD to Silicon: The Full Flow

```
GUARD source                 Bytecode                 FPGA bitstream
┌──────────────┐      ┌──────────────┐      ┌──────────────────┐
│ constraint   │      │ 1D 00 96     │      │ ┌──────────────┐ │
│   alt {      │─────►│ 1B           │─────►│ │  RAU FSM     │ │
│   range(     │      │ 1A           │      │ │  + stack     │ │
│     0, 150)  │      │ 20           │      │ │  + ALU       │ │
│   }          │      └──────────────┘      │ │  + fault     │ │
└──────────────┘   guard2mask compiler      │ │    handler   │ │
                                            │ └──────────────┘ │
                                            └──────────────────┘
                                            Vivado synthesis
```

1. Engineer writes GUARD constraint
2. `guard2mask` compiles to FLUX-C bytecode
3. Bytecode is loaded into RAU's instruction memory
4. Vivado synthesizes the RAU + interconnect
5. Bitstream is loaded onto FPGA
6. Every AI output passes through the RAU

## ASIC Floorplan (Projected)

For production volumes, an ASIC implementation is projected:

| Parameter | Value |
|-----------|-------|
| Process | 22nm FDSOI |
| Die area | 12.7 mm² |
| Power | 0.8W (active), 0.02W (idle) |
| Clock | 500 MHz |
| Pin count | 144 (BGA) |
| Cost (10K units) | ~$3.20 per chip |

The constraint checker occupies 12.7mm² — smaller than a typical SRAM block. It can be integrated as an IP block in any SoC design.

## FPGA Development Setup

### Prerequisites

```bash
# Install Vivado (Xilinx)
# Install SymbiYosys for formal verification
pip install sby

# Install Icarus Verilog for simulation
apt install iverilog
```

### Simulation

```bash
# Run the testbench (9 self-checking tests)
cd flux-hardware/rtl/
iverilog -o flux_tb \
  flux_rau_interlock.sv \
  flux_rau_interlock_tb.sv
vvp flux_tb
# → All 9 tests pass
```

### Formal Verification

```bash
# SymbiYosys: prove FSM properties
cd flux-hardware/formal/
sby run flux_verify.sby
# → PASS: 7 assertions, 6 covers
```

### Synthesis (requires Vivado)

```tcl
# In Vivado TCL console
create_project flux_rau ./build -part xc7a100tcsg324-1
add_files [glob ../rtl/*.sv]
synth_design -top flux_rau_interlock -part xc7a100tcsg324-1
report_utilization -file utilization.rpt
report_timing -file timing.rpt
```

## The GUARD-to-Mask Compiler (Rust)

```rust
use guard2mask::{Parser, Compiler};

// Parse GUARD constraint
let source = r#"
    constraint alt @priority(HARD) {
        range(0, 150)
        thermal(5.0)
    }
"#;

let constraint = Parser::parse(source)?;
let bytecode = Compiler::compile(&constraint)?;

// bytecode = [1D 00 96 1B 00 05 24 1B 1A 20]
// 10 bytes, 5 instructions
```

## Next

- [Temporal Constraints](/learn/temporal) — time-aware safety
- [Security Primitives](/learn/security) — capability-based access control
- [Formal Verification](/learn/formal) — proving correctness
- [Safe-TOPS/W Benchmark](/benchmark) — comparing certified hardware
