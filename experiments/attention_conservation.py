#!/usr/bin/env python3
"""
Attention Conservation Experiment
==================================
Tests whether γ+H = C - α·log(V) conservation law applies to LLM attention patterns.

Hypothesis: Stage 4 models (Seed-2.0-mini) show higher γ+H than Stage 3 models (Hermes-70B),
analogous to the Hebbian vs random regime shift in PLATO room coupling matrices.

Method:
1. Send identical prompts to multiple models via DeepInfra API
2. Extract attention-pattern proxies from logprobs/token probabilities
3. Build token co-occurrence matrix from generated sequences
4. Compute spectral properties (γ = spectral radius, H = Shannon entropy)
5. Test conservation: γ+H across different prompt types and models
"""

import json
import math
import os
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

# --- Configuration ---
DEEPINFRA_KEY_PATH = Path.home() / ".openclaw/workspace/.credentials/deepinfra-api-key.txt"
DEEPINFRA_ENDPOINT = "https://api.deepinfra.com/v1/openai/chat/completions"
RESULTS_PATH = Path("/home/phoenix/.openclaw/workspace/experiments/ATTENTION-CONSERVATION-RESULTS.md")

MODELS = {
    "Seed-2.0-mini": {"id": "ByteDance/Seed-2.0-mini", "stage": 4, "supports_logprobs": False},
    "Hermes-70B": {"id": "NousResearch/Hermes-3-Llama-3.1-70B", "stage": 3, "supports_logprobs": True},
    "Qwen3-235B": {"id": "Qwen/Qwen3-235B-A22B-Instruct-2507", "stage": 3, "supports_logprobs": True},
}

# Diverse prompt types to test conservation across contexts
PROMPTS = {
    "factual": "Explain the process of photosynthesis in exactly 3 sentences.",
    "creative": "Write a haiku about the sound of rain on a tin roof.",
    "reasoning": "If all A are B, and some B are C, can we conclude that some A are C? Explain briefly.",
    "code": "Write a Python function that computes the Fibonacci sequence using memoization.",
    "math": "Prove that the square root of 2 is irrational in 2-3 sentences.",
    "narrative": "Describe a sunset over the ocean using vivid sensory details.",
}

NUM_SAMPLES_PER_PROMPT = 3  # Multiple samples for statistical robustness
MAX_TOKENS = 150


def get_api_key():
    key = DEEPINFRA_KEY_PATH.read_text().strip()
    return key


def query_model(api_key, model_id, prompt, max_tokens=MAX_TOKENS, logprobs=True, top_logprobs=5):
    """Query a model via DeepInfra API, requesting logprobs."""
    import urllib.request
    import urllib.error

    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.7,
        "logprobs": logprobs,
        "top_logprobs": top_logprobs if logprobs else 0,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(DEEPINFRA_ENDPOINT, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"  HTTP {e.code}: {body[:200]}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  Request error: {e}", file=sys.stderr)
        return None


def extract_logprob_matrix(response):
    """
    Extract a token probability matrix from logprobs.
    Returns: (tokens, prob_matrix) where prob_matrix[i, j] = prob of token j at position i.
    """
    if not response or "choices" not in response:
        return None, None

    choice = response["choices"][0]
    logprobs_data = choice.get("logprobs")

    if not logprobs_data or not logprobs_data.get("content"):
        # Fallback: use token text only, no probability info
        text = choice.get("message", {}).get("content", "")
        return text.split(), None

    content_logprobs = logprobs_data["content"]

    # Build token list and probability distributions
    all_tokens = []
    all_top_probs = []  # list of dicts: {token_str: probability}

    for entry in content_logprobs:
        token = entry.get("token", "")
        all_tokens.append(token)

        top_logprobs = entry.get("top_logprobs", [])
        if top_logprobs:
            prob_dict = {}
            for item in top_logprobs:
                t = item.get("token", "")
                lp = item.get("logprob", -100)
                prob_dict[t] = math.exp(lp)  # Convert logprob to probability
            all_top_probs.append(prob_dict)
        else:
            all_top_probs.append({})

    return all_tokens, all_top_probs


def build_cooccurrence_matrix(tokens, window=2):
    """
    Build token co-occurrence matrix within a sliding window.
    This serves as a proxy for the attention/coupling matrix.
    """
    unique_tokens = list(dict.fromkeys(tokens))  # Preserve order, remove dupes
    token_idx = {t: i for i, t in enumerate(unique_tokens)}
    n = len(unique_tokens)

    matrix = np.zeros((n, n))
    for i, token in enumerate(tokens):
        for j in range(max(0, i - window), min(len(tokens), i + window + 1)):
            if i != j:
                ti, tj = token_idx[tokens[i]], token_idx[tokens[j]]
                matrix[ti, tj] += 1
                matrix[tj, ti] += 1  # Symmetric

    # Normalize to probability/stochastic matrix
    row_sums = matrix.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1
    matrix_norm = matrix / row_sums

    return matrix_norm, unique_tokens


def build_logprob_transition_matrix(top_probs_list):
    """
    Build a transition matrix from top logprobs across positions.
    Each position's probability distribution becomes a row/column in the matrix.
    """
    if not top_probs_list or all(len(p) == 0 for p in top_probs_list):
        return None, None

    # Collect all unique tokens across positions
    all_tokens = set()
    for prob_dict in top_probs_list:
        all_tokens.update(prob_dict.keys())
    all_tokens = sorted(all_tokens)
    token_idx = {t: i for i, t in enumerate(all_tokens)}
    n = len(all_tokens)

    if n == 0:
        return None, None

    # Build matrix: rows = output positions, cols = token vocabulary
    matrix = np.zeros((len(top_probs_list), n))
    for i, prob_dict in enumerate(top_probs_list):
        for token, prob in prob_dict.items():
            matrix[i, token_idx[token]] = prob

    # Create square coupling matrix: M^T @ M (token-token correlation)
    if matrix.shape[0] > 0 and n > 0:
        coupling = matrix.T @ matrix  # n x n
        # Normalize
        row_sums = coupling.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1
        coupling_norm = coupling / row_sums
        return coupling_norm, all_tokens

    return None, None


def compute_spectral_properties(matrix):
    """
    Compute spectral radius (γ) and Shannon entropy (H) of a matrix.
    """
    if matrix is None or matrix.size == 0:
        return None, None, None

    n = matrix.shape[0]
    if n < 2:
        return None, None, None

    # Spectral radius: largest absolute eigenvalue
    try:
        eigenvalues = np.linalg.eigvals(matrix)
        gamma = float(np.max(np.abs(eigenvalues)))
    except Exception:
        gamma = None

    # Shannon entropy of the flattened, normalized probability distribution
    flat = matrix.flatten()
    flat = flat[flat > 0]  # Remove zeros for log
    total = flat.sum()
    if total > 0:
        probs = flat / total
        entropy = float(-np.sum(probs * np.log2(probs)))
    else:
        entropy = None

    # Vocabulary size (effective dimensionality)
    V = n

    return gamma, entropy, V


def run_experiment():
    """Run the full attention conservation experiment."""
    api_key = get_api_key()
    all_results = {}

    print("=" * 70)
    print("ATTENTION CONSERVATION EXPERIMENT")
    print("Testing: γ + H = C - α·log(V) for LLM attention patterns")
    print("=" * 70)

    for model_name, model_info in MODELS.items():
        model_id = model_info["id"]
        print(f"\n{'='*60}")
        print(f"Model: {model_name} ({model_id})")
        print(f"{'='*60}")
        all_results[model_name] = {}

        for prompt_name, prompt in PROMPTS.items():
            print(f"\n  Prompt type: {prompt_name}")

            gammas = []
            entropies = []
            gammas_plus_H = []
            vocab_sizes = []
            sample_details = []

            for sample_idx in range(NUM_SAMPLES_PER_PROMPT):
                print(f"    Sample {sample_idx+1}/{NUM_SAMPLES_PER_PROMPT}...", end=" ", flush=True)

                response = query_model(api_key, model_id, prompt,
                                       logprobs=model_info.get("supports_logprobs", True),
                                       top_logprobs=5 if model_info.get("supports_logprobs", True) else 0)
                if not response:
                    print("FAILED")
                    continue

                tokens, top_probs = extract_logprob_matrix(response)
                if tokens is None:
                    print("No tokens")
                    continue

                # Method 1: Co-occurrence matrix
                cooc_matrix, cooc_tokens = build_cooccurrence_matrix(tokens, window=2)
                gamma_c, entropy_c, V_c = compute_spectral_properties(cooc_matrix)

                # Method 2: Logprob transition matrix
                gamma_l, entropy_l, V_l = None, None, None
                logprob_matrix = None
                if top_probs:
                    logprob_matrix, lp_tokens = build_logprob_transition_matrix(top_probs)
                    gamma_l, entropy_l, V_l = compute_spectral_properties(logprob_matrix)

                # Use logprob method if available, fallback to co-occurrence
                gamma = gamma_l if gamma_l is not None else gamma_c
                entropy = entropy_l if entropy_l is not None else entropy_c
                V = V_l if V_l is not None else V_c

                if gamma is not None and entropy is not None:
                    gpH = gamma + entropy
                    gammas.append(gamma)
                    entropies.append(entropy)
                    gammas_plus_H.append(gpH)
                    vocab_sizes.append(V)
                    print(f"γ={gamma:.4f} H={entropy:.4f} γ+H={gpH:.4f} V={V}")
                else:
                    print("Insufficient data")

                sample_details.append({
                    "sample": sample_idx,
                    "tokens": len(tokens) if tokens else 0,
                    "gamma_cooc": gamma_c,
                    "entropy_cooc": entropy_c,
                    "V_cooc": V_c,
                    "gamma_logprob": gamma_l,
                    "entropy_logprob": entropy_l,
                    "V_logprob": V_l,
                    "method_used": "logprob" if gamma_l is not None else "cooc",
                    "generated_text": response["choices"][0].get("message", {}).get("content", "")[:200],
                })

                time.sleep(1)  # Rate limiting

            # Aggregate results for this prompt type
            if gammas_plus_H:
                result = {
                    "mean_gamma": float(np.mean(gammas)),
                    "mean_entropy": float(np.mean(entropies)),
                    "mean_gamma_plus_H": float(np.mean(gammas_plus_H)),
                    "std_gamma_plus_H": float(np.std(gammas_plus_H)) if len(gammas_plus_H) > 1 else 0.0,
                    "mean_V": float(np.mean(vocab_sizes)),
                    "n_samples": len(gammas_plus_H),
                    "samples": sample_details,
                }
                all_results[model_name][prompt_name] = result
                print(f"  → Mean γ+H = {result['mean_gamma_plus_H']:.4f} ± {result['std_gamma_plus_H']:.4f}, V = {result['mean_V']:.0f}")
            else:
                print(f"  → No valid results")
                all_results[model_name][prompt_name] = None

            time.sleep(0.5)

    # --- Analysis ---
    print("\n" + "=" * 70)
    print("CROSS-MODEL ANALYSIS")
    print("=" * 70)

    # Compare Stage 4 (Seed-2.0-mini) vs Stage 3 (Hermes-70B)
    comparison = {}
    for prompt_name in PROMPTS:
        s4 = all_results.get("Seed-2.0-mini", {}).get(prompt_name)
        s3 = all_results.get("Hermes-70B", {}).get(prompt_name)

        if s4 and s3:
            diff = s4["mean_gamma_plus_H"] - s3["mean_gamma_plus_H"]
            ratio = s4["mean_gamma_plus_H"] / s3["mean_gamma_plus_H"] if s3["mean_gamma_plus_H"] != 0 else float('inf')
            comparison[prompt_name] = {
                "stage4_gpH": s4["mean_gamma_plus_H"],
                "stage3_gpH": s3["mean_gamma_plus_H"],
                "diff": diff,
                "ratio": ratio,
                "stage4_higher": diff > 0,
            }
            print(f"\n  {prompt_name}:")
            print(f"    Stage 4 (Seed-2.0-mini): γ+H = {s4['mean_gamma_plus_H']:.4f}")
            print(f"    Stage 3 (Hermes-70B):    γ+H = {s3['mean_gamma_plus_H']:.4f}")
            print(f"    Δ = {diff:+.4f} ({'Stage 4 higher' if diff > 0 else 'Stage 3 higher'})")

    # Conservation test: is γ+H constant across prompt types for each model?
    print("\n\nCONSERVATION TEST (γ+H across prompt types):")
    for model_name in MODELS:
        gpH_values = []
        for prompt_name in PROMPTS:
            r = all_results.get(model_name, {}).get(prompt_name)
            if r:
                gpH_values.append(r["mean_gamma_plus_H"])

        if len(gpH_values) > 1:
            mean_gpH = np.mean(gpH_values)
            std_gpH = np.std(gpH_values)
            cv = std_gpH / mean_gpH if mean_gpH > 0 else float('inf')
            print(f"\n  {model_name}:")
            print(f"    Mean γ+H = {mean_gpH:.4f}")
            print(f"    Std  γ+H = {std_gpH:.4f}")
            print(f"    CV   γ+H = {cv:.4f} ({'CONSERVED' if cv < 0.1 else 'NOT conserved'})")
            print(f"    Range: [{min(gpH_values):.4f}, {max(gpH_values):.4f}]")

    # Log-linear regression: γ+H = C - α·log(V)
    print("\n\nLOG-LINEAR REGRESSION TEST (γ+H vs log(V)):")
    for model_name in MODELS:
        gpH_list = []
        logV_list = []
        for prompt_name in PROMPTS:
            r = all_results.get(model_name, {}).get(prompt_name)
            if r and r["mean_V"] > 1:
                gpH_list.append(r["mean_gamma_plus_H"])
                logV_list.append(math.log(r["mean_V"]))

        if len(gpH_list) >= 3:
            gpH_arr = np.array(gpH_list)
            logV_arr = np.array(logV_list)
            # Linear regression: γ+H = C + α·log(V)
            A = np.vstack([np.ones(len(logV_arr)), logV_arr]).T
            coeffs, residuals, _, _ = np.linalg.lstsq(A, gpH_arr, rcond=None)
            C, alpha = coeffs
            predicted = C + alpha * logV_arr
            ss_res = np.sum((gpH_arr - predicted) ** 2)
            ss_tot = np.sum((gpH_arr - np.mean(gpH_arr)) ** 2)
            r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0

            print(f"\n  {model_name}:")
            print(f"    γ+H = {C:.4f} + ({alpha:.4f})·log(V)")
            print(f"    R² = {r_squared:.4f}")
            print(f"    Conservation constant C = {C:.4f}")

    return all_results, comparison


def write_results_markdown(results, comparison):
    """Write results to markdown file."""
    lines = []
    lines.append("# Attention Conservation Experiment Results")
    lines.append("")
    lines.append(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## Hypothesis")
    lines.append("")
    lines.append("The fleet discovered γ+H = 1.283 - 0.159·log(V) for PLATO room coupling matrices.")
    lines.append("Claude's synthesis hypothesizes an analogous conservation law for LLM attention matrices.")
    lines.append("Specifically, Stage 4 models should show higher γ+H than Stage 3 models (Hebbian shift).")
    lines.append("")
    lines.append("## Method")
    lines.append("")
    lines.append("1. Send identical prompts (6 types) to Seed-2.0-mini (Stage 4) and Hermes-70B (Stage 3)")
    lines.append("2. Extract attention-pattern proxies from logprobs/token probabilities")
    lines.append("3. Build token co-occurrence and logprob transition matrices")
    lines.append("4. Compute γ (spectral radius) and H (Shannon entropy)")
    lines.append("5. Test γ+H conservation across prompt types and models")
    lines.append("")

    # Per-model results
    for model_name in MODELS:
        model_info = MODELS[model_name]
        lines.append(f"## {model_name} (Stage {model_info['stage']})")
        lines.append("")
        lines.append("| Prompt Type | γ (spectral) | H (entropy) | γ+H | V (vocab) |")
        lines.append("|-------------|-------------|-------------|-----|-----------|")
        for prompt_name in PROMPTS:
            r = results.get(model_name, {}).get(prompt_name)
            if r:
                lines.append(f"| {prompt_name} | {r['mean_gamma']:.4f} | {r['mean_entropy']:.4f} | "
                             f"{r['mean_gamma_plus_H']:.4f} ± {r['std_gamma_plus_H']:.4f} | {r['mean_V']:.0f} |")
            else:
                lines.append(f"| {prompt_name} | — | — | — | — |")
        lines.append("")

    # Comparison
    lines.append("## Stage 4 vs Stage 3 Comparison")
    lines.append("")
    lines.append("| Prompt Type | Stage 4 γ+H | Stage 3 γ+H | Δ | Winner |")
    lines.append("|-------------|-------------|-------------|---|--------|")
    for prompt_name, comp in comparison.items():
        winner = "Stage 4 ✓" if comp["stage4_higher"] else "Stage 3"
        lines.append(f"| {prompt_name} | {comp['stage4_gpH']:.4f} | {comp['stage3_gpH']:.4f} | "
                     f"{comp['diff']:+.4f} | {winner} |")
    lines.append("")

    # Conservation analysis
    lines.append("## Conservation Analysis")
    lines.append("")
    lines.append("### γ+H Stability Across Prompt Types")
    lines.append("")
    for model_name in MODELS:
        gpH_values = []
        for prompt_name in PROMPTS:
            r = results.get(model_name, {}).get(prompt_name)
            if r:
                gpH_values.append(r["mean_gamma_plus_H"])
        if len(gpH_values) > 1:
            mean_gpH = np.mean(gpH_values)
            std_gpH = np.std(gpH_values)
            cv = std_gpH / mean_gpH if mean_gpH > 0 else float('inf')
            lines.append(f"**{model_name}**: Mean={mean_gpH:.4f}, Std={std_gpH:.4f}, CV={cv:.4f}")
            lines.append(f"- {'CONSERVED (CV < 0.1)' if cv < 0.1 else 'NOT conserved (CV ≥ 0.1)'}")
            lines.append("")

    # Log-linear regression
    lines.append("### Log-Linear Regression: γ+H = C + α·log(V)")
    lines.append("")
    for model_name in MODELS:
        gpH_list = []
        logV_list = []
        for prompt_name in PROMPTS:
            r = results.get(model_name, {}).get(prompt_name)
            if r and r["mean_V"] > 1:
                gpH_list.append(r["mean_gamma_plus_H"])
                logV_list.append(math.log(r["mean_V"]))
        if len(gpH_list) >= 3:
            gpH_arr = np.array(gpH_list)
            logV_arr = np.array(logV_list)
            A = np.vstack([np.ones(len(logV_arr)), logV_arr]).T
            coeffs, residuals, _, _ = np.linalg.lstsq(A, gpH_arr, rcond=None)
            C, alpha = coeffs
            predicted = C + alpha * logV_arr
            ss_res = np.sum((gpH_arr - predicted) ** 2)
            ss_tot = np.sum((gpH_arr - np.mean(gpH_arr)) ** 2)
            r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0
            lines.append(f"**{model_name}**: γ+H = {C:.4f} + ({alpha:.4f})·log(V), R² = {r_squared:.4f}")
            lines.append("")

    # Conclusions
    lines.append("## Conclusions")
    lines.append("")

    # Count how many prompts Stage 4 wins
    stage4_wins = sum(1 for c in comparison.values() if c["stage4_higher"])
    total_comparisons = len(comparison)

    if total_comparisons > 0:
        lines.append(f"Stage 4 (Seed-2.0-mini) has higher γ+H in **{stage4_wins}/{total_comparisons}** prompt types.")
        lines.append("")

        if stage4_wins > total_comparisons / 2:
            lines.append("**FINDING: Stage 4 models show systematically higher γ+H**, consistent with the "
                         "Hebbian regime shift hypothesis. This supports the conservation law analogy.")
        else:
            lines.append("**FINDING: Stage 4 models do NOT consistently show higher γ+H.** "
                         "The conservation law may not directly transfer from PLATO to LLM attention patterns, "
                         "or the proxy metrics (co-occurrence/logprob matrices) may not capture true attention structure.")
        lines.append("")

    # Compare with PLATO constants
    lines.append("### Comparison with PLATO Constants")
    lines.append("")
    lines.append("PLATO room coupling: γ+H = 1.283 - 0.159·log(V)")
    lines.append("")

    for model_name in MODELS:
        gpH_list = []
        V_list = []
        for prompt_name in PROMPTS:
            r = results.get(model_name, {}).get(prompt_name)
            if r:
                gpH_list.append(r["mean_gamma_plus_H"])
                V_list.append(r["mean_V"])
        if gpH_list:
            mean_gpH = np.mean(gpH_values)
            lines.append(f"**{model_name}** mean γ+H: {np.mean(gpH_list):.4f} "
                         f"(PLATO Hebbian γ+H ≈ 1.283)")
            lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*Generated by attention_conservation.py — Forgemaster experiment*")

    RESULTS_PATH.write_text("\n".join(lines))
    print(f"\nResults written to {RESULTS_PATH}")


if __name__ == "__main__":
    results, comparison = run_experiment()
    write_results_markdown(results, comparison)
