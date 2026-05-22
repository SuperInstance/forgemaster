#!/usr/bin/env python3
"""Experiment 43: Production Configuration Validation.

Combines ALL optimal settings discovered in previous experiments:
- PTP 4-timestamp protocol (Exp 40, 42)
- Correction gain α=0.4 (Exp 37)
- No deadband δ=0 (Exp 38)
- Boot-to-mean for new agents (Exp 41)
- Warm-up period W=50 (Exp 41)
- Two-timestamp asymmetry correction (Exp 36)
- Connected topology, any graph (Exp 27, 30)
- Weighted PTP for heterogeneous clocks (Exp 31)

Production scenario:
- N=20 agents, random connected graph
- Latency: uniformly random 1-20 ticks per message
- Packet loss: 10%
- Heterogeneous drift: σ ∈ {0.001..0.5}
- Churn: 1 join + 1 leave every 200 ticks
- Frequency step at tick 1000 (one agent σ jumps to 2.0)
- Run 5000 ticks, 10 trials

Hypothesis: production configuration maintains bounded drift (< 1.0) under ALL stressors simultaneously.

Save to experiments/results/experiment43_production.json
"""

import json
import math
import os
import random
import time
from collections import deque
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict

SEED = 43


def build_random_connected_graph(n: int, rng: random.Random) -> List[Tuple[int, int]]:
    """Build a random connected graph with ~2n edges (sparse but connected)."""
    if n < 2:
        return []
    edges = []
    # First, build a spanning tree
    for i in range(1, n):
        j = rng.randint(0, i - 1)
        edges.append((i, j))
    # Add extra edges for redundancy (~0.5n more)
    extra = max(1, n // 2)
    nodes = list(range(n))
    for _ in range(extra):
        i, j = rng.sample(nodes, 2)
        if (i, j) not in edges and (j, i) not in edges:
            edges.append((i, j))
    return edges


class PTP4Agent:
    """Agent with full PTP 4-timestamp protocol and all production optimizations.

    Features:
    - PTP 4-timestamp: Sync, FollowUp, DelayReq, DelayResp
    - Correction gain α=0.4
    - No deadband (δ=0)
    - Boot-to-mean initialization for new agents
    - Warm-up period W=50
    - Two-timestamp asymmetry correction
    - Weighted correction for heterogeneous clocks
    """

    def __init__(self, idx: int, sigma: float, alpha: float = 0.4,
                 warmup: int = 50, global_mean_clock: float = 0.0,
                 boot_to_mean: bool = False):
        self.idx = idx
        self.sigma = sigma  # drift rate standard deviation
        self.alpha = alpha  # correction gain

        # Clock: either boot to mean or start at 0
        if boot_to_mean:
            self.local_clock = global_mean_clock
        else:
            self.local_clock = 0.0

        # Drift: drawn from sigma
        self.drift_rate = random.gauss(0, sigma)

        # Neighbors: list of (agent_ref, weight)
        self.neighbors: List[Tuple['PTP4Agent', float]] = []

        # Deadband = 0 (no deadband)
        self.deadband = 0.0

        # Warm-up period
        self.warmup = warmup
        self.joined_tick = 0

        # PTP 4-timestamp state per neighbor
        # Maps neighbor_idx -> {t1, t2, t3, t4}
        self.ptp_state: Dict[int, dict] = {}

        # Asymmetry estimates per neighbor
        # forward_delay, reverse_delay
        self.asymmetry: Dict[int, dict] = {}

        # Inbox: (deliver_at, sender_idx, msg_type, data)
        self.inbox: deque = deque()

        # For churn tracking
        self.active = True
        self.join_tick = 0

    def tick(self, tick_num: int):
        """Advance local clock by 1 + drift."""
        if not self.active:
            return
        self.local_clock += 1.0 + self.drift_rate

    def broadcast_ptp_sync(self, current_tick: int, latency_fn):
        """PTP Step 1+2: Send Sync + FollowUp (t1=send time, t2=receive time)."""
        if not self.active:
            return
        t1 = self.local_clock  # timestamp 1: master sends sync
        for neighbor, weight in self.neighbors:
            if not neighbor.active:
                continue
            latency = latency_fn(current_tick, self.idx, neighbor.idx)
            deliver_at = current_tick + latency
            # Pack: (t1, send_tick, weight_for_heterogeneous)
            neighbor.inbox.append((
                deliver_at, self.idx, 'sync',
                {'t1': t1, 'sent_tick': current_tick, 'weight': weight}
            ))

    def handle_sync(self, current_tick: int):
        """PTP Step 2: Receive sync, record t2. Request delay measurement."""
        messages = []
        remaining = deque()
        for msg in self.inbox:
            deliver_at, sender_idx, msg_type, data = msg
            if deliver_at <= current_tick:
                messages.append(msg)
            else:
                remaining.append(msg)
        self.inbox = remaining

        for deliver_at, sender_idx, msg_type, data in messages:
            if msg_type == 'sync':
                t2 = self.local_clock  # timestamp 2: slave receives sync
                # Store state
                if sender_idx not in self.ptp_state:
                    self.ptp_state[sender_idx] = {}
                self.ptp_state[sender_idx]['t1'] = data['t1']
                self.ptp_state[sender_idx]['t2'] = t2
                self.ptp_state[sender_idx]['sync_sent_tick'] = data['sent_tick']
                self.ptp_state[sender_idx]['weight'] = data['weight']
                self.ptp_state[sender_idx]['latency'] = current_tick - data['sent_tick']

            elif msg_type == 'delay_resp':
                t4 = self.local_clock  # timestamp 4: slave receives delay response
                # Complete 4-timestamp
                if sender_idx in self.ptp_state:
                    state = self.ptp_state[sender_idx]
                    if 't3' in state:
                        t1 = state['t1']
                        t2 = state['t2']
                        t3 = state['t3']
                        self._apply_4timestamp_correction(
                            sender_idx, t1, t2, t3, t4, state.get('weight', 1.0),
                            state.get('latency', 0)
                        )

    def send_delay_req(self, current_tick: int, latency_fn):
        """PTP Step 3: Slave sends DelayReq (t3)."""
        if not self.active:
            return
        t3 = self.local_clock
        for neighbor, weight in self.neighbors:
            if not neighbor.active:
                continue
            if neighbor.idx in self.ptp_state and 't2' in self.ptp_state[neighbor.idx]:
                # Only send delay req if we've received a sync from this neighbor
                latency = latency_fn(current_tick, self.idx, neighbor.idx)
                deliver_at = current_tick + latency
                neighbor.inbox.append((
                    deliver_at, self.idx, 'delay_req',
                    {'t3': t3, 'sent_tick': current_tick}
                ))
                self.ptp_state[neighbor.idx]['t3'] = t3
                self.ptp_state[neighbor.idx]['delay_sent_tick'] = current_tick
                self.ptp_state[neighbor.idx]['delay_latency'] = latency

    def handle_delay_req(self, current_tick: int, latency_fn):
        """PTP Step 4: Master receives DelayReq, sends DelayResp with t4."""
        messages = []
        remaining = deque()
        for msg in self.inbox:
            deliver_at, sender_idx, msg_type, data = msg
            if deliver_at <= current_tick:
                messages.append(msg)
            else:
                remaining.append(msg)
        self.inbox = remaining

        for deliver_at, sender_idx, msg_type, data in messages:
            if msg_type == 'delay_req':
                t4 = self.local_clock  # timestamp 4: master receives delay req
                # Send response back
                latency = latency_fn(current_tick, self.idx, sender_idx)
                deliver_at_resp = current_tick + latency
                # Find the sender agent
                for neighbor, _ in self.neighbors:
                    if neighbor.idx == sender_idx and neighbor.active:
                        neighbor.inbox.append((
                            deliver_at_resp, self.idx, 'delay_resp',
                            {'t4': t4, 'sent_tick': current_tick}
                        ))
                        break

    def _apply_4timestamp_correction(self, neighbor_idx, t1, t2, t3, t4,
                                      weight: float, measured_latency: int):
        """Apply PTP 4-timestamp offset correction with all optimizations."""
        # PTP offset: offset = ((t2 - t1) - (t4 - t3)) / 2
        # Prop delay:  prop_delay = ((t2 - t1) + (t4 - t3)) / 2
        forward_delay = t2 - t1
        reverse_delay = t4 - t3

        offset = (forward_delay - reverse_delay) / 2.0
        prop_delay = (forward_delay + reverse_delay) / 2.0

        # Two-timestamp asymmetry correction (Exp 36)
        # Estimate forward vs reverse delay ratio
        if neighbor_idx not in self.asymmetry:
            self.asymmetry[neighbor_idx] = {
                'forward_samples': [],
                'reverse_samples': [],
                'gamma': 1.0  # symmetry factor (1.0 = symmetric)
            }
        asym = self.asymmetry[neighbor_idx]
        asym['forward_samples'].append(forward_delay)
        asym['reverse_samples'].append(reverse_delay)
        # Keep last 20 samples
        if len(asym['forward_samples']) > 20:
            asym['forward_samples'] = asym['forward_samples'][-20:]
            asym['reverse_samples'] = asym['reverse_samples'][-20:]
        # Estimate gamma (forward/reverse ratio)
        if len(asym['forward_samples']) >= 5:
            fwd_mean = sum(asym['forward_samples']) / len(asym['forward_samples'])
            rev_mean = sum(asym['reverse_samples']) / len(asym['reverse_samples'])
            if abs(rev_mean) > 1e-10:
                asym['gamma'] = fwd_mean / rev_mean

        # Corrected offset with asymmetry
        gamma = asym['gamma']
        # Adjust offset for asymmetry: corrected = offset * 2 / (1 + gamma)
        if abs(1.0 + gamma) > 1e-10:
            corrected_offset = offset * 2.0 / (1.0 + gamma)
        else:
            corrected_offset = offset

        # Weighted PTP for heterogeneous clocks (Exp 31)
        # Weight inversely proportional to sigma of the neighbor
        # Higher weight = more trusted = lower drift agent
        # Weight is passed in from topology setup

        # Correction gain α=0.4 (Exp 37)
        correction = self.alpha * corrected_offset * weight

        # No deadband (Exp 38): apply correction always
        self.local_clock += correction


def make_production_latency_fn(rng: random.Random, loss_rate: float = 0.10):
    """Production latency: uniformly random 1-20 ticks, with packet loss."""
    def fn(tick, sender, receiver):
        if rng.random() < loss_rate:
            return 999999  # Effectively lost (delivered after simulation ends)
        return rng.randint(1, 20)
    return fn


def run_production_trial(trial_seed: int, max_ticks: int = 5000):
    """Run a single production trial with all stressors."""
    rng = random.Random(trial_seed)
    start_time = time.time()

    # Initial N=20 agents with heterogeneous drift
    N_initial = 20
    agents: List[PTP4Agent] = []
    # Heterogeneous drift: σ ∈ {0.001..0.5} — log-uniform
    for i in range(N_initial):
        log_sigma = rng.uniform(math.log10(0.001), math.log10(0.5))
        sigma = 10 ** log_sigma
        agents.append(PTP4Agent(i, sigma, alpha=0.4, warmup=50, boot_to_mean=False))

    # Build random connected graph
    edges = build_random_connected_graph(N_initial, rng)

    # Set up neighbor relationships with heterogeneous weights
    adj = {}
    for u, v in edges:
        adj.setdefault(u, set()).add(v)
        adj.setdefault(v, set()).add(u)

    for u, v in edges:
        # Weight inversely proportional to max sigma of the pair
        max_sigma = max(agents[u].sigma, agents[v].sigma)
        w = 1.0 / (1.0 + max_sigma)
        agents[u].neighbors.append((agents[v], w))
        agents[v].neighbors.append((agents[u], w))

    latency_fn = make_production_latency_fn(rng, loss_rate=0.10)

    # Churn schedule: 1 join + 1 leave every 200 ticks
    churn_events = []
    next_agent_id = N_initial
    for tick in range(200, max_ticks, 200):
        # Join: add a new agent
        join_id = next_agent_id
        next_agent_id += 1
        log_sigma = rng.uniform(math.log10(0.001), math.log10(0.5))
        sigma = 10 ** log_sigma
        # Boot-to-mean: initialize to current mean clock
        active_clocks = [a.local_clock for a in agents if a.active]
        mean_clock = sum(active_clocks) / len(active_clocks) if active_clocks else 0.0
        new_agent = PTP4Agent(join_id, sigma, alpha=0.4, warmup=50,
                              global_mean_clock=mean_clock, boot_to_mean=True)
        new_agent.join_tick = tick
        new_agent.joined_tick = tick

        # Connect to 2-3 random active agents
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

        # Leave: remove a random active agent (not the newest)
        active_for_leave = [a for a in agents if a.active and a.idx != join_id]
        if len(active_for_leave) > 5:  # keep minimum 5
            leaving = rng.choice(active_for_leave)
            leaving.active = False
            # Remove from neighbor lists
            for a in agents:
                a.neighbors = [(n, w) for n, w in a.neighbors if n.idx != leaving.idx]

        churn_events.append({
            'tick': tick,
            'joined': join_id,
            'joined_sigma': round(sigma, 4),
            'left': leaving.idx if len(active_for_leave) > 5 else None
        })

    # Frequency step at tick 1000: one agent's σ jumps to 2.0
    freq_step_agent = rng.randint(0, N_initial - 1)
    freq_step_applied = False

    # Metrics collection
    drift_over_time = []  # sampled every 50 ticks
    convergence_tick = None
    max_drift_log = []
    active_count_log = []

    for tick in range(1, max_ticks + 1):
        # Apply frequency step at tick 1000
        if tick == 1000 and not freq_step_applied:
            target = agents[freq_step_agent]
            if target.active:
                target.drift_rate = rng.gauss(2.0, 0.1)  # σ jumps to 2.0
                freq_step_applied = True

        # Tick all active agents
        for a in agents:
            if a.active:
                a.tick(tick)

        # PTP 4-timestamp exchange
        # Step 1: Masters broadcast sync
        for a in agents:
            if a.active and (tick - getattr(a, 'joined_tick', 0)) > a.warmup:
                a.broadcast_ptp_sync(tick, latency_fn)

        # Step 2: Handle sync messages, send delay req
        for a in agents:
            if a.active and (tick - getattr(a, 'joined_tick', 0)) > a.warmup:
                a.handle_sync(tick)
                a.send_delay_req(tick, latency_fn)

        # Step 3: Handle delay req, send delay resp
        for a in agents:
            if a.active:
                a.handle_delay_req(tick, latency_fn)

        # Step 4: Handle delay resp (done inside handle_sync via delay_resp messages)
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

        # Pairwise drift
        pairwise_drifts = []
        for i in range(len(active_agents)):
            for j in range(i + 1, len(active_agents)):
                pairwise_drifts.append(abs(active_agents[i].local_clock - active_agents[j].local_clock))
        max_pairwise = max(pairwise_drifts) if pairwise_drifts else 0

        active_count_log.append(len(active_agents))

        # Sample every 50 ticks for time series
        if tick % 50 == 0:
            drift_over_time.append({
                'tick': tick,
                'max_drift': round(max_drift, 4),
                'mean_drift': round(mean_drift, 4),
                'max_pairwise': round(max_pairwise, 4),
                'active_agents': len(active_agents)
            })

        # Convergence check (post warmup)
        if tick > 100:
            if max_drift < 1.0:
                # Check sustained convergence
                if len(max_drift_log) >= 50:
                    recent = max_drift_log[-50:]
                    if all(d < 1.0 for d in recent):
                        if convergence_tick is None:
                            convergence_tick = tick - 49

    elapsed = time.time() - start_time

    # Compute summary metrics
    # Steady-state: last 500 ticks
    ss_window = max_drift_log[-500:] if len(max_drift_log) >= 500 else max_drift_log
    ss_max = max(ss_window)
    ss_mean = sum(ss_window) / len(ss_window)
    ss_p95 = sorted(ss_window)[int(0.95 * len(ss_window))]

    # Post-frequency-step recovery (ticks 1000-1500)
    post_step_window = max_drift_log[1000:1500] if len(max_drift_log) > 1500 else []
    post_step_max = max(post_step_window) if post_step_window else None
    post_step_recovery_tick = None
    if post_step_window:
        for i, d in enumerate(post_step_window):
            if d < 1.0 and all(post_step_window[j] < 1.0 for j in range(i, min(i + 50, len(post_step_window)))):
                post_step_recovery_tick = 1000 + i
                break

    # Churn handling: drift right after churn events
    churn_drifts = []
    for ce in churn_events:
        ct = ce['tick']
        if ct < len(max_drift_log):
            churn_drifts.append(max_drift_log[min(ct + 10, len(max_drift_log) - 1)])

    # Overall bounded check
    bounded = all(d < 1.0 for d in ss_window)

    return {
        'trial_seed': trial_seed,
        'convergence_tick': convergence_tick,
        'steady_state_max_drift': round(ss_max, 4),
        'steady_state_mean_drift': round(ss_mean, 4),
        'steady_state_p95_drift': round(ss_p95, 4),
        'peak_drift': round(max(max_drift_log), 4),
        'post_freq_step_max_drift': round(post_step_max, 4) if post_step_max is not None else None,
        'post_freq_step_recovery_tick': post_step_recovery_tick,
        'avg_churn_drift': round(sum(churn_drifts) / len(churn_drifts), 4) if churn_drifts else None,
        'max_churn_drift': round(max(churn_drifts), 4) if churn_drifts else None,
        'bounded_in_steady_state': bounded,
        'drift_over_time': drift_over_time,
        'churn_events': churn_events,
        'freq_step_agent': freq_step_agent,
        'elapsed_seconds': round(elapsed, 1),
        'final_active_agents': sum(1 for a in agents if a.active),
    }


def main():
    start_time = time.time()
    print("=" * 70)
    print("EXPERIMENT 43: Production Configuration Validation")
    print("=" * 70)
    print()
    print("Configuration:")
    print("  N=20 agents, random connected graph")
    print("  Latency: uniformly random 1-20 ticks")
    print("  Packet loss: 10%")
    print("  Heterogeneous drift: σ ∈ {0.001..0.5}")
    print("  Churn: 1 join + 1 leave every 200 ticks")
    print("  Frequency step at tick 1000 (one agent σ→2.0)")
    print("  5000 ticks, 10 trials")
    print()
    print("Optimal settings:")
    print("  PTP 4-timestamp protocol")
    print("  Correction gain α=0.4")
    print("  No deadband (δ=0)")
    print("  Boot-to-mean for new agents")
    print("  Warm-up period W=50")
    print("  Two-timestamp asymmetry correction")
    print("  Weighted PTP for heterogeneous clocks")
    print()

    N_TRIALS = 10
    MAX_TICKS = 5000
    trials = []

    for t in range(N_TRIALS):
        trial_seed = SEED * 1000 + t * 137
        print(f"  Trial {t+1}/{N_TRIALS} (seed={trial_seed})...", end=" ", flush=True)
        result = run_production_trial(trial_seed, MAX_TICKS)
        trials.append(result)
        tag = "✓" if result['bounded_in_steady_state'] else "✗"
        print(f"ss_max={result['steady_state_max_drift']:.4f} "
              f"peak={result['peak_drift']:.4f} "
              f"conv={result['convergence_tick']} "
              f"recovery={result['post_freq_step_recovery_tick']} "
              f"[{tag}]")

    # Aggregate results
    all_bounded = all(t['bounded_in_steady_state'] for t in trials)
    avg_ss_max = sum(t['steady_state_max_drift'] for t in trials) / N_TRIALS
    avg_ss_mean = sum(t['steady_state_mean_drift'] for t in trials) / N_TRIALS
    avg_peak = sum(t['peak_drift'] for t in trials) / N_TRIALS
    worst_ss = max(t['steady_state_max_drift'] for t in trials)
    worst_peak = max(t['peak_drift'] for t in trials)

    conv_ticks = [t['convergence_tick'] for t in trials if t['convergence_tick'] is not None]
    avg_conv = sum(conv_ticks) / len(conv_ticks) if conv_ticks else None

    recovery_ticks = [t['post_freq_step_recovery_tick'] for t in trials if t['post_freq_step_recovery_tick'] is not None]
    avg_recovery = sum(recovery_ticks) / len(recovery_ticks) if recovery_ticks else None
    recovery_rate = len(recovery_ticks) / N_TRIALS

    churn_drifts = [t['avg_churn_drift'] for t in trials if t['avg_churn_drift'] is not None]
    avg_churn_drift = sum(churn_drifts) / len(churn_drifts) if churn_drifts else None

    # Hypothesis check
    hypothesis = {
        'statement': 'Production configuration maintains bounded drift (< 1.0) under ALL stressors simultaneously',
        'bounded_in_steady_state': all_bounded,
        'worst_steady_state_drift': worst_ss,
        'worst_peak_drift': worst_peak,
        'hypothesis_supported': all_bounded and worst_ss < 1.0,
    }

    key_findings = []

    if hypothesis['hypothesis_supported']:
        key_findings.append(
            f"HYPOTHESIS CONFIRMED: All {N_TRIALS} trials maintain drift < 1.0 in steady state. "
            f"Worst SS drift = {worst_ss:.4f}. Production config is VALIDATED."
        )
    else:
        n_failed = sum(1 for t in trials if not t['bounded_in_steady_state'])
        key_findings.append(
            f"HYPOTHESIS {'PARTIALLY SUPPORTED' if n_failed < N_TRIALS else 'REJECTED'}: "
            f"{N_TRIALS - n_failed}/{N_TRIALS} trials bounded. Worst SS drift = {worst_ss:.4f}."
        )

    key_findings.append(
        f"Steady-state drift: avg_max={avg_ss_max:.4f}, avg_mean={avg_ss_mean:.4f}, "
        f"worst_max={worst_ss:.4f}, avg_peak={avg_peak:.4f}"
    )

    if avg_conv:
        key_findings.append(f"Convergence: avg tick {avg_conv:.0f}, {len(conv_ticks)}/{N_TRIALS} trials converged")

    if recovery_rate > 0:
        key_findings.append(
            f"Frequency step recovery: {recovery_rate:.0%} of trials recovered, "
            f"avg recovery at tick {avg_recovery:.0f}"
        )
    else:
        key_findings.append("Frequency step recovery: No trials fully recovered within measurement window")

    if avg_churn_drift is not None:
        key_findings.append(
            f"Churn handling: avg drift after churn = {avg_churn_drift:.4f}"
        )

    # Build composite drift-over-time for plotting (average across trials)
    ticks_sampled = [50 * i for i in range(1, MAX_TICKS // 50 + 1)]
    composite_drift = []
    for tick_idx in range(len(ticks_sampled)):
        drifts_at_tick = []
        for t in trials:
            if tick_idx < len(t['drift_over_time']):
                drifts_at_tick.append(t['drift_over_time'][tick_idx]['max_drift'])
        if drifts_at_tick:
            composite_drift.append({
                'tick': ticks_sampled[tick_idx],
                'avg_max_drift': round(sum(drifts_at_tick) / len(drifts_at_tick), 4),
                'worst_max_drift': round(max(drifts_at_tick), 4),
                'best_max_drift': round(min(drifts_at_tick), 4),
            })

    elapsed = round(time.time() - start_time, 1)

    output = {
        'experiment': 43,
        'title': 'Production Configuration Validation',
        'description': 'Combine all optimal settings and stress test under production conditions',
        'configuration': {
            'N_initial': 20,
            'max_ticks': MAX_TICKS,
            'n_trials': N_TRIALS,
            'latency_range': '1-20 uniform random',
            'packet_loss': 0.10,
            'drift_sigma_range': '0.001..0.5 (log-uniform)',
            'churn_rate': '1 join + 1 leave per 200 ticks',
            'frequency_step': {'tick': 1000, 'sigma_jump': 2.0},
            'correction_gain': 0.4,
            'deadband': 0.0,
            'warmup_period': 50,
            'boot_to_mean': True,
            'protocol': 'PTP 4-timestamp',
            'asymmetry_correction': True,
            'weighted_ptp': True,
        },
        'trials': trials,
        'composite_drift_over_time': composite_drift,
        'aggregate': {
            'all_bounded': all_bounded,
            'avg_steady_state_max_drift': round(avg_ss_max, 4),
            'avg_steady_state_mean_drift': round(avg_ss_mean, 4),
            'worst_steady_state_max_drift': round(worst_ss, 4),
            'avg_peak_drift': round(avg_peak, 4),
            'worst_peak_drift': round(worst_peak, 4),
            'avg_convergence_tick': round(avg_conv, 1) if avg_conv else None,
            'convergence_rate': f"{len(conv_ticks)}/{N_TRIALS}",
            'freq_step_recovery_rate': f"{len(recovery_ticks)}/{N_TRIALS}",
            'avg_freq_step_recovery_tick': round(avg_recovery, 1) if avg_recovery else None,
            'avg_churn_drift': round(avg_churn_drift, 4) if avg_churn_drift else None,
        },
        'hypothesis': hypothesis,
        'key_findings': key_findings,
        'elapsed_seconds': elapsed,
    }

    os.makedirs("experiments/results", exist_ok=True)
    out_path = "experiments/results/experiment43_production.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved → {out_path}")

    # Print summary
    print(f"\n{'='*70}")
    print("EXPERIMENT 43 SUMMARY")
    print(f"{'='*70}")
    print(f"  Trials: {N_TRIALS}")
    print(f"  All bounded (< 1.0): {'YES ✓' if all_bounded else 'NO ✗'}")
    print(f"  Avg SS max drift: {avg_ss_max:.4f}")
    print(f"  Worst SS max drift: {worst_ss:.4f}")
    print(f"  Avg peak drift: {avg_peak:.4f}")
    print(f"  Worst peak drift: {worst_peak:.4f}")
    print(f"  Convergence: {len(conv_ticks)}/{N_TRIALS} (avg tick {avg_conv:.0f})" if avg_conv else f"  Convergence: 0/{N_TRIALS}")
    print(f"  Freq step recovery: {len(recovery_ticks)}/{N_TRIALS}" + (f" (avg tick {avg_recovery:.0f})" if avg_recovery else ""))
    print(f"  Churn avg drift: {avg_churn_drift:.4f}" if avg_churn_drift else "  Churn: N/A")
    print()
    print("KEY FINDINGS:")
    for i, f in enumerate(key_findings):
        print(f"  [{i+1}] {f}")
    print(f"\nElapsed: {elapsed}s")

    return output


if __name__ == "__main__":
    main()
