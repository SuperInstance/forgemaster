#!/usr/bin/env python3
"""
Cycle 016: Anti-Diagonal Anatomy & Conservation Boundary
Why does anti-diagonal coupling break conservation while maintaining contractivity?
"""

import numpy as np
from scipy import linalg
from scipy.stats import pearsonr
import json
import os

np.random.seed(42)

N = 5          # Small system
SAMPLES = 50   # Samples per experiment
STEPS = 100    # Dynamics steps

OUT = "/home/phoenix/.openclaw/workspace/experiments/gpu-loop/cycle-016"

# ============================================================
# Helper functions
# ============================================================

def make_diagonal(n, scale=1.0):
    """Diagonal coupling matrix"""
    D = np.diag(np.random.randn(n) * scale)
    return D

def make_anti_diagonal(n, scale=1.0):
    """Anti-diagonal coupling matrix (nonzero only on anti-diagonal)"""
    A = np.zeros((n, n))
    anti_diag = np.random.randn(n) * scale
    for i in range(n):
        A[i, n-1-i] = anti_diag[i]
    return A

def make_random_goe(n, scale=1.0):
    """GOE random matrix"""
    M = np.random.randn(n, n) * scale / np.sqrt(n)
    return (M + M.T) / 2

def make_mixed(n, alpha, scale=1.0):
    """Interpolate: diagonal (alpha=0) → random (alpha=0.5) → anti-diagonal (alpha=1)"""
    if alpha <= 0.5:
        # diagonal → random
        t = alpha * 2  # 0→1
        D = make_diagonal(n, scale)
        R = make_random_goe(n, scale)
        return (1 - t) * D + t * R
    else:
        # random → anti-diagonal
        t = (alpha - 0.5) * 2  # 0→1
        R = make_random_goe(n, scale)
        A = make_anti_diagonal(n, scale)
        return (1 - t) * R + t * A

def spectral_metrics(C):
    """Compute γ (participation ratio) and H (spectral entropy) for eigenvalue magnitudes"""
    eigvals = np.linalg.eigvals(C)
    mags = np.abs(eigvals)
    total = np.sum(mags)
    if total < 1e-15:
        return 0.0, 0.0
    probs = mags / total
    probs = probs[probs > 1e-15]
    H = -np.sum(probs * np.log(probs))
    gamma = (np.sum(mags))**2 / np.sum(mags**2)
    return gamma, H

def run_dynamics(C, steps=STEPS, noise_sigma=0.01):
    """Run tanh dynamics: x_{t+1} = tanh(C @ x_t) + noise"""
    x = np.random.randn(N) * 0.1
    trajectory = []
    for t in range(steps):
        x = np.tanh(C @ x) + np.random.randn(N) * noise_sigma
        gamma, H = spectral_metrics(C)
        trajectory.append({
            'x': x.copy(),
            'gamma': gamma,
            'H': H,
            'gh': gamma + H,
            'norm': np.linalg.norm(x)
        })
    return trajectory

def run_state_dependent_dynamics(make_C, steps=STEPS, noise_sigma=0.01):
    """Run state-dependent tanh dynamics where C depends on x"""
    x = np.random.randn(N) * 0.1
    trajectory = []
    for t in range(steps):
        C = make_C(x)
        x = np.tanh(C @ x) + np.random.randn(N) * noise_sigma
        gamma, H = spectral_metrics(C)
        trajectory.append({
            'x': x.copy(),
            'gamma': gamma,
            'H': H,
            'gh': gamma + H,
            'norm': np.linalg.norm(x),
            'eigvals': np.sort(np.abs(np.linalg.eigvals(C)))[::-1]
        })
    return trajectory

def commutator_norm(D_diag, C):
    """Compute ||[D, C]||_F where D is diagonal matrix from D_diag"""
    D = np.diag(D_diag)
    comm = D @ C - C @ D
    return np.linalg.norm(comm, 'fro')

def contractivity(C):
    """Compute spectral radius and check contractivity"""
    eigvals = np.linalg.eigvals(C)
    return np.max(np.abs(eigvals))

def eigenvalue_spectrum_analysis(C):
    """Detailed spectral analysis"""
    eigvals, eigvecs = np.linalg.eig(C)
    mags = np.abs(eigvals)
    phases = np.angle(eigvals)
    sorted_idx = np.argsort(mags)[::-1]
    return {
        'eigenvalues': eigvals[sorted_idx],
        'magnitudes': mags[sorted_idx],
        'phases': phases[sorted_idx],
        'eigenvectors': eigvecs[:, sorted_idx],
        'condition_number': np.max(mags) / (np.min(mags) + 1e-15),
        'spectral_gap': mags[sorted_idx[0]] - mags[sorted_idx[1]] if len(mags) > 1 else 0
    }

# ============================================================
# EXP 1: Anti-diagonal anatomy
# ============================================================
print("=" * 60)
print("EXP 1: Anti-diagonal spectral anatomy")
print("=" * 60)

exp1_results = {
    'anti_diag': {'spectra': [], 'trajectories': [], 'cv_gh': [], 'commutators': []},
    'diagonal': {'spectra': [], 'trajectories': [], 'cv_gh': [], 'commutators': []},
    'random': {'spectra': [], 'trajectories': [], 'cv_gh': [], 'commutators': []}
}

for sample in range(SAMPLES):
    for name, make_fn in [
        ('anti_diag', lambda: make_anti_diagonal(N)),
        ('diagonal', lambda: make_diagonal(N)),
        ('random', lambda: make_random_goe(N))
    ]:
        C = make_fn()
        spec = eigenvalue_spectrum_analysis(C)
        traj = run_dynamics(C, STEPS)
        gh_vals = [t['gh'] for t in traj[10:]]  # skip transient
        cv = np.std(gh_vals) / (np.mean(gh_vals) + 1e-15)
        
        # Commutator with saturation diagonal
        x_ss = traj[-1]['x']
        D_diag = 1 - np.tanh(C @ x_ss)**2  # sech^2 saturation
        comm = commutator_norm(D_diag, C)
        
        rho = contractivity(C)
        
        exp1_results[name]['spectra'].append({
            'eigvals_real': spec['eigenvalues'].real.tolist(),
            'eigvals_imag': spec['eigenvalues'].imag.tolist(),
            'magnitudes': spec['magnitudes'].tolist(),
            'phases': spec['phases'].tolist(),
            'condition_number': spec['condition_number'],
            'spectral_gap': spec['spectral_gap']
        })
        exp1_results[name]['cv_gh'].append(cv)
        exp1_results[name]['commutators'].append(comm)

# Summarize
for name in ['diagonal', 'random', 'anti_diag']:
    cvs = exp1_results[name]['cv_gh']
    comms = exp1_results[name]['commutators']
    print(f"\n{name}:")
    print(f"  CV(γ+H): mean={np.mean(cvs):.4f}, std={np.std(cvs):.4f}")
    print(f"  Commutator: mean={np.mean(comms):.4f}, std={np.std(comms):.4f}")
    
    # Eigenvalue phase distribution
    all_phases = []
    for s in exp1_results[name]['spectra']:
        all_phases.extend(s['phases'])
    print(f"  Eigenvalue phases: mean={np.mean(all_phases):.3f}, std={np.std(all_phases):.3f}")
    print(f"  Fraction complex: {np.mean([abs(p) > 0.01 for p in all_phases]):.3f}")
    
    # Condition number
    cond_nums = [s['condition_number'] for s in exp1_results[name]['spectra']]
    print(f"  Condition number: mean={np.mean(cond_nums):.2f}, std={np.std(cond_nums):.2f}")

# Key diagnostic: eigenvector structure of anti-diagonal
print("\n--- Anti-diagonal eigenvector analysis ---")
for i in range(min(5, SAMPLES)):
    spec = exp1_results['anti_diag']['spectra'][i]
    C = make_anti_diagonal(N)
    eigvals, eigvecs = np.linalg.eig(C)
    # Check if eigenvectors are structured (alternating signs)
    ev_top = eigvecs[:, 0]
    pattern = np.sign(ev_top.real)
    print(f"  Sample {i}: top eigval={eigvals[0]:.3f}, "
          f"eigvec signs={pattern.real.tolist()}, "
          f"|imag/real|={np.sum(np.abs(eigvals.imag)) / (np.sum(np.abs(eigvals.real)) + 1e-15):.3f}")

# ============================================================
# EXP 2: Boundary mapping (diagonal → random → anti-diagonal)
# ============================================================
print("\n" + "=" * 60)
print("EXP 2: Phase transition sweep (alpha: 0=diag, 0.5=random, 1=anti-diag)")
print("=" * 60)

alphas = np.linspace(0, 1, 21)
exp2_results = {}

for alpha in alphas:
    cvs = []
    comms = []
    rhos = []
    gh_means = []
    
    for sample in range(SAMPLES):
        C = make_mixed(N, alpha)
        traj = run_dynamics(C, STEPS)
        gh_vals = [t['gh'] for t in traj[10:]]
        cv = np.std(gh_vals) / (np.mean(gh_vals) + 1e-15)
        
        x_ss = traj[-1]['x']
        D_diag = 1 - np.tanh(C @ x_ss)**2
        comm = commutator_norm(D_diag, C)
        
        cvs.append(cv)
        comms.append(comm)
        rhos.append(contractivity(C))
        gh_means.append(np.mean(gh_vals))
    
    exp2_results[alpha] = {
        'mean_cv': np.mean(cvs),
        'std_cv': np.std(cvs),
        'mean_comm': np.mean(comms),
        'std_comm': np.std(comms),
        'mean_rho': np.mean(rhos),
        'mean_gh': np.mean(gh_means),
        'max_cv': np.max(cvs)
    }
    print(f"  α={alpha:.2f}: CV={np.mean(cvs):.4f}±{np.std(cvs):.4f}, "
          f"||[D,C]||={np.mean(comms):.4f}, ρ={np.mean(rhos):.3f}")

# Find phase transition
cvs_by_alpha = [exp2_results[a]['mean_cv'] for a in alphas]
# Detect steepest increase
diffs = np.diff(cvs_by_alpha)
transition_alpha = alphas[np.argmax(diffs) + 1]
print(f"\n  Steepest CV increase at α ≈ {transition_alpha:.2f}")

# Correlation between commutator and CV
all_comms = [exp2_results[a]['mean_comm'] for a in alphas]
r_comm_cv, p_comm_cv = pearsonr(all_comms, cvs_by_alpha)
print(f"  Pearson(||[D,C]||, CV) = {r_comm_cv:.4f}, p = {p_comm_cv:.6f}")

# ============================================================
# EXP 3: Conservation restoration by perturbation
# ============================================================
print("\n" + "=" * 60)
print("EXP 3: Can perturbation restore conservation?")
print("=" * 60)

epsilons = [0, 0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0]
exp3_results = {}

for eps in epsilons:
    cvs = []
    comms = []
    
    for sample in range(SAMPLES):
        # Start with anti-diagonal, add random perturbation
        C = make_anti_diagonal(N)
        perturbation = np.random.randn(N, N) * eps / np.sqrt(N)
        C = C + perturbation
        
        traj = run_dynamics(C, STEPS)
        gh_vals = [t['gh'] for t in traj[10:]]
        cv = np.std(gh_vals) / (np.mean(gh_vals) + 1e-15)
        
        x_ss = traj[-1]['x']
        D_diag = 1 - np.tanh(C @ x_ss)**2
        comm = commutator_norm(D_diag, C)
        
        cvs.append(cv)
        comms.append(comm)
    
    exp3_results[eps] = {
        'mean_cv': np.mean(cvs),
        'std_cv': np.std(cvs),
        'mean_comm': np.mean(comms),
        'mean_cv_drop': exp1_results['anti_diag']['cv_gh'] and np.mean(exp1_results['anti_diag']['cv_gh'])
    }
    print(f"  ε={eps:.3f}: CV={np.mean(cvs):.4f}±{np.std(cvs):.4f}, ||[D,C]||={np.mean(comms):.4f}")

# Find smallest ε that drops CV below 0.1
for eps in epsilons:
    if exp3_results[eps]['mean_cv'] < 0.1:
        print(f"\n  → Smallest ε restoring CV<0.1: {eps:.3f}")
        break

# ============================================================
# EXP 4: Commutator analysis for anti-diagonal
# ============================================================
print("\n" + "=" * 60)
print("EXP 4: Commutator deep analysis")
print("=" * 60)

# Compare commutator across architectures
for name in ['diagonal', 'random', 'anti_diag']:
    comms = exp1_results[name]['commutators']
    cvs = exp1_results[name]['cv_gh']
    r, p = pearsonr(comms, cvs)
    print(f"  {name}: mean||[D,C]||={np.mean(comms):.4f}, "
          f"r(||[D,C]||, CV)={r:.4f}, p={p:.6f}")

# Analytical commutator for anti-diagonal
print("\n--- Analytical commutator structure ---")
# For anti-diagonal A (only A[i,n-1-i] nonzero) and diagonal D:
# [D,A]_{ij} = D_{ii}*A_{ij} - A_{ij}*D_{jj}
# Only nonzero when j = n-1-i: (D_{ii} - D_{n-1-i,n-1-i}) * A_{i,n-1-i}
# So ||[D,A]||² = Σ_i (d_i - d_{n-1-i})² * |A_{i,n-1-i}|²

analytical_comms = []
for sample in range(SAMPLES):
    C = make_anti_diagonal(N)
    x_ss = np.random.randn(N) * 0.1
    for _ in range(50):
        x_ss = np.tanh(C @ x_ss)
    D_diag = 1 - x_ss**2
    
    # Analytical formula
    comm_sq = 0
    for i in range(N):
        j = N - 1 - i
        if C[i, j] != 0:
            comm_sq += (D_diag[i] - D_diag[j])**2 * C[i, j]**2
    
    numerical_comm = commutator_norm(D_diag, C)
    analytical_comms.append((np.sqrt(comm_sq), numerical_comm))

mean_analytical = np.mean([a for a, n in analytical_comms])
mean_numerical = np.mean([n for a, n in analytical_comms])
print(f"  Analytical ||[D,A]||: {mean_analytical:.4f}")
print(f"  Numerical  ||[D,A]||: {mean_numerical:.4f}")
print(f"  Match: {abs(mean_analytical - mean_numerical) / (mean_numerical + 1e-15):.6f}")

# Maximal commutator: D_diag varies maximally when saturation is non-uniform
# For anti-diagonal, the coupling maps x_i → depends on x_{n-1-i}
# This means saturation at position i depends on x_{n-1-i}, not x_i
# → D is "scrambled" relative to C → large commutator

print("\n  Mechanism: Anti-diagonal coupling 'reverses' state indices,")
print("  creating misalignment between saturation diagonal D(x) and coupling C.")

# ============================================================
# EXP 5: Physical analog - spin chain with next-nearest-neighbor coupling
# ============================================================
print("\n" + "=" * 60)
print("EXP 5: Physical analogs")
print("=" * 60)

# Anti-diagonal coupling appears in:
# 1. Time-reversal operators (T² = ±1)
# 2. Mirror-symmetric lattice systems
# 3. Exchange matrices (J: J[i,j] = δ_{i,N+1-j})

# Test: exchange matrix as coupling
print("\n--- Exchange matrix (pure anti-diagonal = 1) ---")
J_exchange = np.eye(N)[:, ::-1]  # Perfect anti-diagonal
traj = run_dynamics(J_exchange, STEPS)
gh_vals = [t['gh'] for t in traj[10:]]
cv_exchange = np.std(gh_vals) / (np.mean(gh_vals) + 1e-15)
print(f"  CV(γ+H) = {cv_exchange:.4f}")

spec = eigenvalue_spectrum_analysis(J_exchange)
print(f"  Eigenvalues: {spec['eigenvalues'].real}")
print(f"  Exchange matrix eigenvalues are ±1 (involutory)")

# Symmetrized anti-diagonal (perserves some structure)
print("\n--- Symmetrized anti-diagonal ---")
C_sym = np.zeros((N, N))
for i in range(N):
    val = np.random.randn()
    C_sym[i, N-1-i] = val
    C_sym[N-1-i, i] = val  # symmetric anti-diagonal
traj = run_dynamics(C_sym, STEPS)
gh_vals = [t['gh'] for t in traj[10:]]
cv_sym = np.std(gh_vals) / (np.mean(gh_vals) + 1e-15)
print(f"  CV(γ+H) = {cv_sym:.4f}")

# Toeplitz with anti-diagonal dominance
print("\n--- Toeplitz with anti-diagonal elements ---")
C_toep = np.zeros((N, N))
for i in range(N):
    for j in range(N):
        if abs(i + j - (N-1)) <= 1:  # near anti-diagonal
            C_toep[i, j] = np.random.randn()
traj = run_dynamics(C_toep, STEPS)
gh_vals = [t['gh'] for t in traj[10:]]
cv_toep = np.std(gh_vals) / (np.mean(gh_vals) + 1e-15)
print(f"  CV(γ+H) = {cv_toep:.4f}")

# ============================================================
# EXP 6: Eigenvalue phase structure of anti-diagonal
# ============================================================
print("\n" + "=" * 60)
print("EXP 6: Eigenvalue phase analysis")
print("=" * 60)

# For anti-diagonal matrix, eigenvalues come in conjugate pairs
# because the matrix is related to a circulant/permuted structure
for sample in range(5):
    C = make_anti_diagonal(N)
    eigvals = np.linalg.eigvals(C)
    print(f"  Sample {sample}:")
    for ev in eigvals:
        print(f"    λ = {ev.real:+.4f} {ev.imag:+.4f}i  |λ|={abs(ev):.4f}  phase={np.angle(ev):.4f}")
    
    # Check pairing
    mags = np.abs(eigvals)
    phases = np.angle(eigvals)
    print(f"    Magnitude pairs: {sorted(mags.round(4))}")
    
    # Fraction of eigenvalue magnitude in imaginary part
    total_mag = np.sum(np.abs(eigvals))
    imag_fraction = np.sum(np.abs(eigvals.imag)) / (total_mag + 1e-15)
    print(f"    Imaginary fraction: {imag_fraction:.4f}")

# ============================================================
# EXP 7: State-dependent anti-diagonal coupling
# ============================================================
print("\n" + "=" * 60)
print("EXP 7: State-dependent anti-diagonal coupling")
print("=" * 60)

def make_state_dep_anti_diag(x):
    """Anti-diagonal coupling that depends on state"""
    n = len(x)
    C = np.zeros((n, n))
    for i in range(n):
        C[i, n-1-i] = x[n-1-i]  # reversed coupling
    return C

def make_state_dep_diag(x):
    """Diagonal coupling that depends on state"""
    n = len(x)
    return np.diag(x)

def make_state_dep_random(x):
    """Random coupling that depends on state"""
    n = len(x)
    return np.outer(x, np.random.randn(n)) / n

for name, make_fn in [
    ('SD anti-diag', make_state_dep_anti_diag),
    ('SD diagonal', make_state_dep_diag),
]:
    cvs = []
    comms = []
    for sample in range(SAMPLES):
        traj = run_state_dependent_dynamics(make_fn, STEPS)
        gh_vals = [t['gh'] for t in traj[10:]]
        cv = np.std(gh_vals) / (np.mean(gh_vals) + 1e-15)
        cvs.append(cv)
        
        # Commutator at last step
        x_ss = traj[-1]['x']
        C = make_fn(x_ss)
        D_diag = 1 - x_ss**2
        comm = commutator_norm(D_diag, C)
        comms.append(comm)
    
    print(f"  {name}: CV={np.mean(cvs):.4f}±{np.std(cvs):.4f}, ||[D,C]||={np.mean(comms):.4f}")

# ============================================================
# Save results
# ============================================================
summary = {
    'exp1': {
        name: {
            'mean_cv': float(np.mean(exp1_results[name]['cv_gh'])),
            'mean_comm': float(np.mean(exp1_results[name]['commutators']))
        } for name in ['diagonal', 'random', 'anti_diag']
    },
    'exp2': {str(a): exp2_results[a] for a in alphas},
    'exp3': {str(e): exp3_results[e] for e in epsilons},
    'exp5': {
        'exchange_cv': float(cv_exchange),
        'symmetric_anti_cv': float(cv_sym),
        'toeplitz_anti_cv': float(cv_toep)
    }
}

# Convert numpy types
def convert(obj):
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, dict):
        return {k: convert(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert(x) for x in obj]
    return obj

summary = convert(summary)

with open(os.path.join(OUT, 'exp_results.json'), 'w') as f:
    json.dump(summary, f, indent=2)

print(f"\nResults saved to {OUT}/exp_results.json")
print("Done!")
