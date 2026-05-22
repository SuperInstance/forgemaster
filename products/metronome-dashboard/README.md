# metronome-dashboard

Real-time terminal dashboard for fleet clock synchronization. Built with Rich and numpy.

## Why

When you're running a fleet of agents across machines, clock drift is silent killer #1. NTP says "synced" but you're 3ms off. PTP says "locked" but the grandmaster just flapped. You need eyes on the actual numbers, not happy-path status LEDs.

This dashboard gives you a live terminal view of every agent's offset, drift rate, state machine, and pairwise latency — no web server required.

## Install

```bash
pip install -e .
```

Requires Python 3.10+, numpy, rich.

## Commands

```bash
# Live dashboard (auto-refresh every second)
metronome-dashboard watch -n 10

# Protocol comparison reference
metronome-dashboard compare

# Fleet topology + latency heat map
metronome-dashboard topology -n 8

# Historical drift bar chart + sparklines
metronome-dashboard history -n 6
```

## How It Works

The simulator creates N agents, each with:
- A **true offset** from the master clock
- A **drift rate** (how fast it's wandering)
- **Jitter** on measurements (real sensors aren't perfect)
- A **state machine**: LOCKED → SYNCING → HOLDOVER → DRIFTING → OFFLINE

Every tick, each agent drifts naturally. Every correction interval, PTP-style correction steps the offset toward zero (configurable aggressiveness). The dashboard watches it all happen.

### Charts

| Chart | What it shows |
|-------|--------------|
| Sparkline | Drift over time per agent |
| Bar chart | Current offset per agent |
| Heat map | Pairwise latency matrix |

### State Machine

```
LOCKED    |offset| < 1μs     — nanosecond-grade sync
SYNCING   |offset| < 1ms     — converging
HOLDOVER  |offset| < 100ms   — lost master, coasting
DRIFTING  |offset| >= 100ms  — unsynced, diverging
OFFLINE                        — not running
```

## Demo

```bash
python examples/demo.py
```

Spins up 10 agents with random drift rates and runs a live dashboard. Ctrl+C to stop.

## Architecture

```
metronome_dashboard/
├── __init__.py        # version
├── cli.py             # Rich dashboard + commands
├── simulator.py       # Fleet simulator with PTP correction
└── charts.py          # ASCII/Rich chart renderers
```

No external services. No network. Pure local simulation with real math.

## License

MIT
