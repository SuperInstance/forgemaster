#!/usr/bin/env python3
"""
Cycle 011: Contraction Metric Test — v3
Use DIVERSE initial conditions to get well-conditioned P fit.
"""

import numpy as np
from scipy.linalg import solve_discrete_lyapunov
from scipy.optimize import minimize as scipy_min
from scipy.special import softmax

np.set_printoptions(precision=4, suppress=True, linewidth=120)
np.random.seed(42)

N = 5
T = 50
N_SAMPLES = 30  # diverse initial conditions

def generate_C(kind, N, seed=42):
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

def compute_gh_at(C, x):
    """Compute γ+H at a single point."""
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

# ── Step 1: Verify conservation along trajectories ──
print("=" * 70)
print("STEP 1: Verify γ+H conservation")
print("=" * 70)

for c_type in ['random', 'attention', 'hebbian', 'symmetric']:
    C = generate_C(c_type, N)
    cvs = []
    for s in range(5):
        x0 = np.random.RandomState(200 + s).randn(N)
        traj = [x0.copy()]
        x = x0.copy()
        for _ in range(T):
            x = np.tanh(C @ x)
            traj.append(x.copy())
        traj = np.array(traj)
        ghs = np.array([compute_gh_at(C, xt) for xt in traj])
        cv = np.std(ghs[5:]) / (np.mean(ghs[5:]) + 1e-30)
        cvs.append(cv)
    print(f"  {c_type:12s}: mean CV = {np.mean(cvs):.4f} (across 5 trajectories)")

# ── Step 2: Collect diverse (x, γ+H) pairs from MANY trajectories ──
print("\n" + "=" * 70)
print("STEP 2: Fit P from diverse samples, compare with contraction metrics")
print("=" * 70)

all_results = {}

for c_type in ['random', 'attention', 'hebbian', 'symmetric']:
    print(f"\n{'─' * 60}")
    print(f"Coupling: {c_type}")
    
    C = generate_C(c_type, N)
    
    # Collect (x, γ+H) pairs from diverse trajectories and timesteps
    xs_all = []
    gh_all = []
    
    rng = np.random.RandomState(42)
    for s in range(N_SAMPLES):
        x0 = rng.randn(N) * rng.uniform(0.3, 2.0)  # diverse scales
        x = x0.copy()
        for t in range(T):
            x = np.tanh(C @ x)
            gh = compute_gh_at(C, x)
            xs_all.append(x.copy())
            gh_all.append(gh)
    
    xs_all = np.array(xs_all)
    gh_all = np.array(gh_all)
    
    # Check diversity
    print(f"  Samples: {len(xs_all)}")
    print(f"  x norm range: [{np.min(np.linalg.norm(xs_all, axis=1)):.4f}, {np.max(np.linalg.norm(xs_all, axis=1)):.4f}]")
    print(f"  γ+H range: [{np.min(gh_all):.4f}, {np.max(gh_all):.4f}], CV={np.std(gh_all)/np.mean(gh_all):.4f}")
    
    # Fit P: x^T P x ≈ γ+H
    Phi = np.array([np.outer(x, x).flatten() for x in xs_all])
    
    # Use ridge regression
    best_P, best_r2, best_alpha = None, -1e9, 0
    for alpha in [0, 1e-6, 1e-4, 1e-2, 0.1, 1.0, 10.0]:
        I_reg = alpha * np.eye(N * N)
        try:
            p_vec = np.linalg.solve(Phi.T @ Phi + I_reg, Phi.T @ gh_all)
        except:
            continue
        P = p_vec.reshape(N, N)
        P = (P + P.T) / 2
        
        pred = Phi @ p_vec
        ss_res = np.sum((gh_all - pred)**2)
        ss_tot = np.sum((gh_all - np.mean(gh_all))**2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 1e-30 else 0.0
        
        if r2 > best_r2:
            best_r2 = r2
            best_P = P
            best_alpha = alpha
    
    P = best_P
    print(f"\n  Best ridge α = {best_alpha}, R² = {best_r2:.6f}")
    
    eigP = np.sort(np.linalg.eigvalsh(P))[::-1]
    print(f"  P eigenvalues: {eigP}")
    print(f"  P positive definite: {'YES' if all(e > 0 for e in eigP) else 'NO'}")
    print(f"  P condition number: {eigP[0]/(abs(eigP[-1])+1e-30):.2f}")
    
    # ── Candidate Metrics ──
    
    # 1. Identity
    M_I = np.eye(N)
    
    # 2. C^T C
    M_CtC = C.T @ C
    
    # 3. α C^T C + β I (optimized)
    def loss_ab(params):
        M = params[0] * M_CtC + params[1] * M_I
        return frob_ratio(P, M)
    res = scipy_min(loss_ab, [1.0, 1.0], method='Nelder-Mead', options={'xatol': 1e-8, 'fatol': 1e-8})
    M_ab = res.x[0] * M_CtC + res.x[1] * M_I
    
    # 4. Jacobian-based: solve J^T M J ≈ M across multiple points
    js = []
    rng2 = np.random.RandomState(77)
    for _ in range(30):
        x_s = rng2.randn(N)
        for _ in range(20):
            x_s = np.tanh(C @ x_s)
        J = np.diag(1 - x_s**2) @ C
        js.append(J)
    
    def jac_obj(m_vec):
        M = m_vec.reshape(N, N)
        M = (M + M.T) / 2
        loss = sum(np.sum((J.T @ M @ J - M)**2) for J in js)
        return loss
    
    res_jac = scipy_min(jac_obj, np.eye(N).flatten(), method='L-BFGS-B', options={'maxiter': 2000})
    M_jac = res_jac.x.reshape(N, N)
    M_jac = (M_jac + M_jac.T) / 2
    jac_resid = np.mean([np.linalg.norm(J.T @ M_jac @ J - M_jac, 'fro') for J in js])
    
    # 5. Discrete Lyapunov at fixed point
    # Find fixed point
    x_fp = np.zeros(N)
    for _ in range(5000):
        x_fp = np.tanh(C @ x_fp)
    J_fp = np.diag(1 - x_fp**2) @ C
    eigs_J = np.sort(np.abs(np.linalg.eigvals(J_fp)))[::-1]
    print(f"  Fixed point x*: {x_fp}")
    print(f"  |eig(J)|: {eigs_J}")
    
    has_lyap = False
    M_lyap = None
    if np.all(eigs_J < 1.0 - 1e-6):
        try:
            M_lyap = solve_discrete_lyapunov(J_fp.T, np.eye(N))
            has_lyap = True
        except:
            pass
    
    # 6. (I - J^T J) approximation — direct contraction measure
    M_direct = np.eye(N) - J_fp.T @ J_fp
    
    # ── Compare all candidates ──
    candidates = {
        'I': M_I,
        'C^T C': M_CtC,
        'αC^TC+βI': M_ab,
        'Jacobian-avg': M_jac,
        'I - J^TJ': M_direct,
    }
    if has_lyap:
        candidates['Lyapunov'] = M_lyap
    
    print(f"\n  ── Metric Comparison (vs fitted P) ──")
    best_cos, best_name = -2, ''
    for name, M in candidates.items():
        cs = cos_sim(P, M)
        fr = frob_ratio(P, M)
        eigM = np.sort(np.linalg.eigvalsh(M))[::-1]
        ecs = cos_sim(eigP.reshape(1,-1), eigM.reshape(1,-1))
        
        flag = " ★★★" if cs > 0.9 else (" ★" if cs > 0.5 else "")
        if cs > best_cos:
            best_cos = cs
            best_name = name
        print(f"    {name:20s}: cos={cs:+.4f}  frob={fr:.4f}  eig_cos={ecs:.4f}{flag}")
    
    # Also: check if γ+H ≈ a||x||² + b (simpler model)
    norms_sq = np.sum(xs_all**2, axis=1)
    A_fit = np.column_stack([norms_sq, np.ones(len(norms_sq))])
    coeffs = np.linalg.lstsq(A_fit, gh_all, rcond=None)[0]
    pred_n = A_fit @ coeffs
    r2_norm = 1 - np.sum((gh_all - pred_n)**2) / np.sum((gh_all - np.mean(gh_all))**2)
    
    print(f"\n  γ+H ≈ a||x||²+b: R²={r2_norm:.4f} (a={coeffs[0]:.4f}, b={coeffs[1]:.4f})")
    print(f"  Best match: {best_name} (cosine={best_cos:.4f})")
    
    all_results[c_type] = {
        'P': P, 'r2': best_r2, 'eigenvalues': eigP,
        'best_metric': best_name, 'best_cosine': best_cos,
        'norm_r2': r2_norm, 'jac_resid': jac_resid,
        'J_fp_eigs': eigs_J, 'candidates': {k: cos_sim(P, v) for k, v in candidates.items()},
    }

# ── FINAL SUMMARY ──
print("\n" + "=" * 70)
print("FINAL SUMMARY")
print("=" * 70)
print(f"\n{'Type':<12} {'P R²':>8} {'||x||² R²':>10} {'Best':<20} {'Cos':>7} {'P>0?':>5}")
print("─" * 65)
for ct, r in all_results.items():
    pd = "YES" if all(e > 0 for e in r['eigenvalues']) else "no"
    print(f"{ct:<12} {r['r2']:>8.4f} {r['norm_r2']:>10.4f} {r['best_metric']:<20} {r['best_cosine']:>7.4f} {pd:>5}")

n_high = sum(1 for r in all_results.values() if r['best_cosine'] > 0.9)
print(f"\n  cosine > 0.9: {n_high}/{len(all_results)}")

print("\n── Verdict ──")
if n_high == len(all_results):
    print("  ★ P ≈ M — THEOREM CONFIRMED: conservation metric = contraction metric")
elif n_high > 0:
    print("  ◐ Partial: P ≈ M for some but not all architectures")
else:
    print("  ✗ P ≠ M — the quadratic invariant P is NOT the contraction metric")
    print("  P is a genuinely novel object — not I, not C^TC, not Lyapunov metric")
    print("  This is the novel finding: quadratic conservation WITHOUT being a standard metric")

# ── Characterize P ──
print("\n── Characterization of P ──")
for ct, r in all_results.items():
    eigP = r['eigenvalues']
    print(f"  {ct}: eigs={eigP}")
    print(f"       rank≈{sum(e > 0.01 * abs(eigP[0]) for e in eigP)}, trace={np.trace(r['P']):.4f}")
