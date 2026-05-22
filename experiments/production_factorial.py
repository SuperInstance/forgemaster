#!/usr/bin/env python3
"""Experiment 44: Production Factorial Analysis — Which stressor combination breaks PTP?

Exp 43 showed combined stress = unbounded drift. Now isolate the culprit.

Test each stressor individually and in pairs:
 1. Baseline: N=20, PTP, gain=0.4, no stressors
 2. Heterogeneous drift only (σ ∈ {0.001..0.5})
 3. Packet loss only (10%)
 4. Random latency only (1-20 ticks)
 5. Churn only (1 join + 1 leave per 200 ticks, W=50 boot-to-mean)
 6. Frequency step only (one agent σ→2.0 at tick 1000)
 7. Heterogeneous + loss
 8. Heterogeneous + latency
 9. Loss + churn
10. Latency + churn
11. ALL stressors (same as Exp 43)

Each: 5 trials, 5000 ticks
Measure: max drift, convergence rate, steady-state drift
Save to experiments/results/experiment44_factorial.json
"""

import json
import math
import os
import random
import time
from collections import deque
from typing import List, Tuple, Optional, Dict

SEED = 44


def build_random_connected_graph(n: int, rng: random.Random) -> List[Tuple[int, int]]:
    if n < 2:
        return []
    edges = []
    for i in range(1, n):
        j = rng.randint(0, i - 1)
        edges.append((i, j))
    extra = max(1, n // 2)
    nodes = list(range(n))
    for _ in range(extra):
        i, j = rng.sample(nodes, 2)
        if (i, j) not in edges and (j, i) not in edges:
            edges.append((i, j))
    return edges


class PTP4Agent:
    def __init__(self, idx: int, sigma: float, alpha: float = 0.4,
                 warmup: int = 50, global_mean_clock: float = 0.0,
                 boot_to_mean: bool = False):
        self.idx = idx
        self.sigma = sigma
        self.alpha = alpha
        self.local_clock = global_mean_clock if boot_to_mean else 0.0
        self.drift_rate = random.gauss(0, sigma)
        self.neighbors: List[Tuple['PTP4Agent', float]] = []
        self.deadband = 0.0
        self.warmup = warmup
        self.joined_tick = 0
        self.ptp_state: Dict[int, dict] = {}
        self.asymmetry: Dict[int, dict] = {}
        self.inbox: deque = deque()
        self.active = True
        self.join_tick = 0

    def tick(self, tick_num: int):
        if not self.active:
            return
        self.local_clock += 1.0 + self.drift_rate

    def broadcast_ptp_sync(self, current_tick: int, latency_fn):
        if not self.active:
            return
        t1 = self.local_clock
        for neighbor, weight in self.neighbors:
            if not neighbor.active:
                continue
            latency = latency_fn(current_tick, self.idx, neighbor.idx)
            neighbor.inbox.append((
                current_tick + latency, self.idx, 'sync',
                {'t1': t1, 'sent_tick': current_tick, 'weight': weight}
            ))

    def handle_sync(self, current_tick: int):
        messages = []
        remaining = deque()
        for msg in self.inbox:
            if msg[0] <= current_tick:
                messages.append(msg)
            else:
                remaining.append(msg)
        self.inbox = remaining

        for deliver_at, sender_idx, msg_type, data in messages:
            if msg_type == 'sync':
                t2 = self.local_clock
                if sender_idx not in self.ptp_state:
                    self.ptp_state[sender_idx] = {}
                self.ptp_state[sender_idx].update({
                    't1': data['t1'], 't2': t2,
                    'sync_sent_tick': data['sent_tick'],
                    'weight': data['weight'],
                    'latency': current_tick - data['sent_tick']
                })
            elif msg_type == 'delay_resp':
                t4 = self.local_clock
                if sender_idx in self.ptp_state and 't3' in self.ptp_state[sender_idx]:
                    s = self.ptp_state[sender_idx]
                    self._apply_4timestamp_correction(
                        sender_idx, s['t1'], s['t2'], s['t3'], t4,
                        s.get('weight', 1.0), s.get('latency', 0)
                    )

    def send_delay_req(self, current_tick: int, latency_fn):
        if not self.active:
            return
        t3 = self.local_clock
        for neighbor, weight in self.neighbors:
            if not neighbor.active:
                continue
            if neighbor.idx in self.ptp_state and 't2' in self.ptp_state[neighbor.idx]:
                latency = latency_fn(current_tick, self.idx, neighbor.idx)
                neighbor.inbox.append((
                    current_tick + latency, self.idx, 'delay_req',
                    {'t3': t3, 'sent_tick': current_tick}
                ))
                self.ptp_state[neighbor.idx]['t3'] = t3
                self.ptp_state[neighbor.idx]['delay_sent_tick'] = current_tick
                self.ptp_state[neighbor.idx]['delay_latency'] = latency

    def handle_delay_req(self, current_tick: int, latency_fn):
        messages = []
        remaining = deque()
        for msg in self.inbox:
            if msg[0] <= current_tick:
                messages.append(msg)
            else:
                remaining.append(msg)
        self.inbox = remaining

        for deliver_at, sender_idx, msg_type, data in messages:
            if msg_type == 'delay_req':
                t4 = self.local_clock
                latency = latency_fn(current_tick, self.idx, sender_idx)
                for neighbor, _ in self.neighbors:
                    if neighbor.idx == sender_idx and neighbor.active:
                        neighbor.inbox.append((
                            current_tick + latency, self.idx, 'delay_resp',
                            {'t4': t4, 'sent_tick': current_tick}
                        ))
                        break

    def _apply_4timestamp_correction(self, neighbor_idx, t1, t2, t3, t4,
                                      weight: float, measured_latency: int):
        forward_delay = t2 - t1
        reverse_delay = t4 - t3
        offset = (forward_delay - reverse_delay) / 2.0
        prop_delay = (forward_delay + reverse_delay) / 2.0

        # Asymmetry correction
        if neighbor_idx not in self.asymmetry:
            self.asymmetry[neighbor_idx] = {
                'forward_samples': [], 'reverse_samples': [], 'gamma': 1.0
            }
        asym = self.asymmetry[neighbor_idx]
        asym['forward_samples'].append(forward_delay)
        asym['reverse_samples'].append(reverse_delay)
        if len(asym['forward_samples']) > 20:
            asym['forward_samples'] = asym['forward_samples'][-20:]
            asym['reverse_samples'] = asym['reverse_samples'][-20:]
        if len(asym['forward_samples']) >= 5:
            fwd_mean = sum(asym['forward_samples']) / len(asym['forward_samples'])
            rev_mean = sum(asym['reverse_samples']) / len(asym['reverse_samples'])
            if abs(rev_mean) > 1e-10:
                asym['gamma'] = fwd_mean / rev_mean

        gamma = asym['gamma']
        if abs(1.0 + gamma) > 1e-10:
            corrected_offset = offset * 2.0 / (1.0 + gamma)
        else:
            corrected_offset = offset

        correction = self.alpha * corrected_offset * weight
        self.local_clock += correction


def make_latency_fn(rng: random.Random, loss_rate: float = 0.0, random_latency: bool = True):
    """Latency function with optional loss and random delay."""
    def fn(tick, sender, receiver):
        if loss_rate > 0 and rng.random() < loss_rate:
            return 999999
        if random_latency:
            return rng.randint(1, 20)
        return 1  # fixed 1-tick latency
    return fn


# Stressor configuration flags
class StressorConfig:
    def __init__(self, name: str, heterogeneous: bool = False,
                 packet_loss: float = 0.0, random_latency: bool = False,
                 churn: bool = False, freq_step: bool = False):
        self.name = name
        self.heterogeneous = heterogeneous
        self.packet_loss = packet_loss
        self.random_latency = random_latency
        self.churn = churn
        self.freq_step = freq_step


STRESSOR_CONFIGS = [
    StressorConfig("1_baseline"),
    StressorConfig("2_heterogeneous", heterogeneous=True),
    StressorConfig("3_packet_loss", packet_loss=0.10),
    StressorConfig("4_random_latency", random_latency=True),
    StressorConfig("5_churn", churn=True),
    StressorConfig("6_freq_step", freq_step=True),
    StressorConfig("7_heterogeneous_plus_loss", heterogeneous=True, packet_loss=0.10),
    StressorConfig("8_heterogeneous_plus_latency", heterogeneous=True, random_latency=True),
    StressorConfig("9_loss_plus_churn", packet_loss=0.10, churn=True),
    StressorConfig("10_latency_plus_churn", random_latency=True, churn=True),
    StressorConfig("11_ALL", heterogeneous=True, packet_loss=0.10,
                    random_latency=True, churn=True, freq_step=True),
]


def run_factorial_trial(trial_seed: int, config: StressorConfig, max_ticks: int = 5000):
    """Run a single trial with specific stressor configuration."""
    rng = random.Random(trial_seed)
    start_time = time.time()

    N_initial = 20
    agents: List[PTP4Agent] = []

    for i in range(N_initial):
        if config.heterogeneous:
            log_sigma = rng.uniform(math.log10(0.001), math.log10(0.5))
            sigma = 10 ** log_sigma
        else:
            sigma = 0.0  # homogeneous — no drift variance

        agents.append(PTP4Agent(i, sigma, alpha=0.4, warmup=50, boot_to_mean=False))

    # Build random connected graph
    edges = build_random_connected_graph(N_initial, rng)

    adj = {}
    for u, v in edges:
        adj.setdefault(u, set()).add(v)
        adj.setdefault(v, set()).add(u)

    for u, v in edges:
        max_sigma = max(agents[u].sigma, agents[v].sigma)
        w = 1.0 / (1.0 + max_sigma)
        agents[u].neighbors.append((agents[v], w))
        agents[v].neighbors.append((agents[u], w))

    latency_fn = make_latency_fn(rng,
                                  loss_rate=config.packet_loss,
                                  random_latency=config.random_latency)

    # Churn schedule
    churn_events = []
    next_agent_id = N_initial
    if config.churn:
        for tick in range(200, max_ticks, 200):
            join_id = next_agent_id
            next_agent_id += 1
            if config.heterogeneous:
                log_sigma = rng.uniform(math.log10(0.001), math.log10(0.5))
                sigma = 10 ** log_sigma
            else:
                sigma = 0.0
            active_clocks = [a.local_clock for a in agents if a.active]
            mean_clock = sum(active_clocks) / len(active_clocks) if active_clocks else 0.0
            new_agent = PTP4Agent(join_id, sigma, alpha=0.4, warmup=50,
                                  global_mean_clock=mean_clock, boot_to_mean=True)
            new_agent.join_tick = tick
            new_agent.joined_tick = tick

            active_ids = [a.idx for a in agents if a.active]
            if len(active_ids) >= 2:
                targets = rng.sample(active_ids, min(3, len(active_ids)))
                for t in targets:
                    target_agent = next(a for a in agents if a.idx == t)
                    max_sigma = max(new_agent.sigma, target_agent.sigma)
                    w = 1.0 / (1.0 + max_sigma)
                    new_agent.neighbors.append((target_agent, w))
                    target_agent.neighbors.append((new_agent, w))

            agents.append(new_agent)

            leaving_agent = None
            active_for_leave = [a for a in agents if a.active and a.idx != join_id]
            if len(active_for_leave) > 5:
                leaving = rng.choice(active_for_leave)
                leaving.active = False
                for a in agents:
                    a.neighbors = [(n, w) for n, w in a.neighbors if n.idx != leaving.idx]
                leaving_agent = leaving

            churn_events.append({
                'tick': tick,
                'joined': join_id,
                'left': leaving_agent.idx if leaving_agent else None
            })

    # Frequency step
    freq_step_agent = rng.randint(0, N_initial - 1)
    freq_step_applied = False

    # Metrics
    max_drift_log = []
    drift_samples = []  # every 50 ticks
    convergence_tick = None

    for tick in range(1, max_ticks + 1):
        # Frequency step at tick 1000
        if config.freq_step and tick == 1000 and not freq_step_applied:
            target = agents[freq_step_agent]
            if target.active:
                target.drift_rate = rng.gauss(2.0, 0.1)
                freq_step_applied = True

        # Tick all active agents
        for a in agents:
            if a.active:
                a.tick(tick)

        # PTP exchanges
        for a in agents:
            if a.active and (tick - getattr(a, 'joined_tick', 0)) > a.warmup:
                a.broadcast_ptp_sync(tick, latency_fn)

        for a in agents:
            if a.active and (tick - getattr(a, 'joined_tick', 0)) > a.warmup:
                a.handle_sync(tick)
                a.send_delay_req(tick, latency_fn)

        for a in agents:
            if a.active:
                a.handle_delay_req(tick, latency_fn)

        for a in agents:
            if a.active and (tick - getattr(a, 'joined_tick', 0)) > a.warmup:
                a.handle_sync(tick)

        # Measure drift
        active_agents = [a for a in agents if a.active]
        if len(active_agents) < 2:
            continue

        ideal_clock = float(tick)
        drifts = [abs(a.local_clock - ideal_clock) for a in active_agents]
        max_drift = max(drifts)
        mean_drift = sum(drifts) / len(drifts)
        max_drift_log.append(max_drift)

        pairwise_drifts = []
        for i in range(len(active_agents)):
            for j in range(i + 1, len(active_agents)):
                pairwise_drifts.append(abs(active_agents[i].local_clock - active_agents[j].local_clock))
        max_pairwise = max(pairwise_drifts) if pairwise_drifts else 0

        if tick % 50 == 0:
            drift_samples.append({
                'tick': tick,
                'max_drift': round(max_drift, 4),
                'mean_drift': round(mean_drift, 4),
                'max_pairwise': round(max_pairwise, 4),
                'active_agents': len(active_agents)
            })

        # Convergence check
        if tick > 100 and max_drift < 1.0 and len(max_drift_log) >= 50:
            recent = max_drift_log[-50:]
            if all(d < 1.0 for d in recent) and convergence_tick is None:
                convergence_tick = tick - 49

    elapsed = time.time() - start_time

    # Steady state: last 500 ticks
    ss_window = max_drift_log[-500:] if len(max_drift_log) >= 500 else max_drift_log
    ss_max = max(ss_window)
    ss_mean = sum(ss_window) / len(ss_window)
    ss_p95 = sorted(ss_window)[int(0.95 * len(ss_window))]

    # Convergence rate: fraction of time drift < 1.0 after tick 500
    post500 = max_drift_log[500:] if len(max_drift_log) > 500 else []
    convergence_rate = sum(1 for d in post500 if d < 1.0) / len(post500) if post500 else 0.0

    # Drift growth rate (linear fit of last 1000 ticks)
    tail = max_drift_log[-1000:] if len(max_drift_log) >= 1000 else max_drift_log
    n_tail = len(tail)
    if n_tail >= 10:
        x_mean = (n_tail - 1) / 2.0
        y_mean = sum(tail) / n_tail
        num = sum((i - x_mean) * (tail[i] - y_mean) for i in range(n_tail))
        den = sum((i - x_mean) ** 2 for i in range(n_tail))
        drift_growth_rate = num / den if abs(den) > 1e-10 else 0.0
    else:
        drift_growth_rate = 0.0

    bounded = all(d < 1.0 for d in ss_window)

    return {
        'trial_seed': trial_seed,
        'convergence_tick': convergence_tick,
        'convergence_rate': round(convergence_rate, 4),
        'steady_state_max_drift': round(ss_max, 4),
        'steady_state_mean_drift': round(ss_mean, 4),
        'steady_state_p95_drift': round(ss_p95, 4),
        'peak_drift': round(max(max_drift_log), 4),
        'drift_growth_rate': round(drift_growth_rate, 6),
        'bounded_in_steady_state': bounded,
        'drift_samples': drift_samples,
        'elapsed_seconds': round(elapsed, 1),
        'final_active_agents': sum(1 for a in agents if a.active),
    }


def main():
    start_time = time.time()
    print("=" * 70)
    print("EXPERIMENT 44: Production Factorial Analysis")
    print("=" * 70)
    print()
    print("Isolating which stressor combination breaks PTP.")
    print(f"Stressor configs: {len(STRESSOR_CONFIGS)}")
    print(f"Trials per config: 5")
    print(f"Ticks per trial: 5000")
    print()

    N_TRIALS = 5
    MAX_TICKS = 5000
    results = {}

    for cfg in STRESSOR_CONFIGS:
        print(f"\n--- {cfg.name} ---")
        cfg_trials = []
        for t in range(N_TRIALS):
            trial_seed = SEED * 10000 + hash(cfg.name) % 10000 + t * 137
            print(f"  Trial {t+1}/{N_TRIALS}...", end=" ", flush=True)
            result = run_factorial_trial(trial_seed, cfg, MAX_TICKS)
            cfg_trials.append(result)
            tag = "✓" if result['bounded_in_steady_state'] else "✗"
            print(f"ss_max={result['steady_state_max_drift']:.4f} "
                  f"peak={result['peak_drift']:.4f} "
                  f"conv_rate={result['convergence_rate']:.2%} "
                  f"growth={result['drift_growth_rate']:.6f} [{tag}]")

        # Aggregate per-config
        all_bounded = all(tr['bounded_in_steady_state'] for tr in cfg_trials)
        avg_ss_max = sum(tr['steady_state_max_drift'] for tr in cfg_trials) / N_TRIALS
        avg_ss_mean = sum(tr['steady_state_mean_drift'] for tr in cfg_trials) / N_TRIALS
        avg_peak = sum(tr['peak_drift'] for tr in cfg_trials) / N_TRIALS
        worst_ss = max(tr['steady_state_max_drift'] for tr in cfg_trials)
        worst_peak = max(tr['peak_drift'] for tr in cfg_trials)
        avg_conv_rate = sum(tr['convergence_rate'] for tr in cfg_trials) / N_TRIALS
        avg_growth = sum(tr['drift_growth_rate'] for tr in cfg_trials) / N_TRIALS
        n_bounded = sum(1 for tr in cfg_trials if tr['bounded_in_steady_state'])

        conv_ticks = [tr['convergence_tick'] for tr in cfg_trials if tr['convergence_tick'] is not None]
        avg_conv_tick = sum(conv_ticks) / len(conv_ticks) if conv_ticks else None

        results[cfg.name] = {
            'config': {
                'heterogeneous': cfg.heterogeneous,
                'packet_loss': cfg.packet_loss,
                'random_latency': cfg.random_latency,
                'churn': cfg.churn,
                'freq_step': cfg.freq_step,
            },
            'trials': cfg_trials,
            'aggregate': {
                'all_bounded': all_bounded,
                'n_bounded': n_bounded,
                'n_trials': N_TRIALS,
                'avg_ss_max_drift': round(avg_ss_max, 4),
                'avg_ss_mean_drift': round(avg_ss_mean, 4),
                'avg_peak_drift': round(avg_peak, 4),
                'worst_ss_max_drift': round(worst_ss, 4),
                'worst_peak_drift': round(worst_peak, 4),
                'avg_convergence_rate': round(avg_conv_rate, 4),
                'avg_drift_growth_rate': round(avg_growth, 6),
                'avg_convergence_tick': round(avg_conv_tick, 1) if avg_conv_tick else None,
            }
        }

        status = "✓ BOUNDED" if all_bounded else "✗ UNBOUNDED"
        print(f"  → {status} | avg_ss_max={avg_ss_max:.4f} | "
              f"conv_rate={avg_conv_rate:.2%} | growth={avg_growth:.6f}")

    # === ANALYSIS ===
    print("\n" + "=" * 70)
    print("FACTORIAL ANALYSIS SUMMARY")
    print("=" * 70)

    # Rank by severity
    ranked = sorted(results.items(), key=lambda x: x[1]['aggregate']['worst_ss_max_drift'], reverse=True)
    print(f"\n{'Config':<35} {'Worst SS':>10} {'Avg SS':>10} {'Conv Rate':>10} {'Growth':>12} {'Bounded':>8}")
    print("-" * 90)
    for name, data in ranked:
        agg = data['aggregate']
        print(f"{name:<35} {agg['worst_ss_max_drift']:>10.4f} {agg['avg_ss_max_drift']:>10.4f} "
              f"{agg['avg_convergence_rate']:>9.2%} {agg['avg_drift_growth_rate']:>12.6f} "
              f"{'✓' if agg['all_bounded'] else '✗':>8}")

    # Identify the killer combinations
    killers = [name for name, data in results.items() if not data['aggregate']['all_bounded']]
    survivors = [name for name, data in results.items() if data['aggregate']['all_bounded']]

    # Find individual stressors that cause unbounded drift
    individual_killers = [name for name in killers if name.count('_') <= 2 and name != '1_baseline']
    combo_killers = [name for name in killers if name not in individual_killers and name != '1_baseline']

    print(f"\n{'=' * 70}")
    print("VERDICT")
    print(f"{'=' * 70}")

    if not killers:
        print("All configurations bounded — no single stressor breaks PTP alone.")
    else:
        print(f"UNBOUNDED configurations ({len(killers)}/{len(STRESSOR_CONFIGS)}):")
        for k in killers:
            agg = results[k]['aggregate']
            print(f"  - {k}: worst_ss={agg['worst_ss_max_drift']:.4f}, growth={agg['avg_drift_growth_rate']:.6f}")

    if survivors:
        print(f"\nBOUNDED configurations ({len(survivors)}/{len(STRESSOR_CONFIGS)}):")
        for s in survivors:
            agg = results[s]['aggregate']
            print(f"  - {s}: worst_ss={agg['worst_ss_max_drift']:.4f}")

    # Key insight
    print(f"\n{'=' * 70}")
    print("KEY INSIGHT")
    print(f"{'=' * 70}")

    # Check if heterogeneous drift is the common factor
    het_configs = [name for name, data in results.items() if data['config']['heterogeneous'] and name != '1_baseline']
    het_bounded = [name for name in het_configs if results[name]['aggregate']['all_bounded']]
    het_unbounded = [name for name in het_configs if not results[name]['aggregate']['all_bounded']]

    loss_configs = [name for name, data in results.items() if data['config']['packet_loss'] > 0]
    loss_bounded = [name for name in loss_configs if results[name]['aggregate']['all_bounded']]

    lat_configs = [name for name, data in results.items() if data['config']['random_latency']]
    lat_bounded = [name for name in lat_configs if results[name]['aggregate']['all_bounded']]

    churn_configs = [name for name, data in results.items() if data['config']['churn']]
    churn_bounded = [name for name in churn_configs if results[name]['aggregate']['all_bounded']]

    fstep_configs = [name for name, data in results.items() if data['config']['freq_step']]
    fstep_bounded = [name for name in fstep_configs if results[name]['aggregate']['all_bounded']]

    print(f"  Heterogeneous drift: {len(het_unbounded)}/{len(het_configs)} configs unbounded")
    print(f"  Packet loss: {len(loss_configs) - len(loss_bounded)}/{len(loss_configs)} configs unbounded")
    print(f"  Random latency: {len(lat_configs) - len(lat_bounded)}/{len(lat_configs)} configs unbounded")
    print(f"  Churn: {len(churn_configs) - len(churn_bounded)}/{len(churn_configs)} configs unbounded")
    print(f"  Freq step: {len(fstep_configs) - len(fstep_bounded)}/{len(fstep_configs)} configs unbounded")

    # Identify which single stressor causes the most drift even alone
    singles = {name: data['aggregate']['worst_ss_max_drift']
               for name, data in results.items()
               if name in ['2_heterogeneous', '3_packet_loss', '4_random_latency', '5_churn', '6_freq_step']}
    worst_single = max(singles, key=singles.get)
    print(f"\n  Worst single stressor: {worst_single} (worst_ss={singles[worst_single]:.4f})")

    # Check pairwise synergy
    baseline_growth = results['1_baseline']['aggregate']['avg_drift_growth_rate']
    for name, data in results.items():
        if name == '1_baseline':
            continue
        growth = data['aggregate']['avg_drift_growth_rate']
        if growth > 0 and baseline_growth <= 0:
            print(f"  ⚠ {name}: positive drift growth ({growth:.6f}) — drift is INCREASING over time")
        elif growth > baseline_growth * 2 and growth > 0.001:
            print(f"  ⚠ {name}: elevated growth rate ({growth:.6f}) — 2x+ baseline")

    elapsed = time.time() - start_time
    print(f"\nTotal elapsed: {elapsed:.1f}s")

    # Save results
    output = {
        'experiment': 44,
        'title': 'Production Factorial Analysis',
        'description': 'Isolate which stressor combination breaks PTP',
        'configuration': {
            'N_initial': 20,
            'max_ticks': MAX_TICKS,
            'n_trials': N_TRIALS,
            'correction_gain': 0.4,
            'warmup': 50,
            'protocol': 'PTP 4-timestamp',
        },
        'stressor_configs': {name: {
            'config': data['config'],
            'aggregate': data['aggregate'],
        } for name, data in results.items()},
        'ranked_by_severity': [name for name, _ in ranked],
        'killers': killers,
        'survivors': survivors,
        'key_insight': {
            'worst_single_stressor': worst_single,
            'worst_single_drift': singles[worst_single],
            'individual_killers': individual_killers,
            'combo_killers': combo_killers,
        },
        'detailed_results': results,
    }

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, 'experiment44_factorial.json')
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nSaved to {out_path}")


if __name__ == '__main__':
    main()
