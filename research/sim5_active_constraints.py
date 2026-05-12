"""
Sim 5 (FIXED): Boundary Detection and Active Constraints
Compare priority-based vs round-robin constraint refinement.
FAIR comparison: same total compute budget per round.
"""
import numpy as np

np.random.seed(42)

N_CONSTRAINTS = 100
N_ROUNDS = 50
N_TRIALS = 50
COMPUTE_BUDGET = 100  # total compute per round (same for all strategies)

A = np.sqrt(3) / 2
rho = 1 / np.sqrt(3)

def generate_errors(n):
    u = np.random.uniform(0, 1, n)
    return np.sqrt(A * u / np.pi)

print("=" * 70)
print("SIM 5 (FIXED): BOUNDARY DETECTION AND ACTIVE CONSTRAINTS")
print("=" * 70)
print(f"N constraints: {N_CONSTRAINTS}, Rounds: {N_ROUNDS}")
print(f"Compute budget per round: {COMPUTE_BUDGET} (same for ALL strategies)")
print(f"Trials: {N_TRIALS}")
print()

def simulate_round_robin(n_c, n_r, budget):
    """Equal compute to all constraints."""
    errors = generate_errors(n_c)
    history = []
    for rnd in range(n_r):
        alloc = np.full(n_c, budget / n_c)
        # Error reduction: error *= exp(-k * alloc)
        errors *= np.exp(-0.3 * alloc)
        history.append({'max': np.max(errors), 'mean': np.mean(errors), 
                        'p95': np.percentile(errors, 95),
                        'pct': 100*np.mean(errors < 0.01), 'round': rnd})
    return history

def simulate_priority_linear(n_c, n_r, budget):
    """Allocate proportional to error."""
    errors = generate_errors(n_c)
    history = []
    for rnd in range(n_r):
        s = np.sum(errors)
        alloc = errors / s * budget if s > 0 else np.full(n_c, budget/n_c)
        errors *= np.exp(-0.3 * alloc)
        history.append({'max': np.max(errors), 'mean': np.mean(errors),
                        'p95': np.percentile(errors, 95),
                        'pct': 100*np.mean(errors < 0.01), 'round': rnd})
    return history

def simulate_boundary_aware(n_c, n_r, budget):
    """80% budget to top-20% worst, 20% to rest."""
    errors = generate_errors(n_c)
    history = []
    K = max(n_c // 5, 5)
    for rnd in range(n_r):
        worst_idx = np.argsort(errors)[-K:]
        best_idx = np.argsort(errors)[:n_c - K]
        alloc = np.full(n_c, 0.2 * budget / n_c)
        alloc[worst_idx] = 0.8 * budget / K
        errors *= np.exp(-0.3 * alloc)
        history.append({'max': np.max(errors), 'mean': np.mean(errors),
                        'p95': np.percentile(errors, 95),
                        'pct': 100*np.mean(errors < 0.01), 'round': rnd})
    return history

def simulate_adaptive_quad(n_c, n_r, budget):
    """Allocate proportional to error² (heavily favors outliers)."""
    errors = generate_errors(n_c)
    history = []
    for rnd in range(n_r):
        s = np.sum(errors**2)
        alloc = errors**2 / s * budget if s > 0 else np.full(n_c, budget/n_c)
        errors *= np.exp(-0.3 * alloc)
        history.append({'max': np.max(errors), 'mean': np.mean(errors),
                        'p95': np.percentile(errors, 95),
                        'pct': 100*np.mean(errors < 0.01), 'round': rnd})
    return history

def simulate_top_k_only(n_c, n_r, budget):
    """100% budget to top-K worst constraints, rest get nothing."""
    errors = generate_errors(n_c)
    history = []
    K = max(n_c // 5, 5)
    for rnd in range(n_r):
        alloc = np.zeros(n_c)
        worst_idx = np.argsort(errors)[-K:]
        alloc[worst_idx] = budget / K
        errors *= np.exp(-0.3 * alloc)
        history.append({'max': np.max(errors), 'mean': np.mean(errors),
                        'p95': np.percentile(errors, 95),
                        'pct': 100*np.mean(errors < 0.01), 'round': rnd})
    return history

strategies = {
    'Round-robin (equal)': simulate_round_robin,
    'Priority (∝ error)': simulate_priority_linear,
    'Boundary-aware (80/20)': simulate_boundary_aware,
    'Adaptive (∝ error²)': simulate_adaptive_quad,
    'Top-K only (20%)': simulate_top_k_only,
}

# Aggregate
agg = {name: {'max': [], 'mean': [], 'p95': [], 'pct': [],
              'r90': [], 'r95': [], 'r99': []} for name in strategies}

for trial in range(N_TRIALS):
    for name, fn in strategies.items():
        h = fn(N_CONSTRAINTS, N_ROUNDS, COMPUTE_BUDGET)
        final = h[-1]
        agg[name]['max'].append(final['max'])
        agg[name]['mean'].append(final['mean'])
        agg[name]['p95'].append(final['p95'])
        agg[name]['pct'].append(final['pct'])
        
        for target, key in [(90, 'r90'), (95, 'r95'), (99, 'r99')]:
            rounds_needed = N_ROUNDS
            for hh in h:
                if hh['pct'] >= target:
                    rounds_needed = hh['round'] + 1
                    break
            agg[name][key].append(rounds_needed)

print(f"{'Strategy':<28} {'Max Err':>10} {'Mean Err':>10} {'P95 Err':>10} {'% Conv':>8} {'Rnd→90%':>8} {'Rnd→95%':>8}")
print("-" * 86)
for name in strategies:
    r = agg[name]
    print(f"{name:<28} {np.mean(r['max']):>10.5f} {np.mean(r['mean']):>10.5f} "
          f"{np.mean(r['p95']):>10.5f} {np.mean(r['pct']):>7.1f}% "
          f"{np.mean(r['r90']):>8.1f} {np.mean(r['r95']):>8.1f}")

print()
print("RANKING by convergence speed (rounds to 95%):")
by_speed = sorted(agg.items(), key=lambda x: np.mean(x[1]['r95']))
for rank, (name, r) in enumerate(by_speed, 1):
    print(f"  {rank}. {name}: {np.mean(r['r95']):.1f} rounds")

print()
print("RANKING by final max error:")
by_max = sorted(agg.items(), key=lambda x: np.mean(x[1]['max']))
for rank, (name, r) in enumerate(by_max, 1):
    print(f"  {rank}. {name}: {np.mean(r['max']):.5f}")

# Detailed trace
print()
print("CONVERGENCE TRACE (single trial):")
for name, fn in [('Round-robin (equal)', simulate_round_robin), 
                  ('Boundary-aware (80/20)', simulate_boundary_aware),
                  ('Top-K only (20%)', simulate_top_k_only)]:
    h = fn(N_CONSTRAINTS, N_ROUNDS, COMPUTE_BUDGET)
    print(f"\n  {name}:")
    for idx in [0, 4, 9, 19, 34, 49]:
        if idx < len(h):
            hh = h[idx]
            print(f"    Rnd {hh['round']:>3}: max={hh['max']:.4f} mean={hh['mean']:.4f} "
                  f"p95={hh['p95']:.4f} conv={hh['pct']:.0f}%")
