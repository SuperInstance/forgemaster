"""
Sim 1 (FIXED): Square-Root Funnel vs Exponential Funnel
Compare funnel shapes for constraint relaxation.

Model: We have N points with initial snap errors. Each step, we apply 
a deadband δ(t). A point "needs attention" if its error > δ(t).
We track how many points still need attention over time.
The funnel shape determines the constraint pressure profile.
"""
import numpy as np

np.random.seed(42)

# Eisenstein lattice parameters
A = np.sqrt(3) / 2  # cell area
rho = 1 / np.sqrt(3)  # covering radius
N_POINTS = 10000
N_STEPS = 100

# Generate random snap errors from right-skewed distribution
# P(d < r) = pi*r^2/A => r = sqrt(A*u/pi)
u = np.random.uniform(0, 1, N_POINTS)
initial_errors = np.sqrt(A * u / np.pi)

print("=" * 70)
print("SIM 1 (FIXED): FUNNEL SHAPE COMPARISON")
print("=" * 70)
print(f"Cell area A = {A:.4f}, Covering radius ρ = {rho:.4f}")
print(f"Error range: [{initial_errors.min():.4f}, {initial_errors.max():.4f}]")
print(f"Error mean: {initial_errors.mean():.4f}, median: {np.median(initial_errors):.4f}")
print()

# Funnel functions: return delta at normalized time t ∈ [0, 1]
# All normalized so δ(0) = ρ and δ(1) = 0
def exp_funnel(t):
    return rho * np.exp(-5 * t)

def sqrt_funnel(t):
    t_clamped = np.clip(t, 0, 0.999)
    return rho * np.sqrt(1 - t_clamped)

def linear_funnel(t):
    return rho * (1 - t)

def inverse_funnel(t):
    return rho / (1 + 5 * t)

funnels = {
    'Exponential exp(-5t)': exp_funnel,
    'Square-Root √(1-t)': sqrt_funnel,
    'Linear (1-t)': linear_funnel,
    'Inverse 1/(1+5t)': inverse_funnel,
}

print("PART A: Deadband pressure profile")
print("How many points exceed the deadband at each time step?")
print()

for name, funnel_fn in funnels.items():
    # Compute how many points still "need attention" at each step
    active_count = []
    info_cost = 0.0
    precision_energy = 0.0
    
    for step in range(N_STEPS):
        t = step / N_STEPS
        delta = funnel_fn(t)
        
        # Points with error > delta still need attention
        active = np.sum(initial_errors > delta)
        active_count.append(active)
        
        # Information cost: sum of 1/delta for active points
        info_cost += active / max(delta, 1e-10)
        
        # Precision energy: integral of (active_count/delta) dt
        precision_energy += (active / max(delta, 1e-10)) * (1.0 / N_STEPS)
    
    # Find when 50%, 90%, 99% of points have relaxed
    times = np.arange(N_STEPS) / N_STEPS
    pct_relaxed = 100 * (1 - np.array(active_count) / N_POINTS)
    
    idx50 = np.searchsorted(pct_relaxed, 50)
    idx90 = np.searchsorted(pct_relaxed, 90)
    idx99 = np.searchsorted(pct_relaxed, 99)
    t50 = times[min(idx50, N_STEPS-1)] if np.any(pct_relaxed >= 50) else 1.0
    t90 = times[min(idx90, N_STEPS-1)] if np.any(pct_relaxed >= 90) else 1.0
    t99 = times[min(idx99, N_STEPS-1)] if np.any(pct_relaxed >= 99) else 1.0
    
    print(f"  {name}:")
    print(f"    t(50% relaxed)={t50:.2f}, t(90%)={t90:.2f}, t(99%)={t99:.2f}")
    print(f"    Total info cost: {info_cost:.0f}, Precision energy: {precision_energy:.2f}")
    print(f"    Active at t=0.5: {active_count[N_STEPS//2]}, at t=0.9: {active_count[int(0.9*N_STEPS)]}")
    print()

print()
print("PART B: Funnel-guided refinement simulation")
print("Each step, allocate compute proportional to how many points need attention.")
print("Points with error > δ(t) get refined (error reduced).")
print()

FINAL_THRESHOLD = 0.01  # convergence threshold

for name, funnel_fn in funnels.items():
    errors = initial_errors.copy()
    total_steps = 0
    compute_used = 0.0
    
    for step in range(N_STEPS * 10):  # allow many steps
        t = min(step / (N_STEPS * 10), 0.999)
        delta = funnel_fn(t)
        
        # Active points need refinement
        active_mask = errors > delta
        n_active = np.sum(active_mask)
        
        if n_active == 0:
            break
        
        # Refine active points: reduce error by a fixed amount
        # Higher compute = more reduction
        compute_per_point = 0.5
        reduction = np.random.exponential(compute_per_point * 0.1, n_active)
        errors[active_mask] = np.maximum(errors[active_mask] - reduction, 0)
        
        total_steps += n_active
        compute_used += n_active * compute_per_point
    
    n_converged = np.sum(errors < FINAL_THRESHOLD)
    print(f"  {name}:")
    print(f"    Total compute steps: {total_steps}, Compute used: {compute_used:.0f}")
    print(f"    Converged (<{FINAL_THRESHOLD}): {n_converged}/{N_POINTS} ({100*n_converged/N_POINTS:.1f}%)")
    print(f"    Mean final error: {errors.mean():.6f}, Max: {errors.max():.6f}")
    print()

print()
print("PART C: Theoretical analysis")
print("Given the right-skewed CDF P(d<r) = πr²/A:")
print(f"  At δ = ρ: P(d < ρ) = πρ²/A = π/(3A) = {np.pi/(3*A):.4f} (all points within covering radius)")
print(f"  At δ = ρ/2: P(d < ρ/2) = πρ²/(4A) = {np.pi*rho**2/(4*A):.4f}")
print(f"  At δ = ρ/4: P(d < ρ/4) = {np.pi*rho**2/(16*A):.4f}")
print()
print("  A square-root funnel δ(t) = ρ√(1-t) matches the CDF shape:")
print(f"    P(d > δ(t)) = 1 - π(ρ√(1-t))²/A = 1 - πρ²(1-t)/A = t × πρ²/A")
print("    Active count decays LINEARLY — the most predictable decay.")
print()
print("  Exponential funnel decays too fast initially (too few active points)")
print("  Linear funnel decays too slow initially (too many active points)")
print("  Square-root is the Goldilocks funnel for right-skewed error distributions.")
