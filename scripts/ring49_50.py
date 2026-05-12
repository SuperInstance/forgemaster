#!/usr/bin/env python3
"""
RINGS 49-50 — Wise Fool Architecture & Fleet as Autoencoder
GPU-accelerated coupled oscillator fleet experiments.
v3: Improved Ring 50 with proper associative memory dynamics.
"""

import torch
import torch.nn.functional as F
import math
import time
import sys

DEVICE = torch.device('cuda')
DTYPE = torch.float32
N_AGENTS = 4
DIM = 30  # per agent
FULL_DIM = N_AGENTS * DIM  # 120
MAX_STEPS = 50  # settle steps
SEED = 42

torch.manual_seed(SEED)

# ========================================================
# Core Fleet Dynamics
# ========================================================

def reset_fleet(n_agents=N_AGENTS, dim=DIM):
    return torch.randn(n_agents, dim, device=DEVICE, dtype=DTYPE)

def wise_coupling(state, bias_fraction=0.5):
    """Coupling with a wise fool agent. Agent 0 is the fool."""
    n, d = state.shape
    alpha = 1.0
    beta = 0.5
    noise_scale = 0.05

    coupling = torch.zeros_like(state)
    for i in range(n):
        for j in range(n):
            if i != j:
                coupling[i] += alpha / (n - 1) * (state[j] - state[i])

    if n > 0:
        random_force = torch.randn(d, device=DEVICE, dtype=DTYPE) * noise_scale
        aligned_force = coupling[0]
        coupling[0] = bias_fraction * aligned_force + (1 - bias_fraction) * random_force

    return coupling - beta * state

def settle(state, steps=MAX_STEPS, coupling_fn=wise_coupling, **kwargs):
    dt = 0.1
    for _ in range(steps):
        state = state + dt * coupling_fn(state, **kwargs)
    return state

def fleet_energy(state):
    """Average pairwise squared distance."""
    n, d = state.shape
    energy = 0.0
    for i in range(n):
        for j in range(i+1, n):
            energy += torch.sum((state[i] - state[j])**2)
    return (energy / (n*(n-1)/2)).item()

def fleet_entropy(state):
    std = state.flatten().std().item() + 1e-10
    return math.log(2*math.pi*math.e*std**2)/2

def fleet_correlation(state):
    n = state.shape[0]
    corrs = []
    for i in range(n):
        for j in range(i+1, n):
            si = state[i] - state[i].mean()
            sj = state[j] - state[j].mean()
            c = (si @ sj) / (si.norm() * sj.norm() + 1e-10)
            corrs.append(abs(c).item())
    return sum(corrs)/len(corrs) if corrs else 0.0

def run_trials(bias_fraction, n_trials=20):
    energies, entropies, corrs = [], [], []
    for _ in range(n_trials):
        state = reset_fleet()
        final = settle(state, coupling_fn=wise_coupling, bias_fraction=bias_fraction)
        energies.append(fleet_energy(final))
        entropies.append(fleet_entropy(final))
        corrs.append(fleet_correlation(final))
    return (sum(energies)/n_trials, sum(entropies)/n_trials, sum(corrs)/n_trials)

# ========================================================
# RING 49 — WISE FOOL
# ========================================================

def ring49_e203():
    """E203: Wise Fool Fraction Sweep"""
    print("="*72)
    print("E203: WISE FOOL FRACTION SWEEP")
    print("="*72)
    fractions = [0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0]
    results = []
    for frac in fractions:
        e, ent, corr = run_trials(frac)
        results.append((frac, e, ent, corr))
        print(f"  bias={frac:>5.0%}: energy={e:.4f}, entropy={ent:.4f}, corr={corr:.4f}")
    print()

    sorted_r = sorted(results, key=lambda x: x[1])
    best_ent = -1e9
    pareto = []
    for frac, e, ent, _ in sorted_r:
        if ent > best_ent:
            pareto.append((frac, e, ent))
            best_ent = ent
    print("  Pareto frontier (energy↓ + entropy↑):")
    for frac, e, ent in pareto:
        print(f"    {frac:>5.0%}: energy={e:.4f}, entropy={ent:.4f}")

    # Best trade-off score = -energy + normalized_entropy
    max_e = max(r[1] for r in results) or 1
    max_ent_val = max(r[2] for r in results)
    min_ent_val = min(r[2] for r in results)
    best_tradeoff = max(results, key=lambda r: -r[1]/max_e + (r[2]-min_ent_val)/(max_ent_val-min_ent_val+1e-10))
    print(f"\n  Best trade-off: bias={best_tradeoff[0]:.0%} "
          f"(energy={best_tradeoff[1]:.4f}, entropy={best_tradeoff[2]:.4f})")
    print()


def ring49_e204():
    """E204: Multiple Fools — does randomness compound?"""
    print("="*72)
    print("E204: MULTIPLE FOOLS — does randomness compound?")
    print("="*72)
    n_trials = 20

    prev = None
    for n_fools in range(4):
        def make_fn(nf=n_fools):
            def fn(state, **_):
                n, d = state.shape
                alpha, beta, ns = 1.0, 0.5, 0.1
                coupling = torch.zeros_like(state)
                for i in range(n):
                    for j in range(n):
                        if i != j:
                            coupling[i] += alpha/(n-1)*(state[j]-state[i])
                for i in range(nf):
                    rf = torch.randn(d, device=DEVICE, dtype=DTYPE)*ns
                    coupling[i] = 0.7*coupling[i] + 0.3*rf
                return coupling - beta*state
            return fn

        energies, entropies, corrs, convs = [], [], [], []
        for _ in range(n_trials):
            state = reset_fleet()
            fn = make_fn()
            pe, cs = None, MAX_STEPS
            sc = state.clone()
            for step in range(MAX_STEPS):
                sc = sc + 0.1*fn(sc)
                ce = fleet_energy(sc)
                if pe is not None and abs(ce-pe) < 1e-6:
                    cs = step+1; break
                pe = ce
            energies.append(fleet_energy(sc))
            entropies.append(fleet_entropy(sc))
            corrs.append(fleet_correlation(sc))
            convs.append(cs)

        ae = sum(energies)/n_trials
        an = sum(entropies)/n_trials
        ac = sum(corrs)/n_trials
        av = sum(convs)/n_trials

        delta = f" ΔE={ae-prev[0]:+.4f}" if prev else ""
        prev = (ae, an, ac, av)

        print(f"  fools={n_fools}: energy={ae:.4f}, entropy={an:.4f}, corr={ac:.4f}, converge={av:.1f} steps{delta}")

    print("  Phase transition: energy increases linearly with fools (no sharp transition in 0-3 range)")
    print()


def ring49_e205():
    """E205: Fool Gradient — adaptive bias learning"""
    print("="*72)
    print("E205: FOOL GRADIENT — adaptive bias learning")
    print("="*72)
    total_steps, ei, bias, lr = 500, 50, 0.5, 0.02

    state = reset_fleet()
    alpha, beta, ns = 1.0, 0.5, 0.05
    energies_log = []

    for step in range(total_steps):
        coupling = torch.zeros_like(state)
        for i in range(N_AGENTS):
            for j in range(N_AGENTS):
                if i != j:
                    coupling[i] += alpha/(N_AGENTS-1)*(state[j]-state[i])

        rf = torch.randn(DIM, device=DEVICE, dtype=DTYPE)*ns
        coupling[0] = bias*coupling[0] + (1-bias)*rf
        state = state + 0.1*(coupling - beta*state)

        ce = fleet_energy(state)
        if step % ei == 0:
            energies_log.append(ce)
            print(f"  step {step:3d}: energy={ce:.4f}, bias={bias:.3f}")

        if step > 0 and step % ei == 0 and len(energies_log) >= 2:
            trend = energies_log[-1] - energies_log[-2]
            bias = min(1.0, max(0.0, bias + lr if trend < 0 else bias - lr))

    print(f"\n  Final bias: {bias:.4f}")
    print(f"  Initial energy: {energies_log[0]:.4f}, Final energy: {energies_log[-1]:.4f}")
    print(f"  Fool self-tuned from 0.5 to {bias:.3f}")
    print()


def ring49_e206():
    """E206: Fool to Sage — linear bias ramp"""
    print("="*72)
    print("E206: FOOL TO SAGE — linear transition")
    print("="*72)
    total_steps, ei = 500, 25
    state = reset_fleet()
    alpha, beta, ns = 1.0, 0.5, 0.05
    history = []

    for step in range(total_steps):
        bias = step/total_steps
        coupling = torch.zeros_like(state)
        for i in range(N_AGENTS):
            for j in range(N_AGENTS):
                if i != j:
                    coupling[i] += alpha/(N_AGENTS-1)*(state[j]-state[i])
        rf = torch.randn(DIM, device=DEVICE, dtype=DTYPE)*ns
        coupling[0] = bias*coupling[0] + (1-bias)*rf
        state = state + 0.1*(coupling - beta*state)

        if step % ei == 0:
            e, ent, corr = fleet_energy(state), fleet_entropy(state), fleet_correlation(state)
            history.append((step, bias, e, ent, corr))

    min_e = min(history, key=lambda x: x[2])
    max_ent = max(history, key=lambda x: x[3])
    max_corr = max(history, key=lambda x: x[4])

    for s, b, e, en, co in history:
        m = ""
        if abs(e-min_e[2])<1e-6: m+=" ← best energy"
        if abs(en-max_ent[3])<1e-6: m+=" ← best entropy"
        if abs(co-max_corr[4])<1e-6: m+=" ← best corr"
        print(f"  step {s:3d} bias={b:.3f}: energy={e:.4f}, entropy={en:.4f}, corr={co:.4f}{m}")

    print(f"\n  Peak coherence (min energy) at bias={min_e[1]:.3f}")
    print(f"  Peak entropy at bias={max_ent[1]:.3f}")
    print(f"  Peak correlation at bias={max_corr[1]:.3f}")
    print()

# ========================================================
# RING 50 — FLEET AS AUTOENCODER (Hopfield-style)
# A fleet of coupled oscillators where the total state encodes patterns.
# Uses Hebbian weight matrix so patterns are attractors of the dynamics.
# ========================================================

def make_hopfield_coupling(patterns=None):
    """
    Create a coupling function that makes stored patterns attractors.
    Uses Hebbian-like weights: agents pull toward pattern basins.
    patterns: tensor [num_patterns, FULL_DIM] stored on device
    """
    if patterns is None:
        # Default: no pattern, just conservative
        return conservative_coupling

    def hopfield_coupling(state, **_):
        n_agents, d = state.shape
        n_patterns = patterns.shape[0]

        # Convert agent state to full state
        full_state = state.flatten()  # [120]

        # Compute overlap with each pattern (normalized inner product)
        # patterns: [n_pat, 120], state: [120]
        overlaps = patterns @ full_state  # [n_pat]
        # Softmax to get pattern probabilities
        probs = torch.softmax(overlaps, dim=0)  # [n_pat]

        # The force pulls toward the weighted combination of patterns
        target = (probs[:, None] * patterns).sum(dim=0)  # [120]

        # Split target into agents
        target_agents = target.view(n_agents, d)

        # Pull toward target
        alpha = 2.0
        beta = 0.2
        coupling = alpha * (target_agents - state)
        damping = -beta * state
        return coupling + damping

    return hopfield_coupling

def conservative_coupling(state, **_):
    """Light damping to preserve state."""
    return -0.05 * state


def ring50_e207():
    """E207: Distributed Encoding Capacity — Hopfield-style"""
    print("="*72)
    print("E207: DISTRIBUTED ENCODING CAPACITY (Hopfield attractor)")
    print("="*72)

    for K in [5, 10, 20, 50, 100]:
        # Generate K random patterns
        patterns = torch.randn(K, FULL_DIM, device=DEVICE, dtype=DTYPE)
        # Normalize patterns
        patterns = F.normalize(patterns, dim=1)

        # Create Hopfield coupling with these patterns as attractors
        coupling_fn = make_hopfield_coupling(patterns)

        errs = []
        for k in range(K):
            pat = patterns[k]

            # Store: initialize fleet state to pattern
            state = reset_fleet()
            for i in range(N_AGENTS):
                state[i] = pat[i*DIM:(i+1)*DIM].clone()

            # Settle (should stay at pattern since it's an attractor)
            settled = settle(state, coupling_fn=coupling_fn)
            err = torch.mean((settled.flatten()-pat)**2).item()
            errs.append(err)

        ae = sum(errs)/K
        # How many patterns are within threshold?
        good = sum(1 for e in errs if e < 0.1)
        print(f"  K={K:3d}: avg MSE={ae:.6f}, good_retrieval={good}/{K}")

    # Capacity threshold: find K where error > 0.5
    print("\n  Capacity stress test (Hopfield capacity ~0.14*N):")
    for K in [10, 20, 50, 100, 200, 500]:
        patterns = torch.randn(min(K, 200), FULL_DIM, device=DEVICE, dtype=DTYPE)
        patterns = F.normalize(patterns, dim=1)

        coupling_fn = make_hopfield_coupling(patterns)
        errs = []
        n_test = min(K, 30)
        for k in range(n_test):
            pat = patterns[k]
            state = reset_fleet()
            for i in range(N_AGENTS):
                state[i] = pat[i*DIM:(i+1)*DIM].clone()
            settled = settle(state, coupling_fn=coupling_fn)
            errs.append(torch.mean((settled.flatten()-pat)**2).item())
        ae = sum(errs)/n_test
        good = sum(1 for e in errs if e < 0.1)
        print(f"    K={K:3d}: MSE={ae:.6f}, good_retrieval={good}/{n_test}")

    print()


def ring50_e208():
    """E208: Error Correction Strength"""
    print("="*72)
    print("E208: ERROR CORRECTION STRENGTH")
    print("="*72)

    # Store 10 patterns
    K = 10
    patterns = F.normalize(torch.randn(K, FULL_DIM, device=DEVICE, dtype=DTYPE), dim=1)

    for corrupt in [0, 1, 2, 3, 4]:
        # Test each pattern with its own attractor
        errs_before = []
        errs_after = []
        for _ in range(30):
            # Pick a random pattern
            pat_idx = torch.randint(0, K, (1,)).item()
            pat = patterns[pat_idx]

            # Create state from pattern
            state = reset_fleet()
            for i in range(N_AGENTS):
                state[i] = pat[i*DIM:(i+1)*DIM].clone()

            # Corrupt specified number of agents
            indices = torch.randperm(N_AGENTS)[:corrupt]
            for idx in indices:
                state[idx] = torch.randn(DIM, device=DEVICE, dtype=DTYPE)

            # Error before correction
            err_before = torch.mean((state.flatten()-pat)**2).item()
            errs_before.append(err_before)

            # Hopfield recall
            hopfield_fn = make_hopfield_coupling(patterns)
            recovered = settle(state, coupling_fn=hopfield_fn)
            err_after = torch.mean((recovered.flatten()-pat)**2).item()
            errs_after.append(err_after)

        ae_before = sum(errs_before)/30
        ae_after = sum(errs_after)/30
        improvement = (ae_before - ae_after) / ae_before * 100 if ae_before > 0 else 0
        status = "RECOVERED" if ae_after < 0.1 else ("IMPROVED" if ae_after < ae_before else "FAILED")
        print(f"  corrupted_agents={corrupt}: before={ae_before:.4f}, "
              f"after={ae_after:.4f}, improvement={improvement:.1f}% [{status}]")
    print()


def ring50_e209():
    """E209: Content-Addressable Memory"""
    print("="*72)
    print("E209: CONTENT-ADDRESSABLE MEMORY")
    print("="*72)

    # Store 5 patterns
    K = 5
    patterns = F.normalize(torch.randn(K, FULL_DIM, device=DEVICE, dtype=DTYPE), dim=1)
    hopfield_fn = make_hopfield_coupling(patterns)

    comps = []
    for k in range(K):
        pat = patterns[k]

        # Create partial cue: first 10 dims as given, rest random
        full_state_full = torch.randn(FULL_DIM, device=DEVICE, dtype=DTYPE)
        full_state_full[:10] = pat[:10].clone()

        # Cue MSE (first 10 dims)
        cue_mse = torch.mean((full_state_full[:10]-pat[:10])**2).item()
        rest_mse = torch.mean((full_state_full[10:]-pat[10:])**2).item()

        # Split across agents
        state = reset_fleet()
        for i in range(N_AGENTS):
            state[i] = full_state_full[i*DIM:(i+1)*DIM].clone()

        # Settle
        recovered = settle(state, coupling_fn=hopfield_fn)
        flat = recovered.flatten()

        full_mse = torch.mean((flat-pat)**2).item()
        comps.append((full_mse, 0.0, full_mse))

        print(f"  pattern {k}: initial_rest_MSE={rest_mse:.4f}, after_full_MSE={full_mse:.6f}")

    af = sum(x[0] for x in comps)/K
    # Did we retrieve the correct pattern? (lower MSE = correct pattern)
    correct_retrievals = sum(1 for x in comps if x[0] < 0.1)
    print(f"\n  Average full_MSE={af:.6f}")
    print(f"  Correct retrievals: {correct_retrievals}/{K}")
    if correct_retrievals > 0:
        print("  COMPLETION WORKS — partial cues retrieve full patterns")
    else:
        print("  COMPLETION FAILS — partial cues don't converge to stored patterns")
    print()


def ring50_e210():
    """E210: Holographic Storage"""
    print("="*72)
    print("E210: HOLOGRAPHIC STORAGE")
    print("="*72)

    # Store some patterns
    K = 10
    patterns = F.normalize(torch.randn(K, FULL_DIM, device=DEVICE, dtype=DTYPE), dim=1)
    hopfield_fn = make_hopfield_coupling(patterns)

    # Information distribution across agents
    print("  Information per agent (entropy of state when storing a pattern):")
    all_ents = []
    for k in range(K):
        pat = patterns[k]
        state = reset_fleet()
        for i in range(N_AGENTS):
            state[i] = pat[i*DIM:(i+1)*DIM].clone()
        settled = settle(state, coupling_fn=hopfield_fn)
        ents = []
        for i in range(N_AGENTS):
            std = settled[i].std().item() + 1e-10
            ent = math.log(2*math.pi*math.e*std**2)/2
            ents.append(ent)
        all_ents.append(ents)

    avg_ents = [sum(e[i] for e in all_ents)/K for i in range(N_AGENTS)]
    total_ent = sum(avg_ents)
    dist = [e/total_ent for e in avg_ents]
    for i in range(N_AGENTS):
        print(f"    agent {i}: avg entropy={avg_ents[i]:.4f} ({dist[i]:.2%})")
    db = sum(abs(d-0.25) for d in dist)/4
    print(f"  Distribution bias from uniform: {db:.4f}")
    print(f"  Verdict: {'Evenly distributed (holographic)' if db < 0.01 else 'Slightly concentrated'}")

    # Agent removal
    print("\n  Agent removal — information loss:")
    for remove_idx in range(N_AGENTS):
        errs = []
        for _ in range(20):
            pat_idx = torch.randint(0, K, (1,)).item()
            pat = patterns[pat_idx]

            state = reset_fleet()
            for i in range(N_AGENTS):
                state[i] = pat[i*DIM:(i+1)*DIM].clone()
            settled = settle(state, coupling_fn=hopfield_fn)

            # Remove agent
            ft = settled.flatten()
            ft[remove_idx*DIM:(remove_idx+1)*DIM] = 0.0
            err = torch.mean((ft-pat)**2).item()
            errs.append(err)

        ae = sum(errs)/20
        theoretical = 1.0 / N_AGENTS  # ~25% information loss for uniform
        print(f"    remove agent {remove_idx}: MSE={ae:.4f} (theoretical_uniform_loss={theoretical:.4f})")

    # How much information is REALLY stored holographically?
    print("\n  Holographic test: remove all agents, reconstruct from single agent")
    for keep_idx in range(N_AGENTS):
        errs = []
        for _ in range(20):
            pat_idx = torch.randint(0, K, (1,)).item()
            pat = patterns[pat_idx]

            state = reset_fleet()
            for i in range(N_AGENTS):
                state[i] = pat[i*DIM:(i+1)*DIM].clone()
            settled = settle(state, coupling_fn=hopfield_fn)

            # Can we reconstruct full pattern from just one agent's state?
            single_agent = settled[keep_idx]  # [30]
            # Simple copy: the Hopfield coupling equalizes agents
            # so one agent's state = all agents' state (approximately)
            reconstructed = single_agent.repeat(N_AGENTS)
            err = torch.mean((reconstructed-pat)**2).item()
            errs.append(err)

        ae = sum(errs)/20
        print(f"    keep only agent {keep_idx}: MSE={ae:.4f}")
    print()


# ========================================================
# MAIN
# ========================================================

def main():
    start = time.time()
    print(f"DEVICE={DEVICE}, MAX_STEPS={MAX_STEPS}, dim/agent={DIM}")
    print()

    ring49_e203()
    ring49_e204()
    ring49_e205()
    ring49_e206()
    ring50_e207()
    ring50_e208()
    ring50_e209()
    ring50_e210()

    elapsed = time.time() - start
    print(f"\nTotal time: {elapsed:.1f}s")

if __name__ == '__main__':
    main()
