"""
Cycle 7: Characterize P in x^T P x = γ+H under tanh nonlinear dynamics.
Fixed: removed N^4 Lyapunov SVD, simplified where needed.
"""
import numpy as np
from scipy import linalg
import json

np.random.seed(42)
N = 20
T = 500
NUM_SAMPLES = 30

def gamma(x, C):
    """Spectral gap proxy."""
    norm_x = np.linalg.norm(x)
    if norm_x < 1e-12:
        return 0.0
    return float(np.clip(1.0 - np.abs(np.dot(x, C @ x)) / (norm_x * np.linalg.norm(C @ x) + 1e-12), 0, 1))

def entropy(x):
    """Shannon entropy of |x|^2 normalized."""
    p = np.abs(x)**2
    s = p.sum()
    if s < 1e-12:
        return 0.0
    p = p / s
    p = p[p > 1e-12]
    return float(-np.sum(p * np.log(p)))

def compute_gh_trajectory(C, activation='tanh', T=500):
    x = np.random.randn(N) * 0.1
    gh_vals = []
    x_trajectory = []
    for t in range(T):
        Cx = C @ x
        if activation == 'tanh':
            x = np.tanh(Cx)
        elif activation == 'sigmoid':
            x = 1.0 / (1.0 + np.exp(-Cx)) - 0.5
        elif activation == 'relu':
            x = np.clip(Cx, 0, None)
        elif activation == 'softplus':
            x = np.log1p(np.exp(np.clip(Cx, -20, 20))) - 0.5
        elif activation == 'linear':
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
    scores_exp = np.exp((scores - scores.max(axis=1, keepdims=True)) / tau)
    C = scores_exp / scores_exp.sum(axis=1, keepdims=True)
    np.fill_diagonal(C, 1.0)
    return C

def discover_P(x_trajectory, gh_vals):
    """Regress gh = x^T P x for symmetric P via least squares on upper-tri features."""
    T_pts = len(gh_vals)
    dim = N * (N + 1) // 2
    features = np.zeros((T_pts, dim))
    
    for t in range(T_pts):
        x = x_trajectory[t]
        idx = 0
        for i in range(N):
            features[t, idx] = x[i]**2
            idx += 1
            for j in range(i + 1, N):
                features[t, idx] = 2 * x[i] * x[j]
                idx += 1
    
    p_vec, _, _, _ = np.linalg.lstsq(features, gh_vals, rcond=None)
    
    P = np.zeros((N, N))
    idx = 0
    for i in range(N):
        P[i, i] = p_vec[idx]
        idx += 1
        for j in range(i + 1, N):
            P[i, j] = p_vec[idx]
            P[j, i] = p_vec[idx]
            idx += 1
    
    predicted = features @ p_vec
    ss_res = np.sum((gh_vals - predicted)**2)
    ss_tot = np.sum((gh_vals - np.mean(gh_vals))**2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return P, r2

# ============================================================
# EXP 1: Characterize P for different architectures
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
        P, r2 = discover_P(x_traj, gh_vals)
        P_list.append(P)
        r2_list.append(r2)
        C_list.append(C)
    
    P_avg = np.mean(P_list, axis=0)
    C_avg = np.mean(C_list, axis=0)
    
    comparisons = {}
    for label, M_ref in [
        ('C', C_avg),
        ('C^T_C', C_avg.T @ C_avg),
        ('CC^T', C_avg @ C_avg.T),
        ('sym(C)', (C_avg + C_avg.T) / 2),
        ('I', np.eye(N)),
    ]:
        vP = P_avg.flatten()
        vM = M_ref.flatten()
        cos_sim = np.dot(vP, vM) / (np.linalg.norm(vP) * np.linalg.norm(vM) + 1e-12)
        rel_frob = np.linalg.norm(P_avg - M_ref) / (np.linalg.norm(P_avg) + 1e-12)
        comparisons[label] = {'cosine_sim': float(cos_sim), 'rel_frobenius': float(rel_frob)}
    
    eigvals_P = np.linalg.eigvalsh(P_avg)
    
    results_exp1[arch_name] = {
        'mean_r2': float(np.mean(r2_list)),
        'std_r2': float(np.std(r2_list)),
        'P_eigenvalues_min': float(eigvals_P[0]),
        'P_eigenvalues_max': float(eigvals_P[-1]),
        'P_trace': float(np.trace(P_avg)),
        'P_rank': int(np.sum(np.abs(eigvals_P) > 0.01 * np.max(np.abs(eigvals_P)))),
        'P_positive_definite': bool(eigvals_P[0] > -0.01),
        'comparisons': comparisons,
    }
    
    print(f"\n{arch_name}:")
    print(f"  R² = {np.mean(r2_list):.6f} ± {np.std(r2_list):.6f}")
    print(f"  Tr(P) = {np.trace(P_avg):.4f}, rank(P) = {results_exp1[arch_name]['P_rank']}")
    print(f"  P eval range: [{eigvals_P[0]:.4f}, {eigvals_P[-1]:.4f}], PD: {eigvals_P[0] > -0.01}")
    for label, comp in comparisons.items():
        print(f"  vs {label}: cos={comp['cosine_sim']:.4f}, rel_F={comp['rel_frobenius']:.4f}")

# ============================================================
# EXP 2: Nonlinear Lyapunov condition
# ============================================================
print("\n" + "=" * 60)
print("EXP 2: Nonlinear Lyapunov condition")
print("=" * 60)

results_exp2 = {}
for arch_name, arch_fn in [('random', lambda: make_random_coupling(N)),
                             ('hebbian', lambda: make_hebbian_coupling(N)),
                             ('attention', lambda: make_attention_coupling(N))]:
    residuals_nl = []
    residuals_lin = []
    
    for s in range(10):
        C = arch_fn()
        gh_vals, x_traj = compute_gh_trajectory(C, 'tanh', T)
        P, r2 = discover_P(x_traj, gh_vals)
        
        for t in range(T - 1):
            x_t = x_traj[t]
            x_next = x_traj[t + 1]
            val_t = x_t @ P @ x_t
            val_next = x_next @ P @ x_next
            residuals_nl.append(abs(val_next - val_t) / (abs(val_t) + 1e-12))
        
        # Linearized: Jacobian at fixed point
        x_fp = x_traj[-1]
        J = np.diag(1 - np.tanh(C @ x_fp)**2) @ C
        residuals_lin.append(np.linalg.norm(J.T @ P @ J - P) / (np.linalg.norm(P) + 1e-12))
    
    results_exp2[arch_name] = {
        'nonlinear_mean': float(np.mean(residuals_nl)),
        'nonlinear_p95': float(np.percentile(residuals_nl, 95)),
        'linearized_mean': float(np.mean(residuals_lin)),
    }
    print(f"\n{arch_name}:")
    print(f"  Nonlinear resid: mean={np.mean(residuals_nl):.6f}, p95={np.percentile(residuals_nl, 95):.6f}")
    print(f"  Linearized resid: {np.mean(residuals_lin):.4f}")

# ============================================================
# EXP 3: Analytical P candidates
# ============================================================
print("\n" + "=" * 60)
print("EXP 3: Analytical P candidates")
print("=" * 60)

C = make_random_coupling(N)
gh_vals, x_traj = compute_gh_trajectory(C, 'tanh', T)
P_discovered, r2_d = discover_P(x_traj, gh_vals)

def r2_for_P(P_test, x_traj, gh_vals):
    preds = np.array([x @ P_test @ x for x in x_traj])
    ss_res = np.sum((gh_vals - preds)**2)
    ss_tot = np.sum((gh_vals - gh_vals.mean())**2)
    return 1 - ss_res / ss_tot if ss_tot > 0 else 0

# Candidate 1: Identity
r2_I = r2_for_P(np.eye(N), x_traj, gh_vals)
# Candidate 2: sym(C)
r2_symC = r2_for_P((C + C.T) / 2, x_traj, gh_vals)
# Candidate 3: Fisher information
diag_d = []
for x in x_traj[-100:]:
    diag_d.append(1 - np.tanh(C @ x)**2)
mean_d = np.mean(diag_d, axis=0)
P_fisher = C.T @ np.diag(mean_d) @ C
P_fisher = (P_fisher + P_fisher.T) / 2
r2_fisher = r2_for_P(P_fisher, x_traj, gh_vals)

# Candidate 4: C^T C (symmetrized)
P_CtC = (C.T @ C + C @ C.T) / 2
r2_CtC = r2_for_P(P_CtC, x_traj, gh_vals)

# Candidate 5: Hessian of V = -sum ln cosh(c_i^T x)
# H = C^T diag(sech^2(Cx)) C averaged over attractor
P_hess_attractor = []
for x in x_traj[-100:]:
    sech2 = 1.0 / np.cosh(np.clip(C @ x, -10, 10))**2
    H = C.T @ np.diag(sech2) @ C
    P_hess_attractor.append(H)
P_hess_avg = np.mean(P_hess_attractor, axis=0)
P_hess_avg = (P_hess_avg + P_hess_avg.T) / 2
# Scale to match P
alpha_h = np.trace(P_discovered) / (np.trace(P_hess_avg) + 1e-12)
P_hess_scaled = alpha_h * P_hess_avg
r2_hess = r2_for_P(P_hess_scaled, x_traj, gh_vals)
r2_hess_raw = r2_for_P(P_hess_avg, x_traj, gh_vals)

# Candidate 6: Basis regression: P = aI + b*sym(C) + c*C^TC + d*(sym(C))^2
basis = {
    'I': np.eye(N),
    'sym(C)': (C + C.T) / 2,
    'C^TC_sym': P_CtC,
    'sym(C)^2': ((C + C.T) / 2) @ ((C + C.T) / 2),
}
A_basis = np.column_stack([M.flatten() for M in basis.values()])
p_coeffs, _, _, _ = np.linalg.lstsq(A_basis, P_discovered.flatten(), rcond=None)
P_recon = sum(c * M for c, M in zip(p_coeffs, basis.values()))
ss_res = np.sum((P_discovered.flatten() - P_recon.flatten())**2)
ss_tot = np.sum((P_discovered.flatten() - P_discovered.flatten().mean())**2)
r2_recon = 1 - ss_res / ss_tot

# Candidate 7: Does P relate to D+C^T*D where D = diag(mean_d)?
P_DC = np.diag(mean_d) + C.T @ np.diag(mean_d)
P_DC = (P_DC + P_DC.T) / 2
r2_DC = r2_for_P(P_DC, x_traj, gh_vals)

print(f"  Discovered P R²: {r2_d:.6f}")
print(f"  Candidates:")
print(f"    I:              R²={r2_I:.6f}")
print(f"    sym(C):         R²={r2_symC:.6f}")
print(f"    C^TC (sym):     R²={r2_CtC:.6f}")
print(f"    Fisher:         R²={r2_fisher:.6f}")
print(f"    Hessian(raw):   R²={r2_hess_raw:.6f}")
print(f"    Hessian(scaled):R²={r2_hess:.6f}")
print(f"    D+C^T*D:        R²={r2_DC:.6f}")
print(f"    Basis recon:    R²={r2_recon:.6f} (I={p_coeffs[0]:.4f}, sym(C)={p_coeffs[1]:.4f}, C^TC={p_coeffs[2]:.4f}, sym(C)^2={p_coeffs[3]:.4f})")

results_exp3 = {
    'discovered_r2': float(r2_d),
    'candidates': {
        'I': float(r2_I),
        'sym(C)': float(r2_symC),
        'C^TC_sym': float(r2_CtC),
        'Fisher': float(r2_fisher),
        'Hessian_raw': float(r2_hess_raw),
        'Hessian_scaled': float(r2_hess),
        'D+CTD': float(r2_DC),
    },
    'basis_reconstruction_r2': float(r2_recon),
    'basis_coefficients': {k: float(v) for k, v in zip(basis.keys(), p_coeffs)},
}

# ============================================================
# EXP 4: Eigenvalue threshold — scale C
# ============================================================
print("\n" + "=" * 60)
print("EXP 4: Eigenvalue threshold — scale C")
print("=" * 60)

scales = [0.1, 0.3, 0.5, 0.7, 0.9, 1.0, 1.2, 1.5, 2.0, 3.0, 5.0]
results_exp4 = []
for scale in scales:
    cvs = []
    r2s = []
    for s in range(10):
        C = make_random_coupling(N, scale=scale)
        gh_vals, x_traj = compute_gh_trajectory(C, 'tanh', T)
        if np.any(np.isnan(gh_vals)):
            cvs.append(float('inf'))
            r2s.append(0)
            continue
        cv = float(np.std(gh_vals) / (np.mean(gh_vals) + 1e-12)) if np.mean(gh_vals) > 1e-12 else float('inf')
        P, r2 = discover_P(x_traj, gh_vals)
        cvs.append(cv)
        r2s.append(r2)
    entry = {
        'scale': scale,
        'mean_cv': float(np.mean(cvs)),
        'mean_r2_P': float(np.mean(r2s)),
    }
    results_exp4.append(entry)
    print(f"  scale={scale:.1f}: CV={np.mean(cvs):.4f}, R²(P)={np.mean(r2s):.6f}")

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
    r2s = []
    for s in range(NUM_SAMPLES):
        C = make_random_coupling(N)
        gh_vals, x_traj = compute_gh_trajectory(C, act, T)
        if np.any(np.isnan(gh_vals)) or np.any(np.isinf(gh_vals)):
            cvs.append(float('inf'))
            r2s.append(0)
            continue
        cv = float(np.std(gh_vals) / (np.mean(gh_vals) + 1e-12)) if np.mean(gh_vals) > 1e-12 else float('inf')
        P, r2 = discover_P(x_traj, gh_vals)
        cvs.append(cv)
        r2s.append(r2)
    results_exp5[act] = {
        'mean_cv': float(np.mean(cvs)),
        'std_cv': float(np.std(cvs)),
        'mean_r2_P': float(np.mean(r2s)),
    }
    print(f"  {act}: CV={np.mean(cvs):.4f}±{np.std(cvs):.4f}, R²(P)={np.mean(r2s):.6f}")

# ============================================================
# EXP 6: P-C correlation + diagonal dominance
# ============================================================
print("\n" + "=" * 60)
print("EXP 6: P structure analysis")
print("=" * 60)

corr_list = []
corr_sym_list = []
diag_frac_list = []
for s in range(50):
    C = make_random_coupling(N)
    gh_vals, x_traj = compute_gh_trajectory(C, 'tanh', T)
    P, r2 = discover_P(x_traj, gh_vals)
    p_flat = P.flatten()
    corr_list.append(np.corrcoef(p_flat, C.flatten())[0, 1])
    corr_sym_list.append(np.corrcoef(p_flat, ((C + C.T) / 2).flatten())[0, 1])
    diag_frac_list.append(np.sum(np.diag(P)**2) / np.sum(P**2))

print(f"  P-C correlation: {np.mean(corr_list):.4f} ± {np.std(corr_list):.4f}")
print(f"  P-sym(C) correlation: {np.mean(corr_sym_list):.4f} ± {np.std(corr_sym_list):.4f}")
print(f"  Diagonal fraction: {np.mean(diag_frac_list):.4f} ± {np.std(diag_frac_list):.4f}")

results_exp6 = {
    'P_C_corr': float(np.mean(corr_list)),
    'P_symC_corr': float(np.mean(corr_sym_list)),
    'diag_fraction': float(np.mean(diag_frac_list)),
}

# ============================================================
# EXP 7: Hessian → P across many samples
# ============================================================
print("\n" + "=" * 60)
print("EXP 7: Hessian of tanh energy landscape → P")
print("=" * 60)

r2_hess_list = []
for s in range(30):
    C = make_random_coupling(N)
    gh_vals, x_traj = compute_gh_trajectory(C, 'tanh', T)
    P, r2 = discover_P(x_traj, gh_vals)
    
    hessians = []
    for x in x_traj[-50:]:
        sech2 = 1.0 / np.cosh(np.clip(C @ x, -10, 10))**2
        H = C.T @ np.diag(sech2) @ C
        hessians.append(H)
    H_avg = np.mean(hessians, axis=0)
    H_avg = (H_avg + H_avg.T) / 2
    
    alpha = np.trace(P) / (np.trace(H_avg) + 1e-12)
    P_from_H = alpha * H_avg
    ss_res = np.sum((P.flatten() - P_from_H.flatten())**2)
    ss_tot = np.sum((P.flatten() - P.flatten().mean())**2)
    r2_h = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    r2_hess_list.append(r2_h)

print(f"  R²(Hessian_scaled → P): {np.mean(r2_hess_list):.4f} ± {np.std(r2_hess_list):.4f}")

# Also test continuous Lyapunov at fixed point
cont_lyap_resids = []
for s in range(20):
    C = make_random_coupling(N)
    gh_vals, x_traj = compute_gh_trajectory(C, 'tanh', T)
    P, r2 = discover_P(x_traj, gh_vals)
    x_fp = x_traj[-1]
    J = np.diag(1 - np.tanh(C @ x_fp)**2) @ C
    cont_lyap_resids.append(float(np.linalg.norm(J.T @ P + P @ J) / (np.linalg.norm(P) + 1e-12)))

print(f"  Continuous Lyapunov residual: {np.mean(cont_lyap_resids):.4f} ± {np.std(cont_lyap_resids):.4f}")

results_exp7 = {
    'hessian_to_P_r2': float(np.mean(r2_hess_list)),
    'continuous_lyapunov_resid': float(np.mean(cont_lyap_resids)),
}

# ============================================================
# EXP 8: Direct test — is P exactly the one-step Jacobian product?
# If tanh(Cx)^T P tanh(Cx) ≈ x^T P x, then 
# (D C x)^T P (D C x) ≈ x^T P x where D = diag(1-tanh^2(Cx))
# i.e. x^T C^T D P D C x ≈ x^T P x
# So P ≈ C^T D P D C in expectation over x on attractor
# This is a STOCHASTIC Lyapunov equation
# ============================================================
print("\n" + "=" * 60)
print("EXP 8: Stochastic Lyapunov equation")
print("=" * 60)

stoch_lyap_resids = []
for s in range(20):
    C = make_random_coupling(N)
    gh_vals, x_traj = compute_gh_trajectory(C, 'tanh', T)
    P, r2 = discover_P(x_traj, gh_vals)
    
    # Average C^T D P D C over attractor points
    rhs_avg = np.zeros((N, N))
    for x in x_traj[-100:]:
        tanh_cx = np.tanh(C @ x)
        D = np.diag(1 - tanh_cx**2)
        rhs_avg += C.T @ D @ P @ D @ C
    rhs_avg /= 100
    
    resid = np.linalg.norm(rhs_avg - P) / (np.linalg.norm(P) + 1e-12)
    stoch_lyap_resids.append(resid)

print(f"  ||E[C^T D P D C] - P|| / ||P|| = {np.mean(stoch_lyap_resids):.4f} ± {np.std(stoch_lyap_resids):.4f}")

results_exp8 = {'stochastic_lyapunov_resid': float(np.mean(stoch_lyap_resids))}

# ============================================================
# Save
# ============================================================
all_results = {
    'exp1': results_exp1,
    'exp2': results_exp2,
    'exp3': results_exp3,
    'exp4': results_exp4,
    'exp5': results_exp5,
    'exp6': results_exp6,
    'exp7': results_exp7,
    'exp8': results_exp8,
}

with open('/home/phoenix/.openclaw/workspace/experiments/gpu-loop/cycle-007/results.json', 'w') as f:
    json.dump(all_results, f, indent=2, default=str)

print("\nDone. Results saved.")
