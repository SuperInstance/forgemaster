#!/usr/bin/env python3
"""
Spoke 5: The DATA Sufficiency Boundary
"How much DATA is enough for DO/DATA/DONE?"

Grounding: Exp 1 showed DATA matters more than FORMAT (3.0/3 vs 2.0/3).
           But we never tested: what's the MINIMUM DATA that still works?
           Is more DATA always better? Or is there a cliff?

This is the most practical spoke — it determines tile size budget.

Experiment: Vary DATA completeness from 0% (just the formula name)
            to 100% (full worked example). Find the cliff.
"""

import requests
import json

MODEL = "phi4-mini"

def query(prompt, max_tokens=200):
    resp = requests.post("http://localhost:11434/api/chat", json={
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"num_predict": max_tokens}
    }, timeout=120)
    return resp.json()["message"]["content"]

# Task: Compute Eisenstein norm of (4,-2)
# Correct answer: 16 + 8 + 4 = 28

DATA_LEVELS = [
    {
        "level": 0,
        "name": "formula_name_only",
        "prompt": """Execute this task:

DO: Compute the Eisenstein norm of the point (4, -2)

DATA: Eisenstein norm formula

DONE: Single integer answer""",
        "tokens_approx": 20,
    },
    {
        "level": 1,
        "name": "formula_expression",
        "prompt": """Execute this task:

DO: Compute the Eisenstein norm of the point (4, -2)

DATA: N(a,b) = a² - ab + b²

DONE: Single integer answer""",
        "tokens_approx": 30,
    },
    {
        "level": 2,
        "name": "formula_with_inputs",
        "prompt": """Execute this task:

DO: Compute the Eisenstein norm of the point (4, -2)

DATA: N(a,b) = a² - ab + b², where a=4, b=-2

DONE: Single integer answer""",
        "tokens_approx": 35,
    },
    {
        "level": 3,
        "name": "partial_worked",
        "prompt": """Execute this task:

DO: Compute the Eisenstein norm of the point (4, -2)

DATA: N(a,b) = a² - ab + b²
a=4, b=-2
a² = 16, ab = -8, b² = 4

DONE: Single integer answer""",
        "tokens_approx": 50,
    },
    {
        "level": 4,
        "name": "full_worked",
        "prompt": """Execute this task:

DO: Compute the Eisenstein norm of the point (4, -2)

DATA: N(a,b) = a² - ab + b²
a=4, b=-2
N = 16 - (4)(-2) + 4 = 16 + 8 + 4 = 28

DONE: Single integer answer""",
        "tokens_approx": 60,
    },
    {
        "level": 5,
        "name": "overloaded",
        "prompt": """Execute this task:

DO: Compute the Eisenstein norm of the point (4, -2)

DATA: The Eisenstein norm N(a,b) = a² - ab + b² is a quadratic form on the ring Z[ω] where ω = e^(2πi/3).
This norm is always non-negative and equals zero only when (a,b) = (0,0).
For the point (4, -2): N(4,-2) = 4² - 4(-2) + (-2)² = 16 + 8 + 4 = 28.
The Eisenstein integers form a hexagonal lattice in the complex plane.
Related formulas: hex_distance(a,b,c,d) = max(|da|, |db|, |da+db|).
For reference: N(3,-1)=13, N(2,3)=7, N(1,0)=1.

DONE: Single integer answer""",
        "tokens_approx": 120,
    },
]

def run_data_sufficiency():
    print("=" * 70)
    print("SPOKE 5: The DATA Sufficiency Boundary")
    print("How much DATA is enough for DO/DATA/DONE?")
    print("=" * 70)
    print()
    
    TARGET_ANSWER = "28"
    
    # Run each level 3 times to reduce noise
    results = []
    for data_level in DATA_LEVELS:
        level_results = []
        for trial in range(3):
            try:
                resp = query(data_level["prompt"], 100)
                correct = TARGET_ANSWER in resp
                level_results.append({
                    "response": resp[:100],
                    "correct": correct,
                })
            except Exception as e:
                level_results.append({"response": f"ERROR: {e}", "correct": False})
        
        pass_rate = sum(1 for r in level_results if r["correct"]) / len(level_results)
        results.append({
            "level": data_level["level"],
            "name": data_level["name"],
            "tokens": data_level["tokens_approx"],
            "pass_rate": pass_rate,
            "responses": [r["response"] for r in level_results],
        })
        
        icon = "✓" if pass_rate >= 0.66 else "✗"
        print(f"  Level {data_level['level']} ({data_level['name']:20s}, ~{data_level['tokens_approx']:3d} tokens): "
              f"{pass_rate:.0%} {icon}")
        for resp in level_results:
            c = "✓" if TARGET_ANSWER in resp["response"] else "✗"
            print(f"    {c} {resp['response'][:80]}")
        print()
    
    # Find the cliff
    print("=" * 70)
    print("THE CLIFF")
    print("=" * 70)
    
    for i in range(1, len(results)):
        delta = results[i]["pass_rate"] - results[i-1]["pass_rate"]
        if delta > 0.3:
            print(f"  CLIFF at level {results[i-1]['level']} → {results[i]['level']}: "
                  f"+{delta:.0%} ({results[i-1]['pass_rate']:.0%} → {results[i]['pass_rate']:.0%})")
    
    # Find minimum sufficient level
    for r in results:
        if r["pass_rate"] >= 0.66:
            print(f"  MINIMUM SUFFICIENT: Level {r['level']} ({r['name']}, ~{r['tokens']} tokens, {r['pass_rate']:.0%})")
            break
    
    # Find degradation from overload
    if results[-1]["pass_rate"] < results[-2]["pass_rate"]:
        print(f"  OVERLOAD DEGRADATION: Level {results[-2]['level']} → {results[-1]['level']}: "
              f"{results[-2]['pass_rate']:.0%} → {results[-1]['pass_rate']:.0%}")
        print("  → More context can HURT (confirms DEEP-RESULTS Exp 2)")
    
    print()
    print("SPOKE 5 → NEXT SPOKES:")
    print("  If cliff at level 2 → Spoke 6: Optimize tile size to formula + inputs")
    print("  If cliff at level 0 → Spoke 7: Models know the formula already, DATA is optional")
    print("  If overload hurts → Spoke 8: Token budget per task type")
    
    return results


if __name__ == "__main__":
    run_data_sufficiency()
