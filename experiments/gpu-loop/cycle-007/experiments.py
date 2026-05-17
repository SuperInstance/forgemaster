"""
Cycle 7: Characterize P in x^T P x = γ+H under tanh nonlinear dynamics.
Also: nonlinear Lyapunov condition, analytical P, eigenvalue threshold, other activations.
"""
import numpy as np
from scipy import linalg
import json, os

np.random.seed(42)
N = 20  # system size
T = 500  # timesteps
NUM_SAMPLES = 30  # matrix samples per config

def gamma(x, C):
    """Spectral gap proxy: 1 - |lambda_2|/|lambda_1| of correlation-like matrix."""
    # Use x as a proxy for participation
    norm_x = np.linalg.norm(x)
    if norm_x < 1e-12:
        return 0.0
    return float(np.clip(1.0 - np.abs(np.dot(x, C @ x)) / (norm_x * np.linalg.norm(C @ x) + 1e-12), 0, 1))

def entropy(x):
    """Shannon entropy of |x|^2 normalized to probability."""
    p = np.abs(x)**2
    s = p.sum()
    if s < 1e-12:
        return 0.0
    p = p / s
    p = p[p > 1e-12]
    return float(-np.sum(p * np.log(p)))

def compute_gh_trajectory(C, activation='tanh', T=500):
    """Run x_{t+1} = activation(C @ x_t) and return trajectory of gamma+H."""
    x = np.random.randn(N) * 0.1
    gh_vals = []
    x_trajectory = []
    
    for t in range(T):
        Cx = C @ x
        if activation == 'tanh':
            x = np.tanh(Cx)
        elif activation == 'sigmoid':
            x = 1.0 / (1.0 + np.exp(-Cx)) - 0.5  # centered sigmoid
        elif activation == 'relu':
            x = np.clip(Cx, 0, None)
        elif activation == 'softplus':
            x = np.log1p(np.exp(Cx)) - 0.5  # centered
        elif activation == 'linear':
            # Normalized linear (power iteration with normalization)
            x = Cx
            norm = np.linalg.norm(x)
            if norm > 1e-12:
                x = x / norm
        
        g = gamma(x, C)
        h = entropy(x)
        gh_vals.append(g + h)
        x_trajectory.append(x.copy())
    
    return np.array(gh_vals), np.array(x_trajectory)

def make_random_coupling(N, scale=1.0):
    W = np.random.randn(N, N) * scale / np.sqrt(N)
    np.fill_diagonal(W, 1.0)
    return W

def make_hebbian_coupling(N):
    patterns = np.random.randn(N, 3)
    C = patterns @ patterns.T / 3
    np.fill_diagonal(C, 1.0)
    return C

def make_attention_coupling(N, tau=1.0):
    Q = np.random.randn(N, N//2)
    K = np.random.randn(N, N//2)
    scores = Q @ K.T / np.sqrt(N//2)
    # softmax per row
    scores_exp = np.exp((scores - scores.max(axis=1, keepdims=True)) / tau)
    C = scores_exp / scores_exp.sum(axis=1, keepdims=True)
    np.fill_diagonal(C, 1.0)
    return C

def discover_P(x_trajectory, gh_vals):
    """Regress gh_vals[t] = x_trajectory[t]^T @ P @ x_trajectory[t] for symmetric P.
    Vectorize: gh = sum_{i<=j} p_ij * (2 - delta_ij) * x_i * x_j
    """
    T = len(gh_vals)
    # Build design matrix: for each timestep, the upper-triangular quadratic features
    features = []
    for t in range(T):
        x = x_trajectory[t]
        row = []
        for i in range(N):
            for j in range(i, N):
                if i == j:
                    row.append(x[i]**2)
                else:
                    row.append(2 * x[i] * x[j])
        features.append(row)
    features = np.array(features)  # (T, N*(N+1)/2)
    
    # Solve least squares
    p_vec, residual, rank, sv = np.linalg.lstsq(features, gh_vals, rcond=None)
    
    # Reconstruct symmetric P
    P = np.zeros((N, N))
    idx = 0
    for i in range(N):
        for j in range(i, N):
            P[i, j] = p_vec[idx]
            P[j, i] = p_vec[idx]
            idx += 1
    
    # Compute R²
    predicted = features @ p_vec
    ss_res = np.sum((gh_vals - predicted)**2)
    ss_tot = np.sum((gh_vals - np.mean(gh_vals))**2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    
    return P, r2, predicted

# ============================================================
# EXP 1: Characterize P — what IS it?
# ============================================================
print("=" * 60)
print("EXP 1: Characterize P for different architectures")
print("=" * 60)

results_exp1 = {}
for arch_name, arch_fn in [('random', lambda: make_random_coupling(N)),
                             ('hebbian', lambda: make_hebbian_coupling(N)),
                             ('attention', lambda: make_attention_coupling(N))]:
    
    P_list = []
    r2_list = []
    C_list = []
    
    for s in range(NUM_SAMPLES):
        C = arch_fn()
        gh_vals, x_traj = compute_gh_trajectory(C, 'tanh', T)
        P, r2, _ = discover_P(x_traj, gh_vals)
        P_list.append(P)
        r2_list.append(r2)
        C_list.append(C)
    
    # Average P across samples
    P_avg = np.mean(P_list, axis=0)
    C_avg = np.mean(C_list, axis=0)
    
    # Compare P to various C-derived matrices
    comparisons = {}
    for label, M_ref in [
        ('C', C_avg),
        ('C^T C', C_avg.T @ C_avg),
        ('C C^T', C_avg @ C_avg.T),
        ('(C+C^T)/2', (C_avg + C_avg.T) / 2),
        ('I', np.eye(N)),
    ]:
        # Cosine similarity
        vec_P = P_avg.flatten()
        vec_M = M_ref.flatten()
        cos_sim = np.dot(vec_P, vec_M) / (np.linalg.norm(vec_P) * np.linalg.norm(vec_M) + 1e-12)
        # Relative Frobenius
        rel_frob = np.linalg.norm(P_avg - M_ref) / (np.linalg.norm(P_avg) + 1e-12)
        comparisons[label] = {'cosine_sim': float(cos_sim), 'rel_frobenius': float(rel_frob)}
    
    # Eigenvalue decomposition of P
    eigvals_P, eigvecs_P = np.linalg.eigh(P_avg)
    
    results_exp1[arch_name] = {
        'mean_r2': float(np.mean(r2_list)),
        'std_r2': float(np.std(r2_list)),
        'P_eigenvalues': eigvals_P.tolist(),
        'P_trace': float(np.trace(P_avg)),
        'P_rank': int(np.sum(np.abs(eigvals_P) > 0.01 * np.max(np.abs(eigvals_P)))),
        'P_symmetric': bool(np.allclose(P_avg, P_avg.T, atol=1e-10)),
        'comparisons': comparisons,
    }
    
    print(f"\n{arch_name}:")
    print(f"  R² = {np.mean(r2_list):.6f} ± {np.std(r2_list):.6f}")
    print(f"  Tr(P) = {np.trace(P_avg):.4f}")
    print(f"  P rank = {results_exp1[arch_name]['P_rank']}")
    print(f"  P symmetric: {results_exp1[arch_name]['P_symmetric']}")
    print(f"  P eigenvalue range: [{eigvals_P[0]:.4f}, {eigvals_P[-1]:.4f}]")
    for label, comp in comparisons.items():
        print(f"  vs {label}: cos={comp['cosine_sim']:.4f}, rel_F={comp['rel_frobenius']:.4f}")

# ============================================================
# EXP 2: Nonlinear Lyapunov condition
# Test: tanh(C x)^T P tanh(C x) vs x^T P x
# ============================================================
print("\n" + "=" * 60)
print("EXP 2: Nonlinear Lyapunov condition")
print("=" * 60)

results_exp2 = {}
for arch_name, arch_fn in [('random', lambda: make_random_coupling(N)),
                             ('hebbian', lambda: make_hebbian_coupling(N)),
                             ('attention', lambda: make_attention_coupling(N))]:
    
    residuals = []
    nonlinear_resids = []
    
    for s in range(NUM_SAMPLES):
        C = arch_fn()
        gh_vals, x_traj = compute_gh_trajectory(C, 'tanh', T)
        P, r2, _ = discover_P(x_traj, gh_vals)
        
        # Test: for each t, compute x^T P x and tanh(Cx)^T P tanh(Cx)
        for t in range(T - 1):
            x_t = x_traj[t]
            x_next = x_traj[t + 1]  # = tanh(C @ x_t)
            
            val_t = x_t @ P @ x_t
            val_next = x_next @ P @ x_next
            resid = abs(val_next - val_t) / (abs(val_t) + 1e-12)
            residuals.append(resid)
            
            # Also test the Jacobian-based linearized Lyapunov
            # J = diag(1 - tanh²(Cx)) @ C  (Jacobian of tanh(Cx) at x_t)
            tanh_cx = np.tanh(C @ x_t)
            J = np.diag(1 - tanh_cx**2) @ C
            linearized_residual = np.linalg.norm(J.T @ P @ J - P) / (np.linalg.norm(P) + 1e-12)
            nonlinear_resids.append(linearized_residual)
    
    results_exp2[arch_name] = {
        'mean_nonlinear_resid': float(np.mean(residuals)),
        'max_nonlinear_resid': float(np.max(residuals)),
        'p95_nonlinear_resid': float(np.percentile(residuals, 95)),
        'mean_linearized_resid': float(np.mean(nonlinear_resids)),
    }
    
    print(f"\n{arch_name}:")
    print(f"  Nonlinear: |tanh(Cx)^T P tanh(Cx) - x^T P x| / |x^T P x|")
    print(f"    mean = {np.mean(residuals):.6f}")
    print(f"    p95  = {np.percentile(residuals, 95):.6f}")
    print(f"    max  = {np.max(residuals):.6f}")
    print(f"  Linearized: ||J^T P J - P|| / ||P||")
    print(f"    mean = {np.mean(nonlinear_resids):.6f}")

# ============================================================
# EXP 3: Analytical P derivation
# For small C, tanh(Cx) ≈ Cx, so P should relate to C.
# For large C, tanh(Cx) → sign(Cx), P encodes sign structure.
# Test: P ∝ I + f(C) for various f.
# ============================================================
print("\n" + "=" * 60)
print("EXP 3: Analytical P derivation")
print("=" * 60)

# For a single C, discover P and try to express it as function of C
results_exp3 = {}
C = make_random_coupling(N)
gh_vals, x_traj = compute_gh_trajectory(C, 'tanh', T)
P_discovered, r2, _ = discover_P(x_traj, gh_vals)

# Test candidate analytical forms
candidates = {}
# C1: P = I
P_I = np.eye(N)
r2_I = 1 - np.sum((gh_vals - np.array([x @ P_I @ x for x in x_traj]))**2) / np.sum((gh_vals - gh_vals.mean())**2)
candidates['I'] = r2_I

# C2: P = (C + C^T)/2 (symmetric part of C)
P_symC = (C + C.T) / 2
r2_symC = 1 - np.sum((gh_vals - np.array([x @ P_symC @ x for x in x_traj]))**2) / np.sum((gh_vals - gh_vals.mean())**2)
candidates['(C+C^T)/2'] = r2_symC

# C3: P = (I - C^T C)^{-1} (if Lyapunov-ish)
try:
    P_lyap = np.linalg.inv(np.eye(N) - C.T @ C + 1e-6 * np.eye(N))
    P_lyap = (P_lyap + P_lyap.T) / 2
    r2_lyap = 1 - np.sum((gh_vals - np.array([x @ P_lyap @ x for x in x_traj]))**2) / np.sum((gh_vals - gh_vals.mean())**2)
    candidates['(I - C^TC)^{-1}'] = r2_lyap
except:
    candidates['(I - C^TC)^{-1}'] = -1

# C4: Solve the nonlinear Lyapunov equation numerically
# We want: E[tanh(Cx)^T P tanh(Cx)] = E[x^T P x] for x on the attractor
# This is automatically satisfied by the discovered P. Check if there's a CLOSED FORM.

# C5: P related to the Fisher information of tanh(Cx)
# For tanh, 1-tanh² is the derivative. The Fisher info matrix is E[diag(1-tanh²(Cx))] @ C^T @ C @ E[diag(1-tanh²(Cx))]
# Approximate:
diag_derivs = []
for x in x_traj[-100:]:
    tanh_cx = np.tanh(C @ x)
    diag_derivs.append(1 - tanh_cx**2)
mean_d = np.mean(diag_derivs, axis=0)
P_fisher = np.diag(mean_d) @ C.T @ C @ np.diag(mean_d)
P_fisher = (P_fisher + P_fisher.T) / 2
r2_fisher = 1 - np.sum((gh_vals - np.array([x @ P_fisher @ x for x in x_traj]))**2) / np.sum((gh_vals - gh_vals.mean())**2)
candidates['Fisher'] = r2_fisher

# C6: P related to C^T diag(d) + diag(d) C (Hessian of tanh potential)
P_hessian = C.T @ np.diag(mean_d) + np.diag(mean_d) @ C
P_hessian = (P_hessian + P_hessian.T) / 2
r2_hessian = 1 - np.sum((gh_vals - np.array([x @ P_hessian @ x for x in x_traj]))**2) / np.sum((gh_vals - gh_refs)**2) if (gh_refs := (gh_vals - gh_vals.mean())) is not None and np.sum(gh_refs**2) > 0 else 0
candidates['Hessian'] = r2_hessian

# Better way for C6
resid_hess = np.array([x @ P_hessian @ x for x in x_traj])
ss_res = np.sum((gh_vals - resid_hess)**2)
ss_tot = np.sum((gh_vals - gh_vals.mean())**2)
candidates['Hessian'] = float(1 - ss_res / ss_tot)

# C7: P = solve Lyapunov for the Jacobian at fixed point
# Find fixed point
x_fp = np.random.randn(N) * 0.1
for _ in range(1000):
    x_fp = np.tanh(C @ x_fp)
J_fp = np.diag(1 - np.tanh(C @ x_fp)**2) @ C
# Solve J^T P J = P (discrete Lyapunov) — but this has non-trivial solution only if J is orthogonal-ish
# Instead solve the continuous Lyapunov: A^T P + P A = Q for some Q
# Or solve J^T P J - P = 0 as a linear system
n = N * N
A_lyap = np.zeros((n, n))
for i in range(N):
    for j in range(N):
        for k in range(N):
            for l in range(N):
                A_lyap[i*N+j, k*N+l] += J_fp[k,i] * J_fp[l,j]
        A_lyap[i*N+j, i*N+j] -= 1
# Find null space
U, s_lyap, Vt = np.linalg.svd(A_lyap)
null_mask = s_lyap < 0.1 * s_lyap[0]
if np.sum(s_lyap < 0.1 * s_lyap[0]) > 0:
    # Use smallest singular vector
    P_lyap_j = Vt[-1].reshape(N, N)
    P_lyap_j = (P_lyap_j + P_lyap_j.T) / 2
    r2_lyap_j = 1 - np.sum((gh_vals - np.array([x @ P_lyap_j @ x for x in x_traj]))**2) / np.sum((gh_vals - gh_vals.mean())**2)
    candidates['Lyapunov_J'] = r2_lyap_j
else:
    candidates['Lyapunov_J'] = -1

# C8: Direct regression of P against various C functions
# P = alpha*I + beta*(C+C^T)/2 + gamma*(C^TC + CC^T)/2 + delta*(C+C^T)^2/4
# Use the discovered P as ground truth
basis_matrices = {
    'I': np.eye(N),
    'sym(C)': (C + C.T) / 2,
    'C^TC': (C.T @ C + C @ C.T) / 2,
    'sym(C)^2': ((C + C.T) / 2) @ ((C + C.T) / 2),
}
# Flatten and regress
A_basis = np.column_stack([M.flatten() for M in basis_matrices.values()])
p_coeffs, _, _, _ = np.linalg.lstsq(A_basis, P_discovered.flatten(), rcond=None)
P_reconstructed = sum(c * M for c, M in zip(p_coeffs, basis_matrices.values()))
r2_recon = 1 - np.sum((P_discovered.flatten() - P_reconstructed.flatten())**2) / np.sum((P_discovered.flatten() - P_discovered.flatten().mean())**2)

print(f"\nCandidate analytical forms (R² of prediction):")
for name, r2_val in candidates.items():
    print(f"  {name}: R² = {r2_val:.6f}")

print(f"\nBasis regression of P against C-derived matrices: R² = {r2_recon:.6f}")
print(f"  Coefficients: I={p_coeffs[0]:.4f}, sym(C)={p_coeffs[1]:.4f}, C^TC={p_coeffs[2]:.4f}, sym(C)^2={p_coeffs[3]:.4f}")

results_exp3 = {
    'candidates': {k: float(v) if v != -1 else None for k, v in candidates.items()},
    'basis_regression_r2': float(r2_recon),
    'basis_coefficients': p_coeffs.tolist(),
}

# ============================================================
# EXP 4: Eigenvalue ≥ 1 threshold
# ============================================================
print("\n" + "=" * 60)
print("EXP 4: Eigenvalue threshold — scale C to test λ ≥ 1")
print("=" * 60)

scales = [0.1, 0.3, 0.5, 0.7, 0.9, 1.0, 1.2, 1.5, 2.0, 3.0, 5.0]
results_exp4 = []

for scale in scales:
    cvs = []
    r2_ps = []
    
    for s in range(10):
        C = make_random_coupling(N, scale=scale)
        eigvals = np.linalg.eigvals(C)
        max_real_eig = float(np.max(np.real(eigvals)))
        
        gh_vals, x_traj = compute_gh_trajectory(C, 'tanh', T)
        cv = float(np.std(gh_vals) / (np.mean(gh_vals) + 1e-12)) if np.mean(gh_vals) > 1e-12 else float('inf')
        
        P, r2, _ = discover_P(x_traj, gh_vals)
        cvs.append(cv)
        r2_ps.append(r2)
    
    results_exp4.append({
        'scale': scale,
        'mean_cv': float(np.mean(cvs)),
        'std_cv': float(np.std(cvs)),
        'mean_r2_P': float(np.mean(r2_ps)),
    })
    print(f"  scale={scale:.1f}: CV={np.mean(cvs):.4f}±{np.std(cvs):.4f}, R²(P)={np.mean(r2_ps):.6f}")

# ============================================================
# EXP 5: Other nonlinearities
# ============================================================
print("\n" + "=" * 60)
print("EXP 5: Other nonlinearities")
print("=" * 60)

activations = ['tanh', 'sigmoid', 'relu', 'softplus', 'linear']
results_exp5 = {}

for act in activations:
    cvs = []
    r2_ps = []
    
    for s in range(NUM_SAMPLES):
        C = make_random_coupling(N)
        gh_vals, x_traj = compute_gh_trajectory(C, act, T)
        
        if np.any(np.isnan(gh_vals)) or np.any(np.isinf(gh_vals)):
            cvs.append(float('inf'))
            r2_ps.append(0.0)
            continue
        
        cv = float(np.std(gh_vals) / (np.mean(gh_vals) + 1e-12)) if np.mean(gh_vals) > 1e-12 else float('inf')
        P, r2, _ = discover_P(x_traj, gh_vals)
        cvs.append(cv)
        r2_ps.append(r2)
    
    results_exp5[act] = {
        'mean_cv': float(np.mean(cvs)),
        'std_cv': float(np.std(cvs)),
        'mean_r2_P': float(np.mean(r2_ps)),
    }
    print(f"  {act}: CV={np.mean(cvs):.4f}±{np.std(cvs):.4f}, R²(P)={np.mean(r2_ps):.6f}")

# ============================================================
# EXP 6: Deeper P characterization — per-sample P vs C
# ============================================================
print("\n" + "=" * 60)
print("EXP 6: Per-sample P structure analysis")
print("=" * 60)

P_C_correlations = []
P_symC_correlations = []

for s in range(50):
    C = make_random_coupling(N)
    gh_vals, x_traj = compute_gh_trajectory(C, 'tanh', T)
    P, r2, _ = discover_P(x_traj, gh_vals)
    
    # Correlate P entries with C entries
    p_flat = P.flatten()
    c_flat = C.flatten()
    sym_c_flat = ((C + C.T) / 2).flatten()
    
    corr = np.corrcoef(p_flat, c_flat)[0, 1]
    corr_sym = np.corrcoef(p_flat, sym_c_flat)[0, 1]
    P_C_correlations.append(corr)
    P_symC_correlations.append(corr_sym)

print(f"  P-C entry correlation: {np.mean(P_C_correlations):.4f} ± {np.std(P_C_correlations):.4f}")
print(f"  P-sym(C) entry correlation: {np.mean(P_symC_correlations):.4f} ± {np.std(P_symC_correlations):.4f}")

# Check if P is diagonal-dominant
diag_fractions = []
for s in range(50):
    C = make_random_coupling(N)
    gh_vals, x_traj = compute_gh_trajectory(C, 'tanh', T)
    P, r2, _ = discover_P(x_traj, gh_vals)
    
    diag_energy = np.sum(np.diag(P)**2)
    total_energy = np.sum(P**2)
    diag_fractions.append(diag_energy / total_energy)

print(f"  Diagonal fraction of P: {np.mean(diag_fractions):.4f} ± {np.std(diag_fractions):.4f}")

# ============================================================
# EXP 7: Test if P is the Hessian of the "tanh energy landscape"
# For tanh dynamics, there's a Lyapunov function V(x) = -sum(ln(cosh(C_i x))
# Its Hessian is C^T @ diag(sech²(Cx)) @ C
# ============================================================
print("\n" + "=" * 60)
print("EXP 7: P vs Hessian of tanh energy landscape")
print("=" * 60)

results_exp7 = {}
for arch_name, arch_fn in [('random', lambda: make_random_coupling(N))]:
    r2_hessian_attractor = []
    
    for s in range(20):
        C = arch_fn()
        gh_vals, x_traj = compute_gh_trajectory(C, 'tanh', T)
        P, r2, _ = discover_P(x_traj, gh_vals)
        
        # Compute Hessian of V(x) = -sum(ln(cosh(C_i x))) at attractor points
        # Hessian = C^T @ diag(sech²(Cx)) @ C
        hessians = []
        for x in x_traj[-50:]:  # use attractor points
            Cx = C @ x
            sech2 = 1.0 / np.cosh(Cx)**2
            H = C.T @ np.diag(sech2) @ C
            hessians.append(H)
        
        H_avg = np.mean(hessians, axis=0)
        H_avg = (H_avg + H_avg.T) / 2
        
        # How well does H_avg predict P?
        # Need to account for scale — P might be alpha * H_avg
        if np.linalg.norm(H_avg) > 1e-10:
            alpha = np.trace(P) / np.trace(H_avg)
            P_from_H = alpha * H_avg
            ss_res = np.sum((P.flatten() - P_from_H.flatten())**2)
            ss_tot = np.sum((P.flatten() - P.flatten().mean())**2)
            r2_h = 1 - ss_res / ss_tot if ss_tot > 0 else 0
            r2_hessian_attractor.append(r2_h)
    
    results_exp7[arch_name] = {
        'mean_r2': float(np.mean(r2_hessian_attractor)),
        'std_r2': float(np.std(r2_hessian_attractor)),
    }
    print(f"  {arch_name}: R²(Hessian → P) = {np.mean(r2_hessian_attractor):.4f} ± {np.std(r2_hessian_attractor):.4f}")

# Also test: P = alpha * (I - C^T C) type (continuous Lyapunov solution)
# For the linearized system at fixed point: J = D @ C where D = diag(1-tanh²(Cx_fp))
# The discrete Lyapunov J^T P J = P has solutions in the null space of (J⊗J - I)
# But we know this doesn't work (residual ~0.95). 
# What about the CONTINUOUS Lyapunov: J^T P + P J = 0?
for s in range(5):
    C = make_random_coupling(N)
    gh_vals, x_traj = compute_gh_trajectory(C, 'tanh', T)
    P, r2, _ = discover_P(x_traj, gh_vals)
    
    # Fixed point
    x_fp = x_traj[-1].copy()
    J = np.diag(1 - np.tanh(C @ x_fp)**2) @ C
    
    # Continuous Lyapunov residual
    cont_resid = np.linalg.norm(J.T @ P + P @ J) / np.linalg.norm(P)
    print(f"  Continuous Lyapunov residual ||J^T P + P J|| / ||P|| = {cont_resid:.4f}")

# ============================================================
# Save results
# ============================================================
all_results = {
    'exp1_characterize_P': results_exp1,
    'exp2_nonlinear_lyapunov': results_exp2,
    'exp3_analytical_P': results_exp3,
    'exp4_eigenvalue_threshold': results_exp4,
    'exp5_other_nonlinearities': results_exp5,
    'exp6_P_C_correlation': {
        'P_C_corr': float(np.mean(P_C_correlations)),
        'P_symC_corr': float(np.mean(P_symC_correlations)),
        'diag_fraction': float(np.mean(diag_fractions)),
    },
    'exp7_hessian': results_exp7,
}

with open('/home/phoenix/.openclaw/workspace/experiments/gpu-loop/cycle-007/results.json', 'w') as f:
    json.dump(all_results, f, indent=2, default=str)

print("\n\nResults saved to cycle-007/results.json")
