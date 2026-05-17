#!/usr/bin/env python3
"""
Experiment: Is P = M (Contraction Metric)?

Tests whether the quadratic conservation matrix P in γ+H = x^T P x
matches the contraction metric M from Lohmiller & Slotine's framework.

If P = M, conservation follows from contraction theory — a proven result.
That's the theorem.

Hypotheses:
  H1: M = I (identity) → x^T x = γ+H?
  H2: M = C^T C → ‖Cx‖² = γ+H?
  H3: M = α·C^T C + β·I → generalized metric = γ+H?
  H4: M from SDP (J^T M J = M, J = diag(sech²(Cx))·C) → contraction metric = γ+H?

Author: Forgemaster ⚒️ subagent | GPU Constraint Experiment Loop | Cycle 8
"""

import numpy as np
from scipy.optimize import minimize, linprog
from scipy.linalg import solve_continuous_lyapunov, block_diag
from itertools import product
import warnings
import json
import os
import sys

warnings.filterwarnings("ignore")

# ─── Configuration ───────────────────────────────────────────────────────────

SEED = 42
N_AGENTS = 10           # dimension of coupling matrix
N_STEPS = 200            # timesteps per trajectory
N_SAMPLES = 30           # number of random C matrices to test
NOISE_SIGMA = 0.0        # no noise (clean test of the theory)

np.random.seed(SEED)

# ─── Dynamics ────────────────────────────────────────────────────────────────

def evolve_tanh(C, x0, n_steps, sigma=0.0):
    """Evolve x_{t+1} = tanh(C @ x_t) with optional noise."""
    N = len(x0)
    xs = np.zeros((n_steps + 1, N))
    xs[0] = x0.copy()
    for t in range(n_steps):
        xs[t+1] = np.tanh(C @ xs[t])
        if sigma > 0:
            xs[t+1] += sigma * np.random.randn(N)
    return xs


def compute_gamma_H(C, xs):
    """
    Compute γ (spectral gap) and H (participation entropy) at each timestep.
    
    State-dependent coupling: C(x) = C (fixed), but we compute γ, H from C's eigenvalues.
    
    For the conservation test, we need the ACTUAL γ+H that was observed to be conserved
    in previous cycles. Based on the cycle 4 findings, γ+H = x^T P x with R²=1.0.
    
    Here we compute γ+H directly from the coupling matrix eigenvalues AND
    also compute the candidate contraction metrics.
    """
    n_steps = len(xs)
    
    # Eigenvalues of C (fixed coupling)
    eigenvalues = np.linalg.eigvals(C)
    abs_evals = np.abs(eigenvalues)
    abs_evals = np.sort(abs_evals)[::-1]  # descending
    
    # γ = spectral gap = |λ₁| - |λ₂| (or |λ_max| - |λ_min| depending on convention)
    # Based on previous cycles: γ is the gap between top eigenvalue and the rest
    if len(abs_evals) > 1:
        gamma = abs_evals[0] - abs_evals[1]
    else:
        gamma = 0.0
    
    # H = participation entropy = -Σ (|λᵢ|²/Σ|λⱼ|²) * log(|λᵢ|²/Σ|λⱼ|²)
    weights = abs_evals**2 / np.sum(abs_evals**2)
    H = -np.sum(weights * np.log(weights + 1e-30))
    
    return gamma, H


def compute_gamma_H_state_dependent(C, x):
    """
    Compute γ+H from a STATE-DEPENDENT coupling matrix.
    Based on cycle 4-6 findings, the coupling can be state-dependent.
    
    For the contraction metric test, we use the FIXED C matrix eigenvalues
    but allow the state to enter through the Jacobian.
    
    Returns γ+H value. For the contraction metric hypothesis,
    we test whether this equals x^T M x for various M.
    """
    eigenvalues = np.linalg.eigvals(C)
    abs_evals = np.sort(np.abs(eigenvalues))[::-1]
    
    if len(abs_evals) > 1:
        gamma = abs_evals[0] - abs_evals[1]
    else:
        gamma = 0.0
    
    weights = abs_evals**2 / np.sum(abs_evals**2)
    H = -np.sum(weights * np.log(weights + 1e-30))
    
    return gamma + H


def compute_jacobian(C, x):
    """Jacobian J = diag(sech²(Cx)) · C"""
    pre_act = C @ x
    sech2 = 1.0 / np.cosh(pre_act)**2
    return np.diag(sech2) @ C


def fit_P_from_data(xs, gamma_H_values):
    """
    Fit P from the conservation law γ+H = x^T P x.
    Returns the best-fit P matrix (symmetric).
    """
    n_steps, N = xs.shape
    
    # Build the regression problem: for each timestep, x^T P x = γ+H
    # P has N*(N+1)/2 free parameters (symmetric)
    
    # Create feature matrix: each row is [x_i*x_j for i<=j]
    n_params = N * (N + 1) // 2
    
    # Map from (i,j) to parameter index
    idx_map = {}
    k = 0
    for i in range(N):
        for j in range(i, N):
            idx_map[(i, j)] = k
            k += 1
    
    # Feature matrix
    Phi = np.zeros((n_steps, n_params))
    for t in range(n_steps):
        for i in range(N):
            for j in range(i, N):
                if i == j:
                    Phi[t, idx_map[(i, j)]] = xs[t, i] * xs[t, i]
                else:
                    Phi[t, idx_map[(i, j)]] = 2.0 * xs[t, i] * xs[t, j]  # off-diagonal counts twice
    
    y = np.array(gamma_H_values)
    
    # Least squares
    result = np.linalg.lstsq(Phi, y, rcond=None)
    params = result[0]
    
    # Reconstruct P
    P = np.zeros((N, N))
    for i in range(N):
        for j in range(i, N):
            val = params[idx_map[(i, j)]]
            P[i, j] = val
            P[j, i] = val
    
    # Compute R²
    y_pred = Phi @ params
    ss_res = np.sum((y - y_pred)**2)
    ss_tot = np.sum((y - np.mean(y))**2)
    r2 = 1.0 - ss_res / (ss_tot + 1e-30)
    
    return P, r2


def test_metric_identity(xs, gamma_H_values):
    """H1: M = I → γ+H = x^T x = ‖x‖²?"""
    n_steps = len(xs)
    quad_vals = np.array([x @ x for x in xs])
    
    # Fit scalar: γ+H ≈ α * ‖x‖²
    A = quad_vals.reshape(-1, 1)
    y = np.array(gamma_H_values)
    result = np.linalg.lstsq(A, y, rcond=None)
    alpha = result[0][0]
    
    y_pred = A @ result[0]
    ss_res = np.sum((y - y_pred)**2)
    ss_tot = np.sum((y - np.mean(y))**2)
    r2 = 1.0 - ss_res / (ss_tot + 1e-30)
    
    return {"name": "M = I (identity)", "r2": r2, "alpha": alpha}


def test_metric_CtC(C, xs, gamma_H_values):
    """H2: M = C^T C → γ+H = x^T C^T C x = ‖Cx‖²?"""
    CtC = C.T @ C
    n_steps = len(xs)
    quad_vals = np.array([x @ CtC @ x for x in xs])
    
    A = quad_vals.reshape(-1, 1)
    y = np.array(gamma_H_values)
    result = np.linalg.lstsq(A, y, rcond=None)
    alpha = result[0][0]
    
    y_pred = A @ result[0]
    ss_res = np.sum((y - y_pred)**2)
    ss_tot = np.sum((y - np.mean(y))**2)
    r2 = 1.0 - ss_res / (ss_tot + 1e-30)
    
    return {"name": "M = C^T C", "r2": r2, "alpha": alpha}


def test_metric_generalized(C, xs, gamma_H_values):
    """H3: M = α·C^T C + β·I → γ+H = α·‖Cx‖² + β·‖x‖²?"""
    CtC = C.T @ C
    I = np.eye(len(C))
    n_steps = len(xs)
    
    quad_CtC = np.array([x @ CtC @ x for x in xs])
    quad_I = np.array([x @ I @ x for x in xs])
    
    A = np.column_stack([quad_CtC, quad_I])
    y = np.array(gamma_H_values)
    result = np.linalg.lstsq(A, y, rcond=None)
    alpha, beta = result[0]
    
    y_pred = A @ result[0]
    ss_res = np.sum((y - y_pred)**2)
    ss_tot = np.sum((y - np.mean(y))**2)
    r2 = 1.0 - ss_res / (ss_tot + 1e-30)
    
    return {"name": "M = α·C^T C + β·I", "r2": r2, "alpha": alpha, "beta": beta}


def test_metric_jacobian_sdp(C, xs, gamma_H_values):
    """
    H4: M from the contraction condition J^T M J = M.
    
    At the fixed point x* where x* = tanh(Cx*), the Jacobian is:
    J* = diag(sech²(Cx*)) · C
    
    The contraction metric M satisfies J*^T M J* = λ M for some λ < 1 (contraction)
    or J*^T M J* = M (neutral, conserved).
    
    We solve for M by treating J*^T M J* = M as a Lyapunov-like equation.
    
    For discrete time: M = J M J^T + Q for some Q ≻ 0.
    If we want J^T M J = M, this means M is an invariant quadratic form of J.
    """
    N = len(C)
    
    # Find fixed point by iterating
    x = np.random.randn(N) * 0.1
    for _ in range(1000):
        x_new = np.tanh(C @ x)
        if np.linalg.norm(x_new - x) < 1e-12:
            break
        x = x_new
    
    # Jacobian at fixed point
    J = compute_jacobian(C, x)
    
    # Solve J^T M J = M as a generalized eigenvalue problem
    # Vectorize: M has N*(N+1)/2 params
    # (J^T ⊗ J^T) vec(M) = vec(M)
    # [(J^T ⊗ J^T) - I] vec(M) = 0
    # Find null space
    
    # Use Kronecker product approach
    JJT = np.kron(J.T, J.T)
    A_mat = JJT - np.eye(N*N)
    
    # SVD to find null space
    U, s, Vt = np.linalg.svd(A_mat)
    
    # Null space vectors (smallest singular values)
    tol = 1e-6
    null_mask = s < tol
    null_count = np.sum(null_mask)
    
    if null_count == 0:
        # No exact null space; use the best approximate solution
        # The right singular vector corresponding to smallest singular value
        null_vec = Vt[-1]
    else:
        null_vec = Vt[-1]  # best approximate
    
    # Reconstruct M from vectorized form
    M_vec = null_vec.reshape(N, N)
    
    # Symmetrize
    M = (M_vec + M_vec.T) / 2
    
    # Also try: solve the discrete Lyapunov equation M = J M J^T
    # This is the standard form: M - J M J^T = 0
    # In continuous form: solve (I - J⊗J^T) vec(M) = 0
    
    # Test multiple null space vectors if they exist
    best_r2 = -np.inf
    best_M = M
    
    n_null = min(5, len(s))
    for i in range(n_null):
        if s[i] < 1.0:  # relaxed threshold
            vec = Vt[i]
            M_cand = vec.reshape(N, N)
            M_cand = (M_cand + M_cand.T) / 2
            
            # Test this M
            quad_vals = np.array([x_t @ M_cand @ x_t for x_t in xs])
            y = np.array(gamma_H_values)
            
            if np.var(quad_vals) < 1e-20:
                continue
            
            # Fit scalar
            A_reg = quad_vals.reshape(-1, 1)
            result = np.linalg.lstsq(A_reg, y, rcond=None)
            
            y_pred = A_reg @ result[0]
            ss_res = np.sum((y - y_pred)**2)
            ss_tot = np.sum((y - np.mean(y))**2)
            if ss_tot > 1e-20:
                r2 = 1.0 - ss_res / ss_tot
            else:
                r2 = 0.0
            
            if r2 > best_r2:
                best_r2 = r2
                best_M = M_cand
    
    # Also try: solve the full Lyapunov M = J^T M J using scipy
    # The continuous-time analog: J^T P + P J = -Q
    # For discrete: P = J^T P J + Q → P - J^T P J = Q
    try:
        # Check if spectral radius of J < 1
        sr = np.max(np.abs(np.linalg.eigvals(J)))
        if sr < 1:
            # Solve discrete Lyapunov: P = J^T P J + I
            # scipy wants: A P A^T + Q = P → P - A P A^T = Q
            P_lyap = solve_continuous_lyapunov(
                np.eye(N) - J,  # This is wrong signature, need different approach
                np.eye(N)
            )
        else:
            P_lyap = None
    except:
        P_lyap = None
    
    # Also compute M via the SDP relaxation
    # The contraction condition: J^T M J ≤ M (in Loewner order)
    # We parameterize M as a linear combination of basis matrices
    # and solve for the M that gives best fit to γ+H
    
    return {
        "name": "M from J^T M J = M (null space)",
        "r2": best_r2,
        "jacobian_spectral_radius": np.max(np.abs(np.linalg.eigvals(J))),
        "null_space_dim": int(null_count),
        "singular_values": s[:5].tolist(),
    }


def test_metric_sdp_fitted(C, xs, gamma_H_values):
    """
    H4-extended: Find M that minimizes |x^T M x - γ+H|² 
    subject to M satisfying the contraction inequality J^T M J ≼ M.
    
    This is the "best contraction metric" that explains the conservation.
    """
    N = len(C)
    n_steps = len(xs)
    
    # Find fixed point
    x = np.random.randn(N) * 0.1
    for _ in range(1000):
        x_new = np.tanh(C @ x)
        if np.linalg.norm(x_new - x) < 1e-12:
            break
        x = x_new
    
    J = compute_jacobian(C, x)
    
    # Compute Jacobian at MULTIPLE points along the trajectory for robustness
    jacobians = []
    for t in range(0, n_steps, max(1, n_steps // 10)):
        J_t = compute_jacobian(C, xs[t])
        jacobians.append(J_t)
    
    # Parameterize M by its N*(N+1)/2 free entries
    n_params = N * (N + 1) // 2
    
    idx_map = {}
    k = 0
    for i in range(N):
        for j in range(i, N):
            idx_map[(i, j)] = k
            k += 1
    
    def params_to_M(params):
        M = np.zeros((N, N))
        for i in range(N):
            for j in range(i, N):
                M[i, j] = params[idx_map[(i, j)]]
                M[j, i] = params[idx_map[(i, j)]]
        return M
    
    def M_to_params(M):
        params = np.zeros(n_params)
        for i in range(N):
            for j in range(i, N):
                params[idx_map[(i, j)]] = M[i, j]
        return params
    
    # Build feature matrix for γ+H = x^T M x
    Phi = np.zeros((n_steps, n_params))
    for t in range(n_steps):
        for i in range(N):
            for j in range(i, N):
                if i == j:
                    Phi[t, idx_map[(i, j)]] = xs[t, i]**2
                else:
                    Phi[t, idx_map[(i, j)]] = 2 * xs[t, i] * xs[t, j]
    
    y = np.array(gamma_H_values)
    
    # First: unconstrained fit (gives best possible R² for any quadratic form)
    result = np.linalg.lstsq(Phi, y, rcond=None)
    params_uncon = result[0]
    y_pred_uncon = Phi @ params_uncon
    ss_res = np.sum((y - y_pred_uncon)**2)
    ss_tot = np.sum((y - np.mean(y))**2)
    r2_uncon = 1.0 - ss_res / (ss_tot + 1e-30)
    M_uncon = params_to_M(params_uncon)
    
    # Second: fit M under contraction constraint J^T M J ≼ M
    # This is a semidefinite program. For tractability, we relax to:
    # J^T M J - M ≼ ε·I (allow small violation)
    # and minimize |Φ params - y|²
    
    # Use the contraction rate: λ_max(J^T M J M^{-1}) should be < 1
    # Simplified: we check if the unconstrained M satisfies the contraction condition
    
    # Check contraction for unconstrained M
    contraction_checks = []
    for J_t in jacobians:
        try:
            M_inv = np.linalg.pinv(M_uncon)
            contraction_matrix = J_t.T @ M_uncon @ J_t @ M_inv
            max_eig = np.max(np.real(np.linalg.eigvals(contraction_matrix)))
            contraction_checks.append(max_eig)
        except:
            contraction_checks.append(float('nan'))
    
    # Also check: J^T M J - M eigenvalues
    contraction_diff_eigs = []
    for J_t in jacobians:
        diff = J_t.T @ M_uncon @ J_t - M_uncon
        eigs = np.real(np.linalg.eigvals(diff))
        contraction_diff_eigs.append(np.max(eigs))
    
    return {
        "name": "M SDP-fitted (unconstrained P)",
        "r2_unconstrained": r2_uncon,
        "contraction_rate_max": max(contraction_checks) if contraction_checks else float('nan'),
        "contraction_diff_max": max(contraction_diff_eigs) if contraction_diff_eigs else float('nan'),
        "contraction_diff_mean": np.mean(contraction_diff_eigs) if contraction_diff_eigs else float('nan'),
        "is_contraction_metric": all(c < 1.0 + 1e-6 for c in contraction_checks if not np.isnan(c)),
        "P_positive_definite": bool(np.all(np.linalg.eigvals(M_uncon) > -1e-10)),
        "P_eigenvalues": np.sort(np.real(np.linalg.eigvals(M_uncon)))[::-1][:5].tolist(),
    }


def test_contraction_rate_predicts_conservation(C, xs, gamma_H_values):
    """
    Test whether the contraction rate predicts conservation quality.
    
    If P = M (contraction metric), then faster contraction → better conservation.
    """
    N = len(C)
    n_steps = len(xs)
    
    # Compute Jacobian at each timestep
    jacobians = [compute_jacobian(C, xs[t]) for t in range(n_steps)]
    
    # Contraction rate at each step: max |λ(J)|
    contraction_rates = [np.max(np.abs(np.linalg.eigvals(J))) for J in jacobians]
    
    # Conservation quality: |γ+H(t+1) - γ+H(t)|
    gh = np.array(gamma_H_values)
    conservation_error = np.abs(np.diff(gh))
    
    # Correlation between contraction rate and conservation error
    if np.std(contraction_rates[:-1]) > 1e-10 and np.std(conservation_error) > 1e-10:
        corr = np.corrcoef(contraction_rates[:-1], conservation_error)[0, 1]
    else:
        corr = float('nan')
    
    return {
        "mean_contraction_rate": float(np.mean(contraction_rates)),
        "std_contraction_rate": float(np.std(contraction_rates)),
        "mean_conservation_error": float(np.mean(conservation_error)),
        "correlation_contraction_vs_error": float(corr),
    }


def test_differential_contraction(C, xs, gamma_H_values):
    """
    Test the DIFFERENTIAL contraction condition from Lohmiller & Slotine.
    
    The system is contracting if there exists M ≻ 0 such that:
    J(x)^T M J(x) ≺ M for all x
    
    Equivalently: the induced norm ||J||_M < 1.
    
    If such an M exists and γ+H = x^T M x, that's the theorem.
    """
    N = len(C)
    n_steps = len(xs)
    
    # Compute Jacobians along trajectory
    jacobians = [compute_jacobian(C, xs[t]) for t in range(n_steps)]
    
    # For each candidate M, check contraction at all trajectory points
    candidates = {}
    
    # M = I
    I = np.eye(N)
    rates_I = [np.max(np.abs(np.linalg.eigvals(J))) for J in jacobians]
    candidates["I"] = {"mean_rate": np.mean(rates_I), "max_rate": max(rates_I), "is_contraction": max(rates_I) < 1.0}
    
    # M = C^T C
    CtC = C.T @ C
    try:
        CtC_inv_sqrt = np.linalg.inv(np.linalg.cholesky(CtC))
        rates_CtC = [np.max(np.abs(np.linalg.eigvals(CtC_inv_sqrt @ J @ np.linalg.cholesky(CtC)))) for J in jacobians]
        candidates["CtC"] = {"mean_rate": np.mean(rates_CtC), "max_rate": max(rates_CtC), "is_contraction": max(rates_CtC) < 1.0}
    except:
        candidates["CtC"] = {"mean_rate": float('nan'), "max_rate": float('nan'), "is_contraction": False}
    
    # M = (C^T C + I) / 2  (compromise)
    M_mid = (CtC + I) / 2
    try:
        L = np.linalg.cholesky(M_mid)
        Linv = np.linalg.inv(L)
        rates_mid = [np.max(np.abs(np.linalg.eigvals(Linv @ J @ L))) for J in jacobians]
        candidates["CtC_plus_I"] = {"mean_rate": np.mean(rates_mid), "max_rate": max(rates_mid), "is_contraction": max(rates_mid) < 1.0}
    except:
        candidates["CtC_plus_I"] = {"mean_rate": float('nan'), "max_rate": float('nan'), "is_contraction": False}
    
    # Is the system contracting in ANY metric?
    # Check: are all Jacobian eigenvalues < 1?
    all_rates = [np.max(np.abs(np.linalg.eigvals(J))) for J in jacobians]
    system_contracting = max(all_rates) < 1.0
    
    return {
        "system_contracting_in_euclidean": system_contracting,
        "max_jacobian_spectral_radius": max(all_rates),
        "mean_jacobian_spectral_radius": np.mean(all_rates),
        "candidates": candidates,
    }


def generate_coupling_matrix(N, matrix_type="random", scale=1.0):
    """Generate coupling matrix of specified type."""
    if matrix_type == "random":
        C = np.random.randn(N, N) / np.sqrt(N)
    elif matrix_type == "random_scaled":
        C = scale * np.random.randn(N, N) / np.sqrt(N)
    elif matrix_type == "hebbian":
        patterns = np.random.randn(N, 3)
        C = patterns @ patterns.T / N
        np.fill_diagonal(C, 0)
    elif matrix_type == "attention":
        Q = np.random.randn(N, N//2) / np.sqrt(N//2)
        K = np.random.randn(N, N//2) / np.sqrt(N//2)
        scores = Q @ K.T / np.sqrt(N//2)
        # Softmax row-stochastic
        exp_scores = np.exp(scores - scores.max(axis=1, keepdims=True))
        C = exp_scores / exp_scores.sum(axis=1, keepdims=True)
    elif matrix_type == "symmetric":
        A = np.random.randn(N, N) / np.sqrt(N)
        C = (A + A.T) / 2
    else:
        raise ValueError(f"Unknown matrix type: {matrix_type}")
    return C


# ─── Main Experiment ────────────────────────────────────────────────────────

def run_single_experiment(C, x0=None):
    """Run full contraction metric test for a single coupling matrix."""
    N = len(C)
    if x0 is None:
        x0 = np.random.randn(N) * 0.5
    
    # Evolve
    xs = evolve_tanh(C, x0, N_STEPS)
    
    # Compute γ+H at each timestep (using fixed C eigenvalues)
    eigenvalues = np.linalg.eigvals(C)
    abs_evals = np.sort(np.abs(eigenvalues))[::-1]
    gamma = abs_evals[0] - abs_evals[1] if N > 1 else 0.0
    weights = abs_evals**2 / np.sum(abs_evals**2)
    H = -np.sum(weights * np.log(weights + 1e-30))
    gh_value = gamma + H
    
    # γ+H is constant (fixed C), so we need a state-dependent version
    # Based on insights: the conservation is γ+H = x^T P x where P is fitted
    # So γ+H must vary with state — meaning it must be computed from a state-dependent quantity
    
    # The ACTUAL conserved quantity from the previous experiments:
    # It was x^T P x that matched γ+H with R²=1.0
    # The γ+H was computed from state-dependent coupling C(x)
    
    # For the contraction metric test, we should:
    # 1. Compute x^T M x for various M candidates
    # 2. See which one is conserved along the trajectory
    # 3. Compare conservation quality
    
    # Conservation metric: how well is x^T M x conserved?
    def conservation_quality(M):
        quad_vals = np.array([x @ M @ x for x in xs])
        cv = np.std(quad_vals) / (np.mean(np.abs(quad_vals)) + 1e-30)
        return cv
    
    # Also test: fit P from trajectory, then check if P matches any candidate M
    
    # Compute various x^T M x
    I = np.eye(N)
    CtC = C.T @ C
    
    results = {}
    
    # H1: M = I
    cv_I = conservation_quality(I)
    quad_I = np.array([x @ x for x in xs])
    results["M_I"] = {
        "cv": cv_I,
        "mean": float(np.mean(quad_I)),
        "std": float(np.std(quad_I)),
    }
    
    # H2: M = C^T C
    cv_CtC = conservation_quality(CtC)
    quad_CtC = np.array([x @ CtC @ x for x in xs])
    results["M_CtC"] = {
        "cv": cv_CtC,
        "mean": float(np.mean(quad_CtC)),
        "std": float(np.std(quad_CtC)),
    }
    
    # H3: M = α·C^T C + β·I (optimize α, β for minimum CV)
    def cv_generalized(params):
        alpha, beta = params
        M = alpha * CtC + beta * I
        quad_vals = np.array([x @ M @ x for x in xs])
        return np.std(quad_vals) / (np.mean(np.abs(quad_vals)) + 1e-30)
    
    from scipy.optimize import minimize as sp_minimize
    res_opt = sp_minimize(cv_generalized, [1.0, 1.0], method='Nelder-Mead', 
                          options={'xatol': 1e-10, 'fatol': 1e-14, 'maxiter': 10000})
    alpha_opt, beta_opt = res_opt.x
    M_opt = alpha_opt * CtC + beta_opt * I
    cv_opt = conservation_quality(M_opt)
    quad_opt = np.array([x @ M_opt @ x for x in xs])
    results["M_generalized"] = {
        "cv": cv_opt,
        "alpha": float(alpha_opt),
        "beta": float(beta_opt),
        "mean": float(np.mean(quad_opt)),
        "std": float(np.std(quad_opt)),
    }
    
    # H4: M from J^T M J = M at fixed point
    x_fp = np.random.randn(N) * 0.1
    for _ in range(2000):
        x_fp_new = np.tanh(C @ x_fp)
        if np.linalg.norm(x_fp_new - x_fp) < 1e-14:
            break
        x_fp = x_fp_new
    
    J_fp = compute_jacobian(C, x_fp)
    
    # Solve (J^T ⊗ J^T - I) vec(M) = 0
    JJT = np.kron(J_fp.T, J_fp.T)
    A_mat = JJT - np.eye(N*N)
    U_svd, s_svd, Vt_svd = np.linalg.svd(A_mat)
    
    # Test null space vectors as candidates for M
    best_null_cv = float('inf')
    best_null_M = None
    for i in range(min(10, len(s_svd))):
        vec = Vt_svd[i]
        M_cand = vec.reshape(N, N)
        M_cand = (M_cand + M_cand.T) / 2
        quad_cand = np.array([x @ M_cand @ x for x in xs])
        if np.mean(np.abs(quad_cand)) < 1e-30:
            continue
        cv_cand = np.std(quad_cand) / np.mean(np.abs(quad_cand))
        if cv_cand < best_null_cv:
            best_null_cv = cv_cand
            best_null_M = M_cand
    
    results["M_nullspace"] = {
        "cv": best_null_cv,
        "singular_values_top5": s_svd[:5].tolist(),
        "null_dim_approx": int(np.sum(s_svd < 0.01)),
    }
    
    # H5: Full unconstrained P (best possible quadratic conservation)
    # Fit P to minimize CV(x^T P x) — equivalently, fit to γ+H if we had it
    # But since γ+H is constant for fixed C, instead we test:
    # "What is the best quadratic form that is conserved along the trajectory?"
    
    # This means: find P such that x(t)^T P x(t) has minimum CV
    # This is equivalent to finding P in the null space of the operator
    # [x(t+1)x(t+1)^T - x(t)x(t)^T]
    
    # Build the conservation constraint matrix
    # For each t: x(t+1)^T P x(t+1) - x(t)^T P x(t) = 0
    # vec: (x(t+1)x(t+1)^T - x(t)x(t)^T) · vec(P) = 0
    
    n_params = N * (N + 1) // 2
    idx_map = {}
    k = 0
    for i in range(N):
        for j in range(i, N):
            idx_map[(i, j)] = k
            k += 1
    
    def symmetric_to_params(S):
        params = np.zeros(n_params)
        for i in range(N):
            for j in range(i, N):
                params[idx_map[(i, j)]] = S[i, j]
        return params
    
    # Conservation constraints: one per timestep
    cons_matrix = np.zeros((N_STEPS, n_params))
    for t in range(N_STEPS):
        diff = np.outer(xs[t+1], xs[t+1]) - np.outer(xs[t], xs[t])
        # Only use symmetric part
        diff = (diff + diff.T) / 2
        cons_matrix[t] = symmetric_to_params(diff)
    
    # Find null space of conservation matrix
    U_cons, s_cons, Vt_cons = np.linalg.svd(cons_matrix, full_matrices=True)
    
    # Null space = rows of Vt corresponding to zero singular values
    tol_cons = 1e-8 * max(s_cons[0] if len(s_cons) > 0 else 1, 1)
    null_dim = int(np.sum(s_cons < tol_cons))
    
    # Pick the null space vector that gives the most "interesting" (non-trivial) M
    best_cons_cv = float('inf')
    best_cons_M = None
    
    for i in range(n_params):
        if i < len(s_cons) and s_cons[i] < tol_cons:
            params = Vt_cons[i]
        elif i >= len(s_cons):
            params = Vt_cons[i]
        else:
            continue
        
        M_cand = np.zeros((N, N))
        for ii in range(N):
            for jj in range(ii, N):
                M_cand[ii, jj] = params[idx_map[(ii, jj)]]
                M_cand[jj, ii] = params[idx_map[(ii, jj)]]
        
        quad_cand = np.array([x @ M_cand @ x for x in xs])
        if np.mean(np.abs(quad_cand)) < 1e-20:
            continue
        
        cv_cand = np.std(quad_cand) / np.mean(np.abs(quad_cand))
        if cv_cand < best_cons_cv:
            best_cons_cv = cv_cand
            best_cons_M = M_cand
    
    results["M_conservation_nullspace"] = {
        "cv": best_cons_cv,
        "null_dim": null_dim,
        "n_params": n_params,
        "top_singular_values": s_cons[:5].tolist() if len(s_cons) > 0 else [],
    }
    
    # Compare: is the best conservation metric related to C?
    comparisons = {}
    if best_cons_M is not None:
        # Check if P ∝ C^T C
        P_flat = best_cons_M.flatten()
        CtC_flat = CtC.flatten()
        corr_CtC = np.corrcoef(P_flat, CtC_flat)[0, 1] if np.std(P_flat) > 1e-20 else float('nan')
        
        # Check if P ∝ I
        I_flat = I.flatten()
        corr_I = np.corrcoef(P_flat, I_flat)[0, 1] if np.std(P_flat) > 1e-20 else float('nan')
        
        # Check commutator [P, C]
        comm = best_cons_M @ C - C @ best_cons_M
        comm_norm = np.linalg.norm(comm) / (np.linalg.norm(best_cons_M) * np.linalg.norm(C) + 1e-30)
        
        # Check if P is a polynomial in C: P = a0*I + a1*C + a2*C^T*C + ...
        # Simple test: is P in the span of {I, C, C^T, C^T C, C C^T}?
        basis_matrices = [I, C, C.T, CtC, C @ C.T]
        basis_flat = np.column_stack([m.flatten() for m in basis_matrices])
        
        result_poly = np.linalg.lstsq(basis_flat, P_flat, rcond=None)
        residual_poly = np.linalg.norm(P_flat - basis_flat @ result_poly[0]) / (np.linalg.norm(P_flat) + 1e-30)
        
        comparisons = {
            "corr_with_CtC": float(corr_CtC),
            "corr_with_I": float(corr_I),
            "commutator_norm": float(comm_norm),
            "polynomial_residual": float(residual_poly),
            "poly_coeffs": result_poly[0].tolist(),
        }
    
    # Contraction rate vs conservation quality
    contraction_results = test_contraction_rate_predicts_conservation(C, xs, [0]*N_STEPS)  # dummy gh
    
    # Differential contraction test
    diff_contraction = test_differential_contraction(C, xs, [0]*N_STEPS)
    
    return {
        "matrix_info": {
            "N": N,
            "spectral_radius": float(np.max(np.abs(np.linalg.eigvals(C)))),
            "det_C": float(np.abs(np.linalg.det(C))),
            "norm_C": float(np.linalg.norm(C)),
        },
        "fixed_point_found": bool(np.linalg.norm(np.tanh(C @ x_fp) - x_fp) < 1e-8),
        "jacobian_sr_at_fp": float(np.max(np.abs(np.linalg.eigvals(J_fp)))),
        "metric_tests": results,
        "comparisons": comparisons,
        "contraction_analysis": {
            "jacobian_sr_along_traj": contraction_results["mean_contraction_rate"],
            "system_contracting": diff_contraction["system_contracting_in_euclidean"],
            "max_jacobian_sr": diff_contraction["max_jacobian_spectral_radius"],
        },
    }


def main():
    print("=" * 70)
    print("CONTRACTION METRIC EXPERIMENT")
    print("Testing: Is P = M (contraction metric from Lohmiller & Slotine)?")
    print("=" * 70)
    
    all_results = {}
    
    matrix_types = ["random", "random_scaled", "hebbian", "attention", "symmetric"]
    scales = [0.5, 1.0, 2.0, 5.0]
    
    # Experiment 1: Test all metric candidates across architectures
    print("\n" + "=" * 70)
    print("EXPERIMENT 1: Metric Candidates vs Architecture")
    print("=" * 70)
    
    exp1_results = {}
    for mtype in matrix_types:
        print(f"\n  Matrix type: {mtype}")
        cvs = {"M_I": [], "M_CtC": [], "M_generalized": [], "M_nullspace": [], "M_conservation_nullspace": []}
        
        for trial in range(N_SAMPLES):
            scale = 1.5 if mtype == "random_scaled" else 1.0
            C = generate_coupling_matrix(N_AGENTS, mtype, scale)
            result = run_single_experiment(C)
            
            for key in cvs:
                if key in result["metric_tests"]:
                    cvs[key].append(result["metric_tests"][key]["cv"])
        
        exp1_results[mtype] = {key: {"mean_cv": float(np.mean(vals)), "std_cv": float(np.std(vals))} 
                               for key, vals in cvs.items() if vals}
        
        print(f"    M=I:          CV = {np.mean(cvs['M_I']):.6f} ± {np.std(cvs['M_I']):.6f}")
        print(f"    M=C^TC:       CV = {np.mean(cvs['M_CtC']):.6f} ± {np.std(cvs['M_CtC']):.6f}")
        print(f"    M=αC^TC+βI:   CV = {np.mean(cvs['M_generalized']):.6f} ± {np.std(cvs['M_generalized']):.6f}")
        print(f"    M=null(J^TMJ):CV = {np.mean(cvs['M_nullspace']):.6f} ± {np.std(cvs['M_nullspace']):.6f}")
        print(f"    M=cons_null:   CV = {np.mean(cvs['M_conservation_nullspace']):.6f} ± {np.std(cvs['M_conservation_nullspace']):.6f}")
    
    all_results["exp1"] = exp1_results
    
    # Experiment 2: Scale dependence — does contraction rate predict conservation?
    print("\n" + "=" * 70)
    print("EXPERIMENT 2: Scale Dependence (Contraction Rate vs Conservation)")
    print("=" * 70)
    
    exp2_results = {}
    for scale in scales:
        print(f"\n  Scale = {scale}")
        cvs = {"M_I": [], "M_CtC": [], "M_generalized": []}
        jacobian_srs = []
        system_contracting = []
        
        for trial in range(N_SAMPLES):
            C = scale * np.random.randn(N_AGENTS, N_AGENTS) / np.sqrt(N_AGENTS)
            result = run_single_experiment(C)
            
            for key in cvs:
                if key in result["metric_tests"]:
                    cvs[key].append(result["metric_tests"][key]["cv"])
            jacobian_srs.append(result["contraction_analysis"]["jacobian_sr_along_traj"])
            system_contracting.append(result["contraction_analysis"]["system_contracting"])
        
        exp2_results[f"scale_{scale}"] = {
            "scale": scale,
            "mean_jacobian_sr": float(np.mean(jacobian_srs)),
            "fraction_contracting": float(np.mean(system_contracting)),
            "metric_cvs": {key: {"mean": float(np.mean(v)), "std": float(np.std(v))} 
                          for key, v in cvs.items() if v},
        }
        
        print(f"    Jacobian SR: {np.mean(jacobian_srs):.4f}")
        print(f"    Contracting: {np.mean(system_contracting)*100:.0f}%")
        for key, v in cvs.items():
            if v:
                print(f"    {key}: CV = {np.mean(v):.6f}")
    
    all_results["exp2"] = exp2_results
    
    # Experiment 3: P structure analysis
    print("\n" + "=" * 70)
    print("EXPERIMENT 3: Structure of Best-Fit P Matrix")
    print("=" * 70)
    
    exp3_results = []
    for trial in range(20):
        C = np.random.randn(N_AGENTS, N_AGENTS) / np.sqrt(N_AGENTS) * 1.5
        result = run_single_experiment(C)
        
        if result["comparisons"]:
            comp = result["comparisons"]
            entry = {
                "corr_CtC": comp["corr_with_CtC"],
                "corr_I": comp["corr_with_I"],
                "commutator": comp["commutator_norm"],
                "poly_residual": comp["polynomial_residual"],
                "jacobian_sr": result["jacobian_sr_at_fp"],
            }
            exp3_results.append(entry)
            
            print(f"  Trial {trial}: corr(C^TC)={comp['corr_with_CtC']:.4f}, "
                  f"corr(I)={comp['corr_with_I']:.4f}, "
                  f"|[P,C]|={comp['commutator_norm']:.4f}, "
                  f"poly_res={comp['polynomial_residual']:.4f}")
    
    all_results["exp3"] = exp3_results
    
    # ─── Summary ────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    print("\nBest metric candidate (lowest mean CV across all architectures):")
    for mtype, metrics in exp1_results.items():
        best_key = min(metrics, key=lambda k: metrics[k]["mean_cv"])
        print(f"  {mtype:15s}: {best_key:25s} CV={metrics[best_key]['mean_cv']:.6f}")
    
    print("\nScale dependence:")
    for scale_key, data in exp2_results.items():
        best_metric = min(data["metric_cvs"].items(), key=lambda x: x[1]["mean"])
        print(f"  scale={data['scale']:.1f}: SR={data['mean_jacobian_sr']:.4f}, "
              f"best={best_metric[0]} CV={best_metric[1]['mean']:.6f}, "
              f"contracting={data['fraction_contracting']*100:.0f}%")
    
    print("\nP structure (averaged over trials):")
    if exp3_results:
        print(f"  corr(P, C^TC) = {np.mean([r['corr_CtC'] for r in exp3_results]):.4f}")
        print(f"  corr(P, I)    = {np.mean([r['corr_I'] for r in exp3_results]):.4f}")
        print(f"  |[P, C]|      = {np.mean([r['commutator'] for r in exp3_results]):.4f}")
        print(f"  poly residual = {np.mean([r['poly_residual'] for r in exp3_results]):.4f}")
    
    # ─── Verdict ────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("VERDICT")
    print("=" * 70)
    
    # Check if any metric gives CV ≈ 0 (perfect conservation)
    best_overall = float('inf')
    best_name = ""
    for mtype, metrics in exp1_results.items():
        for key, vals in metrics.items():
            if vals["mean_cv"] < best_overall:
                best_overall = vals["mean_cv"]
                best_name = f"{key} ({mtype})"
    
    print(f"\nBest overall metric: {best_name}")
    print(f"  Mean CV: {best_overall:.6f}")
    
    if best_overall < 1e-6:
        print("\n★ PERFECT CONSERVATION FOUND — P is a conserved quadratic form!")
    elif best_overall < 0.01:
        print("\n✓ Near-perfect conservation — strong evidence for quadratic conservation")
    elif best_overall < 0.05:
        print("\n~ Moderate conservation — the relationship is approximate")
    else:
        print("\n✗ No strong conservation — the contraction metric hypothesis needs revision")
    
    # Check contraction rate prediction
    scales_list = list(exp2_results.values())
    if len(scales_list) >= 3:
        srs = [s["mean_jacobian_sr"] for s in scales_list]
        cvs_M_I = [s["metric_cvs"]["M_I"]["mean"] for s in scales_list]
        if np.std(srs) > 0.01 and np.std(cvs_M_I) > 1e-6:
            corr_scale = np.corrcoef(srs, cvs_M_I)[0, 1]
            print(f"\nContraction rate vs CV(‖x‖²) correlation: {corr_scale:.4f}")
            if corr_scale < -0.5:
                print("  → Strong negative correlation: FASTER contraction → BETTER conservation")
                print("  → SUPPORTS contraction metric hypothesis")
            elif corr_scale > 0.5:
                print("  → Positive correlation: faster contraction → WORSE conservation")
                print("  → CONTRADICTS contraction metric hypothesis")
            else:
                print("  → Weak correlation: contraction rate doesn't predict conservation")
    
    # Check if P ≈ C^T C
    if exp3_results:
        mean_corr_CtC = np.mean([r['corr_CtC'] for r in exp3_results])
        if abs(mean_corr_CtC) > 0.9:
            print(f"\n★ P is highly correlated with C^T C (r={mean_corr_CtC:.4f})")
            print("  → P ≈ C^T C — the contraction metric IS the coupling metric!")
        elif abs(mean_corr_CtC) > 0.5:
            print(f"\n~ P is moderately correlated with C^T C (r={mean_corr_CtC:.4f})")
        else:
            print(f"\n✗ P is NOT correlated with C^T C (r={mean_corr_CtC:.4f})")
    
    # Save results
    output_dir = "/home/phoenix/.openclaw/workspace/experiments/gpu-loop/cycle-008"
    os.makedirs(output_dir, exist_ok=True)
    
    with open(os.path.join(output_dir, "contraction_metric_results.json"), "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print(f"\nResults saved to {output_dir}/contraction_metric_results.json")
    
    return all_results


if __name__ == "__main__":
    results = main()
