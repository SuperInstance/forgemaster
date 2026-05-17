"""
GPU Loop Cycle 3 — GLM-5.1
FIXED METHODOLOGY: State vector evolution for γ+H computation

Key fix: Previous cycles computed γ+H from static eigenvalue decomposition (trivially CV=0).
Now we trace state vector evolution over 200 rounds and compute γ+H from the evolving state.

Experiments:
1. Fixed dynamics across architectures (Random, Attention, Hebbian) — proper conservation test
2. Eigenvalue repulsion threshold — frac(spacings<0.5) as predictor
3. Engineered coupling via GOE projection + dynamics validation
4. Ternary→binary transition with proper dynamics
5. Floquet/asymmetric coupling as symmetry protection (from research brief)
"""

import numpy as np
from scipy import linalg
from scipy.spatial.distance import pdist
import json
import warnings
warnings.filterwarnings('ignore')

np.random.seed(42)

# ============================================================================
# CORE: State Vector Evolution with FIXED γ+H computation
# ============================================================================

def evolve_state(J, x0, n_rounds=200, normalize=True):
    """Evolve state vector x under coupling matrix J.
    
    Key fix: γ+H computed from evolving state, NOT from eigenvalues.
    γ = spectral gap = 1 - |<x, v1>|^2 where v1 is top eigenvector
    H = Shannon entropy of |x|^2
    """
    x = x0.copy().astype(np.float64)
    if normalize:
        x = x / np.linalg.norm(x)
    
    # Precompute eigendecomposition for spectral gap
    eigenvalues, eigenvectors = linalg.eigh(J)
    v1 = eigenvectors[:, -1]  # Top eigenvector
    
    gh_values = []
    x_traj = [x.copy()]
    
    for r in range(n_rounds):
        # Evolve: x <- J @ x
        x = J @ x
        
        # Normalize
        norm = np.linalg.norm(x)
        if norm < 1e-15 or np.any(np.isnan(x)):
            break
        x = x / norm
        x_traj.append(x.copy())
        
        # Spectral gap from STATE: overlap with top eigenvector
        overlap = np.abs(np.dot(x, v1))
        gamma = 1.0 - overlap**2
        
        # Shannon entropy from STATE
        p = x**2
        p = p[p > 1e-15]
        H = -np.sum(p * np.log(p))
        
        gh_values.append(gamma + H)
    
    return np.array(gh_values), np.array(x_traj)


def compute_cv(values):
    """Coefficient of variation."""
    if len(values) == 0 or np.mean(values) == 0:
        return np.nan
    return np.std(values) / np.abs(np.mean(values))


def eigenvalue_spacing_stats(eigenvalues):
    """Compute eigenvalue spacing statistics including frac<0.5."""
    sorted_evals = np.sort(eigenvalues)
    spacings = np.diff(sorted_evals)
    spacings = spacings / np.mean(spacings)  # Normalize to mean spacing = 1
    frac_below_05 = np.mean(spacings < 0.5)
    frac_below_10 = np.mean(spacings < 1.0)
    spacing_std = np.std(spacings)
    return {
        'frac_below_05': frac_below_05,
        'frac_below_10': frac_below_10,
        'spacing_std': spacing_std,
        'mean_spacing': np.mean(spacings),
        'min_spacing': np.min(spacings),
    }


# ============================================================================
# Coupling Matrix Generators
# ============================================================================

def random_coupling(N, seed=None):
    """GOE (Wigner) random matrix."""
    rng = np.random.default_rng(seed)
    A = rng.standard_normal((N, N))
    return (A + A.T) / (2 * np.sqrt(N))


def hebbian_coupling(N, n_patterns=None, seed=None):
    """Hebbian (outer product) coupling matrix."""
    rng = np.random.default_rng(seed)
    if n_patterns is None:
        n_patterns = max(1, N // 4)
    patterns = rng.choice([-1, 1], size=(n_patterns, N))
    J = patterns.T @ patterns / N
    np.fill_diagonal(J, 0)
    return J


def attention_coupling(N, d_head=None, seed=None):
    """Attention-like coupling matrix (softmax of QK^T)."""
    rng = np.random.default_rng(seed)
    if d_head is None:
        d_head = max(1, N // 4)
    Q = rng.standard_normal((N, d_head)) / np.sqrt(d_head)
    K = rng.standard_normal((N, d_head)) / np.sqrt(d_head)
    scores = Q @ K.T / np.sqrt(d_head)
    # Row-wise softmax
    scores_max = scores.max(axis=1, keepdims=True)
    exp_scores = np.exp(scores - scores_max)
    J = exp_scores / exp_scores.sum(axis=1, keepdims=True)
    return J


def goe_projected_coupling(base_matrix, target_ks=0.1):
    """Project eigenvalue spacing to match GOE distribution."""
    N = base_matrix.shape[0]
    eigenvalues, eigenvectors = linalg.eigh(base_matrix)
    
    # Sort eigenvalues
    idx = np.argsort(eigenvalues)
    eigenvalues = eigenvalues[idx]
    eigenvectors = eigenvectors[:, idx]
    
    # Wigner surmise spacing: p(s) = (π/2)*s*exp(-π*s²/4)
    # Mean spacing = 1 after normalization
    # Rescale eigenvalues to have GOE-like spacing
    sorted_evals = np.sort(eigenvalues)
    spacings = np.diff(sorted_evals)
    mean_spacing = np.mean(spacings)
    
    # Generate GOE target spacing
    n_gaps = len(spacings)
    target_spacings = np.zeros(n_gaps)
    for i in range(n_gaps):
        # Sample from Wigner surmise via inverse CDF
        u = (i + 0.5) / n_gaps  # Quantile positions
        # Approximate: use Rayleigh-like spacing
        target_spacings[i] = np.sqrt(-4/np.pi * np.log(1 - u)) if u < 0.999 else 3.0
    
    # Rescale eigenvalues to match target spacing pattern
    new_evals = np.zeros_like(sorted_evals)
    new_evals[0] = sorted_evals[0]
    for i in range(n_gaps):
        new_evals[i+1] = new_evals[i] + target_spacings[i] * mean_spacing
    
    # Reconstruct matrix
    J_new = eigenvectors @ np.diag(new_evals) @ eigenvectors.T
    # Symmetrize
    J_new = (J_new + J_new.T) / 2
    return J_new


def engineered_repulsion_coupling(N, target_frac_below_05=0.3, seed=None):
    """Design a coupling matrix with specific eigenvalue repulsion.
    
    Start with a random matrix, then iteratively adjust eigenvalues
    to achieve target_frac_below_05 spacing.
    """
    rng = np.random.default_rng(seed)
    
    # Start with random
    J = random_coupling(N, seed=seed)
    eigenvalues, eigenvectors = linalg.eigh(J)
    
    # Sort and create target spacing
    idx = np.argsort(eigenvalues)
    eigenvalues = eigenvalues[idx]
    eigenvectors = eigenvectors[:, idx]
    
    # Target: create spacing with specific frac<0.5
    n = len(eigenvalues)
    n_gaps = n - 1
    n_small = int(target_frac_below_05 * n_gaps)
    n_large = n_gaps - n_small
    
    # Small spacings (below 0.5)
    small_spacings = rng.uniform(0.1, 0.45, size=n_small)
    # Large spacings (above 0.5) 
    large_spacings = rng.uniform(0.6, 2.5, size=n_large)
    
    all_spacings = np.concatenate([small_spacings, large_spacings])
    rng.shuffle(all_spacings)
    all_spacings = all_spacings * np.mean(np.diff(eigenvalues))
    
    new_evals = np.zeros(n)
    new_evals[0] = eigenvalues[0]
    for i in range(n_gaps):
        new_evals[i+1] = new_evals[i] + all_spacings[i]
    
    J_eng = eigenvectors @ np.diag(new_evals) @ eigenvectors.T
    J_eng = (J_eng + J_eng.T) / 2
    return J_eng


def asymmetric_coupling(N, asymmetry_level=1.0, seed=None):
    """Asymmetric coupling (upper/lower triangles have different scales)."""
    rng = np.random.default_rng(seed)
    A = rng.standard_normal((N, N))
    upper = np.triu(A, k=1) * (1.0 + asymmetry_level)
    lower = np.tril(A, k=-1) * (1.0 - asymmetry_level * 0.5)
    diag = np.diag(np.diag(A))
    J = upper + lower + diag
    return J / np.sqrt(N)


# ============================================================================
# EXPERIMENT 1: Fixed Dynamics Across Architectures
# ============================================================================

def exp1_architecture_dynamics():
    """EXP-1: Proper dynamics-based conservation test across architectures.
    
    50 samples per architecture, 200 rounds each.
    Compute γ+H from STATE VECTOR EVOLUTION.
    """
    print("=" * 70)
    print("EXP-1: Architecture × Dynamics-Based Conservation")
    print("=" * 70)
    
    N = 20
    n_rounds = 200
    n_samples = 50
    
    def make_gen(func):
        def gen(seed=None):
            return func(N, seed=seed)
        return gen

    architectures = {
        'random': make_gen(random_coupling),
        'hebbian': make_gen(hebbian_coupling),
        'attention': make_gen(attention_coupling),
    }
    
    results = {}
    for arch_name, gen_func in architectures.items():
        cv_list = []
        gh_means = []
        gh_stds = []
        
        for sample in range(n_samples):
            J = gen_func(seed=sample * 100 + 42)
            x0 = np.random.default_rng(sample * 100 + 99).standard_normal(N)
            
            gh_vals, x_traj = evolve_state(J, x0, n_rounds=n_rounds)
            
            if len(gh_vals) < 50:
                continue
            
            # Use last 150 rounds for stability
            gh_stable = gh_vals[50:]
            cv = compute_cv(gh_stable)
            cv_list.append(cv)
            gh_means.append(np.mean(gh_stable))
            gh_stds.append(np.std(gh_stable))
        
        # Also compute eigenvalue spacing stats
        J_sample = gen_func(seed=9999)
        evals = linalg.eigh(J_sample)[0]
        spacing = eigenvalue_spacing_stats(evals)
        
        results[arch_name] = {
            'cv_mean': np.mean(cv_list),
            'cv_std': np.std(cv_list),
            'cv_min': np.min(cv_list),
            'cv_max': np.max(cv_list),
            'gh_mean': np.mean(gh_means),
            'gh_std_mean': np.mean(gh_stds),
            'n_valid': len(cv_list),
            'frac_below_05': spacing['frac_below_05'],
            'spacing_std': spacing['spacing_std'],
        }
        
        print(f"\n  {arch_name.upper()}:")
        print(f"    CV(γ+H) = {results[arch_name]['cv_mean']:.4f} ± {results[arch_name]['cv_std']:.4f}")
        print(f"    γ+H mean = {results[arch_name]['gh_mean']:.4f}")
        print(f"    Valid samples: {results[arch_name]['n_valid']}")
        print(f"    frac(spacings<0.5) = {results[arch_name]['frac_below_05']:.4f}")
        print(f"    spacing_std = {results[arch_name]['spacing_std']:.4f}")
    
    return results


# ============================================================================
# EXPERIMENT 2: Eigenvalue Repulsion Threshold
# ============================================================================

def exp2_repulsion_threshold():
    """EXP-2: Test frac(spacings<0.5) as predictor of conservation.
    
    Generate matrices with varying eigenvalue repulsion and measure
    dynamics-based conservation.
    """
    print("\n" + "=" * 70)
    print("EXP-2: Eigenvalue Repulsion Threshold")
    print("=" * 70)
    
    N = 20
    n_rounds = 200
    n_samples = 30
    
    # Create matrices with varying repulsion
    target_fracs = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    
    results = {}
    for target in target_fracs:
        cv_list = []
        actual_fracs = []
        
        for sample in range(n_samples):
            J = engineered_repulsion_coupling(N, target_frac_below_05=target, seed=sample * 200 + 7)
            x0 = np.random.default_rng(sample * 200 + 88).standard_normal(N)
            
            # Get actual spacing stats
            evals = linalg.eigh(J)[0]
            spacing = eigenvalue_spacing_stats(evals)
            actual_fracs.append(spacing['frac_below_05'])
            
            # Evolve
            gh_vals, _ = evolve_state(J, x0, n_rounds=n_rounds)
            if len(gh_vals) < 50:
                continue
            gh_stable = gh_vals[50:]
            cv = compute_cv(gh_stable)
            cv_list.append(cv)
        
        results[f'target_{target:.1f}'] = {
            'target_frac': target,
            'actual_frac_mean': np.mean(actual_fracs),
            'actual_frac_std': np.std(actual_fracs),
            'cv_mean': np.mean(cv_list) if cv_list else np.nan,
            'cv_std': np.std(cv_list) if cv_list else np.nan,
            'n_valid': len(cv_list),
        }
        
        r = results[f'target_{target:.1f}']
        print(f"\n  target={target:.1f}: actual_frac={r['actual_frac_mean']:.3f}±{r['actual_frac_std']:.3f}, "
              f"CV={r['cv_mean']:.4f}±{r['cv_std']:.4f} (n={r['n_valid']})")
    
    # Also add pure random and pure hebbian for reference
    for name, gen in [('random_ref', lambda s: random_coupling(N, seed=s)),
                       ('hebbian_ref', lambda s: hebbian_coupling(N, seed=s))]:
        cv_list = []
        for sample in range(n_samples):
            J = gen(sample * 300 + 11)
            x0 = np.random.default_rng(sample * 300 + 22).standard_normal(N)
            gh_vals, _ = evolve_state(J, x0, n_rounds=n_rounds)
            if len(gh_vals) < 50:
                continue
            cv = compute_cv(gh_vals[50:])
            cv_list.append(cv)
        
        evals = linalg.eigh(gen(999))[0]
        spacing = eigenvalue_spacing_stats(evals)
        
        results[name] = {
            'target_frac': spacing['frac_below_05'],
            'actual_frac_mean': spacing['frac_below_05'],
            'cv_mean': np.mean(cv_list),
            'cv_std': np.std(cv_list) if len(cv_list) > 1 else 0,
            'n_valid': len(cv_list),
            'frac_below_05': spacing['frac_below_05'],
        }
        print(f"\n  {name}: frac={spacing['frac_below_05']:.3f}, CV={np.mean(cv_list):.4f}")
    
    return results


# ============================================================================
# EXPERIMENT 3: GOE Projection + Dynamics Validation
# ============================================================================

def exp3_goe_projection_dynamics():
    """EXP-3: Take Hebbian, project to GOE spacing, test dynamics-based conservation."""
    print("\n" + "=" * 70)
    print("EXP-3: GOE Projection + Dynamics Validation")
    print("=" * 70)
    
    N = 20
    n_rounds = 200
    n_samples = 30
    
    configs = {
        'hebbian_raw': lambda s: hebbian_coupling(N, seed=s),
        'hebbian_goe_proj': lambda s: goe_projected_coupling(hebbian_coupling(N, seed=s)),
        'random_raw': lambda s: random_coupling(N, seed=s),
        'attention_goe_proj': lambda s: goe_projected_coupling(attention_coupling(N, seed=s)),
    }
    
    results = {}
    for name, gen in configs.items():
        cv_list = []
        gh_means = []
        
        for sample in range(n_samples):
            J = gen(sample * 400 + 13)
            x0 = np.random.default_rng(sample * 400 + 77).standard_normal(N)
            
            gh_vals, _ = evolve_state(J, x0, n_rounds=n_rounds)
            if len(gh_vals) < 50:
                continue
            cv = compute_cv(gh_vals[50:])
            cv_list.append(cv)
            gh_means.append(np.mean(gh_vals[50:]))
        
        evals = linalg.eigh(gen(999))[0]
        spacing = eigenvalue_spacing_stats(evals)
        
        results[name] = {
            'cv_mean': np.mean(cv_list) if cv_list else np.nan,
            'cv_std': np.std(cv_list) if len(cv_list) > 1 else 0,
            'gh_mean': np.mean(gh_means) if gh_means else np.nan,
            'n_valid': len(cv_list),
            'frac_below_05': spacing['frac_below_05'],
            'spacing_std': spacing['spacing_std'],
        }
        
        print(f"\n  {name}:")
        print(f"    CV = {results[name]['cv_mean']:.4f} ± {results[name]['cv_std']:.4f}")
        print(f"    γ+H = {results[name]['gh_mean']:.4f}")
        print(f"    frac<0.5 = {results[name]['frac_below_05']:.4f}")
    
    return results


# ============================================================================
# EXPERIMENT 4: Ternary→Binary Transition with Proper Dynamics
# ============================================================================

def exp4_ternary_binary_dynamics():
    """EXP-4: Ternary→binary transition with state-vector-based conservation.
    
    Quantize the coupling matrix to different bit widths and trace dynamics.
    """
    print("\n" + "=" * 70)
    print("EXP-4: Ternary→Binary Transition (Dynamics-Based)")
    print("=" * 70)
    
    N = 20
    n_rounds = 200
    n_samples = 30
    
    def quantize_matrix(J, levels):
        """Quantize matrix entries to specified number of levels."""
        J_flat = J.flatten()
        vmin, vmax = J_flat.min(), J_flat.max()
        # Uniform quantization
        quantized = np.round((J_flat - vmin) / (vmax - vmin) * (levels - 1))
        quantized = quantized / (levels - 1) * (vmax - vmin) + vmin
        return quantized.reshape(J.shape)
    
    # Test quantization levels
    quant_configs = {
        'fp32': None,  # No quantization
        'int16': 65536,
        'int8': 256,
        'int4': 16,
        'ternary': 3,  # {-1, 0, 1} effectively
        'binary_pos': 2,  # {0, 1}
    }
    
    results = {}
    for qname, levels in quant_configs.items():
        cv_list = []
        gh_means = []
        survival_count = 0
        
        for sample in range(n_samples):
            J_base = random_coupling(N, seed=sample * 500 + 33)
            
            if levels is not None:
                J = quantize_matrix(J_base, levels)
                # Re-symmetrize after quantization
                J = (J + J.T) / 2
            else:
                J = J_base
            
            x0 = np.random.default_rng(sample * 500 + 44).standard_normal(N)
            
            gh_vals, _ = evolve_state(J, x0, n_rounds=n_rounds)
            
            if len(gh_vals) < 50:
                continue
            
            survival_count += 1
            cv = compute_cv(gh_vals[50:])
            cv_list.append(cv)
            gh_means.append(np.mean(gh_vals[50:]))
        
        results[qname] = {
            'cv_mean': np.mean(cv_list) if cv_list else np.nan,
            'cv_std': np.std(cv_list) if len(cv_list) > 1 else 0,
            'gh_mean': np.mean(gh_means) if gh_means else np.nan,
            'survival_rate': survival_count / n_samples,
            'n_valid': len(cv_list),
        }
        
        print(f"\n  {qname}:")
        print(f"    Survival: {survival_count}/{n_samples} ({survival_count/n_samples*100:.0f}%)")
        if cv_list:
            print(f"    CV = {results[qname]['cv_mean']:.4f} ± {results[qname]['cv_std']:.4f}")
            print(f"    γ+H = {results[qname]['gh_mean']:.4f}")
        else:
            print(f"    No surviving runs!")
    
    return results


# ============================================================================
# EXPERIMENT 5: Floquet-Like Asymmetric Coupling as Symmetry Protection
# ============================================================================

def exp5_floquet_asymmetric():
    """EXP-5: Test if asymmetric coupling acts like Floquet symmetry protection.
    
    From research brief: asymmetric coupling may create emergent symmetry
    that protects conservation (analogous to Fu et al. 2026).
    """
    print("\n" + "=" * 70)
    print("EXP-5: Floquet Asymmetric Coupling — Symmetry Protection Test")
    print("=" * 70)
    
    N = 20
    n_rounds = 200
    n_samples = 30
    
    # Time-alternating coupling: J1 for even rounds, J2 for odd rounds
    # This is the Floquet analogy
    
    def floquet_evolve(J1, J2, x0, n_rounds=200):
        """Alternate between J1 and J2 (Floquet-like driving)."""
        x = x0.copy().astype(np.float64)
        x = x / np.linalg.norm(x)
        
        # Use average eigenstructure for spectral gap
        J_avg = (J1 + J2) / 2
        eigenvalues, eigenvectors = linalg.eigh(J_avg)
        v1 = eigenvectors[:, -1]
        
        gh_values = []
        for r in range(n_rounds):
            J = J1 if r % 2 == 0 else J2
            x = J @ x
            norm = np.linalg.norm(x)
            if norm < 1e-15 or np.any(np.isnan(x)):
                break
            x = x / norm
            
            overlap = np.abs(np.dot(x, v1))
            gamma = 1.0 - overlap**2
            p = x**2
            p = p[p > 1e-15]
            H = -np.sum(p * np.log(p))
            gh_values.append(gamma + H)
        
        return np.array(gh_values)
    
    asymmetry_levels = [0.0, 0.2, 0.5, 1.0, 2.0, 5.0]
    
    results = {}
    for asym in asymmetry_levels:
        cv_list = []
        
        for sample in range(n_samples):
            J1 = random_coupling(N, seed=sample * 600 + 55)
            J2 = random_coupling(N, seed=sample * 600 + 66)
            
            # Create asymmetric coupling: J2 scaled by asymmetry factor
            J2_asym = J2 * (1.0 + asym * 0.1)  # Slight perturbation
            
            x0 = np.random.default_rng(sample * 600 + 77).standard_normal(N)
            
            gh_vals = floquet_evolve(J1, J2_asym, x0, n_rounds=n_rounds)
            
            if len(gh_vals) < 50:
                continue
            cv = compute_cv(gh_vals[50:])
            cv_list.append(cv)
        
        results[f'asym_{asym:.1f}'] = {
            'asymmetry': asym,
            'cv_mean': np.mean(cv_list) if cv_list else np.nan,
            'cv_std': np.std(cv_list) if len(cv_list) > 1 else 0,
            'n_valid': len(cv_list),
        }
        
        r = results[f'asym_{asym:.1f}']
        print(f"\n  asymmetry={asym:.1f}: CV={r['cv_mean']:.4f}±{r['cv_std']:.4f} (n={r['n_valid']})")
    
    # Also test single asymmetric matrix (non-Floquet)
    print("\n  --- Single asymmetric matrix comparison ---")
    for asym in [0.0, 0.5, 1.0, 2.0]:
        cv_list = []
        for sample in range(n_samples):
            J = asymmetric_coupling(N, asymmetry_level=asym, seed=sample * 700 + 11)
            x0 = np.random.default_rng(sample * 700 + 22).standard_normal(N)
            gh_vals, _ = evolve_state(J, x0, n_rounds=n_rounds)
            if len(gh_vals) < 50:
                continue
            cv = compute_cv(gh_vals[50:])
            cv_list.append(cv)
        
        results[f'single_asym_{asym:.1f}'] = {
            'asymmetry': asym,
            'cv_mean': np.mean(cv_list) if cv_list else np.nan,
            'cv_std': np.std(cv_list) if len(cv_list) > 1 else 0,
            'n_valid': len(cv_list),
        }
        r = results[f'single_asym_{asym:.1f}']
        print(f"    single_asym={asym:.1f}: CV={r['cv_mean']:.4f}±{r['cv_std']:.4f}")
    
    return results


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("GPU Loop Cycle 3 — GLM-5.1")
    print("FIXED METHODOLOGY: State vector evolution for γ+H")
    print("=" * 70)
    
    r1 = exp1_architecture_dynamics()
    r2 = exp2_repulsion_threshold()
    r3 = exp3_goe_projection_dynamics()
    r4 = exp4_ternary_binary_dynamics()
    r5 = exp5_floquet_asymmetric()
    
    # Save all results
    all_results = {
        'exp1_architecture_dynamics': r1,
        'exp2_repulsion_threshold': r2,
        'exp3_goe_projection': r3,
        'exp4_ternary_binary': r4,
        'exp5_floquet_asymmetric': r5,
    }
    
    with open('/home/phoenix/.openclaw/workspace/experiments/gpu-loop/cycle-003/raw_results.json', 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print("\n\nAll experiments complete. Results saved.")
