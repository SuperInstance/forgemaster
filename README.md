# Forgemaster — Constraint-Aware Agentic Compiler

> Clone me. Step into the forge.

Forgemaster takes your requirements and assembles optimal components from the fleet, respecting constraints, budgets, and safety requirements. It's an agentic compiler — you describe what you want, it figures out how to build it.

## What This Gives You

- **Requirement-driven assembly** — describe what you need, Forgemaster picks the components
- **Constraint enforcement** — respects resource budgets, safety constraints, and operational limits
- **Fleet plugin system** — integrates with every service in the Cocapn fleet
- **PLATO bridge** — connects to the PLATO educational framework for curriculum-aware compilation
- **Production-validated** — battle-tested with PTP clock synchronization experiments and heterogeneous fleet configurations
- **Docker-ready** — includes Dockerfile and Makefile for reproducible builds

## Quick Start

```bash
git clone https://github.com/SuperInstance/forgemaster.git (dead)
cd forgemaster
make setup
make run
```

```python
# Define what you want
requirements = {
    "task": "Build a health monitoring service",
    "constraints": {
        "max_memory_mb": 256,
        "latency_ms": 100,
        "languages": ["rust", "python"],
    }
}

# Forgemaster assembles the components
from forgemaster import Forge
forge = Forge()
build = forge.compile(requirements)
print(build.components)  # [HealthChecker, AlertEngine, Dashboard, ...]
print(build.plan)        # Execution plan with dependencies
```

## How It Fits

The compiler of the [SuperInstance fleet](https://github.com/SuperInstance). Takes high-level intent and produces executable fleet configurations.

- **[guard-constraints](https://github.com/SuperInstance/guard-constraints)** — Safety constraints fed into the forge
- **[cartridge-mcp](https://github.com/SuperInstance/cartridge-mcp)** — Swappable behavior cartridges
- **[agent-forge](https://github.com/SuperInstance/agent-forge)** — Universal agent framework
- **[captain](https://github.com/SuperInstance/captain)** — Fleet commanding

## Installation

```bash
git clone https://github.com/SuperInstance/forgemaster.git (dead)
cd forgemaster
make setup
```

Requires Python 3.10+ and Docker. MIT license.

## Documentation

📚 [OpenConstruct Docs](https://github.com/SuperInstance/openconstruct-docs)
