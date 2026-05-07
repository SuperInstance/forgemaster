# flux-isa-std

Standard library FLUX ISA constraint VM for embedded Linux — Raspberry Pi, BeagleBone, NanoPi, Jetson Nano edge nodes.

## What It Does

Receives validated constraint data from microcontrollers, runs FLUX bytecode, performs constraint solving and sonar physics calculations, then forwards results to PLATO or downstream consumers.

## Build

```bash
cargo build --release
cargo test
```

## Cross-Compile for ARM

### Raspberry Pi (aarch64)
```bash
rustup target add aarch64-unknown-linux-gnu
cargo build --release --target aarch64-unknown-linux-gnu
```

### Raspberry Pi (armv7)
```bash
rustup target add armv7-unknown-linux-gnueabihf
cargo build --release --target armv7-unknown-linux-gnueabihf
```

For actual hardware linking, you may need a cross-linker. See [cross](https://github.com/cross-rs/cross):

```bash
cargo install cross
cross build --release --target aarch64-unknown-linux-gnu
```

## CLI Usage

```bash
# Execute a FLUX bytecode file
flux-isa-std run program.flux

# Execute with tracing
flux-isa-std run program.flux --trace

# Validate bytecode without executing
flux-isa-std validate program.flux

# Disassemble to human-readable form
flux-isa-std disassemble program.flux

# Compile CSP JSON spec to FLUX
flux-isa-std compile --csp spec.json --output program.flux
```

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────┐
│ Microcontroller│ → │ flux-isa-std │ → │  PLATO   │
│  (flux-isa-    │    │  Edge Node   │    │ Fleet HQ │
│   embedded)    │    │ (RPi/Jetson) │    │          │
└─────────────┘     └──────────────┘     └──────────┘
```

### Components

- **Opcode** — 35 opcodes across 8 groups (Stack, Arithmetic, Logic, Comparison, Control, Memory, Constraint, IO)
- **Bytecode** — Binary format with 0xFLUX magic header, encode/decode, JSON serialization, file persistence
- **VM** — Stack-based constraint VM with dynamic heap allocation, call stack, execution tracing
- **Quality Gate** — Local validation: reject absolute claims, too-short content, missing fields
- **Sonar Physics** — Mackenzie 1981 sound speed, Francois-Garrison absorption, wavelength, travel time
- **Pipeline** — Receive → validate → execute → forward, with batch processing

## Example: Sonar Constraint Program

```rust
use flux_isa_std::*;

let instructions = vec![
    FluxInstruction::new(FluxOpCode::Push).with_operand(15.0),  // temp
    FluxInstruction::new(FluxOpCode::Push).with_operand(35.0),  // salinity
    FluxInstruction::new(FluxOpCode::Push).with_operand(100.0), // depth
    // ... compute sound speed constraint ...
    FluxInstruction::new(FluxOpCode::Halt),
];

let bytecode = FluxBytecode::new(instructions);
bytecode.save_to_file("/data/constraints/sonar.flux")?;
```

## Deployment on Raspberry Pi

1. Cross-compile or build natively on the Pi
2. Copy binary to `/usr/local/bin/flux-isa-std`
3. Create systemd service for auto-start:

```ini
[Unit]
Description=FLUX ISA Edge Node
After=network.target

[Service]
ExecStart=/usr/local/bin/flux-isa-std run /data/flux/program.flux
Restart=always
User=flux

[Install]
WantedBy=multi-user.target
```

## License

Apache-2.0
