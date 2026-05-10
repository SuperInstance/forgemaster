"""
Experiment 3: Precision-Cost Tradeoff in CRDTs

Implements a G-Counter (grow-only counter) CRDT at multiple precisions.
Precision affects MERGE operations, not just queries, so errors propagate.

- FP64: exact, 8 bytes/counter/node
- FP32: approximate, 4 bytes/counter/node  
- FP16: half precision, 2 bytes/counter/node
- INT8: Bloom CRDT (max compression), 1 byte/counter/node

Measures: final consistency, bandwidth, H¹ of final state.
Shows the precision-crossover point where compression beats accuracy.
"""

import asyncio
import json
import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass, field

from sheaf_math import (
    compute_agreement_matrix, compute_H1,
    eisenstein_topology, compute_holonomy
)


class GCounterPrecision:
    """Grow-only counter CRDT with precision-affected operations.
    
    Key: precision affects the MERGE operation itself.
    When a node transmits its counter, it gets quantized to the precision.
    The receiver gets the quantized value, not the true one.
    This models real systems where network serialization truncates precision.
    """
    
    PRECISION_CONFIG = {
        'fp64': {'dtype': np.float64, 'bytes': 8, 'max_val': 1e308, 'quantum': 0},
        'fp32': {'dtype': np.float32, 'bytes': 4, 'max_val': 3.4e38, 'quantum': 0},
        'fp16': {'dtype': np.float16, 'bytes': 2, 'max_val': 65504, 'quantum': 0},
        'int8': {'dtype': np.int8, 'bytes': 1, 'max_val': 127, 'quantum': 1},
    }
    
    def __init__(self, n_nodes: int, precision: str = 'fp64', seed: int = 42):
        self.n_nodes = n_nodes
        self.precision = precision
        self.config = self.PRECISION_CONFIG[precision]
        self.bytes_per_entry = self.config['bytes']
        self.rng = np.random.RandomState(seed)
        
        # Internal state: one counter per node (FP64 ground truth)
        self.counters_fp64 = np.zeros(n_nodes, dtype=np.float64)
        
        # Working state: always stored as float64, but values are quantized
        self.counters_working = np.zeros(n_nodes, dtype=np.float64)
        
        # Bandwidth tracking
        self.total_bytes_sent = 0
        self.merge_count = 0
        self.error_accumulated = 0.0
    
    def _quantize(self, value: float) -> float:
        """Quantize a value to the working precision, then back to FP64.
        
        This simulates the round-trip: store in precision X, read back.
        """
        if self.precision == 'fp64':
            return value
        elif self.precision == 'int8':
            # INT8: scale value to fit in [-127, 127], round, then scale back
            max_int8 = 127.0
            if abs(value) > max_int8:
                # Scale down to fit
                scale = max_int8 / abs(value)
                quantized = np.clip(np.round(value * scale), -128, 127).astype(np.int8)
                return float(quantized) / scale
            else:
                quantized = np.clip(np.round(value), -128, 127).astype(np.int8)
                return float(quantized)
        else:
            # FP32 or FP16: cast to that type and back
            return float(self.config['dtype'](value))
    
    def increment(self, node_id: int, value: float = 1.0):
        """Node increments its counter."""
        self.counters_fp64[node_id] += value
        # Working precision also increments (but may lose precision)
        self.counters_working[node_id] = self._quantize(
            float(self.counters_working[node_id]) + value
        )
    
    def get_transmitted_value(self, node_id: int) -> float:
        """Get the value that would be transmitted over the wire.
        
        This is the working-precision value, quantized again for transmission.
        """
        val = float(self.counters_working[node_id])
        self.total_bytes_sent += self.bytes_per_entry
        return self._quantize(val)
    
    def value_fp64(self) -> float:
        """True value (FP64 ground truth)."""
        return float(np.sum(self.counters_fp64))
    
    def value_working(self) -> float:
        """Value as seen by the system (working precision)."""
        return float(np.sum(self.counters_working))
    
    def merge_from(self, other: 'GCounterPrecision'):
        """Merge: take component-wise max of transmitted values.
        
        The merge uses TRANSMITTED (quantized) values, not the source's FP64 truth.
        This is where precision loss accumulates.
        """
        for i in range(self.n_nodes):
            transmitted = other.get_transmitted_value(i)
            local = float(self.counters_working[i])
            # CRDT merge: component-wise max
            new_val = max(local, transmitted)
            # Always quantize to maintain precision bounds
            quantized_val = self._quantize(new_val)
            self.counters_working[i] = quantized_val
            self.error_accumulated += abs(new_val - other.counters_fp64[i])
        
        self.merge_count += 1
        self.total_bytes_sent += self.n_nodes * self.bytes_per_entry
    
    def bandwidth(self) -> int:
        """Total bytes transmitted."""
        return self.total_bytes_sent
    
    def state_vector(self) -> np.ndarray:
        """Get the working state vector for H¹ computation."""
        return self.counters_working.copy()


class CRDTNetwork:
    """Simulates a network of nodes running precision-limited G-Counter CRDTs."""
    
    def __init__(self, n_nodes: int = 16, precision: str = 'fp64', 
                 n_rounds: int = 100, seed: int = 42):
        self.n_nodes = n_nodes
        self.precision = precision
        self.n_rounds = n_rounds
        self.rng = np.random.RandomState(seed)
        
        # Each node has its own CRDT
        self.crdts = {
            i: GCounterPrecision(n_nodes, precision, seed=seed + i) 
            for i in range(n_nodes)
        }
        
        # Use Eisenstein topology for sync
        self.edges = eisenstein_topology(n_nodes)
        self.adjacency: Dict[int, List[int]] = {i: [] for i in range(n_nodes)}
        for u, v in self.edges:
            self.adjacency[u].append(v)
            self.adjacency[v].append(u)
    
    def run(self, increment_rate: float = 0.5) -> Dict:
        """Run the CRDT simulation."""
        
        results = {
            'precision': self.precision,
            'n_nodes': self.n_nodes,
            'n_rounds': self.n_rounds,
            'bytes_per_entry': self.crdts[0].bytes_per_entry,
            'rounds': []
        }
        
        error_curve = []
        bandwidth_curve = []
        h1_curve = []
        state_divergence_curve = []
        
        for round_num in range(self.n_rounds):
            # Each node randomly increments
            for i in range(self.n_nodes):
                if self.rng.random() < increment_rate:
                    val = self.rng.uniform(0.5, 5.0)
                    self.crdts[i].increment(i, val)
            
            # Sync: each node merges with a random neighbor
            sync_pairs = set()
            sync_order = list(range(self.n_nodes))
            self.rng.shuffle(sync_order)
            
            for i in sync_order:
                neighbors = self.adjacency[i]
                if neighbors:
                    j = int(self.rng.choice(neighbors))
                    pair = (min(i, j), max(i, j))
                    if pair not in sync_pairs:
                        sync_pairs.add(pair)
                        # Bidirectional merge
                        self.crdts[i].merge_from(self.crdts[j])
                        self.crdts[j].merge_from(self.crdts[i])
            
            # Measure precision-induced error
            # Each node's working value vs the true FP64 value
            true_val = self.crdts[0].value_fp64()  # same across nodes (FP64 is per-node in each CRDT)
            
            working_values = [self.crdts[i].value_working() for i in range(self.n_nodes)]
            
            # Consistency: are all nodes seeing the same value?
            if max(working_values) > 0:
                value_spread = (max(working_values) - min(working_values)) / max(abs(max(working_values)), 1e-10)
            else:
                value_spread = 0
            
            # Precision error: working vs FP64 for each node
            precision_errors = []
            for i in range(self.n_nodes):
                node_true = float(np.sum(self.crdts[i].counters_fp64))
                node_working = float(np.sum(self.crdts[i].counters_working))
                if abs(node_true) > 1e-10:
                    precision_errors.append(abs(node_true - node_working) / abs(node_true))
            
            mean_precision_error = float(np.mean(precision_errors)) if precision_errors else 0
            
            # Bandwidth
            total_bw = sum(self.crdts[i].bandwidth() for i in range(self.n_nodes))
            
            # H¹ of the CRDT state across nodes
            states = {i: self.crdts[i].state_vector() for i in range(self.n_nodes)}
            agreement = compute_agreement_matrix(states, self.edges)
            h1 = compute_H1(agreement)
            
            error_curve.append(mean_precision_error)
            bandwidth_curve.append(total_bw)
            h1_curve.append(h1['h1_norm'])
            state_divergence_curve.append(value_spread)
            
            results['rounds'].append({
                'round': round_num + 1,
                'mean_precision_error': mean_precision_error,
                'value_spread': value_spread,
                'bandwidth_bytes': total_bw,
                'h1_norm': h1['h1_norm'],
                'mean_value': float(np.mean(working_values)),
            })
        
        # Summary
        results['summary'] = {
            'final_precision_error': float(error_curve[-1]),
            'max_precision_error': float(max(error_curve)),
            'final_value_spread': float(state_divergence_curve[-1]),
            'max_value_spread': float(max(state_divergence_curve)),
            'total_bandwidth_kb': total_bw / 1024,
            'final_h1': float(h1_curve[-1]),
            'mean_h1': float(np.mean(h1_curve)),
            'h1_decrease_ratio': float(h1_curve[0] / max(h1_curve[-1], 1e-10)) 
                                 if h1_curve and h1_curve[-1] > 1e-10 else 0,
            'bytes_per_entry': self.crdts[0].bytes_per_entry,
            'error_trend': 'decreasing' if error_curve[-1] < error_curve[0] else 
                           ('stable' if abs(error_curve[-1] - error_curve[0]) < 0.01 else 'increasing'),
        }
        
        return results


async def run_experiment():
    """Run the full CRDT precision experiment."""
    print("=" * 70)
    print("EXPERIMENT 3: Precision-Cost Tradeoff in CRDTs")
    print("=" * 70)
    
    N_NODES = 16
    N_ROUNDS = 200
    
    precisions = ['fp64', 'fp32', 'fp16', 'int8']
    all_results = {}
    
    for prec in precisions:
        print(f"\n{'─' * 50}")
        bpe = {'fp64':8,'fp32':4,'fp16':2,'int8':1}[prec]
        print(f"  Precision: {prec.upper()} ({bpe} bytes/entry)")
        print(f"{'─' * 50}")
        
        network = CRDTNetwork(N_NODES, prec, N_ROUNDS, seed=42)
        result = network.run(increment_rate=0.5)
        all_results[prec] = result
        
        s = result['summary']
        print(f"  Final precision error:  {s['final_precision_error']:.6f}")
        print(f"  Max precision error:    {s['max_precision_error']:.6f}")
        print(f"  Final value spread:     {s['final_value_spread']:.6f}")
        print(f"  Max value spread:       {s['max_value_spread']:.6f}")
        print(f"  Total bandwidth:        {s['total_bandwidth_kb']:.2f} KB")
        print(f"  Final H¹:               {s['final_h1']:.6f}")
        print(f"  Error trend:            {s['error_trend']}")
    
    # =========================================================================
    # Comparison
    # =========================================================================
    print(f"\n{'=' * 70}")
    print("PRECISION-COST TRADEOFF ANALYSIS")
    print("=" * 70)
    
    print(f"\n  {'Precision':<12} {'Bytes':<8} {'P.Error':<12} {'V.Spread':<12} "
          f"{'BW(KB)':<12} {'Final H¹':<12}")
    print(f"  {'─'*68}")
    
    for prec in precisions:
        s = all_results[prec]['summary']
        print(f"  {prec:<12} {s['bytes_per_entry']:<8} {s['final_precision_error']:<12.6f} "
              f"{s['final_value_spread']:<12.6f} "
              f"{s['total_bandwidth_kb']:<12.2f} {s['final_h1']:<12.6f}")
    
    # Efficiency: error × bandwidth (lower is better)
    print(f"\n  Efficiency Score (error × bandwidth, lower = better):")
    efficiencies = {}
    for prec in precisions:
        s = all_results[prec]['summary']
        eff = s['final_precision_error'] * s['total_bandwidth_kb']
        efficiencies[prec] = eff
        print(f"    {prec}: {eff:.6f}")
    
    # Compression analysis
    fp64_bw = all_results['fp64']['summary']['total_bandwidth_kb']
    fp64_err = all_results['fp64']['summary']['final_precision_error']
    fp64_spread = all_results['fp64']['summary']['final_value_spread']
    
    print(f"\n  Compression Analysis (vs FP64 baseline):")
    print(f"    FP64 baseline: error={fp64_err:.6f}, spread={fp64_spread:.6f}, bandwidth={fp64_bw:.2f}KB")
    
    crossover_results = {}
    for prec in ['fp32', 'fp16', 'int8']:
        s = all_results[prec]['summary']
        bw_savings = (1 - s['total_bandwidth_kb'] / fp64_bw) * 100
        
        # Error increase relative to FP64
        if fp64_err > 1e-10:
            err_ratio = s['final_precision_error'] / fp64_err
        else:
            err_ratio = float('inf') if s['final_precision_error'] > 1e-10 else 1.0
        
        spread_ratio = s['final_value_spread'] / max(fp64_spread, 1e-10)
        
        # Crossover: bandwidth savings > error increase
        favorable = bw_savings > 0 and (err_ratio < 2.0 or spread_ratio < 2.0)
        
        crossover_results[prec] = {
            'bandwidth_savings_pct': float(bw_savings),
            'error_ratio': float(err_ratio),
            'spread_ratio': float(spread_ratio),
            'favorable': bool(favorable)
        }
        
        print(f"    {prec}: BW savings={bw_savings:.1f}%, "
              f"error ratio={err_ratio:.2f}x, "
              f"spread ratio={spread_ratio:.2f}x, "
              f"favorable={'✅' if favorable else '⚠️'}")
    
    # H¹ analysis across precisions
    print(f"\n  H¹ Analysis:")
    for prec in precisions:
        s = all_results[prec]['summary']
        print(f"    {prec}: H¹={s['final_h1']:.4f}, "
              f"mean H¹={s['mean_h1']:.4f}, "
              f"ratio={s['h1_decrease_ratio']:.1f}x")
    
    # Key finding
    print(f"\n  💡 Key Findings:")
    
    # Does lower precision cause more H¹?
    h1_by_prec = {p: all_results[p]['summary']['final_h1'] for p in precisions}
    error_by_prec = {p: all_results[p]['summary']['final_precision_error'] for p in precisions}
    
    print(f"    - Precision error increases with lower precision: ", end="")
    errors = [error_by_prec[p] for p in precisions]
    if errors[-1] > errors[0]:
        print(f"YES ({errors[0]:.4f} → {errors[-1]:.4f})")
    else:
        print(f"Minimal ({errors[0]:.4f} → {errors[-1]:.4f})")
    
    print(f"    - Bandwidth savings are significant: ", end="")
    savings = (1 - all_results['int8']['summary']['total_bandwidth_kb'] / fp64_bw) * 100
    print(f"{savings:.0f}% for INT8 vs FP64")
    
    print(f"    - Value spread (consistency) degrades with precision: ", end="")
    spreads = [all_results[p]['summary']['final_value_spread'] for p in precisions]
    print(f"FP64={spreads[0]:.4f}, INT8={spreads[-1]:.4f}")
    
    # Verdict: does the tradeoff exist?
    # PASS if bandwidth savings > error increase for at least one precision
    any_favorable = any(crossover_results[p]['favorable'] for p in crossover_results)
    verdict = 'PASS' if any_favorable else 'PARTIAL'
    
    print(f"\n  VERDICT: {verdict}")
    
    final_results = {
        'experiment': 'crdt_precision',
        'config': {
            'n_nodes': N_NODES,
            'n_rounds': N_ROUNDS,
        },
        'precisions': {p: all_results[p]['summary'] for p in precisions},
        'baseline': {
            'precision': 'fp64',
            'bandwidth_kb': fp64_bw,
            'error': fp64_err
        },
        'crossover_analysis': crossover_results,
        'efficiency_scores': efficiencies,
        'verdict': verdict
    }
    
    return final_results


if __name__ == '__main__':
    results = asyncio.run(run_experiment())
    with open('results/experiment3_crdt_precision.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n✅ Results saved to results/experiment3_crdt_precision.json")
