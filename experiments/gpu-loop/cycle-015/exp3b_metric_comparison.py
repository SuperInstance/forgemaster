"""
Experiment 3b: Spectral shape metric comparison — with state-dependent coupling
Compare 5 metrics for predicting CV(γ+H) under NONLINEAR dynamics.
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
    comm = D @ C - C @ C  # intentional: baseline commutator
    comm = D @ C - C @ D
    return np.linalg.norm(comm, 'fro') / np.linalg.norm(D, 'fro')

def evolve_with_coupling(D, C, x0, traj_len):
    """x_{t+1} = D @ tanh(x_t) + C @ x_t — nonlinear dynamics"""
    xs = [x0.copy()]
    x = x0.copy()
    for _ in range(traj_len):
        x = D @ np.tanh(x) + C @ x
        xs.append(x.copy())
    return xs

def metric_eigenvalue_cosine(D, C, xs):
    """Cosine distance between eigenvalue vectors of J at t=0 vs t=end"""
    x0 = xs[0]
    xN = xs[-1]
    
    # Numerical Jacobian at t=0
    eps = 1e-6
    n = len(x0)
    J0 = np.zeros((n, n))
    JN = np.zeros((n, n))
    for j in range(n):
        xp0 = x0.copy(); xp0[j] += eps
        xm0 = x0.copy(); xm0[j] -= eps
        J0[:, j] = (D @ np.tanh(xp0) + C @ xp0 - D @ np.tanh(xm0) - C @ xm0) / (2 * eps)
        
        xpN = xN.copy(); xpN[j] += eps
        xmN = xN.copy(); xmN[j] -= eps
        JN[:, j] = (D @ np.tanh(xpN) + C @ xpN - D @ np.tanh(xmN) - C @ xmN) / (2 * eps)
    
    eigs0 = np.sort(np.abs(np.linalg.eigvals(J0)))
    eigsN = np.sort(np.abs(np.linalg.eigvals(JN)))
    
    denom0 = np.linalg.norm(eigs0)
    denomN = np.linalg.norm(eigsN)
    if denom0 > 1e-10 and denomN > 1e-10:
        return cosine_dist(eigs0, eigsN)
    return 0.0

def metric_emd_eigenvalues(D, C, xs):
    """Earth mover's distance on eigenvalue distributions along trajectory"""
    eps = 1e-6
    n = N
    eig_seqs = []
    for x in xs[::5]:  # sample every 5 steps
        J = np.zeros((n, n))
        for j in range(n):
            xp = x.copy(); xp[j] += eps
            xm = x.copy(); xm[j] -= eps
            J[:, j] = (D @ np.tanh(xp) + C @ xp - D @ np.tanh(xm) - C @ xm) / (2 * eps)
        eig_seqs.append(np.sort(np.real(np.linalg.eigvals(J))))
    
    if len(eig_seqs) >= 2:
        return np.sum(np.abs(eig_seqs[0] - eig_seqs[-1]))
    return 0.0

def metric_fisher_information(D, C, xs):
    """Fisher information distance: trace(J^T J) variance along trajectory"""
    eps = 1e-6
    n = N
    fishers = []
    for x in xs[::5]:
        J = np.zeros((n, n))
        for j in range(n):
            xp = x.copy(); xp[j] += eps
            xm = x.copy(); xm[j] -= eps
            J[:, j] = (D @ np.tanh(xp) + C @ xp - D @ np.tanh(xm) - C @ xm) / (2 * eps)
        fishers.append(np.trace(J.T @ J))
    return np.std(fishers)

def metric_commutator(D, C):
    """||[D, C]|| — our current best"""
    comm = D @ C - C @ D
    return np.linalg.norm(comm, 'fro')

def metric_spectral_stability(D, C, xs):
    """Std of spectral radius ρ(J(x)) over trajectory"""
    eps = 1e-6
    n = N
    radii = []
    for x in xs:
        J = np.zeros((n, n))
        for j in range(n):
            xp = x.copy(); xp[j] += eps
            xm = x.copy(); xm[j] -= eps
            J[:, j] = (D @ np.tanh(xp) + C @ xp - D @ np.tanh(xm) - C @ xm) / (2 * eps)
        radii.append(np.max(np.abs(np.linalg.eigvals(J))))
    return np.std(radii)

# Run experiments
all_cvs = []
all_cosine = []
all_emd = []
all_fisher = []
all_commutator = []
all_spectral_stab = []

print("Running 150 samples with nonlinear dynamics...")
for i in range(SAMPLES):
    d = np.random.uniform(0.2, 0.85, N)
    D = np.diag(d)
    C = np.random.randn(N, N) * 0.15
    
    # Check stability at origin
    J0 = D + C
    rho = np.max(np.abs(np.linalg.eigvals(J0)))
    if rho >= 1:
        C = C * (0.9 / rho)
    
    cv = compute_cv(D, C)
    all_cvs.append(cv)
    
    x0 = np.random.randn(N) * 0.5
    xs = evolve_with_coupling(D, C, x0, TRAJ_LEN)
    
    all_cosine.append(metric_eigenvalue_cosine(D, C, xs))
    all_emd.append(metric_emd_eigenvalues(D, C, xs))
    all_fisher.append(metric_fisher_information(D, C, xs))
    all_commutator.append(metric_commutator(D, C))
    all_spectral_stab.append(metric_spectral_stability(D, C, xs))

# Correlations with CV
metrics = {
    "eigenvalue_cosine": all_cosine,
    "emd_eigenvalues": all_emd,
    "fisher_information": all_fisher,
    "commutator_norm": all_commutator,
    "spectral_stability": all_spectral_stab,
}

results = {
    "experiment": "spectral_metric_comparison_nonlinear",
    "samples": SAMPLES,
    "dynamics": "x_{t+1} = D @ tanh(x_t) + C @ x_t",
    "correlations_with_cv": {},
}

print(f"\nExperiment 3b: Spectral shape metric comparison (nonlinear)")
print(f"{'Metric':<25} {'Pearson r':>10} {'Spearman ρ':>12} {'p-value':>12}")
print("-" * 62)

for name, vals in metrics.items():
    r, p = stats.pearsonr(vals, all_cvs)
    rho_s, p2 = stats.spearmanr(vals, all_cvs)
    results["correlations_with_cv"][name] = {
        "pearson_r": round(r, 4),
        "pearson_p": float(f"{p:.2e}"),
        "spearman_rho": round(rho_s, 4),
    }
    print(f"{name:<25} {r:>10.4f} {rho_s:>12.4f} {p:>12.2e}")

ranked = sorted(results["correlations_with_cv"].items(), key=lambda x: abs(x[1]["pearson_r"]), reverse=True)
results["ranking"] = [(name, data["pearson_r"]) for name, data in ranked]

print(f"\nRanking (by |Pearson r|):")
for i, (name, data) in enumerate(ranked):
    print(f"  {i+1}. {name}: r={data['pearson_r']:.4f}")

outdir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(outdir, "exp3_results.json"), "w") as f:
    json.dump(results, f, indent=2)

print("Saved exp3_results.json")
