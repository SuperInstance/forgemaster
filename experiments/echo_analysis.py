#!/usr/bin/env python3
"""
THE NOISE THAT'S NOT NOISE — Echo Analysis
============================================
Key finding from the time study: wrong answers aren't random. Models echo 
input numbers. N(5,-3) → answers cluster around 5, -3, 9, 25 (all from the prompt).
N(4,-2) → answers cluster around 4, -2, 16, 2 (all from the prompt).

This is ECHO — the model parroting its input instead of computing.

Study 5: Measure echo rate across models and task types.
Study 6: Can we detect echo vs computation from the answer distribution alone?
Study 7: Does the "not noise" carry information about what the model understood?
"""

import requests
import re
from collections import Counter
import math

def query(model, prompt, max_tokens=60):
    try:
        resp = requests.post("http://localhost:11434/api/chat", json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"num_predict": max_tokens}
        }, timeout=120)
        return resp.json()["message"]["content"]
    except Exception as e:
        return f"ERROR: {e}"

def extract_number(text):
    nums = re.findall(r'-?\d+', text)
    return nums[-1] if nums else None

def is_echo(answer, prompt_nums):
    """Is the answer one of the numbers from the prompt?"""
    if answer is None:
        return False
    return answer in prompt_nums

def run_echo_study():
    print("=" * 70)
    print("STUDY 5: ECHO ANALYSIS — The Noise That's Not Noise")
    print("=" * 70)
    print()
    print("Hypothesis: Wrong answers are NOT random noise. They echo input numbers.")
    print("If true, the 'noise' carries information about what the model attended to.")
    print()
    
    models = ["phi4-mini", "gemma3:1b", "llama3.2:1b", "qwen3:0.6b"]
    
    # Tasks with known correct answers and identifiable input numbers
    tasks = [
        {
            "name": "N(5,-3)=49",
            "prompt": "Compute N(5,-3) where N(a,b)=a²-ab+b². Reply ONLY integer.",
            "target": "49",
            "input_nums": ["5", "-3", "2"],  # numbers in the prompt
        },
        {
            "name": "N(4,-2)=28",
            "prompt": "Compute N(4,-2) where N(a,b)=a²-ab+b². Reply ONLY integer.",
            "target": "28",
            "input_nums": ["4", "-2", "2"],
        },
        {
            "name": "N(7,3)=37",
            "prompt": "Compute N(7,3) where N(a,b)=a²-ab+b². Reply ONLY integer.",
            "target": "37",
            "input_nums": ["7", "3", "2"],
        },
        {
            "name": "N(6,-4)=64",
            "prompt": "Compute N(6,-4) where N(a,b)=a²-ab+b². Reply ONLY integer.",
            "target": "64",
            "input_nums": ["6", "-4", "2"],
        },
        {
            "name": "11×13=143",
            "prompt": "What is 11 × 13? Reply ONLY integer.",
            "target": "143",
            "input_nums": ["11", "13"],
        },
        {
            "name": "23+19=42",
            "prompt": "What is 23 + 19? Reply ONLY integer.",
            "target": "42",
            "input_nums": ["23", "19"],
        },
    ]
    
    N = 10
    all_echo_rates = {}
    
    for task in tasks:
        print(f"  {task['name']}: target={task['target']}, inputs={task['input_nums']}")
        
        for model in models:
            answers = []
            for _ in range(N):
                ans = extract_number(query(model, task["prompt"], 60))
                answers.append(ans)
            
            correct = sum(1 for a in answers if a == task["target"]) / N
            echo = sum(1 for a in answers if is_echo(a, task["input_nums"])) / N
            dist = Counter(answers)
            
            # Classify each wrong answer
            wrong = [a for a in answers if a != task["target"]]
            wrong_echo = sum(1 for a in wrong if is_echo(a, task["input_nums"]))
            wrong_total = len(wrong)
            echo_of_wrong = wrong_echo / wrong_total if wrong_total > 0 else 0
            
            all_echo_rates[(task["name"], model)] = {
                "correct": correct,
                "echo": echo,
                "echo_of_wrong": echo_of_wrong,
                "dist": dict(dist.most_common(5)),
            }
            
            icon = "✓" if correct >= 0.8 else "~" if correct >= 0.4 else "✗"
            echo_bar = "▓" * int(echo_of_wrong * 10) + "░" * (10 - int(echo_of_wrong * 10))
            print(f"    {icon} {model:15s}: correct={correct:.0%} echo_of_wrong={echo_of_wrong:.0%} {echo_bar}")
            if wrong_total > 0:
                non_echo_wrong = [a for a in wrong if not is_echo(a, task["input_nums"])]
                if non_echo_wrong:
                    ne_dist = Counter(non_echo_wrong)
                    print(f"        Non-echo wrong: {dict(ne_dist.most_common(3))}")
                    # Are the non-echo wrong answers partial computations?
                    # e.g., for N(5,-3): a²=25 (partial), b²=9 (partial)
                    partials = []
                    for a in non_echo_wrong:
                        try:
                            n = int(a)
                            # Check if it's a², b², ab, a+b, a-b from the inputs
                            # For N(a,b): a², b², ab are partial results
                            pass
                        except:
                            pass
        print()
    
    # ============================================================
    # META-ANALYSIS
    # ============================================================
    print("=" * 70)
    print("META-ANALYSIS: What the echo tells us")
    print("=" * 70)
    print()
    
    # Aggregate echo rates by model
    for model in models:
        rates = [all_echo_rates[(t["name"], model)]["echo_of_wrong"]
                 for t in tasks 
                 if (t["name"], model) in all_echo_rates 
                 and all_echo_rates[(t["name"], model)]["correct"] < 0.8]
        if rates:
            avg_echo = sum(rates) / len(rates)
            print(f"  {model:15s}: avg echo-of-wrong = {avg_echo:.0%} ({len(rates)} failing tasks)")
        else:
            print(f"  {model:15s}: all tasks correct (no wrong answers to analyze)")
    
    print()
    print("  INTERPRETATION:")
    print()
    print("  If echo-of-wrong is HIGH (>60%):")
    print("    → Wrong answers are mostly ECHO (model can't compute, parrots inputs)")
    print("    → The 'noise' IS structured — it reveals what the model attended to")
    print("    → This is NOT noise, it's a SYSTEMATIC COGNITIVE ARTIFACT")
    print("    → Fleet implication: wrong answers carry diagnostic information")
    print()
    print("  If echo-of-wrong is LOW (<30%):")
    print("    → Wrong answers are genuine errors (model computes but makes mistakes)")
    print("    → The 'noise' is closer to random")
    print("    → Fleet implication: wrong answers are less informative")
    print()
    
    # ============================================================
    # STUDY 6: CAN WE DETECT ECHO FROM DISTRIBUTION ALONE?
    # ============================================================
    print("=" * 70)
    print("STUDY 6: ECHO DETECTION — can we identify echo without the prompt?")
    print("=" * 70)
    print()
    print("  For each model × task, check if answer distribution peaks at input numbers:")
    print()
    
    for model in models:
        print(f"  {model}:")
        for task in tasks:
            key = (task["name"], model)
            if key not in all_echo_rates:
                continue
            dist = all_echo_rates[key]["dist"]
            correct = all_echo_rates[key]["correct"]
            if correct >= 0.8:
                continue  # skip correct conditions
            
            # Top answer — is it an input number?
            if dist:
                top_ans, top_count = list(dist.items())[0]
                is_input = top_ans in task["input_nums"]
                marker = "← ECHO PEAK" if is_input else "← COMPUTED (wrong)"
                if top_ans == task["target"]:
                    marker = "← CORRECT"
                print(f"    {task['name']:15s}: top={top_ans:5s} ({top_count}×) {marker}")
        print()
    
    # ============================================================
    # STUDY 7: ATTENTION ARCHAEOLOGY
    # What does the echo pattern reveal about model attention?
    # ============================================================
    print("=" * 70)
    print("STUDY 7: ATTENTION ARCHAEOLOGY")
    print("Reading wrong answers as attention traces")
    print("=" * 70)
    print()
    
    # Deep dive on N(5,-3)=49 for phi4-mini
    print("  Deep dive: N(5,-3)=49, phi4-mini, 30 trials")
    answers = []
    for _ in range(30):
        ans = extract_number(query("phi4-mini", 
            "Compute N(5,-3) where N(a,b)=a²-ab+b². Reply ONLY integer.", 60))
        answers.append(ans)
    
    dist = Counter(answers)
    print(f"  Distribution: {dict(dist.most_common(8))}")
    print()
    
    # Classify each answer
    input_nums = ["5", "-3"]
    squares = {"25": "a²", "9": "b²"}
    products = {"-15": "ab"}
    
    for ans, count in dist.most_common(8):
        classification = []
        if ans == "49": classification.append("CORRECT")
        if ans in input_nums: classification.append("ECHO_INPUT")
        if ans in squares: classification.append(f"PARTIAL({squares.get(ans, '?')})")
        if ans in products: classification.append(f"PARTIAL({products.get(ans, '?')})")
        if not classification: classification.append("UNKNOWN")
        
        print(f"    {count:2d}× {ans:5s} → {' + '.join(classification)}")
    
    print()
    print("  Reading: Each wrong answer reveals which part of the computation")
    print("  the model performed before failing. The distribution IS a trace")
    print("  of the model's attention and partial computation state.")
    print()
    print("  This is the 'noise that's not noise' — it's a COGNITIVE RESIDUE.")
    print("  Fleet implication: Collect wrong answers across agents. The")
    print("  residue pattern tells you WHERE computation failed, not just THAT it failed.")


if __name__ == "__main__":
    run_echo_study()
