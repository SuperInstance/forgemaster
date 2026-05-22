#!/usr/bin/env python3
"""Experiment 27: Spectral-PTP Coupling.

Does the Laplacian eigenvalue structure affect PTP correction quality?

Topologies: complete, ring, star, path, Laman, small-world, random-sparse, grid-2D
For each: compute λ₂ (algebraic connectivity) and λₙ
Run PTP clock sync: N=10, latency=10 ticks, 1000 ticks/trial, 5 trials
Metrics: convergence tick, steady-state drift, jitter, correction magnitude

Hypothesis: higher λ₂ → faster convergence AND lower steady-state drift
Also: does PTP work on non-Laman topologies?
"""
import json
import math
import os
import random
import time
from collections import defaultdict, deque

SEED = 42
N = 10
LATENCY = 10
MAX_TICKS = 1000
N_TRIALS = 5
WARMUP = 100


# ── Topology builders ──────────────────────────────────────────────

def topo_complete(n):
    return [(i, j) for i in range(n) for j in range(i + 1, n)]


def topo_ring(n):
    return [(i, (i + 1) % n) for i in range(n)]


def topo_star(n):
    return [(0, i) for i in range(1, n)]


def topo_path(n):
    return [(i, i + 1) for i in range(n - 1)]


def topo_laman(n, seed_offset=0):
    rng = random.Random(SEED + seed_offset)
    edges = []
    for i in range(3):
        for j in range(i + 1, 3):
            edges.append((i, j))
    for k in range(3, n):
        targets = rng.sample(range(k), 2)
        for t in targets:
            edges.append((k, t))
    return edges


def topo_small_world(n, k=2, p=0.3, seed_offset=0):
    """Watts-Strogatz small-world: ring lattice with rewire prob p."""
    rng = random.Random(SEED + seed_offset)
    edges = set()
    for i in range(n):
        for offset in range(1, k + 1):
            j = (i + offset) % n
            edges.add((min(i, j), max(i, j)))
    # Rewire
    rewired = set()
    for u, v in edges:
        if rng.random() < p:
            candidates = [x for x in range(n) if x != u and (min(u, x), max(u, x)) not in edges]
            if candidates:
                new_v = rng.choice(candidates)
                rewired.add((min(u, new_v), max(u, new_v)))
            else:
                rewired.add((u, v))
        else:
            rewired.add((u, v))
    return list(rewired)


def topo_random_sparse(n, edge_factor=1.5, seed_offset=0):
    """Random sparse graph with ~edge_factor*n edges."""
    rng = random.Random(SEED + seed_offset)
    target_edges = int(n * edge_factor)
    edges = set()
    # Start with spanning tree to ensure connectivity
    for i in range(1, n):
        j = rng.randint(0, i - 1)
        edges.add((min(i, j), max(i, j)))
    # Add random edges
    attempts = 0
    while len(edges) < target_edges and attempts < target_edges * 10:
        i = rng.randint(0, n - 1)
        j = rng.randint(0, n - 1)
        if i != j:
            edges.add((min(i, j), max(i, j)))
        attempts += 1
    return list(edges)


def topo_grid2d(n):
    """2D grid, n agents arranged as close to square as possible."""
    import math as m
    rows = int(m.sqrt(n))
    cols = n // rows
    if rows * cols < n:
        cols += 1
    edges = []
    for r in range(rows):
        for c in range(cols):
            idx = r * cols + c
            if idx >= n:
                break
            # Right neighbor
            if c + 1 < cols and idx + 1 < n:
                edges.append((idx, idx + 1))
            # Down neighbor
            if r + 1 < rows and idx + cols < n:
                edges.append((idx, idx + cols))
    return edges


def is_laman(n, edges):
    """Check Laman condition: |E| = 2n - 3 and all subgraphs |E'| ≤ 2|V'| - 3."""
    m = len(edges)
    if m != 2 * n - 3:
        return False
    # Full check is exponential; sample subsets for practical check
    if n <= 8:
        return _laman_brute(n, edges)
    return _laman_sample(n, edges)


def _laman_brute(n, edges):
    edge_set = set(edges)
    from itertools import combinations
    for k in range(2, n):
        for subset in combinations(range(n), k):
            sub_edges = sum(1 for u, v in edge_set if u in subset and v in subset)
            if sub_edges > 2 * len(subset) - 3:
                return False
    return True


def _laman_sample(n, edges, samples=200):
    rng = random.Random(123)
    edge_set = set(edges)
    nodes = list(range(n))
    for _ in range(samples):
        k = rng.randint(2, n - 1)
        subset = set(rng.sample(nodes, k))
        sub_edges = sum(1 for u, v in edge_set if u in subset and v in subset)
        if sub_edges > 2 * k - 3:
            return False
    return True


# ── Laplacian & eigenvalues ────────────────────────────────────────

def laplacian_eigenvalues(n, edges):
    """Compute eigenvalues of the graph Laplacian (trivial, no scipy needed)."""
    # Build Laplacian matrix L = D - A
    L = [[0.0] * n for _ in range(n)]
    adj = defaultdict(set)
    for u, v in edges:
        adj[u].add(v)
        adj[v].add(u)
    for i in range(n):
        L[i][i] = len(adj[i])
        for j in adj[i]:
            L[i][j] = -1.0
    # Power iteration for top eigenvalue, then deflate
    # Use simple QR-free approach: compute all eigenvalues via characteristic polynomial
    # Actually, let's just use the Gershgorin + power method approach
    # Better: use the iterative method for symmetric matrices
    eigenvalues = _symmetric_eigenvalues(L, n)
    eigenvalues.sort()
    return eigenvalues


def _symmetric_eigenvalues(M, n, iterations=200):
    """Compute eigenvalues of symmetric matrix using Jacobi iteration."""
    A = [row[:] for row in M]  # copy

    for _ in range(iterations * n * n):
        # Find largest off-diagonal element
        max_val = 0.0
        p, q = 0, 1
        for i in range(n):
            for j in range(i + 1, n):
                if abs(A[i][j]) > max_val:
                    max_val = abs(A[i][j])
                    p, q = i, j
        if max_val < 1e-12:
            break

        # Compute rotation angle
        if abs(A[p][p] - A[q][q]) < 1e-15:
            theta = math.pi / 4
        else:
            theta = 0.5 * math.atan2(2 * A[p][q], A[p][p] - A[q][q])

        c = math.cos(theta)
        s = math.sin(theta)

        # Apply Givens rotation
        new_A = [row[:] for row in A]
        for i in range(n):
            if i != p and i != q:
                new_A[i][p] = c * A[i][p] + s * A[i][q]
                new_A[p][i] = new_A[i][p]
                new_A[i][q] = -s * A[i][p] + c * A[i][q]
                new_A[q][i] = new_A[i][q]

        new_A[p][p] = c * c * A[p][p] + 2 * s * c * A[p][q] + s * s * A[q][q]
        new_A[q][q] = s * s * A[p][p] - 2 * s * c * A[p][q] + c * c * A[q][q]
        new_A[p][q] = 0.0
        new_A[q][p] = 0.0

        A = new_A

    return [A[i][i] for i in range(n)]


# ── PTP Agent (from Exp25) ────────────────────────────────────────

class PTPAgent:
    def __init__(self, idx, delta=0.0625, epsilon=0.01):
        self.idx = idx
        self.local_clock = 0.0
        self.epsilon = epsilon
        self.delta = delta
        self.neighbors = []
        self.drift_rate = epsilon * (idx - 4.5) / 20.0
        self.inbox = deque()
        self.total_correction = 0.0
        self.correction_log = []

    def tick(self, tick_num):
        self.local_clock += 1.0 + self.drift_rate

    def broadcast(self, current_tick, latency):
        reported = self.local_clock
        for neighbor, _ in self.neighbors:
            deliver_at = current_tick + latency
            neighbor.inbox.append((deliver_at, self.idx, reported, current_tick))

    def receive(self, current_tick):
        reports = []
        remaining = deque()
        for msg in self.inbox:
            deliver_tick, sender_idx, reported_clock, sent_tick = msg
            if deliver_tick <= current_tick:
                reports.append((sender_idx, reported_clock, sent_tick))
            else:
                remaining.append(msg)
        self.inbox = remaining
        return reports

    def correct_ptp(self, reports, current_tick):
        if not reports:
            return
        offset_estimates = []
        for sender_idx, reported_clock, sent_tick in reports:
            lat = current_tick - sent_tick
            neighbor_now = reported_clock + lat
            offset = neighbor_now - self.local_clock
            offset_estimates.append(offset)

        avg_offset = sum(offset_estimates) / len(offset_estimates)
        correction = 0.5 * avg_offset
        correction = max(-2.0, min(2.0, correction))
        self.local_clock += correction
        self.total_correction += abs(correction)
        self.correction_log.append(abs(correction))


# ── Trial runner ───────────────────────────────────────────────────

def run_trial(n, edges, trial_seed, latency=LATENCY, max_ticks=MAX_TICKS, warmup=WARMUP):
    agents = [PTPAgent(i) for i in range(n)]
    for i, j in edges:
        agents[i].neighbors.append((agents[j], 1.0))
        agents[j].neighbors.append((agents[i], 1.0))

    drift_log = []
    convergence_tick = None
    consecutive_stable = 0

    for tick in range(1, max_ticks + 1):
        for a in agents:
            a.tick(tick)
        for a in agents:
            a.broadcast(tick, latency)
        for a in agents:
            reports = a.receive(tick)
            a.correct_ptp(reports, tick)

        ideal = float(tick)
        drifts = [abs(a.local_clock - ideal) for a in agents]
        max_drift = max(drifts)
        drift_log.append(max_drift)

        if tick > warmup:
            if max_drift < 0.1:
                consecutive_stable += 1
                if consecutive_stable >= 20 and convergence_tick is None:
                    convergence_tick = tick - 19
            else:
                consecutive_stable = 0

    post_warmup = drift_log[warmup:]
    ss_window = post_warmup[-200:]
    steady_state_drift = max(ss_window)
    mean_drift_ss = sum(ss_window) / len(ss_window)
    peak_drift = max(drift_log)
    jitter = sum((d - mean_drift_ss) ** 2 for d in ss_window) / len(ss_window)

    total_corr = sum(a.total_correction for a in agents) / n
    avg_corr_mag = []
    for a in agents:
        if a.correction_log:
            avg_corr_mag.append(sum(a.correction_log) / len(a.correction_log))
    mean_correction = sum(avg_corr_mag) / len(avg_corr_mag) if avg_corr_mag else 0

    return {
        "trial_seed": trial_seed,
        "convergence_tick": convergence_tick,
        "converged": convergence_tick is not None,
        "steady_state_max_drift": round(steady_state_drift, 6),
        "steady_state_mean_drift": round(mean_drift_ss, 6),
        "peak_drift": round(peak_drift, 6),
        "jitter": round(jitter, 8),
        "avg_total_correction": round(total_corr, 6),
        "avg_correction_magnitude": round(mean_correction, 6),
    }


# ── Main experiment ────────────────────────────────────────────────

def run_experiment():
    start_time = time.time()

    topologies = {
        "complete": lambda n: topo_complete(n),
        "ring": lambda n: topo_ring(n),
        "star": lambda n: topo_star(n),
        "path": lambda n: topo_path(n),
        "laman": lambda n: topo_laman(n),
        "small_world": lambda n: topo_small_world(n),
        "random_sparse": lambda n: topo_random_sparse(n),
        "grid_2d": lambda n: topo_grid2d(n),
    }

    results = []

    print("=" * 90)
    print("EXPERIMENT 27: Spectral-PTP Coupling")
    print(f"N={N}  latency={LATENCY}  max_ticks={MAX_TICKS}  trials={N_TRIALS}")
    print("=" * 90)
    print(f"{'Topology':<16} {'|E|':>4} {'λ₂':>10} {'λₙ':>10} {'λ₂/λₙ':>8} {'Laman?':>7} │"
          f" {'Conv':>6} {'SS Drift':>10} {'Jitter':>12} {'AvgCorr':>10}")
    print("-" * 110)

    for topo_name, builder in topologies.items():
        edges = builder(N)
        n_edges = len(edges)

        # Eigenvalues
        eigs = laplacian_eigenvalues(N, edges)
        lambda2 = eigs[1] if len(eigs) > 1 else 0.0
        lambda_n = eigs[-1] if eigs else 1.0
        spectral_gap = lambda_n - lambda2
        cond_number = lambda_n / lambda2 if lambda2 > 1e-12 else float('inf')

        laman_check = is_laman(N, edges)

        # Run trials
        trials = []
        for t in range(N_TRIALS):
            trial_seed = SEED + t * 1000 + hash(topo_name) % 10000
            tr = run_trial(N, edges, trial_seed)
            trials.append(tr)

        # Aggregate
        conv_rate = sum(1 for tr in trials if tr["converged"]) / N_TRIALS
        avg_ss_drift = sum(tr["steady_state_max_drift"] for tr in trials) / N_TRIALS
        avg_jitter = sum(tr["jitter"] for tr in trials) / N_TRIALS
        avg_corr = sum(tr["avg_correction_magnitude"] for tr in trials) / N_TRIALS
        conv_ticks = [tr["convergence_tick"] for tr in trials if tr["convergence_tick"] is not None]
        avg_conv = round(sum(conv_ticks) / len(conv_ticks), 1) if conv_ticks else None
        avg_peak = sum(tr["peak_drift"] for tr in trials) / N_TRIALS

        tag = "✓" if laman_check else "✗"
        print(f"{topo_name:<16} {n_edges:>4} {lambda2:>10.4f} {lambda_n:>10.4f} {cond_number:>8.2f} {tag:>7} │"
              f" {conv_rate:>5.0%} {avg_ss_drift:>10.4f} {avg_jitter:>12.6f} {avg_corr:>10.4f}")

        results.append({
            "topology": topo_name,
            "n_edges": n_edges,
            "eigenvalues": [round(e, 6) for e in eigs],
            "lambda2": round(lambda2, 6),
            "lambda_n": round(lambda_n, 6),
            "spectral_gap": round(spectral_gap, 6),
            "condition_number": round(cond_number, 4) if cond_number != float('inf') else "inf",
            "is_laman": laman_check,
            "avg_convergence_rate": conv_rate,
            "avg_convergence_tick": avg_conv,
            "avg_steady_state_drift": round(avg_ss_drift, 6),
            "avg_jitter": round(avg_jitter, 8),
            "avg_peak_drift": round(avg_peak, 6),
            "avg_correction_magnitude": round(avg_corr, 6),
            "trials": trials,
        })

    # ── Analysis ──────────────────────────────────────────────

    # Sort by λ₂ to see correlation
    by_lam2 = sorted(results, key=lambda r: r["lambda2"])

    print(f"\n{'=' * 90}")
    print("SPECTRAL-PTP CORRELATION (sorted by λ₂)")
    print(f"{'=' * 90}")
    print(f"{'Topology':<16} {'λ₂':>10} {'SS Drift':>12} {'Conv Rate':>10} {'Jitter':>12}")
    print("-" * 65)
    for r in by_lam2:
        print(f"{r['topology']:<16} {r['lambda2']:>10.4f} {r['avg_steady_state_drift']:>12.6f}"
              f" {r['avg_convergence_rate']:>10.2f} {r['avg_jitter']:>12.8f}")

    # Correlation analysis
    lam2_vals = [r["lambda2"] for r in results]
    ss_drifts = [r["avg_steady_state_drift"] for r in results]
    conv_rates = [r["avg_convergence_rate"] for r in results]

    # Pearson correlation λ₂ vs drift (expect negative)
    lam2_drift_corr = _pearson(lam2_vals, ss_drifts)
    # Pearson correlation λ₂ vs convergence (expect positive)
    lam2_conv_corr = _pearson(lam2_vals, conv_rates)

    print(f"\n{'=' * 60}")
    print("HYPOTHESIS ANALYSIS")
    print(f"{'=' * 60}")
    print(f"  λ₂ ↔ steady-state drift correlation: {lam2_drift_corr:+.4f}")
    print(f"  λ₂ ↔ convergence rate correlation:   {lam2_conv_corr:+.4f}")

    hypothesis1 = lam2_drift_corr < -0.3  # higher λ₂ → lower drift
    hypothesis2 = lam2_conv_corr > 0.3    # higher λ₂ → higher convergence

    print(f"\n  H1: Higher λ₂ → lower drift: {'SUPPORTED' if hypothesis1 else 'NOT SUPPORTED'}")
    print(f"  H2: Higher λ₂ → faster convergence: {'SUPPORTED' if hypothesis2 else 'NOT SUPPORTED'}")

    # Non-Laman analysis
    non_laman = [r for r in results if not r["is_laman"]]
    laman = [r for r in results if r["is_laman"]]

    print(f"\n{'=' * 60}")
    print("LAMAN RELAXATION ANALYSIS")
    print(f"{'=' * 60}")
    if laman:
        laman_avg_drift = sum(r["avg_steady_state_drift"] for r in laman) / len(laman)
        print(f"  Laman topologies ({[r['topology'] for r in laman]}): avg SS drift = {laman_avg_drift:.6f}")
    if non_laman:
        nl_avg_drift = sum(r["avg_steady_state_drift"] for r in non_laman) / len(non_laman)
        nl_converged = [r for r in non_laman if r["avg_convergence_rate"] > 0.5]
        print(f"  Non-Laman topologies ({[r['topology'] for r in non_laman]}): avg SS drift = {nl_avg_drift:.6f}")
        if nl_converged:
            print(f"  Non-Laman topologies that converge well: {[r['topology'] for r in nl_converged]}")
            print(f"  → PTP CAN work without Laman rigidity!")

    # Key findings
    key_findings = []

    if hypothesis1 and hypothesis2:
        key_findings.append("HYPOTHESIS CONFIRMED: Higher λ₂ → faster convergence AND lower steady-state drift. "
                            "PTP compounds the spectral advantage of well-connected topologies.")
    elif hypothesis1:
        key_findings.append("PARTIAL SUPPORT: Higher λ₂ → lower drift, but convergence rate not strongly correlated.")
    elif hypothesis2:
        key_findings.append("PARTIAL SUPPORT: Higher λ₂ → faster convergence, but drift not strongly correlated.")
    else:
        key_findings.append("HYPOTHESIS NOT SUPPORTED: λ₂ does not strongly predict PTP performance.")

    # Spectral gap insight
    high_gap = [r for r in results if r["lambda2"] > 1.0]
    low_gap = [r for r in results if r["lambda2"] < 0.5]
    if high_gap and low_gap:
        hg_drift = sum(r["avg_steady_state_drift"] for r in high_gap) / len(high_gap)
        lg_drift = sum(r["avg_steady_state_drift"] for r in low_gap) / len(low_gap)
        key_findings.append(f"High λ₂ (>{1.0}) avg drift: {hg_drift:.6f} vs Low λ₂ (<{0.5}) avg drift: {lg_drift:.6f}. "
                            f"Ratio: {lg_drift/hg_drift:.1f}× worse for low-connectivity graphs.")

    # Rigidity relaxation
    if non_laman:
        nl_work = [r for r in non_laman if r["avg_convergence_rate"] >= 0.8]
        if nl_work:
            key_findings.append(f"PTP converges on non-Laman topologies: {[r['topology'] for r in nl_work]}. "
                                "Rigidity is NOT required for PTP clock sync — spectral connectivity is the key.")
        else:
            key_findings.append("Non-Laman topologies show degraded PTP performance. "
                                "Laman rigidity may provide structural benefits beyond spectral properties.")

    # Condition number analysis
    cond_vs_drift = [(r["condition_number"] if r["condition_number"] != "inf" else 999, 
                      r["avg_steady_state_drift"]) for r in results]
    cond_corr = _pearson([c for c, _ in cond_vs_drift], [d for _, d in cond_vs_drift])
    key_findings.append(f"Condition number (λₙ/λ₂) ↔ drift correlation: {cond_corr:+.4f}. "
                        f"{'Well-conditioned graphs perform better.' if cond_corr > 0.3 else 'Condition number less important than raw λ₂.'}")

    elapsed = round(time.time() - start_time, 1)

    output = {
        "experiment": 27,
        "title": "Spectral-PTP Coupling",
        "description": "Does Laplacian eigenvalue structure affect PTP correction quality?",
        "N": N,
        "latency": LATENCY,
        "max_ticks": MAX_TICKS,
        "n_trials": N_TRIALS,
        "warmup_ticks": WARMUP,
        "topologies_tested": list(topologies.keys()),
        "results": results,
        "correlations": {
            "lambda2_vs_drift": round(lam2_drift_corr, 4),
            "lambda2_vs_convergence": round(lam2_conv_corr, 4),
        },
        "hypothesis": {
            "statement": "Higher λ₂ → faster convergence AND lower steady-state drift",
            "h1_higher_lam2_lower_drift": hypothesis1,
            "h2_higher_lam2_faster_convergence": hypothesis2,
            "overall_supported": hypothesis1 and hypothesis2,
        },
        "laman_relaxation": {
            "laman_topologies": [r["topology"] for r in laman],
            "non_laman_topologies": [r["topology"] for r in non_laman],
            "non_laman_converge_well": [r["topology"] for r in non_laman if r["avg_convergence_rate"] >= 0.8],
            "rigidity_required": not any(r["avg_convergence_rate"] >= 0.8 for r in non_laman),
        },
        "key_findings": key_findings,
        "elapsed_seconds": elapsed,
    }

    os.makedirs("experiments/results", exist_ok=True)
    out_path = "experiments/results/experiment27_spectral_ptp.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved → {out_path}")

    print(f"\n{'=' * 60}")
    print("KEY FINDINGS")
    print(f"{'=' * 60}")
    for i, f in enumerate(key_findings):
        print(f"  [{i + 1}] {f}")

    print(f"\nElapsed: {elapsed}s")
    return output


def _pearson(xs, ys):
    n = len(xs)
    if n < 2:
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    sx = sum((x - mx) ** 2 for x in xs)
    sy = sum((y - my) ** 2 for y in ys)
    if sx == 0 or sy == 0:
        return 0.0
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return cov / math.sqrt(sx * sy)


if __name__ == "__main__":
    run_experiment()
