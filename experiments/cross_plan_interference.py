#!/usr/bin/env python3
"""
Cross-Plan Interference Experiment
"Same task, three execution plans, three DATA variants — where does interference occur?"

Plan A (COMPUTE): Agent receives formula + inputs, just computes.
Plan B (REASON): Agent receives theoretical context, derives from first principles.
Plan C (VERIFY): Agent receives the claimed answer, checks if it's right.

DATA variants:
  V_COMP: N(a,b)=a²-ab+b², a=4, b=-2 (computational data)
  V_THEORY: Eisenstein norm is the quadratic form on Z[ω] where ω=e^(2πi/3). 
            It equals a²-ab+b² and is always non-negative. (theoretical data)
  V_ANSWER: The Eisenstein norm of (4,-2) equals 28. (claimed answer)

Each plan × each DATA variant = 9 conditions. 5 trials each.
The interference pattern reveals itself in the cross-conditions.
"""

import requests
from collections import Counter
import math

MODEL = "phi4-mini"

def query(prompt, max_tokens=100):
    resp = requests.post("http://localhost:11434/api/chat", json={
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"num_predict": max_tokens}
    }, timeout=120)
    return resp.json()["message"]["content"]

TARGET = "28"

# 9 conditions: 3 plans × 3 DATA variants
CONDITIONS = [
    # Plan A (COMPUTE) with each DATA
    ("A_COMP", "COMPUTE", "V_COMP",
     """Execute this computation:

DO: Compute the Eisenstein norm of (4, -2)
DATA: N(a,b) = a² - ab + b², a=4, b=-2
DONE: Reply with ONLY the integer answer."""),
    
    ("A_THEORY", "COMPUTE", "V_THEORY",
     """Execute this computation:

DO: Compute the Eisenstein norm of (4, -2)
DATA: The Eisenstein norm is the quadratic form on Z[ω] where ω=e^(2πi/3). It equals a²-ab+b² and is always non-negative.
DONE: Reply with ONLY the integer answer."""),
    
    ("A_ANSWER", "COMPUTE", "V_ANSWER",
     """Execute this computation:

DO: Compute the Eisenstein norm of (4, -2)
DATA: The Eisenstein norm of (4,-2) equals 28.
DONE: Reply with ONLY the integer answer."""),
    
    # Plan B (REASON) with each DATA
    ("B_COMP", "REASON", "V_COMP",
     """Reason through this step by step:

DO: Derive the Eisenstein norm of (4, -2) from the definition
DATA: N(a,b) = a² - ab + b², a=4, b=-2
DONE: Show your reasoning, then give the final integer answer."""),
    
    ("B_THEORY", "REASON", "V_THEORY",
     """Reason through this step by step:

DO: Derive the Eisenstein norm of (4, -2) from the definition
DATA: The Eisenstein norm is the quadratic form on Z[ω] where ω=e^(2πi/3). It equals a²-ab+b² and is always non-negative.
DONE: Show your reasoning, then give the final integer answer."""),
    
    ("B_ANSWER", "REASON", "V_ANSWER",
     """Reason through this step by step:

DO: Derive the Eisenstein norm of (4, -2) from the definition
DATA: The Eisenstein norm of (4,-2) equals 28.
DONE: Show your reasoning, then give the final integer answer."""),
    
    # Plan C (VERIFY) with each DATA
    ("C_COMP", "VERIFY", "V_COMP",
     """Verify this claim by independent computation:

DO: Verify that the Eisenstein norm of (4, -2) equals 28
DATA: N(a,b) = a² - ab + b², a=4, b=-2
DONE: Reply VERIFIED or FAILED, then show the computation."""),
    
    ("C_THEORY", "VERIFY", "V_THEORY",
     """Verify this claim using theoretical reasoning:

DO: Verify that the Eisenstein norm of (4, -2) equals 28
DATA: The Eisenstein norm is the quadratic form on Z[ω] where ω=e^(2πi/3). It equals a²-ab+b² and is always non-negative.
DONE: Reply VERIFIED or FAILED, then show your reasoning."""),
    
    ("C_ANSWER", "VERIFY", "V_ANSWER",
     """Verify this claim by checking the provided answer:

DO: Verify that the Eisenstein norm of (4, -2) equals 28
DATA: The Eisenstein norm of (4,-2) equals 28.
DONE: Reply VERIFIED or FAILED, then explain why."""),
]

N_TRIALS = 5

def run_cross_plan():
    print("=" * 70)
    print("CROSS-PLAN INTERFERENCE EXPERIMENT")
    print("3 plans × 3 DATA variants = 9 conditions × 5 trials")
    print("=" * 70)
    print()
    
    results = {}
    
    for cond_id, plan, data_type, prompt in CONDITIONS:
        scores = []
        answers = []
        for trial in range(N_TRIALS):
            try:
                resp = query(prompt, 150)
                correct = TARGET in resp
                scores.append(correct)
                # Extract the answer (look for number)
                import re
                nums = re.findall(r'\b\d+\b', resp)
                answer = nums[0] if nums else resp[:30]
                answers.append(answer)
            except Exception as e:
                scores.append(False)
                answers.append(f"ERROR: {e}")
        
        pass_rate = sum(scores) / len(scores)
        results[cond_id] = {
            "plan": plan,
            "data": data_type,
            "pass_rate": pass_rate,
            "answers": answers,
        }
        
        icon = "✓" if pass_rate >= 0.8 else "~" if pass_rate >= 0.4 else "✗"
        ans_dist = Counter(answers)
        print(f"  {icon} {cond_id:10s} ({plan:8s} × {data_type:8s}): {pass_rate:.0%}")
        for ans, count in ans_dist.most_common(3):
            print(f"      {count}× {ans[:40]}")
        print()
    
    # INTERFERENCE MATRIX
    print("=" * 70)
    print("INTERFERENCE MATRIX")
    print("=" * 70)
    print()
    
    plans = ["COMPUTE", "REASON", "VERIFY"]
    datas = ["V_COMP", "V_THEORY", "V_ANSWER"]
    
    print(f"  {'':10s}", end="")
    for d in datas:
        print(f" {d:10s}", end="")
    print()
    
    for plan in plans:
        print(f"  {plan:10s}", end="")
        for data in datas:
            key = f"{plan[0]}_{data.split('_')[1]}"
            r = results.get(key, {})
            rate = r.get("pass_rate", 0)
            bar = "█" * int(rate * 10)
            print(f" {rate:.0%} {bar:10s}", end="")
        print()
    
    print()
    
    # Find interference patterns
    print("=" * 70)
    print("INTERFERENCE ANALYSIS")
    print("=" * 70)
    print()
    
    # Diagonal (plan matches data type) vs off-diagonal (plan mismatches data)
    diagonal = [
        results["A_COMP"]["pass_rate"],   # COMPUTE with computational data
        results["B_THEORY"]["pass_rate"],  # REASON with theoretical data
        results["C_ANSWER"]["pass_rate"], # VERIFY with answer data
    ]
    off_diagonal = [results[k]["pass_rate"] for k in results if k not in ["A_COMP", "B_THEORY", "C_ANSWER"]]
    
    diag_avg = sum(diagonal) / len(diagonal)
    off_avg = sum(off_diagonal) / len(off_diagonal)
    
    print(f"  Diagonal (plan↔data aligned): {diag_avg:.0%}")
    print(f"  Off-diagonal (plan↔data misaligned): {off_avg:.0%}")
    print(f"  Interference penalty: {off_avg - diag_avg:+.0%}")
    print()
    
    if off_avg < diag_avg - 0.15:
        print("  ✅ CROSS-PLAN INTERFERENCE CONFIRMED")
        print("  Data aligned with plan scores higher than misaligned data.")
        print("  → Fleet needs PLAN-AWARE DATA ROUTING")
        print("  → Same task needs different DATA for different execution plans")
    elif off_avg > diag_avg + 0.15:
        print("  ⚠️ REVERSE INTERFERENCE — misalignment HELPS")
        print("  Cross-plan data injection provides useful diversity")
        print("  → Fleet benefits from plan-diverse DATA")
    else:
        print("  ❌ NO CROSS-PLAN INTERFERENCE")
        print("  Data effectiveness is independent of execution plan")
        print("  → Simple model-aware templates sufficient (no plan-awareness needed)")
    
    # Also check: does the answer propagation effect (R8) vary by plan?
    answer_conditions = {k: v for k, v in results.items() if v["data"] == "V_ANSWER"}
    print()
    print("  Answer propagation by plan:")
    for k, v in answer_conditions.items():
        print(f"    {v['plan']:10s}: {v['pass_rate']:.0%} (answer in DATA)")
    
    return results


if __name__ == "__main__":
    run_cross_plan()
