"""
Prediction 5: Two-moment regression — γ+H = a·Tr(C) + b·Tr(C²) + c
Tests across: multiple architectures, temperatures, N values
Dynamics: x_{t+1} = tanh(C @ x_t), 200 timesteps, 50 samples per condition
"""
import numpy as np
import json
from itertools import product

np.random.seed(456)

T = 200
N_SAMPLES = 50

def make_attention_coupling(n, tau=1.0):
    Q = np.random.randn(n, max(4, n//5))
    K = np.random.randn(n, max(4, n//5))
    scores = Q @ K.T / tau
    scores -= scores.max(axis=1, keepdims=True)
    exp_s = np.exp(scores)
    C = exp_s / exp_s.sum(axis=1, keepdims=True)
    return C

def make_random_coupling(n):
    """GOE random coupling."""
    W = np.random.randn(n, n) / np.sqrt(n)
    C = (W + W.T) / (2 * np.sqrt(n))
    # Make row-stochastic
    C = np.abs(C)
    row_sums = C.sum(axis=1, keepdims=True)
    C = C / row_sums
    return C

def make_hebbian_raw_coupling(n, x):
    return np.outer(x, x)

def make_hebbian_rowstoch_coupling(n, x):
    C = np.outer(x, x)
    C = np.abs(C)  # ensure non-negative
    row_sums = C.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1.0
    return C / row_sums

def compute_gamma_H(C):
    sym_C = (C + C.T) / 2
    eigvals = np.linalg.eigvalsh(sym_C)
    abs_eigs = np.sort(np.abs(eigvals))[::-1]
    gamma = float(abs_eigs[0] - abs_eigs[1]) if len(abs_eigs) > 1 else 0
    
    eig_positive = np.abs(eigvals)
    total = eig_positive.sum()
    if total > 0:
        p = eig_positive / total
        p = p[p > 1e-15]
        H = float(-np.sum(p * np.log(p)))
    else:
        H = 0
    return gamma, H

def compute_traces(C):
    return float(np.trace(C)), float(np.trace(C @ C))

def run_single(n, arch, tau=None):
    """Run one sample and return time series of (Tr(C), Tr(C²), γ+H)."""
    x = np.random.randn(n) * 0.1
    
    if arch == 'attention':
        C = make_attention_coupling(n, tau or 1.0)
    elif arch == 'random':
        C = make_random_coupling(n)
    elif arch == 'hebbian_raw':
        C = make_hebbian_raw_coupling(n, x)
    elif arch == 'hebbian_rowstoch':
        C = make_hebbian_rowstoch_coupling(n, x)
    
    records = {'tr_C': [], 'tr_C2': [], 'gamma_plus_H': [], 'gamma': [], 'H': []}
    
    for t in range(T):
        gamma, H = compute_gamma_H(C)
        tr_C, tr_C2 = compute_traces(C)
        
        records['tr_C'].append(tr_C)
        records['tr_C2'].append(tr_C2)
        records['gamma_plus_H'].append(gamma + H)
        records['gamma'].append(gamma)
        records['H'].append(H)
        
        # Nonlinear dynamics
        x = np.tanh(C @ x)
        
        # Update coupling for dynamic architectures
        if arch == 'hebbian_raw':
            new_C = make_hebbian_raw_coupling(n, x)
            C = 0.95 * C + 0.05 * new_C
        elif arch == 'hebbian_rowstoch':
            new_C = make_hebbian_rowstoch_coupling(n, x)
            C = 0.95 * C + 0.05 * new_C
        # attention and random: static C
    
    return records

def main():
    # Configuration matrix
    configs = []
    
    # Architecture sweep at N=20
    for arch in ['attention', 'random', 'hebbian_raw', 'hebbian_rowstoch']:
        configs.append({'n': 20, 'arch': arch, 'tau': 1.0})
    
    # Temperature sweep (attention only)
    for tau in [0.1, 0.5, 2.0, 5.0, 10.0]:
        configs.append({'n': 20, 'arch': 'attention', 'tau': tau})
    
    # Size sweep (attention, tau=1.0)
    for n in [10, 30, 50]:
        configs.append({'n': n, 'arch': 'attention', 'tau': 1.0})
    
    # Collect all data
    all_tr_C = []
    all_tr_C2 = []
    all_gh = []
    all_tr_C3 = []
    
    config_results = []
    
    for cfg in configs:
        n, arch, tau = cfg['n'], cfg['arch'], cfg['tau']
        label = f"{arch}_n{n}_tau{tau}"
        print(f"Running {label}...")
        
        cfg_tr_C = []
        cfg_tr_C2 = []
        cfg_gh = []
        cfg_tr_C3 = []
        
        for s in range(N_SAMPLES):
            rec = run_single(n, arch, tau)
            
            # Use steady-state only (last 100 timesteps)
            for t in range(T // 2, T):
                cfg_tr_C.append(rec['tr_C'][t])
                cfg_tr_C2.append(rec['tr_C2'][t])
                cfg_gh.append(rec['gamma_plus_H'][t])
                
                # Tr(C³) for third-moment test
                C_approx = np.eye(n) * 0.1  # We don't have C saved, use Tr(C²) as proxy
                # Actually compute Tr(C³) from stored eigenvalue trace
                # We'll approximate: Tr(C³) ≈ Tr(C)³ for near-identity... not great
                # Let's just skip Tr(C³) for now and do the two-moment regression
        
        all_tr_C.extend(cfg_tr_C)
        all_tr_C2.extend(cfg_tr_C2)
        all_gh.extend(cfg_gh)
        
        config_results.append({
            'label': label,
            'n': n, 'arch': arch, 'tau': tau,
            'n_points': len(cfg_tr_C),
            'mean_tr_C': float(np.mean(cfg_tr_C)),
            'mean_tr_C2': float(np.mean(cfg_tr_C2)),
            'mean_gh': float(np.mean(cfg_gh)),
        })
    
    all_tr_C = np.array(all_tr_C)
    all_tr_C2 = np.array(all_tr_C2)
    all_gh = np.array(all_gh)
    
    print(f"\nTotal data points: {len(all_tr_C)}")
    
    # === Two-moment regression: γ+H = a + b·Tr(C) + c·Tr(C²) ===
    X = np.column_stack([np.ones(len(all_tr_C)), all_tr_C, all_tr_C2])
    y = all_gh
    
    # OLS
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    y_pred = X @ beta
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2_both = 1 - ss_res / ss_tot
    
    print(f"\n=== TWO-MOMENT REGRESSION: γ+H = a + b·Tr(C) + c·Tr(C²) ===")
    print(f"  a (intercept) = {beta[0]:.6f}")
    print(f"  b (Tr(C) coeff) = {beta[1]:.6f}")
    print(f"  c (Tr(C²) coeff) = {beta[2]:.6f}")
    print(f"  R² = {r2_both:.4f}")
    
    # Single-moment regressions
    X_trC = np.column_stack([np.ones(len(all_tr_C)), all_tr_C])
    beta_trC = np.linalg.lstsq(X_trC, y, rcond=None)[0]
    y_pred_trC = X_trC @ beta_trC
    r2_trC = 1 - np.sum((y - y_pred_trC) ** 2) / ss_tot
    
    X_trC2 = np.column_stack([np.ones(len(all_tr_C2)), all_tr_C2])
    beta_trC2 = np.linalg.lstsq(X_trC2, y, rcond=None)[0]
    y_pred_trC2 = X_trC2 @ beta_trC2
    r2_trC2 = 1 - np.sum((y - y_pred_trC2) ** 2) / ss_tot
    
    print(f"\n  Tr(C) only: R² = {r2_trC:.4f}")
    print(f"  Tr(C²) only: R² = {r2_trC2:.4f}")
    print(f"  Both: R² = {r2_both:.4f}")
    print(f"  Incremental from Tr(C²) over Tr(C): ΔR² = {r2_both - r2_trC:.4f}")
    
    # Residual analysis
    residuals = y - y_pred
    print(f"\n  Residual stats: mean={np.mean(residuals):.6f}, std={np.std(residuals):.6f}")
    print(f"  Residual range: [{np.min(residuals):.4f}, {np.max(residuals):.4f}]")
    
    # Check for systematic pattern in residuals
    for cfg in config_results:
        label = cfg['label']
        # This is approximate since we mixed all data
    
    # Verdict
    if r2_both > 0.95:
        print("\n  ✓ PREDICTION CONFIRMED: R² > 0.95 — two moments explain γ+H")
    elif r2_both > 0.80:
        print(f"\n  ~ PARTIAL: R² = {r2_both:.4f} — two moments have predictive power but < 0.95 target")
    else:
        print(f"\n  ✗ PREDICTION FALSIFIED: R² = {r2_both:.4f} — two moments insufficient")
    
    # Per-config R²
    print("\n=== PER-CONFIG REGRESSION ===")
    offset = 0
    for cfg in config_results:
        n_pts = cfg['n_points']
        cfg_tr_C_local = all_tr_C[offset:offset+n_pts]
        cfg_tr_C2_local = all_tr_C2[offset:offset+n_pts]
        cfg_gh_local = all_gh[offset:offset+n_pts]
        
        X_local = np.column_stack([np.ones(n_pts), cfg_tr_C_local, cfg_tr_C2_local])
        try:
            beta_local = np.linalg.lstsq(X_local, cfg_gh_local, rcond=None)[0]
            y_pred_local = X_local @ beta_local
            ss_res_local = np.sum((cfg_gh_local - y_pred_local) ** 2)
            ss_tot_local = np.sum((cfg_gh_local - np.mean(cfg_gh_local)) ** 2)
            r2_local = 1 - ss_res_local / ss_tot_local if ss_tot_local > 0 else 0
        except:
            r2_local = -1
        
        print(f"  {cfg['label']}: R²={r2_local:.4f}, Tr(C)={cfg['mean_tr_C']:.2f}, Tr(C²)={cfg['mean_tr_C2']:.2f}, γ+H={cfg['mean_gh']:.4f}")
        offset += n_pts
    
    # Save
    save_data = {
        'overall': {
            'r2_both': float(r2_both),
            'r2_trC': float(r2_trC),
            'r2_trC2': float(r2_trC2),
            'coefficients': {
                'intercept': float(beta[0]),
                'b_trC': float(beta[1]),
                'c_trC2': float(beta[2]),
            },
            'n_points': len(all_tr_C),
            'residual_mean': float(np.mean(residuals)),
            'residual_std': float(np.std(residuals)),
        },
        'config_results': config_results,
    }
    
    with open('/home/phoenix/.openclaw/workspace/experiments/gpu-loop/cycle-006/pred5_results.json', 'w') as f:
        json.dump(save_data, f, indent=2)
    
    return save_data

if __name__ == '__main__':
    main()
