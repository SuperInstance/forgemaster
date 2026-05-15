#!/usr/bin/env python3
"""
Study 9: Combination Scaffolding — Can We Rescue qwen3:4b from Partial Computation?

Hypothesis: qwen3:4b computes correct sub-expressions (a², b², ab) but fails to 
combine them into a²-ab+b². If we scaffold the combination step (provide sub-results
and ask only for the combination), accuracy should jump from ~10% to >60%.

This tests the Stage 3 → Stage 4 bridge: the model HAS the computation, 
it just needs help with the assembly.

Tests:
1. Baseline: compute Eisenstein norm from scratch (known ~10%)
2. Scaffolded: given a², ab, b², compute norm (combination only)
3. Partial scaffold: given a and b, first compute squares then combine
4. Step-by-step: explicit "step 1: square a, step 2: square b, step 3: multiply, step 4: combine"
5. Cross-model: same tests on phi4-mini (echo model) and gemma3:1b (echo model)
"""

import requests
import re
import json
import sys
from collections import Counter
from datetime import datetime

# Force unbuffered output
print = lambda *a, **k: (sys.stdout.write(' '.join(map(str, a)) + k.get('end', '\n')), sys.stdout.flush())

def ask_model(model, prompt, max_tokens=300):
    """Ask a model, handle thinking models (qwen3)."""
    resp = requests.post("http://localhost:11434/api/chat", json={
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"num_predict": max_tokens}
    }, timeout=120)
    msg = resp.json()["message"]
    content = msg.get("content", "")
    thinking = msg.get("thinking", "")
    full = content if content.strip() else thinking
    return full.strip(), content.strip(), thinking.strip()

def extract_number(text):
    """Extract the last integer from model output."""
    nums = re.findall(r'-?\d+', text)
    return int(nums[-1]) if nums else None

def eisenstein_norm(a, b):
    """Compute a²-ab+b²."""
    return a*a - a*b + b*b

# Test cases: (a, b) pairs covering various sign combinations
TEST_PAIRS = [
    (5, -3),   # 49
    (7, 2),    # 49
    (3, 8),    # 49
    (-4, -6),  # 28
    (10, -1),  # 111
    (6, 9),    # 63
    (-2, 7),   # 67
    (0, 5),    # 25
    (-3, -3),  # 9
    (8, -4),   # 112
]

N_TRIALS = 5  # per condition per pair

MODELS = {
    "qwen3:4b": "Stage 3 (partial computation)",
    "phi4-mini": "Stage 2-3 (echo dominant)",
    "gemma3:1b": "Stage 2 (echo)",
}

PROMPT_TEMPLATES = {
    "baseline": (
        "Compute the Eisenstein norm of the Eisenstein integer ({a} + {b}ω). "
        "The formula is a²-ab+b² where a={a} and b={b}. "
        "Reply ONLY with the integer result, nothing else."
    ),
    "scaffolded": (
        "Given: a={a}, b={b}. "
        "I've computed: a²={a2}, b²={b2}, ab={ab}. "
        "Now compute a²-ab+b² using these values. "
        "Reply ONLY with the integer result."
    ),
    "partial_scaffold": (
        "Step 1: a={a}, so a²={a2}. Step 2: b={b}, so b²={b2}. "
        "Now compute a²-ab+b². Reply ONLY with the integer result."
    ),
    "step_by_step": (
        "Compute step by step:\n"
        "a = {a}, b = {b}\n"
        "1. a² = {a}² = {a2}\n"
        "2. b² = {b}² = {b2}\n"
        "3. ab = {a} × {b} = {ab}\n"
        "4. Result = a² - ab + b² = {a2} - {ab} + {b2} = ?\n"
        "Reply ONLY with the final integer."
    ),
    "just_arithmetic": (
        "Compute: {a2} - {ab} + {b2} = ?\n"
        "Reply ONLY with the integer result."
    ),
}

def classify_response(response, expected, a, b):
    """Classify the response type."""
    ans = extract_number(response)
    if ans is None:
        return "none", ans
    
    a2, b2, ab_val = a*a, b*b, a*b
    
    if ans == expected:
        return "correct", ans
    elif ans == a or ans == b:
        return "echo_input", ans
    elif ans == a2 or ans == b2:
        return "echo_partial", ans
    elif ans == ab_val:
        return "echo_partial", ans
    elif ans == a + b:
        return "wrong_op_add", ans
    elif ans == a * b:
        return "wrong_op_mult", ans
    elif ans == a2 + b2:
        return "wrong_op_no_minus", ans
    elif ans == a2 - ab_val:
        return "partial_a2_minus_ab", ans
    elif ans == b2 - ab_val:
        return "partial_b2_minus_ab", ans
    else:
        return "other", ans

def run_experiment():
    results = {}
    
    for model_name, model_desc in MODELS.items():
        print(f"\n{'='*70}")
        print(f"MODEL: {model_name} ({model_desc})")
        print(f"{'='*70}")
        
        model_results = {}
        
        for condition, template in PROMPT_TEMPLATES.items():
            correct = 0
            total = 0
            classifications = Counter()
            raw_answers = []
            
            # Use subset of pairs for speed (first 5)
            for a, b in TEST_PAIRS[:5]:
                expected = eisenstein_norm(a, b)
                a2, b2, ab_val = a*a, b*b, a*b
                
                prompt = template.format(a=a, b=b, a2=a2, b2=b2, ab=ab_val)
                
                for trial in range(N_TRIALS):
                    try:
                        response, content, thinking = ask_model(model_name, prompt, 150)
                        rtype, ans = classify_response(response, expected, a, b)
                        classifications[rtype] += 1
                        if rtype == "correct":
                            correct += 1
                        raw_answers.append((a, b, expected, ans, rtype))
                        total += 1
                    except Exception as e:
                        classifications["error"] += 1
                        total += 1
            
            accuracy = correct / total if total > 0 else 0
            model_results[condition] = {
                "accuracy": accuracy,
                "correct": correct,
                "total": total,
                "classifications": dict(classifications),
                "sample_answers": raw_answers[:10],
            }
            
            icon = "✓" if accuracy >= 0.8 else "~" if accuracy >= 0.4 else "✗"
            print(f"\n  {icon} {condition:20s} → {accuracy:.0%} ({correct}/{total})")
            print(f"     Classifications: {dict(classifications.most_common(8))}")
        
        results[model_name] = model_results
    
    return results

def run_deep_probe():
    """Deep probe: test qwen3:4b with JUST arithmetic (no math words)."""
    print(f"\n{'='*70}")
    print("DEEP PROBE: qwen3:4b — Pure Arithmetic (no 'norm', 'Eisenstein')")
    print(f"{'='*70}")
    
    for a, b in TEST_PAIRS[:8]:
        expected = eisenstein_norm(a, b)
        a2, b2, ab_val = a*a, b*b, a*b
        
        # Condition A: just the numbers, no context
        prompt_a = f"{a2} - {ab_val} + {b2} = ?"
        # Condition B: same but with labels
        prompt_b = f"a²={a2}, ab={ab_val}, b²={b2}. a² - ab + b² = ?"
        
        try:
            resp_a, _, _ = ask_model("qwen3:4b", prompt_a, 100)
            resp_b, _, _ = ask_model("qwen3:4b", prompt_b, 100)
            ans_a = extract_number(resp_a)
            ans_b = extract_number(resp_b)
            
            a_ok = "✓" if ans_a == expected else "✗"
            b_ok = "✓" if ans_b == expected else "✗"
            print(f"  ({a:+3d},{b:+3d})→{expected:4d}  bare:{a_ok}{ans_a if ans_a else '?':>6s}  labeled:{b_ok}{ans_b if ans_b else '?':>6s}")
        except Exception as e:
            print(f"  ({a:+3d},{b:+3d}) → ERROR: {e}")

if __name__ == "__main__":
    print("STUDY 9: Combination Scaffolding Experiment")
    print(f"Started: {datetime.now().isoformat()}")
    print(f"Models: {list(MODELS.keys())}")
    print(f"Conditions: {list(PROMPT_TEMPLATES.keys())}")
    print(f"Trials: {N_TRIALS} per condition per pair")
    
    # Run main experiment
    results = run_experiment()
    
    # Run deep probe
    run_deep_probe()
    
    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY: Accuracy by Model × Condition")
    print(f"{'='*70}")
    print(f"{'Condition':20s} | {'qwen3:4b':>10s} | {'phi4-mini':>10s} | {'gemma3:1b':>10s}")
    print("-" * 60)
    for condition in PROMPT_TEMPLATES:
        row = []
        for model in MODELS:
            acc = results[model][condition]["accuracy"]
            row.append(f"{acc:.0%}")
        print(f"{condition:20s} | {row[0]:>10s} | {row[1]:>10s} | {row[2]:>10s}")
    
    # Key hypothesis test
    print(f"\n{'='*70}")
    print("HYPOTHESIS TEST: Does scaffolding rescue qwen3:4b?")
    print(f"{'='*70}")
    q4 = results["qwen3:4b"]
    baseline_acc = q4["baseline"]["accuracy"]
    scaffolded_acc = q4["scaffolded"]["accuracy"]
    just_arith_acc = q4["just_arithmetic"]["accuracy"]
    step_acc = q4["step_by_step"]["accuracy"]
    
    print(f"  Baseline (no help):     {baseline_acc:.0%}")
    print(f"  Scaffolded (sub-results): {scaffolded_acc:.0%}")
    print(f"  Step-by-step (full walk): {step_acc:.0%}")
    print(f"  Just arithmetic (no math words): {just_arith_acc:.0%}")
    
    if scaffolded_acc > baseline_acc + 0.3:
        print(f"\n  ✓ CONFIRMED: Scaffolding rescues qwen3:4b (+{scaffolded_acc-baseline_acc:.0%})")
    elif just_arith_acc > baseline_acc + 0.3:
        print(f"\n  ✓ CONFIRMED: Pure arithmetic rescues qwen3:4b (+{just_arith_acc-baseline_acc:.0%})")
    else:
        print(f"\n  ✗ NOT CONFIRMED: Scaffolding does not significantly help")
        print(f"     The bottleneck may be arithmetic capacity, not combination")
    
    # Save results
    with open("/home/phoenix/.openclaw/workspace/experiments/combination-scaffolding-results.json", "w") as f:
        # Convert Counter objects and tuples for JSON serialization
        clean = {}
        for model, conds in results.items():
            clean[model] = {}
            for cond, data in conds.items():
                clean[model][cond] = {
                    "accuracy": data["accuracy"],
                    "correct": data["correct"],
                    "total": data["total"],
                    "classifications": data["classifications"],
                }
        json.dump(clean, f, indent=2)
    
    print(f"\nResults saved to experiments/combination-scaffolding-results.json")
    print(f"Finished: {datetime.now().isoformat()}")
