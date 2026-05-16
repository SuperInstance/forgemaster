#!/usr/bin/env python3
"""Study 56: Cross-domain transfer of the activation-key model."""
import functools
print = functools.partial(print, flush=True)

import json
import os
import re
import subprocess
import sys
import time
import urllib.request
import urllib.error

# ── Configuration ──────────────────────────────────────────────────────────────

DEEPINFRA_KEY = open(os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")).read().strip()
DEEPINFRA_URL = "https://api.deepinfra.com/v1/openai/chat/completions"
OLLAMA_URL = "http://localhost:11434/api/chat"

MODELS = {
    "Seed-2.0-mini": {"provider": "deepinfra", "model": "ByteDance/Seed-2.0-mini"},
    "Hermes-70B": {"provider": "deepinfra", "model": "NousResearch/Hermes-3-Llama-3.1-70B"},
    "gemma3:1b": {"provider": "ollama", "model": "gemma3:1b"},
}

# ── Problems: 4 domains × 5 problems × 2 conditions ────────────────────────────

PROBLEMS = {
    "chemistry": [
        {
            "id": "chem1",
            "bare": "Compute the molar mass of H2SO4.",
            "labeled": "Using Avogadro's approach and your knowledge of atomic masses, compute the molar mass of sulfuric acid (H2SO4).",
            "answer": 98.08,  # 2(1.008) + 32.06 + 4(16.00) = 98.08
            "extract": "float",
            "tolerance": 0.5,
        },
        {
            "id": "chem2",
            "bare": "What is the molar mass of C6H12O6?",
            "labeled": "Applying standard atomic mass calculations from the periodic table, determine the molar mass of glucose (C6H12O6).",
            "answer": 180.16,  # 6(12.01) + 12(1.008) + 6(16.00) = 180.16
            "extract": "float",
            "tolerance": 0.5,
        },
        {
            "id": "chem3",
            "bare": "Calculate the molar mass of NaCl.",
            "labeled": "Using standard chemical computation methods, calculate the molar mass of sodium chloride.",
            "answer": 58.44,  # 22.99 + 35.45 = 58.44
            "extract": "float",
            "tolerance": 0.5,
        },
        {
            "id": "chem4",
            "bare": "What is the molar mass of CaCO3?",
            "labeled": "Using crystallographic mass analysis, compute the molar mass of calcium carbonate.",
            "answer": 100.09,  # 40.08 + 12.01 + 3(16.00) = 100.09
            "extract": "float",
            "tolerance": 0.5,
        },
        {
            "id": "chem5",
            "bare": "Compute the molar mass of NH3.",
            "labeled": "Applying the principles of stoichiometric calculation, determine the molar mass of ammonia.",
            "answer": 17.03,  # 14.01 + 3(1.008) = 17.03
            "extract": "float",
            "tolerance": 0.5,
        },
    ],
    "physics": [
        {
            "id": "phys1",
            "bare": "What force is needed to accelerate 5 kg at 3 m/s²?",
            "labeled": "Using Newton's second law of motion (F = ma), calculate the force required to accelerate a 5 kg mass at 3 m/s².",
            "answer": 15,
            "extract": "float",
            "tolerance": 0.01,
        },
        {
            "id": "phys2",
            "bare": "A 2 kg ball is dropped from 10 m. What is its velocity when it hits the ground?",
            "labeled": "Applying the kinematic equation for free fall under gravitational acceleration (g = 9.8 m/s²), compute the impact velocity of a 2 kg ball dropped from 10 meters height.",
            "answer": 14.0,  # v = sqrt(2gh) = sqrt(2*9.8*10) = 14.0
            "extract": "float",
            "tolerance": 0.5,
        },
        {
            "id": "phys3",
            "bare": "What is the kinetic energy of a 1000 kg car moving at 20 m/s?",
            "labeled": "Using the kinetic energy formula from classical mechanics, compute the kinetic energy of a 1000 kg automobile traveling at 20 m/s.",
            "answer": 200000,  # 0.5 * 1000 * 20^2 = 200000
            "extract": "float",
            "tolerance": 1,
        },
        {
            "id": "phys4",
            "bare": "What is the gravitational potential energy of a 50 kg object at 3 m height?",
            "labeled": "Applying the gravitational potential energy relation from classical mechanics, compute the PE of a 50 kg mass at 3 m elevation (g = 9.8 m/s²).",
            "answer": 1470,  # mgh = 50 * 9.8 * 3 = 1470
            "extract": "float",
            "tolerance": 5,
        },
        {
            "id": "phys5",
            "bare": "How much work is done moving a 40 N force through 5 m?",
            "labeled": "Using the work-energy principle from Newtonian mechanics, compute the work done when a 40 N force acts through a displacement of 5 m in the direction of the force.",
            "answer": 200,  # W = Fd = 40 * 5 = 200
            "extract": "float",
            "tolerance": 1,
        },
    ],
    "logic": [
        {
            "id": "logic1",
            "bare": "If A→B and B→C, what follows from A?",
            "labeled": "Using the transitive property of material implication in propositional logic, derive the conclusion from: A→B and B→C, given A.",
            "answer": "C",
            "extract": "text",
            "valid": ["c", "C"],
        },
        {
            "id": "logic2",
            "bare": "If all X are Y, and all Y are Z, what can we conclude about X?",
            "labeled": "Applying the Barbara syllogism from classical Aristotelian logic, determine what follows from: all X are Y, and all Y are Z.",
            "answer": "all X are Z",
            "extract": "text",
            "valid": ["all x are z", "x are z", "x is z", "every x is z"],
        },
        {
            "id": "logic3",
            "bare": "If P or Q is true, and P is false, what is Q?",
            "labeled": "Using the disjunctive syllogism rule of inference, determine: given (P ∨ Q) and ¬P, what follows about Q?",
            "answer": "true",
            "extract": "text",
            "valid": ["true", "q is true", "q must be true"],
        },
        {
            "id": "logic4",
            "bare": "If not P implies Q, and not Q is true, what follows about P?",
            "labeled": "Applying modus tollens in propositional logic: given ¬P → Q, and ¬Q is true, derive the conclusion about P.",
            "answer": "P is true",
            "extract": "text",
            "valid": ["p is true", "p must be true", "p is true", "true"],
        },
        {
            "id": "logic5",
            "bare": "If A and B are both true, what can we say about A alone?",
            "labeled": "Using the simplification rule of inference from natural deduction, given (A ∧ B) is true, what follows about A?",
            "answer": "A is true",
            "extract": "text",
            "valid": ["a is true", "true", "a is true"],
        },
    ],
    "code": [
        {
            "id": "code1",
            "bare": "Write a function that reverses a linked list. Return the new head.",
            "labeled": "Implement the classic iterative linked-list reversal algorithm using three pointers (prev, current, next). Return the new head of the reversed list.",
            "answer": "reverses_list",
            "extract": "code",
            "check": "reverse_linked_list",
        },
        {
            "id": "code2",
            "bare": "Write a function that finds the maximum element in an array.",
            "labeled": "Implement the standard linear scan algorithm for finding the maximum value in an unsorted array. Use a single pass with O(n) time complexity.",
            "answer": "finds_max",
            "extract": "code",
            "check": "find_max",
        },
        {
            "id": "code3",
            "bare": "Write a function that checks if a string is a palindrome.",
            "labeled": "Implement the two-pointer palindrome verification algorithm: compare characters from both ends moving inward with O(n) time and O(1) space.",
            "answer": "checks_palindrome",
            "extract": "code",
            "check": "is_palindrome",
        },
        {
            "id": "code4",
            "bare": "Write a function that computes the factorial of n.",
            "labeled": "Implement the recursive factorial function following the standard mathematical definition: n! = n × (n-1)!, with base case 0! = 1.",
            "answer": "computes_factorial",
            "extract": "code",
            "check": "factorial",
        },
        {
            "id": "code5",
            "bare": "Write a function that counts the number of vowels in a string.",
            "labeled": "Implement a vowel-counting function using set membership lookup. Count occurrences of a, e, i, o, u (both cases) in the input string.",
            "answer": "counts_vowels",
            "extract": "code",
            "check": "count_vowels",
        },
    ],
}

# ── API Calls ──────────────────────────────────────────────────────────────────

def call_deepinfra(model_id, prompt, max_tokens=150):
    payload = json.dumps({
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0,
    }).encode()
    req = urllib.request.Request(
        DEEPINFRA_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPINFRA_KEY}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"ERROR: {e}"


def call_ollama(model_id, prompt):
    payload = json.dumps({
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0},
    }).encode()
    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
            return data["message"]["content"]
    except Exception as e:
        return f"ERROR: {e}"


def query_model(model_name, prompt, max_tokens=150):
    cfg = MODELS[model_name]
    if cfg["provider"] == "deepinfra":
        return call_deepinfra(cfg["model"], prompt, max_tokens)
    else:
        return call_ollama(cfg["model"], prompt)


# ── Scoring ────────────────────────────────────────────────────────────────────

def extract_numbers(text):
    """Extract all numbers from text."""
    return [float(x) for x in re.findall(r'[\d]+\.?\d*', text)]


def score_numeric(response, expected, tolerance):
    """Score a numeric answer - correct if ANY number in response matches expected."""
    nums = extract_numbers(response)
    if not nums:
        return "incorrect", None
    for n in nums:
        if abs(n - expected) <= tolerance:
            return "correct", n
    return "incorrect", nums[-1]


def score_text(response, valid_answers):
    """Score a text answer."""
    resp_lower = response.lower().strip()
    for valid in valid_answers:
        if valid.lower() in resp_lower:
            return "correct", valid
    return "incorrect", response[:200]


def score_code(response, check_type):
    """Score a code response - check if it implements the expected algorithm."""
    resp_lower = response.lower()
    
    if check_type == "reverse_linked_list":
        # Should have: function definition, prev/current/next pointers, loop
        has_func = bool(re.search(r'def\s+\w+', response))
        has_prev = "prev" in resp_lower
        has_loop = any(kw in resp_lower for kw in ["while", "for"])
        if has_func and has_prev and has_loop:
            return "correct", "implements_iterative_reversal"
        elif has_func:
            return "partial", "has_function_but_missing_elements"
        return "incorrect", "no_function_found"
    
    elif check_type == "find_max":
        has_func = bool(re.search(r'def\s+\w+', response))
        has_init = any(kw in resp_lower for kw in ["max", "first", "float('-inf')"])
        has_loop = any(kw in resp_lower for kw in ["for ", "while"])
        if has_func and has_init and has_loop:
            return "correct", "implements_linear_scan"
        elif has_func:
            return "partial", "has_function_but_missing_elements"
        return "incorrect", "no_function_found"
    
    elif check_type == "is_palindrome":
        has_func = bool(re.search(r'def\s+\w+', response))
        has_two_pointer = any(kw in resp_lower for kw in ["left", "right", "start", "end", "[0]", "[-1]"])
        has_reverse = "[::-1]" in resp_lower or "revers" in resp_lower
        if has_func and (has_two_pointer or has_reverse):
            return "correct", "implements_palindrome_check"
        elif has_func:
            return "partial", "has_function_but_missing_elements"
        return "incorrect", "no_function_found"
    
    elif check_type == "factorial":
        has_func = bool(re.search(r'def\s+\w+', response))
        has_recursive = "factorial" in resp_lower and "return" in resp_lower
        has_base = "1" in resp_lower and ("0" in resp_lower or "== 1" in resp_lower or "<= 1" in resp_lower)
        if has_func and has_recursive and has_base:
            return "correct", "implements_recursive_factorial"
        elif has_func and has_recursive:
            return "partial", "has_function_but_missing_base_case"
        return "incorrect", "no_function_found"
    
    elif check_type == "count_vowels":
        has_func = bool(re.search(r'def\s+\w+', response))
        has_vowels = "vowel" in resp_lower or ("a" in resp_lower and "e" in resp_lower and "i" in resp_lower)
        has_count = "count" in resp_lower or "+= 1" in resp_lower or "sum" in resp_lower
        if has_func and has_vowels and has_count:
            return "correct", "implements_vowel_counter"
        elif has_func:
            return "partial", "has_function_but_missing_elements"
        return "incorrect", "no_function_found"
    
    return "incorrect", "unknown_check"


# ── Main Experiment ────────────────────────────────────────────────────────────

def run_experiment():
    results = []
    total = 0
    completed = 0
    
    # Count total
    for domain in PROBLEMS:
        for _ in PROBLEMS[domain]:
            for _ in MODELS:
                for _ in ["bare", "labeled"]:
                    total += 1
    
    print(f"Study 56: Cross-Domain Activation-Key Transfer")
    print(f"Total trials: {total}")
    print(f"Models: {list(MODELS.keys())}")
    print(f"Domains: {list(PROBLEMS.keys())}")
    print("=" * 60)
    
    for domain_name, problems in PROBLEMS.items():
        print(f"\n{'='*60}")
        print(f"Domain: {domain_name.upper()}")
        print(f"{'='*60}")
        
        for prob in problems:
            for model_name in MODELS:
                for condition in ["bare", "labeled"]:
                    prompt = prob[condition]
                    max_tokens = 300 if domain_name != "code" else 500
                    
                    response = query_model(model_name, prompt, max_tokens)
                    completed += 1
                    
                    # Score
                    if prob["extract"] == "float":
                        score, val = score_numeric(response, prob["answer"], prob["tolerance"])
                    elif prob["extract"] == "text":
                        score, val = score_text(response, prob["valid"])
                    else:  # code
                        score, val = score_code(response, prob["check"])
                    
                    result = {
                        "domain": domain_name,
                        "problem_id": prob["id"],
                        "model": model_name,
                        "condition": condition,
                        "prompt": prompt,
                        "response": response[:500],
                        "expected": prob["answer"],
                        "extracted": val,
                        "score": score,
                        "trial_num": completed,
                    }
                    results.append(result)
                    
                    status = "✅" if score == "correct" else "⚠️" if score == "partial" else "❌"
                    print(f"  [{completed:3d}/{total}] {model_name:20s} {condition:7s} {prob['id']:8s} → {score:8s} {status}")
                    
                    # Rate limit
                    time.sleep(0.3 if MODELS[model_name]["provider"] == "deepinfra" else 0.1)
    
    # Save results
    out_path = os.path.join(os.path.dirname(__file__), "study56_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {out_path}")
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for domain_name in PROBLEMS:
        print(f"\n{domain_name.upper()}:")
        for model_name in MODELS:
            for condition in ["bare", "labeled"]:
                domain_results = [r for r in results if r["domain"] == domain_name and r["model"] == model_name and r["condition"] == condition]
                correct = sum(1 for r in domain_results if r["score"] == "correct")
                partial = sum(1 for r in domain_results if r["score"] == "partial")
                total_d = len(domain_results)
                print(f"  {model_name:20s} {condition:7s}: {correct}/{total_d} correct, {partial}/{total_d} partial")
    
    # Aggregate by condition
    print("\n\nAGGREGATE BY CONDITION:")
    for model_name in MODELS:
        for condition in ["bare", "labeled"]:
            model_results = [r for r in results if r["model"] == model_name and r["condition"] == condition]
            correct = sum(1 for r in model_results if r["score"] == "correct")
            partial = sum(1 for r in model_results if r["score"] == "partial")
            total_m = len(model_results)
            print(f"  {model_name:20s} {condition:7s}: {correct}/{total_m} ({100*correct/total_m:.0f}%) correct, {partial}/{total_m} partial")
    
    # Aggregate by domain
    print("\n\nAGGREGATE BY DOMAIN:")
    for domain_name in PROBLEMS:
        domain_results = [r for r in results if r["domain"] == domain_name]
        correct = sum(1 for r in domain_results if r["score"] == "correct")
        partial = sum(1 for r in domain_results if r["score"] == "partial")
        total_dd = len(domain_results)
        print(f"  {domain_name:12s}: {correct}/{total_dd} ({100*correct/total_dd:.0f}%) correct, {partial}/{total_dd} partial")
    
    return results


if __name__ == "__main__":
    results = run_experiment()
