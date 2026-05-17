"""
Experiment 4: Conservation lower bound — adversarial C matrices
Maximize CV while keeping ρ(J) < 1 (system contractive).
"""
import numpy as np
import json
import os
from scipy.optimize import minimize

np.random.seed(999)
N = 5

def spectral_radius(W):
    return np.max(np.abs(np.linalg.eigvals(W)))

def compute_cv(D, C):
    comm = D @ C - C @ D
    return np.linalg.norm(comm, 'fro') / np.linalg.norm(D, 'fro')

def contractive_constraint(C_flat, D):
    C = C_flat.reshape(N, N)
    J = D + C
    return 0.98 - spectral_radius(J)  # must be > 0

# Strategy 1: Grid search over structured C matrices
def adversarial_grid_search():
    """Try structured coupling matrices that maximize commutator"""
    d = np.array([0.3, 0.5, 0.7, 0.8, 0.9])
    D = np.diag(d)
    
    best_cv = 0
    best_C = None
    
    for trial in range(500):
        # Construct C to have large off-diagonal structure that fights D's ordering
        C = np.zeros((N, N))
        
        if trial < 100:
            # Anti-diagonal pattern (maximizes commutator with diagonal D)
            scale = np.random.uniform(0.1, 0.8)
            for i in range(N):
                j = N - 1 - i
                if i != j:
                    C[i, j] = scale * np.random.randn()
        elif trial < 250:
            # Upper triangular with increasing magnitude
            scale = np.random.uniform(0.05, 0.5)
            for i in range(N):
                for j in range(i+1, N):
                    C[i, j] = scale * (j - i) * np.random.randn()
        elif trial < 400:
            # Full random with skew-symmetric component
            C = np.random.randn(N, N) * np.random.uniform(0.1, 0.6)
            C = 0.5 * (C - C.T)  # skew-symmetric part maximizes commutator
        else:
            # Rank-1 structure aligned against D
            v = np.random.randn(N)
            w = np.random.randn(N)
            C = np.random.uniform(0.1, 0.8) * np.outer(v, w)
        
        # Scale to be just under contractive boundary
        J = D + C
        rho = spectral_radius(J)
        if rho >= 0.98:
            C = C * (0.95 / rho)
        
        cv = compute_cv(D, C)
        if cv > best_cv:
            best_cv = cv
            best_C = C.copy()
    
    return d, D, best_C, best_cv

# Strategy 2: Optimization-based approach
def adversarial_optimize():
    """Directly maximize CV subject to contractivity constraint"""
    d = np.array([0.3, 0.5, 0.7, 0.8, 0.9])
    D = np.diag(d)
    
    best_results = []
    
    for trial in range(50):
        C0 = np.random.randn(N, N) * 0.2
        
        # Objective: minimize -CV (maximize CV)
        def objective(C_flat):
            C = C_flat.reshape(N, N)
            return -compute_cv(D, C)
        
        # Penalty for non-contractive
        def penalty(C_flat):
            C = C_flat.reshape(N, N)
            J = D + C
            rho = spectral_radius(J)
            return max(0, rho - 0.98) * 1000
        
        def combined(C_flat):
            return objective(C_flat) + penalty(C_flat)
        
        result = minimize(combined, C0.flatten(), method='Nelder-Mead',
                         options={'maxiter': 2000, 'xatol': 1e-8})
        
        C_opt = result.x.reshape(N, N)
        rho = spectral_radius(D + C_opt)
        if rho < 1.0:
            cv = compute_cv(D, C_opt)
            best_results.append((cv, rho, C_opt.copy()))
    
    if best_results:
        best_results.sort(key=lambda x: x[0], reverse=True)
        return d, D, best_results[0][2], best_results[0][0]
    return None

# Strategy 3: Analytical worst case
def analytical_worst_case():
    """
    For diagonal D with eigenvalues d_1 < d_2 < ... < d_n,
    the commutator [D,C]_{ij} = (d_i - d_j) C_{ij}.
    To maximize ||[D,C]||, put all energy in C_{1n} and C_{n1}
    (largest eigenvalue gap).
    """
    d = np.array([0.1, 0.3, 0.5, 0.7, 0.95])
    D = np.diag(d)
    
    best_cv = 0
    best_C = None
    
    for scale in np.linspace(0.01, 0.5, 100):
        for sign1 in [1, -1]:
            for sign2 in [1, -1]:
                C = np.zeros((N, N))
                C[0, N-1] = scale * sign1
                C[N-1, 0] = scale * sign2
                
                J = D + C
                rho = spectral_radius(J)
                if rho < 1.0:
                    cv = compute_cv(D, C)
                    if cv > best_cv:
                        best_cv = cv
                        best_C = C.copy()
    
    return d, D, best_C, best_cv

# Run all strategies
print("Experiment 4: Conservation lower bound (adversarial)")
print("=" * 60)

results = {"experiment": "conservation_lower_bound", "strategies": {}}

# Grid search
d1, D1, C1, cv1 = adversarial_grid_search()
rho1 = spectral_radius(D1 + C1)
comm1 = np.linalg.norm(D1 @ C1 - C1 @ D1, 'fro')
print(f"\nStrategy 1 (Grid search):")
print(f"  Worst CV = {cv1:.4f}")
print(f"  ρ(J) = {rho1:.4f}")
print(f"  ||[D,C]|| = {comm1:.4f}")
results["strategies"]["grid_search"] = {
    "cv": round(cv1, 6),
    "rho_J": round(rho1, 4),
    "commutator_norm": round(comm1, 4),
    "D_diagonal": [round(x, 4) for x in d1],
    "C_matrix": [[round(x, 4) for x in row] for row in C1.tolist()],
}

# Optimization
opt_result = adversarial_optimize()
if opt_result:
    d2, D2, C2, cv2 = opt_result
    rho2 = spectral_radius(D2 + C2)
    comm2 = np.linalg.norm(D2 @ C2 - C2 @ D2, 'fro')
    print(f"\nStrategy 2 (Optimization):")
    print(f"  Worst CV = {cv2:.4f}")
    print(f"  ρ(J) = {rho2:.4f}")
    print(f"  ||[D,C]|| = {comm2:.4f}")
    results["strategies"]["optimization"] = {
        "cv": round(cv2, 6),
        "rho_J": round(rho2, 4),
        "commutator_norm": round(comm2, 4),
        "D_diagonal": [round(x, 4) for x in d2],
        "C_matrix": [[round(x, 4) for x in row] for row in C2.tolist()],
    }

# Analytical
d3, D3, C3, cv3 = analytical_worst_case()
rho3 = spectral_radius(D3 + C3)
comm3 = np.linalg.norm(D3 @ C3 - C3 @ D3, 'fro')
print(f"\nStrategy 3 (Analytical worst case):")
print(f"  Worst CV = {cv3:.4f}")
print(f"  ρ(J) = {rho3:.4f}")
print(f"  ||[D,C]|| = {comm3:.4f}")
results["strategies"]["analytical"] = {
    "cv": round(cv3, 6),
    "rho_J": round(rho3, 4),
    "commutator_norm": round(comm3, 4),
    "D_diagonal": [round(x, 4) for x in d3],
    "C_matrix": [[round(x, 4) for x in row] for row in C3.tolist()],
}

# Summary
all_cvs = [cv1, cv3]
if opt_result:
    all_cvs.append(cv2)
worst_overall = max(all_cvs)
results["worst_cv_found"] = round(worst_overall, 6)
results["conclusion"] = f"Worst CV while maintaining contractivity: {worst_overall:.4f}"

print(f"\n{'='*60}")
print(f"WORST CV FOUND (contractive): {worst_overall:.4f}")
print(f"This means conservation can degrade to {1-worst_overall:.4f} in the worst case")

outdir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(outdir, "exp4_results.json"), "w") as f:
    json.dump(results, f, indent=2)
