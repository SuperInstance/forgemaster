"""
EXP-3: System Size Scaling — Does BBP Broadening Appear at Larger N?
Cycle 0 used N=20 exclusively. BBP transition width was 0.404 for ALL configs — suspicious.
Question: Does the BBP transition broaden with heterogeneity at larger matrix sizes?
"""
import numpy as np
import json

np.random.seed(456)

def make_spiked_wigner(N, beta, noise_std):
    """Create spiked Wigner matrix: beta * v v^T + noise."""
    v = np.random.randn(N)
    v = v / np.linalg.norm(v)
    noise = np.random.randn(N, N) * noise_std
    noise = (noise + noise.T) / (np.sqrt(2) * np.sqrt(N))
    M = beta * np.outer(v, v) + noise
    return M, v

def compute_overlap(eigvec, true_v):
    """Overlap between spike eigenvector and true signal."""
    return abs(np.dot(eigvec, true_v))

def measure_bbp_transition(N, noise_std_high, noise_std_low, beta_range):
    """Measure BBP transition width for heterogeneous matrix."""
    transition_data = []
    
    for beta in beta_range:
        # Create block-structured heterogeneous matrix
        half = N // 2
        M_high, v_high = make_spiked_wigner(half, beta, noise_std_high)
        M_low, v_low = make_spiked_wigner(half, beta, noise_std_low)
        
        # Block matrix with cross-coupling
        M = np.zeros((N, N))
        M[:half, :half] = M_high
        M[half:, half:] = M_low
        # Cross terms (weaker coupling between precision groups)
        cross = np.random.randn(half, half) * 0.01
        M[:half, half:] = cross
        M[half:, :half] = cross.T
        M = (M + M.T) / 2
        
        eigenvalues, eigenvectors = np.linalg.eigh(M)
        
        # True signal is the top eigenvector of the un-noised matrix
        true_v = np.zeros(N)
        true_v[:half] = v_high
        true_v[half:] = v_low
        true_v = true_v / np.linalg.norm(true_v)
        
        top_idx = np.argmax(eigenvalues)
        overlap = compute_overlap(eigenvectors[:, top_idx], true_v)
        
        transition_data.append({"beta": beta, "overlap": overlap, "top_eig": float(eigenvalues[top_idx])})
    
    return transition_data

# Test across system sizes
sizes = [10, 20, 50, 100]
beta_range = np.linspace(0, 5, 50)
results = {}

for N in sizes:
    print(f"  Testing N={N}...")
    
    # Homogeneous (low noise)
    data_homo = measure_bbp_transition(N, 1e-7, 1e-7, beta_range)
    # Heterogeneous (high × low noise)
    data_hetero = measure_bbp_transition(N, 1e-7, 0.1, beta_range)
    
    # Measure transition width (range where overlap goes from 0.1 to 0.9)
    def measure_width(data):
        overlaps = [d["overlap"] for d in data]
        betas = [d["beta"] for d in data]
        
        try:
            idx_10 = next(i for i, o in enumerate(overlaps) if o > 0.1)
            idx_90 = next(i for i, o in enumerate(overlaps) if o > 0.9)
            width = betas[idx_90] - betas[idx_10]
        except StopIteration:
            width = float('inf')
        
        # Also find beta_50 (where overlap crosses 0.5)
        try:
            idx_50 = next(i for i, o in enumerate(overlaps) if o > 0.5)
            beta_50 = betas[idx_50]
        except StopIteration:
            beta_50 = float('inf')
        
        return width, beta_50
    
    w_homo, b50_homo = measure_width(data_homo)
    w_hetero, b50_hetero = measure_width(data_hetero)
    
    ratio = w_hetero / w_homo if w_homo > 0 and w_homo != float('inf') else float('inf')
    
    results[f"N={N}"] = {
        "homo_width": float(w_homo) if w_homo != float('inf') else None,
        "hetero_width": float(w_hetero) if w_hetero != float('inf') else None,
        "broadening_ratio": float(ratio) if ratio != float('inf') else None,
        "homo_beta50": float(b50_homo) if b50_homo != float('inf') else None,
        "hetero_beta50": float(b50_hetero) if b50_hetero != float('inf') else None,
    }

print("\nEXP-3: SYSTEM SIZE SCALING (BBP TRANSITION)")
print("=" * 70)
print(f"{'N':>5} {'Homo Width':>12} {'Hetero Width':>14} {'Ratio':>10} {'Homo β₅₀':>12} {'Hetero β₅₀':>12}")
print("-" * 65)
for name, r in results.items():
    hw = f"{r['homo_width']:.3f}" if r['homo_width'] else "∞"
    htw = f"{r['hetero_width']:.3f}" if r['hetero_width'] else "∞"
    ratio = f"{r['broadening_ratio']:.2f}×" if r['broadening_ratio'] else "∞"
    hb = f"{r['homo_beta50']:.2f}" if r['homo_beta50'] else "∞"
    htb = f"{r['hetero_beta50']:.2f}" if r['hetero_beta50'] else "∞"
    print(f"{name:>5} {hw:>12} {htw:>14} {ratio:>10} {hb:>12} {htb:>12}")

# Key question: does broadening increase with N?
print("\nBROADENING TREND:")
for name, r in results.items():
    if r['broadening_ratio']:
        direction = "↑ BROADENING WITH SIZE" if r['broadening_ratio'] > 1.2 else "~ SAME"
        print(f"  {name}: ratio = {r['broadening_ratio']:.2f}× {direction}")

with open("results_exp3.json", "w") as f:
    json.dump(results, f, indent=2)
