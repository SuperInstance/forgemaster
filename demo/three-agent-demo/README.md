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

### Flags

| Flag | Description |
|------|-------------|
| `--verbose` | Show detailed per-agent thinking each tick |
| `--quick` | Run only 100 ticks (fast testing) |

```bash
# Quick test
python3 run_demo.py --quick

# Full run with agent dashboards
python3 run_demo.py --verbose

# Both
python3 run_demo.py --verbose --quick
```

### Make targets

```bash
make run     # run the full demo
make test    # run test suite
make clean   # remove __pycache__ and generated files
```

## What You'll See

### Normal output (every 10 ticks)

```
[TICK 0000] Caller: forgemaster | Max drift: 0.000000 | clean | Holonomy:✓ Laman:✓
  forgemaster     | drift: +0.000000 | tick: 1
  oracle1         | drift: -0.000000 | tick: 1
  kimi1           | drift: +0.000000 | tick: 1
[TICK 0010] Caller: forgemaster | Max drift: 0.000600 | 2 violations | Holonomy:✓ Laman:✓
  forgemaster     | drift: +0.001000 | tick: 11
  oracle1         | drift: -0.001500 | tick: 11
  kimi1           | drift: +0.002000 | tick: 11
  ⚠ VIOLATION: oracle1 min_clearance
  ⚠ VIOLATION: oracle1 min_fuel
```

### Verbose output (per-agent thinking)

```
[TICK 0050] Agent Dashboards:
  ⚒️  FORGEMASTER | drift:+0.000100 tick:51 caller:YES violations:3 total:12
      → constraint breach: oracle1 min_clearance
  🔮 ORACLE1     | drift:-0.000150 tick:51 holonomy:✓ laman:✓ edges:3
      → fleet time consensus: aligned
  ⚡ KIMI1       | drift:+0.000200 tick:51 gpu:640ops rooms:10 updates:3
      → processing 3 constraint updates from fleet
```

### Sunset/inheritance

```
>>> SUNSET: forgemaster retires → oracle1 inherits
[TICK 0310] Caller: oracle1 | Max drift: 0.000000 | clean | Holonomy:✓ Laman:✓
```

### Final summary

```
============================================================
DASHBOARD SUMMARY
============================================================
Ticks simulated:    1000
Max drift ever:     0.002000
Total violations:   47
============================================================

Final max drift: 0.002000
Drift bounded: YES ✓
Sunset/inheritance: completed ✓
Forge violations caught: 47

Demo complete.
```

Key things to watch:
- **Drift stays bounded** — Fraction arithmetic means no floating-point accumulation
- **Constraint violations caught** — Forgemaster flags them in real time
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
| `demo/constraints.json` | 25 aerospace constraints with real values |
| `demo/plato_tiles.db` | Seeded PLATO tile history (10 tiles) |

## Constraints

The 25 aerospace constraints live in `demo/constraints.json`. Example values:

| Parameter | Range | Unit |
|-----------|-------|------|
| Temperature | -54°C to 125°C | °C (mapped to engine_temp 846–1398 K) |
| Cabin Pressure | 0.1 to 10 bar (0.1–9.9 atm) | atm |
| Vibration | 0 to 20 g (limited to 5.0 g_rms for avionics) | g_rms |
| G-load | 0 to 9 g | g |
| Mach | 0 to 2.5 | — |
| Fuel | 5–100% | % |
| Visibility | 800+ m | m |

## Run Tests

```bash
python3 test_demo.py
```

Verifies: communication, drift bounding, election, sunset/inheritance, Tensor-MIDI encoding.
