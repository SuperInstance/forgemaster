"""
Experiment 2: Holonomy in Gossip Protocols

Simulates gossip/anti-entropy protocols on different topologies and measures:
- Convergence speed
- Holonomy (state drift after full communication cycles)
- Berry phase (systematic drift)

PREDICTION: Topologies with higher triangle density (triangles/edge) converge faster
because triangles enforce H¹ = 0 constraints on the communication sheaf.
"""

import asyncio
import json
import numpy as np
import time
from typing import Dict, List, Tuple
from dataclasses import dataclass, field

from sheaf_math import (
    eisenstein_topology, ring_topology, random_topology,
    topology_stats, compute_agreement_matrix, compute_H1,
    compute_holonomy, berry_phase_drift, chern_simons_invariant
)


@dataclass
class GossipNode:
    """A node in a gossip protocol."""
    id: int
    state: np.ndarray
    initial_state: np.ndarray = field(default_factory=lambda: np.array([]))
    
    def __post_init__(self):
        self.initial_state = self.state.copy()


class GossipNetwork:
    """Simulates a gossip/anti-entropy protocol on a topology."""
    
    def __init__(self, n_nodes: int, state_dim: int, topology: str, 
                 seed: int = 42, target_degree: int = 4):
        self.n_nodes = n_nodes
        self.state_dim = state_dim
        self.topology_name = topology
        self.rng = np.random.RandomState(seed)
        self.target_degree = target_degree
        
        # Build topology
        if topology == 'eisenstein':
            self.edges = eisenstein_topology(n_nodes)
        elif topology == 'ring':
            self.edges = ring_topology(n_nodes)
        elif topology == 'random':
            self.edges = random_topology(n_nodes, degree=target_degree, seed=seed)
        elif topology == 'complete':
            # Complete graph (upper bound)
            self.edges = [(i, j) for i in range(n_nodes) for j in range(i+1, n_nodes)]
        elif topology == 'grid':
            # 2D grid
            self.edges = []
            side = int(np.ceil(np.sqrt(n_nodes)))
            for r in range(side):
                for c in range(side):
                    idx = r * side + c
                    if idx >= n_nodes:
                        break
                    if c + 1 < side and idx + 1 < n_nodes:
                        self.edges.append((idx, idx + 1))
                    if r + 1 < side and idx + side < n_nodes:
                        self.edges.append((idx, idx + side))
        else:
            raise ValueError(f"Unknown topology: {topology}")
        
        # Build adjacency for fast lookup
        self.adjacency: Dict[int, List[int]] = {i: [] for i in range(n_nodes)}
        for u, v in self.edges:
            self.adjacency[u].append(v)
            self.adjacency[v].append(u)
        
        # Initialize nodes with random states
        self.nodes = {}
        for i in range(n_nodes):
            state = self.rng.randn(state_dim)
            self.nodes[i] = GossipNode(id=i, state=state)
        
        self.topo_stats = topology_stats(self.edges, n_nodes)
        self.history = []
    
    def gossip_round(self, mixing_rate: float = 0.3) -> Dict:
        """One round of gossip: each node averages with all neighbors (parallel)."""
        new_states = {}
        
        for i in range(self.n_nodes):
            neighbors = self.adjacency[i]
            if not neighbors:
                new_states[i] = self.nodes[i].state.copy()
                continue
            
            # Anti-entropy: average with neighbors
            neighbor_states = [self.nodes[j].state for j in neighbors]
            avg = np.mean(neighbor_states, axis=0)
            new_states[i] = (1 - mixing_rate) * self.nodes[i].state + mixing_rate * avg
        
        # Update all at once (synchronous round)
        for i in range(self.n_nodes):
            self.nodes[i].state = new_states[i]
        
        # Measure agreement
        states = {i: self.nodes[i].state for i in range(self.n_nodes)}
        agreement = compute_agreement_matrix(states, self.edges)
        h1 = compute_H1(agreement)
        
        # Measure convergence to mean
        all_states = np.array([self.nodes[i].state for i in range(self.n_nodes)])
        mean_state = np.mean(all_states, axis=0)
        convergence = float(np.mean([
            np.linalg.norm(self.nodes[i].state - mean_state) 
            for i in range(self.n_nodes)
        ]))
        
        # Holonomy: deviation of first node from its initial state
        holonomy = compute_holonomy(self.nodes[0].initial_state, self.nodes[0].state)
        
        return {
            'h1': h1,
            'convergence': convergence,
            'holonomy_node0': holonomy,
            'mean_state_norm': float(np.linalg.norm(mean_state))
        }
    
    def run(self, n_rounds: int = 100, mixing_rate: float = 0.3) -> Dict:
        """Run gossip protocol for n_rounds."""
        results = {
            'topology': self.topology_name,
            'topo_stats': self.topo_stats,
            'n_nodes': self.n_nodes,
            'n_rounds': n_rounds,
            'rounds': []
        }
        
        convergence_curve = []
        h1_curve = []
        holonomy_curve = []
        
        # States at cycle boundaries for Berry phase computation
        cycle_states = [self.nodes[0].state.copy()]
        
        initial_convergence = None
        
        for r in range(n_rounds):
            metrics = self.gossip_round(mixing_rate)
            
            if initial_convergence is None:
                initial_convergence = metrics['convergence']
            
            convergence_curve.append(metrics['convergence'])
            h1_curve.append(metrics['h1']['h1_norm'])
            holonomy_curve.append(metrics['holonomy_node0'])
            
            # Save state at cycle boundaries (every 10 rounds)
            if (r + 1) % 10 == 0:
                cycle_states.append(self.nodes[0].state.copy())
            
            results['rounds'].append({
                'round': r + 1,
                'convergence': metrics['convergence'],
                'h1_norm': metrics['h1']['h1_norm'],
                'holonomy': metrics['holonomy_node0']
            })
        
        # Compute Berry phase drift
        berry = berry_phase_drift(cycle_states)
        
        # Find convergence round (to 10% and 1% of initial)
        threshold_10 = 0.1 * (initial_convergence or 1.0)
        threshold_1 = 0.01 * (initial_convergence or 1.0)
        convergence_round_10 = next(
            (i + 1 for i, c in enumerate(convergence_curve) if c < threshold_10),
            n_rounds
        )
        convergence_round_1 = next(
            (i + 1 for i, c in enumerate(convergence_curve) if c < threshold_1),
            n_rounds
        )
        
        final_convergence = convergence_curve[-1] if convergence_curve else float('inf')
        
        results['summary'] = {
            'initial_convergence': float(initial_convergence) if initial_convergence else 0,
            'final_convergence': float(final_convergence),
            'convergence_round_10pct': convergence_round_10,
            'convergence_round_1pct': convergence_round_1,
            'berry_phase_drift': berry,
            'mean_h1': float(np.mean(h1_curve)),
            'final_h1': float(h1_curve[-1]) if h1_curve else 0,
            'mean_holonomy': float(np.mean(holonomy_curve)),
            'final_holonomy': float(holonomy_curve[-1]) if holonomy_curve else 0,
            'h1_decrease_ratio': float(h1_curve[0] / max(h1_curve[-1], 1e-10)) 
                                 if h1_curve else 0,
            'triangles_per_edge': self.topo_stats['n_triangles'] / max(self.topo_stats['n_edges'], 1),
        }
        
        return results


async def run_experiment():
    """Run the full gossip holonomy experiment."""
    print("=" * 70)
    print("EXPERIMENT 2: Holonomy in Gossip Protocols")
    print("=" * 70)
    print("\n  Testing: Triangle-rich topologies converge faster (H¹ → 0 faster)")
    print("  Because triangles enforce consistency constraints on the sheaf")
    
    N_NODES = 16
    STATE_DIM = 8
    N_ROUNDS = 200
    MIXING_RATE = 0.3
    
    topologies = ['eisenstein', 'ring', 'random', 'grid', 'complete']
    all_results = {}
    
    for topo in topologies:
        print(f"\n{'─' * 50}")
        print(f"  Topology: {topo.upper()} ({N_NODES} nodes)")
        print(f"{'─' * 50}")
        
        try:
            network = GossipNetwork(N_NODES, STATE_DIM, topo, seed=42, target_degree=4)
        except Exception as e:
            print(f"  ⚠️  Could not build topology: {e}")
            continue
        
        ts = network.topo_stats
        print(f"  Edges: {ts['n_edges']}, "
              f"Triangles: {ts['n_triangles']}, "
              f"Avg degree: {ts['avg_degree']:.1f}, "
              f"Triangles/edge: {ts['n_triangles']/max(ts['n_edges'],1):.2f}")
        
        result = network.run(N_ROUNDS, MIXING_RATE)
        all_results[topo] = result
        
        s = result['summary']
        print(f"\n  Initial convergence: {s['initial_convergence']:.6f}")
        print(f"  Final convergence:   {s['final_convergence']:.6f}")
        print(f"  Convergence to 10%:  round {s['convergence_round_10pct']}")
        print(f"  Convergence to 1%:   round {s['convergence_round_1pct']}")
        print(f"  Berry phase drift:   {s['berry_phase_drift']:.6f}")
        print(f"  H¹ decrease ratio:   {s['h1_decrease_ratio']:.1f}x")
        print(f"  Final H¹:            {s['final_h1']:.6f}")
    
    # =========================================================================
    # Comparison
    # =========================================================================
    print(f"\n{'=' * 70}")
    print("COMPARISON")
    print("=" * 70)
    
    # Sort by convergence speed (10% threshold)
    sorted_topos = sorted(all_results.keys(), 
                          key=lambda t: all_results[t]['summary']['convergence_round_10pct'])
    
    print(f"\n  {'Topology':<15} {'Edges':<8} {'Triangles':<10} {'Tri/Edge':<10} "
          f"{'Conv.10%':<10} {'Conv.1%':<10} {'Berry':<12} {'H¹↓':<10}")
    print(f"  {'─'*85}")
    
    for topo in sorted_topos:
        ts = all_results[topo]['topo_stats']
        s = all_results[topo]['summary']
        print(f"  {topo:<15} {ts['n_edges']:<8} {ts['n_triangles']:<10} "
              f"{s['triangles_per_edge']:<10.2f} "
              f"{s['convergence_round_10pct']:<10} {s['convergence_round_1pct']:<10} "
              f"{s['berry_phase_drift']:<12.6f} {s['h1_decrease_ratio']:<10.1f}")
    
    # Correlation: triangles/edge vs convergence speed
    tri_per_edge = []
    conv_rounds = []
    berry_drifts = []
    for topo in all_results:
        s = all_results[topo]['summary']
        tri_per_edge.append(s['triangles_per_edge'])
        conv_rounds.append(s['convergence_round_10pct'])
        berry_drifts.append(s['berry_phase_drift'])
    
    if len(tri_per_edge) > 2:
        corr_conv = np.corrcoef(tri_per_edge, conv_rounds)[0, 1]
        corr_berry = np.corrcoef(tri_per_edge, berry_drifts)[0, 1]
        print(f"\n  Correlation (triangles/edge vs convergence):  {corr_conv:.3f}")
        print(f"  Correlation (triangles/edge vs berry drift):  {corr_berry:.3f}")
        print(f"  (Negative = more triangles → faster convergence, less drift)")
    
    winner = sorted_topos[0]
    print(f"\n  🏆 Fastest convergence: {winner} "
          f"(round {all_results[winner]['summary']['convergence_round_10pct']})")
    
    # The real question: is convergence correlated with triangle density?
    top_2 = sorted_topos[:2]
    has_triangle_advantage = all(
        all_results[t]['summary']['triangles_per_edge'] > 0 
        for t in top_2
    )
    
    print(f"\n  Top 2 fastest: {', '.join(top_2)}")
    
    # Check if the "triangle-free" topology (ring) is slowest
    ring_result = all_results.get('ring', {})
    ring_conv = ring_result.get('summary', {}).get('convergence_round_10pct', 0)
    ring_tri = ring_result.get('topo_stats', {}).get('n_triangles', 0)
    
    print(f"\n  Ring (0 triangles): convergence at round {ring_conv}")
    print(f"  This is {ring_conv / all_results[winner]['summary']['convergence_round_10pct']:.1f}x slower than {winner}")
    
    final_results = {
        'experiment': 'gossip_holonomy',
        'config': {
            'n_nodes': N_NODES,
            'state_dim': STATE_DIM,
            'n_rounds': N_ROUNDS,
            'mixing_rate': MIXING_RATE
        },
        'topologies': {t: all_results[t]['summary'] for t in all_results},
        'topology_stats': {t: all_results[t]['topo_stats'] for t in all_results},
        'winner': winner,
        'correlation_triangles_convergence': float(corr_conv) if len(tri_per_edge) > 2 else None,
        'correlation_triangles_berry': float(corr_berry) if len(tri_per_edge) > 2 else None,
        'ring_vs_winner_ratio': ring_conv / all_results[winner]['summary']['convergence_round_10pct'],
        'verdict': 'PASS' if (corr_conv < -0.5 if len(tri_per_edge) > 2 else False) else 'PARTIAL'
    }
    
    return final_results


if __name__ == '__main__':
    results = asyncio.run(run_experiment())
    with open('results/experiment2_gossip_holonomy.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n✅ Results saved to results/experiment2_gossip_holonomy.json")
