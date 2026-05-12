"""
Sim 5: Boundary Detection and Active Constraints
Compare priority-based vs round-robin constraint refinement.
"""
import numpy as np

np.random.seed(42)

N_CONSTRAINTS = 100
N_ROUNDS = 50
N_TRIALS = 20

A = np.sqrt(3) / 2
rho = 1 / np.sqrt(3)

# Generate snap errors from right-skewed distribution
def generate_errors(n):
    u = np.random.uniform(0, 1, n)
    return np.sqrt(A * u / np.pi)

print("=" * 70)
print("SIM 5: BOUNDARY DETECTION AND ACTIVE CONSTRAINTS")
print("=" * 70)
print(f"N constraints: {N_CONSTRAINTS}, Rounds: {N_ROUNDS}, Trials: {N_TRIALS}")
print()

def simulate_round_robin(n_constraints, n_rounds, compute_per_round=10):
    """
    Round-robin: allocate compute evenly across all constraints.
    Each round, each constraint gets equal compute.
    Error reduces proportionally to compute allocated.
    """
    errors = generate_errors(n_constraints)
    total_compute = 0
    convergence_history = []
    
    for round_num in range(n_rounds):
        # Each constraint gets equal compute
        compute_each = compute_per_round
        # Error reduction: error *= exp(-k * compute) where k depends on initial error
        for i in range(n_constraints):
            reduction = np.exp(-0.1 * compute_each)
            errors[i] *= reduction
        
        total_compute += n_constraints * compute_each
        convergence_history.append({
            'round': round_num,
            'max_error': np.max(errors),
            'mean_error': np.mean(errors),
            'p95_error': np.percentile(errors, 95),
            'total_compute': total_compute,
            'pct_converged': 100 * np.mean(errors < 0.01),
        })
    
    return convergence_history

def simulate_priority(n_constraints, n_rounds, compute_budget=100):
    """
    Priority-based: allocate more compute to high-error constraints.
    Budget per round is fixed; distribute proportional to error.
    """
    errors = generate_errors(n_constraints)
    total_compute = 0
    convergence_history = []
    
    for round_num in range(n_rounds):
        # Allocate compute proportional to error (more to high-error)
        error_sum = np.sum(errors)
        if error_sum == 0:
            allocations = np.ones(n_constraints) * compute_budget / n_constraints
        else:
            allocations = errors / error_sum * compute_budget
        
        for i in range(n_constraints):
            reduction = np.exp(-0.1 * allocations[i])
            errors[i] *= reduction
        
        total_compute += compute_budget
        convergence_history.append({
            'round': round_num,
            'max_error': np.max(errors),
            'mean_error': np.mean(errors),
            'p95_error': np.percentile(errors, 95),
            'total_compute': total_compute,
            'pct_converged': 100 * np.mean(errors < 0.01),
        })
    
    return convergence_history

def simulate_boundary_aware(n_constraints, n_rounds, compute_budget=100):
    """
    Boundary-aware: aggressively allocate to top-K worst constraints.
    Based on the right-skew insight: most errors are small, a few are large.
    Focus compute on the large ones.
    """
    errors = generate_errors(n_constraints)
    total_compute = 0
    convergence_history = []
    K = max(n_constraints // 5, 5)  # focus on top 20%
    
    for round_num in range(n_rounds):
        # Find top-K worst constraints
        worst_idx = np.argsort(errors)[-K:]
        best_idx = np.argsort(errors)[:n_constraints - K]
        
        allocations = np.zeros(n_constraints)
        # Give 80% of budget to worst, 20% to rest
        allocations[worst_idx] = 0.8 * compute_budget / K
        allocations[best_idx] = 0.2 * compute_budget / (n_constraints - K) if len(best_idx) > 0 else 0
        
        for i in range(n_constraints):
            reduction = np.exp(-0.1 * allocations[i])
            errors[i] *= reduction
        
        total_compute += compute_budget
        convergence_history.append({
            'round': round_num,
            'max_error': np.max(errors),
            'mean_error': np.mean(errors),
            'p95_error': np.percentile(errors, 95),
            'total_compute': total_compute,
            'pct_converged': 100 * np.mean(errors < 0.01),
        })
    
    return convergence_history

def simulate_adaptive(n_constraints, n_rounds, compute_budget=100):
    """
    Adaptive: allocate based on error² (even more aggressive toward high-error).
    Uses squared error weighting — makes it even more focused on outliers.
    """
    errors = generate_errors(n_constraints)
    total_compute = 0
    convergence_history = []
    
    for round_num in range(n_rounds):
        error_sq_sum = np.sum(errors**2)
        if error_sq_sum == 0:
            allocations = np.ones(n_constraints) * compute_budget / n_constraints
        else:
            allocations = errors**2 / error_sq_sum * compute_budget
        
        for i in range(n_constraints):
            reduction = np.exp(-0.1 * allocations[i])
            errors[i] *= reduction
        
        total_compute += compute_budget
        convergence_history.append({
            'round': round_num,
            'max_error': np.max(errors),
            'mean_error': np.mean(errors),
            'p95_error': np.percentile(errors, 95),
            'total_compute': total_compute,
            'pct_converged': 100 * np.mean(errors < 0.01),
        })
    
    return convergence_history

# Run multiple trials
strategies = {
    'Round-robin': simulate_round_robin,
    'Priority (linear)': simulate_priority,
    'Boundary-aware (top-20%)': simulate_boundary_aware,
    'Adaptive (quadratic)': simulate_adaptive,
}

# Aggregate results
final_results = {name: {'max_err': [], 'mean_err': [], 'p95_err': [], 'pct_conv': [],
                         'rounds_to_90': [], 'rounds_to_95': []} 
                 for name in strategies}

for trial in range(N_TRIALS):
    for name, sim_fn in strategies.items():
        history = sim_fn(N_CONSTRAINTS, N_ROUNDS)
        final = history[-1]
        final_results[name]['max_err'].append(final['max_error'])
        final_results[name]['mean_err'].append(final['mean_error'])
        final_results[name]['p95_err'].append(final['p95_error'])
        final_results[name]['pct_conv'].append(final['pct_converged'])
        
        # Find rounds to 90% and 95% convergence
        for h in history:
            if h['pct_converged'] >= 90:
                final_results[name]['rounds_to_90'].append(h['round'])
                break
        else:
            final_results[name]['rounds_to_90'].append(N_ROUNDS)
        
        for h in history:
            if h['pct_converged'] >= 95:
                final_results[name]['rounds_to_95'].append(h['round'])
                break
        else:
            final_results[name]['rounds_to_95'].append(N_ROUNDS)

print(f"{'Strategy':<30} {'Max Err':>10} {'Mean Err':>10} {'P95 Err':>10} {'% Conv':>10} {'Rnds→90%':>10} {'Rnds→95%':>10}")
print("-" * 90)
for name in strategies:
    r = final_results[name]
    print(f"{name:<30} {np.mean(r['max_err']):>10.4f} {np.mean(r['mean_err']):>10.4f} "
          f"{np.mean(r['p95_err']):>10.4f} {np.mean(r['pct_conv']):>10.1f}% "
          f"{np.mean(r['rounds_to_90']):>10.1f} {np.mean(r['rounds_to_95']):>10.1f}")

print()
print("CONVERGENCE SPEED RANKING:")
by_convergence = sorted(final_results.items(), key=lambda x: np.mean(x[1]['rounds_to_90']))
for rank, (name, r) in enumerate(by_convergence, 1):
    print(f"  {rank}. {name}: {np.mean(r['rounds_to_90']):.1f} rounds to 90% convergence")

print()
print("MAX ERROR RANKING (lower is better):")
by_maxerr = sorted(final_results.items(), key=lambda x: np.mean(x[1]['max_err']))
for rank, (name, r) in enumerate(by_maxerr, 1):
    print(f"  {rank}. {name}: max error = {np.mean(r['max_err']):.4f}")

# Show a detailed convergence trace for one trial
print()
print("DETAILED CONVERGENCE TRACE (single trial):")
print(f"{'Round':>6}", end="")
for name in strategies:
    print(f" {'RR':>8}" if 'Round' in name else f" {'Pri':>8}" if 'Priority' in name else 
          f" {'Bnd':>8}" if 'Boundary' in name else f" {'Adp':>8}", end="")
print("  (Max error)")
print(f"{'':>6}", end="")
for name in strategies:
    print(f" {strategies.keys().__iter__().__next__():>8}" if False else "", end="")
print()
# Just show round-robin vs best strategy trace
for name, sim_fn in [('Round-robin', simulate_round_robin), 
                      ('Boundary-aware (top-20%)', simulate_boundary_aware)]:
    history = sim_fn(N_CONSTRAINTS, N_ROUNDS)
    print(f"\n  {name}:")
    for h in [0, 4, 9, 19, 29, 49]:
        if h < len(history):
            hh = history[h]
            print(f"    Round {hh['round']:>3}: max={hh['max_error']:.4f}, mean={hh['mean_error']:.4f}, "
                  f"p95={hh['p95_error']:.4f}, converged={hh['pct_converged']:.1f}%")
