# SuperInstance Getting Started Guide

## TL;DR
Get a full SuperInstance stack running in four quick steps (three core commands):
1. Clone the official SuperInstance repository: `git clone https://github.com/superinstance-io/superinstance.git && cd superinstance`
2. Install all core Python packages: `pip install constraint-theory fleet-agent sunset-ecosystem deadband-python`
3. Install Rust FFI and low-level crates: `cargo add superinstance-ffi flux-ffi fleet-math-c snapkit-rs`
4. Run the reference 3-agent demo: `cd demo/three-agent-demo && python run_demo.py`

For Node.js users, install early-access bindings with:
```bash
npm install @superinstance/core @superinstance/agent
```

---

## Installation Troubleshooting

### Supported Versions
SuperInstance requires **Python 3.10 or newer**, **Rust 1.75.0 or newer** (for compiled crates), and **Node.js 18+** (for JavaScript bindings). Verify your tools:
```bash
python --version   # 3.10+
rustc --version   # 1.75.0+
node --version     # 18+
```

### Virtual Environment Setup
Always isolate dependencies to avoid version conflicts:
```bash
# Linux/macOS/WSL
python -m venv superinstance-env
source superinstance-env/bin/activate

# Windows PowerShell
python -m venv superinstance-env
.\superinstance-env\Scripts\Activate.ps1
```
Once activated, your prompt shows `(superinstance-env)` — all pip installs should run inside this env.

### Common Install Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `Permission denied` on pip install | System Python | Use a virtual env, or `pip install --user constraint-theory` |
| `cargo build failed: missing trait` | Old Rust toolchain | `rustup update` then retry |
| `npm ERESOLVE` conflict | Node < 18 | `nvm use 18` or update package.json engines |
| Linker errors on Rust crate | Missing build tools | Ubuntu: `sudo apt install build-essential`, macOS: `xcode-select --install` |
| `pip install` still fails | Corrupted cache | `pip cache purge && pip install --no-cache-dir constraint-theory` |

If installing from source, clone the repo and run `maturin develop` to build Rust bindings locally.

---

## What is SuperInstance?
SuperInstance is an open-source, cross-language ecosystem for building distributed, low-drift, coordinated autonomous agent fleets. Designed for use cases like drone swarms, industrial robot teams, and distributed sensor networks, it provides pre-built, battle-tested tools for clock synchronization, formal constraint checking, agent lifecycle management, deadband filtering, and fleet communication—so developers can focus on building their unique agent logic instead of rebuilding core coordination infrastructure from scratch. The ecosystem supports both single-process testing for rapid prototyping and multi-process UDP-distributed deployments for real-world production use, with native bindings for Python, Rust, and Node.js plus cross-language C FFI support for maximum compatibility.

---

## Installation
SuperInstance supports three primary runtime environments, with system-level dependencies required for full functionality:

### System Dependencies First
Some packages require compiled native code:
- **Linux**: Install build tools with `sudo apt install build-essential`
- **macOS**: Install Xcode Command Line Tools with `xcode-select --install`
- **Windows**: Install Microsoft Visual Studio Build Tools with the "Desktop development with C++" workload

### Python (Recommended for Rapid Prototyping)
All core Python packages are hosted on PyPI. Install individual packages for targeted use cases, or the full stack for complete functionality:
```bash
# Full Python stack (recommended for new developers)
pip install constraint-theory fleet-agent sunset-ecosystem deadband-python

# Individual packages
pip install constraint-theory # Formal constraint checking and Laman topology validation
pip install fleet-agent # Build and manage autonomous agent instances
pip install sunset-ecosystem # Graceful agent retirement with state inheritance
pip install deadband-python # Noise-reducing deadband filtering for sensor data
```

Verify your Python installation with:
```bash
python -c "import constraint_theory, fleet_agent, deadband; print('SuperInstance Python stack ready!')"
```

### Rust (For High-Performance Production Deployments)
Low-level crates are hosted on crates.io. Add them to your Rust project with:
```bash
cargo add superinstance-ffi flux-ffi fleet-math-c snapkit-rs
```
Each crate serves a specific role:
- `superinstance-ffi`: Cross-language FFI bindings for core SuperInstance logic
- `flux-ffi`: Fast flux data processing for real-time fleet state updates
- `fleet-math-c`: Low-level mathematical utilities including Pythagorean Fraction arithmetic
- `snapkit-rs`: Tools for capturing and sharing agent state snapshots

Verify your Rust installation with:
```bash
cargo check --package superinstance-ffi
```

### Node.js (For Web and Edge Deployments)
An early-access Node.js binding set is available via npm:
```bash
npm install @superinstance/core @superinstance/agent
```
Full Node.js support for clock sync and constraint checking is in active development.

---

## First Program: Basic Constraint Checking (5 Lines)
Let’s build a minimal 5-line Python script to validate that a 3-agent fleet adheres to **Laman topology rules**—a critical constraint for rigid, stable multi-agent formations. Laman topology requires exactly `2n - 3` edges for `n` agents, where `n=3` so 3 edges total for a fully connected fleet.

```python
# 5-line Laman topology validation script
from constraint_theory import LamanConstraint
constraint = LamanConstraint(agent_count=3)
valid_edges = [(0,1), (1,2), (2,0)]
print(f"Constraint satisfied: {constraint.validate(valid_edges)}")
```

When you run this script, you’ll see:
```
Constraint satisfied: True
```

### Extended Example
Test an invalid fleet configuration to see how constraint checking prevents unstable setups:
```python
# Invalid edge set for 3 agents (only 2 edges, fails Laman rule)
invalid_edges = [(0,1), (1,2)]
print(f"Invalid constraint satisfied: {constraint.validate(invalid_edges)}")
# Output: Invalid constraint satisfied: False
```

This constraint checking system integrates directly with fleet agent logic to block invalid fleet deployments, ensuring your swarm or robot team always operates in a stable formation.

---

## Second Program: Build a Coordinated Fleet Agent (10 Lines)
Now let’s create a minimal autonomous fleet agent that uses metronome clock synchronization, deadband filtering, and constraint checking. This core example fits in exactly 10 lines of Python, and uses all foundational SuperInstance features:

```python
# 10-line coordinated fleet agent
from fleet_agent import SuperAgent
from deadband_python import DeadbandFilter
from constraint_theory import MetronomeClock

agent = SuperAgent(agent_id="kimi1", position=(0.0, 0.0))
position_filter = DeadbandFilter(threshold=0.05)
sync_clock = MetronomeClock(interval=1.0)

raw_position = (0.12, 0.34)
filtered_pos = position_filter.apply(raw_position)
agent.update_state(position=filtered_pos)
print(f"Agent {agent.agent_id} updated state: {agent.state}")
```

### Line-by-Line Breakdown
1. Import core agent, deadband filtering, and clock sync tools
2. Initialize a new agent with ID `kimi1` and a starting position of (0,0)
3. Create a deadband filter that ignores position changes smaller than 0.05 units to eliminate sensor noise
4. Set up a metronome clock that triggers a sync tick every 1 second for zero-drift timekeeping
5. Simulate a raw sensor reading with small position noise
6. Filter the raw position data to remove insignificant fluctuations
7. Update the agent's internal state with the cleaned position data
8. Print the updated state to confirm the change

When you run this script, you’ll see output like:
```
Agent kimi1 updated state: {'position': (0.12, 0.34), 'timestamp': 1718000000.0}
```

### Key Features Explained
This agent uses **cadence calling**—a core SuperInstance pattern where logic runs at fixed, synchronized intervals aligned to the metronome clock ticks. This ensures all fleet agents process state updates at the exact same time, eliminating race conditions and ensuring consistent fleet behavior.

### Add Graceful Retirement
Extend your agent to support seamless state inheritance with the `sunset-ecosystem` package:
```python
from sunset_ecosystem import retire_agent, inherit_state

# Spin up a replacement agent
new_agent = SuperAgent(agent_id="kimi2")
# Trigger graceful retirement and pass all state to the new agent
retire_agent(agent, inherit_to=new_agent)
print(f"New agent inherited state: {new_agent.state}")
# Output: New agent inherited state: {'position': (0.12, 0.34), 'timestamp': 1718000000.0}
```
This ensures no agent state is lost during retirement, making fleet updates zero-downtime and seamless.

---

## Third Program: Run the Official 3-Agent Demo
The SuperInstance repository includes a reference end-to-end demo that showcases all core ecosystem features using the three sample agents: `forgemaster`, `oracle1`, and `kimi1`. The demo demonstrates zero-drift clock sync, deadband filtering, constraint checking, and graceful retirement.

### Prerequisites
You already cloned the repo in the TL;DR step, but if not run:
```bash
git clone https://github.com/superinstance-io/superinstance.git
cd superinstance
```

### Single-Process Demo
The simplest way to run the demo is the single-process script, which runs all 3 agents in a single Python process:
```bash
cd demo/three-agent-demo
python run_demo.py
```

This demo will:
1. Launch the three reference agents
2. Sync their clocks using **Pythagorean Fraction arithmetic** to guarantee zero drift over extended runtime (unlike floating-point timekeeping, fractions never accumulate rounding errors)
3. Apply deadband filtering to all simulated sensor data
4. Validate that the fleet adheres to Laman topology constraints
5. Demonstrate graceful retirement of one agent, with full state inherited by a replacement

Sample demo output:
```
[METRONOME] Sync tick at 1718000000.0 for agent forgemaster
[DEADBAND] Filtered position from (0.12, 0.34) to (0.12, 0.34) for agent oracle1
[CONSTRAINT] Laman topology valid for 3-agent fleet
[SUNSET] Retiring agent kimi1, passing state to kimi2
```

### Quick Mode and Verbose Mode

Short on time? Run 100 ticks instead of 1000:
```bash
python run_demo.py --quick
```

See every agent's per-tick reasoning:
```bash
python run_demo.py --verbose
```

### Multi-Process Distributed Demo
For testing real-world distributed fleet coordination, run the UDP-based multi-process demo across separate terminal windows:
```bash
# Terminal 1
python demo/three-agent-demo/distributed/metronome_node.py --name forgemaster --port 19840 --ticks 10000

# Terminal 2
python demo/three-agent-demo/distributed/metronome_node.py --name oracle1 --port 19840 --ticks 10000

# Terminal 3
python demo/three-agent-demo/distributed/metronome_node.py --name kimi1 --port 19840 --ticks 10000
```
All agents will maintain perfectly synchronized clocks across separate processes via UDP multicast discovery.

Or use the cluster launcher:
```bash
cd demo/three-agent-demo/distributed
bash run_cluster.sh
```

### Understanding the Demo Output

The demo produces structured log output. Here's what each line means:

```
[TICK 0000] Caller: forgemaster | Max drift: 0.000000 | clean | Holonomy:✓ Laman:✓
  forgemaster     | drift: +0.000000 | tick: 1
  oracle1         | drift: -0.000000 | tick: 1
  kimi1           | drift: +0.000000 | tick: 1
```

- **`[TICK NNNN]`** — The global metronome tick counter. Each tick is one beat of the shared clock.
- **`Caller: forgemaster`** — The **cadence caller** for this tick. The caller is the time authority — it broadcasts the reference time that other agents sync to. The role rotates to the agent with the longest uptime.
- **`Max drift: 0.000000`** — The maximum clock offset between any two agents. Because the system uses Python `Fraction` arithmetic (not floats), this stays at exactly zero — no rounding error accumulation, ever.
- **`clean`** — No constraint violations detected this tick.
- **`Holonomy:✓`** — Holonomy consensus check passed (cycle integrity in the fleet graph).
- **`Laman:✓`** — Laman topology rigidity verified (the fleet graph has exactly 2N−3 edges).

#### The Sunset Event (~Tick 300)

Around tick 300, you'll see:
```
>>> SUNSET: forgemaster retires → oracle1 inherits
[TICK 0310] Caller: oracle1 | Max drift: 0.000000 | clean | Holonomy:✓ Laman:✓
```

This is the **money shot**. The cadence caller (forgemaster) gracefully retires, broadcasting its full state — true_time, offset, drift_rate, tick_count — to the fleet. Oracle1 inherits everything and takes over as cadence caller. The clock doesn't blink.

#### Dashboard Summary

At the end, you'll see:
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

| Metric | Good | Great | Explanation |
|--------|------|-------|-------------|
| Max drift | < 0.01 | < 0.001 | Fraction arithmetic keeps drift bounded |
| Convergence | < 40 ticks | < 20 ticks | Time for all agents to align after startup |
| Violations caught | 100% | 100% | Every constraint breach is flagged |
| Sunset handoff | < 1 tick | 0 ticks | Heir picks up with zero interruption |

A max drift above 0.1 indicates a clock sync failure, likely from network issues or misconfigured deadband threshold.

---

## Architecture at a Glance
The SuperInstance ecosystem is built on three layered modules, with cross-language FFI support for maximum compatibility:
```
┌─────────────────────────────────────────────────────────┐
│                 Application Layer                      │
│  (Your Custom Agent Logic, Fleet Dashboards, APIs)     │
└─────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────┐
│                 Core Runtime Layer                      │
│  fleet-agent, constraint-theory, deadband-python,      │
│  sunset-ecosystem, superinstance-ffi, flux-ffi,        │
│  PLATO tile management for provenance-led knowledge    │
└─────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────┐
│                 Low-Level Math Layer                    │
│  fleet-math-c (Pythagorean Fractions, Laman Topology)  │
└─────────────────────────────────────────────────────────┘
```

### Core Workflows
1. **Clock Sync**: Metronome clocks use Pythagorean Fractions to eliminate drift across distributed fleets
2. **State Filtering**: Deadband filters reduce unnecessary state updates by ignoring insignificant sensor noise
3. **Constraint Validation**: Enforce Laman topology and custom rules to keep fleets stable
4. **Graceful Retirement**: Sunset ecosystem ensures no state is lost during agent updates
5. **Distributed Coordination**: UDP and MQTT support for cross-process fleet communication

---

## Key Concepts Explained

### Metronome Clock Sync
The metronome is the fleet's global time source. Each agent maintains a local clock as a Python `Fraction` — exact rational numbers that never accumulate rounding errors. When drift between an agent's clock and the cadence caller's reference time exceeds the **deadband threshold** (default: 0.0001), the agent corrects toward the reference. This is modeled on PLL (phase-locked loop) theory from electrical engineering.

```python
from constraint_theory import TemporalAgent

# Create an agent with the default tolerance
agent = TemporalAgent(name="demo", tolerance=0.1)
agent.observe(1.0)
agent.observe(1.05)
anomalies = agent.detect_anomalies()
print(f"Anomalies: {anomalies}")
```

### Deadband Filter
Agents don't talk constantly. The deadband filter means they only communicate when their drift exceeds a threshold. Below the threshold, they're silent. This is **sparse communication** — the same principle as a temporal deadband filter in control systems. In steady state, the message cost is **O(0)** — zero messages per tick when everything is in sync.

```python
from deadband_python import DeadbandFilter

# Only trigger updates when drift exceeds 0.001
filter = DeadbandFilter(threshold=0.001)
should_send = filter.apply(current_value, last_sent_value)
```

### Cadence Calling
One agent is the **cadence caller** — the time authority. It broadcasts reference time every tick. Other agents correct toward it. The caller is elected deterministically: longest uptime wins, ties broken by name sort. No Byzantine overhead, no leader election protocol.

### Laman Topology
Fleet communication uses a **minimally rigid graph** with exactly `2N−3` edges for `N` agents. Borrowed from rigid body mechanics, this ensures the fleet graph is connected but not redundant. Verification uses the pebble-game algorithm in O(V²) time — microseconds for a 9-agent fleet.

```python
from constraint_theory import LamanConstraint

# Verify a 3-agent topology (needs exactly 3 edges)
constraint = LamanConstraint(agent_count=3)
print(constraint.validate([(0,1), (1,2), (2,0)]))  # True
print(constraint.validate([(0,1), (1,2)]))          # False — not rigid
```

### PLATO Tiles
PLATO (Provenance-Ledgered Autonomous Tiles) are immutable knowledge blocks that carry full audit-trail provenance. Every state change is written to a tile with agent ID, tick number, and key. You can reconstruct exactly what happened at any tick.

```python
from constraint_theory import encode, decode

# Encode agent state to a tile token
token = encode(agent.state)
restored = decode(token)
```

### Sunset and Inheritance
When an agent retires (SIGTERM or planned shutdown), it broadcasts a **sunset packet** containing its full calibrated state: true_time, local_time offset, drift_rate, tick_count, and cadence_caller status. The heir absorbs this state and continues seamlessly — no two-phase commit, no coordination protocol, just a clean handoff.

---

## Common Patterns

### Pattern 1: Single Agent with Constraint Checking
Test constraint logic without a full fleet:
```python
from constraint_theory import LamanConstraint

constraint = LamanConstraint(agent_count=3)
valid = constraint.validate([(0,1), (1,2), (2,0)])
print(f"Fleet topology valid: {valid}")  # True
```

### Pattern 2: Two-Agent Coordination
```python
from fleet_agent import create_local_agent, add_neighbor, check_local_consensus

a1 = create_local_agent("alpha")
a2 = create_local_agent("beta")
add_neighbor(a1, "beta")
add_neighbor(a2, "alpha")
result = check_local_consensus(a1)
print(f"Consistent: {result.consistent}")
```

### Pattern 3: Agent with Sunset Handler
```python
from sunset_ecosystem import Agent, trinity_score

agent = Agent(name="worker", generation=1)
score = trinity_score(agent)
print(f"Trinity score: {score}")  # Health/quality metric
```

### Pattern 4: Encoding and Decoding State
```python
from constraint_theory import encode, decode

state = {"tick": 100, "drift": 0.0, "phase": 0.5}
token = encode(state)
restored = decode(token)
assert restored["tick"] == 100
```

### Pattern 5: Running with Injected Drift
Test the deadband correction by injecting artificial drift:
```bash
# In the distributed demo
python metronome_node.py --name agent --drift 0.01 --ticks 10000 --verbose
```
Watch the correction kick in as the agent's drift exceeds the deadband.

---

## What to Read Next
Now that you’ve mastered the basics of SuperInstance, dive deeper into these core topics:
- **[Ecosystem Overview](SUPERINSTANCE-ECOSYSTEM.md)** — Package list, quick start, and architecture links
- **[Strategic Architecture V2](STRATEGIC-ARCHITECTURE-V2.md)** — Full technical architecture: metronome sync, holonomy consensus, Laman rigidity
- **[Live Demo Guide](../demo/three-agent-demo/LIVE-DEMO-GUIDE.md)** — Detailed walkthrough of the 3-agent demo with customization instructions
- **[Strategic Review](STRATEGIC-REVIEW-KIMI.md)** — Honest assessment of what works and what needs building
- **[Next 30 Days](NEXT-30-DAYS.md)** — Engineering execution plan with daily deliverables
- **[AI Writings](https://github.com/SuperInstance/AI-Writings)** — Essays on constraint theory, music, and distributed systems
- **[PyPI: constraint-theory](https://pypi.org/project/constraint-theory/)** — Package reference

---

## FAQ
### Q: What is Pythagorean Fraction arithmetic, and why does it eliminate clock drift?
A: Pythagorean Fraction arithmetic uses exact rational numbers instead of floating-point values to track time offsets. Unlike floating-point numbers, fractions cannot accumulate rounding errors over time, so all agents in a fleet will maintain perfectly synchronized clocks indefinitely.

### Q: What are PLATO tiles?
A: PLATO (Provenance-Ledgered Autonomous Tiles) are immutable, shareable knowledge blocks that carry full audit trail provenance data. They are used to pass verified state and trusted knowledge between agents in a fleet, ensuring all nodes have access to accurate, unaltered information.

### Q: What is cadence calling?
A: Cadence calling is a standardized pattern where all fleet agents execute their core logic at fixed, synchronized intervals tied to the metronome clock system. This ensures that every agent processes state updates, sensor data, and coordination commands at the exact same time, eliminating race conditions and ensuring consistent, predictable behavior across the entire fleet.

### Q: Can I use SuperInstance with languages other than Python, Rust, and Node.js?
A: Yes! The core `superinstance-ffi` crate provides C-compatible FFI bindings, so you can use SuperInstance logic in any language that supports C interop, including C++, Go, and Java.

### Q: Is the SuperInstance ecosystem production-ready?
A: The core algorithm (metronome clock sync with Fraction arithmetic) is proven in simulation. The Python packages install and import correctly. The distributed transport layer and some production hardening (partition handling, Byzantine tolerance) are still in development. For the current status, see [NEXT-30-DAYS.md](NEXT-30-DAYS.md).

### Q: What is the difference between single-process and distributed demo?
A: The single-process demo runs all agents in one Python process with shared-memory message passing — great for understanding the algorithm. The distributed demo uses real UDP multicast, real peer discovery, and real cadence elections across separate processes — how a production fleet would run.

### Q: How do I add a 4th agent?
A: Add another `metronome_node.py` process on the same port. The Laman topology automatically expands to `2×4−3 = 5` edges. Or add a `MyAgent` class in `agents/` and register it in `run_demo.py`.

### Q: Can I run this on Windows/ARM/Raspberry Pi?
A: Yes — the Python packages are pure Python + NumPy. Any platform with Python 3.10+ works. For the Rust crates, you need the appropriate target triple (`armv7-unknown-linux-gnueabihf` for Raspberry Pi).

### Q: What is the performance overhead of constraint checking?
A: Negligible. The 248 aerospace constraints in the demo run every tick with no measurable overhead. The bottleneck is network I/O, not constraint evaluation.

### Q: How does the deadband threshold affect message frequency?
A: Lower threshold = more corrections = lower drift but more messages. Higher threshold = fewer messages but wider drift tolerance. The default (0.0001) gives near-zero drift with very sparse communication in steady state.

### Q: What happens if two agents disagree on time?
A: The cadence caller broadcasts reference time. If an agent's drift exceeds ε (one-third of the deadband δ), it enters the DRIFTING state and corrects toward the caller. If drift exceeds δ, it enters DESYNCHRONIZED and does a full resync.

### Q: Is this related to Paxos/Raft?
A: Different problem space. Paxos/Raft solve distributed consensus on a value. The metronome solves distributed clock synchronization with O(0) steady-state messages. They're complementary, not competing.

### Q: How do I debug a fleet that is not converging?
A: 1) Check the max drift in the dashboard — above 0.01 suggests a sync issue. 2) Check your deadband threshold isn't too high. 3) Run with `--verbose` to see per-agent state. 4) Verify network connectivity between nodes (UDP multicast on port 19840).

### Q: How do I contribute to the SuperInstance ecosystem?
A: Check out the [SuperInstance GitHub org](https://github.com/SuperInstance) and the [forgemaster repo](https://github.com/SuperInstance/forgemaster). Issues are tagged by priority. The [NEXT-30-DAYS.md](NEXT-30-DAYS.md) plan has daily deliverables if you want to jump in.

---

*Three agents. One clock. Zero drift. Welcome to the fleet.*