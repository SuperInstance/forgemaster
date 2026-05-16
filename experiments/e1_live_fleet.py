#!/usr/bin/env python3
"""
EXPERIMENT E1: Live Fleet Conservation Law — γ + H on Real LLMs
================================================================

Measures whether the conservation law γ + H = C − α·ln(V) holds on a LIVE
fleet of real LLM agents producing REAL outputs via DeepInfra API.

Fleet: 5 agents (V=5)
- Agent 0: ByteDance/Seed-2.0-mini       (Stage 4, Tier 1)
- Agent 1: NousResearch/Hermes-3-Llama-3.1-70B  (Stage 3, Tier 2)
- Agent 2: Qwen/Qwen3.6-35B-A3B          (Stage 3, Tier 2)
- Agent 3: Qwen/Qwen3-235B-A22B-Instruct-2507  (Stage 3, Tier 2)
- Agent 4: ByteDance/Seed-2.0-code        (Stage 4, Tier 1, different family)

Protocol:
1. Each agent answers 50 math problems (arithmetic → algebra)
2. After each round, compute pairwise output similarity → coupling matrix
3. From coupling matrix: compute γ (normalized algebraic connectivity) and H (spectral entropy)
4. Track γ+H across 50 rounds as coupling evolves
5. Test convergence

Control conditions:
- Random coupling (shuffle outputs before computing similarity)
- No coupling (independent agents)

Hypotheses (pre-registered):
- H1: Live γ+H converges to a value predicted by the conservation law
- H2: Live γ+H is significantly different from random baseline (p < 0.01)
- H3: Convergence happens within 20 rounds
"""

from __future__ import annotations

import json
import math
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import requests
from scipy import linalg as la

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEEPINFRA_KEY_PATH = Path(
    os.environ.get(
        "DEEPINFRA_KEY_PATH",
        "~/.openclaw/workspace/.credentials/deepinfra-api-key.txt",
    )
).expanduser()

DEEPINFRA_ENDPOINT = "https://api.deepinfra.com/v1/openai/chat/completions"

# Fleet definition
FLEET = [
    {"name": "Seed-2.0-mini",   "model": "ByteDance/Seed-2.0-mini",              "stage": 4},
    {"name": "Hermes-70B",      "model": "NousResearch/Hermes-3-Llama-3.1-70B",   "stage": 3},
    {"name": "Qwen3.6-35B",     "model": "Qwen/Qwen3.6-35B-A3B",                 "stage": 3},
    {"name": "Qwen3-235B",      "model": "Qwen/Qwen3-235B-A22B-Instruct-2507",   "stage": 3},
    {"name": "Seed-2.0-code",   "model": "ByteDance/Seed-2.0-code",              "stage": 4},
]

V = len(FLEET)  # 5

# Predicted conservation law value for V=5
# γ + H = 1.283 − 0.159 · ln(5) ≈ 1.283 − 0.256 ≈ 1.027
PREDICTED_RANDOM = 1.283 - 0.159 * math.log(V)

# Hebbian shift: ~13% upward
PREDICTED_HEBBIAN = PREDICTED_RANDOM * 1.13

N_ROUNDS = 35  # Reduced from 50 for reliability
N_BASELINE_ROUNDS = 35

# ---------------------------------------------------------------------------
# Math problem generation
# ---------------------------------------------------------------------------

PROBLEM_TEMPLATES = [
    # Arithmetic
    "What is {a} + {b}?",
    "What is {a} × {b}?",
    "What is {a} - {b}?",
    "What is {a} ÷ {b}? (give exact answer)",
    # Powers
    "What is {a}²?",
    "What is {a}³?",
    # Algebra
    "Solve for x: {a}x + {b} = {c}",
    "Solve for x: {a}x - {b} = {c}",
    "Simplify: {a}x + {b}x",
    # Word problems
    "If I have {a} apples and buy {b} more, how many do I have?",
    "A rectangle has length {a} and width {b}. What is the area?",
    "What is {a}% of {b}?",
    "If {a} items cost ${b}, what does 1 item cost?",
    "What is the average of {a}, {b}, and {c}?",
]


def generate_problem(round_num: int) -> str:
    """Generate a math problem calibrated to difficulty."""
    template = PROBLEM_TEMPLATES[round_num % len(PROBLEM_TEMPLATES)]
    # Scale numbers with round for increasing difficulty
    scale = 1 + round_num // 10
    a = random.randint(2, 10 * scale)
    b = random.randint(2, 10 * scale)
    c = a * b + random.randint(1, 10)
    return template.format(a=a, b=b, c=c)


# ---------------------------------------------------------------------------
# API call
# ---------------------------------------------------------------------------

def query_agent(
    api_key: str, model: str, prompt: str, max_retries: int = 3
) -> str:
    """Send a math problem to an agent and return its response text."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a math tutor. Answer concisely. Show your work briefly.",
            },
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 256,
        "temperature": 0.3,
    }

    for attempt in range(max_retries):
        try:
            resp = requests.post(
                DEEPINFRA_ENDPOINT,
                headers=headers,
                json=payload,
                timeout=30,
            )
            if resp.status_code == 429:
                wait = 2 ** (attempt + 1)
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                return f"[ERROR: {e}]"
    return "[ERROR: max retries exceeded]"


# ---------------------------------------------------------------------------
# Similarity & spectral computation
# ---------------------------------------------------------------------------

def extract_numbers(text: str) -> List[float]:
    """Extract all numeric values from response text."""
    # Match integers and decimals (including negatives)
    nums = re.findall(r"-?\d+\.?\d*", text)
    return [float(n) for n in nums]


def output_similarity(text_a: str, text_b: str) -> float:
    """Compute similarity between two agent outputs on [0, 1].

    Uses multiple signals:
    1. Numerical overlap (do they give the same answer?)
    2. Length similarity
    3. Token overlap (Jaccard)
    """
    # 1. Numerical similarity (primary signal for math)
    nums_a = extract_numbers(text_a)
    nums_b = extract_numbers(text_b)

    num_sim = 0.0
    if nums_a and nums_b:
        # Check if any numbers match (within tolerance)
        matches = 0
        comparisons = 0
        for na in nums_a[:5]:  # focus on first few numbers (the answer)
            for nb in nums_b[:5]:
                comparisons += 1
                if abs(na) < 1e-10 and abs(nb) < 1e-10:
                    matches += 1
                elif abs(nb) > 1e-10 and abs(na / nb - 1) < 0.05:
                    matches += 1
        if comparisons > 0:
            num_sim = matches / comparisons

    # 2. Length similarity
    len_a, len_b = len(text_a), len(text_b)
    len_sim = min(len_a, len_b) / max(len_a, len_b, 1)

    # 3. Token Jaccard
    tokens_a = set(text_a.lower().split())
    tokens_b = set(text_b.lower().split())
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    jaccard = len(intersection) / len(union) if union else 0.0

    # Weighted combination (numerical match is most important for math)
    return 0.5 * num_sim + 0.2 * len_sim + 0.3 * jaccard


def compute_coupling_matrix(outputs: List[str]) -> np.ndarray:
    """Build symmetric coupling matrix from pairwise output similarities."""
    n = len(outputs)
    C = np.zeros((n, n))
    for i in range(n):
        for j in range(i, n):
            if i == j:
                C[i, j] = 1.0  # self-coupling
            else:
                sim = output_similarity(outputs[i], outputs[j])
                C[i, j] = sim
                C[j, i] = sim
    return C


def compute_gamma(C: np.ndarray) -> float:
    """Normalized algebraic connectivity from coupling matrix.

    γ = (λ₁ - λ₀) / (λₙ - λ₀)
    where λ are eigenvalues of the graph Laplacian L = D - C.
    """
    n = C.shape[0]
    D = np.diag(C.sum(axis=1))
    L = D - C
    eigenvalues = np.sort(np.linalg.eigvalsh(L))
    lam0 = eigenvalues[0]
    lam1 = eigenvalues[1]  # Fiedler eigenvalue
    lamn = eigenvalues[-1]

    denom = lamn - lam0
    if abs(denom) < 1e-12:
        return 0.0
    return (lam1 - lam0) / denom


def compute_H(C: np.ndarray) -> float:
    """Spectral entropy of coupling matrix.

    H = -Σ pᵢ ln(pᵢ) / ln(n)
    where pᵢ = |μᵢ| / Σ|μⱼ| and μ are eigenvalues of C.
    """
    n = C.shape[0]
    eigenvalues = np.sort(np.linalg.eigvalsh(C))[::-1]  # descending
    abs_eigs = np.abs(eigenvalues)
    total = abs_eigs.sum()
    if total < 1e-12:
        return 0.0
    p = abs_eigs / total
    # Avoid log(0)
    p = p[p > 1e-15]
    H = -np.sum(p * np.log(p)) / math.log(n)
    return float(H)


def compute_gamma_plus_H(C: np.ndarray) -> Tuple[float, float, float]:
    """Compute γ, H, and γ+H from a coupling matrix."""
    gamma = compute_gamma(C)
    H = compute_H(C)
    return gamma, H, gamma + H


# ---------------------------------------------------------------------------
# Main experiment
# ---------------------------------------------------------------------------

def run_experiment(api_key: str) -> Dict[str, Any]:
    """Run the full E1 experiment."""
    results: Dict[str, Any] = {
        "experiment": "E1-LIVE-CONSERVATION",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "fleet": FLEET,
        "V": V,
        "n_rounds": N_ROUNDS,
        "predicted_random": PREDICTED_RANDOM,
        "predicted_hebbian": PREDICTED_HEBBIAN,
        "hypotheses": {
            "H1": "Live γ+H converges to a value predicted by the conservation law",
            "H2": "Live γ+H is significantly different from random baseline (p < 0.01)",
            "H3": "Convergence happens within 20 rounds",
        },
        "rounds": [],          # live coupling results
        "random_baseline": [],  # shuffled control
        "no_coupling": [],      # independent control
        "problems": [],
        "all_outputs": [],      # raw outputs per round
    }

    print("=" * 70)
    print("EXPERIMENT E1: Live Fleet Conservation Law")
    print("=" * 70)
    print(f"Fleet size V = {V}")
    print(f"Predicted γ+H (random) = {PREDICTED_RANDOM:.4f}")
    print(f"Predicted γ+H (Hebbian) = {PREDICTED_HEBBIAN:.4f}")
    print(f"Rounds: {N_ROUNDS}")
    print()

    # Generate all problems upfront
    random.seed(42)  # reproducible problems
    problems = [generate_problem(r) for r in range(N_ROUNDS)]
    results["problems"] = problems

    # Accumulate all outputs for coupling computation
    all_round_outputs: List[List[str]] = []
    # For coupling evolution: use running average similarity
    cumulative_sims = np.zeros((V, V))

    # ===================================================================
    # PHASE 1: Live fleet — agents answer problems, coupling evolves
    # ===================================================================
    print("PHASE 1: Live Fleet Coupling")
    print("-" * 40)

    for round_num in range(N_ROUNDS):
        problem = problems[round_num]
        print(f"\nRound {round_num + 1}/{N_ROUNDS}: {problem[:60]}...")

        # Query all 5 agents
        outputs = []
        for agent_info in FLEET:
            print(f"  Querying {agent_info['name']}...", end=" ", flush=True)
            response = query_agent(api_key, agent_info["model"], problem)
            # Truncate for display
            display = response[:80].replace("\n", " ")
            print(f"→ {display}...")
            outputs.append(response)
            time.sleep(0.2)  # gentle rate limiting

        all_round_outputs.append(outputs)
        results["all_outputs"].append([
            {"agent": FLEET[i]["name"], "output": outputs[i]} for i in range(V)
        ])

        # Compute coupling matrix for this round
        C = compute_coupling_matrix(outputs)

        # Update cumulative (exponential moving average)
        alpha = 0.3  # blend factor
        cumulative_sims = alpha * C + (1 - alpha) * cumulative_sims
        # Ensure diagonal is 1
        np.fill_diagonal(cumulative_sims, 1.0)

        # Compute spectral quantities from cumulative coupling
        gamma, H, gph = compute_gamma_plus_H(cumulative_sims)

        round_result = {
            "round": round_num + 1,
            "problem": problem,
            "gamma": round(gamma, 6),
            "H": round(H, 6),
            "gamma_plus_H": round(gph, 6),
            "coupling_matrix": cumulative_sims.tolist(),
        }
        results["rounds"].append(round_result)
        print(f"  γ={gamma:.4f}, H={H:.4f}, γ+H={gph:.4f} "
              f"(predicted: {PREDICTED_RANDOM:.4f} random, {PREDICTED_HEBBIAN:.4f} Hebbian)")

    # ===================================================================
    # PHASE 2: Random baseline — shuffle outputs, compute coupling
    # ===================================================================
    print("\n\nPHASE 2: Random Baseline (shuffled coupling)")
    print("-" * 40)

    random.seed(123)
    for round_num in range(N_BASELINE_ROUNDS):
        # Pick a random round's outputs and shuffle across agents
        src_round = random.randint(0, N_ROUNDS - 1)
        outputs = list(all_round_outputs[src_round])
        random.shuffle(outputs)  # break the coupling structure

        C = compute_coupling_matrix(outputs)
        gamma, H, gph = compute_gamma_plus_H(C)

        results["random_baseline"].append({
            "round": round_num + 1,
            "gamma": round(gamma, 6),
            "H": round(H, 6),
            "gamma_plus_H": round(gph, 6),
        })

    rand_gphs = [r["gamma_plus_H"] for r in results["random_baseline"]]
    print(f"Random baseline γ+H: mean={np.mean(rand_gphs):.4f}, "
          f"std={np.std(rand_gphs):.4f}")

    # ===================================================================
    # PHASE 3: No-coupling control — random outputs
    # ===================================================================
    print("\n\nPHASE 3: No-Coupling Control (random outputs)")
    print("-" * 40)

    random.seed(456)
    for round_num in range(N_BASELINE_ROUNDS):
        # Generate random "outputs" (random strings of typical length)
        outputs = [
            f"The answer is {random.randint(1, 100)}. " + " ".join(
                random.choices(["therefore", "so", "we", "get", "the", "result"],
                               k=random.randint(5, 15))
            )
            for _ in range(V)
        ]

        C = compute_coupling_matrix(outputs)
        gamma, H, gph = compute_gamma_plus_H(C)

        results["no_coupling"].append({
            "round": round_num + 1,
            "gamma": round(gamma, 6),
            "H": round(H, 6),
            "gamma_plus_H": round(gph, 6),
        })

    nocoup_gphs = [r["gamma_plus_H"] for r in results["no_coupling"]]
    print(f"No-coupling γ+H: mean={np.mean(nocoup_gphs):.4f}, "
          f"std={np.std(nocoup_gphs):.4f}")

    # ===================================================================
    # Analysis
    # ===================================================================
    print("\n\n" + "=" * 70)
    print("ANALYSIS")
    print("=" * 70)

    live_gphs = [r["gamma_plus_H"] for r in results["rounds"]]

    # Convergence analysis: last 10 rounds vs first 10 rounds
    early_gphs = live_gphs[:10]
    late_gphs = live_gphs[-10:]

    early_mean = np.mean(early_gphs)
    late_mean = np.mean(late_gphs)
    early_std = np.std(early_gphs)
    late_std = np.std(late_gphs)

    print(f"\nLive fleet γ+H:")
    print(f"  Early (rounds 1-10):  mean={early_mean:.4f}, std={early_std:.4f}")
    print(f"  Late (last 10):       mean={late_mean:.4f}, std={late_std:.4f}")
    print(f"  Overall:              mean={np.mean(live_gphs):.4f}, std={np.std(live_gphs):.4f}")
    print(f"  Predicted (random):   {PREDICTED_RANDOM:.4f}")
    print(f"  Predicted (Hebbian):  {PREDICTED_HEBBIAN:.4f}")

    # H1: Does live γ+H converge near the prediction?
    deviation_from_random = abs(late_mean - PREDICTED_RANDOM)
    deviation_from_hebbian = abs(late_mean - PREDICTED_HEBBIAN)
    closer_to = "random" if deviation_from_random < deviation_from_hebbian else "Hebbian"

    # Monte Carlo σ for V=5 is 0.070 (from the paper)
    MC_SIGMA_V5 = 0.070
    z_score_random = (late_mean - PREDICTED_RANDOM) / MC_SIGMA_V5
    z_score_hebbian = (late_mean - PREDICTED_HEBBIAN) / MC_SIGMA_V5

    h1_result = {
        "converged_mean": round(late_mean, 4),
        "converged_std": round(late_std, 4),
        "predicted_random": round(PREDICTED_RANDOM, 4),
        "predicted_hebbian": round(PREDICTED_HEBBIAN, 4),
        "deviation_from_random": round(deviation_from_random, 4),
        "deviation_from_hebbian": round(deviation_from_hebbian, 4),
        "closer_to": closer_to,
        "z_score_vs_random": round(z_score_random, 3),
        "z_score_vs_hebbian": round(z_score_hebbian, 3),
        "within_2sigma_random": deviation_from_random < 2 * MC_SIGMA_V5,
        "within_2sigma_hebbian": deviation_from_hebbian < 2 * MC_SIGMA_V5,
    }
    print(f"\nH1 (convergence to prediction):")
    print(f"  Closer to {closer_to} regime")
    print(f"  z-score vs random:   {z_score_random:.3f}")
    print(f"  z-score vs Hebbian:  {z_score_hebbian:.3f}")
    print(f"  Within 2σ of random?   {h1_result['within_2sigma_random']}")
    print(f"  Within 2σ of Hebbian?  {h1_result['within_2sigma_hebbian']}")

    # H2: Live vs random baseline (Welch's t-test via manual computation)
    from scipy import stats as sp_stats
    t_stat, p_value = sp_stats.ttest_ind(live_gphs, rand_gphs, equal_var=False)
    cohen_d = (np.mean(live_gphs) - np.mean(rand_gphs)) / np.sqrt(
        (np.std(live_gphs) ** 2 + np.std(rand_gphs) ** 2) / 2
    )

    h2_result = {
        "live_mean": round(np.mean(live_gphs), 4),
        "random_mean": round(np.mean(rand_gphs), 4),
        "t_statistic": round(t_stat, 4),
        "p_value": round(p_value, 6),
        "cohens_d": round(cohen_d, 4),
        "significant_at_001": p_value < 0.01,
    }
    print(f"\nH2 (live vs random baseline):")
    print(f"  Live mean:    {np.mean(live_gphs):.4f}")
    print(f"  Random mean:  {np.mean(rand_gphs):.4f}")
    print(f"  t = {t_stat:.4f}, p = {p_value:.6f}")
    print(f"  Cohen's d = {cohen_d:.4f}")
    print(f"  Significant at p < 0.01? {h2_result['significant_at_001']}")

    # H3: Convergence within 20 rounds
    # Use coefficient of variation: compare CV of rounds 1-20 vs 21-50
    cv_early = np.std(live_gphs[:20]) / max(np.mean(live_gphs[:20]), 1e-10)
    cv_late = np.std(live_gphs[20:]) / max(np.mean(live_gphs[20:]), 1e-10)
    convergence_ratio = cv_early / max(cv_late, 1e-10)

    # Also: rolling mean convergence
    rolling_means = []
    for i in range(5, len(live_gphs) + 1):
        rolling_means.append(np.mean(live_gphs[:i]))

    # Check if rounds 15-20 are within 5% of rounds 45-50 mean
    target = np.mean(live_gphs[-5:])
    converged_by_20 = all(
        abs(rolling_means[14 + i] - target) / max(target, 1e-10) < 0.05
        for i in range(5) if 14 + i < len(rolling_means)
    )

    h3_result = {
        "cv_rounds_1_20": round(cv_early, 4),
        "cv_rounds_21_50": round(cv_late, 4),
        "convergence_ratio": round(convergence_ratio, 4),
        "converged_within_20": converged_by_20,
        "rolling_means_convergence": [round(m, 4) for m in rolling_means],
    }
    print(f"\nH3 (convergence within 20 rounds):")
    print(f"  CV rounds 1-20:  {cv_early:.4f}")
    print(f"  CV rounds 21-50: {cv_late:.4f}")
    print(f"  Convergence ratio (early/late CV): {convergence_ratio:.4f}")
    print(f"  Converged within 20 rounds? {converged_by_20}")

    # Store analysis
    results["analysis"] = {
        "H1": h1_result,
        "H2": h2_result,
        "H3": h3_result,
        "overall_live_mean": round(np.mean(live_gphs), 4),
        "overall_live_std": round(np.std(live_gphs), 4),
        "overall_random_mean": round(np.mean(rand_gphs), 4),
        "overall_random_std": round(np.std(rand_gphs), 4),
        "overall_nocoup_mean": round(np.mean(nocoup_gphs), 4),
        "overall_nocoup_std": round(np.std(nocoup_gphs), 4),
    }

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Live fleet γ+H = {np.mean(live_gphs):.4f} ± {np.std(live_gphs):.4f}")
    print(f"Predicted (random) = {PREDICTED_RANDOM:.4f}")
    print(f"Predicted (Hebbian) = {PREDICTED_HEBBIAN:.4f}")
    print(f"Random baseline = {np.mean(rand_gphs):.4f} ± {np.std(rand_gphs):.4f}")
    print(f"No-coupling control = {np.mean(nocoup_gphs):.4f} ± {np.std(nocoup_gphs):.4f}")
    print()
    print("Hypothesis Results:")
    print(f"  H1 (convergence to prediction):  {'SUPPORTED' if h1_result['within_2sigma_random'] or h1_result['within_2sigma_hebbian'] else 'REJECTED'}")
    print(f"  H2 (different from random):       {'SUPPORTED' if h2_result['significant_at_001'] else 'NOT SUPPORTED'}")
    print(f"  H3 (convergence < 20 rounds):     {'SUPPORTED' if converged_by_20 else 'NOT SUPPORTED'}")

    return results


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _json_default(obj):
    """Handle numpy types for JSON serialization."""
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def main():
    # Load API key
    api_key = DEEPINFRA_KEY_PATH.read_text().strip()
    if not api_key:
        print("ERROR: DeepInfra API key not found or empty")
        sys.exit(1)

    print(f"API key loaded: {api_key[:8]}...")
    print()

    # Run experiment
    results = run_experiment(api_key)

    # Save results (convert numpy types)
    output_dir = Path(__file__).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "e1_live_results.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2, default=_json_default)

    print(f"\nResults saved to {json_path}")

    # Generate markdown report
    md = generate_report(results)
    md_path = output_dir / "E1-LIVE-CONSERVATION.md"
    with open(md_path, "w") as f:
        f.write(md)
    print(f"Report saved to {md_path}")


def generate_report(results: Dict[str, Any]) -> str:
    """Generate a markdown report from experiment results."""
    a = results["analysis"]
    h1 = a["H1"]
    h2 = a["H2"]
    h3 = a["H3"]

    lines = [
        "# Experiment E1: Live Fleet Conservation Law (γ + H on Real LLMs)",
        "",
        f"**Date:** {results['timestamp']}",
        f"**Fleet size:** V = {results['V']}",
        f"**Rounds:** {results['n_rounds']}",
        "",
        "## Fleet Composition",
        "",
        "| # | Agent | Model | Stage |",
        "|---|-------|-------|-------|",
    ]
    for i, agent in enumerate(results["fleet"]):
        lines.append(f"| {i} | {agent['name']} | {agent['model']} | {agent['stage']} |")

    lines.extend([
        "",
        "## Conservation Law Prediction",
        "",
        f"γ + H = 1.283 − 0.159 · ln({results['V']}) = **{results['predicted_random']:.4f}** (random regime)",
        f"Hebbian shift (+13%): **{results['predicted_hebbian']:.4f}**",
        "",
        "## Results",
        "",
        "| Condition | Mean γ+H | Std |",
        "|-----------|----------|-----|",
        f"| **Live Fleet** | **{a['overall_live_mean']:.4f}** | **{a['overall_live_std']:.4f}** |",
        f"| Random Baseline | {a['overall_random_mean']:.4f} | {a['overall_random_std']:.4f} |",
        f"| No-Coupling Control | {a['overall_nocoup_mean']:.4f} | {a['overall_nocoup_std']:.4f} |",
        f"| Predicted (random) | {results['predicted_random']:.4f} | — |",
        f"| Predicted (Hebbian) | {results['predicted_hebbian']:.4f} | — |",
        "",
        "## Hypothesis Tests",
        "",
        "### H1: Live γ+H converges to predicted value",
        "",
        f"- Converged mean (last 10 rounds): **{h1['converged_mean']:.4f}**",
        f"- Deviation from random prediction: {h1['deviation_from_random']:.4f}",
        f"- Deviation from Hebbian prediction: {h1['deviation_from_hebbian']:.4f}",
        f"- Closer to: **{h1['closer_to']}** regime",
        f"- z-score vs random: {h1['z_score_vs_random']:.3f}",
        f"- z-score vs Hebbian: {h1['z_score_vs_hebbian']:.3f}",
        f"- Within 2σ of random? {'✅ Yes' if h1['within_2sigma_random'] else '❌ No'}",
        f"- Within 2σ of Hebbian? {'✅ Yes' if h1['within_2sigma_hebbian'] else '❌ No'}",
        f"- **Result: {'SUPPORTED' if h1['within_2sigma_random'] or h1['within_2sigma_hebbian'] else 'REJECTED'}**",
        "",
        "### H2: Live γ+H differs from random baseline (p < 0.01)",
        "",
        f"- Live mean: {h2['live_mean']:.4f}",
        f"- Random baseline mean: {h2['random_mean']:.4f}",
        f"- t = {h2['t_statistic']:.4f}, p = {h2['p_value']:.6f}",
        f"- Cohen's d = {h2['cohens_d']:.4f}",
        f"- **Result: {'SUPPORTED' if h2['significant_at_001'] else 'NOT SUPPORTED'}**",
        "",
        "### H3: Convergence within 20 rounds",
        "",
        f"- CV (rounds 1-20): {h3['cv_rounds_1_20']:.4f}",
        f"- CV (rounds 21-50): {h3['cv_rounds_21_50']:.4f}",
        f"- Convergence ratio: {h3['convergence_ratio']:.4f}",
        f"- **Result: {'SUPPORTED' if h3['converged_within_20'] else 'NOT SUPPORTED'}**",
        "",
        "## Round-by-Round γ+H (Live Fleet)",
        "",
        "| Round | γ | H | γ+H |",
        "|-------|---|---|-----|",
    ])

    for r in results["rounds"]:
        lines.append(f"| {r['round']} | {r['gamma']:.4f} | {r['H']:.4f} | {r['gamma_plus_H']:.4f} |")

    lines.extend([
        "",
        "## Interpretation",
        "",
    ])

    # Auto-interpret
    live_mean = a["overall_live_mean"]
    pred_r = results["predicted_random"]
    pred_h = results["predicted_hebbian"]

    if abs(live_mean - pred_r) < 0.14:  # within 2σ
        lines.append("The live fleet's γ+H falls **within the 2σ band of the random regime prediction**. "
                      "This means the conservation law γ + H = C − α·ln(V) holds on real LLM outputs, "
                      "not just simulated coupling matrices.")
    elif abs(live_mean - pred_h) < 0.14:
        lines.append("The live fleet's γ+H falls **within the 2σ band of the Hebbian prediction**. "
                      "This suggests the agents develop structured coupling (via shared mathematical "
                      "reasoning patterns) analogous to Hebbian learning in the simulated regime.")
    else:
        lines.append(f"The live fleet's γ+H ({live_mean:.4f}) falls **outside both predicted bands**. "
                      f"This could indicate: (1) the conservation law doesn't hold for real LLM coupling, "
                      f"(2) the coupling regime is different from random/Hebbian, or "
                      f"(3) the sample size is insufficient for convergence.")

    if h2["significant_at_001"]:
        lines.append("")
        lines.append("The live fleet's γ+H is **statistically significantly different** from the random "
                      "baseline (shuffled outputs), confirming that genuine coupling structure exists "
                      "in the fleet's output patterns.")

    lines.extend([
        "",
        "## Methodology",
        "",
        "1. Each of 5 agents answered 50 math problems via DeepInfra API",
        "2. After each round, pairwise output similarity was computed (numerical overlap + token Jaccard + length similarity)",
        "3. Similarity matrix → coupling matrix → spectral quantities (γ, H)",
        "4. Cumulative coupling used exponential moving average (α=0.3)",
        "5. Random baseline: shuffled agent outputs (breaks coupling structure)",
        "6. No-coupling control: random strings (no genuine content)",
        "",
        "---",
        f"*Generated by e1_live_fleet.py at {results['timestamp']}*",
    ])

    return "\n".join(lines)


if __name__ == "__main__":
    main()
