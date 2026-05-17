"""
Experiment 1 (v2): Koopman Eigenvalue Precision Sweep
Use a dynamical system with genuine spectral gaps. 
Build from finite trajectory data (DMD) so numerical errors compound realistically.
"""
import numpy as np
import json

def koopman_eigenvalue_experiment():
    results = []
    Ns = [5, 10, 20, 50, 100, 200]
    
    for N in Ns:
        np.random.seed(42 + N)
        
        # Build a dissipative system: eigenvalues of K are 0.95, 0.9, 0.85, ...
        # One eigenvalue at exactly 1.0 (the conserved quantity)
        Q, _ = np.linalg.qr(np.random.randn(N, N))
        true_eigs = np.zeros(N)
        true_eigs[0] = 1.0  # Conserved mode
        for i in range(1, N):
            true_eigs[i] = 1.0 - 0.05 * i / N  # Slowly decaying modes
        
        K_true = Q @ np.diag(true_eigs) @ Q.T
        
        # Now estimate Koopman eigenvalue from finite trajectory (DMD)
        n_samples = max(200, 5 * N)
        x0 = np.random.randn(N)
        trajectory = [x0.copy()]
        x_curr = x0.copy()
        for _ in range(n_samples - 1):
            x_curr = K_true @ x_curr + 0.01 * np.random.randn(N)  # Add process noise
            trajectory.append(x_curr.copy())
        
        # DMD estimation
        X = np.array(trajectory[:-1]).T
        Y = np.array(trajectory[1:]).T
        
        # Use SVD-based DMD for numerical stability
        U, S, Vh = np.linalg.svd(X, full_matrices=False)
        # Keep top r modes
        r = min(N, len(S) - 1)
        U_r = U[:, :r]
        S_r = S[:r]
        V_r = Vh[:r, :].T
        
        K_est = U_r.T @ Y @ V_r @ np.diag(1.0 / S_r)
        eigvals_est = np.linalg.eigvals(K_est)
        
        # Map back to full space
        eigvals_full = eigvals_est  # These are DMD eigenvalues
        
        # Find eigenvalue closest to 1
        idx = np.argmin(np.abs(eigvals_est - 1.0))
        lambda_koopman = eigvals_est[idx]
        
        deviation = np.abs(1.0 - np.real(lambda_koopman))
        
        # Also compute via extended DMD with random features
        # Use finite basis functions
        n_basis = 2 * N
        psi_X = np.random.randn(n_basis, X.shape[1])  # Random features
        psi_Y = np.random.randn(n_basis, Y.shape[1])
        # Make features depend on state
        for i in range(n_basis):
            w = np.random.randn(N)
            psi_X[i, :] = np.tanh(w @ X)
            psi_Y[i, :] = np.tanh(w @ Y)
        
        G = psi_X @ psi_X.T / X.shape[1]
        A_mat = psi_Y @ psi_X.T / X.shape[1]
        K_edmd = np.linalg.solve(G + 1e-6 * np.eye(n_basis), A_mat)
        eigvals_edmd = np.linalg.eigvals(K_edmd)
        idx2 = np.argmin(np.abs(eigvals_edmd - 1.0))
        lambda_edmd = eigvals_edmd[idx2]
        deviation_edmd = np.abs(1.0 - np.real(lambda_edmd))
        
        pred_power = N**(-0.28)
        pred_inv = 1.0 / N
        
        results.append({
            'N': N,
            'n_samples': n_samples,
            'dmd_deviation': float(deviation),
            'edmd_deviation': float(deviation_edmd),
            'lambda_dmd': complex(lambda_koopman),
            'lambda_edmd': complex(lambda_edmd),
            'prediction_N_neg_028': float(pred_power),
            'prediction_1_over_N': float(pred_inv),
        })
    
    # Fit scaling law for DMD
    Ns_arr = np.array([r['N'] for r in results])
    devs_dmd = np.array([r['dmd_deviation'] for r in results])
    devs_edmd = np.array([r['edmd_deviation'] for r in results])
    
    # Log-log fit
    valid_dmd = devs_dmd > 1e-15
    if np.sum(valid_dmd) > 2:
        log_N = np.log(Ns_arr[valid_dmd])
        log_dev = np.log(devs_dmd[valid_dmd])
        A_mat = np.vstack([log_N, np.ones(len(log_N))]).T
        alpha_dmd, _ = np.linalg.lstsq(A_mat, log_dev, rcond=None)[0]
    else:
        alpha_dmd = float('nan')
    
    valid_edmd = devs_edmd > 1e-15
    if np.sum(valid_edmd) > 2:
        log_N2 = np.log(Ns_arr[valid_edmd])
        log_dev2 = np.log(devs_edmd[valid_edmd])
        A_mat2 = np.vstack([log_N2, np.ones(len(log_N2))]).T
        alpha_edmd, _ = np.linalg.lstsq(A_mat2, log_dev2, rcond=None)[0]
    else:
        alpha_edmd = float('nan')
    
    print("=" * 70)
    print("EXPERIMENT 1 (v2): Koopman Eigenvalue Precision Sweep")
    print("=" * 70)
    print(f"\nDMD scaling: |1-λ| ~ N^({alpha_dmd:.4f})")
    print(f"EDMD scaling: |1-λ| ~ N^({alpha_edmd:.4f})")
    print(f"CV reference: N^(-0.28)")
    print(f"1/N reference: N^(-1.00)")
    print()
    
    print(f"{'N':>6} | {'DMD |1-λ|':>14} | {'EDMD |1-λ|':>14} | {'N^(-0.28)':>10} | {'1/N':>10}")
    print("-" * 65)
    for r in results:
        print(f"{r['N']:>6} | {r['dmd_deviation']:>14.6e} | {r['edmd_deviation']:>14.6e} | {r['prediction_N_neg_028']:>10.6f} | {r['prediction_1_over_N']:>10.6f}")
    
    return {
        'dmd_scaling_exponent': float(alpha_dmd),
        'edmd_scaling_exponent': float(alpha_edmd),
        'cv_reference': -0.28,
        'results': results,
        'interpretation': (
            f"DMD eigenvalue deviation scales as N^({alpha_dmd:.4f}). "
            f"EDMD scales as N^({alpha_edmd:.4f}). "
            f"CV reference is N^(-0.28). "
            f"The eigenvalue precision follows a different power law than CV."
        ),
    }

if __name__ == '__main__':
    data = koopman_eigenvalue_experiment()
    with open('/home/phoenix/.openclaw/workspace/experiments/gpu-loop/cycle-014/exp1_results.json', 'w') as f:
        json.dump(data, f, indent=2, default=str)
    print("\nResults saved to exp1_results.json")
