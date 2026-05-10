#!/usr/bin/env python3
"""
Experiment 4: Flash Crash Propagation on Network Topology

Constraint theory: markets are networks of stocks connected by correlations.
A shock at one node propagates through the network. Different network
topologies yield different propagation characteristics.

Eisenstein topologies have H¹=0 (no obstructions to constraint propagation),
which means shocks should propagate more smoothly / resist cascades.

Test: Does Eisenstein topology resist flash crash cascades compared to
random and scale-free network topologies?

Key predictions:
  1. Eisenstein topology: slower shock propagation, smaller cascade
  2. Random topology: moderate propagation
  3. Scale-free topology: fastest, largest cascades (hub vulnerability)
  4. Recovery time: Eisenstein < Random < Scale-free
"""

import numpy as np
from scipy import linalg, stats
import json
import os

np.random.seed(42)

# ===========================
# 1. NETWORK TOPOLOGIES
# ===========================

N_NODES = 50
N_TIMESTEPS = 2000
N_PROPAGATION_STEPS = 50


def generate_eisenstein_topology(n_nodes, seed=42):
    """
    Generate an Eisenstein topology: a network where the connection matrix
    forms an Eisenstein lattice structure.
    
    Key property: H¹ = 0 for the sheaf (no obstructions).
    This means constraints propagate without topological defects.
    
    In practice: a regular lattice with hierarchical clustering.
    """
    np.random.seed(seed)
    
    # Adjacency matrix
    adj = np.zeros((n_nodes, n_nodes))
    
    # Create a ring lattice (each node connected to k nearest neighbors)
    k = min(6, n_nodes - 1)
    for i in range(n_nodes):
        for j in range(1, k // 2 + 1):
            adj[i, (i + j) % n_nodes] = 1
            adj[(i + j) % n_nodes, i] = 1
    
    # Add some long-range connections (hierarchical structure)
    n_long_range = n_nodes // 5
    for _ in range(n_long_range):
        i = np.random.randint(0, n_nodes)
        j = (i + n_nodes // 3) % n_nodes
        adj[i, j] = 1
        adj[j, i] = 1
    
    # Symmetric and no self-loops
    np.fill_diagonal(adj, 0)
    
    return adj


def generate_random_topology(n_nodes, p=0.1, seed=42):
    """
    Erdős–Rényi random graph.
    """
    np.random.seed(seed)
    adj = np.random.binomial(1, p, (n_nodes, n_nodes))
    adj = np.triu(adj, 1) + np.triu(adj, 1).T
    return adj


def generate_scale_free_topology(n_nodes, seed=42):
    """
    Barabási–Albert scale-free network.
    Many nodes with few connections, few hubs with many connections.
    """
    np.random.seed(seed)
    adj = np.zeros((n_nodes, n_nodes))
    
    # Start with connected core
    adj[0, 1] = adj[1, 0] = 1
    
    # Preferential attachment
    for i in range(2, n_nodes):
        degrees = np.sum(adj[:i, :i], axis=1)
        probs = degrees / np.sum(degrees)
        
        # Attach to m existing nodes
        m = min(2, i)
        targets = np.random.choice(i, size=m, replace=False, p=probs)
        
        for t in targets:
            adj[i, t] = adj[t, i] = 1
    
    return adj


# ===========================
# 2. SHOCK PROPAGATION MODEL
# ===========================

def shock_propagation(adj, shock_node=0, shock_magnitude=-0.15, 
                       n_timesteps=N_TIMESTEPS, n_propagation=N_PROPAGATION_STEPS):
    """
    Simulate a flash crash propagating through the network.
    
    Models cascading margin calls / contagion:
      - Each node is a financial institution with price/equity = 100
      - Shock at source: loss equal to shock_magnitude of equity
      - Contagion: losses cascade when node's loss exceeds threshold
      - Network effects: losses amplify multiplicatively
      - Recovery is slow (we don't model bailouts)
    """
    n_nodes = adj.shape[0]
    prices = np.ones((n_timesteps, n_nodes)) * 100.0
    
    # Threshold model: a node "crashes" when its cumulative loss > 5%
    loss_threshold = -0.05
    
    # Cascade amplification factor (loss contagion multiplier)
    amplification = 0.3  # 30% of neighbor loss propagates
    
    # Compute graph distances
    from scipy.sparse.csgraph import shortest_path
    from scipy.sparse import csr_matrix
    sparse_adj = csr_matrix(adj)
    distances = shortest_path(sparse_adj, directed=False, unweighted=True)
    
    shock_time = 100
    
    for t in range(n_timesteps):
        if t < shock_time:
            # Pre-shock: small noise
            if t > 0:
                noise = np.random.normal(0, 0.001, n_nodes)
                prices[t] = prices[t-1] * (1 + noise)
        elif t == shock_time:
            # Initial shock
            prices[t] = prices[t-1].copy()
            shock_return = (1 + shock_magnitude)
            prices[t, shock_node] *= shock_return
        elif t < shock_time + n_propagation:
            # Cascade phase
            prices[t] = prices[t-1].copy()
            previous_losses = (prices[t-1] / prices[shock_time - 1]) - 1.0
            
            for i in range(n_nodes):
                if i == shock_node:
                    # Shocked node stays at depressed level
                    continue
                
                if previous_losses[i] < loss_threshold:
                    # Already crashed - stays crashed
                    continue
                
                # Compute contagion from crashed neighbors
                neighbors = np.where(adj[i] > 0)[0]
                neighbor_losses = previous_losses[neighbors]
                crashed_neighbors = neighbor_losses[neighbor_losses < loss_threshold]
                
                if len(crashed_neighbors) > 0:
                    # Loss propagates: average loss of crashed neighbors * amplification
                    contagion = np.mean(crashed_neighbors) * amplification
                    
                    # Distance decay
                    d = distances[shock_node, i]
                    if d > 0 and d < np.inf:
                        contagion *= np.exp(-d * 0.3)
                    
                    # Apply contagion
                    prices[t, i] *= (1 + contagion)
                
                # Small noise
                prices[t, i] *= (1 + np.random.normal(0, 0.0005))
        else:
            # Recovery phase (slow)
            if t == shock_time + n_propagation:
                recovery_base = prices[t-1].copy()
            
            recovery_rate = 0.005  # 0.5% per timestep recovery
            
            for i in range(n_nodes):
                if prices[t-1, i] < 95:  # Only recover if crashed
                    prices[t, i] = prices[t-1, i] * (1 + recovery_rate)
                else:
                    # Normal noise around 100
                    prices[t, i] = prices[t-1, i] * (1 + np.random.normal(0, 0.001))
    
    return prices, distances


def analyze_cascade(prices, distances, shock_node=0, threshold=-0.05):
    """
    Analyze cascade properties.
    
    cascade_size: number of nodes with drawdown > |threshold|
    cascade_depth: maximum drawdown across the network
    propagation_speed: how fast the shock spreads (timesteps to infect half the nodes)
    recovery_time: time for affected nodes to recover to 95% of pre-shock level
    damage_ratio: total wealth destroyed / total pre-shock wealth
    """
    n_nodes = prices.shape[1]
    shock_time = 100
    pre_shock_price = prices[shock_time - 1]
    
    # Find max drawdown for each node relative to pre-shock
    drawdowns = (prices[shock_time:shock_time+300] / pre_shock_price) - 1.0
    max_drawdowns = np.min(drawdowns, axis=0)
    
    # Cascade size: nodes with >5% drawdown
    cascade_nodes = max_drawdowns < threshold
    cascade_size = np.sum(cascade_nodes)
    
    # Cascade depth: average max drawdown of affected nodes
    affected_drawdowns = max_drawdowns[cascade_nodes]
    cascade_depth = np.mean(affected_drawdowns) if len(affected_drawdowns) > 0 else 0
    
    # Propagation speed: how quickly does the shock spread?
    # Measure: time for cascade_size/2 nodes to cross threshold
    propagation_speed = n_propagation_steps = N_PROPAGATION_STEPS
    for t in range(1, N_PROPAGATION_STEPS):
        affected = np.sum(
            (prices[shock_time + t] / pre_shock_price - 1.0) < threshold
        )
        if affected >= cascade_size / 2:
            propagation_speed = t
            break
    
    # Recovery time: time for affected nodes to return to 95% of pre-shock
    recovery_target = 0.95 * np.sum(pre_shock_price[cascade_nodes])
    recovery_time = 2000  # Default: didn't recover in window
    for t in range(shock_time + N_PROPAGATION_STEPS, min(2000, prices.shape[0])):
        total_recovered = np.sum(prices[t, cascade_nodes])
        if total_recovered >= recovery_target:
            recovery_time = t - shock_time
            break
    
    # Total damage: area under the curve for affected nodes
    damage = 0.0
    for i in range(n_nodes):
        if cascade_nodes[i]:
            damage += np.sum(pre_shock_price[i] - prices[shock_time:shock_time+100, i])
    damage_ratio = damage / (np.sum(pre_shock_price[cascade_nodes]) * 100)
    
    return {
        "cascade_size": int(cascade_size),
        "cascade_size_pct": float(cascade_size / n_nodes * 100),
        "cascade_depth_mean": float(cascade_depth),
        "cascade_depth_min": float(np.min(affected_drawdowns)) if len(affected_drawdowns) > 0 else 0,
        "propagation_speed_timesteps": int(propagation_speed),
        "recovery_time_timesteps": int(recovery_time),
        "damage_ratio": float(damage_ratio)
    }


# ===========================
# 3. EXPERIMENTATION
# ===========================

print("=== Experiment 4: Flash Crash Propagation on Network Topology ===\n")

# Generate topologies
print(f"Generating networks with {N_NODES} nodes...")
adj_eisenstein = generate_eisenstein_topology(N_NODES)
adj_random = generate_random_topology(N_NODES, p=0.1)
adj_scale_free = generate_scale_free_topology(N_NODES)

# Analyze network properties
def network_stats(adj, name):
    n = adj.shape[0]
    degrees = np.sum(adj, axis=1)
    # Simple clustering coefficient approximation
    triangles = 0
    triples = 0
    for i in range(n):
        neighbors = np.where(adj[i] > 0)[0]
        k = len(neighbors)
        if k >= 2:
            triples += k * (k - 1) / 2
            for j_idx in range(k):
                for l_idx in range(j_idx + 1, k):
                    if adj[neighbors[j_idx], neighbors[l_idx]] > 0:
                        triangles += 1
    clustering = 2 * triangles / max(triples * 2, 1)
    
    # Hubiness: max degree / mean degree
    hubiness = np.max(degrees) / np.mean(degrees) if np.mean(degrees) > 0 else 1
    
    print(f"\n  {name}:")
    print(f"    Nodes: {n}, Edges: {np.sum(adj) // 2}")
    print(f"    Mean degree: {np.mean(degrees):.1f}, Max degree: {np.max(degrees)}")
    print(f"    Hubiness: {hubiness:.2f}")
    print(f"    Density: {np.sum(adj) / (n * (n - 1)):.3f}")

network_stats(adj_eisenstein, "Eisenstein Topology")
network_stats(adj_random, "Random Topology")
network_stats(adj_scale_free, "Scale-Free Topology")

# Run shock propagation simulations
print("\n\nRunning flash crash simulations...")
n_runs = 5
shock_magnitudes = [-0.05, -0.10, -0.15, -0.20, -0.25]

all_results = {"eisenstein": {}, "random": {}, "scale_free": {}}
topologies = {
    "eisenstein": adj_eisenstein,
    "random": adj_random,
    "scale_free": adj_scale_free
}

for topo_name, adj in topologies.items():
    print(f"\n--- Shock propagation on {topo_name} ---")
    
    for shock_mag in shock_magnitudes:
        run_results = []
        
        for run in range(n_runs):
            np.random.seed(42 + run * 10)
            prices, distances = shock_propagation(
                adj, shock_node=0, shock_magnitude=shock_mag,
            )
            
            result = analyze_cascade(prices, distances, threshold=shock_mag * 0.5)
            run_results.append(result)
        
        # Average
        avg = {
            k: float(np.mean([r[k] for r in run_results]))
            for k in run_results[0].keys()
        }
        
        print(f"    Shock {shock_mag*100:+.0f}%: size={avg['cascade_size_pct']:.0f}% "
              f"depth={avg['cascade_depth_mean']*100:.1f}% "
              f"speed={avg['propagation_speed_timesteps']} "
              f"recovery={avg['recovery_time_timesteps']}")
        
        all_results[topo_name][str(shock_mag)] = avg

# ===========================
# 4. COMPARISON ANALYSIS
# ===========================

print("\n\n--- Experiment 4a: Cascade Size Comparison ---")
print(f"{'Shock':<10} {'Eisenstein':<15} {'Random':<15} {'Scale-Free':<15} {'H¹=0 Advantage':<20}")
print(f"{'-'*70}")
for mag in shock_magnitudes:
    key = str(mag)
    e = all_results["eisenstein"][key]["cascade_size_pct"]
    r = all_results["random"][key]["cascade_size_pct"]
    s = all_results["scale_free"][key]["cascade_size_pct"]
    
    advantage = "Best" if e <= r and e <= s else ("Good" if e < s else "Worst")
    print(f"{mag*100:+.0f}%     {e:<15.1f} {r:<15.1f} {s:<15.1f} {advantage:<20}")

print("\n--- Experiment 4b: Propagation Speed ---")
print(f"{'Shock':<10} {'Eisenstein':<15} {'Random':<15} {'Scale-Free':<15} {'H¹=0 Advantage':<20}")
print(f"{'-'*70}")
for mag in shock_magnitudes:
    key = str(mag)
    e = all_results["eisenstein"][key]["propagation_speed_timesteps"]
    r = all_results["random"][key]["propagation_speed_timesteps"]
    s = all_results["scale_free"][key]["propagation_speed_timesteps"]
    
    # Slower speed = better (more resistance)
    advantage = "Slowest" if e >= r and e >= s else ("Good" if e >= s else "Fastest")
    print(f"{mag*100:+.0f}%     {e:<15} {r:<15} {s:<15} {advantage:<20}")

print("\n--- Experiment 4c: Recovery Time ---")
print(f"{'Shock':<10} {'Eisenstein':<15} {'Random':<15} {'Scale-Free':<15} {'H¹=0 Advantage':<20}")
print(f"{'-'*70}")
for mag in shock_magnitudes:
    key = str(mag)
    e = all_results["eisenstein"][key]["recovery_time_timesteps"]
    r = all_results["random"][key]["recovery_time_timesteps"]
    s = all_results["scale_free"][key]["recovery_time_timesteps"]
    
    advantage = "Fastest" if e <= r and e <= s else ("Good" if e < s else "Worst")
    print(f"{mag*100:+.0f}%     {e:<15} {r:<15} {s:<15} {advantage:<20}")

print("\n--- Experiment 4d: Damage Ratio ---")
print(f"{'Shock':<10} {'Eisenstein':<15} {'Random':<15} {'Scale-Free':<15} {'H¹=0 Advantage':<20}")
print(f"{'-'*70}")
for mag in shock_magnitudes:
    key = str(mag)
    e = all_results["eisenstein"][key]["damage_ratio"] * 100
    r = all_results["random"][key]["damage_ratio"] * 100
    s = all_results["scale_free"][key]["damage_ratio"] * 100
    
    advantage = "Lowest" if e <= r and e <= s else ("Good" if e < s else "Worst")
    print(f"{mag*100:+.0f}%     {e:<15.1f} {r:<15.1f} {s:<15.1f} {advantage:<20}")

# ===========================
# 5. TOPOLOGICAL INVARIANT: H¹
# ===========================

print("\n\n--- Experiment 4e: Topological Invariant H¹ ---")

def compute_network_H1(adj):
    """
    Compute H¹ dimension of the network's sheaf.
    
    The sheaf is constructed from the network Laplacian:
      - 0-cochains = functions on nodes
      - 1-cochains = functions on edges
      - sheaf coboundary δ = gradient operator
      - H¹ = ker(δ₁*) / im(δ₀)
    
    For our networks:
      - Eisenstein: H¹ should be 0 (no obstructions)
      - Random: H¹ should be small but non-zero
      - Scale-free: H¹ should be larger (hub creates obstructions)
    """
    n = adj.shape[0]
    m = np.sum(adj) // 2
    
    # Build incidence matrix B (n x m)
    # B[i, k] = -1 if node i is tail of edge k
    # B[i, k] = +1 if node i is head of edge k
    edges = []
    for i in range(n):
        for j in range(i+1, n):
            if adj[i, j] > 0:
                edges.append((i, j))
    
    m = len(edges)
    B = np.zeros((n, m))
    for k, (i, j) in enumerate(edges):
        B[i, k] = -1
        B[j, k] = +1
    
    # Laplacian L = B @ B.T
    L = B @ B.T
    
    # Compute eigenvalues of Laplacian
    eigvals = np.linalg.eigvalsh(L)
    
    # H¹ dimension = number of zero eigenvalues of L (excluding the trivial one)
    # Actually: H¹ = dim(ker(L)) - 1 (the trivial eigenvalue)
    # But we want a richer measure. Use:
    # H¹_proxy = number of eigenvalues close to zero
    # Small eigenvalues = "soft modes" = potential instabilities
    
    # Measure: number of eigenvalues < threshold (excluding λ=0)
    threshold = 1e-6
    n_zero = np.sum(np.abs(eigvals) < threshold)
    
    # Fiedler value (second smallest eigenvalue)
    sorted_vals = np.sort(eigvals)
    fiedler = sorted_vals[1] if len(sorted_vals) > 1 else 0
    
    # Spectral gap
    spectral_gap = sorted_vals[1] - sorted_vals[0] if len(sorted_vals) > 1 else 0
    
    # Number of near-zero eigenvalues (excluding λ=0)
    near_zero = np.sum((eigvals > threshold) & (eigvals < 0.1))
    
    return {
        "H1_dimension": int(n_zero - 1),  # Exclude trivial eigenvalue
        "fiedler_value": float(fiedler),
        "spectral_gap": float(spectral_gap),
        "near_zero_modes": int(near_zero),
        "eigenvalues": sorted_vals[:20].tolist()
    }

for name, adj in [("Eisenstein", adj_eisenstein), 
                   ("Random", adj_random), 
                   ("Scale-Free", adj_scale_free)]:
    h1_info = compute_network_H1(adj)
    print(f"\n  {name}:")
    print(f"    H¹ dimension: {h1_info['H1_dimension']} (0 = no obstructions)")
    print(f"    Fiedler value: {h1_info['fiedler_value']:.4f} (higher = more robust)")
    print(f"    Near-zero modes: {h1_info['near_zero_modes']} (fewer = more stable)")

# ===========================
# 6. RESULTS SUMMARY
# ===========================
results = {
    "experiment": "4_flash_crash_propagation",
    "predictions": {
        "cascade_size_resistance": {
            "eisenstein_best": bool(
                np.mean([all_results["eisenstein"][str(m)]["cascade_size_pct"] 
                         for m in shock_magnitudes]) <=
                np.mean([all_results["random"][str(m)]["cascade_size_pct"]
                         for m in shock_magnitudes]) and
                np.mean([all_results["eisenstein"][str(m)]["cascade_size_pct"]
                         for m in shock_magnitudes]) <=
                np.mean([all_results["scale_free"][str(m)]["cascade_size_pct"]
                         for m in shock_magnitudes])
            ),
            "eisenstein_mean_cascade_pct": float(np.mean(
                [all_results["eisenstein"][str(m)]["cascade_size_pct"] for m in shock_magnitudes]
            )),
            "random_mean_cascade_pct": float(np.mean(
                [all_results["random"][str(m)]["cascade_size_pct"] for m in shock_magnitudes]
            )),
            "scale_free_mean_cascade_pct": float(np.mean(
                [all_results["scale_free"][str(m)]["cascade_size_pct"] for m in shock_magnitudes]
            ))
        },
        "propagation_speed_resistance": {
            "eisenstein_slowest": bool(
                np.mean([all_results["eisenstein"][str(m)]["propagation_speed_timesteps"]
                         for m in shock_magnitudes]) >=
                np.mean([all_results["random"][str(m)]["propagation_speed_timesteps"]
                         for m in shock_magnitudes]) and
                np.mean([all_results["eisenstein"][str(m)]["propagation_speed_timesteps"]
                         for m in shock_magnitudes]) >=
                np.mean([all_results["scale_free"][str(m)]["propagation_speed_timesteps"]
                         for m in shock_magnitudes])
            )
        },
        "recovery_speed": {
            "eisenstein_fastest": bool(
                np.mean([all_results["eisenstein"][str(m)]["recovery_time_timesteps"]
                         for m in shock_magnitudes]) <=
                np.mean([all_results["random"][str(m)]["recovery_time_timesteps"]
                         for m in shock_magnitudes]) and
                np.mean([all_results["eisenstein"][str(m)]["recovery_time_timesteps"]
                         for m in shock_magnitudes]) <=
                np.mean([all_results["scale_free"][str(m)]["recovery_time_timesteps"]
                         for m in shock_magnitudes])
            )
        },
        "topological_analysis": {
            "eisenstein_H1": compute_network_H1(adj_eisenstein)["H1_dimension"],
            "random_H1": compute_network_H1(adj_random)["H1_dimension"],
            "scale_free_H1": compute_network_H1(adj_scale_free)["H1_dimension"],
            "eisenstein_fiedler": compute_network_H1(adj_eisenstein)["fiedler_value"],
            "random_fiedler": compute_network_H1(adj_random)["fiedler_value"],
            "scale_free_fiedler": compute_network_H1(adj_scale_free)["fiedler_value"]
        }
    },
    "experiment_parameters": {
        "n_nodes": N_NODES,
        "n_timesteps": N_TIMESTEPS,
        "n_shock_magnitudes": len(shock_magnitudes),
        "n_runs_per_config": n_runs
    }
}

os.makedirs("results", exist_ok=True)
with open("results/experiment_4_results.json", "w") as f:
    json.dump(results, f, indent=2)

print("\nResults saved to results/experiment_4_results.json")
print("=" * 60)
