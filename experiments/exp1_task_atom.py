#!/usr/bin/env python3
"""
Experiment 1: Task Decomposition Frontier
What's the smallest unit of work that an agent can pick up zero-shot?

Test 5 decomposition styles against a cheap model (Seed-2.0-mini via DeepInfra).
Each style gets the same task: "Verify SplineLinear compression on drift-detect".

Metric: Can the agent complete the task correctly with ZERO prior context?
"""

import requests, json, time, os, sys

KEY = open(os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")).read().strip()
MODEL = "ByteDance/Seed-2.0-mini"
URL = "https://api.deepinfra.com/v1/openai/chat/completions"

TASK = "Verify that SplineLinear achieves 20× compression on drift-detect while maintaining 100% accuracy"

# 5 decomposition styles
decompositions = {
    "crewai_task": {
        "name": "CrewAI-style",
        "prompt": f"""You are a verification agent. Complete this task:

Task: {TASK}
Expected Output: A 2-3 sentence verification statement with specific numbers
Agent: verification-agent-1

Provide the expected output."""
    },
    
    "a2a_message": {
        "name": "A2A-style",
        "prompt": f"""Message from: foragemster
Message to: verifier
Content-Type: text/plain

{TASK}

Please verify and respond with a Message containing your findings as Parts."""
    },
    
    "raw_tile": {
        "name": "Raw PLATO tile",
        "prompt": f"""PLATO Tile: tile-spline-verify-001
Room: experiment-1

{TASK}

Submit your verification as a result tile."""
    },
    
    "tile_with_perspective": {
        "name": "PLATO tile + perspectives",
        "prompt": f"""PLATO Tile: tile-spline-verify-001

[INTENT] {TASK}
[CONTEXT] SplineLinear uses Eisenstein lattice weight parameterization. Dense weights are float64 (8 bytes). SplineLinear stores (a,b) pairs as int16 (4 bytes). drift-detect has 16K parameters. 100% accuracy = all test samples correct.
[ACCEPT] State: achieved compression ratio (number) AND accuracy (percentage)

Complete this verification."""
    },
    
    "jipr_atom": {
        "name": "JIPR atom (Intent+Context+Accept)",
        "prompt": f"""DO: {TASK}

NEED: SplineLinear stores Eisenstein integer coordinates (int16 pairs) instead of float64 weights. drift-detect task, 16K parameters, 100% accuracy baseline.

DONE WHEN: You state the compression ratio and whether accuracy is maintained."""
    },
}

def query(prompt, max_tokens=200):
    resp = requests.post(URL,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0,
        }, timeout=30)
    data = resp.json()
    return data["choices"][0]["message"]["content"]

def score_response(response):
    """Score 0-3: 0=nothing, 1=vague, 2=partially correct, 3=correct with numbers"""
    score = 0
    r = response.lower()
    
    # Mentions compression ratio
    if any(x in r for x in ["2x", "4x", "8x", "16x", "20x"]):
        score += 1
    elif "compression" in r:
        score += 0.5
    
    # Mentions accuracy
    if "100%" in r or "accuracy" in r:
        score += 1
    
    # Correct math (8 bytes / 4 bytes = 2x per weight, or 16K × factor)
    if "2x" in r or "20x" in r or "16k" in r:
        score += 0.5
    
    # Shows understanding of the mechanism
    if any(x in r for x in ["eisenstein", "int16", "lattice", "parameter"]):
        score += 0.5
    
    return min(score, 3)

results = {}
for key, decomp in decompositions.items():
    print(f"Testing: {decomp['name']}...", end=" ", flush=True)
    try:
        start = time.time()
        response = query(decomp["prompt"])
        elapsed = time.time() - start
        score = score_response(response)
        tokens = len(response.split())
        
        results[key] = {
            "name": decomp["name"],
            "score": score,
            "tokens": tokens,
            "time": round(elapsed, 2),
            "response": response[:200],
        }
        print(f"score={score:.1f} tokens={tokens} time={elapsed:.1f}s")
    except Exception as e:
        results[key] = {"name": decomp["name"], "error": str(e)}
        print(f"ERROR: {e}")

# Summary
print("\n" + "="*60)
print("EXPERIMENT 1 RESULTS: Task Decomposition Frontier")
print("="*60)
print(f"{'Style':<25} {'Score':<8} {'Tokens':<8} {'Time':<8}")
print("-"*60)
for key, r in results.items():
    if "error" in r:
        print(f"{r['name']:<25} ERROR: {r['error'][:40]}")
    else:
        print(f"{r['name']:<25} {r['score']:<8.1f} {r['tokens']:<8} {r['time']:<8.2f}s")

# Winner
winner = max((r for r in results.values() if "score" in r), key=lambda r: r["score"])
print(f"\nWinner: {winner['name']} (score={winner['score']:.1f})")
print(f"\nResponse preview:\n{winner.get('response', '')[:300]}")
