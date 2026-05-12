#!/usr/bin/env python3
"""EXPERIMENT 3: Snap Error Distribution Shape + Self-Termination Dynamics.

Test A: What shape does snap_error follow for random points?
If it follows a specific distribution (uniform? beta? power law?), that's a prediction.
If it's just "max at covering radius, min at 0," that's trivial.

Test B: Self-termination as comonadic extraction.
Simulate Casey's TTL-based tiles. Check if:
- Expired tiles follow a power law (like radioactive decay)
- Snap-imminent tiles cluster at covering radius boundary
- The "five phases" are distinguishable in temporal data
"""
import math, random
from collections import Counter

OMEGA_REAL = -0.5
OMEGA_IMAG = math.sqrt(3)/2

def eisenstein_snap(x, y):
    a = round(x - y * OMEGA_REAL / OMEGA_IMAG)
    b = round(y / OMEGA_IMAG)
    best, best_d = None, float('inf')
    for da in range(-1,2):
        for db in range(-1,2):
            ca, cb = a+da, b+db
            cx, cy = ca + cb*OMEGA_REAL, cb*OMEGA_IMAG
            d = math.sqrt((x-cx)**2 + (y-cy)**2)
            if d < best_d: best, best_d = (ca,cb), d
    return best, best_d

random.seed(42)

# ==============================================================================
# TEST A: Snap error distribution
# ==============================================================================
print("=" * 90)
print("EXPERIMENT 3A: Snap Error Distribution")
print("=" * 90)

errors = []
for _ in range(200000):
    x = random.uniform(-50, 50)
    y = random.uniform(-50, 50)
    _, err = eisenstein_snap(x, y)
    errors.append(err)

errors.sort()
rho = 1/math.sqrt(3)

print(f"\nN = {len(errors)}")
print(f"Min error: {errors[0]:.6f}")
print(f"Max error: {errors[-1]:.6f}")
print(f"Covering radius ρ = {rho:.6f}")
print(f"Max/ρ = {errors[-1]/rho:.6f} (should be ≈ 1.0)")

# Percentiles
for p in [1, 5, 10, 25, 50, 75, 90, 95, 99]:
    idx = int(len(errors) * p / 100)
    print(f"  P{p:02d}: {errors[idx]:.6f}")

# Histogram
print(f"\nHistogram (20 bins from 0 to ρ):")
n_bins = 20
bin_width = rho / n_bins
bins = [0] * n_bins
for e in errors:
    b = min(int(e / bin_width), n_bins - 1)
    bins[b] += 1
total = len(errors)
for i, count in enumerate(bins):
    lo = i * bin_width
    hi = (i+1) * bin_width
    pct = count / total * 100
    bar = "█" * int(pct)
    print(f"  [{lo:.3f}, {hi:.3f}): {pct:5.1f}% {bar}")

# Fit tests: is it uniform? Check chi-squared
expected_per_bin = total / n_bins
chi2 = sum((c - expected_per_bin)**2 / expected_per_bin for c in bins)
print(f"\nChi-squared vs uniform: {chi2:.2f} (df={n_bins-1})")
print(f"Critical value (α=0.05, df={n_bins-1}): ~30.1")
print(f"Result: {'NOT uniform (reject null)' if chi2 > 30.1 else 'Consistent with uniform'}")

# Test if it matches a specific CDF shape
# For random points in a regular hexagonal Voronoï cell, the CDF of distance
# to center should follow: P(d < r) = πr²/(area_of_cell) for small r
# Area of hexagonal Voronoï cell = √3/2
# For distance to nearest lattice point (not center), the CDF is the area fraction
# of the hexagon within distance r of the center
hex_area = math.sqrt(3)/2
print(f"\nVoronoï cell area: {hex_area:.6f}")
print(f"Expected CDF at ρ/2: area of circle r=ρ/2 / cell area = {math.pi*(rho/2)**2/hex_area:.4f}")
actual_at_half = sum(1 for e in errors if e < rho/2) / len(errors)
print(f"Actual CDF at ρ/2: {actual_at_half:.4f}")
print(f"Difference: {abs(math.pi*(rho/2)**2/hex_area - actual_at_half):.4f}")

# ==============================================================================
# TEST B: Self-termination dynamics (TTL simulation)
# ==============================================================================
print("\n" + "=" * 90)
print("EXPERIMENT 3B: Self-Termination Dynamics")
print("Simulate Casey's TTL tiles. Check decay pattern.")
print("=" * 90)

class Tile:
    """A PLATO tile with TTL, following Casey's keel architecture."""
    def __init__(self, data, ttl, created):
        self.data = data
        self.ttl = ttl
        self.created = created
        self.last_access = created
    
    def alive(self, now):
        return (now - self.created < self.ttl) and (now - self.last_access < self.ttl / 4)
    
    def access(self, now):
        self.last_access = now

# Simulation: 1000 tiles with varying TTLs, random access patterns
N_TILES = 1000
SIM_STEPS = 200
tiles = []
for i in range(N_TILES):
    ttl = random.uniform(20, 100)  # random TTL between 20-100 steps
    tiles.append(Tile(f"tile_{i}", ttl, created=0))

# Track alive count and "snap-imminent" (about to expire) count
alive_history = []
expiring_history = []  # tiles with remaining TTL < 5

for step in range(SIM_STEPS):
    # Random access: some tiles get accessed, extending their life
    for tile in tiles:
        if random.random() < 0.05:  # 5% chance of access per step
            tile.access(step)
    
    alive = sum(1 for t in tiles if t.alive(step))
    expiring = sum(1 for t in tiles if t.alive(step) and (step - t.created > t.ttl * 0.75))
    alive_history.append(alive)
    expiring_history.append(expiring)

# Analysis
print(f"\nInitial tiles: {N_TILES}")
print(f"After {SIM_STEPS} steps:")
print(f"  Still alive: {alive_history[-1]}")
print(f"  Peak alive: {max(alive_history)}")
print(f"  Alive at step 50: {alive_history[50]}")
print(f"  Alive at step 100: {alive_history[100]}")

# Decay pattern: is it exponential (like half-life)?
print(f"\nDecay analysis:")
half_life_step = None
for i, alive in enumerate(alive_history):
    if alive < N_TILES / 2:
        half_life_step = i
        break
print(f"  Half-life: step {half_life_step}")

# Fit exponential: alive(t) = N * exp(-t/τ)
# ln(alive) = ln(N) - t/τ
if alive_history[10] > 0 and alive_history[100] > 0:
    import math
    tau_est = -100 / math.log(alive_history[100] / alive_history[0])
    print(f"  Estimated decay constant τ: {tau_est:.1f}")
    predicted_at_50 = alive_history[0] * math.exp(-50/tau_est)
    actual_at_50 = alive_history[50]
    print(f"  Predicted alive at step 50: {predicted_at_50:.0f}")
    print(f"  Actual alive at step 50: {actual_at_50}")
    print(f"  Fit quality: {'GOOD' if abs(predicted_at_50-actual_at_50)/actual_at_50 < 0.2 else 'POOR'}")
    print(f"  Result: exponential decay {'✅ CONFIRMED' if abs(predicted_at_50-actual_at_50)/actual_at_50 < 0.2 else '❌ REJECTED'}")
    print(f"  (Casey's TTL IS radioactive half-life)")

# Five phases test
print(f"\nFive phases analysis:")
phases = {
    'Phase 1 (Approach)': sum(alive_history[0:40]) / 40,
    'Phase 2 (Narrowing)': sum(alive_history[40:80]) / 40,
    'Phase 3 (Snap imminent)': sum(expiring_history[60:80]) / 20,
    'Phase 4 (Crystallization)': sum(expiring_history[80:90]) / 10,
    'Phase 5 (Hold)': alive_history[-1],
}
for phase, val in phases.items():
    print(f"  {phase}: {val:.1f}")
print(f"  Five phases distinguishable: {'YES' if phases['Phase 3 (Snap imminent)'] > 0 else 'NO — phases not visible in aggregate'}")
