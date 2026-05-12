#!/usr/bin/env python3
"""SIMULATION: Optimal Deadband Funnel Shape for Right-Skewed Snap Errors

The snap error CDF is P(d < r) ≈ πr²/A. This means errors are right-skewed.
Current deadband: exponential δ(t) = ρ·exp(-αt)
Proposed: square-root δ(t) = √(A·(1-t)/π) matching the error distribution

Question: which funnel shape minimizes convergence cost?
"""
import math, random, time

OMEGA_REAL = -0.5
OMEGA_IMAG = math.sqrt(3)/2
RHO = 1/math.sqrt(3)
CELL_AREA = math.sqrt(3)/2

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
N_POINTS = 50000

# Generate test points and their snap targets
points = []
for _ in range(N_POINTS):
    x = random.uniform(-5, 5)
    y = random.uniform(-5, 5)
    target, snap_err = eisenstein_snap(x, y)
    tx = target[0] + target[1] * OMEGA_REAL
    ty = target[1] * OMEGA_IMAG
    points.append((x, y, tx, ty, snap_err))

print("=" * 90)
print("FUNNEL SHAPE COMPARISON — Optimizing for Right-Skewed Snap Errors")
print(f"N = {N_POINTS} random points, ρ = {RHO:.4f}, A = {CELL_AREA:.4f}")
print("=" * 90)

funnels = {
    'Exponential (α=5)': lambda t: RHO * math.exp(-5 * t),
    'Exponential (α=3)': lambda t: RHO * math.exp(-3 * t),
    'Square-root (√(A(1-t)/π))': lambda t: math.sqrt(max(CELL_AREA * (1-t) / math.pi, 0.0001)),
    'Linear (ρ(1-t))': lambda t: RHO * (1 - t),
    'Inverse (ρ/(1+5t))': lambda t: RHO / (1 + 5*t),
    'Quadratic (ρ(1-t)²)': lambda t: RHO * (1-t)**2,
}

SNAP_THRESHOLD = 0.01
MAX_STEPS = 200

results = {}

for name, funnel in funnels.items():
    total_steps = 0
    total_info_cost = 0
    total_precision_energy = 0
    snapped_count = 0
    steps_list = []
    
    for x, y, tx, ty, initial_err in points:
        cx, cy = x, y
        steps = 0
        info_cost = 0
        prec_energy = 0
        
        for step in range(MAX_STEPS):
            t = step / MAX_STEPS
            deadband = funnel(t)
            
            if deadband < 0.0001:
                break
            
            # Current distance to target
            dx, dy = tx - cx, ty - cy
            dist = math.sqrt(dx*dx + dy*dy)
            
            # Snap check
            if dist < SNAP_THRESHOLD:
                snapped_count += 1
                steps_list.append(step)
                break
            
            # Precision feeling
            phi = 1.0 / deadband
            prec_energy += phi * (1.0/MAX_STEPS)
            info_cost += phi
            
            # Move toward target proportional to 1/deadband (faster when funnel narrows)
            move_speed = 0.02 * phi / (1.0/RHO)  # normalized by base precision
            if dist > 0:
                cx += dx / dist * move_speed
                cy += dy / dist * move_speed
            
            steps = step + 1
        
        total_steps += steps
        total_info_cost += info_cost
        total_precision_energy += prec_energy
    
    results[name] = {
        'mean_steps': total_steps / N_POINTS,
        'snapped_pct': snapped_count / N_POINTS * 100,
        'mean_info_cost': total_info_cost / N_POINTS,
        'mean_prec_energy': total_precision_energy / N_POINTS,
        'median_steps': sorted(steps_list)[len(steps_list)//2] if steps_list else MAX_STEPS,
    }

print(f"\n{'Funnel Shape':<35} {'Mean Steps':<12} {'Median':<8} {'Snapped%':<10} {'Info Cost':<12} {'Prec Energy'}")
print("-"*95)

# Sort by mean steps (lower is better)
for name, r in sorted(results.items(), key=lambda x: x[1]['mean_steps']):
    marker = " ← BEST" if r['mean_steps'] == min(r2['mean_steps'] for r2 in results.values()) else ""
    marker += " ← WORST" if r['mean_steps'] == max(r2['mean_steps'] for r2 in results.values()) else ""
    print(f"{name:<35} {r['mean_steps']:<12.1f} {r['median_steps']:<8} {r['snapped_pct']:<10.1f} {r['mean_info_cost']:<12.1f} {r['mean_prec_energy']:<12.2f}{marker}")

print("\n" + "=" * 90)
print("KEY COMPARISON: Exponential vs Square-root")
print("=" * 90)
exp_r = results['Exponential (α=5)']
sqrt_r = results['Square-root (√(A(1-t)/π))']
print(f"Steps improvement: {(exp_r['mean_steps'] - sqrt_r['mean_steps'])/exp_r['mean_steps']*100:.1f}%")
print(f"Info cost improvement: {(exp_r['mean_info_cost'] - sqrt_r['mean_info_cost'])/exp_r['mean_info_cost']*100:.1f}%")
print(f"Snap completion: exp={exp_r['snapped_pct']:.1f}% vs sqrt={sqrt_r['snapped_pct']:.1f}%")

# Now the critical test: what does the error distribution LOOK LIKE at each step?
print("\n" + "=" * 90)
print("ERROR DISTRIBUTION OVER TIME (Square-root funnel)")
print("=" * 90)

# Track error distribution at different time points
time_samples = [0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9]
for t in time_samples:
    deadband = math.sqrt(max(CELL_AREA * (1-t) / math.pi, 0.0001))
    # Count how many points have error < deadband at this stage
    inside = sum(1 for _,_,_,_,e in points if e < deadband)
    frac = inside / N_POINTS
    predicted = math.pi * deadband**2 / CELL_AREA
    print(f"  t={t:.1f}: deadband={deadband:.4f}, inside={frac:.4f}, predicted={predicted:.4f}, gap={abs(frac-predicted):.4f}")

print("\n" + "=" * 90)
print("THE OPTIMAL FUNNEL QUESTION")
print("=" * 90)
print("If P(d<r) = πr²/A, then the CDF of snap errors is F(r) = πr²/A")
print("The optimal quantization (minimum MSE) uses levels at the quantiles of F")
print("This means: δ(t) should be the inverse CDF at t: δ(t) = √(A·t/π)")
print("")
print("But we want the funnel to NARROW (δ → 0), so: δ(t) = √(A·(1-t)/π)")
print("This is the square-root funnel: it allocates precision proportionally")
print("to the error density — more precision where errors are dense (near ρ)")
print("less precision where errors are sparse (near 0)")
print("")
print("The right-skew tells us: spend your precision budget at the boundary.")
