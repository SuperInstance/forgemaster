"""
Experiment 3: Spectral shape metric comparison
Compare 5 metrics for predicting CV(γ+H).
"""
import numpy as np
import json
import os
from scipy import stats
from scipy.spatial.distance import cosine as cosine_dist

np.random.seed(777)
N = 5
SAMPLES = 150
TRAJ_LEN = 50

def compute_cv(D, C):
    """Conservation violation: ||[D,C]|| / ||D||"""
    comm = D @ C - C @ D
    return np.linalg.norm(comm, 'fro') / np.linalg.norm(D, 'fro')

def metric_eigenvalue_cosine(D, C, traj_len=TRAJ_LEN):
    """Cosine distance between eigenvalue vectors at t=0 vs t=end"""
    J0 = D + C
    eigs0 = np.sort(np.abs(np.linalg.eigvals(J0)))
    
    # Evolve system and get eigenvalues at end
    x = np.random.randn(N)
    for _ in range(traj_len):
        x = (D + C) @ x
    
    Jend = D + C  # For linear system, Jacobian is constant
    eigsend = np.sort(np.abs(np.linalg.eigvals(Jend)))
    
    return cosine_dist(eigs0, eigsend) if np.linalg.norm(eigs0) > 0 and np.linalg.norm(eigsend) > 0 else 0

def metric_emd_eigenvalues(D, C, traj_len=TRAJ_LEN):
    """Earth mover's distance on eigenvalue distributions along trajectory"""
    x = np.random.randn(N)
    eig_distributions = []
    
    for t in range(min(traj_len, 20)):
        J = D + C
        eigs = np.sort(np.real(np.linalg.eigvals(J)))
        eig_distributions.append(eigs)
        x = (D + C) @ x
    
    # EMD between first and last distributions (1D)
    if len(eig_distributions) >= 2:
        d0 = eig_distributions[0]
        d1 = eig_distributions[-1]
        # Simple 1D EMD approximation
        emd = np.sum(np.abs(np.sort(d0) - np.sort(d1)))
        return emd
    return 0

def metric_fisher_information(D, C):
    """Fisher information distance between system dynamics"""
    J = D + C
    # Fisher info = trace(J^T J)
    fisher = np.trace(J.T @ J)
    # Distance from diagonal dynamics
    fisher_diag = np.trace(D.T @ D)
    return abs(fisher - fisher_diag)

def metric_commutator(D, C):
    """||[D, C]|| — our current best"""
    comm = D @ C - C @ D
    return np.linalg.norm(comm, 'fro')

def metric_spectral_stability(D, C, traj_len=TRAJ_LEN):
    """Std of spectral radius ρ(C(x)) over trajectory"""
    x = np.random.randn(N)
    radii = []
    
    for t in range(traj_len):
        # State-dependent perturbation of C
        Cx = C * (1 + 0.1 * np.tanh(x[:, None] @ x[None, :]))
        rho = np.max(np.abs(np.linalg.eigvals(Cx)))
        radii.append(rho)
        x = (D + C) @ x
    
    return np.std(radii)

# Run experiments
all_cvs = []
all_cosine = []
all_emd = []
all_fisher = []
all_commutator = []
all_spectral_stab = []

for i in range(SAMPLES):
    d = np.random.uniform(0.2, 0.85, N)
    D = np.diag(d)
    C = np.random.randn(N, N) * 0.3
    
    # Ensure system is stable (spectral radius < 1)
    J = D + C
    rho = np.max(np.abs(np.linalg.eigvals(J)))
    if rho >= 1:
        C = C * (0.95 / rho)
    
    cv = compute_cv(D, C)
    all_cvs.append(cv)
    
    all_cosine.append(metric_eigenvalue_cosine(D, C))
    all_emd.append(metric_emd_eigenvalues(D, C))
    all_fisher.append(metric_fisher_information(D, C))
    all_commutator.append(metric_commutator(D, C))
    all_spectral_stab.append(metric_spectral_stability(D, C))

# Correlations with CV
metrics = {
    "eigenvalue_cosine": all_cosine,
    "emd_eigenvalues": all_emd,
    "fisher_information": all_fisher,
    "commutator_norm": all_commutator,
    "spectral_stability": all_spectral_stab,
}

results = {
    "experiment": "spectral_metric_comparison",
    "samples": SAMPLES,
    "correlations_with_cv": {},
}

print("Experiment 3: Spectral shape metric comparison")
print(f"{'Metric':<25} {'Pearson r':>10} {'Spearman ρ':>12} {'p-value':>12}")
print("-" * 62)

for name, vals in metrics.items():
    r, p = stats.pearsonr(vals, all_cvs)
    rho, p2 = stats.spearmanr(vals, all_cvs)
    results["correlations_with_cv"][name] = {
        "pearson_r": round(r, 4),
        "pearson_p": float(f"{p:.2e}"),
        "spearman_rho": round(rho, 4),
    }
    print(f"{name:<25} {r:>10.4f} {rho:>12.4f} {p:>12.2e}")

# Rank by absolute Pearson correlation
ranked = sorted(results["correlations_with_cv"].items(), key=lambda x: abs(x[1]["pearson_r"]), reverse=True)
results["ranking"] = [(name, data["pearson_r"]) for name, data in ranked]

print(f"\nRanking (by |Pearson r|):")
for i, (name, data) in enumerate(ranked):
    print(f"  {i+1}. {name}: r={data['pearson_r']:.4f}")

outdir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(outdir, "exp3_results.json"), "w") as f:
    json.dump(results, f, indent=2)
