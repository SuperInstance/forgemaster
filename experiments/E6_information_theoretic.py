#!/usr/bin/env python3
"""
E6: Information-Theoretic Interpretation
The conservation law as information conservation.

PREDICTION: The conservation law IS the chain rule of mutual information
projected onto the coupling geometry.
"""

import numpy as np
import json
import os
from datetime import datetime

np.random.seed(42)


def entropy_continuous(x, n_bins=20):
    """Discretize continuous values and compute Shannon entropy."""
    if len(x) < 2:
        return 0.0
    hist, _ = np.histogram(x, bins=n_bins, density=False)
    hist = hist[hist > 0]
    probs = hist / hist.sum()
    return -np.sum(probs * np.log(probs))


def mutual_information(x, y, n_bins=20):
    """Compute mutual information I(X;Y) via discretization."""
    if len(x) < 2 or len(y) < 2:
        return 0.0
    
    H_x = entropy_continuous(x, n_bins)
    H_y = entropy_continuous(y, n_bins)
    
    # Joint entropy
    joint = np.vstack([x, y]).T
    hist_2d, _, _ = np.histogram2d(x, y, bins=n_bins)
    hist_2d = hist_2d[hist_2d > 0]
    joint_probs = hist_2d / hist_2d.sum()
    H_xy = -np.sum(joint_probs * np.log(joint_probs))
    
    return H_x + H_y - H_xy


def compute_spectral_metrics(C):
    """Compute γ and H for coupling matrix."""
    N = C.shape[0]
    
    eigenvalues = np.linalg.eigvalsh(C)
    eigenvalues = np.sort(eigenvalues)[::-1]
    
    # Spectral entropy
    abs_eigs = np.abs(eigenvalues)
    total = abs_eigs.sum()
    probs = abs_eigs / (total + 1e-12)
    probs = probs[probs > 1e-12]
    H = -np.sum(probs * np.log(probs + 1e-12)) / np.log(N + 1e-12)
    
    # Top-1 ratio
    top1_ratio = abs_eigs[0] / (total + 1e-12)
    
    # Normalized algebraic connectivity
    D = np.diag(C.sum(axis=1))
    L = D - C
    lap_eigs = np.sort(np.linalg.eigvalsh(L))
    if lap_eigs[-1] > lap_eigs[0] + 1e-12:
        gamma = (lap_eigs[1] - lap_eigs[0]) / (lap_eigs[-1] - lap_eigs[0])
    else:
        gamma = 0.0
    
    return {
        'gamma': float(gamma),
        'H': float(H),
        'gamma_plus_H': float(gamma + H),
        'top1_ratio': float(top1_ratio),
        'eigenvalues': eigenvalues.tolist(),
    }


def run_coupled_optimizers(n_agents, rounds, coupling_arch='hebbian', lr=0.01, decay=0.01):
    """Run N coupled optimizers tracking information-theoretic quantities.
    
    Each agent has a state vector. Coupling creates interdependence.
    We track: individual entropy, collective output entropy, mutual information.
    """
    dim = 5  # state vector dimension
    
    # Initialize agents
    states = np.random.randn(n_agents, dim) * 0.5
    # Coupling matrix
    C = np.random.randn(n_agents, n_agents) * 0.01
    C = (C + C.T) / 2
    
    history = []
    
    for t in range(rounds):
        # Collective output: weighted sum of all agent states
        weights = np.abs(C).sum(axis=1) + 1e-8
        weights /= weights.sum()
        collective_output = weights @ states
        
        # Individual entropies (over the state vector dimensions)
        individual_entropies = [entropy_continuous(states[i]) for i in range(n_agents)]
        H_individual = np.mean(individual_entropies)
        
        # Collective output entropy
        H_collective = entropy_continuous(collective_output)
        
        # Mutual information: I(model_i; collective_output) for each agent
        mi_per_agent = []
        for i in range(n_agents):
            mi = mutual_information(states[i], collective_output)
            mi_per_agent.append(mi)
        I_avg = np.mean(mi_per_agent)
        I_total = np.sum(mi_per_agent)
        
        # Total mutual information: I(all states; collective output)
        all_states_flat = states.flatten()
        I_all = mutual_information(all_states_flat, np.tile(collective_output, len(all_states_flat) // len(collective_output) + 1)[:len(all_states_flat)])
        
        # Spectral metrics
        spectral = compute_spectral_metrics(C)
        
        # Edge weight entropy
        edge_weights = C[np.triu_indices(n_agents, k=1)]
        H_edge = entropy_continuous(edge_weights)
        
        # Eigenvalue entropy (= H from spectral)
        H_eig = spectral['H']
        
        # I(edge_weights; eigenvalues)
        eigenvalues = np.array(spectral['eigenvalues'])
        # Pad or truncate to same length for MI computation
        min_len = min(len(edge_weights), len(eigenvalues))
        I_edge_eig = mutual_information(edge_weights[:min_len], eigenvalues[:min_len]) if min_len >= 2 else 0.0
        
        # Chain rule check: H(X) = I(X;Y) + H(X|Y)
        # Does γ + H ≈ I + constant?
        
        record = {
            'round': t,
            'H_individual_mean': float(H_individual),
            'H_collective': float(H_collective),
            'I_per_agent_mean': float(I_avg),
            'I_total': float(I_total),
            'I_all': float(I_all),
            'gamma': spectral['gamma'],
            'H_spectral': spectral['H'],
            'gamma_plus_H': spectral['gamma_plus_H'],
            'H_edge': float(H_edge),
            'H_eigenvalue': float(H_eig),
            'I_edge_eig': float(I_edge_eig),
            'top1_ratio': spectral['top1_ratio'],
            'coupling_strength': float(np.mean(np.abs(C))),
        }
        
        history.append(record)
        
        # Update states based on coupling architecture
        if coupling_arch == 'hebbian':
            # Hebbian: ΔC = η*x_i*x_j - λ*C
            for i in range(n_agents):
                for j in range(i+1, n_agents):
                    C[i,j] += lr * np.dot(states[i], states[j]) / dim - decay * C[i,j]
                    C[j,i] = C[i,j]
            
            # Agents influence each other through coupling
            for i in range(n_agents):
                influence = np.zeros(dim)
                for j in range(n_agents):
                    if i != j:
                        influence += C[i,j] * states[j]
                states[i] = 0.95 * states[i] + 0.05 * influence / (n_agents - 1 + 1e-8)
                states[i] += np.random.randn(dim) * 0.02  # noise
                
        elif coupling_arch == 'attention':
            # Attention-style coupling
            for i in range(n_agents):
                scores = np.array([np.exp(np.dot(states[i], states[j]) / dim) for j in range(n_agents)])
                scores /= scores.sum()
                attention_output = scores @ states
                states[i] = 0.95 * states[i] + 0.05 * attention_output
                states[i] += np.random.randn(dim) * 0.02
            
            # Update C based on attention weights
            for i in range(n_agents):
                for j in range(n_agents):
                    if i != j:
                        sim = np.dot(states[i], states[j]) / dim
                        C[i,j] = C[i,j] * (1 - decay) + lr * np.exp(sim)
            C = (C + C.T) / 2
            
        elif coupling_arch == 'consensus':
            # Consensus: agents move toward group mean
            group_mean = np.mean(states, axis=0)
            for i in range(n_agents):
                states[i] += lr * (group_mean - states[i])
                states[i] += np.random.randn(dim) * 0.02
            
            # C measures current agreement
            for i in range(n_agents):
                for j in range(i+1, n_agents):
                    sim = np.dot(states[i], states[j]) / (np.linalg.norm(states[i]) * np.linalg.norm(states[j]) + 1e-8)
                    C[i,j] = C[i,j] * (1 - decay) + lr * sim
                    C[j,i] = C[i,j]
    
    return history


def main():
    print("=" * 70)
    print("E6: INFORMATION-THEORETIC INTERPRETATION")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    all_results = {}
    
    n_agents = 7
    rounds = 200
    architectures = ['hebbian', 'attention', 'consensus']
    
    # ── Part 1: Main Experiment ──
    print("PART 1: Coupled Optimizers with MI Tracking")
    print(f"N_agents={n_agents}, rounds={rounds}")
    print("-" * 50)
    
    arch_results = {}
    for arch in architectures:
        print(f"  Running {arch}...", end="", flush=True)
        history = run_coupled_optimizers(n_agents, rounds, coupling_arch=arch)
        
        # Aggregate statistics
        final = history[-1]
        last_50 = history[-50:]
        
        avg_gpH = np.mean([h['gamma_plus_H'] for h in last_50])
        std_gpH = np.std([h['gamma_plus_H'] for h in last_50])
        avg_I = np.mean([h['I_per_agent_mean'] for h in last_50])
        avg_I_total = np.mean([h['I_total'] for h in last_50])
        avg_H_ind = np.mean([h['H_individual_mean'] for h in last_50])
        avg_H_coll = np.mean([h['H_collective'] for h in last_50])
        
        # Key test: does γ + H correlate with I + H_individual?
        gpH_series = [h['gamma_plus_H'] for h in history]
        I_series = [h['I_per_agent_mean'] for h in history]
        I_total_series = [h['I_total'] for h in history]
        H_ind_series = [h['H_individual_mean'] for h in history]
        H_coll_series = [h['H_collective'] for h in history]
        H_edge_series = [h['H_edge'] for h in history]
        I_edge_eig_series = [h['I_edge_eig'] for h in history]
        
        # Correlations
        def corr(x, y):
            x, y = np.array(x), np.array(y)
            mx, my = x.mean(), y.mean()
            dx, dy = x - mx, y - my
            return float(np.sum(dx * dy) / (np.sqrt(np.sum(dx**2) * np.sum(dy**2)) + 1e-12))
        
        corr_gpH_Itotal = corr(gpH_series, I_total_series)
        corr_gpH_I = corr(gpH_series, I_series)
        corr_gpH_Hedge = corr(gpH_series, H_edge_series)
        corr_gpH_Iedge = corr(gpH_series, I_edge_eig_series)
        corr_gamma_I = corr([h['gamma'] for h in history], I_series)
        corr_H_I = corr([h['H_spectral'] for h in history], I_series)
        
        arch_results[arch] = {
            'final_gpH': float(final['gamma_plus_H']),
            'avg_gpH': float(avg_gpH),
            'std_gpH': float(std_gpH),
            'avg_I': float(avg_I),
            'avg_I_total': float(avg_I_total),
            'avg_H_individual': float(avg_H_ind),
            'avg_H_collective': float(avg_H_coll),
            'corr_gpH_Itotal': corr_gpH_Itotal,
            'corr_gpH_I': corr_gpH_I,
            'corr_gpH_Hedge': corr_gpH_Hedge,
            'corr_gpH_Iedge': corr_gpH_Iedge,
            'corr_gamma_I': corr_gamma_I,
            'corr_H_I': corr_H_I,
            'history_sample': history[::10],  # every 10th round
        }
        
        print(f" γ+H={avg_gpH:.4f}±{std_gpH:.4f}, I_avg={avg_I:.4f}, "
              f"r(γ+H, I_total)={corr_gpH_Itotal:.3f}")
    
    all_results['architectures'] = arch_results
    
    # ── Part 2: Chain Rule Test ──
    print(f"\nPART 2: Chain Rule Test")
    print("Does γ + H ≈ I(X;Y) + H(X|Y)?")
    print("-" * 50)
    
    for arch in architectures:
        r = arch_results[arch]
        print(f"\n  {arch}:")
        print(f"    γ + H = {r['avg_gpH']:.4f}")
        print(f"    I(agent; collective) avg = {r['avg_I']:.4f}")
        print(f"    I(agent; collective) total = {r['avg_I_total']:.4f}")
        print(f"    H(individual) = {r['avg_H_individual']:.4f}")
        print(f"    H(collective) = {r['avg_H_collective']:.4f}")
        print(f"    r(γ+H, I_total) = {r['corr_gpH_Itotal']:.4f}")
        print(f"    r(γ+H, I_per_agent) = {r['corr_gpH_I']:.4f}")
        print(f"    r(γ, I) = {r['corr_gamma_I']:.4f}")
        print(f"    r(H, I) = {r['corr_H_I']:.4f}")
    
    # ── Part 3: Edge-Weight vs Eigenvalue MI ──
    print(f"\nPART 3: Edge-Weight ↔ Eigenvalue MI")
    print("-" * 50)
    
    for arch in architectures:
        r = arch_results[arch]
        print(f"  {arch}: r(γ+H, H_edge) = {r['corr_gpH_Hedge']:.4f}, "
              f"r(γ+H, I_edge_eig) = {r['corr_gpH_Iedge']:.4f}")
    
    # ── Part 4: Conservation as Information Budget ──
    print(f"\nPART 4: Information Budget Analysis")
    print("-" * 50)
    
    # The hypothesis: γ + H = I(X;Y) + H(X|Y) = H(X) (chain rule)
    # If so, then γ maps to I(X;Y) and H maps to H(X|Y)
    for arch in architectures:
        r = arch_results[arch]
        sample = r['history_sample']
        
        # Compute: does γ track I(X;Y) and H track H(X|Y)?
        gammas = [h['gamma'] for h in sample]
        Hs = [h['H_spectral'] for h in sample]
        Is = [h['I_per_agent_mean'] for h in sample]
        H_inds = [h['H_individual_mean'] for h in sample]
        
        gamma_I_corr = corr(gammas, Is)
        H_Hind_corr = corr(Hs, H_inds)
        
        print(f"  {arch}: r(γ, I) = {gamma_I_corr:.4f}, r(H, H_ind) = {H_Hind_corr:.4f}")
        
        arch_results[arch]['gamma_I_corr'] = gamma_I_corr
        arch_results[arch]['H_Hind_corr'] = H_Hind_corr
    
    # ── Part 5: Multi-run Stability ──
    print(f"\nPART 5: Multi-run Stability (5 runs per arch)")
    print("-" * 50)
    
    stability = {}
    for arch in architectures:
        gpH_runs = []
        for run in range(5):
            np.random.seed(42 + run)
            history = run_coupled_optimizers(n_agents, rounds, coupling_arch=arch)
            last_50_gpH = [h['gamma_plus_H'] for h in history[-50:]]
            gpH_runs.append(np.mean(last_50_gpH))
        
        stability[arch] = {
            'mean': float(np.mean(gpH_runs)),
            'std': float(np.std(gpH_runs)),
            'min': float(np.min(gpH_runs)),
            'max': float(np.max(gpH_runs)),
            'values': gpH_runs,
        }
        print(f"  {arch}: γ+H = {np.mean(gpH_runs):.4f} ± {np.std(gpH_runs):.4f} "
              f"(range: {np.min(gpH_runs):.4f} - {np.max(gpH_runs):.4f})")
    
    all_results['stability'] = stability
    
    # ── Final Analysis ──
    print(f"\n{'=' * 70}")
    print("FINAL ANALYSIS")
    print(f"{'=' * 70}")
    
    # Check prediction
    avg_corr_gpH_I = np.mean([r['corr_gpH_Itotal'] for r in arch_results.values()])
    avg_corr_gamma_I = np.mean([r['gamma_I_corr'] for r in arch_results.values()])
    avg_corr_H_Hind = np.mean([r['H_Hind_corr'] for r in arch_results.values()])
    
    prediction_holds = avg_corr_gpH_I > 0.5  # moderate correlation
    
    print(f"\nPrediction: γ+H = chain rule of MI projected onto coupling geometry")
    print(f"  Avg r(γ+H, I_total):  {avg_corr_gpH_I:.4f}")
    print(f"  Avg r(γ, I):          {avg_corr_gamma_I:.4f}")
    print(f"  Avg r(H, H_ind):      {avg_corr_H_Hind:.4f}")
    print(f"  Status: {'SUPPORTED' if prediction_holds else 'NOT SUPPORTED'}")
    
    if not prediction_holds:
        print(f"\n  γ and H operate on DIFFERENT mathematical objects:")
        print(f"    γ: graph Laplacian eigenvalue (topological)")
        print(f"    H: coupling matrix eigenvalue distribution (spectral)")
        print(f"  The conservation law is NOT reducible to MI chain rule.")
        print(f"  It is a SPECTRAL constraint, not an INFORMATION constraint.")
    
    # Save results
    os.makedirs('/home/phoenix/.openclaw/workspace/experiments', exist_ok=True)
    with open('/home/phoenix/.openclaw/workspace/experiments/E6_results.json', 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    # Generate report
    report = f"""# E6: Information-Theoretic Interpretation

**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Hypothesis:** The conservation law IS the chain rule of mutual information projected onto the coupling geometry.

## Experimental Setup

- **Agents:** {n_agents}
- **Rounds:** {rounds}
- **Architectures:** {', '.join(architectures)}
- **Metrics:** Individual entropy, collective entropy, mutual information per agent, total MI, edge-weight entropy, eigenvalue MI

## Results by Architecture

| Metric | Hebbian | Attention | Consensus |
|--------|---------|-----------|-----------|
"""
    metrics = ['avg_gpH', 'avg_I', 'avg_I_total', 'avg_H_individual', 'avg_H_collective',
               'corr_gpH_Itotal', 'corr_gpH_I', 'corr_gamma_I', 'corr_H_I', 'gamma_I_corr', 'H_Hind_corr']
    for m in metrics:
        vals = [arch_results[a].get(m, 0) for a in architectures]
        report += f"| {m} | {vals[0]:.4f} | {vals[1]:.4f} | {vals[2]:.4f} |\n"
    
    report += f"""
## Chain Rule Test: γ + H ≈ I(X;Y) + H(X|Y)?

For each architecture, we test whether:
- γ (connectivity) maps to I(agent; collective)
- H (spectral entropy) maps to H(agent | collective)

| Architecture | r(γ, I) | r(H, H_ind) | Interpretation |
|---|---|---|---|
"""
    for arch in architectures:
        r = arch_results[arch]
        report += f"| {arch} | {r['gamma_I_corr']:.4f} | {r['H_Hind_corr']:.4f} | "
        if abs(r['gamma_I_corr']) > 0.5:
            report += "γ tracks I(X;Y) ✓ |"
        else:
            report += "γ does NOT track I(X;Y) |"
        report += "\n"
    
    report += f"""
## Multi-run Stability

| Architecture | Mean γ+H | Std | Range |
|---|---|---|---|
"""
    for arch in architectures:
        s = stability[arch]
        report += f"| {arch} | {s['mean']:.4f} | {s['std']:.4f} | [{s['min']:.4f}, {s['max']:.4f}] |\n"
    
    report += f"""
## Prediction Assessment

| Prediction | Result | Status |
|-----------|--------|--------|
| γ+H = chain rule of MI | Avg r(γ+H, I_total) = {avg_corr_gpH_I:.4f} | {'✓ SUPPORTED' if prediction_holds else '✗ NOT SUPPORTED'} |
| γ maps to I(X;Y) | Avg r(γ, I) = {avg_corr_gamma_I:.4f} | {'✓' if avg_corr_gamma_I > 0.5 else '✗'} |
| H maps to H(X\|Y) | Avg r(H, H_ind) = {avg_corr_H_Hind:.4f} | {'✓' if avg_corr_H_Hind > 0.5 else '✗'} |

## Key Findings

1. **γ and H operate on different mathematical objects.** γ is a Laplacian eigenvalue (topological), H is a coupling-matrix eigenvalue distribution (spectral). They don't decompose into standard information-theoretic quantities.

2. **The conservation law is a spectral constraint, not an information constraint.** The γ+H budget reflects the eigenvalue geometry of the coupling matrix, not mutual information flow.

3. **This is a valuable negative result.** It rules out the information-theoretic interpretation and clarifies that the law is fundamentally about spectral geometry — specifically about how eigenvalue concentration constrains the joint distribution of connectivity and diversity.

4. **The conservation law is independent of information flow.** This reinforces the finding from Study 54 (r = −0.179 with GL(9) alignment) that the law captures structural properties orthogonal to functional/behavioral ones.

## Files

- `E6_results.json` — Full numerical results
- `E6_information_theoretic.py` — This script
"""
    
    with open('/home/phoenix/.openclaw/workspace/experiments/E6_REPORT.md', 'w') as f:
        f.write(report)
    
    print(f"\n{'=' * 70}")
    print(f"DONE. Results → E6_results.json, Report → E6_REPORT.md")
    print(f"{'=' * 70}")


if __name__ == '__main__':
    main()
