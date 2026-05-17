"""
Cycle 12: Effective Rank Sweep — Mapping the Structural/Dynamical Transition
=============================================================================
Cycle 10 discovered TWO independent conservation mechanisms separated by effective rank.
This cycle maps the transition precisely.

Experiments:
1. Effective rank sweep: controlled eff_rank C matrices, measure CV(γ+H) vs rotation
2. Rank threshold: sharp or gradual?
3. Decompose γ+H: in structural regime, is γ=1, H=0 always?
4. Hybrid coupling: mix rank-1 and full-rank components

Parameters: N=5, 10 samples, 50 timesteps (keep small to avoid OOM)
"""

import numpy as np
import json
import os
from pathlib import Path

np.random.seed(42)

N = 5
N_SAMPLES = 10
T_STEPS = 50
NOISE_SIGMA = 0.1  # small noise to keep dynamics non-trivial

def effective_rank(eigenvalues):
    """Compute effective rank from eigenvalues."""
    eigenvalues = np.abs(eigenvalues)
    s = eigenvalues.sum()
    if s < 1e-12:
        return 0.0
    p = eigenvalues / s
    p = p[p > 1e-15]
    entropy = -np.sum(p * np.log(p))
    return np.exp(entropy)

def make_matrix_with_effective_rank(target_rank, N=5):
    """
    Construct a matrix with approximately the target effective rank.
    Strategy: start with rank-1, add decreasing singular values.
    """
    # Random orthogonal basis
    Q, _ = np.linalg.qr(np.random.randn(N, N))
    
    # Construct singular values to achieve target effective rank
    # eff_rank = exp(-sum(p_i * log(p_i))) where p_i = s_i / sum(s_j)
    # For target_rank k: first k singular values = 1, rest decay exponentially
    if target_rank <= 1.0:
        # Pure rank-1
        s = np.zeros(N)
        s[0] = 1.0
    elif target_rank >= N:
        # Full rank, equal singular values
        s = np.ones(N)
    else:
        # Interpolate: first singular value = 1, rest decay
        k = int(np.floor(target_rank))
        frac = target_rank - k
        s = np.zeros(N)
        for i in range(min(k + 1, N)):
            if i < k:
                s[i] = 1.0
            else:
                s[i] = frac  # partial contribution
        # Add small tail for remaining
        for i in range(k + 1, N):
            s[i] = 0.01  # tiny tail
        # Normalize so largest = 1
        s = s / max(s.max(), 1e-10)
    
    C = Q @ np.diag(s) @ Q.T
    # Make symmetric positive semi-definite
    C = (C + C.T) / 2
    return C

def make_state_dependent_coupling_base(target_rank, N=5):
    """
    Return a function that creates state-dependent coupling with target effective rank.
    Mix rank-1 (Hebbian) and full-rank (random) components.
    """
    # Pre-generate random component
    R = np.random.randn(N, N)
    R = (R + R.T) / (2 * np.sqrt(N))
    
    def coupling(x, alpha):
        """
        C(x) = alpha * xx^T/N + (1-alpha) * R
        alpha=1 → rank-1 (Hebbian SD)
        alpha=0 → full-rank random
        """
        hebb = np.outer(x, x) / N
        return alpha * hebb + (1 - alpha) * R
    
    return coupling, R

def compute_gamma_H(C, x):
    """Compute γ (participation) and H (entropy) for coupling C."""
    eigenvalues = np.linalg.eigvalsh(C)
    eigenvalues = np.abs(eigenvalues)
    s = eigenvalues.sum()
    if s < 1e-15:
        return 0.0, 0.0
    p = eigenvalues / s
    
    # γ = participation ratio (1 / sum(p_i^2))
    gamma = 1.0 / np.sum(p ** 2)
    
    # H = Shannon entropy
    p_pos = p[p > 1e-15]
    H = -np.sum(p_pos * np.log(p_pos))
    
    return gamma, H

def run_dynamics(C_func, x0, T, N, noise_sigma=0.1, coupling_type='static'):
    """Run tanh dynamics with state-dependent coupling."""
    x = x0.copy()
    trajectory = []
    gamma_H_traj = []
    
    for t in range(T):
        if coupling_type == 'state_dependent':
            C = C_func(x)
        else:
            C = C_func
        
        x_new = np.tanh(C @ x) + noise_sigma * np.random.randn(N)
        # Normalize to prevent blow-up
        norm = np.linalg.norm(x_new)
        if norm > 10:
            x_new = x_new / norm * 10
        
        x = x_new
        gamma, H = compute_gamma_H(C, x)
        trajectory.append(x.copy())
        gamma_H_traj.append((gamma, H))
    
    return np.array(trajectory), np.array(gamma_H_traj)

def top_eigvec_rotation(C_prev, C_curr):
    """Compute rotation angle (degrees) between top eigenvectors."""
    w1, v1 = np.linalg.eigh(C_prev)
    w2, v2 = np.linalg.eigh(C_curr)
    top1 = v1[:, -1]
    top2 = v2[:, -1]
    cos_angle = np.abs(np.clip(np.dot(top1, top2), -1, 1))
    return np.degrees(np.arccos(cos_angle))

# ============================================================
# EXPERIMENT 1: Effective Rank Sweep with Static Matrices
# ============================================================
print("=" * 60)
print("EXPERIMENT 1: Effective Rank Sweep (Static Matrices)")
print("=" * 60)

target_ranks = [1.0, 1.2, 1.5, 2.0, 3.0, 5.0]
# For N=5, max effective rank is 5.0

exp1_results = []

for target_rank in target_ranks:
    cv_list = []
    rotation_list = []
    actual_ranks = []
    
    for sample in range(N_SAMPLES):
        C = make_matrix_with_effective_rank(target_rank, N)
        
        # Compute actual effective rank
        evals = np.linalg.eigvalsh(C)
        actual_rank = effective_rank(evals)
        actual_ranks.append(actual_rank)
        
        x0 = np.random.randn(N) * 0.1
        
        traj, gh_traj = run_dynamics(C, x0, T_STEPS, N, NOISE_SIGMA, 'static')
        
        gamma_plus_H = gh_traj[:, 0] + gh_traj[:, 1]
        mean_val = np.mean(gamma_plus_H)
        std_val = np.std(gamma_plus_H)
        cv = std_val / abs(mean_val) if abs(mean_val) > 1e-10 else float('inf')
        cv_list.append(cv)
        
        # For static matrices, rotation is always 0
        rotation_list.append(0.0)
    
    exp1_results.append({
        'target_rank': target_rank,
        'actual_rank_mean': np.mean(actual_ranks),
        'actual_rank_std': np.std(actual_ranks),
        'cv_mean': np.mean(cv_list),
        'cv_std': np.std(cv_list),
        'rotation_mean': 0.0,
        'gamma_H_mean': None,  # fill below
    })
    print(f"  eff_rank={target_rank:.1f} (actual={np.mean(actual_ranks):.2f}±{np.std(actual_ranks):.2f}), "
          f"CV(γ+H)={np.mean(cv_list):.4f}±{np.std(cv_list):.4f}")

print("\nNote: Static coupling → trivially CV≈0 for all ranks (eigenvalues don't change)")
print("Need state-dependent coupling to see the transition.\n")

# ============================================================
# EXPERIMENT 2: State-Dependent Effective Rank Sweep (Hybrid)
# ============================================================
print("=" * 60)
print("EXPERIMENT 2: State-Dependent Hybrid (alpha sweep)")
print("C(x) = alpha * xx^T/N + (1-alpha) * R")
print("=" * 60)

alphas = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0]
exp2_results = []

for alpha in alphas:
    cv_list = []
    rotation_list = []
    eff_rank_list = []
    gamma_mean_list = []
    H_mean_list = []
    gH_mean_list = []
    
    for sample in range(N_SAMPLES):
        # Fresh random component per sample
        R = np.random.randn(N, N)
        R = (R + R.T) / (2 * np.sqrt(N))
        # Ensure positive definite
        evals_R = np.linalg.eigvalsh(R)
        if np.min(evals_R) < 0.01:
            R += (0.02 - np.min(evals_R)) * np.eye(N)
        
        x0 = np.random.randn(N) * 0.5
        
        def coupling(x, _alpha=alpha, _R=R):
            hebb = np.outer(x, x) / N
            return _alpha * hebb + (1 - _alpha) * _R
        
        traj, gh_traj = run_dynamics(coupling, x0, T_STEPS, N, NOISE_SIGMA, 'state_dependent')
        
        gamma_plus_H = gh_traj[:, 0] + gh_traj[:, 1]
        mean_val = np.mean(gamma_plus_H)
        std_val = np.std(gamma_plus_H)
        cv = std_val / abs(mean_val) if abs(mean_val) > 1e-10 else float('inf')
        cv_list.append(cv)
        
        gamma_mean_list.append(np.mean(gh_traj[:, 0]))
        H_mean_list.append(np.mean(gh_traj[:, 1]))
        gH_mean_list.append(mean_val)
        
        # Measure eigenvector rotation
        rotations = []
        for t in range(1, T_STEPS):
            C_prev = coupling(traj[t-1])
            C_curr = coupling(traj[t])
            rot = top_eigvec_rotation(C_prev, C_curr)
            rotations.append(rot)
        rotation_list.append(np.mean(rotations))
        
        # Measure effective rank of coupling at steady state
        C_ss = coupling(traj[-1])
        evals_ss = np.linalg.eigvalsh(C_ss)
        eff_rank_list.append(effective_rank(evals_ss))
    
    result = {
        'alpha': alpha,
        'cv_mean': np.mean(cv_list),
        'cv_std': np.std(cv_list),
        'rotation_mean': np.mean(rotation_list),
        'rotation_std': np.std(rotation_list),
        'eff_rank_mean': np.mean(eff_rank_list),
        'eff_rank_std': np.std(eff_rank_list),
        'gamma_mean': np.mean(gamma_mean_list),
        'H_mean': np.mean(H_mean_list),
        'gH_mean': np.mean(gH_mean_list),
    }
    exp2_results.append(result)
    print(f"  alpha={alpha:.2f}: CV={np.mean(cv_list):.4f}±{np.std(cv_list):.4f}, "
          f"rotation={np.mean(rotation_list):.1f}°±{np.std(rotation_list):.1f}°, "
          f"eff_rank={np.mean(eff_rank_list):.2f}±{np.std(eff_rank_list):.2f}, "
          f"γ={np.mean(gamma_mean_list):.2f}, H={np.mean(H_mean_list):.2f}")

# ============================================================
# EXPERIMENT 3: Decompose γ+H in Structural Regime
# ============================================================
print("\n" + "=" * 60)
print("EXPERIMENT 3: γ and H Decomposition (alpha=1.0, pure Hebbian SD)")
print("=" * 60)

exp3_results = []
for sample in range(N_SAMPLES):
    x0 = np.random.randn(N) * 0.5
    
    def hebb_coupling(x):
        return np.outer(x, x) / N
    
    traj, gh_traj = run_dynamics(hebb_coupling, x0, T_STEPS, N, NOISE_SIGMA, 'state_dependent')
    
    gamma_vals = gh_traj[:, 0]
    H_vals = gh_traj[:, 1]
    gH_vals = gamma_vals + H_vals
    
    exp3_results.append({
        'gamma_mean': np.mean(gamma_vals),
        'gamma_std': np.std(gamma_vals),
        'H_mean': np.mean(H_vals),
        'H_std': np.std(H_vals),
        'gH_mean': np.mean(gH_vals),
        'gH_cv': np.std(gH_vals) / abs(np.mean(gH_vals)) if abs(np.mean(gH_vals)) > 1e-10 else float('inf'),
    })

for i, r in enumerate(exp3_results):
    print(f"  Sample {i}: γ={r['gamma_mean']:.4f}±{r['gamma_std']:.6f}, "
          f"H={r['H_mean']:.4f}±{r['H_std']:.6f}, "
          f"γ+H={r['gH_mean']:.4f}, CV={r['gH_cv']:.6f}")

# ============================================================
# EXPERIMENT 4: Fine-Grained Rank Sweep (Low Rank Region)
# ============================================================
print("\n" + "=" * 60)
print("EXPERIMENT 4: Fine-Grained Alpha Sweep (Rank Transition)")
print("=" * 60)

fine_alphas = np.arange(0.0, 1.05, 0.05)
exp4_results = []

for alpha in fine_alphas:
    cv_list = []
    rotation_list = []
    eff_rank_list = []
    gamma_list = []
    H_list = []
    
    for sample in range(N_SAMPLES):
        R = np.random.randn(N, N)
        R = (R + R.T) / (2 * np.sqrt(N))
        evals_R = np.linalg.eigvalsh(R)
        if np.min(evals_R) < 0.01:
            R += (0.02 - np.min(evals_R)) * np.eye(N)
        
        x0 = np.random.randn(N) * 0.5
        
        def coupling(x, _alpha=alpha, _R=R):
            hebb = np.outer(x, x) / N
            return _alpha * hebb + (1 - _alpha) * _R
        
        traj, gh_traj = run_dynamics(coupling, x0, T_STEPS, N, NOISE_SIGMA, 'state_dependent')
        
        gamma_plus_H = gh_traj[:, 0] + gh_traj[:, 1]
        mean_val = np.mean(gamma_plus_H)
        std_val = np.std(gamma_plus_H)
        cv = std_val / abs(mean_val) if abs(mean_val) > 1e-10 else float('inf')
        cv_list.append(cv)
        
        gamma_list.append(np.mean(gh_traj[:, 0]))
        H_list.append(np.mean(gh_traj[:, 1]))
        
        rotations = []
        for t in range(1, T_STEPS):
            C_prev = coupling(traj[t-1])
            C_curr = coupling(traj[t])
            rot = top_eigvec_rotation(C_prev, C_curr)
            rotations.append(rot)
        rotation_list.append(np.mean(rotations))
        
        C_ss = coupling(traj[-1])
        evals_ss = np.linalg.eigvalsh(C_ss)
        eff_rank_list.append(effective_rank(evals_ss))
    
    result = {
        'alpha': round(alpha, 2),
        'cv_mean': np.mean(cv_list),
        'cv_std': np.std(cv_list),
        'rotation_mean': np.mean(rotation_list),
        'eff_rank_mean': np.mean(eff_rank_list),
        'gamma_mean': np.mean(gamma_list),
        'H_mean': np.mean(H_list),
    }
    exp4_results.append(result)
    print(f"  alpha={alpha:.2f}: CV={np.mean(cv_list):.4f}, "
          f"rot={np.mean(rotation_list):.1f}°, "
          f"eff_rank={np.mean(eff_rank_list):.2f}, "
          f"γ={np.mean(gamma_list):.2f}, H={np.mean(H_list):.2f}")

# ============================================================
# EXPERIMENT 5: Controlled Effective Rank via Eigenvalue Engineering
# ============================================================
print("\n" + "=" * 60)
print("EXPERIMENT 5: Eigenvalue-Engineered Effective Rank")
print("=" * 60)

target_ranks_fine = [1.0, 1.1, 1.2, 1.3, 1.5, 1.7, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
exp5_results = []

for target_rank in target_ranks_fine:
    cv_list = []
    rotation_list = []
    actual_ranks = []
    gamma_list = []
    H_list = []
    
    for sample in range(N_SAMPLES):
        # Build C(x) as state-dependent with controlled spectral structure
        # Strategy: C(x) = V @ diag(s(x)) @ V^T where s(x) has target effective rank
        Q, _ = np.linalg.qr(np.random.randn(N, N))
        
        def coupling_engineered(x, _Q=Q, _tr=target_rank):
            # Base: rank-1 Hebbian part
            hebb = np.outer(x, x) / N
            hebb_evals, hebb_evecs = np.linalg.eigh(hebb)
            
            # Create eigenvalue distribution with target effective rank
            # Use exponential decay: s_i = exp(-i/tau), tune tau for rank
            # eff_rank = exp(H) where H = -sum(p_i log(p_i))
            # Approximate: for target_rank k, use s_i = 1 for i<k, geometric decay for rest
            
            if _tr <= 1.0:
                s = np.zeros(N)
                s[-1] = 1.0  # single non-zero eigenvalue
            elif _tr >= N:
                s = np.ones(N)
            else:
                k = int(np.floor(_tr))
                frac = _tr - k
                s = np.zeros(N)
                for i in range(N):
                    idx = N - 1 - i  # from largest
                    if i < k:
                        s[idx] = 1.0
                    elif i == k:
                        s[idx] = max(frac, 0.01)
                    else:
                        s[idx] = 0.01
            
            # Use Hebbian eigenvectors (rank-1 structure) but engineered eigenvalues
            # This gives controlled effective rank while keeping state-dependence
            C = hebb_evecs @ np.diag(s) @ hebb_evecs.T
            return C
        
        x0 = np.random.randn(N) * 0.5
        traj, gh_traj = run_dynamics(coupling_engineered, x0, T_STEPS, N, NOISE_SIGMA, 'state_dependent')
        
        gamma_plus_H = gh_traj[:, 0] + gh_traj[:, 1]
        mean_val = np.mean(gamma_plus_H)
        std_val = np.std(gamma_plus_H)
        cv = std_val / abs(mean_val) if abs(mean_val) > 1e-10 else float('inf')
        cv_list.append(cv)
        
        gamma_list.append(np.mean(gh_traj[:, 0]))
        H_list.append(np.mean(gh_traj[:, 1]))
        
        rotations = []
        for t in range(1, T_STEPS):
            C_prev = coupling_engineered(traj[t-1])
            C_curr = coupling_engineered(traj[t])
            rot = top_eigvec_rotation(C_prev, C_curr)
            rotations.append(rot)
        rotation_list.append(np.mean(rotations))
        
        C_ss = coupling_engineered(traj[-1])
        evals_ss = np.linalg.eigvalsh(C_ss)
        actual_ranks.append(effective_rank(evals_ss))
    
    result = {
        'target_rank': target_rank,
        'actual_rank_mean': np.mean(actual_ranks),
        'cv_mean': np.mean(cv_list),
        'cv_std': np.std(cv_list),
        'rotation_mean': np.mean(rotation_list),
        'gamma_mean': np.mean(gamma_list),
        'H_mean': np.mean(H_list),
    }
    exp5_results.append(result)
    print(f"  target_rank={target_rank:.1f} (actual={np.mean(actual_ranks):.2f}): "
          f"CV={np.mean(cv_list):.4f}±{np.std(cv_list):.4f}, "
          f"rot={np.mean(rotation_list):.1f}°, "
          f"γ={np.mean(gamma_list):.2f}, H={np.mean(H_list):.2f}")

# ============================================================
# SAVE RAW DATA
# ============================================================
raw_data = {
    'exp2_hybrid': exp2_results,
    'exp3_decomposition': exp3_results,
    'exp4_fine_alpha': exp4_results,
    'exp5_engineered_rank': exp5_results,
}

with open('/home/phoenix/.openclaw/workspace/experiments/gpu-loop/cycle-012/raw_data.json', 'w') as f:
    json.dump(raw_data, f, indent=2, default=str)

print("\n" + "=" * 60)
print("ALL EXPERIMENTS COMPLETE")
print("Raw data saved to raw_data.json")
print("=" * 60)
