#!/usr/bin/env python3
"""
Study 10: Stage 4 Boundary — Finding the Computation Threshold

Yesterday's echo analysis established:
- Stage 1 (<1B): NONE
- Stage 2 (1-3B): ECHO
- Stage 3 (~4B): PARTIAL  
- Stage 4 (7B+): FULL (hypothesized, untested)

This test fires the same Eisenstein norm computation at API models across
the 4B-70B range to find where FULL computation kicks in.

Also tests the scaffolding hypothesis: does the same scaffold pattern 
(scaffold helps non-thinking, hurts thinking) hold at larger scale?
"""

import json
import os
import re
import sys
import time
import urllib.request

CRED_DIR = os.path.expanduser("~/.openclaw/workspace/.credentials")

def load_key(name):
    with open(os.path.join(CRED_DIR, name)) as f:
        return f.read().strip()

DEEPINFRA_KEY = load_key("deepinfra-api-key.txt")

MODELS = [
    # Small-medium (should be Stage 3-4 boundary)
    ("Qwen/Qwen3-235B-A22B-Instruct-2507", "Qwen3-235B MoE (~22B active)", 235),
    ("Qwen/Qwen3.6-35B-A3B", "Qwen3.6-35B MoE (~3B active)", 35),
    ("NousResearch/Hermes-3-Llama-3.1-70B", "Hermes-70B dense", 70),
    ("NousResearch/Hermes-3-Llama-3.1-405B", "Hermes-405B dense", 405),
    ("ByteDance/Seed-2.0-mini", "Seed-2.0-mini", 0),  # unknown params
    ("ByteDance/Seed-2.0-code", "Seed-2.0-code", 0),
]

TEST_PAIRS = [
    (5, -3),   # 49
    (7, 2),    # 49  
    (-4, -6),  # 28
    (10, -1),  # 111
    (6, 9),    # 63
    (-2, 7),   # 67
    (0, 5),    # 25
    (8, -4),   # 112
]

def eisenstein_norm(a, b):
    return a*a - a*b + b*b

def extract_number(text):
    nums = re.findall(r'-?\d+', text)
    return int(nums[-1]) if nums else None

def ask_deepinfra(model, prompt, max_tokens=200):
    url = "https://api.deepinfra.com/v1/openai/chat/completions"
    data = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.1,
    }).encode()
    req = urllib.request.Request(url, data=data, headers={
        "Authorization": f"Bearer {DEEPINFRA_KEY}",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
            return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"ERROR: {e}"

def classify_response(response, expected, a, b):
    ans = extract_number(response)
    if ans is None:
        return "none", ans
    a2, b2, ab_val = a*a, b*b, a*b
    if ans == expected:
        return "correct", ans
    elif ans in (a, b):
        return "echo_input", ans
    elif ans in (a2, b2, ab_val):
        return "echo_partial", ans
    elif ans == a2 + b2:
        return "wrong_op_no_minus", ans
    elif ans == a2 - ab_val:
        return "partial_a2_minus_ab", ans
    elif ans == a + b:
        return "wrong_op_add", ans
    else:
        return "other", ans

def run():
    print("STUDY 10: Stage 4 Boundary — API Model Survey")
    print(f"Models: {len(MODELS)}")
    print(f"Test pairs: {len(TEST_PAIRS)}")
    print()
    
    CONDITIONS = {
        "baseline": "Compute the Eisenstein norm of the Eisenstein integer ({a} + {b}ω). The formula is a²-ab+b² where a={a} and b={b}. Reply ONLY with the integer result, nothing else.",
        "just_arithmetic": "Compute: {a2} - {ab} + {b2} = ?\nReply ONLY with the integer result.",
    }
    
    all_results = {}
    
    for model_id, model_name, param_b in MODELS:
        print(f"{'='*60}")
        print(f"MODEL: {model_name} ({model_id})")
        print(f"{'='*60}")
        
        model_results = {}
        
        for cond_name, template in CONDITIONS.items():
            correct = 0
            total = 0
            classes = {}
            
            for a, b in TEST_PAIRS:
                expected = eisenstein_norm(a, b)
                a2, b2, ab_val = a*a, b*b, a*b
                prompt = template.format(a=a, b=b, a2=a2, b2=b2, ab=ab_val)
                
                response = ask_deepinfra(model_id, prompt)
                rtype, ans = classify_response(response, expected, a, b)
                classes[rtype] = classes.get(rtype, 0) + 1
                if rtype == "correct":
                    correct += 1
                total += 1
                
                # Small delay to avoid rate limits
                time.sleep(0.5)
            
            acc = correct / total if total > 0 else 0
            model_results[cond_name] = {"accuracy": acc, "correct": correct, "total": total, "classes": classes}
            
            icon = "✓" if acc >= 0.8 else "~" if acc >= 0.4 else "✗"
            print(f"  {icon} {cond_name:20s} → {acc:.0%} ({correct}/{total}) classes={classes}")
        
        all_results[model_name] = model_results
        print()
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY: Stage Classification")
    print(f"{'='*60}")
    for model_name, results in all_results.items():
        baseline_acc = results["baseline"]["accuracy"]
        arith_acc = results["just_arithmetic"]["accuracy"]
        
        if baseline_acc >= 0.8:
            stage = "Stage 4 (FULL)"
        elif baseline_acc >= 0.4:
            stage = "Stage 3-4 transition"
        elif arith_acc > baseline_acc + 0.2:
            stage = "Stage 3 (META-ECHO — math vocab hurts)"
        elif arith_acc >= 0.4:
            stage = "Stage 3 (PARTIAL)"
        else:
            stage = "Stage 2 (ECHO)"
        
        print(f"  {model_name:40s} baseline={baseline_acc:.0%} arith={arith_acc:.0%} → {stage}")
    
    # Save
    with open("/home/phoenix/.openclaw/workspace/experiments/stage4-boundary-results.json", "w") as f:
        clean = {}
        for mn, res in all_results.items():
            clean[mn] = {}
            for cn, data in res.items():
                clean[mn][cn] = {k: v for k, v in data.items()}
        json.dump(clean, f, indent=2)
    print(f"\nSaved to experiments/stage4-boundary-results.json")

if __name__ == "__main__":
    run()
