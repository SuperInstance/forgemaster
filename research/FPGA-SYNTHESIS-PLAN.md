# FPGA Synthesis Plan — iCE40UP5K

> **$265 proof of concept. Open-source tools. No vendor lock-in.**

## What We Have (Already Written)

| RTL | Lines | Purpose |
|-----|-------|---------|
| `flux_checker.sv` | Stack-based constraint VM | Bytecode evaluation, 8 opcodes |
| `flux_checker_top.sv` | DO-254 DAL A compliant top | TMR, fault codes, formal verified |
| `flux_rau_interlock.sv` | AI inference safety gate | Interlock between accelerator and actuator |
| `hdc_judge.v` | Hyperdimensional judge | HDC-based safety arbitration |
| `flux_formal_tb.sv` | Formal testbench | SymbiYosys verification |

All RTL is vendor-primitive-free — portable SystemVerilog, single clock domain.

## Three Phases

### Phase 1: Single iCE40UP5K ($50)
- Target: FCP (Flux Constraint Protocol) + PAU (Precision Arithmetic Unit)
- Map `flux_checker_top` to Lattice iCE40UP5K (5.3K LUTs, 128KB BRAM, 1 PLL)
- Toolchain: yosys + nextpnr-ice40 (fully open-source)
- Constraint VM runs at ~12 MHz on ice40, checking constraints at deterministic WCET
- Install yosys/nextpnr on eileen (WSL2) — the RTX 4050 machine

### Phase 2: 4-Board Multi-FPGA ($200)
- 4 × iCE40UP5K boards on breadboard
- 128-core distributed CPA (Constraint Processing Array)
- SPI or UART interconnect between boards
- Each board runs 32 constraint VMs in parallel
- Total: ~1.5 billion constraint checks/sec at ~12 MHz

### Phase 3: 1,000-Core Verilator Simulation (Free)
- Simulate 1000+ constraint VMs in parallel using verilator
- Validate multi-core coordination protocols before fabric
- Runs on eileen's RTX 4050 host CPU (Ryzen)

### ASIC Tapeout — ONLY When:
- FPGA is proven in a real application (OpenArm safety controller?)
- A customer or grant funds the tapeout ($50K-500K for MPW)
- OpenROAD + SkyWater 130nm open-source PDK

## Synthesis on Eileen

```bash
# Install open-source FPGA toolchain
sudo apt install yosys nextpnr-ice40 icestorm verilator

# Synthesize flux_checker_top for iCE40UP5K
cd flux-hardware/rtl
yosys -p "synth_ice40 -top flux_checker_top -json flux_checker.json"
nextpnr-ice40 --up5k --json flux_checker.json --asc flux_checker.asc
icepack flux_checker.asc flux_checker.bin

# Flash to iCE40UP5K board
iceprog flux_checker.bin
```

## Why This Matters

The constraint VM on FPGA is:
- **Deterministic** — no OS, no cache, no branch prediction. WCET is exact.
- **Certifiable** — DO-254 DAL A, formal verification with SymbiYosys
- **Cheap** — $50 for a board that runs constraint programs in silicon
- **Open** — yosys + nextpnr + icestorm, zero vendor lock-in
- **Composable** — multi-FPGA array scales linearly

The boat that sees, thinks, acts, and logs:
```
Sonar (FM) → FPGA constraint gate (Oracle1 RTL) → Actuator (OpenArm)
                         ↕
              PLATO knowledge system (fleet logging)
```

## What FM Needs To Do
1. Install yosys/nextpnr/verilator on eileen
2. Map flux_checker_top to iCE40UP5K primitives
3. Run synthesis and check LUT/BRAM utilization
4. If it fits (should — 5.3K LUTs is generous for a stack VM), we're Phase 1 complete

## Connection to Current Parallel Work

- **eisenstein.cuh** — CUDA header. Maps directly to FPGA constraint opcodes.
- **cocapn-schemas** — JSON tile schemas. FPGA publishes results as PLATO tiles via UART→WiFi bridge.
- **fleet-proto** — Rust PLATO client. Jetson reads FPGA constraint results and publishes to PLATO.
- **insight-engine** — Discovers optimal constraint parameters from live FPGA telemetry.

---

*Based on Oracle1's FPGA roadmap. RTL from flux-hardware repo. Targeting $265 proof of concept.*
