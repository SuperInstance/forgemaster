"""
Experiment 1: H¹ Detects Consensus Failure

Simulates Raft-like consensus across N nodes and measures H¹ of the 
"agreement sheaf" under normal operation, network partition, and byzantine faults.

Key hypothesis: H¹ > 0 detects consensus failure BEFORE timeout-based detectors.
"""

import asyncio
import json
import numpy as np
import time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field

from sheaf_math import (
    compute_agreement_matrix, compute_H1, compute_holonomy,
    SimplicialComplex, topology_stats
)


@dataclass
class Node:
    """A consensus node with a replicated log."""
    id: int
    log: List[bytes] = field(default_factory=list)
    term: int = 0
    committed: int = 0
    state: np.ndarray = field(default_factory=lambda: np.zeros(8))
    byzantine: bool = False
    partition_group: int = 0  # 0 = connected to all
    
    def digest(self) -> np.ndarray:
        """Compute a deterministic digest of the node's current log state."""
        if self.byzantine:
            # Byzantine node returns a DIFFERENT digest each time
            # simulating equivocation
            rng = np.random.RandomState(self.id * 1000 + self.term + len(self.log))
            return rng.randn(8)
        
        # Deterministic digest from log state
        d = np.zeros(8)
        d[0] = float(self.term)
        d[1] = float(self.committed)
        # Encode last 6 log entries
        for i in range(min(6, len(self.log))):
            d[2 + i] = float(int.from_bytes(self.log[-(i+1)][:4].ljust(4, b'\x00'), 'big')) % 10000 / 1000.0
        return d


class ConsensusCluster:
    """Simulates a Raft-like consensus cluster."""
    
    def __init__(self, n_nodes: int = 7, quorum_size: int = 4):
        self.n_nodes = n_nodes
        self.quorum_size = quorum_size
        self.nodes = {i: Node(id=i) for i in range(n_nodes)}
        self.edges: List[Tuple[int, int]] = []
        self.active_edges: List[Tuple[int, int]] = []
        self.history: List[Dict] = []
        self.step_count = 0
        self.partition_active = False
        self.partition_group_a: List[int] = []
        self.partition_group_b: List[int] = []
        
        # Build full connectivity
        for i in range(n_nodes):
            for j in range(i + 1, n_nodes):
                self.edges.append((i, j))
        self.active_edges = list(self.edges)
    
    def propose_to_group(self, value: bytes, group: List[int]):
        """Propose a value only to nodes in the specified group."""
        for nid in group:
            node = self.nodes[nid]
            if not node.byzantine:
                node.log.append(value)
                node.term = self.step_count
                node.committed = len(node.log)
    
    def propose(self, value: bytes):
        """Leader proposes a value — all healthy nodes append."""
        self.propose_to_group(value, list(range(self.n_nodes)))
    
    def introduce_partition(self, group_a: List[int], group_b: List[int]):
        """Network partition: nodes in group_a can't talk to group_b."""
        self.partition_active = True
        self.partition_group_a = group_a
        self.partition_group_b = group_b
        
        self.active_edges = []
        for u, v in self.edges:
            if (u in group_a and v in group_b) or (u in group_b and v in group_a):
                continue  # Edge is cut
            self.active_edges.append((u, v))
        
        for nid in group_a:
            self.nodes[nid].partition_group = 1
        for nid in group_b:
            self.nodes[nid].partition_group = 2
    
    def heal_partition(self):
        """Restore full connectivity."""
        self.partition_active = False
        self.active_edges = list(self.edges)
        for node in self.nodes.values():
            node.partition_group = 0
    
    def make_byzantine(self, node_id: int):
        """Turn a node byzantine (lies about its state)."""
        self.nodes[node_id].byzantine = True
    
    def compute_current_H1(self, use_full_topology: bool = True) -> Dict:
        """Compute H¹ of the agreement sheaf on current state.
        
        By default uses the FULL topology (including cut edges) because
        the agreement sheaf is defined on the communication structure — 
        cut edges reveal disagreement between partitions.
        """
        states = {nid: node.digest() for nid, node in self.nodes.items()}
        # Always use full topology for H¹ — cut edges show partition disagreement
        edges = self.edges if use_full_topology else self.active_edges
        
        if not edges:
            return {'h1_norm': 0.0, 'h1_dimension_hint': 0, 'rank': 0, 'rank_deficit': 0,
                    'singular_values': [], 'max_singular': 0.0, 'condition_number': 0.0}
        
        agreement = compute_agreement_matrix(states, edges)
        return compute_H1(agreement)
    
    def detect_failure_timeout(self, timeout_steps: int = 5) -> Dict:
        """Standard timeout-based failure detection.
        
        Detects failures by checking if any node's term is stale relative 
        to the leader (highest term).
        """
        terms = {nid: node.term for nid, node in self.nodes.items() if not node.byzantine}
        if not terms:
            return {'detected': False, 'stale_nodes': [], 'method': 'timeout'}
        
        max_term = max(terms.values())
        stale_nodes = [nid for nid, t in terms.items() if max_term - t > timeout_steps]
        
        return {
            'detected': len(stale_nodes) > 0,
            'stale_nodes': stale_nodes,
            'method': 'timeout'
        }
    
    def detect_failure_H1(self, threshold: float = 0.5) -> Dict:
        """H¹-based failure detection."""
        h1 = self.compute_current_H1()
        return {
            'detected': h1['h1_norm'] > threshold,
            'h1_norm': h1['h1_norm'],
            'h1_dimension': h1['h1_dimension_hint'],
            'method': 'H1'
        }
    
    def step(self, label: str = "") -> Dict:
        """Record a step and compute diagnostics."""
        self.step_count += 1
        h1 = self.compute_current_H1()
        
        record = {
            'step': self.step_count,
            'label': label,
            'h1': h1,
            'timestamp': time.time()
        }
        self.history.append(record)
        return record


async def run_experiment():
    """Run the full H¹ detection experiment."""
    print("=" * 70)
    print("EXPERIMENT 1: H¹ Detects Consensus Failure")
    print("=" * 70)
    
    results = {
        'experiment': 'h1_consensus_detection',
        'config': {'n_nodes': 7, 'quorum_size': 4},
        'phases': {}
    }
    
    # =========================================================================
    # Phase 1: Normal operation — all nodes agree
    # =========================================================================
    print("\n📊 Phase 1: Normal Operation (10 rounds)")
    cluster = ConsensusCluster(n_nodes=7, quorum_size=4)
    
    normal_h1 = []
    for i in range(10):
        cluster.propose(f"entry-{i:04d}".encode())
        record = cluster.step("normal")
        normal_h1.append(record['h1']['h1_norm'])
        print(f"  Round {i+1}: H¹ = {record['h1']['h1_norm']:.6f}")
    
    results['phases']['normal'] = {
        'h1_values': normal_h1,
        'mean_h1': float(np.mean(normal_h1)),
        'max_h1': float(np.max(normal_h1)),
        'all_zero': all(h < 0.01 for h in normal_h1),
        'description': 'All nodes agree — H¹ should be ~0'
    }
    
    # =========================================================================
    # Phase 2: Network Partition — groups diverge
    # =========================================================================
    print("\n📊 Phase 2: Network Partition (group A: [0-3], group B: [4-6])")
    
    cluster.introduce_partition(
        group_a=[0, 1, 2, 3],
        group_b=[4, 5, 6]
    )
    
    partition_h1 = []
    timeout_detected_round = None
    h1_detected_round = None
    
    for i in range(10, 20):
        # ONLY group A gets new entries — group B is isolated
        cluster.propose_to_group(f"entry-{i:04d}".encode(), [0, 1, 2, 3])
        
        # Update terms for group A
        for nid in [0, 1, 2, 3]:
            cluster.nodes[nid].term = i
        
        record = cluster.step("partition")
        partition_h1.append(record['h1']['h1_norm'])
        
        round_in_phase = i - 10 + 1
        
        # Timeout detector (checks if group B terms are stale)
        timeout_det = cluster.detect_failure_timeout(timeout_steps=3)
        if timeout_det['detected'] and timeout_detected_round is None:
            timeout_detected_round = round_in_phase
        
        # H¹ detector
        h1_det = cluster.detect_failure_H1(threshold=0.5)
        if h1_det['detected'] and h1_detected_round is None:
            h1_detected_round = round_in_phase
        
        print(f"  Round {round_in_phase}: H¹ = {record['h1']['h1_norm']:.6f} | "
              f"Timeout: {'YES' if timeout_det['detected'] else 'no'} | "
              f"H¹-det: {'YES' if h1_det['detected'] else 'no'}")
    
    detection_advantage = None
    if timeout_detected_round and h1_detected_round:
        detection_advantage = timeout_detected_round - h1_detected_round
    
    results['phases']['partition'] = {
        'h1_values': partition_h1,
        'mean_h1': float(np.mean(partition_h1)),
        'max_h1': float(np.max(partition_h1)),
        'h1_detected_round': h1_detected_round,
        'timeout_detected_round': timeout_detected_round,
        'detection_advantage': detection_advantage,
        'description': 'Network partition — H¹ should spike immediately'
    }
    
    # =========================================================================
    # Phase 3: Heal partition
    # =========================================================================
    print("\n📊 Phase 3: Heal Partition")
    cluster.heal_partition()
    
    # Group B catches up to group A
    leader_log = cluster.nodes[0].log
    leader_term = cluster.nodes[0].term
    for nid in [4, 5, 6]:
        cluster.nodes[nid].log = list(leader_log)
        cluster.nodes[nid].term = leader_term
        cluster.nodes[nid].committed = len(leader_log)
    
    heal_h1 = []
    for i in range(3):
        cluster.propose(f"entry-{20+i:04d}".encode())
        record = cluster.step("healed")
        heal_h1.append(record['h1']['h1_norm'])
        print(f"  Round {i+1}: H¹ = {record['h1']['h1_norm']:.6f}")
    
    results['phases']['healed'] = {
        'h1_values': heal_h1,
        'mean_h1': float(np.mean(heal_h1)),
        'description': 'Partition healed — H¹ should return to ~0'
    }
    
    # =========================================================================
    # Phase 4: Byzantine Node
    # =========================================================================
    print("\n📊 Phase 4: Byzantine Node (node 3 lies)")
    cluster.make_byzantine(3)
    
    byzantine_h1 = []
    h1_byz_detected_at = None
    timeout_byz_detected_at = None
    
    for i in range(10):
        cluster.propose(f"entry-{23+i:04d}".encode())
        record = cluster.step("byzantine")
        byzantine_h1.append(record['h1']['h1_norm'])
        
        h1_det = cluster.detect_failure_H1(threshold=0.5)
        if h1_det['detected'] and h1_byz_detected_at is None:
            h1_byz_detected_at = i + 1
        
        timeout_det = cluster.detect_failure_timeout(timeout_steps=3)
        if timeout_det['detected'] and timeout_byz_detected_at is None:
            timeout_byz_detected_at = i + 1
        
        print(f"  Round {i+1}: H¹ = {record['h1']['h1_norm']:.6f} | "
              f"H¹-det: {'YES' if h1_det['detected'] else 'no'} | "
              f"Timeout: {'YES' if timeout_det['detected'] else 'no'}")
    
    results['phases']['byzantine'] = {
        'h1_values': byzantine_h1,
        'mean_h1': float(np.mean(byzantine_h1)),
        'max_h1': float(np.max(byzantine_h1)),
        'h1_detected_round': h1_byz_detected_at,
        'timeout_detected_round': timeout_byz_detected_at,
        'description': 'Byzantine node — H¹ detects equivocation immediately'
    }
    
    # =========================================================================
    # Phase 5: Partition BEFORE timeout detection (slow divergence)
    # =========================================================================
    print("\n📊 Phase 5: Early Detection Test (slow divergence)")
    
    cluster2 = ConsensusCluster(n_nodes=7, quorum_size=4)
    
    # Build up normal state first
    for i in range(5):
        cluster2.propose(f"entry-{i:04d}".encode())
        cluster2.step("pre")
    
    # Introduce partition
    cluster2.introduce_partition(
        group_a=[0, 1, 2, 3],
        group_b=[4, 5, 6]
    )
    
    early_h1 = []
    early_detections = []
    early_timeout = None
    
    for i in range(15):
        round_num = i + 1
        # Group A drifts slowly — one entry every 3 rounds
        if i % 3 == 0:
            cluster2.propose_to_group(f"slow-{i:04d}".encode(), [0, 1, 2, 3])
            for nid in [0, 1, 2, 3]:
                cluster2.nodes[nid].term = 5 + i
        
        record = cluster2.step("slow_partition")
        early_h1.append(record['h1']['h1_norm'])
        
        detections = {
            'h1_0.1': record['h1']['h1_norm'] > 0.1,
            'h1_0.5': record['h1']['h1_norm'] > 0.5,
            'h1_1.0': record['h1']['h1_norm'] > 1.0,
        }
        early_detections.append(detections)
        
        timeout_det = cluster2.detect_failure_timeout(timeout_steps=3)
        if timeout_det['detected'] and early_timeout is None:
            early_timeout = round_num
        
        det_str = ', '.join(f"{k}={'Y' if v else 'n'}" for k, v in detections.items())
        print(f"  Round {round_num}: H¹ = {record['h1']['h1_norm']:.6f} | {det_str} | "
              f"Timeout: {'YES' if timeout_det['detected'] else 'no'}")
    
    results['phases']['early_detection'] = {
        'h1_values': early_h1,
        'first_detection_0.1': next((i + 1 for i, d in enumerate(early_detections) if d['h1_0.1']), None),
        'first_detection_0.5': next((i + 1 for i, d in enumerate(early_detections) if d['h1_0.5']), None),
        'first_detection_1.0': next((i + 1 for i, d in enumerate(early_detections) if d['h1_1.0']), None),
        'timeout_detection': early_timeout,
        'description': 'Slow divergence — H¹ detects before timeout at multiple thresholds'
    }
    
    # =========================================================================
    # Summary
    # =========================================================================
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    
    normal_max = results['phases']['normal']['max_h1']
    partition_mean = results['phases']['partition']['mean_h1']
    partition_max = results['phases']['partition']['max_h1']
    byzantine_mean = results['phases']['byzantine']['mean_h1']
    healed_mean = results['phases']['healed']['mean_h1']
    
    print(f"\n  Normal operation H¹ max:        {normal_max:.6f}")
    print(f"  Partition H¹ mean:              {partition_mean:.6f}")
    print(f"  Partition H¹ max:               {partition_max:.6f}")
    print(f"  Byzantine H¹ mean:              {byzantine_mean:.6f}")
    print(f"  Healed H¹ mean:                 {healed_mean:.6f}")
    
    print(f"\n  Detection comparison:")
    print(f"    Partition H¹ detection:       round {h1_detected_round or 'N/A'}")
    print(f"    Partition timeout detection:   round {timeout_detected_round or 'N/A'}")
    if detection_advantage is not None:
        print(f"    H¹ advantage:                 {detection_advantage} rounds faster")
    
    print(f"\n    Byzantine H¹ detection:       round {results['phases']['byzantine']['h1_detected_round'] or 'N/A'}")
    print(f"    Byzantine timeout detection:  round {results['phases']['byzantine']['timeout_detected_round'] or 'N/A'}")
    
    snr_partition = partition_mean / max(normal_max, 1e-10)
    snr_byzantine = byzantine_mean / max(normal_max, 1e-10)
    
    print(f"\n  Signal-to-noise (partition):     {snr_partition:.1f}x")
    print(f"  Signal-to-noise (byzantine):     {snr_byzantine:.1f}x")
    
    # Verdict
    partition_detected = h1_detected_round is not None
    byzantine_detected = results['phases']['byzantine']['h1_detected_round'] is not None
    partition_advantage = detection_advantage is not None and detection_advantage > 0
    
    if partition_detected and byzantine_detected:
        verdict = 'PASS'
        if partition_advantage:
            verdict = 'STRONG PASS'
    elif partition_detected or byzantine_detected:
        verdict = 'PARTIAL'
    else:
        verdict = 'FAIL'
    
    print(f"\n  VERDICT: {verdict}")
    
    results['summary'] = {
        'normal_max_h1': normal_max,
        'partition_mean_h1': partition_mean,
        'partition_max_h1': partition_max,
        'byzantine_mean_h1': byzantine_mean,
        'healed_mean_h1': healed_mean,
        'partition_h1_detection_round': h1_detected_round,
        'partition_timeout_detection_round': timeout_detected_round,
        'detection_advantage_rounds': detection_advantage,
        'byzantine_h1_detection_round': results['phases']['byzantine']['h1_detected_round'],
        'snr_partition': snr_partition,
        'snr_byzantine': snr_byzantine,
        'partition_detected': partition_detected,
        'byzantine_detected': byzantine_detected,
        'partition_advantage': partition_advantage,
        'verdict': verdict
    }
    
    return results


if __name__ == '__main__':
    results = asyncio.run(run_experiment())
    with open('results/experiment1_h1_detection.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n✅ Results saved to results/experiment1_h1_detection.json")
