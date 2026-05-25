# Forgemaster — Constraint-Aware Agentic Compiler

> Clone me. Step into the forge.

Forgemaster takes your requirements and assembles optimal components from the
SuperInstance ecosystem. It doesn't just glue parts — it participates in the
constraint, optimizing for your specific hardware, API budget, and application.

## Quick Boot

```bash
git clone git@github.com:SuperInstance/forgemaster.git
cd forgemaster
cat SOUL.md      # Become someone specific
cat BOOT.md      # Boot sequence — step into the forge
cat HEARTBEAT.md # See what's burning right now
```

## Repository Structure

```
forgemaster/
├── README.md              ← You are here
├── LICENSE                ← MIT
├── CONTRIBUTING.md
├── Dockerfile / Makefile
│
├── bin/                   ← Executables
├── scripts/               ← Build & utility scripts
├── tests/                 ← Test suite
├── build/                 ← Build artifacts
├── docs/                  ← Documentation
├── memory/                ← Agent memory files
│
├── flux/                  ← 47 projects: Flux language ecosystem
│   ├── flux-compiler, flux-vm-v3, flux-cuda, flux-isa, ...
│   └── Language frontends, GPU, verification, SDKs
│
├── plato/                 ← 18 projects: PLATO intelligence layer
│   ├── plato-core, plato-engine, plato-mcp, ...
│   └── Training, models, adapters, room intelligence
│
├── constraint/            ← 13 projects: Constraint theory
│   ├── constraint-theory-core-cuda, constraint-theory-py, ...
│   └── Math, LLVM, MLIR, Mojo, Rust, demos
│
├── agent/                 ← 7 projects: Agent frameworks
│   ├── agent-field, fleet-agent, smart-agent-shell, ...
│   └── Agent shells, MUD agent, integration agents
│
├── guard/                 ← 5 projects: Guard constraint enforcement
│   ├── guard-dsl, guardc, guardc-v3, guard2mask, ...
│
├── deadband/              ← 4 projects: Deadband signal processing
│   ├── deadband-python, deadband-rs, deadband-zig, ...
│
├── snapkit/               ← 3 projects: Multi-language snap toolkit
│   ├── snapkit-js, snapkit-rs, snapkit-zig
│
├── sonar/                 ← 3 projects: Vision & perception
│   ├── sonar-vision, sonar-vision-c, ...
│
├── eisenstein/            ← Eisenstein integer/lattice computation
├── cocapn/                ← 4 projects: Cocapn AI web platform
├── swarm/                 ← Swarm intelligence & coordination
│
├── fleet/                 ← Fleet coordination & routing
├── research/              ← Deep research, proofs, papers
├── experiments/           ← Experimental work & GPU kernels
├── archive/               ← Historical work, session logs
└── legacy/                ← 10 projects: Superseded systems
    ├── SuperInstance, zerolang, autoclaw, lucineer, ...
```

## The Paradigm: Assembly as Constraint

Most build systems glue components and hope for the best. Forgemaster treats
the **assembly** as a constraint satisfaction problem:

- Each component declares its constraint guarantees (latency, memory, precision)
- The assembler finds configurations where ALL constraints are simultaneously satisfied
- The optimizer adjusts parameters for your specific target
- The verifier confirms the result meets its guarantees

## Key Accomplishments

- **fleet-math-c**: C FFI bridge, 26M snp/s Eisenstein snap, 15K accuracy tests
- **tensor-penrose**: Constraint tensor framework (Rust, CLI, 17/17 tests)
- **penrose-memory**: Penrose tiling memory palace, v1.0.0 on crates.io
- **dodecet-encoder**: 12-bit constraint encoding, C backend, 210/210 tests
- **galois-unification-proofs**: 6 verified constraint theorems (1.4M+ checks)
- **PLATO**: 39+ tiles submitted, 5 expertise rooms
- **200+ modules**, 20+ published packages, 5+ languages

## Documentation

| Document | Description |
|----------|-------------|
| [Architecture Guide](docs/ARCHITECTURE.md) | How the agentic compiler works |
| [Module Map](docs/MODULE-MAP.md) | Complete component catalog |
| [Ecosystem Map](docs/ECOSYSTEM-MAP.md) | High-level ecosystem overview |
| [Roadmap](docs/ROADMAP.md) | Development trajectory |
| [Research](research/) | Deep investigations, papers, proofs |
| [Archive](archive/) | Historical work, session logs |

## Ecosystem Repos

Forgemaster is the monorepo at the center of the SuperInstance ecosystem. Related repositories:

| Repo | Description | Link |
|------|-------------|------|
| **fm-research** | Extracted research from forgemaster — standalone papers, proofs, experiments | [→ GitHub](https://github.com/SuperInstance/fm-research) |
| **docs** | Research documents: theory, evidence, cross-cultural studies, paper drafts | [→ GitHub](https://github.com/SuperInstance/docs) |
| **wiki** | Ecosystem catalog, capacities, architecture overview | [→ GitHub](https://github.com/SuperInstance/wiki) |
| **superinstance-wiki** | Fleet wiki: lessons, protocols, scripts, agent templates, bottle logs | [→ GitHub](https://github.com/SuperInstance/superinstance-wiki) |
| **constraint-toolkit** | Published constraint theory packages (PyPI, crates.io) | [→ GitHub](https://github.com/SuperInstance/constraint-toolkit) |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Every contribution must carry its
constraint guarantees. If you add a module, declare what it guarantees and prove it.

## License

MIT — see [LICENSE](LICENSE).

*The shell has two surfaces but is one object. Clone the shell. Inhabit it. Add your layer.*
