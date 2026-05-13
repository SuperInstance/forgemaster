#!/usr/bin/env python3
"""z.ai P3 Experiment: Domain Tag Routing — Python rewrite
Tests whether domain tags shift model's internal routing.
Model: glm-5-turbo (reasoning model, but gives content with high max_tokens)
"""

import json
import time
import urllib.request
import ssl
import sys

API_KEY = "703f56774c324a76b8a283ce50b15744.tLKi6d9yeYza5Spg"
BASE_URL = "https://api.z.ai/api/coding/paas/v4/chat/completions"
MODEL = "glm-5-turbo"
OUTDIR = "/home/phoenix/.openclaw/workspace/experiments/zai-p3"
RESULTS_FILE = f"{OUTDIR}/raw_results.jsonl"

PROMPTS = [
    # Math (0-1)
    "What is the derivative of x^3 * sin(x)?",
    "Prove that the square root of 2 is irrational.",
    # Physics (2-3)
    "Explain the uncertainty principle in quantum mechanics.",
    "What is the relationship between voltage, current, and resistance?",
    # Coding (4-5)
    "Write a function to reverse a linked list in Python.",
    "Explain the difference between TCP and UDP protocols.",
    # Biology (6-7)
    "How does CRISPR gene editing work at the molecular level?",
    "What is the role of mitochondria in cellular energy production?",
    # History (8-9)
    "What caused the fall of the Roman Empire?",
    "Explain the significance of the Industrial Revolution.",
]

DOMAINS = ["MATHEMATICS", "PHYSICS", "COMPUTER_SCIENCE", "BIOLOGY", "HISTORY"]
DOMAIN_MAP = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4]
MISMATCH_MAP = [2, 2, 3, 3, 4, 4, 0, 0, 1, 1]

def call_api(prompt, tag, trial, pidx, condition):
    full_prompt = f"[{tag}] {prompt}" if tag else prompt
    
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": full_prompt}],
        "max_tokens": 1000,
        "temperature": 0.3
    }).encode("utf-8")
    
    req = urllib.request.Request(
        BASE_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        }
    )
    
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        
        content = data["choices"][0]["message"]["content"]
        reasoning = data["choices"][0]["message"].get("reasoning_content", "")
        usage = data.get("usage", {})
        
        result = {
            "prompt_idx": pidx,
            "domain": DOMAINS[DOMAIN_MAP[pidx]],
            "condition": condition,
            "tag": tag,
            "trial": trial,
            "prompt": prompt,
            "response": content,
            "reasoning_length": len(reasoning),
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "reasoning_tokens": usage.get("completion_tokens_details", {}).get("reasoning_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "response_length": len(content),
        }
    except Exception as e:
        result = {
            "prompt_idx": pidx,
            "domain": DOMAINS[DOMAIN_MAP[pidx]],
            "condition": condition,
            "tag": tag,
            "trial": trial,
            "prompt": prompt,
            "response": f"ERROR: {e}",
            "reasoning_length": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "reasoning_tokens": 0,
            "total_tokens": 0,
            "response_length": 0,
        }
    
    return result

def main():
    with open(RESULTS_FILE, "w") as f:
        pass  # clear file
    
    total = 0
    start = time.time()
    print(f"Starting z.ai P3 experiment: 90 API calls (10 prompts × 3 conditions × 3 trials)")
    print(f"Model: {MODEL}, max_tokens: 1000")
    print(f"Start time: {time.strftime('%Y-%m-%dT%H:%M:%S%z')}")
    
    with open(RESULTS_FILE, "a") as f:
        for pidx in range(10):
            prompt = PROMPTS[pidx]
            domain = DOMAINS[DOMAIN_MAP[pidx]]
            mismatch = DOMAINS[MISMATCH_MAP[pidx]]
            
            for trial in range(1, 4):
                conditions = [
                    ("NOTAG", ""),
                    ("MATCHED", domain),
                    ("MISMATCHED", mismatch),
                ]
                
                for condition, tag in conditions:
                    result = call_api(prompt, tag, trial, pidx, condition)
                    f.write(json.dumps(result) + "\n")
                    f.flush()
                    
                    total += 1
                    tag_str = tag if tag else "none"
                    resp_len = result["response_length"]
                    print(f"[{total}/90] P{pidx} {condition:11s} tag={tag_str:20s} resp={resp_len:5d} chars")
                
                time.sleep(0.3)
    
    elapsed = time.time() - start
    print(f"\nDone. Total calls: {total}, elapsed: {elapsed:.1f}s")
    print(f"Results: {RESULTS_FILE}")

if __name__ == "__main__":
    main()
