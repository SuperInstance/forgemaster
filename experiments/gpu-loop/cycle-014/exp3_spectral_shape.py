"""
Experiment 3: Spectral Shape Stability Metric
Define proper metrics for spectral shape variation and test which predicts CV best.
Metrics: cosine similarity, Earth mover's distance, Fisher information, KL divergence, spectral angle.
"""
import numpy as np
import json
from scipy.stats import wasserstein_distance

def spectral_shape_experiment():
    np.random.seed(42)
    
    # Generate spectral data for varying N and perturbation levels
    Ns = [10, 20, 50, 100]
    n_repeats = 50
    perturbation_levels = [0.01, 0.05, 0.1, 0.2, 0.5]
    
    results = []
    
    for N in Ns:
        for eps in perturbation_levels:
            for rep in range(n_repeats):
                # Base spectral density: eigenvalues of a random symmetric matrix
                A_base = np.random.randn(N, N)
                A_base = (A_base + A_base.T) / 2 / np.sqrt(N)
                eig_base = np.sort(np.linalg.eigvalsh(A_base))
                
                # Perturbed version
                A_pert = A_base + eps * np.random.randn(N, N) / np.sqrt(N)
                A_pert = (A_pert + A_pert.T) / 2
                eig_pert = np.sort(np.linalg.eigvalsh(A_pert))
                
                # Compute CV of perturbed eigenvalues (coefficient of variation)
                cv = np.std(eig_pert) / np.mean(np.abs(eig_pert)) if np.mean(np.abs(eig_pert)) > 0 else 0
                
                # Metric 1: Cosine similarity of eigenvalue vectors
                e1 = eig_base - np.mean(eig_base)
                e2 = eig_pert - np.mean(eig_pert)
                cos_sim = np.dot(e1, e2) / (np.linalg.norm(e1) * np.linalg.norm(e2) + 1e-16)
                
                # Metric 2: Earth mover's distance (Wasserstein-1)
                emd = wasserstein_distance(eig_base, eig_pert)
                
                # Metric 3: Spectral angle (angle between eigenvalue vectors)
                spectral_angle = np.arccos(np.clip(cos_sim, -1, 1))
                
                # Metric 4: Fisher information (discrete approximation)
                # F = sum((p_i - q_i)^2 / q_i) where p,q are normalized to probability distributions
                p = np.abs(eig_base) / (np.sum(np.abs(eig_base)) + 1e-16)
                q = np.abs(eig_pert) / (np.sum(np.abs(eig_pert)) + 1e-16)
                fisher = np.sum((p - q)**2 / (q + 1e-16))
                
                # Metric 5: KL divergence (symmetric)
                kl_pq = np.sum(p * np.log((p + 1e-16) / (q + 1e-16)))
                kl_qp = np.sum(q * np.log((q + 1e-16) / (p + 1e-16)))
                kl_sym = (kl_pq + kl_qp) / 2
                
                # Metric 6: Eigenvalue spacing variation
                spacing_base = np.diff(eig_base)
                spacing_pert = np.diff(eig_pert)
                spacing_var = np.std(spacing_pert - spacing_base) / (np.std(spacing_base) + 1e-16)
                
                # Metric 7: Spectral norm deviation
                spec_norm_diff = np.abs(np.max(np.abs(eig_base)) - np.max(np.abs(eig_pert)))
                
                results.append({
                    'N': N,
                    'eps': eps,
                    'rep': rep,
                    'cv': float(cv),
                    'cosine_similarity': float(cos_sim),
                    'emd': float(emd),
                    'spectral_angle': float(spectral_angle),
                    'fisher_info': float(fisher),
                    'kl_symmetric': float(float(kl_sym)),
                    'spacing_variation': float(spacing_var),
                    'spectral_norm_diff': float(spec_norm_diff),
                })
    
    # Now compute correlation of each metric with CV
    metrics = ['cosine_similarity', 'emd', 'spectral_angle', 'fisher_info', 'kl_symmetric', 'spacing_variation', 'spectral_norm_diff']
    
    cvs = np.array([r['cv'] for r in results])
    
    correlations = {}
    print("=" * 70)
    print("EXPERIMENT 3: Spectral Shape Stability Metric")
    print("=" * 70)
    print(f"\nTotal data points: {len(results)}")
    print(f"\nCorrelation with CV (Pearson | Spearman):")
    print("-" * 50)
    
    for metric in metrics:
        vals = np.array([r[metric] for r in results])
        # Pearson
        if np.std(vals) > 1e-16:
            pearson = np.corrcoef(vals, cvs)[0, 1]
            # Spearman (rank correlation)
            rank_vals = np.argsort(np.argsort(vals))
            rank_cvs = np.argsort(np.argsort(cvs))
            spearman = np.corrcoef(rank_vals.astype(float), rank_cvs.astype(float))[0, 1]
        else:
            pearson = float('nan')
            spearman = float('nan')
        
        correlations[metric] = {
            'pearson': float(pearson),
            'spearman': float(spearman),
            'abs_pearson': float(abs(pearson)),
        }
        print(f"  {metric:>25}: r={pearson:>8.4f} | ρ={spearman:>8.4f}")
    
    # Best predictor
    best_metric = max(correlations.keys(), key=lambda k: abs(correlations[k]['pearson']))
    print(f"\nBest CV predictor: {best_metric} (|r|={abs(correlations[best_metric]['pearson']):.4f})")
    
    return {
        'correlations': correlations,
        'best_predictor': best_metric,
        'n_data_points': len(results),
        'sample_results': results[:5],
    }

if __name__ == '__main__':
    data = spectral_shape_experiment()
    with open('/home/phoenix/.openclaw/workspace/experiments/gpu-loop/cycle-014/exp3_results.json', 'w') as f:
        json.dump(data, f, indent=2)
    print("\nResults saved to exp3_results.json")
