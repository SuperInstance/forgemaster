#!/usr/bin/env python3
"""Cycle 8: Attractor geometry and the quadratic form P under nonlinear tanh dynamics."""

import numpy as np
from scipy import linalg
from scipy.optimize import fsolve
from scipy.stats import pearsonr
import json
import warnings
warnings.filterwarnings('ignore')

np.random.seed(42)

N = 20  # matrix size
STEPS = 200
SAMPLES = 50
NOISE_STD = 0.1  # noise to prevent trivial fixed-point convergence

def random_coupling(n):
    """GOE random matrix"""
    W = np.random.randn(n, n) / np.sqrt(n)
    return (W + W.T) / 2

def hebbian_coupling(n):
    """Hebbian-like structured matrix"""
    patterns = np.random.randn(n, n)
    return patterns @ patterns.T / n

def attention_coupling(n, temperature=1.0):
    """Softmax attention-like row-stochastic matrix"""
    W = np.random.randn(n, n) / np.sqrt(n)
    S = np.exp(W / temperature)
    return S / S.sum(axis=1, keepdims=True)

def spectral_gap(C):
    """Largest - second largest eigenvalue magnitude"""
    eigvals = np.sort(np.abs(np.linalg.eigvalsh(C)))[::-1]
    return eigvals[0] - eigvals[1] if len(eigvals) > 1 else eigvals[0]

def participation_entropy(C):
    """Entropy of eigenvalue participation"""
    eigvals = np.abs(np.linalg.eigvalsh(C))
    p = eigvals / eigvals.sum()
    p = p[p > 1e-12]
    return -np.sum(p * np.log(p))

def compute_gamma_H(C):
    """Compute γ+H from coupling matrix C"""
    return spectral_gap(C) + participation_entropy(C)

def run_tanh_dynamics(C, x0, steps=STEPS, noise_std=NOISE_STD):
    """Run x_{t+1} = tanh(C @ x_t) + noise"""
    n = len(x0)
    xs = [x0.copy()]
    for t in range(steps):
        x = np.tanh(C @ xs[-1])
        if noise_std > 0:
            x += np.random.randn(n) * noise_std
        xs.append(x)
    return np.array(xs)

def find_fixed_point(C, n=N, tol=1e-10, max_iter=5000):
    """Find x* = tanh(Cx*) by iterating to convergence"""
    x = np.random.randn(n) * 0.1
    for i in range(max_iter):
        x_new = np.tanh(C @ x)
        if np.linalg.norm(x_new - x) < tol:
            return x_new, i, True
        x = x_new
    return x, max_iter, False

def compute_eigendecomp(C):
    """Eigenvalues and eigenvectors"""
    eigvals, eigvecs = np.linalg.eigh(C)
    idx = np.argsort(np.abs(eigvals))[::-1]
    return eigvals[idx], eigvecs[:, idx]

def subspace_angle(v1, v2):
    """Angle between two vectors in degrees"""
    cos_theta = np.clip(np.abs(np.dot(v1, v2)) / (np.linalg.norm(v1) * np.linalg.norm(v2)), 0, 1)
    return np.degrees(np.arccos(cos_theta))

# =============================================================================
# MISSION 1: Characterize the fixed point x* = tanh(Cx*)
# =============================================================================
print("=" * 70)
print("MISSION 1: Fixed Point Characterization")
print("=" * 70)

architectures = {
    'random': lambda: random_coupling(N),
    'hebbian': lambda: hebbian_coupling(N),
    'attention_tau1': lambda: attention_coupling(N, 1.0),
    'attention_tau01': lambda: attention_coupling(N, 0.1),
    'attention_tau5': lambda: attention_coupling(N, 5.0),
    'degenerate': lambda: np.eye(N) * 1.5,  # s*I, s > 1
}

fixed_point_results = {}

for arch_name, arch_fn in architectures.items():
    fp_data = []
    for sample in range(SAMPLES):
        C = arch_fn()
        x_star, iters, converged = find_fixed_point(C)
        eigvals, eigvecs = compute_eigendecomp(C)
        
        # How aligned is x* with top eigenvectors?
        top_vec = eigvecs[:, 0]
        alignment_top = np.abs(np.dot(x_star, top_vec)) / (np.linalg.norm(x_star) + 1e-12)
        
        # Projection onto top-k eigenvectors
        projections = []
        for k in [1, 2, 3, 5, 10]:
            proj = sum(np.dot(x_star, eigvecs[:, j])**2 for j in range(k))
            total = np.dot(x_star, x_star) + 1e-12
            projections.append(proj / total)
        
        # γ+H at the fixed point
        gamma_H_fp = compute_gamma_H(C)
        
        fp_data.append({
            'converged': converged,
            'iterations': iters,
            'x_star_norm': np.linalg.norm(x_star),
            'alignment_top_eigvec': alignment_top,
            'proj_top1': projections[0],
            'proj_top2': projections[1],
            'proj_top3': projections[2],
            'proj_top5': projections[3],
            'proj_top10': projections[4],
            'gamma_H_at_fp': gamma_H_fp,
        })
    
    fixed_point_results[arch_name] = fp_data
    
    conv_rate = np.mean([d['converged'] for d in fp_data])
    mean_iters = np.mean([d['iterations'] for d in fp_data])
    mean_norm = np.mean([d['x_star_norm'] for d in fp_data])
    mean_align = np.mean([d['alignment_top_eigvec'] for d in fp_data])
    mean_proj = [np.mean([d[f'proj_top{k}'] for d in fp_data]) for k in [1,2,3,5,10]]
    
    print(f"\n{arch_name}:")
    print(f"  Convergence: {conv_rate:.0%}, mean iterations: {mean_iters:.1f}")
    print(f"  ||x*||: {mean_norm:.4f}")
    print(f"  |cos(x*, v_top)|: {mean_align:.4f}")
    print(f"  Energy in top-k eigenvectors: k=1: {mean_proj[0]:.3f}, k=3: {mean_proj[2]:.3f}, k=5: {mean_proj[3]:.3f}, k=10: {mean_proj[4]:.3f}")

# =============================================================================
# MISSION 2: γ+H at the fixed point — spectral properties
# =============================================================================
print("\n" + "=" * 70)
print("MISSION 2: γ+H at the Fixed Point")
print("=" * 70)

# For each architecture, compare γ+H at x* vs γ+H at random x
for arch_name, arch_fn in architectures.items():
    gh_at_fp = []
    gh_at_random = []
    gh_at_trajectory = []
    
    for sample in range(SAMPLES):
        C = arch_fn()
        x_star, _, _ = find_fixed_point(C)
        
        gh_fp = compute_gamma_H(C)
        gh_at_fp.append(gh_fp)
        
        # Random x
        x_rand = np.random.randn(N) * 0.5
        gh_rand = compute_gamma_H(C)
        gh_at_random.append(gh_rand)
        
        # Along a trajectory
        x0 = np.random.randn(N) * 0.1
        traj = run_tanh_dynamics(C, x0, steps=200, noise_std=NOISE_STD)
        gh_traj = [compute_gamma_H(C) for _ in traj]  # C is fixed, so same value
        gh_at_trajectory.append(np.mean(gh_traj))
    
    # Since C is FIXED, γ+H is the same regardless of x state
    # The variation comes from DIFFERENT C matrices
    cv_fp = np.std(gh_at_fp) / (np.mean(gh_at_fp) + 1e-12)
    cv_rand = np.std(gh_at_random) / (np.mean(gh_at_random) + 1e-12)
    
    print(f"\n{arch_name}:")
    print(f"  γ+H at x*: mean={np.mean(gh_at_fp):.4f}, CV={cv_fp:.4f}")
    print(f"  γ+H at random x: mean={np.mean(gh_at_random):.4f}, CV={cv_rand:.4f}")
    print(f"  Note: C is FIXED → γ+H depends on C only, not x")

# Key insight: with static C, γ+H is constant regardless of state
# Now test with STATE-DEPENDENT coupling
print("\n--- State-Dependent Coupling ---")

def state_dependent_attention(x, temperature=1.0):
    """State-dependent attention: C(x) = softmax(x ⊗ x^T / τ)"""
    n = len(x)
    logits = np.outer(x, x) / temperature
    logits -= logits.max(axis=1, keepdims=True)  # numerical stability
    S = np.exp(logits)
    return S / S.sum(axis=1, keepdims=True)

def state_dependent_hebbian(x):
    """State-dependent Hebbian: C(x) = x x^T / N"""
    n = len(x)
    return np.outer(x, x) / n

for sd_name, sd_fn in [('attention_sd_tau1', lambda x: state_dependent_attention(x, 1.0)),
                         ('attention_sd_tau01', lambda x: state_dependent_attention(x, 0.1)),
                         ('attention_sd_tau5', lambda x: state_dependent_attention(x, 5.0)),
                         ('hebbian_sd', state_dependent_hebbian)]:
    
    gh_trajectory_all = []
    x_norms = []
    fp_gh_values = []
    
    for sample in range(SAMPLES):
        x = np.random.randn(N) * 0.1
        
        # Find fixed point for state-dependent coupling
        for _ in range(1000):
            C_x = sd_fn(x)
            x_new = np.tanh(C_x @ x)
            if np.linalg.norm(x_new - x) < 1e-10:
                break
            x = x_new
        
        C_fp = sd_fn(x)
        fp_gh = compute_gamma_H(C_fp)
        fp_gh_values.append(fp_gh)
        
        # Run trajectory with state-dependent coupling
        x = np.random.randn(N) * 0.1
        gh_traj = []
        for t in range(200):
            C_t = sd_fn(x)
            gh = compute_gamma_H(C_t)
            gh_traj.append(gh)
            x = np.tanh(C_t @ x) + np.random.randn(N) * NOISE_STD
            x_norms.append(np.linalg.norm(x))
        
        gh_trajectory_all.extend(gh_traj)
    
    cv_gh = np.std(gh_trajectory_all) / (np.mean(gh_trajectory_all) + 1e-12)
    cv_fp_gh = np.std(fp_gh_values) / (np.mean(fp_gh_values) + 1e-12)
    
    print(f"\n{sd_name}:")
    print(f"  γ+H along trajectory: mean={np.mean(gh_trajectory_all):.4f}, CV={cv_gh:.4f}")
    print(f"  γ+H at fixed point: mean={np.mean(fp_gh_values):.4f}, CV={cv_fp_gh:.4f}")

# =============================================================================
# MISSION 3: Eigenvector Stability During tanh Dynamics
# =============================================================================
print("\n" + "=" * 70)
print("MISSION 3: Eigenvector Rotation During tanh Dynamics")
print("=" * 70)

for sd_name, sd_fn in [('attention_sd_tau1', lambda x: state_dependent_attention(x, 1.0)),
                         ('hebbian_sd', state_dependent_hebbian)]:
    
    rotation_angles = []
    gh_values = []
    
    for sample in range(SAMPLES):
        x = np.random.randn(N) * 0.1
        prev_eigvecs = None
        
        for t in range(100):
            C_t = sd_fn(x)
            eigvals, eigvecs = compute_eigendecomp(C_t)
            
            gh = compute_gamma_H(C_t)
            gh_values.append(gh)
            
            if prev_eigvecs is not None:
                # Rotation of top eigenvector
                angle = subspace_angle(eigvecs[:, 0], prev_eigvecs[:, 0])
                rotation_angles.append(angle)
            
            prev_eigvecs = eigvecs
            x = np.tanh(C_t @ x) + np.random.randn(N) * NOISE_STD
    
    mean_rot = np.mean(rotation_angles)
    std_rot = np.std(rotation_angles)
    cv_gh = np.std(gh_values) / (np.mean(gh_values) + 1e-12)
    
    # Correlation between eigenvector rotation and γ+H change
    gh_arr = np.array(gh_values)
    if len(rotation_angles) > 10:
        gh_diffs = np.abs(np.diff(gh_arr))
        min_len = min(len(rotation_angles), len(gh_diffs))
        r, p = pearsonr(rotation_angles[:min_len], gh_diffs[:min_len])
    else:
        r, p = 0, 1
    
    print(f"\n{sd_name}:")
    print(f"  Top eigenvector rotation: mean={mean_rot:.2f}°, std={std_rot:.2f}°")
    print(f"  CV(γ+H): {cv_gh:.4f}")
    print(f"  Rotation vs |Δγ+H| correlation: r={r:.3f}, p={p:.4f}")

# =============================================================================
# MISSION 4: What IS the matrix P? (γ+H = x^T P x)
# =============================================================================
print("\n" + "=" * 70)
print("MISSION 4: Characterizing the Quadratic Form Matrix P")
print("=" * 70)

# Generate trajectory data and fit P
# With state-dependent coupling, γ+H varies with x
# Test: is γ+H ≈ x^T P x?

for sd_name, sd_fn in [('attention_sd_tau1', lambda x: state_dependent_attention(x, 1.0)),
                         ('hebbian_sd', state_dependent_hebbian)]:
    
    X_data = []  # state vectors
    gh_data = []  # γ+H values
    
    for sample in range(30):
        x = np.random.randn(N) * 0.1
        for t in range(100):
            C_t = sd_fn(x)
            gh = compute_gamma_H(C_t)
            X_data.append(x.copy())
            gh_data.append(gh)
            x = np.tanh(C_t @ x) + np.random.randn(N) * NOISE_STD
    
    X = np.array(X_data)
    y = np.array(gh_data)
    
    # Fit quadratic form: γ+H = x^T P x
    # x^T P x = sum_{i,j} P_ij x_i x_j
    # Build feature matrix: all x_i * x_j
    n_samples = len(y)
    n = N
    n_features = n * (n + 1) // 2  # upper triangle
    
    Phi = np.zeros((n_samples, n_features))
    for s in range(n_samples):
        idx = 0
        for i in range(n):
            for j in range(i, n):
                Phi[s, idx] = X[s, i] * X[s, j]
                idx += 1
    
    # Least squares fit
    coeffs, residuals, rank, sv = np.linalg.lstsq(Phi, y, rcond=None)
    y_pred = Phi @ coeffs
    
    if len(y) > 1:
        ss_res = np.sum((y - y_pred)**2)
        ss_tot = np.sum((y - np.mean(y))**2)
        r_squared = 1 - ss_res / ss_tot
    else:
        r_squared = 0
    
    # Reconstruct P from coefficients
    P = np.zeros((n, n))
    idx = 0
    for i in range(n):
        for j in range(i, n):
            P[i, j] = coeffs[idx]
            P[j, i] = coeffs[idx]
            idx += 1
    
    # Test hypotheses for P
    # Hypothesis 1: P ∝ C^T C (but C varies, so test with mean C)
    # Hypothesis 2: P ∝ I
    # Hypothesis 3: P = diag(sech²(Cx*)) — test later
    
    # P's eigenvalue structure
    P_eigvals = np.linalg.eigvalsh(P)
    
    # Is P diagonal-dominated?
    diag_norm = np.linalg.norm(np.diag(P))
    offdiag_norm = np.linalg.norm(P - np.diag(np.diag(P)))
    
    # Trace and determinant
    tr_P = np.trace(P)
    det_P = np.linalg.det(P)
    
    # Positive definiteness
    min_eig = np.min(P_eigvals)
    max_eig = np.max(P_eigvals)
    
    # Test: γ+H vs ||x||^2 (P = I hypothesis)
    norms_sq = np.sum(X**2, axis=1)
    r_norm, _ = pearsonr(norms_sq, y)
    
    # Test: γ+H vs x^T x / N (normalized norm)
    r_norm_n, _ = pearsonr(norms_sq / n, y)
    
    # Alternative: is γ+H just ||x||?
    norms = np.sqrt(norms_sq)
    r_norm_lin, _ = pearsonr(norms, y)
    
    print(f"\n{sd_name}:")
    print(f"  R²(γ+H = x^T P x): {r_squared:.6f}")
    print(f"  P eigenvalue range: [{min_eig:.6f}, {max_eig:.6f}]")
    print(f"  P trace: {tr_P:.6f}")
    print(f"  P diag/offdiag norm: {diag_norm:.4f} / {offdiag_norm:.4f}")
    print(f"  P positive definite: {'Yes' if min_eig > 0 else 'No'}")
    print(f"  r(γ+H, ||x||²): {r_norm:.4f}")
    print(f"  r(γ+H, ||x||): {r_norm_lin:.4f}")
    
    # Deeper: P diagonal structure
    diag_vals = np.diag(P)
    print(f"  P diagonal mean: {np.mean(diag_vals):.6f}, std: {np.std(diag_vals):.6f}")
    print(f"  P diagonal range: [{np.min(diag_vals):.6f}, {np.max(diag_vals):.6f}]")
    
    # Test: is P ≈ αI + β·ones?
    ones_matrix = np.ones((n, n)) / n
    alpha = np.mean(diag_vals)
    P_residual = P - alpha * np.eye(n)
    residual_norm = np.linalg.norm(P_residual) / np.linalg.norm(P)
    print(f"  ||P - α·I|| / ||P||: {residual_norm:.4f}")

# =============================================================================
# MISSION 4b: P = α·diag(sech²(Cx*))? Test directly
# =============================================================================
print("\n--- Testing P = diag(sech²(Cx*)) hypothesis ---")

for sd_name, sd_fn in [('attention_sd_tau1', lambda x: state_dependent_attention(x, 1.0))]:
    
    correlations = []
    
    for sample in range(50):
        x = np.random.randn(N) * 0.1
        C = sd_fn(x)
        
        # sech²(Cx) diagonal
        Cx = C @ x
        sech2_diag = 1.0 / np.cosh(Cx)**2
        
        # The Jacobian diagonal
        J = np.diag(sech2_diag) @ C
        
        # γ+H for this C
        gh = compute_gamma_H(C)
        
        # Test: does gh correlate with sum(sech²(Cx))?
        sech2_sum = np.sum(sech2_diag)
        correlations.append((sech2_sum, gh))
    
    sech2_vals = np.array([c[0] for c in correlations])
    gh_vals = np.array([c[1] for c in correlations])
    r_sech, p_sech = pearsonr(sech2_vals, gh_vals)
    print(f"\n{sd_name}: r(Σsech²(Cx), γ+H) = {r_sech:.4f}, p = {p_sech:.6f}")

# =============================================================================
# MISSION 5: Activation Comparison — Bounded vs Unbounded
# =============================================================================
print("\n" + "=" * 70)
print("MISSION 5: Activation Function Comparison")
print("=" * 70)

activations = {
    'tanh': np.tanh,
    'sigmoid': lambda x: 1 / (1 + np.exp(-np.clip(x, -20, 20))),
    'relu': lambda x: np.maximum(0, x),
    'leaky_relu': lambda x: np.where(x > 0, x, 0.01 * x),
    'softplus': lambda x: np.log1p(np.exp(np.clip(x, -20, 20))),
    'clipped_relu': lambda x: np.clip(np.maximum(0, x), 0, 1),
    'elu': lambda x: np.where(x > 0, x, np.exp(x) - 1),
    'swish': lambda x: x / (1 + np.exp(-np.clip(x, -20, 20))),
}

def run_dynamics(C_fn, x0, activation, steps=STEPS, noise_std=NOISE_STD, state_dependent=False):
    """Run dynamics with given activation function"""
    n = len(x0)
    xs = [x0.copy()]
    gh_vals = []
    
    for t in range(steps):
        if state_dependent:
            C_t = C_fn(xs[-1])
        else:
            C_t = C_fn
        
        gh = compute_gamma_H(C_t)
        gh_vals.append(gh)
        
        x_new = activation(C_t @ xs[-1])
        if noise_std > 0:
            x_new += np.random.randn(n) * noise_std
        xs.append(x_new)
    
    return np.array(xs), gh_vals

# Test with static coupling
print("\n--- Static Coupling ---")
for act_name, act_fn in activations.items():
    cv_values = []
    
    for sample in range(SAMPLES):
        C = random_coupling(N)
        x0 = np.random.randn(N) * 0.1
        
        xs, gh_vals = run_dynamics(C, x0, act_fn, state_dependent=False)
        cv = np.std(gh_vals) / (np.mean(gh_vals) + 1e-12)
        cv_values.append(cv)
    
    print(f"  {act_name:15s}: CV(γ+H) = {np.mean(cv_values):.6f} ± {np.std(cv_values):.6f}")

# Test with state-dependent coupling (the interesting case)
print("\n--- State-Dependent Coupling ---")
for act_name, act_fn in activations.items():
    cv_values = []
    state_norms = []
    
    for sample in range(SAMPLES):
        x0 = np.random.randn(N) * 0.1
        
        xs, gh_vals = run_dynamics(
            lambda x: state_dependent_attention(x, 1.0),
            x0, act_fn, state_dependent=True
        )
        
        cv = np.std(gh_vals) / (np.mean(gh_vals) + 1e-12)
        cv_values.append(cv)
        state_norms.append(np.mean(np.linalg.norm(xs, axis=1)))
    
    mean_cv = np.mean(cv_values)
    mean_norm = np.mean(state_norms)
    bounded = act_name in ['tanh', 'sigmoid', 'clipped_relu']
    
    print(f"  {act_name:15s}: CV(γ+H) = {mean_cv:.4f} ± {np.std(cv_values):.4f}  |  ||x||={mean_norm:.3f}  |  bounded={bounded}")

# =============================================================================
# SUMMARY: Fixed point structure analysis
# =============================================================================
print("\n" + "=" * 70)
print("SUMMARY: Fixed Point Structure")
print("=" * 70)

# For scaled identity matrices C = s*I, we can solve analytically
# x* = tanh(s*x*) has solutions: x* = 0 (always), and ±x* for s > 1

print("\nAnalytical fixed points for C = s·I:")
for s in [0.5, 0.8, 1.0, 1.2, 1.5, 2.0, 3.0, 5.0]:
    C = np.eye(N) * s
    
    # Find fixed point numerically
    x_star, iters, converged = find_fixed_point(C)
    
    # For s*I, tanh(s*x_i) = x_i for each component independently
    # Solutions: x_i = 0, or x_i satisfying x_i = tanh(s*x_i)
    # For s > 1, non-zero solutions exist
    
    # Analytical: x* satisfies x = tanh(s*x), so x = 0 or x = ±a where a = tanh(s*a)
    # This has a bifurcation at s = 1
    
    fp_norm = np.linalg.norm(x_star)
    mean_comp = np.mean(np.abs(x_star))
    
    # Spectral properties at fixed point
    gamma = spectral_gap(C)
    H = participation_entropy(C)
    
    print(f"  s={s:.1f}: converged={converged}, ||x*||={fp_norm:.4f}, <|x*_i|>={mean_comp:.4f}, γ={gamma:.4f}, H={H:.4f}, γ+H={gamma+H:.4f}")

print("\n" + "=" * 70)
print("KEY FINDING: Fixed point and quadratic form relationship")
print("=" * 70)

# Test: for various C, compute P and relate to C's eigendecomposition
print("\nFitting P for attention state-dependent coupling...")
X_all = []
gh_all = []
C_eigvals_all = []

for sample in range(100):
    x = np.random.randn(N) * 0.1
    C_x = state_dependent_attention(x, 1.0)
    eigvals, _ = compute_eigendecomp(C_x)
    C_eigvals_all.append(eigvals)
    
    gh = compute_gamma_H(C_x)
    X_all.append(x)
    gh_all.append(gh)

X_all = np.array(X_all)
gh_all = np.array(gh_all)

# Fit P
n = N
Phi = np.zeros((len(gh_all), n * (n + 1) // 2))
for s in range(len(gh_all)):
    idx = 0
    for i in range(n):
        for j in range(i, n):
            Phi[s, idx] = X_all[s, i] * X_all[s, j]
            idx += 1

coeffs, _, _, _ = np.linalg.lstsq(Phi, gh_all, rcond=None)
y_pred = Phi @ coeffs
ss_res = np.sum((gh_all - y_pred)**2)
ss_tot = np.sum((gh_all - np.mean(gh_all))**2)
r_sq = 1 - ss_res / ss_tot

print(f"  R²(γ+H = x^T P x): {r_sq:.6f}")

# Reconstruct P
P = np.zeros((n, n))
idx = 0
for i in range(n):
    for j in range(i, n):
        P[i, j] = coeffs[idx]
        P[j, i] = coeffs[idx]
        idx += 1

P_eigvals = np.linalg.eigvalsh(P)
print(f"  P eigenvalue range: [{P_eigvals.min():.6f}, {P_eigvals.max():.6f}]")
print(f"  P trace: {np.trace(P):.6f}")
print(f"  P positive definite: {'Yes' if P_eigvals.min() > 0 else 'No'}")
print(f"  P rank (eigenvalues > 1e-6): {np.sum(np.abs(P_eigvals) > 1e-6)}")

# Is P related to the mean C?
mean_C = np.mean([state_dependent_attention(np.random.randn(N)*0.1, 1.0) for _ in range(100)], axis=0)
CTC = mean_C.T @ mean_C

# Compare P and C^T C
P_norm = np.linalg.norm(P)
CTC_norm = np.linalg.norm(CTC)
diff_norm = np.linalg.norm(P - CTC / CTC_norm * P_norm)

print(f"\n  ||P|| = {P_norm:.6f}, ||C^TC|| = {CTC_norm:.6f}")
print(f"  ||P - scaled(C^TC)|| / ||P|| = {diff_norm/P_norm:.4f}")

# Correlation between P and C^T C elements (upper triangle)
p_upper = []
ctc_upper = []
for i in range(n):
    for j in range(i, n):
        p_upper.append(P[i, j])
        ctc_upper.append(CTC[i, j])

r_P_CTC, _ = pearsonr(p_upper, ctc_upper)
print(f"  r(P_ij, (C^TC)_ij): {r_P_CTC:.4f}")

# Test P = α·I + β·1·1^T
I_mat = np.eye(n)
ones_mat = np.ones((n, n))
A_fit = np.column_stack([I_mat.flatten(), ones_mat.flatten()])
beta_fit, _, _, _ = np.linalg.lstsq(A_fit, P.flatten(), rcond=None)
P_model = beta_fit[0] * I_mat + beta_fit[1] * ones_mat
model_r2 = 1 - np.linalg.norm(P - P_model)**2 / np.linalg.norm(P)**2
print(f"  P ≈ {beta_fit[0]:.6f}·I + {beta_fit[1]:.6f}·11^T: R² = {model_r2:.4f}")

# Also test γ+H as simple function of ||x||^2
norms_sq = np.sum(X_all**2, axis=1)
r_simple, _ = pearsonr(norms_sq, gh_all)
print(f"\n  r(γ+H, ||x||²): {r_simple:.4f}")
print(f"  r(γ+H, ||x||):  {pearsonr(np.sqrt(norms_sq), gh_all)[0]:.4f}")

# Linear fit: γ+H = a + b*||x||²
from numpy.polynomial import polynomial as P_fit
coeffs_lin = np.polyfit(norms_sq, gh_all, 1)
y_lin = np.polyval(coeffs_lin, norms_sq)
r2_lin = 1 - np.sum((gh_all - y_lin)**2) / np.sum((gh_all - np.mean(gh_all))**2)
print(f"  γ+H = {coeffs_lin[0]:.4f}·||x||² + {coeffs_lin[1]:.4f}: R² = {r2_lin:.6f}")

print("\nDone. Writing results...")
