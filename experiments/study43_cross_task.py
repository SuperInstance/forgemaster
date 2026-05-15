#!/usr/bin/env python3
"""Study 43: Cross-Task Replication — Vocabulary Wall generalization test."""

import json
import time
import urllib.request
import urllib.error
import os
import random

API_KEY = "N9RjXro4pXD2jpHmxeTay5PUJ6AxUsac"
MODEL = "NousResearch/Hermes-3-Llama-3.1-70B"
ENDPOINT = "https://api.deepinfra.com/v1/openai/chat/completions"

# Task definitions
TASKS = {
    "cauchy_schwarz": {
        "domain": 'For vectors u=(3,4) and v=(6,2), verify the Cauchy-Schwarz inequality |u·v| ≤ ||u||·||v||. Compute ||u||·||v||. Reply ONLY the integer result.',
        "bare": 'Compute sqrt(9+16) * sqrt(36+4) = ? Reply ONLY the integer rounded to nearest whole number.',
        "answer": 32,  # 5 * sqrt(40) ≈ 31.6 → round to 32
        "answer_check": lambda x: x in [31, 32],  # accept both 31 and 32 due to rounding
    },
    "mobius_function": {
        "domain": 'Compute the Möbius function μ(30). Recall: μ(n)=0 if n has a squared prime factor, μ(n)=(-1)^k if n is a product of k distinct primes. Reply ONLY the integer result.',
        "bare": '30 = 2×3×5. Three distinct prime factors. (-1)^3 = ? Reply ONLY the integer result.',
        "answer": -1,
        "answer_check": lambda x: x == -1,
    },
    "fourier_coefficient": {
        "domain": 'Compute the Fourier coefficient a_0 = (1/π) ∫₀^π cos(x) dx. Reply ONLY the number rounded to 2 decimal places.',
        "bare": 'Compute (1/3.14159) * [sin(3.14159) - sin(0)]. sin(π) = 0, sin(0) = 0. So the result is 0/π = ? Reply ONLY the number.',
        "answer": 0.00,
        "answer_check": lambda x: abs(x) < 0.01,  # accept 0, 0.0, 0.00
    },
    "gram_determinant": {
        "domain": 'For vectors u=(1,2) and v=(3,1), compute the Gram determinant det(G) where G_ij = v_i · v_j. Reply ONLY the integer result.',
        "bare": 'Compute (1*1+2*2)*(3*3+1*1) - (1*3+2*1)^2 = ? Reply ONLY the integer result.',
        "answer": 25,
        "answer_check": lambda x: x == 25,
    },
    "legendre_symbol": {
        "domain": 'Compute the Legendre symbol (5/7). Recall (a/p) = a^((p-1)/2) mod p. Reply ONLY the integer result (1, -1, or 0).',
        "bare": 'Compute 5^3 mod 7. 5^3 = 125. 125 mod 7 = ? Reply ONLY the integer result.',
        "answer": -1,  # Legendre(5/7): 5^3 = 125, 125 mod 7 = 6, but Legendre: 6 ≡ -1 mod 7
        "answer_check": lambda x: x in [-1, 6],  # bare may return 6, domain should return -1
    },
}

def extract_number(text):
    """Extract the last number from response text."""
    import re
    # Try to find numbers including negative and decimals
    numbers = re.findall(r'-?\d+\.?\d*', text.strip())
    if not numbers:
        return None
    # Take the last number (most likely the answer)
    num_str = numbers[-1]
    try:
        if '.' in num_str:
            return float(num_str)
        return int(num_str)
    except:
        return None

def call_api(prompt, temperature=0.3, max_tokens=150):
    """Make a single API call to DeepInfra."""
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode('utf-8')
    
    req = urllib.request.Request(
        ENDPOINT,
        data=payload,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        }
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data['choices'][0]['message']['content'].strip()
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        print(f"  HTTP {e.code}: {body[:200]}")
        return None
    except Exception as e:
        print(f"  Error: {e}")
        return None

def run_study():
    results = []
    total_calls = 0
    
    # Build trial list and shuffle for interleaving
    trials = []
    for task_name, task_def in TASKS.items():
        for condition in ["domain", "bare"]:
            for trial_num in range(1, 21):
                trials.append((task_name, condition, trial_num))
    
    random.seed(42)
    random.shuffle(trials)
    
    print(f"Running {len(trials)} trials...")
    
    for i, (task_name, condition, trial_num) in enumerate(trials):
        task_def = TASKS[task_name]
        prompt = task_def[condition]
        
        response = call_api(prompt)
        total_calls += 1
        
        if response is None:
            extracted = None
            correct = False
        else:
            extracted = extract_number(response)
            if extracted is not None:
                correct = task_def["answer_check"](extracted)
            else:
                correct = False
        
        result = {
            "task": task_name,
            "condition": condition,
            "trial_num": trial_num,
            "response": response,
            "extracted_answer": extracted,
            "expected_answer": task_def["answer"],
            "correct": correct,
        }
        results.append(result)
        
        status = "✓" if correct else "✗"
        print(f"  [{i+1}/{len(trials)}] {task_name}/{condition}/{trial_num}: {extracted} {status}")
        
        # Rate limit: small delay
        time.sleep(0.5)
    
    print(f"\nTotal API calls: {total_calls}")
    return results

def analyze(results):
    """Analyze results by task and condition."""
    from collections import defaultdict
    
    stats = defaultdict(lambda: {"domain_correct": 0, "domain_total": 0, 
                                   "bare_correct": 0, "bare_total": 0})
    
    for r in results:
        key = r["task"]
        if r["condition"] == "domain":
            stats[key]["domain_correct"] += r["correct"]
            stats[key]["domain_total"] += 1
        else:
            stats[key]["bare_correct"] += r["correct"]
            stats[key]["bare_total"] += 1
    
    # Overall
    overall_domain = sum(s["domain_correct"] for s in stats.values())
    overall_bare = sum(s["bare_correct"] for s in stats.values())
    total_domain = sum(s["domain_total"] for s in stats.values())
    total_bare = sum(s["bare_total"] for s in stats.values())
    
    print("\n=== RESULTS BY TASK ===")
    for task_name in TASKS:
        s = stats[task_name]
        d_pct = (s["domain_correct"] / s["domain_total"] * 100) if s["domain_total"] else 0
        b_pct = (s["bare_correct"] / s["bare_total"] * 100) if s["bare_total"] else 0
        delta = d_pct - b_pct
        print(f"  {task_name}: domain={d_pct:.0f}% ({s['domain_correct']}/{s['domain_total']}), "
              f"bare={b_pct:.0f}% ({s['bare_correct']}/{s['bare_total']}), Δ={delta:+.0f}%")
    
    print(f"\n  OVERALL: domain={overall_domain}/{total_domain} ({overall_domain/total_domain*100:.0f}%), "
          f"bare={overall_bare}/{total_bare} ({overall_bare/total_bare*100:.0f}%)")
    
    return stats, overall_domain, overall_bare, total_domain, total_bare

def main():
    results = run_study()
    
    # Save raw JSON
    with open("experiments/study43-results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    # Analyze
    stats, od, ob, td, tb = analyze(results)
    
    # Generate markdown report
    md = generate_report(results, stats, od, ob, td, tb)
    with open("experiments/STUDY-43-CROSS-TASK-REPLICATION.md", "w") as f:
        f.write(md)
    
    print("\nSaved: experiments/study43-results.json, experiments/STUDY-43-CROSS-TASK-REPLICATION.md")

def generate_report(results, stats, od, ob, td, tb):
    lines = [
        "# Study 43: Cross-Task Replication — Vocabulary Wall Generalization",
        "",
        f"**Date:** 2025-05-15",
        f"**Model:** NousResearch/Hermes-3-Llama-3.1-70B (DeepInfra)",
        f"**Temperature:** 0.3 | **Max tokens:** 150",
        f"**Trials:** 5 tasks × 2 conditions × 20 repetitions = 200 calls",
        f"**Order:** Randomized (seed=42)",
        "",
        "## Hypothesis",
        "",
        "The Vocabulary Wall effect generalizes beyond Eisenstein norms. Domain-framed math problems",
        "(using terms like \"Cauchy-Schwarz\", \"Möbius function\", \"Legendre symbol\") will have different",
        "accuracy than bare arithmetic equivalents, even when the underlying computation is identical.",
        "",
        "## Task Definitions",
        "",
        "| Task | Domain Prompt | Bare Prompt | Expected Answer |",
        "|------|--------------|-------------|-----------------|",
    ]
    
    for name, t in TASKS.items():
        lines.append(f"| {name} | {t['domain'][:50]}... | {t['bare'][:50]}... | {t['answer']} |")
    
    lines.extend([
        "",
        "## Results",
        "",
        "| Task | Domain Accuracy | Bare Accuracy | Δ (domain - bare) |",
        "|------|----------------|---------------|-------------------|",
    ])
    
    for task_name in TASKS:
        s = stats[task_name]
        d_pct = (s["domain_correct"] / s["domain_total"] * 100) if s["domain_total"] else 0
        b_pct = (s["bare_correct"] / s["bare_total"] * 100) if s["bare_total"] else 0
        delta = d_pct - b_pct
        lines.append(f"| {task_name} | {d_pct:.0f}% ({s['domain_correct']}/{s['domain_total']}) | "
                      f"{b_pct:.0f}% ({s['bare_correct']}/{s['bare_total']}) | {delta:+.0f}% |")
    
    overall_d = (od / td * 100) if td else 0
    overall_b = (ob / tb * 100) if tb else 0
    overall_delta = overall_d - overall_b
    
    lines.extend([
        f"| **OVERALL** | **{overall_d:.0f}% ({od}/{td})** | **{overall_b:.0f}% ({ob}/{tb})** | **{overall_delta:+.0f}%** |",
        "",
        "## Sample Responses",
        "",
    ])
    
    # Show first trial per task per condition
    for task_name in TASKS:
        for cond in ["domain", "bare"]:
            matches = [r for r in results if r["task"] == task_name and r["condition"] == cond]
            if matches:
                r = matches[0]
                lines.extend([
                    f"### {task_name} / {cond} (trial 1)",
                    f"- **Response:** `{r['response']}`",
                    f"- **Extracted:** {r['extracted_answer']}",
                    f"- **Expected:** {r['expected_answer']}",
                    f"- **Correct:** {r['correct']}",
                    "",
                ])
    
    lines.extend([
        "## Analysis",
        "",
        f"Overall accuracy: Domain = {overall_d:.0f}%, Bare = {overall_b:.0f}%, Δ = {overall_delta:+.0f}%.",
        "",
    ])
    
    if overall_delta > 0:
        lines.append("The Vocabulary Wall replicates: domain-framed prompts yield **higher** accuracy than bare arithmetic.")
    elif overall_delta < 0:
        lines.append("**REVERSE Vocabulary Wall detected:** bare arithmetic yields higher accuracy than domain-framed prompts.")
        lines.append("This suggests the effect may be task-dependent or that domain vocabulary adds confusion rather than scaffolding.")
    else:
        lines.append("No significant difference detected between conditions.")
    
    # Task-level commentary
    lines.append("")
    lines.append("### Task-Level Observations")
    for task_name in TASKS:
        s = stats[task_name]
        d_pct = (s["domain_correct"] / s["domain_total"] * 100) if s["domain_total"] else 0
        b_pct = (s["bare_correct"] / s["bare_total"] * 100) if s["bare_total"] else 0
        delta = d_pct - b_pct
        if delta > 10:
            lines.append(f"- **{task_name}:** Domain advantage (+{delta:.0f}%). Domain vocabulary acts as scaffolding.")
        elif delta < -10:
            lines.append(f"- **{task_name}:** Bare advantage ({delta:.0f}%). Domain vocabulary adds confusion.")
        else:
            lines.append(f"- **{task_name}:** Near-identical performance ({delta:+.0f}%). No vocabulary effect.")
    
    lines.extend([
        "",
        "## Conclusion",
        "",
        "This study tests whether the Vocabulary Wall (observed with Eisenstein norms on GLM models) generalizes to:",
        "1. A different model (Hermes-70B)",
        "2. Five distinct mathematical domains",
        "",
        "The results will determine whether this is a GLM-specific artifact or a general LLM phenomenon.",
    ])
    
    return "\n".join(lines)

if __name__ == "__main__":
    main()
