#!/usr/bin/env python3
"""
EXP-4: BBP Transition Shift Under Precision Heterogeneity (H3)
Does the BBP transition broaden with mixed precision?
Constructs spiked Wigner matrices with precision-dependent noise.
"""
import numpy as np
from scipy.linalg import eigvalsh
import json, os

np.random.seed(2024)
N = 20  # matrix size (5 agents × 4 state dims, or just 20-dim)

def quantize_noise(sigma, bits):
    """Simulate precision-dependent noise floor."""
    if bits >= 52: return sigma  # negligible quantization noise
    if bits >= 23: return sigma + 1e-7
    if bits >= 10: return sigma + 1e-3
    if bits >= 7:  return sigma + 1e-2
    return sigma + 0.1  # 1-4 bit: massive noise

def spiked_wigner_mixed(beta, hi_bits, lo_bits, n=N, n_hi=None):
    """Spiked Wigner matrix with block-dependent noise.
    Top-left block: hi_bits precision, bottom-right: lo_bits.
    """
    if n_hi is None:
        n_hi = n // 2
    n_lo = n - n_hi
    
    # Signal vector (spike)
    v = np.random.randn(n)
    v = v / np.linalg.norm(v)
    
    # Noise matrices with precision-dependent sigma
    sigma_hi = quantize_noise(1.0/np.sqrt(n), hi_bits)
    sigma_lo = quantize_noise(1.0/np.sqrt(n), lo_bits)
    
    W = np.random.randn(n, n)
    # Scale noise per block
    W[:n_hi, :n_hi] *= sigma_hi
    W[n_hi:, n_hi:] *= sigma_lo
    # Cross-block noise (average)
    cross_sigma = (sigma_hi + sigma_lo) / 2
    W[:n_hi, n_hi:] *= cross_sigma
    W[n_hi:, :n_hi] *= cross_sigma
    W = (W + W.T) / (2 * np.sqrt(n))
    
    # Add spike
    M = beta * np.outer(v, v) + W
    
    # Compute top eigenvalue and overlap
    eigs, vecs = np.linalg.eigh(M)
    idx = np.argmax(eigs)
    spike_eig = eigs[idx]
    overlap = abs(np.dot(vecs[:, idx], v))
    
    return spike_eig, overlap, eigs

# BBP transition: sweep β for different precision mixes
beta_range = np.linspace(0, 5, 100)

configs = [
    ('homo_FP64', 52, 52),
    ('homo_FP32', 23, 23),
    ('homo_FP16', 10, 10),
    ('homo_INT8', 7, 7),
    ('mixed_FP64_INT8', 52, 7),
    ('mixed_FP32_FP16', 23, 10),
    ('mixed_FP64_FP16', 52, 10),
    ('extreme_FP64_2bit', 52, 2),
]

n_trials = 20
results = {}

for name, hi, lo in configs:
    spike_eigs = []
    overlaps = []
    
    for beta in beta_range:
        trial_eigs = []
        trial_overlaps = []
        for _ in range(n_trials):
            se, ov, _ = spiked_wigner_mixed(beta, hi, lo)
            trial_eigs.append(se)
            trial_overlaps.append(ov)
        spike_eigs.append(np.mean(trial_eigs))
        overlaps.append(np.mean(trial_overlaps))
    
    # Find transition: where overlap crosses 0.5
    overlaps_arr = np.array(overlaps)
    beta_50 = None
    for i in range(len(overlaps_arr)-1):
        if overlaps_arr[i] < 0.5 <= overlaps_arr[i+1]:
            beta_50 = beta_range[i]
            break
    
    # Transition width: range where overlap goes from 0.1 to 0.9
    beta_10 = beta_range[np.argmax(overlaps_arr > 0.1)] if np.any(overlaps_arr > 0.1) else None
    beta_90 = beta_range[np.argmax(overlaps_arr > 0.9)] if np.any(overlaps_arr > 0.9) else None
    width = (beta_90 - beta_10) if (beta_10 is not None and beta_90 is not None) else None
    
    results[name] = {
        'hi_bits': hi, 'lo_bits': lo,
        'beta_50': beta_50,
        'beta_10': float(beta_10) if beta_10 is not None else None,
        'beta_90': float(beta_90) if beta_90 is not None else None,
        'transition_width': float(width) if width is not None else None,
        'overlap_at_1.0': float(np.interp(1.0, beta_range, overlaps)),
    }
    
    w_str = f"{width:.3f}" if width else "N/A"
    print(f"{name}: β₅₀={beta_50:.2f}, width={w_str}, overlap@β=1={np.interp(1.0, beta_range, overlaps):.3f}")

# Compare transition widths
print("\n=== Key Comparison ===")
homo_widths = [results[k]['transition_width'] for k in results if k.startswith('homo_') and results[k]['transition_width'] is not None]
hetero_widths = [results[k]['transition_width'] for k in results if k.startswith('mixed_') or k.startswith('extreme_') and results[k]['transition_width'] is not None]
if homo_widths and hetero_widths:
    print(f"Homo transition width: {np.mean(homo_widths):.3f}")
    print(f"Hetero transition width: {np.mean(hetero_widths):.3f}")
    print(f"Broadened by {np.mean(hetero_widths)/max(np.mean(homo_widths),0.001):.1f}×")

with open(os.path.join(os.path.dirname(__file__), 'results_exp4.json'), 'w') as f:
    json.dump(results, f, indent=2)
print("\nResults saved to results_exp4.json")
