# metronome-sync

Anti-fragile PTP clock synchronization for distributed agent fleets. Uses exact `Fraction` arithmetic — no floating-point drift, ever.

## Why?

Distributed agent fleets need coordinated timing. NTP isn't good enough (millisecond jitter). PTP hardware is expensive. `metronome-sync` gives you sub-tick synchronization between processes using nothing but UDP and Python's `Fraction` type.

The key insight: if you represent time as exact fractions (numerator/denominator), you never accumulate floating-point rounding errors. Combined with Laman graph topologies (generically rigid — minimally connected but structurally stable), you get anti-fragile sync that actually gets *more* accurate under perturbation.

## Quick Start

```python
from fractions import Fraction
from metronome_sync import MetronomeClient, FleetConfig, PtpMode

# Create a client
client = MetronomeClient(FleetConfig(
    name="agent-1",
    peers=["agent-2:9000", "agent-3:9000"],
    mode=PtpMode.PTP,
))
client.start()

# Get exact time — always a Fraction, never a float
t = client.now()  # Fraction(12345, 1)

# Apply PTP correction from a peer measurement
client.apply_ptp_offset(
    local_time=Fraction(100),
    remote_time=Fraction(105),
    rtt=Fraction(2),
)

client.stop()
```

## How It Works

### Fraction Clock

Every agent maintains a `FractionClock`:
- `true_time` — monotonic counter, advanced by `tick()`
- `offset` — accumulated drift (drift_rate × ticks)
- `local_time = true_time + offset`

All arithmetic is exact. No `0.1 + 0.2 ≠ 0.3` surprises.

### PTP Offset Estimation

Four modes:

| Mode | Algorithm | Use Case |
|------|-----------|----------|
| `NAIVE` | `remote - local` | Baseline (breaks under latency) |
| `CRISTIAN` | Cristian's algorithm (RTT/2) | Low-latency LANs |
| `PTP` | IEEE 1588 style | Production default |
| `EXPONENTIAL` | EMA of PTP offsets | Smooth corrections |

The default `PTP` mode estimates offset as:

```
offset = remote_time - (local_time + RTT/2)
```

Weighted by peer staleness — fresher samples contribute more.

### Laman Topologies

For N agents, the fleet builds a Laman graph with exactly `2N - 3` edges. These are *minimally rigid*: removing any edge reduces rigidity, but the graph is stable under perturbation. This is the graph-theoretic foundation for anti-fragile synchronization.

```python
topo = MetronomeClient.build_fleet_topology(n_agents=5)
# {'n': 5, 'edges': [(0,1), (0,2), (1,2), (1,3), (2,3), (2,4), (3,4)],
#  'is_rigid': True, 'peers': {0: [1, 2], 1: [0, 2, 3], ...}}
```

### Tensor-MIDI Wire Format

Clock state is encoded as compact byte sequences using INT8 quantization for drift values and 8-byte Fraction serialization for timestamps. A full clock snapshot is 17 bytes.

### Sunset and Inheritance

When a cadence caller (leader) retires, it produces a *sunset* payload — complete calibration state serialized as PLATO tiles. The successor *inherits* this state and takes over seamlessly with zero calibration loss.

## Architecture

```
metronome_sync/
├── client.py          # MetronomeClient + FleetConfig
├── fraction_clock.py  # Exact-arithmetic clock
├── ptp.py            # PTP offset estimation (4 modes)
├── topology.py       # Laman graph builder
├── tensor_midi.py    # INT8 wire encoding
├── protocol.py       # UDP message protocol
└── sunset.py         # Retirement + inheritance
```

## Installation

```bash
pip install metronome-sync
```

Or from source:

```bash
git clone https://github.com/SuperInstance/metronome-sync.git
cd metronome-sync
pip install -e .
```

## Running Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## License

MIT
