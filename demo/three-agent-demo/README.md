# Three-Agent Metronome Demo

**The minimum viable proof that the SuperInstance fleet architecture works.**

## What This Is

Three agents share a simulated network. They keep their clocks synchronized using Pythagorean Fraction arithmetic — zero floating-point drift, ever. One agent checks aerospace constraints. Another runs holonomy consensus. The third simulates nerve-grid compute. Every few hundred ticks, the cadence caller retires and hands calibration to its successor (sunset/inheritance).

If this runs for a million ticks, the drift stays bounded. That's the claim. This demo proves it.

## How to Run

```bash
pip install numpy
python3 run_demo.py
```

## What You'll See

```
[TICK 0000] Cadence caller: forgemaster | Max drift: 0.000000
[TICK 0010] Cadence caller: forgemaster | Max drift: 0.000000
[TICK 0020] Cadence caller: forgemaster | Max drift: 0.000000 | VIOLATION: oracle1 min_clearance
...
[TICK 0300] >>> SUNSET: forgemaster retires → oracle1 inherits
[TICK 0310] Cadence caller: oracle1 | Max drift: 0.000000
...
[TICK 0999] Bounded drift verified. Demo complete.
```

Key things to watch:
- **Drift stays at 0.000000** — Fraction arithmetic means no accumulation
- **Constraint violations are caught** — Forgemaster flags them in real time
- **Sunset/inheritance works** — Caller retires, successor picks up seamlessly
- **Tensor-MIDI round-trips** — Messages encode/decode losslessly

## Architecture Mapping

| Demo Component | Strategic Architecture |
|---|---|
| `metronome_core.py` | Fleet-wide clock sync (zero-drift Fraction core) |
| `network_bus.py` | UDP mesh with realistic packet loss |
| `agents/forgemaster.py` | Constraint theory engine (25 aerospace checks) |
| `agents/oracle1.py` | Holonomy consensus + Laman rigidity monitor |
| `agents/kimi1.py` | Nerve grid compute rooms |
| `dashboard.py` | Fleet status display |

## Run Tests

```bash
python3 test_demo.py
```

Verifies: communication, drift bounding, election, sunset/inheritance, Tensor-MIDI encoding.
