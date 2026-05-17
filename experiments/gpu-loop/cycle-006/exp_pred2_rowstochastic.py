"""
Prediction 2: Row-stochastic normalization fixes Hebbian conservation
Prediction 3 (partial): Also runs raw Hebbian for comparison

Dynamics: x_{t+1} = tanh(C @ x_t), 200 timesteps, 50 samples
Compares: raw Hebbian vs row-stochastic Hebbian vs attention (baseline)
"""
import numpy as np
import json

np.random.seed(123)

N = 20
T = 200
N_SAMPLES = 50

def make_attention_coupling(tau=1.0):
    """Standard softmax attention coupling."""
    Q = np.random.randn(N, 4)
    K = np.random.randn(N, 4)
    scores = Q @ K.T / tau
    scores -= scores.max(axis=1, keepdims=True)
    exp_s = np.exp(scores)
    C = exp_s / exp_s.sum(axis=1, keepdims=True)
    return C

def make_hebbian_raw(x):
    """Raw Hebbian: C = x x^T (outer product)."""
    C = np.outer(x, x)
    return C

def make_hebbian_rowstochastic(x):
    """Row-stochastic Hebbian: normalize each row to sum to 1."""
    C = np.outer(x, x)
    row_sums = C.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1.0  # avoid division by zero
    C = C / row_sums
    return C

def compute_spectral_props(C):
    """Compute eigenvalue-related quantities."""
    sym_C = (C + C.T) / 2
    eigvals = np.linalg.eigvalsh(sym_C)
    eigvals = np.sort(np.real(eigvals))[::-1]
    tr_C2 = np.trace(C @ C)
    tr_C = np.trace(C)
    
    abs_eigs = np.sort(np.abs(eigvals))[::-1]
    spectral_gap = abs_eigs[0] - abs_eigs[1] if len(abs_eigs) > 1 else 0
    
    if tr_C2 > 0 and N > 0:
        rho = (tr_C ** 2) / (N * tr_C2)
    else:
        rho = 0
    
    return {
        'tr_C': float(tr_C),
        'tr_C2': float(tr_C2),
        'spectral_gap': float(spectral_gap),
        'rho': float(rho),
    }

def compute_gamma_H(C):
    """Compute spectral gap (γ) and entropy (H) from coupling matrix."""
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

def run_experiment(arch_type):
    """Run experiment for a given architecture type."""
    results = {
        'arch_type': arch_type,
        'samples': []
    }
    
    for sample in range(N_SAMPLES):
        x = np.random.randn(N) * 0.1
        
        # Build initial coupling
        if arch_type == 'attention':
            C = make_attention_coupling(tau=1.0)
        elif arch_type == 'hebbian_raw':
            C = make_hebbian_raw(x)
        elif arch_type == 'hebbian_rowstoch':
            C = make_hebbian_rowstochastic(x)
        
        trajectory = {
            'gamma': [],
            'H': [],
            'gamma_plus_H': [],
            'tr_C2': [],
            'tr_C': []
        }
        
        for t in range(T):
            gamma, H = compute_gamma_H(C)
            props = compute_spectral_props(C)
            
            trajectory['gamma'].append(gamma)
            trajectory['H'].append(H)
            trajectory['gamma_plus_H'].append(gamma + H)
            trajectory['tr_C2'].append(props['tr_C2'])
            trajectory['tr_C'].append(props['tr_C'])
            
            # Nonlinear dynamics
            x = np.tanh(C @ x)
            
            # Update coupling (slowly, α=0.05 mixing)
            if arch_type == 'hebbian_raw':
                new_C = make_hebbian_raw(x)
                C = 0.95 * C + 0.05 * new_C
            elif arch_type == 'hebbian_rowstoch':
                new_C = make_hebbian_rowstochastic(x)
                C = 0.95 * C + 0.05 * new_C
            # Attention: C is static (pre-computed from Q,K)
        
        results['samples'].append(trajectory)
    
    # Aggregate
    all_tr_C2 = np.array([np.array(s['tr_C2']) for s in results['samples']])
    all_gh = np.array([np.array(s['gamma_plus_H']) for s in results['samples']])
    all_gamma = np.array([np.array(s['gamma']) for s in results['samples']])
    all_H = np.array([np.array(s['H']) for s in results['samples']])
    
    temporal_cv_trC2 = float(np.mean(np.std(all_tr_C2, axis=1) / (np.mean(all_tr_C2, axis=1) + 1e-10)))
    temporal_cv_gh = float(np.mean(np.std(all_gh, axis=1) / (np.mean(all_gh, axis=1) + 1e-10)))
    
    # Steady-state (last 50)
    ss_trC2 = float(all_tr_C2[:, -50:].mean())
    ss_gh = float(all_gh[:, -50:].mean())
    
    # Cross-sample CV
    cross_cv_trC2 = float(np.std(all_tr_C2[:, -1]) / (np.mean(all_tr_C2[:, -1]) + 1e-10))
    cross_cv_gh = float(np.std(all_gh[:, -1]) / (np.mean(all_gh[:, -1]) + 1e-10))
    
    # γ-H correlation
    gh_corrs = []
    for i in range(N_SAMPLES):
        r = np.corrcoef(all_gamma[i], all_H[i])[0, 1]
        gh_corrs.append(r)
    
    results['summary'] = {
        'arch_type': arch_type,
        'temporal_cv_trC2': temporal_cv_trC2,
        'temporal_cv_gh': temporal_cv_gh,
        'steady_state_trC2': ss_trC2,
        'steady_state_gh': ss_gh,
        'cross_sample_cv_trC2': cross_cv_trC2,
        'cross_sample_cv_gh': cross_cv_gh,
        'mean_gamma_H_corr': float(np.mean(gh_corrs)),
        'std_gamma_H_corr': float(np.std(gh_corrs)),
    }
    
    return results

def main():
    architectures = ['attention', 'hebbian_raw', 'hebbian_rowstoch']
    all_summaries = {}
    
    for arch in architectures:
        print(f"\nRunning {arch}...")
        res = run_experiment(arch)
        s = res['summary']
        all_summaries[arch] = s
        print(f"  CV(TrC²)={s['temporal_cv_trC2']:.6f}, CV(γ+H)={s['temporal_cv_gh']:.6f}, "
              f"SS_TrC²={s['steady_state_trC2']:.4f}, γ-H r={s['mean_gamma_H_corr']:.3f}")
    
    # Key comparison
    print("\n=== PREDICTION 2: Row-stochastic normalization fixes Hebbian ===")
    raw_cv = all_summaries['hebbian_raw']['temporal_cv_gh']
    rs_cv = all_summaries['hebbian_rowstoch']['temporal_cv_gh']
    att_cv = all_summaries['attention']['temporal_cv_gh']
    
    improvement = raw_cv / (rs_cv + 1e-10)
    print(f"  Raw Hebbian CV(γ+H): {raw_cv:.4f}")
    print(f"  Row-stoch Hebbian CV(γ+H): {rs_cv:.4f}")
    print(f"  Attention CV(γ+H): {att_cv:.4f}")
    print(f"  Improvement factor: {improvement:.1f}×")
    
    if rs_cv < 0.02 and improvement >= 5.0:
        print("  ✓ PREDICTION CONFIRMED: Row-stochastic Hebbian CV < 0.02 with 5×+ improvement")
    elif rs_cv < raw_cv:
        print(f"  ~ PARTIAL: Row-stochastic improves by {improvement:.1f}× but target CV < 0.02 not met")
    else:
        print("  ✗ PREDICTION FALSIFIED: Row-stochastic does NOT improve conservation")
    
    # Save
    with open('/home/phoenix/.openclaw/workspace/experiments/gpu-loop/cycle-006/pred2_results.json', 'w') as f:
        json.dump(all_summaries, f, indent=2)
    
    return all_summaries

if __name__ == '__main__':
    main()
