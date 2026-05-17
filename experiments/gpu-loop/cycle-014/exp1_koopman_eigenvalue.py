"""
Experiment 1: Koopman Eigenvalue Precision Sweep
For N=5,10,20,50,100,200 compute |1-λ| for the dominant Koopman eigenvalue.
How does it scale with N? Compare to N^{-0.28} scaling found for CV.
"""
import numpy as np
import json

def koopman_eigenvalue_experiment():
    results = []
    Ns = [5, 10, 20, 50, 100, 200, 500]
    
    for N in Ns:
        # Build a random Koopman matrix (dynamics matrix) with spectral radius < 1
        # Simulate a discrete dynamical system K: x_{n+1} = K x_n
        # The Koopman operator's dominant eigenvalue should be near 1 for conserved quantities
        
        # Method: Build K from a nearly-conservative system with small dissipation
        # Use: K = I - (1/N) * A where A is a random symmetric positive semi-definite matrix
        # This gives eigenvalues near 1 with deviation ~ O(1/N)
        
        np.random.seed(42)
        # Random orthonormal basis
        Q, _ = np.linalg.qr(np.random.randn(N, N))
        # Eigenvalues: one at exactly 1 (conserved), rest near 1 with small gaps
        # Physically: Koopman operator for a weakly dissipative system
        true_eigenvalues = np.ones(N)
        for i in range(1, N):
            true_eigenvalues[i] = 1.0 - (i / N)**0.5 * 0.01  # Small deviations
        
        K = Q @ np.diag(true_eigenvalues) @ Q.T
        
        # Now estimate the dominant eigenvalue numerically via power iteration
        # (simulating finite-sample estimation)
        n_samples = 1000
        x = np.random.randn(N)
        x /= np.linalg.norm(x)
        
        # Power iteration to find dominant eigenvalue
        for _ in range(100):
            x = K @ x
            x /= np.linalg.norm(x)
        
        lambda_dom = x @ K @ x  # Rayleigh quotient
        
        # Also compute via DMD (Dynamic Mode Decomposition) from trajectory
        x0 = np.random.randn(N)
        x0 /= np.linalg.norm(x0)
        trajectory = [x0.copy()]
        x_curr = x0.copy()
        for _ in range(n_samples - 1):
            x_curr = K @ x_curr
            trajectory.append(x_curr.copy())
        
        X = np.array(trajectory[:-1]).T  # N x (T-1)
        Y = np.array(trajectory[1:]).T   # N x (T-1)
        
        # DMD: K_est = Y X^+ (pseudoinverse)
        K_est = Y @ np.linalg.pinv(X)
        
        # Eigenvalues of K_est
        eigvals = np.linalg.eigvals(K_est)
        # Find eigenvalue closest to 1
        idx = np.argmin(np.abs(eigvals - 1.0))
        lambda_koopman = eigvals[idx]
        
        deviation = np.abs(1.0 - lambda_koopman)
        phase = np.angle(lambda_koopman)
        
        # Compute analytical scaling prediction
        pred_power = N**(-0.28)
        pred_inv = 1.0 / N
        
        results.append({
            'N': N,
            'lambda_koopman_real': float(np.real(lambda_koopman)),
            'lambda_koopman_imag': float(np.imag(lambda_koopman)),
            'deviation_abs': float(deviation),
            'phase': float(phase),
            'prediction_N_neg_028': float(pred_power),
            'prediction_1_over_N': float(pred_inv),
            'ratio_dev_to_N_neg_028': float(deviation / pred_power) if pred_power > 0 else float('inf'),
        })
    
    # Fit scaling law
    Ns_arr = np.array([r['N'] for r in results])
    devs = np.array([r['deviation_abs'] for r in results])
    
    # Log-log fit: log(dev) = alpha * log(N) + const
    log_N = np.log(Ns_arr)
    log_dev = np.log(devs + 1e-16)
    
    # Linear regression
    A = np.vstack([log_N, np.ones(len(log_N))]).T
    alpha, const = np.linalg.lstsq(A, log_dev, rcond=None)[0]
    
    print("=" * 70)
    print("EXPERIMENT 1: Koopman Eigenvalue Precision Sweep")
    print("=" * 70)
    print(f"\nFitted scaling: |1-λ| ~ N^({alpha:.4f})")
    print(f"Compare: CV scales as N^(-0.28)")
    print(f"Compare: 1/N scales as N^(-1.00)")
    print()
    
    print(f"{'N':>6} | {'|1-λ|':>12} | {'N^{-0.28}':>12} | {'1/N':>12} | {'ratio':>8}")
    print("-" * 65)
    for r in results:
        print(f"{r['N']:>6} | {r['deviation_abs']:>12.6e} | {r['prediction_N_neg_028']:>12.6e} | {r['prediction_1_over_N']:>12.6e} | {r['ratio_dev_to_N_neg_028']:>8.4f}")
    
    return {
        'scaling_exponent': float(alpha),
        'scaling_constant': float(const),
        'results': results,
        'interpretation': f"Koopman eigenvalue deviation scales as N^({alpha:.4f}), compared to N^(-0.28) for CV"
    }

if __name__ == '__main__':
    data = koopman_eigenvalue_experiment()
    with open('/home/phoenix/.openclaw/workspace/experiments/gpu-loop/cycle-014/exp1_results.json', 'w') as f:
        json.dump(data, f, indent=2)
    print("\nResults saved to exp1_results.json")
