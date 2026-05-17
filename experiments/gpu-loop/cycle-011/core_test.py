#!/usr/bin/env python3
"""
Cycle 011: Core test — is γ+H(x) genuinely quadratic in x?
And if so, does P match any known metric?
"""

import numpy as np
from scipy.optimize import minimize as scipy_min
from scipy.special import softmax
from scipy.linalg import solve_discrete_lyapunov

np.set_printoptions(precision=4, suppress=True, linewidth=120)
np.random.seed(42)

N = 5

def generate_C(kind, N, seed=42):
    rng = np.random.RandomState(seed)
    if kind == 'random':
        return rng.randn(N, N) * 0.5
    elif kind == 'attention':
        Q, K = rng.randn(N, N), rng.randn(N, N)
        return softmax((Q @ K.T) / np.sqrt(N), axis=1)
    elif kind == 'hebbian':
        patterns = rng.choice([-1, 1], size=(3, N))
        C = patterns.T @ patterns / N
        np.fill_diagonal(C, 0)
        return C
    elif kind == 'symmetric':
        A = rng.randn(N, N) * 0.5
        return (A + A.T) / 2

def compute_gh(C, x):
    """γ+H at state x."""
    J = np.diag(1 - x**2) @ C
    eigs = np.sort(np.real(np.linalg.eigvals(J)))[::-1]
    gamma = eigs[0] - eigs[1]
    abs_eigs = np.abs(eigs)
    total = np.sum(abs_eigs)
    if total > 1e-15:
        p = abs_eigs / total
        p = p[p > 1e-15]
        H = -np.sum(p * np.log(p))
    else:
        H = 0.0
    return gamma + H

def cos_sim(A, B):
    a, b = A.flatten(), B.flatten()
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-30)

def frob_ratio(A, B):
    return np.linalg.norm(A - B, 'fro') / (np.linalg.norm(A, 'fro') + 1e-30)

# ── TEST 1: Is γ+H(x) genuinely quadratic? ──
print("=" * 70)
print("TEST 1: Is γ+H(x) a quadratic function of x?")
print("=" * 70)

for c_type in ['random', 'attention', 'hebbian', 'symmetric']:
    C = generate_C(c_type, N)
    
    # Sample diverse x values in [-1,1]^N (bounded by tanh)
    rng = np.random.RandomState(42)
    n_pts = 500
    xs = rng.uniform(-1, 1, size=(n_pts, N))
    ghs = np.array([compute_gh(C, x) for x in xs])
    
    # Fit 1: x^T P x (full quadratic, 25 params)
    Phi = np.array([np.outer(x, x).flatten() for x in xs])
    # Use lstsq directly
    p_vec, residuals, rank, sv = np.linalg.lstsq(Phi, ghs, rcond=None)
    P = p_vec.reshape(N, N)
    P = (P + P.T) / 2
    pred = Phi @ p_vec
    ss_res = np.sum((ghs - pred)**2)
    ss_tot = np.sum((ghs - np.mean(ghs))**2)
    r2_quad = 1 - ss_res / ss_tot
    
    # Fit 2: a||x||^2 + b (simplest quadratic)
    norms_sq = np.sum(xs**2, axis=1)
    A_fit = np.column_stack([norms_sq, np.ones(n_pts)])
    coeffs = np.linalg.lstsq(A_fit, ghs, rcond=None)[0]
    pred_simple = A_fit @ coeffs
    r2_simple = 1 - np.sum((ghs - pred_simple)**2) / ss_tot
    
    # Fit 3: Linear in x (5 params) — as baseline
    A_lin = np.column_stack([xs, np.ones(n_pts)])
    coeffs_lin = np.linalg.lstsq(A_lin, ghs, rcond=None)[0]
    pred_lin = A_lin @ coeffs_lin
    r2_lin = 1 - np.sum((ghs - pred_lin)**2) / ss_tot
    
    # Fit 4: Higher-order polynomial (x_i*x_j*x_k) — is it better than quadratic?
    # Only do up to degree 3 for N=5 (manageable)
    from itertools import combinations_with_replacement
    cubic_features = list(combinations_with_replacement(range(N), 3))
    Phi3 = np.zeros((n_pts, len(cubic_features)))
    for k, idx in enumerate(cubic_features):
        Phi3[:, k] = xs[:, idx[0]] * xs[:, idx[1]] * xs[:, idx[2]]
    
    # Combined quadratic + cubic
    Phi_full = np.column_stack([Phi, Phi3])
    p_full, _, _, _ = np.linalg.lstsq(Phi_full, ghs, rcond=None)
    pred_full = Phi_full @ p_full
    r2_full = 1 - np.sum((ghs - pred_full)**2) / ss_tot
    
    print(f"\n  {c_type}:")
    print(f"    Linear:        R² = {r2_lin:.6f}")
    print(f"    a||x||²+b:     R² = {r2_simple:.6f}")
    print(f"    Full quadratic: R² = {r2_quad:.6f}")
    print(f"    Quad + cubic:  R² = {r2_full:.6f}")
    print(f"    Improvement quadratic→cubic: {r2_full - r2_quad:.6f}")
    
    eigP = np.sort(np.linalg.eigvalsh(P))[::-1]
    print(f"    P eigs: {eigP}")

# ── TEST 2: For C types where quadratic IS good, compare P with metrics ──
print("\n" + "=" * 70)
print("TEST 2: P vs contraction metric candidates (where R² > 0.5)")
print("=" * 70)

for c_type in ['random', 'attention', 'hebbian', 'symmetric']:
    C = generate_C(c_type, N)
    
    rng = np.random.RandomState(42)
    n_pts = 500
    xs = rng.uniform(-1, 1, size=(n_pts, N))
    ghs = np.array([compute_gh(C, x) for x in xs])
    
    Phi = np.array([np.outer(x, x).flatten() for x in xs])
    p_vec, _, _, _ = np.linalg.lstsq(Phi, ghs, rcond=None)
    P = p_vec.reshape(N, N)
    P = (P + P.T) / 2
    pred = Phi @ p_vec
    ss_res = np.sum((ghs - pred)**2)
    ss_tot = np.sum((ghs - np.mean(ghs))**2)
    r2 = 1 - ss_res / ss_tot
    
    if r2 < 0.1:
        print(f"\n  {c_type}: R²={r2:.4f} — SKIPPING (poor quadratic fit)")
        continue
    
    eigP = np.sort(np.linalg.eigvalsh(P))[::-1]
    
    # Fixed point
    x_fp = np.zeros(N)
    for _ in range(5000):
        x_fp = np.tanh(C @ x_fp)
    J_fp = np.diag(1 - x_fp**2) @ C
    eigs_J = np.sort(np.abs(np.linalg.eigvals(J_fp)))[::-1]
    
    print(f"\n  {c_type}: R²={r2:.4f}")
    print(f"    P eigs: {eigP}")
    print(f"    |eig(J_fp)|: {eigs_J}")
    
    # Candidates
    M_I = np.eye(N)
    M_CtC = C.T @ C
    M_direct = np.eye(N) - J_fp.T @ J_fp  # contraction measure
    
    # α C^T C + β I (optimized)
    def loss_ab(params):
        M = params[0] * M_CtC + params[1] * M_I
        return frob_ratio(P, M)
    res = scipy_min(loss_ab, [1.0, 1.0], method='Nelder-Mead')
    M_ab = res.x[0] * M_CtC + res.x[1] * M_I
    
    # Lyapunov at fixed point
    M_lyap = None
    if np.all(eigs_J < 1 - 1e-6):
        try:
            M_lyap = solve_discrete_lyapunov(J_fp.T, np.eye(N))
        except:
            pass
    
    candidates = {
        'I': M_I,
        'C^T C': M_CtC,
        'αC^TC+βI': M_ab,
        'I-J^TJ': M_direct,
    }
    if M_lyap is not None:
        candidates['Lyapunov'] = M_lyap
    
    best_cos, best_name = -2, ''
    for name, M in candidates.items():
        cs = cos_sim(P, M)
        fr = frob_ratio(P, M)
        eigM = np.sort(np.linalg.eigvalsh(M))[::-1]
        ecs = cos_sim(eigP.reshape(1,-1), eigM.reshape(1,-1))
        flag = " ★" if cs > 0.9 else ""
        if cs > best_cos:
            best_cos = cs
            best_name = name
        print(f"    {name:15s}: cos={cs:+.4f}  frob={fr:.4f}  eig_cos={ecs:.4f}{flag}")
    
    print(f"    Best: {best_name} (cos={best_cos:.4f})")

# ── TEST 3: Conservation along single trajectory — what's the relationship? ──
print("\n" + "=" * 70)
print("TEST 3: What is γ+H really? Conservation mechanism analysis")
print("=" * 70)

for c_type in ['random', 'attention', 'hebbian', 'symmetric']:
    C = generate_C(c_type, N)
    x0 = np.random.RandomState(42).randn(N)
    
    traj = [x0.copy()]
    x = x0.copy()
    for _ in range(100):
        x = np.tanh(C @ x)
        traj.append(x.copy())
    traj = np.array(traj)
    
    ghs = np.array([compute_gh(C, xt) for xt in traj])
    norms_sq = np.sum(traj**2, axis=1)
    
    # After convergence (step 20+), what is γ+H?
    late_gh = ghs[20:]
    late_norms = norms_sq[20:]
    
    cv = np.std(late_gh) / (np.mean(late_gh) + 1e-30)
    
    # Check: is γ+H constant because ||x||² is constant?
    cv_norm = np.std(late_norms) / (np.mean(late_norms) + 1e-30)
    
    print(f"\n  {c_type}:")
    print(f"    Late CV(γ+H) = {cv:.6f}")
    print(f"    Late CV(||x||²) = {cv_norm:.6f}")
    print(f"    Correlation r(γ+H, ||x||²) = {np.corrcoef(ghs, norms_sq)[0,1]:.4f}")
    print(f"    Late γ+H ≈ {np.mean(late_gh):.4f} ± {np.std(late_gh):.6f}")
    print(f"    Late ||x||² ≈ {np.mean(late_norms):.4f} ± {np.std(late_norms):.6f}")
    
    # What about the Jacobian eigenvalue structure?
    J_fp = np.diag(1 - traj[-1]**2) @ C
    eigs_J = np.sort(np.real(np.linalg.eigvals(J_fp)))[::-1]
    print(f"    Jacobian eigs at endpoint: {eigs_J}")
    print(f"    Spectral gap (γ): {eigs_J[0]-eigs_J[1]:.4f}")
    
    abs_eigs = np.abs(eigs_J)
    p = abs_eigs / np.sum(abs_eigs)
    H = -np.sum(p * np.log(p))
    print(f"    Participation (H): {H:.4f}")
    print(f"    γ+H = {eigs_J[0]-eigs_J[1]+H:.4f}")
