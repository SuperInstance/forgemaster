#!/usr/bin/env python3
"""
Spoke 7: The Partial-Data Death Zone
"Why does showing intermediate steps WITHOUT the answer crash accuracy to 0%?"

Grounding: Spoke 5 showed Level 3 (partial worked: a²=16, ab=-8, b²=4 but NOT the sum)
           scored 0%. Level 2 (formula + inputs) scored 67%. Level 4 (full worked) scored 67%.
           
           There is a DEATH ZONE between "enough context" and "too much partial context."
           This experiment maps it precisely.

Hypothesis: The model treats partial intermediates as CORRECTIONS to the formula.
            When it sees "ab = -8" it thinks "the formula is wrong, ab should be -8"
            and re-derives everything from scratch, getting confused.

Experiment: Systematically vary what's included in DATA.
            Map the exact boundary of the death zone.
"""

import requests

MODEL = "phi4-mini"

def query(prompt, max_tokens=100):
    resp = requests.post("http://localhost:11434/api/chat", json={
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"num_predict": max_tokens}
    }, timeout=120)
    return resp.json()["message"]["content"]

TARGET = "28"  # N(4,-2) = 16+8+4 = 28

# 12 DATA variants, each adding or removing one element
VARIANTS = [
    {
        "name": "formula_only",
        "data": "N(a,b) = a² - ab + b²",
        "includes_answer": False,
        "includes_intermediates": False,
        "includes_inputs": False,
    },
    {
        "name": "formula+inputs",
        "data": "N(a,b) = a² - ab + b², a=4, b=-2",
        "includes_answer": False,
        "includes_intermediates": False,
        "includes_inputs": True,
    },
    {
        "name": "formula+inputs+a²",
        "data": "N(a,b) = a² - ab + b², a=4, b=-2\na² = 16",
        "includes_answer": False,
        "includes_intermediates": True,
        "includes_inputs": True,
    },
    {
        "name": "formula+inputs+ab_val",
        "data": "N(a,b) = a² - ab + b², a=4, b=-2\nab = (4)(-2) = -8",
        "includes_answer": False,
        "includes_intermediates": True,
        "includes_inputs": True,
    },
    {
        "name": "formula+inputs+b²",
        "data": "N(a,b) = a² - ab + b², a=4, b=-2\nb² = 4",
        "includes_answer": False,
        "includes_intermediates": True,
        "includes_inputs": True,
    },
    {
        "name": "formula+inputs+all_intermediates",
        "data": "N(a,b) = a² - ab + b², a=4, b=-2\na² = 16, ab = -8, b² = 4",
        "includes_answer": False,
        "includes_intermediates": True,
        "includes_inputs": True,
    },
    {
        "name": "formula+inputs+all_intermediates+sum_signs",
        "data": "N(a,b) = a² - ab + b², a=4, b=-2\na² = 16, -ab = 8, b² = 4\nSum: 16 + 8 + 4",
        "includes_answer": False,
        "includes_intermediates": True,
        "includes_inputs": True,
    },
    {
        "name": "formula+inputs+all_intermediates+answer_wrong",
        "data": "N(a,b) = a² - ab + b², a=4, b=-2\na² = 16, ab = -8, b² = 4\nResult = 12",
        "includes_answer": True,  # WRONG answer!
        "includes_intermediates": True,
        "includes_inputs": True,
    },
    {
        "name": "formula+inputs+answer_only",
        "data": "N(a,b) = a² - ab + b², a=4, b=-2\nResult = 28",
        "includes_answer": True,
        "includes_intermediates": False,
        "includes_inputs": True,
    },
    {
        "name": "full_worked",
        "data": "N(a,b) = a² - ab + b²\na=4, b=-2\nN = 16 - (4)(-2) + 4 = 16 + 8 + 4 = 28",
        "includes_answer": True,
        "includes_intermediates": True,
        "includes_inputs": True,
    },
    {
        "name": "answer_only_no_formula",
        "data": "The answer is 28.",
        "includes_answer": True,
        "includes_intermediates": False,
        "includes_inputs": False,
    },
    {
        "name": "wrong_answer_only",
        "data": "The answer is 27.",
        "includes_answer": True,  # WRONG
        "includes_intermediates": False,
        "includes_inputs": False,
    },
]


def run_spoke_7():
    print("=" * 70)
    print("SPOKE 7: The Partial-Data Death Zone")
    print("Mapping the exact boundary where DATA hurts")
    print("=" * 70)
    print()
    
    results = []
    
    for variant in VARIANTS:
        prompt = f"""Compute the Eisenstein norm of (4, -2).

DATA: {variant['data']}

DONE: Reply with ONLY the integer answer."""
        
        scores = []
        responses = []
        for trial in range(3):
            try:
                resp = query(prompt, 60)
                correct = TARGET in resp
                scores.append(correct)
                responses.append(resp[:80])
            except Exception as e:
                scores.append(False)
                responses.append(f"ERROR: {e}")
        
        pass_rate = sum(scores) / len(scores)
        results.append({**variant, "pass_rate": pass_rate, "responses": responses})
        
        # Visual: death zone marker
        icon = "✓" if pass_rate >= 0.66 else "☠️" if pass_rate == 0 else "~"
        answer_tag = "ANS" if variant["includes_answer"] else "   "
        inter_tag = "INT" if variant["includes_intermediates"] else "   "
        input_tag = "INP" if variant["includes_inputs"] else "   "
        
        print(f"  {icon} {variant['name']:40s} ({answer_tag} {inter_tag} {input_tag}): "
              f"{pass_rate:.0%}")
        for i, resp in enumerate(responses):
            c = "✓" if scores[i] else "✗"
            print(f"      {c} {resp}")
        print()
    
    # Death zone analysis
    print("=" * 70)
    print("DEATH ZONE MAP")
    print("=" * 70)
    print()
    
    # Group by pattern
    for includes_answer in [False, True]:
        for includes_intermediates in [False, True]:
            for includes_inputs in [False, True]:
                group = [r for r in results 
                         if r["includes_answer"] == includes_answer 
                         and r["includes_intermediates"] == includes_intermediates
                         and r["includes_inputs"] == includes_inputs]
                if group:
                    avg = sum(r["pass_rate"] for r in group) / len(group)
                    ans = "A" if includes_answer else "-"
                    inter = "I" if includes_intermediates else "-"
                    inp = "D" if includes_inputs else "-"
                    bar = "█" * int(avg * 20)
                    dead = " ☠️ DEATH ZONE" if avg == 0 else ""
                    print(f"  [{ans}{inter}{inp}] {avg:.0%} {bar:20s}{dead}")
    
    print()
    print("Key: A=includes answer, I=includes intermediates, D=includes input values")
    print()
    
    # Check: does the WRONG answer in DATA corrupt the model?
    wrong_answer = [r for r in results if r["name"] == "wrong_answer_only"]
    correct_answer = [r for r in results if r["name"] == "answer_only_no_formula"]
    
    if wrong_answer and correct_answer:
        print(f"  Wrong answer only: {wrong_answer[0]['pass_rate']:.0%}")
        print(f"  Right answer only: {correct_answer[0]['pass_rate']:.0%}")
        if wrong_answer[0]['pass_rate'] > 0:
            print("  ⚠️ MODEL TRUSTS PROVIDED ANSWER EVEN WHEN WRONG")
            print("  → Providing answers in DATA can INTRODUCE errors!")
    
    print()
    print("SPOKE 7 → NEXT:")
    print("  If death zone is intermediates-only → never show partial steps")
    print("  If death zone is answer-corruption → never show answers in DATA")
    print("  If death zone is universal → DATA should be minimal (formula + inputs only)")


if __name__ == "__main__":
    run_spoke_7()
