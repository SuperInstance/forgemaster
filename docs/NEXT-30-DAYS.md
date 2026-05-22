# NEXT 30 DAYS — Engineering Execution Plan

**Constraint-Theoretic Fleet · SuperInstance Ecosystem**
**Date:** 2026-05-21
**Status:** Engineering plan, not a vision doc. Every line is a task someone types.

---

## Context (What We Actually Have)

- `demo/three-agent-demo/` — A single-process Python simulation with shared-memory message passing. It runs. It is not distributed. It is not networked. The "UDP bus" is a Python dict with random delay.
- `constraint-theory-py/`, `fleet-agent/`, `i2i-protocol/`, `plato-core/`, `sunset-ecosystem/` — Five core packages with `dist/` directories. Some install. None have a working 3-line quickstart.
- `metronome_unified.py` — A 562-line simulation proving the algorithm converges under idealized conditions. Not production code.
- **My own review (STRATEGIC-REVIEW-KIMI.md) rated the ecosystem 4/10.** The metronome design is world-class. The ratio of documentation to working code is dangerously inverted. 170 repositories is unmanageable. There is no integration test. There is no network transport. PLATO is a file naming convention, not a database.

This plan fixes all of that — in 30 days, with daily deliverables.

---

## Week 1 (Days 1–7): Ship the Demo

**Goal at end of Week 1:** A stranger can `pip install` five packages, copy-paste a 3-line script, and see three agents synchronize on their screen. All known beta issues are fixed. Dists are on PyPI.

---

### Day 1 (Mon): Fix the Five Core Packages

**What to build:**
1. `constraint-theory-py` — Verify `pip install constraint-theory` works from the wheel in `dist/`. The wheel exists (v0.3.0). Confirm it imports and the 248 constraints load.
2. `fleet-agent` — The Python package imports but `from fleet_agent.holonomy_bridge import verify_fleet_cycles` fails (`ModuleNotFoundError`). Fix the package discovery in `pyproject.toml` so the bridge module is included in the wheel.
3. `plato-core` — v0.1.0 wheel exists. Verify `import plato_core` works. Confirm the entry-point plugin loads without `pkg_resources` deprecation warnings.
4. `i2i-protocol` — No wheel in `dist/`. Build one. Verify `import i2i_protocol` or `from i2i import message` works (check the actual namespace in `src/i2i/`).
5. `sunset-ecosystem` — v0.1.0 wheel is 172KB (good sign). But `import sunset_ecosystem` returns only dunder methods in `dir()`. The `__init__.py` has an `__all__` list but nothing is actually importable by a user doing `from sunset_ecosystem import Agent`. Fix the `__init__.py` to expose the top-level API.

**Tests that must pass:**
```bash
python -c "import constraint_theory; print(len(constraint_theory.list_constraints()))"
# MUST OUTPUT: 248

python -c "from fleet_agent.holonomy_bridge import verify_cycle; print('OK')"
# MUST NOT raise ModuleNotFoundError

python -c "import plato_core; print(plato_core.__version__)"
# MUST OUTPUT version string

python -c "from i2i_protocol import format_drift_report; print('OK')"
# OR whatever the actual top-level API is — must not fail

python -c "from sunset_ecosystem import Agent, trinity_score; print('OK')"
# MUST expose Agent and trinity_score
```

**Deliverable:** All five packages install cleanly in a fresh venv. A `scripts/test_install.sh` script exists and passes.

---

### Day 2 (Tue): Fix Every Beta Issue

**Beta issue 1: holonomy-consensus ghost page**

The `holonomy-consensus` Rust crate has no Python bindings compiled. `fleet-agent` falls back to `holonomy_stubs.py` (pure Python). The README claims "38ms @ 26316 tx/s" but users cannot access the Rust engine from Python. The crate is marked v0.2.0 but `cargo build` in `holonomy-consensus/` produces a `target/debug/libholonomy_consensus.so` that is not wrapped by PyO3.

- Write a minimal `src/python.rs` using PyO3 that exposes `HolonomyConsensus`, `ConsensusTile`, `HolonomyMatrix`, `check_consensus()`.
- Add `[lib] crate-type = ["cdylib"]` to `Cargo.toml`.
- Build with `maturin build` or `cargo build --release`.
- Verify `import holonomy_consensus` works and is faster than the Python stubs.
- If PyO3 build is blocked, document the fallback path clearly: "Rust engine requires `cargo build`. Python stubs are used by default."

**Beta issue 2: sunset-ecosystem empty exports**

`import sunset_ecosystem` shows `['__all__', '__builtins__', ...]` — no user-visible API.

- Audit `sunset_ecosystem/__init__.py`. The `__all__` list references `Agent`, `trinity_score`, etc., but the import lines use relative imports from modules that may not exist in the installed package.
- Fix: ensure all modules referenced in `__init__.py` are included in `pyproject.toml` package discovery.
- Add a `sunset_ecosystem/api.py` that re-exports the 5 most common entry points: `Agent`, `GenerationRunner`, `trinity_score`, `SeedBank`, `run_stress_test`.
- Update `__init__.py` to import from `api.py`.

**Beta issue 3: fleet-agent undocumented**

`fleet-agent` has 476 lines across 3 files and no docstrings on public functions. A user reading the README sees `verify_fleet_cycles(...)` but the function does not exist in the codebase.

- Add docstrings to `create_local_agent()`, `add_neighbor()`, `check_local_consensus()`.
- Add a `docs/fleet-agent-quickstart.md` with working code:
```python
from fleet_agent import create_local_agent, add_neighbor, check_local_consensus
agent = create_local_agent("forge")
add_neighbor(agent, "oracle1")
result = check_local_consensus(agent)
print(result.consistent)
```
- Verify the example actually runs without error.

**Tests that must pass:**
```bash
cd holonomy-consensus && cargo test && python -c "import holonomy_consensus; print(holonomy_consensus.__version__)"
cd sunset-ecosystem && python -c "from sunset_ecosystem import Agent, trinity_score; print('OK')"
cd fleet-agent && python -c "from fleet_agent import create_local_agent; a = create_local_agent('test'); print(a['name'])"
```

**Deliverable:** A `BETA-FIXES.md` file listing each issue, the fix, and the verification command. All three test commands pass.

---

### Day 3 (Wed): Build `metronome-core` as a Real Package

**What to build:**

The implementation guide (§2.5) specifies a full `metronome/` package. None of it exists outside `demo/three-agent-demo/`, which is a simulation, not a library. Build the real package now.

Files to create:
```
metronome/
├── __init__.py
├── types.py          # AgentState, DeadbandRegime, MetronomeConfig, PhaseState, SunsetPacket
├── theta.py          # beat_phase(), phase_error(), tighten_epsilon()
├── deadband.py       # classify_regime(), apply_correction()
├── agent.py          # MetronomeAgent.tick(), correct(), sunset(), from_sunset_packet()
├── plato_adapter.py  # PlatoAdapter (JSONL disk), MockPlatoAdapter (memory)
├── topology.py       # LamanTopology, henneberg_construction(), add_small_world_edges()
├── election.py       # elect_cadence_caller(), cadence_correction_phase()
└── diagnostic.py     # DiagnosticMiner (observation-only)

tests/
├── test_types.py
├── test_theta.py
├── test_deadband.py
├── test_agent.py
├── test_plato_store.py
├── test_topology.py
└── test_mining_safe.py
```

Code directly from the implementation guide. Do not redesign. The spec is 2240 lines; use it.

**Critical rule:** Every phase computation uses `fractions.Fraction`. No `float` in the hot path. The zero-drift guarantee depends on this.

**Tests that must pass:**
```bash
cd metronome && python -m pytest tests/ -v
# MUST PASS:
# test_zero_drift_1000_beats
# test_in_band_zero_corrections
# test_sunset_inheritance
# test_phase_survives_restart
# test_laman_9_agents
# test_mining_safe
```

**Deliverable:** `metronome/` directory committed. All 7 test files green.

---

### Day 4 (Thu): The 3-Line Quickstart

**What to build:**

A user should be able to:
```bash
pip install constraint-theory fleet-agent plato-core sunset-ecosystem metronome
python -c "
from metronome import MetronomeConfig, MetronomeAgent, MockPlatoAdapter
cfg = MetronomeConfig.default_fleet('forge', ['oracle1'])
agent = MetronomeAgent(cfg, MockPlatoAdapter())
agent.tick({})
print('beat', agent.beat_k, 'phase', agent.phase)
"
```

Steps:
1. Add `metronome` to the workspace as a sixth package with `pyproject.toml`.
2. Ensure `metronome` declares dependencies on `plato-core` (for tile format) and `constraint-theory` (for deadband primitives).
3. Write `README.md` in `metronome/` with the 3-line quickstart.
4. Build the wheel: `python -m build metronome/`
5. Test in a fresh venv: `pip install ./metronome/dist/metronome-0.1.0-py3-none-any.whl`
6. Run the 3-line script. It must work.

**Tests that must pass:**
```bash
./scripts/test_quickstart.sh
# This script:
# 1. Creates a fresh venv
# 2. pip installs all 6 wheels from dist/
# 3. Runs the 3-line quickstart
# 4. Exits 0 on success, 1 on failure
```

**Deliverable:** `scripts/test_quickstart.sh` passes. `metronome/dist/` contains a wheel. `README.md` has the 3-line example.

---

### Day 5 (Fri): Replace the Simulation Demo with a Real Subprocess Demo

**What to build:**

The current `demo/three-agent-demo/run_demo.py` runs all three agents in one Python process with a `NetworkBus` that is just a `defaultdict(deque)`. Replace this with a real multiprocess demo.

New architecture:
```
demo/three-agent-demo/
├── run_demo.py          # Orchestrator: spawns 3 agents, monitors them
├── agent_process.py     # Entry point for one agent subprocess
├── udp_bus.py           # REAL UDP socket bus (replaces network_bus.py)
├── metronome_core.py    # Keep the working core, but use metronome/ package imports
└── dashboard.py         # Live terminal dashboard
```

`udp_bus.py` requirements:
- Bind to `localhost` ports: forgemaster=9001, oracle1=9002, kimi1=9003.
- Serialize messages with `msgpack` (not the custom pipe-delimited format).
- Handle UDP packet loss: if a drift report is lost, the agent detects timeout and retransmits.
- Latency injection: `time.sleep(random.uniform(0, 0.05))` before `socket.sendto()`.

`agent_process.py` requirements:
- Reads `agent_id` and `neighbors` from command line or `config.json`.
- Creates a `MetronomeAgent` using the real `metronome` package.
- Listens on its UDP port.
- Sends drift reports to neighbors when `|error| > epsilon`.
- Prints its state to stdout every 10 ticks.

`run_demo.py` requirements:
- Uses `subprocess.Popen` to spawn 3 `agent_process.py` instances.
- Waits 5 seconds for bootstrap.
- Runs for 1000 ticks (or 30 minutes real-time if T=17/12 ≈ 1.4s per tick).
- Kills one process at tick 300, verifies the other two continue.
- Spawns a replacement process, verifies it inherits via sunset packet.

**Tests that must pass:**
```bash
cd demo/three-agent-demo && python run_demo.py
# Expected output:
# [TICK 0000] Cadence caller: forgemaster | Max drift: 0.000000
# [TICK 0010] Cadence caller: forgemaster | Max drift: 0.000000
# ...
# [TICK 0300] >>> SUNSET: forgemaster retires → oracle1 inherits
# ...
# [TICK 0999] Bounded drift verified. Demo complete.
```

**Deliverable:** `run_demo.py` completes with zero DESYNC events. The dashboard shows 3 separate process PIDs.

---

### Day 6 (Sat): Beta Test the Demo

**What to build:**

Recruit 3 beta testers (can be the same machine with 3 venvs). Each tester:
1. Runs `pip install` from the local dists.
2. Runs `run_demo.py`.
3. Reports any failure.

Fix every issue found. Known likely issues:
- Port conflicts if testers run on the same machine.
- Missing `msgpack` dependency.
- `config.json` path issues.
- Windows vs. Unix subprocess differences.

**Tests that must pass:**
```bash
# For each beta tester:
cd /tmp && python -m venv tester_venv && source tester_venv/bin/activate
pip install /path/to/dist/*.whl
python -m three_agent_demo.run_demo
# MUST complete without error
```

**Deliverable:** A `BETA-REPORT.md` with tester names, issues found, fixes applied. No open issues.

---

### Day 7 (Sun): Upload to PyPI

**What to build:**

1. Bump versions if any code changed since dist build:
   - `constraint-theory` 0.3.0 → 0.3.1 (if fixes applied)
   - `fleet-agent` 0.2.2 → 0.2.3 (if fixes applied)
   - `plato-core` 0.1.0 → 0.1.1 (if fixes applied)
   - `sunset-ecosystem` 0.1.0 → 0.1.1 (if fixes applied)
   - `metronome` 0.1.0 (new)
   - `i2i-protocol` — build first wheel, version 0.1.0

2. Rebuild all wheels: `python -m build` in each package directory.

3. Upload with `twine upload dist/*` for each package.
   - Use the PyPI tokens in `.credentials/` if available.
   - Check PyPI upload cooldown: if a version was uploaded recently, bump the patch number.

4. Verify on PyPI:
```bash
pip install --index-url https://pypi.org/simple constraint-theory fleet-agent plato-core sunset-ecosystem metronome i2i-protocol
python -c "from metronome import MetronomeAgent; print('OK')"
```

**Tests that must pass:**
```bash
./scripts/test_pypi_install.sh
# Fresh venv, install from PyPI (not local), run quickstart.
```

**Deliverable:** All 6 packages are live on PyPI with working install commands. `scripts/test_pypi_install.sh` passes.

---

## Week 2 (Days 8–14): Real Network

**Goal at end of Week 2:** Agents run on separate physical or virtual machines. They communicate over real UDP sockets with real latency and packet loss. A web dashboard updates in real-time. A 24-hour soak test completes without a single DESYNC event.

---

### Day 8 (Mon): Replace Simulated UDP with Actual UDP

**What to build:**

The `udp_bus.py` from Day 5 uses `localhost`. Make it production-ready.

1. Add IP address configuration to `config.json`:
```json
{
  "agents": [
    {"id": "forgemaster", "host": "192.168.1.10", "port": 9001},
    {"id": "oracle1", "host": "192.168.1.11", "port": 9002},
    {"id": "kimi1", "host": "192.168.1.12", "port": 9003}
  ]
}
```

2. Update `udp_bus.py`:
- `bind()` to `(host, port)` from config.
- `sendto()` to neighbor `(host, port)` from config.
- Use `socket.AF_INET`, `socket.SOCK_DGRAM`.
- Set `socket.SO_REUSEADDR`.
- Serialize with `msgpack.packb()` / `msgpack.unpackb()`.
- Add message types: `THETA_PROPOSE`, `THETA_ACK`, `DRIFT_REPORT`, `CADENCE_CALL`, `SUNSET_ANNOUNCE`.

3. Add retry logic:
- If `CADENCE_CALL` is not acknowledged within `4T`, retransmit.
- If `DRIFT_REPORT` is lost, the agent detects missing neighbors via heartbeat timeout (timeout = `8T`).

**Tests that must pass:**
```bash
cd demo/three-agent-demo && python test_udp_bus.py
# MUST PASS:
# test_send_receive_round_trip
# test_packet_loss_recovery
# test_serialization_msgpack
# test_timeout_retransmission
```

**Deliverable:** `udp_bus.py` has 100% unit test coverage for send, receive, retry, and timeout.

---

### Day 9 (Tue): Run Agents on Separate Machines

**What to build:**

Deploy the 3-agent demo across 3 separate processes on different machines (or WSL instances, or Docker containers).

Setup:
- Machine A (eileen, 192.168.1.10): Forgemaster
- Machine B (kimi1, 192.168.1.11): Oracle1
- Machine C (oracle1, 192.168.1.12): kimi1

If physical machines are unavailable, use 3 Docker containers on the same host with bridged networking.

`docker-compose.yml`:
```yaml
version: '3'
services:
  forgemaster:
    build: .
    command: python agent_process.py --id forgemaster --config /config.json
    networks:
      fleet_net:
        ipv4_address: 172.20.0.2
  oracle1:
    build: .
    command: python agent_process.py --id oracle1 --config /config.json
    networks:
      fleet_net:
        ipv4_address: 172.20.0.3
  kimi1:
    build: .
    command: python agent_process.py --id kimi1 --config /config.json
    networks:
      fleet_net:
        ipv4_address: 172.20.0.4
```

**Tests that must pass:**
```bash
docker-compose up -d
sleep 10
# Check that all 3 agents are receiving messages
docker logs forgemaster | grep "beat=" | tail -5
docker logs oracle1 | grep "beat=" | tail -5
docker logs kimi1 | grep "beat=" | tail -5
# All must show beat numbers incrementing
```

**Deliverable:** `docker-compose.yml` committed. All 3 containers run for 30 minutes without crash.

---

### Day 10 (Wed): Add Real Latency, Real Packet Loss

**What to build:**

Use `tc` (traffic control) on Linux to inject real network impairment between containers.

```bash
# On each container:
tc qdisc add dev eth0 root netem delay 50ms 10ms loss 2% corrupt 0.1%
```

This adds:
- 50ms base latency ± 10ms jitter
- 2% packet loss
- 0.1% corrupted packets

Update `agent_process.py` to log:
- Number of retransmissions per tick
- Average latency observed
- Packet loss rate estimated

**Tests that must pass:**
```bash
cd demo/three-agent-demo && python test_network_impairment.py
# MUST PASS:
# test_drift_bounded_under_50ms_latency
# test_recovery_from_2_percent_loss
# test_no_desync_under_impairment
```

Run 500 ticks with impairment. Max drift must remain `< delta` (1/16 = 0.0625).

**Deliverable:** `test_network_impairment.py` passes. Log file shows retransmissions < 5% of ticks.

---

### Day 11 (Thu): Build a Real-Time Web Dashboard

**What to build:**

Replace the terminal print dashboard with a web dashboard.

Stack: Python `http.server` + Server-Sent Events (SSE) + vanilla JS.

Files:
```
demo/three-agent-demo/dashboard/
├── server.py       # HTTP server on port 8080, serves index.html + SSE /events
├── index.html      # Single page: 3 cards showing agent state
└── app.js          # EventSource connection, updates DOM every beat
```

`server.py` reads `phase.jsonl` from each agent's PLATO directory and streams updates.

`index.html` shows:
- Agent name, beat number, phase, error, regime (color-coded)
- Fleet coherence score: `1 - (sum |error|) / (N * delta)`
- Cadence caller name
- Topology graph (3 nodes, edges)
- Live log of corrections and drift reports

**Tests that must pass:**
```bash
cd demo/three-agent-demo/dashboard && python server.py &
curl -s http://localhost:8080 | grep -q "Fleet Status"
# MUST return 0
```

Open browser at `http://localhost:8080`. Verify it updates every ~1.4 seconds (the beat period).

**Deliverable:** Screenshot of dashboard showing 3 agents IN_BAND. Dashboard updates without page refresh.

---

### Day 12 (Fri): Network Partition Test

**What to build:**

Test what happens when the network splits.

Scenario:
1. Run 3-agent fleet for 100 ticks (all stable).
2. Use `tc` or `iptables` to block UDP between Forgemaster and Oracle1.
3. Wait 50 ticks.
4. Verify:
   - Oracle1 and kimi1 continue synchronized (they can still talk).
   - Forgemaster detects partition (no messages from neighbors within `8T`).
   - Forgemaster enters RECOVERING state.
5. Restore the link.
6. Verify all 3 reconverge to IN_BAND within 20 ticks.

**Tests that must pass:**
```bash
cd demo/three-agent-demo && python test_partition.py
# MUST PASS:
# test_partition_detected_within_8T
# test_partial_fleet_continues_sync
# test_reconvergence_after_heal
```

**Deliverable:** `test_partition.py` passes. The dashboard shows the partition visually (Forgemaster card turns red, then green after heal).

---

### Day 13 (Sat): Stress Test — 10,000 Ticks

**What to build:**

Run the 3-agent fleet for 10,000 ticks (~4 hours real time with T=17/12s).

Use `nohup` or `systemd` to keep it running:
```bash
nohup python agent_process.py --id forgemaster > forge.log 2>&1 &
```

Monitor via dashboard. Log metrics every 100 ticks:
- Max drift
- Corrections per agent
- Retransmissions
- Cadence caller changes
- DESYNC events

**Acceptance criteria:**
- Zero DESYNC events after tick 100 (initial convergence period).
- All agents IN_BAND for > 99% of ticks after tick 100.
- No memory leaks (RSS stable within ±10MB over 4 hours).
- Sunset/inheritance works at tick 5000 (kill one agent, spawn successor, verify reconvergence).

**Deliverable:** `stress-10000.log` file with 100 lines of metrics. No DESYNC after tick 100.

---

### Day 14 (Sun): 24-Hour Soak Test + Dashboard Hardening

**What to build:**

Run the fleet continuously for 24 hours.

During the soak:
- Inject a 5-minute network partition at hour 6.
- Inject 10% packet loss for 30 minutes at hour 12.
- Sunset one agent at hour 18, spawn successor.
- Collect full drift logs.

At the end, generate a report:
```bash
python scripts/soak_report.py --log-dir logs/ --output soak-report.md
```

Report must include:
- Uptime percentage per agent
- Total corrections
- Total retransmissions
- Partition detection accuracy
- Sunset inheritance success
- Max drift ever observed
- Dashboard availability (was the web UI reachable the whole time?)

**Tests that must pass:**
```bash
# After 24 hours:
python scripts/verify_soak.py logs/
# MUST OUTPUT: "SOAK PASS: all criteria met"
```

**Deliverable:** `soak-report.md` with all metrics. `SOAK PASS` stamp.

---

## Week 3 (Days 15–21): Real Agents

**Goal at end of Week 3:** Forgemaster, Oracle1, and kimi1 are actual OpenClaw agent instances. They use real PLATO tiles, real constraint checks, and real nerve-grid compute. The first live tournament runs: 3 agents, 1 hour, real tasks.

---

### Day 15 (Mon): Wire OpenClaw Heartbeat as Tick Source

**What to build:**

The metronome currently uses `time.sleep(T)` as its beat source. Replace this with the OpenClaw heartbeat.

In OpenClaw, the heartbeat is a periodic task (see `OpenShell/HEARTBEAT.md`). Wire the metronome `tick()` to be called from `on_heartbeat()`.

Create `metronome/openclaw_plugin.py`:
```python
from metronome import MetronomeAgent, MetronomeConfig, MockPlatoAdapter

class MetronomePlugin:
    def __init__(self, agent_id: str, neighbors: list[str]):
        cfg = MetronomeConfig.default_fleet(agent_id, neighbors)
        self.agent = MetronomeAgent(cfg, MockPlatoAdapter())

    def on_heartbeat(self, ctx):
        """Called by OpenClaw every heartbeat."""
        neighbor_phases = self._read_neighbor_phases(ctx)
        self.agent.tick(neighbor_phases)
        self._write_plato_tiles(ctx)
```

Register the plugin in the OpenClaw plugin system:
```yaml
# .openclaw/plugins/metronome.yaml
plugin: metronome.openclaw_plugin.MetronomePlugin
config:
  agent_id: forgemaster
  neighbors: [oracle1, kimi1]
```

**Tests that must pass:**
```bash
cd OpenShell && python -m pytest tests/test_metronome_plugin.py -v
# MUST PASS:
# test_heartbeat_triggers_tick
# test_tick_updates_plato_tiles
# test_plugin_loads_without_error
```

**Deliverable:** OpenClaw heartbeat triggers metronome tick. PLATO tiles update after each heartbeat.

---

### Day 16 (Tue): Deploy Forgemaster as Real Agent

**What to build:**

Forgemaster is the constraint-theory agent. In the demo, it checks 25 aerospace constraints against simulated telemetry. Make it real.

1. Create `agents/forgemaster/` package:
```
agents/forgemaster/
├── __init__.py
├── agent.py          # ForgemasterAgent class
├── constraints.py    # The 25 constraints, loaded from constraint-theory-py
└── config.json
```

2. The real Forgemaster agent:
- Reads its `agent_id` and `neighbors` from `AGENTS.md` or `config.json`.
- Creates a `MetronomeAgent` with `agent_id="forgemaster"`.
- On each tick, receives fleet state via I2I protocol.
- Runs `constraint_theory.check_constraints(state)` against the 25 rules.
- Broadcasts violations via I2I `CONSTRAINT_VIOLATION` messages.
- Persists its phase state to `.local-plato/twin/metronome/agents/forgemaster/phase.jsonl`.

3. Run Forgemaster as a standalone process:
```bash
python -m agents.forgemaster --config agents/forgemaster/config.json
```

**Tests that must pass:**
```bash
cd agents/forgemaster && python -m pytest tests/ -v
# MUST PASS:
# test_constraints_load
# test_violation_detection
# test_tick_persists_phase
```

**Deliverable:** Forgemaster process runs standalone. It detects a constraint violation when fuel < 5%.

---

### Day 17 (Wed): Deploy Oracle1 as Real Agent

**What to build:**

Oracle1 is the fleet coordinator. It runs holonomy consensus and monitors Laman rigidity.

1. Create `agents/oracle1/` package.
2. Oracle1 agent:
- Listens to all `DRIFT_REPORT` messages.
- Computes fleet consensus phase using `cadence_correction_phase()` (weighted median).
- If an agent reports `|error| >= delta`, Oracle1 (as cadence caller) broadcasts `CADENCE_CALL`.
- Runs `fleet_agent.check_local_consensus()` to verify topology.
- If topology loses rigidity (edge count < 2N-3), broadcasts `TOPOLOGY_ALERT`.

3. Oracle1 has the cadence caller role by default (longest uptime).

**Tests that must pass:**
```bash
cd agents/oracle1 && python -m pytest tests/ -v
# MUST PASS:
# test_cadence_call_broadcast
# test_median_correction
# test_topology_rigidity_check
```

**Deliverable:** Oracle1 process runs. When Forgemaster drifts, Oracle1 sends `CADENCE_CALL` and Forgemaster corrects.

---

### Day 18 (Thu): Deploy kimi1 as Real Agent

**What to build:**

kimi1 is the GPU/compute agent. It runs the "nerve grid" — parallel compute rooms.

1. Create `agents/kimi1/` package.
2. kimi1 agent:
- Runs 10 compute rooms. Each room performs a small matrix operation.
- Reports `gpu_throughput` via I2I `NERVE_METRIC` messages.
- If GPU is unavailable (no CUDA), falls back to CPU with a warning log.
- Checks for `CONSTRAINT_VIOLATION` messages and archives them in its local PLATO room.

3. Verify CUDA accessibility:
```bash
python -c "import torch; print(torch.cuda.is_available())"
```
If NO → CPU fallback. If YES → use `torch` for matrix ops.

**Tests that must pass:**
```bash
cd agents/kimi1 && python -m pytest tests/ -v
# MUST PASS:
# test_rooms_compute
# test_gpu_fallback
# test_violation_archiving
```

**Deliverable:** kimi1 process runs. It reports throughput every 10 ticks.

---

### Day 19 (Fri): Real PLATO Tiles, Real Constraints, Real Nerve Grid

**What to build:**

Integrate the three agents with the real PLATO system.

1. **Real PLATO tiles:**
- Each agent writes its `PhaseState` to `.local-plato/twin/metronome/agents/{id}/phase.jsonl`.
- Each agent reads neighbor phases from the same path.
- Sunset packets write to `sunset.json`.

2. **Real constraints:**
- Forgemaster loads constraints from `constraint_theory.load_constraints("aerospace")`.
- Constraints are PLATO tiles: each constraint has a tile ID, confidence score, and provenance.

3. **Real nerve grid:**
- kimi1's compute rooms are PLATO rooms: `plato-core` manages room registration.
- Each room's output is a tile.
- Tiles have `agent_id=kimi1`, `room_id=room_3`, `confidence=0.95`.

**Integration test:**
```bash
python scripts/run_fleet_integration.py --duration 10m
# Spins up all 3 agents, real PLATO I/O, real I2I messages.
```

**Tests that must pass:**
```bash
python -m pytest tests/test_fleet_integration.py -v
# MUST PASS:
# test_all_agents_write_tiles
# test_plato_reads_neighbor_phases
# test_sunset_packet_in_plato
# test_constraint_tiles_have_provenance
```

**Deliverable:** `test_fleet_integration.py` passes. PLATO `.local-plato/twin/` directory has real JSONL files.

---

### Day 20 (Sat): End-to-End Integration Test

**What to build:**

The integration test that the architecture has been missing. This is the test I called for in my review (§3.5).

`tests/test_e2e_fleet.py`:
```python
def test_e2e_3_agent_fleet():
    """Spin up 3 real agent processes, wire them with Laman topology,
    run 1000 beats with injected latency, verify all within delta.
    """
    # 1. Spawn 3 processes
    # 2. Bootstrap: propose theta, ACK, COMMIT
    # 3. Run 1000 beats
    # 4. Inject 50ms latency, 2% loss
    # 5. Verify all agents within delta
    # 6. Sunset one agent
    # 7. Verify successor inherits theta and reconverges
```

This test must:
- Use `subprocess.Popen`, not threads.
- Use real UDP sockets.
- Use real PLATO JSONL files (not in-memory mocks).
- Run in under 5 minutes (1000 beats × 1.4s = ~23 minutes; use `T=Fraction(1,10)` for test speed).

**Tests that must pass:**
```bash
python -m pytest tests/test_e2e_fleet.py -v --timeout=300
# MUST PASS:
# test_e2e_3_agent_fleet
# test_e2e_partition_recovery
# test_e2e_sunset_inheritance
```

**Deliverable:** `test_e2e_fleet.py` green. This is the new "hello world" for the fleet.

---

### Day 21 (Sun): First Live Tournament

**What to build:**

A 1-hour live tournament: 3 agents, real tasks, scored.

**Tournament rules:**
- Agents start with `T = Fraction(17, 12)`, `epsilon = Fraction(1, 48)`, `delta = Fraction(1, 16)`.
- Task 1 (0–20 min): All agents must stay IN_BAND. Penalty: -1 point per DESYNC.
- Task 2 (20–40 min): Inject constraint violations. Forgemaster must detect ≥ 90% of violations within 3 ticks.
- Task 3 (40–60 min): Sunset Oracle1 at minute 45. Successor must reconverge within 10 ticks. Score: +10 points if reconvergence < 10 ticks, +5 if < 20 ticks, 0 otherwise.

**Scoring:**
```python
score = 100
score -= desync_count * 1
score += constraint_detection_bonus
score += sunset_reconvergence_bonus
```

**Deliverable:** `tournament-2026-05-21.md` report with scores, logs, and a link to the dashboard screenshot. Minimum passing score: 80/100.

---

## Week 4 (Days 22–30): Real Users

**Goal at end of Week 4:** A getting-started guide exists. A demo video is recorded. A blog post is published. At least 3 external beta users have run their own agent. Feedback is collected and triaged.

---

### Day 22 (Mon): Write the Getting-Started Guide

**What to build:**

`docs/GETTING-STARTED.md` — the single document a new user reads.

Structure:
1. **Prerequisites:** Python 3.10+, 3 open UDP ports, 1GB RAM.
2. **Install:** `pip install metronome fleet-agent plato-core`
3. **Configure:** Edit `config.json` with your agent's ID and neighbors.
4. **Run one agent:** `python -m metronome.agent_process --config config.json`
5. **Run a fleet of 3:** Use `docker-compose up` (provide the file).
6. **Watch the dashboard:** Open `http://localhost:8080`.
7. **Customize:** Add your own constraints, your own compute rooms.
8. **Troubleshooting:** Port conflicts, firewall rules, clock skew.

The guide must be tested by someone who did NOT write the code. If you are the only person available, test it in a fresh VM or container where you have not run the code before.

**Tests that must pass:**
```bash
# In a fresh Ubuntu container:
apt-get update && apt-get install -y python3-pip
pip install metronome fleet-agent plato-core
# Follow GETTING-STARTED.md step by step
# Step 4 must produce a running agent within 60 seconds.
```

**Deliverable:** `docs/GETTING-STARTED.md` committed. Fresh-container test passes.

---

### Day 23 (Tue): Polish Documentation + API Reference

**What to build:**

1. `docs/API.md` — Auto-generated from docstrings using `pydoc` or `mkdocstrings`.
2. `docs/ARCHITECTURE.md` — A 1-page summary (not 1166 lines). One diagram, 5 bullet points.
3. `docs/FAQ.md` — Answers to the skeptical questions from my review:
   - "Why not just use Temporal.io?" → Answer: Temporal provides durable execution; metronome provides zero-steady-state coordination with deterministic phase convergence.
   - "What happens in a partition?" → Answer: Partition is detected within 8T. Partial fleet continues. Reconvergence on heal.
   - "Where is the formal proof?" → Answer: Laman and Pythagorean52 are computationally verified. Spectral gap theorem is standard gossip theory. The deadband-corrected gossip Lyapunov function is open — see `docs/OPEN-PROBLEMS.md`.

**Tests that must pass:**
```bash
python -m pydoc metronome.agent.MetronomeAgent > /dev/null
# Must not error
```

**Deliverable:** 4 docs files committed. No broken links.

---

### Day 24 (Wed): Record the Demo Video

**What to build:**

A terminal recording (use `asciinema` or `termtosvg`) showing:
1. `pip install metronome fleet-agent plato-core`
2. `docker-compose up`
3. Dashboard at `localhost:8080` (screen capture of browser)
4. 3 agents running, all IN_BAND
5. Kill one agent, show the other two continue
6. Restart the agent, show reconvergence
7. Final `docker-compose down`

Length target: 3–5 minutes.

No voiceover needed. Use text captions in the terminal or overlay in post.

**Tests that must pass:**
```bash
# Play the recording back:
asciinema play demo.cast
# Must show all 7 scenes without error
```

**Deliverable:** `assets/demo-video.cast` (or `.svg`) committed. README links to it.

---

### Day 25 (Thu): Write the Blog Post

**What to build:**

`blog/fleet-metronome.md` — a public-facing explanation.

Target audience: Engineers who build multi-agent systems.

Key points:
- The problem: Coordinating 3+ agents without a central clock or constant heartbeat traffic.
- The insight: Simulate beats locally, gossip only when drift exceeds a deadband. O(0) steady-state messages.
- The demo: 3 agents, 1000 ticks, zero DESYNC, fraction arithmetic = zero drift accumulation.
- The code: `pip install metronome` and go.
- The invitation: Try it. Open an issue. Join the beta.

Tone: Humble, concrete, no hype. Cite the open problems honestly.

**Deliverable:** `blog/fleet-metronome.md` ready for publishing. Reviewed by at least one person for clarity.

---

### Day 26 (Fri): Open Beta Infrastructure

**What to build:**

Set up the infrastructure for external users.

1. **Discord or Telegram channel** for beta support.
2. **GitHub issue template** for bug reports:
   - `---
     name: Bug report
     about: Something broke in the fleet
     ---
     **Agent count:**
     **Topology:**
     **Error:**
     **Logs:**
     `
3. **Beta signup form** (Google Form or GitHub Discussion):
   - Name, email, use case, fleet size.
4. **Beta release on GitHub:**
   - Tag `v0.1.0-beta`.
   - Release notes with install instructions.
   - Attach the demo video.

**Deliverable:** GitHub release `v0.1.0-beta` published. 5 people signed up.

---

### Day 27 (Sat): First Beta Users Run Their Own Agent

**What to build:**

Onboard the first 3 beta users.

For each user:
1. Send them the GitHub release link.
2. They run `pip install metronome`.
3. They run `docker-compose up`.
4. They report back: did it work? What broke?

Track issues in a `BETA-FEEDBACK.md` file:
```markdown
## Beta User 1: Alice
- OS: macOS 14
- Issue: Port 9001 already in use
- Fix: Added port-auto-discovery to agent_process.py
- Status: RESOLVED

## Beta User 2: Bob
- OS: Ubuntu 22.04
- Issue: Dashboard didn't load (firewall)
- Fix: Documented firewall rule in GETTING-STARTED.md
- Status: DOCUMENTED
```

**Deliverable:** 3 beta users have run the demo. At least 1 has run it on macOS, 1 on Linux.

---

### Day 28 (Sun): Collect Feedback, Triage

**What to build:**

Synthesize all feedback into a prioritized issue list.

Use the `BETA-FEEDBACK.md` to create GitHub issues:
- P0 (blockers): Crashes, install failures, data loss.
- P1 (major): Performance issues, missing features.
- P2 (minor): UI polish, docs clarity.

Close the loop with beta users: reply to each one with their issue number and expected fix date.

**Deliverable:** GitHub issues created for all P0 and P1 feedback. Users acknowledged.

---

### Day 29 (Mon): Iterate — Fix the Top 3 Issues

**What to build:**

Fix the top 3 issues from beta feedback.

Likely candidates based on my review and the demo state:
1. **"No module named 'holonomy_bridge'"** — Fix fleet-agent package discovery.
2. **"Dashboard doesn't update on macOS"** — Fix SSE or switch to WebSocket.
3. **"I don't know what T to pick"** — Add `MetronomeConfig.auto_fleet(n_agents)` that computes T based on expected network latency.

For each fix:
- Write a regression test.
- Commit the fix.
- Rebuild the wheel.
- Ask the affected beta user to verify.

**Tests that must pass:**
```bash
python -m pytest tests/test_beta_regression.py -v
# MUST PASS all 3 regression tests
```

**Deliverable:** 3 fixes committed. 3 regression tests green.

---

### Day 30 (Tue): Ship the Day-30 Release

**What to build:**

The Day-30 release is the first version you can show to an investor or a new engineer with confidence.

Release checklist:
```bash
[ ] Version bumped to 0.2.0 (or 1.0.0-beta.1)
[ ] CHANGELOG.md has entries for Days 1–30
[ ] All 6 packages rebuilt and uploaded to PyPI
[ ] Docker image published to GHCR or Docker Hub
[ ] GitHub release with:
    - Release notes
    - Demo video
    - Link to GETTING-STARTED.md
    - Known issues list (honest)
[ ] Tag: git tag v0.2.0 && git push origin v0.2.0
```

Final verification:
```bash
# In a fresh container:
pip install metronome==0.2.0 fleet-agent==0.2.3 plato-core==0.1.1
python -c "
from metronome import MetronomeAgent, MetronomeConfig, MockPlatoAdapter
cfg = MetronomeConfig.default_fleet('test', [])
agent = MetronomeAgent(cfg, MockPlatoAdapter())
for _ in range(100):
    agent.tick({})
print('Day 30 release: OK')
"
```

**Deliverable:** `v0.2.0` tagged. PyPI updated. GitHub release published. The 3-line quickstart works for a stranger.

---

## RISK: What Could Go Wrong

| Risk | Probability | Impact | Fallback |
|------|-------------|--------|----------|
| **PyPI upload blocked by name squatting or rate limit** | Medium | High (Week 1 slip) | Use TestPyPI for beta. Use `pip install --index-url https://test.pypi.org/simple/`. Ship locally with `pip install ./dist/*.whl` if needed. |
| **Real UDP networking fails on WSL/Docker** | High | High (Week 2 slip) | Fall back to Unix domain sockets on localhost. The metronome algorithm doesn't care about the transport. Document WSL networking limitations. |
| **OpenClaw heartbeat API incompatible with metronome tick** | Medium | Medium (Week 3 slip) | Run metronome as a standalone daemon. OpenClaw reads PLATO tiles for phase state. Decoupling is safer anyway. |
| **kimi1 CUDA unavailable** | High | Low (Week 3) | CPU fallback is already designed. Nerve grid runs on CPU. Performance degrades but correctness is preserved. |
| **Beta users find fundamental algorithm flaw** | Low | Catastrophic | If a user finds a case where drift diverges under the specified parameters, document it as a known limitation. Adjust `epsilon` and `delta` defaults. The architecture admits ε = δ/3 is a conjecture, not a theorem. |
| **No external beta users sign up** | Medium | Medium (Week 4 slip) | Recruit internally: Casey, other agents, friends. The goal is 3 users, not 300. |
| **24-hour soak test reveals memory leak** | Medium | High | Profile with `tracemalloc`. The most likely leak is unbounded `phase.jsonl` growth. Add log rotation: keep last 10,000 lines. |
| **Partition test reveals reconvergence failure** | Medium | High | If the fleet cannot reconverge after partition, the issue is likely stale `phi_0` inherited from pre-partition state. Fix: reset `phi_0` to current local time on partition heal detection. |

---

## SUCCESS CRITERIA: What Does "Done" Look Like at Day 30

**Technical:**
- [ ] `pip install metronome fleet-agent plato-core` works in a fresh venv.
- [ ] The 3-line quickstart runs without error.
- [ ] `demo/three-agent-demo/run_demo.py` uses real UDP sockets, not shared memory.
- [ ] 3 agents run on 3 separate processes (or machines) and synchronize.
- [ ] 24-hour soak test completes with zero DESYNC after initial convergence.
- [ ] Network partition is detected and healed automatically.
- [ ] Sunset/inheritance works end-to-end with real PLATO tiles.
- [ ] OpenClaw heartbeat drives the metronome tick.

**Product:**
- [ ] `docs/GETTING-STARTED.md` exists and a stranger can follow it.
- [ ] Demo video (3–5 min) recorded and linked from README.
- [ ] Blog post published.
- [ ] GitHub release `v0.2.0` tagged.
- [ ] 3+ beta users have run the demo.
- [ ] All P0 beta issues fixed.

**Honest assessment of what is NOT done at Day 30:**
- The 9-agent fleet is not deployed (only 3).
- The Rust holonomy-consensus engine is not necessarily faster than Python stubs (PyO3 binding may still be in progress).
- The 4-generation lifecycle with ε tightening is not validated (requires months of data).
- Tensor-MIDI is not validated for safety-critical timing (INT8 monotonicity remains UNKNOWN).
- The adaptive deadband safety conjecture is not proven.
- GUARD DSL safety specs are not compiled to FLUX bytecode.
- The full 170-repo ecosystem is not integrated (and should not be — focus is 6 packages).

These are not failures. They are the next 30 days.

---

*Engineering plan, not a vision doc. Every task above has a file path, a test command, and a deliverable. If a task is vague, it is not done. Type the code. Run the tests. Ship it.*
