#!/usr/bin/env python3
"""
Cycle 9: Attractor Geometry — Phase Diagram, Commutator, Activation Comparison, Multi-FP

Key insight from pretest: for ρ(C) > 1, undamped tanh iteration can converge to
period-2 orbits. Use damped iteration (α=0.5) for fixed point finding.
"""

import numpy as np
from scipy.stats import pearsonr
import json, sys
import warnings
warnings.filterwarnings('ignore')

np.random.seed(42)
N = 20
SAMPLES = 40

# ============================================================
# Core functions
# ============================================================

def spectral_gap(C):
    eigvals = np.sort(np.abs(np.linalg.eigvalsh(C)))[::-1]
    return float(eigvals[0] - eigvals[1]) if len(eigvals) > 1 else float(eigvals[0])

def participation_entropy(C):
    eigvals = np.abs(np.linalg.eigvalsh(C))
    p = eigvals / eigvals.sum()
    p = p[p > 1e-12]
    return float(-np.sum(p * np.log(p)))

def gamma_plus_H(C):
    return spectral_gap(C) + participation_entropy(C)

def goe_matrix(n, scale=1.0):
    W = np.random.randn(n, n) / np.sqrt(n)
    return (W + W.T) / 2 * scale

def spectral_radius(M):
    return float(np.max(np.abs(np.linalg.eigvals(M))))

def find_fixed_point(C, x0=None, tol=1e-10, max_iter=20000, damping=0.5):
    """Damped iteration: x_new = (1-α)*x + α*tanh(C@x)"""
    n = C.shape[0]
    x = np.random.randn(n) * 0.1 if x0 is None else x0.copy()
    for i in range(max_iter):
        x_new = (1 - damping) * x + damping * np.tanh(C @ x)
        if np.linalg.norm(x_new - x) < tol:
            return x_new, i, True
        x = x_new
    return x, max_iter, False

def find_undamped_orbit(C, x0=None, steps=500, warmup=200):
    """Run undamped dynamics and check for period-1 or period-2 convergence."""
    x = np.random.randn(N) * 0.1 if x0 is None else x0.copy()
    for _ in range(warmup):
        x = np.tanh(C @ x)
    # Collect last few points
    trajectory = []
    for _ in range(steps):
        x = np.tanh(C @ x)
        trajectory.append(x.copy())
    trajectory = np.array(trajectory)
    
    # Check convergence: variance of norms
    norms = np.linalg.norm(trajectory, axis=1)
    cv_norm = np.std(norms) / (np.mean(norms) + 1e-12)
    
    # Average state
    mean_x = np.mean(trajectory, axis=0)
    
    return trajectory, mean_x, cv_norm

def commutator_norm(D_diag, C):
    """||[diag(D), C]||_F"""
    DC = D_diag[:, None] * C
    CD = C * D_diag[None, :]
    return float(np.linalg.norm(DC - CD, 'fro'))

def state_dependent_attention(x, temperature=1.0):
    n = len(x)
    logits = np.outer(x, x) / temperature
    logits -= logits.max(axis=1, keepdims=True)
    S = np.exp(logits)
    return S / S.sum(axis=1, keepdims=True)

# ============================================================
# EXPERIMENT 1: Phase Diagram — γ+H vs ρ(C)
# ============================================================
print("=" * 70)
print("EXP 1: Phase Diagram — γ+H(x*) vs ρ(C)")
print("=" * 70)

scales = np.arange(0.5, 5.1, 0.25)
phase_data = []

for si, scale in enumerate(scales):
    gh_vals = []
    rho_C_vals = []
    rho_A_vals = []
    xstar_norms = []
    conv_rates = []
    orbit_cv_norms = []
    is_period2 = []
    
    for _ in range(SAMPLES):
        C = goe_matrix(N, scale)
        rho_C = spectral_radius(C)
        
        # Find fixed point with damping
        x_star, iters, conv = find_fixed_point(C, damping=0.5)
        
        # Check undamped dynamics
        traj, mean_x, cv_norm = find_undamped_orbit(C)
        
        # Jacobian at fixed point
        D_diag = 1 - x_star**2
        A = np.diag(D_diag) @ C
        rho_A = spectral_radius(A)
        
        gh = gamma_plus_H(C)
        
        gh_vals.append(gh)
        rho_C_vals.append(rho_C)
        rho_A_vals.append(rho_A)
        xstar_norms.append(np.linalg.norm(x_star))
        conv_rates.append(float(conv))
        orbit_cv_norms.append(cv_norm)
        is_period2.append(1.0 if cv_norm > 0.001 else 0.0)
    
    phase_data.append({
        'scale': float(scale),
        'rho_C_mean': float(np.mean(rho_C_vals)),
        'gh_mean': float(np.mean(gh_vals)),
        'gh_std': float(np.std(gh_vals)),
        'gh_cv': float(np.std(gh_vals) / (np.mean(gh_vals) + 1e-12)),
        'rho_A_mean': float(np.mean(rho_A_vals)),
        'xstar_norm_mean': float(np.mean(xstar_norms)),
        'conv_rate': float(np.mean(conv_rates)),
        'period2_rate': float(np.mean(is_period2)),
        'orbit_cv_norm_mean': float(np.mean(orbit_cv_norms)),
    })
    
    print(f"  ρ={np.mean(rho_C_vals):.2f} (s={scale:.2f}): γ+H={np.mean(gh_vals):.4f}±{np.std(gh_vals):.4f}, ρ(A)={np.mean(rho_A_vals):.3f}, ||x*||={np.mean(xstar_norms):.3f}, p2={np.mean(is_period2):.0%}")
    
    sys.stdout.flush()

# Bifurcation analysis
print("\n--- Bifurcation Analysis ---")
gh_means = [p['gh_mean'] for p in phase_data]
gh_diffs = np.abs(np.diff(gh_means))
max_j = np.argmax(gh_diffs)
print(f"Largest γ+H jump: scales[{max_j}]={scales[max_j]:.2f}→{scales[max_j+1]:.2f}, Δ={gh_diffs[max_j]:.4f}")
print(f"Period-2 onset (first scale with >10% period-2): ", end="")
for p in phase_data:
    if p['period2_rate'] > 0.1:
        print(f"scale={p['scale']:.2f}, ρ(C)≈{p['rho_C_mean']:.2f}")
        break
print(f"ρ(A) crosses 1.0: ", end="")
for p in phase_data:
    if p['rho_A_mean'] > 1.0:
        print(f"scale={p['scale']:.2f}, ρ(A)={p['rho_A_mean']:.3f}")
        break
    elif p == phase_data[-1]:
        print("Never (ρ(A) < 1.0 for all tested scales)")

# ============================================================
# EXPERIMENT 2: Commutator Diagnostic — ||[D, C]|| vs CV(γ+H)
# ============================================================
print("\n" + "=" * 70)
print("EXP 2: Commutator ||[D, C]|| vs CV(γ+H)")
print("=" * 70)

comm_cv_data = []

# With state-dependent coupling (where CV is non-trivial)
for tau in [0.1, 0.3, 0.5, 1.0, 2.0, 5.0, 10.0]:
    gh_trajs_all = []
    comm_mean_list = []
    
    for sample in range(25):
        x = np.random.randn(N) * 0.1
        gh_traj = []
        comm_vals = []
        
        for t in range(200):
            C_t = state_dependent_attention(x, tau)
            gh = gamma_plus_H(C_t)
            gh_traj.append(gh)
            
            # Commutator at current state
            D_diag = 1 - x**2
            comm = commutator_norm(D_diag, C_t)
            comm_vals.append(comm)
            
            x = np.tanh(C_t @ x) + np.random.randn(N) * 0.05
        
        gh_trajs_all.extend(gh_traj)
        comm_mean_list.append(np.mean(comm_vals))
    
    cv_gh = np.std(gh_trajs_all) / (np.mean(gh_trajs_all) + 1e-12)
    mean_comm = np.mean(comm_mean_list)
    
    comm_cv_data.append({
        'tau': tau,
        'cv_gh': float(cv_gh),
        'mean_comm': float(mean_comm),
    })
    
    print(f"  τ={tau:.1f}: CV(γ+H)={cv_gh:.6f}, mean||[D,C]||={mean_comm:.4f}")
    sys.stdout.flush()

# Correlation
if len(comm_cv_data) > 2:
    c_arr = np.array([d['mean_comm'] for d in comm_cv_data])
    v_arr = np.array([d['cv_gh'] for d in comm_cv_data])
    r, p = pearsonr(c_arr, v_arr)
    print(f"\n  r(||[D,C]||, CV(γ+H)) = {r:.4f}, p = {p:.4f}")

# Also: commutator at fixed point vs cross-instance CV for static coupling
print("\n--- Commutator at Fixed Point vs Cross-Instance CV ---")
fp_comm_data = []
for scale in [0.5, 1.0, 1.5, 2.0, 3.0, 5.0]:
    gh_vals = []
    comm_vals = []
    rho_A_vals = []
    
    for _ in range(SAMPLES):
        C = goe_matrix(N, scale)
        x_star, _, conv = find_fixed_point(C)
        D_diag = 1 - x_star**2
        comm = commutator_norm(D_diag, C)
        A = np.diag(D_diag) @ C
        rho_A = spectral_radius(A)
        
        gh_vals.append(gamma_plus_H(C))
        comm_vals.append(comm)
        rho_A_vals.append(rho_A)
    
    ci_cv = np.std(gh_vals) / (np.mean(gh_vals) + 1e-12)
    mean_comm = np.mean(comm_vals)
    mean_rho_A = np.mean(rho_A_vals)
    
    fp_comm_data.append({
        'scale': scale,
        'ci_cv': float(ci_cv),
        'mean_comm': float(mean_comm),
        'mean_rho_A': float(mean_rho_A),
    })
    print(f"  s={scale:.1f}: CI_CV(γ+H)={ci_cv:.6f}, ||[D,C]||={mean_comm:.4f}, ρ(A)={mean_rho_A:.4f}")
    sys.stdout.flush()

c_arr = np.array([d['mean_comm'] for d in fp_comm_data])
v_arr = np.array([d['ci_cv'] for d in fp_comm_data])
if len(c_arr) > 2:
    r, p = pearsonr(c_arr, v_arr)
    print(f"  r(||[D,C]||, CI_CV) = {r:.4f}, p = {p:.4f}")

# ============================================================
# EXPERIMENT 3: Activation Comparison
# ============================================================
print("\n" + "=" * 70)
print("EXP 3: Activation Comparison — Bounded vs Unbounded")
print("=" * 70)

activations = {
    'tanh': np.tanh,
    'sigmoid_shifted': lambda x: 2.0 / (1 + np.exp(-np.clip(x, -20, 20))) - 1.0,
    'softsign': lambda x: x / (1 + np.abs(x)),
    'relu': lambda x: np.maximum(0, x),
    'leaky_relu': lambda x: np.where(x > 0, x, 0.01 * x),
    'elu': lambda x: np.where(x > 0, x, np.exp(np.clip(x, -20, 0)) - 1),
    'swish': lambda x: x / (1 + np.exp(-np.clip(x, -20, 20))),
    'clipped_relu': lambda x: np.clip(np.maximum(0, x), 0, 1),
}

bounded = {'tanh', 'sigmoid_shifted', 'softsign', 'clipped_relu'}

# 3a: Static coupling — does bounded activation conserve better?
print("\n--- 3a: Static GOE Coupling (scale=2.0) ---")
act_results = {}

for act_name, act_fn in activations.items():
    cv_list = []
    norm_list = []
    blowup = 0
    
    for _ in range(SAMPLES):
        C = goe_matrix(N, 2.0)
        x = np.random.randn(N) * 0.1
        gh_vals = []
        
        for t in range(300):
            x = act_fn(C @ x)
            if np.any(np.isnan(x)) or np.any(np.isinf(x)) or np.linalg.norm(x) > 1e8:
                blowup += 1
                break
            gh_vals.append(gamma_plus_H(C))
        
        if len(gh_vals) > 10:
            cv = np.std(gh_vals) / (np.mean(gh_vals) + 1e-12)
            cv_list.append(cv)
            norm_list.append(np.linalg.norm(x))
    
    if cv_list:
        act_results[act_name] = {
            'cv_mean': float(np.mean(cv_list)),
            'cv_std': float(np.std(cv_list)),
            'norm_mean': float(np.mean(norm_list)),
            'blowup_rate': float(blowup / SAMPLES),
            'bounded': act_name in bounded,
        }
        r = act_results[act_name]
        b = 'YES' if r['bounded'] else 'no'
        print(f"  {act_name:20s}: CV={r['cv_mean']:.6f}±{r['cv_std']:.6f}, ||x||={r['norm_mean']:.2f}, blowup={r['blowup_rate']:.0%}, bounded={b}")
    sys.stdout.flush()

# 3b: Quadratic form R² for each activation (static coupling)
print("\n--- 3b: R²(x^T P x = γ+H) by Activation ---")
act_r2 = {}

for act_name, act_fn in activations.items():
    r2_list = []
    
    for _ in range(15):
        C = goe_matrix(N, 2.0)
        x = np.random.randn(N) * 0.1
        X_data = []
        gh_data = []
        
        for t in range(300):
            x = act_fn(C @ x)
            if np.any(np.isnan(x)) or np.any(np.isinf(x)) or np.linalg.norm(x) > 1e8:
                break
            gh_data.append(gamma_plus_H(C))
            X_data.append(x.copy())
        
        if len(X_data) < 50:
            continue
        
        X = np.array(X_data)
        y = np.array(gh_data)
        
        # Only fit if there's variance in y (static C → y is constant → skip)
        if np.std(y) < 1e-12:
            r2_list.append(1.0)  # trivially constant
            continue
        
        # Fit x^T P x
        n_feat = N * (N + 1) // 2
        Phi = np.zeros((len(y), n_feat))
        for s in range(len(y)):
            idx = 0
            for i in range(N):
                for j in range(i, N):
                    Phi[s, idx] = X[s, i] * X[s, j]
                    idx += 1
        
        try:
            coeffs, _, _, _ = np.linalg.lstsq(Phi, y, rcond=None)
            y_pred = Phi @ coeffs
            ss_res = np.sum((y - y_pred)**2)
            ss_tot = np.sum((y - np.mean(y))**2)
            r2 = max(-1, 1 - ss_res / ss_tot) if ss_tot > 1e-12 else 1.0
            r2_list.append(r2)
        except:
            pass
    
    if r2_list:
        act_r2[act_name] = {
            'r2_mean': float(np.mean(r2_list)),
            'r2_std': float(np.std(r2_list)),
            'bounded': act_name in bounded,
        }
        b = 'YES' if act_name in bounded else 'no'
        print(f"  {act_name:20s}: R²={np.mean(r2_list):.6f}±{np.std(r2_list):.6f}, bounded={b}")
    sys.stdout.flush()

# 3c: State-dependent coupling — where CV is meaningful
print("\n--- 3c: State-Dependent Coupling (attention τ=1.0) ---")
act_sd_results = {}

for act_name, act_fn in activations.items():
    cv_list = []
    blowup = 0
    
    for _ in range(25):
        x = np.random.randn(N) * 0.1
        gh_vals = []
        
        for t in range(200):
            C_t = state_dependent_attention(x, 1.0)
            gh = gamma_plus_H(C_t)
            gh_vals.append(gh)
            
            x = act_fn(C_t @ x) + np.random.randn(N) * 0.05
            
            if np.any(np.isnan(x)) or np.any(np.isinf(x)) or np.linalg.norm(x) > 1e8:
                blowup += 1
                break
        
        if len(gh_vals) > 10:
            cv = np.std(gh_vals) / (np.mean(gh_vals) + 1e-12)
            cv_list.append(cv)
    
    if cv_list:
        act_sd_results[act_name] = {
            'cv_mean': float(np.mean(cv_list)),
            'cv_std': float(np.std(cv_list)),
            'blowup_rate': float(blowup / 25),
            'bounded': act_name in bounded,
        }
        r = act_sd_results[act_name]
        b = 'YES' if r['bounded'] else 'no'
        print(f"  {act_name:20s}: CV={r['cv_mean']:.4f}±{r['cv_std']:.4f}, blowup={r['blowup_rate']:.0%}, bounded={b}")
    sys.stdout.flush()

# ============================================================
# EXPERIMENT 4: Multi-Fixed-Point Regime
# ============================================================
print("\n" + "=" * 70)
print("EXP 4: Multi-Fixed-Point Regime (ρ(C) > 1)")
print("=" * 70)

multi_fp_summary = []

for scale in [1.5, 2.0, 3.0, 5.0]:
    n_fp_counts = []
    fp_norm_spreads = []
    
    for _ in range(SAMPLES):
        C = goe_matrix(N, scale)
        eigvals_C, eigvecs_C = np.linalg.eigh(C)
        idx = np.argsort(np.abs(eigvals_C))[::-1]
        eigvecs_C = eigvecs_C[:, idx]
        
        # Try many initial conditions
        inits = [np.random.randn(N) * 0.5 for _ in range(15)]
        for k in range(min(5, N)):
            inits.append(eigvecs_C[:, k] * 0.5)
            inits.append(-eigvecs_C[:, k] * 0.5)
        
        unique_fps = []
        for x0 in inits:
            x_star, _, conv = find_fixed_point(C, x0, damping=0.5)
            if not conv:
                continue
            
            is_new = True
            for uf in unique_fps:
                if np.linalg.norm(x_star - uf) < 0.01:
                    is_new = False
                    break
            if is_new:
                unique_fps.append(x_star.copy())
        
        n_fp_counts.append(len(unique_fps))
        if len(unique_fps) > 1:
            norms = [np.linalg.norm(fp) for fp in unique_fps]
            fp_norm_spreads.append(np.std(norms) / (np.mean(norms) + 1e-12))
    
    mean_n = np.mean(n_fp_counts)
    max_n = np.max(n_fp_counts)
    p_multi = np.mean([c > 1 for c in n_fp_counts])
    
    multi_fp_summary.append({
        'scale': float(scale),
        'mean_n_fps': float(mean_n),
        'max_n_fps': int(max_n),
        'multi_fp_rate': float(p_multi),
        'norm_cv_mean': float(np.mean(fp_norm_spreads)) if fp_norm_spreads else 0,
    })
    
    print(f"  s={scale:.1f}: mean FPs={mean_n:.2f}, max={max_n}, multi-FP rate={p_multi:.0%}", end="")
    if fp_norm_spreads:
        print(f", CV(||x*||)={np.mean(fp_norm_spreads):.4f}")
    else:
        print()
    sys.stdout.flush()

# For one sample at scale=3.0, analyze multiple FPs in detail
print("\n--- Detailed Multi-FP Analysis (scale=3.0) ---")
C = goe_matrix(N, 3.0)
eigvals_C, eigvecs_C = np.linalg.eigh(C)
idx = np.argsort(np.abs(eigvals_C))[::-1]
eigvals_C = eigvals_C[idx]
eigvecs_C = eigvecs_C[:, idx]

rho_C = spectral_radius(C)
gh_C = gamma_plus_H(C)
print(f"  ρ(C)={rho_C:.3f}, γ+H(C)={gh_C:.4f}")

inits = [np.random.randn(N) * 0.5 for _ in range(30)]
for k in range(min(5, N)):
    inits.append(eigvecs_C[:, k] * 0.5)
    inits.append(-eigvecs_C[:, k] * 0.5)

unique_fps = []
for x0 in inits:
    x_star, _, conv = find_fixed_point(C, x0, damping=0.5)
    if not conv:
        continue
    is_new = True
    for uf in unique_fps:
        if np.linalg.norm(x_star - uf['x']) < 0.01:
            is_new = False
            break
    if is_new:
        D_diag = 1 - x_star**2
        A = np.diag(D_diag) @ C
        rho_A = spectral_radius(A)
        comm = commutator_norm(D_diag, C)
        unique_fps.append({
            'x': x_star.copy(),
            'norm': np.linalg.norm(x_star),
            'rho_A': rho_A,
            'comm': comm,
            'max_sat': np.max(np.abs(x_star)),
            'alignment_top': np.abs(np.dot(x_star, eigvecs_C[:, 0])) / (np.linalg.norm(x_star) + 1e-12),
        })

print(f"  Found {len(unique_fps)} unique fixed points:")
for i, fp in enumerate(unique_fps[:8]):
    print(f"    FP{i}: ||x*||={fp['norm']:.4f}, ρ(A)={fp['rho_A']:.4f}, ||[D,C]||={fp['comm']:.4f}, max|xi|={fp['max_sat']:.4f}, align_top={fp['alignment_top']:.4f}")

# All FPs have same γ+H (static C), but different x* → different x^T P x
# Fit P
X_fit = []
gh_fit = []
for _ in range(5):
    x = np.random.randn(N) * 0.5
    for t in range(200):
        x = np.tanh(C @ x)
        gh_fit.append(gh_C)
        X_fit.append(x.copy())

X_fit = np.array(X_fit)
y_fit = np.array(gh_fit)

n_feat = N * (N + 1) // 2
Phi = np.zeros((len(y_fit), n_feat))
for s in range(len(y_fit)):
    idx = 0
    for i in range(N):
        for j in range(i, N):
            Phi[s, idx] = X_fit[s, i] * X_fit[s, j]
            idx += 1

coeffs_P, _, _, _ = np.linalg.lstsq(Phi, y_fit, rcond=None)
P = np.zeros((N, N))
idx = 0
for i in range(N):
    for j in range(i, N):
        P[i, j] = coeffs_P[idx]
        P[j, i] = coeffs_P[idx]
        idx += 1

xPx_vals = [float(fp['x'] @ P @ fp['x']) for fp in unique_fps]
print(f"\n  x^T P x at each FP:")
for i, (fp, xPx) in enumerate(zip(unique_fps[:8], xPx_vals[:8])):
    print(f"    FP{i}: x^T P x = {xPx:.6f}")
if len(xPx_vals) > 1:
    print(f"  Spread: mean={np.mean(xPx_vals):.6f}, std={np.std(xPx_vals):.6f}, CV={np.std(xPx_vals)/(np.mean(xPx_vals)+1e-12):.6f}")

# ============================================================
# SAVE ALL RESULTS
# ============================================================
print("\nSaving results...")

results = {
    'exp1_phase_diagram': phase_data,
    'exp2_commutator_sd': comm_cv_data,
    'exp2_commutator_fp': fp_comm_data,
    'exp3_static': act_results,
    'exp3_r2': act_r2,
    'exp3_sd': act_sd_results,
    'exp4_multi_fp': multi_fp_summary,
}

class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.ndarray,)):
            return obj.tolist()
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        return super().default(obj)

with open('/home/phoenix/.openclaw/workspace/experiments/gpu-loop/cycle-009/results.json', 'w') as f:
    json.dump(results, f, indent=2, cls=NpEncoder)

print("Done!")
