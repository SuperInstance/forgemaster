"""
Experiment 1: Koopman eigenvalue vs Commutator correlation
For 100 random 5x5 coupling matrices, compute |1-λ_Koopman| and ||[D,C]||
"""
import numpy as np
import json
import os

np.random.seed(42)
N = 5
SAMPLES = 100

commutator_norms = []
koopman_devs = []
cvs = []

for i in range(SAMPLES):
    # Generate random coupling matrix C
    C = np.random.randn(N, N) * 0.5
    
    # Diagonal dynamics matrix D
    d = np.random.uniform(0.3, 0.9, N)
    D = np.diag(d)
    
    # Commutator [D, C] = DC - CD
    comm = D @ C - C @ D
    comm_norm = np.linalg.norm(comm, 'fro')
    commutator_norms.append(comm_norm)
    
    # Koopman operator for the coupled system: x_{t+1} = (D + C) x_t
    # The Jacobian J = D + C
    J = D + C
    eigenvalues = np.linalg.eigvals(J)
    
    # Koopman eigenvalue closest to 1
    koopman_eigs = eigenvalues
    deviations = np.abs(1 - np.abs(koopman_eigs))
    min_dev = np.min(deviations)
    koopman_devs.append(min_dev)
    
    # Conservation violation: CV = ||[D,C]|| / ||D||
    cv = comm_norm / np.linalg.norm(D, 'fro')
    cvs.append(cv)

# Correlations
from scipy import stats

corr_comm_koopman, p1 = stats.pearsonr(commutator_norms, koopman_devs)
corr_comm_cv, p2 = stats.pearsonr(commutator_norms, cvs)
corr_koopman_cv, p3 = stats.pearsonr(koopman_devs, cvs)

spearman_comm_koopman, sp1 = stats.spearmanr(commutator_norms, koopman_devs)
spearman_comm_cv, sp2 = stats.spearmanr(commutator_norms, cvs)

results = {
    "experiment": "koopman_vs_commutator",
    "samples": SAMPLES,
    "matrix_size": N,
    "pearson_commutator_koopman": round(corr_comm_koopman, 4),
    "pearson_commutator_koopman_p": float(f"{p1:.2e}"),
    "pearson_commutator_cv": round(corr_comm_cv, 4),
    "pearson_commutator_cv_p": float(f"{p2:.2e}"),
    "pearson_koopman_cv": round(corr_koopman_cv, 4),
    "spearman_commutator_koopman": round(spearman_comm_koopman, 4),
    "spearman_commutator_cv": round(spearman_comm_cv, 4),
    "mean_commutator_norm": round(np.mean(commutator_norms), 4),
    "mean_koopman_dev": round(np.mean(koopman_devs), 4),
    "mean_cv": round(np.mean(cvs), 4),
    "koopman_devs": [round(x, 6) for x in koopman_devs],
    "commutator_norms": [round(x, 6) for x in commutator_norms],
    "cvs": [round(x, 6) for x in cvs],
}

outdir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(outdir, "exp1_results.json"), "w") as f:
    json.dump(results, f, indent=2)

print(f"Experiment 1 Results:")
print(f"  Pearson(commutator, koopman_dev) = {corr_comm_koopman:.4f} (p={p1:.2e})")
print(f"  Spearman(commutator, koopman_dev) = {spearman_comm_koopman:.4f}")
print(f"  Pearson(commutator, CV) = {corr_comm_cv:.4f} (p={p2:.2e})")
print(f"  Pearson(koopman_dev, CV) = {corr_koopman_cv:.4f}")
print(f"  Mean ||[D,C]|| = {np.mean(commutator_norms):.4f}")
print(f"  Mean |1-λ_Koopman| = {np.mean(koopman_devs):.4f}")
