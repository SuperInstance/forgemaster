"""
Benchmark suite for snapkit-v2 — before/after optimization comparison.
Reduced iteration counts to avoid O(n²) spectral hanging.
"""
import time
import random
import math
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

random.seed(42)

# ── Helpers ──

def bench(name, fn, iterations=100_000, warmup=100):
    """Run fn() `iterations` times, return (name, seconds, ops/sec)."""
    for _ in range(warmup):
        fn()
    t0 = time.perf_counter()
    for _ in range(iterations):
        fn()
    elapsed = time.perf_counter() - t0
    ops = iterations / elapsed
    return {"name": name, "elapsed": elapsed, "ops_sec": ops}


def fmt(r):
    return f"  {r['name']:55s} {r['elapsed']:8.4f}s  {r['ops_sec']:>12,.0f} ops/s"


# ── Test data generation ──

N_POINTS = 10_000
N_TS = 10_000

points = [complex(random.uniform(-100, 100), random.uniform(-100, 100)) for _ in range(N_POINTS)]
xy_points = [(random.uniform(-100, 100), random.uniform(-100, 100)) for _ in range(N_POINTS)]
timestamps = [random.uniform(0, 10000) for _ in range(N_TS)]
series_500 = [random.gauss(0, 1) for _ in range(500)]
series_5k = [random.gauss(0, 1) for _ in range(5000)]

all_results = {}

print("=" * 80)
print("SNAPKIT-V2 BASELINE BENCHMARK")
print("=" * 80)

# ── EISENSTEIN VORONOI ──
print("\n── VORONOI SNAP ──")
from snapkit.eisenstein_voronoi import eisenstein_snap_naive, eisenstein_snap_voronoi, snap_distance

x0, y0 = xy_points[0]
results = []
results.append(bench("snap_naive (single)", lambda: eisenstein_snap_naive(x0, y0), 200_000))
results.append(bench("snap_voronoi (single)", lambda: eisenstein_snap_voronoi(x0, y0), 100_000))
results.append(bench("snap_voronoi (1K unique)", lambda: [eisenstein_snap_voronoi(p[0], p[1]) for p in xy_points[:1000]], 100))
results.append(bench("snap_distance (single)", lambda: snap_distance(x0, y0, 5, 3), 500_000))
for r in results: print(fmt(r))
all_results["voronoi"] = results

# ── EISENSTEIN ──
print("\n── EISENSTEIN ──")
from snapkit.eisenstein import eisenstein_round_naive, eisenstein_round, eisenstein_snap, EisensteinInteger

z0 = points[0]
results = []
results.append(bench("eisenstein_round_naive (single)", lambda: eisenstein_round_naive(z0), 100_000))
results.append(bench("eisenstein_round (single)", lambda: eisenstein_round(z0), 50_000))
results.append(bench("eisenstein_snap (single)", lambda: eisenstein_snap(z0), 50_000))
e1 = EisensteinInteger(5, 3)
e2 = EisensteinInteger(7, -2)
results.append(bench("EisensteinInteger multiply", lambda: e1 * e2, 500_000))
results.append(bench("EisensteinInteger.norm_squared", lambda: e1.norm_squared, 1_000_000))
results.append(bench("EisensteinInteger.complex", lambda: e1.complex, 1_000_000))
for r in results: print(fmt(r))
all_results["eisenstein"] = results

# ── TEMPORAL ──
print("\n── TEMPORAL ──")
from snapkit.temporal import BeatGrid, TemporalSnap

grid = BeatGrid(period=480, phase=0, t_start=0)
t0 = timestamps[0]
results = []
results.append(bench("BeatGrid.nearest_beat (single)", lambda: grid.nearest_beat(t0), 200_000))
results.append(bench("BeatGrid.snap (single)", lambda: grid.snap(t0), 200_000))
results.append(bench("BeatGrid.snap (10K unique)", lambda: [grid.snap(t) for t in timestamps[:1000]], 50))
results.append(bench("BeatGrid.beats_in_range", lambda: grid.beats_in_range(0, 10000), 50_000))
snap = TemporalSnap(grid=grid, tolerance=0.1)
results.append(bench("TemporalSnap.observe (single)", lambda: snap.observe(t0, random.gauss(0, 1)), 50_000))
for r in results: print(fmt(r))
all_results["temporal"] = results

# ── SPECTRAL (reduced iterations for O(n²) functions) ──
print("\n── SPECTRAL ──")
from snapkit.spectral import entropy, autocorrelation, hurst_exponent, spectral_summary

results = []
results.append(bench("entropy (500 pts, 10 bins)", lambda: entropy(series_500), 1_000))
results.append(bench("autocorrelation (500 pts, lag=50)", lambda: autocorrelation(series_500, max_lag=50), 50))
results.append(bench("hurst_exponent (500 pts)", lambda: hurst_exponent(series_500), 50))
results.append(bench("spectral_summary (500 pts)", lambda: spectral_summary(series_500), 10))
# 5K benchmarks run separately due to O(n²) cost
for r in results: print(fmt(r))
all_results["spectral"] = results

# ── CONNECTOME ──
print("\n── CONNECTOME ──")
from snapkit.connectome import TemporalConnectome

tc = TemporalConnectome(threshold=0.3, max_lag=5)
for name in ["bridge", "engineering", "medbay", "cargo", "quarters"]:
    tc.add_room(name, [random.gauss(0, 1) for _ in range(200)])
results = []
results.append(bench("Connectome.analyze (5 rooms, 200 pts)", lambda: tc.analyze(), 500))
tc2 = TemporalConnectome(threshold=0.3, max_lag=10)
for i in range(20):
    tc2.add_room(f"room_{i}", [random.gauss(0, 1) for _ in range(500)])
results.append(bench("Connectome.analyze (20 rooms, 500 pts)", lambda: tc2.analyze(), 10))
for r in results: print(fmt(r))
all_results["connectome"] = results

# ── MIDI ──
print("\n── MIDI / FLUX-TENSOR ──")
from snapkit.midi import FluxTensorMIDI, TempoMap

conductor = FluxTensorMIDI()
for i in range(8):
    conductor.add_room(f"room_{i}", channel=i)
results = []
results.append(bench("FluxTensorMIDI.note_on", lambda: conductor.note_on("room_0", tick=480, note=60), 50_000))
# Render
for i in range(100):
    conductor.note_on(f"room_{i % 8}", tick=i * 480, note=60 + i)
    conductor.note_off(f"room_{i % 8}", tick=i * 480 + 240, note=60 + i)
results.append(bench("FluxTensorMIDI.render (100 events)", lambda: conductor.render(), 10_000))
results.append(bench("FluxTensorMIDI.quantize (100 events)", lambda: conductor.quantize(120), 5_000))
tm = TempoMap()
tm.set_tempo(4800, 140)
tm.set_tempo(9600, 100)
results.append(bench("TempoMap.tick_to_seconds", lambda: tm.tick_to_seconds(7200), 100_000))
results.append(bench("TempoMap.seconds_to_tick", lambda: tm.seconds_to_tick(30.0), 100_000))
for r in results: print(fmt(r))
all_results["midi"] = results

print("\n" + "=" * 80)
print("BENCHMARK COMPLETE")
print("=" * 80)

# Save results for comparison
with open(os.path.join(os.path.dirname(__file__), 'baseline_results.json'), 'w') as f:
    json.dump(all_results, f, indent=2, default=str)
print(f"\nResults saved to benchmarks/baseline_results.json")
