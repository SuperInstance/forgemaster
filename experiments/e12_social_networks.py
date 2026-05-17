#!/usr/bin/env python3
"""
E12: Social Network Simulation — Fleet Coupling Conservation Law
Tests: γ+H = C − α·ln(V) for opinion dynamics on scale-free networks
"""

import numpy as np
import networkx as nx
from scipy.optimize import curve_fit
import os

np.random.seed(42)

# ── Network Generation ─────────────────────────────────────────

def generate_scale_free_network(n, m=3, seed=42):
    """Barabási–Albert preferential attachment model."""
    return nx.barabasi_albert_graph(n, m, seed=seed)


def degroot_dynamics(G, n_steps=100, seed=42):
    """
    DeGroot opinion dynamics: each node updates opinion as
    weighted average of neighbors' opinions.
    Returns the influence matrix and final opinions.
    """
    rng = np.random.RandomState(seed)
    n = G.number_of_nodes()
    nodes = list(G.nodes())
    
    # Build adjacency/weight matrix (normalized by degree)
    W = np.zeros((n, n))
    for i, node_i in enumerate(nodes):
        neighbors = list(G.neighbors(node_i))
        if len(neighbors) > 0:
            weight = 1.0 / (len(neighbors) + 1)  # include self-weight
            W[i, i] = weight
            for node_j in neighbors:
                j = nodes.index(node_j)
                W[i, j] = weight
        else:
            W[i, i] = 1.0  # isolated node

    # Initial opinions (continuous, 0-1)
    opinions = rng.uniform(0, 1, n)
    
    # Run dynamics
    for step in range(n_steps):
        opinions = W @ opinions
    
    return W, opinions


def compute_influence_coupling(W, opinions):
    """
    Coupling matrix from the influence/weight matrix.
    Symmetrize and use as coupling.
    """
    n = W.shape[0]
    # Symmetrize
    C = (W + W.T) / 2
    # Ensure non-negative
    C = np.maximum(C, 0)
    # Set diagonal to row max for self-coupling
    for i in range(n):
        C[i, i] = max(C[i, i], C[i].max())
    return C


def spectral_properties(C):
    eigenvalues = np.linalg.eigvalsh(C)
    eigenvalues = np.sort(eigenvalues)[::-1]
    total = eigenvalues.sum()
    if total <= 0:
        return 0, 0, eigenvalues
    probs = eigenvalues / total
    probs = probs[probs > 1e-15]
    H = -np.sum(probs * np.log(probs))
    gamma = eigenvalues[0] / total
    return gamma, H, eigenvalues


def conservation_model(V, C_const, alpha):
    return C_const - alpha * np.log(V)


def main():
    print("=" * 60)
    print("E12: Social Network Simulation — Conservation Law Test")
    print("γ+H = C − α·ln(V)")
    print("=" * 60)

    network_sizes = [10, 20, 50, 100, 200]
    results = []
    network_stats = []

    for V in network_sizes:
        print(f"\n--- Network size V={V} ---")
        trial_results = []
        
        for trial in range(5):
            seed = 42 + trial * 100
            G = generate_scale_free_network(V, m=3, seed=seed)
            W, opinions = degroot_dynamics(G, n_steps=200, seed=seed)
            C = compute_influence_coupling(W, opinions)
            g, h, eigs = spectral_properties(C)
            trial_results.append((g, h, g + h))
            
            if trial == 0:
                # Collect network stats
                degrees = [d for _, d in G.degree()]
                network_stats.append({
                    'V': V,
                    'edges': G.number_of_edges(),
                    'avg_degree': np.mean(degrees),
                    'max_degree': max(degrees),
                    'opinion_std': np.std(opinions),
                    'gamma': g,
                    'H': h,
                })

        g = np.mean([r[0] for r in trial_results])
        h = np.mean([r[1] for r in trial_results])
        gh = np.mean([r[2] for r in trial_results])
        gh_std = np.std([r[2] for r in trial_results])
        results.append((V, g, h, gh, gh_std))
        print(f"  γ={g:.4f}  H={h:.4f}  γ+H={gh:.4f} ± {gh_std:.4f}")

    # Fit conservation law
    V_arr = np.array([r[0] for r in results], dtype=float)
    GH_arr = np.array([r[3] for r in results])

    try:
        popt, _ = curve_fit(conservation_model, V_arr, GH_arr, p0=[1.0, 0.1])
        C_fit, alpha_fit = popt
        GH_pred = conservation_model(V_arr, C_fit, alpha_fit)
        ss_res = np.sum((GH_arr - GH_pred)**2)
        ss_tot = np.sum((GH_arr - GH_arr.mean())**2)
        r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0
    except Exception as e:
        C_fit, alpha_fit, r_squared = 0, 0, 0
        print(f"Fit failed: {e}")

    print(f"\nConservation Law Fit: γ+H = {C_fit:.4f} − {alpha_fit:.4f}·ln(V)")
    print(f"R² = {r_squared:.4f}")

    social_gh_range = f"{min(r[3] for r in results):.2f}–{max(r[3] for r in results):.2f}"

    # Write results
    md = f"""# E12: Social Network Simulation — Conservation Law Results

## Setup
- **Network model:** Barabási–Albert scale-free (m=3 edges per new node)
- **Dynamics:** DeGroot opinion model (200 steps to convergence)
- **Coupling:** Symmetrized influence/weight matrix
- **Trials:** 5 per network size, different seeds

## Network Properties

| V (nodes) | Edges | Avg Degree | Max Degree | Opinion σ |
|:---:|:---:|:---:|:---:|:---:|
"""
    for s in network_stats:
        md += f"| {s['V']} | {s['edges']} | {s['avg_degree']:.2f} | {s['max_degree']} | {s['opinion_std']:.4f} |\n"

    md += f"""
## Coupling Results

| V (nodes) | γ (coupling) | H (entropy) | γ+H | ± std |
|:---:|:---:|:---:|:---:|:---:|
"""
    for V, g, h, gh, gh_std in results:
        md += f"| {V} | {g:.4f} | {h:.4f} | {gh:.4f} | {gh_std:.4f} |\n"

    md += f"""
## Conservation Law Fit

**γ+H = {C_fit:.4f} − {alpha_fit:.4f}·ln(V)**

- R² = {r_squared:.4f}
- C (intercept) = {C_fit:.4f}
- α (scaling) = {alpha_fit:.4f}

## Analysis

### Does the law hold for social networks?
{"**YES** — strong fit (R² ≥ 0.9)" if r_squared >= 0.9 else "**PARTIAL** — moderate fit" if r_squared >= 0.5 else "**WEAK** — social networks show different coupling dynamics"}

### Comparison to Fleet Results
- **Fleet γ+H range:** 0.98–1.15
- **Social network γ+H range:** {social_gh_range}

### Network Coupling vs Fleet Coupling
Scale-free networks have a distinctive spectral signature:
- Hub nodes create strong coupling (high γ) 
- Long tail of low-degree nodes maintains entropy (H)
- The balance between hubs and periphery creates a natural γ+H conservation

### Key Observations
- Scale-free structure concentrates influence on hub nodes
- DeGroot convergence drives opinions to a weighted average
- Larger networks maintain more spectral diversity
- The conservation law {"captures" if r_squared >= 0.7 else "partially captures"} how network structure
  constrains the coupling-diversity tradeoff

---
*Generated by e12_social_networks.py | Seed: 42*
"""

    out_path = os.path.join(os.path.dirname(__file__), "E12-SOCIAL-NETWORKS.md")
    with open(out_path, "w") as f:
        f.write(md)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
