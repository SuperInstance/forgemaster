#!/usr/bin/env python3
"""
GPU Loop Cycle 5 v2 — PROPER nonlinear dynamics
Fix: Use state-dependent coupling, noise injection, and multi-agent dynamics
so that γ+H has room to VARY. If it doesn't vary, we can't measure conservation.
"""

import numpy as np
import json
import os

np.random.seed(42)

# ============================================================
# Metrics
# ============================================================
def spectral_entropy(eigenvalues):
    pos = eigenvalues[eigenvalues > 1e-12]
    if len(pos) == 0:
        return 0.0
    p = pos / pos.sum()
    return -np.sum(p * np.log(p + 1e-30))

def compute_metrics(C, x=None):
    eigvals = np.linalg.eigvalsh(C)
    eigvals_abs = np.sort(np.abs(eigvals))[::-1]
    gamma = eigvals_abs[0] - eigvals_abs[1] if len(eigvals_abs) > 1 else eigvals_abs[0]
    H = spectral_entropy(eigvals)
    tr_c2 = np.real(np.trace(C @ C))
    tr_c = np.real(np.trace(C))
    rho = tr_c**2 / (C.shape[0] * tr_c2) if tr_c2 > 1e-12 else 0
    return {
        'gamma': gamma,
        'H': H,
        'gamma_plus_H': gamma + H,
        'tr_c2': tr_c2,
        'tr_c': tr_c,
        'rho': rho,
        'top_eig': eigvals_abs[0],
        'second_eig': eigvals_abs[1] if len(eigvals_abs) > 1 else 0,
    }

def analyze_trajectory(history, warmup=20):
    """Analyze conservation from a trajectory of metrics dicts."""
    gh = np.array([h['gamma_plus_H'] for h in history[warmup:]])
    tr_c2 = np.array([h['tr_c2'] for h in history[warmup:]])
    gamma = np.array([h['gamma'] for h in history[warmup:]])
    H = np.array([h['H'] for h in history[warmup:]])
    
    mask = np.isfinite(gh) & np.isfinite(tr_c2) & (gh > 0)
    if mask.sum() < 10:
        return None
    
    gh, tr_c2, gamma, H = gh[mask], tr_c2[mask], gamma[mask], H[mask]
    
    gh_cv = np.std(gh) / (np.mean(gh) + 1e-15)
    tr_c2_cv = np.std(tr_c2) / (np.mean(tr_c2) + 1e-15)
    
    gh_corr = np.corrcoef(gamma, H)[0,1] if (np.std(gamma) > 1e-15 and np.std(H) > 1e-15) else 0.0
    trc2_gh_corr = np.corrcoef(tr_c2, gh)[0,1] if (np.std(tr_c2) > 1e-15 and np.std(gh) > 1e-15) else 0.0
    
    return {
        'gh_mean': float(np.mean(gh)),
        'gh_std': float(np.std(gh)),
        'gh_cv': float(gh_cv),
        'gh_range': float(np.ptp(gh)),
        'tr_c2_mean': float(np.mean(tr_c2)),
        'tr_c2_std': float(np.std(tr_c2)),
        'tr_c2_cv': float(tr_c2_cv),
        'gamma_mean': float(np.mean(gamma)),
        'H_mean': float(np.mean(H)),
        'gh_H_corr': float(gh_corr),
        'trc2_gh_corr': float(trc2_gh_corr),
        'n_points': int(mask.sum()),
    }

# ============================================================
# Matrix generators
# ============================================================
def softmax_attention(N, temperature=1.0, seed=0):
    rng = np.random.RandomState(seed)
    Q = rng.randn(N, N)
    K = rng.randn(N, N)
    scores = Q @ K.T / np.sqrt(N)
    exp_s = np.exp(scores / temperature - np.max(scores / temperature, axis=1, keepdims=True))
    return exp_s / exp_s.sum(axis=1, keepdims=True)

def random_symmetric(N, seed=0):
    rng = np.random.RandomState(seed)
    A = rng.randn(N, N)
    return (A + A.T) / (2 * np.sqrt(N))

def normalize_hebbian(x):
    """Row-stochastic Hebbian: C_ij = |x_i||x_j|, normalize rows."""
    C = np.outer(np.abs(x), np.abs(x)) + 1e-10
    return C / C.sum(axis=1, keepdims=True)

# ============================================================
# EXP 1: State-Dependent Coupling with Noise
# ============================================================
def exp1_state_dependent():
    """
    x_{t+1} = tanh(C(x_t) @ x_t + η_t)
    C(x_t) depends on architecture. η_t is noise to prevent trivial convergence.
    
    Key: C EVOLVES with state, so γ+H has room to vary.
    """
    print("\n" + "="*60)
    print("EXP-1: State-Dependent Coupling with Noise Injection")
    print("="*60)
    
    N = 20
    n_steps = 500
    warmup = 50
    noise_std = 0.1
    n_samples = 20
    
    def run_architecture(name, make_C, x0):
        histories = []
        for s in range(n_samples):
            rng = np.random.RandomState(s * 1000)
            x = x0(s).copy()
            history = []
            
            for t in range(n_steps):
                C = make_C(x, s, t)
                metrics = compute_metrics(C)
                history.append(metrics)
                
                # Nonlinear update with noise
                eta = rng.randn(N) * noise_std
                x = np.tanh(C @ x + eta)
            
            result = analyze_trajectory(history, warmup=warmup)
            if result is not None:
                histories.append(result)
        
        if not histories:
            print(f"  {name:30s} | NO VALID RUNS")
            return None
        
        avg = lambda k: np.mean([h[k] for h in histories])
        print(f"  {name:30s} | CV(γ+H)={avg('gh_cv'):.4f} | CV(TrC²)={avg('tr_c2_cv'):.4f} | "
              f"r(γ,H)={avg('gh_H_corr'):+.3f} | r(TrC²,γ+H)={avg('trc2_gh_corr'):+.3f} | "
              f"⟨γ+H⟩={avg('gh_mean'):.3f} | range={avg('gh_range'):.3f}")
        return {k: float(avg(k)) for k in histories[0].keys()}
    
    results = {}
    
    # (a) Attention-based coupling from state
    results['attention_state'] = run_architecture(
        "Attention (state-dep)",
        lambda x, s, t: softmax_attention(N, 1.0, seed=int(np.sum(np.abs(x)*100)) % 100000),
        lambda s: np.random.RandomState(s*200).randn(N)
    )
    
    # (b) Hebbian coupling from state (raw)
    results['hebbian_raw'] = run_architecture(
        "Hebbian raw (state-dep)",
        lambda x, s, t: np.outer(x, x) / (np.dot(x, x) + 1e-12),
        lambda s: np.random.RandomState(s*200).randn(N) * 0.5 + 1.0
    )
    
    # (c) Hebbian normalized to row-stochastic
    results['hebbian_normalized'] = run_architecture(
        "Hebbian normalized (state-dep)",
        lambda x, s, t: normalize_hebbian(x),
        lambda s: np.random.RandomState(s*200).randn(N) * 0.5 + 1.0
    )
    
    # (d) Random coupling (fixed, but state evolves with noise)
    results['random_fixed'] = run_architecture(
        "Random GOE (fixed coupling)",
        lambda x, s, t: random_symmetric(N, seed=s),
        lambda s: np.random.RandomState(s*200).randn(N)
    )
    
    # (e) Evolving random coupling (resampled each step)
    results['random_evolving'] = run_architecture(
        "Random GOE (resampled each step)",
        lambda x, s, t: random_symmetric(N, seed=s*1000 + t),
        lambda s: np.random.RandomState(s*200).randn(N)
    )
    
    return results

# ============================================================
# EXP 2: Temperature Sweep with State-Dependent Attention
# ============================================================
def exp2_temperature_sweep():
    """
    Prediction: higher τ → more uniform attention → Tr(C²) closer to 1 → better conservation.
    Using state-dependent coupling so there's variation to measure.
    """
    print("\n" + "="*60)
    print("EXP-2: Temperature Sweep (State-Dependent Attention)")
    print("="*60)
    
    N = 20
    n_steps = 500
    warmup = 50
    noise_std = 0.1
    n_samples = 15
    temperatures = [0.05, 0.1, 0.3, 0.5, 1.0, 2.0, 5.0, 10.0, 50.0]
    
    results = []
    for tau in temperatures:
        sample_metrics = []
        for s in range(n_samples):
            rng = np.random.RandomState(s * 1000)
            x = rng.randn(N)
            history = []
            
            for t in range(n_steps):
                # State-dependent attention
                scores = np.outer(x, x) / np.sqrt(N)
                exp_s = np.exp(scores / tau - np.max(scores / tau, axis=1, keepdims=True))
                C = exp_s / exp_s.sum(axis=1, keepdims=True)
                
                metrics = compute_metrics(C)
                history.append(metrics)
                
                eta = rng.randn(N) * noise_std
                x = np.tanh(C @ x + eta)
            
            result = analyze_trajectory(history, warmup=warmup)
            if result is not None:
                sample_metrics.append(result)
        
        if sample_metrics:
            avg = lambda k: np.mean([m[k] for m in sample_metrics])
            r = {
                'temperature': tau,
                'gh_cv': avg('gh_cv'),
                'tr_c2_cv': avg('tr_c2_cv'),
                'gh_H_corr': avg('gh_H_corr'),
                'trc2_gh_corr': avg('trc2_gh_corr'),
                'gh_mean': avg('gh_mean'),
                'tr_c2_mean': avg('tr_c2_mean'),
                'rho_mean': avg('rho_mean') if 'rho_mean' in sample_metrics[0] else 0,
            }
            results.append(r)
            print(f"  τ={tau:5.2f} | CV(γ+H)={r['gh_cv']:.4f} | CV(TrC²)={r['tr_c2_cv']:.4f} | "
                  f"r(γ,H)={r['gh_H_corr']:+.3f} | r(TrC²,γ+H)={r['trc2_gh_corr']:+.3f} | "
                  f"⟨γ+H⟩={r['gh_mean']:.3f} | ⟨TrC²⟩={r['tr_c2_mean']:.3f}")
    
    return results

# ============================================================
# EXP 3: Multi-Agent Coupled Dynamics
# ============================================================
def exp3_multi_agent():
    """
    N agents with independent states. Coupling matrix computed from agent interactions.
    Each agent i: x_i(t+1) = tanh(Σ_j J_ij * x_j(t) + η_i)
    where J is fixed or evolves.
    """
    print("\n" + "="*60)
    print("EXP-3: Multi-Agent Coupled Dynamics (Fixed J + Noise)")
    print("="*60)
    
    N = 20
    n_steps = 500
    warmup = 50
    n_samples = 15
    noise_levels = [0.01, 0.05, 0.1, 0.3, 0.5, 1.0]
    
    configs = [
        ('attention', lambda s: softmax_attention(N, 1.0, seed=s)),
        ('random', lambda s: random_symmetric(N, seed=s)),
        ('hebbian_norm', lambda s: normalize_hebbian(np.random.RandomState(s).randn(N) * 0.5 + 1.0)),
    ]
    
    results = {}
    for name, J_func in configs:
        noise_results = []
        for noise_std in noise_levels:
            sample_metrics = []
            for s in range(n_samples):
                J = J_func(s)
                rng = np.random.RandomState(s * 1000)
                x = rng.randn(N)
                history = []
                
                for t in range(n_steps):
                    metrics = compute_metrics(J)
                    history.append(metrics)
                    
                    eta = rng.randn(N) * noise_std
                    x = np.tanh(J @ x + eta)
                
                result = analyze_trajectory(history, warmup=warmup)
                if result is not None:
                    sample_metrics.append(result)
            
            if sample_metrics:
                avg = lambda k: np.mean([m[k] for m in sample_metrics])
                noise_results.append({
                    'noise': noise_std,
                    'gh_cv': avg('gh_cv'),
                    'tr_c2_cv': avg('tr_c2_cv'),
                    'gh_H_corr': avg('gh_H_corr'),
                })
                print(f"  {name:15s} noise={noise_std:.2f} | CV(γ+H)={avg('gh_cv'):.4f} | "
                      f"CV(TrC²)={avg('tr_c2_cv'):.4f} | r(γ,H)={avg('gh_H_corr'):+.3f}")
        
        results[name] = noise_results
    
    return results

# ============================================================
# EXP 4: Falsification with Dynamic Coupling
# ============================================================
def exp4_falsification():
    """
    Try to BREAK conservation with state-dependent dynamics.
    """
    print("\n" + "="*60)
    print("EXP-4: Falsification (State-Dependent Dynamics)")
    print("="*60)
    
    N = 20
    n_steps = 500
    warmup = 50
    noise_std = 0.15
    n_samples = 15
    
    def run_test(name, make_C, x0_func):
        sample_metrics = []
        for s in range(n_samples):
            rng = np.random.RandomState(s * 1000)
            x = x0_func(s)
            history = []
            
            for t in range(n_steps):
                try:
                    C = make_C(x, s, t, rng)
                    metrics = compute_metrics(C)
                    history.append(metrics)
                    
                    eta = rng.randn(N) * noise_std
                    x = np.tanh(C @ x + eta)
                except:
                    break
            
            result = analyze_trajectory(history, warmup=warmup)
            if result is not None:
                sample_metrics.append(result)
        
        if sample_metrics:
            avg = lambda k: np.mean([m[k] for m in sample_metrics])
            print(f"  {name:40s} | CV(γ+H)={avg('gh_cv'):.4f} | CV(TrC²)={avg('tr_c2_cv'):.4f} | "
                  f"r(γ,H)={avg('gh_H_corr'):+.3f} | ⟨γ+H⟩={avg('gh_mean'):.3f} | n={len(sample_metrics)}")
            return {k: float(avg(k)) for k in sample_metrics[0].keys()}
        else:
            print(f"  {name:40s} | NO VALID RUNS")
            return None
    
    results = {}
    
    # (a) State-dependent Hebbian (raw, no normalization)
    results['hebbian_raw_dynamic'] = run_test(
        "Hebbian raw (state-dependent)",
        lambda x, s, t, rng: np.outer(x, x) / (np.dot(x, x) + 1e-12),
        lambda s: np.random.RandomState(s*200).randn(N) + 1.0
    )
    
    # (b) Rank-1 coupling (worst case for eigenvalue degeneracy)
    results['rank1'] = run_test(
        "Rank-1 coupling (pure outer product)",
        lambda x, s, t, rng: np.outer(x, x) / (np.linalg.norm(x)**2 + 1e-12),
        lambda s: np.random.RandomState(s*200).randn(N)
    )
    
    # (c) Anti-correlated coupling (negative off-diagonal)
    results['anticorrelated'] = run_test(
        "Anti-correlated coupling",
        lambda x, s, t, rng: _make_anticorrelated(N, x),
        lambda s: np.random.RandomState(s*200).randn(N)
    )
    
    # (d) Competition dynamics (subtract mean before coupling)
    results['competitive'] = run_test(
        "Competitive dynamics (mean-subtracted)",
        lambda x, s, t, rng: _make_competitive(N, x),
        lambda s: np.random.RandomState(s*200).randn(N)
    )
    
    # (e) Random coupling but with state-dependent scale
    results['scaled_random'] = run_test(
        "Scaled random (state-dependent scale)",
        lambda x, s, t, rng: random_symmetric(N, seed=s) * np.linalg.norm(x),
        lambda s: np.random.RandomState(s*200).randn(N)
    )
    
    # (f) Oscillating coupling (alternating sign)
    results['oscillating'] = run_test(
        "Oscillating coupling (±1 flip)",
        lambda x, s, t, rng: ((-1)**t) * softmax_attention(N, 1.0, seed=s),
        lambda s: np.random.RandomState(s*200).randn(N)
    )
    
    # (g) Pure noise coupling (random each step)
    results['pure_noise'] = run_test(
        "Pure noise coupling (random each step)",
        lambda x, s, t, rng: rng.randn(N, N),
        lambda s: np.random.RandomState(s*200).randn(N)
    )
    
    return results

def _make_anticorrelated(N, x):
    """Coupling where off-diagonal is negative."""
    C = -np.outer(x, x)
    np.fill_diagonal(C, np.abs(np.diag(C)) + 1.0)
    return C / (np.abs(C).sum() + 1e-12)

def _make_competitive(N, x):
    """Subtract mean from state, then form coupling."""
    x_demean = x - x.mean()
    C = np.outer(x_demean, x_demean)
    np.fill_diagonal(C, np.abs(np.diag(C)) + 0.1)
    return C / (np.abs(C).sum() + 1e-12)

# ============================================================
# EXP 5: The Two-Moment Theory Test
# ============================================================
def exp5_two_moment_test():
    """
    Direct test: is γ+H determined by Tr(C) and Tr(C²)?
    For each trajectory, regress γ+H ~ f(Tr(C), Tr(C²)) and check R².
    """
    print("\n" + "="*60)
    print("EXP-5: Two-Moment Theory Test (Regression R²)")
    print("="*60)
    
    N = 20
    n_steps = 500
    warmup = 50
    noise_std = 0.15
    n_samples = 15
    
    configs = [
        ('attention', lambda x, s: softmax_attention(N, 1.0, seed=int(np.sum(np.abs(x)*1000)) % 100000)),
        ('hebbian_raw', lambda x, s: np.outer(x, x) / (np.dot(x, x) + 1e-12)),
        ('hebbian_norm', lambda x, s: normalize_hebbian(x)),
        ('random', lambda x, s: random_symmetric(N, seed=s)),
    ]
    
    results = {}
    for name, C_func in configs:
        r2_values = []
        
        for s in range(n_samples):
            rng = np.random.RandomState(s * 1000)
            x = rng.randn(N)
            tr_c_list = []
            tr_c2_list = []
            gh_list = []
            
            for t in range(n_steps):
                C = C_func(x, s)
                metrics = compute_metrics(C)
                
                tr_c_list.append(metrics['tr_c'])
                tr_c2_list.append(metrics['tr_c2'])
                gh_list.append(metrics['gamma_plus_H'])
                
                eta = rng.randn(N) * noise_std
                x = np.tanh(C @ x + eta)
            
            # Trim warmup
            tr_c_arr = np.array(tr_c_list[warmup:])
            tr_c2_arr = np.array(tr_c2_list[warmup:])
            gh_arr = np.array(gh_list[warmup:])
            
            mask = np.isfinite(gh_arr) & np.isfinite(tr_c2_arr) & np.isfinite(tr_c_arr)
            if mask.sum() < 20:
                continue
            
            tr_c_arr = tr_c_arr[mask]
            tr_c2_arr = tr_c2_arr[mask]
            gh_arr = gh_arr[mask]
            
            # Regress γ+H = a + b*Tr(C) + c*Tr(C²)
            X = np.column_stack([tr_c_arr, tr_c2_arr, np.ones_like(tr_c_arr)])
            try:
                coeffs, res, _, _ = np.linalg.lstsq(X, gh_arr, rcond=None)
                predicted = X @ coeffs
                ss_res = np.sum((gh_arr - predicted)**2)
                ss_tot = np.sum((gh_arr - np.mean(gh_arr))**2)
                r2 = 1 - ss_res / (ss_tot + 1e-15)
                r2_values.append(r2)
            except:
                pass
        
        if r2_values:
            avg_r2 = np.mean(r2_values)
            std_r2 = np.std(r2_values)
            results[name] = {'r2_mean': float(avg_r2), 'r2_std': float(std_r2), 'n': len(r2_values)}
            print(f"  {name:20s} | R²={avg_r2:.4f} ± {std_r2:.4f} | n={len(r2_values)}")
            if avg_r2 > 0.9:
                print(f"                        → Two-moment theory SUPPORTED (R²>0.9)")
            elif avg_r2 > 0.5:
                print(f"                        → Two-moment theory PARTIAL support")
            else:
                print(f"                        → Two-moment theory NOT sufficient")
    
    return results

# ============================================================
# Main
# ============================================================
def main():
    print("="*60)
    print("GPU LOOP CYCLE 5 v2 — Nemotron-30B")
    print("Fix: State-dependent coupling + noise for proper dynamics")
    print("="*60)
    
    results = {}
    results['exp1_state_dependent'] = exp1_state_dependent()
    results['exp2_temperature'] = exp2_temperature_sweep()
    results['exp3_multi_agent'] = exp3_multi_agent()
    results['exp4_falsification'] = exp4_falsification()
    results['exp5_two_moment'] = exp5_two_moment_test()
    
    out_path = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(out_path, 'raw_results_v2.json'), 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n\nResults saved to {out_path}/raw_results_v2.json")
    return results

if __name__ == '__main__':
    main()
