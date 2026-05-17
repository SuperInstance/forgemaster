#!/usr/bin/env python3
"""
Cycle 016 (v2): Anti-diagonal anatomy with STATE-DEPENDENT coupling.
Static coupling gives trivially CV=0 because eigenvalues don't change.
The breaking happens when C depends on x.
"""

import numpy as np
from scipy.stats import pearsonr
import json, os

np.random.seed(42)
N = 5
SAMPLES = 50
STEPS = 100
NOISE = 0.01
OUT = "/home/phoenix/.openclaw/workspace/experiments/gpu-loop/cycle-016"

def spectral_metrics(C):
    eigvals = np.linalg.eigvals(C)
    mags = np.abs(eigvals)
    total = np.sum(mags)
    if total < 1e-15:
        return 0.0, 0.0
    probs = mags / total
    probs = probs[probs > 1e-15]
    H = -np.sum(probs * np.log(probs))
    gamma = total**2 / np.sum(mags**2)
    return gamma, H

def commutator_norm(d, C):
    D = np.diag(d)
    return np.linalg.norm(D @ C - C @ D, 'fro')

def run_sd_dynamics(make_C, steps=STEPS):
    """State-dependent dynamics: x_{t+1} = tanh(C(x_t) @ x_t) + noise"""
    x = np.random.randn(N) * 0.1
    gh_vals, comm_vals, norm_vals = [], [], []
    for t in range(steps):
        C = make_C(x)
        gamma, H = spectral_metrics(C)
        gh_vals.append(gamma + H)
        
        # Commutator with saturation diagonal
        sat = 1 - np.tanh(C @ x)**2  # sech^2 at current state
        comm_vals.append(commutator_norm(sat, C))
        norm_vals.append(np.linalg.norm(x))
        
        # Step
        x = np.tanh(C @ x) + np.random.randn(N) * NOISE
    
    return gh_vals, comm_vals, norm_vals, x

# ============================================================
# Coupling constructors (state-dependent)
# ============================================================

def sd_random(x):
    """Random state-dependent coupling"""
    n = len(x)
    M = np.random.randn(n, n) / np.sqrt(n)
    return (M + M.T) / 2

def sd_attention(x, tau=1.0):
    """Softmax attention coupling"""
    n = len(x)
    logits = np.outer(x, x) / tau
    logits -= logits.max(axis=1, keepdims=True)
    exp_l = np.exp(logits)
    return exp_l / exp_l.sum(axis=1, keepdims=True)

def sd_hebbian(x):
    """Hebbian coupling C = xx^T/N"""
    return np.outer(x, x) / len(x)

def sd_anti_diagonal(x):
    """Anti-diagonal state-dependent: only connects i → N-1-i"""
    n = len(x)
    C = np.zeros((n, n))
    for i in range(n):
        C[i, n-1-i] = x[n-1-i]
    return C

def sd_diagonal(x):
    """Diagonal state-dependent"""
    return np.diag(x)

def sd_mixed(x, alpha):
    """Interpolate: diagonal(0) → attention(0.5) → anti-diagonal(1.0)"""
    if alpha <= 0.5:
        t = alpha * 2
        return (1-t) * sd_diagonal(x) + t * sd_attention(x)
    else:
        t = (alpha - 0.5) * 2
        return (1-t) * sd_attention(x) + t * sd_anti_diagonal(x)

def sd_perturbed_anti_diag(x, eps):
    """Anti-diagonal + random perturbation"""
    C = sd_anti_diagonal(x)
    C += np.random.randn(N, N) * eps / np.sqrt(N)
    return C

# ============================================================
# EXP 1: Anti-diagonal anatomy with state-dependent coupling
# ============================================================
print("=" * 60)
print("EXP 1: State-dependent anti-diagonal spectral anatomy")
print("=" * 60)

configs = {
    'diagonal': lambda x: sd_diagonal(x),
    'attention': lambda x: sd_attention(x, 1.0),
    'hebbian': lambda x: sd_hebbian(x),
    'random': lambda x: sd_random(x),
    'anti_diag': lambda x: sd_anti_diagonal(x),
}

exp1 = {}
for name, make_C in configs.items():
    cvs, comms, gh_means, rhos = [], [], [], []
    for s in range(SAMPLES):
        gh, comm, norm, x_final = run_sd_dynamics(make_C)
        gh_after_trans = gh[20:]
        mean_gh = np.mean(gh_after_trans)
        cv = np.std(gh_after_trans) / (abs(mean_gh) + 1e-15)
        
        C_final = make_C(x_final)
        rho = np.max(np.abs(np.linalg.eigvals(C_final)))
        
        cvs.append(cv)
        comms.append(np.mean(comm[20:]))
        gh_means.append(mean_gh)
        rhos.append(rho)
    
    exp1[name] = {
        'cv_mean': np.mean(cvs), 'cv_std': np.std(cvs),
        'comm_mean': np.mean(comms), 'comm_std': np.std(comms),
        'gh_mean': np.mean(gh_means), 'gh_std': np.std(gh_means),
        'rho_mean': np.mean(rhos),
        'max_cv': np.max(cvs),
    }
    print(f"  {name:12s}: CV={np.mean(cvs):.4f}±{np.std(cvs):.4f}, "
          f"||[D,C]||={np.mean(comms):.4f}, "
          f"mean(γ+H)={np.mean(gh_means):.4f}, ρ={np.mean(rhos):.3f}")

# Eigenvalue analysis of anti-diagonal coupling
print("\n--- Anti-diagonal eigenvalue structure (state-dependent) ---")
for s in range(5):
    x = np.random.randn(N) * 0.1
    for _ in range(50):
        C = sd_anti_diagonal(x)
        x = np.tanh(C @ x)
    C = sd_anti_diagonal(x)
    eigvals = np.linalg.eigvals(C)
    print(f"  x={np.round(x, 3)}")
    print(f"    C (anti-diag) = diag^rev: {np.round(np.diag(C[:, ::-1]), 4)}")
    print(f"    Eigenvalues: {[f'{e:.4f}' for e in eigvals]}")
    print(f"    |Imag/Real| ratio: {np.sum(np.abs(eigvals.imag)) / (np.sum(np.abs(eigvals.real)) + 1e-15):.3f}")

# ============================================================
# EXP 2: Phase transition (diagonal → attention → anti-diagonal)
# ============================================================
print("\n" + "=" * 60)
print("EXP 2: Phase transition sweep")
print("=" * 60)

alphas = np.linspace(0, 1, 21)
exp2 = {}

for alpha in alphas:
    cvs, comms, gh_means = [], [], []
    for s in range(SAMPLES):
        gh, comm, norm, _ = run_sd_dynamics(lambda x, a=alpha: sd_mixed(x, a))
        gh_at = gh[20:]
        mean_gh = np.mean(gh_at)
        cv = np.std(gh_at) / (abs(mean_gh) + 1e-15)
        cvs.append(cv)
        comms.append(np.mean(comm[20:]))
        gh_means.append(mean_gh)
    
    exp2[alpha] = {
        'cv': np.mean(cvs), 'cv_std': np.std(cvs),
        'comm': np.mean(comms), 'gh': np.mean(gh_means),
        'max_cv': np.max(cvs)
    }
    print(f"  α={alpha:.2f}: CV={np.mean(cvs):.4f}±{np.std(cvs):.4f}, "
          f"||[D,C]||={np.mean(comms):.4f}, γ+H={np.mean(gh_means):.4f}")

# Detect transition
cvs_list = [exp2[a]['cv'] for a in alphas]
diffs = np.diff(cvs_list)
peak_alpha = alphas[np.argmax(np.abs(diffs)) + 1]
print(f"\n  Steepest CV change at α ≈ {peak_alpha:.2f}")
print(f"  CV range: {min(cvs_list):.4f} → {max(cvs_list):.4f}")

# ============================================================
# EXP 3: Perturbation restoration
# ============================================================
print("\n" + "=" * 60)
print("EXP 3: Can perturbation restore conservation?")
print("=" * 60)

epsilons = [0, 0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0]
exp3 = {}

for eps in epsilons:
    cvs, comms = [], []
    for s in range(SAMPLES):
        gh, comm, norm, _ = run_sd_dynamics(lambda x, e=eps: sd_perturbed_anti_diag(x, e))
        gh_at = gh[20:]
        mean_gh = np.mean(gh_at)
        cv = np.std(gh_at) / (abs(mean_gh) + 1e-15)
        cvs.append(cv)
        comms.append(np.mean(comm[20:]))
    
    exp3[eps] = {'cv': np.mean(cvs), 'cv_std': np.std(cvs), 'comm': np.mean(comms)}
    print(f"  ε={eps:.3f}: CV={np.mean(cvs):.4f}±{np.std(cvs):.4f}, ||[D,C]||={np.mean(comms):.4f}")

# Recovery threshold
base_cv = exp3[0]['cv']
for eps in epsilons:
    if exp3[eps]['cv'] < base_cv * 0.5:
        print(f"\n  → ε={eps:.3f} halves the CV (from {base_cv:.4f} to {exp3[eps]['cv']:.4f})")
        break

# ============================================================
# EXP 4: Commutator as predictor
# ============================================================
print("\n" + "=" * 60)
print("EXP 4: Commutator vs CV across all architectures")
print("=" * 60)

all_cvs = []
all_comms = []

for name, make_C in configs.items():
    for s in range(SAMPLES):
        gh, comm, norm, _ = run_sd_dynamics(make_C)
        gh_at = gh[20:]
        mean_gh = np.mean(gh_at)
        cv = np.std(gh_at) / (abs(mean_gh) + 1e-15)
        all_cvs.append(cv)
        all_comms.append(np.mean(comm[20:]))

# Overall correlation
r, p = pearsonr(all_comms, all_cvs)
print(f"  Overall Pearson(||[D,C]||, CV) = {r:.4f}, p = {p:.6f}")

# Per-architecture correlation
for name, make_C in configs.items():
    arch_cvs, arch_comms = [], []
    for s in range(SAMPLES):
        gh, comm, norm, _ = run_sd_dynamics(make_C)
        gh_at = gh[20:]
        mean_gh = np.mean(gh_at)
        cv = np.std(gh_at) / (abs(mean_gh) + 1e-15)
        arch_cvs.append(cv)
        arch_comms.append(np.mean(comm[20:]))
    
    if np.std(arch_cvs) > 1e-10 and np.std(arch_comms) > 1e-10:
        r_arch, p_arch = pearsonr(arch_comms, arch_cvs)
        print(f"  {name:12s}: r={r_arch:.4f}, p={p_arch:.4f}")
    else:
        print(f"  {name:12s}: constant values, no correlation")

# Anti-diagonal commutator is it maximal?
mean_comms = {name: exp1[name]['comm_mean'] for name in exp1}
print(f"\n  Commutator ranking: {sorted(mean_comms.items(), key=lambda x: -x[1])}")

# ============================================================
# EXP 5: Spectral shape stability for anti-diagonal
# ============================================================
print("\n" + "=" * 60)
print("EXP 5: Spectral shape stability analysis")
print("=" * 60)

for name, make_C in configs.items():
    shape_vars = []
    for s in range(SAMPLES):
        x = np.random.randn(N) * 0.1
        spectra = []
        for t in range(STEPS):
            C = make_C(x)
            eigvals = np.abs(np.linalg.eigvals(C))
            # Normalize to probability distribution
            total = np.sum(eigvals)
            if total > 1e-15:
                spectra.append(eigvals / total)
            x = np.tanh(C @ x) + np.random.randn(N) * NOISE
        
        # Measure spectral shape variation (EMD-like: L2 between consecutive spectra)
        if len(spectra) > 20:
            spectra = spectra[20:]
            shape_var = np.mean([np.linalg.norm(np.array(spectra[t]) - np.array(spectra[t-1])) 
                                for t in range(1, len(spectra))])
            shape_vars.append(shape_var)
    
    if shape_vars:
        print(f"  {name:12s}: spectral_shape_var={np.mean(shape_vars):.6f}±{np.std(shape_vars):.6f}")

# ============================================================
# EXP 6: Why anti-diagonal breaks conservation — detailed trace
# ============================================================
print("\n" + "=" * 60)
print("EXP 6: Detailed trace of anti-diagonal dynamics")
print("=" * 60)

x = np.array([0.5, -0.3, 0.8, -0.1, 0.6])  # fixed initial state
print(f"Initial x: {x}")

for t in range(15):
    C = sd_anti_diagonal(x)
    eigvals = np.linalg.eigvals(C)
    gamma, H = spectral_metrics(C)
    sat = 1 - np.tanh(C @ x)**2
    comm = commutator_norm(sat, C)
    
    print(f"\n  t={t}: x={np.round(x, 4)}")
    print(f"    C (nonzero): {[(i, N-1-i, round(C[i, N-1-i], 4)) for i in range(N)]}")
    print(f"    |eigvals|: {np.round(np.sort(np.abs(eigvals))[::-1], 4)}")
    print(f"    γ={gamma:.4f}, H={H:.4f}, γ+H={gamma+H:.4f}")
    print(f"    sech²={np.round(sat, 4)}, ||[D,C]||={comm:.4f}")
    print(f"    participation: {np.round(np.abs(eigvals)/np.sum(np.abs(eigvals)), 4)}")
    
    x = np.tanh(C @ x) + np.random.randn(N) * NOISE

# ============================================================
# EXP 7: Real-world analog — PT-symmetric systems
# ============================================================
print("\n" + "=" * 60)
print("EXP 7: Physical analogs of anti-diagonal coupling")
print("=" * 60)

# Anti-diagonal = exchange/reversal operator
# In physics: parity operator P, time-reversal T
# PT-symmetric systems have balanced gain/loss → our "anti-diagonal coupling"

# Test: anti-diagonal with equal magnitudes (PT-symmetric)
def sd_pt_symmetric(x):
    """PT-symmetric: anti-diagonal with conjugate pair entries"""
    n = len(x)
    C = np.zeros((n, n))
    for i in range(n):
        j = n - 1 - i
        if i <= j:
            val = x[j]  # coupled to partner
            C[i, j] = val
            C[j, i] = val  # symmetric for physicality
    return C

gh, comm, norm, _ = run_sd_dynamics(sd_pt_symmetric)
gh_at = gh[20:]
cv_pt = np.std(gh_at) / (abs(np.mean(gh_at)) + 1e-15)
print(f"  PT-symmetric (symmetric anti-diag): CV={cv_pt:.4f}")

# Pure reversal (exchange matrix scaled by state)
def sd_reversal(x):
    n = len(x)
    C = np.zeros((n, n))
    for i in range(n):
        C[i, n-1-i] = np.abs(x[n-1-i])
    return C

gh, comm, norm, _ = run_sd_dynamics(sd_reversal)
gh_at = gh[20:]
cv_rev = np.std(gh_at) / (abs(np.mean(gh_at)) + 1e-15)
print(f"  Reversal coupling: CV={cv_rev:.4f}")

# "Mirror neuron" coupling: each agent sees only the opposite agent's state
# This is literally anti-diagonal in agent-space
print(f"\n  Real-world analog: mirror/reflection coupling")
print(f"  In optical systems: beam splitter + mirror = anti-diagonal transfer matrix")
print(f"  In neural circuits: contralateral (cross-brain) connections")
print(f"  In spin chains: reflections at boundaries")

# ============================================================
# Save all results
# ============================================================
results = {
    'exp1': {k: {kk: float(vv) for kk, vv in v.items()} for k, v in exp1.items()},
    'exp2': {str(k): {kk: float(vv) for kk, vv in v.items()} for k, v in exp2.items()},
    'exp3': {str(k): {kk: float(vv) for kk, vv in v.items()} for k, v in exp3.items()},
    'exp5_physical': {'pt_symmetric_cv': float(cv_pt), 'reversal_cv': float(cv_rev)},
    'commutator_correlation': {'r': float(r), 'p': float(p)},
}

with open(os.path.join(OUT, 'exp_results_v2.json'), 'w') as f:
    json.dump(results, f, indent=2)

print(f"\nResults saved to {OUT}/exp_results_v2.json")
print("Done!")
