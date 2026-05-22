#!/usr/bin/env python3
"""Experiment 28: O(1) Memoir Compression

The d=1 manifold conjecture: agent calibration state lives on a low-dimensional
manifold, meaning we can compress checkpoints to a single tile per agent.

Run single agent for 10,000 ticks, record full 8-dim state at every checkpoint.
Compress using SVD at d=1, d=3, d=7 and measure reconstruction quality vs
clock correction performance.

Hypothesis: d=1 compression produces <5% degradation in clock quality despite 8x compression.
If confirmed, memoir goes from O(√T) to O(1) per agent — fundamental improvement.
"""
import json
import math
import os
import random
import numpy as np
from collections import defaultdict

random.seed(42)
np.random.seed(42)

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# === Agent Simulation Parameters ===
TOTAL_TICKS = 10000
CHECKPOINT_INTERVAL = 10
EVAL_TICKS = 1000       # extra ticks to evaluate drift after reconstruction
N_DIMS = 8
DRIFT_THRESHOLD = 0.05  # δ for drift violation
K_CONSENSUS = 0.02      # consensus coupling
NOISE_STD = 0.001       # process noise per tick

# 8-dimensional agent state representing clock calibration
# dims: [offset, skew, drift_rate, temperature_coeff, phase, freq_offset, jitter_bias, gain]
def initial_state():
    return np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0])

def consensus_step(state, neighbor_states, noise=True):
    """Single tick of consensus dynamics on 8-dim state."""
    new_state = state.copy()
    for ns in neighbor_states:
        diff = ns - state
        new_state += K_CONSENSUS * diff
    # Add small process noise (simulating real clock dynamics)
    if noise:
        new_state[:7] += np.random.normal(0, NOISE_STD, 7)
    # Clamp gain to [0.5, 2.0]
    new_state[7] = max(0.5, min(2.0, new_state[7]))
    return new_state

def run_single_agent(ticks):
    """Run a single agent with simulated neighbor interactions for `ticks` steps.
    
    We simulate a single "focal" agent that has 3 virtual neighbors
    running their own dynamics. This creates realistic correlated state evolution.
    """
    focal = initial_state()
    neighbors = [initial_state() + np.random.normal(0, 0.01, N_DIMS) for _ in range(3)]
    
    checkpoints = []
    
    for tick in range(ticks):
        # Update neighbors with their own dynamics (slow random walk)
        for i in range(len(neighbors)):
            neighbors[i] += np.random.normal(0, NOISE_STD * 0.5, N_DIMS)
            neighbors[i][7] = max(0.5, min(2.0, neighbors[i][7]))
        
        # Focal agent consensus step
        focal = consensus_step(focal, neighbors)
        
        # Record checkpoint
        if tick % CHECKPOINT_INTERVAL == 0:
            checkpoints.append(focal.copy())
    
    return np.array(checkpoints)  # shape: (n_checkpoints, 8)

def svd_compress(states, d):
    """Compress state matrix using truncated SVD to d dimensions.
    
    states: (n_checkpoints, 8) matrix
    Returns: (compressed, U_d, singular_values, mean) where compressed is (n_checkpoints, d)
    """
    mean = states.mean(axis=0)
    centered = states - mean
    
    U, S, Vt = np.linalg.svd(centered, full_matrices=False)
    
    # Truncate to d components
    U_d = U[:, :d]
    S_d = S[:d]
    Vt_d = Vt[:d, :]
    
    compressed = U_d * S_d  # (n_checkpoints, d) — the compressed representation
    
    return compressed, U_d, S_d, Vt_d, mean

def svd_reconstruct(compressed, Vt_d, mean):
    """Reconstruct from compressed form."""
    return compressed @ Vt_d + mean

def compute_reconstruction_error(original, reconstructed):
    """Mean squared error and max error."""
    mse = np.mean((original - reconstructed) ** 2)
    max_err = np.max(np.abs(original - reconstructed))
    return float(mse), float(max_err)

def run_clock_correction(state, neighbor_states, ticks):
    """Run clock correction from given state, measure drift over `ticks` steps.
    
    Returns: (final_drift, max_drift, drift_violations, convergence_tick)
    """
    current = state.copy()
    drifts = []
    
    for tick in range(ticks):
        current = consensus_step(current, neighbor_states, noise=True)
        # Drift = distance from consensus centroid
        centroid = np.mean(neighbor_states + [current], axis=0)
        drift = np.linalg.norm(current - centroid)
        drifts.append(drift)
    
    # Find convergence time (first tick where drift stays below threshold for 50 ticks)
    convergence_tick = ticks  # default: never converged
    for i in range(len(drifts) - 50):
        if all(d < DRIFT_THRESHOLD for d in drifts[i:i+50]):
            convergence_tick = i
            break
    
    return {
        "final_drift": float(drifts[-1]),
        "max_drift": float(max(drifts)),
        "mean_drift": float(np.mean(drifts)),
        "drift_violations": int(sum(1 for d in drifts if d > DRIFT_THRESHOLD)),
        "convergence_tick": int(convergence_tick),
        "all_drifts": [float(d) for d in drifts[:100]]  # first 100 for plotting
    }

def main():
    print("=" * 70)
    print("EXPERIMENT 28: O(1) Memoir Compression")
    print("=" * 70)
    
    # Phase 1: Generate full state history
    print("\n[Phase 1] Running agent for 10,000 ticks...")
    checkpoints = run_single_agent(TOTAL_TICKS)
    n_checkpoints = len(checkpoints)
    print(f"  Recorded {n_checkpoints} checkpoints, each {N_DIMS} dims")
    print(f"  Total state data: {n_checkpoints * N_DIMS} floats")
    
    # Analyze intrinsic dimensionality
    print("\n[Phase 2] SVD analysis of state matrix...")
    centered = checkpoints - checkpoints.mean(axis=0)
    U, S, Vt = np.linalg.svd(centered, full_matrices=False)
    
    total_energy = np.sum(S ** 2)
    cumulative = np.cumsum(S ** 2) / total_energy
    
    print("  Singular values:", [f"{s:.6f}" for s in S])
    print("  Cumulative energy retained:")
    for d in range(N_DIMS):
        print(f"    d={d+1}: {cumulative[d]*100:.4f}%")
    
    # Phase 3: Compression comparison
    print("\n[Phase 3] Compression comparison...")
    
    compression_levels = [1, 3, 7]  # d values
    results = {}
    
    # Prepare neighbors for clock correction evaluation
    random.seed(123)
    np.random.seed(123)
    eval_neighbors = [
        initial_state() + np.random.normal(0, 0.01, N_DIMS) 
        for _ in range(3)
    ]
    
    # Take the last checkpoint as the "true" state for evaluation
    true_final_state = checkpoints[-1]
    
    # Baseline: full state clock correction
    print("\n  Baseline (full 8-dim state):")
    baseline_result = run_clock_correction(true_final_state, eval_neighbors, EVAL_TICKS)
    print(f"    Final drift: {baseline_result['final_drift']:.6f}")
    print(f"    Mean drift:  {baseline_result['mean_drift']:.6f}")
    print(f"    Violations:  {baseline_result['drift_violations']}")
    print(f"    Convergence: tick {baseline_result['convergence_tick']}")
    
    results["baseline"] = {
        "dims_per_checkpoint": N_DIMS,
        "total_floats": n_checkpoints * N_DIMS,
        "compression_ratio": 1.0,
        "clock_correction": baseline_result
    }
    
    # Test each compression level
    for d in compression_levels:
        print(f"\n  SVD d={d} compression:")
        
        compressed, U_d, S_d, Vt_d, mean = svd_compress(checkpoints, d)
        reconstructed = svd_reconstruct(compressed, Vt_d, mean)
        
        # Reconstruction error
        mse, max_err = compute_reconstruction_error(checkpoints, reconstructed)
        energy = float(cumulative[d-1])
        total_floats = n_checkpoints * d
        ratio = (n_checkpoints * N_DIMS) / total_floats
        
        print(f"    Reconstruction MSE: {mse:.8f}")
        print(f"    Max reconstruction error: {max_err:.8f}")
        print(f"    Energy retained: {energy*100:.4f}%")
        print(f"    Total floats: {total_floats} (ratio: {ratio:.1f}x)")
        
        # Clock correction with reconstructed final state
        reconstructed_final = reconstructed[-1]
        
        # Reset RNG for fair comparison
        random.seed(123)
        np.random.seed(123)
        cc_result = run_clock_correction(reconstructed_final, eval_neighbors, EVAL_TICKS)
        
        print(f"    Final drift: {cc_result['final_drift']:.6f}")
        print(f"    Mean drift:  {cc_result['mean_drift']:.6f}")
        print(f"    Violations:  {cc_result['drift_violations']}")
        print(f"    Convergence: tick {cc_result['convergence_tick']}")
        
        # Degradation relative to baseline
        drift_degradation = abs(cc_result['mean_drift'] - baseline_result['mean_drift']) / max(baseline_result['mean_drift'], 1e-10) * 100
        print(f"    Drift degradation: {drift_degradation:.2f}%")
        
        results[f"svd_d{d}"] = {
            "dims_per_checkpoint": d,
            "total_floats": total_floats,
            "compression_ratio": ratio,
            "energy_retained": energy,
            "reconstruction_mse": mse,
            "max_reconstruction_error": max_err,
            "clock_correction": cc_result,
            "drift_degradation_pct": drift_degradation
        }
    
    # Phase 4: Extended O(1) analysis — does compression work across time?
    print("\n\n[Phase 4] Time-segment analysis (is compression stable?)...")
    
    # Split into 10 segments of 1000 ticks each, compress independently
    seg_size = n_checkpoints // 10
    segment_results = []
    
    for seg_idx in range(10):
        seg_start = seg_idx * seg_size
        seg_end = seg_start + seg_size
        segment = checkpoints[seg_start:seg_end]
        
        # Compress each segment with d=1
        compressed_seg, _, _, Vt_seg, mean_seg = svd_compress(segment, 1)
        recon_seg = svd_reconstruct(compressed_seg, Vt_seg, mean_seg)
        
        seg_mse, seg_max = compute_reconstruction_error(segment, recon_seg)
        
        _, S_seg, _ = np.linalg.svd(segment - segment.mean(axis=0), full_matrices=False)
        seg_energy = float((S_seg[0] ** 2) / np.sum(S_seg ** 2))
        
        segment_results.append({
            "segment": seg_idx,
            "tick_range": [int(seg_start * CHECKPOINT_INTERVAL), int(seg_end * CHECKPOINT_INTERVAL)],
            "d1_energy": seg_energy,
            "d1_mse": seg_mse,
            "d1_max_error": seg_max
        })
        print(f"    Segment {seg_idx} (ticks {seg_start*CHECKPOINT_INTERVAL}-{seg_end*CHECKPOINT_INTERVAL}): "
              f"d=1 energy={seg_energy*100:.2f}%, MSE={seg_mse:.8f}")
    
    # Phase 5: Random projection baseline (is SVD actually better?)
    print("\n\n[Phase 5] SVD vs Random Projection for d=1...")
    
    # Random projection to d=1
    np.random.seed(999)
    R = np.random.randn(N_DIMS, 1)
    R = R / np.linalg.norm(R)
    
    rp_compressed = checkpoints @ R  # (n_checkpoints, 1)
    rp_reconstructed = rp_compressed @ R.T + (checkpoints.mean(axis=0) - (checkpoints.mean(axis=0) @ R) @ R.T)
    # More accurate: reconstruct with projection and residual
    mean_state = checkpoints.mean(axis=0)
    centered_cp = checkpoints - mean_state
    rp_compressed2 = centered_cp @ R
    rp_reconstructed2 = rp_compressed2 @ R.T + mean_state
    
    rp_mse, rp_max = compute_reconstruction_error(checkpoints, rp_reconstructed2)
    svd_d1_mse = results["svd_d1"]["reconstruction_mse"]
    
    print(f"    SVD d=1 MSE:     {svd_d1_mse:.8f}")
    print(f"    Random Proj MSE: {rp_mse:.8f}")
    print(f"    SVD improvement: {rp_mse / max(svd_d1_mse, 1e-15):.1f}x better")
    
    # Final verdict
    print("\n" + "=" * 70)
    print("VERDICT")
    print("=" * 70)
    
    d1_degradation = results["svd_d1"]["drift_degradation_pct"]
    d1_energy = results["svd_d1"]["energy_retained"]
    
    hypothesis_confirmed = d1_degradation < 5.0
    
    print(f"\n  d=1 energy retained: {d1_energy*100:.2f}%")
    print(f"  d=1 drift degradation: {d1_degradation:.2f}%")
    print(f"  d=1 compression ratio: {results['svd_d1']['compression_ratio']:.1f}x")
    print(f"  Hypothesis (<5% degradation): {'CONFIRMED ✅' if hypothesis_confirmed else 'REJECTED ❌'}")
    
    if hypothesis_confirmed:
        print(f"\n  🏆 Memoir compression: O(√T) → O(1) per agent!")
        print(f"     Single tile per agent suffices for clock correction.")
    
    # Save results
    output = {
        "experiment": "memoir_o1_compression",
        "hypothesis": "d=1 compression produces <5% degradation in clock quality despite 8x compression",
        "confirmed": hypothesis_confirmed,
        "parameters": {
            "total_ticks": TOTAL_TICKS,
            "checkpoint_interval": CHECKPOINT_INTERVAL,
            "n_checkpoints": n_checkpoints,
            "n_dims": N_DIMS,
            "eval_ticks": EVAL_TICKS,
            "drift_threshold": DRIFT_THRESHOLD,
            "k_consensus": K_CONSENSUS,
            "noise_std": NOISE_STD
        },
        "svd_analysis": {
            "singular_values": [float(s) for s in S],
            "cumulative_energy": [float(c) for c in cumulative]
        },
        "results": results,
        "segment_analysis": segment_results,
        "svd_vs_random_projection": {
            "svd_d1_mse": svd_d1_mse,
            "random_projection_mse": rp_mse,
            "svd_improvement_factor": float(rp_mse / max(svd_d1_mse, 1e-15))
        },
        "conclusion": {
            "d1_sufficient": hypothesis_confirmed,
            "compression_achievement": "O(1) per agent" if hypothesis_confirmed else "needs higher d",
            "practical_implication": "Memoir checkpoints compress to single tile per agent" if hypothesis_confirmed else "Higher compression dimension needed"
        }
    }
    
    outpath = os.path.join(RESULTS_DIR, "experiment28_memoir_o1.json")
    with open(outpath, "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\n  Results saved to {outpath}")
    return output

if __name__ == "__main__":
    main()
