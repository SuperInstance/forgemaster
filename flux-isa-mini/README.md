# flux-isa-mini

Minimal `no_std` FLUX ISA constraint VM for bare-metal ARM Cortex-M microcontrollers.

Sensor nodes running sonar arrays validate constraint checks locally — on the metal — before forwarding data upstream. No OS. No allocator. No safety net.

## Why `no_std`?

Because your sensor node has **8KB SRAM** and doesn't run Linux.

- **Stack VM**: 32 × f64 = 256 bytes. Fits in a single Cortex-M stack frame.
- **Fixed instruction buffer**: Max 64 instructions × 24 bytes = 1.5KB.
- **Zero heap allocation**: No `Vec`, no `String`, no `Box`. Everything is stack or static.
- **Const-evaluated bounds**: Sonar constraints are checked against pre-computed Mackenzie limits, not computed at runtime.

Total memory footprint: **~2KB** for a typical constraint program.

## Memory Layout

```
┌──────────────────────┐ 0x2000_0000 (SRAM base)
│  .bss / .data        │
├──────────────────────┤
│  FluxVm stack [256B] │  32 × f64
│  Instruction buf     │  up to 64 × 24B = 1536B
│  Output buffer [64B] │  8 × f64
├──────────────────────┤
│  Stack (Cortex-M)    │  ~1KB remaining for call frames
└──────────────────────┘
```

## Supported Targets

| Target | Core | SRAM typical |
|--------|------|-------------|
| `thumbv6m-none-eabi` | Cortex-M0+ | 4–8 KB |
| `thumbv7em-none-eabi` | Cortex-M4F | 32–256 KB |
| `thumbv7m-none-eabi` | Cortex-M3 | 16–64 KB |

## Opcodes (21 of 35)

```
Arithmetic:  ADD SUB MUL DIV MOD
Comparison:  EQ  LT  GT  LTE GTE
Constraint:  ASSERT CHECK VALIDATE REJECT
Stack:       LOAD PUSH POP
Transform:   SNAP QUANTIZE
Control:     HALT NOP
```

## Quick Start

```rust
use flux_isa_mini::{FluxOpcode, FluxInstruction, FluxVm};

let mut vm = FluxVm::new();

// Validate depth is in [0, 200m]
let program = [
    FluxInstruction::new(FluxOpcode::Load, 45.3, 0.0),   // push measured depth
    FluxInstruction::new(FluxOpcode::Load, 0.0, 0.0),    // lower bound
    FluxInstruction::new(FluxOpcode::Load, 200.0, 0.0),  // upper bound
    FluxInstruction::new(FluxOpcode::Validate, 0.0, 0.0),
    FluxInstruction::new(FluxOpcode::Assert, 0.0, 0.0),
    FluxInstruction::new(FluxOpcode::Halt, 0.0, 0.0),
];

let result = vm.execute(&program).unwrap();
assert!(result.constraints_satisfied);
```

## Wire Format

```
[0x46 0x4C] [count:u16 LE] [instruction₀][instruction₁]...
   magic      2 bytes           24 bytes each
```

Zero-copy decode — cast the buffer directly as `&[FluxInstruction]`.

## Sonar Constraint Checks

Pre-built const-evaluated checks for common sonar validation:

- `check_sound_speed(c, min, max)` — validate against Mackenzie bounds
- `check_depth_pressure(depth, max_depth)` — depth safety
- `check_frequency_range(freq_khz)` — valid sonar frequency

These don't compute — they validate. The MCU just checks a number is in range.

## License

Apache-2.0
