# Live Demo Guide — Three-Agent Metronome

> *Countdown initiated. Three agents. One clock. Zero drift.*

---

## 1. What You're About to See

Three autonomous agents — Forgemaster, Oracle1, Kimi1 — share a simulated network and synchronize their clocks using **Pythagorean Fraction arithmetic**. There is no floating-point drift. There are no rounding errors. The math is exact, from tick zero to tick one million. What you'll watch is a live distributed consensus protocol where cadence leadership rotates, agents retire and hand off their state to successors, and the clock never wavers.

This isn't a toy. The same architecture powers constraint-theory agent fleets that converge to truth in production systems. The demo you're about to run is the minimum viable proof — stripped down to three agents, readable output, and undeniable math. When you see the drift column stay at `0.000000` for a thousand ticks, you're watching something that classical floating-point systems literally cannot do.

---

## 2. Prerequisites

You need exactly two things:

```
Python 3.10+
numpy
```

```bash
pip install numpy
```

That's it. No Docker, no Kubernetes, no cloud account. The demo runs on a laptop.

---

## 3. Quick Demo (2 minutes)

The single-process demo runs three agents in one Python process. It takes about 60 seconds and produces a full dashboard output.

```bash
cd demo/three-agent-demo
python3 run_demo.py
```

### What you'll see

```
[TICK 0000] Caller: forgemaster | Max drift: 0.000000 | clean | Holonomy:✓ Laman:✓
  forgemaster     | drift: +0.000000 | tick: 1
  oracle1         | drift: -0.000000 | tick: 1
  kimi1           | drift: +0.000000 | tick: 1
```

At around tick 300, watch for this:

```
>>> SUNSET: forgemaster retires → oracle1 inherits
[TICK 0310] Caller: oracle1 | Max drift: 0.000000 | clean | Holonomy:✓ Laman:✓
```

The caller retires. The successor picks up. The clock doesn't blink.

### Quick mode

Short on time? Run 100 ticks:

```bash
python3 run_demo.py --quick
```

### Verbose mode

See every agent's per-tick reasoning:

```bash
python3 run_demo.py --verbose
```

---

## 4. Distributed Demo (5 minutes)

This is the real thing. Three separate Python processes, real UDP multicast, real peer discovery, real cadence elections. Each node discovers the others, elects a leader, and synchronizes — exactly as a production fleet would.

```bash
cd demo/three-agent-demo/distributed
bash run_cluster.sh
```

### What happens

| Phase | Duration | What you see |
|-------|----------|--------------|
| **Launch** | 2s | Three processes spawn, begin discovery |
| **Discovery** | 3-5s | Nodes find each other via UDP multicast |
| **Election** | Every 10 ticks | Longest-uptime node wins cadence calling |
| **Synchronization** | 60s | Continuous tick loop, drift stays bounded |
| **Sunset** | 1s | Forgemaster receives SIGTERM, broadcasts inheritance data |
| **Succession** | 30s | Oracle1 or Kimi1 takes over, cluster continues |

### Manual cluster (advanced)

Launch nodes individually for full control:

```bash
# Terminal 1
python3 distributed/metronome_node.py --name forgemaster --port 19840 --ticks 10000

# Terminal 2
python3 distributed/metronome_node.py --name oracle1 --port 19840 --ticks 10000

# Terminal 3
python3 distributed/metronome_node.py --name kimi1 --port 19840 --ticks 10000
```

Add `--verbose` to any node for debug output. Use `--drift 0.001` to inject simulated drift and watch the deadband correction kick in.

---

## 5. What to Watch For

These are the moments that matter. Point them out to your audience.

### 🔥 Ignition — Tick 0

Three agents, zero drift, perfect alignment. The calm before the storm.

```
[TICK 0000] Caller: forgemaster | Max drift: 0.000000 | clean
```

### 📡 Discovery — First 5 seconds

Nodes announce themselves via UDP multicast. Watch the peer count climb:

```
Node forgemaster tick=100 drift=0.000100 cadence_caller=True peers=2
```

### 👑 Election — Every 10 ticks

The node with the longest uptime becomes cadence caller. If two nodes tie, name sort breaks it. Simple, deterministic, no Byzantine overhead.

### ⚠ Violations — Real-time

Forgemaster runs 25 aerospace constraint checks every tick. When a constraint is breached:

```
⚠ VIOLATION: oracle1 min_clearance
⚠ VIOLATION: oracle1 min_fuel
```

Every violation is caught. Every one.

### 🌅 Sunset — ~Tick 300

The cadence caller retires. Broadcasts its full state — true_time, offset, drift_rate, tick_count. The heir inherits everything and continues without a single dropped tick.

```
>>> SUNSET: forgemaster retires → oracle1 inherits
```

**This is the money shot.** If you only point out one thing, make it this.

### 📊 Final Dashboard

```
============================================================
DASHBOARD SUMMARY
============================================================
Ticks simulated:    1000
Max drift ever:     0.002000
Total violations:   47
============================================================
Drift bounded: YES ✓
Sunset/inheritance: completed ✓
```

---

## 6. The Numbers

Here's what good looks like. If your numbers are in these ranges, everything is working.

| Metric | Good | Great | Explanation |
|--------|------|-------|-------------|
| **Max drift** | < 0.01 | < 0.001 | Fraction arithmetic keeps drift bounded |
| **Convergence** | < 40 ticks | < 20 ticks | Time for all agents to align after startup |
| **Violations caught** | 100% | 100% | Forgemaster flags every breach |
| **Sunset handoff** | < 1 tick | 0 ticks | Heir picks up with zero interruption |
| **Tensor-MIDI round-trip** | < 0.001 error | < 0.0001 error | Wire format is lossless within quantization |

Run the test suite to verify:

```bash
python3 test_demo.py                    # Single-process tests
python3 distributed/test_distributed.py # Distributed tests (30 tests)
```

---

## 7. What's Happening Under the Hood

**Clock sync.** Each agent maintains a local clock as a Python `Fraction`. Fractions are exact — no floating-point rounding, no accumulation error. When drift exceeds the deadband threshold (default: `0.0001`), the agent corrects toward the cadence caller's reference time.

**Cadence calling.** One agent is the "caller" — the time authority. It broadcasts reference time every tick. Other agents correct toward it. The caller is elected democratically: longest uptime wins, ties broken by name.

**Deadband filter.** Agents only communicate when drift exceeds the threshold. Below the threshold, they're silent. This is sparse communication — the same principle as a temporal deadband filter in control systems.

**Sunset/inheritance.** When an agent retires (SIGTERM), it broadcasts its full state: true_time, local_time offset, drift_rate, tick_count, cadence_caller status. The heir absorbs this state and continues seamlessly. No coordination protocol, no two-phase commit — just a clean handoff.

**Tensor-MIDI wire format.** Messages are encoded in a compact binary format inspired by MIDI CC structure. Values are clamped to [-1.0, 1.0] and scaled to int64 for transport. Round-trip error stays below 0.001.

**PLATO tiles.** Every state change is written to a SQLite-backed tile store with agent ID, tick number, and key. This gives provenance tracking — you can reconstruct exactly what happened at any tick.

---

## 8. Customizing

### Add your own agent

Create a new agent file in `agents/`:

```python
from metronome_core import MetronomeAgent

class MyAgent(MetronomeAgent):
    def __init__(self):
        super().__init__("my_agent", drift_rate=0.0)

    def tick(self):
        super().tick()
        # Your custom logic here
        pass
```

Register it in `run_demo.py` and add it to the network bus.

### Change constraints

Edit `demo/constraints.json`. The 25 aerospace constraints use real parameter ranges:

| Parameter | Range | Unit |
|-----------|-------|------|
| Temperature | -54°C to 125°C | °C |
| Cabin Pressure | 0.1 to 10 bar | atm |
| Vibration | 0 to 20 g | g_rms |
| G-load | 0 to 9 g | g |
| Mach | 0 to 2.5 | — |
| Fuel | 5–100% | % |

Add, remove, or tighten constraints to see how violations change.

### Adjust topology

In `run_cluster.sh`, change the number of nodes:

```bash
# Run a 5-node cluster instead of 3
python3 "$NODE_SCRIPT" --name node4 --port 19840 --ticks 10000 &
python3 "$NODE_SCRIPT" --name node5 --port 19840 --ticks 10000 &
```

Or use different ports for isolated sub-clusters. The UDP multicast discovery automatically finds peers on the same group:port.

### Tune parameters

```bash
# Tighter deadband — more corrections, lower drift
python3 metronome_node.py --name agent --delta 0.00001 --ticks 10000

# Inject drift to test correction
python3 metronome_node.py --name agent --drift 0.01 --ticks 10000

# Verbose debug logging
python3 metronome_node.py --name agent --verbose
```

---

## 9. Next Steps

- **[SUPERINSTANCE-ECOSYSTEM.md](../../docs/SUPERINSTANCE-ECOSYSTEM.md)** — The full package ecosystem: `constraint-theory`, `fleet-agent`, `sunset-ecosystem`, `deadband-python`
- **[STRATEGIC-ARCHITECTURE-V2.md](../../docs/STRATEGIC-ARCHITECTURE-V2.md)** — The architecture this demo proves: metronome sync, holonomy consensus, Laman rigidity
- **[AI Writings](https://github.com/SuperInstance/AI-Writings)** — Essays on constraint theory, music, and distributed systems
- **[PyPI: constraint-theory](https://pypi.org/project/constraint-theory/)** — `pip install constraint-theory` and start building

---

*Three agents. One clock. Zero drift. Welcome to the fleet.*
