#!/usr/bin/env python3
"""
Study 80: Live Conservation Verification on Mixed Fleet
Tests if γ + H conservation holds across heterogeneous models.
"""

import json, time, os, sys, math
from datetime import datetime
import urllib.request
import ssl
import numpy as np

# --- Config ---
ZAI_KEY = "703f56774c324a76b8a283ce50b15744.tLKi6d9yeYza5Spg"
ZAI_URL = "https://api.z.ai/api/coding/paas/v4/chat/completions"
DEEPINFRA_KEY = open("/home/phoenix/.openclaw/workspace/.credentials/deepinfra-api-key.txt").read().strip()
DEEPINFRA_URL = "https://api.deepinfra.com/v1/openai/chat/completions"
OLLAMA_URL = "http://localhost:11434/api/chat"

RESULTS_FILE = "/home/phoenix/.openclaw/workspace/experiments/study80_results.json"
REPORT_FILE = "/home/phoenix/.openclaw/workspace/experiments/STUDY_80_REPORT.md"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def query_model(provider, model, messages, timeout=30):
    """Query a model and return response text."""
    if provider == "zai":
        headers = {"Authorization": f"Bearer {ZAI_KEY}", "Content-Type": "application/json"}
        payload = {"model": model, "messages": messages, "max_tokens": 256, "temperature": 0.3}
        try:
            data = json.dumps(payload).encode()
            req = urllib.request.Request(ZAI_URL, data=data, headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                r = json.loads(resp.read().decode())
            msg = r["choices"][0]["message"]
            return msg.get("content", "") or msg.get("reasoning_content", "")
        except Exception as e:
            return f"ERROR: {e}"
    elif provider == "deepinfra":
        headers = {"Authorization": f"Bearer {DEEPINFRA_KEY}", "Content-Type": "application/json"}
        payload = {"model": model, "messages": messages, "max_tokens": 256, "temperature": 0.3}
        try:
            data = json.dumps(payload).encode()
            req = urllib.request.Request(DEEPINFRA_URL, data=data, headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                r = json.loads(resp.read().decode())
            msg = r["choices"][0]["message"]
            return msg.get("content", "") or msg.get("reasoning_content", "")
        except Exception as e:
            return f"ERROR: {e}"
    elif provider == "ollama":
        payload = {"model": model, "messages": messages, "stream": False, "options": {"temperature": 0.3}}
        try:
            data = json.dumps(payload).encode()
            req = urllib.request.Request(OLLAMA_URL, data=data, headers={"Content-Type": "application/json"}, method='POST')
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                r = json.loads(resp.read().decode())
            return r.get("message", {}).get("content", "")
        except Exception as e:
            return f"ERROR: {e}"

# --- Constraint Satisfaction Problems ---
PROBLEMS = [
    {"prompt": "Find integers x, y such that x + y = 10 and x * y = 21.", "solution": "3,7"},
    {"prompt": "Find x such that x² = 144 and x > 0.", "solution": "12"},
    {"prompt": "Find x, y such that x - y = 5 and x + y = 11.", "solution": "8,3"},
    {"prompt": "Find x such that 2x + 3 = 17.", "solution": "7"},
    {"prompt": "Find integers x, y such that xy = 24 and x + y = 10.", "solution": "4,6"},
    {"prompt": "Find x such that x³ = 64.", "solution": "4"},
    {"prompt": "Find x, y such that x² + y² = 25 and x + y = 7.", "solution": "3,4"},
    {"prompt": "Find x such that |x - 3| = 5.", "solution": "8,-2"},
    {"prompt": "Find x such that x! = 120.", "solution": "5"},
    {"prompt": "Find x, y such that 2x + y = 12 and x - y = 2.", "solution": "4.67,2.67"},
    {"prompt": "Find x such that log₂(x) = 8.", "solution": "256"},
    {"prompt": "Find integers x, y such that x + 2y = 14 and x - y = 2.", "solution": "6,4"},
    {"prompt": "Find x such that √(x+9) = 5.", "solution": "16"},
    {"prompt": "Find x such that 3^x = 81.", "solution": "4"},
    {"prompt": "Find x, y such that x + y = 8 and x² + y² = 40.", "solution": "4,4"},
    {"prompt": "Find x such that sin(x) = 0 and 0 < x < 10.", "solution": "pi"},
    {"prompt": "Find x such that x mod 7 = 3 and x < 20.", "solution": "3,10,17"},
    {"prompt": "Find x such that x² - 5x + 6 = 0.", "solution": "2,3"},
    {"prompt": "Find x such that 2^x + 2^(x+1) = 24.", "solution": "3"},
    {"prompt": "Find x, y such that x² - y² = 16 and x + y = 8.", "solution": "5,3"},
]

# --- Models ---
MODELS = [
    ("zai", "glm-5-turbo", "GLM-5-Turbo"),
    ("deepinfra", "ByteDance/Seed-2.0-mini", "Seed-2.0-Mini"),
    ("ollama", "qwen3:0.6b", "Qwen3-0.6B"),
    ("ollama", "gemma3:1b", "Gemma3-1B"),
    ("ollama", "llama3.2:1b", "Llama3.2-1B"),
]

def extract_answer(response):
    """Extract a normalized answer from response."""
    r = response.lower().strip()
    # Remove common prefixes
    for prefix in ["the answer is", "therefore", "so", "x =", "x=", "solution:", "answer:"]:
        if prefix in r:
            r = r.split(prefix)[-1].strip()
    return r

def similarity(resp1, resp2):
    """Simple text similarity between two responses."""
    # Token-level Jaccard
    t1 = set(resp1.lower().split())
    t2 = set(resp2.lower().split())
    if not t1 or not t2:
        return 0.0
    return len(t1 & t2) / len(t1 | t2)

def compute_fiedler(coupling_matrix):
    """Compute the Fiedler value (second smallest eigenvalue of Laplacian)."""
    n = coupling_matrix.shape[0]
    # Degree matrix
    D = np.diag(coupling_matrix.sum(axis=1))
    # Laplacian
    L = D - coupling_matrix
    eigenvalues = np.sort(np.real(np.linalg.eigvalsh(L)))
    if len(eigenvalues) >= 2:
        return eigenvalues[1]  # Fiedler value
    return 0.0

def compute_entropy(coupling_matrix):
    """Compute coupling entropy H."""
    total = coupling_matrix.sum()
    if total == 0:
        return 0.0
    probs = coupling_matrix.flatten() / total
    H = 0.0
    for p in probs:
        if p > 0:
            H -= p * np.log2(p + 1e-12)
    return H

def run_study():
    print(f"=== Study 80: Live Conservation Verification on Mixed Fleet ===")
    print(f"Started: {datetime.now().isoformat()}")
    
    n_agents = len(MODELS)
    n_problems = len(PROBLEMS)
    n_rounds = 3  # Run 3 rounds
    
    all_results = {"metadata": {"study": 80, "started": datetime.now().isoformat()}, "rounds": {}}
    
    for round_num in range(n_rounds):
        print(f"\n=== Round {round_num + 1} ===")
        round_data = {"responses": {}}
        
        # Each agent answers all problems
        responses = {}  # model_name -> [response_strings]
        for provider, model_id, model_name in MODELS:
            print(f"  Querying {model_name}...")
            model_responses = []
            for p_idx, problem in enumerate(PROBLEMS):
                messages = [
                    {"role": "system", "content": "You are a math solver. Give ONLY the numerical answer(s), nothing else."},
                    {"role": "user", "content": problem["prompt"]}
                ]
                resp = query_model(provider, model_id, messages, timeout=30)
                model_responses.append(resp)
                time.sleep(0.3)
            responses[model_name] = model_responses
            round_data["responses"][model_name] = model_responses
        
        # Build coupling matrix from pairwise similarity
        coupling = np.zeros((n_agents, n_agents))
        model_names = [m[2] for m in MODELS]
        
        for i in range(n_agents):
            for j in range(n_agents):
                sim = 0
                for p_idx in range(n_problems):
                    sim += similarity(responses[model_names[i]][p_idx], responses[model_names[j]][p_idx])
                sim /= n_problems
                coupling[i][j] = sim
        
        # Compute metrics
        gamma = compute_fiedler(coupling)
        H = compute_entropy(coupling)
        
        round_data["coupling_matrix"] = coupling.tolist()
        round_data["gamma"] = float(gamma)
        round_data["H"] = float(H)
        round_data["gamma_plus_H"] = float(gamma + H)
        
        all_results["rounds"][f"round_{round_num+1}"] = round_data
        print(f"  γ (Fiedler) = {gamma:.4f}")
        print(f"  H (Entropy) = {H:.4f}")
        print(f"  γ + H       = {gamma + H:.4f}")
    
    # Check conservation
    gamma_H_values = [all_results["rounds"][f"round_{r+1}"]["gamma_plus_H"] for r in range(n_rounds)]
    mean_gh = np.mean(gamma_H_values)
    std_gh = np.std(gamma_H_values)
    cv_gh = std_gh / mean_gh if mean_gh > 0 else float('inf')
    
    all_results["conservation"] = {
        "gamma_H_values": [float(v) for v in gamma_H_values],
        "mean": float(mean_gh),
        "std": float(std_gh),
        "cv": float(cv_gh),
        "conserved": bool(cv_gh < 0.15)  # <15% variation = conserved
    }
    
    all_results["metadata"]["completed"] = datetime.now().isoformat()
    
    with open(RESULTS_FILE, "w") as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\nResults saved to {RESULTS_FILE}")
    generate_report(all_results)
    return all_results

def generate_report(results):
    lines = [
        "# Study 80: Live Conservation Verification on Mixed Fleet",
        f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Hypothesis",
        "Conservation of γ + H holds even across heterogeneous models (different architectures, sizes, training data).",
        "",
        "## Fleet Composition",
        "",
    ]
    for _, _, name in MODELS:
        lines.append(f"- {name}")
    
    lines.extend(["", "## Results by Round", ""])
    
    for round_key in results["rounds"]:
        r = results["rounds"][round_key]
        lines.append(f"### {round_key.replace('_', ' ').title()}")
        lines.append(f"- γ (Fiedler value): {r['gamma']:.4f}")
        lines.append(f"- H (Coupling entropy): {r['H']:.4f}")
        lines.append(f"- γ + H: {r['gamma_plus_H']:.4f}")
        lines.append("")
    
    # Coupling matrices
    lines.append("## Coupling Matrices")
    lines.append("")
    model_names = [m[2] for m in MODELS]
    
    for round_key in results["rounds"]:
        cm = np.array(results["rounds"][round_key]["coupling_matrix"])
        lines.append(f"### {round_key.replace('_', ' ').title()}")
        lines.append("")
        header = "| | " + " | ".join([n.split("-")[0] for n in model_names]) + " |"
        sep = "|---" + "|---" * len(model_names) + "|"
        lines.append(header)
        lines.append(sep)
        for i, name in enumerate(model_names):
            row = f"| {name.split('-')[0]} | " + " | ".join([f"{cm[i][j]:.3f}" for j in range(len(model_names))]) + " |"
            lines.append(row)
        lines.append("")
    
    # Conservation check
    cons = results["conservation"]
    lines.extend([
        "## Conservation Analysis",
        "",
        f"| Round | γ + H |",
        f"|-------|-------|",
    ])
    for i, v in enumerate(cons["gamma_H_values"]):
        lines.append(f"| Round {i+1} | {v:.4f} |")
    
    lines.extend([
        "",
        f"**Mean γ + H: {cons['mean']:.4f}**",
        f"**Std Dev: {cons['std']:.4f}**",
        f"**Coefficient of Variation: {cons['cv']:.4f} ({cons['cv']*100:.1f}%)**",
        f"**Conserved? {'YES ✓' if cons['conserved'] else 'NO ✗'}** (threshold: CV < 15%)",
        "",
        "## Conclusions",
        "",
        f"1. γ + H is {'conserved' if cons['conserved'] else 'not conserved'} across rounds with mixed models",
        f"2. The Fiedler value γ measures fleet coherence — higher = more agreement",
        f"3. Entropy H measures coupling diversity — reflects heterogeneity",
        f"4. The trade-off γ + H = const would indicate a fundamental conservation law",
        "",
    ])
    
    with open(REPORT_FILE, "w") as f:
        f.write("\n".join(lines))
    print(f"Report saved to {REPORT_FILE}")

if __name__ == "__main__":
    run_study()
