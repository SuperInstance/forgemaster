#!/usr/bin/env python3
"""
Cycle 011: Test whether P matrix from γ+H = x^T P x equals the contraction metric M.

KEEP IT SMALL: N=5, 10 samples, 50 timesteps
"""

import numpy as np
from scipy.optimize import minimize
from itertools import product

np.random.seed(42)

# ── Parameters ──
N = 5
T = 50
N_SAMPLES = 10
ACTIVATIONS = 50  # for computing Jacobian at multiple points

def generate_C(kind, N, seed=None):
    """Generate coupling matrix of given type."""
    rng = np.random.RandomState(seed)
    if kind == 'random':
        C = rng.randn(N, N) * 0.5
    elif kind == 'attention':
        Q, K = rng.randn(N, N), rng.randn(N, N)
        C = (Q @ K.T) / np.sqrt(N)
        # Row-stochastic via softmax
        from scipy.special import softmax
        C = softmax(C, axis=1)
    elif kind == 'hebbian':
        patterns = rng.choice([-1, 1], size=(3, N))
        C = patterns.T @ patterns / N
        np.fill_diagonal(C, 0)
    elif kind == 'symmetric':
        A = rng.randn(N, N) * 0.5
        C = (A + A.T) / 2
    else:
        raise ValueError(f"Unknown kind: {kind}")
    return C

def evolve(C, x0, T):
    """Evolve x_{t+1} = tanh(C @ x_t) for T steps."""
    traj = [x0.copy()]
    x = x0.copy()
    for _ in range(T):
        x = np.tanh(C @ x)
        traj.append(x.copy())
    return np.array(traj)

def compute_gamma_plus_H(traj, C):
    """Compute γ+H at each timestep along trajectory."""
    n = traj.shape[0]
    vals = np.zeros(n)
    for t in range(n):
        x = traj[t]
        # Eigenvalues of Jacobian of the map
        J = np.diag(1 - x**2) @ C  # d(tanh(Cx))/dx = diag(sech²(Cx)) · C
        eigs = np.linalg.eigvals(J)
        eigs = np.real(eigs)
        eigs = np.sort(eigs)[::-1]
        
        # γ: spectral gap (largest real part eigenvalue - second largest)
        gamma = np.real(eigs[0]) - np.real(eigs[1]) if len(eigs) > 1 else 0.0
        
        # H: participation entropy of eigenvectors
        # Use |eigenvalues|^2 as weights (from eigenvector participation)
        abs_eigs = np.abs(eigs)
        if np.sum(abs_eigs) > 0:
            p = abs_eigs / np.sum(abs_eigs)
            p = p[p > 1e-15]
            H = -np.sum(p * np.log(p + 1e-30))
        else:
            H = 0.0
        
        vals[t] = gamma + H
    return vals

def fit_P_quadratic(xs, ghs, N):
    """Fit P such that x^T P x ≈ γ+H via least squares."""
    # x^T P x = sum_{i,j} P_{ij} x_i x_j
    # Build design matrix: each row is x_i*x_j for all (i,j) with i<=j
    # P is symmetric, so we only need upper triangle
    
    # Build full quadratic feature matrix
    n_points = len(xs)
    n_features = N * N  # full matrix (we'll symmetrize)
    
    # Actually, use vectorized form: x^T P x = vec(P)^T vec(x x^T)
    # But P is symmetric, so we can use upper triangle
    triu_idx = np.triu_indices(N)
    n_features = len(triu_idx[0])
    
    # Simpler: just build full outer product and solve for full P
    Phi_full = np.zeros((n_points, N * N))
    for k, x in enumerate(xs):
        Phi_full[k] = np.outer(x, x).flatten()
    
    # Solve least squares: Phi_full @ p_vec = ghs
    result = np.linalg.lstsq(Phi_full, ghs, rcond=None)
    p_vec = result[0]
    P = p_vec.reshape(N, N)
    # Symmetrize
    P = (P + P.T) / 2
    
    # Compute R²
    predicted = np.array([x @ P @ x for x in xs])
    ss_res = np.sum((ghs - predicted)**2)
    ss_tot = np.sum((ghs - np.mean(ghs))**2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    
    return P, r2

def cosine_similarity_matrices(A, B):
    """Cosine similarity between flattened matrices."""
    a = A.flatten()
    b = B.flatten()
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-30)

def frobenius_ratio(A, B):
    """||A - B||_F / ||A||_F (relative Frobenius distance)."""
    return np.linalg.norm(A - B, 'fro') / (np.linalg.norm(A, 'fro') + 1e-30)

def compute_jacobian_metric(C, N, n_points=20):
    """Compute M such that J^T M J ≈ M averaged over Jacobians at sample points.
    
    This is the contraction metric condition from Lohmiller-Slotine:
    For contraction, we need the symmetric part of the generalized Jacobian
    to be negative definite: M J + J^T M < 0 (continuous) or 
    J^T M J < M (discrete).
    
    We solve for M that best satisfies J^T M J ≈ M in least-squares sense
    across multiple sample points.
    """
    rng = np.random.RandomState(123)
    
    # Sample points in the state space
    js = []
    for _ in range(n_points):
        x = rng.randn(N) * 0.5
        J = np.diag(1 - x**2) @ C  # Jacobian of tanh(Cx)
        js.append(J)
    
    # Solve: find symmetric M such that sum_k ||J_k^T M J_k - M||_F^2 is minimized
    # Vectorize: for each J_k, J_k^T M J_k = (J_k ⊗ J_k)^T vec(M)
    # So vec(J_k^T M J_k) = (J_k ⊗ J_k)^T vec(M) ... no wait
    
    # J^T M J: element (i,j) = sum_{a,b} J_{ai} M_{ab} J_{bj}
    # vec(J^T M J) = (J ⊗ J)^T vec(M)
    # Actually: (J^T M J) = unfold(J^T M J) and there's a Kronecker relationship
    
    # Simpler approach: just use scipy.optimize
    # Minimize sum_k ||J_k^T M J_k - M||_F^2
    
    def objective(m_vec):
        M = m_vec.reshape(N, N)
        M = (M + M.T) / 2  # enforce symmetry
        loss = 0.0
        for J in js:
            diff = J.T @ M @ J - M
            loss += np.sum(diff**2)
        return loss
    
    def grad(m_vec):
        M = m_vec.reshape(N, N)
        M = (M + M.T) / 2
        g = np.zeros_like(M)
        for J in js:
            diff = J.T @ M @ J - M
            # d/dM ||J^T M J - M||^2 = 2*(J^T M J - M) : (J J^T - I)
            # Actually: d/dM_ij sum_{kl} (sum_{ab} J_{ak}M_{ab}J_{bl} - M_{kl})^2
            # = 2 * sum_{kl} diff_{kl} * d(diff_{kl})/dM_{ij}
            # diff_{kl} = sum_{ab} J_{ak} M_{ab} J_{bl} - M_{kl}
            # d(diff_{kl})/dM_{ij} = J_{ik} J_{jl} - delta_{ki} delta_{lj}
            g += 2 * (J @ diff @ J.T - diff)
        g = (g + g.T) / 2  # symmetrize gradient
        return g.flatten()
    
    # Start from identity
    m0 = np.eye(N).flatten()
    result = minimize(objective, m0, jac=grad, method='L-BFGS-B', 
                     options={'maxiter': 500})
    M = result.x.reshape(N, N)
    M = (M + M.T) / 2
    
    # Quality: average ||J^T M J - M||_F
    avg_residual = np.mean([np.linalg.norm(J.T @ M @ J - M, 'fro') for J in js])
    
    return M, avg_residual, result.fun

def solve_contraction_sdp(C, N):
    """Solve for contraction metric M via the discrete condition J^T M J <= M.
    
    For tanh(Cx), the Jacobian at any point x satisfies ||J|| <= ||C|| * max(sech²).
    We seek M > 0 such that for the fixed-point Jacobian, J^T M J < M.
    
    Simplified: solve at the fixed point x* = tanh(C x*).
    """
    # Find fixed point
    x = np.random.randn(N) * 0.1
    for _ in range(1000):
        x_new = np.tanh(C @ x)
        if np.linalg.norm(x_new - x) < 1e-12:
            break
        x = x_new
    x_star = x
    
    J_star = np.diag(1 - x_star**2) @ C
    
    # For discrete contraction: need M > 0 such that M - J^T M J > 0
    # This is a Lyapunov inequality. If J is stable (all |eigs| < 1), 
    # then M = I works. If not, we need to find M.
    
    # Try: M = I
    M_identity = np.eye(N)
    residual_identity = np.linalg.norm(J_star.T @ M_identity @ J_star - M_identity, 'fro')
    
    # Try: solve discrete Lyapunov for the Jacobian
    # J^T M J - M = -Q for some Q > 0
    # This is the Stein equation. scipy.linalg.solve_discrete_lyapunov
    from scipy.linalg import solve_discrete_lyapunov
    try:
        # Stein: M - J^T M J = Q. With Q = I:
        M_lyap = solve_discrete_lyapunov(J_star.T, np.eye(N))
        residual_lyap = np.linalg.norm(J_star.T @ M_lyap @ J_star - M_lyap, 'fro')
    except Exception:
        M_lyap = None
        residual_lyap = float('inf')
    
    return {
        'x_star': x_star,
        'J_star': J_star,
        'M_identity': M_identity,
        'residual_identity': residual_identity,
        'M_lyap': M_lyap,
        'residual_lyap': residual_lyap,
        'eigs_J': np.sort(np.abs(np.linalg.eigvals(J_star)))[::-1]
    }

# ── Main Experiment ──
print("=" * 70)
print("CYCLE 011: P Matrix vs Contraction Metric M")
print("=" * 70)

C_types = ['random', 'attention', 'hebbian', 'symmetric']
results = {}

for c_type in C_types:
    print(f"\n{'─' * 60}")
    print(f"Coupling type: {c_type}")
    print(f"{'─' * 60}")
    
    all_Ps = []
    all_r2s = []
    
    for sample in range(N_SAMPLES):
        C = generate_C(c_type, N, seed=42 + sample)
        
        # Evolve from random initial condition
        x0 = np.random.RandomState(100 + sample).randn(N) * 0.5
        traj = evolve(C, x0, T)
        ghs = compute_gamma_plus_H(traj, C)
        
        # Skip first few steps (transient)
        xs = traj[5:]
        gh_vals = ghs[5:]
        
        # Fit P
        P, r2 = fit_P_quadratic(xs, gh_vals, N)
        all_Ps.append(P)
        all_r2s.append(r2)
    
    # Average P across samples
    P_avg = np.mean(all_Ps, dtype=float)
    avg_r2 = np.mean(all_r2s)
    
    print(f"  Average R² of x^T P x ≈ γ+H: {avg_r2:.6f}")
    print(f"  P matrix (averaged, first sample):")
    P0 = all_Ps[0]
    for row in P0:
        print(f"    [{', '.join(f'{v:8.4f}' for v in row)}]")
    
    # Now compute candidate metrics using first sample's C
    C0 = generate_C(c_type, N, seed=42)
    
    # Candidate 1: M = I
    M_identity = np.eye(N)
    
    # Candidate 2: M = C^T C
    M_ctc = C0.T @ C0
    
    # Candidate 3: M = α·C^T C + β·I (fit α, β)
    def loss_alpha_beta(params):
        alpha, beta = params
        M = alpha * M_ctc + beta * M_identity
        return frobenius_ratio(P0, M)
    
    from scipy.optimize import minimize as scipy_min
    res_ab = scipy_min(loss_alpha_beta, [1.0, 1.0], method='Nelder-Mead')
    alpha_opt, beta_opt = res_ab.x
    M_alpha_beta = alpha_opt * M_ctc + beta_opt * M_identity
    
    # Candidate 4: Jacobian-based contraction metric
    M_jacobian, jac_residual, jac_loss = compute_jacobian_metric(C0, N, n_points=20)
    
    # Candidate 5: Discrete Lyapunov / SDP at fixed point
    sdp_result = solve_contraction_sdp(C0, N)
    M_lyap = sdp_result['M_lyap']
    
    # Compare all candidates to fitted P
    print(f"\n  ── Candidate Metric Comparison ──")
    candidates = {
        'I (identity)': M_identity,
        'C^T C': M_ctc,
        f'αC^TC+βI (α={alpha_opt:.3f}, β={beta_opt:.3f})': M_alpha_beta,
        'Jacobian-avg (J^T M J ≈ M)': M_jacobian,
    }
    if M_lyap is not None:
        candidates['Discrete Lyapunov'] = M_lyap
    
    best_sim = -1
    best_name = ''
    
    for name, M in candidates.items():
        cos_sim = cosine_similarity_matrices(P0, M)
        f_ratio = frobenius_ratio(P0, M)
        
        # Also check: is P *closer* to M in eigenspace?
        eigP = np.sort(np.linalg.eigvalsh(P0))[::-1]
        eigM = np.sort(np.linalg.eigvalsh(M))[::-1]
        eig_cos = cosine_similarity_matrices(eigP.reshape(1,-1), eigM.reshape(1,-1))
        
        marker = " ◀◀◀" if cos_sim > best_sim else ""
        if cos_sim > best_sim:
            best_sim = cos_sim
            best_name = name
        
        print(f"  {name}:")
        print(f"    cosine_sim = {cos_sim:.6f}  |  frob_ratio = {f_ratio:.4f}  |  eig_cos = {eig_cos:.6f}{marker}")
    
    # Eigenvalue spectrum of P
    eigP = np.sort(np.linalg.eigvalsh(P0))[::-1]
    print(f"\n  P eigenvalues: [{', '.join(f'{v:.4f}' for v in eigP)}]")
    print(f"  P is {'positive definite' if all(e > 0 for e in eigP) else 'NOT positive definite'}")
    print(f"  P condition number: {eigP[0]/(eigP[-1]+1e-30):.2f}")
    print(f"  Best matching metric: {best_name} (cosine_sim = {best_sim:.6f})")
    
    # Store
    results[c_type] = {
        'P': P0,
        'r2': avg_r2,
        'best_metric': best_name,
        'best_cosine': best_sim,
        'candidates': {k: {'cosine': cosine_similarity_matrices(P0, v), 
                           'frob': frobenius_ratio(P0, v)} 
                      for k, v in candidates.items()},
        'P_eigenvalues': eigP,
        'SDP': sdp_result,
    }

# ── Summary ──
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"\n{'Type':<15} {'R²':>8} {'Best Metric':<30} {'Cosine':>8} {'P pos.def?':>10}")
print("─" * 75)
for c_type, r in results.items():
    pd = "YES" if all(e > 0 for e in r['P_eigenvalues']) else "NO"
    print(f"{c_type:<15} {r['r2']:>8.4f} {r['best_metric']:<30} {r['best_cosine']:>8.4f} {pd:>10}")

print("\n── Verdict ──")
high_match = sum(1 for r in results.values() if r['best_cosine'] > 0.9)
print(f"  Architectures with cosine_sim > 0.9: {high_match}/{len(results)}")
if high_match == len(results):
    print("  ★ P ≈ M (contraction metric) — THEOREM CONFIRMED")
elif high_match > 0:
    print("  ◐ Partial match — P ≈ M for some architectures")
    for c_type, r in results.items():
        if r['best_cosine'] > 0.9:
            print(f"    Match: {c_type} → {r['best_metric']} (cos={r['best_cosine']:.4f})")
        else:
            print(f"    No match: {c_type} → best cos={r['best_cosine']:.4f}")
else:
    print("  ✗ P ≠ M — conservation metric is NOT the contraction metric")
    print("  P represents something else — document its properties")

# What does P look like?
print("\n── What is P? ──")
for c_type, r in results.items():
    P = r['P']
    eigP = r['P_eigenvalues']
    print(f"\n  {c_type}:")
    print(f"    Eigenvalues: {eigP}")
    print(f"    Rank (eigs > 0.01*max): {sum(e > 0.01*eigP[0] for e in eigP)}/{N}")
    print(f"    Trace: {np.trace(P):.4f}")
    print(f"    Det: {np.linalg.det(P):.6f}")
