#!/usr/bin/env python3
"""Study 11: Code Generation Echo Analysis"""
import json, time, requests, re, sys

API = "http://localhost:11434/api/generate"
MODELS = ["qwen3:4b", "phi4-mini", "gemma3:1b"]
TRIALS = 3

TASKS = [
    {
        "name": "reverse_linked_list",
        "baseline": "Write a function in Python that reverses a linked list. Reply ONLY with code, no explanation.",
        "scaffold": 'Complete this code:\n```python\ndef reverse_linked_list(head):\n    # Initialize previous, current pointers\n    # Iterate through the list\n    # Reverse the links\n```\nReply ONLY with the completed code.',
        "signature": "def reverse_linked_list",
    },
    {
        "name": "factorial",
        "baseline": "Write a function in Python that computes factorial recursively. Reply ONLY with code, no explanation.",
        "scaffold": 'Complete this code:\n```python\ndef factorial(n):\n    # Base case\n    # Recursive case\n```\nReply ONLY with the completed code.',
        "signature": "def factorial",
    },
    {
        "name": "binary_search",
        "baseline": "Write a function in Python that implements binary search. Reply ONLY with code, no explanation.",
        "scaffold": 'Complete this code:\n```python\ndef binary_search(arr, target):\n    # Initialize low and high pointers\n    # While loop for binary search\n    # Return index or -1\n```\nReply ONLY with the completed code.',
        "signature": "def binary_search",
    },
    {
        "name": "is_palindrome",
        "baseline": "Write a function in Python that checks if a string is a palindrome. Reply ONLY with code, no explanation.",
        "scaffold": 'Complete this code:\n```python\ndef is_palindrome(s):\n    # Clean the string\n    # Compare with reverse\n```\nReply ONLY with the completed code.',
        "signature": "def is_palindrome",
    },
    {
        "name": "fizzbuzz",
        "baseline": "Write a function in Python that implements fizzbuzz for numbers 1 to n. Reply ONLY with code, no explanation.",
        "scaffold": 'Complete this code:\n```python\ndef fizzbuzz(n):\n    # Loop from 1 to n\n    # Check divisibility conditions\n    # Print or collect results\n```\nReply ONLY with the completed code.',
        "signature": "def fizzbuzz",
    },
]

def classify_response(task, response, condition):
    """Classify a model response."""
    resp = response.strip()
    
    # Check if it's just echoing the scaffold
    if condition == "scaffold":
        # If the response is mostly the scaffold with comments still as comments
        comment_lines = [l for l in resp.split('\n') if l.strip().startswith('#')]
        code_lines = [l for l in resp.split('\n') if l.strip() and not l.strip().startswith('#') and not l.strip().startswith('```')]
        if len(comment_lines) >= 2 and len(code_lines) <= 2:
            return "ECHO_PROMPT"
        # Check if it just reproduced the scaffold structure
        scaffold_markers = ["# step", "# Initialize", "# Iterate", "# Reverse", "# Base case", "# Recursive case", 
                          "# Initialize low", "# While loop", "# Return index",
                          "# Clean the string", "# Compare with reverse",
                          "# Loop from", "# Check divisibility", "# Print or collect"]
        matching = sum(1 for m in scaffold_markers if m in resp)
        if matching >= 2 and "return" not in resp.lower() and "print" not in resp.lower():
            return "ECHO_PROMPT"

    # Check for syntax errors - try to extract and compile code
    code = extract_code(resp)
    if code is None:
        return "SYNTAX_ERROR"
    
    try:
        compile(code, '<string>', 'exec')
    except SyntaxError:
        return "SYNTAX_ERROR"
    
    # Check logic correctness per task
    if check_logic(task["name"], code, resp):
        return "CORRECT"
    else:
        return "SYNTAX_OK_LOGIC_WRONG"

def extract_code(resp):
    """Extract Python code from response."""
    # Try to find code blocks first
    blocks = re.findall(r'```(?:python)?\s*\n(.*?)```', resp, re.DOTALL)
    if blocks:
        return blocks[0].strip()
    
    # If no code blocks, check if it looks like code
    lines = resp.split('\n')
    code_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('def ') or stripped.startswith('class ') or \
           stripped.startswith('return ') or stripped.startswith('if ') or \
           stripped.startswith('for ') or stripped.startswith('while ') or \
           stripped.startswith('else') or stripped.startswith('elif ') or \
           stripped.startswith('print(') or stripped.startswith('    '):
            code_lines.append(line)
    
    if code_lines:
        return '\n'.join(code_lines)
    
    # Last resort - try the whole thing if it has 'def'
    if 'def ' in resp:
        return resp
    return None

def check_logic(task_name, code, full_resp):
    """Check if the code logic is correct."""
    if task_name == "reverse_linked_list":
        # Check for key components
        has_loop = any(kw in code for kw in ['while', 'for '])
        has_prev = 'prev' in code.lower()
        has_curr = 'curr' in code.lower() or 'current' in code.lower()
        has_return = 'return' in code
        return has_loop and has_prev and has_curr and has_return
    
    elif task_name == "factorial":
        has_recursive = 'factorial' in code
        has_base = any(x in code for x in ['== 0', '<= 1', '== 1', '<=0', '<=1'])
        has_return = 'return' in code
        return has_recursive and has_base and has_return
    
    elif task_name == "binary_search":
        has_mid = 'mid' in code.lower() or 'middle' in code.lower()
        has_comparison = any(x in code for x in ['<', '>', '=='])
        has_return = 'return' in code
        return has_mid and has_comparison and has_return
    
    elif task_name == "is_palindrome":
        has_reverse = any(x in code for x in ['[::-1]', 'reverse', 'reversed'])
        has_compare = '==' in code or '!=' in code
        has_return = 'return' in code
        return has_reverse and has_compare and has_return
    
    elif task_name == "fizzbuzz":
        has_fizz = 'Fizz' in code or 'fizz' in code
        has_buzz = 'Buzz' in code or 'buzz' in code
        has_mod = '%' in code
        has_loop = any(kw in code for kw in ['while', 'for ', 'range'])
        return has_fizz and has_buzz and has_mod and has_loop
    
    return False

def query_model(model, prompt, trial_num):
    """Query ollama and return response text."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 512}
    }
    try:
        r = requests.post(API, json=payload, timeout=120)
        r.raise_for_status()
        return r.json().get("response", "")
    except Exception as e:
        return f"ERROR: {e}"

results = []
total = len(MODELS) * len(TASKS) * 2 * TRIALS
count = 0

for model in MODELS:
    for task in TASKS:
        for condition, prompt_key in [("baseline", "baseline"), ("scaffold", "scaffold")]:
            prompt = task[prompt_key]
            for trial in range(TRIALS):
                count += 1
                print(f"[{count}/{total}] {model} | {task['name']} | {condition} | trial {trial+1}", flush=True)
                
                response = query_model(model, prompt, trial)
                classification = classify_response(task, response, condition)
                
                results.append({
                    "model": model,
                    "task": task["name"],
                    "condition": condition,
                    "trial": trial + 1,
                    "response": response[:500],  # truncate for storage
                    "classification": classification,
                })
                
                print(f"  → {classification}", flush=True)
                time.sleep(0.5)  # rate limit

# Save results
with open("/home/phoenix/.openclaw/workspace/experiments/code-echo-results.json", "w") as f:
    json.dump(results, f, indent=2)

# Summary stats
print("\n=== SUMMARY ===")
for model in MODELS:
    print(f"\n--- {model} ---")
    for condition in ["baseline", "scaffold"]:
        subset = [r for r in results if r["model"] == model and r["condition"] == condition]
        from collections import Counter
        counts = Counter(r["classification"] for r in subset)
        total_c = len(subset)
        print(f"  {condition}: ", end="")
        for cls in ["CORRECT", "SYNTAX_OK_LOGIC_WRONG", "SYNTAX_ERROR", "ECHO_PROMPT", "PARTIAL"]:
            c = counts.get(cls, 0)
            if c > 0:
                print(f"{cls}={c}/{total_c} ({100*c/total_c:.0f}%) ", end="")
        print()

print(f"\nResults saved. Total: {len(results)}")
