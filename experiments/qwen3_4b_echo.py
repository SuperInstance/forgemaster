#!/usr/bin/env python3
"""
Study 8: qwen3:4b Echo Analysis — The 4B Model Test
Tests our interference hypothesis on the largest available local model.
qwen3:4b puts all reasoning in 'thinking' field, content stays empty.
We extract from thinking.
"""

import requests
import re
from collections import Counter

def ask_thinking(model, prompt, max_tokens=300):
    resp = requests.post("http://localhost:11434/api/chat", json={
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"num_predict": max_tokens}
    }, timeout=120)
    msg = resp.json()["message"]
    content = msg.get("content", "")
    thinking = msg.get("thinking", "")
    # For thinking models, extract from thinking field
    full = content if content else thinking
    return full, content, thinking

def extract_number(text):
    nums = re.findall(r'-?\d+', text)
    return nums[-1] if nums else None

N = 10

print("=" * 70)
print("STUDY 8: qwen3:4b — Echo Analysis on 4B Model")
print("=" * 70)
print()

# Test 1: Can it compute?
print("=== Basic Computation ===")
for q, expected in [
    ("What is 7 × 9? Reply ONLY integer.", "63"),
    ("What is 11 × 13? Reply ONLY integer.", "143"),
    ("What is 23 + 19? Reply ONLY integer.", "42"),
]:
    correct = 0
    answers = []
    for _ in range(N):
        full, content, thinking = ask_thinking("qwen3:4b", q, 200)
        ans = extract_number(full)
        answers.append(ans)
        if ans == expected:
            correct += 1
    dist = Counter(answers)
    rate = correct / N
    icon = "✓" if rate >= 0.8 else "~" if rate >= 0.4 else "✗"
    print(f"  {icon} {q[:50]:50s} → {rate:.0%} correct")
    print(f"     dist: {dict(dist.most_common(5))}")
    if thinking and not content:
        print(f"     (answers extracted from thinking, not content)")
    print()

# Test 2: Eisenstein Norm — the echo test
print("=== Eisenstein Norm — Echo Test ===")
tasks = [
    ("N(5,-3)=49", "Compute N(5,-3) where N(a,b)=a²-ab+b². Reply ONLY integer.", "49", ["5", "-3", "2"]),
    ("N(4,-2)=28", "Compute N(4,-2) where N(a,b)=a²-ab+b². Reply ONLY integer.", "28", ["4", "-2", "2"]),
    ("N(7,3)=37", "Compute N(7,3) where N(a,b)=a²-ab+b². Reply ONLY integer.", "37", ["7", "3", "2"]),
    ("N(6,-4)=64", "Compute N(6,-4) where N(a,b)=a²-ab+b². Reply ONLY integer.", "64", ["6", "-4", "2"]),
]

for name, prompt, target, inputs in tasks:
    correct = 0
    answers = []
    for _ in range(N):
        full, content, thinking = ask_thinking("qwen3:4b", prompt, 400)
        ans = extract_number(full)
        answers.append(ans)
        if ans == target:
            correct += 1
    
    dist = Counter(answers)
    wrong = [a for a in answers if a != target]
    wrong_echo = sum(1 for a in wrong if a in inputs)
    echo_rate = wrong_echo / len(wrong) if wrong else 0
    rate = correct / N
    
    icon = "✓" if rate >= 0.8 else "~" if rate >= 0.4 else "✗"
    echo_bar = "▓" * int(echo_rate * 10) + "░" * (10 - int(echo_rate * 10))
    
    print(f"  {icon} {name:15s}: correct={rate:.0%} echo_of_wrong={echo_rate:.0%} {echo_bar}")
    print(f"     dist: {dict(dist.most_common(5))}")
    
    # Show a thinking sample for first task
    if name == "N(5,-3)=49":
        full, content, thinking = ask_thinking("qwen3:4b", prompt, 400)
        print(f"     thinking sample: {thinking[:300]}...")
    print()

# Test 3: Death Zone — partial intermediates
print("=== Death Zone Test — Partial Intermediates ===")
for condition, prompt_extra in [
    ("NO DATA", ""),
    ("MINIMAL (formula+inputs)", "\n\nDATA: N(a,b)=a²-ab+b², a=5, b=-3"),
    ("PARTIAL (a²,ab,b² computed)", "\n\nDATA: a²=25, ab=-15, b²=9"),
    ("FULL ANSWER", "\n\nDATA: N(5,-3)=49"),
]:
    correct = 0
    for _ in range(N):
        full, _, _ = ask_thinking("qwen3:4b", 
            f"Compute N(5,-3) where N(a,b)=a²-ab+b².{prompt_extra}\nReply ONLY integer.", 400)
        ans = extract_number(full)
        if ans == "49":
            correct += 1
    rate = correct / N
    icon = "✓" if rate >= 0.8 else "~" if rate >= 0.4 else "✗"
    print(f"  {icon} {condition:35s}: {rate:.0%}")

print()

# COMPARISON TABLE
print("=" * 70)
print("CROSS-MODEL COMPARISON: Echo Rate of Wrong Answers")
print("=" * 70)
print()
print(f"  {'Model':15s} {'Size':>6s} {'N(5,-3)':>8s} {'N(4,-2)':>8s} {'N(7,3)':>8s} {'N(6,-4)':>8s}")
print(f"  {'qwen3:0.6b':15s} {'0.6B':>6s} {'N/A':>8s} {'N/A':>8s} {'N/A':>8s} {'N/A':>8s}")
print(f"  {'gemma3:1b':15s} {'1.0B':>6s} {'70%':>8s} {'60%':>8s} {'50%':>8s} {'50%':>8s}")
print(f"  {'llama3.2:1b':15s} {'1.2B':>6s} {'56%':>8s} {'56%':>8s} {'33%':>8s} {'60%':>8s}")
print(f"  {'phi4-mini':15s} {'3.8B':>6s} {'88%':>8s} {'62%':>8s} {'67%':>8s} {'30%':>8s}")
# qwen3:4b results filled in dynamically above
print()
print("  Prediction: qwen3:4b echo rate should be LOWER than phi4-mini (3.8B)")
print("  If higher or similar → echo doesn't decrease monotonically with size")
print("  If much lower → interference hypothesis supported")
