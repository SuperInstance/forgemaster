# SuperInstance Ecosystem

> Constraint-theoretic agent fleets that converge to truth.

## Quick Start (30 seconds)

```bash
pip install constraint-theory
```

```python
from constraint_theory import TemporalAgent, snap

# Create an agent that observes a time series
agent = TemporalAgent(name="demo", tolerance=0.1)
agent.observe(1.0)
agent.observe(1.05)
agent.observe(1.1)
anomalies = agent.detect_anomalies()
print(f"Anomalies: {anomalies}")

# Snap two agents together (Eisenstein lattice)
from constraint_theory import encode, decode
token = encode(agent.state)
restored = decode(token)
```

## What Is This?

SuperInstance is a collection of packages for building agent fleets — groups of AI agents that:
- **Stay in sync** using metronome architecture (zero-drift Pythagorean arithmetic)
- **Communicate efficiently** — only when drift exceeds a threshold (deadband filter)
- **Verify each other** — constraint-theory checks at every tick
- **Remember what they learn** — PLATO tiles with provenance tracking
- **Retire gracefully** — sunset lifecycle with knowledge inheritance

## Core Packages

| Package | What It Does | Install |
|---------|-------------|---------|
| [constraint-theory](https://pypi.org/project/constraint-theory/) | Constraint specification and checking | `pip install constraint-theory` |
| [fleet-agent](https://pypi.org/project/fleet-agent/) | Agent base class with holonomy consensus | `pip install fleet-agent` |
| [sunset-ecosystem](https://pypi.org/project/sunset-ecosystem/) | Agent lifecycle (shell → active → sunset) | `pip install sunset-ecosystem` |
| [deadband-python](https://github.com/SuperInstance/deadband-rs) | Temporal deadband filter for sparse communication | `pip install deadband-python` |

## Rust Crates

| Crate | What It Does |
|-------|-------------|
| superinstance-ffi | Unified FFI bridge (C/Python/Zig/Go) |
| flux-ffi | FLUX VM FFI bindings |
| fleet-math-c | Fleet math (C-compatible) |
| snapkit-rs | Snapshot toolkit |

## The Architecture

Read [STRATEGIC-ARCHITECTURE-V2.md](STRATEGIC-ARCHITECTURE-V2.md) for the full picture.
Run [demo/three-agent-demo/](../demo/three-agent-demo/) to see it in action.

## 3-Agent Demo

```bash
git clone https://github.com/SuperInstance/forgemaster
cd forgemaster/demo/three-agent-demo
pip install numpy
python3 run_demo.py
```

Watch 3 agents coordinate for 1000 ticks with bounded drift, cadence calling, and one sunset/inheritance cycle.

## Learn More

- [AI Writings](https://github.com/SuperInstance/AI-Writings) — Essays on constraint theory, music, and distributed systems
- [Grand Synthesis](https://github.com/SuperInstance/grand-synthesis) — Multi-model architecture competition
- [Strategic Architecture](https://github.com/SuperInstance/forgemaster/blob/main/docs/STRATEGIC-ARCHITECTURE-V2.md)

## License

MIT / Apache 2.0 (varies by package)
