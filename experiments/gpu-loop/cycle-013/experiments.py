"""
Cycle 13: DEEP STRESS TEST — Try to BREAK spectral shape stability theory.

Theory: Conservation quality = f(spectral shape stability).
Three regimes: structural (rank-1), dynamical (stable spectrum), transitional.

Six stress tests:
1. Non-spectral coupling (non-diagonalizable/defective matrices)
2. Time-varying C (externally driven, not state-dependent)
3. Chaotic regime (high spectral radius, period-doubling)
4. Non-square coupling (M ≠ N)
5. Random activation per timestep
6. Adversarial coupling (maximize spectral shape variation, minimize other variation)
"""

import numpy as np
import json
from itertools import product

np.random.seed(42)

# ============================================================
# Core dynamics and spectral functions
# ============================================================

def participation_ratio(eigvals):
    """γ = (Σλ)² / Σλ²"""
    s1 = np.sum(np.abs(eigvals))
    s2 = np.sum(eigvals**2)
    if s2 < 1e-15:
        return 1.0
    return s1**2 / s2

def spectral_entropy(eigvals):
    """H = -Σ pᵢ ln(pᵢ) where pᵢ = |λᵢ|/Σ|λⱼ|"""
    abse = np.abs(eigvals)
    total = np.sum(abse)
    if total < 1e-15:
        return 0.0
    p = abse / total
    p = p[p > 1e-15]
    return -np.sum(p * np.log(p))

def gamma_plus_H(C):
    """Compute γ+H for coupling matrix C."""
    eigvals = np.linalg.eigvals(C)
    # For complex eigenvalues, use real parts for participation
    real_eig = np.real(eigvals)
    abs_eig = np.abs(eigvals)
    
    # Participation ratio on magnitudes
    s1 = np.sum(abs_eig)
    s2 = np.sum(abs_eig**2)
    if s2 < 1e-15:
        gamma = 1.0
    else:
        gamma = s1**2 / s2
    
    # Entropy on magnitudes
    p = abs_eig / s1 if s1 > 1e-15 else np.ones_like(abs_eig) / len(abs_eig)
    p = p[p > 1e-15]
    H = -np.sum(p * np.log(p))
    
    return gamma + H

def run_dynamics(C_func, x0, n_steps, activation='tanh'):
    """Run coupled dynamics x_{t+1} = σ(C(x_t) @ x_t) + noise."""
    x = x0.copy()
    trajectory = []
    
    for t in range(n_steps):
        C = C_func(x, t)
        pre_act = C @ x
        
        if activation == 'tanh':
            x = np.tanh(pre_act)
        elif activation == 'sigmoid':
            x = 1.0 / (1.0 + np.exp(-pre_act))
        elif activation == 'relu':
            x = np.maximum(0, pre_act)
        elif activation == 'random':
            # Random activation per timestep
            choice = np.random.randint(3)
            if choice == 0:
                x = np.tanh(pre_act)
            elif choice == 1:
                x = 1.0 / (1.0 + np.exp(-pre_act))
            else:
                x = np.maximum(0, pre_act)
        
        trajectory.append((x.copy(), C.copy()))
    
    return trajectory

def compute_cv_gamma_H(trajectory):
    """Compute CV(γ+H) along a trajectory."""
    values = []
    for x, C in trajectory:
        values.append(gamma_plus_H(C))
    values = np.array(values)
    mean = np.mean(values)
    if abs(mean) < 1e-15:
        return 0.0, mean, np.std(values)
    return np.std(values) / abs(mean), mean, np.std(values)

def spectral_shape_stability(trajectory):
    """Measure how much the eigenvalue shape changes over time."""
    spectra = []
    for x, C in trajectory:
        eigvals = np.sort(np.abs(np.linalg.eigvals(C)))[::-1]
        spectra.append(eigvals)
    spectra = np.array(spectra)
    
    # Mean spectrum
    mean_spec = np.mean(spectra, axis=0)
    # Earth mover's distance approximation: mean L1 distance from mean
    deviations = np.mean(np.abs(spectra - mean_spec), axis=1)
    mean_dev = np.mean(deviations)
    norm = np.mean(mean_spec) if np.mean(mean_spec) > 1e-15 else 1.0
    return mean_dev / norm  # Normalized spectral shape variation

# ============================================================
# EXPERIMENT 1: Non-diagonalizable / Defective Matrices
# ============================================================

def make_defective_matrix(n, defect_strength=0.5):
    """Create a non-diagonalizable (defective) matrix.
    Jordan block with repeated eigenvalues and nilpotent part."""
    # Jordan form: eigenvalue λ on diagonal, 1s on superdiagonal
    lam = 2.0
    J = lam * np.eye(n) + np.diag(np.ones(n-1), 1) * defect_strength
    # Random similarity transform
    P = np.random.randn(n, n)
    while np.abs(np.linalg.det(P)) < 0.1:
        P = np.random.randn(n, n)
    C = P @ J @ np.linalg.inv(P)
    return C

def exp1_nonspectral():
    """Test defective (non-diagonalizable) matrices."""
    print("=" * 60)
    print("EXPERIMENT 1: Non-diagonalizable / Defective Matrices")
    print("=" * 60)
    
    results = []
    N = 5
    n_steps = 50
    n_samples = 10
    
    for defect in [0.0, 0.1, 0.5, 1.0, 2.0]:
        cvs = []
        spec_stabs = []
        is_diagonalizable = []
        
        for s in range(n_samples):
            C_static = make_defective_matrix(N, defect)
            
            # Check if actually defective
            eigvals = np.linalg.eigvals(C_static)
            eigvecs = np.linalg.eig(C_static)[1]
            cond = np.linalg.cond(eigvecs)
            is_diag = cond < 1e10
            
            # State-dependent version: C(x) = C_static (no state dep, just test spectral)
            # Actually let's do: C(x) = C_static + ε·xx^T/N to make it state-dependent
            def C_func(x, t, C0=C_static):
                return C0 + 0.01 * np.outer(x, x) / N
            
            x0 = np.random.randn(N) * 0.5
            traj = run_dynamics(C_func, x0, n_steps, 'tanh')
            cv, mean, std = compute_cv_gamma_H(traj)
            ss = spectral_shape_stability(traj)
            
            cvs.append(cv)
            spec_stabs.append(ss)
            is_diagonalizable.append(is_diag)
        
        frac_diag = np.mean(is_diagonalizable)
        mean_cv = np.mean(cvs)
        mean_ss = np.mean(spec_stabs)
        results.append({
            'defect_strength': defect,
            'frac_diagonalizable': frac_diag,
            'mean_CV': mean_cv,
            'mean_spectral_stability': mean_ss,
        })
        print(f"  defect={defect:.1f}: CV={mean_cv:.6f}, spec_stab={mean_ss:.6f}, "
              f"diag={frac_diag:.1f}")
    
    return results

# ============================================================
# EXPERIMENT 2: Time-varying C (externally driven)
# ============================================================

def exp2_time_varying():
    """Test with C changing every timestep, externally driven."""
    print("=" * 60)
    print("EXPERIMENT 2: Time-Varying C (externally driven)")
    print("=" * 60)
    
    results = []
    N = 5
    n_steps = 50
    n_samples = 10
    
    # C(t) oscillates between two matrices
    for freq in [0.01, 0.1, 0.5, 1.0, 5.0]:
        for amplitude in [0.1, 0.5, 1.0]:
            cvs = []
            spec_stabs = []
            
            for s in range(n_samples):
                C_base = np.random.randn(N, N) * 0.5
                C_perturb = np.random.randn(N, N) * amplitude
                
                def C_func(x, t, cb=C_base, cp=C_perturb, f=freq):
                    return cb + np.sin(2 * np.pi * f * t) * cp
                
                x0 = np.random.randn(N) * 0.5
                traj = run_dynamics(C_func, x0, n_steps, 'tanh')
                cv, mean, std = compute_cv_gamma_H(traj)
                ss = spectral_shape_stability(traj)
                cvs.append(cv)
                spec_stabs.append(ss)
            
            mean_cv = np.mean(cvs)
            mean_ss = np.mean(spec_stabs)
            results.append({
                'frequency': freq,
                'amplitude': amplitude,
                'mean_CV': mean_cv,
                'mean_spectral_stability': mean_ss,
            })
            print(f"  freq={freq:.2f}, amp={amplitude:.1f}: CV={mean_cv:.6f}, "
                  f"spec_stab={mean_ss:.6f}")
    
    return results

# ============================================================
# EXPERIMENT 3: Chaotic regime (high spectral radius)
# ============================================================

def exp3_chaotic():
    """Test with high spectral radius → chaos, period-doubling."""
    print("=" * 60)
    print("EXPERIMENT 3: Chaotic Regime (high spectral radius)")
    print("=" * 60)
    
    results = []
    N = 5
    n_steps = 50
    n_samples = 10
    
    for scale in [0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0]:
        cvs = []
        spec_stabs = []
        period_detections = []
        
        for s in range(n_samples):
            C_static = np.random.randn(N, N) * scale / np.sqrt(N)
            
            def C_func(x, t, C0=C_static):
                return C0 + 0.01 * np.outer(x, x) / N
            
            x0 = np.random.randn(N) * 0.5
            traj = run_dynamics(C_func, x0, n_steps, 'tanh')
            cv, mean, std = compute_cv_gamma_H(traj)
            ss = spectral_shape_stability(traj)
            
            # Detect period-2, period-4 by looking at x norm
            norms = [np.linalg.norm(x) for x, C in traj[-20:]]
            norms = np.array(norms)
            if len(norms) > 4:
                diffs = np.abs(np.diff(norms))
                # Check for oscillation
                period2 = np.mean(diffs[::2]) / (np.mean(norms) + 1e-10)
                period_detections.append(period2)
            
            cvs.append(cv)
            spec_stabs.append(ss)
        
        mean_cv = np.mean(cvs)
        mean_ss = np.mean(spec_stabs)
        mean_period = np.mean(period_detections)
        
        # Compute spectral radius
        rho = np.mean([np.max(np.abs(np.linalg.eigvals(
            np.random.randn(N, N) * scale / np.sqrt(N) + 0.01 * np.outer(
                np.random.randn(N), np.random.randn(N)) / N
        ))) for _ in range(5)])
        
        results.append({
            'scale': scale,
            'spectral_radius_est': rho,
            'mean_CV': mean_cv,
            'mean_spectral_stability': mean_ss,
            'period_indicator': mean_period,
        })
        print(f"  scale={scale:.1f}, ρ≈{rho:.2f}: CV={mean_cv:.6f}, "
              f"spec_stab={mean_ss:.6f}, period_ind={mean_period:.4f}")
    
    return results

# ============================================================
# EXPERIMENT 4: Non-square coupling (M ≠ N)
# ============================================================

def exp4_nonsquare():
    """Test with non-square coupling matrices (state in R^N, maps to R^M)."""
    print("=" * 60)
    print("EXPERIMENT 4: Non-Square Coupling (M ≠ N)")
    print("=" * 60)
    
    results = []
    n_steps = 50
    n_samples = 10
    
    for M, N in [(3, 5), (5, 3), (2, 5), (5, 2), (1, 5), (5, 1), (4, 3), (3, 4)]:
        cvs = []
        spec_stabs = []
        
        for s in range(n_samples):
            # C is M×N. For γ+H we use singular values instead of eigenvalues
            C_static = np.random.randn(M, N) * 0.5
            
            def C_func(x, t, C0=C_static, m=M, n=N):
                # State-dependent: scale rows by state
                row_scale = 1.0 + 0.01 * x[:m] if len(x) >= m else 1.0 + 0.01 * np.pad(x, (0, m-len(x)))
                return C0 * row_scale[:, None]
            
            def gamma_plus_H_nonsquare(C_mat):
                """Use singular values for non-square matrices."""
                svd = np.linalg.svd(C_mat, compute_uv=False)
                svd = np.abs(svd)
                s1 = np.sum(svd)
                s2 = np.sum(svd**2)
                if s2 < 1e-15:
                    return 1.0
                gamma = s1**2 / s2
                p = svd / s1
                p = p[p > 1e-15]
                H = -np.sum(p * np.log(p))
                return gamma + H
            
            def spectral_stability_nonsquare(traj):
                spectra = []
                for x, C in traj:
                    svd = np.sort(np.linalg.svd(C, compute_uv=False))[::-1]
                    spectra.append(svd)
                spectra = np.array(spectra)
                mean_spec = np.mean(spectra, axis=0)
                deviations = np.mean(np.abs(spectra - mean_spec), axis=1)
                mean_dev = np.mean(deviations)
                norm = np.mean(mean_spec) if np.mean(mean_spec) > 1e-15 else 1.0
                return mean_dev / norm
            
            # Run dynamics: x_{t+1} = σ(C @ x), but need to handle dimension mismatch
            x0 = np.random.randn(N) * 0.5
            x = x0.copy()
            trajectory = []
            
            for t in range(n_steps):
                C = C_func(x, t)
                pre_act = C @ x
                # C @ x gives M-dim, but state is N-dim
                # Strategy: project back to N-dim via C^T @ σ(C @ x)
                activated = np.tanh(pre_act)
                x = C.T @ activated
                x = x / (np.linalg.norm(x) + 1e-10) * np.linalg.norm(x0)  # preserve norm
                trajectory.append((x.copy(), C.copy()))
            
            values = [gamma_plus_H_nonsquare(C) for x, C in trajectory]
            values = np.array(values)
            mean_v = np.mean(values)
            cv = np.std(values) / abs(mean_v) if abs(mean_v) > 1e-15 else 0.0
            ss = spectral_stability_nonsquare(trajectory)
            
            cvs.append(cv)
            spec_stabs.append(ss)
        
        mean_cv = np.mean(cvs)
        mean_ss = np.mean(spec_stabs)
        results.append({
            'M': M,
            'N': N,
            'mean_CV': mean_cv,
            'mean_spectral_stability': mean_ss,
        })
        print(f"  M={M}, N={N}: CV={mean_cv:.6f}, spec_stab={mean_ss:.6f}")
    
    return results

# ============================================================
# EXPERIMENT 5: Random activation per timestep
# ============================================================

def exp5_random_activation():
    """Test with different activation at each timestep."""
    print("=" * 60)
    print("EXPERIMENT 5: Random Activation Per Timestep")
    print("=" * 60)
    
    results = []
    N = 5
    n_steps = 50
    n_samples = 10
    
    for coupling_type in ['random', 'attention', 'hebbian']:
        for scale in [0.5, 1.0, 2.0]:
            cvs = []
            spec_stabs = []
            cvs_fixed = []  # Compare with fixed tanh
            
            for s in range(n_samples):
                if coupling_type == 'random':
                    C_base = np.random.randn(N, N) * scale / np.sqrt(N)
                    def C_func(x, t, C0=C_base):
                        return C0 + 0.01 * np.outer(x, x) / N
                elif coupling_type == 'attention':
                    def C_func(x, t, sc=scale):
                        raw = np.outer(x, x) / N
                        row_sums = np.sum(np.abs(raw), axis=1, keepdims=True) + 1e-10
                        return sc * raw / row_sums
                else:  # hebbian
                    def C_func(x, t, sc=scale):
                        return sc * np.outer(x, x) / N
                
                x0 = np.random.randn(N) * 0.5
                
                # Random activation
                traj_rand = run_dynamics(C_func, x0.copy(), n_steps, 'random')
                cv_r, _, _ = compute_cv_gamma_H(traj_rand)
                ss_r = spectral_shape_stability(traj_rand)
                
                # Fixed tanh for comparison
                traj_fix = run_dynamics(C_func, x0.copy(), n_steps, 'tanh')
                cv_f, _, _ = compute_cv_gamma_H(traj_fix)
                
                cvs.append(cv_r)
                spec_stabs.append(ss_r)
                cvs_fixed.append(cv_f)
            
            mean_cv = np.mean(cvs)
            mean_ss = np.mean(spec_stabs)
            mean_cv_fixed = np.mean(cvs_fixed)
            ratio = mean_cv / mean_cv_fixed if mean_cv_fixed > 1e-10 else float('inf')
            
            results.append({
                'coupling': coupling_type,
                'scale': scale,
                'mean_CV_random_act': mean_cv,
                'mean_CV_fixed_tanh': mean_cv_fixed,
                'CV_ratio': ratio,
                'mean_spectral_stability': mean_ss,
            })
            print(f"  {coupling_type} scale={scale:.1f}: CV_rand={mean_cv:.6f}, "
                  f"CV_tanh={mean_cv_fixed:.6f}, ratio={ratio:.2f}, "
                  f"spec_stab={mean_ss:.6f}")
    
    return results

# ============================================================
# EXPERIMENT 6: Adversarial coupling — maximize spectral shape variation
# ============================================================

def exp6_adversarial():
    """Construct C to maximize spectral shape variation while keeping
    other properties (norm, rank) fixed. Try to get HIGH CV with STABLE
    spectral shape → would falsify the theory."""
    print("=" * 60)
    print("EXPERIMENT 6: Adversarial Coupling")
    print("=" * 60)
    
    results = []
    N = 5
    n_steps = 50
    n_samples = 10
    
    # Strategy 1: Coupling that oscillates between rank-1 and full-rank
    # with same Frobenius norm
    print("\n  Strategy 1: Rank oscillation (same ||C||_F)")
    for osc_freq in [0.1, 0.5, 1.0, 2.0]:
        cvs = []
        spec_stabs = []
        
        for s in range(n_samples):
            U, _ = np.linalg.qr(np.random.randn(N, N))
            V, _ = np.linalg.qr(np.random.randn(N, N))
            base_singular = np.array([2.0, 1.5, 1.0, 0.5, 0.1])
            
            def C_func(x, t, u=U, v=V, bs=base_singular, freq=osc_freq):
                # Oscillate between rank-1 and full-rank
                alpha = 0.5 * (1 + np.sin(2 * np.pi * freq * t))
                # rank-1: [2.5, 0, 0, 0, 0], full: base_singular
                svs = alpha * np.array([np.sqrt(np.sum(bs**2)), 0, 0, 0, 0]) + \
                      (1 - alpha) * bs
                return u @ np.diag(svs) @ v.T
            
            x0 = np.random.randn(N) * 0.5
            traj = run_dynamics(C_func, x0, n_steps, 'tanh')
            cv, mean, std = compute_cv_gamma_H(traj)
            ss = spectral_shape_stability(traj)
            cvs.append(cv)
            spec_stabs.append(ss)
        
        mean_cv = np.mean(cvs)
        mean_ss = np.mean(spec_stabs)
        results.append({
            'strategy': 'rank_oscillation',
            'frequency': osc_freq,
            'mean_CV': mean_cv,
            'mean_spectral_stability': mean_ss,
        })
        print(f"    freq={osc_freq:.1f}: CV={mean_cv:.6f}, spec_stab={mean_ss:.6f}")
    
    # Strategy 2: Eigenvalue rotation — same spectrum, rotating eigenvectors
    # This should have LOW CV if the theory is right (stable spectrum → stable γ+H)
    # If CV is HIGH despite stable spectrum → theory is WRONG
    print("\n  Strategy 2: Eigenvalue rotation (fixed spectrum, rotating eigvecs)")
    for rot_speed in [0.01, 0.1, 0.5, 1.0]:
        cvs = []
        spec_stabs = []
        
        for s in range(n_samples):
            fixed_spectrum = np.array([2.0, 1.5, 1.0, 0.5, 0.1])
            
            def C_func(x, t, spec=fixed_spectrum, rs=rot_speed):
                # Rotate eigenvectors each step
                angle = rs * t
                G = np.eye(N)
                for i in range(N):
                    for j in range(i+1, N):
                        R = np.eye(N)
                        a = angle * (i + 1) * (j + 1)
                        R[i, i] = np.cos(a)
                        R[j, j] = np.cos(a)
                        R[i, j] = -np.sin(a)
                        R[j, i] = np.sin(a)
                        G = G @ R
                return G @ np.diag(spec) @ G.T
            
            x0 = np.random.randn(N) * 0.5
            traj = run_dynamics(C_func, x0, n_steps, 'tanh')
            cv, mean, std = compute_cv_gamma_H(traj)
            ss = spectral_shape_stability(traj)
            cvs.append(cv)
            spec_stabs.append(ss)
        
        mean_cv = np.mean(cvs)
        mean_ss = np.mean(spec_stabs)
        results.append({
            'strategy': 'eigenvalue_rotation',
            'rotation_speed': rot_speed,
            'mean_CV': mean_cv,
            'mean_spectral_stability': mean_ss,
        })
        print(f"    rot_speed={rot_speed:.2f}: CV={mean_cv:.6f}, spec_stab={mean_ss:.6f}")
    
    # Strategy 3: Counter-theory — try to get LOW CV with UNSTABLE spectrum
    # If we can't → theory has predictive power
    print("\n  Strategy 3: Unstable spectrum (try to maintain γ+H despite spectral change)")
    for perturb_mode in ['swap', 'scale', 'redistribute']:
        cvs = []
        spec_stabs = []
        
        for s in range(n_samples):
            base_spectrum = np.array([3.0, 2.0, 1.5, 1.0, 0.5])
            
            if perturb_mode == 'swap':
                def C_func(x, t, bs=base_spectrum):
                    spec = bs.copy()
                    if t % 2 == 1:
                        spec[0], spec[-1] = spec[-1], spec[0]
                    Q, _ = np.linalg.qr(np.random.randn(N, N))
                    return Q @ np.diag(spec) @ Q.T
            elif perturb_mode == 'scale':
                def C_func(x, t, bs=base_spectrum):
                    scale = 1.0 + 0.5 * np.sin(t * 0.5)
                    Q, _ = np.linalg.qr(np.random.randn(N, N))
                    return Q @ np.diag(bs * scale) @ Q.T
            else:  # redistribute
                def C_func(x, t, bs=base_spectrum):
                    total = np.sum(bs)
                    # Random redistribution preserving total
                    spec = np.random.dirichlet(np.ones(N)) * total
                    Q, _ = np.linalg.qr(np.random.randn(N, N))
                    return Q @ np.diag(spec) @ Q.T
            
            x0 = np.random.randn(N) * 0.5
            traj = run_dynamics(C_func, x0, n_steps, 'tanh')
            cv, mean, std = compute_cv_gamma_H(traj)
            ss = spectral_shape_stability(traj)
            cvs.append(cv)
            spec_stabs.append(ss)
        
        mean_cv = np.mean(cvs)
        mean_ss = np.mean(spec_stabs)
        results.append({
            'strategy': f'unstable_spectrum_{perturb_mode}',
            'mean_CV': mean_cv,
            'mean_spectral_stability': mean_ss,
        })
        print(f"    mode={perturb_mode}: CV={mean_cv:.6f}, spec_stab={mean_ss:.6f}")
    
    # Strategy 4: Carefully engineered to have SAME γ+H with DIFFERENT spectra
    # If γ+H is the same for different spectral shapes → there's a degeneracy
    print("\n  Strategy 4: Spectral degeneracy search (same γ+H, different spectra)")
    target_gamma_H = None
    found_degeneracies = 0
    degeneracy_pairs = []
    
    for trial in range(1000):
        spec1 = np.sort(np.abs(np.random.randn(N)))[::-1]
        spec1 = spec1 / np.sum(spec1) * 5.0  # normalize
        
        s1 = np.sum(spec1)
        s2 = np.sum(spec1**2)
        gamma1 = s1**2 / s2
        p1 = spec1 / s1
        H1 = -np.sum(p1[p1 > 1e-15] * np.log(p1[p1 > 1e-15]))
        gH1 = gamma1 + H1
        
        if target_gamma_H is None:
            target_gamma_H = gH1
            continue
        
        # Try to find different spectrum with same γ+H
        spec2 = np.sort(np.abs(np.random.randn(N)))[::-1]
        spec2 = spec2 / np.sum(spec2) * 5.0
        
        s1_2 = np.sum(spec2)
        s2_2 = np.sum(spec2**2)
        gamma2 = s1_2**2 / s2_2
        p2 = spec2 / s1_2
        H2 = -np.sum(p2[p2 > 1e-15] * np.log(p2[p2 > 1e-15]))
        gH2 = gamma2 + H2
        
        if abs(gH1 - gH2) < 0.01 and np.max(np.abs(spec1 - spec2)) > 0.5:
            found_degeneracies += 1
            if found_degeneracies <= 3:
                degeneracy_pairs.append({
                    'spec1': spec1.tolist(),
                    'spec2': spec2.tolist(),
                    'gamma_H': float(gH1),
                    'spectral_diff': float(np.max(np.abs(spec1 - spec2)))
                })
    
    results.append({
        'strategy': 'degeneracy_search',
        'trials': 1000,
        'degeneracies_found': found_degeneracies,
        'sample_pairs': degeneracy_pairs
    })
    print(f"    Found {found_degeneracies} spectral degeneracies in 1000 trials")
    
    return results


# ============================================================
# RUN ALL EXPERIMENTS
# ============================================================

if __name__ == '__main__':
    all_results = {}
    
    print("\n" + "=" * 60)
    print("CYCLE 13: DEEP STRESS TEST")
    print("Theory: conservation quality = f(spectral shape stability)")
    print("Goal: BREAK IT")
    print("=" * 60 + "\n")
    
    all_results['exp1_nonspectral'] = exp1_nonspectral()
    all_results['exp2_time_varying'] = exp2_time_varying()
    all_results['exp3_chaotic'] = exp3_chaotic()
    all_results['exp4_nonsquare'] = exp4_nonsquare()
    all_results['exp5_random_activation'] = exp5_random_activation()
    all_results['exp6_adversarial'] = exp6_adversarial()
    
    # Save raw data
    with open('/home/phoenix/.openclaw/workspace/experiments/gpu-loop/cycle-013/raw_data.json', 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print("\n" + "=" * 60)
    print("ALL EXPERIMENTS COMPLETE")
    print("=" * 60)
