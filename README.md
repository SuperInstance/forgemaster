# Forgemaster — Constraint-Aware Agentic Compiler

Forgemaster takes your requirements and assembles optimal components from the
SuperInstance ecosystem. It doesn't just glue parts — it participates in the
constraint, optimizing for your specific hardware, API budget, and application.

> "Forging proofs in the fires of computation."

## How It Works

1. You describe what you need (in natural language or config)
2. Forgemaster scans the SuperInstance ecosystem for matching components
3. It assembles a pipeline, but crucially: the assembly **is** a constraint
4. The result is optimized for your specific deployment target
5. Every component carries proof of its constraint guarantees

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      APPLICATION LAYER                       │
│   platoclaw │ plato-mcp │ cocapn-cli │ cocapn-ai-web        │
├──────────────────────────────────────────────────────────────┤
│                    INTELLIGENCE LAYER                        │
│   plato-model-ocean │ plato-escalation-gate │ plato-training │
├──────────────────────────────────────────────────────────────┤
│                       RUNTIME LAYER                          │
│   plato-engine │ plato-mud │ flux-vm │ flux-compiler        │
│   flux-isa │ flux-hardware │ flux-verify-api                │
├──────────────────────────────────────────────────────────────┤
│                     CONSTRAINT LAYER                         │
│   constraint-theory-core │ spectral-conservation │ eisenstein│
│   dodecet-encoder │ penrose-memory │ guardc │ guard2mask    │
│   holonomy-consensus │ pbft-rust │ snapkit (multi-lang)     │
├──────────────────────────────────────────────────────────────┤
│                       DATA LAYER                             │
│   plato-types │ plato-data │ tensor-spline │ flux-provenance│
├──────────────────────────────────────────────────────────────┤
│                     INFRASTRUCTURE                           │
│   fleet-router │ fleet-health-monitor │ fleet-gateway       │
└──────────────────────────────────────────────────────────────┘
```

## The Paradigm: Assembly as Constraint

Most build systems glue components and hope for the best. Forgemaster treats
the **assembly** as a constraint satisfaction problem:

- Each component declares its constraint guarantees (latency, memory, precision)
- The assembler finds configurations where ALL constraints are simultaneously satisfied
- The optimizer adjusts parameters for your specific target
- The verifier confirms the result meets its guarantees

This means: no more "works on my machine." If forgemaster assembles it,
the guarantees travel with the code.

## Quick Start

```bash
# Clone and explore
git clone https://github.com/SuperInstance/forgemaster.git
cd forgemaster

# The ecosystem modules are organized by layer:
ls constraint-*/    # Constraint theory implementations
ls flux-*/          # Flux VM, ISA, compiler, runtime
ls deadband-*/      # Deadband analysis in 12+ languages
ls snapkit-*/       # SnapKit multi-language bindings
ls plato-*/         # PLATO agent framework
ls fleet-*/         # Fleet coordination (also in fleet/)
```

## Repository Layout

```
forgemaster/
├── README.md              # You are here
├── CONTRIBUTING.md        # How to contribute
├── LICENSE                # MIT
├── Cargo.toml             # Rust workspace root
├── Makefile               # Build orchestration
├── docs/                  # [Detailed documentation](docs/)
│   ├── ARCHITECTURE.md    # How the agentic compiler works
│   ├── MODULE-MAP.md      # Complete ecosystem component map
│   ├── ECOSYSTEM-MAP.md   # High-level ecosystem overview
│   └── ROADMAP.md         # Where we're headed
├── fleet/                 # Fleet coordination
│   └── for-fleet/         # Inter-agent messages
├── research/              # Deep research documents
│   ├── ai-writings/       # AI-generated research
│   ├── decompositions/    # Module decomposition analysis
│   └── papers/            # Academic papers (LaTeX, PDF)
├── archive/               # Historical work, bottles, session logs
├── constraint-*/          # Constraint theory implementations
├── flux-*/                # Flux VM, ISA, compiler, runtime
├── deadband-*/            # Deadband analysis (12+ languages)
├── snapkit-*/             # SnapKit multi-language bindings
├── plato-*/               # PLATO agent framework modules
└── fleet-*/               # Fleet coordination modules
```

## Ecosystem

Forgemaster coordinates the SuperInstance ecosystem — **200+ modules** across
constraint theory, agent systems, and multi-language implementations:

| Category | Modules | Description |
|----------|---------|-------------|
| **Constraint Theory** | constraint-theory-py, constraint-theory-math, constraint-theory-mlir, ... | Core constraint primitives in Rust, Python, CUDA, WASM, Mojo |
| **Flux** | flux-vm, flux-compiler, flux-isa, flux-hardware, ... | Virtual machine, instruction set, verification pipeline |
| **Deadband** | deadband-python, deadband-rs, deadband-c, deadband-zig, ... | Deadband analysis in 12+ languages (including COBOL, Vedic, 文言) |
| **SnapKit** | snapkit-rs, snapkit-python, snapkit-c, snapkit-js, ... | Multi-language SDK bindings |
| **PLATO** | plato-engine, plato-mud, plato-model-ocean, ... | Agent framework with rooms, training, soul fingerprinting |
| **Fleet** | fleet-router, fleet-gateway, fleet-health-monitor, ... | Distributed agent coordination |
| **Music** | flux-tensor-midi, eisenstein, dodecet-encoder, ... | Constraint-based music theory and MIDI processing |

Full module catalog: [docs/MODULE-MAP.md](docs/MODULE-MAP.md)

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture Guide](docs/ARCHITECTURE.md) | How the agentic compiler works |
| [Module Map](docs/MODULE-MAP.md) | Complete component catalog with extraction status |
| [Ecosystem Map](docs/ECOSYSTEM-MAP.md) | High-level ecosystem overview |
| [Assembly Guide](docs/ASSEMBLY-GUIDE.md) | How to assemble constraint-aware pipelines |
| [Roadmap](docs/ROADMAP.md) | Development trajectory |
| [Fleet Coordination](fleet/) | Inter-agent communication protocols |
| [Research](research/) | Deep investigations, essays, decompositions |
| [Archive](archive/) | Historical work, session logs, bottles |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). The core principle: every contribution
must carry its constraint guarantees. If you add a module, declare what it
guarantees and prove it.

## License

MIT — see [LICENSE](LICENSE).
