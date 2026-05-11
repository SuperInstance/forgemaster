#!/usr/bin/env python3
"""
Simulator 2: Cross-Domain Transfer

Test whether snap topologies transfer across domains.
A well-calibrated snap from domain A should work in domain B when the randomness shape matches.
"""

import json
import random
import math
from collections import defaultdict
from typing import List, Tuple, Dict

# ─── Randomness Flavors ─────────────────────────────────────────────

def generate_coin(n: int) -> List[float]:
    """Binary randomness (2 outcomes) — tetrahedral."""
    return [random.choice([0.0, 1.0]) for _ in range(n)]

def generate_d6(n: int) -> List[float]:
    """Uniform 6 outcomes — cubic."""
    return [random.randint(1, 6) / 6.0 for _ in range(n)]

def generate_d20(n: int) -> List[float]:
    """Rich bounded (20 outcomes) — dodecahedral."""
    return [random.randint(1, 20) / 20.0 for _ in range(n)]

def generate_2d6(n: int) -> List[float]:
    """Bell curve (sum of 2d6) — gaussian-like."""
    return [(random.randint(1,6) + random.randint(1,6)) / 12.0 for _ in range(n)]

def generate_categorical(n: int, categories: int = 4) -> List[float]:
    """Categorical — tetrahedral-ish."""
    return [random.randint(1, categories) / categories for _ in range(n)]

def generate_directional(n: int) -> List[float]:
    """Directional (8 compass) — octahedral."""
    return [random.randint(1, 8) / 8.0 for _ in range(n)]

def generate_gaussian(n: int) -> List[float]:
    """Normal distribution — smooth gradient."""
    return [max(0, min(1, random.gauss(0.5, 0.15))) for _ in range(n)]

FLAVORS = {
    'coin': generate_coin,
    'd6': generate_d6,
    'd20': generate_d20,
    '2d6': generate_2d6,
    'categorical': generate_categorical,
    'directional': generate_directional,
    'gaussian': generate_gaussian,
}

# Shape compatibility: which flavors have similar snap topologies
SHAPE_GROUPS = {
    'binary': ['coin'],
    'uniform': ['d6', 'd20'],
    'bell': ['2d6', 'gaussian'],
    'categorical': ['categorical', 'directional'],
}


# ─── Snap Function ───────────────────────────────────────────────────

class SnapFunction:
    """Tolerance-based snap function that can be calibrated on one domain."""
    
    def __init__(self, tolerance: float = 0.2):
        self.tolerance = tolerance
        self.baseline = 0.5
        self.calibration_samples = 0
        self.calibration_sum = 0.0
        self.calibration_var = 0.0
    
    def snap(self, value: float) -> Tuple[bool, float]:
        delta = abs(value - self.baseline)
        return (delta <= self.tolerance, delta)
    
    def calibrate(self, values: List[float], rate: float = 0.1):
        """Train the snap function on a domain's data."""
        for v in values:
            self.calibration_samples += 1
            self.calibration_sum += v
            old_baseline = self.baseline
            self.baseline = self.baseline * (1 - rate) + v * rate
            
            # Adaptive tolerance: track variance to set tolerance
            diff = abs(v - old_baseline)
            self.tolerance = self.tolerance * 0.95 + diff * 0.05
    
    def reset_baseline(self):
        """Reset baseline but keep tolerance calibration."""
        self.baseline = 0.5
    
    def copy_tolerance(self) -> 'SnapFunction':
        """Return a new snap with same tolerance but fresh baseline."""
        new = SnapFunction(self.tolerance)
        new.calibration_samples = self.calibration_samples
        return new


def transfer_efficiency(source_flavor: str, target_flavor: str, 
                        calibration_size: int = 500, test_size: int = 500) -> dict:
    """Test how well a snap calibrated on source transfers to target."""
    
    # Train on source domain
    source_data = FLAVORS[source_flavor](calibration_size + test_size)
    snap = SnapFunction()
    snap.calibrate(source_data[:calibration_size])
    
    # Get the trained tolerance
    trained_tolerance = snap.tolerance
    
    # Transfer to target domain (keep tolerance, reset baseline)
    transferred = snap.copy_tolerance()
    target_data = FLAVORS[target_flavor](test_size)
    
    # Also create a fresh snap for target (no transfer)
    fresh = SnapFunction()
    fresh.calibrate(FLAVORS[target_flavor](calibration_size))
    
    # Measure how quickly each snap calibrates on target data
    # "Calibration speed" = how fast baseline converges to target distribution mean
    transferred_errors = []
    fresh_errors = []
    
    target_mean = sum(target_data) / len(target_data)
    
    trans_baseline = 0.5
    fresh_baseline = 0.5
    
    transferred_deltas_detected = 0
    fresh_deltas_detected = 0
    transferred_correct_deltas = 0  # delta that was actually anomalous
    fresh_correct_deltas = 0
    
    for i, v in enumerate(target_data):
        # Transferred snap
        t_snapped, t_delta = transferred.snap(v)
        if not t_snapped:
            transferred_deltas_detected += 1
        trans_baseline = trans_baseline * 0.9 + v * 0.1
        transferred_errors.append(abs(trans_baseline - target_mean))
        
        # Fresh snap
        f_snapped, f_delta = fresh.snap(v)
        if not f_snapped:
            fresh_deltas_detected += 1
        fresh_baseline = fresh_baseline * 0.9 + v * 0.1
        fresh_errors.append(abs(fresh_baseline - target_mean))
        
        # Also update both
        transferred.baseline = trans_baseline
        fresh.baseline = fresh_baseline
    
    # Transfer efficiency: ratio of convergence speeds
    avg_trans_error = sum(transferred_errors[-100:]) / 100
    avg_fresh_error = sum(fresh_errors[-100:]) / 100
    
    # Shapes match?
    matching = False
    for group_name, flavors in SHAPE_GROUPS.items():
        if source_flavor in flavors and target_flavor in flavors:
            matching = True
            break
    
    return {
        'source': source_flavor,
        'target': target_flavor,
        'shapes_match': matching,
        'trained_tolerance': round(trained_tolerance, 4),
        'transferred_final_error': round(avg_trans_error, 4),
        'fresh_final_error': round(avg_fresh_error, 4),
        'transfer_efficiency': round(avg_fresh_error / max(avg_trans_error, 0.0001), 4),
        'transferred_deltas_detected': transferred_deltas_detected,
        'fresh_deltas_detected': fresh_deltas_detected,
        'convergence_ratio': round(sum(transferred_errors) / max(sum(fresh_errors), 1), 4),
    }


def run_simulation(num_trials: int = 50000) -> dict:
    """Run cross-domain transfer simulation."""
    flavor_names = list(FLAVORS.keys())
    
    all_results = []
    matching_results = []
    mismatching_results = []
    
    # Run all pairwise transfers
    for _ in range(num_trials // (len(flavor_names) * len(flavor_names))):
        for source in flavor_names:
            for target in flavor_names:
                result = transfer_efficiency(source, target)
                all_results.append(result)
                if result['shapes_match']:
                    matching_results.append(result)
                else:
                    mismatching_results.append(result)
    
    # Aggregate
    def agg(results, key):
        if not results:
            return 0
        return sum(r[key] for r in results) / len(results)
    
    summary = {
        'total_transfers': len(all_results),
        'avg_transfer_efficiency_matching': round(agg(matching_results, 'transfer_efficiency'), 4),
        'avg_transfer_efficiency_mismatching': round(agg(mismatching_results, 'transfer_efficiency'), 4),
        'avg_convergence_matching': round(agg(matching_results, 'convergence_ratio'), 4),
        'avg_convergence_mismatching': round(agg(mismatching_results, 'convergence_ratio'), 4),
        'avg_deltas_matching': round(agg(matching_results, 'transferred_deltas_detected'), 2),
        'avg_deltas_mismatching': round(agg(mismatching_results, 'transferred_deltas_detected'), 2),
        'matching_count': len(matching_results),
        'mismatching_count': len(mismatching_results),
    }
    
    # Per-flavor analysis
    per_flavor = defaultdict(lambda: {'efficiency': [], 'convergence': []})
    for r in all_results:
        if r['source'] != r['target']:
            per_flavor[r['source']]['efficiency'].append(r['transfer_efficiency'])
            per_flavor[r['source']]['convergence'].append(r['convergence_ratio'])
    
    flavor_summary = {}
    for f in flavor_names:
        if per_flavor[f]['efficiency']:
            flavor_summary[f] = {
                'avg_transfer_efficiency': round(sum(per_flavor[f]['efficiency']) / len(per_flavor[f]['efficiency']), 4),
                'avg_convergence': round(sum(per_flavor[f]['convergence']) / len(per_flavor[f]['convergence']), 4),
            }
    
    return {
        'num_trials': len(all_results),
        'summary': summary,
        'per_flavor': flavor_summary,
        'sample_transfers': all_results[:20],  # first 20 for inspection
        'insight': (
            "Matching shapes (e.g., coin→coin, d6→d20) should transfer better than mismatching shapes "
            "(e.g., coin→gaussian, 2d6→directional). Transfer efficiency > 1.0 means the transferred snap "
            "calibrates FASTER than a fresh snap — supporting the theory that snap topologies are domain-invariant."
        ),
    }


if __name__ == '__main__':
    print("🔄 Cross-Domain Transfer — Running 50,000 trials...")
    results = run_simulation(50000)
    
    with open('results_transfer.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Results saved to results_transfer.json")
    s = results['summary']
    print(f"\n📊 Transfer Efficiency:")
    print(f"  Matching shapes:    {s['avg_transfer_efficiency_matching']:.4f}")
    print(f"  Mismatching shapes: {s['avg_transfer_efficiency_mismatching']:.4f}")
    print(f"  Matching convergence:    {s['avg_convergence_matching']:.4f}")
    print(f"  Mismatching convergence: {s['avg_convergence_mismatching']:.4f}")
    print(f"\n  Matching: {s['matching_count']} | Mismatching: {s['mismatching_count']}")
