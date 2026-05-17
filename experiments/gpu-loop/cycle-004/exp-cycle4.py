#!/usr/bin/env python3
"""
GPU Constraint Experiment Loop — Cycle 4
Model: Seed-2.0-mini (second rotation)
Focus: NONLINEAR coupled dynamics, Tr(C²) conservation, two-moment constraint, Lyapunov connection

KEY CHANGES FROM CYCLE 3:
- Use tanh-coupled dynamics: x_{t+1} = tanh(C @ x_t), NOT power iteration
- Measure Tr(C²) alongside γ+H at every timestep
- Test whether Tr(C²) stability predicts γ+H conservation
- Try to BREAK conservation by forcing Tr(C²) to vary
- Connect to Lyapunov equation (A^T P A = P)
"""

import numpy as np
from scipy.linalg import svdvals, sqrtm
from scipy.stats import pearsonr
import json
import os
import warnings
warnings.filterwarnings('ignore')

np.random.seed(42)

RESULTS_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def spectral_gap(C):
    """Compute spectral gap (largest - second largest singular value)."""
    s = svdvals(C)
    s_sorted = np.sort(s)[::-1]
    if len(s_sorted) > 1:
        return float(s_sorted[0] - s_sorted[1])
    return float(s_sorted[0])

def participation_entropy(x):
    """Compute participation entropy of state vector."""
    p = np.abs(x) ** 2
    p = p / (np.sum(p) + 1e-15)
    p = p[p > 1e-15]
    H = -np.sum(p * np.log(p + 1e-15))
    return float(H)

def make_random_coupling(N, scale=1.0):
    """GOE random coupling matrix."""
    C = np.random.randn(N, N) * scale / np.sqrt(N)
    C = (C + C.T) / 2  # Symmetrize
    np.fill_diagonal(C, 1.0)
    return C

def make_hebbian_coupling(N, n_patterns=5):
    """Hebbian coupling from stored patterns."""
    patterns = np.random.choice([-1, 1], size=(n_patterns, N))
    C = patterns.T @ patterns / N
    np.fill_diagonal(C, 1.0)
    return C.astype(float)

def make_attention_coupling(N, temperature=1.0):
    """Attention-like coupling (row-stochastic softmax)."""
    Q = np.random.randn(N, N) * 0.5
    K = np.random.randn(N, N) * 0.5
    scores = Q @ K.T / temperature
    # Row-stochastic softmax
    scores_exp = np.exp(scores - scores.max(axis=1, keepdims=True))
    C = scores_exp / scores_exp.sum(axis=1, keepdims=True)
    np.fill_diagonal(C, 1.0)
    return C

def trace_C2(C):
    """Compute Tr(C^2) = sum of squared eigenvalues."""
    eigvals = np.linalg.eigvalsh(C)
    return float(np.sum(eigvals**2))

def trace_C(C):
    """Compute Tr(C)."""
    return float(np.trace(C))

def run_nonlinear_dynamics(C, x0, n_steps=200, coupling_fn='tanh'):
    """
    Run nonlinear coupled dynamics.
    x_{t+1} = f(C @ x_t) where f is the coupling function.
    
    Returns trajectory of: x, gamma, H, gamma+H, Tr(C), Tr(C²), eigenvalues
    """
    N = C.shape[0]
    x = x0.copy()
    
    trajectory = {
        'gamma': [],
        'H': [],
        'gamma_H': [],
        'tr_C': [],
        'tr_C2': [],
        'x_norm': [],
        'x_entropy': [],
    }
    
    eigvals_C = np.linalg.eigvalsh(C)
    
    for t in range(n_steps):
        # Compute quantities before update
        s = svdvals(np.outer(x, x))
        gamma = spectral_gap(np.outer(x, x))
        H = participation_entropy(x)
        
        trajectory['gamma'].append(gamma)
        trajectory['H'].append(H)
        trajectory['gamma_H'].append(gamma + H)
        trajectory['tr_C'].append(trace_C(C))
        trajectory['tr_C2'].append(trace_C2(C))
        trajectory['x_norm'].append(float(np.linalg.norm(x)))
        trajectory['x_entropy'].append(H)
        
        # Nonlinear update
        coupling = C @ x
        if coupling_fn == 'tanh':
            x = np.tanh(coupling)
        elif coupling_fn == 'sigmoid':
            x = 1.0 / (1.0 + np.exp(-coupling))
        elif coupling_fn == 'relu':
            x = np.maximum(0, coupling)
        elif coupling_fn == 'power':
            # Power iteration (baseline comparison)
            x = coupling
            x = x / (np.linalg.norm(x) + 1e-15)
        elif coupling_fn == 'tanh_scaled':
            # Scale-preserving tanh
            norm_before = np.linalg.norm(x)
            x = np.tanh(coupling)
            x = x / (np.linalg.norm(x) + 1e-15) * norm_before
        elif coupling_fn == 'multi_agent':
            # Multi-agent: each agent has own state, nonlinear interaction
            # x_i(t+1) = tanh(sum_j C_ij * x_j(t)) + 0.1 * noise
            x = np.tanh(coupling) + 0.05 * np.random.randn(N)
    
    return trajectory

def compute_cv(values):
    """Coefficient of variation."""
    v = np.array(values)
    if np.mean(v) == 0:
        return 0.0
    return float(np.std(v) / (np.abs(np.mean(v)) + 1e-15))

def compute_correlation(x, y):
    """Pearson correlation."""
    x, y = np.array(x), np.array(y)
    if np.std(x) < 1e-10 or np.std(y) < 1e-10:
        return 0.0
    return float(pearsonr(x, y)[0])


# ============================================================
# EXPERIMENT 1: Nonlinear Dynamics × Architecture
# ============================================================
def exp1_nonlinear_architecture():
    """
    Test Tr(C²) conservation under TANH nonlinear dynamics.
    Compare: tanh, power iteration (baseline), multi-agent.
    Measure γ+H and Tr(C²) simultaneously.
    """
    print("=" * 70)
    print("EXP-1: Nonlinear Dynamics × Architecture × Tr(C²)")
    print("=" * 70)
    
    N = 20
    n_steps = 200
    n_samples = 30
    
    architectures = {
        'random': lambda: make_random_coupling(N),
        'hebbian': lambda: make_hebbian_coupling(N),
        'attention': lambda: make_attention_coupling(N),
    }
    
    dynamics = ['tanh', 'power', 'multi_agent']
    
    results = {}
    
    for arch_name, arch_fn in architectures.items():
        for dyn in dynamics:
            cv_gh_list = []
            cv_trC2_list = []
            corr_gh_trC2_list = []
            gamma_H_corr_list = []  # γ-H anti-correlation
            gh_means = []
            trC2_means = []
            final_x_entropy_list = []
            
            for sample in range(n_samples):
                C = arch_fn()
                x0 = np.random.randn(N)
                x0 = x0 / np.linalg.norm(x0)
                
                traj = run_nonlinear_dynamics(C, x0, n_steps, dyn)
                
                # Skip first 5 steps (transient)
                gh = traj['gamma_H'][5:]
                trC2 = traj['tr_C2'][5:]
                gammas = traj['gamma'][5:]
                Hs = traj['H'][5:]
                
                cv_gh = compute_cv(gh)
                cv_trC2 = compute_cv(trC2)
                corr_gh_trC2 = compute_correlation(gh, trC2)
                gamma_H_corr = compute_correlation(gammas, Hs)
                
                cv_gh_list.append(cv_gh)
                cv_trC2_list.append(cv_trC2)
                corr_gh_trC2_list.append(corr_gh_trC2)
                gamma_H_corr_list.append(gamma_H_corr)
                gh_means.append(np.mean(gh))
                trC2_means.append(np.mean(trC2))
                final_x_entropy_list.append(traj['x_entropy'][-1])
            
            key = f"{arch_name}_{dyn}"
            results[key] = {
                'architecture': arch_name,
                'dynamics': dyn,
                'cv_gh_mean': float(np.mean(cv_gh_list)),
                'cv_gh_std': float(np.std(cv_gh_list)),
                'cv_trC2_mean': float(np.mean(cv_trC2_list)),
                'cv_trC2_std': float(np.std(cv_trC2_list)),
                'corr_gh_trC2': float(np.mean(corr_gh_trC2_list)),
                'gamma_H_corr': float(np.mean(gamma_H_corr_list)),
                'gamma_H_corr_std': float(np.std(gamma_H_corr_list)),
                'gh_mean': float(np.mean(gh_means)),
                'trC2_mean': float(np.mean(trC2_means)),
                'final_entropy_mean': float(np.mean(final_x_entropy_list)),
            }
            
            print(f"  {key:30s} | CV(γ+H)={results[key]['cv_gh_mean']:.4f}±{results[key]['cv_gh_std']:.4f} | "
                  f"CV(Tr(C²))={results[key]['cv_trC2_mean']:.4f}±{results[key]['cv_trC2_std']:.4f} | "
                  f"r(γ,H)={results[key]['gamma_H_corr']:.3f}±{results[key]['gamma_H_corr_std']:.3f} | "
                  f"r(γ+H,TrC²)={results[key]['corr_gh_trC2']:.3f}")
    
    return results


# ============================================================
# EXPERIMENT 2: Two-Moment Constraint Test
# ============================================================
def exp2_two_moment():
    """
    Test whether BOTH Tr(C) and Tr(C²) are needed to predict γ+H.
    
    Method: Deliberately VARY Tr(C) and Tr(C²) independently and see 
    if γ+H tracks their joint variation.
    
    Approach: Use a coupling matrix that evolves over time:
    C(t) = C0 + delta * sin(omega * t) * E
    where E is a perturbation matrix.
    
    Test cases:
    1. Vary Tr(C) but keep Tr(C²) fixed
    2. Vary Tr(C²) but keep Tr(C) fixed
    3. Vary both independently
    """
    print("\n" + "=" * 70)
    print("EXP-2: Two-Moment Constraint Test")
    print("=" * 70)
    
    N = 20
    n_steps = 200
    
    def run_with_evolving_C(C0, perturbation_fn, n_steps=200):
        """Run dynamics where C evolves according to perturbation_fn."""
        x = np.random.randn(N)
        x = x / np.linalg.norm(x)
        
        tr_C_vals = []
        tr_C2_vals = []
        gh_vals = []
        gamma_vals = []
        H_vals = []
        
        for t in range(n_steps):
            C = perturbation_fn(C0, t)
            
            gamma = spectral_gap(np.outer(x, x))
            H = participation_entropy(x)
            
            tr_C_vals.append(trace_C(C))
            tr_C2_vals.append(trace_C2(C))
            gh_vals.append(gamma + H)
            gamma_vals.append(gamma)
            H_vals.append(H)
            
            # tanh dynamics with evolving C
            x = np.tanh(C @ x)
        
        return {
            'tr_C': tr_C_vals,
            'tr_C2': tr_C2_vals,
            'gamma_H': gh_vals,
            'gamma': gamma_vals,
            'H': H_vals,
        }
    
    C0 = make_attention_coupling(N)
    
    # Perturbation that varies Tr(C) but not Tr(C²)
    E_trace = np.eye(N) * 0.1  # Only affects diagonal = Tr(C)
    
    # Perturbation that varies Tr(C²) but not Tr(C)
    E_offdiag = np.random.randn(N, N)
    E_offdiag = (E_offdiag - E_offdiag.T) / 2  # Skew-symmetric → Tr = 0
    np.fill_diagonal(E_offdiag, 0)
    E_offdiag = E_offdiag * 0.1
    
    # Perturbation that varies both
    E_both = np.random.randn(N, N) * 0.1
    E_both = (E_both + E_both.T) / 2
    
    configs = {
        'vary_TrC_only': lambda C, t: C + np.sin(t * 0.1) * E_trace,
        'vary_TrC2_only': lambda C, t: C + np.sin(t * 0.1) * E_offdiag,
        'vary_both': lambda C, t: C + np.sin(t * 0.1) * E_both,
        'static': lambda C, t: C,
    }
    
    results = {}
    n_reps = 15
    
    for config_name, perturb_fn in configs.items():
        r2_trC = []
        r2_trC2 = []
        r2_both = []
        cv_gh = []
        gh_trC2_corr = []
        
        for rep in range(n_reps):
            data = run_with_evolving_C(C0, perturb_fn, n_steps)
            
            gh = np.array(data['gamma_H'][5:])
            trC = np.array(data['tr_C'][5:])
            trC2 = np.array(data['tr_C2'][5:])
            
            cv_gh.append(compute_cv(gh))
            gh_trC2_corr.append(compute_correlation(gh, trC2))
            
            # Regression: γ+H ~ Tr(C)
            if np.std(trC) > 1e-10:
                from numpy.polynomial import polynomial as P
                coeffs = np.polyfit(trC, gh, 1)
                pred = np.polyval(coeffs, trC)
                ss_res = np.sum((gh - pred)**2)
                ss_tot = np.sum((gh - np.mean(gh))**2)
                r2_trC.append(1 - ss_res / (ss_tot + 1e-15))
            else:
                r2_trC.append(0.0)
            
            # Regression: γ+H ~ Tr(C²)
            if np.std(trC2) > 1e-10:
                coeffs = np.polyfit(trC2, gh, 1)
                pred = np.polyval(coeffs, trC2)
                ss_res = np.sum((gh - pred)**2)
                ss_tot = np.sum((gh - np.mean(gh))**2)
                r2_trC2.append(1 - ss_res / (ss_tot + 1e-15))
            else:
                r2_trC2.append(0.0)
            
            # Regression: γ+H ~ Tr(C) + Tr(C²)
            if np.std(trC) > 1e-10 and np.std(trC2) > 1e-10:
                X = np.column_stack([trC, trC2, np.ones(len(trC))])
                try:
                    beta = np.linalg.lstsq(X, gh, rcond=None)[0]
                    pred = X @ beta
                    ss_res = np.sum((gh - pred)**2)
                    ss_tot = np.sum((gh - np.mean(gh))**2)
                    r2_both.append(1 - ss_res / (ss_tot + 1e-15))
                except:
                    r2_both.append(0.0)
            else:
                r2_both.append(0.0)
        
        results[config_name] = {
            'cv_gh': float(np.mean(cv_gh)),
            'R2_TrC': float(np.mean(r2_trC)),
            'R2_TrC2': float(np.mean(r2_trC2)),
            'R2_both': float(np.mean(r2_both)),
            'corr_gh_trC2': float(np.mean(gh_trC2_corr)),
        }
        
        print(f"  {config_name:20s} | CV(γ+H)={results[config_name]['cv_gh']:.4f} | "
              f"R²(TrC→γ+H)={results[config_name]['R2_TrC']:.3f} | "
              f"R²(TrC²→γ+H)={results[config_name]['R2_TrC2']:.3f} | "
              f"R²(both→γ+H)={results[config_name]['R2_both']:.3f}")
    
    return results


# ============================================================
# EXPERIMENT 3: Break Conservation on Purpose
# ============================================================
def exp3_break_conservation():
    """
    Try to BREAK γ+H conservation by:
    1. Large coupling strength (push tanh into saturation)
    2. Rapidly time-varying coupling
    3. Eigenvalue injection (force Tr(C²) to oscillate)
    4. Asymmetric (non-symmetric) coupling matrices
    5. Add structured noise that targets eigenvalue spread
    """
    print("\n" + "=" * 70)
    print("EXP-3: Break Conservation on Purpose")
    print("=" * 70)
    
    N = 20
    n_steps = 200
    n_reps = 15
    
    configs = {
        'baseline': {'scale': 1.0, 'symmetric': True, 'noise': 0.0, 'evolving': False},
        'strong_coupling': {'scale': 5.0, 'symmetric': True, 'noise': 0.0, 'evolving': False},
        'very_strong': {'scale': 20.0, 'symmetric': True, 'noise': 0.0, 'evolving': False},
        'asymmetric': {'scale': 1.0, 'symmetric': False, 'noise': 0.0, 'evolving': False},
        'noisy': {'scale': 1.0, 'symmetric': True, 'noise': 0.3, 'evolving': False},
        'evolving_fast': {'scale': 1.0, 'symmetric': True, 'noise': 0.0, 'evolving': True, 'omega': 0.5},
        'evolving_slow': {'scale': 1.0, 'symmetric': True, 'noise': 0.0, 'evolving': True, 'omega': 0.02},
        'eigenvalue_inject': {'scale': 1.0, 'symmetric': True, 'noise': 0.0, 'evolving': False, 'inject_eig': True},
    }
    
    results = {}
    
    for config_name, cfg in configs.items():
        cv_gh_list = []
        cv_trC2_list = []
        gamma_H_corr_list = []
        gh_drift_list = []
        trC2_drift_list = []
        
        for rep in range(n_reps):
            # Build coupling matrix
            C = make_attention_coupling(N)
            C = C * cfg.get('scale', 1.0)
            
            if not cfg.get('symmetric', True):
                # Add asymmetric perturbation
                C = C + 0.5 * np.random.randn(N, N)
            
            np.fill_diagonal(C, 1.0)
            
            x0 = np.random.randn(N)
            x0 = x0 / np.linalg.norm(x0)
            x = x0.copy()
            
            gh_traj = []
            trC2_traj = []
            gamma_traj = []
            H_traj = []
            
            for t in range(n_steps):
                Ct = C.copy()
                
                if cfg.get('evolving', False):
                    omega = cfg.get('omega', 0.1)
                    E = np.random.randn(N, N) * 0.2
                    E = (E + E.T) / 2
                    np.fill_diagonal(E, 0)
                    Ct = C + np.sin(omega * t) * E
                    np.fill_diagonal(Ct, 1.0)
                
                if cfg.get('inject_eig', False):
                    # Force Tr(C²) to oscillate by scaling off-diagonal
                    factor = 1.0 + 0.5 * np.sin(t * 0.3)
                    mask = np.ones((N, N)) - np.eye(N)
                    Ct = C * mask * factor + np.eye(N)
                
                gamma = spectral_gap(np.outer(x, x))
                H = participation_entropy(x)
                
                gh_traj.append(gamma + H)
                trC2_traj.append(trace_C2(Ct))
                gamma_traj.append(gamma)
                H_traj.append(H)
                
                coupling = Ct @ x
                x = np.tanh(coupling)
                
                if cfg.get('noise', 0) > 0:
                    x += cfg['noise'] * np.random.randn(N)
            
            # Skip transient
            gh = gh_traj[5:]
            trC2 = trC2_traj[5:]
            gammas = gamma_traj[5:]
            Hs = H_traj[5:]
            
            cv_gh_list.append(compute_cv(gh))
            cv_trC2_list.append(compute_cv(trC2))
            gamma_H_corr_list.append(compute_correlation(gammas, Hs))
            
            # Drift: (max - min) / mean
            gh_drift_list.append(float((max(gh) - min(gh)) / (np.mean(gh) + 1e-15)))
            trC2_drift_list.append(float((max(trC2) - min(trC2)) / (np.mean(trC2) + 1e-15)))
        
        results[config_name] = {
            'cv_gh_mean': float(np.mean(cv_gh_list)),
            'cv_gh_std': float(np.std(cv_gh_list)),
            'cv_trC2_mean': float(np.mean(cv_trC2_list)),
            'cv_trC2_std': float(np.std(cv_trC2_list)),
            'gamma_H_corr': float(np.mean(gamma_H_corr_list)),
            'gh_drift': float(np.mean(gh_drift_list)),
            'trC2_drift': float(np.mean(trC2_drift_list)),
        }
        
        print(f"  {config_name:20s} | CV(γ+H)={results[config_name]['cv_gh_mean']:.4f}±{results[config_name]['cv_gh_std']:.4f} | "
              f"CV(TrC²)={results[config_name]['cv_trC2_mean']:.4f} | "
              f"r(γ,H)={results[config_name]['gamma_H_corr']:.3f} | "
              f"drift(γ+H)={results[config_name]['gh_drift']:.3f}")
    
    return results


# ============================================================
# EXPERIMENT 4: Lyapunov Equation Connection
# ============================================================
def exp4_lyapunov():
    """
    Test whether the Lyapunov equation A^T P A = P connects to Tr(C²).
    
    For linear dynamics x_{t+1} = A x_t where A = tanh'(C x*) * C 
    (linearized around fixed point x*), check if:
    1. The Lyapunov residual ||A^T P A - P|| predicts conservation quality
    2. Tr(C²) is related to the Lyapunov eigenvalue structure
    3. Discover P from data by fitting Q(x) = γ+H as quadratic form
    """
    print("\n" + "=" * 70)
    print("EXP-4: Lyapunov Equation Connection")
    print("=" * 70)
    
    N = 15
    n_steps = 300
    n_reps = 15
    
    architectures = {
        'random': lambda: make_random_coupling(N),
        'hebbian': lambda: make_hebbian_coupling(N),
        'attention': lambda: make_attention_coupling(N),
    }
    
    results = {}
    
    for arch_name, arch_fn in architectures.items():
        lyapunov_residuals = []
        cv_gh_list = []
        cv_trC2_list = []
        P_fit_quality = []
        skewness_list = []
        
        for rep in range(n_reps):
            C = arch_fn()
            x0 = np.random.randn(N)
            x0 = x0 / np.linalg.norm(x0)
            
            # Run dynamics to find approximate fixed point
            x = x0.copy()
            for t in range(100):
                x = np.tanh(C @ x)
            x_star = x.copy()  # Approximate fixed point
            
            # Linearize: A_ij = tanh'(sum_k C_ik x_k*) * C_ij
            pre_activation = C @ x_star
            tanh_deriv = 1 - np.tanh(pre_activation)**2  # Diagonal
            A = np.diag(tanh_deriv) @ C  # Jacobian at fixed point
            
            # Discover P from data: collect (x, γ+H) pairs
            x = x0.copy()
            X_data = []
            q_data = []
            
            for t in range(n_steps):
                gamma = spectral_gap(np.outer(x, x))
                H = participation_entropy(x)
                q = gamma + H
                
                X_data.append(x.copy())
                q_data.append(q)
                
                x = np.tanh(C @ x)
            
            X_data = np.array(X_data)
            q_data = np.array(q_data)
            
            # Fit quadratic form: q ≈ x^T P x
            # x^T P x = sum_{i<=j} P_ij x_i x_j + P_ji x_j x_i
            # For symmetric P: x^T P x = sum_{i,j} P_ij x_i x_j
            # We need: P such that x^T P x ≈ q for all samples
            
            # Build quadratic features
            n_samples = len(q_data)
            n_features = N * (N + 1) // 2
            Phi = np.zeros((n_samples, n_features))
            
            idx = 0
            for i in range(N):
                for j in range(i, N):
                    if i == j:
                        Phi[:, idx] = X_data[:, i] ** 2
                    else:
                        Phi[:, idx] = 2 * X_data[:, i] * X_data[:, j]
                    idx += 1
            
            # Fit with regularization
            try:
                # Use only data after transient
                Phi_fit = Phi[50:]
                q_fit = q_data[50:]
                
                beta = np.linalg.lstsq(Phi_fit, q_fit, rcond=None)[0]
                pred = Phi_fit @ beta
                ss_res = np.sum((q_fit - pred)**2)
                ss_tot = np.sum((q_fit - np.mean(q_fit))**2)
                R2 = 1 - ss_res / (ss_tot + 1e-15)
                P_fit_quality.append(R2)
                
                # Reconstruct P matrix
                P = np.zeros((N, N))
                idx = 0
                for i in range(N):
                    for j in range(i, N):
                        P[i, j] = beta[idx]
                        P[j, i] = beta[idx]
                        idx += 1
                
                # Compute Lyapunov residual: ||A^T P A - P||_F / ||P||_F
                residual = A.T @ P @ A - P
                lyap_res = np.linalg.norm(residual, 'fro') / (np.linalg.norm(P, 'fro') + 1e-15)
                lyapunov_residuals.append(lyap_res)
                
            except Exception as e:
                P_fit_quality.append(0.0)
                lyapunov_residuals.append(999.0)
                P = np.eye(N)
            
            # Compute CV(γ+H) and CV(Tr(C²))
            gh_traj = q_data[50:]
            trC2_val = trace_C2(C)
            cv_gh_list.append(compute_cv(gh_traj))
            cv_trC2_list.append(0.0)  # Static C → Tr(C²) constant
            
            # Check skew-symmetry of P^{1/2} C P^{-1/2}
            try:
                eigvals_P = np.linalg.eigvalsh(P)
                if np.all(eigvals_P > 0):
                    P_sqrt = sqrtm(P).real
                    P_inv_sqrt = np.linalg.inv(P_sqrt)
                    M = P_sqrt @ C @ P_inv_sqrt
                    skew = np.linalg.norm(M + M.T, 'fro') / (np.linalg.norm(M, 'fro') + 1e-15)
                    skewness_list.append(skew)
                else:
                    skewness_list.append(999.0)
            except:
                skewness_list.append(999.0)
        
        results[arch_name] = {
            'lyapunov_residual': float(np.mean([r for r in lyapunov_residuals if r < 100])),
            'lyapunov_residual_std': float(np.std([r for r in lyapunov_residuals if r < 100])),
            'P_fit_R2': float(np.mean([r for r in P_fit_quality if r > 0])),
            'P_fit_R2_std': float(np.std([r for r in P_fit_quality if r > 0])),
            'cv_gh': float(np.mean(cv_gh_list)),
            'skewness': float(np.mean([s for s in skewness_list if s < 100])),
            'skewness_std': float(np.std([s for s in skewness_list if s < 100])),
        }
        
        print(f"  {arch_name:15s} | Lyap_res={results[arch_name]['lyapunov_residual']:.4f} | "
              f"P_fit_R²={results[arch_name]['P_fit_R2']:.3f} | "
              f"CV(γ+H)={results[arch_name]['cv_gh']:.4f} | "
              f"skewness={results[arch_name]['skewness']:.4f}")
    
    return results


# ============================================================
# EXPERIMENT 5: Dynamic C — Evolving Coupling Matrix
# ============================================================
def exp5_dynamic_coupling():
    """
    The CRITICAL test: what happens when C ITSELF changes over time?
    
    This tests whether Tr(C²) conservation under static C is trivial
    (of course it's constant if C doesn't change!) vs genuinely
    predictive of γ+H conservation.
    
    Method: C(t) evolves via small perturbations. Track both Tr(C²)(t)
    and γ+H(t). Test correlation.
    """
    print("\n" + "=" * 70)
    print("EXP-5: Dynamic Coupling Matrix — Tr(C²) as Live Predictor")
    print("=" * 70)
    
    N = 20
    n_steps = 500
    
    configs = {
        'slow_drift': {'omega': 0.01, 'amplitude': 0.1},
        'fast_drift': {'omega': 0.2, 'amplitude': 0.1},
        'large_drift': {'omega': 0.05, 'amplitude': 0.5},
        'small_drift': {'omega': 0.05, 'amplitude': 0.01},
        'chaotic_drift': {'omega': 0.0, 'amplitude': 0.1, 'chaotic': True},
        'random_walk': {'omega': 0.0, 'amplitude': 0.02, 'walk': True},
    }
    
    results = {}
    n_reps = 15
    
    for config_name, cfg in configs.items():
        corr_gh_trC2_list = []
        corr_gh_trC_list = []
        r2_trC2_predict_list = []
        r2_both_predict_list = []
        cv_gh_list = []
        cv_trC2_list = []
        gamma_H_corr_list = []
        
        for rep in range(n_reps):
            C_base = make_attention_coupling(N)
            x = np.random.randn(N)
            x = x / np.linalg.norm(x)
            
            gh_traj = []
            trC_traj = []
            trC2_traj = []
            gamma_traj = []
            H_traj = []
            
            C = C_base.copy()
            
            for t in range(n_steps):
                # Evolve C
                if cfg.get('chaotic', False):
                    E = np.random.randn(N, N) * cfg['amplitude']
                    E = (E + E.T) / 2
                    np.fill_diagonal(E, 0)
                    C = C * 0.99 + E * 0.01 + C_base * 0.01  # Mean-reverting + chaos
                    np.fill_diagonal(C, 1.0)
                elif cfg.get('walk', False):
                    E = np.random.randn(N, N) * cfg['amplitude']
                    E = (E + E.T) / 2
                    np.fill_diagonal(E, 0)
                    C = C + E
                    C = C * 0.99 + C_base * 0.01  # Soft mean-reversion
                    np.fill_diagonal(C, 1.0)
                else:
                    omega = cfg['omega']
                    amp = cfg['amplitude']
                    E = np.random.randn(N, N)
                    E = (E + E.T) / 2
                    np.fill_diagonal(E, 0)
                    C = C_base + amp * np.sin(omega * t) * E
                    np.fill_diagonal(C, 1.0)
                
                gamma = spectral_gap(np.outer(x, x))
                H = participation_entropy(x)
                
                gh_traj.append(gamma + H)
                trC_traj.append(trace_C(C))
                trC2_traj.append(trace_C2(C))
                gamma_traj.append(gamma)
                H_traj.append(H)
                
                x = np.tanh(C @ x)
            
            # Skip transient
            start = 20
            gh = np.array(gh_traj[start:])
            trC = np.array(trC_traj[start:])
            trC2 = np.array(trC2_traj[start:])
            gammas = np.array(gamma_traj[start:])
            Hs = np.array(H_traj[start:])
            
            corr_gh_trC2_list.append(compute_correlation(gh, trC2))
            corr_gh_trC_list.append(compute_correlation(gh, trC))
            cv_gh_list.append(compute_cv(gh))
            cv_trC2_list.append(compute_cv(trC2))
            gamma_H_corr_list.append(compute_correlation(gammas, Hs))
            
            # Regression: γ+H ~ Tr(C²)
            if np.std(trC2) > 1e-10:
                coeffs = np.polyfit(trC2, gh, 1)
                pred = np.polyval(coeffs, trC2)
                ss_res = np.sum((gh - pred)**2)
                ss_tot = np.sum((gh - np.mean(gh))**2)
                r2_trC2_predict_list.append(1 - ss_res / (ss_tot + 1e-15))
            else:
                r2_trC2_predict_list.append(0.0)
            
            # Regression: γ+H ~ Tr(C) + Tr(C²)
            if np.std(trC) > 1e-10 and np.std(trC2) > 1e-10:
                X = np.column_stack([trC, trC2, np.ones(len(trC))])
                try:
                    beta = np.linalg.lstsq(X, gh, rcond=None)[0]
                    pred = X @ beta
                    ss_res = np.sum((gh - pred)**2)
                    ss_tot = np.sum((gh - np.mean(gh))**2)
                    r2_both_predict_list.append(1 - ss_res / (ss_tot + 1e-15))
                except:
                    r2_both_predict_list.append(0.0)
            else:
                r2_both_predict_list.append(0.0)
        
        results[config_name] = {
            'corr_gh_trC2': float(np.mean(corr_gh_trC2_list)),
            'corr_gh_trC2_std': float(np.std(corr_gh_trC2_list)),
            'corr_gh_trC': float(np.mean(corr_gh_trC_list)),
            'R2_trC2_predict': float(np.mean(r2_trC2_predict_list)),
            'R2_both_predict': float(np.mean(r2_both_predict_list)),
            'cv_gh': float(np.mean(cv_gh_list)),
            'cv_trC2': float(np.mean(cv_trC2_list)),
            'gamma_H_corr': float(np.mean(gamma_H_corr_list)),
        }
        
        print(f"  {config_name:18s} | r(γ+H,TrC²)={results[config_name]['corr_gh_trC2']:.3f}±{results[config_name]['corr_gh_trC2_std']:.3f} | "
              f"R²(TrC²→γ+H)={results[config_name]['R2_trC2_predict']:.3f} | "
              f"R²(both→γ+H)={results[config_name]['R2_both_predict']:.3f} | "
              f"r(γ,H)={results[config_name]['gamma_H_corr']:.3f}")
    
    return results


# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    print("GPU Constraint Experiment Loop — Cycle 4")
    print("Model: Seed-2.0-mini (second rotation)")
    print("Focus: Nonlinear dynamics, Tr(C²), two-moment constraint, Lyapunov")
    print()
    
    all_results = {}
    
    exp1_results = exp1_nonlinear_architecture()
    all_results['exp1'] = exp1_results
    
    exp2_results = exp2_two_moment()
    all_results['exp2'] = exp2_results
    
    exp3_results = exp3_break_conservation()
    all_results['exp3'] = exp3_results
    
    exp4_results = exp4_lyapunov()
    all_results['exp4'] = exp4_results
    
    exp5_results = exp5_dynamic_coupling()
    all_results['exp5'] = exp5_results
    
    # Save raw results
    with open(os.path.join(RESULTS_DIR, 'raw_results.json'), 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print("\n\n" + "=" * 70)
    print("ALL EXPERIMENTS COMPLETE")
    print("=" * 70)
    print(f"Results saved to {RESULTS_DIR}/raw_results.json")
