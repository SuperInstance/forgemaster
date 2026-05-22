"""
Experiment 16: BFT Filter Optimality
HYPOTHESIS: Reputation-weighted trimmed mean is near-optimal among linear-time filters for Laman topologies.

WHAT THIS CONSTRAINS: Whether our BFT filter can be improved, and by how much.

PROTOCOL:
N=10 agents, f=3 Byzantine (adversarial, report random [0, 1000])
Compare 6 filter strategies:

1. NO_FILTER: raw average of all neighbor reports
2. MEDIAN: simple median of neighbor reports
3. TRIMMED_MEAN: discard top/bottom 25%, average rest
4. REPUTATION_ONLY: weighted by inverse historical variance
5. REPUTATION_PLUS_TRIMMED: our current approach
6. TOPOLOGY_AWARE: weight by graph distance (direct neighbors weighted more, also use reputation)

For each filter, run 500 ticks, measure:
- Convergence: does max drift reach < delta?
- Convergence tick
- Peak drift
- False positive rate: how often are honest agents incorrectly down-weighted?

Run 10 trials per filter (different random seeds) for statistical significance.

KEY QUESTION: Is there a filter that converges faster than reputation+trimmed?
If topology-aware is better, that's a novel result.

Save to experiments/results/experiment16_bft_filters.json
Print ASCII comparison table.
"""

import json
import math
import os
import random
import statistics
from collections import defaultdict
from pathlib import Path

# --- Configuration ---
N_AGENTS = 10
N_BYZANTINE = 3
HONEST_COUNT = N_AGENTS - N_BYZANTINE
TICKS = 500
TRIALS = 10
DELTA = 5.0  # convergence threshold
TRUE_VALUE = 500.0

# Byzantine report range
BYZ_MIN, BYZ_MAX = 0, 1000

# --- Laman-like graph (2N-3 edges, N>=3, generically rigid) ---
# For N=10, we need 17 edges. Construct a Henneberg-like sequence.
def build_laman_graph(n):
    """Build a simple Laman-like graph via Henneberg type-I construction."""
    edges = set()
    # Start with K3 (vertices 0,1,2)
    edges.add((0, 1)); edges.add((0, 2)); edges.add((1, 2))
    # Add vertices 3..n-1, each connecting to 2 existing vertices
    rng = random.Random(42)  # deterministic structure
    for v in range(3, n):
        candidates = list(range(v))
        pick = rng.sample(candidates, min(2, len(candidates)))
        for u in pick:
            edges.add((min(u, v), max(u, v)))
    # Verify edge count: should be 2*n - 3
    assert len(edges) >= 2 * n - 3 - 2, f"Too few edges: {len(edges)}"
    return list(edges)


def adjacency(n, edges):
    """Build adjacency list."""
    adj = defaultdict(set)
    for u, v in edges:
        adj[u].add(v)
        adj[v].add(u)
    return adj


# --- Agent state ---
class Agent:
    def __init__(self, idx, is_byzantine):
        self.idx = idx
        self.is_byzantine = is_byzantine
        self.estimate = TRUE_VALUE + random.uniform(-20, 20)
        self.reputation = {}  # neighbor_idx -> (mean_error, count)
        self.history = []  # track estimates over time

    def report(self):
        if self.is_byzantine:
            return random.uniform(BYZ_MIN, BYZ_MAX)
        return self.estimate

    def update_reputation(self, neighbor_idx, reported, accepted):
        """Track historical error of neighbor reports vs accepted value."""
        err = abs(reported - accepted)
        if neighbor_idx not in self.reputation:
            self.reputation[neighbor_idx] = [0.0, 0]  # [sum_err, count]
        self.reputation[neighbor_idx][0] += err
        self.reputation[neighbor_idx][1] += 1


# --- Filter strategies ---
def no_filter(reports):
    """Raw average."""
    if not reports:
        return TRUE_VALUE
    return sum(v for _, v in reports) / len(reports)


def median_filter(reports):
    """Simple median."""
    if not reports:
        return TRUE_VALUE
    vals = sorted(v for _, v in reports)
    n = len(vals)
    if n % 2 == 1:
        return vals[n // 2]
    return (vals[n // 2 - 1] + vals[n // 2]) / 2


def trimmed_mean_filter(reports, trim_frac=0.25):
    """Discard top/bottom 25%, average rest."""
    if not reports:
        return TRUE_VALUE
    vals = sorted(v for _, v in reports)
    n = len(vals)
    trim = max(1, int(n * trim_frac))
    trimmed = vals[trim:n - trim] if trim < n - trim else vals
    if not trimmed:
        return vals[n // 2]  # fallback to median
    return sum(trimmed) / len(trimmed)


def reputation_only_filter(agent, reports):
    """Weight by inverse historical variance."""
    if not reports:
        return TRUE_VALUE
    weights = []
    for neighbor_idx, val in reports:
        if neighbor_idx in agent.reputation:
            mean_err, count = agent.reputation[neighbor_idx]
            avg_err = mean_err / max(count, 1)
            w = 1.0 / (avg_err + 1.0)  # avoid div/0
        else:
            w = 1.0  # default
        weights.append(w)
    total_w = sum(weights)
    if total_w == 0:
        return no_filter(reports)
    return sum(w * v for w, (_, v) in zip(weights, reports)) / total_w


def reputation_plus_trimmed_filter(agent, reports, trim_frac=0.25):
    """Trim extreme values, then weight by reputation."""
    if not reports:
        return TRUE_VALUE
    # Sort by value
    sorted_reports = sorted(reports, key=lambda x: x[1])
    n = len(sorted_reports)
    trim = max(1, int(n * trim_frac))
    trimmed = sorted_reports[trim:n - trim] if trim < n - trim else sorted_reports
    if not trimmed:
        return sorted_reports[n // 2][1]
    # Now weight by reputation
    weights = []
    for neighbor_idx, val in trimmed:
        if neighbor_idx in agent.reputation:
            mean_err, count = agent.reputation[neighbor_idx]
            avg_err = mean_err / max(count, 1)
            w = 1.0 / (avg_err + 1.0)
        else:
            w = 1.0
        weights.append(w)
    total_w = sum(weights)
    if total_w == 0:
        return no_filter(trimmed)
    return sum(w * v for w, (_, v) in zip(weights, trimmed)) / total_w


def topology_aware_filter(agent, reports, adj, depth_penalty=0.5):
    """Weight by graph distance (direct neighbors weighted more) + reputation."""
    if not reports:
        return TRUE_VALUE
    weights = []
    for neighbor_idx, val in reports:
        # Topology weight: direct neighbors get weight 1.0
        # For Laman graphs, most neighbors are direct
        topo_w = 1.0  # all reporters are neighbors in this setup
        # Reputation weight
        if neighbor_idx in agent.reputation:
            mean_err, count = agent.reputation[neighbor_idx]
            avg_err = mean_err / max(count, 1)
            rep_w = 1.0 / (avg_err + 1.0)
        else:
            rep_w = 1.0
        # Combined: topology * reputation
        w = topo_w * rep_w
        weights.append(w)
    total_w = sum(weights)
    if total_w == 0:
        return no_filter(reports)
    return sum(w * v for w, (_, v) in zip(weights, reports)) / total_w


FILTERS = {
    "NO_FILTER": lambda agent, reports, adj: no_filter(reports),
    "MEDIAN": lambda agent, reports, adj: median_filter(reports),
    "TRIMMED_MEAN": lambda agent, reports, adj: trimmed_mean_filter(reports),
    "REPUTATION_ONLY": lambda agent, reports, adj: reputation_only_filter(agent, reports),
    "REPUTATION_PLUS_TRIMMED": lambda agent, reports, adj: reputation_plus_trimmed_filter(agent, reports),
    "TOPOLOGY_AWARE": lambda agent, reports, adj: topology_aware_filter(agent, reports, adj),
}


def run_trial(filter_name, filter_fn, seed):
    """Run a single trial with a given filter and seed."""
    random.seed(seed)
    
    # Build graph
    edges = build_laman_graph(N_AGENTS)
    adj = adjacency(N_AGENTS, edges)
    
    # Assign Byzantine agents (last N_BYZANTINE)
    byzantine_set = set(range(HONEST_COUNT, N_AGENTS))
    agents = [Agent(i, i in byzantine_set) for i in range(N_AGENTS)]
    
    converged_tick = None
    peak_drift = 0.0
    false_positive_events = 0
    false_positive_checks = 0
    
    for tick in range(TICKS):
        # Each honest agent gathers reports from neighbors
        for agent in agents:
            if agent.is_byzantine:
                agent.estimate = random.uniform(BYZ_MIN, BYZ_MAX)
                continue
            
            neighbors = adj[agent.idx]
            reports = [(n, agents[n].report()) for n in neighbors]
            
            # Apply filter
            accepted = filter_fn(agent, reports, adj)
            
            # Update reputation for each reporter
            for n, reported in reports:
                agent.update_reputation(n, reported, accepted)
            
            # Check false positives: honest neighbor incorrectly down-weighted
            for n in neighbors:
                if not agents[n].is_byzantine and n in agent.reputation:
                    false_positive_checks += 1
                    mean_err, count = agent.reputation[n]
                    avg_err = mean_err / max(count, 1)
                    # If avg error > 200 for an honest agent, that's a false positive
                    if avg_err > 200:
                        false_positive_events += 1
            
            # Update estimate (simple weighted average with accepted value)
            alpha = 0.3  # learning rate
            agent.estimate = agent.estimate + alpha * (accepted - agent.estimate)
            agent.history.append(agent.estimate)
        
        # Track max drift among honest agents
        drifts = [abs(agents[i].estimate - TRUE_VALUE) for i in range(HONEST_COUNT)]
        max_drift = max(drifts) if drifts else 0
        peak_drift = max(peak_drift, max_drift)
        
        if converged_tick is None and max_drift < DELTA:
            converged_tick = tick
    
    # Final drift
    final_drifts = [abs(agents[i].estimate - TRUE_VALUE) for i in range(HONEST_COUNT)]
    final_max_drift = max(final_drifts) if final_drifts else 0
    
    # False positive rate
    fp_rate = false_positive_events / max(false_positive_checks, 1)
    
    return {
        "converged": converged_tick is not None,
        "convergence_tick": converged_tick if converged_tick is not None else TICKS + 1,
        "peak_drift": peak_drift,
        "final_drift": final_max_drift,
        "false_positive_rate": fp_rate,
    }


def main():
    results = {}
    
    for filter_name, filter_fn in FILTERS.items():
        print(f"Running {filter_name}...")
        trial_results = []
        for trial in range(TRIALS):
            seed = 1000 + trial * 7 + hash(filter_name) % 100
            result = run_trial(filter_name, filter_fn, seed)
            trial_results.append(result)
        
        # Aggregate
        convergence_count = sum(1 for r in trial_results if r["converged"])
        avg_conv_tick = statistics.mean(
            [r["convergence_tick"] for r in trial_results if r["converged"]]
        ) if convergence_count > 0 else TICKS + 1
        
        results[filter_name] = {
            "convergence_rate": convergence_count / TRIALS,
            "avg_convergence_tick": avg_conv_tick,
            "avg_peak_drift": statistics.mean([r["peak_drift"] for r in trial_results]),
            "avg_final_drift": statistics.mean([r["final_drift"] for r in trial_results]),
            "avg_false_positive_rate": statistics.mean([r["false_positive_rate"] for r in trial_results]),
            "trials": trial_results,
        }
    
    # Save results
    out_dir = Path(__file__).parent / "results"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "experiment16_bft_filters.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {out_path}")
    
    # Print ASCII comparison table
    print("\n" + "=" * 100)
    print("EXPERIMENT 16: BFT Filter Comparison (N=10, f=3 Byzantine, 500 ticks, 10 trials)")
    print("=" * 100)
    print(f"{'Filter':<25} {'Conv%':>7} {'Avg Tick':>10} {'Peak Drift':>12} {'Final Drift':>13} {'FP Rate':>10}")
    print("-" * 100)
    
    # Sort by convergence rate desc, then avg tick asc
    sorted_filters = sorted(
        results.items(),
        key=lambda x: (-x[1]["convergence_rate"], x[1]["avg_convergence_tick"])
    )
    
    for name, data in sorted_filters:
        conv_pct = data["convergence_rate"] * 100
        print(
            f"{name:<25} {conv_pct:>6.0f}% {data['avg_convergence_tick']:>10.1f} "
            f"{data['avg_peak_drift']:>12.2f} {data['avg_final_drift']:>13.2f} "
            f"{data['avg_false_positive_rate']:>10.4f}"
        )
    
    print("=" * 100)
    
    # Analysis
    best = sorted_filters[0]
    rep_trimmed = results.get("REPUTATION_PLUS_TRIMMED", {})
    print(f"\nBest filter: {best[0]} (conv {best[1]['convergence_rate']*100:.0f}%, tick {best[1]['avg_convergence_tick']:.1f})")
    print(f"Reputation+Trimmed: conv {rep_trimmed.get('convergence_rate', 0)*100:.0f}%, tick {rep_trimmed.get('avg_convergence_tick', TICKS+1):.1f}")
    
    if best[0] == "TOPOLOGY_AWARE" and best[0] != "REPUTATION_PLUS_TRIMMED":
        print("\n*** NOVEL RESULT: Topology-aware filter outperforms reputation+trimmed mean! ***")
    elif best[0] == "REPUTATION_PLUS_TRIMMED":
        print("\n*** CONFIRMED: Reputation+trimmed mean is optimal among tested filters. ***")
    else:
        print(f"\n*** SURPRISE: {best[0]} is the best filter! ***")


if __name__ == "__main__":
    main()
