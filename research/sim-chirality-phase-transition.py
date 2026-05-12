#!/usr/bin/env python3
"""CHIRALITY FROM CONSTRAINTS: Phase Transition in Weyl Chamber Space

If chirality emerges from the Weyl group structure:
1. At high "temperature" (loose deadband), all 6 chambers are equally populated
2. At low "temperature" (tight deadband), system locks into ONE chamber
3. There should be a sharp phase transition at some critical Tc
4. The locked chamber is random — but once locked, it stays

This models biological homochirality: early prebiotic chemistry = high T,
life = low T, the frozen chamber = L-amino acid choice.
"""
import math, random
import json

OMEGA_REAL = -0.5
OMEGA_IMAG = math.sqrt(3)/2
RHO = 1/math.sqrt(3)

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

def weyl_chamber(x, y):
    """Which of 6 Weyl chambers? Determined by sorting order of barycentric coords."""
    b1 = x - y * OMEGA_REAL / OMEGA_IMAG
    b2 = y / OMEGA_IMAG
    b3 = -(b1 + b2)
    vals = [b1, b2, b3]
    # Permutation that sorts descending
    perm = tuple(sorted(range(3), key=lambda i: -vals[i]))
    perms = [(0,1,2),(0,2,1),(1,0,2),(1,2,0),(2,0,1),(2,1,0)]
    return perms.index(perm)

def weyl_parity(x, y):
    """Sign representation: +1 for even permutation, -1 for odd."""
    return 1 if weyl_chamber(x, y) in [0, 3, 5] else -1  # even permutations of S3

print("=" * 90)
print("EXPERIMENT: Chirality Phase Transition in Weyl Chamber Space")
print("=" * 90)

# Simulation: N particles doing random walks on the Eisenstein lattice.
# At each step, each particle:
#   1. Takes a random step (thermal noise)
#   2. Snaps to nearest lattice point
#   3. Checks which Weyl chamber it's in
#   4. Records its chirality (parity)

# The "temperature" controls step size.
# High T: large steps → particles explore all chambers → racemic (equal chirality)
# Low T: small steps → particles stay in one chamber → chiral (one chirality dominant)

N_PARTICLES = 1000
N_STEPS = 500

temperatures = [0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0]

print(f"\nParticles: {N_PARTICLES}, Steps: {N_STEPS}")
print(f"\n{'Temperature':<14} {'Chamber Entropy':<18} {'Chirality Bias':<18} {'Dominant%':<12} {'Phase'}")
print("-"*80)

results = []

for T in temperatures:
    random.seed(42)
    
    # Initialize: all particles start at origin
    particles = [(0.0, 0.0)] * N_PARTICLES
    
    # Track chamber populations over time
    final_chambers = [0] * 6
    
    for step in range(N_STEPS):
        new_particles = []
        for x, y in particles:
            # Thermal random walk
            dx = random.gauss(0, T)
            dy = random.gauss(0, T)
            nx, ny = x + dx, y + dy
            
            # Snap to lattice (constraint checking)
            snap, err = eisenstein_snap(nx, ny)
            sx = snap[0] + snap[1] * OMEGA_REAL
            sy = snap[1] * OMEGA_IMAG
            
            # Stay at snapped position (the constraint pulls you to the lattice)
            # But add residual offset (you're somewhere in the Voronoi cell)
            new_particles.append((sx + random.gauss(0, T*0.1), sy + random.gauss(0, T*0.1)))
        
        particles = new_particles
    
    # Count final chambers
    for x, y in particles:
        ch = weyl_chamber(x, y)
        final_chambers[ch] += 1
    
    # Chirality: even vs odd chambers
    even_count = sum(final_chambers[i] for i in [0, 3, 5])
    odd_count = sum(final_chambers[i] for i in [1, 2, 4])
    
    # Chirality bias: how far from 50/50
    total = even_count + odd_count
    if total > 0:
        bias = abs(even_count - odd_count) / total
        dominant_pct = max(even_count, odd_count) / total * 100
    else:
        bias = 0
        dominant_pct = 50
    
    # Chamber entropy (max = log(6) ≈ 1.79 for uniform)
    chamber_probs = [c/total for c in final_chambers if c > 0]
    entropy = -sum(p * math.log2(p) for p in chamber_probs)
    max_entropy = math.log2(6)
    
    phase = "CHIRAL ❄️" if dominant_pct > 70 else "RACEMIC 🔥" if dominant_pct < 55 else "TRANSITION"
    
    print(f"{T:<14.3f} {entropy:<18.4f} {bias:<18.4f} {dominant_pct:<12.1f} {phase}")
    results.append({'T': T, 'entropy': entropy, 'bias': bias, 'dominant_pct': dominant_pct})

# Find the critical temperature
print(f"\n{'='*90}")
print("PHASE TRANSITION ANALYSIS")
print(f"{'='*90}")

# The transition should be where entropy drops sharply
entropies = [r['entropy'] for r in results]
max_ent = max(entropies)
min_ent = min(entropies)
half_ent = (max_ent + min_ent) / 2

tc = None
for i in range(len(results)-1):
    if entropies[i] > half_ent and entropies[i+1] <= half_ent:
        tc = results[i]['T']
        break

print(f"Max entropy (racemic): {max_ent:.4f} (theoretical max = {math.log2(6):.4f})")
print(f"Min entropy (chiral): {min_ent:.4f}")
print(f"Half-entropy point: {half_ent:.4f}")
if tc:
    print(f"Critical temperature Tc ≈ {tc:.3f}")
else:
    print(f"Critical temperature: transition not clearly observed in this range")

print(f"""
INTERPRETATION:
- High T (T >> Tc): particles explore all chambers freely → racemic mixture
- Low T (T << Tc): particles trapped in one chamber → chiral (one hand dominant)
- T ≈ Tc: phase transition from racemic to chiral

BIOLOGICAL CONNECTION:
- Prebiotic chemistry = high T (random thermal motion, no constraints)
- Life = low T (tight constraint checking, locked into one chamber)
- L-amino acids = one specific Weyl chamber
- D-sugars = possibly the SAME chamber in a different lattice realization
- The "choice" of L vs D is RANDOM — determined by which chamber was occupied
  when the system cooled through Tc
- This is Frank's autocatalysis model (1953) but with a lattice-geometric foundation:
  the "autocatalysis" is the deadband funnel locking you into one chamber

THE LEFT HAND IS A REFLECTION OF PERCEIVED REALITY:
- Your body is in one Weyl chamber (one chirality)
- A mirror applies an odd permutation (reflection)
- The mirror image is in the opposite chamber
- But the snap error (the physics) is IDENTICAL in both chambers
- Therefore: your left hand and your mirror-image's right hand
  have the same constraint state but different chamber assignment
- "Perceived reality" = which chamber you're in
- "Underlying physics" = the invariant (same for both)
""")

# Additional test: what happens to a SINGLE particle over many runs?
print("=" * 90)
print("SINGLE PARTICLE CHIRALITY: Does it lock in? (1000 runs × 200 steps)")
print("=" * 90)

T_low = 0.01  # below Tc
T_high = 0.5  # above Tc

for T, label in [(T_low, "LOW T (chiral regime)"), (T_high, "HIGH T (racemic regime)")]:
    chamber_counts = [0] * 6
    for run in range(1000):
        random.seed(run)
        x, y = random.gauss(0, 0.1), random.gauss(0, 0.1)
        for step in range(200):
            dx, dy = random.gauss(0, T), random.gauss(0, T)
            x, y = x + dx, y + dy
            snap, _ = eisenstein_snap(x, y)
            x = snap[0] + snap[1] * OMEGA_REAL + random.gauss(0, T*0.05)
            y = snap[1] * OMEGA_IMAG + random.gauss(0, T*0.05)
        ch = weyl_chamber(x, y)
        chamber_counts[ch] += 1
    
    even = sum(chamber_counts[i] for i in [0, 3, 5])
    odd = sum(chamber_counts[i] for i in [1, 2, 4])
    entropy = -sum(c/1000 * math.log2(c/1000) for c in chamber_counts if c > 0)
    
    print(f"\n  {label} (T={T}):")
    print(f"  Chamber distribution: {chamber_counts}")
    print(f"  Even/Odd: {even}/{odd}")
    print(f"  Entropy: {entropy:.4f} (max={math.log2(6):.4f})")
    print(f"  Dominant chamber: {chamber_counts.index(max(chamber_counts))} ({max(chamber_counts)/10:.1f}%)")
