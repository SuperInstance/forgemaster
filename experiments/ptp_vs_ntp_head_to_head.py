#!/usr/bin/env python3
"""
Experiment 40: PTP vs NTP Head-to-Head — Direct Comparison
N=10 agents, Laman topology
4 protocols × 6 latencies × 4 loss rates × 3 drift configs = 288 conditions
"""

import json
import math
import random
import os
import sys
from dataclasses import dataclass, field
from typing import List, Tuple, Dict
from collections import defaultdict

# ── Laman Topology ──────────────────────────────────────────────────────────

def generate_laman_graph(n: int, seed: int = 42) -> List[Tuple[int, int]]:
    """Generate a Laman graph (2|V|-3 edges, generic rigidity) via Henneberg."""
    rng = random.Random(seed)
    if n < 2:
        return []
    edges = []
    placed = list(range(min(3, n)))
    if n >= 2:
        edges.append((0, 1))
    if n >= 3:
        edges.append((0, 2))
        edges.append((1, 2))
    for i in range(3, n):
        # Pick 2 existing vertices
        a, b = rng.sample(placed, 2)
        edges.append((a, i))
        edges.append((b, i))
        placed.append(i)
    return edges


# ── Agent Model ─────────────────────────────────────────────────────────────

@dataclass
class Agent:
    id: int
    clock: float  # current clock value
    drift_rate: float  # ticks per tick drift
    frequency_offset: float  # accumulated frequency correction
    offset_estimate: float  # accumulated offset correction


# ── Protocol Implementations ────────────────────────────────────────────────

def run_ntp_marzullo(agents, edges, latency, loss_rate, ticks, rng):
    """
    NTP-style: Marzullo algorithm. Symmetric delay assumption.
    Each round: pick neighbors, exchange timestamps, compute offset via
    (t2-t1 + t3-t4)/2, filter with Marzullo intersection.
    """
    n = len(agents)
    corrections = [[] for _ in range(n)]
    
    for t in range(ticks):
        # Drift clocks (natural drift + frequency correction)
        for a in agents:
            a.clock += 1.0 + a.drift_rate + a.frequency_offset
        
        # Synchronization rounds every 10 ticks
        if t % 10 != 0 or t == 0:
            continue
        
        # Exchange with neighbors
        for (i, j) in edges:
            if rng.random() < loss_rate:
                continue
            
            t1 = agents[i].clock
            delay = latency * (0.5 + rng.random())  # variable delay
            t2 = agents[j].clock + delay
            t3 = t2 + 0.1
            delay2 = latency * (0.5 + rng.random())
            t4 = agents[i].clock + delay2
            
            offset_ij = ((t2 - t1) + (t3 - t4)) / 2.0
            delay_est = abs((t2 - t1) - (t3 - t4)) / 2.0
            
            corrections[i].append((offset_ij, delay_est))
            corrections[j].append((-offset_ij, delay_est))
        
        # Apply Marzullo filtering
        for a in agents:
            if not corrections[a.id]:
                continue
            # Marzullo: use best intersection (pick median instead of quartile trim)
            corrs = sorted(corrections[a.id], key=lambda x: x[0])
            n_corrs = len(corrs)
            if n_corrs >= 3:
                mid = n_corrs // 2
                # Use middle third
                third = max(1, n_corrs // 3)
                filtered = corrs[third:-third]
                if not filtered:
                    filtered = [corrs[mid]]
            else:
                filtered = corrs
            if filtered:
                avg_offset = sum(c[0] for c in filtered) / len(filtered)
                # Apply correction with conservative damping
                a.clock -= avg_offset * 0.02
                a.frequency_offset -= avg_offset * 0.0002
                a.frequency_offset = max(-0.05, min(0.05, a.frequency_offset))
            corrections[a.id] = []


def run_cristian(agents, edges, latency, loss_rate, ticks, rng):
    """
    Cristian's algorithm: simple request-response.
    Client asks server for time, server responds. Client adjusts by (response - request)/2.
    Uses a designated root (agent 0) as time server.
    """
    n = len(agents)
    root = agents[0]
    
    for t in range(ticks):
        for a in agents:
            a.clock += 1.0 + a.drift_rate + a.frequency_offset
        
        if t % 10 != 0 or t == 0:
            continue
        
        # Each non-root agent queries root
        for a in agents[1:]:
            if rng.random() < loss_rate:
                continue
            
            # Request
            t0 = a.clock
            delay_req = latency * (0.5 + rng.random())
            t1 = root.clock + delay_req
            # Processing
            t2 = t1 + 0.05
            delay_resp = latency * (0.5 + rng.random())
            t3 = a.clock + delay_resp
            
            # Estimated one-way delay
            rtt = t3 - t0
            estimated_delay = rtt / 2.0
            
            # Offset = server_time + delay - client_time
            offset = (t1 + estimated_delay) - t3
            
            a.clock += offset * 0.3
            a.frequency_offset += offset * 0.002
            a.frequency_offset = max(-0.05, min(0.05, a.frequency_offset))


def run_ptp_4timestamp(agents, edges, latency, loss_rate, ticks, rng):
    """
    PTP (IEEE 1588 style): 4-timestamp offset estimation.
    Sync, Follow_Up, Delay_Req, Delay_Resp.
    Computes both offset and mean path delay.
    """
    n = len(agents)
    
    # Pick a grandmaster (agent 0)
    corrections = [[] for _ in range(n)]
    
    for t in range(ticks):
        for a in agents:
            a.clock += 1.0 + a.drift_rate + a.frequency_offset
        
        if t % 10 != 0 or t == 0:
            continue
        
        # For each edge, do 4-timestamp exchange
        for (i, j) in edges:
            if rng.random() < loss_rate:
                continue
            
            # t1: master sends sync
            t1 = agents[i].clock
            # t2: slave receives
            delay1 = latency * (0.5 + rng.random())
            t2 = agents[j].clock + delay1
            # t3: slave sends delay_req
            t3 = t2 + 0.05
            # t4: master receives delay_req
            delay2 = latency * (0.5 + rng.random())
            t4 = agents[i].clock + delay2
            
            # PTP offset = ((t2-t1) - (t4-t3)) / 2
            offset = ((t2 - t1) - (t4 - t3)) / 2.0
            # Mean path delay = ((t2-t1) + (t4-t3)) / 2
            mean_delay = ((t2 - t1) + (t4 - t3)) / 2.0
            
            # Apply correction to slave (j)
            corrections[j].append((offset, mean_delay))
        
        # Apply corrections
        for a in agents:
            if not corrections[a.id]:
                continue
            avg_offset = sum(c[0] for c in corrections[a.id]) / len(corrections[a.id])
            avg_delay = sum(c[1] for c in corrections[a.id]) / len(corrections[a.id])
            
            # PTP: correct offset, and use delay for frequency adj
            a.clock -= avg_offset * 0.5
            a.frequency_offset -= avg_offset * 0.002
            a.frequency_offset = max(-0.05, min(0.05, a.frequency_offset))
            corrections[a.id] = []


def run_ewma(agents, edges, latency, loss_rate, ticks, rng):
    """
    Exponential Weighted Moving Average.
    Each agent tracks an EWMA of neighbor clock differences and drifts toward it.
    """
    n = len(agents)
    alpha = 0.3  # smoothing factor
    ewma_offset = [0.0] * n
    ewma_drift = [0.0] * n
    
    for t in range(ticks):
        for a in agents:
            a.clock += 1.0 + a.drift_rate + a.frequency_offset
        
        if t % 10 != 0 or t == 0:
            continue
        
        for (i, j) in edges:
            if rng.random() < loss_rate:
                continue
            
            delay = latency * (0.5 + rng.random())
            # Agent i observes j's clock
            observed_j = agents[j].clock + delay
            diff_i = observed_j - agents[i].clock
            
            observed_i = agents[i].clock + delay
            diff_j = observed_i - agents[j].clock
            
            # Update EWMA
            ewma_offset[i] = alpha * diff_i + (1 - alpha) * ewma_offset[i]
            ewma_drift[i] = alpha * (diff_i - ewma_offset[i]) + (1 - alpha) * ewma_drift[i]
            
            ewma_offset[j] = alpha * diff_j + (1 - alpha) * ewma_offset[j]
            ewma_drift[j] = alpha * (diff_j - ewma_offset[j]) + (1 - alpha) * ewma_drift[j]
        
        # Apply corrections
        for a in agents:
            a.clock += ewma_offset[a.id] * 0.2
            a.frequency_offset += ewma_drift[a.id] * 0.002
            a.frequency_offset = max(-0.05, min(0.05, a.frequency_offset))


# ── Experiment Runner ───────────────────────────────────────────────────────

PROTOCOLS = {
    "ntp_marzullo": run_ntp_marzullo,
    "cristian": run_cristian,
    "ptp_4timestamp": run_ptp_4timestamp,
    "ewma": run_ewma,
}

LATENCIES = [1, 5, 10, 20, 50, 100]
LOSS_RATES = [0.0, 0.1, 0.3, 0.5]
DRIFT_CONFIGS = [
    {"name": "low", "sigma_range": (0.001, 0.01), "rates": [0.001, 0.003, 0.005, 0.007, 0.009, 0.002, 0.004, 0.006, 0.008, 0.01]},
    {"name": "medium", "sigma_range": (0.01, 0.1), "rates": [0.01, 0.03, 0.05, 0.07, 0.09, 0.02, 0.04, 0.06, 0.08, 0.1]},
    {"name": "high", "sigma_range": (0.1, 1.0), "rates": [0.1, 0.3, 0.5, 0.7, 0.9, 0.2, 0.4, 0.6, 0.8, 1.0]},
]

N_AGENTS = 10
N_TICKS = 1000
WARMUP_TICKS = 200


def compute_steady_state_drift(agents):
    """Compute RMS drift from mean clock."""
    clocks = [a.clock for a in agents]
    mean_clock = sum(clocks) / len(clocks)
    rms = math.sqrt(sum((c - mean_clock) ** 2 for c in clocks) / len(clocks))
    return rms


def run_single_condition(protocol_name, protocol_fn, latency, loss_rate, drift_config, seed=42):
    rng = random.Random(seed)
    edges = generate_laman_graph(N_AGENTS, seed=seed)
    
    agents = []
    for i in range(N_AGENTS):
        agents.append(Agent(
            id=i,
            clock=0.0,
            drift_rate=drift_config["rates"][i],
            frequency_offset=0.0,
            offset_estimate=0.0,
        ))
    
    # Track drift over time for convergence
    drift_history = []
    for tick_batch in range(0, N_TICKS, 100):
        protocol_fn(agents, edges, latency, loss_rate, min(100, N_TICKS - tick_batch), rng)
        drift_history.append(compute_steady_state_drift(agents))
    
    # Steady-state: average of last 3 windows
    steady_drift = sum(drift_history[-3:]) / 3 if len(drift_history) >= 3 else drift_history[-1]
    
    # Convergence time: first window where drift < 2x final drift
    convergence_time = N_TICKS
    if drift_history:
        threshold = max(drift_history[-1] * 2, 0.01)
        for idx, d in enumerate(drift_history):
            if d <= threshold:
                convergence_time = (idx + 1) * 100
                break
    
    # Anti-fragility: how drift changes with latency
    # Computed externally by comparing across latencies
    
    return {
        "steady_state_drift": round(steady_drift, 6),
        "convergence_time": convergence_time,
        "drift_history": [round(d, 6) for d in drift_history],
    }


def main():
    results = []
    
    total = len(PROTOCOLS) * len(LATENCIES) * len(LOSS_RATES) * len(DRIFT_CONFIGS)
    count = 0
    
    for proto_name, proto_fn in PROTOCOLS.items():
        for latency in LATENCIES:
            for loss_rate in LOSS_RATES:
                for drift_cfg in DRIFT_CONFIGS:
                    count += 1
                    seed = hash((proto_name, latency, loss_rate, drift_cfg["name"])) % (2**31)
                    r = run_single_condition(proto_name, proto_fn, latency, loss_rate, drift_cfg, seed)
                    results.append({
                        "protocol": proto_name,
                        "latency": latency,
                        "loss_rate": loss_rate,
                        "drift_config": drift_cfg["name"],
                        "sigma_range": drift_cfg["sigma_range"],
                        "steady_state_drift": r["steady_state_drift"],
                        "convergence_time": r["convergence_time"],
                        "drift_history": r["drift_history"],
                    })
                    if count % 50 == 0 or count == total:
                        print(f"  [{count}/{total}] {proto_name} lat={latency} loss={loss_rate} drift={drift_cfg['name']} → drift={r['steady_state_drift']:.4f}")
    
    # ── Compute Anti-Fragility Scores ───────────────────────────────────────
    # Anti-fragility: for each protocol/drift/loss, does drift *decrease* as latency increases?
    # Score = correlation(latency, drift) — negative = anti-fragile
    
    anti_frag = {}
    for proto_name in PROTOCOLS:
        for drift_name in [dc["name"] for dc in DRIFT_CONFIGS]:
            for loss_rate in LOSS_RATES:
                key = (proto_name, drift_name, loss_rate)
                pairs = [(r["latency"], r["steady_state_drift"]) 
                         for r in results 
                         if r["protocol"] == proto_name and r["drift_config"] == drift_name and r["loss_rate"] == loss_rate]
                if len(pairs) < 2:
                    continue
                lats = [p[0] for p in pairs]
                drifts = [p[1] for p in pairs]
                mean_l = sum(lats) / len(lats)
                mean_d = sum(drifts) / len(drifts)
                cov = sum((l - mean_l) * (d - mean_d) for l, d in zip(lats, drifts))
                var_l = sum((l - mean_l) ** 2 for l in lats)
                var_d = sum((d - mean_d) ** 2 for d in drifts)
                if var_l > 0 and var_d > 0:
                    corr = cov / (math.sqrt(var_l) * math.sqrt(var_d))
                else:
                    corr = 0.0
                anti_frag[key] = round(corr, 4)
    
    # Add anti-fragility to results
    for r in results:
        key = (r["protocol"], r["drift_config"], r["loss_rate"])
        r["anti_fragility_corr"] = anti_frag.get(key, 0.0)
    
    # ── Save Results ────────────────────────────────────────────────────────
    out_dir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "experiment40_head_to_head.json")
    with open(out_path, "w") as f:
        json.dump({"experiment": 40, "total_conditions": total, "results": results}, f, indent=2)
    print(f"\nSaved {len(results)} results to {out_path}")
    
    # ── Print Comparison Table ──────────────────────────────────────────────
    print("\n" + "=" * 110)
    print("EXPERIMENT 40: PTP vs NTP Head-to-Head Comparison")
    print("=" * 110)
    
    # Table 1: Average steady-state drift per protocol
    print("\n┌─ Table 1: Mean Steady-State Drift by Protocol ─────────────────────────────────────────────────┐")
    print(f"│ {'Protocol':<18} │ {'Low Drift':>10} │ {'Med Drift':>10} │ {'High Drift':>10} │ {'Overall':>10} │ {'Converge(t)':>12} │")
    print("├────────────────────┼────────────┼────────────┼────────────┼────────────┼──────────────┤")
    
    for proto_name in PROTOCOLS:
        proto_results = [r for r in results if r["protocol"] == proto_name]
        overall_drift = sum(r["steady_state_drift"] for r in proto_results) / len(proto_results)
        overall_conv = sum(r["convergence_time"] for r in proto_results) / len(proto_results)
        
        drift_by_config = {}
        for dc in DRIFT_CONFIGS:
            dn = dc["name"]
            subset = [r for r in proto_results if r["drift_config"] == dn]
            drift_by_config[dn] = sum(r["steady_state_drift"] for r in subset) / len(subset)
        
        print(f"│ {proto_name:<18} │ {drift_by_config.get('low', 0):>10.4f} │ {drift_by_config.get('medium', 0):>10.4f} │ {drift_by_config.get('high', 0):>10.4f} │ {overall_drift:>10.4f} │ {overall_conv:>10.0f} t │")
    print("└────────────────────┴────────────┴────────────┴────────────┴────────────┴──────────────┘")
    
    # Table 2: Impact of packet loss
    print("\n┌─ Table 2: Mean Drift by Packet Loss Rate ─────────────────────────────────────────────────────┐")
    print(f"│ {'Protocol':<18} │ {'0% loss':>10} │ {'10% loss':>10} │ {'30% loss':>10} │ {'50% loss':>10} │")
    print("├────────────────────┼────────────┼────────────┼────────────┼────────────┤")
    
    for proto_name in PROTOCOLS:
        proto_results = [r for r in results if r["protocol"] == proto_name]
        losses = {}
        for lr in LOSS_RATES:
            subset = [r for r in proto_results if r["loss_rate"] == lr]
            losses[lr] = sum(r["steady_state_drift"] for r in subset) / len(subset)
        print(f"│ {proto_name:<18} │ {losses[0.0]:>10.4f} │ {losses[0.1]:>10.4f} │ {losses[0.3]:>10.4f} │ {losses[0.5]:>10.4f} │")
    print("└────────────────────┴────────────┴────────────┴────────────┴────────────┘")
    
    # Table 3: Anti-fragility scores (lower = more anti-fragile)
    print("\n┌─ Table 3: Anti-Fragility Score (correlation of latency→drift; negative=anti-fragile) ───────┐")
    print(f"│ {'Protocol':<18} │ {'Low Drift':>10} │ {'Med Drift':>10} │ {'High Drift':>10} │ {'Mean':>10} │")
    print("├────────────────────┼────────────┼────────────┼────────────┼────────────┤")
    
    for proto_name in PROTOCOLS:
        scores = {}
        for dc in DRIFT_CONFIGS:
            dn = dc["name"]
            vals = [anti_frag[(proto_name, dn, lr)] for lr in LOSS_RATES if (proto_name, dn, lr) in anti_frag]
            scores[dn] = sum(vals) / len(vals) if vals else 0.0
        mean_score = sum(scores.values()) / len(scores) if scores else 0.0
        print(f"│ {proto_name:<18} │ {scores.get('low', 0):>10.4f} │ {scores.get('medium', 0):>10.4f} │ {scores.get('high', 0):>10.4f} │ {mean_score:>10.4f} │")
    print("└────────────────────┴────────────┴────────────┴────────────┴────────────┘")
    
    # Table 4: Latency breakdown
    print("\n┌─ Table 4: Mean Drift by Latency ──────────────────────────────────────────────────────────────┐")
    header = "│ {:<18}".format("Protocol")
    for lat in LATENCIES:
        header += " │ {:>8}".format(f"L={lat}")
    header += " │"
    print(header)
    sep = "├────────────────────" + "┼──────────" * len(LATENCIES) + "┤"
    print(sep)
    
    for proto_name in PROTOCOLS:
        proto_results = [r for r in results if r["protocol"] == proto_name]
        row = f"│ {proto_name:<18}"
        for lat in LATENCIES:
            subset = [r for r in proto_results if r["latency"] == lat]
            avg = sum(r["steady_state_drift"] for r in subset) / len(subset)
            row += f" │ {avg:>8.3f}"
        row += " │"
        print(row)
    print("└────────────────────" + "┴──────────" * len(LATENCIES) + "┘")
    
    # Winner summary
    print("\n┌─ Summary ─────────────────────────────────────────────────────────────────────────────────────┐")
    proto_avgs = {}
    for proto_name in PROTOCOLS:
        proto_results = [r for r in results if r["protocol"] == proto_name]
        proto_avgs[proto_name] = sum(r["steady_state_drift"] for r in proto_results) / len(proto_results)
    
    ranked = sorted(proto_avgs.items(), key=lambda x: x[1])
    for rank, (name, drift) in enumerate(ranked, 1):
        medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"#{rank}"
        print(f"│  {medal}  {name:<16} — mean drift: {drift:.4f}")
    
    best = ranked[0][0]
    worst = ranked[-1][0]
    ratio = ranked[-1][1] / ranked[0][1] if ranked[0][1] > 0 else float('inf')
    print(f"│")
    print(f"│  Best: {best} ({ranked[0][1]:.4f}) | Worst: {worst} ({ranked[-1][1]:.4f}) | Ratio: {ratio:.1f}x")
    print("└────────────────────────────────────────────────────────────────────────────────────────────────┘")


if __name__ == "__main__":
    main()
