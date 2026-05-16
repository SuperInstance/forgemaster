#!/usr/bin/env python3
"""Study 61: GSM8K Replication of Activation-Key Model
20 problems × 3 conditions × 4 models × 2 trials = 480 trials
"""

import json, os, time, re, sys
import requests

# ─── Load API key ───
with open(os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")) as f:
    DEEPINFRA_KEY = f.read().strip()

DEEPINFRA_URL = "https://api.deepinfra.com/v1/openai/chat/completions"
OLLAMA_URL = "http://localhost:11434/api/chat"

# ─── Problems (GSM8K-style) ───
PROBLEMS = [
    # === Addition/Subtraction (Easy) - 5 problems ===
    {"id": "add_sub_1", "difficulty": "easy", "answer": 834,
     "bare": "What is 456 plus 378?",
     "notation": "Compute 456 + 378.",
     "scaffolded": "To add 456 and 378, first add 400 + 300 = 700, then 50 + 70 = 120, then 6 + 8 = 14. Now sum: 700 + 120 + 14 = ?"},
    {"id": "add_sub_2", "difficulty": "easy", "answer": 417,
     "bare": "What is 903 minus 486?",
     "notation": "Compute 903 - 486.",
     "scaffolded": "To subtract 486 from 903: start from 903, subtract 400 to get 503, subtract 80 to get 423, subtract 6 to get ?"},
    {"id": "add_sub_3", "difficulty": "easy", "answer": 1247,
     "bare": "What is 589 plus 658?",
     "notation": "Compute 589 + 658.",
     "scaffolded": "To add 589 and 658, first add 500 + 600 = 1100, then 80 + 50 = 130, then 9 + 8 = 17. Sum: 1100 + 130 + 17 = ?"},
    {"id": "add_sub_4", "difficulty": "easy", "answer": 296,
     "bare": "What is 1000 minus 704?",
     "notation": "Compute 1000 - 704.",
     "scaffolded": "To subtract 704 from 1000, first 1000 - 700 = 300, then 300 - 4 = ?"},
    {"id": "add_sub_5", "difficulty": "easy", "answer": 1538,
     "bare": "What is 847 plus 691?",
     "notation": "Compute 847 + 691.",
     "scaffolded": "To add 847 and 691, first add 800 + 600 = 1400, then 40 + 90 = 130, then 7 + 1 = 8. Sum: 1400 + 130 + 8 = ?"},

    # === Multiplication/Division (Medium) - 5 problems ===
    {"id": "mul_div_1", "difficulty": "medium", "answer": 99186,
     "bare": "What is 347 times 286?",
     "notation": "Compute 347 times 286.",
     "scaffolded": "To multiply 347 times 286, first multiply 347 times 200 = 69400, then 347 times 80 = 27760, then 347 times 6 = 2082. Sum: 69400 + 27760 + 2082 = ?"},
    {"id": "mul_div_2", "difficulty": "medium", "answer": 67,
     "bare": "What is 469 divided by 7?",
     "notation": "Compute 469 divided by 7.",
     "scaffolded": "To divide 469 by 7, note that 7 times 60 = 420, remainder 49. Then 7 times 7 = 49, remainder 0. So 60 + 7 = ?"},
    {"id": "mul_div_3", "difficulty": "medium", "answer": 11704,
     "bare": "What is 152 times 77?",
     "notation": "Compute 152 times 77.",
     "scaffolded": "To multiply 152 times 77, first compute 152 times 70 = 10640, then 152 times 7 = 1064. Sum: 10640 + 1064 = ?"},
    {"id": "mul_div_4", "difficulty": "medium", "answer": 93,
     "bare": "What is 6696 divided by 72?",
     "notation": "Compute 6696 divided by 72.",
     "scaffolded": "To divide 6696 by 72, note 72 times 90 = 6480, remainder 216. Then 72 times 3 = 216, remainder 0. So 90 + 3 = ?"},
    {"id": "mul_div_5", "difficulty": "medium", "answer": 24384,
     "bare": "What is 508 times 48?",
     "notation": "Compute 508 times 48.",
     "scaffolded": "To multiply 508 times 48, first compute 508 times 50 = 25400, then subtract 508 times 2 = 1016. Result: 25400 - 1016 = ?"},

    # === Multi-step Word Problems (Hard) - 5 problems ===
    {"id": "word_1", "difficulty": "hard", "answer": 20,
     "bare": "A store sells pencils for $3 each and notebooks for $5 each. If Sarah buys 4 pencils and 2 notebooks, how much does she spend in total?",
     "notation": "A store sells pencils for $3 each and notebooks for $5 each. Compute the cost of 4 pencils plus 2 notebooks.",
     "scaffolded": "Sarah buys 4 pencils at $3 each and 2 notebooks at $5 each. Step 1: pencils cost 4 times 3 = 12. Step 2: notebooks cost 2 times 5 = 10. Step 3: total = 12 + 10 = ?"},
    {"id": "word_2", "difficulty": "hard", "answer": 31,
     "bare": "Tom has 45 marbles. He gives 8 to Alice and 12 to Bob. Then he finds 6 more marbles and loses 3. How many marbles does Tom have now?",
     "notation": "Starting with 45, subtract 8 and 12, add 6, subtract 3. Compute the result.",
     "scaffolded": "Tom starts with 45 marbles. Step 1: gives 8 to Alice, so 45 - 8 = 37. Step 2: gives 12 to Bob, so 37 - 12 = 25. Step 3: finds 6 more, so 25 + 6 = 31. Step 4: loses 3, so 31 - 3 = ?"},
    {"id": "word_3", "difficulty": "hard", "answer": 20,
     "bare": "A rectangular garden is 12 meters long and 8 meters wide. If you put fence posts every 2 meters along the perimeter, how many posts do you need?",
     "notation": "For a 12m by 8m rectangle, compute the number of fence posts placed every 2m along the perimeter.",
     "scaffolded": "Step 1: perimeter = 2 times (12 + 8) = 2 times 20 = 40 meters. Step 2: posts every 2 meters along a closed loop means 40 divided by 2 = ? posts."},
    {"id": "word_4", "difficulty": "hard", "answer": 84,
     "bare": "A baker makes 24 muffins per batch. If she bakes 5 batches and sells 3 dozen, how many muffins are left? One dozen equals 12.",
     "notation": "24 muffins per batch, 5 batches total, minus 3 dozen sold. Compute remaining muffins.",
     "scaffolded": "Step 1: total muffins = 24 times 5 = 120. Step 2: sold = 3 times 12 = 36. Step 3: remaining = 120 - 36 = ?"},
    {"id": "word_5", "difficulty": "hard", "answer": 234,
     "bare": "A train travels at 65 mph for 3 hours, then at 78 mph for 2 hours. What is the total distance traveled?",
     "notation": "Distance = 65 times 3 plus 78 times 2. Compute.",
     "scaffolded": "Step 1: first segment = 65 times 3 = 195 miles. Step 2: second segment = 78 times 2 = 156 miles. Step 3: total = 195 + 156 = ?"},

    # === Algebra (Hardest) - 5 problems ===
    {"id": "algebra_1", "difficulty": "hardest", "answer": 7,
     "bare": "If 3 times a number plus 11 equals 32, what is the number?",
     "notation": "Solve for x: 3x + 11 = 32.",
     "scaffolded": "To solve 3x + 11 = 32, first subtract 11 from both sides: 3x = 32 - 11 = 21. Then divide by 3: x = 21 divided by 3 = ?"},
    {"id": "algebra_2", "difficulty": "hardest", "answer": 19,
     "bare": "The sum of two numbers is 31 and their difference is 7. What is the larger number?",
     "notation": "Given x + y = 31 and x - y = 7, find x.",
     "scaffolded": "Given x + y = 31 and x - y = 7. Step 1: add the two equations to get 2x = 31 + 7 = 38. Step 2: divide both sides by 2: x = 38 divided by 2 = ?"},
    {"id": "algebra_3", "difficulty": "hardest", "answer": 14,
     "bare": "If a number squared minus 5 times the number equals 126, and the number is positive, what is the number?",
     "notation": "Solve n squared minus 5n = 126 for positive n.",
     "scaffolded": "To solve n squared minus 5n = 126, rewrite as n squared minus 5n minus 126 = 0. Step 1: find factors of -126 that sum to -5. Try 9 and -14: 9 times -14 = -126 and 9 + (-14) = -5. Step 2: factor as (n + 9)(n - 14) = 0. Since n is positive, n = ?"},
    {"id": "algebra_4", "difficulty": "hardest", "answer": 6,
     "bare": "Three consecutive integers add up to 21. What is the smallest?",
     "notation": "If n plus n+1 plus n+2 equals 21, find n.",
     "scaffolded": "Three consecutive integers: n, n+1, n+2. Step 1: sum = 3n + 3 = 21. Step 2: subtract 3: 3n = 18. Step 3: divide by 3: n = ?"},
    {"id": "algebra_5", "difficulty": "hardest", "answer": 15,
     "bare": "A number is doubled, then increased by 9, giving 39. What was the original number?",
     "notation": "Solve 2x + 9 = 39.",
     "scaffolded": "Step 1: subtract 9 from both sides: 2x = 39 - 9 = 30. Step 2: divide by 2: x = 30 divided by 2 = ?"},
]

# ─── Models ───
MODELS = {
    "seed-mini": {"tier": 1, "provider": "deepinfra", "model": "ByteDance/Seed-2.0-mini"},
    "hermes-70b": {"tier": 2, "provider": "deepinfra", "model": "NousResearch/Hermes-3-Llama-3.1-70B"},
    "gemma3-1b": {"tier": 1, "provider": "ollama", "model": "gemma3:1b"},
    "qwen3-0.6b": {"tier": 3, "provider": "ollama", "model": "qwen3:0.6b"},
}

def call_deepinfra(model_id, prompt, max_tokens=200):
    headers = {"Authorization": f"Bearer {DEEPINFRA_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0,
    }
    resp = requests.post(DEEPINFRA_URL, headers=headers, json=payload, timeout=90)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]

def call_ollama(model_id, prompt, max_tokens=200):
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0, "num_predict": max_tokens},
    }
    resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()["message"]["content"]

def call_model(model_key, prompt, max_tokens=200):
    m = MODELS[model_key]
    if m["provider"] == "deepinfra":
        return call_deepinfra(m["model"], prompt, max_tokens)
    else:
        return call_ollama(m["model"], prompt, max_tokens)

def extract_number(text):
    """Extract the most likely intended answer number from response."""
    # Try common answer patterns first
    patterns = [
        r'(?:the answer is|answer is|equals?|result is|total is|the number is|x\s*=\s*|n\s*=\s*)([+-]?\d+\.?\d*)',
        r'=\s*([+-]?\d+\.?\d*)\s*[.!]?\s*$',
    ]
    for pat in patterns:
        matches = re.findall(pat, text, re.IGNORECASE | re.MULTILINE)
        if matches:
            try:
                return float(matches[-1])
            except:
                continue
    
    # Find the last number in the text (most likely the final answer)
    numbers = re.findall(r'(\d+\.?\d*)', text)
    if numbers:
        return float(numbers[-1])
    return None

def score_answer(extracted, expected):
    if extracted is None:
        return False
    return abs(extracted - expected) < 0.01

# ─── Run Experiment ───
results = []
total_trials = len(PROBLEMS) * 3 * len(MODELS) * 2
trial_num = 0

for trial in range(2):
    for problem in PROBLEMS:
        for condition in ["bare", "notation", "scaffolded"]:
            prompt = problem[condition]
            for model_key in MODELS:
                trial_num += 1
                m = MODELS[model_key]
                print(f"[{trial_num}/{total_trials}] {model_key} T{m['tier']} | {problem['id']} | {condition} | trial {trial+1}", flush=True)
                
                try:
                    max_tok = 400 if condition == "scaffolded" else 200
                    response = call_model(model_key, prompt, max_tokens=max_tok)
                    extracted = extract_number(response)
                    correct = score_answer(extracted, problem["answer"])
                    
                    result = {
                        "trial": trial + 1,
                        "problem_id": problem["id"],
                        "difficulty": problem["difficulty"],
                        "condition": condition,
                        "model": model_key,
                        "tier": m["tier"],
                        "provider": m["provider"],
                        "expected": problem["answer"],
                        "extracted": extracted,
                        "correct": correct,
                        "response": response[:500],
                        "status": "ok"
                    }
                except Exception as e:
                    result = {
                        "trial": trial + 1,
                        "problem_id": problem["id"],
                        "difficulty": problem["difficulty"],
                        "condition": condition,
                        "model": model_key,
                        "tier": m["tier"],
                        "provider": m["provider"],
                        "expected": problem["answer"],
                        "extracted": None,
                        "correct": False,
                        "response": f"ERROR: {str(e)[:200]}",
                        "status": f"error: {type(e).__name__}"
                    }
                    print(f"  ERROR: {e}", flush=True)
                
                results.append(result)
                if m["provider"] == "deepinfra":
                    time.sleep(0.3)

# ─── Save Raw Results ───
output_path = "/home/phoenix/.openclaw/workspace/experiments/study61_results.json"
with open(output_path, "w") as f:
    json.dump(results, f, indent=2)
print(f"\nSaved {len(results)} results to {output_path}")

# ─── Analysis ───
print("\n" + "="*60)
print("STUDY 61 RESULTS")
print("="*60)

valid = [r for r in results if r["status"] == "ok"]
errors = [r for r in results if r["status"] != "ok"]
print(f"\nValid: {len(valid)}/{len(results)}, Errors: {len(errors)}")

print("\n== H1: Notation Gradient ==")
for condition in ["bare", "notation", "scaffolded"]:
    cr = [r for r in valid if r["condition"] == condition]
    c = sum(1 for r in cr if r["correct"])
    t = len(cr)
    print(f"  {condition:12s}: {c:3d}/{t:3d} = {100*c/t:.1f}%")

for tier_num in [1, 2, 3]:
    print(f"\n== Tier {tier_num} ==")
    for condition in ["bare", "notation", "scaffolded"]:
        cr = [r for r in valid if r["condition"] == condition and r["tier"] == tier_num]
        c = sum(1 for r in cr if r["correct"])
        t = len(cr)
        print(f"  {condition:12s}: {c:3d}/{t:3d} = {100*c/t:.1f}%" if t > 0 else f"  {condition:12s}: no data")

print("\n== Per-Model ==")
for mk in MODELS:
    print(f"\n  {mk} (Tier {MODELS[mk]['tier']}):")
    for condition in ["bare", "notation", "scaffolded"]:
        cr = [r for r in valid if r["condition"] == condition and r["model"] == mk]
        c = sum(1 for r in cr if r["correct"])
        t = len(cr)
        print(f"    {condition:12s}: {c:3d}/{t:3d} = {100*c/t:.1f}%")

print("\n== Per-Difficulty ==")
for diff in ["easy", "medium", "hard", "hardest"]:
    cr = [r for r in valid if r["difficulty"] == diff]
    c = sum(1 for r in cr if r["correct"])
    t = len(cr)
    print(f"  {diff:8s}: {c:3d}/{t:3d} = {100*c/t:.1f}%")

print("\n== Model x Difficulty x Condition ==")
for mk in MODELS:
    print(f"\n  {mk}:")
    for diff in ["easy", "medium", "hard", "hardest"]:
        row = f"    {diff:8s}: "
        for condition in ["bare", "notation", "scaffolded"]:
            cr = [r for r in valid if r["condition"] == condition and r["difficulty"] == diff and r["model"] == mk]
            c = sum(1 for r in cr if r["correct"])
            t = len(cr)
            pct = 100*c/t if t > 0 else 0
            row += f"{condition[:3]}={pct:4.0f}%  "
        print(row)

print("\nDone.")
