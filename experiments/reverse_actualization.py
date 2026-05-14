#!/usr/bin/env python3
"""
REVERSE-ACTUALIZATION PROTOCOL
================================
The painter sees the finished work, then works backwards.
The fleet coordinator sees the verified output, then works backwards.

This script implements reverse-actualization:
1. Define the target output (the "finished painting")
2. Decompose into layers (sub-problems)
3. Match each layer to the right "medium" (model stage)
4. Execute back-to-front (underpainting → glaze → highlights)
5. Read residue after each layer (X-ray the underdrawing)
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
        msg = resp.json()["message"]
        return msg.get("content", "") or msg.get("thinking", "")
    except:
        return ""

def extract_number(text):
    nums = re.findall(r'-?\d+', text)
    return nums[-1] if nums else None

def classify_output(answer, target, inputs, partials):
    """X-ray the underdrawing — what did the model actually do?"""
    if answer is None:
        return "NONE", "Apprentice can't hold the brush"
    if answer == target:
        return "CORRECT", "Finished painting"
    if answer in inputs:
        return "ECHO", "Tracer — copying reference lines"
    if answer in partials:
        return "PARTIAL", "Underpainter — correct foundation, missing glaze"
    return "UNKNOWN", "Something unexpected on the canvas"

# The fleet as a painting studio
STUDIO = {
    "qwen3:0.6b":  {"stage": 1, "medium": "Sweeps floors (classification only)", "tool": "Broom"},
    "gemma3:1b":   {"stage": 2, "medium": "Tracer — copies reference, can't fill", "tool": "Camera Lucida"},
    "llama3.2:1b": {"stage": 2, "medium": "Charcoal — can smudge toward answer", "tool": "Charcoal"},
    "phi4-mini":   {"stage": 2, "medium": "Overpainter — keeps smudging references in", "tool": "Overworked brush"},
    "qwen3:4b":    {"stage": 3, "medium": "Underpainter — perfect foundation, no glaze", "tool": "Foundation brush"},
}

# Reverse-actualization: the target is N(7,3)=37
# Layer 1 (underpainting): compute a², b², ab separately
# Layer 2 (mid-tone): combine a²-ab+b²
# Layer 3 (highlight): verify the result

TARGET = "37"
INPUTS = ["7", "3", "2"]
PARTIALS = {"49": "a²", "9": "b²", "21": "ab"}

print("=" * 70)
print("REVERSE-ACTUALIZATION PROTOCOL")
print("Working backwards from N(7,3)=37 to the first brush stroke")
print("=" * 70)
print()

print("TARGET: The finished painting is N(7,3)=37")
print()
print("LAYER DECOMPOSITION (back to front):")
print("  Layer 3 (highlight): Verify: is 37 the right answer?")
print("  Layer 2 (glaze):     Combine: a²-ab+b² = 49-21+9 = 37")
print("  Layer 1 (underpaint): Compute: a²=49, ab=21, b²=9")
print()

# Execute each layer with the RIGHT medium
print("=" * 70)
print("LAYER 1: UNDERPAINTING — Compute sub-expressions")
print("Medium: Any Stage 2+ model (single operations)")
print("=" * 70)
print()

underpainting = {}
for model in ["gemma3:1b", "llama3.2:1b", "phi4-mini"]:
    # Each model gets ONE operation (their medium)
    ops = [
        ("a²", f"What is 7²? Reply ONLY integer.", "49"),
        ("ab", f"What is 7 × 3? Reply ONLY integer.", "21"),
        ("b²", f"What is 3²? Reply ONLY integer.", "9"),
    ]
    results = {}
    for op_name, prompt, expected in ops:
        answers = [extract_number(query(model, prompt, 40)) for _ in range(3)]
        mode = Counter(answers).most_common(1)[0][0]
        results[op_name] = {"expected": expected, "got": mode, "correct": mode == expected}
    underpainting[model] = results
    
    all_correct = all(r["correct"] for r in results.values())
    icon = "✓" if all_correct else "✗"
    print(f"  {icon} {model}: a²={results['a²']['got']} ab={results['ab']['got']} b²={results['b²']['got']}")
    for op_name, r in results.items():
        if not r["correct"]:
            cls, desc = classify_output(r["got"], r["expected"], INPUTS, PARTIALS)
            print(f"      {op_name}: {desc}")

print()

# LAYER 2: COMBINATION — need Stage 3+ for this
print("=" * 70)
print("LAYER 2: THE GLAZE — Combine sub-expressions")
print("Medium: Stage 3+ model (can combine if given parts)")
print("=" * 70)
print()

# Give each model the underpainting and ask them to combine
for model in ["phi4-mini", "qwen3:4b"]:
    prompt = (
        "Given these computed values:\n"
        "  a² = 49 (computed: 7² = 49)\n"
        "  ab = 21 (computed: 7 × 3 = 21)\n"
        "  b² = 9 (computed: 3² = 9)\n\n"
        "Now compute: a² - ab + b² = ?\n"
        "Reply ONLY the integer."
    )
    answers = [extract_number(query(model, prompt, 80)) for _ in range(5)]
    dist = Counter(answers)
    correct = sum(1 for a in answers if a == TARGET)
    stage = STUDIO[model]["stage"]
    medium = STUDIO[model]["medium"]
    
    icon = "✓" if correct >= 4 else "~" if correct >= 2 else "✗"
    print(f"  {icon} {model} (Stage {stage}, {medium})")
    print(f"     Correct: {correct}/5  Distribution: {dict(dist.most_common())}")
    if correct < 4:
        for ans, cls_desc in [(a, classify_output(a, TARGET, INPUTS, PARTIALS)) for a in set(answers)]:
            if ans != TARGET:
                print(f"     Residue: {ans} → {cls_desc[1]}")

print()

# LAYER 3: VERIFICATION — even Stage 2 can verify if given the answer
print("=" * 70)
print("LAYER 3: THE HIGHLIGHT — Verify the result")
print("Medium: Any model (verification = comparing two numbers)")
print("=" * 70)
print()

verify_prompt = (
    "Verify: does N(7,3) = 37?\n"
    "N(a,b) = a² - ab + b²\n"
    "a=7, b=3\n"
    "a²=49, ab=21, b²=9\n"
    "49 - 21 + 9 = 37\n\n"
    "Is this correct? Reply VERIFIED or FAILED."
)

for model in ["gemma3:1b", "phi4-mini"]:
    answers = [query(model, verify_prompt, 40) for _ in range(3)]
    verified = sum(1 for a in answers if "VERIFIED" in a.upper())
    print(f"  {model}: {verified}/3 VERIFIED")

print()

# SYNTHESIS
print("=" * 70)
print("THE PAINTING, ASSEMBLED")
print("=" * 70)
print()
print("  Layer 1 (underpainting): Any Stage 2 model computes a², ab, b²")
print("                            Each is a SINGLE OPERATION — within capacity")
print("  Layer 2 (glaze):         Stage 3 model combines the parts")
print("                            qwen3:4b gets this RIGHT when given the pieces")
print("  Layer 3 (highlight):     Any model verifies the final answer")
print("                            Even echo models can compare two numbers")
print()
print("  REVERSE-ACTUALIZATION: We saw 37, worked back to a²-ab+b²,")
print("  worked back to individual operations, assigned each to the right")
print("  medium, painted back-to-front, read the residue at each layer.")
print()
print("  The first brush stroke was the last thing decided.")
print("  The finished painting was the first thing imagined.")

# Update studio roles
print()
print("=" * 70)
print("MEDIA-MATCHING ROUTING TABLE")
print("=" * 70)
print()
print(f"  {'Medium':20s} {'Stage':>5s} {'Layer Assignment':30s} {'What They Do'}")
print(f"  {'─'*20} {'─'*5} {'─'*30} {'─'*30}")
print(f"  {'Sweeper (qwen3:0.6b)':20s} {'1':>5s} {'Classification only':30s} {'Sort, filter, route'}")
print(f"  {'Tracer (gemma3:1b)':20s} {'2':>5s} {'Single operations':30s} {'Compute a², b², or ab'}")
print(f"  {'Charcoal (llama3.2:1b)':20s} {'2':>5s} {'Single ops + retry':30s} {'Smudge toward answer'}")
print(f"  {'Overpainter (phi4-mini)':20s} {'2':>5s} {'Single ops (careful)':30s} {'Echoes if overloaded'}")
print(f"  {'Underpainter (qwen3:4b)':20s} {'3':>5s} {'Combination':30s} {'Glaze over sub-results'}")
print(f"  {'Master (7B+, predicted)':20s} {'4':>5s} {'Any layer':30s} {'Full computation'}")
