"""
Experiment 2: Supermartingale Decay Rate vs Activation
Measure α (exponential decay rate) for all 7 activations.
Test correlation with Lipschitz constant.
"""
import numpy as np
import json

def supermartingale_experiment():
    # 7 activations and their properties
    activations = {
        'relu': {
            'fn': lambda x: np.maximum(0, x),
            'lipschitz': 1.0,
            'smooth': False,
        },
        'gelu': {
            'fn': lambda x: 0.5 * x * (1 + np.tanh(np.sqrt(2/np.pi) * (x + 0.044715 * x**3))),
            'lipschitz': 1.0,  # Approximate
            'smooth': True,
        },
        'silu': {
            'fn': lambda x: x / (1 + np.exp(-x)),
            'lipschitz': 1.0,  # Sup of sigmoid*(1+sigmoid*x) is bounded
            'smooth': True,
        },
        'tanh': {
            'fn': lambda x: np.tanh(x),
            'lipschitz': 1.0,
            'smooth': True,
        },
        'sigmoid': {
            'fn': lambda x: 1 / (1 + np.exp(-x)),
            'lipschitz': 0.25,  # Max derivative
            'smooth': True,
        },
        'softplus': {
            'fn': lambda x: np.log(1 + np.exp(x)),
            'lipschitz': 1.0,
            'smooth': True,
        },
        'mish': {
            'fn': lambda x: x * np.tanh(np.log(1 + np.exp(x))),
            'lipschitz': 1.0,  # Approximate
            'smooth': True,
        },
    }
    
    results = {}
    
    for name, act in activations.items():
        # Simulate a supermartingale: E[V_{n+1} | F_n] <= α * V_n
        # We model this as a neural network layer with the given activation
        # V(x) = ||x||^2 as Lyapunov function
        
        # Build: x_{n+1} = σ(W x_n) where W is random with spectral radius ρ
        # The decay rate depends on activation contractivity
        
        np.random.seed(42)
        N = 50  # State dimension
        n_trials = 10000
        n_steps = 100
        
        # Random weight matrix with controlled spectral radius
        W = np.random.randn(N, N) / np.sqrt(N)
        
        alphas = []
        for trial in range(n_trials):
            x = np.random.randn(N)
            x /= np.linalg.norm(x)
            
            vs = [np.linalg.norm(x)**2]
            for step in range(n_steps):
                x = act['fn'](W @ x)
                vs.append(np.linalg.norm(x)**2)
            
            vs = np.array(vs[1:])  # Skip initial
            # Fit exponential decay: V_n ~ V_0 * α^n
            # log(V_n) = log(V_0) + n * log(α)
            vs_pos = vs[vs > 0]
            if len(vs_pos) > 10:
                log_vs = np.log(vs_pos)
                ns = np.arange(1, len(vs_pos) + 1)
                A_mat = np.vstack([ns, np.ones(len(ns))]).T
                slope, _ = np.linalg.lstsq(A_mat, log_vs, rcond=None)[0]
                if slope < 0:  # Decay
                    alphas.append(np.exp(slope))
        
        if alphas:
            mean_alpha = np.mean(alphas)
            std_alpha = np.std(alphas)
        else:
            mean_alpha = float('nan')
            std_alpha = float('nan')
        
        # Also compute empirical Lipschitz estimate via gradient
        x_test = np.random.randn(1000, N) * 0.1
        eps = 1e-5
        grad_norms = []
        for i in range(min(100, len(x_test))):
            x0 = x_test[i]
            dx = eps * np.random.randn(N)
            lhs = np.linalg.norm(act['fn'](W @ (x0 + dx)) - act['fn'](W @ x0))
            rhs = np.linalg.norm(dx) * act['lipschitz'] * np.linalg.norm(W, ord=2)
            if rhs > 0:
                grad_norms.append(lhs / rhs)
        
        empirical_contractivity = np.mean(grad_norms) if grad_norms else float('nan')
        
        results[name] = {
            'lipschitz_constant': act['lipschitz'],
            'smooth': act['smooth'],
            'decay_rate_alpha': float(mean_alpha),
            'decay_rate_std': float(std_alpha),
            'empirical_contractivity': float(empirical_contractivity),
            'n_trials': len(alphas),
        }
    
    # Correlation analysis
    lipschitz_arr = []
    alpha_arr = []
    contract_arr = []
    names_arr = []
    for name, r in results.items():
        lipschitz_arr.append(r['lipschitz_constant'])
        alpha_arr.append(r['decay_rate_alpha'])
        contract_arr.append(r['empirical_contractivity'])
        names_arr.append(name)
    
    # Pearson correlation: Lipschitz vs alpha
    l_a = np.array(lipschitz_arr)
    a_a = np.array(alpha_arr)
    c_a = np.array(contract_arr)
    
    if np.std(l_a) > 0:
        corr_lip_alpha = np.corrcoef(l_a, a_a)[0, 1]
    else:
        corr_lip_alpha = float('nan')
    
    corr_contract_alpha = np.corrcoef(c_a, a_a)[0, 1] if np.std(c_a) > 0 else float('nan')
    
    print("=" * 70)
    print("EXPERIMENT 2: Supermartingale Decay Rate vs Activation")
    print("=" * 70)
    print(f"\nCorrelation (Lipschitz constant vs α): {corr_lip_alpha:.4f}")
    print(f"Correlation (empirical contractivity vs α): {corr_contract_alpha:.4f}")
    print()
    print(f"{'Activation':>12} | {'Lipschitz':>10} | {'α (decay)':>10} | {'α std':>10} | {'Contract':>10}")
    print("-" * 65)
    for name in names_arr:
        r = results[name]
        print(f"{name:>12} | {r['lipschitz_constant']:>10.4f} | {r['decay_rate_alpha']:>10.6f} | {r['decay_rate_std']:>10.6f} | {r['empirical_contractivity']:>10.6f}")
    
    return {
        'correlation_lipschitz_alpha': float(corr_lip_alpha),
        'correlation_contractivity_alpha': float(corr_contract_alpha),
        'activations': results,
    }

if __name__ == '__main__':
    data = supermartingale_experiment()
    with open('/home/phoenix/.openclaw/workspace/experiments/gpu-loop/cycle-014/exp2_results.json', 'w') as f:
        json.dump(data, f, indent=2)
    print("\nResults saved to exp2_results.json")
