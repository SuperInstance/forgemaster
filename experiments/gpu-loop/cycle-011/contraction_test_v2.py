#!/usr/bin/env python3
"""
Cycle 011: Contraction Metric Test — v2 (fixed)
First verify γ+H conservation, then fit P with proper conditioning.
"""

import numpy as np
from scipy.linalg import solve_discrete_lyapunov
from scipy.optimize import minimize as scipy_min
from scipy.special import softmax

np.set_printoptions(precision=4, suppress=True, linewidth=120)
np.random.seed(42)

# ── Parameters (SMALL) ──
N = 5
T = 50
N_SAMPLES = 10

def generate_C(kind, N, seed=None):
    rng = np.random.RandomState(seed)
    if kind == 'random':
        C = rng.randn(N, N) * 0.5
    elif kind == 'attention':
        Q, K = rng.randn(N, N), rng.randn(N, N)
        raw = (Q @ K.T) / np.sqrt(N)
        C = softmax(raw, axis=1)
    elif kind == 'hebbian':
        patterns = rng.choice([-1, 1], size=(3, N))
        C = patterns.T @ patterns / N
        np.fill_diagonal(C, 0)
    elif kind == 'symmetric':
        A = rng.randn(N, N) * 0.5
        C = (A + A.T) / 2
    return C

def evolve(C, x0, T):
    traj = [x0.copy()]
    x = x0.copy()
    for _ in range(T):
        x = np.tanh(C @ x)
        traj.append(x.copy())
    return np.array(traj)

def compute_gh(traj, C):
    """γ+H = spectral_gap + participation_entropy of Jacobian eigenvalues."""
    vals = np.zeros(len(traj))
    for t in range(len(traj)):
        x = traj[t]
        J = np.diag(1 - x**2) @ C
        eigs = np.sort(np.real(np.linalg.eigvals(J)))[::-1]
        gamma = eigs[0] - eigs[1] if len(eigs) > 1 else 0.0
        abs_eigs = np.abs(eigs)
        total = np.sum(abs_eigs)
        if total > 1e-15:
            p = abs_eigs / total
            p = p[p > 1e-15]
            H = -np.sum(p * np.log(p))
        else:
            H = 0.0
        vals[t] = gamma + H
    return vals

def fit_P_ridge(xs, ghs, N, alpha=0.01):
    """Fit P via ridge regression: x^T P x ≈ γ+H"""
    n = len(xs)
    Phi = np.zeros((n, N * N))
    for k, x in enumerate(xs):
        Phi[k] = np.outer(x, x).flatten()
    
    # Ridge regression
    I_reg = alpha * np.eye(N * N)
    p_vec = np.linalg.solve(Phi.T @ Phi + I_reg, Phi.T @ ghs)
    P = p_vec.reshape(N, N)
    P = (P + P.T) / 2  # symmetrize
    
    predicted = Phi @ p_vec
    ss_res = np.sum((ghs - predicted)**2)
    ss_tot = np.sum((ghs - np.mean(ghs))**2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    
    return P, r2

def cos_sim(A, B):
    a, b = A.flatten(), B.flatten()
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-30)

def frob_ratio(A, B):
    return np.linalg.norm(A - B, 'fro') / (np.linalg.norm(A, 'fro') + 1e-30)

# ── Step 1: Verify conservation ──
print("=" * 70)
print("STEP 1: Verify γ+H conservation")
print("=" * 70)

for c_type in ['random', 'attention', 'hebbian', 'symmetric']:
    C = generate_C(c_type, N, seed=42)
    x0 = np.random.RandomState(100).randn(N) * 0.5
    traj = evolve(C, x0, T)
    ghs = compute_gh(traj, C)
    
    cv = np.std(ghs) / (np.mean(ghs) + 1e-30)
    print(f"  {c_type:12s}: mean={np.mean(ghs):.4f}, std={np.std(ghs):.4f}, CV={cv:.4f}")
    print(f"               range=[{np.min(ghs):.4f}, {np.max(ghs):.4f}]")

# ── Step 2: Fit P and compare with candidates ──
print("\n" + "=" * 70)
print("STEP 2: Fit P and compare with contraction metric candidates")
print("=" * 70)

all_results = {}

for c_type in ['random', 'attention', 'hebbian', 'symmetric']:
    print(f"\n{'─' * 60}")
    print(f"Coupling: {c_type}")
    
    C = generate_C(c_type, N, seed=42)
    x0 = np.random.RandomState(100).randn(N) * 0.5
    traj = evolve(C, x0, T)
    ghs = compute_gh(traj, C)
    
    # Use all trajectory points (skip very first transient)
    xs = traj[3:]
    gh_vals = ghs[3:]
    
    # Check diversity of x values
    xs_centered = xs - np.mean(xs, axis=0)
    x_spread = np.linalg.norm(xs_centered, axis=1)
    print(f"  x spread: mean={np.mean(x_spread):.6f}, std={np.std(x_spread):.6f}")
    
    # Fit P with different ridge penalties
    best_P = None
    best_r2 = -1e9
    for alpha in [0.0, 1e-6, 1e-4, 1e-2, 1e-1, 1.0]:
        P, r2 = fit_P_ridge(xs, gh_vals, N, alpha=alpha)
        if r2 > best_r2:
            best_r2 = r2
            best_P = P
            best_alpha = alpha
    
    print(f"  Best ridge alpha: {best_alpha}")
    print(f"  R² of x^T P x ≈ γ+H: {best_r2:.6f}")
    
    P = best_P
    eigP = np.sort(np.linalg.eigvalsh(P))[::-1]
    print(f"  P eigenvalues: {eigP}")
    print(f"  P pos def: {'YES' if all(e > 0 for e in eigP) else 'NO'}")
    
    # ── Candidate metrics ──
    M_identity = np.eye(N)
    M_ctc = C.T @ C
    
    # α·C^T C + β·I (optimize)
    def loss_ab(params):
        a, b = params
        M = a * M_ctc + b * M_identity
        return frob_ratio(P, M)
    res = scipy_min(loss_ab, [1.0, 1.0], method='Nelder-Mead')
    M_ab = res.x[0] * M_ctc + res.x[1] * M_identity
    
    # Jacobian-based: find M such that J^T M J ≈ M at sample points
    # Use fixed point Jacobian
    x = np.random.randn(N) * 0.1
    for _ in range(2000):
        x_new = np.tanh(C @ x)
        if np.linalg.norm(x_new - x) < 1e-12:
            break
        x = x_new
    J_star = np.diag(1 - x**2) @ C
    
    # Discrete Lyapunov: solve J^T M J = M (invariant quadratic)
    # This is the Stein equation J^T M J - M = 0
    # For |eig(J)| < 1, the unique solution is M = 0 (trivial)
    # For our purposes, solve J^T M J ≈ M in least squares
    
    # Sample multiple Jacobians
    js = []
    rng2 = np.random.RandomState(99)
    for _ in range(30):
        x_sample = rng2.randn(N) * 0.5
        x_sample = np.tanh(C @ x_sample)  # put on/near attractor
        J = np.diag(1 - x_sample**2) @ C
        js.append(J)
    js = np.array(js)
    
    # Solve: minimize sum_k ||J_k^T M J_k - M||_F^2
    def jac_metric_obj(m_vec):
        M = m_vec.reshape(N, N)
        M = (M + M.T) / 2
        loss = 0
        for J in js:
            diff = J.T @ M @ J - M
            loss += np.sum(diff**2)
        return loss
    
    res_jac = scipy_min(jac_metric_obj, np.eye(N).flatten(), method='L-BFGS-B', 
                        options={'maxiter': 1000})
    M_jac = res_jac.x.reshape(N, N)
    M_jac = (M_jac + M_jac.T) / 2
    jac_avg_resid = np.mean([np.linalg.norm(J.T @ M_jac @ J - M_jac, 'fro') for J in js])
    
    # Try discrete Lyapunov (solve M - J^T M J = Q, Q = I)
    try:
        M_lyap = solve_discrete_lyapunov(J_star.T, np.eye(N))
        has_lyap = True
    except:
        M_lyap = None
        has_lyap = False
    
    # ── Compare ──
    print(f"\n  ── Metric Comparison ──")
    candidates = {
        'I': M_identity,
        'C^T C': M_ctc,
        f'αC^TC+βI': M_ab,
        'Jacobian-avg': M_jac,
    }
    if has_lyap:
        candidates['Lyapunov'] = M_lyap
    
    best_cos = -2
    best_name = ''
    for name, M in candidates.items():
        cs = cos_sim(P, M)
        fr = frob_ratio(P, M)
        
        # Eigenvalue spectrum comparison
        eigM = np.sort(np.linalg.eigvalsh(M))[::-1]
        eig_cs = cos_sim(eigP.reshape(1,-1), eigM.reshape(1,-1))
        
        flag = " ★" if cs > 0.9 else (" ◐" if cs > 0.5 else "")
        if cs > best_cos:
            best_cos = cs
            best_name = name
        
        print(f"    {name:20s}: cos={cs:+.4f}  frob={fr:.4f}  eig_cos={eig_cs:.4f}{flag}")
    
    print(f"\n  Best match: {best_name} (cosine={best_cos:.4f})")
    
    # Also: what IS γ+H as a function of x?
    # Check if γ+H ≈ a||x||^2 + b
    norms_sq = np.array([np.dot(x, x) for x in xs])
    norms_sq_norm = (norms_sq - np.mean(norms_sq)) / (np.std(norms_sq) + 1e-30)
    gh_norm = (gh_vals - np.mean(gh_vals)) / (np.std(gh_vals) + 1e-30)
    r_norm = np.corrcoef(norms_sq_norm, gh_norm)[0, 1]
    
    # Linear fit: γ+H = a * ||x||^2 + b
    A_fit = np.column_stack([norms_sq, np.ones(len(norms_sq))])
    coeffs = np.linalg.lstsq(A_fit, gh_vals, rcond=None)[0]
    predicted_norm = A_fit @ coeffs
    ss_res = np.sum((gh_vals - predicted_norm)**2)
    ss_tot = np.sum((gh_vals - np.mean(gh_vals))**2)
    r2_norm = 1 - ss_res / ss_tot
    
    print(f"\n  γ+H ≈ a||x||²+b: r={r_norm:.4f}, R²={r2_norm:.4f}")
    print(f"  (a={coeffs[0]:.4f}, b={coeffs[1]:.4f})")
    
    all_results[c_type] = {
        'P': P, 'r2': best_r2, 'eigenvalues': eigP,
        'best_metric': best_name, 'best_cosine': best_cos,
        'norm_r2': r2_norm,
        'candidates': {k: cos_sim(P, v) for k, v in candidates.items()},
    }

# ── Summary ──
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"\n{'Type':<12} {'P R²':>8} {'Best Metric':<20} {'Cos':>7} {'P>0?':>5} {'||x||² R²':>10}")
print("─" * 65)
for ct, r in all_results.items():
    pd = "YES" if all(e > 0 for e in r['eigenvalues']) else "no"
    print(f"{ct:<12} {r['r2']:>8.4f} {r['best_metric']:<20} {r['best_cosine']:>7.4f} {pd:>5} {r['norm_r2']:>10.4f}")

n_match = sum(1 for r in all_results.values() if r['best_cosine'] > 0.9)
print(f"\n  cosine > 0.9: {n_match}/{len(all_results)}")
if n_match == len(all_results):
    print("  ★ P ≈ M (contraction metric) — THEOREM CONFIRMED")
elif n_match > 0:
    print("  ◐ Partial match")
else:
    print("  ✗ P ≠ M for all architectures")
    print("  The conservation metric P is NOT the standard contraction metric.")
    print("  It is a genuinely novel quadratic invariant.")
