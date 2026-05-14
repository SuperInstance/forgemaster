#!/usr/bin/env python3
"""
THE SHALLOW-SIDE CONSTRAINT — Bathymetric Routing Experiment
============================================================

Casey's bathymetric chart never snaps to the deep side of truth.
The shallowest integer in the uncertainty range is the sounding.

Applied to fleet routing: when models disagree, don't average.
Take the minimum-depth answer — the one closest to "can't compute."

If 3 agents answer [2, 2, 49] for N(5,-3)=49:
  - AVERAGE route: majority vote → 2 (echo consensus, WRONG)
  - SHALLOW route: read residue → 2 is echo (can't compute), 49 is computation
    → trust the computation, not the echo

If 3 agents answer [25, 9, -15] for N(5,-3)=49:
  - AVERAGE route: no agreement, all wrong
  - SHALLOW route: all are PARTIAL (a², b², ab) → model can compute steps but not combine
    → provide combination scaffolding, retry once

The shallow-side constraint: always route based on the WORST CASE interpretation
of the evidence, because the cost of overestimating model capability (deep side)
is catastrophic (wrong answer accepted), while underestimating (shallow side) 
just costs an extra verification.
"""

import requests
import re
from collections import Counter

def query(model, prompt, max_tokens=80):
    try:
        resp = requests.post("http://localhost:11434/api/chat", json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"num_predict": max_tokens}
        }, timeout=120)
        return resp.json()["message"]["content"]
    except:
        return ""

def extract_number(text):
    nums = re.findall(r'-?\d+', text)
    return nums[-1] if nums else None

# The input numbers that models might echo
TASKS = [
    {"prompt": "Compute N(5,-3) where N(a,b)=a²-ab+b². Reply ONLY integer.", 
     "target": "49", "inputs": ["5", "-3", "2"], "partials": {"25": "a²", "9": "b²", "-15": "ab", "15": "|ab|"}},
    {"prompt": "Compute N(7,3) where N(a,b)=a²-ab+b². Reply ONLY integer.", 
     "target": "37", "inputs": ["7", "3", "2"], "partials": {"49": "a²", "9": "b²", "21": "ab"}},
    {"prompt": "Compute N(6,-4) where N(a,b)=a²-ab+b². Reply ONLY integer.", 
     "target": "64", "inputs": ["6", "-4", "2"], "partials": {"36": "a²", "16": "b²", "-24": "ab", "24": "|ab|"}},
]

MODELS = ["phi4-mini", "gemma3:1b", "llama3.2:1b"]
N_TRIALS = 5

def classify_answer(answer, target, inputs, partials):
    """Classify a model answer as CORRECT, ECHO, PARTIAL, or UNKNOWN."""
    if answer is None:
        return "NONE"
    if answer == target:
        return "CORRECT"
    if answer in inputs:
        return "ECHO"
    if answer in partials:
        return f"PARTIAL({partials[answer]})"
    return "UNKNOWN"

def shallow_route(answers_with_classification):
    """Route based on shallow-side constraint: trust computation over echo."""
    for ans, cls in answers_with_classification:
        if cls == "CORRECT":
            return "ACCEPT", ans
    for ans, cls in answers_with_classification:
        if cls.startswith("PARTIAL"):
            return "SCAFFOLD", f"Model computed {cls}, needs combination help"
    for ans, cls in answers_with_classification:
        if cls == "ECHO":
            return "REJECT", f"All agents echoed inputs, can't compute"
    return "UNKNOWN", "No recognizable output"

def majority_vote(answers):
    """Standard majority vote."""
    dist = Counter(answers)
    winner = dist.most_common(1)[0]
    return winner[0], winner[1] / len(answers)

print("=" * 70)
print("THE SHALLOW-SIDE CONSTRAINT — Bathymetric Routing vs Majority Vote")
print("=" * 70)
print()

for task in TASKS:
    print(f"Task: {task['prompt'][:50]}... (target: {task['target']})")
    print()
    
    # Collect answers from all models
    all_answers = []
    for model in MODELS:
        for trial in range(N_TRIALS):
            raw = query(model, task["prompt"], 60)
            ans = extract_number(raw)
            cls = classify_answer(ans, task["target"], task["inputs"], task["partials"])
            all_answers.append((ans, cls, model))
    
    # Display all answers
    for ans, cls, model in all_answers:
        tag = "✓" if cls == "CORRECT" else "◀ ECHO" if cls == "ECHO" else f"◐ {cls}" if cls.startswith("PARTIAL") else f"✗ {cls}"
        print(f"  {model:15s}: {str(ans):6s} {tag}")
    print()
    
    # MAJORITY VOTE
    answers_only = [a for a, _, _ in all_answers]
    vote_winner, vote_conf = majority_vote(answers_only)
    vote_correct = vote_winner == task["target"]
    print(f"  MAJORITY VOTE: {vote_winner} ({vote_conf:.0%} agreement) {'✓ CORRECT' if vote_correct else '✗ WRONG'}")
    
    # SHALLOW ROUTE
    classifications = [(a, c) for a, c, _ in all_answers]
    route, detail = shallow_route(classifications)
    route_correct = route == "ACCEPT"
    print(f"  SHALLOW ROUTE: {route} — {detail} {'✓ CORRECT' if route_correct else '✗ MISSED'}")
    
    # Comparison
    if vote_correct and not route_correct:
        print(f"  → Vote wins (shallow missed the correct answer)")
    elif route_correct and not vote_correct:
        print(f"  → SHALLOW WINS (majority voted for echo/error)")
    elif not vote_correct and not route_correct:
        print(f"  → Neither correct (all models failed)")
    else:
        print(f"  → Both correct")
    
    print()
    print(f"  {'─' * 60}")
    print()

# SUMMARY
print("=" * 70)
print("THE BATHYMETRIC PRINCIPLE")
print("=" * 70)
print()
print("  When models disagree:")
print("  1. READ the residue — don't just count votes")
print("  2. TRUST computation over echo")
print("  3. SCAFFOLD partial over reject")
print("  4. REJECT echo consensus — it's agreement about inability")
print()
print("  The shallow-side constraint: always assume the WORST about")
print("  what a model can do, because the cost of overestimation")
print("  (accepting a wrong answer) is catastrophic, while the cost")
print("  of underestimation (extra verification) is just tokens.")
print()
print("  The number on the chart is the shallowest integer in the")
print("  measurement's uncertainty range. Always.")
