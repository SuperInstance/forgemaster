# snapkit

Constraint geometry snap toolkit — Eisenstein, temporal, spectral, connectome, MIDI.

Zero external dependencies. stdlib only. Python ≥3.10.

## Install

```bash
pip install snapkit
```

## Quickstart

### Eisenstein Lattice Snap

```python
from snapkit import EisensteinInteger, eisenstein_snap, eisenstein_round

# Snap a complex number to the nearest Eisenstein integer
z = complex(0.3, 0.7)
nearest, distance, is_snap = eisenstein_snap(z, tolerance=0.5)
print(f"{nearest} — distance={distance:.4f}, snapped={is_snap}")

# Round directly
e = EisensteinInteger.from_complex(z)
print(f"Eisenstein integer: {e}, norm²={e.norm_squared}")
```

### Temporal Snap (Beat Grid + T-minus-0)

```python
from snapkit import BeatGrid, TemporalSnap

grid = BeatGrid(period=1.0, phase=0.0)
snap = TemporalSnap(grid, tolerance=0.1, t0_threshold=0.05)

# Feed observations
result = snap.observe(t=1.04, value=0.3)
print(f"On beat: {result.is_on_beat}, T-0: {result.is_t_minus_0}, offset: {result.offset:.3f}")
```

### Spectral Analysis

```python
from snapkit import spectral_summary
import random

signal = [random.gauss(0, 1) for _ in range(500)]
summary = spectral_summary(signal)
print(f"Entropy: {summary.entropy_bits:.2f} bits")
print(f"Hurst: {summary.hurst:.3f} (stationary: {summary.is_stationary})")
```

### Connectome (Room Coupling Detection)

```python
from snapkit import TemporalConnectome

conn = TemporalConnectome(threshold=0.3, max_lag=5)
conn.add_room("alpha", [0.1, 0.5, 0.3, 0.8, 0.2])
conn.add_room("beta",  [0.2, 0.4, 0.4, 0.7, 0.3])

result = conn.analyze()
for pair in result.significant:
    print(f"{pair.room_a} ↔ {pair.room_b}: {pair.coupling.value} (r={pair.correlation:.3f})")
```

### MIDI (FLUX-Tensor Protocol)

```python
from snapkit import FluxTensorMIDI, TempoMap

flux = FluxTensorMIDI(TempoMap(ticks_per_beat=480, initial_bpm=120))
piano = flux.add_room("piano", channel=0)
drums = flux.add_room("drums", channel=9)

flux.note_on("piano", tick=0, note=60, velocity=100)
flux.note_off("piano", tick=480, note=60)
flux.note_on("drums", tick=0, note=36)

events = flux.render()  # sorted by tick
quantized = flux.quantize(grid=120)
```

## API Reference

### `snapkit.eisenstein` — Eisenstein Lattice

| Symbol | Description |
|--------|-------------|
| `EisensteinInteger` | Frozen dataclass: `a + bω` on the A₂ lattice |
| `eisenstein_round(z)` | Round complex → nearest Eisenstein integer |
| `eisenstein_snap(z, tol)` | Snap with tolerance check |
| `eisenstein_distance(z1, z2)` | Lattice distance between two complex points |
| `eisenstein_snap_batch(points, tol)` | Vectorized snap |

### `snapkit.eisenstein_voronoi` — Voronoï Cell Snap

| Symbol | Description |
|--------|-------------|
| `eisenstein_snap_voronoi(x, y)` | True nearest-neighbor via A₂ Voronoï cell |
| `eisenstein_snap_batch(points)` | Vectorized Voronoï snap |

### `snapkit.temporal` — Beat Grid & T-minus-0

| Symbol | Description |
|--------|-------------|
| `BeatGrid` | Periodic time grid with snap |
| `TemporalSnap` | Beat snap + T-minus-0 detection |
| `TemporalResult` | Snap result (frozen dataclass) |

### `snapkit.spectral` — Signal Analysis

| Symbol | Description |
|--------|-------------|
| `entropy(data, bins)` | Shannon entropy via histogram |
| `hurst_exponent(data)` | R/S analysis Hurst exponent |
| `autocorrelation(data, max_lag)` | Normalized autocorrelation |
| `spectral_summary(data)` | Full spectral summary |
| `SpectralSummary` | Frozen dataclass with entropy, Hurst, ACF, stationarity |

### `snapkit.connectome` — Room Coupling

| Symbol | Description |
|--------|-------------|
| `TemporalConnectome` | Coupled/anti-coupled room detection |
| `ConnectomeResult` | Analysis result with adjacency matrix, Graphviz export |
| `RoomPair` | Coupled pair (frozen dataclass) |
| `CouplingType` | Enum: `COUPLED`, `ANTI_COUPLED`, `UNCOUPLED` |

### `snapkit.midi` — FLUX-Tensor-MIDI

| Symbol | Description |
|--------|-------------|
| `FluxTensorMIDI` | Conductor: rooms, events, quantize, render |
| `TempoMap` | Tick↔seconds with tempo changes |
| `Room` | Musician/channel with note helpers |
| `MIDIEvent` | Discrete timing event (frozen dataclass) |

## Performance

- Voronoï snap uses squared-distance comparison (no sqrt in hot path)
- BeatGrid uses precomputed inverse period
- Autocorrelation uses local variable caching
- All dataclasses use `__slots__` / `frozen=True`
- Batch operations on all modules

## License

MIT
